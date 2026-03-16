"""Comprehensive flow execution tests - fast tests that verify flow structure.

These tests verify flow structure without running the actual flow (which is slow).
For full flow execution tests, see test_flow_execution_comprehensive.py (marked as slow).
"""

import os

os.environ["CREWAI_TELEMETRY_DISABLED"] = "true"
os.environ["OTEL_SDK_DISABLED"] = "true"

import pytest


@pytest.mark.unit
class TestFlowStructure:
    """Test flow has required methods and structure."""

    def test_flow_class_exists(self):
        """Flow class should exist."""
        from mycrew.main import CodePipelineFlow

        assert CodePipelineFlow is not None

    def test_flow_inherits_from_flow(self):
        """Flow should inherit from crewai Flow."""
        from crewai.flow import Flow
        from mycrew.main import CodePipelineFlow

        assert issubclass(CodePipelineFlow, Flow)

    def test_flow_has_kickoff_method(self):
        """Flow should have kickoff method."""
        from mycrew.main import CodePipelineFlow

        assert hasattr(CodePipelineFlow, "kickoff")

    def test_flow_has_run_step_method(self):
        """Flow should have _run_step method."""
        from mycrew.main import CodePipelineFlow

        assert hasattr(CodePipelineFlow, "_run_step")

    def test_flow_has_load_step_input_method(self):
        """Flow should have _load_step_input method."""
        from mycrew.main import CodePipelineFlow

        assert hasattr(CodePipelineFlow, "_load_step_input")

    def test_flow_has_save_step_output_method(self):
        """Flow should have _save_step_output method."""
        from mycrew.main import CodePipelineFlow

        assert hasattr(CodePipelineFlow, "_save_step_output")

    def test_flow_has_get_previous_step_method(self):
        """Flow should have _get_previous_step method."""
        from mycrew.main import CodePipelineFlow

        assert hasattr(CodePipelineFlow, "_get_previous_step")

    def test_flow_has_has_target_steps_method(self):
        """Flow should have _has_target_steps method."""
        from mycrew.main import CodePipelineFlow

        assert hasattr(CodePipelineFlow, "_has_target_steps")

    def test_flow_has_is_step_in_targets_method(self):
        """Flow should have _is_step_in_targets method."""
        from mycrew.main import CodePipelineFlow

        assert hasattr(CodePipelineFlow, "_is_step_in_targets")


@pytest.mark.unit
class TestFlowStepMethods:
    """Test flow step execution methods exist."""

    def test_has_run_step_explore_method(self):
        """Flow should have _run_step_explore method."""
        from mycrew.main import CodePipelineFlow

        assert hasattr(CodePipelineFlow, "_run_step_explore")

    def test_has_run_step_analyze_method(self):
        """Flow should have _run_step_analyze method."""
        from mycrew.main import CodePipelineFlow

        assert hasattr(CodePipelineFlow, "_run_step_analyze")

    def test_has_run_step_architect_method(self):
        """Flow should have _run_step_architect method."""
        from mycrew.main import CodePipelineFlow

        assert hasattr(CodePipelineFlow, "_run_step_architect")

    def test_has_run_step_implement_method(self):
        """Flow should have _run_step_implement method."""
        from mycrew.main import CodePipelineFlow

        assert hasattr(CodePipelineFlow, "_run_step_implement")

    def test_has_run_step_review_method(self):
        """Flow should have _run_step_review method."""
        from mycrew.main import CodePipelineFlow

        assert hasattr(CodePipelineFlow, "_run_step_review")

    def test_has_run_step_commit_method(self):
        """Flow should have _run_step_commit method."""
        from mycrew.main import CodePipelineFlow

        assert hasattr(CodePipelineFlow, "_run_step_commit")

    def test_has_run_step_validate_tests_method(self):
        """Flow should have _run_step_validate_tests method."""
        from mycrew.main import CodePipelineFlow

        assert hasattr(CodePipelineFlow, "_run_step_validate_tests")


@pytest.mark.unit
class TestFlowDecorators:
    """Test flow uses CrewAI decorators correctly."""

    def test_flow_has_start_decorator(self):
        """Flow should have a start method."""
        from mycrew.main import CodePipelineFlow

        assert hasattr(CodePipelineFlow, "start")

    def test_flow_has_explore_method(self):
        """Flow should have explore method."""
        from mycrew.main import CodePipelineFlow

        assert hasattr(CodePipelineFlow, "explore")

    def test_flow_has_analyze_issue_method(self):
        """Flow should have analyze_issue method."""
        from mycrew.main import CodePipelineFlow

        assert hasattr(CodePipelineFlow, "analyze_issue")

    def test_flow_has_architect_method(self):
        """Flow should have architect method."""
        from mycrew.main import CodePipelineFlow

        assert hasattr(CodePipelineFlow, "architect")

    def test_flow_has_implement_method(self):
        """Flow should have implement method."""
        from mycrew.main import CodePipelineFlow

        assert hasattr(CodePipelineFlow, "implement")

    def test_flow_has_review_method(self):
        """Flow should have review method."""
        from mycrew.main import CodePipelineFlow

        assert hasattr(CodePipelineFlow, "review")

    def test_flow_has_commit_method(self):
        """Flow should have commit method."""
        from mycrew.main import CodePipelineFlow

        assert hasattr(CodePipelineFlow, "commit")


@pytest.mark.unit
class TestFlowCrewMethods:
    """Test flow crew execution methods."""

    def test_flow_has_run_crew_method(self):
        """Flow should have _run_crew method."""
        from mycrew.main import CodePipelineFlow

        assert hasattr(CodePipelineFlow, "_run_crew")

    def test_flow_has_get_field_from_state_method(self):
        """Flow should have _get_field_from_state method."""
        from mycrew.main import CodePipelineFlow

        assert hasattr(CodePipelineFlow, "_get_field_from_state")


@pytest.mark.unit
class TestPipelineCrewImports:
    """Test that all pipeline crews can be imported."""

    def test_import_explorer_crew(self):
        """ExplorerCrew should be importable."""
        from mycrew.crews.explorer_crew.explorer_crew import ExplorerCrew

        assert ExplorerCrew is not None

    def test_import_issue_analyst_crew(self):
        """IssueAnalystCrew should be importable."""
        from mycrew.crews.issue_analyst_crew.issue_analyst_crew import IssueAnalystCrew

        assert IssueAnalystCrew is not None

    def test_import_architect_crew(self):
        """ArchitectCrew should be importable."""
        from mycrew.crews.architect_crew.architect_crew import ArchitectCrew

        assert ArchitectCrew is not None

    def test_import_implementer_crew(self):
        """ImplementerCrew should be importable."""
        from mycrew.crews.implementer_crew.implementer_crew import ImplementerCrew

        assert ImplementerCrew is not None

    def test_import_reviewer_crew(self):
        """ReviewerCrew should be importable."""
        from mycrew.crews.reviewer_crew.reviewer_crew import ReviewerCrew

        assert ReviewerCrew is not None

    def test_import_commit_crew(self):
        """CommitCrew should be importable."""
        from mycrew.crews.commit_crew.commit_crew import CommitCrew

        assert CommitCrew is not None
