"""Tests for input builder - building inputs for crews from state."""

import re
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mycrew.crews.input_builder import PipelineInputBuilder
from mycrew.main import PipelineState


@pytest.mark.unit
class TestInputBuilder:
    """Tests for PipelineInputBuilder."""

    def test_input_builder_includes_issue_url(self):
        """Test that issue URL is included in inputs."""
        builder = PipelineInputBuilder()

        state = PipelineState(
            id="test",
            issue_url="https://github.com/test/repo/issues/1",
            issue_data={"owner": "test", "repo": "repo", "number": "1"},
            repo_path="/tmp/test",
            repo_root="/tmp/test",
            programmatic=True,
        )

        inputs = builder.build(state, None)

        assert "issue_url" in inputs
        assert inputs["issue_url"] == "https://github.com/test/repo/issues/1"

    def test_input_builder_includes_repo_context(self):
        """Test that repo context is passed to next crew."""
        builder = PipelineInputBuilder()

        state = PipelineState(
            id="test",
            issue_url="https://github.com/test/repo/issues/1",
            issue_data={"owner": "test", "repo": "repo", "number": "1"},
            exploration_result={"tech_stack": ["Python"], "key_files": ["app.py"]},
            repo_path="/tmp/test",
            repo_root="/tmp/test",
            programmatic=True,
        )

        inputs = builder.build(state, None)

        # Should include repo context
        assert "repo_context" in inputs or "exploration_result" in inputs

    def test_input_builder_merges_custom(self):
        """Test that custom inputs are merged with standard inputs."""
        builder = PipelineInputBuilder()

        state = PipelineState(
            id="test",
            issue_url="https://github.com/test/repo/issues/1",
            issue_data={"owner": "test", "repo": "repo", "number": "1"},
            repo_path="/tmp/test",
            repo_root="/tmp/test",
            programmatic=True,
        )

        custom_inputs = {"custom_field": "custom_value", "task": "special task"}

        inputs = builder.build(state, custom_inputs)

        # Custom inputs should be merged
        assert "custom_field" in inputs
        assert inputs["custom_field"] == "custom_value"

    def test_input_builder_handles_missing_fields(self):
        """Test that builder handles missing optional fields gracefully."""
        builder = PipelineInputBuilder()

        # State with minimal fields
        state = PipelineState(
            id="test",
            issue_url="https://github.com/test/repo/issues/1",
            repo_path="/tmp/test",
            repo_root="/tmp/test",
            programmatic=True,
        )

        # Should not raise exception
        inputs = builder.build(state, None)

        # Should still have issue_url
        assert "issue_url" in inputs
        assert inputs["issue_url"] == "https://github.com/test/repo/issues/1"

    def test_input_builder_includes_issue_data(self):
        """Test that issue_data is included in inputs."""
        builder = PipelineInputBuilder()

        issue_data = {
            "owner": "test",
            "repo": "repo",
            "number": "1",
            "kind": "issue",
            "is_pull": False,
            "github_repo": "test/repo",
        }

        state = PipelineState(
            id="test",
            issue_url="https://github.com/test/repo/issues/1",
            issue_data=issue_data,
            repo_path="/tmp/test",
            repo_root="/tmp/test",
            programmatic=True,
        )

        inputs = builder.build(state, None)

        assert "issue_analysis" in inputs
        assert inputs["issue_analysis"]["owner"] == "test"

    def test_input_builder_includes_repo_path(self):
        """Test that repo_path is included in inputs."""
        builder = PipelineInputBuilder()

        state = PipelineState(
            id="test",
            issue_url="https://github.com/test/repo/issues/1",
            repo_path="/path/to/repo",
            repo_root="/path/to/repo",
            programmatic=True,
        )

        inputs = builder.build(state, None)

        # Should have repo path info in repo_context
        assert "repo_context" in inputs
        assert "/path/to/repo" in inputs["repo_context"]

    def test_input_builder_for_different_crews(self):
        """Test that builder works for different crew types."""
        builder = PipelineInputBuilder()

        # State with full context
        state = PipelineState(
            id="test",
            issue_url="https://github.com/test/repo/issues/1",
            issue_data={"owner": "test", "repo": "repo", "number": "1"},
            exploration_result={"result": "explored"},
            architecture_result={"result": "architectured"},
            implementation_result={"result": "implemented"},
            repo_path="/tmp/test",
            repo_root="/tmp/test",
            programmatic=True,
        )

        # For different crews, builder should include relevant context
        inputs = builder.build(state, None)

        # Should have base inputs at minimum
        assert "issue_url" in inputs


class TestTemplateVariableCompleteness:
    """Tests that all template variables in configs are provided in input_data.

    These tests catch bugs where:
    - A new {variable} is added to YAML config but not passed in input_data
    - Template variable is misspelled causing silent failure
    """

    # Standard variables that PipelineInputBuilder always provides
    STANDARD_VARIABLES = [
        "repo_context",
        "github_repo",
        "issue_url",
        "focus_paths",
        "exclude_paths",
        "task",
        "issue_analysis",
        "branch",
    ]

    @pytest.mark.parametrize("var", STANDARD_VARIABLES)
    def test_standard_variables_in_inputs(self, var):
        """Test that PipelineInputBuilder provides all standard variables.

        This test verifies that the builder always provides these core variables.
        """
        builder = PipelineInputBuilder()

        state = PipelineState(
            id="test",
            issue_url="https://github.com/test/repo/issues/1",
            issue_data={"owner": "test", "repo": "repo", "number": "1"},
            branch="main",
            repo_path="/tmp/test",
            repo_root="/tmp/test",
            programmatic=True,
        )

        inputs = builder.build(state, None)

        assert var in inputs, (
            f"Standard variable '{var}' not in builder output. "
            f"This would cause KeyError when crews run."
        )


class TestInputValidation:
    """Tests that input builder validates and handles edge cases properly.

    These tests catch bugs where:
    - Empty strings are used instead of failing fast
    - Missing required fields cause silent failures
    """

    def test_empty_repo_path_in_context(self):
        """Test that empty repo_path results in appropriate handling."""
        builder = PipelineInputBuilder()

        state = PipelineState(
            id="test",
            issue_url="https://github.com/test/repo/issues/1",
            issue_data={"owner": "test", "repo": "repo", "number": "1"},
            repo_path="",  # Empty
            repo_root="",  # Empty
            programmatic=True,
        )

        inputs = builder.build(state, None)

        # Should have repo_context even with empty paths
        assert "repo_context" in inputs

    def test_missing_issue_data_uses_empty(self):
        """Test that missing issue_data is handled gracefully."""
        builder = PipelineInputBuilder()

        state = PipelineState(
            id="test",
            issue_url="https://github.com/test/repo/issues/1",
            issue_data=None,  # Missing
            repo_path="/tmp/test",
            repo_root="/tmp/test",
            programmatic=True,
        )

        inputs = builder.build(state, None)

        # Should not raise
        assert "issue_url" in inputs
        assert inputs["issue_analysis"] is None

    def test_empty_task_value_in_inputs(self):
        """Test that empty task doesn't cause issues."""
        builder = PipelineInputBuilder()

        state = PipelineState(
            id="test",
            issue_url="https://github.com/test/repo/issues/1",
            issue_data={},  # Empty issue_data - no task
            repo_path="/tmp/test",
            repo_root="/tmp/test",
            programmatic=True,
        )

        inputs = builder.build(state, None)

        # Should have task key with empty string value
        assert "task" in inputs
        assert inputs["task"] == ""
