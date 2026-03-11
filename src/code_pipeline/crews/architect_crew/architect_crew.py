import os
from typing import List

from crewai import Agent, Crew, Process, Task
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai.project import CrewBase, agent, crew, task

from code_pipeline.llm import get_llm_for_stage
from code_pipeline.tools.factory import get_tools_for_stage


@CrewBase
class ArchitectCrew:
    """Architect crew: produces file-level plan, no code."""

    agents: List[BaseAgent]
    tasks: List[Task]

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def architect(self) -> Agent:
        repo_path = os.path.abspath(os.environ.get("REPO_PATH", os.getcwd()))
        github_repo = (os.environ.get("GITHUB_REPO", "") or "").strip() or None
        serper_enabled = os.environ.get("SERPER_ENABLED", "false").lower() == "true"
        tools = get_tools_for_stage(
            "plan",
            repo_path,
            github_repo=github_repo,
            serper_enabled=serper_enabled,
        )
        return Agent(
            config=self.agents_config["architect"],  # type: ignore[index]
            tools=tools,
            llm=get_llm_for_stage("plan", agent_name="architect"),
            verbose=False,
        )

    @agent
    def dependency_orderer(self) -> Agent:
        repo_path = os.path.abspath(os.environ.get("REPO_PATH", os.getcwd()))
        serper_enabled = os.environ.get("SERPER_ENABLED", "false").lower() == "true"
        tools = get_tools_for_stage(
            "plan",
            repo_path,
            serper_enabled=serper_enabled,
        )
        return Agent(
            config=self.agents_config["dependency_orderer"],  # type: ignore[index]
            tools=tools,
            llm=get_llm_for_stage("auxiliary", agent_name="dependency_orderer"),
            verbose=False,
        )

    @agent
    def refactor_guard(self) -> Agent:
        repo_path = os.path.abspath(os.environ.get("REPO_PATH", os.getcwd()))
        tools = get_tools_for_stage("refactor_guard", repo_path)
        return Agent(
            config=self.agents_config["refactor_guard"],  # type: ignore[index]
            tools=tools,
            llm=get_llm_for_stage("auxiliary", agent_name="refactor_guard"),
            verbose=False,
        )

    @agent
    def test_plan_advisor(self) -> Agent:
        repo_path = os.path.abspath(os.environ.get("REPO_PATH", os.getcwd()))
        serper_enabled = os.environ.get("SERPER_ENABLED", "false").lower() == "true"
        tools = get_tools_for_stage(
            "plan",
            repo_path,
            serper_enabled=serper_enabled,
        )
        return Agent(
            config=self.agents_config["test_plan_advisor"],  # type: ignore[index]
            tools=tools,
            llm=get_llm_for_stage("auxiliary", agent_name="test_plan_advisor"),
            verbose=False,
        )

    @agent
    def migration_checker(self) -> Agent:
        repo_path = os.path.abspath(os.environ.get("REPO_PATH", os.getcwd()))
        tools = get_tools_for_stage("refactor_guard", repo_path)
        return Agent(
            config=self.agents_config["migration_checker"],  # type: ignore[index]
            tools=tools,
            llm=get_llm_for_stage("auxiliary", agent_name="migration_checker"),
            verbose=False,
        )

    @agent
    def rollback_planner(self) -> Agent:
        repo_path = os.path.abspath(os.environ.get("REPO_PATH", os.getcwd()))
        tools = get_tools_for_stage("refactor_guard", repo_path)
        return Agent(
            config=self.agents_config["rollback_planner"],  # type: ignore[index]
            tools=tools,
            llm=get_llm_for_stage("auxiliary", agent_name="rollback_planner"),
            verbose=False,
        )

    @task
    def plan_task(self) -> Task:
        return Task(
            config=self.tasks_config["plan_task"],  # type: ignore[index]
        )

    @task
    def dependency_order_task(self) -> Task:
        return Task(
            config=self.tasks_config["dependency_order_task"],  # type: ignore[index]
        )

    @task
    def refactor_guard_task(self) -> Task:
        return Task(
            config=self.tasks_config["refactor_guard_task"],  # type: ignore[index]
        )

    @task
    def test_plan_task(self) -> Task:
        return Task(
            config=self.tasks_config["test_plan_task"],  # type: ignore[index]
        )

    @task
    def migration_check_task(self) -> Task:
        return Task(
            config=self.tasks_config["migration_check_task"],  # type: ignore[index]
        )

    @task
    def rollback_plan_task(self) -> Task:
        return Task(
            config=self.tasks_config["rollback_plan_task"],  # type: ignore[index]
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=False,
            tracing=False,
            output_log_file=True,
            memory=False,
        )
