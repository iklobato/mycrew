"""Shared utilities for the code pipeline."""

import functools
import logging
import os
import re
import subprocess
from typing import Callable, TypeVar

from code_pipeline.settings import get_settings

F = TypeVar("F", bound=Callable[..., object])


def resolve_issue_url(issue_url: str) -> dict[str, str]:
    """
    Parse a GitHub issue/PR URL and fetch its content via the GitHub API.
    Returns task, github_repo, issue_id, repo_path. GITHUB_TOKEN required.
    """
    if issue_url is not None:
        url = issue_url.strip()
    else:
        url = ""
    if not url:
        raise ValueError("issue_url is required and cannot be empty")

    # Parse: https://github.com/owner/repo/issues/123 or /pull/456
    m = re.search(
        r"https?://(?:www\.)?github\.com/([^/]+)/([^/]+)/(issues|pull)/(\d+)",
        url,
        re.IGNORECASE,
    )
    if not m:
        raise ValueError(
            f"Invalid GitHub issue URL: {url}. "
            "Expected format: https://github.com/owner/repo/issues/123 or /pull/456"
        )

    owner, repo_name, kind, number = (
        m.group(1),
        m.group(2),
        m.group(3).lower(),
        m.group(4),
    )
    is_pull = kind == "pull"

    github_repo = f"{owner}/{repo_name}"
    if is_pull:
        issue_id = f"PR#{number}"
    else:
        issue_id = f"#{number}"

    # Fetch title from GitHub API
    token = get_settings().github_token.strip()
    if not token:
        raise ValueError(
            "GITHUB_TOKEN is required when using issue_url. "
            "Set it in environment or config api_keys.github_token."
        )

    try:
        import httpx

        api_url = f"https://api.github.com/repos/{owner}/{repo_name}/issues/{number}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json",
        }
        with httpx.Client(timeout=30) as client:
            resp = client.get(api_url, headers=headers)
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        raise ValueError(
            f"Failed to fetch issue from GitHub API: {e}. "
            "Check GITHUB_TOKEN and issue URL."
        ) from e

    title_val = data.get("title")
    if title_val is not None:
        task = title_val.strip()
    else:
        task = ""
    if not task:
        raise ValueError("GitHub issue has no title")

    return {
        "task": task,
        "github_repo": github_repo,
        "issue_id": issue_id,
        "issue_url": url,
        "repo_path": ".",
    }


def build_repo_context(
    repo_path: str = "",
    github_repo: str = "",
    issue_url: str = "",
    test_command: str = "",
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
    if test_command is not None:
        tc = test_command.strip()
    else:
        tc = ""
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
    rp = repo_path
    if rp is None or rp == "":
        rp = os.getcwd()
    repo = os.path.abspath(rp)
    if not repo or repo == ".":
        repo = detect_repo_path(os.getcwd())

    gh_raw = github_repo
    if gh_raw is not None:
        gh = gh_raw.strip()
    else:
        gh = None
    if not gh:
        gh = detect_github_repo(repo)
    if not gh:
        gh = ""

    iu_raw = issue_url
    if iu_raw is not None:
        url = iu_raw.strip()
    else:
        url = None
    if not url and gh and issue_id:
        url = derive_issue_url(gh, issue_id)
    if not url:
        url = ""

    return {"repo_path": repo, "github_repo": gh, "issue_url": url}


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
