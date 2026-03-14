"""Unit tests for mycrew.tools."""

from unittest.mock import MagicMock, patch

import pytest

from mycrew.tools.factory import (
    get_github_search_tool,
    get_scrape_website_tool,
    get_tools_for_stage,
)
from mycrew.tools.noop_tool import NoOpTool
from mycrew.tools.repo_file_writer_tool import RepoFileWriterTool
from mycrew.tools.repo_shell_tool import RepoShellTool


# ---------------------------------------------------------------------------
# get_tools_for_stage
# ---------------------------------------------------------------------------


def test_get_tools_for_stage_implement_returns_shell_and_file_writer():
    """implement stage returns RepoShellTool and RepoFileWriterTool."""
    tools = get_tools_for_stage("implement", "/tmp/repo")
    tool_types = [type(t).__name__ for t in tools]
    assert "RepoShellTool" in tool_types
    assert "RepoFileWriterTool" in tool_types


def test_get_tools_for_stage_commit_returns_shell_only():
    """commit stage returns only RepoShellTool."""
    tools = get_tools_for_stage("commit", "/tmp/repo")
    assert len(tools) == 1
    assert isinstance(tools[0], RepoShellTool)


def test_get_tools_for_stage_publish_returns_create_pr_and_shell():
    """publish stage returns CreatePRTool and RepoShellTool."""
    tools = get_tools_for_stage("publish", "/tmp/repo")
    tool_types = [type(t).__name__ for t in tools]
    assert "CreatePRTool" in tool_types
    assert "RepoShellTool" in tool_types


def test_get_tools_for_stage_explore_returns_shell():
    """explore stage returns at least RepoShellTool."""
    tools = get_tools_for_stage("explore", "/tmp/repo")
    tool_types = [type(t).__name__ for t in tools]
    assert "RepoShellTool" in tool_types


def test_get_tools_for_stage_plan_returns_shell():
    """plan stage returns at least RepoShellTool."""
    tools = get_tools_for_stage("plan", "/tmp/repo")
    tool_types = [type(t).__name__ for t in tools]
    assert "RepoShellTool" in tool_types


def test_get_tools_for_stage_unknown_returns_empty():
    """Unknown stage returns empty list."""
    tools = get_tools_for_stage("unknown_stage_xyz", "/tmp/repo")
    assert tools == []


def test_get_tools_for_stage_analyze_issue_returns_tools(github_token):
    """analyze_issue stage returns ScrapeWebsiteTool and RepoShellTool (github when token set)."""
    tools = get_tools_for_stage("analyze_issue", "/tmp/repo")
    tool_names = [type(t).__name__ for t in tools]
    assert "RepoShellTool" in tool_names
    assert "ScrapeWebsiteTool" in tool_names


def test_get_tools_for_stage_review_returns_shell():
    """review stage returns RepoShellTool."""
    tools = get_tools_for_stage("review", "/tmp/repo")
    assert len(tools) >= 1
    assert any(isinstance(t, RepoShellTool) for t in tools)


# ---------------------------------------------------------------------------
# get_github_search_tool
# ---------------------------------------------------------------------------


def test_get_github_search_tool_returns_none_without_token():
    """get_github_search_tool returns None when GITHUB_TOKEN is empty."""
    with patch("mycrew.tools.factory.get_settings") as mock_get:
        mock_get.return_value.github_token = ""
        assert get_github_search_tool("owner/repo") is None


def test_get_github_search_tool_returns_none_with_empty_repo(github_token):
    """get_github_search_tool returns None when github_repo is empty."""
    assert get_github_search_tool("") is None
    assert get_github_search_tool("   ") is None


# ---------------------------------------------------------------------------
# get_serper_tool
# ---------------------------------------------------------------------------


def test_get_serper_tool_disabled_returns_none():
    """get_serper_tool returns None when enabled=False."""
    from mycrew.tools.factory import get_serper_tool

    assert get_serper_tool(enabled=False) is None


def test_get_serper_tool_no_api_key_returns_none():
    """get_serper_tool returns None when SERPER_API_KEY is not set."""
    from mycrew.tools.factory import get_serper_tool

    with patch("mycrew.tools.factory.get_settings") as mock_get:
        mock_get.return_value.serper_api_key = ""
        assert get_serper_tool(enabled=True) is None


# ---------------------------------------------------------------------------
# RepoShellTool
# ---------------------------------------------------------------------------


def test_repo_shell_tool_empty_repo_path_returns_error():
    """RepoShellTool returns error when repo_path is not set."""
    tool = RepoShellTool(repo_path="")
    result = tool._run("ls")
    assert "Error: repo_path is not set" in result


def test_repo_shell_tool_empty_command_returns_error(tmp_path):
    """RepoShellTool returns error for empty command."""
    tool = RepoShellTool(repo_path=str(tmp_path))
    result = tool._run("   ")
    assert "Error: empty command" in result


def test_repo_shell_tool_blocks_dangerous_commands(tmp_path):
    """RepoShellTool blocks rm -rf / and similar dangerous patterns."""
    tool = RepoShellTool(repo_path=str(tmp_path))
    result = tool._run("rm -rf /")
    assert "Error: command blocked" in result


def test_repo_shell_tool_safe_command_succeeds(tmp_path):
    """RepoShellTool runs safe commands (ls) successfully."""
    tool = RepoShellTool(repo_path=str(tmp_path))
    result = tool._run("ls")
    # Tool errors use "Error: " prefix; command output may contain "error" (e.g. stderr)
    assert not result.startswith("Error: ")
    assert isinstance(result, str)


def test_repo_shell_tool_nonexistent_dir_returns_error():
    """RepoShellTool returns error when repo_path does not exist."""
    tool = RepoShellTool(repo_path="/nonexistent/path/xyz")
    result = tool._run("ls")
    assert "Error" in result
    assert "not exist" in result or "not a directory" in result


# ---------------------------------------------------------------------------
# RepoFileWriterTool
# ---------------------------------------------------------------------------


def test_repo_file_writer_empty_repo_path_returns_error():
    """RepoFileWriterTool returns error when repo_path not set."""
    tool = RepoFileWriterTool(repo_path="")
    result = tool._run("file.txt", "content")
    assert "Error: repo_path is not set" in result


def test_repo_file_writer_nonexistent_repo_returns_error():
    """RepoFileWriterTool returns error when repo_path does not exist."""
    tool = RepoFileWriterTool(repo_path="/nonexistent/repo")
    result = tool._run("file.txt", "content")
    assert "Error" in result
    assert "not exist" in result


def test_repo_file_writer_creates_file(tmp_path):
    """RepoFileWriterTool creates new file when overwrite=False."""
    tool = RepoFileWriterTool(repo_path=str(tmp_path))
    result = tool._run("newfile.txt", "hello world")
    assert "Error" not in result
    assert (tmp_path / "newfile.txt").read_text() == "hello world"


def test_repo_file_writer_overwrite_false_existing_returns_error(tmp_path):
    """RepoFileWriterTool returns error when file exists and overwrite=False."""
    (tmp_path / "existing.txt").write_text("old")
    tool = RepoFileWriterTool(repo_path=str(tmp_path))
    result = tool._run("existing.txt", "new content", overwrite=False)
    assert "already exists" in result
    assert (tmp_path / "existing.txt").read_text() == "old"


def test_repo_file_writer_overwrite_true_modifies_file(tmp_path):
    """RepoFileWriterTool overwrites when overwrite=True."""
    (tmp_path / "modify.txt").write_text("old")
    tool = RepoFileWriterTool(repo_path=str(tmp_path))
    result = tool._run("modify.txt", "new content", overwrite=True)
    assert "Error" not in result
    assert (tmp_path / "modify.txt").read_text() == "new content"


def test_repo_file_writer_strtobool_overwrite_strings(tmp_path):
    """RepoFileWriterTool accepts overwrite as y/yes/true/1 and overwrites file."""
    tool = RepoFileWriterTool(repo_path=str(tmp_path))
    (tmp_path / "f.txt").write_text("x")
    for val in ("yes", "true", "1", "y"):
        result = tool._run("f.txt", "updated", overwrite=val)
        assert "Error" not in result
    assert (tmp_path / "f.txt").read_text() == "updated"


def test_repo_file_writer_path_escaping_returns_error(tmp_path):
    """RepoFileWriterTool rejects path that escapes repo."""
    tool = RepoFileWriterTool(repo_path=str(tmp_path))
    result = tool._run("../../../etc/passwd", "bad")
    assert "Error" in result
    assert "escapes" in result


# ---------------------------------------------------------------------------
# CreatePRTool / _make_pr_body
# ---------------------------------------------------------------------------


def test_make_pr_body_includes_task_and_issue():
    """_make_pr_body includes task, issue_url, issue_id."""
    from mycrew.tools.create_pr_tool import _make_pr_body

    body = _make_pr_body(
        task="Fix bug",
        implementation="",
        issue_url="https://github.com/o/r/issues/1",
        issue_id="#1",
    )
    assert "## Task" in body
    assert "Fix bug" in body
    assert "**Issue:**" in body
    assert "**Closes:** #1" in body
    assert "_Generated by mycrew_" in body


def test_make_pr_body_approved_verdict_adds_checkmark():
    """_make_pr_body adds APPROVED section when verdict starts with APPROVED."""
    from mycrew.tools.create_pr_tool import _make_pr_body

    body = _make_pr_body(
        task="X",
        implementation="",
        review_verdict="APPROVED",
    )
    assert "## Review" in body
    assert "APPROVED" in body


def test_create_pr_tool_empty_github_repo_returns_error(tmp_path):
    """CreatePRTool returns error when github_repo empty."""
    from mycrew.tools.create_pr_tool import CreatePRTool

    tool = CreatePRTool(repo_path=str(tmp_path))
    result = tool._run(
        feature_branch="feat-1",
        base_branch="main",
        task="Task",
        github_repo="",
    )
    assert "Error" in result
    assert "github_repo" in result


# ---------------------------------------------------------------------------
# GitHubAPISearchTool
# ---------------------------------------------------------------------------


@patch("mycrew.tools.github_api_search_tool.requests.get")
def test_github_api_search_tool_returns_formatted_results(mock_get, github_token):
    """GitHubAPISearchTool returns formatted results from API."""
    from mycrew.tools.github_api_search_tool import GitHubAPISearchTool

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {
        "items": [
            {
                "path": "src/foo.py",
                "name": "foo.py",
                "html_url": "https://github.com/o/r/blob/foo.py",
                "repository": {"full_name": "owner/repo"},
                "score": 1.0,
            },
        ],
    }
    mock_get.return_value = mock_resp

    tool = GitHubAPISearchTool(github_token="token", github_repo="owner/repo")
    result = tool._run("query", "code")

    assert "foo.py" in result
    assert "src/foo.py" in result
    mock_get.assert_called()


@patch("mycrew.tools.github_api_search_tool.requests.get")
def test_github_api_search_tool_issues_content_type(mock_get, github_token):
    """GitHubAPISearchTool search issues returns formatted results."""
    from mycrew.tools.github_api_search_tool import GitHubAPISearchTool

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {
        "items": [
            {
                "title": "Bug in login",
                "number": 42,
                "state": "open",
                "html_url": "https://github.com/o/r/issues/42",
                "body": "Description",
                "score": 1.0,
            },
        ],
    }
    mock_get.return_value = mock_resp

    tool = GitHubAPISearchTool(github_token="token", github_repo="owner/repo")
    result = tool._run("login bug", "issues")
    assert "Bug in login" in result
    assert "#42" in result


@patch("mycrew.tools.github_api_search_tool.requests.get")
def test_github_api_search_tool_no_results(mock_get, github_token):
    """GitHubAPISearchTool returns no results message when empty."""
    from mycrew.tools.github_api_search_tool import GitHubAPISearchTool

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {"items": []}
    mock_get.return_value = mock_resp

    tool = GitHubAPISearchTool(github_token="token", github_repo="owner/repo")
    result = tool._run("nonexistent", "code")
    assert "No results" in result


@patch("mycrew.tools.github_api_search_tool.requests.get")
def test_github_api_search_tool_exception_returns_error_message(mock_get, github_token):
    """GitHubAPISearchTool returns error message when API fails."""
    from mycrew.tools.github_api_search_tool import GitHubAPISearchTool

    mock_get.side_effect = Exception("Connection refused")

    tool = GitHubAPISearchTool(github_token="token", github_repo="owner/repo")
    result = tool._run("query", "code")
    assert "failed" in result.lower() or "error" in result.lower()


def test_github_api_search_tool_invalid_repo_raises():
    """GitHubAPISearchTool raises for invalid repo format."""
    from mycrew.tools.github_api_search_tool import GitHubAPISearchTool

    with pytest.raises(ValueError, match="Invalid repository format"):
        GitHubAPISearchTool(github_token="t", github_repo="no-slash")


# ---------------------------------------------------------------------------
# NoOpTool
# ---------------------------------------------------------------------------


def test_noop_tool_returns_disabled_message():
    """NoOpTool._run returns tool disabled message."""
    tool = NoOpTool()
    assert tool._run() == "Tool disabled."
    assert tool._run(query="anything") == "Tool disabled."


# ---------------------------------------------------------------------------
# get_scrape_website_tool
# ---------------------------------------------------------------------------


def test_get_scrape_website_tool_returns_tool():
    """get_scrape_website_tool returns ScrapeWebsiteTool."""
    tool = get_scrape_website_tool()
    assert tool is not None
    assert "Scrape" in type(tool).__name__
