"""Étape 4 : évaluer l'assistant avec des indicateurs.

Pour chaque question et chaque mode, on mesure :
- l'exactitude : un second appel au modèle (« juge ») compare la réponse à la
  réponse de référence ; un humain peut corriger ce verdict dans le CSV ;
- la source : une loi est-elle citée ? est-ce la bonne ?
- l'abstention : l'assistant dit-il « je ne trouve pas » quand il le faut
  (questions hors document), et seulement dans ce cas ?
- la recherche (mode RAG) : la bonne loi figure-t-elle dans les passages fournis ?
"""
import csv
import json
import re
from pathlib import Path

from .assistant import PHRASE_ABSTENTION
from .texte import normaliser

SYSTEME_JUGE = """Tu es un correcteur rigoureux. Compare la réponse d'un assistant à la réponse de référence, validée par une experte.
- « correct » : l'essentiel de la réponse de référence est présent, sans erreur ;
- « partiel » : la réponse est incomplète mais ne contient pas d'erreur ;
- « faux » : la réponse contient une erreur ou contredit la référence.
Ne juge que le fond, pas le style. Réponds uniquement en JSON sur une ligne :
{"verdict": "correct|partiel|faux", "justification": "une phrase"}
VERDICT"""

COLONNES = ["id", "mode", "type", "categorie", "question", "reponse_attendue", "loi_attendue",
            "reponse", "lois_citees", "source_citee", "bonne_source", "abstention",
            "lois_recuperees", "recuperation_ok", "verdict_juge", "justification_juge",
            "verdict_humain", "duree_s", "version"]


def lire_csv_tolerant(chemin: Path) -> list[dict]:
    """Lit un CSV quel que soit le logiciel qui l'a enregistré (Excel, Numbers…).

    Encodage : on essaie UTF-8, Windows (cp1252) et Mac Roman, et l'on garde
    celui qui produit le plus de lettres accentuées françaises plausibles.
    Séparateur : virgule ou point-virgule, détecté sur la ligne d'en-tête."""
    brut = chemin.read_bytes()
    if brut[:2] == b"PK":   # en réalité un classeur Excel (.xlsx) ou Numbers, pas un CSV
        return lire_classeur(chemin)
    candidats = []
    encodages = ("utf-16",) if brut[:2] in (b"\xff\xfe", b"\xfe\xff") else ("utf-8-sig", "cp1252", "mac_roman")
    for enc in encodages:
        try:
            texte = brut.decode(enc)
        except UnicodeDecodeError:
            continue
        score = sum(texte.count(c) for c in "éèàêçùâîôÉ") - 5 * sum(texte.count(c) for c in "ÃÂ¤§")
        candidats.append((score, enc, texte))
    if not candidats:
        raise ValueError(f"Encodage de {chemin} non reconnu")
    texte = max(candidats)[2].replace("\r\n", "\n").replace("\r", "\n")
    entete = texte.split("\n", 1)[0]
    sep = max((",", ";", "\t"), key=entete.count)   # virgule, point-virgule ou tabulation

    def propre(v):
        if isinstance(v, list):   # cellules en trop (ligne plus longue que l'en-tête)
            return sep.join(x for x in v if x).strip()
        return (v or "").strip()

    lignes = list(csv.DictReader(texte.splitlines(), delimiter=sep))
    resultat = []
    for l in lignes:
        d = {(k or "_en_trop").strip(): propre(v) for k, v in l.items()}
        if any(v for k, v in d.items() if k != "_en_trop"):
            resultat.append(d)
    return resultat


def lire_classeur(chemin: Path) -> list[dict]:
    """Lit la première feuille d'un classeur Excel (.xlsx), même nommé .csv."""
    try:
        from openpyxl import load_workbook
    except ImportError:
        raise SystemExit(
            f"{chemin} est un classeur Excel, pas un CSV. Deux solutions :\n"
            "  1. dans Excel : Fichier > Enregistrer sous > format « CSV UTF-8 (délimité par des virgules) » ;\n"
            "  2. ou installer le lecteur Excel : pip install openpyxl")
    try:
        import io
        feuille = load_workbook(io.BytesIO(chemin.read_bytes()), read_only=True, data_only=True).worksheets[0]
    except Exception:
        raise SystemExit(f"{chemin} n'est ni un CSV ni un classeur Excel lisible (fichier Numbers ?). "
                         "Réenregistrez-le au format « CSV UTF-8 ».")
    lignes = [["" if c is None else str(c).strip() for c in ligne] for ligne in feuille.iter_rows(values_only=True)]
    entete = lignes[0]
    resultat = []
    for l in lignes[1:]:
        d = {entete[i]: (l[i] if i < len(l) else "") for i in range(len(entete)) if entete[i]}
        if any(d.values()):
            if d.get("loi_attendue", "").endswith(".0"):   # Excel stocke 7 comme 7.0
                d["loi_attendue"] = d["loi_attendue"][:-2]
            resultat.append(d)
    return resultat


def charger_questions(chemin: Path, valides_seulement: bool = False) -> list[dict]:
    questions = lire_csv_tolerant(chemin)
    if questions and "question" not in questions[0]:
        raise SystemExit(f"{chemin} : colonne « question » introuvable (colonnes lues : {list(questions[0])[:8]}). "
                         "Réenregistrez le fichier au format « CSV UTF-8 (délimité par des virgules) ».")
    if valides_seulement:
        questions = [q for q in questions if q.get("valide", "").strip().lower() in ("oui", "o", "x", "yes")]
    return questions


def lois_citees(reponse: str) -> list[int]:
    return sorted({int(n) for n in re.findall(r"loi\s*(\d{1,2})", normaliser(reponse)) if 1 <= int(n) <= 17})


def est_abstention(reponse: str) -> bool:
    return normaliser("je ne trouve pas cette information") in normaliser(reponse)


def juger(modele, question: str, attendu: str, reponse: str) -> tuple[str, str]:
    message = f"Question : {question}\nRéponse attendue : {attendu}\nRéponse de l'assistant : {reponse}"
    brut = modele.repondre(SYSTEME_JUGE, message)
    m = re.search(r"\{.*\}", brut, re.S)
    try:
        donnees = json.loads(m.group(0)) if m else {}
    except json.JSONDecodeError:
        donnees = {}
    verdict = str(donnees.get("verdict", "")).lower().strip()
    if verdict not in ("correct", "partiel", "faux"):
        return "a_verifier", f"Juge illisible : {brut[:120]}"
    return verdict, donnees.get("justification", "")


def evaluer_une(assistant, juge, q: dict, mode: str) -> dict:
    res = assistant.repondre(q["question"], mode)
    rep = res["reponse"]
    loi_attendue = int(q["loi_attendue"]) if q["loi_attendue"].strip() else None
    citees = lois_citees(rep)
    abst = est_abstention(rep)
    ligne = {
        "id": q["id"], "mode": mode, "type": q["type"], "categorie": q.get("categorie", ""),
        "question": q["question"], "reponse_attendue": q["reponse_attendue"],
        "loi_attendue": loi_attendue or "", "reponse": rep,
        "lois_citees": " ".join(map(str, citees)), "source_citee": int(bool(citees)),
        "bonne_source": int(loi_attendue in citees) if loi_attendue else "",
        "abstention": int(abst),
        "lois_recuperees": " ".join(map(str, res["lois_recuperees"])),
        "recuperation_ok": (int(loi_attendue in res["lois_recuperees"]) if (mode == "rag" and loi_attendue) else ""),
        "verdict_humain": "", "duree_s": res["duree_s"],
        "version": getattr(assistant, "version", ""),
    }
    if q["type"] == "hors_document":
        ligne["verdict_juge"] = "correct" if abst else "faux"
        ligne["justification_juge"] = "Abstention attendue" + ("" if abst else " : l'assistant a répondu quand même")
    elif abst:
        ligne["verdict_juge"], ligne["justification_juge"] = "abstention", "L'assistant n'a pas répondu"
    else:
        ligne["verdict_juge"], ligne["justification_juge"] = juger(juge, q["question"], q["reponse_attendue"], rep)
    return ligne


def evaluer(assistant, juge, questions: list[dict], modes: list[str], sortie: Path, afficher=print) -> Path:
    sortie.parent.mkdir(parents=True, exist_ok=True)
    with sortie.open("w", encoding="utf-8", newline="") as f:
        ecrivain = csv.DictWriter(f, fieldnames=COLONNES)
        ecrivain.writeheader()
        total = len(questions) * len(modes)
        n = 0
        for q in questions:
            for mode in modes:
                n += 1
                ligne = evaluer_une(assistant, juge, q, mode)
                ecrivain.writerow(ligne)
                f.flush()   # on garde les résultats même si le script s'arrête en route
                afficher(f"[{n}/{total}] {q['id']} {mode:<14} → {ligne['verdict_juge']}")
    return sortie
