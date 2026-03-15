"""Reviewer crew: reviews implementation against plan and task."""

from typing import Any, List, Literal, ClassVar

from crewai import Agent, LLM, Process, Task
from crewai.project import CrewBase, agent, llm, task
from pydantic import BaseModel, Field

from mycrew.crews.base import PipelineCrewBase
from mycrew.llm import get_llm_for_stage


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

    stage: ClassVar[str] = "review"

    @property
    def required_agents(self) -> List[str]:
        return [
            "reviewer",
            "security_reviewer",
            "performance_reviewer",
            "accessibility_checker",
            "backward_compat_checker",
            "convention_checker",
        ]

    @property
    def required_tasks(self) -> List[str]:
        return [
            "review_task",
            "security_review_task",
            "performance_review_task",
            "accessibility_review_task",
            "backward_compat_task",
            "convention_check_task",
        ]

    @llm
    def review_llm(self) -> LLM:
        return get_llm_for_stage("review")

    @llm
    def security_review_llm(self) -> LLM:
        return get_llm_for_stage("security")

    @agent
    def reviewer(self) -> Agent:
        return self._build_agent("reviewer")

    @agent
    def security_reviewer(self) -> Agent:
        return self._build_agent("security_reviewer")

    @agent
    def performance_reviewer(self) -> Agent:
        return self._build_agent("performance_reviewer")

    @agent
    def accessibility_checker(self) -> Agent:
        return self._build_agent("accessibility_checker")

    @agent
    def backward_compat_checker(self) -> Agent:
        return self._build_agent("backward_compat_checker")

    @agent
    def convention_checker(self) -> Agent:
        return self._build_agent("convention_checker")

    @task
    def review_task(self) -> Task:
        return self._build_task("review_task")

    @task
    def security_review_task(self) -> Task:
        return self._build_task("security_review_task")

    @task
    def performance_review_task(self) -> Task:
        return self._build_task("performance_review_task")

    @task
    def accessibility_review_task(self) -> Task:
        return self._build_task("accessibility_review_task")

    @task
    def backward_compat_task(self) -> Task:
        return self._build_task("backward_compat_task")

    @task
    def convention_check_task(self) -> Task:
        return self._build_task("convention_check_task")
