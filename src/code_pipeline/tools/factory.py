"""Tool factory for creating repo-scoped and optional tools."""

import os
from crewai.tools import BaseTool

from code_pipeline.tools.repo_shell_tool import RepoShellTool


def get_tools_for_stage(
    stage: str,
    repo_path: str,
    github_repo: str | None = None,
    docs_url: str | None = None,
) -> list[BaseTool]:
    """Return the full tool list for a pipeline stage. Centralizes tool selection."""
    repo_path = os.path.abspath(repo_path)
    github_repo = (github_repo or "").strip() or None
    docs_url = (docs_url or "").strip() or None

    if stage == "analyze_issue":
        tools: list[BaseTool] = [get_scrape_website_tool()]
        gh = get_github_search_tool(github_repo)
        if gh:
            tools.append(gh)
        return tools

    if stage == "explore":
        # Use RepoShellTool only for explore to avoid segfault from crewai_tools
        # (DirectoryReadTool/DirectorySearchTool/FileReadTool can crash on macOS).
        tools: list[BaseTool] = [RepoShellTool(repo_path=repo_path)]
        cd = get_code_docs_search_tool(docs_url)
        if cd:
            tools.append(cd)
        return tools

    if stage == "plan":
        tools = [
            RepoShellTool(repo_path=repo_path),
            *get_repo_scoped_tools(repo_path),
        ]
        cd = get_code_docs_search_tool(docs_url)
        if cd:
            tools.append(cd)
        gh = get_github_search_tool(github_repo)
        if gh:
            tools.append(gh)
        return tools

    if stage == "implement":
        from crewai_tools import FileWriterTool

        tools = [
            RepoShellTool(repo_path=repo_path),
            FileWriterTool(),
            *get_repo_scoped_tools(repo_path),
        ]
        ci = get_code_interpreter_tool()
        if ci:
            tools.append(ci)
        return tools

    if stage == "review":
        tools = [
            RepoShellTool(repo_path=repo_path),
            *get_repo_scoped_tools(repo_path),
        ]
        cd = get_code_docs_search_tool(docs_url)
        if cd:
            tools.append(cd)
        return tools

    if stage == "commit":
        return [RepoShellTool(repo_path=repo_path)]

    return []


def get_repo_scoped_tools(repo_path: str) -> list[BaseTool]:
    """Create DirectoryReadTool, DirectorySearchTool, and FileReadTool for the repo."""
    from crewai_tools import (
        DirectoryReadTool,
        DirectorySearchTool,
        FileReadTool,
    )

    repo_path = os.path.abspath(repo_path)
    tools: list[BaseTool] = [
        DirectoryReadTool(directory=repo_path),
        DirectorySearchTool(directory=repo_path),
        FileReadTool(),
    ]
    return tools


def get_github_search_tool(github_repo: str | None) -> BaseTool | None:
    """Return GithubSearchTool if GITHUB_TOKEN and github_repo are set."""
    if not github_repo or not github_repo.strip():
        return None
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not token:
        return None
    from crewai_tools import GithubSearchTool

    return GithubSearchTool(gh_token=token, github_repo=github_repo.strip())


def get_scrape_website_tool() -> BaseTool:
    """Return ScrapeWebsiteTool for web-based issue trackers."""
    from crewai_tools import ScrapeWebsiteTool

    return ScrapeWebsiteTool()


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
    except Exception:
        return None
