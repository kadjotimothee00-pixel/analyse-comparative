"""Étape 7 : analyse de l'historique des prix (Black Friday et saisonnalité)."""

import pandas as pd

import config


class Historique:
    """Compare la semaine du Black Friday au prix moyen de l'année, enseigne par enseigne.

    Les prix de l'historique sont les prix affichés : livraison incluse chez Marché Lagune,
    hors livraison chez Baobab Shop, prix catalogue sans remise chez Comptoir Ivoire.
    Chaque enseigne n'est comparée qu'à elle-même, ce qui rend la comparaison cohérente.
    """

    def __init__(self, historique):
        self.h = historique.copy()
        cles = ["source", "produit_id"]
        self.h["moyenne_annee"] = self.h.groupby(cles)["prix_fcfa"].transform("mean")
        self.h["indice"] = self.h["prix_fcfa"] / self.h["moyenne_annee"] * 100

    def black_friday(self):
        """Renvoie (résumé par enseigne, détail par produit)."""
        debut = pd.Timestamp(config.BLACK_FRIDAY_DEBUT)
        fin = pd.Timestamp(config.BLACK_FRIDAY_FIN)
        cles = ["source", "produit_id"]

        moyenne_annee = self.h.groupby(cles)["prix_fcfa"].mean().rename("prix_moyen_annee")
        semaine = self.h[self.h["date"].between(debut, fin)]
        moyenne_bf = semaine.groupby(cles)["prix_fcfa"].mean().rename("prix_moyen_black_friday")

        detail = pd.concat([moyenne_annee, moyenne_bf], axis=1).dropna().reset_index()
        detail["variation_pct"] = (
            detail["prix_moyen_black_friday"] / detail["prix_moyen_annee"] - 1) * 100
        detail["prix_moyen_annee"] = detail["prix_moyen_annee"].round(0)
        detail["prix_moyen_black_friday"] = detail["prix_moyen_black_friday"].round(0)
        detail["variation_pct"] = detail["variation_pct"].round(2)

        lignes = []
        for enseigne in config.ENSEIGNES:
            d = detail[detail["source"] == enseigne]
            variation = d["variation_pct"].mean()
            if variation < -1:
                verdict = "Promotion nette : acheter pendant la semaine du Black Friday"
            elif variation > 1:
                verdict = "Pas de promotion : plus cher que la moyenne annuelle"
            else:
                verdict = "Prix proches de la moyenne annuelle"
            lignes.append({
                "enseigne": enseigne,
                "produits": len(d),
                "jours_releves": int(semaine.loc[semaine["source"] == enseigne, "date"].nunique()),
                "variation_moyenne_pct": round(variation, 2),
                "produits_sous_la_moyenne": int((d["variation_pct"] < 0).sum()),
                "variation_min_pct": d["variation_pct"].min(),
                "variation_max_pct": d["variation_pct"].max(),
                "verdict": verdict,
            })
        return pd.DataFrame(lignes), detail

    def semaines(self):
        """Meilleure et pire semaine complète de l'année pour chaque enseigne.

        Pour chaque produit, le prix est ramené à un indice (100 = moyenne annuelle du produit).
        L'indice d'une enseigne pour une semaine est la moyenne des indices de ses produits.
        Seules les semaines complètes (du lundi au dimanche) sont comparées.
        """
        h = self.h
        h["semaine"] = h["date"] - pd.to_timedelta(h["date"].dt.weekday, unit="D")
        premiere = h["date"].min()
        premier_lundi = premiere + pd.Timedelta(days=(7 - premiere.weekday()) % 7)
        dernier_jour = h["date"].max()
        complete = h[(h["semaine"] >= premier_lundi)
                     & (h["semaine"] + pd.Timedelta(days=6) <= dernier_jour)]
        par_semaine = complete.groupby(["source", "semaine"])["indice"].mean().reset_index()

        debut_bf = pd.Timestamp(config.BLACK_FRIDAY_DEBUT)
        lignes = []
        for enseigne in config.ENSEIGNES:
            s = par_semaine[par_semaine["source"] == enseigne]
            meilleure = s.loc[s["indice"].idxmin()]
            pire = s.loc[s["indice"].idxmax()]
            bf = s[s["semaine"] == debut_bf]
            lignes.append({
                "enseigne": enseigne,
                "meilleure_semaine": meilleure["semaine"],
                "variation_meilleure_pct": round(meilleure["indice"] - 100, 2),
                "pire_semaine": pire["semaine"],
                "variation_pire_pct": round(pire["indice"] - 100, 2),
                "variation_black_friday_pct": round(bf["indice"].iloc[0] - 100, 2) if len(bf) else float("nan"),
            })
        return pd.DataFrame(lignes)
