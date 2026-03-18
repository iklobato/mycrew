"""Review runner - orchestrates PR review pipeline."""

import logging
import os
import re

import requests

from mycrew.shared.pulls import PRHandlerFactory
from mycrew.shared.settings import Settings, set_pipeline_context, PipelineContext
from mycrew.agents.review.pr_review import PRReviewCrew

logger = logging.getLogger("mycrew")


class ReviewRunner:
    def __init__(self, repo_path: str | None):
        self.repo_path = os.path.abspath(repo_path) if repo_path else os.getcwd()
        self.settings = Settings()

    def run(self, pr_url: str) -> str:
        logger.info("Starting PR review...")

        # Fetch PR
        handler = PRHandlerFactory.create(
            github_token=self.settings.github_token or None,
            gitlab_token=self.settings.gitlab_token
            or self.settings.github_token
            or None,
        )
        pr_content = handler.process(pr_url)

        # Set context
        set_pipeline_context(
            PipelineContext(
                repo_path=self.repo_path,
                pr_url=pr_url,
            )
        )

        # Run crew
        result = PRReviewCrew().run(
            inputs={
                "pr_title": pr_content.title,
                "pr_body": pr_content.body,
                "pr_author": pr_content.author,
                "pr_labels": ", ".join(pr_content.labels)
                if pr_content.labels
                else "none",
                "pr_diff": pr_content.diff,
                "changed_files": "\n".join(pr_content.files_changed),
            }
        )

        review = result.raw

        # Post comment
        self._post_pr_comment(pr_url, review)

        logger.info("PR review complete")

        return review

    def _post_pr_comment(self, pr_url: str, review_body: str) -> None:
        # Parse URL
        if "github.com" in pr_url.lower():
            self._post_github_comment(pr_url, review_body)
        elif "gitlab.com" in pr_url.lower():
            self._post_gitlab_comment(pr_url, review_body)
        else:
            logger.warning("Unsupported PR source, printing review instead:")
            print(review_body)

    def _post_github_comment(self, pr_url: str, review_body: str) -> None:
        match = re.search(
            r"github\.com/([^/]+)/([^/]+)/pull/(\d+)", pr_url, re.IGNORECASE
        )
        if not match:
            logger.error("Could not parse GitHub PR URL: %s", pr_url)
            return

        owner, repo, pr_number = match.groups()

        token = self.settings.github_token
        if not token:
            logger.warning("No GitHub token, printing review instead:")
            print(review_body)
            return

        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
        }
        url = f"https://api.github.com/repos/{owner}/{repo}/issues/{pr_number}/comments"

        try:
            response = requests.post(
                url,
                headers=headers,
                json={"body": review_body},
                timeout=30,
            )
            response.raise_for_status()
            logger.info("Posted review comment to GitHub PR")
        except requests.RequestException as e:
            logger.error("Failed to post comment: %s", e)
            logger.info("Review body:\n%s", review_body)

    def _post_gitlab_comment(self, pr_url: str, review_body: str) -> None:
        match = re.search(
            r"gitlab\.com/([^/]+)/([^/]+)/-?/merge_requests/(\d+)",
            pr_url,
            re.IGNORECASE,
        )
        if not match:
            logger.error("Could not parse GitLab MR URL: %s", pr_url)
            return

        owner, repo, mr_iid = match.groups()

        token = self.settings.gitlab_token or self.settings.github_token
        if not token:
            logger.warning("No GitLab token, printing review instead:")
            print(review_body)
            return

        headers = {
            "PRIVATE-TOKEN": token,
        }
        project_id = f"{owner}%2F{repo}"
        url = f"https://gitlab.com/api/v4/projects/{project_id}/merge_requests/{mr_iid}/notes"

        try:
            response = requests.post(
                url,
                headers=headers,
                json={"body": review_body},
                timeout=30,
            )
            response.raise_for_status()
            logger.info("Posted review comment to GitLab MR")
        except requests.RequestException as e:
            logger.error("Failed to post comment: %s", e)
            logger.info("Review body:\n%s", review_body)
