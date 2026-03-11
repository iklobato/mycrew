"""Commit crew: runs git add, commit, then pushes and creates PR."""

from crewai import Agent, LLM, Task
from crewai.project import CrewBase, agent, llm, task

from code_pipeline.crews.base import PipelineCrewBase
from code_pipeline.llm import get_llm_for_stage


@CrewBase
class CommitCrew(PipelineCrewBase):
    """Commit crew: creates branch, commits, then pushes and creates PR via publish agent."""

    @llm
    def commit_llm(self) -> LLM:
        return get_llm_for_stage("commit")

    @llm
    def publish_llm(self) -> LLM:
        return get_llm_for_stage("publish")

    @agent
    def git_agent(self) -> Agent:
        return Agent(config=self.agents_config["git_agent"])  # type: ignore[index]

    @agent
    def commit_message_reviewer(self) -> Agent:
        return Agent(
            config=self.agents_config["commit_message_reviewer"],  # type: ignore[index]
        )

    @agent
    def changelog_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["changelog_agent"],  # type: ignore[index]
        )

    @agent
    def pr_labels_suggester(self) -> Agent:
        return Agent(config=self.agents_config["pr_labels_suggester"])  # type: ignore[index]

    @agent
    def publish_agent(self) -> Agent:
        return Agent(config=self.agents_config["publish_agent"])  # type: ignore[index]

    @task
    def commit_task(self) -> Task:
        return Task(
            config=self.tasks_config["commit_task"],  # type: ignore[index]
        )

    @task
    def commit_message_review_task(self) -> Task:
        return Task(
            config=self.tasks_config["commit_message_review_task"],  # type: ignore[index]
        )

    @task
    def changelog_task(self) -> Task:
        return Task(
            config=self.tasks_config["changelog_task"],  # type: ignore[index]
        )

    @task
    def pr_labels_suggest_task(self) -> Task:
        return Task(
            config=self.tasks_config["pr_labels_suggest_task"],  # type: ignore[index]
        )

    @task
    def publish_task(self) -> Task:
        return Task(
            config=self.tasks_config["publish_task"],  # type: ignore[index]
        )
