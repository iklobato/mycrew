"""Clarify crew: detects ambiguities, prioritizes, asks human before planning."""

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

from code_pipeline.crews.base import PipelineCrewBase


@CrewBase
class ClarifyCrew(PipelineCrewBase):
    """Clarify crew: ambiguity detection, prioritization, human questions."""

    @agent
    def ambiguity_detector(self) -> Agent:
        return Agent(
            config=self.agents_config["ambiguity_detector"],  # type: ignore[index]
        )

    @agent
    def question_prioritizer(self) -> Agent:
        return Agent(
            config=self.agents_config["question_prioritizer"],  # type: ignore[index]
        )

    @agent
    def clarifier(self) -> Agent:
        return Agent(config=self.agents_config["clarifier"])  # type: ignore[index]

    @task
    def ambiguity_detect_task(self) -> Task:
        return Task(
            config=self.tasks_config["ambiguity_detect_task"],  # type: ignore[index]
        )

    @task
    def question_prioritize_task(self) -> Task:
        return Task(
            config=self.tasks_config["question_prioritize_task"],  # type: ignore[index]
        )

    @task
    def clarify_task(self) -> Task:
        return Task(
            config=self.tasks_config["clarify_task"],  # type: ignore[index]
        )

    @crew
    def crew(self) -> Crew:
        """Creates the ClarifyCrew crew."""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=False,
            tracing=False,
        )
