import os
from typing import List

from crewai import Agent, Crew, Process, Task
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai.project import CrewBase, agent, crew, task

from code_pipeline.llm import get_llm_for_stage
from code_pipeline.tools.factory import get_tools_for_stage


@CrewBase
class ExplorerCrew:
    """Explorer crew: repo summary, dependency map, and test layout."""

    agents: List[BaseAgent]
    tasks: List[Task]

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def repo_explorer(self) -> Agent:
        repo_path = os.path.abspath(os.environ.get("REPO_PATH", os.getcwd()))
        docs_url = (os.environ.get("DOCS_URL", "") or "").strip() or None
        serper_enabled = os.environ.get("SERPER_ENABLED", "false").lower() == "true"
        serper_n_results = int(os.environ.get("SERPER_N_RESULTS", "5"))
        tools = get_tools_for_stage(
            "explore",
            repo_path,
            docs_url=docs_url,
            serper_enabled=serper_enabled,
            serper_n_results=serper_n_results,
        )
        return Agent(
            config=self.agents_config["repo_explorer"],  # type: ignore[index]
            tools=tools,
            llm=get_llm_for_stage("explore", "repo_explorer"),
            verbose=False,
        )

    @agent
    def dependency_analyzer(self) -> Agent:
        repo_path = os.path.abspath(os.environ.get("REPO_PATH", os.getcwd()))
        serper_enabled = os.environ.get("SERPER_ENABLED", "false").lower() == "true"
        serper_n_results = int(os.environ.get("SERPER_N_RESULTS", "5"))
        tools = get_tools_for_stage(
            "explore",
            repo_path,
            serper_enabled=serper_enabled,
            serper_n_results=serper_n_results,
        )
        return Agent(
            config=self.agents_config["dependency_analyzer"],  # type: ignore[index]
            tools=tools,
            llm=get_llm_for_stage("explore", "dependency_analyzer"),
            verbose=False,
        )

    @agent
    def test_layout_scout(self) -> Agent:
        repo_path = os.path.abspath(os.environ.get("REPO_PATH", os.getcwd()))
        serper_enabled = os.environ.get("SERPER_ENABLED", "false").lower() == "true"
        serper_n_results = int(os.environ.get("SERPER_N_RESULTS", "5"))
        tools = get_tools_for_stage(
            "explore",
            repo_path,
            serper_enabled=serper_enabled,
            serper_n_results=serper_n_results,
        )
        return Agent(
            config=self.agents_config["test_layout_scout"],  # type: ignore[index]
            tools=tools,
            llm=get_llm_for_stage("explore", "test_layout_scout"),
            verbose=False,
        )

    @agent
    def convention_extractor(self) -> Agent:
        repo_path = os.path.abspath(os.environ.get("REPO_PATH", os.getcwd()))
        serper_enabled = os.environ.get("SERPER_ENABLED", "false").lower() == "true"
        serper_n_results = int(os.environ.get("SERPER_N_RESULTS", "5"))
        tools = get_tools_for_stage(
            "explore",
            repo_path,
            serper_enabled=serper_enabled,
            serper_n_results=serper_n_results,
        )
        return Agent(
            config=self.agents_config["convention_extractor"],  # type: ignore[index]
            tools=tools,
            llm=get_llm_for_stage("explore", "convention_extractor"),
            verbose=False,
        )

    @agent
    def api_boundary_scout(self) -> Agent:
        repo_path = os.path.abspath(os.environ.get("REPO_PATH", os.getcwd()))
        serper_enabled = os.environ.get("SERPER_ENABLED", "false").lower() == "true"
        serper_n_results = int(os.environ.get("SERPER_N_RESULTS", "5"))
        tools = get_tools_for_stage(
            "explore",
            repo_path,
            serper_enabled=serper_enabled,
            serper_n_results=serper_n_results,
        )
        return Agent(
            config=self.agents_config["api_boundary_scout"],  # type: ignore[index]
            tools=tools,
            llm=get_llm_for_stage("explore", "api_boundary_scout"),
            verbose=False,
        )

    @task
    def explore_task(self) -> Task:
        return Task(
            config=self.tasks_config["explore_task"],  # type: ignore[index]
        )

    @task
    def dependency_analyze_task(self) -> Task:
        return Task(
            config=self.tasks_config["dependency_analyze_task"],  # type: ignore[index]
        )

    @task
    def test_layout_task(self) -> Task:
        return Task(
            config=self.tasks_config["test_layout_task"],  # type: ignore[index]
        )

    @task
    def convention_extract_task(self) -> Task:
        return Task(
            config=self.tasks_config["convention_extract_task"],  # type: ignore[index]
        )

    @task
    def api_boundary_scout_task(self) -> Task:
        return Task(
            config=self.tasks_config["api_boundary_scout_task"],  # type: ignore[index]
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
