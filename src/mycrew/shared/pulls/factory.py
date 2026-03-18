"""PR handler factory."""

from mycrew.shared.pulls.fetchers import GitHubPRFetcher, GitLabPRFetcher
from mycrew.shared.pulls.models import PRContent, PRSourceType
from mycrew.shared.pulls.parsers import PRParserFactory


class PRHandler:
    def __init__(
        self,
        github_fetcher: GitHubPRFetcher,
        gitlab_fetcher: GitLabPRFetcher,
    ):
        self._github_fetcher = github_fetcher
        self._gitlab_fetcher = gitlab_fetcher

    def process(self, url: str) -> PRContent:
        source = PRParserFactory.parse(url)
        if source.source_type == PRSourceType.GITHUB:
            return self._github_fetcher.fetch(source)
        else:
            return self._gitlab_fetcher.fetch(source)


class PRHandlerFactory:
    @staticmethod
    def create(
        github_token: str | None = None,
        gitlab_token: str | None = None,
    ) -> PRHandler:
        return PRHandler(
            github_fetcher=GitHubPRFetcher(github_token),
            gitlab_fetcher=GitLabPRFetcher(gitlab_token),
        )
