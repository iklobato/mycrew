"""Reusable mock classes for testing."""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch


# ============================================================================
# Crew-specific LLM Response Fixtures
# ============================================================================

EXPLORE_RESPONSE = """## Tech Stack
- Python 3.x
- Flask web framework
- pytest for testing

## Directory Layout
- src/app.py - Main application
- tests/test_app.py - Tests
- pyproject.toml - Project config

## Key Files
- src/app.py - Main application entry point

## Conventions
- Testing: pytest
- Style: PEP 8
"""

ANALYZE_RESPONSE = """## Issue Analysis
- Feature: Add user authentication
- Type: Enhancement
- Priority: Medium

## Requirements
1. Add login endpoint
2. Add user registration
3. Add JWT token handling
"""

ARCHITECT_RESPONSE = """## Architecture Plan

### Changes Required
1. Create auth/ module with:
   - src/auth/__init__.py
   - src/auth/models.py
   - src/auth/routes.py

### Dependencies
- Add pyjwt to dependencies
- Update pyproject.toml
"""

IMPLEMENT_RESPONSE = """## Implementation Complete

### Files Created/Modified
1. src/auth/__init__.py - Auth module
2. src/auth/models.py - User model
3. src/auth/routes.py - Auth endpoints

### Tests Added
- tests/test_auth.py
"""

REVIEW_RESPONSE = """## Code Review

### Verdict: APPROVED

### Issues Found
- None

### Suggestions
- Consider adding rate limiting to login endpoint
"""

COMMIT_RESPONSE = """## Commit Complete

### Changes
- Added authentication module
- Added user models
- Added auth routes

### PR Created
- PR #1: Add user authentication
"""


class MockLLM:
    """Mock LLM that returns predefined responses."""

    def __init__(self, responses: dict[str, str] | None = None):
        self.responses = responses or {}
        self.call_history: list[dict[str, Any]] = []
        self._response_index = 0

    def add_response(self, prompt_pattern: str, response: str):
        """Add response for specific prompt pattern."""
        self.responses[prompt_pattern] = response

    def chat(self, messages: list[dict[str, str]]) -> "MockLLMResponse":
        """Simulate LLM chat by returning predefined response."""
        self.call_history.append({"messages": messages})

        # Get the last message as the prompt
        prompt = messages[-1]["content"] if messages else ""

        # Try to find matching response
        for pattern, response in self.responses.items():
            if pattern in prompt:
                return MockLLMResponse(content=response)

        # Return default response if no match
        default_response = self.responses.get(
            "__default__", '{"result": "Mock response"}'
        )
        return MockLLMResponse(content=default_response)


class MockLLMResponse:
    """Mock LLM response object."""

    def __init__(self, content: str):
        self.content = content
        self._content = content

    def model_dump(self, **kwargs) -> dict:
        return {"content": self._content}

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key, None)

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)


class MockRepoShellTool:
    """Mock shell tool that returns predefined command outputs."""

    def __init__(
        self, outputs: dict[str, str] | None = None, repo_path: str = "/tmp/test"
    ):
        self.outputs = outputs or {}
        self.call_history: list[str] = []
        self.repo_path = repo_path
        self._last_command = ""

    def add_output(self, command: str, output: str):
        """Add output for a specific command."""
        self.outputs[command] = output

    def run(self, command: str) -> str:
        """Run a command and return predefined output."""
        self.call_history.append(command)
        self._last_command = command

        # Try exact match first
        if command in self.outputs:
            return self.outputs[command]

        # Try to find partial match
        for cmd_pattern, output in self.outputs.items():
            if cmd_pattern in command:
                return output

        # Default empty response
        return ""

    def __call__(self, command: str) -> str:
        """Allow tool to be called directly."""
        return self.run(command)


class MockRepoFileWriterTool:
    """Mock file writer tool that captures written content."""

    def __init__(self, repo_path: str = "/tmp/test"):
        self.repo_path = repo_path
        self.written_files: dict[str, str] = {}
        self.call_history: list[dict[str, Any]] = []

    def write(self, file_path: str, content: str) -> str:
        """Simulate writing a file."""
        self.call_history.append(
            {"action": "write", "file_path": file_path, "content": content}
        )
        self.written_files[file_path] = content
        return f"Wrote {len(content)} bytes to {file_path}"

    def append(self, file_path: str, content: str) -> str:
        """Simulate appending to a file."""
        existing = self.written_files.get(file_path, "")
        self.written_files[file_path] = existing + content
        self.call_history.append(
            {"action": "append", "file_path": file_path, "content": content}
        )
        return f"Appended {len(content)} bytes to {file_path}"

    def __call__(self, file_path: str, content: str) -> str:
        """Allow tool to be called directly."""
        return self.write(file_path, content)


class MockGitHubClient:
    """Mock GitHub client for testing."""

    def __init__(self):
        self.issues: dict[str, list[dict]] = {}
        self.pulls: dict[str, list[dict]] = {}
        self.call_history: list[dict[str, Any]] = []

    def add_issue(self, repo: str, issue: dict):
        """Add a mock issue."""
        if repo not in self.issues:
            self.issues[repo] = []
        self.issues[repo].append(issue)

    def get_issues(self, repo: str, state: str = "open") -> list[dict]:
        """Get issues for a repo."""
        self.call_history.append({"action": "get_issues", "repo": repo, "state": state})
        return self.issues.get(repo, [])

    def get_pulls(self, repo: str, state: str = "open") -> list[dict]:
        """Get pull requests for a repo."""
        self.call_history.append({"action": "get_pulls", "repo": repo, "state": state})
        return self.pulls.get(repo, [])

    def create_pull(
        self, repo: str, title: str, body: str, head: str, base: str
    ) -> dict:
        """Create a mock pull request."""
        self.call_history.append(
            {
                "action": "create_pull",
                "repo": repo,
                "title": title,
                "body": body,
                "head": head,
                "base": base,
            }
        )
        pull = {
            "number": len(self.pulls.get(repo, [])) + 1,
            "title": title,
            "body": body,
            "head": head,
            "base": base,
            "html_url": f"https://github.com/{repo}/pull/{len(self.pulls.get(repo, [])) + 1}",
        }
        if repo not in self.pulls:
            self.pulls[repo] = []
        self.pulls[repo].append(pull)
        return pull


class MockToolResult:
    """Mock tool result for CrewAI."""

    def __init__(self, output: str = "", tool: str = "mock_tool"):
        self.output = output
        self.tool = tool

    def __str__(self) -> str:
        return self.output


class MockCrewResult:
    """Mock crew result for CrewAI."""

    def __init__(self, raw: Any = None, pydantic: Any = None):
        self.raw = raw
        self.pydantic = pydantic


class MockAgent:
    """Mock agent for CrewAI."""

    def __init__(self, name: str = "mock_agent", llm: MockLLM | None = None):
        self.name = name
        self.llm = llm or MockLLM()
        self.tools: list[Any] = []

    def add_tool(self, tool):
        """Add a tool to the agent."""
        self.tools.append(tool)


class MockTask:
    """Mock task for CrewAI."""

    def __init__(
        self,
        name: str = "mock_task",
        description: str = "",
        expected_output: str = "",
        agent: MockAgent | None = None,
    ):
        self.name = name
        self.description = description
        self.expected_output = expected_output
        self.agent = agent


class MockCrew:
    """Mock crew for CrewAI."""

    def __init__(
        self, agents: list[MockAgent] | None = None, tasks: list[MockTask] | None = None
    ):
        self.agents = agents or []
        self.tasks = tasks or []
        self.kickoff_history: list[dict] = []

    def kickoff(self, inputs: dict | None = None) -> MockCrewResult:
        """Simulate crew kickoff."""
        self.kickoff_history.append({"inputs": inputs})

        # Simulate running tasks and generating output
        output = ""
        for task in self.tasks:
            output += f"Task: {task.name}\n"

        return MockCrewResult(raw=output)


class MockFlowState:
    """Mock flow state for testing."""

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


# ============================================================================
# Fixture Loaders
# ============================================================================

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture(relative_path: str) -> dict:
    """Load a single fixture JSON file."""
    path = FIXTURES_DIR / relative_path
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def load_fixture_dir(relative_path: str) -> dict[str, dict]:
    """Load all JSON files in a directory as dict by filename."""
    dir_path = FIXTURES_DIR / relative_path
    if not dir_path.exists():
        return {}

    result = {}
    for f in dir_path.glob("*.json"):
        try:
            result[f.stem] = json.loads(f.read_text())
        except json.JSONDecodeError:
            result[f.stem] = {"error": "Invalid JSON"}
    return result


def create_test_repo(tmp_path: Path, size: str = "small") -> Path:
    """Create a test repository in the given temp directory."""
    repo_path = tmp_path / f"test_repo_{size}"
    repo_path.mkdir(parents=True, exist_ok=True)

    if size == "empty":
        return repo_path

    # Create minimal Python project
    (repo_path / "pyproject.toml").write_text(
        '[project]\nname = "test-project"\nversion = "0.1.0"\n'
    )

    src_dir = repo_path / "src"
    src_dir.mkdir(exist_ok=True)
    (src_dir / "__init__.py").write_text("")
    (src_dir / "app.py").write_text(
        '"""Test application."""\ndef hello():\n    return "Hello, World!"\n'
    )

    tests_dir = repo_path / "tests"
    tests_dir.mkdir(exist_ok=True)
    (tests_dir / "__init__.py").write_text("")
    (tests_dir / "test_app.py").write_text(
        '"""Test app."""\ndef test_hello():\n    assert hello() == "Hello, World!"\n'
    )

    (repo_path / "README.md").write_text("# Test Project\n")

    return repo_path


class CrewAIMockLLM:
    """Mock LLM compatible with CrewAI Agent constructor.

    CrewAI's Agent requires an LLM with a 'model' attribute.
    """

    def __init__(
        self,
        model: str = "gpt-4",
        response: str = "Mock response",
        temperature: float | None = None,
    ):
        self.model = model
        self.response = response
        self.temperature = temperature
        self.call_count = 0

    def chat(self, messages):
        """Simulate LLM chat."""
        self.call_count += 1
        mock_msg = MagicMock()
        mock_msg.content = self.response
        return mock_msg

    def __call__(self, *args, **kwargs):
        """Make mock callable."""
        return self.chat(args[0] if args else [])


def create_mock_llm(
    response: str = "Mock response",
    model: str = "gpt-4",
) -> CrewAIMockLLM:
    """Create a mock LLM that works with CrewAI Agent."""
    return CrewAIMockLLM(model=model, response=response)
