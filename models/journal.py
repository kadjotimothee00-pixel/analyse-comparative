"""Journal des anomalies détectées et des traitements appliqués."""

NIVEAUX = ("INFO", "CORRECTION", "EXCLUSION", "ALERTE")
ETAPES = ("Nettoyage", "Rapprochement", "Cohérence")


class Journal:
    """Liste ordonnée d'entrées : étape, enseigne, niveau, message."""

    def __init__(self):
        self.entrees = []

    def ajouter(self, source, niveau, message, etape="Nettoyage"):
        if niveau not in NIVEAUX:
            raise ValueError("Niveau de journal inconnu : " + str(niveau))
        self.entrees.append(
            {"etape": etape, "source": source, "niveau": niveau, "message": message}
        )

    def __len__(self):
        return len(self.entrees)

    def compter(self):
        """Nombre d'entrées par niveau."""
        resultat = {niveau: 0 for niveau in NIVEAUX}
        for entree in self.entrees:
            resultat[entree["niveau"]] += 1
        return resultat

    def filtrer(self, niveaux):
        return [e for e in self.entrees if e["niveau"] in niveaux]

    @staticmethod
    def formater(entree):
        return "[{:<10}] {} : {}".format(
            entree["niveau"], entree["source"], entree["message"]
        )

    def lignes(self, niveaux=None):
        """Lignes de texte, regroupées par étape (dans l'ordre de traitement)."""
        entrees = self.entrees if niveaux is None else self.filtrer(niveaux)
        lignes = []
        for etape in ETAPES:
            groupe = [e for e in entrees if e["etape"] == etape]
            if not groupe:
                continue
            lignes.append("")
            lignes.append("=== Étape : " + etape + " ===")
            lignes.extend(self.formater(e) for e in groupe)
        return lignes
