"""Étape 3 : l'assistant (le « G » de RAG, génération de la réponse).

Deux modes, avec les mêmes consignes pour que la comparaison soit juste :
- « sans_contexte » : le modèle répond de mémoire ;
- « rag » : le modèle reçoit les passages les plus pertinents du livret
  (4 en version 1, 6 en version 2 : voir rag/versions.py).
"""
import time

PHRASE_ABSTENTION = "Je ne trouve pas cette information dans les Lois du Jeu."

REGLES = f"""Règles :
- Réponds en français, en 3 phrases au maximum.
- Cite la ou les lois utilisées sous la forme [Loi N] (N entre 1 et 17).
- Si la question ne relève pas des Lois du Jeu ou si tu n'as pas l'information, réponds exactement : « {PHRASE_ABSTENTION} »
- N'invente jamais de chiffre ni de règle."""

SYSTEME_RAG = ("Tu es un assistant sur les Lois du Jeu de football de l'IFAB (édition 2026/27). "
               "Tu réponds UNIQUEMENT à partir des extraits fournis.\n" + REGLES)
SYSTEME_SANS_CONTEXTE = ("Tu es un assistant sur les Lois du Jeu de football de l'IFAB (édition 2026/27). "
                         "Tu réponds à partir de tes connaissances.\n" + REGLES)


def etiquette(e: dict) -> str:
    """[Loi N] pour un extrait d'une loi ; les autres pages ne doivent pas être citées comme « Loi 0 »."""
    return f"[Loi {e['loi']}]" if e["loi"] else "[Hors des 17 lois]"


def formater_extraits(extraits: list[dict]) -> str:
    return "\n\n".join(f"{etiquette(e)} {e['titre']} (page {e['page']})\n{e['texte']}" for e in extraits)


class Assistant:
    def __init__(self, modele, index=None, k: int = 4, version: str = "v1"):
        self.modele, self.index, self.k, self.version = modele, index, k, version

    def repondre(self, question: str, mode: str = "rag") -> dict:
        debut = time.time()
        extraits = []
        if mode == "rag":
            extraits = self.index.chercher(question, self.k)
            message = f"Extraits des Lois du Jeu :\n\n{formater_extraits(extraits)}\n\nQuestion : {question}"
            reponse = self.modele.repondre(SYSTEME_RAG, message)
        else:
            reponse = self.modele.repondre(SYSTEME_SANS_CONTEXTE, f"Question : {question}")
        return {
            "reponse": reponse,
            "lois_recuperees": sorted({e["loi"] for e in extraits}),
            "extraits": [e["id"] for e in extraits],
            "duree_s": round(time.time() - debut, 2),
        }
