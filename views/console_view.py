"""Vue : tout ce qui s'affiche dans la console et toutes les saisies de l'utilisateur.

Cette classe ne fait aucun calcul métier et ne lit aucun fichier de données.
"""

import numpy as np
import pandas as pd

LARGEUR = 100


class ConsoleView:
    # ------------------------------------------------------------------
    # Saisies et messages simples
    # ------------------------------------------------------------------
    def accueil(self):
        print("=" * LARGEUR)
        print("ANALYSE COMPARATIVE DE MARCHÉ - Marché Lagune, Baobab Shop, Comptoir Ivoire")
        print("=" * LARGEUR)

    def menu(self):
        print("\n" + "-" * LARGEUR)
        print("MENU")
        print("  1. Charger, nettoyer et rapprocher les données")
        print("  2. Comparatif des prix")
        print("  3. Synthèse")
        print("  4. Panier de rentrée")
        print("  5. Historique (Black Friday)")
        print("  6. Temps d'exécution et structures de données")
        print("  7. Journal de nettoyage complet")
        print("  8. Tout exécuter et exporter")
        print("  0. Quitter")
        return input("Votre choix : ").strip()

    def attendre(self):
        input("\nAppuyez sur Entrée pour revenir au menu...")

    def titre(self, texte):
        print("\n" + "=" * LARGEUR)
        print(texte)
        print("=" * LARGEUR)

    def sous_titre(self, texte):
        print("\n--- " + texte + " ---")

    def message(self, texte):
        print(texte)

    def erreur(self, texte):
        print("\nERREUR : " + texte)

    def fichier_ecrit(self, chemin):
        print("  Fichier écrit : " + chemin)

    # ------------------------------------------------------------------
    # Tableaux
    # ------------------------------------------------------------------
    @staticmethod
    def _formater_valeur(nom, valeur):
        if valeur is None or (not isinstance(valeur, (str, bool)) and pd.isna(valeur)):
            return "-"
        if isinstance(valeur, (bool, np.bool_)):
            return "oui" if valeur else "non"
        if isinstance(valeur, pd.Timestamp):
            return valeur.strftime("%d/%m/%Y")
        if isinstance(valeur, (int, float, np.integer, np.floating)):
            if "variation" in nom:
                return "{:+.1f} %".format(valeur)
            if nom.endswith("_pct"):
                return "{:.1f} %".format(valeur)
            if float(valeur).is_integer():
                return "{:,.0f}".format(valeur).replace(",", " ")
            return "{:.2f}".format(valeur)
        return str(valeur)

    NOMS_AFFICHES = {
        "etape": "Étape",
        "quantite": "Quantité",
        "operation": "Opération",
        "methode": "Méthode",
        "complexite": "Complexité",
        "resultat_identique": "Identique",
        "produits_compares": "Produits comparés",
        "enseigne_moins_chere": "Enseigne la moins chère",
        "enseigne_plus_chere": "Enseigne la plus chère",
        "meilleure_enseigne": "Meilleure enseigne",
        "meilleure_semaine": "Meilleure semaine",
        "variation_meilleure_pct": "Variation meilleure sem.",
        "variation_pire_pct": "Variation pire sem.",
        "variation_black_friday_pct": "Variation Black Friday",
        "produits_sous_la_moyenne": "Produits sous la moyenne",
        "ecart_moyen_fcfa": "Écart moyen (FCFA)",
        "ecart_moyen_pct": "Écart moyen (%)",
        "gain_vs_balayage": "Gain vs balayage",
        "fois_moins_chere": "Fois la moins chère",
        "ecart_fcfa": "Écart (FCFA)",
        "ecart_pct": "Écart (%)",
        "produit_id": "Produit",
        "sous_total_meilleur": "Sous-total meilleur",
        "temps_requetes_ms": "Requêtes (ms)",
        "construction_ms": "Construction (ms)",
        "par_requete_us": "Par requête (us)",
        "nb_requetes": "Nb requêtes",
    }

    @classmethod
    def _nom_colonne(cls, colonne):
        if colonne in cls.NOMS_AFFICHES:
            return cls.NOMS_AFFICHES[colonne]
        nom = colonne
        for suffixe, remplacement in (("_fcfa", " (FCFA)"), ("_pct", " (%)"),
                                      ("_ms", " (ms)"), ("_us", " (us)")):
            if nom.endswith(suffixe):
                nom = nom[:-len(suffixe)] + remplacement
        nom = nom.replace("_", " ")
        return nom[:1].upper() + nom[1:]

    def afficher_table(self, df, titre="", colonnes=None, largeur_max=30):
        """Affiche un DataFrame : texte aligné à gauche, nombres à droite, milliers séparés."""
        if titre:
            self.sous_titre(titre)
        if df is None or len(df) == 0:
            print("(aucune ligne)")
            return
        if colonnes is not None:
            df = df[colonnes]

        en_tetes, colonnes_texte, a_droite = [], [], []
        for colonne in df.columns:
            valeurs = df[colonne].tolist()
            textes = [self._formater_valeur(colonne, v) for v in valeurs]
            textes = [t if len(t) <= largeur_max else t[:largeur_max - 3] + "..." for t in textes]
            numerique = all(
                isinstance(v, (int, float, np.integer, np.floating)) and not isinstance(v, (bool, np.bool_))
                for v in valeurs if not (v is None or (not isinstance(v, str) and pd.isna(v))))
            en_tetes.append(self._nom_colonne(colonne))
            colonnes_texte.append(textes)
            a_droite.append(numerique)

        largeurs = [max(len(en_tetes[i]), max(len(t) for t in colonnes_texte[i]))
                    for i in range(len(en_tetes))]

        def formater_ligne(cellules):
            morceaux = []
            for i, cellule in enumerate(cellules):
                morceaux.append(cellule.rjust(largeurs[i]) if a_droite[i] else cellule.ljust(largeurs[i]))
            return "  ".join(morceaux).rstrip()

        print(formater_ligne(en_tetes))
        print("  ".join("-" * largeur for largeur in largeurs))
        for numero in range(len(df)):
            print(formater_ligne([colonnes_texte[i][numero] for i in range(len(en_tetes))]))

    # ------------------------------------------------------------------
    # Étape 1 : chargement, journal
    # ------------------------------------------------------------------
    def afficher_chargement(self, donnees):
        self.sous_titre("Fichiers lus")
        print("  catalogue_reference.csv : {} produits".format(len(donnees["catalogue"])))
        print("  marche_lagune.csv       : {} lignes".format(len(donnees["marche_lagune"])))
        print("  baobab_shop.json        : {} articles".format(len(donnees["baobab"])))
        print("  comptoir_ivoire.xlsx    : {} articles".format(len(donnees["comptoir"])))
        print("  historique_prix.csv     : {} lignes".format(len(donnees["historique"])))

    def afficher_resume_journal(self, journal, chemin_fichier):
        self.sous_titre("Journal de nettoyage")
        compte = journal.compter()
        print("  {} entrées : {} correction(s), {} exclusion(s), {} alerte(s), {} information(s)".format(
            len(journal), compte["CORRECTION"], compte["EXCLUSION"], compte["ALERTE"], compte["INFO"]))
        for ligne in journal.lignes(niveaux=("CORRECTION", "ALERTE")):
            print(ligne if not ligne.startswith("[") else "  " + ligne)
        print("\n  Le détail complet (informations et exclusions) est dans : " + chemin_fichier)
        print("  Il est aussi affichable avec l'option 7 du menu.")

    def afficher_journal_complet(self, journal):
        self.titre("Journal de nettoyage complet")
        for ligne in journal.lignes():
            print(ligne)

    def afficher_rapprochement(self, df):
        total = len(df)
        rapproches = int(df["produit_id"].notna().sum())
        exploitables = int(df["exploitable"].sum())
        self.sous_titre("Rapprochement avec le catalogue")
        print("  {} articles sur {} associés à un produit_id.".format(rapproches, total))
        print("  {} offres exploitables (disponibles et avec un prix).".format(exploitables))
        resume = df.groupby("source").agg(
            articles=("ref_source", "count"),
            exploitables=("exploitable", "sum"),
        ).reset_index()
        self.afficher_table(resume)

    # ------------------------------------------------------------------
    # Étapes 4 et 5
    # ------------------------------------------------------------------
    def afficher_comparatif(self, comparatif, chemin_fichier):
        self.sous_titre("Comparatif des prix payés (FCFA), produits présents chez au moins 2 enseignes")
        colonnes = ["produit_id", "nom", "Marché Lagune", "Baobab Shop", "Comptoir Ivoire",
                    "enseigne_moins_chere", "ecart_fcfa", "ecart_pct"]
        self.afficher_table(comparatif, colonnes=colonnes, largeur_max=32)
        print("\n  {} produits comparés. Écart = prix le plus haut - prix le plus bas.".format(
            len(comparatif)))
        print("  Ex aequo : les enseignes sont séparées par ' / '. Export complet : " + chemin_fichier)

    def afficher_synthese(self, par_enseigne, top3):
        self.sous_titre("Synthèse par enseigne")
        self.afficher_table(par_enseigne)
        print("\n  fois_moins_chere : produits où l'enseigne a le prix le plus bas (les ex aequo "
              "comptent pour chaque enseigne).")
        print("  ecart_moyen : écart moyen entre le prix de l'enseigne et le prix le plus bas.")
        self.afficher_table(
            top3, "Les 3 produits où il y a le plus à gagner à comparer",
            colonnes=["produit_id", "nom", "enseigne_moins_chere", "prix_min",
                      "enseigne_plus_chere", "prix_max", "ecart_fcfa", "ecart_pct"],
            largeur_max=32)

    # ------------------------------------------------------------------
    # Étape 6 : panier
    # ------------------------------------------------------------------
    def afficher_panier(self, detail, totaux, economie):
        self.sous_titre("Panier de rentrée : détail par article (prix unitaire payé, FCFA)")
        self.afficher_table(
            detail,
            colonnes=["produit_id", "nom", "quantite", "Marché Lagune", "Baobab Shop",
                      "Comptoir Ivoire", "meilleure_enseigne", "sous_total_meilleur"],
            largeur_max=32)
        self.afficher_table(totaux, "Coût total du panier")
        if economie["meilleure_enseigne"] is not None:
            print("\n  Meilleur panier dans une seule enseigne : {}.".format(economie["meilleure_enseigne"]))
            print("  Acheter chaque article là où il est le moins cher fait économiser {} FCFA "
                  "({:.1f} %) par rapport à ce panier.".format(
                      "{:,.0f}".format(economie["economie_fcfa"]).replace(",", " "),
                      economie["economie_pct"]))

    # ------------------------------------------------------------------
    # Étape 7 : historique
    # ------------------------------------------------------------------
    def afficher_historique(self, resume, detail, semaines):
        self.sous_titre("Semaine du Black Friday (24 au 30 novembre 2025) contre prix moyen de l'année")
        self.afficher_table(
            resume,
            colonnes=["enseigne", "produits", "variation_moyenne_pct", "produits_sous_la_moyenne",
                      "variation_min_pct", "variation_max_pct"])
        for _, ligne in resume.iterrows():
            print("  {} : {} ({} jour(s) de relevé dans la semaine).".format(
                ligne["enseigne"], ligne["verdict"], ligne["jours_releves"]))
        self.afficher_table(semaines, "Meilleure et pire semaine de l'année (semaines complètes)")
        print("\n  Variation = écart du prix moyen par rapport à la moyenne annuelle du même "
              "produit, moyenné sur les produits de l'enseigne.")
        print("  Les prix de l'historique sont les prix affichés (Comptoir Ivoire : sans la remise).")

    # ------------------------------------------------------------------
    # Étape 8 : complexité
    # ------------------------------------------------------------------
    def afficher_benchmark(self, etapes, structures, explications, nb_lignes):
        self.sous_titre("Temps d'exécution de chaque étape du programme")
        self.afficher_table(etapes)
        self.sous_titre("Structures de données sur l'historique ({} lignes)".format(nb_lignes))
        self.afficher_table(
            structures,
            colonnes=["operation", "methode", "complexite", "construction_ms", "temps_requetes_ms",
                      "nb_requetes", "par_requete_us", "gain_vs_balayage", "resultat_identique"],
            largeur_max=40)
        print("\n  gain_vs_balayage : nombre de fois plus rapide que le balayage de la liste "
              "(valeur inférieure à 1 : plus lent).")
        print("  resultat_identique : toutes les méthodes d'une opération donnent la même somme "
              "de contrôle.")
        self.sous_titre("Choix de structures de données")
        for texte in explications:
            print("  - " + texte)
