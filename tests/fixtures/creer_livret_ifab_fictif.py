"""Imite la mise en page RÉELLE du livret IFAB 2026/27 (relevée sur le PDF),
avec un contenu FICTIF : préambule, une page « Loi / N » avant chaque loi,
en-têtes courants, protocole VAR, programme qualité, puis amendements."""
from pathlib import Path

from rag.ingestion import NOMS_LOIS

REMPLISSAGE = " ".join(["Phrase fictive sans valeur réglementaire."] * 25)


def generer(chemin: Path) -> Path:
    pages = []
    ajouter = pages.append
    ajouter("Lois du Jeu 2026/27\n1 Terrain\n2 Ballon\n3 Joueurs")
    ajouter("Lois du Jeu 2026/27   |  Table des matières\n11  Hors-jeu\n12  Fautes et incorrections")
    ajouter("3\nDirectives pour le\nprincipe selon lequel\nseul le capitaine peut\ns’adresser à l’arbitre\n" + REMPLISSAGE)
    ajouter("4\nLois du Jeu 2026/27   |  Notes et modifications\n" + REMPLISSAGE)
    ajouter("5\n2026/27\nLois\ndu Jeu")
    for n, titre in NOMS_LOIS.items():
        ajouter(f"Loi\n{n}")
        num = len(pages) + 1
        ajouter(f"{num}\n1. Section fictive de la loi {n}\nContenu fictif sur « {titre.lower()} ». {REMPLISSAGE}")
        num = len(pages) + 1
        ajouter(f"{num}\nLois du Jeu 2026/27   |  Loi {n}  |  {titre}\n2. Paragraphe fictif. {REMPLISSAGE}")
    ajouter("Protocole\nd’assistance\nvidéo à\nl’arbitrage")
    ajouter(f"{len(pages) + 1}\nTexte fictif sur l'assistance vidéo. {REMPLISSAGE}")
    ajouter("Programme\nQualité\nde la FIFA")
    ajouter(f"{len(pages) + 1}\nTexte fictif sur les normes de qualité. {REMPLISSAGE}")
    ajouter("2026/27\nAmendements\nLois du Jeu")
    ajouter(f"{len(pages) + 1}\nLois du Jeu 2026/27  |  Amendements Lois du Jeu 2026/27\nLoi 3 – Joueurs (p. 67)\n"
            f"Texte ajouté : délai fictif de sortie du joueur remplacé. {REMPLISSAGE}\n"
            f"Loi 15 – Rentrée de touche (p. 151, 152)\nTexte amendé : décompte fictif. {REMPLISSAGE}")
    ajouter(f"{len(pages) + 1}\nProtocole d’assistance vidéo à l’arbitrage (p. 165)\nTexte amendé fictif. {REMPLISSAGE}")
    chemin.write_text("\f".join(pages), encoding="utf-8")
    return chemin
