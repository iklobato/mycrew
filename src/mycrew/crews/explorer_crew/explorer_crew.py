from typing import ClassVar, List

from crewai import Agent, LLM, Task
from crewai.project import CrewBase, agent, llm, task

from mycrew.crews.base import PipelineCrewBase
from mycrew.llm import get_llm_for_stage


@CrewBase
class ExplorerCrew(PipelineCrewBase):
    """Explorer crew: repo summary, dependency map, and test layout."""

    stage: ClassVar[str] = "explore"

    @property
    def required_agents(self) -> List[str]:
        return [
            "repo_explorer",
            "dependency_analyzer",
            "test_layout_scout",
            "convention_extractor",
            "internal_deps_scout",
            "api_boundary_scout",
        ]

    @property
    def required_tasks(self) -> List[str]:
        return [
            "explore_task",
            "dependency_analyze_task",
            "test_layout_task",
            "convention_extract_task",
            "internal_deps_task",
            "api_boundary_scout_task",
        ]

    @llm
    def explore_llm(self) -> LLM:
        return get_llm_for_stage("explore")

    @agent
    def repo_explorer(self) -> Agent:
        return self._build_agent("repo_explorer")

    @agent
    def dependency_analyzer(self) -> Agent:
        return self._build_agent("dependency_analyzer")

    @agent
    def test_layout_scout(self) -> Agent:
        return self._build_agent("test_layout_scout")

    @agent
    def convention_extractor(self) -> Agent:
        return self._build_agent("convention_extractor")

    @agent
    def internal_deps_scout(self) -> Agent:
        return self._build_agent("internal_deps_scout")

    @agent
    def api_boundary_scout(self) -> Agent:
        return self._build_agent("api_boundary_scout")

    @task
    def explore_task(self) -> Task:
        return self._build_task("explore_task")

    @task
    def dependency_analyze_task(self) -> Task:
        return self._build_task("dependency_analyze_task")

    @task
    def test_layout_task(self) -> Task:
        return self._build_task("test_layout_task")

    @task
    def convention_extract_task(self) -> Task:
        return self._build_task("convention_extract_task")

    @task
    def internal_deps_task(self) -> Task:
        return self._build_task("internal_deps_task")

    @task
    def api_boundary_scout_task(self) -> Task:
        return self._build_task("api_boundary_scout_task")
