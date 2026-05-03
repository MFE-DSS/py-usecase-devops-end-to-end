# 01 — Business Overview

## À quoi sert le service
Microservice interne calculant et exposant des métriques de risque pour des fonds suivis en Multi-Management. Première métrique : **Tracking Error 12M**.

## Consommateurs
- Portfolio Managers (PM) — risk budgeting
- Fund Selectors — conformité au mandat
- Risk Officers — détection de dérive de style
- Compliance — audit
- IT — reporting et alerting downstream

## Pourquoi ce n'est pas qu'une formule
La formule tient en une ligne. Les enjeux sont :
- alignement des dates (fin de mois ouvré vs calendaire)
- gestion des données manquantes (NaN au milieu d'une fenêtre)
- benchmark mapping qui change dans le temps
- devises homogènes
- dividendes (total return vs price return)
- fréquence stricte mensuelle
- décisions méthodologiques traçables

## Pourquoi un backend fiable
- persister chaque calcul (jamais à la volée non tracé)
- versionner la méthodologie (`calculation_version`)
- horodater les inputs (lineage)
- exposer un statut qualité (`OK`, `DEGRADED`, `INSUFFICIENT_DATA`)

## Pourquoi versionner le calcul
Si la convention NaN-handling change, **toutes les TE historiques peuvent bouger**. Le versioning permet : *"Ce chiffre du 31/03 a été calculé en v1.2, on n'y touche plus. Le chiffre du 30/04 est en v1.3."*

## Pourquoi un PM peut contester
- son fonds vient de lancer, returns history court
- il compare à Bloomberg : 4.2 % vs 4.5 %, pourquoi ?
- la fenêtre 12M inclut un mois où la NAV était stale

Le service doit pouvoir **expliquer** chaque chiffre : combien d'observations, quel benchmark, quelle version, quel statut qualité.

## Pourquoi 80 % des enjeux du poste
Un Quantitative Technology Analyst en Multi-Management :
1. comprend une métrique quant
2. la code proprement
3. l'industrialise dans un service
4. l'expose à des consommateurs
5. la défend face à un PM

Ce projet couvre exactement ces cinq dimensions.

## Ce que je dois être capable d'expliquer en entretien
- Pitch 60s sur le service
- Différence entre "calcul Excel" et "calcul industrialisé"
- Pourquoi un PM dépend de la fiabilité du chiffre, pas de la formule
