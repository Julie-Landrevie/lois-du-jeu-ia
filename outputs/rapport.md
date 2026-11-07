# Rapport d'évaluation — assistant Lois du Jeu

Modèle : `mistral / mistral-large-4` · 36 questions dans le document, 4 hors document · fichier : `resultats_v2_20261106_1955.csv`

## Indicateurs

| Indicateur | Avec RAG |
|---|---|
| Réponses exactes (questions dans le document) | 89 % |
| Réponses partielles | 3 % |
| Réponses fausses (erreurs, dont inventions) | 6 % |
| Refus de répondre à tort | 3 % |
| Réponses qui citent une loi | 97 % |
| Réponses qui citent la bonne loi | 97 % |
| Refus justifiés (questions hors document) | 100 % |
| Bonne loi parmi les passages retrouvés (rappel de la recherche) | 100 % |
| Temps moyen par réponse | 8.8 s |

Aucune réponse relue à la main pour l'instant (colonne « verdict_humain » vide).

## Réponses fausses ou à vérifier

| Question | Mode | Réponse | Verdict |
|---|---|---|---|
| q10 – À quelle distance de la ligne de but se trouve le point de penalty ? | Avec RAG | Le point de penalty se trouve à **11 m (12 yds)** de la ligne de but. Cette distance est mesurée entre le centre du point de penalty et la limite extérieure de la ligne de but. [Loi 1] | faux |
| q30 – Où doit se placer le gardien au moment d'un penalty ? | Avec RAG | Le gardien de but doit rester sur sa ligne de but, face au tireur, entre les poteaux avant que le tir ne soit effectué [Loi 14]. Au moment du tir, il doit avoir au moins un pied sur ou derrière sa ligne (ou au même nivea | faux |

## Lecture

- Les pourcentages des quatre premières lignes portent sur les questions dont la réponse est dans le livret.
- « Refus justifiés » : part des questions hors document où l'assistant a bien dit qu'il ne savait pas.
- Le verdict d'exactitude vient d'un juge automatique, remplacé par la relecture humaine quand elle existe.
