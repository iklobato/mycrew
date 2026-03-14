from typing import ClassVar, List

from crewai import Agent, LLM, Task
from crewai.project import CrewBase, agent, llm, task

from code_pipeline.crews.base import PipelineCrewBase
from code_pipeline.llm import get_llm_for_stage


@CrewBase
class ImplementerCrew(PipelineCrewBase):
    """Implementer crew: writes code, tests, and self-reviews."""

    stage: ClassVar[str] = "implement"

    @property
    def required_agents(self) -> List[str]:
        return [
            "implementer",
            "docstring_writer",
            "type_hint_checker",
            "lint_fixer",
            "self_reviewer",
        ]

    @property
    def required_tasks(self) -> List[str]:
        return [
            "implement_task",
            "docstring_write_task",
            "type_hint_task",
            "lint_fix_task",
            "self_review_task",
        ]

    @llm
    def implement_llm(self) -> LLM:
        return get_llm_for_stage("implement")

    @agent
    def implementer(self) -> Agent:
        return self._build_agent("implementer")

    @agent
    def docstring_writer(self) -> Agent:
        return self._build_agent("docstring_writer")

    @agent
    def type_hint_checker(self) -> Agent:
        return self._build_agent("type_hint_checker")

    @agent
    def lint_fixer(self) -> Agent:
        return self._build_agent("lint_fixer")

    @agent
    def self_reviewer(self) -> Agent:
        return self._build_agent("self_reviewer")

    @task
    def implement_task(self) -> Task:
        return self._build_task("implement_task")

    @task
    def docstring_write_task(self) -> Task:
        return self._build_task("docstring_write_task")

    @task
    def type_hint_task(self) -> Task:
        return self._build_task("type_hint_task")

    @task
    def lint_fix_task(self) -> Task:
        return self._build_task("lint_fix_task")

    @task
    def self_review_task(self) -> Task:
        return self._build_task("self_review_task")
