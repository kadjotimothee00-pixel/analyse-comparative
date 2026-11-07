"""Constantes et chemins du projet."""

import os

# Chemins (calculés à partir de l'emplacement de ce fichier, donc indépendants du dossier courant)
RACINE = os.path.dirname(os.path.abspath(__file__))
DOSSIER_DONNEES = os.path.join(RACINE, "donnees")
DOSSIER_SORTIES = os.path.join(RACINE, "sorties")

# Fichiers d'entrée
FICHIER_CATALOGUE = "catalogue_reference.csv"
FICHIER_MARCHE_LAGUNE = "marche_lagune.csv"
FICHIER_BAOBAB = "baobab_shop.json"
FICHIER_COMPTOIR = "comptoir_ivoire.xlsx"
FICHIER_HISTORIQUE = "historique_prix.csv"

# Noms des enseignes (identiques à ceux de historique_prix.csv)
MARCHE_LAGUNE = "Marché Lagune"
BAOBAB_SHOP = "Baobab Shop"
COMPTOIR_IVOIRE = "Comptoir Ivoire"
ENSEIGNES = [MARCHE_LAGUNE, BAOBAB_SHOP, COMPTOIR_IVOIRE]

# Panier de rentrée : produit_id -> quantité
PANIER_RENTREE = {"P04": 1, "P12": 1, "P14": 2, "P15": 1, "P28": 1}

# Semaine du Black Friday 2025 (bornes incluses)
BLACK_FRIDAY_DEBUT = "2025-11-24"
BLACK_FRIDAY_FIN = "2025-11-30"

# Contrôle de cohérence avec l'historique
# Un prix est jugé aberrant s'il est plus de 3 fois supérieur ou inférieur au dernier prix connu.
SEUIL_ABERRANT_HAUT = 3.0
SEUIL_ABERRANT_BAS = 1.0 / 3.0
# Un écart de plus de 25 % (sans être aberrant) est simplement signalé.
SEUIL_ALERTE_ECART = 0.25

# Rapprochement : score minimal pour accepter une correspondance
SEUIL_SCORE_RAPPROCHEMENT = 2
# Similarité minimale pour tolérer une faute de frappe dans un mot (difflib)
SEUIL_SIMILARITE_MOT = 0.85

# Format des CSV exportés (lisibles directement par Excel en version française)
SEPARATEUR_CSV = ";"
DECIMALE_CSV = ","
ENCODAGE_CSV = "utf-8-sig"
