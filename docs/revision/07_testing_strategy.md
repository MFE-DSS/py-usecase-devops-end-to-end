# 07 — Testing Strategy

## Test Pyramid
- **70 %** unit tests sur `domain/` (fonctions pures, ultra-rapides)
- **20 %** service tests avec fakes
- **10 %** API tests end-to-end (DB)

## 5 catégories

### A. Unit tests (`test_metrics.py`)
Couvrent : `align_returns`, `compute_excess_returns`, `compute_tracking_error`, `classify_data_quality`, edge cases.

Edge cases obligatoires :
- alignement avec dates discordantes
- 0 observation
- 1 observation (NaN attendu)
- exactement 9 obs (DEGRADED)
- exactement 12 obs (OK)
- std nulle (replication parfaite)
- toutes valeurs NaN

### B. Service tests
- service crée bien un `RiskMetric`
- service rattache la bonne `calculation_version`
- service détecte les données manquantes
- service retourne `DEGRADED` si trop peu d'observations
- transaction atomique (run + metric ou rien)

### C. API tests
- endpoint returns 200 sur happy path
- endpoint returns 404 si fonds absent
- endpoint expose `data_quality_status`
- contrat JSON respecté (clés attendues présentes)
- endpoint **ne recalcule pas** silencieusement (lecture seule)

### D. Non-regression tests
- golden dataset versionné (CSV inputs + JSON expected)
- même input + même `calculation_version` = même output (à 1e-8 près)
- changement de version = update explicite du JSON dans la PR

### E. Data quality tests
- fonds actif sans return récent → `STALE_NAV`
- benchmark manquant → `MISSING_BENCHMARK`
- dates non alignées
- duplicates (cassés par UniqueConstraint)
- return aberrant (|r| > 30%/mois)

## Golden dataset
Format :
- `tests/golden/inputs.csv` : returns mensuels (entity, date, return)
- `tests/golden/expected_outputs.json` : valeurs gravées avec tolérance

Update workflow :
1. PR de changement méthodologique
2. Régénération du JSON
3. Bump `calculation_version`
4. Documentation du diff dans `methodology_versions.md`

## Couverture cible
- 100 % sur `domain/metrics.py`
- 85 % global
- CI fail si `--cov-fail-under=85` non atteint

## Ce que je dois être capable d'expliquer en entretien
- Test pyramid et pourquoi 70/20/10
- Différence unit / integration / e2e
- Qu'est-ce qu'un golden dataset
- Comment éviter les tests flaky (freeze time, seed random)
- Que mocker (I/O externes), que ne jamais mocker (le code testé)
