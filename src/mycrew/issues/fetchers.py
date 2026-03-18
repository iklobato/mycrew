"""Issue fetchers for different sources."""

import logging
from abc import ABC, abstractmethod
from datetime import datetime

import requests

from mycrew.issues.exceptions import IssueFetchError
from mycrew.issues.models import IssueContent, IssueSource

logger = logging.getLogger(__name__)


class IssueFetcher(ABC):
    """Abstract base class for fetching issues from different sources."""

    @abstractmethod
    def fetch(self, source: IssueSource) -> IssueContent:
        """Fetch issue content from source.

        Args:
            source: IssueSource identifying the issue to fetch.

        Returns:
            IssueContent with the issue data.

        Raises:
            IssueFetchError: If the fetch fails.
        """
        pass


class GitHubFetcher(IssueFetcher):
    """Fetcher for GitHub issues using the REST API."""

    _BASE_URL = "https://api.github.com"

    def __init__(self, token: str | None = None):
        self._token = token

    def fetch(self, source: IssueSource) -> IssueContent:
        headers = {"Accept": "application/vnd.github.v3+json"}
        if self._token:
            headers["Authorization"] = f"token {self._token}"

        url = f"{self._BASE_URL}/repos/{source.owner}/{source.repo}/issues/{source.issue_number}"

        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
        except requests.RequestException as e:
            raise IssueFetchError(f"Failed to fetch GitHub issue: {e}") from e

        data = response.json()

        return IssueContent(
            title=data["title"],
            body=data["body"] or "",
            author=data["user"]["login"],
            labels=[label["name"] for label in data.get("labels", [])],
            state=data["state"],
            created_at=parse_github_datetime(data["created_at"]),
            source=source,
        )


class GitLabFetcher(IssueFetcher):
    """Fetcher for GitLab issues using the REST API."""

    _BASE_URL = "https://gitlab.com/api/v4"

    def __init__(self, token: str | None = None):
        self._token = token

    def fetch(self, source: IssueSource) -> IssueContent:
        headers = {}
        if self._token:
            headers["PRIVATE-TOKEN"] = self._token

        project_path = f"{source.owner}%2F{source.repo}"
        url = f"{self._BASE_URL}/projects/{project_path}/issues/{source.issue_number}"

        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
        except requests.RequestException as e:
            raise IssueFetchError(f"Failed to fetch GitLab issue: {e}") from e

        data = response.json()

        return IssueContent(
            title=data["title"],
            body=data["description"] or "",
            author=data["author"]["username"],
            labels=data.get("labels", []),
            state=data["state"],
            created_at=parse_gitlab_datetime(data["created_at"]),
            source=source,
        )


def parse_github_datetime(dt_str: str) -> datetime:
    """Parse GitHub ISO 8601 datetime string."""
    dt_str = dt_str.replace("Z", "+00:00")
    return datetime.fromisoformat(dt_str)


def parse_gitlab_datetime(dt_str: str) -> datetime:
    """Parse GitLab ISO 8601 datetime string."""
    dt_str = dt_str.replace("Z", "+00:00")
    return datetime.fromisoformat(dt_str)
