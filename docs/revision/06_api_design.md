# 06 — API Design

## Endpoints

| # | Méthode | URL | Objectif | Code succès |
|---|---|---|---|---|
| 1 | GET | `/api/v1/funds/` | Liste paginée des fonds | 200 |
| 2 | GET | `/api/v1/funds/{id}/tracking-error/?as_of=YYYY-MM-DD` | Dernière TE | 200 / 404 |
| 3 | POST | `/api/v1/calculation-runs/` | Déclencher un run | 202 |
| 4 | GET | `/api/v1/calculation-runs/{id}/metrics/` | Métriques d'un run | 200 |
| 5 | GET | `/api/v1/funds/{id}/metric-lineage/?metric=...` | Historique calculs | 200 |
| 6 | GET | `/api/v1/data-quality/issues/` | Issues qualité | 200 |
| 7 | GET | `/health/` | Healthcheck | 200 |

## Payload type GET tracking-error

```json
{
  "fund_id": 42,
  "fund_isin": "FR0000123456",
  "benchmark_code": "STOXX_600",
  "metric_name": "tracking_error_12m",
  "metric_value": 0.0427,
  "window_months": 12,
  "as_of_date": "2026-04-30",
  "observation_count": 12,
  "data_quality_status": "OK",
  "calculation_version": "te.v1.0",
  "calculation_run_id": 1873,
  "methodology": {"ddof": 1, "annualization": "sqrt12", "min_obs": 12}
}
```

## Standards à respecter

| Standard | Application |
|---|---|
| REST pragmatique | Ressources nominatives (`funds`, `calculation-runs`) |
| Status codes | 200 read, 201 create sync, 202 accepted async, 404, 422, 503 |
| Erreurs | `{"detail": "...", "code": "FUND_NOT_FOUND"}` |
| Pagination | `?page=1&page_size=50` |
| Filtres | query string GET, body POST |
| Idempotence | header `Idempotency-Key` sur POST |
| Versioning | URL prefix `/api/v1/` |
| OpenAPI | `drf-spectacular`, `/api/schema/`, `/api/docs/` |
| Backward compat | ajout OK, suppression jamais en v1 |
| Représentation ≠ modèle | Serializer dédié, jamais `fields="__all__"` |

## Choix méthode HTTP
- **GET** : safe, idempotent, cacheable → consultation
- **POST** : non-idempotent par défaut, side-effects → trigger calc
- **PUT/PATCH** : update — ici peu pertinent (returns immutables)
- **DELETE** : rarement utilisé (auditability)

## Ce que je dois être capable d'expliquer en entretien
- GET vs POST : pourquoi POST pour trigger calcul
- Versioning d'API : approche URL prefix
- Idempotency-Key : pourquoi et comment
- Backward compatibility en v1
- Pourquoi pas `fields = "__all__"`
