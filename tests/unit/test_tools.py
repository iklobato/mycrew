"""Unit tests for code_pipeline.tools."""

from code_pipeline.tools.factory import get_tools_for_stage
from code_pipeline.tools.repo_shell_tool import RepoShellTool


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


# ---------------------------------------------------------------------------
# get_github_search_tool
# ---------------------------------------------------------------------------


def test_get_github_search_tool_returns_none_without_token():
    """get_github_search_tool returns None when GITHUB_TOKEN is empty."""
    from unittest.mock import patch

    from code_pipeline.tools.factory import get_github_search_tool

    with patch("code_pipeline.tools.factory.get_settings") as mock_get:
        mock_get.return_value.github_token = ""
        assert get_github_search_tool("owner/repo") is None


def test_get_github_search_tool_returns_none_with_empty_repo(github_token):
    """get_github_search_tool returns None when github_repo is empty."""
    from code_pipeline.tools.factory import get_github_search_tool

    assert get_github_search_tool("") is None
    assert get_github_search_tool("   ") is None


# ---------------------------------------------------------------------------
# get_serper_tool
# ---------------------------------------------------------------------------


def test_get_serper_tool_disabled_returns_none():
    """get_serper_tool returns None when enabled=False."""
    from code_pipeline.tools.factory import get_serper_tool

    assert get_serper_tool(enabled=False) is None


def test_get_serper_tool_no_api_key_returns_none():
    """get_serper_tool returns None when SERPER_API_KEY is not set."""
    from unittest.mock import patch

    from code_pipeline.tools.factory import get_serper_tool

    with patch("code_pipeline.tools.factory.get_settings") as mock_get:
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
    assert "Error" not in result or "Error" not in result[:20]
    # ls may output directory listing or be empty
    assert isinstance(result, str)


def test_repo_shell_tool_nonexistent_dir_returns_error():
    """RepoShellTool returns error when repo_path does not exist."""
    tool = RepoShellTool(repo_path="/nonexistent/path/xyz")
    result = tool._run("ls")
    assert "Error" in result
    assert "not exist" in result or "not a directory" in result
