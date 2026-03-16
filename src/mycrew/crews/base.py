"""PipelineCrewBase: shared tools, LLMs, config, and crew() for all crews."""

from typing import Any, List, ClassVar

from crewai import Agent, Crew, LLM, Process, Task
from crewai.project import crew, llm, tool
from crewai.tools import BaseTool

from mycrew.llm import get_llm_for_stage
from mycrew.settings import get_pipeline_context, get_settings
from mycrew.tools.create_pr_tool import CreatePRTool
from mycrew.tools.factory import (
    get_code_interpreter_tool,
    get_github_search_tool,
    get_scrape_website_tool,
    get_serper_tool,
    get_tactiq_tool,
)
from mycrew.tools.human_tool import ask_human as ask_human_tool
from mycrew.tools.noop_tool import NoOpTool
from mycrew.tools.repo_file_writer_tool import RepoFileWriterTool
from mycrew.tools.repo_shell_tool import RepoShellTool

from .abc_crew import ABCrew


class PipelineCrewBase(ABCrew):
    """Base class for pipeline crews. Subclasses add @agent and @task methods."""

    stage: ClassVar[str] = "auxiliary"
    process: ClassVar[Any] = Process.sequential

    @property
    def crew_process(self) -> Any:
        """Process type for this crew. Override in subclass to use Process.parallel."""
        return self.process

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

        # Debug logging
        import logging

        logger = logging.getLogger(__name__)
        logger.info(f"_build_agent: agent={agent_key}, llm_ref={llm_ref}")

        # Check if llm_ref is a stage reference (like "explore_llm") or a full model ID
        if isinstance(llm_ref, str) and llm_ref.endswith("_llm"):
            stage = llm_ref.removesuffix("_llm")
            logger.info(f"  -> Using stage: {stage}")
        elif isinstance(llm_ref, str) and llm_ref.startswith("openrouter/"):
            # Full model ID provided directly - use it as-is
            logger.info(f"  -> Using custom_model: {llm_ref}")
            config["llm"] = get_llm_for_stage("auxiliary", custom_model=llm_ref)
            return Agent(config=config)
        else:
            logger.info(f"  -> Using default auxiliary")
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

    def build_inputs(
        self,
        state: Any,
        custom_inputs: dict | None = None,
    ) -> dict[str, Any]:
        """Build standard inputs for this crew from pipeline state.

        Args:
            state: PipelineState containing all pipeline data
            custom_inputs: Additional inputs specific to this crew (optional)

        Returns:
            Dictionary of inputs to pass to crew.kickoff()
        """
        from mycrew.crews.input_builder import PipelineInputBuilder

        builder = PipelineInputBuilder()
        return builder.build(state, custom_inputs)

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
            process=self.crew_process,
            verbose=True,
        )
