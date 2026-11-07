# Assistant IA sur les Lois du Jeu — RAG et évaluation de la qualité des réponses

Un assistant de questions-réponses sur les **Lois du Jeu de football (IFAB, édition 2026/27)**, et surtout une **grille d'évaluation** pour mesurer si ses réponses sont fiables : exactitude, source citée, bonne source, capacité à dire « je ne sais pas ».

La question posée : **un modèle de langage répond-il mieux quand on lui fournit le texte officiel (RAG) que lorsqu'il répond de mémoire ?** Les Lois du Jeu sont un bon terrain de test : le texte fait foi, il change chaque année (les nouveautés 2026/27 ne sont pas forcément connues d'un modèle), et les erreurs se vérifient facilement.

## Ce que fait le projet
| Étape | Fichier | Choix |
|---|---|---|
| Préparation des données | `rag/ingestion.py` | Découpage par loi (repérage des 17 titres), extraits de ~180 mots avec chevauchement de 40 mots, page conservée ; contrôle qualité par loi |
| Recherche | `rag/recherche.py` | BM25 codé à la main (mots-clés pondérés par leur rareté) : simple, explicable, sans service externe |
| Génération | `rag/assistant.py` | Mêmes consignes dans les deux modes : citer [Loi N], 3 phrases maximum, phrase d'abstention imposée, ne rien inventer |
| Modèle | `rag/modele.py` | Mistral, Anthropic, OpenAI ou modèle local (Ollama), température 0 ; mode « simulé » pour tester sans clé |
| Évaluation | `rag/evaluation.py` | Juge automatique (second appel au modèle) + relecture humaine possible ligne par ligne |
| Rapport | `rag/rapport.py` | Indicateurs par mode, liste des erreurs, accord juge / humain |

## Les indicateurs

| Indicateur | Ce qu'il mesure |
|---|---|
| Réponses exactes / partielles / fausses | Fond de la réponse comparé à une réponse de référence rédigée à partir du livret |
| Refus de répondre à tort | L'assistant dit « je ne trouve pas » alors que la réponse est dans le livret |
| Réponses qui citent une loi / la bonne loi | Traçabilité : peut-on vérifier la réponse ? |
| Refus justifiés | Questions hors document (classement d'un championnat, futsal…) : l'assistant doit refuser plutôt qu'inventer |
| Rappel de la recherche | La bonne loi est-elle dans les passages fournis ? Sépare les erreurs de recherche des erreurs de génération |
| Accord juge / humain | Fiabilité du juge automatique, mesurée sur les réponses relues |

## Le jeu de questions

`data/questions.csv` : 40 questions, dont 36 dont la réponse est dans le livret (durée, joueurs, terrain, hors-jeu, fautes, coups francs, penalty, touche, corner, **trois nouveautés 2026/27**) et 4 hors document. Les réponses de référence ont été rédigées à partir des Lois du Jeu ; leur relecture ligne à ligne dans le livret officiel est en cours, en commençant par les 7 lignes signalées dans la colonne `a_verifier`.

## Résultats — version 1 (5 novembre 2026)

Modèle : `mistral-large-4` (API Mistral), température 0. Recherche v1 : 4 passages, tout le livret. Verdicts d'exactitude donnés par le juge automatique (relecture humaine en cours).

| Indicateur | Sans document | Avec le livret (RAG v1) |
|---|---|---|
| Réponses exactes | 75 % | 78 % |
| **Réponses fausses** | **22 %** (8 sur 36) | **3 %** (1 sur 36) |
| Refus de répondre à tort | 3 % | 19 % (7 sur 36) |
| Réponses qui citent la bonne loi | 92 % | 78 % |
| Nouveautés 2026/27 bien traitées | 0 sur 3 | 3 sur 3 |
| Refus justifiés (questions hors document) | 4 sur 4 | 4 sur 4 |
| Bonne loi parmi les passages retrouvés | – | 83 % |

**Ce qu'on en retient**

1. **Avec le texte officiel, l'assistant ne se trompe presque plus** (22 % → 3 % de réponses fausses). Sans document, le modèle affirme avec assurance des règles fausses ou périmées : 6 secondes au lieu de 8 pour le gardien, corner au lieu de coup de pied de but, carton jaune au lieu du décompte de 5 secondes sur une rentrée de touche (nouveauté 2026/27).
2. **Le prix à payer, ce sont des refus** : avec le livret, l'assistant préfère dire « je ne trouve pas » plutôt qu'inventer. Pour un assistant de référence, c'est le bon compromis : un refus se voit, une erreur affirmée avec assurance passe inaperçue.
3. **L'évaluation localise le maillon faible** : 5 refus sur 7 viennent de la recherche (la bonne loi n'était pas dans les passages fournis), pas du modèle. Une cause identifiée : 40 % des extraits sont des pages hors des 17 lois (introduction, directives, protocole VAR) qui prennent la place des bons passages.

## Version 2 (6 novembre 2026) : corriger le maillon faible

Correctifs issus de l'analyse des erreurs de la v1 (`rag/versions.py`) : recherche limitée aux 17 lois (modifications 2026/27 comprises), 6 passages au lieu de 4, et plus de citation « Loi 0 » pour les pages hors des 17 lois.

**1. La recherche seule** (`tester-recherche`, sans appel au modèle) : la bonne loi est retrouvée pour **36 questions sur 36**, contre 30 en v1. Les 6 ratés de la v1 avaient tous des passages hors des 17 lois parmi les résultats.

| Périmètre | 4 passages | 6 passages | 8 passages |
|---|---|---|---|
| Tout le livret (v1) | 83 % | 94 % | 97 % |
| 17 lois seulement | 97 % | **100 %** (v2) | 100 % |

**2. L'évaluation complète** (`comparer`, même modèle, mêmes 40 questions, juge automatique) :

| Indicateur | Sans document | RAG v1 | RAG v2 |
|---|---|---|---|
| Réponses exactes | 75 % | 78 % | **89 %** |
| Réponses partielles | 0 % | 0 % | 3 % |
| Réponses fausses | 22 % | 3 % | 6 % |
| Refus de répondre à tort | 3 % | 19 % | **3 %** |
| Réponses qui citent la bonne loi | 92 % | 78 % | **97 %** |
| Refus justifiés (hors document) | 100 % | 100 % | 100 % |
| Bonne loi parmi les passages retrouvés | – | 83 % | **100 %** |
| Temps moyen par réponse | 8,6 s | 10,3 s | 8,8 s |

**Ce qu'on en retient**

1. **Corriger la recherche suffit à faire disparaître presque tous les refus** (19 % → 3 %) : les réponses exactes passent de 78 % à 89 %, et la bonne loi est citée dans 97 % des cas.
2. **Les réponses fausses restent rares** (6 %, soit 2 questions sur 36, contre 1 en v1) : sur 36 questions, cet écart d'une réponse ne permet pas de conclure, et ces deux cas sont en cours d'analyse (erreur du modèle ou du juge automatique).
3. **La démarche** : mesurer, localiser le maillon faible (la recherche, pas le modèle), corriger, remesurer.

## Lancer le projet

```bash
pip install -r requirements.txt
cp .env.example .env            # puis renseigner le fournisseur, la clé et le modèle
# Télécharger le livret « Lois du Jeu 2026/27 (pages simples) » sur downloads.theifab.com
python3 main.py preparer --source data/lois_du_jeu_2026_27.pdf
python3 main.py demander "Combien de temps le gardien peut-il garder le ballon en main ?"
python3 main.py demander "Combien de temps le gardien peut-il garder le ballon en main ?" --mode sans_contexte
python3 main.py tester-recherche                         # rappel de la recherche par réglage, sans appel au modèle
python3 main.py evaluer --valides-seulement --version v1 # évaluation complète (sans document + RAG)
python3 main.py evaluer --valides-seulement --version v2 --modes rag
python3 main.py rapport                                  # recalcul après relecture humaine (colonne verdict_humain)
python3 main.py comparer                                 # sans document / RAG v1 / RAG v2
python3 -m unittest discover tests                       # 17 tests (livret fictif, modèle simulé)
```

Le PDF officiel n'est pas inclus dans ce dépôt (droits de l'IFAB) : chacun le télécharge sur le site officiel. Avec l'offre gratuite de Mistral, prévoir `DELAI_ENTRE_APPELS=6` à `8` dans `.env` (limite de 20 000 tokens par minute).

## Limites

- **40 questions** : assez pour comparer deux modes, trop peu pour des écarts fins entre modèles.
- **Juge automatique** : un modèle qui note un modèle peut se tromper ; d'où la colonne de relecture humaine et l'indicateur d'accord juge / humain.
- **Un seul modèle testé** (`mistral-large-4`) : les chiffres ne se transposent pas tels quels à un autre modèle.
- **Recherche lexicale** : BM25 rate les reformulations (« gardien » / « portier ») ; une recherche par embeddings serait l'étape suivante.
- **Découpage du PDF** : dépend de la mise en page ; le contrôle qualité signale une loi manquante ou trop courte.

## Pistes

Recherche hybride (BM25 + embeddings), comparaison de plusieurs modèles, questions piégées (règles d'anciennes éditions), suivi des indicateurs à chaque nouvelle édition des Lois du Jeu.
