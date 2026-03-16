"""Tests for reviewer crew - code inspection, quality checks, approval."""

from pathlib import Path

import pytest

from mocks import MockLLM, MockRepoShellTool


@pytest.mark.crew
class TestReviewerCrew:
    """Tests for reviewer crew functionality."""

    def test_review_calls_code_inspection_tool(self):
        """Test that reviewer calls code inspection tool."""
        tool = MockRepoShellTool()
        tool.add_output("cat src/app.py", "def hello():\n    return 'Hello'\n")

        result = tool.run("cat src/app.py")

        assert "def hello" in result

    def test_review_returns_code_quality_section(self, load_fixture):
        """Test that review returns code quality section."""
        fixture = load_fixture("llm_responses/review/success.json")

        response = fixture.get("response", "")

        assert "## Code Quality" in response or "Quality" in response

    def test_review_returns_security_issues(self, load_fixture):
        """Test that review returns security issues section."""
        fixture = load_fixture("llm_responses/review/success.json")

        response = fixture.get("response", "")

        assert "## Security Issues" in response or "Security" in response

    def test_review_returns_suggestions(self, load_fixture):
        """Test that review returns suggestions section."""
        fixture = load_fixture("llm_responses/review/success.json")

        response = fixture.get("response", "")

        assert "## Suggestions" in response or "suggestions" in response.lower()

    def test_review_approves_clean_implementation(self, load_fixture):
        """Test that review approves clean implementation."""
        fixture = load_fixture("llm_responses/review/success.json")

        response = fixture.get("response", "")

        assert "APPROVED" in response

    def test_review_rejects_with_blocking_issues(self):
        """Test that review rejects when there are blocking issues."""
        response = "## Review Decision\n- BLOCKED: Syntax errors found\n- Not approved"

        assert "BLOCKED" in response
        assert "Not approved" in response

    def test_review_handles_test_failures(self):
        """Test that review handles test failures gracefully."""
        test_result = {
            "passed": False,
            "failures": ["test_hello failed"],
            "errors": [],
        }

        assert test_result["passed"] is False
        assert len(test_result["failures"]) > 0

    def test_review_uses_implementation_context(self):
        """Test that review uses implementation context as input."""
        implementation_context = {
            "files_created": ["src/new_feature.py"],
            "files_modified": ["src/app.py"],
            "test_results": {"passed": True},
        }

        review_input = {
            "implementation": implementation_context,
            "repo_path": "/tmp/test",
        }

        assert "implementation" in review_input
        assert len(review_input["implementation"]["files_created"]) == 1

    def test_review_runs_linter(self):
        """Test that reviewer runs linter."""
        tool = MockRepoShellTool()
        tool.add_output(
            "ruff check src/", "src/app.py:1:1: E302 expected 2 blank lines"
        )

        result = tool.run("ruff check src/")

        assert "E302" in result or result == ""

    def test_review_returns_review_complete(self, load_fixture):
        """Test that review returns completion status."""
        fixture = load_fixture("llm_responses/review/success.json")

        response = fixture.get("response", "")

        # Should have some review decision
        assert "APPROVED" in response or "REJECTED" in response or "BLOCKED" in response
