"""Unit tests for code_pipeline.crews (construction only, no LLM calls)."""

from unittest.mock import patch

from crewai import LLM

from code_pipeline.crews.architect_crew.architect_crew import ArchitectCrew
from code_pipeline.crews.clarify_crew.clarify_crew import ClarifyCrew
from code_pipeline.crews.commit_crew.commit_crew import CommitCrew
from code_pipeline.crews.explorer_crew.explorer_crew import ExplorerCrew
from code_pipeline.crews.implementer_crew.implementer_crew import ImplementerCrew
from code_pipeline.crews.issue_analyst_crew.issue_analyst_crew import IssueAnalystCrew
from code_pipeline.crews.reviewer_crew.reviewer_crew import ReviewerCrew
from code_pipeline.crews.test_validator_crew.test_validator_crew import (
    TestValidatorCrew,
)


def _mock_llm():
    return LLM(model="openrouter/openai/gpt-3.5-turbo")


@patch("code_pipeline.crews.base.get_llm_for_stage")
@patch("code_pipeline.crews.base.get_pipeline_context")
def test_issue_analyst_crew_constructs_successfully(mock_ctx, mock_llm):
    """IssueAnalystCrew can be instantiated with mocked LLM (no API calls)."""
    mock_llm.return_value = _mock_llm()
    mock_ctx.return_value.repo_path = "/tmp"
    mock_ctx.return_value.github_repo = "owner/repo"
    mock_ctx.return_value.serper_enabled = False

    crew_instance = IssueAnalystCrew()
    crew = crew_instance.crew()

    assert crew is not None
    assert crew.agents is not None
    assert len(crew.agents) > 0
    assert crew.tasks is not None
    assert len(crew.tasks) > 0


@patch("code_pipeline.crews.base.get_llm_for_stage")
@patch("code_pipeline.crews.base.get_pipeline_context")
def test_architect_crew_constructs_successfully(mock_ctx, mock_llm):
    """ArchitectCrew constructs successfully."""
    mock_llm.return_value = _mock_llm()
    mock_ctx.return_value.repo_path = "/tmp"
    mock_ctx.return_value.github_repo = "owner/repo"
    mock_ctx.return_value.serper_enabled = False

    crew = ArchitectCrew().crew()
    assert crew is not None
    assert len(crew.agents) > 0
    assert len(crew.tasks) > 0


@patch("code_pipeline.crews.base.get_llm_for_stage")
@patch("code_pipeline.crews.base.get_pipeline_context")
def test_explorer_crew_constructs_successfully(mock_ctx, mock_llm):
    """ExplorerCrew constructs successfully."""
    mock_llm.return_value = _mock_llm()
    mock_ctx.return_value.repo_path = "/tmp"
    mock_ctx.return_value.github_repo = ""
    mock_ctx.return_value.serper_enabled = False

    crew = ExplorerCrew().crew()
    assert crew is not None
    assert len(crew.agents) > 0
    assert len(crew.tasks) > 0


@patch("code_pipeline.crews.base.get_llm_for_stage")
@patch("code_pipeline.crews.base.get_pipeline_context")
def test_implementer_crew_constructs_successfully(mock_ctx, mock_llm):
    """ImplementerCrew constructs successfully."""
    mock_llm.return_value = _mock_llm()
    mock_ctx.return_value.repo_path = "/tmp"
    mock_ctx.return_value.github_repo = ""
    mock_ctx.return_value.serper_enabled = False

    crew = ImplementerCrew().crew()
    assert crew is not None
    assert len(crew.agents) > 0
    assert len(crew.tasks) > 0


@patch("code_pipeline.crews.base.get_llm_for_stage")
@patch("code_pipeline.crews.base.get_pipeline_context")
def test_reviewer_crew_constructs_successfully(mock_ctx, mock_llm):
    """ReviewerCrew constructs successfully."""
    mock_llm.return_value = _mock_llm()
    mock_ctx.return_value.repo_path = "/tmp"
    mock_ctx.return_value.github_repo = ""
    mock_ctx.return_value.serper_enabled = False

    crew = ReviewerCrew().crew()
    assert crew is not None
    assert len(crew.agents) > 0
    assert len(crew.tasks) > 0


@patch("code_pipeline.crews.base.get_llm_for_stage")
@patch("code_pipeline.crews.base.get_pipeline_context")
def test_commit_crew_constructs_successfully(mock_ctx, mock_llm):
    """CommitCrew constructs successfully."""
    mock_llm.return_value = _mock_llm()
    mock_ctx.return_value.repo_path = "/tmp"
    mock_ctx.return_value.github_repo = "owner/repo"
    mock_ctx.return_value.serper_enabled = False

    crew = CommitCrew().crew()
    assert crew is not None
    assert len(crew.agents) > 0
    assert len(crew.tasks) > 0


@patch("code_pipeline.crews.base.get_llm_for_stage")
@patch("code_pipeline.crews.base.get_pipeline_context")
def test_clarify_crew_constructs_successfully(mock_ctx, mock_llm):
    """ClarifyCrew constructs successfully."""
    mock_llm.return_value = _mock_llm()
    mock_ctx.return_value.repo_path = "/tmp"
    mock_ctx.return_value.github_repo = ""
    mock_ctx.return_value.serper_enabled = False

    crew = ClarifyCrew().crew()
    assert crew is not None
    assert len(crew.agents) > 0
    assert len(crew.tasks) > 0


@patch("code_pipeline.crews.base.get_llm_for_stage")
@patch("code_pipeline.crews.base.get_pipeline_context")
def test_test_validator_crew_constructs_successfully(mock_ctx, mock_llm):
    """TestValidatorCrew constructs successfully."""
    mock_llm.return_value = _mock_llm()
    mock_ctx.return_value.repo_path = "/tmp"
    mock_ctx.return_value.github_repo = ""
    mock_ctx.return_value.serper_enabled = False

    crew = TestValidatorCrew().crew()
    assert crew is not None
    assert len(crew.agents) > 0
    assert len(crew.tasks) > 0
