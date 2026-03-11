"""Clarify crew: detects ambiguities, prioritizes, asks human before planning."""

from typing import List

from crewai import Agent, Crew, Process, Task
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai.project import CrewBase, agent, crew, task

from code_pipeline.llm import get_llm_for_stage
from code_pipeline.settings import get_pipeline_context
from code_pipeline.tools.factory import get_tools_for_stage
from code_pipeline.tools.human_tool import ask_human


@CrewBase
class ClarifyCrew:
    """Clarify crew: ambiguity detection, prioritization, human questions."""

    agents: List[BaseAgent]
    tasks: List[Task]

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def ambiguity_detector(self) -> Agent:
        ctx = get_pipeline_context()
        tools = get_tools_for_stage("scope_validate", ctx.repo_path)
        return Agent(
            config=self.agents_config["ambiguity_detector"],  # type: ignore[index]
            tools=tools,
            llm=get_llm_for_stage("auxiliary", agent_name="ambiguity_detector"),
            verbose=False,
        )

    @agent
    def question_prioritizer(self) -> Agent:
        ctx = get_pipeline_context()
        tools = get_tools_for_stage("scope_validate", ctx.repo_path)
        return Agent(
            config=self.agents_config["question_prioritizer"],  # type: ignore[index]
            tools=tools,
            llm=get_llm_for_stage("auxiliary", agent_name="question_prioritizer"),
            verbose=False,
        )

    @agent
    def clarifier(self) -> Agent:
        return Agent(
            config=self.agents_config["clarifier"],  # type: ignore[index]
            tools=[ask_human],
            llm=get_llm_for_stage("analyze_issue", agent_name="clarifier"),
            verbose=False,
        )

    @task
    def ambiguity_detect_task(self) -> Task:
        return Task(
            config=self.tasks_config["ambiguity_detect_task"],  # type: ignore[index]
        )

    @task
    def question_prioritize_task(self) -> Task:
        return Task(
            config=self.tasks_config["question_prioritize_task"],  # type: ignore[index]
        )

    @task
    def clarify_task(self) -> Task:
        return Task(
            config=self.tasks_config["clarify_task"],  # type: ignore[index]
        )

    @crew
    def crew(self) -> Crew:
        """Creates the ClarifyCrew crew."""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=False,
            tracing=False,
        )
