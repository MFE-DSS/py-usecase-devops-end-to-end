# 05 — Data Model

## Vue d'ensemble

```
Fund 1──N FundReturn
  │
  ├─1──N FundBenchmarkMapping N──1 Benchmark 1──N BenchmarkReturn
  │
  └─1──N RiskMetric N──1 CalculationRun
              │
              └ data_quality_status, observation_count, methodology
```

## Tables clés

### Fund
- `id`, `name`, `isin` (unique, indexed), `currency` (ISO 4217), `active`
- Index sur `active`

### FundBenchmarkMapping (bitemporal)
- `fund`, `benchmark`, `valid_from`, `valid_to`, `is_active`
- UniqueConstraint `(fund, valid_from)`
- Permet de gérer un changement de benchmark dans le temps

### FundReturn / BenchmarkReturn
- `fund`/`benchmark`, `date` (fin de mois), `monthly_return` (Decimal), `source`, `created_at`
- UniqueConstraint `(entity, date)` — empêche les doublons
- Index `(entity, date)` — fenêtres glissantes rapides

### CalculationRun
- `calculation_version` (ex: "te.v1.0")
- `run_date`, `status` (PENDING/SUCCESS/FAILED), `triggered_by`, `notes`

### RiskMetric
- `fund`, `benchmark`, `calculation_run` (PROTECT)
- `metric_name`, `metric_value` (Decimal nullable), `window_months`, `as_of_date`
- `data_quality_status`, `observation_count`, `methodology` (JSONField)
- UniqueConstraint `(fund, metric_name, as_of_date, calculation_run)`
- Index `(fund, metric_name, as_of_date)` pour le lookup typique

### DataQualityIssue
- `fund`, `issue_type`, `severity`, `description`, `detected_at`, `resolved_at`

## Décisions clés
| Choix | Raison |
|---|---|
| `Decimal` returns/metrics | Précision auditable, pas de drift binaire |
| `on_delete=PROTECT` sur RiskMetric | Intégrité historique : pas de delete d'un fonds qui a des métriques |
| `methodology` en JSONField | Snapshot des paramètres utilisés (ddof, min_obs, annualization) |
| `CalculationRun` séparé | Traçabilité (qui/quand/quelle version) + rejouabilité |
| Pas d'UPDATE sur returns | Restatement = nouvelle ligne, jamais destructif |

## SQL équivalent (extrait)
```sql
CREATE TABLE risk_metric (
  id BIGSERIAL PRIMARY KEY,
  fund_id BIGINT NOT NULL REFERENCES fund(id),
  benchmark_id BIGINT NOT NULL REFERENCES benchmark(id),
  calculation_run_id BIGINT NOT NULL REFERENCES calculation_run(id),
  metric_name VARCHAR(50) NOT NULL,
  metric_value NUMERIC(12,8),
  window_months SMALLINT NOT NULL,
  as_of_date DATE NOT NULL,
  data_quality_status VARCHAR(30) NOT NULL,
  observation_count SMALLINT NOT NULL,
  methodology JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(fund_id, metric_name, as_of_date, calculation_run_id)
);
CREATE INDEX idx_risk_metric_lookup ON risk_metric(fund_id, metric_name, as_of_date);
```

## Ce que je dois être capable d'expliquer en entretien
- Pourquoi `Decimal` plutôt que `Float`
- Pourquoi un `CalculationRun` séparé du `RiskMetric`
- Comment gérer un restatement de returns sans destruction
- Pourquoi `on_delete=PROTECT`
- SQL pour récupérer la dernière TE par fonds (`DISTINCT ON`)
