"""Appel au modèle de langage, quel que soit le fournisseur.

Fournisseurs pris en charge : mistral, anthropic, openai, ollama (local) et
simule (aucun appel réseau, pour tester le code sans clé). Réglages dans .env.
"""
import json
import os
import re
import time
from pathlib import Path

import requests

MODELES_PAR_DEFAUT = {
    "mistral": "mistral-small-latest",
    "anthropic": "claude-haiku-5-5",
    "openai": "gpt-4o-mini",
    "ollama": "mistral",
    "simule": "simule",
}


def charger_env(chemin: Path = Path(".env")) -> None:
    """Lit un fichier .env simple (CLE=valeur) sans dépendance externe."""
    if not chemin.exists():
        return
    for ligne in chemin.read_text(encoding="utf-8").splitlines():
        ligne = ligne.strip()
        if ligne and not ligne.startswith("#") and "=" in ligne:
            cle, val = ligne.split("=", 1)
            val = val.split(" #")[0]   # commentaire en fin de ligne
            os.environ.setdefault(cle.strip(), val.strip().strip('"').strip("'"))


class Modele:
    def __init__(self, fournisseur: str | None = None, nom: str | None = None):
        self.fournisseur = (fournisseur or os.environ.get("FOURNISSEUR_IA", "simule")).lower()
        if self.fournisseur not in MODELES_PAR_DEFAUT:
            raise ValueError(f"Fournisseur inconnu : {self.fournisseur}")
        self.nom = nom or os.environ.get("MODELE_IA") or MODELES_PAR_DEFAUT[self.fournisseur]

    def repondre(self, systeme: str, message: str, essais: int = 5) -> str:
        if self.fournisseur == "simule":
            return reponse_simulee(systeme, message)
        for tentative in range(essais):
            self._espacer()
            try:
                return self._appel(systeme, message)
            except requests.HTTPError as err:
                rep = err.response
                code = rep.status_code if rep is not None else 0
                detail = (rep.text[:300] if rep is not None else "").strip()
                if code in (429, 500, 502, 503, 529) and tentative < essais - 1:
                    attente = float(rep.headers.get("Retry-After", 0) or 0) if rep is not None else 0
                    attente = max(attente, 5 * 2 ** tentative)   # 5, 10, 20, 40 s
                    print(f"  … erreur {code} ({detail[:120]}), nouvel essai dans {attente:.0f} s")
                    time.sleep(attente)
                    continue
                raise RuntimeError(f"Erreur {code} du fournisseur {self.fournisseur} : {detail}") from None
            except (requests.Timeout, requests.ConnectionError) as err:
                # Réponse trop lente ou connexion coupée : on patiente puis on réessaie
                if tentative < essais - 1:
                    attente = 10 * (tentative + 1)
                    print(f"  … {type(err).__name__} (réponse trop lente ou connexion coupée), nouvel essai dans {attente} s")
                    time.sleep(attente)
                    continue
                raise RuntimeError(f"Le fournisseur {self.fournisseur} ne répond pas ({type(err).__name__}).") from None
        raise RuntimeError("Échec de l'appel au modèle")

    @staticmethod
    def _delai_max() -> float:
        """Temps d'attente maximal d'une réponse (les modèles « à raisonnement » sont lents)."""
        return float(os.environ.get("DELAI_MAX_REPONSE", "180"))

    def _espacer(self) -> None:
        """Respecte un délai minimal entre deux appels (offres gratuites : ~1 requête/s)."""
        delai = float(os.environ.get("DELAI_ENTRE_APPELS", "1.5" if self.fournisseur == "mistral" else "0"))
        ecoule = time.time() - getattr(self, "_dernier_appel", 0)
        if ecoule < delai:
            time.sleep(delai - ecoule)
        self._dernier_appel = time.time()

    def _appel(self, systeme: str, message: str) -> str:
        if self.fournisseur in ("mistral", "openai"):
            url = {"mistral": "https://api.mistral.ai/v1/chat/completions",
                   "openai": "https://api.openai.com/v1/chat/completions"}[self.fournisseur]
            cle = os.environ[f"{self.fournisseur.upper()}_API_KEY"]
            r = requests.post(url, timeout=self._delai_max(), headers={"Authorization": f"Bearer {cle}"}, json={
                "model": self.nom, "temperature": 0, "top_p": 1,
                "messages": [{"role": "system", "content": systeme}, {"role": "user", "content": message}],
            })
            r.raise_for_status()
            return extraire_texte(r.json()["choices"][0]["message"]["content"])
        if self.fournisseur == "anthropic":
            r = requests.post("https://api.anthropic.com/v1/messages", timeout=self._delai_max(), headers={
                "x-api-key": os.environ["ANTHROPIC_API_KEY"], "anthropic-version": "2023-06-01",
            }, json={"model": self.nom, "max_tokens": 400, "temperature": 0, "system": systeme,
                     "messages": [{"role": "user", "content": message}]})
            r.raise_for_status()
            return "".join(b.get("text", "") for b in r.json()["content"]).strip()
        if self.fournisseur == "ollama":
            url = os.environ.get("OLLAMA_URL", "http://localhost:11434") + "/api/chat"
            r = requests.post(url, timeout=300, json={
                "model": self.nom, "stream": False, "options": {"temperature": 0},
                "messages": [{"role": "system", "content": systeme}, {"role": "user", "content": message}],
            })
            r.raise_for_status()
            return r.json()["message"]["content"].strip()
        raise ValueError(self.fournisseur)


def extraire_texte(contenu) -> str:
    """Le contenu d'une réponse est soit un texte, soit (modèles « à raisonnement »
    comme mistral-large-4) une liste de morceaux : on ne garde que les morceaux
    de type texte et on ignore la réflexion interne du modèle."""
    if isinstance(contenu, str):
        return contenu.strip()
    morceaux = []
    for m in contenu or []:
        if isinstance(m, str):
            morceaux.append(m)
        elif isinstance(m, dict) and m.get("type", "text") == "text":
            morceaux.append(str(m.get("text", "")))
    return "".join(morceaux).strip()


def reponse_simulee(systeme: str, message: str) -> str:
    """Comportement déterministe pour les tests (aucune « intelligence »)."""
    if "VERDICT" in systeme:   # rôle de juge
        attendu = re.search(r"Réponse attendue : (.*)", message)
        donnee = re.search(r"Réponse de l'assistant : (.*)", message, re.S)
        mots = set(re.findall(r"\d+(?:,\d+)?", attendu.group(1) if attendu else ""))
        ok = mots and all(m in (donnee.group(1) if donnee else "") for m in mots)
        return json.dumps({"verdict": "correct" if ok else "faux", "justification": "simulation"})
    extraits = re.findall(r"\[Loi (\d+)\][^\n]*\n(.*)", message)
    if extraits:
        loi, texte = extraits[0]
        return f"{texte[:160]} [Loi {loi}]"
    return "Je ne trouve pas cette information dans les Lois du Jeu."
