"""Clarify crew: asks targeted questions grounded in exploration before planning."""

from typing import List

from crewai import Agent, Crew, Process, Task
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai.project import CrewBase, agent, crew, task

from code_pipeline.llm import get_llm_for_stage
from code_pipeline.tools.human_tool import ask_human


@CrewBase
class ClarifyCrew:
    """Clarify crew: resolves ambiguities via human questions before the architect plans."""

    agents: List[BaseAgent]
    tasks: List[Task]

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def clarifier(self) -> Agent:
        return Agent(
            config=self.agents_config["clarifier"],  # type: ignore[index]
            tools=[ask_human],
            llm=get_llm_for_stage("analyze_issue"),
            verbose=False,
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
            tracing=True,
        )
