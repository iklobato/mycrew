"""Error path tests - test failure scenarios don't crash.

These tests verify that:
- State validates correctly
- State fields work properly
- Configuration is handled properly
"""

import os

os.environ["CREWAI_TELEMETRY_DISABLED"] = "true"
os.environ["OTEL_SDK_DISABLED"] = "true"

import pytest
from mycrew.main import PipelineState


@pytest.mark.unit
class TestStateValidation:
    """Test that state validates correctly."""

    def test_empty_repo_path_creates_state(self):
        """Empty repo_path should create state without error."""
        state = PipelineState(
            id="test-empty",
            issue_url="https://github.com/test/repo/issues/1",
            repo_path="",
            repo_root="",
            programmatic=True,
        )
        assert state.id == "test-empty"
        assert state.repo_path == ""

    def test_invalid_issue_url_creates_state(self):
        """Invalid issue URL should create state without error."""
        state = PipelineState(
            id="test-invalid",
            issue_url="not-a-url",
            repo_path="/tmp/test",
            repo_root="/tmp/test",
            programmatic=True,
        )
        assert state.issue_url == "not-a-url"

    def test_none_issue_data_creates_state(self):
        """None issue_data should create state without error."""
        state = PipelineState(
            id="test-none",
            issue_url="https://github.com/test/repo/issues/1",
            issue_data=None,
            repo_path="/tmp/test",
            repo_root="/tmp/test",
            programmatic=True,
        )
        assert state.issue_data is None

    def test_valid_state_with_all_fields(self):
        """State with all fields should be created."""
        state = PipelineState(
            id="test-full",
            issue_url="https://github.com/test/repo/issues/1",
            issue_data={
                "owner": "test",
                "repo": "repo",
                "number": "1",
                "github_repo": "test/repo",
                "task": "Add feature",
            },
            repo_path="/tmp/test",
            repo_root="/tmp/test",
            programmatic=True,
            target_steps=["EXPLORE", "ANALYZE"],
            input_file="/tmp/input.json",
            mock=True,
        )
        assert state.id == "test-full"
        assert state.target_steps == ["EXPLORE", "ANALYZE"]
        assert state.mock is True


@pytest.mark.unit
class TestStateFields:
    """Test state fields work correctly."""

    def test_target_steps_defaults_to_empty_list(self):
        """target_steps should default to empty list."""
        state = PipelineState(id="test", programmatic=True)
        assert state.target_steps == []

    def test_input_file_defaults_to_empty_string(self):
        """input_file should default to empty string."""
        state = PipelineState(id="test", programmatic=True)
        assert state.input_file == ""

    def test_mock_defaults_to_false(self):
        """mock should default to False."""
        state = PipelineState(id="test", programmatic=True)
        assert state.mock is False

    def test_programmatic_defaults_to_false(self):
        """programmatic should default to False."""
        state = PipelineState(id="test")
        assert state.programmatic is False


@pytest.mark.unit
class TestStateStepExecution:
    """Test state step execution fields."""

    def test_state_stores_target_steps(self):
        """State should store target_steps."""
        state = PipelineState(
            id="test-steps",
            programmatic=True,
            target_steps=["EXPLORE", "ANALYZE", "ARCHITECT"],
        )
        assert state.target_steps == ["EXPLORE", "ANALYZE", "ARCHITECT"]

    def test_state_stores_input_file(self):
        """State should store input_file."""
        state = PipelineState(
            id="test-input",
            programmatic=True,
            input_file="/path/to/input.json",
        )
        assert state.input_file == "/path/to/input.json"

    def test_state_stores_mock_flag(self):
        """State should store mock flag."""
        state = PipelineState(
            id="test-mock",
            programmatic=True,
            mock=True,
        )
        assert state.mock is True


@pytest.mark.unit
class TestStateResults:
    """Test state result fields."""

    def test_state_initializes_result_fields_to_none(self):
        """Result fields should initialize to None."""
        state = PipelineState(id="test", programmatic=True)

        assert state.exploration_result is None
        assert state.architecture_result is None
        assert state.implementation_result is None
        assert state.review_result is None
        assert state.validation_result is None
        assert state.commit_result is None

    def test_state_can_store_exploration_result(self):
        """State should store exploration_result."""
        state = PipelineState(
            id="test",
            programmatic=True,
            exploration_result={"tech_stack": ["Python"]},
        )
        assert state.exploration_result == {"tech_stack": ["Python"]}

    def test_state_can_store_architecture_result(self):
        """State should store architecture_result."""
        state = PipelineState(
            id="test",
            programmatic=True,
            architecture_result={"plan": "Create auth module"},
        )
        assert state.architecture_result == {"plan": "Create auth module"}

    def test_state_can_store_implementation_result(self):
        """State should store implementation_result."""
        state = PipelineState(
            id="test",
            programmatic=True,
            implementation_result={"files_created": ["auth.py"]},
        )
        assert state.implementation_result == {"files_created": ["auth.py"]}


@pytest.mark.unit
class TestStateModel:
    """Test PipelineState model behavior."""

    def test_state_is_pydantic_model(self):
        """PipelineState should be a Pydantic model."""
        state = PipelineState(id="test", programmatic=True)
        assert hasattr(state, "model_dump")

    def test_state_can_copy(self):
        """State can be copied with model_copy."""
        state = PipelineState(
            id="test",
            programmatic=True,
            exploration_result={"tech_stack": ["Python"]},
        )
        new_state = state.model_copy()
        new_state.exploration_result = {"tech_stack": ["Python", "Flask"]}

        assert state.exploration_result == {"tech_stack": ["Python"]}
        assert new_state.exploration_result == {"tech_stack": ["Python", "Flask"]}

    def test_state_serializes_to_dict(self):
        """State serializes to dict correctly."""
        state = PipelineState(
            id="test-serialize",
            issue_url="https://github.com/test/repo/issues/1",
            programmatic=True,
        )
        data = state.model_dump()

        assert data["id"] == "test-serialize"
        assert data["issue_url"] == "https://github.com/test/repo/issues/1"
        assert data["programmatic"] is True
