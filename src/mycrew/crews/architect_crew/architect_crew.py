from typing import ClassVar, List

from crewai import Agent, LLM, Task
from crewai.project import CrewBase, agent, llm, task

from mycrew.crews.base import PipelineCrewBase
from mycrew.llm import get_llm_for_stage


@CrewBase
class ArchitectCrew(PipelineCrewBase):
    """Architect crew: produces file-level plan, no code."""

    stage: ClassVar[str] = "plan"

    @property
    def required_agents(self) -> List[str]:
        return [
            "architect",
            "dependency_orderer",
            "refactor_guard",
            "test_plan_advisor",
            "migration_checker",
            "rollback_planner",
        ]

    @property
    def required_tasks(self) -> List[str]:
        return [
            "plan_task",
            "dependency_order_task",
            "refactor_guard_task",
            "test_plan_task",
            "migration_check_task",
            "rollback_plan_task",
        ]

    @llm
    def plan_llm(self) -> LLM:
        return get_llm_for_stage("plan")

    @agent
    def architect(self) -> Agent:
        return self._build_agent("architect")

    @agent
    def dependency_orderer(self) -> Agent:
        return self._build_agent("dependency_orderer")

    @agent
    def refactor_guard(self) -> Agent:
        return self._build_agent("refactor_guard")

    @agent
    def test_plan_advisor(self) -> Agent:
        return self._build_agent("test_plan_advisor")

    @agent
    def migration_checker(self) -> Agent:
        return self._build_agent("migration_checker")

    @agent
    def rollback_planner(self) -> Agent:
        return self._build_agent("rollback_planner")

    @task
    def plan_task(self) -> Task:
        return self._build_task("plan_task")

    @task
    def dependency_order_task(self) -> Task:
        return self._build_task("dependency_order_task")

    @task
    def refactor_guard_task(self) -> Task:
        return self._build_task("refactor_guard_task")

    @task
    def test_plan_task(self) -> Task:
        return self._build_task("test_plan_task")

    @task
    def migration_check_task(self) -> Task:
        return self._build_task("migration_check_task")

    @task
    def rollback_plan_task(self) -> Task:
        return self._build_task("rollback_plan_task")
