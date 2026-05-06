"""Non-regression tests against the golden dataset.

The golden dataset (inputs.csv + expected_outputs.json) is the single
source of truth for *expected* methodology output. If you change the
methodology (formula, ddof, annualization, thresholds), you MUST:

1. bump CALCULATION_VERSION in risk/services/calculation_service.py
2. re-run python -m risk.tests.golden.regenerate
3. review the diff in the PR (numerical changes must be justified)
4. document the change in docs/methodology_versions.md

A bare regression — i.e. the values shifted without an intentional change
— will make this test fail in CI, which is the whole point.
"""
import json
from pathlib import Path

import pandas as pd
import pytest

from risk.domain.metrics import compute_tracking_error_for_fund
from risk.services.calculation_service import CALCULATION_VERSION

GOLDEN_DIR = Path(__file__).parent / "golden"
INPUTS = GOLDEN_DIR / "inputs.csv"
EXPECTED = GOLDEN_DIR / "expected_outputs.json"

ABS_TOLERANCE = 1e-8


def _load_expected():
    payload = json.loads(EXPECTED.read_text())
    if not payload.get("cases"):
        pytest.skip(
            "Golden dataset is empty. Bootstrap it with: "
            "python -m risk.tests.golden.regenerate"
        )
    return payload


def test_golden_calculation_version_matches_code():
    payload = _load_expected()
    assert payload["calculation_version"] == CALCULATION_VERSION, (
        f"Golden was generated with {payload['calculation_version']!r} but code is "
        f"{CALCULATION_VERSION!r}. Either regenerate the golden (intentional change) "
        f"or revert the code change (regression)."
    )


def test_golden_outputs_unchanged():
    payload = _load_expected()
    df = pd.read_csv(INPUTS, parse_dates=["date"])

    for case in payload["cases"]:
        fund_s = df[df.entity == case["fund"]].set_index("date")["return"]
        bench_s = df[df.entity == case["benchmark"]].set_index("date")["return"]
        res = compute_tracking_error_for_fund(fund_s, bench_s, window_months=case["window"])

        assert res.data_quality_status == case["expected_status"], (
            f"[{case['name']}] status changed: "
            f"{res.data_quality_status} != {case['expected_status']}"
        )
        assert res.observation_count == case["expected_observation_count"], (
            f"[{case['name']}] observation_count changed"
        )
        if case["expected_value"] is None:
            assert res.value is None, f"[{case['name']}] expected None, got {res.value}"
        else:
            assert res.value is not None, f"[{case['name']}] expected value, got None"
            assert res.value == pytest.approx(case["expected_value"], abs=ABS_TOLERANCE), (
                f"[{case['name']}] numerical drift: "
                f"{res.value} != {case['expected_value']} (tol={ABS_TOLERANCE})"
            )
