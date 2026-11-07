"""Étape 1 : lecture des fichiers (CSV, JSON, Excel) sans aucune transformation."""

import json
import os

import pandas as pd

import config


class Chargeur:
    """Lit les cinq fichiers et les renvoie tels quels (le nettoyage vient après)."""

    def __init__(self, dossier=config.DOSSIER_DONNEES):
        self.dossier = dossier

    def _chemin(self, nom_fichier):
        chemin = os.path.join(self.dossier, nom_fichier)
        if not os.path.isfile(chemin):
            raise FileNotFoundError("Fichier introuvable : " + chemin)
        return chemin

    def charger_catalogue(self):
        return pd.read_csv(
            self._chemin(config.FICHIER_CATALOGUE), encoding="utf-8-sig", dtype=str
        )

    def charger_marche_lagune(self):
        # Export "Excel français" : séparateur ';', BOM UTF-8 au début du fichier.
        # Tout est lu en texte : les prix contiennent 'FCFA' et des espaces.
        return pd.read_csv(
            self._chemin(config.FICHIER_MARCHE_LAGUNE),
            sep=";",
            encoding="utf-8-sig",
            dtype=str,
            keep_default_na=False,
        )

    def charger_baobab(self):
        """Renvoie (articles, meta) : un DataFrame aplati et les infos de l'en-tête JSON."""
        with open(self._chemin(config.FICHIER_BAOBAB), encoding="utf-8") as fichier:
            contenu = json.load(fichier)
        if "items" not in contenu:
            raise ValueError("Le fichier JSON de Baobab Shop ne contient pas de clé 'items'.")
        articles = pd.json_normalize(contenu["items"])
        meta = {cle: valeur for cle, valeur in contenu.items() if cle != "items"}
        return articles, meta

    def charger_comptoir(self):
        # Titre en ligne 1, ligne vide, en-têtes en ligne 3 : header=2 (numérotation depuis 0).
        # dtype=object pour garder les prix saisis comme du texte (ex. '279 300').
        return pd.read_excel(
            self._chemin(config.FICHIER_COMPTOIR), sheet_name=0, header=2, dtype=object
        )

    def charger_historique(self):
        return pd.read_csv(
            self._chemin(config.FICHIER_HISTORIQUE), parse_dates=["date"]
        )

    def charger_tout(self):
        baobab, meta = self.charger_baobab()
        return {
            "catalogue": self.charger_catalogue(),
            "marche_lagune": self.charger_marche_lagune(),
            "baobab": baobab,
            "baobab_meta": meta,
            "comptoir": self.charger_comptoir(),
            "historique": self.charger_historique(),
        }
