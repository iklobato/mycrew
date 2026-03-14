"""PipelineCrewBase: shared tools, LLMs, config, and crew() for all crews."""

from typing import List, ClassVar

from crewai import Agent, Crew, LLM, Process, Task
from crewai.project import crew, llm, tool
from crewai.tools import BaseTool

from code_pipeline.llm import get_llm_for_stage
from code_pipeline.settings import get_pipeline_context, get_settings
from code_pipeline.tools.create_pr_tool import CreatePRTool
from code_pipeline.tools.factory import (
    get_code_interpreter_tool,
    get_github_search_tool,
    get_scrape_website_tool,
    get_serper_tool,
    get_tactiq_tool,
)
from code_pipeline.tools.human_tool import ask_human as ask_human_tool
from code_pipeline.tools.noop_tool import NoOpTool
from code_pipeline.tools.repo_file_writer_tool import RepoFileWriterTool
from code_pipeline.tools.repo_shell_tool import RepoShellTool

from .abc_crew import ABCrew


class PipelineCrewBase(ABCrew):
    """Base class for pipeline crews. Subclasses add @agent and @task methods."""

    stage: ClassVar[str] = "auxiliary"

    @property
    def required_agents(self) -> List[str]:
        """List of agent keys this crew requires."""
        return []

    @property
    def required_tasks(self) -> List[str]:
        """List of task keys this crew requires."""
        return []

    def _build_agent(self, agent_key: str) -> Agent:
        """Build an agent for the given key."""
        config = dict(self.agents_config[agent_key])  # type: ignore[attr-defined,index,union-attr]
        llm_ref = config.get("llm", "auxiliary_llm")

        if isinstance(llm_ref, str) and llm_ref.endswith("_llm"):
            stage = llm_ref.removesuffix("_llm")
        else:
            stage = "auxiliary"

        if stage == "security_review":
            stage = "security"

        settings = get_settings()
        config["llm"] = get_llm_for_stage(
            stage, agent_name=agent_key, provider_type=settings.provider_type
        )
        return Agent(config=config)

    def _build_task(self, task_key: str) -> Task:
        """Build a task for the given key."""
        config = dict(self.tasks_config[task_key])  # type: ignore[attr-defined,index,union-attr]
        return Task(
            config=config,
            description=config.get("description", ""),
            expected_output=config.get("expected_output", ""),
            agent=None,  # Will be set when task is added to crew
        )

    @llm
    def auxiliary_llm(self) -> LLM:
        return get_llm_for_stage("auxiliary")  # type: ignore[abstract]

    @llm
    def analyze_issue_llm(self) -> LLM:
        return get_llm_for_stage("analyze_issue")  # type: ignore[abstract]

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
        return NoOpTool()  # type: ignore[abstract]  # type: ignore[abstract]

    @tool
    def github_search(self) -> BaseTool:
        ctx = get_pipeline_context()
        repo: str | None
        if ctx.github_repo:
            repo = ctx.github_repo
        else:
            repo = None
        t = get_github_search_tool(repo)
        if t:
            return t
        return NoOpTool()  # type: ignore[abstract]

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
        return NoOpTool()  # type: ignore[abstract]

    @tool
    def ask_human(self) -> BaseTool:
        return ask_human_tool

    @tool
    def tactiq_meeting(self) -> BaseTool:
        t = get_tactiq_tool()
        if t:
            return t
        return NoOpTool()  # type: ignore[abstract]

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,  # type: ignore[attr-defined]
            tasks=self.tasks,  # type: ignore[attr-defined]
            process=Process.sequential,
            verbose=True,
        )
