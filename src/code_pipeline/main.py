#!/usr/bin/env python
"""Code Pipeline Flow: event-driven coding pipeline with implement
review retry loop and quality gates."""

import argparse
import os
import subprocess

from pydantic import BaseModel

from crewai.flow import Flow, listen, or_, router, start

from code_pipeline.crews.issue_analyst_crew.issue_analyst_crew import IssueAnalystCrew
from code_pipeline.crews.explorer_crew.explorer_crew import ExplorerCrew
from code_pipeline.crews.architect_crew.architect_crew import ArchitectCrew
from code_pipeline.crews.implementer_crew.implementer_crew import ImplementerCrew
from code_pipeline.crews.reviewer_crew.reviewer_crew import ReviewerCrew
from code_pipeline.crews.commit_crew.commit_crew import CommitCrew


class PipelineState(BaseModel):
    """State for the code pipeline flow."""

    repo_path: str = ""
    task: str = ""
    branch: str = "main"
    dry_run: bool = False
    max_retries: int = 3
    test_command: str = ""
    issue_id: str = ""
    issue_analysis: str = ""
    exploration: str = ""
    plan: str = ""
    implementation: str = ""
    review_verdict: str = ""
    retry_count: int = 0
    prior_issues: str = ""
    quality_gate_passed: bool = False
    quality_gate_output: str = ""
    verification_passed: bool = False
    verification_output: str = ""


class CodePipelineFlow(Flow[PipelineState]):
    """Event-driven coding pipeline: explore 1 plan 1 implement 1 review 1 commit."""

    def _run_quality_check(self, test_command: str) -> tuple[bool, str]:
        """Run test command in repo. Return (passed, output)."""
        if not test_command:
            return True, ""
        try:
            result = subprocess.run(
                test_command,
                shell=True,
                cwd=self.state.repo_path,
                capture_output=True,
                text=True,
                timeout=300,
            )
            output = (result.stdout or "") + (result.stderr or "")
            return result.returncode == 0, output
        except subprocess.TimeoutExpired:
            return False, "Error: command timed out after 300 seconds."
        except Exception as e:
            return False, str(e)

    @start()
    def analyze_issue(self):
        """Run IssueAnalystCrew to parse issue into structured requirements."""
        result = IssueAnalystCrew().crew().kickoff(inputs={"task": self.state.task})
        raw = result.raw if hasattr(result, "raw") else str(result)
        self.state.issue_analysis = raw
        return raw

    @listen(analyze_issue)
    def explore(self):
        """Run ExplorerCrew and set REPO_PATH for all crews."""
        repo_path = os.path.abspath(self.state.repo_path or os.getcwd())
        os.environ["REPO_PATH"] = repo_path
        self.state.repo_path = repo_path

        result = ExplorerCrew().crew().kickoff(
            inputs={
                "repo_path": repo_path,
                "issue_analysis": self.state.issue_analysis,
            }
        )
        raw = result.raw if hasattr(result, "raw") else str(result)
        self.state.exploration = raw
        return raw

    @listen(explore)
    def plan(self):
        """Run ArchitectCrew to produce file-level plan."""
        result = ArchitectCrew().crew().kickoff(
            inputs={
                "task": self.state.task,
                "exploration": self.state.exploration,
                "issue_analysis": self.state.issue_analysis,
            }
        )
        raw = result.raw if hasattr(result, "raw") else str(result)
        self.state.plan = raw
        return raw

    @listen(or_(plan, "retry"))
    def implement(self):
        """Run ImplementerCrew; fires on first run and on retries."""
        result = ImplementerCrew().crew().kickoff(
            inputs={
                "task": self.state.task,
                "plan": self.state.plan,
                "prior_issues": self.state.prior_issues,
                "repo_path": self.state.repo_path,
                "issue_analysis": self.state.issue_analysis,
            }
        )
        raw = result.raw if hasattr(result, "raw") else str(result)
        self.state.implementation = raw
        return raw

    @listen(implement)
    def quality_gate(self):
        """Run quality check (tests) if test_command is set."""
        passed, output = self._run_quality_check(self.state.test_command)
        self.state.quality_gate_passed = passed
        self.state.quality_gate_output = output
        return passed

    @router(quality_gate)
    def route_after_implement(self):
        """Route to review or retry based on quality gate."""
        if not self.state.test_command:
            return "review"
        if self.state.quality_gate_passed:
            return "review"

        self.state.retry_count += 1
        if self.state.retry_count >= self.state.max_retries:
            return "abort"

        self.state.prior_issues = (
            "Quality gate failed (tests/lint):\n\n" + self.state.quality_gate_output
        )
        return "retry"

    @listen("review")
    def review(self):
        """Run ReviewerCrew; sets review_verdict (APPROVED or ISSUES:...)."""
        result = ReviewerCrew().crew().kickoff(
            inputs={
                "task": self.state.task,
                "plan": self.state.plan,
                "implementation": self.state.implementation,
                "repo_path": self.state.repo_path,
                "issue_analysis": self.state.issue_analysis,
            }
        )
        raw = result.raw if hasattr(result, "raw") else str(result)
        self.state.review_verdict = raw
        return raw

    @router(review)
    def route_verdict(self):
        """Route based on verdict: commit, retry, or abort. Run verification when APPROVED."""
        verdict = self.state.review_verdict.strip()
        if verdict.upper().startswith("APPROVED"):
            if self.state.test_command:
                passed, output = self._run_quality_check(self.state.test_command)
                self.state.verification_passed = passed
                self.state.verification_output = output
                if not passed:
                    self.state.retry_count += 1
                    if self.state.retry_count >= self.state.max_retries:
                        return "abort"
                    self.state.prior_issues = (
                        "Tests failed after approval. Fix:\n\n" + output
                    )
                    return "retry"
            return "commit"

        self.state.retry_count += 1
        if self.state.retry_count >= self.state.max_retries:
            return "abort"

        self.state.prior_issues = (
            "IMPORTANT — A previous attempt was REJECTED. Fix ALL:\n\n" + verdict
        )
        return "retry"

    @listen("commit")
    def commit(self):
        """Run CommitCrew; skips actual commit if dry_run is true."""
        result = CommitCrew().crew().kickoff(
            inputs={
                "repo_path": self.state.repo_path,
                "branch": self.state.branch,
                "dry_run": "true" if self.state.dry_run else "false",
                "issue_id": self.state.issue_id,
            }
        )
        raw = result.raw if hasattr(result, "raw") else str(result)
        return raw

    @listen("abort")
    def abort(self):
        """Return message with retry count and last verdict."""
        msg = (
            f"Pipeline aborted after {self.state.retry_count} retries. "
            f"Last verdict:\n\n{self.state.review_verdict}"
        )
        return msg


def _parse_args():
    """Parse command-line arguments for the pipeline."""
    parser = argparse.ArgumentParser(
        description="Code pipeline: explore -> plan -> implement -> review -> commit"
    )
    parser.add_argument(
        "-r",
        "--repo-path",
        default=os.getcwd(),
        help="Repository path to work in (default: current directory)",
    )
    parser.add_argument(
        "-t",
        "--task",
        help="Task description for the pipeline",
    )
    parser.add_argument(
        "-b",
        "--branch",
        default="main",
        help="Git branch for commits (default: main)",
    )
    parser.add_argument(
        "-n",
        "--retries",
        type=int,
        default=3,
        help="Max implement->review retries (default: 3)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip actual git commit",
    )
    parser.add_argument(
        "--test-command",
        default="",
        help="Command to run for quality gate and verification (e.g. pytest, npm test)",
    )
    parser.add_argument(
        "--issue-id",
        default="",
        help="Issue ID for commit message (e.g. PROJ-123, fixes #42)",
    )
    return parser.parse_args()


def kickoff(
    repo_path: str | None = None,
    task: str | None = None,
    branch: str | None = None,
    max_retries: int | None = None,
    dry_run: bool | None = None,
    test_command: str | None = None,
    issue_id: str | None = None,
    inputs: dict | None = None,
):
    """Run the code pipeline flow. Uses argparse when invoked from CLI."""
    args = _parse_args()
    repo_path = os.path.abspath(repo_path if repo_path is not None else args.repo_path)
    task = task if task is not None else args.task
    branch = branch if branch is not None else args.branch
    max_retries = max_retries if max_retries is not None else args.retries
    dry_run = dry_run if dry_run is not None else args.dry_run
    test_command = (
        test_command if test_command is not None else getattr(args, "test_command", "")
    )
    issue_id = issue_id if issue_id is not None else getattr(args, "issue_id", "")

    if not task:
        raise ValueError("task is required (use --task / -t)")

    flow_inputs = inputs or {}
    flow_inputs.setdefault("repo_path", repo_path)
    flow_inputs.setdefault("task", task)
    flow_inputs.setdefault("branch", branch)
    flow_inputs.setdefault("dry_run", dry_run)
    flow_inputs.setdefault("max_retries", max_retries)
    flow_inputs.setdefault("test_command", test_command)
    flow_inputs.setdefault("issue_id", issue_id)

    flow = CodePipelineFlow()
    return flow.kickoff(inputs=flow_inputs)


def plot():
    """Plot the flow diagram."""
    flow = CodePipelineFlow()
    flow.plot("code_pipeline_flow")


def run_with_trigger():
    """Run the flow with trigger payload from command line."""
    import json
    import sys

    if len(sys.argv) < 2:
        raise ValueError("No trigger payload provided. Pass JSON as argument.")

    try:
        trigger_payload = json.loads(sys.argv[1])
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON payload: {e}") from e

    flow = CodePipelineFlow()
    return flow.kickoff({"crewai_trigger_payload": trigger_payload})


if __name__ == "__main__":
    args = _parse_args()
    kickoff(
        repo_path=args.repo_path,
        task=args.task,
        branch=args.branch,
        max_retries=args.retries,
        dry_run=args.dry_run,
        test_command=getattr(args, "test_command", ""),
        issue_id=getattr(args, "issue_id", ""),
    )
