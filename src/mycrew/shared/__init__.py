"""Shared modules for both pipelines."""

from mycrew.shared.base import BaseCrew
from mycrew.shared.exceptions import AppError
from mycrew.shared.llm import ModelMappings, get_llm_for_stage, PipelineStage
from mycrew.shared.settings import (
    Settings,
    get_settings,
    PipelineContext,
    set_pipeline_context,
    get_pipeline_context,
)
from mycrew.shared.tools import (
    DirectoryReadTool,
    FileReadTool,
    FileWriterTool,
    WriteFileTool,
)
from mycrew.shared.issues import (
    IssueHandlerFactory,
    IssueContent,
    IssueSource,
    IssueFetchError,
    IssueParseError,
)
from mycrew.shared.pulls import (
    PRHandlerFactory,
    PRContent,
    PRSource,
    PRFetchError,
    PRParseError,
)

__all__ = [
    # Base
    "BaseCrew",
    "AppError",
    # LLM
    "ModelMappings",
    "get_llm_for_stage",
    "PipelineStage",
    # Settings
    "Settings",
    "get_settings",
    "PipelineContext",
    "set_pipeline_context",
    "get_pipeline_context",
    # Tools
    "DirectoryReadTool",
    "FileReadTool",
    "FileWriterTool",
    "WriteFileTool",
    # Issues
    "IssueHandlerFactory",
    "IssueContent",
    "IssueSource",
    "IssueFetchError",
    "IssueParseError",
    # Pulls
    "PRHandlerFactory",
    "PRContent",
    "PRSource",
    "PRFetchError",
    "PRParseError",
]
