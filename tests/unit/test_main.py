"""Unit tests for code_pipeline.main."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from code_pipeline.main import (
    PipelineArgs,
    _execute_flow,
    _load_config,
    _parse_args,
    kickoff,
)


def test_pipeline_args_to_flow_inputs_requires_issue_url():
    """Empty issue_url raises ValueError."""
    args = PipelineArgs(issue_url="")
    with pytest.raises(ValueError, match="issue_url is required"):
        args.to_flow_inputs()

    args = PipelineArgs(issue_url="   ")
    with pytest.raises(ValueError, match="issue_url is required"):
        args.to_flow_inputs()


@patch("code_pipeline.main.resolve_issue_url")
def test_pipeline_args_to_flow_inputs_calls_resolve(mock_resolve):
    """to_flow_inputs merges resolved dict with operational params."""
    mock_resolve.return_value = {
        "task": "Fix bug",
        "github_repo": "owner/repo",
        "issue_id": "#42",
        "issue_url": "https://github.com/owner/repo/issues/42",
        "repo_path": ".",
    }

    args = PipelineArgs(
        issue_url="https://github.com/owner/repo/issues/42",
        branch="develop",
        dry_run=True,
        test_command="pytest",
    )
    result = args.to_flow_inputs()

    mock_resolve.assert_called_once_with("https://github.com/owner/repo/issues/42")
    assert result["task"] == "Fix bug"
    assert result["github_repo"] == "owner/repo"
    assert result["issue_id"] == "#42"
    assert result["branch"] == "develop"
    assert result["dry_run"] is True
    assert result["test_command"] == "pytest"
    assert "repo_path" in result


# ---------------------------------------------------------------------------
# PipelineArgs.replace
# ---------------------------------------------------------------------------


def test_pipeline_args_replace_applies_overrides():
    """replace() returns new instance with overrides; None values ignored."""
    base = PipelineArgs(issue_url="x", branch="main", serper_enabled=False)
    out = base.replace(branch="develop", serper_enabled=True)
    assert out is not base
    assert out.issue_url == "x"
    assert out.branch == "develop"
    assert out.serper_enabled is True


def test_pipeline_args_replace_ignores_none():
    """replace() with None does not override existing value."""
    base = PipelineArgs(issue_url="x", branch="main")
    out = base.replace(branch=None)
    assert out.branch == "main"


# ---------------------------------------------------------------------------
# _load_config
# ---------------------------------------------------------------------------


def test_load_config_missing_file_raises():
    """Non-existent config path raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError, match="Config file not found"):
        _load_config("/nonexistent/path.yaml")


def test_load_config_invalid_yaml_structure_raises():
    """YAML that is not a dict raises ValueError."""
    with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
        f.write(b"not a mapping")
        f.flush()
        path = f.name
    try:
        with pytest.raises(ValueError, match="Config must be a YAML object"):
            _load_config(path)
    finally:
        Path(path).unlink(missing_ok=True)


def test_load_config_nested_pipeline_section():
    """Nested pipeline section maps to PipelineArgs fields."""
    with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as f:
        f.write("""
pipeline:
  issue_url: "https://github.com/a/b/issues/1"
  branch: develop
  from_scratch: true
  dry_run: true
  test_command: pytest
""")
        f.flush()
        path = f.name
    try:
        out = _load_config(path)
        assert out["issue_url"] == "https://github.com/a/b/issues/1"
        assert out["branch"] == "develop"
        assert out["from_scratch"] is True
        assert out["dry_run"] is True
        assert out["test_command"] == "pytest"
    finally:
        Path(path).unlink(missing_ok=True)


def test_load_config_flat_structure():
    """Flat (legacy) structure maps keys correctly."""
    with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as f:
        f.write("""
issue_url: "https://github.com/x/y/issues/2"
branch: feature
""")
        f.flush()
        path = f.name
    try:
        out = _load_config(path)
        assert out["issue_url"] == "https://github.com/x/y/issues/2"
        assert out["branch"] == "feature"
    finally:
        Path(path).unlink(missing_ok=True)


def test_load_config_tools_serper_section(monkeypatch):
    """Nested tools.serper extracts serper_enabled."""
    monkeypatch.setenv("SERPER_ENABLED", "")

    with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as f:
        f.write("""
pipeline: {}
tools:
  serper:
    enabled: true
""")
        f.flush()
        path = f.name
    try:
        out = _load_config(path)
        assert out.get("serper_enabled") is True
    finally:
        Path(path).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# _parse_args
# ---------------------------------------------------------------------------


@patch("sys.argv", ["prog"])
def test_parse_args_defaults_without_config():
    """Without config file, returns defaults (empty issue_url)."""
    args = _parse_args()
    assert args.issue_url == ""
    assert args.branch == "main"
    assert args.dry_run is False
    assert args.from_scratch is False
    assert args.test_command == ""


@patch("sys.argv", ["prog", "--issue-url", "https://github.com/a/b/issues/1"])
def test_parse_args_cli_overrides():
    """CLI args override defaults."""
    args = _parse_args()
    assert args.issue_url == "https://github.com/a/b/issues/1"


@patch(
    "sys.argv",
    [
        "prog",
        "--branch",
        "dev",
        "--dry-run",
        "--from-scratch",
        "--test-command",
        "npm test",
    ],
)
def test_parse_args_multiple_cli_overrides():
    """Multiple CLI flags override defaults."""
    args = _parse_args()
    assert args.branch == "dev"
    assert args.dry_run is True
    assert args.from_scratch is True
    assert args.test_command == "npm test"


# ---------------------------------------------------------------------------
# kickoff
# ---------------------------------------------------------------------------


@patch("code_pipeline.main._execute_flow")
@patch("code_pipeline.main.resolve_issue_url")
@patch("sys.argv", ["prog", "--issue-url", "https://github.com/a/b/issues/99"])
def test_kickoff_calls_execute_flow_with_resolved_inputs(mock_resolve, mock_exec):
    """kickoff resolves issue_url and passes flow_inputs to _execute_flow."""
    mock_resolve.return_value = {
        "task": "Fix test",
        "github_repo": "a/b",
        "issue_id": "#99",
        "issue_url": "https://github.com/a/b/issues/99",
        "repo_path": ".",
    }
    mock_exec.return_value = "flow-result"

    result = kickoff()

    mock_exec.assert_called_once()
    call_inputs = mock_exec.call_args[0][0]
    assert call_inputs["task"] == "Fix test"
    assert call_inputs["github_repo"] == "a/b"
    assert call_inputs["issue_id"] == "#99"
    assert "repo_context" in call_inputs
    assert result == "flow-result"


# ---------------------------------------------------------------------------
# _execute_flow
# ---------------------------------------------------------------------------


@patch("code_pipeline.main.CodePipelineFlow")
def test_execute_flow_kickoffs_flow_with_inputs(mock_flow_class):
    """_execute_flow creates flow and calls kickoff with inputs."""
    mock_flow = MagicMock()
    mock_flow.flow_id = "test-flow-id"
    mock_flow.kickoff.return_value = "flow-output"
    mock_flow_class.return_value = mock_flow

    inputs = {
        "repo_path": "/tmp/repo",
        "task": "Do something",
        "branch": "main",
        "from_scratch": True,
    }
    result = _execute_flow(inputs)

    mock_flow_class.assert_called_once()
    mock_flow.kickoff.assert_called_once()
    call_inputs = mock_flow.kickoff.call_args[1]["inputs"]
    assert call_inputs["repo_path"] == "/tmp/repo"
    assert call_inputs["task"] == "Do something"
    assert result == "flow-output"
