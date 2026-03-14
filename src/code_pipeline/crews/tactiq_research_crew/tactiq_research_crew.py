"""Tactiq Research crew: fetch meeting context and determine if clarification is needed."""

from typing import ClassVar, List

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

from code_pipeline.crews.base import PipelineCrewBase


@CrewBase
class TactiqResearchCrew(PipelineCrewBase):
    """Tactiq Research crew: synthesize meeting context and determine if clarification needed."""

    stage: ClassVar[str] = "auxiliary"

    @property
    def required_agents(self) -> List[str]:
        return [
            "tactiq_researcher",
        ]

    @property
    def required_tasks(self) -> List[str]:
        return [
            "tactiq_research_task",
        ]

    @agent
    def tactiq_researcher(self) -> Agent:
        return self._build_agent("tactiq_researcher")

    @task
    def tactiq_research_task(self) -> Task:
        return self._build_task("tactiq_research_task")

    @crew
    def crew(self) -> Crew:
        """Creates the TactiqResearchCrew crew."""
        return Crew(
            agents=self.agents,  # type: ignore[attr-defined]
            tasks=self.tasks,  # type: ignore[attr-defined]
            process=Process.sequential,
            verbose=True,
        )
