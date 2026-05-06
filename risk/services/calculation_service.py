"""Application layer: orchestrates a tracking-error calculation use case.

Responsibilities:
- fetch fund + active benchmark mapping at as_of_date
- fetch monthly returns for both
- delegate the calculation to the pure domain
- persist a CalculationRun + RiskMetric atomically
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from django.db import transaction

from risk.domain.metrics import compute_tracking_error_for_fund
from risk.repositories.fund_repository import FundRepository
from risk.repositories.metric_repository import MetricRepository
from risk.repositories.return_repository import ReturnRepository

CALCULATION_VERSION = "te.v1.0"
METRIC_NAME = "tracking_error_12m"
WINDOW_MONTHS = 12
HISTORY_FETCH_MONTHS = 18  # buffer to handle missing recent months gracefully


@dataclass(frozen=True)
class TrackingErrorCommand:
    fund_id: int
    as_of_date: date
    triggered_by: str


class TrackingErrorCalculationService:
    """Constructor-injected dependencies — easy to swap for fakes in tests."""

    def __init__(
        self,
        fund_repo: FundRepository | None = None,
        return_repo: ReturnRepository | None = None,
        metric_repo: MetricRepository | None = None,
    ):
        self._funds = fund_repo or FundRepository()
        self._returns = return_repo or ReturnRepository()
        self._metrics = metric_repo or MetricRepository()

    @transaction.atomic
    def run(self, cmd: TrackingErrorCommand):
        fund = self._funds.get_active(cmd.fund_id)
        benchmark = self._funds.get_active_benchmark(fund, cmd.as_of_date)

        fund_returns = self._returns.get_fund_returns(
            fund, cmd.as_of_date, months=HISTORY_FETCH_MONTHS
        )
        bench_returns = self._returns.get_benchmark_returns(
            benchmark, cmd.as_of_date, months=HISTORY_FETCH_MONTHS
        )

        result = compute_tracking_error_for_fund(
            fund_returns, bench_returns, window_months=WINDOW_MONTHS
        )

        run = self._metrics.create_run(
            calculation_version=CALCULATION_VERSION,
            triggered_by=cmd.triggered_by,
        )
        metric_value = (
            Decimal(format(result.value, ".10f")) if result.value is not None else None
        )
        metric = self._metrics.persist_metric(
            fund=fund,
            benchmark=benchmark,
            run=run,
            metric_name=METRIC_NAME,
            metric_value=metric_value,
            window_months=WINDOW_MONTHS,
            as_of_date=cmd.as_of_date,
            observation_count=result.observation_count,
            data_quality_status=result.data_quality_status,
            methodology={
                "ddof": 1,
                "annualization": "sqrt12",
                "min_obs_ok": 12,
                "min_obs_degraded": 9,
                "history_fetch_months": HISTORY_FETCH_MONTHS,
            },
        )
        self._metrics.mark_run_success(run)
        return metric
