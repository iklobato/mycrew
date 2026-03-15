"""No-op tool for disabled optional tools (e.g. Serper, GithubSearch when not configured)."""

from typing import Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class NoOpToolInput(BaseModel):
    """No-op tool accepts any query but does nothing."""

    query: str = Field(default="", description="Ignored; tool is disabled.")


class NoOpTool(BaseTool):
    """Tool that does nothing. Used when optional tools (Serper, GithubSearch) are disabled."""

    name: str = "NoOpTool"
    description: str = "This tool is disabled. Do not use it."
    args_schema: Type[BaseModel] = NoOpToolInput

    def _run(self, query: str = "") -> str:
        return "Tool disabled."
