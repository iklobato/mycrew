"""Tool behavior tests - verify tools are available and configured correctly.

These tests verify that:
- Tools can be imported
- Tool classes exist
- Tools have required methods
"""

import os

os.environ["CREWAI_TELEMETRY_DISABLED"] = "true"
os.environ["OTEL_SDK_DISABLED"] = "true"

import pytest


@pytest.mark.unit
class TestToolImports:
    """Test that tools can be imported."""

    def test_import_repo_shell_tool(self):
        """RepoShellTool should be importable."""
        from mycrew.tools.repo_shell_tool import RepoShellTool

        assert RepoShellTool is not None

    def test_import_repo_file_writer_tool(self):
        """RepoFileWriterTool should be importable."""
        from mycrew.tools.repo_file_writer_tool import RepoFileWriterTool

        assert RepoFileWriterTool is not None

    def test_import_github_search_tool(self):
        """GitHubSearchTool should be importable."""
        from mycrew.tools.github_api_search_tool import GitHubAPISearchTool

        assert GitHubAPISearchTool is not None

    def test_import_create_pr_tool(self):
        """CreatePRTool should be importable."""
        from mycrew.tools.create_pr_tool import CreatePRTool

        assert CreatePRTool is not None


@pytest.mark.unit
class TestToolClasses:
    """Test tool classes have required attributes."""

    def test_repo_shell_tool_has_run_method(self):
        """RepoShellTool should have _run method."""
        from mycrew.tools.repo_shell_tool import RepoShellTool

        assert hasattr(RepoShellTool, "_run")

    def test_repo_file_writer_tool_has_run_method(self):
        """RepoFileWriterTool should have run method."""
        from mycrew.tools.repo_file_writer_tool import RepoFileWriterTool

        assert hasattr(RepoFileWriterTool, "run")

    def test_repo_shell_tool_has_args_schema(self):
        """RepoShellTool should have args_schema."""
        from mycrew.tools.repo_shell_tool import RepoShellTool

        tool = RepoShellTool(repo_path="/tmp/test")
        assert hasattr(tool, "args_schema")


@pytest.mark.unit
class TestToolFactory:
    """Test tool factory functions."""

    def test_factory_import(self):
        """Tool factory should be importable."""
        from mycrew.tools.factory import (
            get_code_interpreter_tool,
            get_github_search_tool,
            get_scrape_website_tool,
            get_serper_tool,
        )

        assert get_code_interpreter_tool is not None
        assert get_github_search_tool is not None
        assert get_scrape_website_tool is not None
        assert get_serper_tool is not None


@pytest.mark.unit
class TestBaseCrewTools:
    """Test base crew provides tools."""

    def test_base_crew_import(self):
        """PipelineCrewBase should be importable."""
        from mycrew.crews.base import PipelineCrewBase

        assert PipelineCrewBase is not None

    def test_base_crew_has_repo_shell_method(self):
        """PipelineCrewBase should have repo_shell method."""
        from mycrew.crews.base import PipelineCrewBase

        assert hasattr(PipelineCrewBase, "repo_shell")

    def test_base_crew_has_github_search_method(self):
        """PipelineCrewBase should have github_search method."""
        from mycrew.crews.base import PipelineCrewBase

        assert hasattr(PipelineCrewBase, "github_search")

    def test_base_crew_has_file_writer_method(self):
        """PipelineCrewBase should have repo_file_writer method."""
        from mycrew.crews.base import PipelineCrewBase

        assert hasattr(PipelineCrewBase, "repo_file_writer")
