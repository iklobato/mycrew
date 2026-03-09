"""Commit crew: runs git add and commit."""

import os
from typing import List

from crewai import Agent, Crew, Process, Task
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai.project import CrewBase, agent, crew, task

from code_pipeline.llm import get_llm_for_stage
from code_pipeline.tools.factory import get_tools_for_stage


@CrewBase
class CommitCrew:
    """Commit crew: runs git add -A && git commit. Skips if dry_run is true."""

    agents: List[BaseAgent]
    tasks: List[Task]

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def git_agent(self) -> Agent:
        repo_path = os.path.abspath(os.environ.get("REPO_PATH", os.getcwd()))
        tools = get_tools_for_stage("commit", repo_path)
        return Agent(
            config=self.agents_config["git_agent"],  # type: ignore[index]
            tools=tools,
            llm=get_llm_for_stage("commit"),
            verbose=True,
        )

    @task
    def commit_task(self) -> Task:
        return Task(
            config=self.tasks_config["commit_task"],  # type: ignore[index]
        )

    @crew
    def crew(self) -> Crew:
        """Creates the CommitCrew crew."""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
            tracing=True,
            output_log_file=True,
            memory=False,
        )
