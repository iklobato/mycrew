"""Flow orchestration - all orchestration classes in one file.

Classes:
- StageRunner: Runs a single crew stage
- VerdictParser: Parses review verdict from result
- RetryHandler: Handles retry logic
- FlowCoordinator: Orchestrates stage sequence
- CLI: CLI entry point
"""

import argparse
import logging
import uuid
from typing import Any

from mycrew.result import StageResult, StageStatus


class VerdictParser:
    """Parses verdict from review result."""

    def parse(self, result: Any) -> str:
        """Parse verdict from raw result."""
        if isinstance(result, dict):
            inner_verdict = result.get("verdict", {})
            if isinstance(inner_verdict, dict):
                verdict_val = inner_verdict.get("verdict")
                if verdict_val is not None:
                    return verdict_val

        result_str = str(result).upper()
        if "APPROVED" in result_str:
            return "APPROVED"
        return "ISSUES"


class RetryHandler:
    """Handles retry logic."""

    def should_retry(self, state) -> bool:
        """Check if retry should happen."""
        return state.retry_count < state.max_retries

    def increment_retry(self, state):
        """Increment retry counter."""
        state.retry_count += 1


class StageRunner:
    """Runs a single crew stage."""

    def run(self, crew_class, state, inputs=None):
        """Execute a crew with input building."""
        from mycrew.settings import set_pipeline_context, PipelineContext

        github_repo = ""
        if state.issue_data and isinstance(state.issue_data, dict):
            github_repo = state.issue_data.get("github_repo", "")

        ctx = PipelineContext(
            repo_path=state.repo_root or state.repo_path,
            github_repo=github_repo,
            issue_url=state.issue_url,
            programmatic=state.programmatic,
        )
        set_pipeline_context(ctx)

        try:
            crew_instance = crew_class()
            final_inputs = crew_instance.build_inputs(state, inputs)
            crew = crew_instance.crew()
            result = crew.kickoff(inputs=final_inputs)
            return StageResult(status=StageStatus.COMPLETED, data={"raw": result})
        except Exception as e:
            logging.error(f"Stage runner failed: {e}")
            return StageResult(status=StageStatus.FAILED, error=str(e))


class FlowCoordinator:
    """Orchestrates the pipeline stage sequence."""

    def __init__(self, state):
        self.state = state
        self.runner = StageRunner()
        self.verdict_parser = VerdictParser()
        self.retry_handler = RetryHandler()
        self._load_crews()

    def _load_crews(self):
        """Load crew registry."""
        from mycrew.crews.explorer_crew.explorer_crew import ExplorerCrew
        from mycrew.crews.issue_analyst_crew.issue_analyst_crew import IssueAnalystCrew
        from mycrew.crews.architect_crew.architect_crew import ArchitectCrew
        from mycrew.crews.implementer_crew.implementer_crew import ImplementerCrew
        from mycrew.crews.reviewer_crew.reviewer_crew import ReviewerCrew
        from mycrew.crews.commit_crew.commit_crew import CommitCrew

        self._crew_registry = {
            "explore": ExplorerCrew,
            "analyze": IssueAnalystCrew,
            "architect": ArchitectCrew,
            "implement": ImplementerCrew,
            "review": ReviewerCrew,
            "commit": CommitCrew,
        }

        self._stage_order = [
            "explore",
            "analyze",
            "architect",
            "implement",
            "review",
            "commit",
        ]

    def next_stage(self, current: str) -> str | None:
        """Get next stage in sequence."""
        try:
            idx = self._stage_order.index(current)
            if idx + 1 < len(self._stage_order):
                return self._stage_order[idx + 1]
        except ValueError:
            pass
        return None

    def run_stage(self, stage: str, inputs: dict | None = None) -> StageResult:
        """Run a single stage."""
        crew_class = self._crew_registry.get(stage)
        if not crew_class:
            logging.warning(f"No crew registered for stage: {stage}")
            return StageResult(status=StageStatus.FAILED, error="No crew found")
        return self.runner.run(crew_class, self.state, inputs)

    def should_proceed(self, stage: str, result: StageResult) -> bool:
        """Check if should proceed to next stage."""
        if result.status == StageStatus.FAILED:
            return False
        if stage == "review":
            verdict = self.verdict_parser.parse(
                result.data.get("raw", {}) if result.data else {}
            )
            return verdict == "APPROVED"
        return True

    def run(self):
        """Run the full pipeline."""
        self.state.current_stage = "explore"
        result = self.run_stage("explore", {"issue_url": self.state.issue_url})
        self.state.explore_result = result

        if not self.should_proceed("explore", result):
            return

        self.state.current_stage = "analyze"
        result = self.run_stage(
            "analyze",
            {
                "issue_url": self.state.issue_url,
                "issue_data": self.state.issue_data,
                "exploration_result": self.state.explore_result.data
                if self.state.explore_result
                else None,
            },
        )
        self.state.analyze_result = result

        if not self.should_proceed("analyze", result):
            return

        self.state.current_stage = "architect"
        result = self.run_stage(
            "architect",
            {
                "issue_url": self.state.issue_url,
                "issue_data": self.state.issue_data,
                "exploration_result": self.state.explore_result.data
                if self.state.explore_result
                else None,
            },
        )
        self.state.architect_result = result

        if not self.should_proceed("architect", result):
            return

        self.state.current_stage = "implement"
        result = self.run_stage(
            "implement",
            {
                "issue_url": self.state.issue_url,
                "issue_data": self.state.issue_data,
                "exploration": self.state.explore_result.data
                if self.state.explore_result
                else None,
                "plan": self.state.architect_result.data
                if self.state.architect_result
                else None,
            },
        )
        self.state.implement_result = result

        if not self.should_proceed("implement", result):
            if self.retry_handler.should_retry(self.state):
                self.retry_handler.increment_retry(self.state)
                return self.run()
            return

        self.state.current_stage = "review"
        result = self.run_stage(
            "review",
            {
                "issue_url": self.state.issue_url,
                "issue_data": self.state.issue_data,
                "exploration": self.state.explore_result.data
                if self.state.explore_result
                else None,
                "plan": self.state.architect_result.data
                if self.state.architect_result
                else None,
                "implementation": self.state.implement_result.data
                if self.state.implement_result
                else None,
            },
        )
        self.state.review_result = result

        if self.should_proceed("review", result):
            self.state.current_stage = "commit"
            self.run_stage(
                "commit",
                {
                    "issue_url": self.state.issue_url,
                    "issue_data": self.state.issue_data,
                    "exploration": self.state.explore_result.data
                    if self.state.explore_result
                    else None,
                    "plan": self.state.architect_result.data
                    if self.state.architect_result
                    else None,
                    "implementation": self.state.implement_result.data
                    if self.state.implement_result
                    else None,
                    "review_verdict": self.state.review_result.data
                    if self.state.review_result
                    else None,
                },
            )


class CLI:
    """CLI entry point."""

    @staticmethod
    def parse_args() -> argparse.Namespace:
        """Parse command line arguments."""
        parser = argparse.ArgumentParser(description="Code Pipeline")
        parser.add_argument("issue_url", help="GitHub issue URL", nargs="?")
        parser.add_argument("--repo-path", default="", help="Local repo path")
        parser.add_argument("--branch", default="", help="Branch name")
        parser.add_argument(
            "--from-scratch", action="store_true", help="Start from scratch"
        )
        parser.add_argument("--max-retries", type=int, default=3, help="Max retries")
        parser.add_argument("--dry-run", action="store_true", help="Dry run")
        parser.add_argument(
            "--programmatic", action="store_true", help="Programmatic mode"
        )
        parser.add_argument("--tactiq-meeting-id", default="", help="Tactiq meeting ID")
        parser.add_argument(
            "--verbose", "-v", action="store_true", help="Verbose logging"
        )
        parser.add_argument("--debug", action="store_true", help="Debug logging")
        return parser.parse_args()

    @staticmethod
    def configure_logging(level: int | str | None = None):
        """Configure logging."""
        if level is None:
            level = logging.INFO
        logging.basicConfig(
            level=level,
            format="%(asctime)s | %(levelname)-8s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    @classmethod
    def run(cls):
        """Run the CLI."""
        args = cls.parse_args()

        if not args.issue_url and not args.repo_path:
            raise ValueError("Either issue_url or --repo-path is required")

        if args.debug:
            log_level = logging.DEBUG
        elif args.verbose:
            log_level = logging.INFO
        else:
            log_level = None

        cls.configure_logging(log_level)

        from mycrew.llm import validate_required_models

        validate_required_models()

        from mycrew.pipeline_state import PipelineState

        state = PipelineState(
            id=str(uuid.uuid4()),
            issue_url=args.issue_url or "",
            branch=args.branch,
            max_retries=args.max_retries,
            dry_run=args.dry_run,
            programmatic=args.programmatic,
            tactiq_meeting_id=args.tactiq_meeting_id,
            repo_path=args.repo_path,
        )

        coordinator = FlowCoordinator(state)
        coordinator.run()
