# 12 — Cheatsheet 2 pages

## Architecture
```
HTTP (ViewSet) → Service → Repository → ORM
                    ↓
                Domain (pure)
```

## Formule
```
TE_12M = std(R_fund - R_bench, ddof=1) * sqrt(12)
```

## Pipeline
```
fetch → align (inner join) → window 12M → excess → std ddof=1
     → annualize sqrt(12) → classify quality → persist (run + metric)
```

## Statuts qualité
| Obs | Statut |
|---|---|
| ≥ 12 | OK |
| 9-11 | DEGRADED |
| < 9 | INSUFFICIENT_DATA (value=None) |

## Models
`Fund · Benchmark · FundBenchmarkMapping · FundReturn · BenchmarkReturn · CalculationRun · RiskMetric · DataQualityIssue`

## Endpoints
- `GET /api/v1/funds/`
- `GET /api/v1/funds/{id}/tracking-error/?as_of=...`
- `POST /api/v1/calculation-runs/`
- `GET /api/v1/calculation-runs/{id}/metrics/`
- `GET /api/v1/funds/{id}/metric-lineage/`
- `GET /api/v1/data-quality/issues/`
- `GET /health/`

## Tests
- unit (domain pur, 100 % cov)
- service (fakes injectés)
- API (DRF APIClient)
- golden (CSV in + JSON expected)
- data quality (rules engine)

## Non-régression workflow
1. dev v1.1
2. run golden v1.0 et v1.1
3. diff report + tolérance
4. revue quant + IT
5. bump methodology_versions.md
6. release

## DevOps
```
docker compose up
  → migrate
  → seed_demo_data
  → gunicorn

CI: install → migrate → pytest --cov-fail-under=85 → build image
Rollback: redeploy ancien tag + replay batch
```

## Erreurs à éviter
- calcul dans la View
- `fields = "__all__"`
- UPDATE destructif sur returns
- pas de `calculation_version`
- pas de golden test
- pas de `data_quality_status` exposé
- oublier `ddof=1`
- oublier `sqrt(12)`
- benchmark non versionné dans le temps

## Réponses orales prêtes
- **Architecture** : 4 couches, domaine pur sans Django
- **Tests** : pyramid 70/20/10 + golden dataset
- **Versioning** : `calculation_version` + golden update obligatoire
- **Data quality** : 3 statuts exposés dans le payload
- **Incident** : tracer, hypothèses, requêtes, communication 3 niveaux

## Mots-clés senior
auditability · idempotence · lineage · methodology versioning · golden dataset · non-regression · data quality status · calculation_run · service layer · dependency inversion · OpenAPI contract · backward compatibility · production-readiness · observability

## Plan 2 jours
- **J1** : comprendre métier, formule, architecture, lire code, mock 10 questions
- **J2** : coder domain + tests, models + API, Docker up, simuler incident, mock interview 30 min
