"""End-to-end API tests via DRF APIClient.

These tests verify the JSON contract: status codes, expected keys,
error shapes. They do NOT re-test the calculation (that's covered
by domain unit tests and service tests).
"""
from datetime import date
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from risk.models import (
    Benchmark,
    BenchmarkReturn,
    Fund,
    FundBenchmarkMapping,
    FundReturn,
)


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def fund_with_history(db):
    fund = Fund.objects.create(name="Alpha", isin="FR0000ALPHA9", currency="EUR")
    bench = Benchmark.objects.create(name="STOXX 600", code="STOXX_600", currency="EUR")
    FundBenchmarkMapping.objects.create(
        fund=fund, benchmark=bench, valid_from=date(2024, 1, 1), is_active=True
    )
    fv = [0.01, -0.005, 0.02, -0.01, 0.015, 0.005,
          -0.002, 0.018, -0.012, 0.006, 0.008, -0.005]
    bv = [0.008, -0.004, 0.018, -0.008, 0.014, 0.004,
          -0.001, 0.016, -0.011, 0.005, 0.007, -0.004]
    dts = [date(2025, 5, 31), date(2025, 6, 30), date(2025, 7, 31), date(2025, 8, 31),
           date(2025, 9, 30), date(2025, 10, 31), date(2025, 11, 30), date(2025, 12, 31),
           date(2026, 1, 31), date(2026, 2, 28), date(2026, 3, 31), date(2026, 4, 30)]
    for d, f, b in zip(dts, fv, bv):
        FundReturn.objects.create(fund=fund, date=d, monthly_return=Decimal(str(f)))
        BenchmarkReturn.objects.create(benchmark=bench, date=d, monthly_return=Decimal(str(b)))
    return fund


# --- GET /api/v1/funds/ ----------------------------------------------------

@pytest.mark.django_db
def test_list_funds_returns_paginated_response(api_client, fund_with_history):
    resp = api_client.get("/api/v1/funds/")
    assert resp.status_code == 200
    body = resp.json()
    assert {"count", "next", "previous", "results"} <= body.keys()
    assert body["count"] >= 1
    first = body["results"][0]
    assert {"id", "isin", "name", "currency", "active"} <= first.keys()


# --- POST /api/v1/calculation-runs/ ----------------------------------------

@pytest.mark.django_db
def test_trigger_calculation_returns_202_with_metric_payload(api_client, fund_with_history):
    resp = api_client.post(
        "/api/v1/calculation-runs/",
        data={
            "fund_id": fund_with_history.pk,
            "as_of_date": "2026-04-30",
            "triggered_by": "test",
        },
        format="json",
    )
    assert resp.status_code == 202
    body = resp.json()
    expected = {
        "id", "fund", "fund_isin", "benchmark", "benchmark_code",
        "metric_name", "metric_value", "window_months", "as_of_date",
        "observation_count", "data_quality_status",
        "calculation_run", "calculation_version", "methodology", "created_at",
    }
    assert expected <= body.keys()
    assert body["metric_name"] == "tracking_error_12m"
    assert body["data_quality_status"] == "OK"
    assert body["calculation_version"] == "te.v1.0"
    assert body["observation_count"] == 12


@pytest.mark.django_db
def test_trigger_calculation_returns_404_when_fund_missing(api_client):
    resp = api_client.post(
        "/api/v1/calculation-runs/",
        data={"fund_id": 99999, "as_of_date": "2026-04-30"},
        format="json",
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "FUND_NOT_FOUND"


@pytest.mark.django_db
def test_trigger_calculation_returns_422_when_no_benchmark_mapping(api_client):
    fund = Fund.objects.create(name="Orphan", isin="FR0000ORPHAN1", currency="EUR")
    resp = api_client.post(
        "/api/v1/calculation-runs/",
        data={"fund_id": fund.pk, "as_of_date": "2026-04-30"},
        format="json",
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "BENCHMARK_MAPPING_NOT_FOUND"


@pytest.mark.django_db
def test_trigger_calculation_validates_input(api_client):
    resp = api_client.post(
        "/api/v1/calculation-runs/",
        data={"fund_id": "not-an-int", "as_of_date": "bad-date"},
        format="json",
    )
    assert resp.status_code == 400


# --- GET /api/v1/funds/{id}/tracking-error/ -------------------------------

@pytest.mark.django_db
def test_get_tracking_error_404_when_no_metric(api_client, fund_with_history):
    resp = api_client.get(
        f"/api/v1/funds/{fund_with_history.pk}/tracking-error/?as_of=2026-04-30"
    )
    assert resp.status_code == 404


@pytest.mark.django_db
def test_get_tracking_error_returns_persisted_metric(api_client, fund_with_history):
    api_client.post(
        "/api/v1/calculation-runs/",
        data={"fund_id": fund_with_history.pk, "as_of_date": "2026-04-30",
              "triggered_by": "test"},
        format="json",
    )
    resp = api_client.get(
        f"/api/v1/funds/{fund_with_history.pk}/tracking-error/?as_of=2026-04-30"
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["data_quality_status"] == "OK"
    assert body["calculation_version"] == "te.v1.0"
    assert body["observation_count"] == 12


@pytest.mark.django_db
def test_get_tracking_error_400_when_as_of_missing(api_client, fund_with_history):
    resp = api_client.get(f"/api/v1/funds/{fund_with_history.pk}/tracking-error/")
    assert resp.status_code == 400
    assert resp.json()["code"] == "AS_OF_REQUIRED"


@pytest.mark.django_db
def test_get_tracking_error_400_when_as_of_invalid(api_client, fund_with_history):
    resp = api_client.get(
        f"/api/v1/funds/{fund_with_history.pk}/tracking-error/?as_of=not-a-date"
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "AS_OF_INVALID"


# --- GET /api/v1/calculation-runs/{id}/metrics/ ---------------------------

@pytest.mark.django_db
def test_calculation_run_metrics_listing(api_client, fund_with_history):
    trigger = api_client.post(
        "/api/v1/calculation-runs/",
        data={"fund_id": fund_with_history.pk, "as_of_date": "2026-04-30",
              "triggered_by": "test"},
        format="json",
    )
    run_id = trigger.json()["calculation_run"]
    resp = api_client.get(f"/api/v1/calculation-runs/{run_id}/metrics/")
    assert resp.status_code == 200
    metrics = resp.json()
    assert len(metrics) == 1
    assert metrics[0]["metric_name"] == "tracking_error_12m"
