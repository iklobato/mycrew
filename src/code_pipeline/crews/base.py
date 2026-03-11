"""PipelineCrewBase: shared tools, LLMs, config, and crew() for all crews."""

from typing import List

from crewai import Crew, LLM, Process, Task
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai.project import crew, llm, tool
from crewai.tools import BaseTool

from code_pipeline.llm import get_llm_for_stage
from code_pipeline.settings import get_pipeline_context
from code_pipeline.tools.create_pr_tool import CreatePRTool
from code_pipeline.tools.factory import (
    get_code_interpreter_tool,
    get_github_search_tool,
    get_scrape_website_tool,
    get_serper_tool,
)
from code_pipeline.tools.human_tool import ask_human as ask_human_tool
from code_pipeline.tools.noop_tool import NoOpTool
from code_pipeline.tools.repo_file_writer_tool import RepoFileWriterTool
from code_pipeline.tools.repo_shell_tool import RepoShellTool


class PipelineCrewBase:
    """Base class for pipeline crews. Subclasses add @agent and @task methods."""

    agents: List[BaseAgent]
    tasks: List[Task]

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @llm
    def auxiliary_llm(self) -> LLM:
        return get_llm_for_stage("auxiliary")

    @llm
    def analyze_issue_llm(self) -> LLM:
        return get_llm_for_stage("analyze_issue")

    @tool
    def repo_shell(self) -> BaseTool:
        return RepoShellTool(repo_path=get_pipeline_context().repo_path)

    @tool
    def repo_file_writer(self) -> BaseTool:
        return RepoFileWriterTool(repo_path=get_pipeline_context().repo_path)

    @tool
    def serper_dev(self) -> BaseTool:
        t = get_serper_tool(enabled=get_pipeline_context().serper_enabled)
        if t:
            return t
        return NoOpTool()

    @tool
    def github_search(self) -> BaseTool:
        ctx = get_pipeline_context()
        t = get_github_search_tool(ctx.github_repo or None)
        if t:
            return t
        return NoOpTool()

    @tool
    def create_pr(self) -> BaseTool:
        return CreatePRTool(repo_path=get_pipeline_context().repo_path)

    @tool
    def scrape_website(self) -> BaseTool:
        return get_scrape_website_tool()

    @tool
    def code_interpreter(self) -> BaseTool:
        t = get_code_interpreter_tool()
        if t:
            return t
        return NoOpTool()

    @tool
    def ask_human(self) -> BaseTool:
        return ask_human_tool

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=False,
            tracing=False,
            output_log_file=True,
            memory=False,
        )
