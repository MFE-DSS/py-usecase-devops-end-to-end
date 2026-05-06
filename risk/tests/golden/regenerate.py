"""Regenerate expected_outputs.json from inputs.csv using the CURRENT code.

Run ONCE when bootstrapping the golden, or after a deliberate methodology
change (calculation_version bump). The output should be reviewed in the PR
and committed.

Usage:
    python -m risk.tests.golden.regenerate

Never run this in CI — the golden test will then trivially pass.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from risk.domain.metrics import compute_tracking_error_for_fund
from risk.services.calculation_service import CALCULATION_VERSION

GOLDEN_DIR = Path(__file__).parent
INPUTS = GOLDEN_DIR / "inputs.csv"
OUTPUTS = GOLDEN_DIR / "expected_outputs.json"

CASES = [
    {"name": "fund_a_full_12m", "fund": "FUND_A", "benchmark": "BENCH_X", "window": 12},
    {"name": "fund_b_insufficient", "fund": "FUND_B", "benchmark": "BENCH_X", "window": 12},
]


def main() -> None:
    df = pd.read_csv(INPUTS, parse_dates=["date"])
    results = {"calculation_version": CALCULATION_VERSION, "cases": []}

    for case in CASES:
        fund_s = df[df.entity == case["fund"]].set_index("date")["return"]
        bench_s = df[df.entity == case["benchmark"]].set_index("date")["return"]
        res = compute_tracking_error_for_fund(fund_s, bench_s, window_months=case["window"])
        results["cases"].append({
            "name": case["name"],
            "fund": case["fund"],
            "benchmark": case["benchmark"],
            "window": case["window"],
            "expected_status": res.data_quality_status,
            "expected_observation_count": res.observation_count,
            "expected_value": res.value,  # None or float
        })

    OUTPUTS.write_text(json.dumps(results, indent=2) + "\n")
    print(f"Wrote {OUTPUTS}")
    for c in results["cases"]:
        print(f"  {c['name']}: {c['expected_status']} value={c['expected_value']}")


if __name__ == "__main__":
    main()
