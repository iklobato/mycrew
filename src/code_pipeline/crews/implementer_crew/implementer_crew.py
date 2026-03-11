from crewai import Agent, LLM, Task
from crewai.project import CrewBase, agent, llm, task

from code_pipeline.crews.base import PipelineCrewBase
from code_pipeline.llm import get_llm_for_stage


@CrewBase
class ImplementerCrew(PipelineCrewBase):
    """Implementer crew: writes code, tests, and self-reviews."""

    @llm
    def implement_llm(self) -> LLM:
        return get_llm_for_stage("implement")

    @agent
    def implementer(self) -> Agent:
        return Agent(config=self.agents_config["implementer"])  # type: ignore[index]

    @agent
    def docstring_writer(self) -> Agent:
        return Agent(
            config=self.agents_config["docstring_writer"],  # type: ignore[index]
        )

    @agent
    def type_hint_checker(self) -> Agent:
        return Agent(
            config=self.agents_config["type_hint_checker"],  # type: ignore[index]
        )

    @agent
    def lint_fixer(self) -> Agent:
        return Agent(
            config=self.agents_config["lint_fixer"],  # type: ignore[index]
        )

    @agent
    def self_reviewer(self) -> Agent:
        return Agent(
            config=self.agents_config["self_reviewer"],  # type: ignore[index]
        )

    @task
    def implement_task(self) -> Task:
        return Task(
            config=self.tasks_config["implement_task"],  # type: ignore[index]
        )

    @task
    def docstring_write_task(self) -> Task:
        return Task(
            config=self.tasks_config["docstring_write_task"],  # type: ignore[index]
        )

    @task
    def type_hint_task(self) -> Task:
        return Task(
            config=self.tasks_config["type_hint_task"],  # type: ignore[index]
        )

    @task
    def lint_fix_task(self) -> Task:
        return Task(
            config=self.tasks_config["lint_fix_task"],  # type: ignore[index]
        )

    @task
    def self_review_task(self) -> Task:
        return Task(
            config=self.tasks_config["self_review_task"],  # type: ignore[index]
        )
