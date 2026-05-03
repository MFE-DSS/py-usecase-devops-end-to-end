# 08 — DevOps

## Pile minimale
- Docker (image Python 3.12-slim)
- docker-compose (app + Postgres)
- `.env` pour secrets/config
- Makefile pour commandes courantes
- GitHub Actions pour CI

## Concepts clés

| Concept | Définition |
|---|---|
| Image | Recette figée (FS + commande) |
| Conteneur | Instance runtime d'une image |
| Build | `docker build` produit une image |
| Run | `docker run` instancie un conteneur |
| Volume | Persistence indépendante du conteneur |
| Healthcheck | Vérifie liveness (DB joignable, port ouvert) |
| Compose | Orchestration locale multi-services |

## Pourquoi conteneuriser
- reproductibilité dev/prod
- onboarding rapide (`docker compose up`)
- isolation des dépendances système (libpq)
- tag d'image = unité de release/rollback

## Workflow release / rollback
1. tag d'image (`registry/risk-metrics:v1.0`)
2. déploiement = redéploiement avec nouveau tag
3. rollback = redéploiement avec ancien tag + replay batch sur fenêtre impactée
4. les `RiskMetric` versionnées permettent un rollback **logique** (sans toucher l'image)

## CI conceptuelle
```
checkout → install → migrate → pytest --cov-fail-under=85 → build image → push registry
```

## Monitoring (à connaître même si pas implémenté)
- logs structurés JSON (`fund_id`, `run_id`, `duration_ms`)
- `/health/` endpoint
- métriques Prometheus optionnelles (latence p95, error rate)
- count(DEGRADED) par jour comme signal qualité
- error tracking via Sentry

## Ce que je dois être capable d'expliquer en entretien
- Image vs conteneur
- Build vs run
- Pourquoi healthcheck
- Comment faire un rollback
- Comment monitorer un service de calcul
- Différence migration en dev vs prod (toujours auto via app, jamais manuel)
