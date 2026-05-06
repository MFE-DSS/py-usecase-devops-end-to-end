"""Persistence of CalculationRun + RiskMetric."""
from datetime import date
from decimal import Decimal

from risk.models import Benchmark, CalculationRun, Fund, RiskMetric


class MetricRepository:
    def create_run(self, calculation_version: str, triggered_by: str) -> CalculationRun:
        return CalculationRun.objects.create(
            calculation_version=calculation_version,
            triggered_by=triggered_by,
            status=CalculationRun.Status.PENDING,
        )

    def mark_run_success(self, run: CalculationRun) -> None:
        run.status = CalculationRun.Status.SUCCESS
        run.save(update_fields=["status"])

    def mark_run_failed(self, run: CalculationRun, notes: str = "") -> None:
        run.status = CalculationRun.Status.FAILED
        run.notes = notes
        run.save(update_fields=["status", "notes"])

    def persist_metric(
        self,
        *,
        fund: Fund,
        benchmark: Benchmark,
        run: CalculationRun,
        metric_name: str,
        metric_value: Decimal | None,
        window_months: int,
        as_of_date: date,
        observation_count: int,
        data_quality_status: str,
        methodology: dict,
    ) -> RiskMetric:
        return RiskMetric.objects.create(
            fund=fund,
            benchmark=benchmark,
            calculation_run=run,
            metric_name=metric_name,
            metric_value=metric_value,
            window_months=window_months,
            as_of_date=as_of_date,
            observation_count=observation_count,
            data_quality_status=data_quality_status,
            methodology=methodology,
        )

    def latest_for_fund(
        self, fund: Fund, metric_name: str, as_of: date
    ) -> RiskMetric | None:
        return (
            RiskMetric.objects
            .filter(fund=fund, metric_name=metric_name, as_of_date=as_of)
            .select_related("benchmark", "calculation_run")
            .order_by("-created_at")
            .first()
        )
