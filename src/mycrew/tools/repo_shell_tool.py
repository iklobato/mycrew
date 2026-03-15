"""RepoShellTool: run shell commands in a repo with safety checks."""

import logging
import os
import re
import subprocess
import time
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
            "(ls, find, cat, head, grep). For tests use project's test runner. "
            "grep: use 'grep PATTERN file' or 'cmd | grep PATTERN'; "
            "never pass '>' as an option—use 'grep -- \"->\" file' for patterns with dashes. "
            "gh: issue list accepts --state=open|closed|all only; for merged PRs use 'gh pr list --state=merged'."
        ),
    )


class RepoShellTool(BaseTool):
    """Tool to run shell commands in a repository with safety checks."""

    name: str = "Repo Shell Tool"
    description: str = (
        "Run shell commands in the repository. Use relative paths. "
        "Examples: 'ls -la', 'cat path/to/file', 'grep -r \"pattern\" src/', 'pytest', 'npm test'. "
        "Python: use uvx for linters (uvx ruff check --fix ., uvx black .) when ruff/black not on PATH. "
        "grep: use 'grep PATTERN file' or 'cmd | grep PATTERN'; "
        "for patterns with '-' or '>' use 'grep -e \"pattern\" file' or 'grep -- \"->\" file'. "
        "gh: issue list --state= accepts only open|closed|all; for merged PRs use 'gh pr list --state=merged'. "
        "Commands run with cwd=repo_path. Output is limited to 16KB to prevent memory exhaustion. "
        'For large repositories, use focused searches: \'grep -r "pattern" src --include="*.py" --exclude-dir=node_modules --exclude-dir=.git | head -100\'. '
        "Dangerous commands (rm -rf /, mkfs, etc.) are blocked."
    )
    args_schema: Type[BaseModel] = RepoShellToolInput

    repo_path: str = ""

    def _run(self, command: str) -> str:
        """Execute a shell command in the repo with safety checks."""
        logger.info(f"SHELL: repo_path={self.repo_path}, command={command[:100]}")

        if not self.repo_path:
            return "Error: repo_path is not set."

        repo_path = os.path.abspath(self.repo_path)
        logger.info(f"SHELL: working directory={repo_path}")

        if not os.path.isdir(repo_path):
            return f"Error: repo_path does not exist or is not a directory: {repo_path}"

        command = command.strip()
        if not command:
            return "Error: empty command."

        # Block dangerous patterns
        cmd_lower = command.lower()
        for pattern in _DANGEROUS_PATTERNS:
            if re.search(pattern, cmd_lower, re.IGNORECASE):
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
                except (ValueError, OSError):
                    return f"Error: path outside repo is not allowed: {part_clean}"

        try:
            # Use Popen with streaming to limit memory usage
            process = subprocess.Popen(
                command,
                shell=True,
                cwd=repo_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,  # Line buffered
            )

            # Aggressive memory reduction: 16KB max output, 200 lines max
            MAX_OUTPUT_SIZE = 16384  # Reduced from 32KB to 16KB
            stdout_chunks = []
            stderr_chunks = []
            total_size = 0
            truncated = False
            line_count = 0
            MAX_LINES = 200  # Reduced from 500 to 200 lines

            # Read output with timeout
            import select

            start_time = time.time()
            TIMEOUT = 90  # Reduced timeout

            while process.poll() is None:
                # Check timeout
                if time.time() - start_time > TIMEOUT:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                    raise subprocess.TimeoutExpired(command, TIMEOUT)

                # Check for output
                ready, _, _ = select.select(
                    [process.stdout, process.stderr],
                    [],
                    [],
                    0.5,  # Reduced poll interval
                )

                for stream in ready:
                    if stream is process.stdout:
                        chunk = stream.readline()
                        if chunk:
                            line_count += 1
                            if (
                                line_count > MAX_LINES
                                or total_size + len(chunk) > MAX_OUTPUT_SIZE
                            ):
                                truncated = True
                                break
                            stdout_chunks.append(chunk)
                            total_size += len(chunk)
                    elif stream is process.stderr:
                        chunk = stream.readline()
                        if chunk:
                            if total_size + len(chunk) > MAX_OUTPUT_SIZE:
                                truncated = True
                                break
                            stderr_chunks.append(chunk)
                            total_size += len(chunk)

                if truncated:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                    break

            # Get any remaining output if process finished
            if not truncated:
                stdout_remain, stderr_remain = process.communicate(timeout=5)
                if stdout_remain:
                    lines = stdout_remain.split("\n")
                    for line in lines:
                        if line_count >= MAX_LINES:
                            truncated = True
                            break
                        if total_size + len(line) + 1 > MAX_OUTPUT_SIZE:
                            truncated = True
                            break
                        stdout_chunks.append(line + "\n")
                        total_size += len(line) + 1
                        line_count += 1
                if stderr_remain and not truncated:
                    if total_size + len(stderr_remain) > MAX_OUTPUT_SIZE:
                        truncated = True
                        stderr_remain = stderr_remain[: MAX_OUTPUT_SIZE - total_size]
                    stderr_chunks.append(stderr_remain)
                    total_size += len(stderr_remain)

            returncode = process.returncode or 0

            # Combine output efficiently
            all_lines = stdout_chunks + stderr_chunks

            # Apply smart sampling for very large outputs (first 50, middle 50, last 50)
            if len(all_lines) > 150:  # If we have more than 150 lines, apply sampling
                sampled_lines = []
                total_lines = len(all_lines)

                # First 50 lines
                sampled_lines.extend(all_lines[:50])

                # Middle 50 lines (centered around midpoint)
                if total_lines > 100:
                    mid_start = max(50, total_lines // 2 - 25)
                    mid_end = min(total_lines - 50, total_lines // 2 + 25)
                    sampled_lines.append(
                        f"\n... (skipped {mid_start - 50} lines) ...\n"
                    )
                    sampled_lines.extend(all_lines[mid_start:mid_end])

                # Last 50 lines
                if total_lines > 100:
                    sampled_lines.append(
                        f"\n... (skipped {total_lines - 100} lines) ...\n"
                    )
                sampled_lines.extend(all_lines[-50:])

                output = "".join(sampled_lines)
                truncated = True  # Mark as truncated since we sampled
            else:
                output = "".join(all_lines)

            output_len = len(output)

            # Add truncation notice if needed
            if truncated:
                if len(all_lines) > 150:
                    truncation_msg = f"\n... (output sampled: first 50 / middle 50 / last 50 of {len(all_lines)} total lines, {MAX_OUTPUT_SIZE // 1024}KB limit)"
                else:
                    truncation_msg = f"\n... (output truncated at {MAX_OUTPUT_SIZE // 1024}KB, {MAX_LINES} lines limit)"

                if output_len + len(truncation_msg) > MAX_OUTPUT_SIZE:
                    output = (
                        output[: MAX_OUTPUT_SIZE - len(truncation_msg)] + truncation_msg
                    )
                else:
                    output = output + truncation_msg
                output_len = len(output)

            # Log completion with output preview
            logger.info(
                "│ Exit code: %d, Output: %d chars, %d lines%s",
                returncode,
                output_len,
                line_count,
                " (truncated)" if truncated else "",
            )

            # Show preview of output (first 2 lines only to save memory)
            if output_len > 0:
                lines = output.split("\n")
                if len(lines) > 2:
                    preview = " | ".join(
                        line.strip() for line in lines[:2] if line.strip()
                    )
                    preview += f" ... ({len(lines) - 2} more lines)"
                else:
                    preview = " | ".join(line.strip() for line in lines if line.strip())

                # Limit preview length
                if len(preview) > 200:
                    preview = preview[:197] + "..."

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
