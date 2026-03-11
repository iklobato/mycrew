"""Tests for webhook API endpoints."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from code_pipeline.webhook import app


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


@patch("code_pipeline.webhook.kickoff")
def test_webhook_trigger_success(mock_kickoff, client):
    """POST /webhook/trigger with issue_url returns success when kickoff succeeds."""
    mock_kickoff.return_value = "Pipeline completed"
    payload = {
        "issue_url": "https://github.com/test/example/issues/123",
        "branch": "main",
        "dry_run": True,
        "test_command": "python -c 'print(\"Test passed\")'",
    }
    response = client.post("/webhook/trigger", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["issue_url"] == payload["issue_url"]
    assert "Pipeline completed" in data["result"]
    mock_kickoff.assert_called_once_with(
        issue_url=payload["issue_url"],
        branch="main",
        dry_run=True,
        test_command=payload["test_command"],
    )


@patch("code_pipeline.webhook.kickoff")
def test_webhook_trigger_minimal_payload(mock_kickoff, client):
    """POST /webhook/trigger with minimal payload (issue_url only)."""
    mock_kickoff.return_value = "Done"
    response = client.post(
        "/webhook/trigger",
        json={"issue_url": "https://github.com/owner/repo/issues/42"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"


def test_webhook_trigger_missing_issue_url_returns_422(client):
    """POST /webhook/trigger without issue_url returns validation error."""
    response = client.post("/webhook/trigger", json={})
    assert response.status_code == 422


@patch("code_pipeline.webhook.kickoff")
def test_webhook_trigger_kickoff_failure_returns_500(mock_kickoff, client):
    """POST /webhook/trigger returns 500 when kickoff raises."""
    mock_kickoff.side_effect = RuntimeError("Pipeline failed")
    response = client.post(
        "/webhook/trigger",
        json={"issue_url": "https://github.com/owner/repo/issues/1"},
    )
    assert response.status_code == 500


@pytest.mark.integration
def test_webhook_trigger_live():
    """Live integration test requiring running server. Skip by default."""
    import requests

    payload = {
        "issue_url": "https://github.com/test/example/issues/123",
        "branch": "main",
        "dry_run": True,
        "test_command": "python -c 'print(\"Test passed\")'",
    }
    try:
        response = requests.post(
            "http://localhost:8000/webhook/trigger",
            json=payload,
            timeout=10,
        )
        assert response.status_code == 200
        assert response.json().get("status") == "success"
    except requests.exceptions.ConnectionError:
        pytest.skip("Webhook server not running at localhost:8000")
