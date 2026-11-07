"""Petites fonctions utilitaires partagées par les modèles."""

import re

import numpy as np
import pandas as pd


def en_nombre(valeur):
    """Convertit un nombre ou un texte du type '102 900 FCFA' en float.

    Renvoie nan si la valeur est vide ou n'est pas un nombre
    (par exemple 'Prix sur demande').
    """
    if valeur is None:
        return np.nan
    if isinstance(valeur, (int, float, np.integer, np.floating)):
        return float(valeur)
    texte = str(valeur).strip()
    texte = re.sub(r"(?i)fcfa|xof", "", texte)
    texte = re.sub(r"[\s\u00a0\u202f]", "", texte)
    texte = texte.replace(",", ".")
    if not re.fullmatch(r"\d+(\.\d+)?", texte):
        return np.nan
    return float(texte)


def calculer_prix_paye(prix_affiche, frais_livraison, remise_pct):
    """Prix réellement payé par le client : (prix - remise) + frais de livraison."""
    if pd.isna(prix_affiche):
        return np.nan
    remise = 0.0 if pd.isna(remise_pct) else float(remise_pct)
    frais = 0.0 if pd.isna(frais_livraison) else float(frais_livraison)
    return float(round(prix_affiche * (100.0 - remise) / 100.0)) + frais


def formater_fcfa(valeur):
    """Écrit un montant avec un espace comme séparateur de milliers."""
    if pd.isna(valeur):
        return "-"
    return "{:,.0f}".format(valeur).replace(",", " ")
