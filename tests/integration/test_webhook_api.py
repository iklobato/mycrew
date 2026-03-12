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
    """POST /webhook (manual, no X-GitHub-Event) returns 202 and queues pipeline."""
    mock_kickoff.return_value = "Pipeline completed"
    payload = {
        "issue_url": "https://github.com/test/example/issues/123",
        "branch": "main",
        "dry_run": True,
        "test_command": "python -c 'print(\"Test passed\")'",
    }
    response = client.post("/webhook", json=payload)
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "accepted"
    assert data["issue_url"] == payload["issue_url"]
    assert data["message"] == "Pipeline queued"
    mock_kickoff.assert_called_once_with(
        issue_url=payload["issue_url"],
        branch="main",
        dry_run=True,
        test_command=payload["test_command"],
        programmatic=False,
    )


@patch("code_pipeline.webhook.kickoff")
def test_webhook_trigger_minimal_payload(mock_kickoff, client):
    """POST /webhook with minimal payload (issue_url only) returns 202."""
    mock_kickoff.return_value = "Done"
    response = client.post(
        "/webhook",
        json={"issue_url": "https://github.com/owner/repo/issues/42"},
    )
    assert response.status_code == 202
    assert response.json()["status"] == "accepted"


@patch("code_pipeline.webhook.kickoff")
def test_webhook_trigger_programmatic_passes_to_kickoff(mock_kickoff, client):
    """POST /webhook with programmatic: true passes programmatic=True to kickoff."""
    mock_kickoff.return_value = "Done"
    response = client.post(
        "/webhook",
        json={
            "issue_url": "https://github.com/owner/repo/issues/42",
            "programmatic": True,
        },
    )
    assert response.status_code == 202
    mock_kickoff.assert_called_once()
    call_kwargs = mock_kickoff.call_args[1]
    assert call_kwargs["programmatic"] is True


def test_webhook_manual_missing_issue_url_returns_400(client):
    """POST /webhook without issue_url (manual flow) returns 400."""
    response = client.post("/webhook", json={})
    assert response.status_code == 400


@patch("code_pipeline.webhook.kickoff")
def test_webhook_trigger_kickoff_failure_still_returns_202(mock_kickoff, client):
    """POST /webhook returns 202 even when kickoff fails in background."""
    mock_kickoff.side_effect = RuntimeError("Pipeline failed")
    response = client.post(
        "/webhook",
        json={"issue_url": "https://github.com/owner/repo/issues/1"},
    )
    assert response.status_code == 202
    assert response.json()["status"] == "accepted"


@patch("code_pipeline.settings.get_settings")
@patch("code_pipeline.webhook.kickoff")
def test_webhook_github_issues_assigned(mock_kickoff, mock_settings, client):
    """POST /webhook with GitHub issues/assigned returns 202 and queues pipeline."""
    mock_settings.return_value.github_webhook_secret = ""
    mock_settings.return_value.default_branch = "main"
    mock_settings.return_value.default_dry_run = False
    mock_kickoff.return_value = "Pipeline completed"
    payload = {
        "action": "assigned",
        "issue": {
            "number": 123,
            "html_url": "https://github.com/owner/repo/issues/123",
            "title": "Fix bug",
        },
        "repository": {"full_name": "owner/repo"},
        "assignee": {"login": "dev"},
    }
    response = client.post(
        "/webhook",
        json=payload,
        headers={"X-GitHub-Event": "issues", "X-Hub-Signature-256": ""},
    )
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "accepted"
    assert "issues/123" in data["issue_url"]
    assert data["message"] == "Pipeline queued"


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
            "http://localhost:8000/webhook",
            json=payload,
            timeout=10,
        )
        assert response.status_code == 202
        assert response.json().get("status") == "accepted"
    except requests.exceptions.ConnectionError:
        pytest.skip("Webhook server not running at localhost:8000")
