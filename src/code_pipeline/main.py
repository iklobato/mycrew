#!/usr/bin/env python
"""Simplified Code Pipeline Flow - Core pipeline logic only."""

import argparse
import logging
import subprocess
from pathlib import Path

from crewai.flow import Flow, listen, or_, start
from crewai.flow.persistence import SQLiteFlowPersistence, persist
from crewai.utilities.paths import db_storage_path
from pydantic import BaseModel

# Load settings before any CrewAI imports
from code_pipeline.settings import get_settings

get_settings().apply_crewai_telemetry()  # noqa: E402

from code_pipeline.crews.architect_crew.architect_crew import ArchitectCrew  # noqa: E402
from code_pipeline.crews.clarify_crew.clarify_crew import ClarifyCrew  # noqa: E402
from code_pipeline.crews.commit_crew.commit_crew import CommitCrew  # noqa: E402
from code_pipeline.crews.explorer_crew.explorer_crew import ExplorerCrew  # noqa: E402
from code_pipeline.crews.implementer_crew.implementer_crew import ImplementerCrew  # noqa: E402
from code_pipeline.crews.issue_analyst_crew.issue_analyst_crew import IssueAnalystCrew  # noqa: E402
from code_pipeline.crews.reviewer_crew.reviewer_crew import ReviewerCrew  # noqa: E402
from code_pipeline.crews.tactiq_research_crew.tactiq_research_crew import (
    TactiqResearchCrew,
)  # noqa: E402

logger = logging.getLogger(__name__)


class PipelineState(BaseModel):
    """Minimal pipeline state."""

    issue_url: str
    branch: str = ""
    max_retries: int = 3
    dry_run: bool = False
    programmatic: bool = False

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

    def _log_step(self, step: str, message: str, **kwargs):
        """Consolidated logging helper."""
        logger.info(f"PIPELINE step={step} {message}", extra=kwargs)

    def _get_field_from_state(self, field_name: str, default=None):
        """Get field from state with fallback."""
        return getattr(self.state, field_name, default)

    def _run_crew(self, crew_class, crew_name: str, input_data: dict | None = None):
        """Run a crew with simplified error handling."""
        if not crew_class:
            self._log_step(crew_name, "crew_class is None, skipping")
            return None

        try:
            crew = crew_class()
            result = crew.kickoff(inputs=input_data)
            self._log_step(crew_name, "completed successfully")
            return result.raw
        except Exception as e:
            self._log_step(crew_name, f"failed: {e}")
            return None

    def _run_validate_tests(self, test_command: str | None = None):
        """Run test validation."""
        if not test_command:
            test_command = self._get_field_from_state("test_command")

        if not test_command:
            self._log_step("validate_tests", "no test command provided")
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
            self._log_step(
                "validate_tests", f"tests {'passed' if passed else 'failed'}"
            )
            return {"passed": passed, "output": result.stdout}
        except Exception as e:
            self._log_step("validate_tests", f"error running tests: {e}")
            return {"passed": False, "output": str(e)}

    @start()
    def start(self):
        """Start the pipeline."""
        self._log_step("start", f"starting pipeline for {self.state.issue_url}")
        return self.explore

    @listen(start)
    def explore(self):
        """Explore the repository."""
        self.state.current_stage = "explore"

        # Parse issue URL
        import re

        url = self.state.issue_url.strip()
        m = re.search(
            r"https?://(?:www\.)?github\.com/([^/]+)/([^/]+)/(issues|pull)/(\d+)",
            url,
            re.IGNORECASE,
        )
        if not m:
            self._log_step("explore", f"invalid issue URL: {self.state.issue_url}")
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

        # Get repo root
        import os

        self.state.repo_root = Path(os.getcwd())

        # Run exploration
        result = self._run_crew(
            ExplorerCrew,
            "explore",
            {
                "issue_url": self.state.issue_url,
                "issue_data": self.state.issue_data,
            },
        )

        if not result:
            self._log_step("explore", "exploration failed")
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
            self._log_step("analyze_issue", "issue analysis failed")
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
            self._log_step("tactiq_research", "failed, falling back to clarify")
            return self.clarify

        self.state.tactiq_result = result

        # Check if clarification is still needed based on result
        # If "sufficient_info: true" is in the result, skip clarification
        if isinstance(result, str) and "sufficient_info: true" in result.lower():
            self._log_step("tactiq_research", "sufficient info found, skipping clarify")
            return self.architect

        self._log_step("tactiq_research", "clarification still needed")
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
            self._log_step("clarify", "clarification failed")
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
            self._log_step("architect", "architecture failed")
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
            self._log_step("implement", "implementation failed")
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
            self._log_step("review", "review failed")
            return self.retry_implement

        self.state.review_result = result

        # Check review verdict
        verdict = result.get("verdict", {}).get("verdict", "ISSUES")
        if verdict == "ISSUES":
            self._log_step("review", "implementation has issues")
            return self.retry_implement
        else:  # APPROVED
            self._log_step("review", "implementation approved")
            return self.validate_tests

    @listen(review)
    def validate_tests(self):
        """Validate tests."""
        self.state.current_stage = "validate_tests"

        result = self._run_validate_tests()
        self.state.validation_result = result

        if result.get("passed", False):
            self._log_step("validate_tests", "tests passed")
            return self.commit
        else:
            self._log_step("validate_tests", "tests failed")
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
            self._log_step("commit", "commit failed")
            return self.end

        self.state.commit_result = result
        return self.end

    @listen(or_(implement, review, validate_tests))
    def retry_implement(self):
        """Retry implementation."""
        self.state.current_stage = "retry_implement"
        self.state.retry_count += 1

        if self.state.retry_count > self.state.max_retries:
            self._log_step(
                "retry_implement", f"max retries exceeded ({self.state.max_retries})"
            )
            return self.end

        self._log_step(
            "retry_implement",
            f"retry {self.state.retry_count}/{self.state.max_retries}",
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
        self._log_step("end", f"pipeline completed for {self.state.issue_url}")
        return None


def _configure_logging(level: int | str | None = None):
    """Configure logging."""
    if level is None:
        level = logging.INFO

    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
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
):
    """Kickoff the pipeline."""
    state = PipelineState(
        issue_url=issue_url,
        branch=branch,
        max_retries=max_retries,
        dry_run=dry_run,
        programmatic=programmatic,
        tactiq_meeting_id=tactiq_meeting_id,
    )
    flow = CodePipelineFlow(state=state)
    flow.kickoff()


def _main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Code Pipeline")
    parser.add_argument("issue_url", help="GitHub issue URL")
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

    if args.debug:
        log_level = logging.DEBUG
    elif args.verbose:
        log_level = logging.INFO
    else:
        log_level = None

    _configure_logging(level=log_level)

    kickoff(
        issue_url=args.issue_url,
        branch=args.branch,
        from_scratch=args.from_scratch,
        max_retries=args.max_retries,
        dry_run=args.dry_run,
        programmatic=args.programmatic,
        tactiq_meeting_id=args.tactiq_meeting_id,
    )


if __name__ == "__main__":
    _main()
