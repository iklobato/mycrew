"""Factory for creating issue handlers."""

import logging

from mycrew.issues.exceptions import IssueParseError
from mycrew.issues.fetchers import GitHubFetcher, GitLabFetcher
from mycrew.issues.models import IssueContent, IssueSourceType
from mycrew.issues.parsers import IssueURLParserFactory

logger = logging.getLogger(__name__)


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
        """Process an issue URL and return the issue content.

        Args:
            url: The issue URL to process.

        Returns:
            IssueContent with the parsed issue data.

        Raises:
            IssueParseError: If the URL cannot be parsed.
            IssueFetchError: If the issue cannot be fetched.
        """
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
        """Create an IssueHandler.

        Args:
            github_token: Optional GitHub API token.
            gitlab_token: Optional GitLab API token.

        Returns:
            IssueHandler configured for GitHub and GitLab.
        """
        return IssueHandler(
            github_fetcher=GitHubFetcher(github_token),
            gitlab_fetcher=GitLabFetcher(gitlab_token),
        )
