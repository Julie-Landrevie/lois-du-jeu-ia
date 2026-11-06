"""Point d'entrée en ligne de commande.

Exemples :
  python main.py preparer --source data/lois_du_jeu_2026_27.pdf
  python main.py controler
  python main.py demander "Quelle est la durée d'un match ?"          (version 2 par défaut)
  python main.py demander "Quelle est la durée d'un match ?" --version v1
  python main.py tester-recherche          (rappel de la recherche, sans appel au modèle)
  python main.py evaluer --limite 5
  python main.py evaluer --valides-seulement --version v2 --modes rag
  python main.py rapport
  python main.py comparer                  (sans document / RAG v1 / RAG v2)
"""
import argparse
import sys
from datetime import datetime
from pathlib import Path

from rag.assistant import Assistant
from rag.evaluation import charger_questions, evaluer
from rag.ingestion import charger_extraits, controle_qualite, ingerer
from rag.modele import Modele, charger_env
from rag.rapport import comparer, ecrire_rapport
from rag.recherche import IndexBM25, tester_recherche
from rag.versions import VERSION_PAR_DEFAUT, VERSIONS

EXTRAITS = Path("data/extraits.jsonl")
QUESTIONS = Path("data/questions.csv")
SORTIES = Path("outputs")


def construire_assistant(version: str = VERSION_PAR_DEFAUT) -> Assistant:
    if not EXTRAITS.exists():
        sys.exit("Lancez d'abord : python main.py preparer --source <fichier PDF>")
    cfg = VERSIONS[version]
    index = IndexBM25(charger_extraits(EXTRAITS), exclure_hors_lois=cfg["exclure_hors_lois"])
    return Assistant(Modele(), index, k=cfg["k"], version=version)


def dernier(motifs: list[str]) -> Path | None:
    fichiers = sorted((f for m in motifs for f in SORTIES.glob(m)), key=lambda f: f.stat().st_mtime)
    return fichiers[-1] if fichiers else None


def main() -> None:
    charger_env()
    p = argparse.ArgumentParser(description="Assistant IA sur les Lois du Jeu, avec évaluation")
    sous = p.add_subparsers(dest="commande", required=True)
    pr = sous.add_parser("preparer", help="Découper le PDF officiel en extraits")
    pr.add_argument("--source", type=Path, required=True)
    sous.add_parser("controler", help="Contrôle qualité du découpage par loi")
    de = sous.add_parser("demander", help="Poser une question")
    de.add_argument("question")
    de.add_argument("--mode", choices=["rag", "sans_contexte"], default="rag")
    de.add_argument("--version", choices=list(VERSIONS), default=VERSION_PAR_DEFAUT)
    sous.add_parser("tester-recherche", help="Rappel de la recherche par réglage, sans appel au modèle")
    ev = sous.add_parser("evaluer", help="Lancer l'évaluation sur le jeu de questions")
    ev.add_argument("--limite", type=int, default=None, help="N premières questions seulement (essai)")
    ev.add_argument("--valides-seulement", action="store_true", help="Seulement les questions validées")
    ev.add_argument("--modes", nargs="+", default=["sans_contexte", "rag"])
    ev.add_argument("--version", choices=list(VERSIONS), default=VERSION_PAR_DEFAUT)
    ra = sous.add_parser("rapport", help="Calculer les indicateurs (dernier fichier de résultats par défaut)")
    ra.add_argument("--resultats", type=Path, default=None)
    co = sous.add_parser("comparer", help="Tableau comparatif : sans document, RAG v1, RAG v2")
    co.add_argument("--v1", type=Path, default=None, help="Résultats de la version 1 (dernier fichier par défaut)")
    co.add_argument("--v2", type=Path, default=None, help="Résultats de la version 2 (dernier fichier par défaut)")
    a = p.parse_args()

    if a.commande == "preparer":
        extraits = ingerer(a.source, EXTRAITS)
        print(f"{len(extraits)} extraits enregistrés dans {EXTRAITS}")
        a.commande = "controler"
    if a.commande == "controler":
        lignes, alertes = controle_qualite(charger_extraits(EXTRAITS))
        print("\n".join(lignes))
        print("\n".join(["", "ALERTES :"] + alertes) if alertes else "\nContrôle OK : les 17 lois sont présentes.")
    elif a.commande == "demander":
        assistant = construire_assistant(a.version)
        res = assistant.repondre(a.question, a.mode)
        print(res["reponse"])
        if a.mode == "rag":
            print(f"\n(Version {a.version} · passages utilisés : lois {res['lois_recuperees']} · {res['duree_s']} s)")
    elif a.commande == "tester-recherche":
        if not EXTRAITS.exists():
            sys.exit("Lancez d'abord : python main.py preparer --source <fichier PDF>")
        lignes, rates = tester_recherche(charger_extraits(EXTRAITS), charger_questions(QUESTIONS))
        print("Bonne loi parmi les passages retrouvés (questions dont la réponse est dans le livret) :\n")
        print("\n".join(lignes))
        for nom, cfg in VERSIONS.items():
            manques = rates.get((cfg["exclure_hors_lois"], cfg["k"]), [])
            print(f"\nRatés de la {nom} ({cfg['description']}) : {len(manques)}")
            for qid, attendue, lois in manques:
                print(f"  {qid} : loi {attendue} attendue, passages trouvés dans les lois {lois}")
    elif a.commande == "evaluer":
        assistant = construire_assistant(a.version)
        questions = charger_questions(QUESTIONS, a.valides_seulement)[: a.limite]
        if not questions:
            sys.exit("Aucune question à évaluer : écrivez « oui » dans la colonne « valide » de "
                     "data/questions.csv pour les questions vérifiées, puis enregistrez le fichier.")
        sortie = SORTIES / f"resultats_{a.version}_{datetime.now():%Y%m%d_%H%M}.csv"
        print(f"Modèle : {assistant.modele.fournisseur} / {assistant.modele.nom} · version {a.version} "
              f"({VERSIONS[a.version]['description']}) · {len(questions)} questions × {len(a.modes)} modes")
        evaluer(assistant, assistant.modele, questions, a.modes, sortie)
        print(ecrire_rapport(sortie, SORTIES / "rapport.md", f"{assistant.modele.fournisseur} / {assistant.modele.nom}"))
        print(f"\nRésultats : {sortie} · Rapport : {SORTIES / 'rapport.md'}")
    elif a.commande == "rapport":
        resultats = a.resultats or dernier(["resultats_*.csv"])
        if not resultats:
            sys.exit("Aucun fichier de résultats : lancez d'abord python main.py evaluer")
        m = Modele()
        print(ecrire_rapport(resultats, SORTIES / "rapport.md", f"{m.fournisseur} / {m.nom}"))
    elif a.commande == "comparer":
        # Les résultats de la v1 portent l'ancien nom (resultats_AAAAMMJJ_HHMM.csv) ou resultats_v1_…
        v1 = a.v1 or dernier(["resultats_v1_*.csv", "resultats_2*.csv"])
        v2 = a.v2 or dernier(["resultats_v2_*.csv"])
        if not v1 or not v2:
            sys.exit("Il faut un fichier de résultats v1 et un fichier v2 dans outputs/ (ou les indiquer avec --v1 / --v2).")
        print(comparer([("Sans document", v1, "sans_contexte"), ("RAG v1", v1, "rag"), ("RAG v2", v2, "rag")],
                       SORTIES / "comparaison.md"))
        print(f"\nTableau enregistré dans {SORTIES / 'comparaison.md'}")


if __name__ == "__main__":
    main()
