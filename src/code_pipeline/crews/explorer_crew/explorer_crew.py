from crewai import Agent, LLM, Task
from crewai.project import CrewBase, agent, llm, task

from code_pipeline.crews.base import PipelineCrewBase
from code_pipeline.llm import get_llm_for_stage


@CrewBase
class ExplorerCrew(PipelineCrewBase):
    """Explorer crew: repo summary, dependency map, and test layout."""

    @llm
    def explore_llm(self) -> LLM:
        return get_llm_for_stage("explore")

    @agent
    def repo_explorer(self) -> Agent:
        return Agent(config=self.agents_config["repo_explorer"])  # type: ignore[index]

    @agent
    def dependency_analyzer(self) -> Agent:
        return Agent(
            config=self.agents_config["dependency_analyzer"],  # type: ignore[index]
        )

    @agent
    def test_layout_scout(self) -> Agent:
        return Agent(
            config=self.agents_config["test_layout_scout"],  # type: ignore[index]
        )

    @agent
    def convention_extractor(self) -> Agent:
        return Agent(
            config=self.agents_config["convention_extractor"],  # type: ignore[index]
        )

    @agent
    def api_boundary_scout(self) -> Agent:
        return Agent(
            config=self.agents_config["api_boundary_scout"],  # type: ignore[index]
        )

    @task
    def explore_task(self) -> Task:
        return Task(
            config=self.tasks_config["explore_task"],  # type: ignore[index]
        )

    @task
    def dependency_analyze_task(self) -> Task:
        return Task(
            config=self.tasks_config["dependency_analyze_task"],  # type: ignore[index]
        )

    @task
    def test_layout_task(self) -> Task:
        return Task(
            config=self.tasks_config["test_layout_task"],  # type: ignore[index]
        )

    @task
    def convention_extract_task(self) -> Task:
        return Task(
            config=self.tasks_config["convention_extract_task"],  # type: ignore[index]
        )

    @task
    def api_boundary_scout_task(self) -> Task:
        return Task(
            config=self.tasks_config["api_boundary_scout_task"],  # type: ignore[index]
        )
