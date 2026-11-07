# Comparaison des versions — assistant Lois du Jeu

| Indicateur | Sans document | RAG v1 | RAG v2 |
|---|---|---|---|
| Réponses exactes | 75 % | 81 % | 94 % |
| Réponses partielles | 0 % | 0 % | 3 % |
| Réponses fausses | 22 % | 0 % | 0 % |
| Refus de répondre à tort | 3 % | 19 % | 3 % |
| Réponses qui citent la bonne loi | 92 % | 78 % | 97 % |
| Refus justifiés (hors document) | 100 % | 100 % | 100 % |
| Bonne loi parmi les passages retrouvés | – | 83 % | 100 % |
| Temps moyen par réponse | 8.6 s | 10.3 s | 8.8 s |

Fichiers utilisés :
- Sans document : `resultats_20261105_2132.csv` (mode sans_contexte)
- RAG v1 : `resultats_20261105_2132.csv` (mode rag)
- RAG v2 : `resultats_v2_20261106_1955.csv` (mode rag)

Les verdicts relus à la main remplacent ceux du juge automatique.
