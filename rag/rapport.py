"""Étape 5 : calculer les indicateurs et écrire le rapport (Markdown).

Si la colonne « verdict_humain » du CSV est remplie, elle remplace le verdict
du juge automatique : c'est la relecture humaine qui fait foi. Le rapport
mesure aussi l'accord entre le juge et l'humain (fiabilité du juge).
"""
import csv
from pathlib import Path

LIBELLES = {"sans_contexte": "Sans document", "rag": "Avec RAG"}


def pct(n: int, d: int) -> str:
    return f"{100 * n / d:.0f} %" if d else "–"


def charger(chemin: Path) -> list[dict]:
    with chemin.open(encoding="utf-8") as f:
        lignes = list(csv.DictReader(f))
    for l in lignes:
        humain = l.get("verdict_humain", "").strip().lower()
        l["verdict_final"] = humain or l["verdict_juge"]
    return lignes


def indicateurs(lignes: list[dict], mode: str) -> dict:
    ls = [l for l in lignes if l["mode"] == mode]
    dedans = [l for l in ls if l["type"] == "dans_le_document"]
    hors = [l for l in ls if l["type"] == "hors_document"]
    compte = lambda liste, v: sum(1 for l in liste if l["verdict_final"] == v)
    recup = [l for l in dedans if l["recuperation_ok"] != ""]
    return {
        "n_dedans": len(dedans), "n_hors": len(hors),
        "correct": pct(compte(dedans, "correct"), len(dedans)),
        "partiel": pct(compte(dedans, "partiel"), len(dedans)),
        "faux": pct(compte(dedans, "faux"), len(dedans)),
        "abstention_a_tort": pct(compte(dedans, "abstention"), len(dedans)),
        "source_citee": pct(sum(int(l["source_citee"]) for l in dedans), len(dedans)),
        "bonne_source": pct(sum(int(l["bonne_source"] or 0) for l in dedans), len(dedans)),
        "abstention_juste": pct(compte(hors, "correct"), len(hors)),
        "rappel_recherche": pct(sum(int(l["recuperation_ok"]) for l in recup), len(recup)) if recup else "–",
        "duree": f"{sum(float(l['duree_s']) for l in ls) / len(ls):.1f} s" if ls else "–",
    }


def accord_juge_humain(lignes: list[dict]) -> str:
    relues = [l for l in lignes if l.get("verdict_humain", "").strip() and l["type"] == "dans_le_document"]
    if not relues:
        return "Aucune réponse relue à la main pour l'instant (colonne « verdict_humain » vide)."
    accord = sum(1 for l in relues if l["verdict_humain"].strip().lower() == l["verdict_juge"])
    return f"Accord entre le juge automatique et la relecture humaine : {pct(accord, len(relues))} ({accord}/{len(relues)} réponses relues)."


def ecrire_rapport(resultats: Path, sortie: Path, modele: str = "") -> str:
    lignes = charger(resultats)
    modes = [m for m in ("sans_contexte", "rag") if any(l["mode"] == m for l in lignes)]
    ind = {m: indicateurs(lignes, m) for m in modes}
    tete = "| Indicateur | " + " | ".join(LIBELLES[m] for m in modes) + " |"
    sep = "|---|" + "---|" * len(modes)
    rangs = [
        ("Réponses exactes (questions dans le document)", "correct"),
        ("Réponses partielles", "partiel"),
        ("Réponses fausses (erreurs, dont inventions)", "faux"),
        ("Refus de répondre à tort", "abstention_a_tort"),
        ("Réponses qui citent une loi", "source_citee"),
        ("Réponses qui citent la bonne loi", "bonne_source"),
        ("Refus justifiés (questions hors document)", "abstention_juste"),
        ("Bonne loi parmi les passages retrouvés (rappel de la recherche)", "rappel_recherche"),
        ("Temps moyen par réponse", "duree"),
    ]
    tableau = [tete, sep] + [f"| {lib} | " + " | ".join(ind[m][cle] for m in modes) + " |" for lib, cle in rangs]
    erreurs = [l for l in lignes if l["verdict_final"] in ("faux", "a_verifier")]
    detail = ["| Question | Mode | Réponse | Verdict |", "|---|---|---|---|"]
    for l in erreurs:
        rep = l["reponse"].replace("\n", " ").replace("|", "/")
        detail.append(f"| {l['id']} – {l['question']} | {LIBELLES[l['mode']]} | {rep[:220]} | {l['verdict_final']} |")
    n0 = ind[modes[0]]
    texte = "\n".join([
        "# Rapport d'évaluation — assistant Lois du Jeu",
        "",
        f"Modèle : `{modele or 'non précisé'}` · {n0['n_dedans']} questions dans le document, {n0['n_hors']} hors document · fichier : `{resultats.name}`",
        "",
        "## Indicateurs",
        "",
        *tableau,
        "",
        accord_juge_humain(lignes),
        "",
        "## Réponses fausses ou à vérifier",
        "",
        *(detail if erreurs else ["Aucune."]),
        "",
        "## Lecture",
        "",
        "- Les pourcentages des quatre premières lignes portent sur les questions dont la réponse est dans le livret.",
        "- « Refus justifiés » : part des questions hors document où l'assistant a bien dit qu'il ne savait pas.",
        "- Le verdict d'exactitude vient d'un juge automatique, remplacé par la relecture humaine quand elle existe.",
    ])
    sortie.parent.mkdir(parents=True, exist_ok=True)
    sortie.write_text(texte + "\n", encoding="utf-8")
    return texte


def comparer(colonnes: list[tuple[str, Path, str]], sortie: Path) -> str:
    """Tableau comparatif : une colonne par (libellé, fichier de résultats, mode).

    Les verdicts relus à la main (colonne « verdict_humain ») sont pris en compte."""
    ind = [indicateurs(charger(chemin), mode) for _, chemin, mode in colonnes]
    rangs = [
        ("Réponses exactes", "correct"),
        ("Réponses partielles", "partiel"),
        ("Réponses fausses", "faux"),
        ("Refus de répondre à tort", "abstention_a_tort"),
        ("Réponses qui citent la bonne loi", "bonne_source"),
        ("Refus justifiés (hors document)", "abstention_juste"),
        ("Bonne loi parmi les passages retrouvés", "rappel_recherche"),
        ("Temps moyen par réponse", "duree"),
    ]
    lignes = ["| Indicateur | " + " | ".join(lib for lib, _, _ in colonnes) + " |",
              "|---|" + "---|" * len(colonnes)]
    lignes += [f"| {lib} | " + " | ".join(i[cle] for i in ind) + " |" for lib, cle in rangs]
    sources = [f"- {lib} : `{chemin.name}` (mode {mode})" for lib, chemin, mode in colonnes]
    texte = "\n".join(["# Comparaison des versions — assistant Lois du Jeu", "", *lignes, "",
                       "Fichiers utilisés :", *sources, "",
                       "Les verdicts relus à la main remplacent ceux du juge automatique."])
    sortie.parent.mkdir(parents=True, exist_ok=True)
    sortie.write_text(texte + "\n", encoding="utf-8")
    return texte
