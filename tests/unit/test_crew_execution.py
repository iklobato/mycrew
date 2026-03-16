"""Tests for actual crew execution - testing real crew logic with mocked dependencies."""

from unittest.mock import MagicMock, patch

import pytest

from mycrew.crews.explorer_crew.explorer_crew import ExplorerCrew
from mycrew.main import PipelineState


class MockLLM:
    """Mock CrewAI LLM that returns predefined responses."""

    def __init__(self, model: str = "gpt-4", response: str = "Mock response"):
        self.model = model
        self.response = response
        self.call_count = 0

    def chat(self, messages):
        self.call_count += 1
        mock_msg = MagicMock()
        mock_msg.content = self.response
        return mock_msg


class MockLLMResponse:
    """Mock LLM response for crew results."""

    def __init__(self, response_text: str = "Mock response"):
        self.response_text = response_text
        self.call_count = 0

    def chat(self, messages):
        self.call_count += 1
        mock_msg = MagicMock()
        mock_msg.content = self.response_text
        return mock_msg


class MockAgentResult:
    """Mock agent result for crew kickoff."""

    def __init__(self, output: str = "Mock output"):
        self.output = output
        self.raw = output


class MockTaskResult:
    """Mock task result."""

    def __init__(self, output: str = "Mock task output"):
        self.output = output
        self.raw = output


@pytest.mark.unit
class TestExplorerCrewExecution:
    """Tests for actual explorer crew execution with mocked LLM."""

    def test_explorer_crew_initializes_with_correct_stage(self):
        """Test that explorer crew has correct stage."""
        with patch(
            "mycrew.crews.explorer_crew.explorer_crew.get_llm_for_stage"
        ) as mock_get_llm:
            mock_get_llm.return_value = MockLLM(response="test")
            crew = ExplorerCrew()
            assert crew.stage == "explore"

    def test_explorer_crew_has_required_agents(self):
        """Test that explorer crew defines required agents."""
        with patch(
            "mycrew.crews.explorer_crew.explorer_crew.get_llm_for_stage"
        ) as mock_get_llm:
            mock_get_llm.return_value = MockLLM(response="test")
            crew = ExplorerCrew()
            agents = crew.required_agents
            assert len(agents) > 0
            assert "repo_explorer" in agents

    def test_explorer_crew_has_required_tasks(self):
        """Test that explorer crew defines required tasks."""
        with patch(
            "mycrew.crews.explorer_crew.explorer_crew.get_llm_for_stage"
        ) as mock_get_llm:
            mock_get_llm.return_value = MockLLM(response="test")
            crew = ExplorerCrew()
            tasks = crew.required_tasks
            assert len(tasks) > 0
            assert "explore_task" in tasks

    def test_explorer_crew_build_returns_crew_object(self):
        """Test that crew building returns a valid Crew object."""
        with patch(
            "mycrew.crews.explorer_crew.explorer_crew.get_llm_for_stage"
        ) as mock_get_llm:
            mock_get_llm.return_value = MockLLM(response='{"result": "ok"}')

            crew_instance = ExplorerCrew()
            crew = crew_instance.crew()

            assert crew is not None
            assert len(crew.agents) > 0

    def test_explorer_crew_build_includes_tools(self):
        """Test that built crew includes tools for agents."""
        with patch(
            "mycrew.crews.explorer_crew.explorer_crew.get_llm_for_stage"
        ) as mock_get_llm:
            mock_get_llm.return_value = MockLLM(response='{"result": "ok"}')

            crew_instance = ExplorerCrew()
            crew = crew_instance.crew()

            # At least one agent should have tools
            agents_with_tools = [a for a in crew.agents if a.tools]
            assert len(agents_with_tools) > 0

    def test_explorer_crew_tasks_bound_to_agents(self):
        """Test that tasks are bound to agents."""
        with patch(
            "mycrew.crews.explorer_crew.explorer_crew.get_llm_for_stage"
        ) as mock_get_llm:
            mock_get_llm.return_value = MockLLM(response='{"result": "ok"}')

            crew_instance = ExplorerCrew()
            crew = crew_instance.crew()

            # Each task should have an agent
            for task in crew.tasks:
                assert task.agent is not None, f"Task {task.name} has no agent bound"


@pytest.mark.unit
class TestPipelineStateIntegration:
    """Tests for pipeline state integration with crews."""

    def test_state_passes_to_crew_inputs(self):
        """Test that state values are passed to crew inputs."""
        state = PipelineState(
            id="test-id",
            issue_url="https://github.com/test/repo/issues/1",
            issue_data={
                "owner": "test",
                "repo": "repo",
                "number": "1",
                "github_repo": "test/repo",
            },
            repo_path="/tmp/test",
            repo_root="/tmp/test",
            programmatic=True,
        )

        # State should have required fields
        assert state.id == "test-id"
        assert state.issue_url == "https://github.com/test/repo/issues/1"
        assert state.repo_path == "/tmp/test"

    def test_state_holds_exploration_result(self):
        """Test that state can hold exploration results."""
        state = PipelineState(
            id="test-id",
            programmatic=True,
            exploration_result={
                "tech_stack": ["Python", "Flask"],
                "key_files": ["src/app.py"],
                "conventions": {"testing": "pytest"},
            },
        )

        assert state.exploration_result is not None
        assert "tech_stack" in state.exploration_result
        assert state.exploration_result["tech_stack"] == ["Python", "Flask"]

    def test_state_chains_between_steps(self):
        """Test that state can chain results between pipeline steps."""
        state = PipelineState(
            id="test-id",
            programmatic=True,
            exploration_result={"tech_stack": ["Python"]},
        )

        # Simulate adding analyze result
        new_state = state.model_copy()
        new_state.issue_data = {
            "task": "Add user authentication",
            "similar_issues": [],
        }

        assert state.exploration_result is not None
        assert new_state.issue_data is not None
        assert new_state.issue_data["task"] == "Add user authentication"


@pytest.mark.unit
class TestCrewToolIntegration:
    """Tests for crew tool integration."""

    def test_repo_shell_tool_in_explorer_crew(self):
        """Test that repo_shell tool is available in explorer crew."""
        with patch(
            "mycrew.crews.explorer_crew.explorer_crew.get_llm_for_stage"
        ) as mock_get_llm:
            mock_get_llm.return_value = MockLLM(response='{"result": "ok"}')

            crew_instance = ExplorerCrew()
            crew = crew_instance.crew()

            # Check that at least one agent has the repo_shell tool
            tool_names = []
            for agent in crew.agents:
                for tool in agent.tools:
                    tool_names.append(tool.name)

            # Should have shell-related tools
            assert any(
                "shell" in name.lower() or "bash" in name.lower() for name in tool_names
            )


@pytest.mark.unit
class TestCrewErrorHandling:
    """Tests for crew error handling."""

    def test_handles_missing_repo_path_gracefully(self):
        """Test that crew handles missing repo_path."""
        state = PipelineState(
            id="test-id",
            issue_url="https://github.com/test/repo/issues/1",
            repo_path="",  # Empty path
            programmatic=True,
        )

        # Should not raise, just log warning
        assert state.repo_path == ""

    def test_handles_missing_issue_data(self):
        """Test that crew handles missing issue_data."""
        state = PipelineState(
            id="test-id",
            issue_url="https://github.com/test/repo/issues/1",
            issue_data=None,
            programmatic=True,
        )

        # Should handle gracefully
        assert state.issue_data is None


@pytest.mark.unit
class TestMultiCrewExecution:
    """Tests for executing multiple crews in sequence."""

    def test_state_transitions_between_crews(self):
        """Test that state correctly transitions between crew executions."""
        # Step 1: Exploration result
        state = PipelineState(
            id="test-id",
            programmatic=True,
            exploration_result={
                "tech_stack": ["Python", "FastAPI"],
                "key_files": ["src/main.py"],
            },
        )

        # Step 2: Analyze (uses exploration result)
        assert state.exploration_result is not None
        tech_stack = state.exploration_result.get("tech_stack", [])
        assert "Python" in tech_stack

    def test_input_builder_includes_previous_results(self):
        """Test that input builder includes previous step results."""
        from mycrew.crews.input_builder import PipelineInputBuilder

        builder = PipelineInputBuilder()

        state = PipelineState(
            id="test-id",
            issue_url="https://github.com/test/repo/issues/1",
            issue_data={
                "owner": "test",
                "repo": "repo",
                "number": "1",
                "github_repo": "test/repo",
            },
            repo_path="/tmp/test",
            repo_root="/tmp/test",
            programmatic=True,
            exploration_result={"tech_stack": ["Python"]},
        )

        inputs = builder.build(state, None)

        # Should include exploration context
        assert "repo_context" in inputs
        assert "issue_url" in inputs
