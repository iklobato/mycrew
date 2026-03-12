"""Unit tests for code_pipeline.utils."""

import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from code_pipeline.utils import (
    build_repo_context,
    clone_repo_for_issue,
    delete_cloned_repo,
    derive_issue_url,
    detect_github_repo,
    detect_repo_path,
    enrich_repo_context,
    is_git_repo,
    log_exceptions,
    resolve_issue_url,
)


def test_resolve_issue_url_empty_raises():
    """Empty issue_url raises ValueError."""
    with pytest.raises(ValueError, match="issue_url is required and cannot be empty"):
        resolve_issue_url("")
    with pytest.raises(ValueError, match="issue_url is required and cannot be empty"):
        resolve_issue_url("   ")


def test_resolve_issue_url_invalid_format_raises():
    """Invalid URL format raises ValueError with expected message."""
    with pytest.raises(ValueError, match="Invalid GitHub issue URL"):
        resolve_issue_url("https://gitlab.com/owner/repo/issues/123")
    with pytest.raises(ValueError, match="Invalid GitHub issue URL"):
        resolve_issue_url("https://github.com/owner/repo")
    with pytest.raises(ValueError, match="Invalid GitHub issue URL"):
        resolve_issue_url("not-a-url")


def test_resolve_issue_url_no_token_raises():
    """Missing GITHUB_TOKEN raises ValueError."""
    with patch("code_pipeline.utils.get_settings") as mock_get:
        mock_get.return_value.github_token = ""
        with pytest.raises(ValueError, match="GITHUB_TOKEN is required"):
            resolve_issue_url("https://github.com/owner/repo/issues/123")


@patch("code_pipeline.utils.get_settings")
@patch("httpx.Client")
def test_resolve_issue_url_parses_issues_url(mock_client_class, mock_get_settings):
    """Valid issues URL returns correct github_repo, issue_id, task."""
    mock_get_settings.return_value.github_token = "token"
    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"title": "Fix login bug"}
    mock_resp.raise_for_status = MagicMock()
    mock_client.get.return_value = mock_resp
    mock_client_class.return_value.__enter__ = MagicMock(return_value=mock_client)
    mock_client_class.return_value.__exit__ = MagicMock(return_value=False)

    result = resolve_issue_url("https://github.com/owner/repo/issues/123")

    assert result["task"] == "Fix login bug"
    assert result["github_repo"] == "owner/repo"
    assert result["issue_id"] == "#123"
    assert result["issue_url"] == "https://github.com/owner/repo/issues/123"
    assert result["repo_path"] == "."


@patch("code_pipeline.utils.get_settings")
@patch("httpx.Client")
def test_resolve_issue_url_parses_pull_url(mock_client_class, mock_get_settings):
    """Valid PR URL returns issue_id as PR#N."""
    mock_get_settings.return_value.github_token = "token"
    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"title": "Add feature"}
    mock_resp.raise_for_status = MagicMock()
    mock_client.get.return_value = mock_resp
    mock_client_class.return_value.__enter__ = MagicMock(return_value=mock_client)
    mock_client_class.return_value.__exit__ = MagicMock(return_value=False)

    result = resolve_issue_url("https://github.com/owner/repo/pull/456")

    assert result["issue_id"] == "PR#456"
    assert result["github_repo"] == "owner/repo"
    assert result["task"] == "Add feature"


@patch("code_pipeline.utils.get_settings")
@patch("httpx.Client")
def test_resolve_issue_url_api_failure_raises(mock_client_class, mock_get_settings):
    """API 404/401 raises ValueError."""
    mock_get_settings.return_value.github_token = "token"
    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.raise_for_status.side_effect = Exception("404 Not Found")
    mock_client.get.return_value = mock_resp
    mock_client_class.return_value.__enter__ = MagicMock(return_value=mock_client)
    mock_client_class.return_value.__exit__ = MagicMock(return_value=False)

    with pytest.raises(ValueError, match="Failed to fetch issue from GitHub API"):
        resolve_issue_url("https://github.com/owner/repo/issues/999")


@patch("code_pipeline.utils.get_settings")
@patch("httpx.Client")
def test_resolve_issue_url_empty_title_raises(mock_client_class, mock_get_settings):
    """GitHub issue with no title raises ValueError."""
    mock_get_settings.return_value.github_token = "token"
    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"title": ""}
    mock_resp.raise_for_status = MagicMock()
    mock_client.get.return_value = mock_resp
    mock_client_class.return_value.__enter__ = MagicMock(return_value=mock_client)
    mock_client_class.return_value.__exit__ = MagicMock(return_value=False)

    with pytest.raises(ValueError, match="GitHub issue has no title"):
        resolve_issue_url("https://github.com/owner/repo/issues/123")


# ---------------------------------------------------------------------------
# build_repo_context
# ---------------------------------------------------------------------------


def test_build_repo_context_empty_returns_github_hint():
    """All empty inputs still show GitHub auto-detect hint (one line)."""
    # Implementation always adds GitHub line; empty gh shows auto-detect message
    result = build_repo_context()
    assert "GitHub: (auto-detected from git remote when empty)" in result
    assert result == "- GitHub: (auto-detected from git remote when empty)"


def test_build_repo_context_single_field():
    """Single field produces expected line(s)."""
    # repo_path only: also get GitHub auto-detect (empty gh)
    result = build_repo_context(repo_path="/foo")
    assert "- Repository: /foo" in result
    assert "GitHub: (auto-detected" in result
    # github_repo set: only that line (no auto-detect)
    assert build_repo_context(github_repo="a/b") == ("- GitHub: a/b (use for gh -R)")
    # issue_url, test_command: always get GitHub line too (when gh empty)
    result = build_repo_context(issue_url="https://x")
    assert "- Issue URL: https://x" in result
    result = build_repo_context(test_command="pytest")
    assert "- Test command: pytest" in result


def test_build_repo_context_empty_github_shows_auto_detect():
    """Empty github_repo shows auto-detect message."""
    result = build_repo_context(repo_path="/foo", github_repo="")
    assert "GitHub: (auto-detected from git remote when empty)" in result


def test_build_repo_context_multiple_fields():
    """Multiple fields joined by newlines."""
    result = build_repo_context(
        repo_path="/repo",
        github_repo="owner/repo",
        issue_url="https://github.com/owner/repo/issues/1",
        test_command="pytest",
    )
    lines = result.split("\n")
    assert len(lines) == 4
    assert "- Repository: /repo" in result
    assert "- GitHub: owner/repo (use for gh -R)" in result
    assert "- Issue URL: https://github.com/owner/repo/issues/1" in result
    assert "- Test command: pytest" in result


def test_build_repo_context_strips_whitespace():
    """Whitespace-only values are treated as empty."""
    result = build_repo_context(repo_path="  ", github_repo="  ")
    assert "GitHub: (auto-detected" in result
    assert "Repository:" not in result


# ---------------------------------------------------------------------------
# derive_issue_url
# ---------------------------------------------------------------------------


def test_derive_issue_url_empty_inputs():
    """Empty github_repo or issue_id returns empty string."""
    assert derive_issue_url("", "#42") == ""
    assert derive_issue_url("owner/repo", "") == ""


def test_derive_issue_url_extracts_number():
    """Extracts issue number from various formats."""
    assert derive_issue_url("owner/repo", "#42") == (
        "https://github.com/owner/repo/issues/42"
    )
    assert derive_issue_url("owner/repo", "42") == (
        "https://github.com/owner/repo/issues/42"
    )
    assert derive_issue_url("owner/repo", "fixes #123") == (
        "https://github.com/owner/repo/issues/123"
    )
    assert derive_issue_url("owner/repo", "PR#456") == (
        "https://github.com/owner/repo/issues/456"
    )


def test_derive_issue_url_no_number_returns_empty():
    """Issue id with no number returns empty string."""
    assert derive_issue_url("owner/repo", "no numbers") == ""


# ---------------------------------------------------------------------------
# detect_repo_path
# ---------------------------------------------------------------------------


@patch("subprocess.run")
def test_detect_repo_path_git_root(mock_run):
    """When git rev-parse succeeds, returns git root."""
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout="/abs/path/to/repo\n",
    )
    result = detect_repo_path("/some/cwd")
    mock_run.assert_called_once_with(
        ["git", "rev-parse", "--show-toplevel"],
        cwd="/some/cwd",
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert result == "/abs/path/to/repo"


@patch("subprocess.run")
def test_detect_repo_path_git_fails_returns_cwd(mock_run):
    """When git fails or not found, returns absolute cwd."""
    mock_run.side_effect = FileNotFoundError()
    result = detect_repo_path("/my/cwd")
    assert result == "/my/cwd"


@patch("subprocess.run")
def test_detect_repo_path_git_nonzero_returns_cwd(mock_run):
    """When git returns non-zero, returns cwd."""
    mock_run.return_value = MagicMock(returncode=1, stdout="")
    result = detect_repo_path("/my/cwd")
    assert result == "/my/cwd"


@patch("subprocess.run")
def test_detect_repo_path_timeout_returns_cwd(mock_run):
    """When git times out, returns cwd."""
    import subprocess

    mock_run.side_effect = subprocess.TimeoutExpired("git", 5)
    result = detect_repo_path("/my/cwd")
    assert result == "/my/cwd"


# ---------------------------------------------------------------------------
# is_git_repo
# ---------------------------------------------------------------------------


@patch("code_pipeline.utils.subprocess.run")
def test_is_git_repo_true(mock_run, tmp_path):
    """When git rev-parse succeeds, returns True."""
    mock_run.return_value = MagicMock(returncode=0, stdout=f"{tmp_path}\n")
    assert is_git_repo(str(tmp_path)) is True


@patch("code_pipeline.utils.subprocess.run")
def test_is_git_repo_false_empty_dir(tmp_path):
    """Empty temp dir is not a git repo."""
    assert is_git_repo(str(tmp_path)) is False


@patch("code_pipeline.utils.subprocess.run")
def test_is_git_repo_false_git_fails(mock_run, tmp_path):
    """When git fails, returns False."""
    mock_run.return_value = MagicMock(returncode=1, stdout="")
    assert is_git_repo(str(tmp_path)) is False


def test_is_git_repo_nonexistent():
    """Nonexistent path returns False."""
    assert is_git_repo("/nonexistent/path/xyz") is False


# ---------------------------------------------------------------------------
# clone_repo_for_issue
# ---------------------------------------------------------------------------


@patch("subprocess.run")
def test_clone_repo_for_issue_success(mock_run, tmp_path):
    """clone_repo_for_issue clones and returns absolute path."""
    mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
    parent = str(tmp_path / "workspace")
    result = clone_repo_for_issue("owner/repo", parent, "main", "token123")
    assert result == str(tmp_path / "workspace" / "owner-repo")
    mock_run.assert_called_once()
    call_args = mock_run.call_args[0][0]
    assert "clone" in call_args
    assert "--branch" in call_args
    assert "main" in call_args
    assert "--depth" in call_args
    assert "1" in call_args


def test_clone_repo_for_issue_no_token_raises():
    """Empty token raises ValueError."""
    with pytest.raises(ValueError, match="GITHUB_TOKEN is required"):
        clone_repo_for_issue("owner/repo", "/tmp/x", "main", "")


def test_clone_repo_for_issue_invalid_github_repo_raises():
    """Invalid github_repo format raises ValueError."""
    with pytest.raises(ValueError, match="owner/repo format"):
        clone_repo_for_issue("invalid", "/tmp/x", "main", "token")


# ---------------------------------------------------------------------------
# delete_cloned_repo
# ---------------------------------------------------------------------------


def test_delete_cloned_repo_removes_dir():
    """delete_cloned_repo removes directory under /tmp."""
    with tempfile.TemporaryDirectory(dir="/tmp", prefix="code_pipeline_test_") as td:
        subdir = os.path.join(td, "subdir")
        os.makedirs(subdir)
        assert os.path.exists(subdir)
        delete_cloned_repo(td)
        assert not os.path.exists(td)


def test_delete_cloned_repo_refuses_non_tmp(tmp_path):
    """delete_cloned_repo does not delete when path is outside /tmp."""
    out_of_tmp = str(tmp_path.resolve())
    if "/tmp" in out_of_tmp or out_of_tmp.startswith("/var/folders"):
        pytest.skip("tmp_path may be under /tmp on this system")
    if not os.path.exists(out_of_tmp):
        os.makedirs(out_of_tmp)
    delete_cloned_repo(out_of_tmp)
    assert os.path.exists(out_of_tmp)


def test_delete_cloned_repo_empty_path_noop():
    """Empty path does nothing."""
    delete_cloned_repo("")
    delete_cloned_repo("   ")


# ---------------------------------------------------------------------------
# detect_github_repo
# ---------------------------------------------------------------------------


@patch("subprocess.run")
def test_detect_github_repo_https_url(mock_run):
    """HTTPS remote URL returns owner/repo."""
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout="https://github.com/owner/repo.git\n",
    )
    assert detect_github_repo("/path") == "owner/repo"


@patch("subprocess.run")
def test_detect_github_repo_ssh_url(mock_run):
    """SSH remote URL returns owner/repo."""
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout="git@github.com:owner/repo.git\n",
    )
    assert detect_github_repo("/path") == "owner/repo"


@patch("subprocess.run")
def test_detect_github_repo_no_dot_git(mock_run):
    """URL without .git suffix works."""
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout="https://github.com/owner/repo\n",
    )
    assert detect_github_repo("/path") == "owner/repo"


@patch("subprocess.run")
def test_detect_github_repo_non_github_returns_empty(mock_run):
    """Non-GitHub remote returns empty string."""
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout="https://gitlab.com/owner/repo.git\n",
    )
    assert detect_github_repo("/path") == ""


@patch("subprocess.run")
def test_detect_github_repo_git_fails_returns_empty(mock_run):
    """When git fails, returns empty string."""
    mock_run.side_effect = FileNotFoundError()
    assert detect_github_repo("/path") == ""


# ---------------------------------------------------------------------------
# enrich_repo_context
# ---------------------------------------------------------------------------


def test_enrich_repo_context_preserves_non_empty():
    """Non-empty values are preserved."""
    result = enrich_repo_context(
        "/abs/repo",
        github_repo="owner/repo",
        issue_url="https://github.com/owner/repo/issues/1",
    )
    assert result["repo_path"] == "/abs/repo"
    assert result["github_repo"] == "owner/repo"
    assert result["issue_url"] == "https://github.com/owner/repo/issues/1"


@patch("code_pipeline.utils.detect_github_repo")
def test_enrich_repo_context_fills_empty(detect_gh):
    """Empty github_repo is filled from detect_github_repo; issue_url from derive."""
    detect_gh.return_value = "detected/repo"

    result = enrich_repo_context(
        "/abs/repo",
        github_repo="",
        issue_url="",
        issue_id="#42",
    )
    assert result["repo_path"] == "/abs/repo"
    assert result["github_repo"] == "detected/repo"
    assert result["issue_url"] == "https://github.com/detected/repo/issues/42"
    detect_gh.assert_called_once_with("/abs/repo")


def test_log_exceptions_decorator_logs_and_reraises():
    """log_exceptions decorator logs exception and re-raises."""

    @log_exceptions("custom msg")
    def failing():
        raise ValueError("test error")

    with pytest.raises(ValueError, match="test error"):
        failing()


def test_log_exceptions_decorator_passes_through_success():
    """log_exceptions decorator passes return value when no exception."""

    @log_exceptions("custom msg")
    def succeeding():
        return 42

    assert succeeding() == 42


def test_enrich_repo_context_derive_issue_url_when_issue_id():
    """When issue_url empty but issue_id set, derives URL from github_repo."""
    result = enrich_repo_context(
        "/repo",
        github_repo="owner/repo",
        issue_url="",
        issue_id="#99",
    )
    assert result["issue_url"] == "https://github.com/owner/repo/issues/99"
