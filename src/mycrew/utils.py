"""Shared utilities for the code pipeline."""

import functools
import httpx
import logging
import os
import re
import shutil
import subprocess
from typing import Callable, TypeVar

from mycrew.settings import get_settings

F = TypeVar("F", bound=Callable[..., object])
logger = logging.getLogger(__name__)


def build_repo_context(
    repo_path: str = "",
    github_repo: str = "",
    issue_url: str = "",
) -> str:
    """
    Build a shared context string for agents. Reduces repetition of repo_path,
    github_repo, etc. across task descriptions. Used when running inside the repo.
    """
    lines = []
    if repo_path is not None:
        rp = repo_path.strip()
    else:
        rp = ""
    if rp:
        lines.append(f"- Repository: {rp}")
    if github_repo is not None:
        gh = github_repo.strip()
    else:
        gh = ""
    if gh:
        lines.append(f"- GitHub: {gh} (use for gh -R)")
    else:
        lines.append("- GitHub: (auto-detected from git remote when empty)")
    if issue_url is not None:
        iu = issue_url.strip()
    else:
        iu = ""
    if iu:
        lines.append(f"- Issue URL: {iu}")
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


def is_git_repo(path: str) -> bool:
    """Return True if path is a valid git repository root."""
    if not path or not os.path.isdir(path):
        return False
    abs_path = os.path.abspath(path)
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=abs_path,
            capture_output=True,
            text=True,
            timeout=5,
        )
        return out.returncode == 0 and bool(out.stdout and out.stdout.strip())
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def clone_repo_for_issue(
    github_repo: str,
    parent_dir: str,
    branch: str,
    token: str,
) -> str:
    """
    Clone the repo into parent_dir. Returns absolute path to clone.

    Uses GITHUB_TOKEN for auth. parent_dir should be unique per run
    (e.g. /tmp/code_pipeline_<uuid>).
    """
    if not token or not token.strip():
        raise ValueError("GITHUB_TOKEN is required for clone_repo_for_issue")
    if not github_repo or "/" not in github_repo:
        raise ValueError("github_repo must be owner/repo format")
    owner, repo_name = github_repo.split("/", 1)
    repo_name = repo_name.strip()
    owner = owner.strip()
    if not owner or not repo_name:
        raise ValueError("github_repo must be owner/repo format")
    url = f"https://x-access-token:{token.strip()}@github.com/{owner}/{repo_name}.git"
    target_name = f"{owner}-{repo_name}".replace("/", "-")
    target_dir = os.path.join(parent_dir, target_name)
    abs_target = os.path.abspath(target_dir)
    abs_parent = os.path.abspath(parent_dir)
    if not abs_target.startswith(abs_parent):
        raise ValueError("Target path escapes parent_dir")
    os.makedirs(parent_dir, exist_ok=True)
    logger.info(f"Cloning {github_repo}")
    result = subprocess.run(
        ["git", "clone", "--branch", branch, "--depth", "1", url, target_dir],
        capture_output=True,
        text=True,
        timeout=300,
    )
    if result.returncode != 0:
        stderr = result.stderr if result.stderr else ""
        raise ValueError(f"git clone failed: {stderr.strip() or 'unknown error'}")
    return abs_target


def delete_cloned_repo(path: str) -> None:
    """
    Remove the cloned repo directory. Swallows errors but logs them.

    Called in finally block after pipeline execution.
    Only deletes paths under /tmp for safety.
    """
    if not path or not path.strip():
        return
    abs_path = os.path.abspath(os.path.normpath(path.strip()))
    tmp_real = os.path.realpath("/tmp")
    path_real = os.path.realpath(abs_path) if os.path.exists(abs_path) else abs_path
    if not path_real.startswith(tmp_real + os.sep) and path_real != tmp_real:
        return
    try:
        if os.path.exists(abs_path):
            shutil.rmtree(abs_path)
            logger.info(f"Deleted cloned repo")
    except Exception:
        pass


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


def log_exceptions(
    message: str | F | None = None,
) -> Callable[[F], F] | F:
    """Decorator that logs any exception with exc_info=True and re-raises.

    Use as @log_exceptions or @log_exceptions("custom message").
    """

    if isinstance(message, str):
        msg_prefix: str | None = message
    else:
        msg_prefix = None

    def decorator(fn: F) -> F:
        @functools.wraps(fn)
        def wrapper(*args: object, **kwargs: object) -> object:
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                log = logging.getLogger(fn.__module__)
                if msg_prefix is not None:
                    msg = msg_prefix
                else:
                    msg = f"{fn.__qualname__} failed"
                log.error("%s: %s", msg, e, exc_info=True)
                raise

        return wrapper  # type: ignore[return-value]

    if message is not None and callable(message) and not isinstance(message, str):
        return decorator(message)  # type: ignore[return-value]
    return decorator  # type: ignore[return-value]
