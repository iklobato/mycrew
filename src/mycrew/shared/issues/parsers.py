"""Issue URL parsers for different sources."""

import re
from abc import ABC, abstractmethod

from mycrew.shared.issues.exceptions import IssueParseError
from mycrew.shared.issues.models import IssueSource, IssueSourceType


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
        """Parse URL to IssueSource.

        Args:
            url: The issue URL to parse.

        Returns:
            IssueSource with parsed information.

        Raises:
            IssueParseError: If URL cannot be parsed.
        """
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
