"""Étape 1 : préparer les données.

Lit le PDF officiel des Lois du Jeu (ou un fichier texte), repère le début de
chacune des 17 lois, puis découpe le texte en extraits (« chunks ») d'environ
180 mots qui se chevauchent légèrement. Chaque extrait garde son numéro de loi
et sa page : c'est ce qui permettra à l'assistant de citer ses sources.
"""
import json
import re
from collections import Counter
from pathlib import Path

from .texte import normaliser

TITRES_LOIS = {
    1: "le terrain",
    2: "le ballon",
    3: "les joueurs",
    4: "l'equipement des joueurs",
    5: "l'arbitre",
    6: "les autres arbitres",
    7: "la duree du match",
    8: "le coup d'envoi",
    9: "ballon en jeu et hors du jeu",
    10: "issue d'un match",
    11: "le hors-jeu",
    12: "fautes et incorrections",
    13: "coups francs",
    14: "le penalty",
    15: "la rentree de touche",
    16: "le coup de pied de but",
    17: "le coup de pied de coin",
}
# Autres formulations possibles selon l'édition ou la traduction
VARIANTES_TITRES = {
    4: ["equipement des joueurs", "equipement"],
    8: ["debut et reprise du jeu", "le debut et la reprise", "coup d'envoi et reprise"],
    9: ["le ballon en jeu", "ballon en jeu"],
    10: ["determiner l'issue", "issue du match", "resultat d'un match"],
    12: ["fautes et comportement antisportif", "fautes"],
    13: ["coup franc"],
    17: ["le corner", "corner"],
}


def sans_article(texte: str) -> str:
    return re.sub(r"^(le |la |les |l')", "", texte.strip())


NOMS_LOIS = {
    1: "Le terrain", 2: "Le ballon", 3: "Les joueurs", 4: "L'équipement des joueurs",
    5: "L'arbitre", 6: "Les autres arbitres", 7: "La durée du match",
    8: "Le coup d'envoi et la reprise du jeu", 9: "Ballon en jeu et hors du jeu",
    10: "Issue d'un match", 11: "Le hors-jeu", 12: "Fautes et incorrections",
    13: "Coups francs", 14: "Le penalty", 15: "La rentrée de touche",
    16: "Le coup de pied de but", 17: "Le coup de pied de coin",
}
# Sections qui suivent la Loi 17 dans le livret (modifications, directives, glossaire)
FIN_DES_LOIS = re.compile(r"^(modifications des lois|directives pratiques|glossaire|termes de football)")
ENTETE = re.compile(r"^(?:loi\s*)?(\d{1,2})\s*[-.:|]?\s*(.+)$")

TAILLE_EXTRAIT = 180   # mots
CHEVAUCHEMENT = 40     # mots repris de l'extrait précédent


def lire_pages(chemin: Path) -> list[str]:
    """Renvoie le texte page par page (PDF) ou un texte unique (.txt)."""
    if chemin.suffix.lower() == ".pdf":
        from pypdf import PdfReader
        lecteur = PdfReader(str(chemin))
        return [(p.extract_text() or "") for p in lecteur.pages]
    return chemin.read_text(encoding="utf-8").split("\f")


def detecter_entete(ligne: str, loi_courante: int) -> int | None:
    """Renvoie le numéro de loi si la ligne est le titre de la loi suivante.

    On n'accepte que la loi suivante (ou la Loi 1, pour repartir de zéro après
    le sommaire) : cela évite de confondre un paragraphe numéroté « 2. ... »
    avec un changement de loi, et ignore les en-têtes répétés en haut de page.
    """
    norm = normaliser(ligne).strip()
    if len(norm) > 90:
        return None
    m = ENTETE.match(norm)
    if not m:
        return None
    numero = int(m.group(1))
    if numero not in TITRES_LOIS:
        return None
    reste = sans_article(m.group(2).strip())
    variantes = [TITRES_LOIS[numero]] + VARIANTES_TITRES.get(numero, [])
    if not any(reste.startswith(sans_article(v)) for v in variantes):
        return None
    if numero == loi_courante + 1 or (numero == 1 and loi_courante != 1):
        return numero
    return None


def decouper_en_sections(pages: list[str]) -> list[dict]:
    """Associe chaque ligne du document à une loi (0 = hors des 17 lois)."""
    sections, loi, actuelle = [], 0, {"loi": 0, "page": 1, "lignes": []}
    for num_page, texte in enumerate(pages, start=1):
        for ligne in texte.splitlines():
            if not ligne.strip():
                continue
            nouvelle = detecter_entete(ligne, loi)
            if nouvelle is None and loi == 17 and FIN_DES_LOIS.match(normaliser(ligne).strip()):
                nouvelle = 0
            if nouvelle is not None:
                sections.append(actuelle)
                loi = nouvelle
                actuelle = {"loi": loi, "page": num_page, "lignes": []}
            actuelle["lignes"].append(ligne.strip())
    sections.append(actuelle)
    return [s for s in sections if s["lignes"]]


PAGE_DE_LOI = re.compile(r"^(?:\d+\s+)?loi\s+(\d{1,2})(?:\s+\d+)?$")
DEBUT_ANNEXE = re.compile(r"^(?:\d+\s+)?(protocole d'assistance|programme qualite|directives pratiques|glossaire)")
DEBUT_AMENDEMENTS = re.compile(r"^(?:\d+\s+)?(?:2026/27\s+)?amendements")
LOI_AMENDEE = re.compile(r"^loi\s+(\d{1,2})\s*[-–]\s*\S")


def decouper_par_pages(pages: list[str]) -> list[dict]:
    """Découpage adapté au livret officiel de l'IFAB.

    - Chaque loi commence sur une page qui ne contient que « Loi » et son numéro.
    - Le protocole VAR, le programme qualité, les directives et le glossaire
      sont rangés hors des 17 lois (loi 0).
    - Dans la partie « Amendements », chaque bloc « Loi N – … » est rattaché à
      la loi N : ce sont les nouveautés de l'édition.
    """
    sections, actuelle, amendements = [], {"loi": 0, "page": 1, "lignes": [], "amendement": False}, False

    def nouvelle_section(loi, page, amendement=False):
        nonlocal actuelle
        sections.append(actuelle)
        actuelle = {"loi": loi, "page": page, "lignes": [], "amendement": amendement}

    for num, texte in enumerate(pages, start=1):
        lignes = [l.strip() for l in texte.splitlines() if l.strip()]
        lignes = [l for l in lignes if l != str(num)]          # numéro de page seul
        tete = normaliser(" ".join(lignes[:4]))
        m = PAGE_DE_LOI.match(normaliser(" ".join(lignes)))
        if m and len(lignes) <= 3 and 1 <= int(m.group(1)) <= 17:
            amendements = False
            nouvelle_section(int(m.group(1)), num)
            continue
        if DEBUT_AMENDEMENTS.match(tete) and len(lignes) <= 4:
            amendements = True
            nouvelle_section(0, num)
        elif DEBUT_ANNEXE.match(tete):
            amendements = False
            nouvelle_section(0, num)
        for ligne in lignes:
            if amendements:
                ma = LOI_AMENDEE.match(normaliser(ligne))
                if ma and len(ligne) < 80 and 1 <= int(ma.group(1)) <= 17:
                    nouvelle_section(int(ma.group(1)), num, amendement=True)
                elif normaliser(ligne).startswith("protocole d'assistance") and len(ligne) < 80:
                    nouvelle_section(0, num)
            actuelle["lignes"].append(ligne)
    sections.append(actuelle)
    return [s for s in sections if s["lignes"]]


def loi_majoritaire(texte: str) -> int:
    """Secours si aucun titre n'est détecté : loi la plus citée dans l'extrait."""
    cites = Counter(int(n) for n in re.findall(r"loi\s*(\d{1,2})", normaliser(texte)) if int(n) in TITRES_LOIS)
    return cites.most_common(1)[0][0] if cites else 0


def decouper_en_extraits(sections: list[dict]) -> list[dict]:
    extraits = []
    for s in sections:
        mots = " ".join(s["lignes"]).split()
        pas = TAILLE_EXTRAIT - CHEVAUCHEMENT
        for debut in range(0, max(len(mots), 1), pas):
            morceau = mots[debut:debut + TAILLE_EXTRAIT]
            if len(morceau) < 15 and debut > 0:
                break
            texte = " ".join(morceau)
            loi = s["loi"]
            titre = NOMS_LOIS.get(loi, "Hors des 17 lois")
            if s.get("amendement"):
                titre += " (modifications 2026/27)"
            extraits.append({
                "id": f"x{len(extraits) + 1:04d}",
                "loi": loi,
                "titre": titre,
                "page": s["page"],
                "texte": texte,
            })
            if debut + TAILLE_EXTRAIT >= len(mots):
                break
    if all(e["loi"] == 0 for e in extraits):
        for e in extraits:
            e["loi"] = loi_majoritaire(e["texte"])
            e["titre"] = NOMS_LOIS.get(e["loi"], "Hors des 17 lois")
    return extraits


def ingerer(source: Path, sortie: Path) -> list[dict]:
    pages = lire_pages(source)
    sections = decouper_par_pages(pages)
    lois_trouvees = {s["loi"] for s in sections if s["loi"] and not s.get("amendement")}
    if len(lois_trouvees) < 17:   # mise en page différente : repérage par les titres
        sections = decouper_en_sections(pages)
    extraits = decouper_en_extraits(sections)
    sortie.parent.mkdir(parents=True, exist_ok=True)
    with sortie.open("w", encoding="utf-8") as f:
        for e in extraits:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    return extraits


def charger_extraits(chemin: Path) -> list[dict]:
    with chemin.open(encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def controle_qualite(extraits: list[dict]) -> tuple[list[str], list[str]]:
    """Vérifie que chaque loi est bien présente et assez fournie.

    Renvoie (lignes du tableau, alertes)."""
    par_loi = Counter(e["loi"] for e in extraits)
    mots, modifs = Counter(), Counter()
    for e in extraits:
        mots[e["loi"]] += len(e["texte"].split())
        if "modifications" in e["titre"]:
            modifs[e["loi"]] += 1
    lignes, alertes = [], []
    for loi in range(0, 18):
        nom = NOMS_LOIS.get(loi, "Hors des 17 lois (préambule, directives, glossaire)")
        lignes.append(f"Loi {loi:>2} | {nom:<45} | {par_loi[loi]:>3} extraits | {mots[loi]:>6} mots"
                      + (f" | dont {modifs[loi]} sur les modifications 2026/27" if modifs[loi] else ""))
        if loi and par_loi[loi] == 0:
            alertes.append(f"Loi {loi} introuvable : vérifier le titre dans le PDF.")
        elif loi and mots[loi] < 150:
            alertes.append(f"Loi {loi} très courte ({mots[loi]} mots) : découpage à vérifier.")
    return lignes, alertes
