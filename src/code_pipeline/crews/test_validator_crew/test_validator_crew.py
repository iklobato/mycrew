import os
from typing import List

from crewai import Agent, Crew, Process, Task
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai.project import CrewBase, agent, crew, task
from code_pipeline.llm import get_llm_for_stage
from code_pipeline.tools.factory import get_tools_for_stage


@CrewBase
class TestValidatorCrew:
    """Test Validator crew: writes tests and validates they catch bugs."""

    agents: List[BaseAgent]
    tasks: List[Task]

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def test_implementer(self) -> Agent:
        repo_path = os.path.abspath(os.environ.get("REPO_PATH", os.getcwd()))
        tools = get_tools_for_stage("test_validation", repo_path)
        return Agent(
            config=self.agents_config["test_implementer"],  # type: ignore[index]
            tools=tools,
            llm=get_llm_for_stage("test_validation", agent_name="test_implementer"),
            verbose=False,
        )

    @agent
    def test_quality_checker(self) -> Agent:
        repo_path = os.path.abspath(os.environ.get("REPO_PATH", os.getcwd()))
        tools = get_tools_for_stage("test_validation", repo_path)
        return Agent(
            config=self.agents_config["test_quality_checker"],  # type: ignore[index]
            tools=tools,
            llm=get_llm_for_stage("test_validation", agent_name="test_quality_checker"),
            verbose=False,
        )

    @agent
    def test_coverage_checker(self) -> Agent:
        repo_path = os.path.abspath(os.environ.get("REPO_PATH", os.getcwd()))
        tools = get_tools_for_stage("test_validation", repo_path)
        return Agent(
            config=self.agents_config["test_coverage_checker"],  # type: ignore[index]
            tools=tools,
            llm=get_llm_for_stage(
                "test_validation", agent_name="test_coverage_checker"
            ),
            verbose=False,
        )

    @task
    def test_implement_task(self) -> Task:
        return Task(
            config=self.tasks_config["test_implement_task"],  # type: ignore[index]
        )

    @task
    def test_quality_check_task(self) -> Task:
        return Task(
            config=self.tasks_config["test_quality_check_task"],  # type: ignore[index]
        )

    @task
    def test_coverage_check_task(self) -> Task:
        return Task(
            config=self.tasks_config["test_coverage_check_task"],  # type: ignore[index]
        )

    @crew
    def crew(self) -> Crew:
        """Creates the TestValidatorCrew"""
        return Crew(
            agents=self.agents,  # type: ignore[arg-type]
            tasks=self.tasks,  # type: ignore[arg-type]
            process=Process.sequential,
            verbose=False,
        )
