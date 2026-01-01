"""Tests for the health endpoint."""

import pytest
from fastapi.testclient import TestClient

from phishguard.main import app


@pytest.fixture
def client() -> TestClient:
    """Create a test client for the FastAPI app."""
    return TestClient(app)


def test_health_check_returns_healthy(client: TestClient) -> None:
    """Test that the health endpoint returns a healthy status."""
    response = client.get("/api/health")

    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert "version" in data


def test_health_check_includes_version(client: TestClient) -> None:
    """Test that the health endpoint includes the correct version."""
    response = client.get("/api/health")

    data = response.json()
    assert data["version"] == "0.1.0"
