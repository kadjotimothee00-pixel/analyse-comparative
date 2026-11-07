"""Écriture des fichiers de résultats dans le dossier sorties/."""

import os

import config


def _chemin(nom_fichier):
    os.makedirs(config.DOSSIER_SORTIES, exist_ok=True)
    return os.path.join(config.DOSSIER_SORTIES, nom_fichier)


def _entiers_propres(df):
    """Les montants stockés en float (104000.0) sont écrits comme des entiers (104000)."""
    df = df.copy()
    for colonne in df.columns:
        if colonne == "note_clients" or str(df[colonne].dtype) not in ("float64", "float32"):
            continue
        valeurs = df[colonne].dropna()
        if len(valeurs) and all(float(v).is_integer() for v in valeurs):
            df[colonne] = df[colonne].astype("Int64")
    return df


def ecrire_csv(df, nom_fichier):
    """Écrit un DataFrame en CSV (séparateur ';', virgule décimale, UTF-8 avec BOM)."""
    chemin = _chemin(nom_fichier)
    df = _entiers_propres(df)
    df.to_csv(
        chemin,
        index=False,
        sep=config.SEPARATEUR_CSV,
        decimal=config.DECIMALE_CSV,
        encoding=config.ENCODAGE_CSV,
    )
    return chemin


def ecrire_texte(lignes, nom_fichier):
    """Écrit une liste de lignes dans un fichier texte UTF-8."""
    chemin = _chemin(nom_fichier)
    with open(chemin, "w", encoding="utf-8") as fichier:
        fichier.write("\n".join(lignes) + "\n")
    return chemin


def chemin_relatif(chemin):
    """Chemin affichable, relatif à la racine du projet."""
    return os.path.relpath(chemin, config.RACINE)
