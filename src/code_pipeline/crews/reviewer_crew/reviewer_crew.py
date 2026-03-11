"""Reviewer crew: reviews implementation against plan and task."""

from typing import List, Literal

from crewai import Agent, LLM, Task
from crewai.project import CrewBase, agent, llm, task
from pydantic import BaseModel, Field

from code_pipeline.crews.base import PipelineCrewBase
from code_pipeline.llm import get_llm_for_stage


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
class ReviewerCrew(PipelineCrewBase):
    """Reviewer crew: reviews implementation and returns APPROVED or ISSUES:..."""

    @llm
    def review_llm(self) -> LLM:
        return get_llm_for_stage("review")

    @llm
    def security_review_llm(self) -> LLM:
        return get_llm_for_stage("security")

    @agent
    def reviewer(self) -> Agent:
        return Agent(config=self.agents_config["reviewer"])  # type: ignore[index]

    @agent
    def security_reviewer(self) -> Agent:
        return Agent(
            config=self.agents_config["security_reviewer"],  # type: ignore[index]
        )

    @agent
    def performance_reviewer(self) -> Agent:
        return Agent(
            config=self.agents_config["performance_reviewer"],  # type: ignore[index]
        )

    @agent
    def accessibility_checker(self) -> Agent:
        return Agent(
            config=self.agents_config["accessibility_checker"],  # type: ignore[index]
        )

    @agent
    def backward_compat_checker(self) -> Agent:
        return Agent(
            config=self.agents_config["backward_compat_checker"],  # type: ignore[index]
        )

    @agent
    def convention_checker(self) -> Agent:
        return Agent(
            config=self.agents_config["convention_checker"],  # type: ignore[index]
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
