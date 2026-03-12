"""GitHub API Search Tool using GitHub REST API instead of gh CLI."""

import logging
from typing import Any

import requests
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class GitHubAPISearchToolInput(BaseModel):
    """Input schema for GitHubAPISearchTool."""

    search_query: str = Field(
        ...,
        description="Search query for GitHub (e.g., 'filename:*.py def calculate_total')",
    )
    content_types: str = Field(
        default="code",
        description="Comma-separated content types: code,repo,pr,issue,discussion,commit",
    )


class GitHubAPISearchTool(BaseTool):
    """Search GitHub repositories using GitHub REST API."""

    name: str = "GitHubAPISearchTool"
    description: str = (
        "Search GitHub repositories for code, issues, PRs, and discussions using GitHub REST API. "
        "Useful for finding similar implementations, documentation, or examples."
    )
    args_schema: type[BaseModel] = GitHubAPISearchToolInput

    # Pydantic fields
    github_token: str
    github_repo: str

    # Model config to allow extra attributes
    model_config = {"extra": "allow"}

    def __init__(self, github_token: str, github_repo: str):
        """Initialize with GitHub token and repository."""
        super().__init__(github_token=github_token, github_repo=github_repo)
        self.owner, self.repo = self._parse_repo(github_repo)
        self.headers = {
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "code_pipeline",
        }
        self.base_url = "https://api.github.com"

    def _parse_repo(self, github_repo: str) -> tuple[str, str]:
        """Parse owner/repo from repository string."""
        if "/" not in github_repo:
            raise ValueError(
                f"Invalid repository format: {github_repo}. Expected 'owner/repo'"
            )
        parts = github_repo.split("/", 1)
        return parts[0], parts[1]

    def _run(self, search_query: str, content_types: str = "code") -> str:
        """Execute GitHub search using REST API."""
        logger.info(
            "GitHubAPISearchTool: query=%s types=%s",
            search_query[:80],
            content_types,
        )
        try:
            # Build search query with repository filter
            repo_filter = f"repo:{self.owner}/{self.repo}"
            full_query = f"{search_query} {repo_filter}"

            # Parse content types
            content_type_list = [ct.strip() for ct in content_types.split(",")]

            results = []

            # Search each content type
            for content_type in content_type_list:
                if content_type == "code":
                    search_results = self._search_code(full_query)
                    results.extend(search_results)
                elif content_type == "issues":
                    search_results = self._search_issues(full_query)
                    results.extend(search_results)
                elif content_type == "pr":
                    search_results = self._search_pull_requests(full_query)
                    results.extend(search_results)
                elif content_type == "repo":
                    # For repo search, we might want to search within the repo
                    # but GitHub repo search is for repositories, not within them
                    pass
                elif content_type == "discussion":
                    search_results = self._search_discussions(full_query)
                    results.extend(search_results)
                elif content_type == "commit":
                    search_results = self._search_commits(full_query)
                    results.extend(search_results)

            if not results:
                return f"No results found for query: {search_query}"

            logger.info("GitHubAPISearchTool: found %d results", len(results))

            # Format results
            formatted_results = []
            for i, result in enumerate(results[:10], 1):  # Limit to 10 results
                formatted_results.append(self._format_result(result, i))

            return "\n\n".join(formatted_results)

        except Exception as e:
            logger.error("GitHub API search failed: %s", e)
            return f"GitHub search failed: {str(e)}"

    def _search_code(self, query: str) -> list[dict[str, Any]]:
        """Search code in repository."""
        url = f"{self.base_url}/search/code"
        params = {"q": query, "per_page": 5}

        response = requests.get(url, headers=self.headers, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()
        return [
            {
                "type": "code",
                "path": item["path"],
                "name": item["name"],
                "html_url": item["html_url"],
                "repository": item["repository"]["full_name"],
                "score": item.get("score", 0),
            }
            for item in data.get("items", [])
        ]

    def _search_issues(self, query: str) -> list[dict[str, Any]]:
        """Search issues in repository."""
        url = f"{self.base_url}/search/issues"
        params = {"q": query, "per_page": 5}

        response = requests.get(url, headers=self.headers, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()
        return [
            {
                "type": "issue",
                "title": item["title"],
                "number": item["number"],
                "state": item["state"],
                "html_url": item["html_url"],
                "body_preview": item.get("body", "")[:200] + "..."
                if item.get("body")
                else "",
                "score": item.get("score", 0),
            }
            for item in data.get("items", [])
        ]

    def _search_pull_requests(self, query: str) -> list[dict[str, Any]]:
        """Search pull requests in repository."""
        # GitHub API uses issues endpoint for PRs too
        url = f"{self.base_url}/search/issues"
        params = {"q": f"{query} is:pr", "per_page": 5}

        response = requests.get(url, headers=self.headers, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()
        return [
            {
                "type": "pull_request",
                "title": item["title"],
                "number": item["number"],
                "state": item["state"],
                "html_url": item["html_url"],
                "body_preview": item.get("body", "")[:200] + "..."
                if item.get("body")
                else "",
                "score": item.get("score", 0),
            }
            for item in data.get("items", [])
        ]

    def _search_discussions(self, query: str) -> list[dict[str, Any]]:
        """Search discussions in repository (if enabled)."""
        # Discussions API is GraphQL, simpler to use REST for now
        # We'll use issues as a fallback
        return self._search_issues(query)

    def _search_commits(self, query: str) -> list[dict[str, Any]]:
        """Search commits in repository."""
        url = f"{self.base_url}/search/commits"
        params = {"q": query, "per_page": 5}

        response = requests.get(url, headers=self.headers, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()
        return [
            {
                "type": "commit",
                "sha": item["sha"],
                "message": item["commit"]["message"],
                "author": item["commit"]["author"]["name"],
                "html_url": item["html_url"],
                "score": item.get("score", 0),
            }
            for item in data.get("items", [])
        ]

    def _format_result(self, result: dict[str, Any], index: int) -> str:
        """Format a single search result."""
        result_type = result.get("type", "unknown")

        if result_type == "code":
            return (
                f"{index}. **Code: {result['path']}**\n"
                f"   Repository: {result['repository']}\n"
                f"   URL: {result['html_url']}\n"
                f"   Relevance score: {result.get('score', 'N/A')}"
            )
        elif result_type in ["issue", "pull_request"]:
            if result_type == "issue":
                item_type = "Issue"
            else:
                item_type = "Pull Request"
            return (
                f"{index}. **{item_type} #{result['number']}: {result['title']}**\n"
                f"   State: {result['state']}\n"
                f"   URL: {result['html_url']}\n"
                f"   Preview: {result.get('body_preview', 'No description')}\n"
                f"   Relevance score: {result.get('score', 'N/A')}"
            )
        elif result_type == "commit":
            return (
                f"{index}. **Commit: {result['sha'][:8]}**\n"
                f"   Message: {result['message']}\n"
                f"   Author: {result['author']}\n"
                f"   URL: {result['html_url']}\n"
                f"   Relevance score: {result.get('score', 'N/A')}"
            )
        else:
            return f"{index}. Unknown result type: {result}"
