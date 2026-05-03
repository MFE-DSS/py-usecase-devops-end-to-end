# 03 — Architecture

## Schéma des couches

```
┌────────────────────────────────────────┐
│  HTTP layer (DRF)                      │
│  ViewSet → Serializer → Permissions    │
└──────────────┬─────────────────────────┘
               │
┌──────────────▼─────────────────────────┐
│  Application layer                     │
│  Services (orchestration, transactions)│
└──────────────┬─────────────────────────┘
               │
       ┌───────┴────────┐
       │                │
┌──────▼──────┐  ┌──────▼─────────┐
│  Domain     │  │  Infrastructure│
│  (pure)     │  │  Repositories  │
│  numpy      │  │  ORM, models   │
└─────────────┘  └────────────────┘
```

## Principe directeur
- **Domain** ne dépend de personne (pas de Django, pas d'I/O)
- **Application** dépend du domaine + repositories (interfaces)
- **Infrastructure** dépend de Django/ORM
- **HTTP** dépend de Application (pas du domaine directement)

## Pourquoi ces frontières
| Frontière | Bénéfice |
|---|---|
| Domain pur | Tests ultra-rapides, formule isolée du framework |
| Service ≠ View | Réutilisable batch / CLI / Celery |
| Service ≠ Model | Pas de Fat Model, plusieurs versions possibles |
| Repository | Mockable en test, swap data source possible |

## Structure de repo

```
risk_metrics_service/
├── manage.py
├── pyproject.toml
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── Makefile
├── config/                  # settings, urls, wsgi
├── risk/
│   ├── models.py            # ORM
│   ├── api/                 # serializers, views, urls, permissions
│   ├── domain/              # pure functions (numpy, pandas)
│   ├── services/            # orchestration
│   ├── repositories/        # data access
│   ├── tests/
│   │   └── golden/          # CSV inputs + JSON expected outputs
│   └── management/commands/ # CLI: seed_demo_data, run_tracking_error
└── docs/
```

## Ce que je dois être capable d'expliquer en entretien
- Dessiner le schéma au tableau en 30 secondes
- Justifier chaque frontière par un bénéfice testabilité ou release
- Répondre à "pourquoi pas tout dans la View ?"
- Répondre à "Django ORM est déjà un repository pattern ?"
