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
        docs_url = (os.environ.get("DOCS_URL", "") or "").strip() or None
        tools = get_tools_for_stage("review", repo_path, docs_url=docs_url)
        return Agent(
            config=self.agents_config["reviewer"],  # type: ignore[index]
            tools=tools,
            llm=get_llm_for_stage("review"),
            verbose=False,
        )

    @task
    def review_task(self) -> Task:
        return Task(
            config=self.tasks_config["review_task"],  # type: ignore[index]
            output_pydantic=ReviewVerdict,
        )

    @crew
    def crew(self) -> Crew:
        """Creates the ReviewerCrew crew."""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=False,
            tracing=True,
            output_log_file=True,
            memory=False,
        )
