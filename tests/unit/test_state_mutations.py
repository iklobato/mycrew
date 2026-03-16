"""State mutation tests - verify state is properly configured for mutations.

These tests verify that:
- State can hold results from each step
- State can be copied and modified
- State fields are properly typed
"""

import os

os.environ["CREWAI_TELEMETRY_DISABLED"] = "true"
os.environ["OTEL_SDK_DISABLED"] = "true"

import pytest
from mycrew.main import PipelineState


@pytest.mark.unit
class TestExplorationResult:
    """Test exploration_result field."""

    def test_exploration_result_can_be_set(self):
        """exploration_result should be settable."""
        state = PipelineState(
            id="test",
            programmatic=True,
            exploration_result={"tech_stack": ["Python", "Flask"]},
        )
        assert state.exploration_result == {"tech_stack": ["Python", "Flask"]}

    def test_exploration_result_with_key_files(self):
        """exploration_result should hold key files."""
        state = PipelineState(
            id="test",
            programmatic=True,
            exploration_result={
                "tech_stack": ["Python"],
                "key_files": ["src/app.py", "src/models.py"],
            },
        )
        assert "key_files" in state.exploration_result
        assert len(state.exploration_result["key_files"]) == 2


@pytest.mark.unit
class TestArchitectureResult:
    """Test architecture_result field."""

    def test_architecture_result_can_be_set(self):
        """architecture_result should be settable."""
        state = PipelineState(
            id="test",
            programmatic=True,
            architecture_result={"plan": "Add auth module"},
        )
        assert state.architecture_result == {"plan": "Add auth module"}


@pytest.mark.unit
class TestImplementationResult:
    """Test implementation_result field."""

    def test_implementation_result_can_be_set(self):
        """implementation_result should be settable."""
        state = PipelineState(
            id="test",
            programmatic=True,
            implementation_result={"files_created": ["auth.py"]},
        )
        assert state.implementation_result == {"files_created": ["auth.py"]}


@pytest.mark.unit
class TestReviewResult:
    """Test review_result field."""

    def test_review_result_can_be_set(self):
        """review_result should be settable."""
        state = PipelineState(
            id="test",
            programmatic=True,
            review_result={"verdict": "APPROVED"},
        )
        assert state.review_result == {"verdict": "APPROVED"}


@pytest.mark.unit
class TestStateCopy:
    """Test that state can be copied for mutation."""

    def test_model_copy_creates_independent_state(self):
        """model_copy should create independent state."""
        state1 = PipelineState(
            id="test",
            programmatic=True,
            exploration_result={"tech_stack": ["Python"]},
        )
        state2 = state1.model_copy()

        state2.exploration_result = {"tech_stack": ["Python", "JavaScript"]}

        assert state1.exploration_result == {"tech_stack": ["Python"]}
        assert state2.exploration_result == {"tech_stack": ["Python", "JavaScript"]}

    def test_model_copy_with_update(self):
        """model_copy with update should work."""
        state = PipelineState(
            id="original",
            programmatic=True,
        )
        new_state = state.model_copy(update={"id": "updated", "mock": True})

        assert state.id == "original"
        assert new_state.id == "updated"
        assert new_state.mock is True


@pytest.mark.unit
class TestStateJsonSerialization:
    """Test state can be serialized to JSON."""

    def test_to_json(self):
        """State should serialize to JSON."""
        import json

        state = PipelineState(
            id="test-json",
            issue_url="https://github.com/test/repo/issues/1",
            programmatic=True,
            exploration_result={"tech_stack": ["Python"]},
        )
        json_str = state.model_dump_json()
        data = json.loads(json_str)

        assert data["id"] == "test-json"
        assert data["exploration_result"]["tech_stack"] == ["Python"]


@pytest.mark.unit
class TestStateIteration:
    """Test state can be iterated."""

    def test_model_dump_includes_all_fields(self):
        """model_dump should include all fields."""
        state = PipelineState(
            id="test-dump",
            issue_url="https://github.com/test/repo/issues/1",
            repo_path="/tmp/test",
            repo_root="/tmp/test",
            programmatic=True,
            target_steps=["EXPLORE"],
            mock=True,
            exploration_result={"tech_stack": ["Python"]},
        )
        data = state.model_dump()

        assert "id" in data
        assert "issue_url" in data
        assert "repo_path" in data
        assert "target_steps" in data
        assert "mock" in data
        assert "exploration_result" in data
