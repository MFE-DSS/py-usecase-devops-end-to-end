"""Unit tests on pure domain functions.

No DB, no Django. These tests run in milliseconds and protect the
methodology against silent regressions.
"""
import math

import numpy as np
import pandas as pd
import pytest

from risk.domain.metrics import (
    align_returns,
    classify_data_quality,
    compute_excess_returns,
    compute_tracking_error,
    compute_tracking_error_for_fund,
)


def _series(values, start="2025-05-31", freq="ME"):
    """Helper: month-end indexed pandas Series."""
    idx = pd.date_range(start=start, periods=len(values), freq=freq)
    return pd.Series(values, index=idx, dtype=float)


# --- align_returns ---------------------------------------------------------

def test_align_inner_join_drops_misaligned_dates():
    f = _series([0.01, 0.02, 0.03])
    b_idx = pd.DatetimeIndex(["2025-05-31", "2025-06-30"])
    b = pd.Series([0.005, 0.01], index=b_idx)
    aligned = align_returns(f, b)
    assert len(aligned) == 2
    assert list(aligned.columns) == ["fund", "benchmark"]


def test_align_drops_nans():
    f = _series([0.01, np.nan, 0.03])
    b = _series([0.005, 0.01, 0.02])
    aligned = align_returns(f, b)
    assert len(aligned) == 2  # NaN row dropped


def test_align_requires_datetime_index():
    f = pd.Series([0.01, 0.02])  # default RangeIndex
    b = _series([0.005, 0.01])
    with pytest.raises(TypeError):
        align_returns(f, b)


# --- compute_excess_returns ------------------------------------------------

def test_excess_returns_basic():
    aligned = pd.DataFrame({"fund": [0.02, 0.01], "benchmark": [0.015, 0.012]})
    e = compute_excess_returns(aligned)
    assert e.tolist() == pytest.approx([0.005, -0.002])
    assert e.name == "excess"


# --- compute_tracking_error ------------------------------------------------

def test_tracking_error_matches_known_formula():
    excess = pd.Series([0.01, -0.01, 0.02, -0.02] * 3)  # 12 obs
    te = compute_tracking_error(excess)
    expected = float(excess.std(ddof=1) * np.sqrt(12))
    assert te == pytest.approx(expected)


def test_tracking_error_zero_when_excess_constant():
    excess = pd.Series([0.0] * 12)
    assert compute_tracking_error(excess) == 0.0


def test_tracking_error_nan_when_too_few_points():
    excess = pd.Series([0.01])
    assert math.isnan(compute_tracking_error(excess))


def test_tracking_error_uses_ddof_1():
    """ddof=1 (unbiased) is the industry convention. ddof=0 would differ."""
    excess = pd.Series([0.01, -0.01, 0.02, -0.02])
    te_ddof1 = compute_tracking_error(excess)
    te_ddof0_manual = float(excess.std(ddof=0) * np.sqrt(12))
    assert te_ddof1 != pytest.approx(te_ddof0_manual)


# --- classify_data_quality -------------------------------------------------

@pytest.mark.parametrize(
    "obs, expected",
    [
        (0, "INSUFFICIENT_DATA"),
        (8, "INSUFFICIENT_DATA"),
        (9, "DEGRADED"),
        (11, "DEGRADED"),
        (12, "OK"),
        (24, "OK"),
    ],
)
def test_classify_data_quality_thresholds(obs, expected):
    assert classify_data_quality(obs) == expected


# --- compute_tracking_error_for_fund (orchestration pure) -----------------

def test_full_pipeline_ok_status_with_12_obs():
    f = _series([0.01, -0.005, 0.02, -0.01, 0.015, 0.005, -0.002, 0.018, -0.012, 0.006, 0.008, -0.005])
    b = _series([0.008, -0.004, 0.018, -0.008, 0.014, 0.004, -0.001, 0.016, -0.011, 0.005, 0.007, -0.004])
    res = compute_tracking_error_for_fund(f, b, window_months=12)
    assert res.data_quality_status == "OK"
    assert res.observation_count == 12
    assert res.value is not None
    assert res.value > 0


def test_full_pipeline_insufficient_data_returns_none_value():
    f = _series([0.01] * 5)
    b = _series([0.005] * 5)
    res = compute_tracking_error_for_fund(f, b, window_months=12)
    assert res.data_quality_status == "INSUFFICIENT_DATA"
    assert res.value is None
    assert res.observation_count == 5


def test_full_pipeline_degraded_with_10_obs():
    f = _series([0.01, 0.02, -0.01, 0.0, 0.005, -0.005, 0.01, 0.02, -0.01, 0.005])
    b = _series([0.008, 0.018, -0.012, 0.001, 0.004, -0.006, 0.009, 0.019, -0.011, 0.004])
    res = compute_tracking_error_for_fund(f, b, window_months=12)
    assert res.data_quality_status == "DEGRADED"
    assert res.observation_count == 10
    assert res.value is not None


def test_full_pipeline_takes_last_window_when_history_longer():
    """If 18 months of history are passed but window=12, only the last 12 are used."""
    f = _series([0.01] * 18)
    b = _series([0.0] * 18)
    res = compute_tracking_error_for_fund(f, b, window_months=12)
    assert res.observation_count == 12
    assert res.data_quality_status == "OK"
    # constant excess => zero TE
    assert res.value == pytest.approx(0.0)
