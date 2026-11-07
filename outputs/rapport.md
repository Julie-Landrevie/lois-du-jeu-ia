# Rapport d'évaluation — assistant Lois du Jeu

Modèle : `mistral / mistral-large-4` · 36 questions dans le document, 4 hors document · fichier : `resultats_v2_20261106_1955.csv`

## Indicateurs

| Indicateur | Avec RAG |
|---|---|
| Réponses exactes (questions dans le document) | 94 % |
| Réponses partielles | 3 % |
| Réponses fausses (erreurs, dont inventions) | 0 % |
| Refus de répondre à tort | 3 % |
| Réponses qui citent une loi | 97 % |
| Réponses qui citent la bonne loi | 97 % |
| Refus justifiés (questions hors document) | 100 % |
| Bonne loi parmi les passages retrouvés (rappel de la recherche) | 100 % |
| Temps moyen par réponse | 8.8 s |

Accord entre le juge automatique et la relecture humaine : 0 % (0/2 réponses relues).

## Réponses fausses ou à vérifier

Aucune.

## Lecture

- Les pourcentages des quatre premières lignes portent sur les questions dont la réponse est dans le livret.
- « Refus justifiés » : part des questions hors document où l'assistant a bien dit qu'il ne savait pas.
- Le verdict d'exactitude vient d'un juge automatique, remplacé par la relecture humaine quand elle existe.
