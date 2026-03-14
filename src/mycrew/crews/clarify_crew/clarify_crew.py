"""Clarify crew: detects ambiguities, prioritizes, asks human before planning."""

from typing import ClassVar, List

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

from mycrew.crews.base import PipelineCrewBase


@CrewBase
class ClarifyCrew(PipelineCrewBase):
    """Clarify crew: ambiguity detection, prioritization, human questions."""

    stage: ClassVar[str] = "auxiliary"

    @property
    def required_agents(self) -> List[str]:
        return [
            "ambiguity_detector",
            "question_prioritizer",
            "clarifier",
        ]

    @property
    def required_tasks(self) -> List[str]:
        return [
            "ambiguity_detect_task",
            "question_prioritize_task",
            "clarify_task",
        ]

    @agent
    def ambiguity_detector(self) -> Agent:
        return self._build_agent("ambiguity_detector")

    @agent
    def question_prioritizer(self) -> Agent:
        return self._build_agent("question_prioritizer")

    @agent
    def clarifier(self) -> Agent:
        return self._build_agent("clarifier")

    @task
    def ambiguity_detect_task(self) -> Task:
        return self._build_task("ambiguity_detect_task")

    @task
    def question_prioritize_task(self) -> Task:
        return self._build_task("question_prioritize_task")

    @task
    def clarify_task(self) -> Task:
        return self._build_task("clarify_task")

    @crew
    def crew(self) -> Crew:
        """Creates the ClarifyCrew crew."""
        return Crew(
            agents=self.agents,  # type: ignore[attr-defined]
            tasks=self.tasks,  # type: ignore[attr-defined]
            process=Process.sequential,
            verbose=True,
        )
