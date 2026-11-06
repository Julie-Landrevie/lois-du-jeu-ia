"""Réglages de la recherche, par version.

v1 : première version (évaluée le 5/11/2026) — 4 passages, tout le livret.
v2 : correctifs issus de l'évaluation de la v1 — 5 refus sur 7 venaient de la
     recherche, et 40 % des extraits sont des pages hors des 17 lois
     (introduction, directives, protocole VAR) qui prenaient la place des bons
     passages. La v2 limite la recherche aux 17 lois (modifications 2026/27
     comprises) et fournit 6 passages au lieu de 4.
"""
VERSIONS = {
    "v1": {"k": 4, "exclure_hors_lois": False,
           "description": "4 passages, tout le livret"},
    "v2": {"k": 6, "exclure_hors_lois": True,
           "description": "6 passages, 17 lois seulement (modifications 2026/27 comprises)"},
}
VERSION_PAR_DEFAUT = "v2"
