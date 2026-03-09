import os
from typing import List

from crewai import Agent, Crew, Process, Task
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai.project import CrewBase, agent, crew, task
from code_pipeline.llm import get_llm_for_stage
from code_pipeline.tools.factory import get_tools_for_stage


@CrewBase
class ImplementerCrew:
    """Implementer crew: writes code, tests, and self-reviews."""

    agents: List[BaseAgent]
    tasks: List[Task]

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def implementer(self) -> Agent:
        repo_path = os.path.abspath(os.environ.get("REPO_PATH", os.getcwd()))
        tools = get_tools_for_stage("implement", repo_path)
        return Agent(
            config=self.agents_config["implementer"],  # type: ignore[index]
            tools=tools,
            llm=get_llm_for_stage("implement"),
            verbose=False,
        )

    @agent
    def test_writer(self) -> Agent:
        repo_path = os.path.abspath(os.environ.get("REPO_PATH", os.getcwd()))
        tools = get_tools_for_stage("test_write", repo_path)
        return Agent(
            config=self.agents_config["test_writer"],  # type: ignore[index]
            tools=tools,
            llm=get_llm_for_stage("auxiliary"),
            verbose=False,
        )

    @agent
    def docstring_writer(self) -> Agent:
        repo_path = os.path.abspath(os.environ.get("REPO_PATH", os.getcwd()))
        tools = get_tools_for_stage("test_write", repo_path)
        return Agent(
            config=self.agents_config["docstring_writer"],  # type: ignore[index]
            tools=tools,
            llm=get_llm_for_stage("auxiliary"),
            verbose=False,
        )

    @agent
    def type_hint_checker(self) -> Agent:
        repo_path = os.path.abspath(os.environ.get("REPO_PATH", os.getcwd()))
        tools = get_tools_for_stage("test_write", repo_path)
        return Agent(
            config=self.agents_config["type_hint_checker"],  # type: ignore[index]
            tools=tools,
            llm=get_llm_for_stage("auxiliary"),
            verbose=False,
        )

    @agent
    def lint_fixer(self) -> Agent:
        repo_path = os.path.abspath(os.environ.get("REPO_PATH", os.getcwd()))
        tools = get_tools_for_stage("implement", repo_path)
        return Agent(
            config=self.agents_config["lint_fixer"],  # type: ignore[index]
            tools=tools,
            llm=get_llm_for_stage("auxiliary"),
            verbose=False,
        )

    @agent
    def self_reviewer(self) -> Agent:
        repo_path = os.path.abspath(os.environ.get("REPO_PATH", os.getcwd()))
        tools = get_tools_for_stage("self_review", repo_path)
        return Agent(
            config=self.agents_config["self_reviewer"],  # type: ignore[index]
            tools=tools,
            llm=get_llm_for_stage("auxiliary"),
            verbose=False,
        )

    @task
    def implement_task(self) -> Task:
        return Task(
            config=self.tasks_config["implement_task"],  # type: ignore[index]
        )

    @task
    def docstring_write_task(self) -> Task:
        return Task(
            config=self.tasks_config["docstring_write_task"],  # type: ignore[index]
        )

    @task
    def type_hint_task(self) -> Task:
        return Task(
            config=self.tasks_config["type_hint_task"],  # type: ignore[index]
        )

    @task
    def test_write_task(self) -> Task:
        return Task(
            config=self.tasks_config["test_write_task"],  # type: ignore[index]
        )

    @task
    def lint_fix_task(self) -> Task:
        return Task(
            config=self.tasks_config["lint_fix_task"],  # type: ignore[index]
        )

    @task
    def self_review_task(self) -> Task:
        return Task(
            config=self.tasks_config["self_review_task"],  # type: ignore[index]
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=False,
            tracing=True,
            output_log_file=True,
            memory=False,
        )
