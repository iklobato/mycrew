import os
from typing import List

from crewai import Agent, Crew, Process, Task
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai.project import CrewBase, agent, crew, task

from code_pipeline.tools.repo_shell_tool import RepoShellTool


@CrewBase
class ArchitectCrew:
    """Architect crew: produces file-level plan, no code."""

    agents: List[BaseAgent]
    tasks: List[Task]

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def architect(self) -> Agent:
        repo_path = os.environ.get("REPO_PATH", os.getcwd())
        return Agent(
            config=self.agents_config["architect"],  # type: ignore[index]
            tools=[RepoShellTool(repo_path=repo_path)],
            verbose=True,
        )

    @task
    def plan_task(self) -> Task:
        return Task(
            config=self.tasks_config["plan_task"],  # type: ignore[index]
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
