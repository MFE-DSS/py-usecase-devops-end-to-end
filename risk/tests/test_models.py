"""Smoke tests on models: constraints, defaults, relations.

These tests protect the schema decisions (UniqueConstraint, PROTECT,
nullable fields). If a future migration weakens an invariant, CI fails.
"""
from datetime import date
from decimal import Decimal

import pytest
from django.db import IntegrityError

from risk.models import (
    Benchmark,
    CalculationRun,
    Fund,
    FundReturn,
    RiskMetric,
)


@pytest.mark.django_db
def test_fund_isin_is_unique():
    Fund.objects.create(name="Alpha", isin="FR0000000001", currency="EUR")
    with pytest.raises(IntegrityError):
        Fund.objects.create(name="Alpha 2", isin="FR0000000001", currency="EUR")


@pytest.mark.django_db
def test_fund_return_unique_per_fund_date():
    fund = Fund.objects.create(name="A", isin="FR0000000010", currency="EUR")
    FundReturn.objects.create(fund=fund, date=date(2025, 1, 31), monthly_return=Decimal("0.01"))
    with pytest.raises(IntegrityError):
        FundReturn.objects.create(fund=fund, date=date(2025, 1, 31), monthly_return=Decimal("0.02"))


@pytest.mark.django_db
def test_risk_metric_protects_fund_deletion():
    fund = Fund.objects.create(name="A", isin="FR0000000020", currency="EUR")
    bench = Benchmark.objects.create(name="MSCI", code="MSCI_W", currency="EUR")
    run = CalculationRun.objects.create(calculation_version="te.v1.0", triggered_by="test")
    RiskMetric.objects.create(
        fund=fund,
        benchmark=bench,
        calculation_run=run,
        metric_name="tracking_error_12m",
        metric_value=Decimal("0.04"),
        window_months=12,
        as_of_date=date(2025, 12, 31),
        data_quality_status="OK",
        observation_count=12,
    )
    with pytest.raises(Exception):  # ProtectedError, but Django subclass of IntegrityError
        fund.delete()


@pytest.mark.django_db
def test_risk_metric_value_can_be_null_when_insufficient_data():
    fund = Fund.objects.create(name="A", isin="FR0000000030", currency="EUR")
    bench = Benchmark.objects.create(name="B", code="B1", currency="EUR")
    run = CalculationRun.objects.create(calculation_version="te.v1.0", triggered_by="test")
    metric = RiskMetric.objects.create(
        fund=fund,
        benchmark=bench,
        calculation_run=run,
        metric_name="tracking_error_12m",
        metric_value=None,
        window_months=12,
        as_of_date=date(2025, 12, 31),
        data_quality_status="INSUFFICIENT_DATA",
        observation_count=3,
    )
    assert metric.metric_value is None
