"""PR fetchers for GitHub and GitLab."""

import requests

from mycrew.shared.pulls.models import PRContent, PRSource
from mycrew.shared.pulls.exceptions import PRFetchError


class GitHubPRFetcher:
    _BASE_URL = "https://api.github.com"

    def __init__(self, token: str | None = None):
        self._token = token

    def fetch(self, source: PRSource) -> PRContent:
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "mycrew-pr-reviewer",
        }
        if self._token:
            headers["Authorization"] = f"token {self._token}"

        # Fetch PR metadata
        pr_url = f"{self._BASE_URL}/repos/{source.owner}/{source.repo}/pulls/{source.pr_number}"
        try:
            pr_response = requests.get(pr_url, headers=headers, timeout=30)
            pr_response.raise_for_status()
        except requests.RequestException as e:
            raise PRFetchError(f"Failed to fetch PR: {e}") from e

        pr_data = pr_response.json()

        # Fetch diff
        diff_headers = dict(headers)
        diff_headers["Accept"] = "application/vnd.github.v3.diff"
        try:
            diff_response = requests.get(pr_url, headers=diff_headers, timeout=30)
            diff_response.raise_for_status()
        except requests.RequestException as e:
            raise PRFetchError(f"Failed to fetch PR diff: {e}") from e

        diff = diff_response.text
        files_changed = self._parse_files_from_diff(diff)

        return PRContent(
            title=pr_data.get("title", ""),
            body=pr_data.get("body", "") or "",
            author=pr_data.get("user", {}).get("login", "unknown"),
            labels=[label.get("name", "") for label in pr_data.get("labels", [])],
            state=pr_data.get("state", "unknown"),
            source=source,
            diff=diff,
            files_changed=files_changed,
        )

    def _parse_files_from_diff(self, diff: str) -> list[str]:
        files = []
        for line in diff.split("\n"):
            if line.startswith("diff --git a/"):
                parts = line.split(" b/", 1)
                if len(parts) == 2:
                    files.append(parts[1])
        return files


class GitLabPRFetcher:
    _BASE_URL = "https://gitlab.com/api/v4"

    def __init__(self, token: str | None = None):
        self._token = token

    def fetch(self, source: PRSource) -> PRContent:
        headers = {"User-Agent": "mycrew-pr-reviewer"}
        if self._token:
            headers["PRIVATE-TOKEN"] = self._token

        # Fetch MR metadata + changes
        mr_url = (
            f"{self._BASE_URL}/projects/{source.owner}%2F{source.repo}"
            f"/merge_requests/{source.pr_number}/changes"
        )
        try:
            response = requests.get(mr_url, headers=headers, timeout=30)
            response.raise_for_status()
        except requests.RequestException as e:
            raise PRFetchError(f"Failed to fetch MR: {e}") from e

        mr_data = response.json()

        # Fetch diff
        diff_url = (
            f"{self._BASE_URL}/projects/{source.owner}%2F{source.repo}"
            f"/merge_requests/{source.pr_number}"
        )
        try:
            diff_response = requests.get(diff_url, headers=headers, timeout=30)
            diff_response.raise_for_status()
        except requests.RequestException as e:
            raise PRFetchError(f"Failed to fetch MR diff: {e}") from e

        diff_data = diff_response.json()
        diff = diff_data.get("diff", "")
        files_changed = self._parse_files_from_diff(diff)

        return PRContent(
            title=mr_data.get("title", ""),
            body=mr_data.get("description", "") or "",
            author=mr_data.get("author", {}).get("username", "unknown"),
            labels=mr_data.get("labels", []),
            state=mr_data.get("state", "unknown"),
            source=source,
            diff=diff,
            files_changed=files_changed,
        )

    def _parse_files_from_diff(self, diff: str) -> list[str]:
        files = []
        for line in diff.split("\n"):
            if line.startswith("diff --git a/"):
                parts = line.split(" b/", 1)
                if len(parts) == 2:
                    files.append(parts[1])
        return files
