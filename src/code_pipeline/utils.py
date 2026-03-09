"""Shared utilities for the code pipeline."""

import functools
import logging
import os
import re
import subprocess
from typing import Callable, TypeVar

F = TypeVar("F", bound=Callable[..., object])


def build_repo_context(
    repo_path: str = "",
    github_repo: str = "",
    issue_url: str = "",
    docs_url: str = "",
    test_command: str = "",
) -> str:
    """
    Build a shared context string for agents. Reduces repetition of repo_path,
    github_repo, etc. across task descriptions. Used when running inside the repo.
    """
    lines = []
    rp = (repo_path or "").strip()
    if rp:
        lines.append(f"- Repository: {rp}")
    gh = (github_repo or "").strip()
    if gh:
        lines.append(f"- GitHub: {gh} (use for gh -R)")
    else:
        lines.append("- GitHub: (auto-detected from git remote when empty)")
    iu = (issue_url or "").strip()
    if iu:
        lines.append(f"- Issue URL: {iu}")
    doc = (docs_url or "").strip()
    if doc:
        lines.append(f"- Docs: {doc}")
    tc = (test_command or "").strip()
    if tc:
        lines.append(f"- Test command: {tc}")
    if not lines:
        return "(no context)"
    return "\n".join(lines)


def detect_repo_path(cwd: str | None = None) -> str:
    """Resolve repo path: use git root when in a git repo, else cwd."""
    base = os.path.abspath(cwd or os.getcwd())
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=base,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if out.returncode == 0 and out.stdout:
            return out.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return base


def detect_github_repo(repo_path: str) -> str:
    """Parse owner/repo from git remote origin. Empty if not a GitHub repo."""
    try:
        out = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if out.returncode != 0 or not out.stdout:
            return ""
        url = out.stdout.strip()
        m = re.search(r"github\.com[/:]([^/]+)/([^/]+?)(?:\.git)?$", url)
        if m:
            return f"{m.group(1)}/{m.group(2)}"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return ""


def derive_issue_url(github_repo: str, issue_id: str) -> str:
    """Build GitHub issue URL from repo and issue_id (e.g. 'fixes #42' -> 42)."""
    if not github_repo or not issue_id:
        return ""
    m = re.search(r"#?(\d+)", issue_id)
    if m:
        return f"https://github.com/{github_repo}/issues/{m.group(1)}"
    return ""


def enrich_repo_context(
    repo_path: str,
    github_repo: str = "",
    issue_url: str = "",
    issue_id: str = "",
) -> dict[str, str]:
    """
    Auto-detect repo_path, github_repo, and issue_url when running inside a GitHub repo.
    Only fills values that are empty. Returns dict with repo_path, github_repo, issue_url.
    """
    repo = os.path.abspath(repo_path or os.getcwd())
    if not repo or repo == ".":
        repo = detect_repo_path(os.getcwd())

    gh = (github_repo or "").strip() or None
    if not gh:
        gh = detect_github_repo(repo)
    gh = gh or ""

    url = (issue_url or "").strip() or None
    if not url and gh and issue_id:
        url = derive_issue_url(gh, issue_id)
    url = url or ""

    return {"repo_path": repo, "github_repo": gh, "issue_url": url}


def log_exceptions(
    message: str | F | None = None,
) -> Callable[[F], F] | F:
    """Decorator that logs any exception with exc_info=True and re-raises.

    Use as @log_exceptions or @log_exceptions("custom message").
    """

    msg_prefix: str | None = message if isinstance(message, str) else None

    def decorator(fn: F) -> F:
        @functools.wraps(fn)
        def wrapper(*args: object, **kwargs: object) -> object:
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                log = logging.getLogger(fn.__module__)
                msg = msg_prefix or f"{fn.__qualname__} failed"
                log.error("%s: %s", msg, e, exc_info=True)
                raise

        return wrapper  # type: ignore[return-value]

    if message is not None and callable(message) and not isinstance(message, str):
        return decorator(message)  # type: ignore[return-value]
    return decorator  # type: ignore[return-value]
