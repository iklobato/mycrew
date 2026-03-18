"""PR URL parsers."""

import re

from mycrew.shared.pulls.models import PRSource, PRSourceType
from mycrew.shared.pulls.exceptions import PRParseError


class GitHubPRParser:
    _PATTERN = re.compile(
        r"github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/pull/(?P<number>\d+)"
    )

    def parse(self, url: str) -> PRSource:
        match = self._PATTERN.search(url)
        if not match:
            raise PRParseError(f"Invalid GitHub PR URL: {url}")

        return PRSource(
            source_type=PRSourceType.GITHUB,
            owner=match.group("owner"),
            repo=match.group("repo"),
            pr_number=int(match.group("number")),
            web_url=url,
        )


class GitLabPRParser:
    _PATTERN = re.compile(
        r"gitlab\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/-/merge_requests/(?P<number>\d+)"
    )

    def parse(self, url: str) -> PRSource:
        match = self._PATTERN.search(url)
        if not match:
            raise PRParseError(f"Invalid GitLab MR URL: {url}")

        return PRSource(
            source_type=PRSourceType.GITLAB,
            owner=match.group("owner"),
            repo=match.group("repo"),
            pr_number=int(match.group("number")),
            web_url=url,
        )


class PRParserFactory:
    @classmethod
    def parse(cls, url: str) -> PRSource:
        url_lower = url.lower()
        if "github.com" in url_lower:
            return GitHubPRParser().parse(url)
        elif "gitlab.com" in url_lower:
            return GitLabPRParser().parse(url)
        else:
            raise PRParseError(f"Unsupported PR source: {url}")
