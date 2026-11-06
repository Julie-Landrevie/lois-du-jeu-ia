"""Outils de normalisation du texte français (accents, casse, mots vides)."""
import re
import unicodedata

MOTS_VIDES = set("""
a au aux avec ce ces cet cette dans de des du elle en et est etre il ils je la le les leur lui
ma mais me meme mes moi mon ne nos notre nous on ou par pas pour qu que qui sa se ses son sur ta
te tes toi ton tu un une vos votre vous y d l s c n j m t qu est sont ete peut peuvent doit doivent
si alors comme plus moins tout tous toute toutes quel quelle quels quelles combien comment quand
quoi lorsque lors avant apres entre sans sous chaque autre autres cela ceci celui celle
""".split())


def sans_accents(texte: str) -> str:
    nfkd = unicodedata.normalize("NFKD", texte)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def normaliser(texte: str) -> str:
    """Minuscules, sans accents, apostrophes et tirets unifiés."""
    t = sans_accents(texte).lower()
    t = t.replace("’", "'").replace("‘", "'").replace("–", "-").replace("—", "-")
    return t


def radical(mot: str) -> str:
    """Racinisation très légère : retire le pluriel (s, x) des mots assez longs."""
    if len(mot) > 4 and mot[-1] in "sx":
        return mot[:-1]
    return mot


def tokeniser(texte: str) -> list[str]:
    """Découpe en mots utiles pour la recherche (sans mots vides)."""
    mots = re.findall(r"[a-z0-9]+", normaliser(texte))
    return [radical(m) for m in mots if m not in MOTS_VIDES and (len(m) > 1 or m.isdigit())]
