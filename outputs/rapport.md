# Rapport d'évaluation — assistant Lois du Jeu

Modèle : `mistral / mistral-large-4` · 36 questions dans le document, 4 hors document · fichier : `resultats_20261105_2132.csv`

## Indicateurs

| Indicateur | Sans document | Avec RAG |
|---|---|---|
| Réponses exactes (questions dans le document) | 75 % | 78 % |
| Réponses partielles | 0 % | 0 % |
| Réponses fausses (erreurs, dont inventions) | 22 % | 3 % |
| Refus de répondre à tort | 3 % | 19 % |
| Réponses qui citent une loi | 97 % | 78 % |
| Réponses qui citent la bonne loi | 92 % | 78 % |
| Refus justifiés (questions hors document) | 100 % | 100 % |
| Bonne loi parmi les passages retrouvés (rappel de la recherche) | – | 83 % |
| Temps moyen par réponse | 8.6 s | 10.3 s |

Aucune réponse relue à la main pour l'instant (colonne « verdict_humain » vide).

## Réponses fausses ou à vérifier

| Question | Mode | Réponse | Verdict |
|---|---|---|---|
| q08 – En combien de temps un joueur remplacé doit-il quitter le terrain, et que se passe-t-il s'il dépasse ce délai ? | Sans document | Le joueur remplacé doit quitter le terrain immédiatement par la ligne de touche la plus proche, sauf indication contraire de l'arbitre, et avant que le remplaçant n'y entre [Loi 3]. S'il ne quitte pas le terrain dans un  | faux |
| q10 – À quelle distance de la ligne de but se trouve le point de penalty ? | Avec RAG | Le point de penalty se trouve à 11 m (12 yds) de la ligne de but. Cette distance est mesurée entre le centre du point de penalty et la limite extérieure de la ligne de but. [Loi 1] | faux |
| q25 – Combien de temps le gardien peut-il garder le ballon en main, et quelle est la sanction s'il dépasse ce délai ? | Sans document | Le gardien de but ne peut pas garder le ballon en main pendant plus de six secondes. Si ce délai est dépassé, l'arbitre accorde un corner à l'équipe adverse. [Loi 12] | faux |
| q26 – Un but marqué juste après que le ballon a touché accidentellement la main d'un attaquant est-il valable ? | Sans document | Non, ce but n'est pas valable : il est interdit de marquer directement avec la main ou le bras, même de manière accidentelle [Loi 12]. Le but est annulé et un coup franc indirect est accordé à l'équipe adverse à l'endroi | faux |
| q27 – Que se passe-t-il si un coup franc indirect entre directement dans le but adverse ? | Sans document | Lorsqu'un coup franc indirect est botté directement dans le but adverse sans avoir été touché par un autre joueur, aucun but n'est accordé. Un corner est alors accordé à l'équipe qui défendait. [Loi 13] | faux |
| q29 – Lorsque la défense forme un mur d'au moins trois joueurs, à quelle distance les attaquants doivent-ils se tenir ? | Sans document | Lorsqu'un mur défensif est formé d'au moins trois joueurs, les attaquants doivent se tenir à au moins **1 mètre** de celui-ci. Cette distance ne s'applique pas si les attaquants se trouvent dans la surface de réparation, | faux |
| q31 – Peut-on marquer directement sur une rentrée de touche ? | Sans document | Non, un but ne peut pas être marqué directement contre l'adversaire sur une rentrée de touche. Si le ballon pénètre directement dans le but adverse sans toucher aucun joueur, un coup de pied de coin est accordé à l'équip | faux |
| q33 – Que peut faire l'arbitre si une équipe tarde à effectuer une rentrée de touche ? | Sans document | L'arbitre doit infliger un avertissement (carton jaune) au joueur qui retarde la reprise du jeu. Cette sanction s'applique pour comportement antisportif lorsqu'une équipe tarde à effectuer une rentrée de touche. [Loi 12] | faux |
| q34 – Quand le ballon est-il en jeu sur un coup de pied de but ? | Sans document | Le ballon est en jeu sur un coup de pied de but lorsqu'il est botté et qu'il sort clairement de la surface de réparation. Les adversaires doivent se trouver à l'extérieur de la surface de réparation lorsque le ballon est | faux |

## Lecture

- Les pourcentages des quatre premières lignes portent sur les questions dont la réponse est dans le livret.
- « Refus justifiés » : part des questions hors document où l'assistant a bien dit qu'il ne savait pas.
- Le verdict d'exactitude vient d'un juge automatique, remplacé par la relecture humaine quand elle existe.
