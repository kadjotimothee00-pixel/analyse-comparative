# Analyse comparative de marché

Application console en Python (architecture MVC) qui compare les prix de trois enseignes d'Abidjan : Marché Lagune (site marchand), Baobab Shop (application mobile) et Comptoir Ivoire (boutique d'Adjamé).

Projet réalisé pour le TP de Data Analysis avec Python (L2 Computer Science, séance 3).

## 1. Objectif

Aider un client à décider où acheter son matériel électronique et électroménager. Les trois enseignes n'exposent pas leurs données de la même façon (CSV, JSON, Excel), n'écrivent pas les noms de produits pareil et ne calculent pas le prix payé de la même façon. Le programme :

1. charge les cinq fichiers fournis ;
2. nettoie les données et tient un journal de chaque anomalie ;
3. rapproche chaque article du catalogue commun (P01 à P30) ;
4. compare les prix réellement payés, produit par produit ;
5. produit une synthèse par enseigne ;
6. calcule le coût du panier de rentrée ;
7. analyse l'historique des prix (semaine du Black Friday) ;
8. mesure les temps d'exécution et justifie les structures de données.

## 2. Installation et lancement (VS Code)

Prérequis : Python 3.9 ou plus récent.

1. Ouvrir le dossier `analyse_comparative` dans VS Code (Fichier, Ouvrir le dossier).
2. Ouvrir un terminal (Terminal, Nouveau terminal) et créer un environnement virtuel :

```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Sous Linux ou macOS, l'activation est `source venv/bin/activate`.

3. Lancer l'application :

```
python main.py
```

Pour exécuter toutes les étapes d'un coup, sans menu, et régénérer tous les fichiers de `sorties/` :

```
python main.py --tout
```

Le dossier `sorties/` livré contient déjà les résultats d'une exécution complète. Ils sont réécrits à chaque lancement.

## 3. Menu de l'application

| Choix | Action | Fichiers produits |
|---|---|---|
| 1 | Charger, nettoyer et rapprocher les données | `journal_nettoyage.txt`, `donnees_propres.csv` |
| 2 | Comparatif des prix | `comparatif.csv` |
| 3 | Synthèse par enseigne et top 3 des écarts | `synthese_enseignes.csv`, `top3_ecarts.csv` |
| 4 | Panier de rentrée | `panier_detail.csv`, `panier_totaux.csv` |
| 5 | Historique (Black Friday) | `historique_black_friday_enseignes.csv`, `historique_black_friday_produits.csv`, `historique_semaines.csv` |
| 6 | Temps d'exécution et structures de données | `temps_etapes.csv`, `benchmark_structures.csv` |
| 7 | Afficher le journal de nettoyage complet | aucun |
| 8 | Tout exécuter et exporter | tous |
| 0 | Quitter | aucun |

Si une analyse (2 à 7) est demandée avant l'option 1, le chargement est lancé automatiquement.

## 4. Architecture MVC

```
analyse_comparative/
|-- main.py                     point d'entrée (menu ou option --tout)
|-- config.py                   chemins, noms des enseignes, panier, seuils
|-- requirements.txt            pandas, openpyxl
|-- README.md
|-- donnees/                    fichiers fournis (jamais modifiés)
|-- sorties/                    fichiers produits par le programme
|-- models/                     données et logique métier
|   |-- chargeur.py             étape 1 : lecture CSV, JSON, Excel
|   |-- nettoyeur.py            étape 2 : nettoyage, journal, contrôle de cohérence
|   |-- rapprocheur.py          étape 3 : association article -> produit_id
|   |-- comparateur.py          étapes 4 et 5 : comparatif et synthèse
|   |-- panier.py               étape 6 : panier de rentrée
|   |-- historique.py           étape 7 : Black Friday et saisonnalité
|   |-- benchmark.py            étape 8 : chronomètre et comparaison de structures
|   |-- journal.py              classe Journal (anomalies et traitements)
|   |-- export.py               écriture des CSV et du journal dans sorties/
|   `-- outils.py               conversions de nombres et prix payé
|-- views/
|   `-- console_view.py         affichage console et saisies
`-- controllers/
    `-- app_controller.py       relie le menu, les modèles et les exports
```

| Couche | Rôle | Interdit |
|---|---|---|
| Modèles | lire, nettoyer, calculer, retourner des DataFrames | `print()` et `input()` |
| Vue | afficher les menus et les tableaux, lire les choix | calculs, lecture des données |
| Contrôleur | appeler les bons modèles dans le bon ordre, déclencher les exports | logique de calcul |

Le dossier `sorties/` n'appartient pas au MVC : c'est simplement l'endroit où le programme écrit ses résultats, pour ne jamais mélanger les données d'entrée et les fichiers produits.

## 5. Les données

| Fichier | Contenu | Particularités |
|---|---|---|
| `catalogue_reference.csv` | 30 produits (P01 à P30) | référence commune |
| `marche_lagune.csv` | 30 lignes | séparateur `;`, BOM UTF-8, prix en texte, virgule décimale, livraison incluse |
| `baobab_shop.json` | 26 articles | structure imbriquée (`pricing`, `rating`), frais de livraison à part |
| `comptoir_ivoire.xlsx` | 22 articles | titre en ligne 1, en-têtes en ligne 3, remise en %, retrait en boutique |
| `historique_prix.csv` | 20 876 lignes, du 01/11/2025 au 31/10/2026 | prix quotidien (Comptoir Ivoire : hebdomadaire) |

## 6. Traitement détaillé

### Étape 1 : chargement

Chaque source a sa propre méthode de lecture :

- Marché Lagune : `read_csv` avec `sep=";"` et `encoding="utf-8-sig"` (retire le BOM), tout lu en texte pour traiter les prix soi-même.
- Baobab Shop : `json.load` puis `pd.json_normalize` pour aplatir `pricing.amount`, `pricing.delivery_fee`, `rating.average`.
- Comptoir Ivoire : `read_excel` avec `header=2` (en-têtes en ligne 3) et `dtype=object` pour conserver les prix saisis comme du texte.
- Historique : `read_csv` avec dates converties.

### Étape 2 : nettoyage et journal

Toutes les sources sont ramenées à une structure commune (enseigne, référence, désignation, prix affiché, frais de livraison, remise, prix payé, stock, disponibilité, retrait en boutique, note, nombre d'avis). Chaque anomalie est consignée dans `sorties/journal_nettoyage.txt` avec l'un de ces niveaux : INFO, CORRECTION, EXCLUSION, ALERTE.

Anomalies repérées et traitement :

| Source | Anomalie | Traitement |
|---|---|---|
| Marché Lagune | 2 lignes en double (ML-1000, ML-1147) | supprimées |
| Marché Lagune | désignation avec espaces superflus et en minuscules (ML-1105) | espaces supprimés, casse ignorée au rapprochement |
| Marché Lagune | 26 prix avec une espace insécable fine (U+202F) comme séparateur de milliers | retirée avant la conversion en nombre |
| Marché Lagune | prix "Prix sur demande" (ML-1119) | article exclu ; l'ancien prix est un prix barré, pas un prix de vente |
| Marché Lagune | prix absent (ML-1168) | article exclu |
| Marché Lagune | 779 000 FCFA pour le Tecno Spark 20 (ML-1021) | valeur aberrante, corrigée (voir ci-dessous) |
| Marché Lagune | 6 articles en rupture | exclus des comparaisons |
| Marché Lagune | 3 articles en stock limité | conservés |
| Baobab Shop | montant `null` (BB27999, fer à repasser) | article exclu |
| Baobab Shop | 3 articles à stock 0 (BB03433, BB16464, BB30124) | exclus des comparaisons |
| Baobab Shop | titres en anglais, 8 vendeurs partenaires | gérés au rapprochement, articles conservés |
| Comptoir Ivoire | prix saisi comme texte "279 300" (CI216) | converti en nombre |
| Comptoir Ivoire | 2 articles à quantité 0 (CI214, CI217) | exclus des comparaisons |
| Comptoir Ivoire | nom avec faute de frappe "Samsun" (CI200) | reconnu au rapprochement |
| Comptoir Ivoire | 9 remises de 5 % à 15 % | appliquées au prix payé |

Au total : 76 articles dans la structure commune, dont 63 exploitables (disponibles et avec un prix). Le journal contient 45 entrées : 3 corrections, 16 exclusions, 1 alerte et 25 informations.

Prix réellement payé, calculé de façon homogène :

| Enseigne | Prix payé |
|---|---|
| Marché Lagune | prix affiché (la livraison est déjà incluse) |
| Baobab Shop | `amount` + `delivery_fee` |
| Comptoir Ivoire | prix catalogue x (1 - remise) |

Traitement de la valeur aberrante du Tecno Spark 20 chez Marché Lagune : après le rapprochement, chaque prix affiché est comparé au dernier prix connu de l'historique pour la même enseigne et le même produit. Un prix plus de 3 fois supérieur ou inférieur est jugé aberrant. Ici, 779 000 FCFA contre 77 900 FCFA dans l'historique au 31/10/2026 (rapport de 10), et l'ancien prix affiché (88 700 FCFA) est inférieur au prix actuel, ce qui est incohérent. Il s'agit très probablement d'un chiffre en trop à la saisie. Le prix est remplacé par 77 900 FCFA et l'opération est journalisée. Les prix manquants, eux, ne sont jamais reconstitués : l'article reste exclu.

### Étape 3 : rapprochement avec le catalogue

Chaque désignation est normalisée : minuscules, accents retirés, unités unifiées (`128GB` et `128 Go` donnent `128 go`, `1.5HP` donne `1.5 cv`, `24"` donne `24 pouces`), synonymes traduits (`frigo`, `fridge` donnent `refrigerateur` ; `monitor` donne `ecran` ; `kettle` donne `bouilloire`), mots génériques ignorés.

Pour chaque produit du catalogue, un score est calculé :

```
score = nombre de mots communs - nombre de mots chiffrés qui contredisent le catalogue
```

Un mot chiffré contient un chiffre (`128`, `a15`, `40i`, `1.5`). S'il figure dans l'article mais pas dans le produit du catalogue, c'est une contradiction : un Galaxy A25 ne doit pas être associé à un Galaxy A15. Le produit au meilleur score est retenu si ce score atteint 2 et si le résultat n'est pas ex aequo avec un autre produit. Une tolérance aux fautes de frappe (module `difflib`, similarité de 0,85) reconnaît "Samsun" comme "Samsung".

Résultat : 76 articles sur 76 rapprochés, sans ambiguïté. Couverture du catalogue : Marché Lagune 28 produits sur 30 (absents : P18, P29), Baobab Shop 26 (absents : P08, P13, P21, P25), Comptoir Ivoire 22 (absents : P03, P05, P07, P10, P17, P18, P19, P30). Ce résultat est cohérent avec les produits présents dans `historique_prix.csv`.

### Étape 4 : comparatif

`comparatif.csv` contient les 23 produits proposés (en stock et avec un prix) par au moins deux enseignes : prix payé dans chaque enseigne, enseigne la moins chère, enseigne la plus chère, écart en FCFA et en pourcentage.

- Écart en FCFA = prix le plus élevé - prix le plus bas.
- Écart en % = écart en FCFA / prix le plus bas.
- Un article en rupture ou sans prix n'entre jamais dans la comparaison, donc ne peut pas être désigné "moins cher".
- En cas d'égalité du prix le plus bas, les enseignes concernées sont séparées par " / " (cas du P16, souris Logitech, et du P27, fer à repasser Philips : Marché Lagune et Comptoir Ivoire au même prix).

### Étape 5 : synthèse

| Enseigne | Produits comparés | Fois la moins chère | dont ex aequo | Écart moyen au prix le plus bas |
|---|---|---|---|---|
| Marché Lagune | 19 | 6 | 2 | 7 771 FCFA (3,8 %) |
| Baobab Shop | 20 | 9 | 0 | 2 702 FCFA (4,7 %) |
| Comptoir Ivoire | 18 | 10 | 2 | 6 667 FCFA (2,8 %) |

Les ex aequo comptent pour chaque enseigne concernée. Comptoir Ivoire est le moins cher le plus souvent, mais Baobab Shop a le plus petit écart moyen en FCFA : quand Baobab Shop n'est pas le moins cher, il en est proche, alors que Comptoir Ivoire est nettement plus cher sur plusieurs gros articles.

Les trois produits où il y a le plus à gagner à comparer (écart en FCFA) :

| Produit | Moins cher | Plus cher | Écart |
|---|---|---|---|
| HP 250 G9 Core i5 | Baobab Shop, 354 200 FCFA | Comptoir Ivoire, 407 000 FCFA | 52 800 FCFA (14,9 %) |
| Apple iPhone 13 128 Go | Baobab Shop, 417 200 FCFA | Comptoir Ivoire, 443 700 FCFA | 26 500 FCFA (6,3 %) |
| Climatiseur LG 1 CV | Baobab Shop, 253 300 FCFA | Comptoir Ivoire, 279 300 FCFA | 26 000 FCFA (10,3 %) |

### Étape 6 : panier de rentrée

Composition : 1 Tecno Spark 20, 1 Lenovo IdeaPad 3, 2 clés USB SanDisk 64 Go, 1 disque dur Seagate 1 To, 1 micro-ondes Samsung 23 L.

| Option | Total |
|---|---|
| Tout chez Marché Lagune | 504 300 FCFA |
| Tout chez Baobab Shop | 491 500 FCFA |
| Tout chez Comptoir Ivoire | 484 075 FCFA |
| Chaque article au meilleur prix | 477 575 FCFA |

Le panier mixte (Spark 20 et micro-ondes chez Baobab Shop, IdeaPad chez Comptoir Ivoire, clés USB et disque dur chez Marché Lagune) fait économiser 6 500 FCFA (1,3 %) par rapport au meilleur panier d'une seule enseigne (Comptoir Ivoire). Si un article manque dans une enseigne, son total est marqué "incomplet" au lieu d'être faussé.

### Étape 7 : historique et Black Friday

Pour chaque produit, le prix moyen de la semaine du 24 au 30 novembre 2025 est comparé à son prix moyen sur l'année, puis la variation est moyennée par enseigne.

| Enseigne | Variation moyenne | Produits sous la moyenne annuelle |
|---|---|---|
| Marché Lagune | -11,3 % | 28 sur 28 |
| Baobab Shop | -11,7 % | 26 sur 26 |
| Comptoir Ivoire | +3,8 % | 0 sur 22 |

Marché Lagune et Baobab Shop ont une vraie promotion Black Friday d'environ 11 % : c'est leur meilleure semaine de l'année. Comptoir Ivoire n'en a pas (ses prix de la semaine sont même au-dessus de sa moyenne), et sa meilleure semaine complète est mi-septembre 2026 (-5,2 %). Sur l'ensemble de l'année, les prix baissent progressivement : la semaine la plus chère est la première (début novembre 2025, entre +4 % et +5 % par rapport à la moyenne).

Précautions de lecture : les prix de l'historique sont les prix affichés (livraison incluse chez Marché Lagune, hors livraison chez Baobab Shop, prix catalogue sans remise chez Comptoir Ivoire). Chaque enseigne n'est donc comparée qu'à elle-même, jamais aux autres. Comptoir Ivoire n'a qu'un relevé par semaine : un seul jour (24/11/2025) tombe dans la semaine du Black Friday.

### Étape 8 : complexité et structures de données

Le programme chronomètre chaque étape (`time.perf_counter`). Ordres de grandeur sur l'exécution complète (ils varient selon la machine) :

| Étape | Temps |
|---|---|
| Chargement des 5 fichiers | environ 90 ms |
| Nettoyage | environ 20 ms |
| Rapprochement | environ 37 ms |
| Contrôle de cohérence | environ 13 ms |
| Comparatif | environ 8 ms |
| Synthèse | environ 4 ms |
| Panier | environ 6 ms |
| Historique | environ 22 ms |

Le programme compare aussi plusieurs façons d'interroger les 20 876 lignes de l'historique, avec 300 recherches de prix à une date précise et la recherche d'une période pour les 76 séries. Toutes les méthodes sont vérifiées : elles donnent la même somme de contrôle.

| Opération | Méthode | Complexité | Temps mesuré (ordre de grandeur) |
|---|---|---|---|
| Prix d'un jour | Balayage d'une liste | O(n) par requête | 51 ms pour 300 requêtes |
| Prix d'un jour | Dictionnaire `{(enseigne, produit, date): prix}` | O(1) par requête | 0,08 ms pour 300 requêtes (construction : 3 ms) |
| Prix d'un jour | pandas, filtre booléen | O(n) par requête | 530 ms pour 300 requêtes |
| Prix d'un jour | pandas, MultiIndex trié | O(log n) par requête | 5 ms pour 300 requêtes |
| Prix d'une période | Balayage d'une liste | O(n) par série | 31 ms pour 76 séries |
| Prix d'une période | Dictionnaire de listes triées + `bisect` | O(log m) par série | 0,03 ms pour 76 séries |

Choix retenus et justification :

- Le dictionnaire ramène une recherche ponctuelle à un accès direct. Il coûte une construction en O(n), payée une seule fois, et un peu de mémoire.
- Pour une période, une liste triée par date et la recherche dichotomique (`bisect`) trouvent les bornes en O(log m), avec m au plus égal à 365 jours par série, au lieu de relire tout l'historique.
- Le filtre booléen de pandas relit tout l'historique à chaque requête et ajoute une surcharge fixe : à cette taille, il est plus lent qu'un simple balayage Python. pandas reste le bon outil pour les agrégations (moyennes, regroupements), où l'on traite toutes les lignes en une passe.
- Le rapprochement compare chaque article aux 30 produits du catalogue : 76 x 30 comparaisons, négligeable. Si le catalogue devenait très grand, il faudrait indexer les produits par marque ou par mot-clé avant de calculer les scores.

## 7. Fichiers produits dans `sorties/`

| Fichier | Contenu |
|---|---|
| `journal_nettoyage.txt` | toutes les anomalies et tous les traitements, groupés par étape |
| `donnees_propres.csv` | les 76 articles dans la structure commune, avec `produit_id`, prix payé, score de rapprochement |
| `comparatif.csv` | le comparatif des 23 produits |
| `synthese_enseignes.csv` | victoires, ex aequo et écarts moyens par enseigne |
| `top3_ecarts.csv` | les 3 produits où comparer rapporte le plus |
| `panier_detail.csv` | prix de chaque article du panier dans chaque enseigne |
| `panier_totaux.csv` | total du panier par enseigne et panier mixte |
| `historique_black_friday_enseignes.csv` | variation du Black Friday par enseigne |
| `historique_black_friday_produits.csv` | variation du Black Friday produit par produit |
| `historique_semaines.csv` | meilleure et pire semaine de l'année par enseigne |
| `temps_etapes.csv` | durée de chaque étape |
| `benchmark_structures.csv` | comparaison des structures de données |

Les CSV utilisent le séparateur `;`, la virgule décimale et l'encodage UTF-8 avec BOM : ils s'ouvrent directement dans Excel en version française.

## 8. Hypothèses et limites

- Le prix payé de Comptoir Ivoire est un prix de retrait en boutique : le coût du déplacement jusqu'à Adjamé n'est pas compté.
- Les prix du fichier Comptoir Ivoire ont été relevés à des dates différentes (du 03/10/2026 au 31/10/2026) : ils sont conservés tels quels.
- La correction du prix aberrant du Spark 20 s'appuie sur l'historique du 31/10/2026, la même date que les fichiers. C'est une hypothèse raisonnable, documentée dans le journal, mais elle reste une hypothèse. Sans cette correction, le panier de Marché Lagune serait gonflé de 701 100 FCFA, ou incomplet si l'article était simplement exclu.
- Le seuil d'aberration (rapport de 3) et le seuil d'alerte (écart de 25 %) sont modifiables dans `config.py`, comme le panier et les dates du Black Friday.
- Les écarts moyens de la synthèse portent uniquement sur les produits retenus pour chaque enseigne, qui n'ont pas tous la même couverture.
- Les temps d'exécution dépendent de la machine : seuls les ordres de grandeur et les rapports entre méthodes sont significatifs.
