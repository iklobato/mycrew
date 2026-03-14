"""Unit tests for GitHub webhook integration."""

import hashlib
import hmac
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from code_pipeline.webhook import (
    _accepted_response,
    _default_params,
    _extract_github_params,
    _get_nested,
    _run_kickoff_background,
    verify_github_signature,
)


def test_signature_verification_valid_passes():
    """Valid signature passes verification."""
    secret = "mysecret"
    payload = b'{"test": "data"}'
    hash_obj = hmac.new(secret.encode("utf-8"), msg=payload, digestmod=hashlib.sha256)
    valid_signature = "sha256=" + hash_obj.hexdigest()
    with patch("code_pipeline.settings.get_settings") as mock_get:
        mock_get.return_value.github_webhook_secret = secret
        verify_github_signature(payload, valid_signature)


def test_signature_verification_invalid_fails():
    """Invalid signature raises."""
    secret = "mysecret"
    payload = b'{"test": "data"}'
    with patch("code_pipeline.settings.get_settings") as mock_get:
        mock_get.return_value.github_webhook_secret = secret
        with pytest.raises(HTTPException, match="Invalid signature"):
            verify_github_signature(payload, "sha256=invalid")


def test_signature_verification_missing_when_secret_set():
    """Missing signature fails when secret is configured."""
    secret = "mysecret"
    payload = b'{"test": "data"}'
    with patch("code_pipeline.settings.get_settings") as mock_get:
        mock_get.return_value.github_webhook_secret = secret
        with pytest.raises(HTTPException):
            verify_github_signature(payload, "")


def test_signature_verification_no_secret_passes():
    """No verification when secret not configured."""
    with patch("code_pipeline.settings.get_settings") as mock_get:
        mock_get.return_value.github_webhook_secret = ""
        verify_github_signature(b'{"test": "data"}', "")


def test_payload_extraction_issues():
    """Extract pipeline params from GitHub issue payload."""
    with patch("code_pipeline.settings.get_settings") as mock_get:
        mock_get.return_value.default_branch = "main"
        mock_get.return_value.default_dry_run = False
        sample_payload = {
            "action": "assigned",
            "issue": {
                "number": 123,
                "title": "Fix login page bug",
                "html_url": "https://github.com/owner/repo/issues/123",
                "body": "The login page crashes.",
                "labels": [{"name": "bug"}],
            },
            "repository": {"full_name": "owner/repo"},
            "assignee": {"login": "developer1"},
            "sender": {"login": "project-manager"},
        }
        params = _extract_github_params(sample_payload, "issues", "assigned")
        assert params is not None
        assert params["issue_url"] == "https://github.com/owner/repo/issues/123"
        assert params["dry_run"] is False
        assert params["branch"] == "main"


@pytest.mark.parametrize(
    ("name", "payload"),
    [
        ("missing_issue", {"repository": {"full_name": "owner/repo"}}),
        ("missing_html_url", {"issue": {"title": "Test", "number": 1}}),
        (
            "empty_html_url",
            {
                "issue": {"title": "Test", "number": 1, "html_url": ""},
                "repository": {"full_name": "owner/repo"},
            },
        ),
    ],
)
def test_invalid_payloads_raise(name, payload):
    """Invalid payloads raise HTTPException."""
    with pytest.raises(HTTPException):
        _extract_github_params(payload, "issues", "assigned")


def test_extract_github_params_unsupported_event_returns_none():
    """Unsupported event/action returns None."""
    assert _extract_github_params({}, "push", "opened") is None
    assert (
        _extract_github_params({"issue": {"html_url": "x"}}, "issues", "opened") is None
    )


def test_pr_comment_extraction():
    """Extract pipeline params from PR comment payload."""
    with patch("code_pipeline.settings.get_settings") as mock_get:
        mock_get.return_value.default_branch = "main"
        mock_get.return_value.default_dry_run = False
        sample_payload = {
            "action": "created",
            "comment": {
                "id": 123456789,
                "body": "This function needs better error handling.",
                "user": {"login": "code-reviewer"},
            },
            "pull_request": {
                "number": 42,
                "title": "Add user authentication middleware",
                "html_url": "https://github.com/owner/repo/pull/42",
            },
            "repository": {"full_name": "owner/repo"},
            "sender": {"login": "code-reviewer"},
        }
        params = _extract_github_params(
            sample_payload, "pull_request_review_comment", "created"
        )
        assert params is not None
        assert params["issue_url"] == "https://github.com/owner/repo/pull/42"
        assert params["dry_run"] is False
        assert params["branch"] == "main"


def test_get_nested_missing_key_returns_none():
    """_get_nested returns None when key is missing."""
    assert _get_nested({}, ("a",)) is None
    assert _get_nested({"a": 1}, ("a", "b")) is None
    assert _get_nested({"a": {"b": 1}}, ("a", "c")) is None


def test_get_nested_nested_path_returns_value():
    """_get_nested returns value for valid nested path."""
    data = {"a": {"b": {"c": 42}}}
    assert _get_nested(data, ("a", "b", "c")) == 42


def test_get_nested_not_dict_returns_none():
    """_get_nested returns None when intermediate value is not dict."""
    data = {"a": "string"}
    assert _get_nested(data, ("a", "b")) is None


def test_run_kickoff_background_calls_kickoff():
    """_run_kickoff_background calls kickoff with params."""
    with patch("code_pipeline.webhook.kickoff") as mock_kickoff:
        _run_kickoff_background(
            issue_url="https://github.com/o/r/issues/1",
            branch="main",
            dry_run=True,
        )
        mock_kickoff.assert_called_once_with(
            issue_url="https://github.com/o/r/issues/1",
            branch="main",
            dry_run=True,
        )


def test_run_kickoff_background_logs_on_exception():
    """_run_kickoff_background logs and swallows exception."""
    with patch("code_pipeline.webhook.kickoff", side_effect=RuntimeError("oops")):
        with patch("code_pipeline.webhook.logger") as mock_logger:
            _run_kickoff_background(issue_url="https://x")
            mock_logger.error.assert_called_once()
            assert "oops" in str(mock_logger.error.call_args)


def test_default_params_returns_settings_values():
    """_default_params returns branch and dry_run from settings."""
    with patch("code_pipeline.settings.get_settings") as mock_get:
        mock_get.return_value.default_branch = "develop"
        mock_get.return_value.default_dry_run = True
        params = _default_params()
        assert params["branch"] == "develop"
        assert params["dry_run"] is True
        assert params["programmatic"] is False


def test_default_params_defaults():
    """_default_params uses sensible defaults when settings not set."""
    with patch("code_pipeline.settings.get_settings") as mock_get:
        mock_get.return_value.default_branch = ""
        mock_get.return_value.default_dry_run = False
        params = _default_params()
        assert params["branch"] == ""
        assert params["dry_run"] is False


def test_accepted_response_returns_202():
    """_accepted_response returns correct 202 response."""
    response = _accepted_response("https://github.com/owner/repo/issues/123")
    assert response.status_code == 202
    from starlette.responses import JSONResponse

    assert isinstance(response, JSONResponse)
    assert b"123" in response.body
    assert b'"status"' in response.body
    assert b'"accepted"' in response.body
    assert b'"Pipeline queued"' in response.body


@patch("code_pipeline.webhook._send_callback")
def test_run_kickoff_background_with_callback_url(mock_send_callback):
    """_run_kickoff_background extracts callback_url and sends on completion."""
    with patch("code_pipeline.webhook.kickoff") as mock_kickoff:
        mock_kickoff.return_value = "success"
        _run_kickoff_background(
            issue_url="https://github.com/o/r/issues/1",
            callback_url="https://callback.example.com/notify",
        )
        mock_kickoff.assert_called_once_with(
            issue_url="https://github.com/o/r/issues/1"
        )
        mock_send_callback.assert_called_once()
        call_args = mock_send_callback.call_args[0]
        assert call_args[0] == "https://callback.example.com/notify"
        assert call_args[1] == "completed"


@patch("code_pipeline.webhook._send_callback")
def test_run_kickoff_background_sends_error_callback(mock_send_callback):
    """_run_kickoff_background sends error callback when kickoff fails."""
    with patch("code_pipeline.webhook.kickoff", side_effect=RuntimeError("boom")):
        _run_kickoff_background(
            issue_url="https://github.com/o/r/issues/1",
            callback_url="https://callback.example.com/notify",
        )
        mock_send_callback.assert_called_once()
        call_args = mock_send_callback.call_args[0]
        assert call_args[0] == "https://callback.example.com/notify"
        assert call_args[1] == "failed"
        assert "boom" in call_args[2]["error"]
