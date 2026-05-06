# Methodology Versions

Each version corresponds to a `calculation_version` value stamped on
`CalculationRun` and `RiskMetric`. Old runs remain reproducible — you can
always re-derive a v1.0 number from the same inputs even after v1.1 ships.

## te.v1.0 — initial release

**Scope:** `tracking_error_12m`

**Methodology:**
- Inputs: monthly returns of fund and benchmark, indexed by month-end.
- Alignment: inner-join on date (drops any non-overlapping or NaN month).
- Window: last 12 aligned months relative to `as_of_date`.
- Calculation: `std(R_fund - R_bench, ddof=1) * sqrt(12)`.
- Data quality:
  - >= 12 obs → `OK`
  - 9-11 obs → `DEGRADED` (value still computed)
  - < 9 obs → `INSUFFICIENT_DATA` (value = NULL)

**Parameters snapshot stored in `RiskMetric.methodology`:**
```json
{
  "ddof": 1,
  "annualization": "sqrt12",
  "min_obs_ok": 12,
  "min_obs_degraded": 9,
  "history_fetch_months": 18
}
```

**Known limitations:**
- No currency conversion: fund and benchmark are assumed to be in the
  same currency. A FX-mismatched mapping will produce numerically valid
  but business-wrong TE.
- No outlier handling: a single extreme month will inflate the TE; the
  responsibility lies on `DataQualityIssue` flagging upstream.
- Total-return assumption: monthly returns are assumed dividend-reinvested.
  Price-return inputs would systematically understate TE for high-yield funds.

## How to ship a new version

1. Open a PR that bumps `CALCULATION_VERSION` in
   `risk/services/calculation_service.py`.
2. Run `python -m risk.tests.golden.regenerate` and commit the updated
   `risk/tests/golden/expected_outputs.json`.
3. Add a section here describing what changed and why.
4. Generate a diff report between the old and new versions on a representative
   set of funds; attach it to the PR.
5. Get sign-off from quant + IT before merging.
6. After release, monitor `data_quality_status` distribution for 48h.
