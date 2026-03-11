from crewai import Agent, LLM, Task
from crewai.project import CrewBase, agent, llm, task

from code_pipeline.crews.base import PipelineCrewBase
from code_pipeline.llm import get_llm_for_stage


@CrewBase
class ArchitectCrew(PipelineCrewBase):
    """Architect crew: produces file-level plan, no code."""

    @llm
    def plan_llm(self) -> LLM:
        return get_llm_for_stage("plan")

    @agent
    def architect(self) -> Agent:
        return Agent(config=self.agents_config["architect"])  # type: ignore[index]

    @agent
    def dependency_orderer(self) -> Agent:
        return Agent(
            config=self.agents_config["dependency_orderer"],  # type: ignore[index]
        )

    @agent
    def refactor_guard(self) -> Agent:
        return Agent(
            config=self.agents_config["refactor_guard"],  # type: ignore[index]
        )

    @agent
    def test_plan_advisor(self) -> Agent:
        return Agent(
            config=self.agents_config["test_plan_advisor"],  # type: ignore[index]
        )

    @agent
    def migration_checker(self) -> Agent:
        return Agent(
            config=self.agents_config["migration_checker"],  # type: ignore[index]
        )

    @agent
    def rollback_planner(self) -> Agent:
        return Agent(
            config=self.agents_config["rollback_planner"],  # type: ignore[index]
        )

    @task
    def plan_task(self) -> Task:
        return Task(
            config=self.tasks_config["plan_task"],  # type: ignore[index]
        )

    @task
    def dependency_order_task(self) -> Task:
        return Task(
            config=self.tasks_config["dependency_order_task"],  # type: ignore[index]
        )

    @task
    def refactor_guard_task(self) -> Task:
        return Task(
            config=self.tasks_config["refactor_guard_task"],  # type: ignore[index]
        )

    @task
    def test_plan_task(self) -> Task:
        return Task(
            config=self.tasks_config["test_plan_task"],  # type: ignore[index]
        )

    @task
    def migration_check_task(self) -> Task:
        return Task(
            config=self.tasks_config["migration_check_task"],  # type: ignore[index]
        )

    @task
    def rollback_plan_task(self) -> Task:
        return Task(
            config=self.tasks_config["rollback_plan_task"],  # type: ignore[index]
        )
