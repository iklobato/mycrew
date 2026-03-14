"""Tool factory for creating repo-scoped and optional tools."""

import logging
import os

from crewai.tools import BaseTool

from mycrew.settings import get_settings
from mycrew.tools.create_pr_tool import CreatePRTool
from mycrew.tools.repo_file_writer_tool import RepoFileWriterTool
from mycrew.tools.repo_shell_tool import RepoShellTool
from mycrew.utils import log_exceptions

logger = logging.getLogger(__name__)


def _repo_shell_plus_optional(
    repo_path: str,
    *,
    github_repo: str | None = None,
    serper_enabled: bool = False,
) -> list[BaseTool]:
    """RepoShellTool plus optional GithubSearch and SerperDevTool."""
    tools: list[BaseTool] = [RepoShellTool(repo_path=repo_path)]
    if github_repo and (gh := get_github_search_tool(github_repo)):
        tools.append(gh)
    if serper_enabled and (sp := get_serper_tool(enabled=True)):
        tools.append(sp)
    return tools


def get_tools_for_stage(
    stage: str,
    repo_path: str,
    github_repo: str | None = None,
    serper_enabled: bool = False,
) -> list[BaseTool]:
    """Return the full tool list for a pipeline stage. Centralizes tool selection."""
    repo_path = os.path.abspath(repo_path)
    gh_raw = github_repo
    if gh_raw is not None:
        gh_stripped = gh_raw.strip()
    else:
        gh_stripped = ""
    if gh_stripped:
        github_repo = gh_stripped
    else:
        github_repo = None
    logger.debug(
        "get_tools_for_stage: stage=%s, repo_path=%s, serper_enabled=%s",
        stage,
        repo_path,
        serper_enabled,
    )

    if stage == "analyze_issue":
        tools: list[BaseTool] = [
            get_scrape_website_tool(),
            RepoShellTool(repo_path=repo_path),
        ]
        gh = get_github_search_tool(github_repo)
        sp = get_serper_tool(enabled=serper_enabled)
        if gh:
            tools.append(gh)
        if sp:
            tools.append(sp)
        logger.debug(
            "Stage %s: %d tools (scrape, RepoShell, github=%s, serper=%s)",
            stage,
            len(tools),
            gh is not None,
            sp is not None,
        )
        return tools

    if stage == "explore":
        tools = _repo_shell_plus_optional(
            repo_path,
            serper_enabled=serper_enabled,
        )
        logger.debug(
            "Stage %s: %d tools (RepoShell, serper=%s)",
            stage,
            len(tools),
            serper_enabled,
        )
        return tools

    if stage == "plan":
        tools = _repo_shell_plus_optional(
            repo_path,
            github_repo=github_repo,
            serper_enabled=serper_enabled,
        )
        logger.debug(
            "Stage %s: %d tools (serper=%s)", stage, len(tools), serper_enabled
        )
        return tools

    if stage == "implement":
        # RepoScopedFileWriterTool writes to repo_path (not cwd); avoids files landing in wrong dir
        tools = [
            RepoShellTool(repo_path=repo_path),
            RepoFileWriterTool(repo_path=repo_path),
        ]
        ci = get_code_interpreter_tool()
        if ci:
            tools.append(ci)
        logger.debug(
            "Stage %s: %d tools (FileWriter, CodeInterpreter=%s)",
            stage,
            len(tools),
            ci is not None,
        )
        return tools

    if stage == "review":
        tools = _repo_shell_plus_optional(
            repo_path,
            serper_enabled=serper_enabled,
        )
        logger.debug(
            "Stage %s: %d tools (serper=%s)", stage, len(tools), serper_enabled
        )
        return tools

    if stage == "commit":
        logger.debug("Stage %s: RepoShell only", stage)
        return [RepoShellTool(repo_path=repo_path)]

    if stage == "commit_review":
        logger.debug("Stage %s: RepoShell for commit message validation", stage)
        return [RepoShellTool(repo_path=repo_path)]

    if stage == "publish":
        logger.debug(
            "Stage %s: CreatePRTool + RepoShellTool for conflict resolution", stage
        )
        return [CreatePRTool(repo_path=repo_path), RepoShellTool(repo_path=repo_path)]

    if stage in ("auxiliary", "scope_validate", "refactor_guard", "self_review"):
        logger.debug("Stage %s: RepoShell", stage)
        return [RepoShellTool(repo_path=repo_path)]

    if stage == "test_write":
        tools = [
            RepoShellTool(repo_path=repo_path),
            RepoFileWriterTool(repo_path=repo_path),
        ]
        logger.debug("Stage %s: RepoShell + RepoFileWriter", stage)
        return tools

    if stage == "test_validation":
        tools = [
            RepoShellTool(repo_path=repo_path),
            RepoFileWriterTool(repo_path=repo_path),
        ]
        ci = get_code_interpreter_tool()
        if ci:
            tools.append(ci)
        logger.debug(
            "Stage %s: RepoShell + RepoFileWriter + CodeInterpreter=%s",
            stage,
            ci is not None,
        )
        return tools

    if stage == "changelog":
        tools = [
            RepoShellTool(repo_path=repo_path),
            RepoFileWriterTool(repo_path=repo_path),
        ]
        logger.debug("Stage %s: RepoShell + RepoFileWriter", stage)
        return tools

    if stage == "security_review":
        tools = _repo_shell_plus_optional(
            repo_path,
            serper_enabled=serper_enabled,
        )
        logger.debug(
            "Stage %s: %d tools (serper=%s)", stage, len(tools), serper_enabled
        )
        return tools

    if stage == "tactiq_research":
        tools = []
        tt = get_tactiq_tool()
        if tt:
            tools.append(tt)
        logger.debug("Stage %s: TactiqTool=%s", stage, tt is not None)
        return tools

    logger.warning("Unknown stage %s, returning empty tools", stage)
    return []


@log_exceptions("GitHubAPISearchTool")
def get_github_search_tool(github_repo: str | None) -> BaseTool | None:
    """Return GitHubAPISearchTool (REST API, no LLM) if GITHUB_TOKEN and github_repo are set."""
    if not github_repo or not github_repo.strip():
        return None
    token = get_settings().github_token.strip()
    if not token:
        return None
    from mycrew.tools.github_api_search_tool import GitHubAPISearchTool

    return GitHubAPISearchTool(github_token=token, github_repo=github_repo.strip())


@log_exceptions("ScrapeWebsiteTool")
def get_scrape_website_tool() -> BaseTool:
    """Return ScrapeWebsiteTool for web-based issue trackers."""
    from crewai_tools import ScrapeWebsiteTool

    return ScrapeWebsiteTool()


@log_exceptions("CodeDocsSearchTool")
def get_code_docs_search_tool(docs_url: str | None = None) -> BaseTool | None:
    """Return CodeDocsSearchTool when docs_url is set; otherwise None to avoid loading heavy deps."""
    if not docs_url or not docs_url.strip():
        return None
    from crewai_tools import CodeDocsSearchTool

    return CodeDocsSearchTool(docs_url=docs_url.strip())


def get_code_interpreter_tool() -> BaseTool | None:
    """Return CodeInterpreterTool if Docker is available."""
    try:
        from crewai_tools import CodeInterpreterTool

        return CodeInterpreterTool()
    except Exception as e:
        logger.error("CodeInterpreterTool unavailable: %s", e, exc_info=True)
        return None


@log_exceptions("SerperDevTool")
def get_serper_tool(enabled: bool = True, n_results: int = 5) -> BaseTool | None:
    """Return SerperDevTool for web search if enabled and API key is available."""
    if not enabled:
        logger.debug("SerperDevTool disabled by configuration")
        return None

    api_key = get_settings().serper_api_key.strip()
    if not api_key:
        logger.warning("SerperDevTool disabled: SERPER_API_KEY not set")
        return None

    try:
        from crewai_tools import SerperDevTool

        logger.info("SerperDevTool enabled with n_results=%d", n_results)
        return SerperDevTool(n_results=n_results)
    except Exception as e:
        logger.error("SerperDevTool unavailable: %s", e, exc_info=True)
        return None


def get_tactiq_tool() -> BaseTool | None:
    """Return TactiqTool for meeting lookup if TACTIQ_TOKEN is configured."""
    token = get_settings().tactiq_token.strip()
    if not token:
        logger.debug("TactiqTool disabled: TACTIQ_TOKEN not set")
        return None

    try:
        from mycrew.tools.tactiq_tool import TactiqTool

        logger.info("TactiqTool enabled")
        return TactiqTool()
    except Exception as e:
        logger.error("TactiqTool unavailable: %s", e, exc_info=True)
        return None
