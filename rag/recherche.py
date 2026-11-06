"""Étape 2 : retrouver les passages utiles (le « R » de RAG).

Recherche lexicale BM25, codée à la main pour rester lisible : un extrait est
d'autant mieux classé qu'il contient les mots de la question, surtout les mots
rares dans le document. Le titre de la loi est ajouté au texte indexé.

Option « exclure_hors_lois » (version 2) : on n'indexe que les extraits
rattachés à l'une des 17 lois, pour que les pages d'introduction, de
directives ou du protocole VAR ne prennent pas la place des bons passages.
"""
import math
from collections import Counter

from .texte import tokeniser


class IndexBM25:
    def __init__(self, extraits: list[dict], k1: float = 1.5, b: float = 0.75, exclure_hors_lois: bool = False):
        if exclure_hors_lois:
            extraits = [e for e in extraits if e["loi"] != 0]
        self.extraits = extraits
        self.k1, self.b = k1, b
        self.docs = [tokeniser(f"{e['titre']} {e['titre']} {e['texte']}") for e in extraits]
        self.longueurs = [len(d) for d in self.docs]
        self.longueur_moy = sum(self.longueurs) / max(len(self.docs), 1)
        self.freqs = [Counter(d) for d in self.docs]
        n = len(self.docs)
        df = Counter(m for d in self.docs for m in set(d))
        self.idf = {m: math.log(1 + (n - f + 0.5) / (f + 0.5)) for m, f in df.items()}

    def score(self, mots_question: list[str], i: int) -> float:
        s, freq, longueur = 0.0, self.freqs[i], self.longueurs[i]
        for m in mots_question:
            if m not in freq:
                continue
            tf = freq[m]
            norm = tf * (self.k1 + 1) / (tf + self.k1 * (1 - self.b + self.b * longueur / self.longueur_moy))
            s += self.idf.get(m, 0.0) * norm
        return s

    def chercher(self, question: str, k: int = 4) -> list[dict]:
        mots = tokeniser(question)
        scores = [(self.score(mots, i), i) for i in range(len(self.docs))]
        meilleurs = sorted((x for x in scores if x[0] > 0), reverse=True)[:k]
        return [dict(self.extraits[i], score=round(s, 3)) for s, i in meilleurs]


def tester_recherche(extraits: list[dict], questions: list[dict], ks=(4, 6, 8)) -> tuple[list[str], dict]:
    """Rappel de la recherche SANS appel au modèle : pour chaque question dont la
    réponse est dans le livret, la bonne loi figure-t-elle parmi les k passages ?

    Renvoie (lignes du tableau, ratés par réglage)."""
    cas = [q for q in questions if q.get("type") == "dans_le_document" and str(q.get("loi_attendue", "")).strip()]
    lignes = ["| Périmètre | " + " | ".join(f"{k} passages" for k in ks) + " |",
              "|---|" + "---|" * len(ks)]
    rates = {}
    for exclure, libelle in ((False, "Tout le livret"), (True, "17 lois seulement")):
        index = IndexBM25(extraits, exclure_hors_lois=exclure)
        cellules = []
        for k in ks:
            manques = []
            for q in cas:
                trouves = index.chercher(q["question"], k)
                lois = sorted({e["loi"] for e in trouves})
                if int(q["loi_attendue"]) not in lois:
                    manques.append((q["id"], int(q["loi_attendue"]), lois))
            rates[(exclure, k)] = manques
            ok = len(cas) - len(manques)
            cellules.append(f"{ok}/{len(cas)} ({100 * ok / max(len(cas), 1):.0f} %)")
        lignes.append(f"| {libelle} | " + " | ".join(cellules) + " |")
    return lignes, rates
