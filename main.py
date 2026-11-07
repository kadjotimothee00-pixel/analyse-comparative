import argparse
import sys

from controllers.app_controller import AppController


def main():
    parser = argparse.ArgumentParser(description="Analyse comparative de marché (application console)")
    parser.add_argument(
        "--tout", action="store_true",
        help="exécute toutes les étapes sans afficher le menu et exporte les résultats")
    args = parser.parse_args()

    # Évite les erreurs d'affichage des accents sur certains terminaux
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

    controleur = AppController()
    if args.tout:
        controleur.vue.accueil()
        controleur.tout_executer()
    else:
        controleur.run()


if __name__ == "__main__":
    main()
