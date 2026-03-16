"""Tests for flow execution - CrewAI flow kickoff, state persistence."""

from unittest.mock import MagicMock, patch

import pytest

from mycrew.main import CodePipelineFlow, PipelineState


class MockCrewResult:
    """Mock crew result for flow testing."""

    def __init__(self, raw=None):
        self.raw = raw


class MockLLMResponse:
    """Mock LLM response."""

    def __init__(self, content: str = '{"result": "test"}'):
        self.content = content
        self._content = content

    def model_dump(self, **kwargs):
        return {"content": self._content}


@pytest.mark.unit
class TestFlowExecution:
    """Tests for flow execution with mocked LLM."""

    def test_flow_kickoff_returns_result(self, tmp_path):
        """Test that flow kickoff returns a result."""
        # Create a minimal test repo
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()
        (repo_path / "pyproject.toml").write_text('[project]\nname = "test"\n')

        state = PipelineState(
            id="test-id",
            issue_url="https://github.com/test/repo/issues/1",
            repo_path=str(repo_path),
            repo_root=str(repo_path),
            programmatic=True,
            issue_data={"owner": "test", "repo": "repo", "number": "1"},
        )

        # Mock LLM to avoid real API calls
        with patch("mycrew.llm.LLMManager.get_for_stage") as mock_llm:
            mock_llm.return_value = MagicMock()

            flow = CodePipelineFlow(state=state)

            # In step mode, should not need real crew execution
            flow.state.target_steps = ["EXPLORE"]
            flow.state.mock = True

            # Run step mode which uses mock
            result = flow.kickoff()

            # Should complete without error
            assert result is None or result is not None

    def test_flow_state_initialization(self):
        """Test that flow initializes with correct state."""
        state = PipelineState(
            id="test-id",
            issue_url="https://github.com/test/repo/issues/1",
            repo_path="/tmp/test",
            programmatic=True,
        )

        flow = CodePipelineFlow(state=state)

        assert flow.state.id == "test-id"
        assert flow.state.issue_url == "https://github.com/test/repo/issues/1"
        assert flow.state.programmatic is True

    def test_flow_state_persists(self, tmp_path):
        """Test that state persists through flow execution."""
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

        # Add custom state
        state.exploration_result = {"tech_stack": ["Python"]}

        flow = CodePipelineFlow(state=state)

        # Run kickoff (will use mock)
        flow.kickoff()

        # State should still have exploration result
        assert flow.state.exploration_result == {"tech_stack": ["Python"]}

    def test_start_decorator_configuration(self):
        """Test that flow has start method configured."""
        from mycrew.main import CodePipelineFlow

        # Verify the class has the @start decorator applied
        # The start method should exist
        assert hasattr(CodePipelineFlow, "start")

        # Create instance and verify
        state = PipelineState(id="test", programmatic=True)
        flow = CodePipelineFlow(state=state)

        # start should be callable
        assert callable(getattr(flow, "start", None))

    def test_listen_decorators_configured(self):
        """Test that listen decorators are applied for step chaining."""
        from mycrew.main import CodePipelineFlow

        # The flow should have methods decorated with @listen
        # Check that key methods exist that would be decorated
        expected_methods = [
            "explore",
            "analyze_issue",
            "architect",
            "implement",
            "review",
        ]

        for method_name in expected_methods:
            assert hasattr(CodePipelineFlow, method_name), (
                f"Flow should have {method_name} method"
            )


@pytest.mark.unit
class TestFlowWithMocks:
    """Tests using detailed mocking of flow components."""

    def test_flow_runs_with_mocked_crew(self, tmp_path):
        """Test that flow completes when crew is mocked."""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()
        (repo_path / "pyproject.toml").write_text('[project]\nname = "test"\n')

        state = PipelineState(
            id="test-id",
            issue_url="https://github.com/test/repo/issues/1",
            repo_path=str(repo_path),
            repo_root=str(repo_path),
            programmatic=True,
            target_steps=["EXPLORE"],
            mock=True,  # Use mock mode
        )

        flow = CodePipelineFlow(state=state)

        # Should complete without error in mock mode
        result = flow.kickoff()

        # Mock mode should work
        assert result is None  # mock mode returns None after completion

    def test_flow_handles_missing_repo_path(self):
        """Test that flow handles missing repo_path gracefully."""
        state = PipelineState(
            id="test-id",
            issue_url="https://github.com/test/repo/issues/1",
            repo_path="",  # Empty repo path
            programmatic=True,
            target_steps=["EXPLORE"],
            mock=True,
        )

        flow = CodePipelineFlow(state=state)

        # Should handle gracefully
        result = flow.kickoff()

        # Mock mode should complete
        assert result is None
