"""Commit crew: runs git add, commit, then pushes and creates PR."""

from typing import List

from crewai import Agent, Crew, Process, Task
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai.project import CrewBase, agent, crew, task

from code_pipeline.llm import get_llm_for_stage
from code_pipeline.settings import get_pipeline_context
from code_pipeline.tools.factory import get_tools_for_stage


@CrewBase
class CommitCrew:
    """Commit crew: creates branch, commits, then pushes and creates PR via publish agent."""

    agents: List[BaseAgent]
    tasks: List[Task]

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def git_agent(self) -> Agent:
        ctx = get_pipeline_context()
        tools = get_tools_for_stage("commit", ctx.repo_path)
        return Agent(
            config=self.agents_config["git_agent"],  # type: ignore[index]
            tools=tools,
            llm=get_llm_for_stage("commit", agent_name="git_agent"),
            verbose=False,
            max_iter=3,  # Limit iterations to prevent infinite loops
            max_rpm=10,  # Limit requests per minute
        )

    @agent
    def commit_message_reviewer(self) -> Agent:
        ctx = get_pipeline_context()
        tools = get_tools_for_stage("commit_review", ctx.repo_path)
        return Agent(
            config=self.agents_config["commit_message_reviewer"],  # type: ignore[index]
            tools=tools,
            llm=get_llm_for_stage("auxiliary", agent_name="commit_message_reviewer"),
            verbose=False,
            max_iter=3,
            max_rpm=10,
        )

    @agent
    def changelog_agent(self) -> Agent:
        ctx = get_pipeline_context()
        tools = get_tools_for_stage("changelog", ctx.repo_path)
        return Agent(
            config=self.agents_config["changelog_agent"],  # type: ignore[index]
            tools=tools,
            llm=get_llm_for_stage("auxiliary", agent_name="changelog_agent"),
            verbose=False,
            max_iter=3,
            max_rpm=10,
        )

    @agent
    def pr_labels_suggester(self) -> Agent:
        return Agent(
            config=self.agents_config["pr_labels_suggester"],  # type: ignore[index]
            tools=[],
            llm=get_llm_for_stage("auxiliary", agent_name="pr_labels_suggester"),
            verbose=False,
            max_iter=3,
            max_rpm=10,
        )

    @agent
    def publish_agent(self) -> Agent:
        ctx = get_pipeline_context()
        tools = get_tools_for_stage("publish", ctx.repo_path)
        return Agent(
            config=self.agents_config["publish_agent"],  # type: ignore[index]
            tools=tools,
            llm=get_llm_for_stage("publish", agent_name="publish_agent"),
            verbose=False,
            max_iter=3,
            max_rpm=10,
        )

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

    @crew
    def crew(self) -> Crew:
        """Creates the CommitCrew crew."""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=False,
            tracing=False,
            output_log_file=True,
            memory=False,
        )
