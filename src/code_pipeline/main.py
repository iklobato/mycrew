#!/usr/bin/env python
"""Code Pipeline Flow: event-driven coding pipeline with implement
review retry loop and quality gates."""

import argparse
import json
import logging
import os
import re
import subprocess
import sys
import time
from dataclasses import asdict, dataclass

from pydantic import BaseModel

from crewai.flow import Flow, listen, or_, router, start

# Apply Anthropic message-format monkey-patch before any crew/LLM usage
import code_pipeline.llm  # noqa: F401

from code_pipeline.crews.architect_crew.architect_crew import ArchitectCrew
from code_pipeline.crews.commit_crew.commit_crew import CommitCrew
from code_pipeline.crews.explorer_crew.explorer_crew import ExplorerCrew
from code_pipeline.crews.implementer_crew.implementer_crew import ImplementerCrew
from code_pipeline.crews.issue_analyst_crew.issue_analyst_crew import IssueAnalystCrew
from code_pipeline.crews.reviewer_crew.reviewer_crew import ReviewerCrew

logger = logging.getLogger(__name__)

# Retry config for rate limits (429) and empty LLM responses
RATE_LIMIT_MAX_RETRIES = 5
RATE_LIMIT_BASE_DELAY = 8
RATE_LIMIT_BACKOFF_FACTOR = 2
EMPTY_RESPONSE_MAX_RETRIES = 5
EMPTY_RESPONSE_DELAY = 8


def _is_retryable_error(e: Exception) -> bool:
    """True if the error is transient and worth retrying."""

    def _err_matches(exc: BaseException) -> bool:
        s = str(exc)
        if "RateLimitError" in type(exc).__name__ or "429" in s:
            return True
        if "None or empty" in s or "Invalid response from LLM" in s:
            return True
        return False

    # Check this exception and its cause chain (wrapped exceptions)
    current = e
    while current is not None:
        if _err_matches(current):
            return True
        current = getattr(current, "__cause__", None) or getattr(
            current, "__context__", None
        )
    return False


def _fallback_exploration(repo_path: str, issue_analysis: str) -> str:
    """Minimal exploration using shell commands when ExplorerCrew crashes (e.g. segfault on macOS)."""
    try:
        result = subprocess.run(
            "find . -maxdepth 3 -type f -name '*.py' -o -name '*.ts' -o -name '*.tsx' -o -name '*.json' -o -name '*.toml' -o -name '*.yaml' 2>/dev/null | head -80",
            shell=True,
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=30,
        )
        files = (result.stdout or "").strip() or "(none found)"
        result2 = subprocess.run(
            "ls -la 2>/dev/null",
            shell=True,
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=5,
        )
        root_list = (result2.stdout or "").strip() or "(empty)"
        return f"""## Tech Stack
(Inferred from fallback exploration - ExplorerCrew unavailable)

## Directory Layout
```
{root_list}
```

## Key Files
```
{files}
```

## Conventions
(Use issue context to focus: {issue_analysis[:200]}...)
"""
    except Exception as e:
        return f"Fallback exploration failed: {e}. Issue context: {issue_analysis[:300]}"


def _run_explore_with_fallback(
    repo_path: str, issue_analysis: str, state_attr: str
) -> str:
    """Run ExplorerCrew in subprocess; on crash (139) or timeout, use fallback exploration."""
    import tempfile

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False
    ) as f_in:
        json.dump(
            {"repo_path": repo_path, "issue_analysis": issue_analysis},
            f_in,
        )
        inputs_path = f_in.name
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False
    ) as f_out:
        output_path = f_out.name

    try:
        env = os.environ.copy()
        env["REPO_PATH"] = repo_path
        proc = subprocess.run(
            [
                sys.executable,
                "-c",
                """
import json
import os
import sys
os.environ["REPO_PATH"] = sys.argv[1]
with open(sys.argv[2]) as f:
    inputs = json.load(f)
with open(sys.argv[3], "w") as out:
    try:
        from code_pipeline.crews.explorer_crew.explorer_crew import ExplorerCrew
        result = ExplorerCrew().crew().kickoff(inputs=inputs)
        raw = result.raw if hasattr(result, "raw") else str(result)
        out.write(raw)
    except Exception as e:
        out.write(f"Error: {e}")
""",
                repo_path,
                inputs_path,
                output_path,
            ],
            env=env,
            timeout=300,
            capture_output=True,
            cwd=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        )
        if proc.returncode == 0 and os.path.exists(output_path):
            with open(output_path) as f:
                return f.read()
    except subprocess.TimeoutExpired:
        logger.warning("ExplorerCrew timed out, using fallback exploration")
    except Exception as e:
        logger.warning("ExplorerCrew failed (%s), using fallback exploration", e)
    finally:
        for p in (inputs_path, output_path):
            try:
                os.unlink(p)
            except OSError:
                pass

    return _fallback_exploration(repo_path, issue_analysis)


def _kickoff_with_retry(crew, inputs: dict):
    """Run crew.kickoff with exponential backoff on rate limits and empty LLM responses."""
    max_retries = max(RATE_LIMIT_MAX_RETRIES, EMPTY_RESPONSE_MAX_RETRIES)
    last_error = None
    for attempt in range(max_retries):
        try:
            return crew.kickoff(inputs=inputs)
        except Exception as e:
            last_error = e
            if _is_retryable_error(e) and attempt < max_retries - 1:
                if "429" in str(e) or "RateLimitError" in type(e).__name__:
                    delay = RATE_LIMIT_BASE_DELAY * (RATE_LIMIT_BACKOFF_FACTOR**attempt)
                    logger.warning(
                        "Rate limit hit (attempt %d/%d), sleeping %.0fs before retry",
                        attempt + 1,
                        max_retries,
                        delay,
                    )
                else:
                    delay = EMPTY_RESPONSE_DELAY
                    logger.warning(
                        "Empty/invalid LLM response (attempt %d/%d), sleeping %.0fs before retry: %s",
                        attempt + 1,
                        max_retries,
                        delay,
                        str(e)[:80],
                    )
                time.sleep(delay)
            else:
                raise
    if last_error is not None:
        raise last_error
    raise RuntimeError("Retry loop exited without capturing exception")


def _fallback_exploration(repo_path: str, issue_analysis: str) -> str:
    """Minimal repo exploration via shell when ExplorerCrew crashes (e.g. segfault on macOS)."""
    try:
        result = subprocess.run(
            "find . -maxdepth 3 -type f -name '*.py' -o -name '*.ts' -o -name '*.tsx' -o -name '*.js' -o -name '*.json' -o -name 'pyproject.toml' -o -name 'package.json' 2>/dev/null | head -80",
            shell=True,
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=30,
        )
        files = (result.stdout or "").strip() or "(none found)"
        result2 = subprocess.run(
            "ls -la 2>/dev/null; echo '---'; head -50 pyproject.toml package.json 2>/dev/null || true",
            shell=True,
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=10,
        )
        layout = (result2.stdout or "").strip() or "(unable to read)"
        return f"""## Tech Stack
(Inferred from fallback exploration - ExplorerCrew unavailable)

## Directory Layout
```
{layout[:4000]}
```

## Key Files
```
{files}
```

## Conventions
(Use issue context and file structure above for planning.)

Issue context: {issue_analysis[:500]}
"""
    except Exception as e:
        return f"Fallback exploration failed: {e}\n\nIssue context: {issue_analysis[:500]}"


def _run_explore_with_fallback(
    repo_path: str, issue_analysis: str, state_attr: str
) -> str:
    """Run ExplorerCrew in subprocess; on crash (exit 139) or timeout, use fallback."""
    import tempfile

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False
    ) as f_in:
        json.dump(
            {"repo_path": repo_path, "issue_analysis": issue_analysis},
            f_in,
        )
        input_path = f_in.name
    output_path = input_path.replace(".json", "_out.txt")
    try:
        env = os.environ.copy()
        env["REPO_PATH"] = repo_path
        env["CODE_PIPELINE_EXPLORE_INPUT"] = input_path
        env["CODE_PIPELINE_EXPLORE_OUTPUT"] = output_path
        script = """
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from code_pipeline.crews.explorer_crew.explorer_crew import ExplorerCrew
with open(os.environ["CODE_PIPELINE_EXPLORE_INPUT"]) as f:
    inp = json.load(f)
os.environ["REPO_PATH"] = inp["repo_path"]
result = ExplorerCrew().crew().kickoff(inputs=inp)
raw = result.raw if hasattr(result, "raw") else str(result)
with open(os.environ["CODE_PIPELINE_EXPLORE_OUTPUT"], "w") as f:
    f.write(raw)
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False
        ) as f_script:
            f_script.write(script)
            script_path = f_script.name
        try:
            proc = subprocess.run(
                [sys.executable, script_path],
                env=env,
                capture_output=True,
                timeout=300,
                cwd=os.path.dirname(os.path.dirname(__file__)),
            )
            if proc.returncode == 0 and os.path.exists(output_path):
                with open(output_path) as f:
                    return f.read()
        finally:
            if os.path.exists(script_path):
                os.unlink(script_path)
    except (subprocess.TimeoutExpired, Exception) as e:
        logger.warning("ExplorerCrew subprocess failed (%s), using fallback", e)
    finally:
        for p in (input_path, output_path):
            if os.path.exists(p):
                try:
                    os.unlink(p)
                except OSError:
                    pass
    return _fallback_exploration(repo_path, issue_analysis)


@dataclass
class PipelineArgs:
    """Single source of truth for pipeline arguments from CLI or programmatic call."""

    repo_path: str = ""
    task: str = ""
    branch: str = "main"
    max_retries: int = 3
    dry_run: bool = False
    test_command: str = ""
    issue_id: str = ""
    github_repo: str = ""
    issue_url: str = ""
    docs_url: str = ""

    def to_flow_inputs(self) -> dict:
        """Convert to flow inputs dict with repo_path normalized."""
        return {
            "repo_path": os.path.abspath(self.repo_path or os.getcwd()),
            "task": self.task,
            "branch": self.branch,
            "dry_run": self.dry_run,
            "max_retries": self.max_retries,
            "test_command": self.test_command,
            "issue_id": self.issue_id,
            "github_repo": self.github_repo,
            "issue_url": self.issue_url,
            "docs_url": self.docs_url,
        }

    def replace(self, **overrides) -> "PipelineArgs":
        """Return new PipelineArgs with overrides applied (None values ignored)."""
        d = asdict(self)
        for k, v in overrides.items():
            if v is not None and k in d:
                d[k] = v
        return PipelineArgs(**d)


def _parse_args() -> PipelineArgs:
    """Parse command-line arguments into PipelineArgs."""
    parser = argparse.ArgumentParser(
        description="Code pipeline: explore -> plan -> implement -> review -> commit"
    )
    parser.add_argument(
        "-r", "--repo-path", default=os.getcwd(), help="Repository path"
    )
    parser.add_argument("-t", "--task", help="Task description (required)")
    parser.add_argument("-b", "--branch", default="main", help="Git branch")
    parser.add_argument("-n", "--retries", type=int, default=3, help="Max retries")
    parser.add_argument("--dry-run", action="store_true", help="Skip git commit")
    parser.add_argument("--test-command", default="", help="Test command (e.g. pytest)")
    parser.add_argument("--issue-id", default="", help="Issue ID for commit")
    parser.add_argument(
        "--github-repo", default="", help="GitHub repo for GithubSearchTool"
    )
    parser.add_argument(
        "--issue-url", default="", help="Issue URL for ScrapeWebsiteTool"
    )
    parser.add_argument(
        "--docs-url", default="", help="Docs URL for CodeDocsSearchTool"
    )
    ns = parser.parse_args()
    return PipelineArgs(
        repo_path=ns.repo_path,
        task=ns.task or "",
        branch=ns.branch,
        max_retries=ns.retries,
        dry_run=ns.dry_run,
        test_command=ns.test_command,
        issue_id=ns.issue_id,
        github_repo=ns.github_repo,
        issue_url=ns.issue_url,
        docs_url=ns.docs_url,
    )


class PipelineState(BaseModel):
    """State for the code pipeline flow."""

    repo_path: str = ""
    task: str = ""
    branch: str = "main"
    dry_run: bool = False
    max_retries: int = 3
    test_command: str = ""
    issue_id: str = ""
    github_repo: str = ""
    issue_url: str = ""
    docs_url: str = ""
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

    def _run_crew(self, crew_class, inputs: dict, state_attr: str | None = None):
        """Run a crew and optionally store result in state. Returns raw output."""
        result = _kickoff_with_retry(crew_class().crew(), inputs)
        raw = result.raw if hasattr(result, "raw") else str(result)
        if state_attr:
            setattr(self.state, state_attr, raw)
        return raw

    def _retry_or_abort(self, prior_issues_prefix: str, output: str) -> str:
        """Increment retry count; return 'pipeline_aborted' or 'retry'."""
        self.state.retry_count += 1
        if self.state.retry_count >= self.state.max_retries:
            return "pipeline_aborted"
        self.state.prior_issues = prior_issues_prefix + output
        return "retry"

    @start()
    def analyze_issue(self):
        """Run IssueAnalystCrew to parse issue into structured requirements."""
        os.environ["GITHUB_REPO"] = self.state.github_repo or ""
        os.environ["ISSUE_URL"] = self.state.issue_url or ""
        os.environ["DOCS_URL"] = self.state.docs_url or ""
        return self._run_crew(
            IssueAnalystCrew,
            {
                "task": self.state.task,
                "issue_url": self.state.issue_url,
                "github_repo": self.state.github_repo,
            },
            "issue_analysis",
        )

    @listen(analyze_issue)
    def explore(self):
        """Run ExplorerCrew and set REPO_PATH for all crews. Uses subprocess+fallback to avoid segfault killing the pipeline."""
        repo_path = os.path.abspath(self.state.repo_path or os.getcwd())
        os.environ["REPO_PATH"] = repo_path
        self.state.repo_path = repo_path
        raw = _run_explore_with_fallback(
            repo_path, self.state.issue_analysis, "exploration"
        )
        self.state.exploration = raw
        return raw

    @listen(explore)
    def plan(self):
        """Run ArchitectCrew to produce file-level plan."""
        return self._run_crew(
            ArchitectCrew,
            {
                "task": self.state.task,
                "exploration": self.state.exploration,
                "issue_analysis": self.state.issue_analysis,
                "github_repo": self.state.github_repo,
                "docs_url": self.state.docs_url,
            },
            "plan",
        )

    @listen(or_(plan, "retry"))
    def implement(self):
        """Run ImplementerCrew; fires on first run and on retries."""
        return self._run_crew(
            ImplementerCrew,
            {
                "task": self.state.task,
                "plan": self.state.plan,
                "prior_issues": self.state.prior_issues,
                "repo_path": self.state.repo_path,
                "issue_analysis": self.state.issue_analysis,
            },
            "implementation",
        )

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
        return self._retry_or_abort(
            "Quality gate failed (tests/lint):\n\n",
            self.state.quality_gate_output,
        )

    @listen("review")
    def review(self):
        """Run ReviewerCrew; sets review_verdict (APPROVED or ISSUES:...)."""
        return self._run_crew(
            ReviewerCrew,
            {
                "task": self.state.task,
                "plan": self.state.plan,
                "implementation": self.state.implementation,
                "repo_path": self.state.repo_path,
                "issue_analysis": self.state.issue_analysis,
                "docs_url": self.state.docs_url,
            },
            "review_verdict",
        )

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
                    return self._retry_or_abort(
                        "Tests failed after approval. Fix:\n\n", output
                    )
            return "commit"
        return self._retry_or_abort(
            "IMPORTANT — A previous attempt was REJECTED. Fix ALL:\n\n", verdict
        )

    def _make_feature_branch_name(self) -> str:
        """Generate a feature branch name from task and issue_id."""
        slug = re.sub(r"[^a-z0-9]+", "-", self.state.task.lower()).strip("-")[:50]
        if not slug:
            slug = "changes"
        if self.state.issue_id:
            issue_slug = re.sub(r"[^a-zA-Z0-9-]", "", self.state.issue_id)
            return f"feature/{issue_slug}-{slug}"
        return f"feature/{slug}"

    @listen("commit")
    def commit(self):
        """Run CommitCrew; creates feature branch and commits. Skips if dry_run."""
        feature_branch = self._make_feature_branch_name()
        return self._run_crew(
            CommitCrew,
            {
                "repo_path": self.state.repo_path,
                "branch": self.state.branch,
                "feature_branch": feature_branch,
                "dry_run": "true" if self.state.dry_run else "false",
                "issue_id": self.state.issue_id,
            },
            state_attr=None,
        )

    @listen("pipeline_aborted")
    def handle_abort(self):
        """Terminal: return message with retry count and last verdict. Uses distinct
        event name to avoid loop (completing 'abort' would re-emit and retrigger)."""
        msg = (
            f"Pipeline aborted after {self.state.retry_count} retries. "
            f"Last verdict:\n\n{self.state.review_verdict}"
        )
        return msg


def kickoff(
    repo_path: str | None = None,
    task: str | None = None,
    branch: str | None = None,
    max_retries: int | None = None,
    dry_run: bool | None = None,
    test_command: str | None = None,
    issue_id: str | None = None,
    github_repo: str | None = None,
    issue_url: str | None = None,
    docs_url: str | None = None,
    inputs: dict | None = None,
):
    """Run the code pipeline flow. Uses argparse when invoked from CLI."""
    overrides = {
        "repo_path": repo_path,
        "task": task,
        "branch": branch,
        "max_retries": max_retries,
        "dry_run": dry_run,
        "test_command": test_command,
        "issue_id": issue_id,
        "github_repo": github_repo,
        "issue_url": issue_url,
        "docs_url": docs_url,
    }
    args = _parse_args().replace(**overrides)
    flow_inputs = (inputs or {}) | args.to_flow_inputs()
    if not flow_inputs.get("task"):
        raise ValueError("task is required (use --task / -t)")
    return CodePipelineFlow().kickoff(inputs=flow_inputs)


def plot():
    """Plot the flow diagram."""
    flow = CodePipelineFlow()
    flow.plot("code_pipeline_flow")


def run_with_trigger():
    """Run the flow with trigger payload from command line."""
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
        max_retries=args.max_retries,
        dry_run=args.dry_run,
        test_command=getattr(args, "test_command", ""),
        issue_id=getattr(args, "issue_id", ""),
        github_repo=getattr(args, "github_repo", ""),
        issue_url=getattr(args, "issue_url", ""),
        docs_url=getattr(args, "docs_url", ""),
    )
