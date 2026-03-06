import os
from typing import List

from crewai import Agent, Crew, Process, Task
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import FileWriterTool

from code_pipeline.tools.repo_shell_tool import RepoShellTool


@CrewBase
class ImplementerCrew:
    """Implementer crew: writes files according to the plan."""

    agents: List[BaseAgent]
    tasks: List[Task]

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def implementer(self) -> Agent:
        repo_path = os.environ.get("REPO_PATH", os.getcwd())
        return Agent(
            config=self.agents_config["implementer"],  # type: ignore[index]
            tools=[
                RepoShellTool(repo_path=repo_path),
                FileWriterTool(),
            ],
            verbose=True,
        )

    @task
    def implement_task(self) -> Task:
        return Task(
            config=self.tasks_config["implement_task"],  # type: ignore[index]
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
