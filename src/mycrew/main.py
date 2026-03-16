#!/usr/bin/env python
"""Simplified Code Pipeline Flow - Core pipeline logic only."""

import argparse
import logging
import os
import re
import subprocess
import tempfile
import uuid
from datetime import datetime
from pathlib import Path

from crewai.flow import Flow, listen, or_, start
from crewai.flow.persistence import SQLiteFlowPersistence, persist
from crewai.utilities.paths import db_storage_path
from pydantic import BaseModel

# Load settings before any CrewAI imports
from mycrew.llm import validate_required_models
from mycrew.pipeline_state import (
    PipelineStep,
    PipelineStateManager,
)
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
from mycrew.logging_utils import StepContext  # noqa: E402
from mycrew.crews.reviewer_crew.reviewer_crew import ReviewerCrew  # noqa: E402
from mycrew.crews.tactiq_research_crew.tactiq_research_crew import (
    TactiqResearchCrew,
)  # noqa: E402

logger = logging.getLogger("mycrew.main")


class PipelineState(BaseModel):
    """Minimal pipeline state."""

    id: str = ""  # Required for CrewAI Flow persistence
    issue_url: str = (
        ""  # Required for CLI, but needs default for CrewAI Flow initialization
    )
    branch: str = ""
    max_retries: int = 3
    dry_run: bool = False
    programmatic: bool = False
    repo_path: str = ""  # User-provided repo path (optional)
    repo_path_cloned: bool = False  # True if repo was cloned (for cleanup)

    # Core state fields
    repo_root: str | None = None  # Use string instead of Path for JSON serialization
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

    # Step-by-step execution
    target_steps: list[str] = []  # List of step names to execute
    input_file: str = ""  # Path to previous step results
    mock: bool = False  # Mock mode - return fake results


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

    def kickoff(self, inputs: dict | None = None, **kwargs):
        """Override kickoff to support step-by-step execution."""
        # Check if running in step-by-step mode
        if self._has_target_steps():
            logger.info(f"Running in step-by-step mode: {self.state.target_steps}")

            for step in self.state.target_steps:
                logger.info(f"=== Starting step: {step} ===")

                if not self._run_step(step):
                    logger.error(f"Step {step} failed")
                    return None

                logger.info(f"Step {step} completed successfully")

            logger.info("All steps completed successfully")
            return None

        # Default: run full pipeline
        return super().kickoff(inputs=inputs, **kwargs)

    def _get_field_from_state(self, field_name: str, default=None):
        """Get field from state with fallback."""
        return getattr(self.state, field_name, default)

    def _run_crew(self, crew_class, crew_name: str, input_data: dict | None = None):
        """Run a crew with simplified error handling.

        Uses the crew's build_inputs method to construct standard inputs from
        pipeline state, then merges with custom input_data.
        """
        if not crew_class:
            logger.info(f"Skipping {crew_name}: crew_class is None")
            return None

        # Set the pipeline context before running the crew so tools use correct repo_path
        from mycrew.settings import set_pipeline_context, PipelineContext

        github_repo = ""
        if self.state.issue_data and isinstance(self.state.issue_data, dict):
            github_repo = self.state.issue_data.get("github_repo", "")

        ctx = PipelineContext(
            repo_path=self.state.repo_root or self.state.repo_path,
            github_repo=github_repo,
            issue_url=self.state.issue_url,
            programmatic=self.state.programmatic,
        )

        # CRITICAL: Set context BEFORE creating crew instance
        # Tools are initialized when @crew decorator runs, so context must be set first
        set_pipeline_context(ctx)

        # Use StepContext for structured logging (SRP - logging separated from business logic)
        with StepContext(crew_name) as step:
            # Log inputs at DEBUG level
            try:
                crew_instance = crew_class()
                final_inputs = crew_instance.build_inputs(self.state, input_data)
                step.log_input(final_inputs)
            except Exception as e:
                logger.error(f"[{crew_name}] Failed to build inputs: {e}")
                return None

            # CrewBase decorated classes have a crew() method that returns the Crew
            try:
                crew = crew_instance.crew()
                result = crew.kickoff(inputs=final_inputs)

                # Log outputs at DEBUG level
                step.log_output(result.raw if result else None)

                return result.raw if result else None
            except Exception as e:
                import traceback

                logger.error(f"Failed {crew_name} crew: {e}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                return None
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

        self.state.repo_root = os.path.abspath(rp)
        logger.info(f"Using provided repo path: {self.state.repo_root}")

        if not url:
            github_repo = detect_github_repo(self.state.repo_root)
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
            self.state.repo_root = cloned_path
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

        # If tactiq_meeting_id is provided, run both tactiq_research and clarify in parallel
        # Otherwise just run clarify
        if self.state.tactiq_meeting_id:
            return or_(self.tactiq_research, self.clarify)

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
                if isinstance(self.state.issue_data, dict)
                else "",
                "issue_analysis": self.state.issue_data,
                "exploration": self.state.exploration_result,
                "tactiq_meeting_id": self.state.tactiq_meeting_id,
            },
        )

        if not result:
            logger.info("tactiq_research: failed")
            return None

        self.state.tactiq_result = result

        # Check if clarification is still needed based on result
        # If "sufficient_info: true" is in the result, skip clarification
        if isinstance(result, str) and "sufficient_info: true" in result.lower():
            logger.info("tactiq_research: sufficient info found")
            return "sufficient"

        logger.info("tactiq_research: clarification still needed")
        return None

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
                "exploration": self.state.exploration_result,
            },
        )

        if not result:
            logger.error("clarify: clarification failed")
            return self.end

        return "clarified"

    @listen(or_(tactiq_research, clarify))
    def architect(self):
        """Create architecture."""
        self.state.current_stage = "architect"

        clarifications_for_arch = ""
        prior_issues_for_arch = ""
        if self.state.issue_data is not None:
            if isinstance(self.state.issue_data, dict):
                clar_check = self.state.issue_data.get("clarifications")
                if clar_check is not None:
                    clarifications_for_arch = clar_check
                prior_check = self.state.issue_data.get("prior_issues")
                if prior_check is not None:
                    prior_issues_for_arch = prior_check

        result = self._run_crew(
            ArchitectCrew,
            "architect",
            {
                "issue_url": self.state.issue_url,
                "issue_data": self.state.issue_data,
                "exploration": self.state.exploration_result,
                "clarifications": clarifications_for_arch,
                "prior_issues": prior_issues_for_arch,
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

        clarifications = ""
        prior_issues = ""
        if self.state.issue_data and isinstance(self.state.issue_data, dict):
            clarifications = self.state.issue_data.get("clarifications", "")
            prior_issues = self.state.issue_data.get("prior_issues", "")

        result = self._run_crew(
            ImplementerCrew,
            "implement",
            {
                "issue_url": self.state.issue_url,
                "issue_data": self.state.issue_data,
                "exploration": self.state.exploration_result,
                "plan": self.state.architecture_result,
                "clarifications": clarifications,
                "prior_issues": prior_issues,
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

        clarifications_for_review = ""
        prior_issues_for_review = ""
        if self.state.issue_data is not None:
            if isinstance(self.state.issue_data, dict):
                clar_check = self.state.issue_data.get("clarifications")
                if clar_check is not None:
                    clarifications_for_review = clar_check
                prior_check = self.state.issue_data.get("prior_issues")
                if prior_check is not None:
                    prior_issues_for_review = prior_check

        result = self._run_crew(
            ReviewerCrew,
            "review",
            {
                "issue_url": self.state.issue_url,
                "issue_data": self.state.issue_data,
                "exploration": self.state.exploration_result,
                "plan": self.state.architecture_result,
                "implementation": self.state.implementation_result,
                "clarifications": clarifications_for_review,
                "prior_issues": prior_issues_for_review,
            },
        )

        if not result:
            logger.error("review: review failed")
            return self.retry_implement

        self.state.review_result = result

        # Check review verdict
        verdict = "ISSUES"
        if isinstance(result, dict):
            inner_verdict = result.get("verdict", {})
            if isinstance(inner_verdict, dict):
                verdict_result = inner_verdict.get("verdict")
                if verdict_result is not None:
                    verdict = verdict_result
            return
        result_upper = str(result).upper()
        if "APPROVED" in result_upper:
            verdict = "APPROVED"
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

        test_passed = False
        if isinstance(result, dict):
            passed_value = result.get("passed")
            if passed_value is not None:
                test_passed = passed_value
        if not isinstance(result, dict):
            result_upper = result.upper()
            if "PASS" in result_upper:
                test_passed = True
            if "OK" in result_upper:
                test_passed = True

        if test_passed:
            logger.info("validate_tests: tests passed")
            return self.commit
        logger.warning("validate_tests: tests failed")
        return self.retry_implement

    @listen(validate_tests)
    def commit(self):
        """Commit changes."""
        self.state.current_stage = "commit"

        branch_value = ""
        if hasattr(self.state, "branch"):
            branch_value = self.state.branch

        dry_run_value = False
        if hasattr(self.state, "dry_run"):
            dry_run_value = self.state.dry_run

        feature_branch_name = "feature/task"
        if isinstance(self.state.issue_data, dict):
            issue_number = self.state.issue_data.get("number")
            if issue_number is not None:
                feature_branch_name = "feature/" + issue_number

        issue_id_value = ""
        if isinstance(self.state.issue_data, dict):
            issue_id_value = self.state.issue_data.get("number", "")

        github_repo_value = ""
        if self.state.issue_data is not None:
            if isinstance(self.state.issue_data, dict):
                gh_check = self.state.issue_data.get("github_repo")
                if gh_check is not None:
                    github_repo_value = gh_check

        result = self._run_crew(
            CommitCrew,
            "commit",
            {
                "issue_url": self.state.issue_url,
                "issue_data": self.state.issue_data,
                "exploration": self.state.exploration_result,
                "plan": self.state.architecture_result,
                "implementation": self.state.implementation_result,
                "review_verdict": self.state.review_result,
                "validation_result": self.state.validation_result,
                "branch": branch_value,
                "dry_run": dry_run_value,
                "feature_branch": feature_branch_name,
                "issue_id": issue_id_value,
                "github_repo": github_repo_value,
            },
        )

        if not result:
            logger.error("commit: commit failed")
            return self.end

        self.state.commit_result = result

        if not dry_run_value and github_repo_value:
            self._validate_commit_result(result, feature_branch_name, github_repo_value)

        return self.end

    def _validate_commit_result(
        self, result: str, feature_branch: str, github_repo: str
    ) -> None:
        """Validate that commit and PR were actually created."""
        import re

        if not result:
            logger.error("commit validation: no result from commit crew")
            return

        result_lower = result.lower()

        if "skipped" in result_lower and (
            "dry_run" in result_lower or "no github_repo" in result_lower
        ):
            logger.info(
                "commit validation: PR creation was skipped (dry_run or no github_repo)"
            )
            return

        placeholder_patterns = [
            r"pull/123",
            r"pull/\d+",
            r"example\.com",
            r"owner/repo",
        ]

        for pattern in placeholder_patterns:
            if re.search(pattern, result, re.IGNORECASE):
                logger.error(
                    f"commit validation: FAILED - Found placeholder URL in result: {result[:200]}"
                )
                return

        pr_url_match = re.search(r"https://github\.com/[^/]+/[^/]+/pull/\d+", result)
        if not pr_url_match:
            logger.warning(
                f"commit validation: WARNING - No valid PR URL found in result. "
                f"Result: {result[:200]}"
            )
            return

        pr_url = pr_url_match.group(0)
        logger.info(f"commit validation: SUCCESS - PR created: {pr_url}")

        repo_path = self.state.repo_root or self.state.repo_path
        if repo_path and os.path.isdir(repo_path):
            try:
                import subprocess

                git_log = subprocess.run(
                    ["git", "log", "--oneline", "-3"],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if git_log.returncode == 0:
                    logger.info(
                        f"commit validation: Recent commits: {git_log.stdout[:200]}"
                    )
            except Exception as e:
                logger.warning(f"commit validation: Could not check git log: {e}")

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

    # ============ Step-by-Step Execution Methods ============

    def _has_target_steps(self) -> bool:
        """Check if running in step-by-step mode."""
        return bool(self.state.target_steps)

    def _is_step_in_targets(self, step: str) -> bool:
        """Check if step should run (None = run all, otherwise check list)."""
        if not self.state.target_steps:
            return True
        return step in self.state.target_steps

    def _load_step_input(self, step: str, from_step: str | None = None) -> dict | None:
        """Load input data for a step from file or auto-load from state."""
        # First check if input_file is provided
        if self.state.input_file:
            return PipelineStateManager.load_step_result(self.state.input_file)

        # Determine which step to load from
        load_from = from_step if from_step else step

        # Auto-load from state directory
        try:
            step_enum = PipelineStep(load_from)
        except ValueError:
            logger.error(f"Invalid step: {load_from}")
            return None

        result = PipelineStateManager.get_latest_result_for_step(step_enum)
        if result:
            logger.info(f"Auto-loaded input for {step} from {load_from} in state")
            return result.get("data")

        return None

    def _save_step_output(self, step: str, data: dict) -> None:
        """Save step output to state directory."""
        try:
            step_enum = PipelineStep(step)
        except ValueError:
            logger.error(f"Invalid step: {step}")
            return

        PipelineStateManager.save_step_result(step_enum, data)
        logger.info(f"Saved output for step: {step}")

    STEP_ORDER = [
        "EXPLORE",
        "ANALYZE",
        "ARCHITECT",
        "IMPLEMENT",
        "REVIEW",
        "VALIDATE_TESTS",
        "COMMIT",
    ]

    def _get_previous_step(self, step: str) -> str | None:
        """Get the step that comes before the current step."""
        try:
            idx = self.STEP_ORDER.index(step)
            if idx > 0:
                return self.STEP_ORDER[idx - 1]
        except ValueError:
            pass
        return None

    def _run_step(self, step: str) -> bool:
        """Run a single step with validation."""
        logger.info(f"=== Executing step: {step} ===")

        # Validate input for this step - load from previous step
        if step != "EXPLORE":
            prev_step = self._get_previous_step(step)
            input_data = self._load_step_input(step, from_step=prev_step)
            if not input_data:
                logger.error(
                    f"Step {step} requires output from {prev_step}. "
                    f"Provide --input-file or run previous step first."
                )
                return False

        # Map step names to methods
        step_methods = {
            "EXPLORE": self._run_step_explore,
            "ANALYZE": self._run_step_analyze,
            "ARCHITECT": self._run_step_architect,
            "IMPLEMENT": self._run_step_implement,
            "REVIEW": self._run_step_review,
            "VALIDATE_TESTS": self._run_step_validate_tests,
            "COMMIT": self._run_step_commit,
        }

        if step not in step_methods:
            logger.error(f"Unknown step: {step}")
            return False

        # Execute the step (or return mock data if mock mode)
        if self.state.mock:
            result = self._get_mock_result(step)
            logger.info(f"Mock mode: returning fake result for {step}")
        else:
            result = step_methods[step]()

        # Save output for next step
        if result:
            self._save_step_output(step, result)

        return result is not None

    def _get_mock_result(self, step: str) -> dict:
        """Return mock data for a step without calling LLM."""
        mock_data = {
            "EXPLORE": {
                "exploration_result": "Mock exploration: Tech Stack detected, Directory Layout mapped, Key Files identified, Conventions documented."
            },
            "ANALYZE": {
                "analyze_result": "Mock analysis: Issue #838 parsed into structured requirements. Xerxes Robots TXT - Conditional GET Support."
            },
            "ARCHITECT": {
                "architect_result": "Mock architect: Implementation plan created with Files to Create and Files to Modify sections."
            },
            "IMPLEMENT": {
                "implementation_result": "Mock implementation: Files modified in target repository. Changes ready for review."
            },
            "REVIEW": {
                "review_result": "Mock review: Code reviewed, feedback provided, approved for merge."
            },
            "VALIDATE_TESTS": {
                "validation_result": {
                    "passed": True,
                    "output": "Mock tests: All tests passed.",
                }
            },
            "COMMIT": {
                "commit_result": "Mock commit: Changes committed and PR created."
            },
        }
        return mock_data.get(step, {"result": f"Mock result for {step}"})

    def _run_step_explore(self) -> dict | None:
        """Execute EXPLORE step."""
        self.state.current_stage = "explore"
        url = self.state.issue_url.strip() if self.state.issue_url else ""
        rp = self.state.repo_path.strip() if self.state.repo_path else ""

        if not url and not rp:
            logger.error("EXPLORE step requires issue_url or repo_path")
            return None

        # Set up repo root and issue_data
        if rp:
            if not os.path.isdir(rp):
                logger.error(f"repo_path does not exist: {rp}")
                return None
            self.state.repo_root = os.path.abspath(rp)
            logger.info(f"Using provided repo path: {self.state.repo_root}")

            if not url:
                github_repo = detect_github_repo(self.state.repo_root)
                if not github_repo:
                    logger.error("Could not detect github_repo from local repo")
                    return None
                self.state.issue_data = {
                    "owner": github_repo.split("/")[0],
                    "repo": github_repo.split("/")[1],
                    "kind": "repo",
                    "number": "",
                    "is_pull": False,
                    "github_repo": github_repo,
                }

        # Run the exploration crew directly
        result = self._run_crew(
            ExplorerCrew,
            "explore",
            {"issue_url": url, "issue_data": self.state.issue_data},
        )

        if result:
            self.state.exploration_result = result
            return {"exploration_result": result}

        logger.error("EXPLORE step failed")
        return None

    def _run_step_analyze(self) -> dict | None:
        """Execute ANALYZE step."""
        if not self._is_step_in_targets("EXPLORE"):
            # Need exploration result from input
            input_data = self._load_step_input("EXPLORE")
            if input_data:
                self.state.exploration_result = input_data.get("exploration_result")

        self.state.current_stage = "analyze"
        result = self._run_crew(
            IssueAnalystCrew,
            "analyze_issue",
            {"issue_url": self.state.issue_url, "issue_data": self.state.issue_data},
        )
        if result:
            return {"analyze_result": result}
        return None

    def _run_step_architect(self) -> dict | None:
        """Execute ARCHITECT step."""
        self.state.current_stage = "architect"
        result = self._run_crew(
            ArchitectCrew,
            "architect",
            {"issue_url": self.state.issue_url, "issue_data": self.state.issue_data},
        )
        if result:
            return {"architect_result": result}
        return None

    def _run_step_implement(self) -> dict | None:
        """Execute IMPLEMENT step."""
        self.state.current_stage = "implement"
        result = self._run_crew(
            ImplementerCrew,
            "implement",
            {"issue_url": self.state.issue_url, "issue_data": self.state.issue_data},
        )
        if result:
            return {"implementation_result": result}
        return None

    def _run_step_review(self) -> dict | None:
        """Execute REVIEW step."""
        self.state.current_stage = "review"
        result = self._run_crew(
            ReviewerCrew,
            "review",
            {"issue_url": self.state.issue_url, "issue_data": self.state.issue_data},
        )
        if result:
            return {"review_result": result}
        return None

    def _run_step_validate_tests(self) -> dict | None:
        """Execute VALIDATE_TESTS step."""
        self.state.current_stage = "validate_tests"
        result = self.validate_tests()
        if result:
            return {"validation_result": result}
        return None

    def _run_step_commit(self) -> dict | None:
        """Execute COMMIT step."""
        self.state.current_stage = "commit"
        result = self._run_crew(
            CommitCrew,
            "commit",
            {"issue_url": self.state.issue_url, "issue_data": self.state.issue_data},
        )
        if result:
            return {"commit_result": result}
        return None


class PipelineRunner:
    """Pipeline runner - handles CLI entry point and orchestration."""

    @staticmethod
    def _configure_logging(level: int | str | None = None, log_file: str | None = None):
        """Configure logging to console and optional file."""
        if level is None:
            level = logging.INFO

        handlers: list[logging.Handler] = []

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        handlers.append(console_handler)

        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                )
            )
            handlers.append(file_handler)

        logging.basicConfig(
            level=level,
            format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            handlers=handlers,
        )

        for lib in ["LiteLLM", "litellm", "urllib3", "httpx", "openai", "crewai"]:
            logging.getLogger(lib).setLevel(logging.WARNING)

    @classmethod
    def kickoff(
        cls,
        issue_url: str,
        branch: str = "",
        from_scratch: bool = False,
        max_retries: int = 3,
        dry_run: bool = False,
        programmatic: bool = False,
        tactiq_meeting_id: str = "",
        repo_path: str = "",
        target_steps: str = "",
        input_file: str = "",
        mock: bool = False,
    ):
        """Kickoff the pipeline."""
        if not mock:
            validate_required_models()

        # Parse target steps
        steps_list: list[str] = []
        if target_steps:
            valid_step_values = {s.value for s in PipelineStep}
            for s in target_steps.split(","):
                step = s.strip()
                if step not in valid_step_values:
                    logger.error(f"Invalid step: {step}")
                    logger.error(f"Valid steps: {list(valid_step_values)}")
                    return
                steps_list.append(step)

        state = PipelineState(
            id=str(uuid.uuid4()),
            issue_url=issue_url,
            branch=branch,
            max_retries=max_retries,
            dry_run=dry_run,
            programmatic=programmatic,
            tactiq_meeting_id=tactiq_meeting_id,
            repo_path=repo_path,
            target_steps=steps_list,
            input_file=input_file,
            mock=mock,
        )
        flow = CodePipelineFlow(state=state)
        flow._state = state
        flow.kickoff()

    @classmethod
    def main(cls):
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
        parser.add_argument(
            "--programmatic", action="store_true", help="Programmatic mode"
        )
        parser.add_argument(
            "--tactiq-meeting-id", default="", help="Tactiq meeting ID for context"
        )
        parser.add_argument(
            "--verbose", "-v", action="store_true", help="Verbose logging"
        )
        parser.add_argument("--debug", action="store_true", help="Debug logging")
        parser.add_argument(
            "--steps",
            default="",
            help="Comma-separated steps: EXPLORE,ANALYZE,ARCHITECT,IMPLEMENT,REVIEW,VALIDATE_TESTS,COMMIT",
        )
        parser.add_argument(
            "--input-file",
            default="",
            help="Path to previous step results (JSON). If empty, auto-loads from ~/.mycrew/state/",
        )
        parser.add_argument(
            "--mock",
            action="store_true",
            help="Mock mode - return fake results without calling LLM",
        )

        args = parser.parse_args()

        if not args.issue_url and not args.repo_path and not args.steps:
            parser.error("Either issue_url, --repo-path, or --steps is required")

        if args.debug:
            log_level = logging.DEBUG
        elif args.verbose:
            log_level = logging.INFO
        else:
            log_level = None

        log_dir = os.path.join(os.path.expanduser("~"), ".mycrew", "logs")
        os.makedirs(log_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(log_dir, f"pipeline_{timestamp}.log")

        cls._configure_logging(level=log_level, log_file=log_file)

        logger.info(f"Logging to file: {log_file}")

        cls.kickoff(
            issue_url=args.issue_url or "",
            repo_path=args.repo_path,
            branch=args.branch,
            from_scratch=args.from_scratch,
            max_retries=args.max_retries,
            dry_run=args.dry_run,
            programmatic=args.programmatic,
            tactiq_meeting_id=args.tactiq_meeting_id,
            target_steps=args.steps,
            input_file=args.input_file,
            mock=args.mock,
        )


def _main():
    """Entry point for CLI."""
    PipelineRunner.main()


def kickoff(issue_url: str, **kwargs):
    """Programmatic entry point."""
    PipelineRunner.kickoff(issue_url=issue_url, **kwargs)


def run_with_trigger(issue_url: str, trigger_type: str, **kwargs):
    """Entry point for webhook triggers."""
    PipelineRunner.kickoff(issue_url=issue_url, **kwargs)


def plot():
    """Entry point for plotting."""
    pass


if __name__ == "__main__":
    PipelineRunner.main()
