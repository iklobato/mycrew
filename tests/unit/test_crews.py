"""Unit tests for code_pipeline.crews (construction only, no LLM calls)."""

from unittest.mock import patch

from crewai import LLM

from code_pipeline.crews.issue_analyst_crew.issue_analyst_crew import IssueAnalystCrew


@patch("code_pipeline.crews.base.get_llm_for_stage")
def test_issue_analyst_crew_constructs_successfully(mock_llm):
    """IssueAnalystCrew can be instantiated with mocked LLM (no API calls)."""
    # CrewAI Agent requires a valid LLM with model string; use minimal LLM for construction
    mock_llm.return_value = LLM(model="openrouter/openai/gpt-3.5-turbo")

    crew_instance = IssueAnalystCrew()
    crew = crew_instance.crew()

    assert crew is not None
    assert crew.agents is not None
    assert len(crew.agents) > 0
    assert crew.tasks is not None
    assert len(crew.tasks) > 0
