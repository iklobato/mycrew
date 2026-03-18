"""Pipeline runner - orchestrates all crews."""

import logging
import os
import re

from mycrew.shared.settings import get_settings, set_pipeline_context, PipelineContext
from mycrew.shared.issues import IssueHandlerFactory
from mycrew.shared.issues import IssueFetchError, IssueParseError

logger = logging.getLogger("mycrew")


class PipelineRunner:
    def __init__(self, repo_path: str | None):
        self.repo_path = os.path.abspath(repo_path) if repo_path else os.getcwd()
        set_pipeline_context(PipelineContext(repo_path=self.repo_path))
        self.settings = get_settings()

    def run(self, issue_url: str) -> dict:
        logger.info("Starting pipeline...")

        # Fetch issue
        handler = IssueHandlerFactory.create(
            github_token=self.settings.github_token or None,
            gitlab_token=self.settings.gitlab_token
            or self.settings.github_token
            or None,
        )
        try:
            issue_content = handler.process(issue_url)
        except (IssueParseError, IssueFetchError) as e:
            logger.error(f"Failed to fetch issue: {e}")
            raise

        # Format issue description
        issue_description = f"""# {issue_content.title}

{issue_content.body}

**Author:** {issue_content.author}
**Labels:** {", ".join(issue_content.labels) if issue_content.labels else "none"}
**State:** {issue_content.state}
**Source:** {issue_content.source.web_url}
"""

        # Extract issue number
        match = re.search(r"/issues/(\d+)", issue_url)
        issue_number = match.group(1) if match else "unknown"

        # Import agents here to avoid circular imports
        from mycrew.agents.development.issue_analyst import IssueAnalystCrew
        from mycrew.agents.development.explorer import ExplorerCrew
        from mycrew.agents.development.clarify import ClarifyCrew
        from mycrew.agents.development.architect import ArchitectCrew
        from mycrew.agents.development.implementer import (
            ImplementerCrew,
            parse_code_blocks,
            write_files_from_specs,
        )
        from mycrew.agents.development.test_validator import TestValidatorCrew
        from mycrew.agents.development.reviewer import ReviewerCrew
        from mycrew.agents.development.commit import CommitCrew

        # Run Issue Analyst
        issue_analysis_result = IssueAnalystCrew().run(
            inputs={"issue_description": issue_description}
        )
        issue_analysis = issue_analysis_result.raw

        # Run Explorer
        explorer_result = ExplorerCrew().run(
            inputs={
                "issue_analysis": issue_analysis,
                "repo_path": self.repo_path,
            }
        )
        exploration = explorer_result.raw

        # Run Clarify
        clarify_result = ClarifyCrew().run(
            inputs={
                "issue_analysis": issue_analysis,
                "exploration": exploration,
                "repo_path": self.repo_path,
            }
        )
        clarifications = clarify_result.raw

        # Run Architect
        architect_result = ArchitectCrew().run(
            inputs={
                "issue_description": issue_description,
                "issue_analysis": issue_analysis,
                "exploration": exploration,
                "clarifications": clarifications,
                "repo_path": self.repo_path,
            }
        )
        plan = architect_result.raw

        # Run Implementer
        implementer_result = ImplementerCrew().run(
            inputs={
                "issue_description": issue_description,
                "plan": plan,
                "repo_path": self.repo_path,
            }
        )
        implementation = implementer_result.raw

        # File writing
        files_spec = parse_code_blocks(implementation)
        written_files = []
        if files_spec:
            written_files = write_files_from_specs(files_spec, self.repo_path)
            logger.info(f"Wrote {len(written_files)} files")
        else:
            logger.warning("No files to write")

        # Run Test Validator
        test_result = TestValidatorCrew().run(
            inputs={
                "plan": plan,
                "implementation": implementation,
                "repo_path": self.repo_path,
            }
        )
        tests = test_result.raw

        # Run Reviewer
        review_result = ReviewerCrew().run(
            inputs={
                "implementation": implementation,
                "tests": tests,
                "repo_path": self.repo_path,
            }
        )
        review = review_result.raw

        # Run Commit
        commit_result = CommitCrew().run(
            inputs={
                "implementation": implementation,
                "review": review,
                "repo_path": self.repo_path,
                "issue_number": issue_number,
            }
        )
        commit = commit_result.raw

        logger.info("Pipeline complete")

        return {
            "issue_analysis": issue_analysis,
            "exploration": exploration,
            "clarifications": clarifications,
            "plan": plan,
            "implementation": implementation,
            "written_files": written_files,
            "tests": tests,
            "review": review,
            "commit": commit,
        }
