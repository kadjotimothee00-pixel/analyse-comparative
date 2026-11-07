"""Étapes 4 et 5 : comparatif des prix et synthèse."""

import pandas as pd

import config


def _enseignes_au_prix(ligne, prix_cible):
    """Noms des enseignes dont le prix est égal à prix_cible (gère les ex aequo)."""
    return " / ".join(e for e in config.ENSEIGNES if ligne[e] == prix_cible)


class Comparateur:
    """Compare le prix payé produit par produit et résume le résultat."""

    def __init__(self, catalogue):
        self.catalogue = catalogue.set_index("produit_id")

    def comparer(self, df):
        """Tableau des produits proposés (disponibles et avec un prix) par au moins 2 enseignes.

        Écart = prix le plus élevé - prix le plus bas, en FCFA et en % du prix le plus bas.
        Un article en rupture ou sans prix n'est jamais retenu (il n'est pas dans les offres).
        """
        offres = df[df["exploitable"] & df["produit_id"].notna()]
        prix = offres.pivot_table(
            index="produit_id", columns="source", values="prix_paye", aggfunc="min"
        ).reindex(columns=config.ENSEIGNES)

        prix["nb_enseignes"] = prix[config.ENSEIGNES].notna().sum(axis=1)
        prix = prix[prix["nb_enseignes"] >= 2].copy()

        grille = prix[config.ENSEIGNES]
        prix["prix_min"] = grille.min(axis=1)
        prix["prix_max"] = grille.max(axis=1)
        prix["enseigne_moins_chere"] = prix.apply(
            lambda ligne: _enseignes_au_prix(ligne, ligne["prix_min"]), axis=1)
        prix["enseigne_plus_chere"] = prix.apply(
            lambda ligne: _enseignes_au_prix(ligne, ligne["prix_max"]), axis=1)
        prix["ecart_fcfa"] = prix["prix_max"] - prix["prix_min"]
        prix["ecart_pct"] = (prix["ecart_fcfa"] / prix["prix_min"] * 100).round(2)

        prix.insert(0, "nom", self.catalogue.loc[prix.index, "nom"])
        prix.insert(1, "categorie", self.catalogue.loc[prix.index, "categorie"])
        resultat = prix.reset_index().sort_values("produit_id").reset_index(drop=True)
        resultat.columns.name = None
        return resultat

    def synthese(self, comparatif):
        """Renvoie (tableau par enseigne, top 3 des écarts).

        - fois_moins_chere : nombre de produits où l'enseigne a le prix le plus bas
          (en cas d'égalité, chaque enseigne concernée compte une fois).
        - ecart_moyen : moyenne, sur les produits où l'enseigne a un prix retenu,
          de l'écart entre son prix et le prix le plus bas.
        """
        lignes = []
        for enseigne in config.ENSEIGNES:
            presents = comparatif[comparatif[enseigne].notna()]
            gagne = presents[presents[enseigne] == presents["prix_min"]]
            ex_aequo = gagne[gagne["enseigne_moins_chere"].str.contains(" / ", regex=False)]
            ecart_fcfa = presents[enseigne] - presents["prix_min"]
            ecart_pct = ecart_fcfa / presents["prix_min"] * 100
            lignes.append({
                "enseigne": enseigne,
                "produits_compares": len(presents),
                "fois_moins_chere": len(gagne),
                "dont_ex_aequo": len(ex_aequo),
                "ecart_moyen_fcfa": round(ecart_fcfa.mean(), 0) if len(presents) else float("nan"),
                "ecart_moyen_pct": round(ecart_pct.mean(), 2) if len(presents) else float("nan"),
            })
        par_enseigne = pd.DataFrame(lignes)

        colonnes = ["produit_id", "nom", "enseigne_moins_chere", "prix_min",
                    "enseigne_plus_chere", "prix_max", "ecart_fcfa", "ecart_pct"]
        top3 = comparatif.sort_values(["ecart_fcfa", "ecart_pct"], ascending=False).head(3)[colonnes]
        return par_enseigne, top3.reset_index(drop=True)
