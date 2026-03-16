"""Shared pytest fixtures and configuration."""

from pathlib import Path

import pytest

# Import mocks for reuse
from mocks import (
    MockCrew,
    MockFlowState,
    MockGitHubClient,
    MockLLM,
    MockRepoFileWriterTool,
    MockRepoShellTool,
    create_test_repo,
    load_fixture_dir,
)


# ============================================================================
# Configuration
# ============================================================================

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "integration: marks tests requiring running server and/or external APIs (deselect with '-m \"not integration\"')",
    )
    config.addinivalue_line(
        "markers",
        "crew: marks tests for crew functionality",
    )
    config.addinivalue_line(
        "markers",
        "pipeline: marks tests for pipeline flow",
    )
    config.addinivalue_line(
        "markers",
        "unit: marks tests that don't require external calls",
    )


# ============================================================================
# Environment Fixtures
# ============================================================================


@pytest.fixture(autouse=True)
def webhook_env(monkeypatch):
    """Set default webhook-related env vars for tests."""
    monkeypatch.setenv("DEFAULT_DRY_RUN", "false")
    monkeypatch.setenv("DEFAULT_BRANCH", "main")
    monkeypatch.setenv("TESTING", "1")


@pytest.fixture
def github_token(monkeypatch):
    """Set GITHUB_TOKEN for tests that need it."""
    monkeypatch.setenv("GITHUB_TOKEN", "test-token")


@pytest.fixture
def openrouter_api_key(monkeypatch):
    """Set OPENROUTER_API_KEY for tests that need it."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")


# ============================================================================
# Mock Fixtures
# ============================================================================


@pytest.fixture
def mock_llm():
    """Create a mock LLM."""
    return MockLLM()


@pytest.fixture
def mock_llm_with_responses():
    """Create a mock LLM with predefined responses."""
    return MockLLM(
        {
            "__default__": '{"result": "Mock response"}',
        }
    )


@pytest.fixture
def mock_shell_tool():
    """Create a mock shell tool."""
    return MockRepoShellTool()


@pytest.fixture
def mock_file_writer_tool():
    """Create a mock file writer tool."""
    return MockRepoFileWriterTool()


@pytest.fixture
def mock_github_client():
    """Create a mock GitHub client."""
    return MockGitHubClient()


@pytest.fixture
def mock_crew():
    """Create a mock crew."""
    return MockCrew()


@pytest.fixture
def mock_flow_state():
    """Create a mock flow state."""
    return MockFlowState(
        id="test-id",
        issue_url="https://github.com/test/repo/issues/1",
        repo_path="/tmp/test",
        repo_root="/tmp/test",
    )


# ============================================================================
# Mock Factories
# ============================================================================


@pytest.fixture
def mock_llm_factory():
    """Factory to create mock LLM with custom responses."""

    def _create(responses: dict[str, str] | None = None) -> MockLLM:
        return MockLLM(responses)

    return _create


@pytest.fixture
def mock_tool_factory():
    """Factory for creating mock tools."""

    def _create(
        tool_outputs: dict[str, str] | None = None, repo_path: str = "/tmp/test"
    ):
        return MockRepoShellTool(tool_outputs, repo_path)

    return _create


@pytest.fixture
def mock_file_writer_factory():
    """Factory for creating mock file writer tools."""

    def _create(repo_path: str = "/tmp/test"):
        return MockRepoFileWriterTool(repo_path)

    return _create


# ============================================================================
# Fixture Loaders
# ============================================================================

# Use load_fixture directly from mocks: from mocks import load_fixture

# ============================================================================
# Repository Fixtures
# ============================================================================


@pytest.fixture
def test_repo_small(tmp_path):
    """Create a small test repository."""
    return create_test_repo(tmp_path, size="small")


@pytest.fixture
def test_repo_empty(tmp_path):
    """Create an empty test repository."""
    return create_test_repo(tmp_path, size="empty")


@pytest.fixture
def test_repo_path(tmp_path):
    """Create a test repository (default small)."""
    return create_test_repo(tmp_path, size="small")


# ============================================================================
# Pipeline Fixtures
# ============================================================================


@pytest.fixture
def pipeline_state_base():
    """Create a base pipeline state for testing."""
    return {
        "id": "test-pipeline-id",
        "issue_url": "https://github.com/test/repo/issues/1",
        "repo_path": "/tmp/test",
        "repo_root": "/tmp/test",
        "programmatic": True,
        "target_steps": None,
        "input_file": "",
    }


@pytest.fixture
def exploration_result_sample():
    """Sample exploration result."""
    return {
        "tech_stack": ["Python", "Flask"],
        "directory_layout": {"src": ["app.py"], "tests": ["test_app.py"]},
        "key_files": ["src/app.py"],
        "conventions": {"testing": "pytest"},
    }


@pytest.fixture
def analyze_result_sample():
    """Sample analyze result."""
    return {
        "requirements": ["Add feature X"],
        "similar_issues": [],
        "company_moment": "Recent merge: PR #10",
    }


# ============================================================================
# LLM Response Fixtures
# ============================================================================


@pytest.fixture
def llm_responses_explorer():
    """Load explorer LLM responses."""
    return load_fixture_dir("llm_responses/explorer")


@pytest.fixture
def llm_responses_analyze():
    """Load analyze LLM responses."""
    return load_fixture_dir("llm_responses/analyze")


@pytest.fixture
def llm_responses_implement():
    """Load implement LLM responses."""
    return load_fixture_dir("llm_responses/implement")


@pytest.fixture
def llm_responses_review():
    """Load review LLM responses."""
    return load_fixture_dir("llm_responses/review")


@pytest.fixture
def llm_responses_commit():
    """Load commit LLM responses."""
    return load_fixture_dir("llm_responses/commit")


# ============================================================================
# Tool Output Fixtures
# ============================================================================


@pytest.fixture
def tool_outputs_shell():
    """Load shell tool outputs."""
    return load_fixture_dir("tool_outputs/shell")


@pytest.fixture
def tool_outputs_github():
    """Load GitHub tool outputs."""
    return load_fixture_dir("tool_outputs/github")


# ============================================================================
# Input/Output Fixtures
# ============================================================================


@pytest.fixture
def valid_issue_input():
    """Common valid issue input."""
    return {
        "owner": "test",
        "repo": "repo",
        "number": "1",
        "kind": "issue",
        "is_pull": False,
        "github_repo": "test/repo",
    }


@pytest.fixture
def empty_context():
    """Empty context for error testing."""
    return {}


# ============================================================================
# Test Case Templates
# ============================================================================


class CrewTestBase:
    """Base class for crew tests."""

    @pytest.fixture(autouse=True)
    def setup(self, mock_llm_factory, test_repo_path):
        self.llm = mock_llm_factory(
            {
                "__default__": '{"result": "Mock crew response"}',
            }
        )
        self.repo = test_repo_path
        self.tools = {}

    def get_llm_response(self, prompt: str) -> str:
        """Get LLM response for a prompt."""
        for pattern, response in self.llm.responses.items():
            if pattern in prompt:
                return response
        return self.llm.responses.get("__default__", "")


class ExplorerTestCase(CrewTestBase):
    """Test case template for explorer crew."""

    @pytest.fixture(autouse=True)
    def setup_explorer(
        self,
        llm_responses_explorer,
        tool_outputs_shell,
        mock_llm_factory,
        test_repo_path,
    ):
        self.llm = mock_llm_factory(
            llm_responses_explorer.get("success", {}).get("response", "")
        )
        self.repo = test_repo_path
        self.shell_outputs = tool_outputs_shell
        self.tools = {
            "repo_shell": MockRepoShellTool(tool_outputs_shell),
        }


class AnalyzeTestCase(CrewTestBase):
    """Test case template for analyze crew."""

    @pytest.fixture(autouse=True)
    def setup_analyze(self, llm_responses_analyze, mock_llm_factory, valid_issue_input):
        self.llm = mock_llm_factory(
            llm_responses_analyze.get("success", {}).get("response", "")
        )
        self.issue_input = valid_issue_input
        self.tools = {}


class ImplementTestCase(CrewTestBase):
    """Test case template for implement crew."""

    @pytest.fixture(autouse=True)
    def setup_implement(
        self, llm_responses_implement, mock_file_writer_factory, test_repo_path
    ):
        self.llm = mock_llm_factory(
            llm_responses_implement.get("success", {}).get("response", "")
        )
        self.repo = test_repo_path
        self.file_writer = mock_file_writer_factory(str(test_repo_path))
        self.tools = {
            "repo_file_writer": self.file_writer,
        }


class ReviewTestCase(CrewTestBase):
    """Test case template for review crew."""

    @pytest.fixture(autouse=True)
    def setup_review(self, llm_responses_review, mock_llm_factory):
        self.llm = mock_llm_factory(
            llm_responses_review.get("success", {}).get("response", "")
        )
        self.tools = {}


class CommitTestCase(CrewTestBase):
    """Test case template for commit crew."""

    @pytest.fixture(autouse=True)
    def setup_commit(self, llm_responses_commit, mock_github_client, test_repo_path):
        self.llm = mock_llm_factory(
            llm_responses_commit.get("success", {}).get("response", "")
        )
        self.github = mock_github_client
        self.repo = test_repo_path
        self.tools = {
            "github": self.github,
        }
