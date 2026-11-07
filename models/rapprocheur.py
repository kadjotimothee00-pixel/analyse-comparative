"""Étape 3 : rapprochement des articles de chaque enseigne avec le catalogue commun.

Méthode : chaque nom est normalisé (minuscules, sans accents, unités et synonymes unifiés)
puis découpé en mots. Pour chaque produit du catalogue, on calcule un score :

    score = nombre de mots communs - nombre de mots "chiffrés" qui contredisent le catalogue

Un mot chiffré est un mot qui contient un chiffre (128, a15, 40i, 1.5...). S'il figure dans
l'article mais pas dans le produit du catalogue, c'est une contradiction (un Galaxy A25 ne
doit pas être associé à un Galaxy A15). Le produit au meilleur score est retenu, à condition
que le score atteigne un seuil et que le résultat ne soit pas ambigu.
"""

import difflib
import re
import unicodedata

import numpy as np
import pandas as pd

import config

# Mots ignorés : articles, mots génériques ou sans valeur d'identification
MOTS_IGNORES = {
    "de", "du", "la", "le", "les", "a", "et", "sur", "pour", "avec",
    "pied", "sans", "fil", "wireless", "core", "pc", "portable", "laptop", "air", "steam",
}

# Synonymes : mot rencontré -> mot du catalogue (peut donner plusieurs mots)
SYNONYMES = {
    "gb": "go", "tb": "to",
    "frigo": "refrigerateur", "fridge": "refrigerateur",
    "clim": "climatiseur", "conditioner": "climatiseur",
    "ventilo": "ventilateur",
    "monitor": "ecran",
    "kettle": "bouilloire", "electric": "electrique",
    "blender": "mixeur",
    "iron": "fer",
    "microwave": "micro ondes",
    "mouse": "souris",
    "printer": "imprimante",
    "dd": "disque dur",
}


def normaliser(texte):
    """Transforme un nom de produit en liste de mots normalisés."""
    t = unicodedata.normalize("NFKD", str(texte)).encode("ascii", "ignore").decode("ascii")
    t = t.lower()
    t = t.replace('"', " pouces ")                      # 43" devient 43 pouces
    t = re.sub(r"(\d),(\d)", r"\1.\2", t)               # 1,5 devient 1.5
    t = re.sub(r"(\d+(?:\.\d+)?)\s*hp\b", r"\1 cv", t)  # 1.5HP devient 1.5 cv (cheval-vapeur)
    t = re.sub(r"(\d+(?:\.\d+)?)\s*(gb|go|tb|to|l|cv)\b", r"\1 \2", t)  # 128GB devient 128 gb
    t = re.sub(r"[^a-z0-9. ]", " ", t)                  # ponctuation, tirets, barres
    mots = []
    for mot in t.split():
        mot = mot.strip(".")
        if not mot:
            continue
        mot = SYNONYMES.get(mot, mot)
        for sous_mot in mot.split():
            if sous_mot not in MOTS_IGNORES:
                mots.append(sous_mot)
    return mots


def contient_chiffre(mot):
    return any(caractere.isdigit() for caractere in mot)


class Rapprocheur:
    """Associe chaque article à un produit_id du catalogue."""

    def __init__(self, catalogue, journal):
        self.journal = journal
        self.noms = dict(zip(catalogue["produit_id"], catalogue["nom"]))
        self.mots_catalogue = {
            pid: set(normaliser(nom)) for pid, nom in self.noms.items()
        }

    def _mot_proche(self, mot, candidats):
        """Mot du catalogue ressemblant à 'mot' (faute de frappe), ou None."""
        if contient_chiffre(mot) or len(mot) < 5:
            return None
        proches = difflib.get_close_matches(
            mot, [c for c in candidats if not contient_chiffre(c)],
            n=1, cutoff=config.SEUIL_SIMILARITE_MOT)
        return proches[0] if proches else None

    def _evaluer(self, mots_article, mots_produit):
        """Renvoie (score, couverture, corrections) pour un couple article / produit."""
        communs = set()
        corrections = {}
        for mot in mots_article:
            if mot in mots_produit:
                communs.add(mot)
            else:
                proche = self._mot_proche(mot, mots_produit)
                if proche is not None:
                    communs.add(proche)
                    corrections[mot] = proche
        contradictions = {
            m for m in mots_article if contient_chiffre(m) and m not in mots_produit
        }
        score = len(communs) - len(contradictions)
        couverture = len(communs) / len(mots_produit) if mots_produit else 0.0
        return score, couverture, corrections

    def rapprocher(self, df):
        """Ajoute les colonnes produit_id, nom_catalogue et score_rapprochement."""
        j = self.journal
        etape = "Rapprochement"
        df = df.copy()
        identifiants, scores = [], []

        for _, ligne in df.iterrows():
            mots = normaliser(ligne["designation"])
            resultats = []
            for pid, mots_produit in self.mots_catalogue.items():
                score, couverture, corrections = self._evaluer(mots, mots_produit)
                resultats.append((score, couverture, pid, corrections))
            resultats.sort(key=lambda r: (r[0], r[1]), reverse=True)
            meilleur, second = resultats[0], resultats[1]
            etiquette = "{} ({})".format(ligne["ref_source"], ligne["designation_brute"].strip())

            if meilleur[0] < config.SEUIL_SCORE_RAPPROCHEMENT:
                j.ajouter(ligne["source"], "EXCLUSION",
                          "{} : aucun produit du catalogue ne correspond (meilleur score {}), "
                          "article ignoré.".format(etiquette, meilleur[0]), etape=etape)
                identifiants.append(None)
                scores.append(meilleur[0])
            elif (meilleur[0], meilleur[1]) == (second[0], second[1]):
                j.ajouter(ligne["source"], "ALERTE",
                          "{} : correspondance ambiguë entre {} et {}, article ignoré.".format(
                              etiquette, meilleur[2], second[2]), etape=etape)
                identifiants.append(None)
                scores.append(meilleur[0])
            else:
                identifiants.append(meilleur[2])
                scores.append(meilleur[0])
                for mot, proche in meilleur[3].items():
                    j.ajouter(ligne["source"], "CORRECTION",
                              "{} : mot '{}' reconnu comme '{}' (faute de frappe probable), "
                              "article associé à {}.".format(etiquette, mot, proche, meilleur[2]),
                              etape=etape)

        df["produit_id"] = identifiants
        df["nom_catalogue"] = df["produit_id"].map(self.noms)
        df["score_rapprochement"] = scores

        total = len(df)
        rapproches = int(df["produit_id"].notna().sum())
        j.ajouter("Global", "INFO", "{} articles rapprochés sur {}.".format(rapproches, total),
                  etape=etape)

        # Deux articles d'une même enseigne associés au même produit : anomalie
        for (source, pid), groupe in df[df["produit_id"].notna()].groupby(["source", "produit_id"]):
            if len(groupe) > 1:
                j.ajouter(source, "ALERTE", "{} associé à {} articles ({}) : le prix le plus "
                          "bas sera retenu.".format(pid, len(groupe), ", ".join(groupe["ref_source"])),
                          etape=etape)

        # Couverture du catalogue par enseigne
        tous = list(self.noms)
        for source in config.ENSEIGNES:
            presents = set(df.loc[df["source"] == source, "produit_id"].dropna())
            absents = [p for p in tous if p not in presents]
            j.ajouter(source, "INFO",
                      "{} produits du catalogue sur {} présents. Absents : {}.".format(
                          len(presents), len(tous), ", ".join(absents) if absents else "aucun"),
                      etape=etape)
        return df
