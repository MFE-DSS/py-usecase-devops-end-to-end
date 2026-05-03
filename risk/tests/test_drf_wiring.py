"""Smoke tests verifying DRF + drf-spectacular are wired correctly.

These tests exist before any business endpoint, so they protect the
infrastructure: if someone breaks settings or url config, CI fails
loudly instead of silently shipping a broken framework setup.
"""
import pytest
from django.test import Client


@pytest.fixture
def client():
    return Client()


@pytest.mark.django_db
def test_health_endpoint(client):
    response = client.get("/health/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.django_db
def test_openapi_schema_endpoint(client):
    response = client.get("/api/schema/")
    assert response.status_code == 200
    # spectacular returns YAML by default
    assert b"openapi" in response.content


@pytest.mark.django_db
def test_swagger_ui_loads(client):
    response = client.get("/api/docs/")
    assert response.status_code == 200
    assert b"swagger" in response.content.lower()
