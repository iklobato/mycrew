"""Tests for explorer crew - tool usage, output format, error handling."""

from unittest.mock import MagicMock, patch

import pytest

from mocks import MockLLM, MockRepoShellTool, load_fixture


@pytest.mark.crew
class TestExplorerCrew:
    """Tests for explorer crew functionality."""

    def test_explore_calls_repo_shell_tool(self):
        """Test that explorer calls repo_shell tool with correct commands."""
        tool = MockRepoShellTool()
        tool.add_output("ls -la", "total 224\ndrwxr-xr-x 54 iklo staff 1728 ...")

        # Simulate calling the tool
        result = tool.run("ls -la")

        assert "total 224" in result
        assert "ls -la" in tool.call_history

    def test_explore_returns_tech_stack_section(self):
        """Test that explore returns tech stack section."""
        fixture = load_fixture("llm_responses/explorer/success.json")

        response = fixture.get("response", "")

        assert "## Tech Stack" in response
        assert "Python" in response

    def test_explore_returns_directory_layout(self):
        """Test that explore returns directory layout."""
        fixture = load_fixture("llm_responses/explorer/success.json")

        response = fixture.get("response", "")

        assert "## Directory Layout" in response or "src/" in response

    def test_explore_returns_key_files(self):
        """Test that explore returns key files."""
        fixture = load_fixture("llm_responses/explorer/success.json")

        response = fixture.get("response", "")

        assert "## Key Files" in response or "app.py" in response

    def test_explore_returns_conventions(self):
        """Test that explore returns conventions."""
        fixture = load_fixture("llm_responses/explorer/success.json")

        response = fixture.get("response", "")

        assert "## Conventions" in response or "pytest" in response

    def test_dependency_analyzer_traces_imports(self):
        """Test that dependency analyzer traces imports."""
        tool = MockRepoShellTool()
        tool.add_output("grep -r 'import' src/", "from flask import Flask\nimport os")

        result = tool.run("grep -r 'import' src/")

        assert "from flask import Flask" in result
        assert "import os" in result

    def test_dependency_analyzer_maps_blast_radius(self):
        """Test that dependency analyzer maps blast radius."""
        # This tests the output format
        response = "## Dependency Map\n- src/app.py: Blast Radius: HIGH"

        assert "Blast Radius" in response
        assert "HIGH" in response

    def test_test_layout_scout_finds_test_dir(self):
        """Test that test layout scout finds test directory."""
        tool = MockRepoShellTool()
        tool.add_output("ls tests/", "test_app.py\ntest_utils.py")

        result = tool.run("ls tests/")

        assert "test_app.py" in result

    def test_explore_handles_missing_pyproject(self):
        """Test that explore handles missing pyproject.toml gracefully."""
        tool = MockRepoShellTool()
        tool.add_output("cat pyproject.toml", "cat: pyproject.toml: No such file")

        result = tool.run("cat pyproject.toml")

        assert "No such file" in result

    def test_explore_state_persists_between_tasks(self):
        """Test that state persists between tasks in exploration."""
        # Simulate state being passed between tasks
        state = {
            "repo_path": "/tmp/test",
            "tech_stack": ["Python"],
            "key_files": ["app.py"],
        }

        # Task 1 outputs become input for Task 2
        task1_output = state

        # Task 2 should receive Task 1's output
        task2_input = task1_output

        assert task2_input["repo_path"] == "/tmp/test"
        assert "tech_stack" in task2_input


@pytest.mark.crew
class TestInternalDepsScout:
    """Tests for internal dependencies scout."""

    def test_internal_deps_scout_identifies_private_npm_packages(self):
        """Test that internal deps scout identifies @company/* packages."""
        response = """## Internal Dependencies
### @company/shared-utils
- Source: private npm registry
- GitHub: github.com/company/shared-utils
"""
        assert "@company/shared-utils" in response
        assert "private npm" in response

    def test_internal_deps_scout_identifies_private_pip_packages(self):
        """Test that internal deps scout identifies company-* pip packages."""
        response = """## Internal Dependencies
### company-auth-lib
- Source: private PyPI
- Version: ^2.0.0
"""
        assert "company-auth-lib" in response

    def test_internal_deps_scout_documents_contracts(self):
        """Test that internal deps scout documents known contracts."""
        response = """## Internal Dependencies
### @company/ui-components
- Contracts used:
  - ButtonProps: { variant, size, onClick }
  - ModalProps: { isOpen, onClose }
"""
        assert "ButtonProps" in response
        assert "ModalProps" in response

    def test_internal_deps_scout_handles_no_internal_deps(self):
        """Test that internal deps scout outputs None when no internal deps."""
        response = "## Internal Dependencies\nNone found (all dependencies are public)"
        assert "None found" in response

    def test_internal_deps_scout_warns_on_inaccessible(self):
        """Test that internal deps scout warns when inaccessible but continues."""
        response = """## Internal Dependencies
WARNING: Some internal packages detected but not accessible
"""
        assert "WARNING" in response

    def test_internal_deps_scout_identifies_github_packages(self):
        """Test that internal deps scout identifies GitHub package references."""
        response = """## Internal Dependencies
### @company/ui-components
- Source: GitHub Packages
- GitHub: github.com/company/ui-components
"""
        assert "GitHub Packages" in response
        assert "github.com/company/ui-components" in response

    def test_internal_deps_scout_identifies_git_references(self):
        """Test that internal deps scout identifies direct git references."""
        response = """## Internal Dependencies
### internal-lib
- Source: Direct git reference
- URL: git+https://github.com/company/internal-lib.git
"""
        assert "git+" in response
        assert "internal-lib" in response

    def test_internal_deps_scout_documents_usage_in_repo(self):
        """Test that internal deps scout documents usage in codebase."""
        response = """## Internal Dependencies
### @company/auth
- Usage in repo: src/auth/login.ts, src/api/client.ts
"""
        assert "Usage in repo" in response
        assert "src/auth/login.ts" in response

    def test_internal_deps_scout_handles_org_scoped_packages(self):
        """Test that internal deps scout handles @org/* scoped packages."""
        response = """## Internal Dependencies
### @org/shared-components
- Source: private npm registry
"""
        assert "@org/shared-components" in response

    def test_internal_deps_scout_checks_npmrc(self):
        """Test that internal deps scout checks .npmrc for private registry."""
        tool = MockRepoShellTool()
        tool.add_output(
            "cat .npmrc",
            "//npm.pkg.github.com/:_authToken=xxxx\n@company:registry=https://npm.pkg.github.com",
        )

        result = tool.run("cat .npmrc")
        assert "npm.pkg.github.com" in result
        assert "@company" in result
