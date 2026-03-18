"""Issues module - GitHub/GitLab issue fetching."""

import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

import requests

logger = logging.getLogger(__name__)


# Exceptions


class IssueHandlerError(Exception):
    """Base exception for issue handling."""

    pass


class UnsupportedSourceError(IssueHandlerError):
    """Raised when issue URL is not from a supported source."""

    pass


class IssueFetchError(IssueHandlerError):
    """Raised when API call to fetch issue fails."""

    pass


class IssueParseError(IssueHandlerError):
    """Raised when issue URL cannot be parsed."""

    pass


# Models


class IssueSourceType(Enum):
    """Supported issue tracker types."""

    GITHUB = "github"
    GITLAB = "gitlab"


@dataclass(frozen=True)
class IssueSource:
    """Identifies where an issue lives."""

    source_type: IssueSourceType
    owner: str
    repo: str
    issue_number: int
    web_url: str


@dataclass(frozen=True)
class IssueContent:
    """Parsed issue content from an issue tracker."""

    title: str
    body: str
    author: str
    labels: list[str]
    state: str
    created_at: datetime
    source: IssueSource


# Parsers


class IssueURLParser(ABC):
    """Abstract base class for issue URL parsers."""

    @abstractmethod
    def parse(self, url: str) -> IssueSource:
        """Parse URL to IssueSource.

        Raises:
            IssueParseError: If URL is invalid for this parser.
        """
        pass


class GitHubURLParser(IssueURLParser):
    """Parser for GitHub issue URLs."""

    _PATTERN = re.compile(
        r"github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/issues/(?P<number>\d+)"
    )

    def parse(self, url: str) -> IssueSource:
        match = self._PATTERN.search(url)
        if not match:
            raise IssueParseError(f"Invalid GitHub issue URL: {url}")
        return IssueSource(
            source_type=IssueSourceType.GITHUB,
            owner=match.group("owner"),
            repo=match.group("repo"),
            issue_number=int(match.group("number")),
            web_url=url,
        )


class GitLabURLParser(IssueURLParser):
    """Parser for GitLab issue URLs."""

    _PATTERN = re.compile(
        r"gitlab\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/-/issues/(?P<number>\d+)"
    )

    def parse(self, url: str) -> IssueSource:
        match = self._PATTERN.search(url)
        if not match:
            raise IssueParseError(f"Invalid GitLab issue URL: {url}")
        return IssueSource(
            source_type=IssueSourceType.GITLAB,
            owner=match.group("owner"),
            repo=match.group("repo"),
            issue_number=int(match.group("number")),
            web_url=url,
        )


class IssueURLParserFactory:
    """Factory for creating appropriate parser based on URL."""

    _PARSERS: dict[IssueSourceType, IssueURLParser] = {
        IssueSourceType.GITHUB: GitHubURLParser(),
        IssueSourceType.GITLAB: GitLabURLParser(),
    }

    _SOURCE_DETECTOR = re.compile(r"github\.com|gitlab\.com")

    @classmethod
    def parse(cls, url: str) -> IssueSource:
        """Parse URL to IssueSource."""
        url_lower = url.lower()

        if "github.com" in url_lower:
            return cls._PARSERS[IssueSourceType.GITHUB].parse(url)
        if "gitlab.com" in url_lower:
            return cls._PARSERS[IssueSourceType.GITLAB].parse(url)

        raise IssueParseError(
            f"Unsupported issue URL (no GitHub or GitLab detected): {url}"
        )

    @classmethod
    def get_parser(cls, source_type: IssueSourceType) -> IssueURLParser:
        """Get parser for a specific source type."""
        return cls._PARSERS[source_type]


# Fetchers


class IssueFetcher(ABC):
    """Abstract base class for fetching issues from different sources."""

    @abstractmethod
    def fetch(self, source: IssueSource) -> IssueContent:
        """Fetch issue content from source."""
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


# Factory


class IssueHandler:
    """Handles fetching issues from a URL using the appropriate fetcher."""

    def __init__(
        self,
        github_fetcher: GitHubFetcher,
        gitlab_fetcher: GitLabFetcher,
    ):
        self._github_fetcher = github_fetcher
        self._gitlab_fetcher = gitlab_fetcher
        self._parsers = IssueURLParserFactory._PARSERS

    def process(self, url: str) -> IssueContent:
        """Process an issue URL and return the issue content."""
        source = IssueURLParserFactory.parse(url)

        if source.source_type == IssueSourceType.GITHUB:
            return self._github_fetcher.fetch(source)
        if source.source_type == IssueSourceType.GITLAB:
            return self._gitlab_fetcher.fetch(source)

        raise IssueParseError(f"Unknown source type: {source.source_type}")


class IssueHandlerFactory:
    """Factory for creating IssueHandler instances."""

    @staticmethod
    def create(
        github_token: str | None = None, gitlab_token: str | None = None
    ) -> IssueHandler:
        """Create an IssueHandler."""
        return IssueHandler(
            github_fetcher=GitHubFetcher(github_token),
            gitlab_fetcher=GitLabFetcher(gitlab_token),
        )
