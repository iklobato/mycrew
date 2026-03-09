"""Issue Analyst crew: parses raw issue cards into structured requirements."""

import os
from typing import List

from crewai import Agent, Crew, Process, Task
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai.project import CrewBase, agent, crew, task

from code_pipeline.llm import get_llm_for_stage
from code_pipeline.tools.factory import get_tools_for_stage


@CrewBase
class IssueAnalystCrew:
    """Issue Analyst crew: extracts structured requirements from issue cards."""

    agents: List[BaseAgent]
    tasks: List[Task]

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def issue_analyst(self) -> Agent:
        repo_path = os.path.abspath(os.environ.get("REPO_PATH", os.getcwd()))
        github_repo = (os.environ.get("GITHUB_REPO", "") or "").strip() or None
        docs_url = (os.environ.get("DOCS_URL", "") or "").strip() or None
        tools = get_tools_for_stage(
            "analyze_issue", repo_path, github_repo=github_repo, docs_url=docs_url
        )
        return Agent(
            config=self.agents_config["issue_analyst"],  # type: ignore[index]
            tools=tools,
            llm=get_llm_for_stage("analyze_issue"),
            verbose=False,
        )

    @task
    def analyze_task(self) -> Task:
        return Task(
            config=self.tasks_config["analyze_task"],  # type: ignore[index]
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=False,
            tracing=True,
            output_log_file=True,
            memory=False,
        )
