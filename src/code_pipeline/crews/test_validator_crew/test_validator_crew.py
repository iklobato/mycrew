from crewai import Agent, Crew, LLM, Process, Task
from crewai.project import CrewBase, agent, crew, llm, task

from code_pipeline.crews.base import PipelineCrewBase
from code_pipeline.llm import get_llm_for_stage


@CrewBase
class TestValidatorCrew(PipelineCrewBase):
    """Test Validator crew: writes tests and validates they catch bugs."""

    @llm
    def test_validation_llm(self) -> LLM:
        return get_llm_for_stage("test_validation")

    @agent
    def test_implementer(self) -> Agent:
        return Agent(
            config=self.agents_config["test_implementer"],  # type: ignore[index]
        )

    @agent
    def test_quality_checker(self) -> Agent:
        return Agent(
            config=self.agents_config["test_quality_checker"],  # type: ignore[index]
        )

    @agent
    def test_coverage_checker(self) -> Agent:
        return Agent(
            config=self.agents_config["test_coverage_checker"],  # type: ignore[index]
        )

    @task
    def test_implement_task(self) -> Task:
        return Task(
            config=self.tasks_config["test_implement_task"],  # type: ignore[index]
        )

    @task
    def test_quality_check_task(self) -> Task:
        return Task(
            config=self.tasks_config["test_quality_check_task"],  # type: ignore[index]
        )

    @task
    def test_coverage_check_task(self) -> Task:
        return Task(
            config=self.tasks_config["test_coverage_check_task"],  # type: ignore[index]
        )

    @crew
    def crew(self) -> Crew:
        """Creates the TestValidatorCrew."""
        return Crew(
            agents=self.agents,  # type: ignore[arg-type]
            tasks=self.tasks,  # type: ignore[arg-type]
            process=Process.sequential,
            verbose=False,
        )
