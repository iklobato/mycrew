#!/usr/bin/env python
"""Code Pipeline Flow: event-driven coding pipeline with implement
review retry loop and quality gates."""

import argparse
import hashlib
import json
import logging
import os
from datetime import datetime, timezone

import yaml
import re
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from pydantic import BaseModel

from crewai.flow import Flow, listen, or_, router, start
from crewai.flow.human_feedback import HumanFeedbackResult, human_feedback
from crewai.flow.persistence import SQLiteFlowPersistence, persist
from crewai.utilities.paths import db_storage_path

# Suppress CrewAI event pairing mismatch warnings (Flow + Crew + tracing can reorder
# scope events; see crewai.events.event_context)
from crewai.events.event_context import (
    EventContextConfig,
    MismatchBehavior,
    _event_context_config,
)

_event_context_config.set(
    EventContextConfig(
        mismatch_behavior=MismatchBehavior.SILENT,
        empty_pop_behavior=MismatchBehavior.SILENT,
    )
)

# Apply Anthropic message-format monkey-patch before any crew/LLM usage
import code_pipeline.llm  # noqa: F401
from code_pipeline.llm import get_llm_for_stage

from code_pipeline.crews.architect_crew.architect_crew import ArchitectCrew
from code_pipeline.crews.clarify_crew.clarify_crew import ClarifyCrew
from code_pipeline.crews.commit_crew.commit_crew import CommitCrew
from code_pipeline.crews.explorer_crew.explorer_crew import ExplorerCrew
from code_pipeline.crews.implementer_crew.implementer_crew import ImplementerCrew
from code_pipeline.crews.issue_analyst_crew.issue_analyst_crew import IssueAnalystCrew
from code_pipeline.crews.reviewer_crew.reviewer_crew import ReviewerCrew, ReviewVerdict
from code_pipeline.utils import build_repo_context, enrich_repo_context, log_exceptions

logger = logging.getLogger(__name__)

# Set by handle_abort when pipeline aborts after max retries; checked by _execute_flow
_pipeline_aborted = False


def _task_hash(task: str) -> str:
    """Stable hash for checkpoint key."""
    return hashlib.sha256((task or "").encode()).hexdigest()[:16]


def _get_checkpoint_path(repo_path: str) -> Path:
    """Path to checkpoint registry in repo."""
    return Path(repo_path) / ".code_pipeline" / "checkpoint.json"


def _load_checkpoint(repo_path: str, task: str) -> str | None:
    """Load flow_id for (repo_path, task). Returns None if not found."""
    path = _get_checkpoint_path(repo_path)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        key = f"{os.path.abspath(repo_path)}|{_task_hash(task)}"
        entry = data.get(key)
        if entry and isinstance(entry, dict):
            return entry.get("flow_id")
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Checkpoint load failed: %s", e)
    return None


def _save_checkpoint(repo_path: str, task: str, flow_id: str) -> None:
    """Save flow_id for (repo_path, task)."""
    path = _get_checkpoint_path(repo_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    key = f"{os.path.abspath(repo_path)}|{_task_hash(task)}"
    data = {}
    if path.exists():
        try:
            data = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    data[key] = {
        "flow_id": flow_id,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    path.write_text(json.dumps(data, indent=2))


# Retry config for rate limits (429) and empty LLM responses
RATE_LIMIT_MAX_RETRIES = 5
RATE_LIMIT_BASE_DELAY = 8
RATE_LIMIT_BACKOFF_FACTOR = 2
EMPTY_RESPONSE_MAX_RETRIES = 5
EMPTY_RESPONSE_DELAY = 8


def _configure_logging(level: str | int | None = None) -> None:
    """Configure logger for code_pipeline. Call early in kickoff."""
    log = logging.getLogger("code_pipeline")
    if log.handlers:
        return
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(
        logging.Formatter("%(asctime)s │ %(levelname)-7s │ %(message)s")
    )
    log.addHandler(handler)
    log.propagate = False
    if level is not None:
        log.setLevel(level)
    else:
        env_level = os.environ.get("CODE_PIPELINE_LOG_LEVEL", "INFO").upper()
        log.setLevel(getattr(logging, env_level, logging.INFO))


def _log_section(title: str, body: str, char: str = "─") -> None:
    """Log a section with a visual separator."""
    width = 60
    logger.info("%s %s %s", char * 2, title, char * (width - len(title) - 4))
    for line in body.strip().split("\n"):
        logger.info("  %s", line)
    logger.info(char * width)


def _log_crew_context(crew_name: str, inputs: dict, exclude_keys: tuple = ()) -> None:
    """Log a brief summary of the context a crew is considering."""
    exclude = set(exclude_keys) | {
        "plan",
        "implementation",
        "exploration",
        "issue_analysis",
        "clarifications",
    }
    parts = []
    for k, v in sorted(inputs.items()):
        if k in exclude or v is None:
            continue
        s = str(v).strip()
        if not s:
            continue
        if len(s) > 120:
            s = s[:117] + "..."
        parts.append(f"  {k}: {s}")
    if parts:
        logger.info("%s context:", crew_name)
        for p in parts:
            logger.info("%s", p)


def _log_reviewer_verdict(verdict: str) -> None:
    """Log reviewer verdict in a human-readable format."""
    v = (verdict or "").strip()
    if not v:
        logger.info("Review: (empty verdict)")
        return
    if v.upper().startswith("APPROVED"):
        rest = v[7:].strip()
        logger.info("Review: APPROVED")
        if rest:
            for line in rest.split("\n")[:5]:
                line = line.strip()
                if line:
                    logger.info("  %s", line)
    elif "ISSUES:" in v.upper():
        logger.info("Review: REJECTED (issues found)")
        lines = v.split("\n")
        for line in lines[1:12]:  # First 12 issue lines
            line = line.strip()
            if line and (line.startswith("-") or line.startswith("•")):
                logger.info("  %s", line)
            elif line and not line.upper().startswith("APPROVED"):
                logger.info("  %s", line)
        if len(lines) > 13:
            logger.info("  ... (%d more lines)", len(lines) - 13)
    else:
        logger.info("Review: %s", v[:200])


def _log_implementer_summary(implementation: str) -> None:
    """Log a brief summary of what the implementer changed."""
    impl = (implementation or "").strip()
    if not impl:
        logger.info("Implementer: (no summary)")
        return
    # Extract "Wrote path" patterns or bullet points
    lines = impl.split("\n")
    wrote = [
        l.strip()
        for l in lines
        if "wrote" in l.lower() or "wrote:" in l.lower() or l.strip().startswith("- ")
    ]
    if wrote:
        logger.info("Implementer changes:")
        for line in wrote[:15]:
            if line:
                logger.info("  %s", line[:100])
        if len(wrote) > 15:
            logger.info("  ... (%d more)", len(wrote) - 15)
    else:
        # Fallback: first few lines
        preview = "\n  ".join(l.strip() for l in lines[:8] if l.strip())
        if preview:
            logger.info(
                "Implementer summary:\n  %s",
                preview[:400] + ("..." if len(preview) > 400 else ""),
            )


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
    """Minimal exploration using os.walk when ExplorerCrew fails. No subprocess."""
    logger.info("Using fallback exploration (ExplorerCrew unavailable)")
    try:
        patterns = ("*.py", "*.ts", "*.tsx", "*.json", "*.toml", "*.yaml")
        files_list = []
        for root, _dirs, fnames in os.walk(repo_path, topdown=True):
            rel_root = os.path.relpath(root, repo_path)
            if rel_root.startswith(".") and rel_root != ".":
                depth = rel_root.count(os.sep) + 1
                if depth > 3:
                    continue
            for f in fnames:
                for ext in patterns:
                    if f.endswith(ext.replace("*", "")):
                        files_list.append(os.path.join(rel_root, f))
                        break
            if len(files_list) >= 80:
                break
        files = "\n".join(files_list[:80]) if files_list else "(none found)"
        entries = []
        try:
            for e in sorted(os.listdir(repo_path))[:30]:
                st = os.stat(os.path.join(repo_path, e))
                entries.append(
                    f"{'d' if os.path.isdir(os.path.join(repo_path, e)) else '-'} {e}"
                )
        except OSError as e:
            logger.error(
                "Fallback exploration: failed to list directory %s: %s",
                repo_path,
                e,
                exc_info=True,
            )
            entries = ["(unable to list)"]
        layout = "\n".join(entries)
        return f"""## Tech Stack
(Inferred from fallback exploration - ExplorerCrew unavailable)

## Directory Layout
```
{layout}
```

## Key Files
```
{files}
```

## Conventions
(Use issue context to focus: {issue_analysis[:200]}...)
"""
    except Exception as e:
        logger.error("Fallback exploration failed: %s", e, exc_info=True)
        return (
            f"Fallback exploration failed: {e}. Issue context: {issue_analysis[:300]}"
        )


def _run_explore_in_process(
    repo_path: str,
    issue_analysis: str,
    *,
    task: str = "",
    test_command: str = "",
    focus_paths: str = "",
    exclude_paths: str = "",
    github_repo: str = "",
    repo_context: str = "",
) -> str:
    """Run ExplorerCrew in-process. On exception, use fallback exploration."""
    try:
        crew = ExplorerCrew().crew()
        inputs = {
            "repo_path": repo_path,
            "task": task,
            "issue_analysis": issue_analysis,
            "test_command": test_command,
            "focus_paths": focus_paths,
            "exclude_paths": exclude_paths,
            "github_repo": github_repo,
            "repo_context": repo_context
            or build_repo_context(repo_path, github_repo, "", "", test_command),
        }
        result = _kickoff_with_retry(
            crew,
            inputs,
            crew_name="ExplorerCrew",
        )
        raw = result.raw if hasattr(result, "raw") else str(result)
        logger.info("ExplorerCrew completed (output_len=%d)", len(raw))
        if len((raw or "").strip()) < 200:
            logger.warning(
                "Exploration too short (%d chars), using fallback", len(raw or "")
            )
            return _fallback_exploration(repo_path, issue_analysis)
        return raw
    except Exception as e:
        logger.error("ExplorerCrew failed: %s", e, exc_info=True)
        return _fallback_exploration(repo_path, issue_analysis)


def _format_review_verdict(result) -> str:
    """Format crew result as 'APPROVED' or 'ISSUES:\\n- ...' for route_verdict."""
    pydantic_val = getattr(result, "pydantic", None)
    if isinstance(pydantic_val, ReviewVerdict):
        if pydantic_val.verdict == "APPROVED":
            return "APPROVED"
        issues = pydantic_val.issues or []
        if not issues:
            return "ISSUES:\n- (Reviewer found problems but did not list specifics)"
        return "ISSUES:\n" + "\n".join(f"- {i}" for i in issues)
    raw = getattr(result, "raw", None) or str(result)
    return _normalize_raw_verdict(raw)


def _normalize_raw_verdict(raw: str) -> str:
    """Fallback: try to extract APPROVED or ISSUES from malformed raw output."""
    text = raw.strip()
    if not text:
        return "ISSUES:\n- (Empty reviewer output)"
    if text.upper().startswith("APPROVED"):
        return "APPROVED"
    if text.upper().startswith("ISSUES:"):
        return text
    idx = text.upper().find("ISSUES:")
    if idx >= 0:
        return text[idx:]
    if "APPROVED" in text.upper() and "ISSUES" not in text.upper()[:50]:
        return "APPROVED"
    return f"ISSUES:\n- (Reviewer output malformed): {text[:300]}"


def _log_crew_metrics(crew, result, crew_name: str = "Crew") -> None:
    """Log crew output (tasks_output, token_usage) and per-agent usage_metrics."""
    try:
        if hasattr(result, "tasks_output") and result.tasks_output:
            summaries = []
            for j, to in enumerate(result.tasks_output):
                s = str(to)
                summaries.append(f"[{j}] {s[:300]}{'...' if len(s) > 300 else ''}")
            logger.debug(
                "%s tasks_output (%d tasks): %s",
                crew_name,
                len(result.tasks_output),
                summaries,
            )
        if hasattr(result, "token_usage") and result.token_usage is not None:
            logger.debug("%s token_usage: %s", crew_name, result.token_usage)
        agents = getattr(crew, "agents", None) or []
        for i, agent in enumerate(agents):
            um = getattr(agent, "usage_metrics", None)
            if um is not None:
                agent_name = (
                    getattr(agent, "role", None)
                    or getattr(agent, "name", None)
                    or f"agent_{i}"
                )
                logger.debug(
                    "%s agent[%s] usage_metrics: %s", crew_name, agent_name, um
                )
        crew_um = getattr(crew, "usage_metrics", None)
        if crew_um is not None:
            logger.debug("%s crew usage_metrics: %s", crew_name, crew_um)
    except Exception as e:
        logger.debug("Could not log crew metrics: %s", e)


def _kickoff_with_retry(crew, inputs: dict, crew_name: str = "Crew"):
    """Run crew.kickoff with exponential backoff on rate limits and empty LLM responses."""
    max_retries = max(RATE_LIMIT_MAX_RETRIES, EMPTY_RESPONSE_MAX_RETRIES)
    last_error = None
    for attempt in range(max_retries):
        try:
            result = crew.kickoff(inputs=inputs)
            _log_crew_metrics(crew, result, crew_name)
            if attempt > 0:
                logger.info(
                    "Crew kickoff succeeded on attempt %d/%d", attempt + 1, max_retries
                )
            return result
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
                logger.error(
                    "Crew kickoff attempt %d/%d failed (retrying): %s",
                    attempt + 1,
                    max_retries,
                    e,
                    exc_info=True,
                )
                time.sleep(delay)
            else:
                logger.error(
                    "Crew kickoff failed after %d attempts: %s",
                    attempt + 1,
                    e,
                    exc_info=True,
                )
                raise
    if last_error is not None:
        raise last_error
    raise RuntimeError("Retry loop exited without capturing exception")


@dataclass
class PipelineArgs:
    """Single source of truth for pipeline arguments from CLI or programmatic call."""

    repo_path: str = ""
    task: str = ""
    branch: str = "main"
    from_scratch: bool = False
    max_retries: int = 3
    dry_run: bool = False
    test_command: str = ""
    issue_id: str = ""
    github_repo: str = ""
    issue_url: str = ""
    docs_url: str = ""
    focus_paths: str = ""
    exclude_paths: str = ""

    def to_flow_inputs(self) -> dict:
        """Convert to flow inputs dict with repo_path normalized."""
        return {
            "repo_path": os.path.abspath(self.repo_path or os.getcwd()),
            "task": self.task,
            "branch": self.branch,
            "from_scratch": self.from_scratch,
            "dry_run": self.dry_run,
            "max_retries": self.max_retries,
            "test_command": self.test_command,
            "issue_id": self.issue_id,
            "github_repo": self.github_repo,
            "issue_url": self.issue_url,
            "docs_url": self.docs_url,
            "focus_paths": self.focus_paths,
            "exclude_paths": self.exclude_paths,
        }

    def replace(self, **overrides) -> "PipelineArgs":
        """Return new PipelineArgs with overrides applied (None values ignored)."""
        d = asdict(self)
        for k, v in overrides.items():
            if v is not None and k in d:
                d[k] = v
        return PipelineArgs(**d)


def _load_config(path: str) -> dict:
    """Load pipeline config from YAML. Returns dict with snake_case keys."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    data = yaml.safe_load(p.read_text())
    if not isinstance(data, dict):
        raise ValueError(f"Config must be a YAML object, got {type(data)}")
    # Map config keys (snake_case) to PipelineArgs fields
    key_map = {
        "task": "task",
        "repo_path": "repo_path",
        "branch": "branch",
        "from_scratch": "from_scratch",
        "max_retries": "max_retries",
        "dry_run": "dry_run",
        "test_command": "test_command",
        "issue_id": "issue_id",
        "github_repo": "github_repo",
        "issue_url": "issue_url",
        "docs_url": "docs_url",
        "focus_paths": "focus_paths",
        "exclude_paths": "exclude_paths",
    }
    out = {}
    for k, v in data.items():
        key = k.replace("-", "_")  # support kebab-case
        if key in key_map:
            val = v
            if key in ("focus_paths", "exclude_paths") and isinstance(v, list):
                val = ",".join(str(x) for x in v) if v else ""
            out[key_map[key]] = val
    return out


def _parse_args() -> PipelineArgs:
    """Parse command-line arguments into PipelineArgs."""
    parser = argparse.ArgumentParser(
        description="Code pipeline: explore -> plan -> implement -> review -> commit"
    )
    parser.add_argument("-c", "--config", help="Path to YAML config file (all params)")
    parser.add_argument("-r", "--repo-path", default=None, help="Repository path")
    parser.add_argument(
        "-t", "--task", default=None, help="Task description (required)"
    )
    parser.add_argument("-b", "--branch", default=None, help="Git branch")
    parser.add_argument("-n", "--retries", type=int, default=None, help="Max retries")
    parser.add_argument("--dry-run", action="store_true", help="Skip git commit")
    parser.add_argument(
        "--test-command", default=None, help="Test command (e.g. pytest)"
    )
    parser.add_argument("--issue-id", default=None, help="Issue ID for commit")
    parser.add_argument(
        "--github-repo", default=None, help="GitHub repo for GithubSearchTool"
    )
    parser.add_argument(
        "--issue-url", default=None, help="Issue URL for ScrapeWebsiteTool"
    )
    parser.add_argument(
        "--docs-url", default=None, help="Docs URL for CodeDocsSearchTool"
    )
    parser.add_argument(
        "--focus-paths",
        default=None,
        help="Comma-separated paths to prioritize in exploration (e.g. src,lib)",
    )
    parser.add_argument(
        "--exclude-paths",
        default=None,
        help="Comma-separated paths to skip in exploration (e.g. node_modules,vendor)",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable DEBUG logging"
    )
    parser.add_argument(
        "-f",
        "--from-scratch",
        action="store_true",
        help="Ignore checkpoint and run from the beginning",
    )
    ns = parser.parse_args()

    # Load config file as base (if provided)
    config_data: dict = {}
    if ns.config:
        config_data = _load_config(ns.config)
        # Normalize booleans
        for key in ("from_scratch", "dry_run"):
            if key in config_data:
                v = config_data[key]
                if isinstance(v, str):
                    config_data[key] = v.lower() in ("true", "1", "yes")

    # Defaults when no config
    defaults = {
        "repo_path": os.getcwd(),
        "task": "",
        "branch": "main",
        "from_scratch": False,
        "max_retries": 3,
        "dry_run": False,
        "test_command": "",
        "issue_id": "",
        "github_repo": "",
        "issue_url": "",
        "docs_url": "",
        "focus_paths": "",
        "exclude_paths": "",
    }
    # Merge: config first, then defaults, then CLI overrides
    base = {**defaults, **config_data}
    cli_overrides = {
        "repo_path": ns.repo_path,
        "task": ns.task,
        "branch": ns.branch,
        "max_retries": ns.retries,
        "test_command": ns.test_command,
        "issue_id": ns.issue_id,
        "github_repo": ns.github_repo,
        "issue_url": ns.issue_url,
        "docs_url": ns.docs_url,
        "focus_paths": ns.focus_paths,
        "exclude_paths": ns.exclude_paths,
    }
    # store_true: only override when user explicitly passed the flag (don't overwrite config with False)
    if getattr(ns, "from_scratch", False):
        cli_overrides["from_scratch"] = True
    if getattr(ns, "dry_run", False):
        cli_overrides["dry_run"] = True
    for k, v in cli_overrides.items():
        if v is not None:
            base[k] = v

    return PipelineArgs(
        repo_path=base["repo_path"],
        task=base["task"] or "",
        branch=base["branch"],
        from_scratch=base["from_scratch"],
        max_retries=base["max_retries"],
        dry_run=base["dry_run"],
        test_command=base["test_command"] or "",
        issue_id=base["issue_id"] or "",
        github_repo=base["github_repo"] or "",
        issue_url=base["issue_url"] or "",
        docs_url=base["docs_url"] or "",
        focus_paths=base.get("focus_paths", "") or "",
        exclude_paths=base.get("exclude_paths", "") or "",
    )


class PipelineState(BaseModel):
    """State for the code pipeline flow."""

    id: str = ""
    from_scratch: bool = False
    repo_path: str = ""
    repo_context: str = ""  # Shared context (Repository, GitHub, etc.) for agents
    task: str = ""
    branch: str = "main"
    dry_run: bool = False
    focus_paths: str = ""
    exclude_paths: str = ""
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
    clarifications: str = ""
    replan_count: int = 0
    max_replans: int = 2
    quality_gate_passed: bool = False
    quality_gate_output: str = ""
    verification_passed: bool = False
    verification_output: str = ""


@persist(
    SQLiteFlowPersistence(
        db_path=str(Path(db_storage_path()) / "code_pipeline_flow_states.db")
    ),
    verbose=False,
)
class CodePipelineFlow(Flow[PipelineState]):
    """Event-driven coding pipeline: explore 1 plan 1 implement 1 review 1 commit."""

    def _run_quality_check(self, test_command: str) -> tuple[bool, str]:
        """Run test command in repo. Return (passed, output)."""
        if not test_command:
            logger.debug("Quality gate skipped (no test_command)")
            return True, ""
        logger.info("Running quality gate: %s", test_command)
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
            passed = result.returncode == 0
            logger.info(
                "Quality gate %s (exit=%d)",
                "PASSED" if passed else "FAILED",
                result.returncode,
            )
            return passed, output
        except subprocess.TimeoutExpired:
            logger.error("Quality gate timed out after 300s", exc_info=True)
            return False, "Error: command timed out after 300 seconds."
        except Exception as e:
            logger.error("Quality gate failed: %s", e, exc_info=True)
            return False, str(e)

    def _run_crew(self, crew_class, inputs: dict, state_attr: str | None = None):
        """Run a crew and optionally store result in state. Returns raw output."""
        crew_name = crew_class.__name__
        if "repo_context" not in inputs:
            inputs = dict(inputs)
            inputs["repo_context"] = build_repo_context(
                inputs.get("repo_path", "") or self.state.repo_path,
                inputs.get("github_repo", "") or self.state.github_repo,
                inputs.get("issue_url", "") or self.state.issue_url,
                inputs.get("docs_url", "") or self.state.docs_url,
                inputs.get("test_command", "") or self.state.test_command,
            )
        logger.info("Running crew: %s", crew_name)
        _log_crew_context(crew_name, inputs)
        try:
            result = _kickoff_with_retry(
                crew_class().crew(),
                inputs,
                crew_name=crew_name,
            )
        except Exception as e:
            logger.error("Crew %s failed: %s", crew_name, e, exc_info=True)
            raise
        raw = result.raw if hasattr(result, "raw") else str(result)
        if state_attr:
            setattr(self.state, state_attr, raw)
            if state_attr == "implementation":
                _log_implementer_summary(raw)
            else:
                logger.info(
                    "Crew %s completed -> state.%s (len=%d)",
                    crew_name,
                    state_attr,
                    len(raw),
                )
        else:
            logger.info("Crew %s completed (no state_attr)", crew_name)
        return raw

    def _retry_or_abort(self, prior_issues_prefix: str, output: str) -> str:
        """Increment retry count; return 'pipeline_aborted' or 'retry'."""
        self.state.retry_count += 1
        if self.state.retry_count >= self.state.max_retries:
            logger.warning(
                "Max retries (%d) reached -> pipeline_aborted", self.state.max_retries
            )
            return "pipeline_aborted"
        self.state.prior_issues = prior_issues_prefix + output
        logger.info(
            "Retry %d/%d requested, prior_issues updated",
            self.state.retry_count,
            self.state.max_retries,
        )
        return "retry"

    @start()
    def analyze_issue(self):
        """Run IssueAnalystCrew to parse issue into structured requirements."""
        if self.state.issue_analysis and not self.state.from_scratch:
            logger.info("Flow step: analyze_issue (resumed, cached)")
            return self.state.issue_analysis
        logger.info("Flow step: analyze_issue (start)")
        repo_path = os.path.abspath(self.state.repo_path or os.getcwd())
        os.environ["REPO_PATH"] = repo_path
        os.environ["GITHUB_REPO"] = self.state.github_repo or ""
        os.environ["ISSUE_URL"] = self.state.issue_url or ""
        os.environ["DOCS_URL"] = self.state.docs_url or ""
        return self._run_crew(
            IssueAnalystCrew,
            {
                "task": self.state.task,
                "issue_url": self.state.issue_url,
                "github_repo": self.state.github_repo,
                "repo_path": self.state.repo_path,
                "docs_url": self.state.docs_url,
                "test_command": self.state.test_command,
                "branch": self.state.branch,
            },
            "issue_analysis",
        )

    @listen(analyze_issue)
    def explore(self):
        """Run ExplorerCrew sequentially. On failure, use fallback exploration."""
        if self.state.exploration and not self.state.from_scratch:
            logger.info("Flow step: explore (resumed, cached)")
            return self.state.exploration
        logger.info("Flow step: explore")
        repo_path = os.path.abspath(self.state.repo_path or os.getcwd())
        os.environ["REPO_PATH"] = repo_path
        self.state.repo_path = repo_path
        _log_crew_context(
            "ExplorerCrew",
            {
                "repo_path": repo_path,
                "test_command": self.state.test_command,
                "focus_paths": getattr(self.state, "focus_paths", "") or "",
                "exclude_paths": getattr(self.state, "exclude_paths", "") or "",
                "github_repo": self.state.github_repo or "",
            },
            exclude_keys=(
                "plan",
                "implementation",
                "exploration",
                "issue_analysis",
                "clarifications",
            ),
        )
        raw = _run_explore_in_process(
            repo_path,
            self.state.issue_analysis,
            task=self.state.task,
            test_command=self.state.test_command,
            focus_paths=getattr(self.state, "focus_paths", "") or "",
            exclude_paths=getattr(self.state, "exclude_paths", "") or "",
            github_repo=self.state.github_repo or "",
            repo_context=getattr(self.state, "repo_context", "") or "",
        )
        self.state.exploration = raw
        return raw

    @listen(explore)
    def clarify(self):
        """
        Clarify step: ask the human targeted questions grounded in the exploration
        results, before the architect creates the implementation plan.
        """
        if self.state.clarifications and not self.state.from_scratch:
            logger.info("Flow step: clarify (resumed, cached)")
            return self.state.clarifications
        logger.info("Flow step: clarify")
        return self._run_crew(
            ClarifyCrew,
            {
                "task": self.state.task,
                "issue_analysis": self.state.issue_analysis,
                "exploration": self.state.exploration,
            },
            "clarifications",
        )

    @listen(or_(clarify, "do_replan"))
    def plan(self):
        """Run ArchitectCrew to produce file-level plan."""
        if self.state.plan and not self.state.from_scratch:
            logger.info("Flow step: plan (resumed, cached)")
            return self.state.plan
        logger.info("Flow step: plan")
        return self._run_crew(
            ArchitectCrew,
            {
                "task": self.state.task,
                "exploration": self.state.exploration,
                "issue_analysis": self.state.issue_analysis,
                "prior_issues": self.state.prior_issues,
                "clarifications": self.state.clarifications,
                "github_repo": self.state.github_repo,
                "docs_url": self.state.docs_url,
                "repo_path": self.state.repo_path,
                "test_command": self.state.test_command,
            },
            "plan",
        )

    @listen(plan)
    def implement(self):
        """Run ImplementerCrew; fires on first run (after plan)."""
        if self.state.implementation and not self.state.from_scratch:
            logger.info("Flow step: implement (resumed, cached)")
            return self.state.implementation
        return self._run_implement()

    @listen("retry")
    def implement_retry(self):
        """Run ImplementerCrew on retry; fires when route_verdict or route_after_implement returns 'retry'."""
        return self._run_implement()

    def _run_implement(self):
        """Shared implementation logic for initial run and retries."""
        logger.info("Flow step: implement (retry_count=%d)", self.state.retry_count)
        repo_path = os.path.abspath(self.state.repo_path or os.getcwd())
        os.environ["REPO_PATH"] = repo_path
        return self._run_crew(
            ImplementerCrew,
            {
                "task": self.state.task,
                "plan": self.state.plan,
                "prior_issues": self.state.prior_issues,
                "clarifications": self.state.clarifications,
                "repo_path": self.state.repo_path,
                "issue_analysis": self.state.issue_analysis,
                "exploration": self.state.exploration,
                "test_command": self.state.test_command,
            },
            "implementation",
        )

    @listen(implement)
    def quality_gate(self):
        """Run quality check (tests) if test_command is set; fires after initial implement."""
        return self._run_quality_gate()

    @listen(implement_retry)
    def quality_gate_retry(self):
        """Run quality check after retry; fires after implement_retry."""
        return self._run_quality_gate()

    def _repo_has_changes(self) -> tuple[bool, str]:
        """Run git status --short in repo. Return (has_changes, output).
        Ignores .code_pipeline/ (pipeline state, not application code)."""
        repo = os.path.abspath(self.state.repo_path or "")
        if not repo or not os.path.isdir(repo):
            return False, "Repo path invalid"
        try:
            result = subprocess.run(
                ["git", "status", "--short"],
                cwd=repo,
                capture_output=True,
                text=True,
                timeout=10,
            )
            out = (result.stdout or "").strip()
            # Filter out .code_pipeline — pipeline state, not application changes
            lines = [l for l in out.splitlines() if ".code_pipeline" not in l]
            filtered = "\n".join(lines).strip()
            return bool(filtered), filtered or out or "(no changes)"
        except Exception as e:
            logger.warning("git status failed: %s", e)
            return False, str(e)

    def _run_quality_gate(self):
        """Shared quality gate logic. Fails if no file changes detected."""
        logger.info("Flow step: quality_gate")
        has_changes, status_out = self._repo_has_changes()
        if not has_changes:
            msg = (
                "CRITICAL: No file changes detected in the repository. "
                "You MUST use the Repo File Writer Tool to create or modify files. "
                "Do not output intent ('I'll...')—actually invoke the tool and write the code."
            )
            logger.warning("Quality gate failed: %s", msg)
            self.state.quality_gate_passed = False
            self.state.quality_gate_output = msg
            return False
        passed, output = self._run_quality_check(self.state.test_command)
        self.state.quality_gate_passed = passed
        self.state.quality_gate_output = output
        return passed

    @router(or_(quality_gate, quality_gate_retry))
    def route_after_implement(self):
        """Route to review or retry based on quality gate."""
        logger.info(
            "Flow step: route_after_implement (quality_gate_passed=%s)",
            self.state.quality_gate_passed,
        )
        if not self.state.test_command:
            return "review"
        if self.state.quality_gate_passed:
            return "review"
        prefix = (
            "No file changes detected. Implementer must write files:\n\n"
            if "No file changes" in (self.state.quality_gate_output or "")
            else "Quality gate failed (tests/lint):\n\n"
        )
        return self._retry_or_abort(prefix, self.state.quality_gate_output)

    @listen("review")
    def run_review(self):
        """Run ReviewerCrew; sets review_verdict (APPROVED or ISSUES:...).
        Named run_review to avoid collision: method name must differ from listen('review')
        or CrewAI re-triggers this step when it completes (infinite loop)."""
        if self.state.review_verdict and not self.state.from_scratch:
            logger.info("Flow step: review (resumed, cached)")
            return self.state.review_verdict
        logger.info("Flow step: review")
        repo_path = os.path.abspath(self.state.repo_path or os.getcwd())
        os.environ["REPO_PATH"] = repo_path
        _log_crew_context(
            "ReviewerCrew",
            {
                "task": (self.state.task or "")[:80]
                + ("..." if len(self.state.task or "") > 80 else ""),
                "plan_len": len(self.state.plan or ""),
                "implementation_len": len(self.state.implementation or ""),
                "repo_path": repo_path,
            },
            exclude_keys=(),
        )
        inputs = {
            "task": self.state.task,
            "plan": self.state.plan,
            "implementation": self.state.implementation,
            "repo_path": self.state.repo_path,
            "issue_analysis": self.state.issue_analysis,
            "docs_url": self.state.docs_url,
            "repo_context": getattr(self.state, "repo_context", "")
            or build_repo_context(
                self.state.repo_path,
                "",
                "",
                self.state.docs_url,
                self.state.test_command,
            ),
        }
        result = _kickoff_with_retry(
            ReviewerCrew().crew(),
            inputs,
            crew_name="ReviewerCrew",
        )
        verdict_str = _format_review_verdict(result)
        self.state.review_verdict = verdict_str
        _log_reviewer_verdict(verdict_str)
        return verdict_str

    @router(run_review)
    def route_verdict(self):
        """Route based on verdict: commit, retry, or abort. Run verification when APPROVED."""
        verdict = self.state.review_verdict.strip()
        logger.info(
            "Flow step: route_verdict (verdict_prefix=%s)",
            verdict[:50] if verdict else "(empty)",
        )
        if verdict.upper().startswith("APPROVED"):
            if self.state.test_command:
                logger.info("Running verification tests after APPROVED")
                passed, output = self._run_quality_check(self.state.test_command)
                self.state.verification_passed = passed
                self.state.verification_output = output
                if not passed:
                    logger.warning("Verification failed after approval -> retry")
                    return self._retry_or_abort(
                        "Tests failed after approval. Fix:\n\n", output
                    )
            logger.info("APPROVED -> routing to human_gate")
            return "human_gate"
        return self._retry_or_abort(
            "IMPORTANT — A previous attempt was REJECTED. Fix ALL:\n\n", verdict
        )

    @listen("human_gate")
    @human_feedback(
        message=(
            "──────────────────────────────────────────────────────────\n"
            "🔍  PIPELINE REVIEW — Human approval required before commit\n"
            "──────────────────────────────────────────────────────────\n\n"
            "The AI reviewer returned APPROVED.\n\n"
            "Review the output above, then reply:\n"
            "  • 'commit'  — approve and commit to the branch\n"
            "  • 'replan'  — reject and describe what needs to change\n\n"
            "Your feedback (if rejecting) will be fed back into the planner."
        ),
        emit=["commit", "replan"],
        llm="gpt-4o-mini",
        default_outcome="replan",
    )
    def run_human_gate(self):
        """
        Present the final review verdict to the human.
        The method output is what gets shown — include all context the human needs.
        """
        logger.info("Flow step: human_gate (awaiting commit/replan)")
        return (
            f"## Task\n{self.state.task}\n\n"
            f"## Review Verdict\n{self.state.review_verdict}\n\n"
            f"## Implementation Summary\n{self.state.implementation}\n\n"
            f"## Plan\n{self.state.plan}"
        )

    @listen("replan")
    def handle_human_replan(self, result: HumanFeedbackResult):
        """
        Human rejected the implementation. Feed their feedback back as prior_issues
        and restart from the plan step.
        """
        logger.info(
            "Flow step: handle_human_replan (feedback_len=%d)",
            len(result.feedback or ""),
        )
        if self.state.replan_count >= self.state.max_replans:
            logger.warning("Max replans (%d) reached, aborting", self.state.max_replans)
            print(
                f"\n⛔  Max replans ({self.state.max_replans}) reached. "
                "Aborting pipeline.\n"
            )
            return "pipeline_aborted"

        self.state.replan_count += 1
        self.state.retry_count = 0  # reset AI retry counter for the new attempt

        # Store human feedback as prior issues so the planner and implementer see it
        self.state.prior_issues = (
            f"[Human reviewer requested changes in replan #{self.state.replan_count}]\n"
            f"{result.feedback}"
        )

        logger.info(
            "Replan #%d -> do_replan (feeding prior_issues)", self.state.replan_count
        )
        print(
            f"\n🔄  Replan #{self.state.replan_count} requested.\n"
            f"Feedback: {result.feedback}\n"
        )
        return "do_replan"

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
    def run_commit(self):
        """Run CommitCrew; creates feature branch, commits, then pushes and creates PR."""
        feature_branch = self._make_feature_branch_name()
        repo_path = os.path.abspath(self.state.repo_path or os.getcwd())
        os.environ["REPO_PATH"] = repo_path
        logger.info(
            "Flow step: commit (dry_run=%s, feature_branch=%s)",
            self.state.dry_run,
            feature_branch,
        )
        return self._run_crew(
            CommitCrew,
            {
                "repo_path": self.state.repo_path,
                "branch": self.state.branch,
                "feature_branch": feature_branch,
                "dry_run": "true" if self.state.dry_run else "false",
                "issue_id": self.state.issue_id or "",
                "task": self.state.task or "",
                "implementation": self.state.implementation or "",
                "plan": self.state.plan or "",
                "review_verdict": self.state.review_verdict or "",
                "issue_url": self.state.issue_url or "",
                "github_repo": self.state.github_repo or "",
            },
            state_attr=None,
        )

    @listen("pipeline_aborted")
    def handle_abort(self):
        """Terminal: return message with retry count and last verdict. Uses distinct
        event name to avoid loop (completing 'abort' would re-emit and retrigger)."""
        global _pipeline_aborted
        _pipeline_aborted = True
        logger.warning("Flow step: handle_abort (pipeline aborted)")
        msg = (
            f"Pipeline aborted after {self.state.retry_count} retries. "
            f"Last verdict:\n\n{self.state.review_verdict}"
        )
        return msg


def kickoff(
    repo_path: str | None = None,
    task: str | None = None,
    branch: str | None = None,
    from_scratch: bool | None = None,
    max_retries: int | None = None,
    dry_run: bool | None = None,
    test_command: str | None = None,
    issue_id: str | None = None,
    github_repo: str | None = None,
    issue_url: str | None = None,
    docs_url: str | None = None,
    focus_paths: str | None = None,
    exclude_paths: str | None = None,
    inputs: dict | None = None,
):
    """Run the code pipeline flow. Uses argparse when invoked from CLI."""
    _configure_logging()
    overrides = {
        "repo_path": repo_path,
        "task": task,
        "branch": branch,
        "from_scratch": from_scratch,
        "max_retries": max_retries,
        "dry_run": dry_run,
        "test_command": test_command,
        "issue_id": issue_id,
        "github_repo": github_repo,
        "issue_url": issue_url,
        "docs_url": docs_url,
        "focus_paths": focus_paths,
        "exclude_paths": exclude_paths,
    }
    args = _parse_args().replace(**overrides)
    flow_inputs = (inputs or {}) | args.to_flow_inputs()
    # Auto-detect repo_path, github_repo, issue_url when running inside the repo
    enriched = enrich_repo_context(
        flow_inputs.get("repo_path", ""),
        flow_inputs.get("github_repo", ""),
        flow_inputs.get("issue_url", ""),
        flow_inputs.get("issue_id", ""),
    )
    for k, v in enriched.items():
        if not v:
            continue
        current = (flow_inputs.get(k) or "").strip()
        use = (not current or current == ".") if k == "repo_path" else not current
        if use:
            flow_inputs[k] = v
    flow_inputs["repo_context"] = build_repo_context(
        flow_inputs.get("repo_path", ""),
        flow_inputs.get("github_repo", ""),
        flow_inputs.get("issue_url", ""),
        flow_inputs.get("docs_url", ""),
        flow_inputs.get("test_command", ""),
    )
    if not flow_inputs.get("task"):
        raise ValueError("task is required (use --task / -t)")
    logger.info(
        "Pipeline kickoff: task=%s, repo_path=%s",
        flow_inputs.get("task", "")[:80],
        flow_inputs.get("repo_path", ""),
    )
    return _execute_flow(flow_inputs)


@log_exceptions("Pipeline kickoff")
def _execute_flow(inputs: dict):
    """Run the pipeline flow. Decorator logs any exception before re-raising."""
    global _pipeline_aborted
    _pipeline_aborted = False

    repo_path = os.path.abspath(inputs.get("repo_path", os.getcwd()))
    task = inputs.get("task", "")
    from_scratch = inputs.get("from_scratch", False)

    flow = CodePipelineFlow()
    kickoff_inputs = dict(inputs)

    if not from_scratch and task:
        checkpoint_id = _load_checkpoint(repo_path, task)
        if checkpoint_id:
            kickoff_inputs["id"] = checkpoint_id
            logger.info("Resuming from checkpoint (flow_id=%s)", checkpoint_id[:8])

    result = flow.kickoff(inputs=kickoff_inputs)

    if task:
        _save_checkpoint(repo_path, task, flow.flow_id)

    if _pipeline_aborted:
        sys.exit(1)

    return result


@log_exceptions("Flow plot")
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
        logger.error("Invalid JSON trigger payload: %s", e, exc_info=True)
        raise ValueError(f"Invalid JSON payload: {e}") from e

    return _execute_flow_with_trigger(trigger_payload)


@log_exceptions("Flow execution (run_with_trigger)")
def _execute_flow_with_trigger(trigger_payload: dict):
    """Run flow with trigger payload. Decorator logs any exception before re-raising."""
    flow = CodePipelineFlow()
    return flow.kickoff({"crewai_trigger_payload": trigger_payload})


@log_exceptions("Pipeline exited")
def _main():
    """Entry point for CLI. Decorator logs any exception before re-raising."""
    args = _parse_args()
    if getattr(args, "verbose", False):
        os.environ["CODE_PIPELINE_LOG_LEVEL"] = "DEBUG"
    _configure_logging()
    kickoff(
        repo_path=args.repo_path,
        task=args.task,
        branch=args.branch,
        from_scratch=args.from_scratch,
        max_retries=args.max_retries,
        dry_run=args.dry_run,
        test_command=getattr(args, "test_command", ""),
        issue_id=getattr(args, "issue_id", ""),
        github_repo=getattr(args, "github_repo", ""),
        issue_url=getattr(args, "issue_url", ""),
        docs_url=getattr(args, "docs_url", ""),
        focus_paths=getattr(args, "focus_paths", "") or "",
        exclude_paths=getattr(args, "exclude_paths", "") or "",
    )


if __name__ == "__main__":
    _main()
