#!/usr/bin/env python
"""Simplified Code Pipeline Flow - Core pipeline logic only."""

import argparse
import logging
import os
import re
import subprocess
import tempfile
import uuid
from pathlib import Path

from crewai.flow import Flow, listen, or_, start
from crewai.flow.persistence import SQLiteFlowPersistence, persist
from crewai.utilities.paths import db_storage_path
from pydantic import BaseModel

# Load settings before any CrewAI imports
from mycrew.settings import get_settings
from mycrew.utils import (
    clone_repo_for_issue,
    delete_cloned_repo,
    detect_github_repo,
)

get_settings().apply_crewai_telemetry()  # noqa: E402

from mycrew.crews.architect_crew.architect_crew import ArchitectCrew  # noqa: E402
from mycrew.crews.clarify_crew.clarify_crew import ClarifyCrew  # noqa: E402
from mycrew.crews.commit_crew.commit_crew import CommitCrew  # noqa: E402
from mycrew.crews.explorer_crew.explorer_crew import ExplorerCrew  # noqa: E402
from mycrew.crews.implementer_crew.implementer_crew import ImplementerCrew  # noqa: E402
from mycrew.crews.issue_analyst_crew.issue_analyst_crew import IssueAnalystCrew  # noqa: E402
from mycrew.crews.reviewer_crew.reviewer_crew import ReviewerCrew  # noqa: E402
from mycrew.crews.tactiq_research_crew.tactiq_research_crew import (
    TactiqResearchCrew,
)  # noqa: E402

logger = logging.getLogger("mycrew.main")


class PipelineState(BaseModel):
    """Minimal pipeline state."""

    issue_url: str
    branch: str = ""
    max_retries: int = 3
    dry_run: bool = False
    programmatic: bool = False
    repo_path: str = ""  # User-provided repo path (optional)
    repo_path_cloned: bool = False  # True if repo was cloned (for cleanup)

    # Core state fields
    repo_root: Path | None = None
    issue_data: dict | None = None
    exploration_result: dict | None = None
    architecture_result: dict | None = None
    implementation_result: dict | None = None
    review_result: dict | None = None
    validation_result: dict | None = None
    commit_result: dict | None = None
    tactiq_meeting_id: str = ""
    tactiq_result: dict | None = None

    # Retry tracking
    retry_count: int = 0
    current_stage: str = ""


@persist(
    SQLiteFlowPersistence(
        db_path=str(Path(db_storage_path()) / "code_pipeline_flow_states.db")
    ),
    verbose=False,
)
class CodePipelineFlow(Flow[PipelineState]):
    """Simplified code pipeline flow."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _get_field_from_state(self, field_name: str, default=None):
        """Get field from state with fallback."""
        return getattr(self.state, field_name, default)

    def _run_crew(self, crew_class, crew_name: str, input_data: dict | None = None):
        """Run a crew with simplified error handling."""
        if not crew_class:
            logger.info(f"Skipping {crew_name}: crew_class is None")
            return None

        logger.info(f"Starting {crew_name} crew")
        try:
            crew = crew_class()
            result = crew.kickoff(inputs=input_data)
            logger.info(f"Completed {crew_name} crew")
            return result.raw
        except Exception as e:
            logger.error(f"Failed {crew_name} crew: {e}")
            return None

    def _run_validate_tests(self, test_command: str | None = None):
        """Run test validation."""
        if not test_command:
            test_command = self._get_field_from_state("test_command")

        if not test_command:
            logger.info("validate_tests: no test command provided")
            return {"passed": False, "output": "No test command provided"}

        try:
            result = subprocess.run(
                test_command,
                shell=True,
                cwd=self.state.repo_root,
                capture_output=True,
                text=True,
            )
            passed = result.returncode == 0
            logger.info(f"validate_tests: tests {'passed' if passed else 'failed'}")
            return {"passed": passed, "output": result.stdout}
        except Exception as e:
            logger.error(f"validate_tests: error running tests: {e}")
            return {"passed": False, "output": str(e)}

    @start()
    def start(self):
        """Start the pipeline."""
        logger.info(f"Starting pipeline: {self.state.issue_url}")
        return self.explore

    @listen(start)
    def explore(self):
        """Explore the repository."""
        self.state.current_stage = "explore"

        url = self.state.issue_url.strip() if self.state.issue_url else ""
        rp = self.state.repo_path.strip() if self.state.repo_path else ""

        if not url and not rp:
            logger.error("Either issue_url or --repo-path is required")
            return self.end

        if rp:
            return self._explore_with_repo_path(rp, url)

        return self._explore_with_clone(url)

    def _explore_with_repo_path(self, rp: str, url: str):
        """Handle exploration with user-provided repo path."""
        if not os.path.isdir(rp):
            logger.error(f"repo_path does not exist: {rp}")
            return self.end

        self.state.repo_root = Path(os.path.abspath(rp))
        logger.info(f"Using provided repo path: {self.state.repo_root}")

        if not url:
            github_repo = detect_github_repo(str(self.state.repo_root))
            if not github_repo:
                logger.error("Could not detect github_repo from local repo")
                return self.end
            self.state.issue_data = {
                "owner": github_repo.split("/")[0],
                "repo": github_repo.split("/")[1],
                "kind": "repo",
                "number": "",
                "is_pull": False,
                "github_repo": github_repo,
            }
            result = self._run_crew(
                ExplorerCrew,
                "explore",
                {"issue_url": "", "issue_data": self.state.issue_data},
            )
            if not result:
                logger.error("explore: exploration failed")
                return self.end
            self.state.exploration_result = result
            return self.analyze_issue

        m = re.search(
            r"https?://(?:www\.)?github\.com/([^/]+)/([^/]+)/(issues|pull)/(\d+)",
            url,
            re.IGNORECASE,
        )
        if not m:
            logger.error(f"explore: invalid issue URL: {url}")
            return self.end

        owner, repo_name, kind, number = (
            m.group(1),
            m.group(2),
            m.group(3).lower(),
            m.group(4),
        )
        self.state.issue_data = {
            "owner": owner,
            "repo": repo_name,
            "kind": kind,
            "number": number,
            "is_pull": kind == "pull",
            "github_repo": f"{owner}/{repo_name}",
        }
        return self._run_exploration()

    def _explore_with_clone(self, url: str):
        """Handle exploration by cloning repo from GitHub issue URL."""
        m = re.search(
            r"https?://(?:www\.)?github\.com/([^/]+)/([^/]+)/(issues|pull)/(\d+)",
            url,
            re.IGNORECASE,
        )
        if not m:
            logger.error(f"explore: invalid issue URL: {url}")
            return self.end

        owner, repo_name, kind, number = (
            m.group(1),
            m.group(2),
            m.group(3).lower(),
            m.group(4),
        )
        self.state.issue_data = {
            "owner": owner,
            "repo": repo_name,
            "kind": kind,
            "number": number,
            "is_pull": kind == "pull",
            "github_repo": f"{owner}/{repo_name}",
        }

        settings = get_settings()
        github_repo = f"{owner}/{repo_name}"
        branch = self.state.branch if self.state.branch else "main"
        token = settings.github_token

        if not token:
            logger.error("GITHUB_TOKEN required to clone repo")
            return self.end

        parent_dir = os.path.join(
            tempfile.gettempdir(), f"code_pipeline_{uuid.uuid4().hex[:8]}"
        )

        try:
            cloned_path = clone_repo_for_issue(github_repo, parent_dir, branch, token)
            self.state.repo_root = Path(cloned_path)
            self.state.repo_path_cloned = True
            logger.info(f"Cloned repo to: {self.state.repo_root}")
        except Exception as e:
            logger.error(f"Failed to clone repo: {e}")
            return self.end

        return self._run_exploration()

    def _run_exploration(self):
        """Run the exploration crew. Returns next stage or self.end."""
        result = self._run_crew(
            ExplorerCrew,
            "explore",
            {"issue_url": self.state.issue_url, "issue_data": self.state.issue_data},
        )

        if not result:
            logger.error("explore: exploration failed")
            return self.end

        self.state.exploration_result = result
        return self.analyze_issue

    @listen(explore)
    def analyze_issue(self):
        """Analyze the issue."""
        self.state.current_stage = "analyze_issue"

        result = self._run_crew(
            IssueAnalystCrew,
            "analyze_issue",
            {
                "issue_url": self.state.issue_url,
                "issue_data": self.state.issue_data,
                "exploration_result": self.state.exploration_result,
            },
        )

        if not result:
            logger.error("analyze_issue: issue analysis failed")
            return self.end

        # If tactiq_meeting_id is provided, run tactiq_research
        if self.state.tactiq_meeting_id:
            return self.tactiq_research

        return self.clarify

    @listen(analyze_issue)
    def tactiq_research(self):
        """Fetch meeting context from Tactiq and determine if clarification is needed."""
        self.state.current_stage = "tactiq_research"

        result = self._run_crew(
            TactiqResearchCrew,
            "tactiq_research",
            {
                "task": self.state.issue_data.get("task", "")
                if self.state.issue_data
                else "",
                "issue_analysis": self.state.issue_data,
                "exploration": self.state.exploration_result,
                "tactiq_meeting_id": self.state.tactiq_meeting_id,
            },
        )

        if not result:
            logger.info("tactiq_research: failed, falling back to clarify")
            return self.clarify

        self.state.tactiq_result = result

        # Check if clarification is still needed based on result
        # If "sufficient_info: true" is in the result, skip clarification
        if isinstance(result, str) and "sufficient_info: true" in result.lower():
            logger.info("tactiq_research: sufficient info found, skipping clarify")
            return self.architect

            logger.info("tactiq_research: clarification still needed")
        return self.clarify

    @listen(analyze_issue)
    def clarify(self):
        """Clarify requirements."""
        self.state.current_stage = "clarify"

        result = self._run_crew(
            ClarifyCrew,
            "clarify",
            {
                "issue_url": self.state.issue_url,
                "issue_data": self.state.issue_data,
                "exploration_result": self.state.exploration_result,
            },
        )

        if not result:
            logger.error("clarify: clarification failed")
            return self.end

        return self.architect

    @listen(clarify)
    def architect(self):
        """Create architecture."""
        self.state.current_stage = "architect"

        result = self._run_crew(
            ArchitectCrew,
            "architect",
            {
                "issue_url": self.state.issue_url,
                "issue_data": self.state.issue_data,
                "exploration_result": self.state.exploration_result,
            },
        )

        if not result:
            logger.error("architect: architecture failed")
            return self.end

        self.state.architecture_result = result
        return self.implement

    @listen(architect)
    def implement(self):
        """Implement solution."""
        self.state.current_stage = "implement"

        result = self._run_crew(
            ImplementerCrew,
            "implement",
            {
                "issue_url": self.state.issue_url,
                "issue_data": self.state.issue_data,
                "exploration_result": self.state.exploration_result,
                "architecture_result": self.state.architecture_result,
            },
        )

        if not result:
            logger.error("implement: implementation failed")
            return self.retry_implement

        self.state.implementation_result = result
        return self.review

    @listen(implement)
    def review(self):
        """Review implementation."""
        self.state.current_stage = "review"

        result = self._run_crew(
            ReviewerCrew,
            "review",
            {
                "issue_url": self.state.issue_url,
                "issue_data": self.state.issue_data,
                "exploration_result": self.state.exploration_result,
                "architecture_result": self.state.architecture_result,
                "implementation_result": self.state.implementation_result,
            },
        )

        if not result:
            logger.error("review: review failed")
            return self.retry_implement

        self.state.review_result = result

        # Check review verdict
        verdict = result.get("verdict", {}).get("verdict", "ISSUES")
        if verdict == "ISSUES":
            logger.warning("review: implementation has issues")
            return self.retry_implement
        else:  # APPROVED
            logger.info("review: implementation approved")
            return self.validate_tests

    @listen(review)
    def validate_tests(self):
        """Validate tests."""
        self.state.current_stage = "validate_tests"

        result = self._run_validate_tests()
        self.state.validation_result = result

        if result.get("passed", False):
            logger.info("validate_tests: tests passed")
            return self.commit
        else:
            logger.warning("validate_tests: tests failed")
            return self.retry_implement

    @listen(validate_tests)
    def commit(self):
        """Commit changes."""
        self.state.current_stage = "commit"

        result = self._run_crew(
            CommitCrew,
            "commit",
            {
                "issue_url": self.state.issue_url,
                "issue_data": self.state.issue_data,
                "exploration_result": self.state.exploration_result,
                "implementation_result": self.state.implementation_result,
                "review_result": self.state.review_result,
                "validation_result": self.state.validation_result,
            },
        )

        if not result:
            logger.error("commit: commit failed")
            return self.end

        self.state.commit_result = result
        return self.end

    @listen(or_(implement, review, validate_tests))
    def retry_implement(self):
        """Retry implementation."""
        self.state.current_stage = "retry_implement"
        self.state.retry_count += 1

        if self.state.retry_count > self.state.max_retries:
            logger.error(
                f"retry_implement: max retries exceeded ({self.state.max_retries})"
            )
            return self.end

            logger.info(
                f"retry_implement: retry {self.state.retry_count}/{self.state.max_retries}"
            )
        return self.implement

    @listen(explore)
    @listen(analyze_issue)
    @listen(clarify)
    @listen(architect)
    @listen(implement)
    @listen(review)
    @listen(validate_tests)
    @listen(commit)
    @listen(retry_implement)
    def end(self):
        """End the pipeline."""
        # Clean up cloned repo if we cloned it
        if self.state.repo_path_cloned and self.state.repo_root:
            try:
                delete_cloned_repo(str(self.state.repo_root))
            except Exception as e:
                logger.warning(f"Failed to delete cloned repo: {e}")

        logger.info(f"Pipeline completed: {self.state.issue_url}")
        return None


def _configure_logging(level: int | str | None = None):
    """Configure logging."""
    if level is None:
        level = logging.INFO

    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def kickoff(
    issue_url: str,
    branch: str = "",
    from_scratch: bool = False,
    max_retries: int = 3,
    dry_run: bool = False,
    programmatic: bool = False,
    tactiq_meeting_id: str = "",
    repo_path: str = "",
):
    """Kickoff the pipeline."""
    state = PipelineState(
        issue_url=issue_url,
        branch=branch,
        max_retries=max_retries,
        dry_run=dry_run,
        programmatic=programmatic,
        tactiq_meeting_id=tactiq_meeting_id,
        repo_path=repo_path,
    )
    flow = CodePipelineFlow(state=state)
    flow.kickoff()


def _main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Code Pipeline")
    parser.add_argument("issue_url", help="GitHub issue URL", nargs="?")
    parser.add_argument(
        "--repo-path",
        default="",
        help="Local repo path (if not provided, repo will be cloned)",
    )
    parser.add_argument("--branch", default="", help="Branch name")
    parser.add_argument(
        "--from-scratch", action="store_true", help="Start from scratch"
    )
    parser.add_argument("--max-retries", type=int, default=3, help="Max retries")
    parser.add_argument("--dry-run", action="store_true", help="Dry run")
    parser.add_argument("--programmatic", action="store_true", help="Programmatic mode")
    parser.add_argument(
        "--tactiq-meeting-id", default="", help="Tactiq meeting ID for context"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    parser.add_argument("--debug", action="store_true", help="Debug logging")

    args = parser.parse_args()

    # Must provide either issue_url or repo_path
    if not args.issue_url and not args.repo_path:
        parser.error("Either issue_url or --repo-path is required")

    if args.debug:
        log_level = logging.DEBUG
    elif args.verbose:
        log_level = logging.INFO
    else:
        log_level = None

    _configure_logging(level=log_level)

    kickoff(
        issue_url=args.issue_url or "",
        repo_path=args.repo_path,
        branch=args.branch,
        from_scratch=args.from_scratch,
        max_retries=args.max_retries,
        dry_run=args.dry_run,
        programmatic=args.programmatic,
        tactiq_meeting_id=args.tactiq_meeting_id,
    )


if __name__ == "__main__":
    _main()
