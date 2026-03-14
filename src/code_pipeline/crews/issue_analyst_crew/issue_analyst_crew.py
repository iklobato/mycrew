"""Issue Analyst crew: parses raw issue cards into structured requirements."""

from typing import ClassVar, List

from crewai import Agent, Task
from crewai.project import CrewBase, agent, task

from code_pipeline.crews.base import PipelineCrewBase


@CrewBase
class IssueAnalystCrew(PipelineCrewBase):
    """Issue Analyst crew: extracts structured requirements and validates scope."""

    stage: ClassVar[str] = "analyze_issue"

    @property
    def required_agents(self) -> List[str]:
        return [
            "issue_analyst",
            "scope_validator",
            "similar_issues_synthesizer",
            "acceptance_criteria_normalizer",
        ]

    @property
    def required_tasks(self) -> List[str]:
        return [
            "similar_issues_task",
            "analyze_task",
            "validate_scope_task",
            "acceptance_criteria_normalize_task",
        ]

    @agent
    def issue_analyst(self) -> Agent:
        return self._build_agent("issue_analyst")

    @agent
    def scope_validator(self) -> Agent:
        return self._build_agent("scope_validator")

    @agent
    def similar_issues_synthesizer(self) -> Agent:
        return self._build_agent("similar_issues_synthesizer")

    @agent
    def acceptance_criteria_normalizer(self) -> Agent:
        return self._build_agent("acceptance_criteria_normalizer")

    @task
    def similar_issues_task(self) -> Task:
        return self._build_task("similar_issues_task")

    @task
    def analyze_task(self) -> Task:
        return self._build_task("analyze_task")

    @task
    def validate_scope_task(self) -> Task:
        return self._build_task("validate_scope_task")

    @task
    def acceptance_criteria_normalize_task(self) -> Task:
        return self._build_task("acceptance_criteria_normalize_task")
