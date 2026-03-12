"""Unit tests for code_pipeline.main helper functions."""

from unittest.mock import MagicMock

from code_pipeline.crews.reviewer_crew.reviewer_crew import ReviewVerdict
from code_pipeline.main import (
    _configure_logging,
    _fallback_exploration,
    _format_review_verdict,
    _is_retryable_error,
    _log_implementer_summary,
    _log_reviewer_verdict,
    _normalize_raw_verdict,
)


def test_is_retryable_error_rate_limit():
    """Rate limit errors (429) are retryable."""
    err = Exception("429 Too Many Requests")
    assert _is_retryable_error(err) is True


def test_is_retryable_error_empty_response():
    """Empty response errors are retryable."""
    err = Exception("None or empty response")
    assert _is_retryable_error(err) is True


def test_is_retryable_error_invalid_response():
    """Invalid response errors are retryable."""
    err = Exception("Invalid response from LLM")
    assert _is_retryable_error(err) is True


def test_is_retryable_error_not_retryable():
    """Generic errors are not retryable."""
    err = Exception("Something else failed")
    assert _is_retryable_error(err) is False


def test_normalize_raw_verdict_approved():
    """APPROVED verdict is normalized."""
    assert _normalize_raw_verdict("APPROVED") == "APPROVED"
    assert _normalize_raw_verdict("  APPROVED  ") == "APPROVED"


def test_normalize_raw_verdict_issues():
    """ISSUES verdict with content is normalized."""
    raw = "ISSUES:\n- file1: problem"
    assert _normalize_raw_verdict(raw).startswith("ISSUES")


def test_normalize_raw_verdict_empty_returns_issues():
    """Empty verdict returns ISSUES (empty output)."""
    result = _normalize_raw_verdict("")
    assert "ISSUES" in result


def test_normalize_raw_verdict_malformed_returns_issues():
    """Malformed output returns ISSUES with message."""
    result = _normalize_raw_verdict("Random text that is not APPROVED or ISSUES")
    assert "ISSUES" in result
    assert "malformed" in result


def test_format_review_verdict_pydantic():
    """_format_review_verdict extracts verdict from result.pydantic ReviewVerdict."""
    val = ReviewVerdict(verdict="APPROVED", issues=[])
    result_obj = MagicMock(pydantic=val)
    result = _format_review_verdict(result_obj)
    assert result == "APPROVED"


def test_format_review_verdict_issues():
    """_format_review_verdict formats ISSUES with list from pydantic."""
    val = ReviewVerdict(verdict="ISSUES", issues=["a.py: bug", "b.py: typo"])
    result_obj = MagicMock(pydantic=val)
    result = _format_review_verdict(result_obj)
    assert "ISSUES" in result
    assert "a.py" in result


def test_format_review_verdict_issues_empty_list():
    """_format_review_verdict handles ISSUES with empty issues list."""
    val = ReviewVerdict(verdict="ISSUES", issues=[])
    result_obj = MagicMock(pydantic=val)
    result = _format_review_verdict(result_obj)
    assert "ISSUES" in result
    assert "did not list specifics" in result


def test_format_review_verdict_raw_fallback():
    """_format_review_verdict uses raw when pydantic is not ReviewVerdict."""
    result_obj = MagicMock(pydantic=None, raw="APPROVED")
    result = _format_review_verdict(result_obj)
    assert result == "APPROVED"


def test_configure_logging_idempotent():
    """_configure_logging does not add duplicate handlers on second call."""
    import logging

    log = logging.getLogger("code_pipeline")
    _configure_logging(level="WARNING")
    initial_count = len(log.handlers)
    _configure_logging(level="WARNING")
    assert len(log.handlers) == initial_count


def test_fallback_exploration_returns_string(tmp_path):
    """_fallback_exploration returns exploration string with discovered files."""
    (tmp_path / "foo.py").write_text("# test")
    (tmp_path / "bar.json").write_text("{}")
    result = _fallback_exploration(str(tmp_path), "Issue: fix bug")
    # With files present, implementation must find them (os.walk + pattern match)
    assert "foo.py" in result or "bar.json" in result
    assert isinstance(result, str)


def test_log_reviewer_verdict_does_not_raise():
    """_log_reviewer_verdict logs without raising."""
    _log_reviewer_verdict("APPROVED")
    _log_reviewer_verdict("ISSUES:\n- file: problem")


def test_log_implementer_summary_does_not_raise():
    """_log_implementer_summary logs without raising."""
    _log_implementer_summary("Implementation code here")
