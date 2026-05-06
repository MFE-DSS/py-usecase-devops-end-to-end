"""Service-layer tests. Hit the DB via repositories, but no HTTP.

These verify the orchestration glue: that the right calculation_version
is stamped, that DEGRADED is correctly persisted, and that a missing
benchmark mapping raises a clean exception.
"""
from datetime import date
from decimal import Decimal

import pytest

from risk.models import (
    Benchmark,
    BenchmarkReturn,
    Fund,
    FundBenchmarkMapping,
    FundReturn,
    RiskMetric,
)
from risk.repositories.fund_repository import (
    BenchmarkMappingNotFound,
    FundNotFound,
)
from risk.services.calculation_service import (
    CALCULATION_VERSION,
    METRIC_NAME,
    TrackingErrorCalculationService,
    TrackingErrorCommand,
)


def _seed_fund_with_history(months: int):
    """Create a fund + benchmark + N monthly returns ending 2026-04-30."""
    fund = Fund.objects.create(name="Alpha", isin="FR0000ALPHA1", currency="EUR")
    bench = Benchmark.objects.create(name="MSCI Europe", code="MSCI_EUR", currency="EUR")
    FundBenchmarkMapping.objects.create(
        fund=fund, benchmark=bench, valid_from=date(2024, 1, 1), is_active=True
    )

    end = date(2026, 4, 30)
    # generate N month-end dates ending at `end`
    dates = []
    y, m = end.year, end.month
    for _ in range(months):
        dates.append(date(y, m, _last_day_of_month(y, m)))
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    dates.reverse()

    fund_vals = [0.01, -0.005, 0.02, -0.01, 0.015, 0.005,
                 -0.002, 0.018, -0.012, 0.006, 0.008, -0.005,
                 0.011, -0.004, 0.017, -0.009, 0.014, 0.004]
    bench_vals = [0.008, -0.004, 0.018, -0.008, 0.014, 0.004,
                  -0.001, 0.016, -0.011, 0.005, 0.007, -0.004,
                  0.009, -0.003, 0.015, -0.007, 0.013, 0.003]

    for d, fv, bv in zip(dates, fund_vals[:months], bench_vals[:months]):
        FundReturn.objects.create(fund=fund, date=d, monthly_return=Decimal(str(fv)))
        BenchmarkReturn.objects.create(benchmark=bench, date=d, monthly_return=Decimal(str(bv)))

    return fund, bench


def _last_day_of_month(year: int, month: int) -> int:
    if month == 12:
        return 31
    from datetime import date as _d
    from datetime import timedelta
    return (_d(year, month + 1, 1) - timedelta(days=1)).day


@pytest.mark.django_db
def test_service_creates_metric_with_calculation_version():
    fund, _ = _seed_fund_with_history(months=12)
    svc = TrackingErrorCalculationService()
    metric = svc.run(TrackingErrorCommand(
        fund_id=fund.pk, as_of_date=date(2026, 4, 30), triggered_by="test"
    ))
    assert metric.calculation_run.calculation_version == CALCULATION_VERSION
    assert metric.metric_name == METRIC_NAME
    assert metric.window_months == 12
    assert metric.observation_count == 12
    assert metric.data_quality_status == "OK"
    assert metric.metric_value is not None


@pytest.mark.django_db
def test_service_returns_degraded_when_short_history():
    fund, _ = _seed_fund_with_history(months=10)
    svc = TrackingErrorCalculationService()
    metric = svc.run(TrackingErrorCommand(
        fund_id=fund.pk, as_of_date=date(2026, 4, 30), triggered_by="test"
    ))
    assert metric.data_quality_status == "DEGRADED"
    assert metric.observation_count == 10
    assert metric.metric_value is not None


@pytest.mark.django_db
def test_service_returns_insufficient_data_when_too_few_obs():
    fund, _ = _seed_fund_with_history(months=5)
    svc = TrackingErrorCalculationService()
    metric = svc.run(TrackingErrorCommand(
        fund_id=fund.pk, as_of_date=date(2026, 4, 30), triggered_by="test"
    ))
    assert metric.data_quality_status == "INSUFFICIENT_DATA"
    assert metric.metric_value is None


@pytest.mark.django_db
def test_service_raises_when_fund_missing():
    svc = TrackingErrorCalculationService()
    with pytest.raises(FundNotFound):
        svc.run(TrackingErrorCommand(
            fund_id=99999, as_of_date=date(2026, 4, 30), triggered_by="test"
        ))


@pytest.mark.django_db
def test_service_raises_when_no_benchmark_mapping():
    fund = Fund.objects.create(name="Orphan", isin="FR0000ORPHAN", currency="EUR")
    svc = TrackingErrorCalculationService()
    with pytest.raises(BenchmarkMappingNotFound):
        svc.run(TrackingErrorCommand(
            fund_id=fund.pk, as_of_date=date(2026, 4, 30), triggered_by="test"
        ))


@pytest.mark.django_db
def test_service_persists_methodology_snapshot():
    fund, _ = _seed_fund_with_history(months=12)
    svc = TrackingErrorCalculationService()
    metric = svc.run(TrackingErrorCommand(
        fund_id=fund.pk, as_of_date=date(2026, 4, 30), triggered_by="test"
    ))
    assert metric.methodology["ddof"] == 1
    assert metric.methodology["annualization"] == "sqrt12"
    assert metric.methodology["min_obs_ok"] == 12


@pytest.mark.django_db
def test_service_marks_run_success():
    fund, _ = _seed_fund_with_history(months=12)
    svc = TrackingErrorCalculationService()
    metric = svc.run(TrackingErrorCommand(
        fund_id=fund.pk, as_of_date=date(2026, 4, 30), triggered_by="test"
    ))
    assert metric.calculation_run.status == "SUCCESS"
