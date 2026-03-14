"""Commit crew: runs git add, commit, then pushes and creates PR."""

from typing import ClassVar, List

from crewai import Agent, LLM, Task
from crewai.project import CrewBase, agent, llm, task

from mycrew.crews.base import PipelineCrewBase
from mycrew.llm import get_llm_for_stage


@CrewBase
class CommitCrew(PipelineCrewBase):
    """Commit crew: creates branch, commits, then pushes and creates PR via publish agent."""

    stage: ClassVar[str] = "commit"

    @property
    def required_agents(self) -> List[str]:
        return [
            "git_agent",
            "commit_message_reviewer",
            "changelog_agent",
            "pr_labels_suggester",
            "publish_agent",
        ]

    @property
    def required_tasks(self) -> List[str]:
        return [
            "commit_task",
            "commit_message_review_task",
            "changelog_task",
            "pr_labels_suggest_task",
            "publish_task",
        ]

    @llm
    def commit_llm(self) -> LLM:
        return get_llm_for_stage("commit")

    @llm
    def publish_llm(self) -> LLM:
        return get_llm_for_stage("publish")

    @agent
    def git_agent(self) -> Agent:
        return self._build_agent("git_agent")

    @agent
    def commit_message_reviewer(self) -> Agent:
        return self._build_agent("commit_message_reviewer")

    @agent
    def changelog_agent(self) -> Agent:
        return self._build_agent("changelog_agent")

    @agent
    def pr_labels_suggester(self) -> Agent:
        return self._build_agent("pr_labels_suggester")

    @agent
    def publish_agent(self) -> Agent:
        return self._build_agent("publish_agent")

    @task
    def commit_task(self) -> Task:
        return self._build_task("commit_task")

    @task
    def commit_message_review_task(self) -> Task:
        return self._build_task("commit_message_review_task")

    @task
    def changelog_task(self) -> Task:
        return self._build_task("changelog_task")

    @task
    def pr_labels_suggest_task(self) -> Task:
        return self._build_task("pr_labels_suggest_task")

    @task
    def publish_task(self) -> Task:
        return self._build_task("publish_task")
