"""Repo-scoped file writer: writes files inside the target repository."""

import logging
import os
from typing import Any, Type

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
    args_schema: Type[BaseModel] = RepoFileWriterToolInput

    repo_path: str = ""

    def _run(
        self,
        filename: str,
        content: str,
        overwrite: bool | str = False,
        directory: str | None = None,
    ) -> str:
        logger.info(
            f"FILE WRITER: repo_path={self.repo_path}, filename={filename}, directory={directory}"
        )

        if not self.repo_path:
            return "Error: repo_path is not set."

        repo = os.path.abspath(self.repo_path)
        logger.info(f"FILE WRITER: absolute repo_path={repo}")

        if not os.path.isdir(repo):
            return f"Error: repo_path does not exist: {repo}"

        base = repo
        if directory and directory.strip():
            sub = directory.strip().lstrip("/")
            if sub and sub != ".":
                base = os.path.join(repo, sub)
                base = os.path.normpath(base)
                if not base.startswith(repo):
                    return f"Error: directory must be inside repo: {directory}"

        filepath = os.path.normpath(os.path.join(base, filename.lstrip("/")))
        if not os.path.abspath(filepath).startswith(os.path.abspath(repo)):
            return f"Error: path escapes repo: {filename}"

        try:
            overwrite_flag = _strtobool(overwrite)

            if not overwrite_flag and os.path.exists(filepath):
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
            logger.info(f"Wrote {rel}")
            return f"Wrote {rel}"

        except FileExistsError:
            return f"File {filepath} already exists. Set overwrite=true to modify."
        except Exception as e:
            logger.error(f"Failed to write file: {e}")
            return f"Error writing file: {e}"
