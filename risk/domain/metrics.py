"""Pure functions for risk metrics. No Django, no I/O.

This module is the methodological core. It is intentionally framework-free
so it can be unit-tested in milliseconds and reused outside Django (notebook,
batch CLI, future microservice).

Methodology version `te.v1.0`:
- monthly returns aligned by inner-join on month-end dates
- excess = R_fund - R_benchmark
- annualization = std(excess, ddof=1) * sqrt(12)
- thresholds: >=12 obs -> OK, 9-11 -> DEGRADED, <9 -> INSUFFICIENT_DATA
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

MIN_OBS_OK = 12
MIN_OBS_DEGRADED = 9
PERIODS_PER_YEAR = 12


@dataclass(frozen=True)
class TrackingErrorResult:
    """Output of a tracking-error calculation.

    `value` is None when the data quality status is INSUFFICIENT_DATA,
    so consumers must handle missing values explicitly rather than
    misreading a 0.0.
    """
    value: float | None
    observation_count: int
    data_quality_status: str  # OK | DEGRADED | INSUFFICIENT_DATA


def align_returns(
    fund_returns: pd.Series,
    benchmark_returns: pd.Series,
) -> pd.DataFrame:
    """Align two monthly return series on a common DatetimeIndex via inner-join.

    Both inputs must be DatetimeIndex-indexed. Rows with NaN on either side
    are dropped so the downstream excess calculation never silently propagates
    missing values.
    """
    if not isinstance(fund_returns.index, pd.DatetimeIndex):
        raise TypeError("fund_returns must have a DatetimeIndex")
    if not isinstance(benchmark_returns.index, pd.DatetimeIndex):
        raise TypeError("benchmark_returns must have a DatetimeIndex")

    df = pd.concat(
        {"fund": fund_returns, "benchmark": benchmark_returns},
        axis=1,
        join="inner",
    ).dropna()
    return df.sort_index()


def compute_excess_returns(aligned: pd.DataFrame) -> pd.Series:
    """Excess returns = fund - benchmark, on already-aligned data."""
    return (aligned["fund"] - aligned["benchmark"]).rename("excess")


def compute_tracking_error(excess: pd.Series, periods_per_year: int = PERIODS_PER_YEAR) -> float:
    """Annualized tracking error: std(excess, ddof=1) * sqrt(periods_per_year)."""
    if len(excess) < 2:
        return float("nan")
    return float(excess.std(ddof=1) * np.sqrt(periods_per_year))


def classify_data_quality(observation_count: int) -> str:
    if observation_count >= MIN_OBS_OK:
        return "OK"
    if observation_count >= MIN_OBS_DEGRADED:
        return "DEGRADED"
    return "INSUFFICIENT_DATA"


def compute_tracking_error_for_fund(
    fund_returns: pd.Series,
    benchmark_returns: pd.Series,
    window_months: int = 12,
) -> TrackingErrorResult:
    """Pure orchestration: align, slice to window, compute, classify.

    Still no I/O — the service layer is responsible for fetching inputs
    and persisting the result.
    """
    aligned = align_returns(fund_returns, benchmark_returns)
    aligned = aligned.tail(window_months)
    excess = compute_excess_returns(aligned)
    obs = len(excess)
    status = classify_data_quality(obs)

    if status == "INSUFFICIENT_DATA":
        return TrackingErrorResult(value=None, observation_count=obs, data_quality_status=status)

    te = compute_tracking_error(excess)
    return TrackingErrorResult(value=te, observation_count=obs, data_quality_status=status)
