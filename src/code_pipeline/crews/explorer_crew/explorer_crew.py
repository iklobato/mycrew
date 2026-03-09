import os
from typing import List

from crewai import Agent, Crew, Process, Task
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai.project import CrewBase, agent, crew, task

from code_pipeline.llm import get_llm_for_stage
from code_pipeline.tools.factory import get_tools_for_stage


@CrewBase
class ExplorerCrew:
    """Explorer crew: produces structured repo summary (stack, files, conventions)."""

    agents: List[BaseAgent]
    tasks: List[Task]

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def repo_explorer(self) -> Agent:
        repo_path = os.path.abspath(os.environ.get("REPO_PATH", os.getcwd()))
        docs_url = (os.environ.get("DOCS_URL", "") or "").strip() or None
        tools = get_tools_for_stage("explore", repo_path, docs_url=docs_url)
        return Agent(
            config=self.agents_config["repo_explorer"],  # type: ignore[index]
            tools=tools,
            llm=get_llm_for_stage("explore"),
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
            tracing=True,
            output_log_file=True,
            memory=False,
        )
