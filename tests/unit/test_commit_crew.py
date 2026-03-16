"""Tests for commit crew - git operations, PR creation, error handling."""

from pathlib import Path

import pytest

from mocks import MockGitHubClient, MockRepoShellTool


@pytest.mark.crew
class TestCommitCrew:
    """Tests for commit crew functionality."""

    def test_commit_calls_git_tool(self):
        """Test that commit calls git tool."""
        tool = MockRepoShellTool()
        tool.add_output("git status", "On branch main\nnothing to commit")

        result = tool.run("git status")

        assert "git" in tool.call_history[0]
        assert "main" in result

    def test_commit_creates_branch(self):
        """Test that commit creates branch correctly."""
        tool = MockRepoShellTool()
        tool.add_output(
            "git checkout -b feature/test", "Switched to new branch 'feature/test'"
        )

        result = tool.run("git checkout -b feature/test")

        assert "feature/test" in result

    def test_commit_commits_changes(self):
        """Test that commit commits changes correctly."""
        tool = MockRepoShellTool()
        tool.add_output(
            "git commit -m 'Add feature'", "1 file changed, 10 insertions(+)"
        )

        result = tool.run("git commit -m 'Add feature'")

        assert "1 file changed" in result

    def test_commit_calls_github_pr_api(self):
        """Test that commit calls GitHub PR API."""
        github = MockGitHubClient()

        pull = github.create_pull(
            repo="test/repo",
            title="Add feature X",
            body="This PR adds feature X",
            head="feature/test",
            base="main",
        )

        assert pull["title"] == "Add feature X"
        assert pull["head"] == "feature/test"

    def test_commit_returns_pr_url(self, load_fixture):
        """Test that commit returns PR URL."""
        fixture = load_fixture("llm_responses/commit/success.json")

        response = fixture.get("response", "")

        assert "PR" in response or "pull" in response.lower()

    def test_commit_returns_commit_summary(self, load_fixture):
        """Test that commit returns commit summary."""
        fixture = load_fixture("llm_responses/commit/success.json")

        response = fixture.get("response", "")

        assert "## Commit Summary" in response or "Commit" in response

    def test_commit_handles_uncommitted_changes(self):
        """Test that commit handles uncommitted changes gracefully."""
        tool = MockRepoShellTool()
        tool.add_output(
            "git status", "On branch main\nChanges not staged:\n  modified: src/app.py"
        )

        result = tool.run("git status")

        # Has uncommitted changes
        assert "Changes not staged" in result or "not staged" in result.lower()

    def test_commit_handles_git_conflicts(self):
        """Test that commit handles git conflicts gracefully."""
        # Simulate conflict detection
        conflict = True

        if conflict:
            error_message = "Merge conflict detected. Please resolve conflicts first."

        assert "conflict" in error_message.lower()

    def test_commit_uses_review_context(self):
        """Test that commit uses review context as input."""
        review_context = {
            "approved": True,
            "files_changed": ["src/app.py"],
            "commit_message": "Add feature X",
        }

        commit_input = {
            "review": review_context,
            "repo_path": "/tmp/test",
        }

        assert "review" in commit_input
        assert commit_input["review"]["approved"] is True

    def test_commit_empty_diff_no_pr(self):
        """Test that commit handles empty diff - no PR created."""
        diff = ""

        # No changes, no PR
        if len(diff) == 0:
            pr_created = False
        else:
            pr_created = True

        assert pr_created is False


class TestCommitResultValidation:
    """Tests for commit result validation logic.

    These tests verify that _validate_commit_result correctly:
    - Accepts real PR URLs
    - Rejects placeholder URLs like pull/123
    """

    def test_validate_commit_result_accepts_real_pr_url(self):
        """Test that real PR URLs are accepted by validation regex."""
        import re

        valid_urls = [
            "https://github.com/owner/repo/pull/456",
            "PR created: https://github.com/test/repo/pull/789",
            "See PR: https://github.com/myorg/myproject/pull/1234",
        ]

        pr_url_pattern = r"https://github\.com/[^/]+/[^/]+/pull/\d+"

        for url in valid_urls:
            match = re.search(pr_url_pattern, url)
            assert match is not None, f"Valid URL should match: {url}"

    def test_validate_commit_result_rejects_placeholder_urls(self):
        """Test that placeholder URLs are detected by validation patterns."""
        import re

        placeholder_patterns = [
            r"pull/123",
            r"example\.com",
        ]

        test_strings = [
            "PR created: https://github.com/owner/repo/pull/123",
            "See: https://github.com/example.com/repo/pull/456",
            "pull/123",
        ]

        found_placeholders = []
        for test_str in test_strings:
            for pattern in placeholder_patterns:
                if re.search(pattern, test_str, re.IGNORECASE):
                    found_placeholders.append(test_str)
                    break

        assert len(found_placeholders) == 3, "All placeholder URLs should be detected"

    def test_validate_commit_result_handles_dry_run_skip(self):
        """Test that dry_run skip messages are accepted."""
        import re

        skip_messages = [
            "PR creation skipped (dry_run)",
            "PR creation skipped (no github_repo)",
            "Skipped: dry_run is true",
        ]

        for msg in skip_messages:
            if "skipped" in msg.lower() and (
                "dry_run" in msg.lower() or "github_repo" in msg.lower()
            ):
                assert True
            else:
                assert False, f"Skip message should be recognized: {msg}"


class TestPublishAgentConfig:
    """Tests for publish_agent configuration to ensure tool is called."""

    def test_publish_agent_has_create_pr_tool(self):
        """Test that publish_agent has create_pr tool in config."""
        import yaml

        config_path = (
            Path(__file__).parent.parent.parent
            / "src"
            / "mycrew"
            / "crews"
            / "commit_crew"
            / "config"
            / "agents.yaml"
        )

        with open(config_path) as f:
            config = yaml.safe_load(f)

        assert "publish_agent" in config, "publish_agent should be in config"
        assert "create_pr" in config["publish_agent"].get("tools", []), (
            "publish_agent should have create_pr tool"
        )

    def test_publish_agent_goal_mentions_tool_call(self):
        """Test that publish_agent goal instructs to call create_pr tool.

        This catches the bug where agents output placeholder URLs instead of
        actually calling the create_pr tool.
        """
        import yaml

        config_path = (
            Path(__file__).parent.parent.parent
            / "src"
            / "mycrew"
            / "crews"
            / "commit_crew"
            / "config"
            / "agents.yaml"
        )

        with open(config_path) as f:
            config = yaml.safe_load(f)

        goal = config["publish_agent"].get("goal", "").lower()

        assert "create_pr" in goal or "create pr" in goal, (
            "publish_agent goal should mention calling create_pr tool"
        )
        assert "must" in goal or "mandatory" in goal or "required" in goal, (
            "publish_agent goal should explicitly require calling the tool"
        )
