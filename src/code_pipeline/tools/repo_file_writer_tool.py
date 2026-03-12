"""Repo-scoped file writer: writes files inside the target repository."""

import logging
import os
from typing import Any

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


def _strtobool(val: Any) -> bool:
    if isinstance(val, bool):
        return val
    s = str(val).lower()
    if s in ("y", "yes", "t", "true", "on", "1"):
        return True
    if s in ("n", "no", "f", "false", "off", "0"):
        return False
    return False


class RepoFileWriterToolInput(BaseModel):
    """Input schema for RepoFileWriterTool."""

    filename: str = Field(
        ..., description="Relative path to the file (e.g. src/module.py)"
    )
    content: str = Field(..., description="Full content to write")
    overwrite: bool | str = Field(
        default=False,
        description="If true, overwrite existing file. Required when modifying existing files.",
    )
    directory: str | None = Field(
        default=None,
        description="Optional subdirectory inside repo (e.g. src/). Omit or use . for repo root.",
    )


class RepoFileWriterTool(BaseTool):
    """Write files inside the target repository. All paths are relative to repo_path."""

    name: str = "Repo File Writer Tool"
    description: str = (
        "Write content to a file in the repository. Accepts filename (relative path), "
        "content, and overwrite (true to modify existing). Paths are relative to repo root. "
        "Use overwrite=true when modifying existing files."
    )
    args_schema: type[BaseModel] = RepoFileWriterToolInput

    repo_path: str = ""

    def _run(
        self,
        filename: str,
        content: str,
        overwrite: bool | str = False,
        directory: str | None = None,
        **kwargs: Any,
    ) -> str:
        if _strtobool(overwrite):
            action = "modifying"
        else:
            action = "creating"
        logger.info("┌─[ RepoFileWriterTool EXECUTE ]─")
        logger.info("│ Input:")
        logger.info("│   Action: %s", action)
        logger.info("│   Filename: %s", filename)
        if directory:
            dir_display = directory
        else:
            dir_display = "(repo root)"
        logger.info("│   Directory: %s", dir_display)
        logger.info("│   Overwrite: %s", overwrite)
        logger.info("│   Content length: %d chars", len(content))
        if len(content) > 100:
            content_preview = content[:100] + "..."
        else:
            content_preview = content
        logger.info("│   Content preview: %s", content_preview)

        if not self.repo_path:
            logger.warning("RepoFileWriterTool: repo_path not set")
            logger.info("└─[ RepoFileWriterTool FAILED ]─ repo_path not set")
            return "Error: repo_path is not set."

        repo = os.path.abspath(self.repo_path)
        if not os.path.isdir(repo):
            logger.info("└─[ RepoFileWriterTool FAILED ]─ repo_path does not exist")
            return f"Error: repo_path does not exist: {repo}"

        # Calculate filepath first (outside try block for exception handler)
        base = repo
        if directory and directory.strip():
            sub = directory.strip().lstrip("/")
            if sub and sub != ".":
                base = os.path.join(repo, sub)
                base = os.path.normpath(base)
                if not base.startswith(repo):
                    logger.info(
                        "└─[ RepoFileWriterTool FAILED ]─ directory escapes repo"
                    )
                    return f"Error: directory must be inside repo: {directory}"

        filepath = os.path.normpath(os.path.join(base, filename.lstrip("/")))
        if not os.path.abspath(filepath).startswith(os.path.abspath(repo)):
            logger.info("└─[ RepoFileWriterTool FAILED ]─ path escapes repo")
            return f"Error: path escapes repo: {filename}"

        try:
            overwrite_flag = _strtobool(overwrite)

            if not overwrite_flag and os.path.exists(filepath):
                logger.info("└─[ RepoFileWriterTool FAILED ]─ file already exists")
                return f"File {filepath} already exists. Set overwrite=true to modify."

            parent = os.path.dirname(filepath)
            if parent and not os.path.exists(parent):
                os.makedirs(parent, exist_ok=True)

            if overwrite_flag:
                mode = "w"
            else:
                mode = "x"
            with open(filepath, mode) as f:
                f.write(content)

            rel = os.path.relpath(filepath, repo)
            logger.info("│ Output: Wrote %s", rel)
            logger.info("│ File size: %d bytes", len(content))
            logger.info("└─[ RepoFileWriterTool COMPLETE ]─")
            return f"Wrote {rel}"

        except FileExistsError:
            logger.info("└─[ RepoFileWriterTool FAILED ]─ file already exists")
            return f"File {filepath} already exists. Set overwrite=true to modify."
        except Exception as e:
            logger.error("RepoFileWriterTool failed: %s", e, exc_info=True)
            logger.info("└─[ RepoFileWriterTool FAILED ]─")
            return f"Error writing file: {e}"
