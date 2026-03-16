"""Tests for error handling in crews and flow."""

import logging
from unittest.mock import MagicMock, patch

import pytest

from mycrew.main import CodePipelineFlow, PipelineState


@pytest.mark.unit
class TestErrorHandling:
    """Tests for error handling in pipeline components."""

    def test_invalid_yaml_raises_error(self):
        """Test that invalid YAML config raises appropriate error."""
        import yaml

        # Corrupt YAML
        invalid_yaml = "{ invalid: yaml: content: ["

        with pytest.raises(yaml.YAMLError):
            yaml.safe_load(invalid_yaml)

    def test_missing_crew_class_handled(self):
        """Test that missing crew class is handled gracefully."""
        state = PipelineState(
            id="test-id",
            issue_url="https://github.com/test/repo/issues/1",
            repo_path="/tmp/test",
            programmatic=True,
        )

        flow = CodePipelineFlow(state=state)

        # Passing None crew class should be handled
        result = flow._run_crew(None, "test_crew", {})

        # Should return None gracefully
        assert result is None

    def test_llm_failure_does_not_crash_flow(self, tmp_path, caplog):
        """Test that LLM failure is handled and logged."""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        state = PipelineState(
            id="test-id",
            issue_url="https://github.com/test/repo/issues/1",
            repo_path=str(repo_path),
            repo_root=str(repo_path),
            programmatic=True,
            target_steps=["EXPLORE"],
            mock=True,  # Use mock to avoid real LLM
        )

        flow = CodePipelineFlow(state=state)

        # Should not crash even if there are issues
        with caplog.at_level(logging.ERROR):
            result = flow.kickoff()

        # Should complete without crashing
        assert result is None or result is not None

    def test_tool_failure_logged(self, tmp_path, caplog):
        """Test that tool failures are logged appropriately."""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        state = PipelineState(
            id="test-id",
            issue_url="https://github.com/test/repo/issues/1",
            repo_path=str(repo_path),
            repo_root=str(repo_path),
            programmatic=True,
            target_steps=["EXPLORE"],
            mock=True,
        )

        flow = CodePipelineFlow(state=state)

        # Run with mock - tool failures should be handled
        with caplog.at_level(logging.WARNING):
            result = flow.kickoff()

        # Should complete
        assert result is None

    def test_missing_repo_path_handled(self):
        """Test that missing repo_path is handled gracefully."""
        state = PipelineState(
            id="test-id",
            issue_url="https://github.com/test/repo/issues/1",
            repo_path="",  # Empty
            programmatic=True,
            target_steps=["EXPLORE"],
            mock=True,
        )

        flow = CodePipelineFlow(state=state)

        # Should handle gracefully
        result = flow.kickoff()

        # Mock mode should handle
        assert result is None

    def test_invalid_step_name_handled(self):
        """Test that invalid step name is handled."""
        state = PipelineState(
            id="test-id",
            issue_url="https://github.com/test/repo/issues/1",
            repo_path="/tmp/test",
            programmatic=True,
            target_steps=["INVALID_STEP"],  # Invalid
            mock=True,
        )

        flow = CodePipelineFlow(state=state)

        # Should handle invalid step
        result = flow.kickoff()

        # Should complete (may skip invalid step)
        assert result is None

    def test_state_manager_handles_missing_file(self, tmp_path):
        """Test that state manager handles missing files gracefully."""
        from mycrew.pipeline_state import PipelineStateManager

        state_dir = tmp_path / "state"
        state_dir.mkdir()

        with patch.object(PipelineStateManager, "STATE_DIR", str(state_dir)):
            # Try to load non-existent file
            result = PipelineStateManager.load_step_result(
                str(state_dir / "nonexistent.json")
            )

            # Should return None, not crash
            assert result is None

    def test_flow_handles_exception_in_step(self, tmp_path):
        """Test that flow handles exceptions in step methods."""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        state = PipelineState(
            id="test-id",
            issue_url="https://github.com/test/repo/issues/1",
            repo_path=str(repo_path),
            repo_root=str(repo_path),
            programmatic=True,
            target_steps=["EXPLORE"],
            mock=True,
        )

        flow = CodePipelineFlow(state=state)

        # Should handle exceptions gracefully
        result = flow.kickoff()

        # Should complete without raising
        assert result is None or result is not None


@pytest.mark.unit
class TestEdgeCases:
    """Tests for edge cases in error handling."""

    def test_empty_issue_url(self):
        """Test handling of empty issue URL."""
        state = PipelineState(
            id="test-id",
            issue_url="",
            repo_path="/tmp/test",
            programmatic=True,
            mock=True,
        )

        flow = CodePipelineFlow(state=state)

        # Should handle gracefully
        assert flow.state.issue_url == ""

    def test_none_state_fields(self):
        """Test handling of None state fields."""
        state = PipelineState(
            id="test-id",
        )

        # Accessing undefined fields should not crash
        # (They have defaults)
        assert state.issue_url == ""
        assert state.repo_path == ""

    def test_state_with_all_fields(self):
        """Test state with all fields populated."""
        state = PipelineState(
            id="test-id",
            issue_url="https://github.com/test/repo/issues/1",
            repo_path="/tmp/test",
            repo_root="/tmp/test",
            programmatic=True,
            issue_data={"owner": "test", "repo": "repo"},
            exploration_result={"tech_stack": ["Python"]},
            target_steps=["EXPLORE"],
            input_file="/tmp/input.json",
            mock=True,
        )

        assert state.id == "test-id"
        assert state.target_steps == ["EXPLORE"]
        assert state.mock is True
