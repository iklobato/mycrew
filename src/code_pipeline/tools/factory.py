"""Tool factory for creating repo-scoped and optional tools."""

import logging
import os

from crewai.tools import BaseTool

from code_pipeline.tools.create_pr_tool import CreatePRTool
from code_pipeline.tools.repo_file_writer_tool import RepoFileWriterTool
from code_pipeline.tools.repo_shell_tool import RepoShellTool
from code_pipeline.utils import log_exceptions

logger = logging.getLogger(__name__)


def _repo_shell_plus_optional(
    repo_path: str,
    *,
    docs_url: str | None = None,
    github_repo: str | None = None,
    serper_enabled: bool = False,
    serper_n_results: int = 5,
) -> list[BaseTool]:
    """RepoShellTool plus optional CodeDocsSearch, GithubSearch, and SerperDevTool."""
    tools: list[BaseTool] = [RepoShellTool(repo_path=repo_path)]
    if docs_url and (cd := get_code_docs_search_tool(docs_url)):
        tools.append(cd)
    if github_repo and (gh := get_github_search_tool(github_repo)):
        tools.append(gh)
    if serper_enabled and (
        sp := get_serper_tool(enabled=True, n_results=serper_n_results)
    ):
        tools.append(sp)
    return tools


def get_tools_for_stage(
    stage: str,
    repo_path: str,
    github_repo: str | None = None,
    docs_url: str | None = None,
    serper_enabled: bool = False,
    serper_n_results: int = 5,
) -> list[BaseTool]:
    """Return the full tool list for a pipeline stage. Centralizes tool selection."""
    repo_path = os.path.abspath(repo_path)
    github_repo = (github_repo or "").strip() or None
    docs_url = (docs_url or "").strip() or None
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
        cd = get_code_docs_search_tool(docs_url)
        sp = get_serper_tool(enabled=serper_enabled, n_results=serper_n_results)
        if gh:
            tools.append(gh)
        if cd:
            tools.append(cd)
        if sp:
            tools.append(sp)
        logger.debug(
            "Stage %s: %d tools (scrape, RepoShell, github=%s, docs=%s, serper=%s)",
            stage,
            len(tools),
            gh is not None,
            cd is not None,
            sp is not None,
        )
        return tools

    if stage == "explore":
        tools = _repo_shell_plus_optional(
            repo_path,
            docs_url=docs_url,
            serper_enabled=serper_enabled,
            serper_n_results=serper_n_results,
        )
        logger.debug(
            "Stage %s: %d tools (RepoShell, docs=%s, serper=%s)",
            stage,
            len(tools),
            bool(docs_url),
            serper_enabled,
        )
        return tools

    if stage == "plan":
        tools = _repo_shell_plus_optional(
            repo_path,
            docs_url=docs_url,
            github_repo=github_repo,
            serper_enabled=serper_enabled,
            serper_n_results=serper_n_results,
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
            docs_url=docs_url,
            serper_enabled=serper_enabled,
            serper_n_results=serper_n_results,
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
        logger.debug("Stage %s: CreatePRTool only", stage)
        return [CreatePRTool(repo_path=repo_path)]

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
            docs_url=docs_url,
            serper_enabled=serper_enabled,
            serper_n_results=serper_n_results,
        )
        logger.debug(
            "Stage %s: %d tools (serper=%s)", stage, len(tools), serper_enabled
        )
        return tools

    logger.warning("Unknown stage %s, returning empty tools", stage)
    return []


@log_exceptions("GithubSearchTool")
def get_github_search_tool(github_repo: str | None) -> BaseTool | None:
    """Return GithubSearchTool if GITHUB_TOKEN and github_repo are set."""
    if not github_repo or not github_repo.strip():
        return None
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not token:
        return None
    from crewai_tools import GithubSearchTool

    return GithubSearchTool(gh_token=token, github_repo=github_repo.strip())


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

    api_key = os.environ.get("SERPER_API_KEY", "").strip()
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
