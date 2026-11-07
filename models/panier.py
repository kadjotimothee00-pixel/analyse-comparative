"""Étape 6 : coût du panier de rentrée."""

import numpy as np
import pandas as pd

import config

LIBELLE_MIXTE = "Meilleur prix par article"


class Panier:
    """Calcule le panier dans chaque enseigne, puis article par article au meilleur prix."""

    def __init__(self, composition, catalogue):
        self.composition = dict(composition)
        self.noms = dict(zip(catalogue["produit_id"], catalogue["nom"]))

    def calculer(self, df):
        """Renvoie (détail par article, totaux, économie du panier mixte)."""
        offres = df[df["exploitable"] & df["produit_id"].isin(self.composition)]
        prix = offres.pivot_table(
            index="produit_id", columns="source", values="prix_paye", aggfunc="min"
        ).reindex(index=list(self.composition), columns=config.ENSEIGNES)

        # Détail article par article
        detail = prix.copy()
        detail.insert(0, "nom", [self.noms.get(p, p) for p in detail.index])
        detail.insert(1, "quantite", [self.composition[p] for p in detail.index])
        detail["prix_unitaire_min"] = prix.min(axis=1)
        detail["meilleure_enseigne"] = prix.apply(
            lambda ligne: " / ".join(e for e in config.ENSEIGNES if ligne[e] == ligne.min())
            if ligne.notna().any() else "aucune", axis=1)
        detail["sous_total_meilleur"] = detail["prix_unitaire_min"] * detail["quantite"]
        detail = detail.reset_index()
        detail.columns.name = None

        # Totaux par enseigne
        quantites = pd.Series(self.composition)
        lignes = []
        for enseigne in config.ENSEIGNES:
            manquants = [p for p in prix.index if pd.isna(prix.at[p, enseigne])]
            if manquants:
                total, statut = np.nan, "incomplet"
            else:
                total, statut = float((prix[enseigne] * quantites).sum()), "complet"
            lignes.append({"enseigne": enseigne, "total_fcfa": total, "statut": statut,
                           "articles_indisponibles": ", ".join(manquants)})

        mini = prix.min(axis=1)
        manquants = [p for p in mini.index if pd.isna(mini[p])]
        total_mixte = np.nan if manquants else float((mini * quantites).sum())
        lignes.append({"enseigne": LIBELLE_MIXTE, "total_fcfa": total_mixte,
                       "statut": "incomplet" if manquants else "complet",
                       "articles_indisponibles": ", ".join(manquants)})
        totaux = pd.DataFrame(lignes)

        # Économie du panier mixte par rapport au meilleur panier d'une seule enseigne
        economie = {"economie_fcfa": np.nan, "economie_pct": np.nan, "meilleure_enseigne": None}
        complets = totaux[(totaux["statut"] == "complet") & (totaux["enseigne"] != LIBELLE_MIXTE)]
        if len(complets) and not np.isnan(total_mixte):
            meilleur = complets.sort_values("total_fcfa").iloc[0]
            economie["meilleure_enseigne"] = meilleur["enseigne"]
            economie["economie_fcfa"] = meilleur["total_fcfa"] - total_mixte
            economie["economie_pct"] = round(economie["economie_fcfa"] / meilleur["total_fcfa"] * 100, 2)
        return detail, totaux, economie
