"""Génère un règlement FICTIF (contenu inventé) qui imite la mise en page du
livret officiel : sommaire, en-têtes de page répétés, paragraphes numérotés.
Il sert uniquement à tester le code sans le PDF officiel."""
from pathlib import Path

from rag.ingestion import NOMS_LOIS

FAITS = {
    1: "Le cercle fictif mesure 4 mètres. 1. Surface de jeu : la pelouse fictive est verte. 2. Marquage : des lignes fictives blanches.",
    3: "Une équipe fictive compte au minimum 5 joueurs pour débuter la rencontre fictive.",
    7: "Une rencontre fictive dure deux périodes de 30 minutes. La pause fictive ne dépasse pas 10 minutes.",
    11: "Dans ce règlement fictif, un joueur dans sa propre moitié n'est jamais en position de hors-jeu.",
    15: "La rentrée de touche fictive se fait à deux mains. Les adversaires fictifs restent à 3 mètres.",
}


def generer(chemin: Path) -> Path:
    pages = ["RÈGLEMENT FICTIF DE TEST\nSommaire\n" + "\n".join(f"Loi {n} – {t} {10 + n}" for n, t in NOMS_LOIS.items())]
    for n, titre in NOMS_LOIS.items():
        corps = FAITS.get(n, f"Texte fictif de remplissage pour la loi {n}, consacrée au thème « {titre.lower()} ».")
        remplissage = " ".join(["Phrase fictive sans valeur réglementaire."] * 30)
        pages.append(f"Loi {n} – {titre}\n{corps}\n{remplissage}")
        pages.append(f"Loi {n} | {titre}\n2. Paragraphe numéroté fictif de la loi {n}. {remplissage}")
    pages.append("Glossaire\nTermes fictifs de football. " + " ".join(["Définition fictive."] * 40))
    chemin.write_text("\f".join(pages), encoding="utf-8")
    return chemin
