"""Contrôleur : relie le menu (vue) aux modèles et décide de l'ordre des opérations."""

import config
from models import export
from models.benchmark import Benchmark, Chronometre
from models.chargeur import Chargeur
from models.comparateur import Comparateur
from models.historique import Historique
from models.nettoyeur import Nettoyeur
from models.panier import Panier
from models.rapprocheur import Rapprocheur
from views.console_view import ConsoleView


class AppController:
    def __init__(self):
        self.vue = ConsoleView()
        self.chrono = Chronometre()
        self.donnees = None
        self.catalogue = None
        self.df = None
        self.journal = None
        self.comparatif = None
        self.pret = False

    # ------------------------------------------------------------------
    # Boucle principale
    # ------------------------------------------------------------------
    def run(self):
        actions = {
            "1": self.charger_et_nettoyer,
            "2": self.comparer,
            "3": self.synthese,
            "4": self.panier,
            "5": self.historique,
            "6": self.benchmark,
            "7": self.afficher_journal,
            "8": self.tout_executer,
        }
        self.vue.accueil()
        while True:
            choix = self.vue.menu()
            if choix == "0":
                self.vue.message("Au revoir.")
                break
            action = actions.get(choix)
            if action is None:
                self.vue.erreur("Choix invalide, tapez un chiffre entre 0 et 8.")
                continue
            try:
                action()
            except (FileNotFoundError, ValueError, KeyError) as erreur:
                self.vue.erreur(str(erreur))
            self.vue.attendre()

    def tout_executer(self):
        """Exécute toutes les étapes dans l'ordre et exporte tous les résultats."""
        self.charger_et_nettoyer()
        self.comparer()
        self.synthese()
        self.panier()
        self.historique()
        self.benchmark()
        self.vue.titre("Terminé : tous les résultats sont dans le dossier sorties/")

    def _assurer_donnees(self):
        """Lance le chargement si l'utilisateur demande une analyse avant l'option 1."""
        if not self.pret:
            self.charger_et_nettoyer()

    def _exporter_csv(self, df, nom):
        self.vue.fichier_ecrit(export.chemin_relatif(export.ecrire_csv(df, nom)))

    # ------------------------------------------------------------------
    # Étapes 1 à 3
    # ------------------------------------------------------------------
    def charger_et_nettoyer(self):
        self.vue.titre("1. Chargement, nettoyage et rapprochement")
        self.chrono = Chronometre()
        self.comparatif = None

        self.donnees = self.chrono.mesurer("Chargement des 5 fichiers", Chargeur().charger_tout)
        self.catalogue = self.donnees["catalogue"]
        self.vue.afficher_chargement(self.donnees)

        nettoyeur = Nettoyeur()
        df, journal = self.chrono.mesurer("Nettoyage", nettoyeur.nettoyer, self.donnees)
        df = self.chrono.mesurer(
            "Rapprochement", Rapprocheur(self.catalogue, journal).rapprocher, df)
        df = self.chrono.mesurer(
            "Contrôle de cohérence", nettoyeur.controler_coherence, df, self.donnees["historique"])
        self.df, self.journal = df, journal
        self.pret = True

        chemin_journal = export.chemin_relatif(
            export.ecrire_texte(self._lignes_journal(), "journal_nettoyage.txt"))
        self.vue.afficher_resume_journal(journal, chemin_journal)
        self.vue.afficher_rapprochement(df)
        self.vue.message("")
        self.vue.fichier_ecrit(chemin_journal)
        self._exporter_csv(df, "donnees_propres.csv")

    def _lignes_journal(self):
        compte = self.journal.compter()
        entete = [
            "JOURNAL DE NETTOYAGE - Analyse comparative de marché",
            "{} entrées : {} correction(s), {} exclusion(s), {} alerte(s), {} information(s)".format(
                len(self.journal), compte["CORRECTION"], compte["EXCLUSION"],
                compte["ALERTE"], compte["INFO"]),
            "Niveaux : INFO (observation), CORRECTION (valeur corrigée), "
            "EXCLUSION (article non retenu), ALERTE (anomalie signalée).",
        ]
        return entete + self.journal.lignes()

    def afficher_journal(self):
        self._assurer_donnees()
        self.vue.afficher_journal_complet(self.journal)

    # ------------------------------------------------------------------
    # Étapes 4 et 5
    # ------------------------------------------------------------------
    def _calculer_comparatif(self):
        self._assurer_donnees()
        if self.comparatif is None:
            self.comparatif = self.chrono.mesurer(
                "Comparatif", Comparateur(self.catalogue).comparer, self.df)

    def comparer(self):
        self.vue.titre("2. Comparatif des prix")
        self._calculer_comparatif()
        chemin = export.chemin_relatif(export.ecrire_csv(self.comparatif, "comparatif.csv"))
        self.vue.afficher_comparatif(self.comparatif, chemin)

    def synthese(self):
        self.vue.titre("3. Synthèse")
        self._calculer_comparatif()
        par_enseigne, top3 = self.chrono.mesurer(
            "Synthèse", Comparateur(self.catalogue).synthese, self.comparatif)
        self.vue.afficher_synthese(par_enseigne, top3)
        self.vue.message("")
        self._exporter_csv(par_enseigne, "synthese_enseignes.csv")
        self._exporter_csv(top3, "top3_ecarts.csv")

    # ------------------------------------------------------------------
    # Étape 6
    # ------------------------------------------------------------------
    def panier(self):
        self.vue.titre("4. Panier de rentrée")
        self._assurer_donnees()
        detail, totaux, economie = self.chrono.mesurer(
            "Panier", Panier(config.PANIER_RENTREE, self.catalogue).calculer, self.df)
        self.vue.afficher_panier(detail, totaux, economie)
        self.vue.message("")
        self._exporter_csv(detail, "panier_detail.csv")
        self._exporter_csv(totaux, "panier_totaux.csv")

    # ------------------------------------------------------------------
    # Étape 7
    # ------------------------------------------------------------------
    def historique(self):
        self.vue.titre("5. Historique : quand fallait-il acheter ?")
        self._assurer_donnees()

        def analyser():
            analyse = Historique(self.donnees["historique"])
            resume, detail = analyse.black_friday()
            return resume, detail, analyse.semaines()

        resume, detail, semaines = self.chrono.mesurer("Historique (Black Friday)", analyser)
        self.vue.afficher_historique(resume, detail, semaines)
        self.vue.message("")
        self._exporter_csv(resume, "historique_black_friday_enseignes.csv")
        self._exporter_csv(detail, "historique_black_friday_produits.csv")
        self._exporter_csv(semaines, "historique_semaines.csv")

    # ------------------------------------------------------------------
    # Étape 8
    # ------------------------------------------------------------------
    def benchmark(self):
        self.vue.titre("6. Temps d'exécution et structures de données")
        self._assurer_donnees()
        mesure = Benchmark(self.donnees["historique"])
        structures = mesure.comparer_structures()
        etapes = self.chrono.tableau()
        self.vue.afficher_benchmark(
            etapes, structures, Benchmark.EXPLICATIONS, len(self.donnees["historique"]))
        self.vue.message("")
        self._exporter_csv(etapes, "temps_etapes.csv")
        self._exporter_csv(structures, "benchmark_structures.csv")
