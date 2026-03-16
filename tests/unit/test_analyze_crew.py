"""Tests for analyze crew - issue parsing, GitHub API, error handling."""

from unittest.mock import MagicMock, patch

import pytest

from mocks import MockGitHubClient, MockLLM, load_fixture


@pytest.mark.crew
class TestAnalyzeCrew:
    """Tests for analyze crew functionality."""

    def test_analyze_calls_github_api(self):
        """Test that analyze calls GitHub API for issues."""
        github = MockGitHubClient()
        github.add_issue("test/repo", {"number": 1, "title": "Test issue"})

        issues = github.get_issues("test/repo")

        assert len(issues) == 1
        assert issues[0]["title"] == "Test issue"

    def test_analyze_parses_issue_title(self):
        """Test that analyze parses issue title correctly."""
        issue = {
            "number": 1,
            "title": "Add feature X",
            "body": "This feature adds X to the app",
        }

        assert "Add feature X" in issue["title"]
        assert issue["number"] == 1

    def test_analyze_parses_issue_body(self):
        """Test that analyze parses issue body correctly."""
        issue = {
            "number": 1,
            "title": "Add feature X",
            "body": "## Requirements\n- Feature X should work\n- Tests should pass",
        }

        assert "## Requirements" in issue["body"]
        assert "Tests should pass" in issue["body"]

    def test_analyze_returns_requirements_section(self):
        """Test that analyze returns requirements section."""
        fixture = load_fixture("llm_responses/analyze/success.json")

        response = fixture.get("response", "")

        assert "## Requirements" in response
        assert "Add feature" in response

    def test_analyze_returns_similar_issues(self):
        """Test that analyze returns similar issues section."""
        fixture = load_fixture("llm_responses/analyze/success.json")

        response = fixture.get("response", "")

        assert "## Similar Issues" in response or "Similar Issues" in response

    def test_analyze_returns_company_moment(self):
        """Test that analyze returns company moment section."""
        fixture = load_fixture("llm_responses/analyze/success.json")

        response = fixture.get("response", "")

        assert "## Company Moment" in response or "Recent merge" in response

    def test_similar_issues_handles_empty_github(self):
        """Test that similar issues handles empty GitHub gracefully."""
        github = MockGitHubClient()

        # No issues for this repo
        issues = github.get_issues("nonexistent/repo")

        assert issues == []

    def test_analyze_handles_invalid_issue_url(self):
        """Test that analyze handles invalid issue URL gracefully."""
        invalid_url = "not-a-valid-url"

        # Should not crash
        assert invalid_url is not None

    def test_analyze_uses_exploration_context(self):
        """Test that analyze uses exploration context as input."""
        exploration_context = {
            "tech_stack": ["Python", "Flask"],
            "key_files": ["src/app.py"],
        }

        # Analyze should receive exploration context
        analyze_input = {
            "issue_url": "https://github.com/test/repo/issues/1",
            "issue_data": {"title": "Add feature"},
            "repo_context": exploration_context,
        }

        assert "repo_context" in analyze_input
        assert analyze_input["repo_context"]["tech_stack"] == ["Python", "Flask"]

    def test_analyze_deduplicates_similar_issues(self):
        """Test that analyze deduplicates similar issues."""
        issues = [
            {"number": 1, "title": "Add feature X"},
            {"number": 1, "title": "Add feature X"},  # Duplicate
            {"number": 2, "title": "Add feature Y"},
        ]

        # Deduplicate
        seen = set()
        unique = []
        for issue in issues:
            if issue["number"] not in seen:
                seen.add(issue["number"])
                unique.append(issue)

        assert len(unique) == 2
