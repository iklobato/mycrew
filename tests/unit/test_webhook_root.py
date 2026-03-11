"""Unit tests for webhook root and health endpoints."""

from fastapi.testclient import TestClient

from code_pipeline.webhook import app


def test_root_returns_ok():
    """GET / returns status ok."""
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_returns_healthy():
    """GET /health returns healthy."""
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
