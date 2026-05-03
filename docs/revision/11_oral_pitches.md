# 11 — Oral Pitches Prêts

## 1. Pitch projet (60s)
*"J'ai construit un microservice Django REST qui calcule, stocke et expose la Tracking Error 12-mois pour un univers de fonds suivis en multi-management. L'enjeu n'est pas la formule — std des excess returns annualisée — mais l'industrialisation : alignement strict des dates, gestion des NaN avec un statut data_quality, versioning de la méthodologie via un calculation_run, exposition REST avec un contrat stable, tests unitaires sur le domaine pur, et un golden dataset pour la non-régression. C'est exactement le genre d'outil qu'un PM utilise au quotidien et qui doit pouvoir être défendu chiffre à chiffre face à une contestation."*

## 2. Architecture (30s)
*"Quatre couches : HTTP avec ViewSet + Serializer, service d'orchestration, repository pour l'accès données, et domaine pur pour le calcul. Le domaine ne dépend pas de Django, ce qui me donne des tests rapides et une formule isolée du framework. Le service est appelable depuis l'API, depuis un batch CLI, ou depuis Celery sans changer une ligne."*

## 3. Tracking Error (45s)
Voir `02_tracking_error_methodology.md`.

## 4. Tests (30s)
*"Test pyramid classique : 70 % unit sur le domain pur, 20 % service avec fakes, 10 % API end-to-end. En plus, un golden dataset versionné qui grave les valeurs attendues. Toute modification de la formule oblige à bumper la calculation_version et à mettre à jour le golden dans la même PR."*

## 5. Versioning méthodologique (30s)
*"Chaque calcul stocke sa calculation_version. Un changement de méthodologie bump la version, on rejoue le golden dataset, on produit un diff report avec un seuil de tolérance, on documente. Le chiffre historique reste reproductible : on peut toujours revenir à v1.0 et obtenir le même output."*

## 6. Data quality (20s)
*"Trois statuts exposés : OK, DEGRADED, INSUFFICIENT_DATA. Le statut est dans le payload API, donc le consommateur sait toujours sur quoi il s'appuie. En plus, un endpoint dédié liste les DataQualityIssue ouvertes."*

## 7. Incident (60s)
Voir `09_incident_playbook.md`.

## 8. SOLID (45s)
*"S : chaque fonction du domaine a une responsabilité — aligner, calculer l'excess, calculer la TE, classifier la qualité. O : pour ajouter une nouvelle métrique, j'ajoute une fonction et une route, je ne modifie rien. L : les repositories sont remplaçables par des fakes en test, le service ne voit pas la différence. I : un repository expose `get_monthly_returns`, pas tout l'ORM. D : le service prend ses dépendances en constructeur, ce qui découple application et infrastructure."*

## 9. DevOps (30s)
*"Dockerfile multi-stage Python 3.12-slim, docker-compose avec app + Postgres, healthcheck, CI GitHub Actions qui run migrate + pytest avec --cov-fail-under=85 + génère le schema OpenAPI. Release par tag d'image. Rollback par redéploiement de l'ancien tag plus replay du batch sur la fenêtre concernée."*

## 10. Mots-clés à placer
`auditability` · `idempotence` · `lineage` · `methodology versioning` · `golden dataset` · `non-regression` · `data quality status` · `calculation_run` · `service layer` · `dependency inversion` · `OpenAPI contract` · `backward compatibility` · `production-readiness` · `observability`

## Ce que je dois être capable d'expliquer en entretien
- Délivrer chacun de ces pitches sans support, en chronométrant
- Adapter la longueur selon la question (15s flash vs 60s deep)
- Glisser au moins 3 mots-clés par pitch
