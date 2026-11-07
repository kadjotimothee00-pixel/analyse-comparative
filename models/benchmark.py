"""Étape 8 : mesure des temps d'exécution et comparaison de structures de données.

Deux outils :
- Chronometre : mesure la durée de chaque étape du programme.
- Benchmark   : compare plusieurs façons de chercher des prix dans l'historique
                (20 876 lignes) et vérifie qu'elles donnent le même résultat.
"""

import random
import time
from bisect import bisect_left, bisect_right

import pandas as pd

import config


class Chronometre:
    """Enregistre la durée de chaque étape (la dernière mesure d'une étape remplace la précédente)."""

    def __init__(self):
        self.mesures = {}

    def mesurer(self, nom, fonction, *args, **kwargs):
        debut = time.perf_counter()
        resultat = fonction(*args, **kwargs)
        self.mesures[nom] = time.perf_counter() - debut
        return resultat

    def tableau(self):
        lignes = [{"etape": nom, "temps_ms": round(duree * 1000, 2)}
                  for nom, duree in self.mesures.items()]
        return pd.DataFrame(lignes)


class Benchmark:
    """Compare des structures de données pour interroger l'historique des prix."""

    EXPLICATIONS = [
        "Balayage d'une liste : il faut parcourir les lignes une à une, donc O(n) par recherche. "
        "Avec n = 20 876 lignes, le coût croît avec la taille de l'historique.",
        "Dictionnaire {(enseigne, produit, date): prix} : une table de hachage donne l'accès en "
        "O(1) en moyenne. Il coûte O(n) à construire, une seule fois, et un peu de mémoire.",
        "Dictionnaire de listes triées + bisect : pour une période (ex. la semaine du Black "
        "Friday), la recherche dichotomique trouve les bornes en O(log m) (m = jours d'une "
        "série, au plus 365) au lieu de relire tout l'historique.",
        "pandas : le filtre booléen reste O(n) par requête et relit tout l'historique, avec une "
        "surcharge fixe importante (souvent plus lent qu'un balayage Python à cette taille). "
        "Un index trié (MultiIndex) ramène la recherche à O(log n).",
    ]

    def __init__(self, historique, nb_requetes=300, graine=42):
        self.historique = historique
        self.nb_requetes = nb_requetes
        self.graine = graine

    @staticmethod
    def _chrono(fonction):
        debut = time.perf_counter()
        resultat = fonction()
        return resultat, time.perf_counter() - debut

    def comparer_structures(self):
        h = self.historique
        dates = h["date"].dt.strftime("%Y-%m-%d").tolist()
        lignes = list(zip(dates, h["source"].tolist(), h["produit_id"].tolist(),
                          h["prix_fcfa"].tolist()))
        resultats = []
        resultats += self._recherche_ponctuelle(h, lignes)
        resultats += self._recherche_periode(lignes)
        tableau = pd.DataFrame(resultats)

        # Gain par rapport au balayage de la liste, pour une même opération
        gains = []
        for _, ligne in tableau.iterrows():
            reference = tableau[(tableau["operation"] == ligne["operation"])
                                & (tableau["methode"].str.startswith("Balayage"))]
            base = reference["temps_requetes_ms"].iloc[0]
            gains.append(round(base / ligne["temps_requetes_ms"], 1)
                         if ligne["temps_requetes_ms"] > 0 else float("nan"))
        tableau["gain_vs_balayage"] = gains
        # Toutes les méthodes d'une même opération doivent donner la même somme de contrôle
        tableau["resultat_identique"] = (
            tableau.groupby("operation")["controle_somme"].transform("nunique") == 1)
        return tableau

    # ------------------------------------------------------------------
    def _recherche_ponctuelle(self, h, lignes):
        """Chercher le prix d'un (enseigne, produit, date) précis, nb_requetes fois."""
        nom = "Prix d'un jour"
        hasard = random.Random(self.graine)
        echantillon = hasard.sample(lignes, self.nb_requetes)
        requetes = [(d, s, p) for d, s, p, _ in echantillon]
        n = self.nb_requetes
        sorties = []

        # A. Balayage de la liste
        def balayage():
            total = 0
            for d, s, p in requetes:
                for ld, ls, lp, prix in lignes:
                    if ld == d and ls == s and lp == p:
                        total += prix
                        break
            return total
        somme_a, t_a = self._chrono(balayage)
        sorties.append(self._ligne(nom, "Balayage d'une liste", "O(n)", 0.0, t_a, n, somme_a))

        # B. Dictionnaire
        index, t_cons = self._chrono(lambda: {(d, s, p): prix for d, s, p, prix in lignes})
        def par_dictionnaire():
            return sum(index[cle] for cle in requetes)
        somme_b, t_b = self._chrono(par_dictionnaire)
        sorties.append(self._ligne(nom, "Dictionnaire (clé = triplet)", "O(1)", t_cons, t_b, n, somme_b))

        # C. pandas, filtre booléen
        def par_filtre():
            total = 0
            for d, s, p in requetes:
                masque = (h["date"] == pd.Timestamp(d)) & (h["source"] == s) & (h["produit_id"] == p)
                total += int(h.loc[masque, "prix_fcfa"].iloc[0])
            return total
        somme_c, t_c = self._chrono(par_filtre)
        sorties.append(self._ligne(nom, "pandas : filtre booléen", "O(n) vectorisé", 0.0, t_c, n, somme_c))

        # D. pandas, MultiIndex trié
        indexe, t_cons_d = self._chrono(
            lambda: h.set_index(["source", "produit_id", "date"]).sort_index()["prix_fcfa"])
        def par_multiindex():
            total = 0
            for d, s, p in requetes:
                total += int(indexe.loc[(s, p, pd.Timestamp(d))])
            return total
        somme_d, t_d = self._chrono(par_multiindex)
        sorties.append(self._ligne(nom, "pandas : MultiIndex trié", "O(log n)", t_cons_d, t_d, n, somme_d))
        return sorties

    def _recherche_periode(self, lignes):
        """Somme des prix de la semaine du Black Friday pour chacune des séries."""
        nom = "Prix d'une période (76 séries)"
        debut, fin = config.BLACK_FRIDAY_DEBUT, config.BLACK_FRIDAY_FIN
        cles = sorted({(s, p) for _, s, p, _ in lignes})
        n = len(cles)
        sorties = []

        # E. Balayage : une lecture complète de l'historique par série
        def balayage():
            total = 0
            for s, p in cles:
                for ld, ls, lp, prix in lignes:
                    if ls == s and lp == p and debut <= ld <= fin:
                        total += prix
            return total
        somme_e, t_e = self._chrono(balayage)
        sorties.append(self._ligne(nom, "Balayage d'une liste", "O(n) par série", 0.0, t_e, n, somme_e))

        # F. Dictionnaire de listes triées + recherche dichotomique
        def construire():
            series = {}
            for d, s, p, prix in lignes:
                series.setdefault((s, p), []).append((d, prix))
            dates_par_serie, prix_par_serie = {}, {}
            for cle, liste in series.items():
                liste.sort()
                dates_par_serie[cle] = [d for d, _ in liste]
                prix_par_serie[cle] = [prix for _, prix in liste]
            return dates_par_serie, prix_par_serie
        (dates_par_serie, prix_par_serie), t_cons = self._chrono(construire)

        def par_bisect():
            total = 0
            for cle in cles:
                dates = dates_par_serie[cle]
                i = bisect_left(dates, debut)
                j = bisect_right(dates, fin)
                total += sum(prix_par_serie[cle][i:j])
            return total
        # Cette opération dure quelques dizaines de microsecondes : on la répète pour la mesurer.
        repetitions = 200
        debut_mesure = time.perf_counter()
        for _ in range(repetitions):
            somme_f = par_bisect()
        t_f = (time.perf_counter() - debut_mesure) / repetitions
        sorties.append(self._ligne(nom, "Dictionnaire de listes triées + bisect",
                                   "O(log m) par série", t_cons, t_f, n, somme_f))
        return sorties

    @staticmethod
    def _ligne(operation, methode, complexite, construction, requetes, nb, verification):
        return {
            "operation": operation,
            "methode": methode,
            "complexite": complexite,
            "construction_ms": round(construction * 1000, 3),
            "temps_requetes_ms": round(requetes * 1000, 3),
            "nb_requetes": nb,
            "par_requete_us": round(requetes / nb * 1_000_000, 2),
            "controle_somme": int(verification),
        }
