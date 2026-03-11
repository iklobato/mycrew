"""Reviewer crew: reviews implementation against plan and task."""

import os
from typing import List, Literal

from crewai import Agent, Crew, Process, Task
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai.project import CrewBase, agent, crew, task
from pydantic import BaseModel, Field

from code_pipeline.llm import get_llm_for_stage
from code_pipeline.tools.factory import get_tools_for_stage


class ReviewVerdict(BaseModel):
    """Structured review verdict. Forces LLM to output APPROVED or ISSUES with list."""

    verdict: Literal["APPROVED", "ISSUES"] = Field(
        description="Exactly APPROVED if implementation meets all criteria, otherwise ISSUES"
    )
    issues: List[str] = Field(
        default_factory=list,
        description="When ISSUES: list of 'file_path: concise description' for each problem",
    )


@CrewBase
class ReviewerCrew:
    """Reviewer crew: reviews implementation and returns APPROVED or ISSUES:..."""

    agents: List[BaseAgent]
    tasks: List[Task]

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def reviewer(self) -> Agent:
        repo_path = os.path.abspath(os.environ.get("REPO_PATH", os.getcwd()))
        serper_enabled = os.environ.get("SERPER_ENABLED", "false").lower() == "true"
        tools = get_tools_for_stage(
            "review",
            repo_path,
            serper_enabled=serper_enabled,
        )
        return Agent(
            config=self.agents_config["reviewer"],  # type: ignore[index]
            tools=tools,
            llm=get_llm_for_stage("review", agent_name="reviewer"),
            verbose=False,
        )

    @agent
    def security_reviewer(self) -> Agent:
        repo_path = os.path.abspath(os.environ.get("REPO_PATH", os.getcwd()))
        serper_enabled = os.environ.get("SERPER_ENABLED", "false").lower() == "true"
        tools = get_tools_for_stage(
            "security_review",
            repo_path,
            serper_enabled=serper_enabled,
        )
        return Agent(
            config=self.agents_config["security_reviewer"],  # type: ignore[index]
            tools=tools,
            llm=get_llm_for_stage("security", agent_name="security_reviewer"),
            verbose=False,
        )

    @agent
    def performance_reviewer(self) -> Agent:
        repo_path = os.path.abspath(os.environ.get("REPO_PATH", os.getcwd()))
        serper_enabled = os.environ.get("SERPER_ENABLED", "false").lower() == "true"
        tools = get_tools_for_stage(
            "security_review",
            repo_path,
            serper_enabled=serper_enabled,
        )
        return Agent(
            config=self.agents_config["performance_reviewer"],  # type: ignore[index]
            tools=tools,
            llm=get_llm_for_stage("auxiliary", agent_name="performance_reviewer"),
            verbose=False,
        )

    @agent
    def accessibility_checker(self) -> Agent:
        repo_path = os.path.abspath(os.environ.get("REPO_PATH", os.getcwd()))
        serper_enabled = os.environ.get("SERPER_ENABLED", "false").lower() == "true"
        tools = get_tools_for_stage(
            "security_review",
            repo_path,
            serper_enabled=serper_enabled,
        )
        return Agent(
            config=self.agents_config["accessibility_checker"],  # type: ignore[index]
            tools=tools,
            llm=get_llm_for_stage("auxiliary", agent_name="accessibility_checker"),
            verbose=False,
        )

    @agent
    def backward_compat_checker(self) -> Agent:
        repo_path = os.path.abspath(os.environ.get("REPO_PATH", os.getcwd()))
        serper_enabled = os.environ.get("SERPER_ENABLED", "false").lower() == "true"
        tools = get_tools_for_stage(
            "security_review",
            repo_path,
            serper_enabled=serper_enabled,
        )
        return Agent(
            config=self.agents_config["backward_compat_checker"],  # type: ignore[index]
            tools=tools,
            llm=get_llm_for_stage("auxiliary", agent_name="backward_compat_checker"),
            verbose=False,
        )

    @agent
    def convention_checker(self) -> Agent:
        repo_path = os.path.abspath(os.environ.get("REPO_PATH", os.getcwd()))
        serper_enabled = os.environ.get("SERPER_ENABLED", "false").lower() == "true"
        tools = get_tools_for_stage(
            "review",
            repo_path,
            serper_enabled=serper_enabled,
        )
        return Agent(
            config=self.agents_config["convention_checker"],  # type: ignore[index]
            tools=tools,
            llm=get_llm_for_stage("auxiliary", agent_name="convention_checker"),
            verbose=False,
        )

    @task
    def review_task(self) -> Task:
        return Task(
            config=self.tasks_config["review_task"],  # type: ignore[index]
            output_pydantic=ReviewVerdict,
        )

    @task
    def security_review_task(self) -> Task:
        return Task(
            config=self.tasks_config["security_review_task"],  # type: ignore[index]
        )

    @task
    def performance_review_task(self) -> Task:
        return Task(
            config=self.tasks_config["performance_review_task"],  # type: ignore[index]
        )

    @task
    def accessibility_review_task(self) -> Task:
        return Task(
            config=self.tasks_config["accessibility_review_task"],  # type: ignore[index]
        )

    @task
    def backward_compat_task(self) -> Task:
        return Task(
            config=self.tasks_config["backward_compat_task"],  # type: ignore[index]
        )

    @task
    def convention_check_task(self) -> Task:
        return Task(
            config=self.tasks_config["convention_check_task"],  # type: ignore[index]
        )

    @crew
    def crew(self) -> Crew:
        """Creates the ReviewerCrew crew."""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=False,
            tracing=False,
            output_log_file=True,
            memory=False,
        )
