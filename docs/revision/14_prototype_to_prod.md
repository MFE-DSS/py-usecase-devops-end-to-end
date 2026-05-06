# 14 — Prototype → Production

Cette note couvre la question : *"Comment passes-tu d'un prototype à une application Django en production ? Bootstrap rules, tests, environnements."*

## 1. Bootstrap rules (le "cookie cutter" mental)

Tout nouveau projet Django sérieux démarre avec **ces 10 décisions** prises avant la première feature :

1. **`pyproject.toml`** déclare runtime + dev deps. Pas de `requirements.txt` éparpillé.
2. **`config/settings.py`** lit la config via env vars (12-factor).
3. **`SECRET_KEY` jamais committé**, défaut dev marqué `insecure`.
4. **`DATABASE_URL`** parsé via `dj-database-url`.
5. **`BigAutoField`** par défaut — pas de migration douloureuse à 2B rows.
6. **`USE_TZ=True`** — toutes les datetimes en UTC en DB.
7. **`/health/` endpoint** dès le bootstrap, avant tout autre code.
8. **Layout en couches** : `domain/` (pur), `services/`, `repositories/`, `api/`. Pas de logique métier dans les views ou les models.
9. **Tests configurés** : `pytest-django`, `pytest.ini` (ou `[tool.pytest.ini_options]`) qui pointe le bon `DJANGO_SETTINGS_MODULE`.
10. **Lint + formatter** (`ruff`) configurés dès le commit zéro, pas après 5000 lignes.

### Ce qui distingue prototype et production
| Aspect | Prototype | Prod-ready |
|---|---|---|
| Settings | hardcodés | env vars + `.env.example` |
| DB | SQLite locale | Postgres avec `conn_max_age` |
| Auth | `AllowAny` | `IsAuthenticated` + permissions par viewset |
| `DEBUG` | `True` | `False` strict en prod |
| `ALLOWED_HOSTS` | `*` | liste explicite |
| Logs | `print()` | `logging` configuré, JSON structuré |
| Erreurs | tracebacks visibles | Sentry, redaction |
| Static files | servis par Django | `whitenoise` ou CDN |
| Secrets | en clair | Vault, AWS Secrets Manager, GCP Secret Manager |
| Migrations | générées à la volée | revues, testées, jamais éditées après merge |

## 2. Discipline de tests : unit vs integration vs e2e

### Unit tests
- ciblent les **fonctions pures** du domaine (`domain/metrics.py`)
- aucune DB, aucun HTTP
- **70 %** de la suite, doivent tourner en < 1s total
- exemple : `compute_tracking_error([0.01, -0.01, ...])` retourne la bonne valeur

### Integration tests
- ciblent les **services** et **repositories**
- DB en jeu (transaction rollback par test via `pytest.mark.django_db`)
- **20 %** de la suite
- exemple : le `TrackingErrorCalculationService` crée bien un `RiskMetric` avec la bonne version

### API tests (end-to-end côté backend)
- via `APIClient` DRF
- on teste le **contrat** : status code, clés JSON, codes d'erreur
- **10 %** de la suite
- exemple : `GET /api/v1/funds/42/tracking-error/` renvoie 404 si fonds absent

### Règle d'or
Si un test demande de mocker plus de 3 dépendances, c'est qu'il y a un problème de design — pas de test. Refactor les couches, pas les mocks.

### Garde-fous CI
```toml
[tool.pytest.ini_options]
addopts = "-ra --strict-markers --cov=risk --cov-fail-under=85"
```
- `--strict-markers` : interdit les marqueurs typo'd silencieux
- `--cov-fail-under=85` : la CI rejette une PR qui baisse la couverture sous 85 %
- `100 %` exigé sur `domain/` (la formule)

## 3. Migrations — la zone la plus risquée

### Règles non-négociables
1. **Toujours** committer la migration avec le code qui la rend nécessaire.
2. **Jamais** éditer une migration après qu'elle a été mergée — créer une nouvelle migration corrective.
3. **Jamais** lancer `migrate` à la main en prod — c'est le job du déploiement automatisé.
4. **Toujours** relire la migration générée — `makemigrations` n'est pas magique, il peut générer un `RemoveField` puis `AddField` qui drop des données.
5. **Données + schéma séparés** : `RunPython` pour data migrations, dans un fichier dédié, **réversible**.

### Workflow type
```bash
# 1. modifier les models
vim risk/models.py

# 2. générer la migration
python manage.py makemigrations

# 3. lire la migration
cat risk/migrations/0002_*.py

# 4. tester en local
python manage.py migrate

# 5. tester reverse
python manage.py migrate risk 0001

# 6. commit AVEC le code applicatif
git add risk/models.py risk/migrations/0002_*.py
```

### Migrations dangereuses
| Opération | Risque | Mitigation |
|---|---|---|
| `RemoveField` | data loss | étape 1: déprécier, étape 2: arrêter d'écrire, étape 3: drop |
| `AlterField` (NOT NULL) | downtime | rolling : ajouter colonne nullable, backfill, lock |
| Ajout d'index sur grosse table | lock | `CONCURRENTLY` (Postgres) via `RunSQL` |
| Renommer une colonne | apps connectées cassent | étape 1: alias, étape 2: client migré, étape 3: drop ancien nom |

### Squash
Au-delà de 50 migrations dans une app, `python manage.py squashmigrations risk 0001 0050` pour réduire le bruit. À faire entre deux releases majeures.

## 4. Environnements dev / test / prod

### Stratégie settings
**Option A** : un seul `settings.py` qui lit l'env. Recommandée pour ce projet.
**Option B** : `settings/base.py`, `settings/dev.py`, `settings/prod.py` qui héritent. Utile dès qu'on a 5+ env vars qui divergent.

### Variables typiques par env
```
# dev
DJANGO_DEBUG=1
DATABASE_URL=sqlite:///db.sqlite3
DJANGO_ALLOWED_HOSTS=*

# test (CI)
DJANGO_DEBUG=0
DATABASE_URL=postgres://test:test@localhost:5432/test
DJANGO_SECRET_KEY=test-key

# prod
DJANGO_DEBUG=0
DATABASE_URL=${SECRET_FROM_VAULT}
DJANGO_ALLOWED_HOSTS=risk.acme.internal
DJANGO_SECRET_KEY=${SECRET_FROM_VAULT}
SENTRY_DSN=${SECRET_FROM_VAULT}
```

### Règle parité dev/prod
- même version Django
- même version Python
- **même DB en CI qu'en prod** (Postgres, pas SQLite)
- même image Docker en staging et prod (seul l'env change)

## 5. Release / déploiement / rollback

### Pipeline CI → CD type
```
1. push branch
2. CI: lint + tests + coverage gate
3. PR review
4. merge to main
5. CI tag image: registry/risk-metrics:sha-abc123
6. deploy staging (auto)
7. smoke tests staging
8. promote to prod (manuel ou auto si feature-flag)
9. monitor 24h
```

### Rollback à deux niveaux

**Rollback infrastructure** (image)
- redéployer le tag précédent : `kubectl set image deploy/risk-metrics app=registry/risk-metrics:sha-prev`
- retour < 2 min

**Rollback logique** (calcul)
- les `RiskMetric` sont versionnés via `calculation_version`
- si v1.1 produit du faux : on garde l'image en place, on relance le batch en v1.0 sur la fenêtre concernée
- les anciens `RiskMetric` v1.1 restent en base (audit), on filtre côté API par version active

### Migrations + rollback
Un déploiement qui ajoute une migration et un rollback qui ne la défait pas → schema avancé / code reculé. Stratégie :
- migrations **forward-compatible** : nouveau code marche avec ancien schéma ET nouveau schéma
- déploie schema d'abord, code ensuite (expand/contract)

## 6. Observabilité minimale en prod

| Couche | Outil typique | Question répondue |
|---|---|---|
| Logs | JSON structuré + Loki/CloudWatch | "Que s'est-il passé pour le fonds 42 à 14h12 ?" |
| Métriques | Prometheus + Grafana | "Quelle est la latence p95 de mon endpoint TE ?" |
| Erreurs | Sentry | "Quelle exception a-t-on jamais vue sans le savoir ?" |
| Tracing | OpenTelemetry + Jaeger | "Où sont les 800ms ? DB ? service externe ?" |
| Healthcheck | k8s liveness/readiness | "Le pod est-il sain ?" |
| Business KPI | dashboard custom | "Combien de DEGRADED par jour ?" |

## Réponses orales prêtes

### "Comment fais-tu passer un projet du proto à la prod ?"
*"Trois axes en parallèle. Un, l'hygiène de code dès le commit zéro : pyproject.toml, layout en couches avec un domaine pur testable, settings en env vars, healthcheck. Deux, la discipline tests : pyramid 70/20/10, coverage gate en CI, golden dataset pour la non-régression métier. Trois, la chaîne de release : Docker pour la parité dev/prod, image taguée par SHA, déploiement staging avant prod, rollback par redéploiement de l'image précédente, et au-dessus un rollback logique via le calculation_version pour les bugs de calcul. Le critère 'prod-ready' c'est : si je merge à 17h59 un vendredi et que ça se déploie tout seul, est-ce que je peux dormir tranquille ? Si oui, c'est prêt."*

### "Bootstrap rules sur un nouveau projet ?"
*"Je pose dix décisions avant la première feature : pyproject.toml standard, settings via env vars, BigAutoField, UTC, healthcheck, layout en couches, pytest configuré, ruff configuré, README avec quickstart en 5 lignes, et un .env.example. Ces dix décisions sont gratuites au jour 1, et impayables à reprendre au jour 100. C'est ce que j'appelle un cookie cutter mental."*

### "Comment gères-tu les migrations en prod ?"
*"Trois règles strictes : la migration est committée avec le code qui la justifie ; jamais d'édition après merge, on corrige par une nouvelle migration ; et on lit chaque migration générée parce que makemigrations peut faire un RemoveField + AddField qui drop des données. Pour les changements risqués — colonne NOT NULL, rename, index sur grosse table — j'utilise le pattern expand/contract sur deux releases : on étend d'abord, le code tolère les deux schémas, on contracte ensuite. Et `migrate` ne se lance jamais à la main en prod, c'est le job du pipeline."*

## Ce que je dois être capable d'expliquer en entretien
- 10 décisions de bootstrap
- Différence prototype vs prod (10+ axes)
- Pyramid de tests + coverage gate
- Migrations : 5 règles non-négociables, opérations dangereuses
- Settings par env (option A vs B)
- Rollback infra ET rollback logique
- Observability stack minimale
