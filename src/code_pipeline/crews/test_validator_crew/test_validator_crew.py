from typing import ClassVar, List

from crewai import Agent, Crew, LLM, Process, Task
from crewai.project import CrewBase, agent, crew, llm, task

from code_pipeline.crews.base import PipelineCrewBase
from code_pipeline.llm import get_llm_for_stage


@CrewBase
class TestValidatorCrew(PipelineCrewBase):
    """Test Validator crew: writes tests and validates they catch bugs."""

    stage: ClassVar[str] = "test_validation"

    @property
    def required_agents(self) -> List[str]:
        return [
            "test_implementer",
            "test_quality_checker",
            "test_coverage_checker",
        ]

    @property
    def required_tasks(self) -> List[str]:
        return [
            "test_implement_task",
            "test_quality_check_task",
            "test_coverage_check_task",
        ]

    @llm
    def test_validation_llm(self) -> LLM:
        return get_llm_for_stage("test_validation")

    @agent
    def test_implementer(self) -> Agent:
        return self._build_agent("test_implementer")

    @agent
    def test_quality_checker(self) -> Agent:
        return self._build_agent("test_quality_checker")

    @agent
    def test_coverage_checker(self) -> Agent:
        return self._build_agent("test_coverage_checker")

    @task
    def test_implement_task(self) -> Task:
        return self._build_task("test_implement_task")

    @task
    def test_quality_check_task(self) -> Task:
        return self._build_task("test_quality_check_task")

    @task
    def test_coverage_check_task(self) -> Task:
        return self._build_task("test_coverage_check_task")

    @crew
    def crew(self) -> Crew:
        """Creates the TestValidatorCrew."""
        return Crew(
            agents=self.agents,  # type: ignore[attr-defined]
            tasks=self.tasks,  # type: ignore[attr-defined]
            process=Process.sequential,
            verbose=True,
        )
