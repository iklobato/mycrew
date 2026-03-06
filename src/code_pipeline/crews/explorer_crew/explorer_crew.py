import os
from typing import List

from crewai import Agent, Crew, Process, Task
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai.project import CrewBase, agent, crew, task

from code_pipeline.tools.repo_shell_tool import RepoShellTool


@CrewBase
class ExplorerCrew:
    """Explorer crew: produces structured repo summary (stack, files, conventions)."""

    agents: List[BaseAgent]
    tasks: List[Task]

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def repo_explorer(self) -> Agent:
        repo_path = os.environ.get("REPO_PATH", os.getcwd())
        return Agent(
            config=self.agents_config["repo_explorer"],  # type: ignore[index]
            tools=[RepoShellTool(repo_path=repo_path)],
            verbose=True,
        )

    @task
    def explore_task(self) -> Task:
        return Task(
            config=self.tasks_config["explore_task"],  # type: ignore[index]
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
