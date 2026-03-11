"""Issue Analyst crew: parses raw issue cards into structured requirements."""

from crewai import Agent, Task
from crewai.project import CrewBase, agent, task

from code_pipeline.crews.base import PipelineCrewBase


@CrewBase
class IssueAnalystCrew(PipelineCrewBase):
    """Issue Analyst crew: extracts structured requirements and validates scope."""

    @agent
    def issue_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config["issue_analyst"],  # type: ignore[index]
        )

    @agent
    def scope_validator(self) -> Agent:
        return Agent(
            config=self.agents_config["scope_validator"],  # type: ignore[index]
        )

    @agent
    def similar_issues_synthesizer(self) -> Agent:
        return Agent(
            config=self.agents_config["similar_issues_synthesizer"],  # type: ignore[index]
        )

    @agent
    def acceptance_criteria_normalizer(self) -> Agent:
        return Agent(
            config=self.agents_config["acceptance_criteria_normalizer"],  # type: ignore[index]
        )

    @task
    def similar_issues_task(self) -> Task:
        return Task(
            config=self.tasks_config["similar_issues_task"],  # type: ignore[index]
        )

    @task
    def analyze_task(self) -> Task:
        return Task(
            config=self.tasks_config["analyze_task"],  # type: ignore[index]
        )

    @task
    def validate_scope_task(self) -> Task:
        return Task(
            config=self.tasks_config["validate_scope_task"],  # type: ignore[index]
        )

    @task
    def acceptance_criteria_normalize_task(self) -> Task:
        return Task(
            config=self.tasks_config["acceptance_criteria_normalize_task"],  # type: ignore[index]
        )
