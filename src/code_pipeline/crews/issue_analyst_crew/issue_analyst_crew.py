"""Issue Analyst crew: parses raw issue cards into structured requirements."""

from typing import List

from crewai import Agent, Crew, Process, Task
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai.project import CrewBase, agent, crew, task

from code_pipeline.llm import get_llm_for_stage
from code_pipeline.settings import get_pipeline_context
from code_pipeline.tools.factory import get_tools_for_stage


@CrewBase
class IssueAnalystCrew:
    """Issue Analyst crew: extracts structured requirements and validates scope."""

    agents: List[BaseAgent]
    tasks: List[Task]

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def issue_analyst(self) -> Agent:
        ctx = get_pipeline_context()
        tools = get_tools_for_stage(
            "analyze_issue",
            ctx.repo_path,
            github_repo=ctx.github_repo or None,
            serper_enabled=ctx.serper_enabled,
        )
        return Agent(
            config=self.agents_config["issue_analyst"],  # type: ignore[index]
            tools=tools,
            llm=get_llm_for_stage("analyze_issue", "issue_analyst"),
            verbose=False,
        )

    @agent
    def scope_validator(self) -> Agent:
        ctx = get_pipeline_context()
        tools = get_tools_for_stage("scope_validate", ctx.repo_path)
        return Agent(
            config=self.agents_config["scope_validator"],  # type: ignore[index]
            tools=tools,
            llm=get_llm_for_stage("analyze_issue", "scope_validator"),
            verbose=False,
        )

    @agent
    def similar_issues_synthesizer(self) -> Agent:
        ctx = get_pipeline_context()
        tools = get_tools_for_stage(
            "analyze_issue",
            ctx.repo_path,
            serper_enabled=ctx.serper_enabled,
        )
        return Agent(
            config=self.agents_config["similar_issues_synthesizer"],  # type: ignore[index]
            tools=tools,
            llm=get_llm_for_stage("analyze_issue", "similar_issues_synthesizer"),
            verbose=False,
        )

    @agent
    def acceptance_criteria_normalizer(self) -> Agent:
        ctx = get_pipeline_context()
        tools = get_tools_for_stage("scope_validate", ctx.repo_path)
        return Agent(
            config=self.agents_config["acceptance_criteria_normalizer"],  # type: ignore[index]
            tools=tools,
            llm=get_llm_for_stage("analyze_issue", "acceptance_criteria_normalizer"),
            verbose=False,
        )

    @task
    def similar_issues_task(self) -> Task:
        return Task(
            config=self.tasks_config["similar_issues_task"],  # type: ignore[index]
        )

    @task
    def analyze_task(self) -> Task:
        return Task(
            config=self.tasks_config["analyze_task"],  # type: ignore[index]
        )

    @task
    def validate_scope_task(self) -> Task:
        return Task(
            config=self.tasks_config["validate_scope_task"],  # type: ignore[index]
        )

    @task
    def acceptance_criteria_normalize_task(self) -> Task:
        return Task(
            config=self.tasks_config["acceptance_criteria_normalize_task"],  # type: ignore[index]
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
