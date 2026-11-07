"""Étape 2 : nettoyage des trois sources et mise en forme dans une structure commune.

Chaque anomalie repérée est consignée dans le journal. Après le nettoyage, tous les
articles ont les mêmes colonnes (voir COLONNES), quelle que soit l'enseigne d'origine.
"""

import numpy as np
import pandas as pd

import config
from models.journal import Journal
from models.outils import calculer_prix_paye, en_nombre, formater_fcfa

# Colonnes de la structure commune
COLONNES = [
    "source",             # enseigne
    "ref_source",         # référence chez l'enseigne
    "designation_brute",  # nom tel qu'il apparaît dans le fichier
    "designation",        # nom nettoyé (espaces)
    "prix_affiche",       # prix affiché (comparable à l'historique)
    "frais_livraison",    # frais ajoutés au prix affiché
    "remise_pct",         # remise appliquée au prix affiché
    "prix_paye",          # prix réellement payé par le client
    "stock",              # quantité disponible (vide si inconnue)
    "statut_stock",       # En stock, Stock limité ou Rupture
    "disponible",         # True si l'article peut être acheté
    "retrait_boutique",   # True si l'article se retire en magasin
    "note_clients",
    "nb_avis",
]


class Nettoyeur:
    """Nettoie les données et tient le journal des anomalies."""

    def __init__(self, journal=None):
        self.journal = journal if journal is not None else Journal()

    # ------------------------------------------------------------------
    # Point d'entrée
    # ------------------------------------------------------------------
    def nettoyer(self, brut):
        """Renvoie (DataFrame commun, journal) à partir du dictionnaire du Chargeur."""
        marche = self._nettoyer_marche_lagune(brut["marche_lagune"])
        baobab = self._nettoyer_baobab(brut["baobab"], brut["baobab_meta"])
        comptoir = self._nettoyer_comptoir(brut["comptoir"])

        df = pd.concat([marche, baobab, comptoir], ignore_index=True)
        df["prix_corrige"] = False
        df["exploitable"] = df["disponible"] & df["prix_paye"].notna()
        self.journal.ajouter(
            "Global",
            "INFO",
            "{} articles dans la structure commune, dont {} exploitables "
            "(disponibles et avec un prix).".format(len(df), int(df["exploitable"].sum())),
        )
        return df, self.journal

    # ------------------------------------------------------------------
    # Marché Lagune (CSV)
    # ------------------------------------------------------------------
    def _nettoyer_marche_lagune(self, brut):
        src = config.MARCHE_LAGUNE
        j = self.journal
        df = brut.copy()
        j.ajouter(
            src, "INFO",
            "{} lignes lues (CSV, séparateur ';', BOM UTF-8 retiré à la lecture).".format(len(df)),
        )

        colonnes = ["reference", "designation", "prix", "ancien_prix",
                    "disponibilite", "note_clients", "nb_avis"]
        df["designation_brute"] = df["designation"]
        for colonne in colonnes:
            df[colonne] = df[colonne].astype(str).str.strip()
        df["designation"] = df["designation"].map(lambda s: " ".join(s.split()))

        # Espaces superflus dans les désignations
        modifiees = df[df["designation"] != df["designation_brute"]]
        for _, ligne in modifiees.iterrows():
            j.ajouter(src, "INFO", "{} : espaces superflus autour de la désignation "
                      "'{}', supprimés (la casse est ignorée au rapprochement).".format(
                          ligne["reference"], ligne["designation_brute"]))

        # Doublons exacts
        masque_doublon = df.duplicated(subset=colonnes, keep="first")
        for _, ligne in df[masque_doublon].iterrows():
            j.ajouter(src, "EXCLUSION", "{} ({}) : ligne en double (identique à une ligne "
                      "précédente), supprimée.".format(ligne["reference"], ligne["designation"]))
        df = df[~masque_doublon].reset_index(drop=True)
        references_repetees = df.loc[df["reference"].duplicated(), "reference"].tolist()
        if references_repetees:
            j.ajouter(src, "ALERTE", "Références répétées avec des valeurs différentes : "
                      + ", ".join(references_repetees))

        # Prix au format texte
        j.ajouter(src, "INFO", "Colonne 'prix' au format texte avec séparateur de milliers et "
                  "unité 'FCFA' (ex. '102 900 FCFA') : convertie en nombre.")
        nb_fines = int(df["prix"].str.contains("\u202f", regex=False).sum())
        if nb_fines:
            j.ajouter(src, "INFO", "{} prix utilisent l'espace insécable fine (code U+202F) comme "
                      "séparateur de milliers : retirée avant la conversion (un simple split sur "
                      "l'espace normale ne suffirait pas).".format(nb_fines))
        df["prix_affiche"] = df["prix"].map(en_nombre)
        df["ancien_prix_num"] = df["ancien_prix"].map(en_nombre)

        # Prix absents ou non numériques
        for _, ligne in df[df["prix_affiche"].isna()].iterrows():
            if ligne["prix"] == "":
                motif = "prix absent"
            else:
                motif = "prix non numérique '{}'".format(ligne["prix"])
            complement = ""
            if not pd.isna(ligne["ancien_prix_num"]):
                complement = (" L'ancien_prix ({} FCFA) est un prix barré, pas un prix de "
                              "vente : ignoré.".format(formater_fcfa(ligne["ancien_prix_num"])))
            j.ajouter(src, "EXCLUSION", "{} ({}) : {}, article sans prix exploitable.{}".format(
                ligne["reference"], ligne["designation"], motif, complement))

        # Prix barré inférieur au prix affiché : incohérent
        incoherents = df[df["ancien_prix_num"].notna() & df["prix_affiche"].notna()
                         & (df["ancien_prix_num"] < df["prix_affiche"])]
        for _, ligne in incoherents.iterrows():
            j.ajouter(src, "ALERTE", "{} ({}) : ancien_prix ({} FCFA) inférieur au prix affiché "
                      "({} FCFA), prix suspect (voir le contrôle de cohérence).".format(
                          ligne["reference"], ligne["designation"],
                          formater_fcfa(ligne["ancien_prix_num"]),
                          formater_fcfa(ligne["prix_affiche"])))

        # Disponibilité
        connus = {"En stock", "Stock limité", "Rupture"}
        for _, ligne in df[~df["disponibilite"].isin(connus)].iterrows():
            j.ajouter(src, "ALERTE", "{} : disponibilité inconnue '{}', article non retenu.".format(
                ligne["reference"], ligne["disponibilite"]))
        df["disponible"] = df["disponibilite"].isin({"En stock", "Stock limité"})
        for _, ligne in df[df["disponibilite"] == "Rupture"].iterrows():
            j.ajouter(src, "EXCLUSION", "{} ({}) : en rupture de stock, non retenu comme offre.".format(
                ligne["reference"], ligne["designation"]))
        limites = df.loc[df["disponibilite"] == "Stock limité", "reference"].tolist()
        if limites:
            j.ajouter(src, "INFO", "{} articles en 'Stock limité' ({}) : conservés comme "
                      "disponibles.".format(len(limites), ", ".join(limites)))

        # Note à virgule décimale
        j.ajouter(src, "INFO", "Colonne 'note_clients' avec virgule décimale (ex. '4,0') : "
                  "convertie en nombre.")
        df["note_clients"] = df["note_clients"].map(en_nombre)
        df["nb_avis"] = df["nb_avis"].map(en_nombre)

        j.ajouter(src, "INFO", "Le prix affiché inclut déjà la livraison : prix payé = prix affiché.")

        return pd.DataFrame({
            "source": src,
            "ref_source": df["reference"],
            "designation_brute": df["designation_brute"],
            "designation": df["designation"],
            "prix_affiche": df["prix_affiche"],
            "frais_livraison": 0.0,
            "remise_pct": 0.0,
            "prix_paye": df["prix_affiche"],
            "stock": np.nan,
            "statut_stock": df["disponibilite"],
            "disponible": df["disponible"],
            "retrait_boutique": False,
            "note_clients": df["note_clients"],
            "nb_avis": df["nb_avis"],
        })[COLONNES]

    # ------------------------------------------------------------------
    # Baobab Shop (JSON)
    # ------------------------------------------------------------------
    def _nettoyer_baobab(self, brut, meta):
        src = config.BAOBAB_SHOP
        j = self.journal
        renommage = {
            "sku": "ref_source",
            "title": "designation_brute",
            "pricing.amount": "prix_affiche",
            "pricing.currency": "devise",
            "pricing.delivery_fee": "frais_livraison",
            "stock": "stock",
            "seller": "vendeur",
            "rating.average": "note_clients",
            "rating.count": "nb_avis",
        }
        manquantes = [c for c in renommage if c not in brut.columns]
        if manquantes:
            raise ValueError("Colonnes absentes du JSON de Baobab Shop : " + ", ".join(manquantes))
        df = brut.rename(columns=renommage).copy()

        j.ajouter(src, "INFO", "{} articles lus (JSON de l'application, structure imbriquée "
                  "aplatie : pricing.* et rating.*).".format(len(df)))

        # Cohérence de l'en-tête
        annonce = meta.get("count")
        if annonce is not None and annonce != len(df):
            j.ajouter(src, "ALERTE", "L'en-tête annonce {} articles mais {} sont présents.".format(
                annonce, len(df)))
        else:
            j.ajouter(src, "INFO", "Nombre d'articles conforme à l'en-tête du JSON ({}).".format(len(df)))
        devises = set(df["devise"].dropna().unique()) | {meta.get("currency")}
        if devises != {"XOF"}:
            j.ajouter(src, "ALERTE", "Devises rencontrées : {} (XOF attendu).".format(
                ", ".join(sorted(str(d) for d in devises))))
        else:
            j.ajouter(src, "INFO", "Toutes les valeurs sont en XOF (équivalent du FCFA).")

        df["designation_brute"] = df["designation_brute"].astype(str)
        df["designation"] = df["designation_brute"].map(lambda s: " ".join(s.split()))
        df["prix_affiche"] = pd.to_numeric(df["prix_affiche"], errors="coerce")
        df["frais_livraison"] = pd.to_numeric(df["frais_livraison"], errors="coerce")
        df["stock"] = pd.to_numeric(df["stock"], errors="coerce")

        # Prix absent (null)
        for _, ligne in df[df["prix_affiche"].isna()].iterrows():
            j.ajouter(src, "EXCLUSION", "{} ({}) : montant absent (null), article sans prix "
                      "exploitable.".format(ligne["ref_source"], ligne["designation"]))

        # Frais de livraison manquants
        manquants = df["frais_livraison"].isna()
        if manquants.any():
            j.ajouter(src, "ALERTE", "{} frais de livraison manquants, remplacés par 0.".format(
                int(manquants.sum())))
            df.loc[manquants, "frais_livraison"] = 0.0

        # Stock
        for _, ligne in df[df["stock"].isna()].iterrows():
            j.ajouter(src, "ALERTE", "{} : stock inconnu, article non retenu.".format(ligne["ref_source"]))
        df["disponible"] = df["stock"] > 0
        df["statut_stock"] = np.where(df["disponible"], "En stock", "Rupture")
        for _, ligne in df[df["stock"] == 0].iterrows():
            j.ajouter(src, "EXCLUSION", "{} ({}) : stock = 0, non retenu comme offre.".format(
                ligne["ref_source"], ligne["designation"]))

        # Vendeurs
        nb_partenaires = int((df["vendeur"] != "Baobab Shop").sum())
        j.ajouter(src, "INFO", "{} articles vendus par des partenaires et {} par Baobab Shop : "
                  "tous conservés.".format(nb_partenaires, len(df) - nb_partenaires))
        j.ajouter(src, "INFO", "Titres en anglais et structure différente des autres sources : "
                  "traités au rapprochement.")

        df["prix_paye"] = [
            calculer_prix_paye(p, f, 0.0)
            for p, f in zip(df["prix_affiche"], df["frais_livraison"])
        ]
        j.ajouter(src, "INFO", "Prix payé = amount + delivery_fee.")

        return pd.DataFrame({
            "source": src,
            "ref_source": df["ref_source"],
            "designation_brute": df["designation_brute"],
            "designation": df["designation"],
            "prix_affiche": df["prix_affiche"],
            "frais_livraison": df["frais_livraison"],
            "remise_pct": 0.0,
            "prix_paye": df["prix_paye"],
            "stock": df["stock"],
            "statut_stock": df["statut_stock"],
            "disponible": df["disponible"],
            "retrait_boutique": False,
            "note_clients": pd.to_numeric(df["note_clients"], errors="coerce"),
            "nb_avis": pd.to_numeric(df["nb_avis"], errors="coerce"),
        })[COLONNES]

    # ------------------------------------------------------------------
    # Comptoir Ivoire (Excel)
    # ------------------------------------------------------------------
    def _nettoyer_comptoir(self, brut):
        src = config.COMPTOIR_IVOIRE
        j = self.journal
        renommage = {
            "Code": "ref_source",
            "Article": "designation_brute",
            "Rayon": "rayon",
            "Prix catalogue (FCFA)": "prix_brut",
            "Remise (%)": "remise_pct",
            "Quantité en rayon": "stock",
            "Date de mise à jour": "date_maj",
        }
        brut = brut.rename(columns=lambda c: str(c).strip())
        manquantes = [c for c in renommage if c not in brut.columns]
        if manquantes:
            raise ValueError("Colonnes absentes du fichier Excel : " + ", ".join(manquantes))
        df = brut.rename(columns=renommage).copy()

        j.ajouter(src, "INFO", "Feuille Excel : titre en ligne 1 et ligne vide ignorés, en-têtes "
                  "en ligne 3, données à partir de la ligne 4.")
        avant = len(df)
        df = df.dropna(subset=["ref_source", "designation_brute"], how="all").reset_index(drop=True)
        if len(df) != avant:
            j.ajouter(src, "INFO", "{} lignes vides supprimées.".format(avant - len(df)))
        j.ajouter(src, "INFO", "{} articles lus.".format(len(df)))

        df["designation_brute"] = df["designation_brute"].astype(str)
        df["designation"] = df["designation_brute"].map(lambda s: " ".join(s.split()))

        # Prix catalogue : certains sont saisis comme du texte
        for _, ligne in df.iterrows():
            valeur = ligne["prix_brut"]
            if isinstance(valeur, str):
                converti = en_nombre(valeur)
                precision = ""
                if "\u202f" in valeur or "\u00a0" in valeur:
                    precision = " Le séparateur de milliers est une espace insécable (U+202F ou U+00A0)."
                j.ajouter(src, "CORRECTION", "{} ({}) : prix catalogue saisi comme texte '{}', "
                          "converti en nombre ({}).{}".format(
                              ligne["ref_source"], ligne["designation"],
                              valeur.replace("\u202f", " ").replace("\u00a0", " "),
                              "non convertible" if pd.isna(converti) else formater_fcfa(converti),
                              precision))
        df["prix_affiche"] = df["prix_brut"].map(en_nombre)
        for _, ligne in df[df["prix_affiche"].isna()].iterrows():
            j.ajouter(src, "EXCLUSION", "{} ({}) : prix catalogue absent ou illisible.".format(
                ligne["ref_source"], ligne["designation"]))

        # Remise
        df["remise_pct"] = df["remise_pct"].map(en_nombre)
        sans_remise = df["remise_pct"].isna()
        if sans_remise.any():
            j.ajouter(src, "ALERTE", "{} remises absentes, remplacées par 0 %.".format(int(sans_remise.sum())))
            df.loc[sans_remise, "remise_pct"] = 0.0
        hors_plage = (df["remise_pct"] < 0) | (df["remise_pct"] > 100)
        for _, ligne in df[hors_plage].iterrows():
            j.ajouter(src, "ALERTE", "{} : remise de {} % hors plage, remplacée par 0 %.".format(
                ligne["ref_source"], ligne["remise_pct"]))
        df.loc[hors_plage, "remise_pct"] = 0.0
        remises = df.loc[df["remise_pct"] > 0, "remise_pct"]
        if len(remises):
            j.ajouter(src, "INFO", "{} articles avec une remise (de {:.0f} % à {:.0f} %) : le prix "
                      "payé est le prix catalogue diminué de la remise.".format(
                          len(remises), remises.min(), remises.max()))

        # Stock
        df["stock"] = pd.to_numeric(df["stock"], errors="coerce")
        for _, ligne in df[df["stock"].isna()].iterrows():
            j.ajouter(src, "ALERTE", "{} : quantité inconnue, article non retenu.".format(ligne["ref_source"]))
        df["disponible"] = df["stock"] > 0
        df["statut_stock"] = np.where(df["disponible"], "En stock", "Rupture")
        for _, ligne in df[df["stock"] == 0].iterrows():
            j.ajouter(src, "EXCLUSION", "{} ({}) : quantité en rayon = 0, non retenu comme "
                      "offre.".format(ligne["ref_source"], ligne["designation"]))

        # Dates de mise à jour
        dates = pd.to_datetime(df["date_maj"], errors="coerce")
        if dates.notna().any():
            j.ajouter(src, "INFO", "Dates de mise à jour comprises entre le {} et le {} : prix "
                      "relevés à des dates différentes, conservés tels quels.".format(
                          dates.min().strftime("%d/%m/%Y"), dates.max().strftime("%d/%m/%Y")))

        j.ajouter(src, "INFO", "Boutique physique : retrait sur place, aucun frais de livraison "
                  "ajouté (le coût du déplacement n'est pas compté).")
        j.ajouter(src, "INFO", "Rayons ({}) différents des catégories du catalogue : colonne non "
                  "utilisée.".format(", ".join(sorted(df["rayon"].astype(str).unique()))))

        df["prix_paye"] = [
            calculer_prix_paye(p, 0.0, r) for p, r in zip(df["prix_affiche"], df["remise_pct"])
        ]

        return pd.DataFrame({
            "source": src,
            "ref_source": df["ref_source"].astype(str),
            "designation_brute": df["designation_brute"],
            "designation": df["designation"],
            "prix_affiche": df["prix_affiche"],
            "frais_livraison": 0.0,
            "remise_pct": df["remise_pct"],
            "prix_paye": df["prix_paye"],
            "stock": df["stock"],
            "statut_stock": df["statut_stock"],
            "disponible": df["disponible"],
            "retrait_boutique": True,
            "note_clients": np.nan,
            "nb_avis": np.nan,
        })[COLONNES]

    # ------------------------------------------------------------------
    # Contrôle de cohérence avec l'historique (à appeler après le rapprochement)
    # ------------------------------------------------------------------
    def controler_coherence(self, df, historique):
        """Compare chaque prix affiché au dernier prix connu dans l'historique.

        Un prix plus de 3 fois supérieur (ou inférieur) au dernier prix connu est une valeur
        aberrante : il est remplacé par le prix de l'historique et l'opération est journalisée.
        Les prix manquants ne sont jamais reconstitués : ils restent exclus.
        """
        j = self.journal
        etape = "Cohérence"
        df = df.copy()
        derniers = (
            historique.sort_values("date")
            .groupby(["source", "produit_id"])
            .agg(prix=("prix_fcfa", "last"), date=("date", "last"))
        )
        references = {cle: (ligne["prix"], ligne["date"]) for cle, ligne in derniers.iterrows()}

        nb_verifies = 0
        nb_corriges = 0
        for i in df.index:
            produit = df.at[i, "produit_id"]
            prix = df.at[i, "prix_affiche"]
            if pd.isna(produit) or pd.isna(prix):
                continue
            cle = (df.at[i, "source"], produit)
            if cle not in references:
                continue
            prix_ref, date_ref = references[cle]
            nb_verifies += 1
            rapport = prix / prix_ref
            nom = "{} ({})".format(df.at[i, "ref_source"], df.at[i, "designation"])
            if rapport > config.SEUIL_ABERRANT_HAUT or rapport < config.SEUIL_ABERRANT_BAS:
                df.at[i, "prix_affiche"] = float(prix_ref)
                df.at[i, "prix_paye"] = calculer_prix_paye(
                    prix_ref, df.at[i, "frais_livraison"], df.at[i, "remise_pct"])
                df.at[i, "prix_corrige"] = True
                nb_corriges += 1
                j.ajouter(
                    df.at[i, "source"], "CORRECTION",
                    "{} : prix affiché {} FCFA incohérent avec l'historique (dernier prix connu "
                    "{} FCFA au {}, rapport de {:.1f}). Valeur aberrante, probablement une "
                    "erreur de saisie : remplacée par le prix de l'historique.".format(
                        nom, formater_fcfa(prix), formater_fcfa(prix_ref),
                        date_ref.strftime("%d/%m/%Y"), rapport),
                    etape=etape)
            elif abs(rapport - 1.0) > config.SEUIL_ALERTE_ECART:
                j.ajouter(
                    df.at[i, "source"], "ALERTE",
                    "{} : prix affiché {} FCFA éloigné de {:.0f} % du dernier prix de "
                    "l'historique ({} FCFA), conservé.".format(
                        nom, formater_fcfa(prix), abs(rapport - 1.0) * 100, formater_fcfa(prix_ref)),
                    etape=etape)

        j.ajouter("Global", "INFO",
                  "{} prix comparés au dernier prix de l'historique, {} valeur(s) aberrante(s) "
                  "corrigée(s).".format(nb_verifies, nb_corriges), etape=etape)
        df["exploitable"] = df["disponible"] & df["prix_paye"].notna()
        return df
