"""RepoShellTool: run shell commands in a repo with safety checks."""

import logging
import os
import re
import subprocess
from typing import Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# Dangerous patterns to block
_DANGEROUS_PATTERNS = [
    r"rm\s+-rf\s+/",
    r"rm\s+-rf\s+/\*",
    r":\s*\(\s*\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;",
    r"mkfs",
    r"dd\s+if=",
    r">\s*/dev/sd",
    r">\s*/dev/hd",
    r"chmod\s+-R\s+777\s+/",
    r"format\s+[a-z]:",
    r"del\s+/[sf]\s+",
    r"wmic\s+disk",
    r"shutdown\s+-",
    r"reboot",
    r"init\s+[06]",
    r"systemctl\s+(poweroff|reboot)",
    r"\|\s*bash\s*$",
    r"\|\s*sh\s*$",
]


class RepoShellToolInput(BaseModel):
    """Input schema for RepoShellTool."""

    command: str = Field(
        ...,
        description=(
            "Single shell command. Use relative paths. Read-only preferred "
            "(ls, find, cat, head, grep). For tests use project's test runner."
        ),
    )


class RepoShellTool(BaseTool):
    """Tool to run shell commands in a repository with safety checks."""

    name: str = "Repo Shell Tool"
    description: str = (
        "Run shell commands in the repository. Use relative paths. "
        "Examples: 'ls -la', 'cat path/to/file', 'pytest', 'npm test'. "
        "Commands run with cwd=repo_path. Output is truncated at 8000 chars. "
        "Dangerous commands (rm -rf /, mkfs, etc.) are blocked."
    )
    args_schema: Type[BaseModel] = RepoShellToolInput

    repo_path: str = ""

    def _run(self, command: str) -> str:
        """Execute a shell command in the repo with safety checks."""
        logger.info("┌─[ RepoShellTool EXECUTE ]─ Command: %s", command)
        if not self.repo_path:
            logger.warning("RepoShellTool: repo_path not set")
            return "Error: repo_path is not set."

        repo_path = os.path.abspath(self.repo_path)
        if not os.path.isdir(repo_path):
            logger.warning("RepoShellTool: repo_path not found: %s", repo_path)
            return f"Error: repo_path does not exist or is not a directory: {repo_path}"

        command = command.strip()
        if not command:
            return "Error: empty command."

        # Block dangerous patterns
        cmd_lower = command.lower()
        for pattern in _DANGEROUS_PATTERNS:
            if re.search(pattern, cmd_lower, re.IGNORECASE):
                logger.warning(
                    "RepoShellTool: blocked dangerous command (pattern=%s)", pattern
                )
                return f"Error: command blocked for safety (pattern: {pattern})"

        # Reject absolute paths escaping repo_path
        repo_norm = os.path.normpath(repo_path)
        for part in command.split():
            part_clean = part.strip("'\"").rstrip("/")
            is_abs = part_clean.startswith("/") or (
                len(part_clean) >= 2 and part_clean[1] == ":"
            )
            if is_abs:
                try:
                    resolved = os.path.normpath(os.path.abspath(part_clean))
                    common = os.path.commonpath([resolved, repo_norm])
                    if common != repo_norm:
                        return f"Error: absolute path outside repo is not allowed: {part_clean}"
                except (ValueError, OSError) as e:
                    logger.error(
                        "RepoShellTool: path validation failed for %s: %s",
                        part_clean,
                        e,
                        exc_info=True,
                    )
                    return f"Error: path outside repo is not allowed: {part_clean}"

        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=repo_path,
                timeout=120,
                capture_output=True,
                text=True,
            )
            output = (result.stdout or "") + (result.stderr or "")
            output_len = len(output)

            # Truncate if too long
            if output_len > 8000:
                output = output[:8000] + "\n... (truncated)"

            # Log completion with output preview
            logger.info(
                "│ Exit code: %d, Output length: %d chars",
                result.returncode,
                output_len,
            )

            # Show preview of output (first 3 lines as single line)
            if output_len > 0:
                lines = output.split("\n")
                if len(lines) > 3:
                    # Join first 3 lines, replace newlines with spaces for single-line display
                    preview = " | ".join(
                        line.strip() for line in lines[:3] if line.strip()
                    )
                    preview += f" ... ({len(lines) - 3} more lines)"
                else:
                    # Join all lines, replace newlines with spaces for single-line display
                    preview = " | ".join(line.strip() for line in lines if line.strip())

                # Limit preview length
                if len(preview) > 300:
                    preview = preview[:297] + "..."

                logger.info("│ Output preview: %s", preview)

            logger.info("└─[ RepoShellTool COMPLETE ]─")
            return output

        except subprocess.TimeoutExpired:
            logger.error(
                "RepoShellTool: command timed out: %r", command[:80], exc_info=True
            )
            return "Error: command timed out after 120 seconds."
        except Exception as e:
            logger.error("RepoShellTool: %s", e, exc_info=True)
            return f"Error: {e}"
