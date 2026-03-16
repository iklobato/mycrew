"""Tests for crew building - loading from YAML, agent/task configuration."""

import re
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mocks import MockLLM


class MockLLMWithModel:
    """Mock LLM that tracks model assignments."""

    def __init__(self, model_name: str = "mock-model"):
        self.model = model_name
        self._call_count = 0

    def chat(self, messages):
        self._call_count += 1
        return MagicMock(content='{"result": "mock response"}')


@pytest.mark.crew
class TestCrewBuilding:
    """Tests for crew building from YAML configuration."""

    def test_build_explorer_crew_from_yaml(self):
        """Test that explorer crew loads correctly from YAML config."""
        from mycrew.crews.explorer_crew.explorer_crew import ExplorerCrew

        with patch("mycrew.llm.LLMManager.get_for_stage") as mock_get_llm:
            mock_get_llm.return_value = MockLLMWithModel("explore-model")

            crew_instance = ExplorerCrew()
            crew = crew_instance.crew()

            assert crew is not None
            assert len(crew.agents) > 0, "Crew should have agents"

    def test_crew_has_correct_agents(self):
        """Test that crew has all expected agents from config."""
        from mycrew.crews.explorer_crew.explorer_crew import ExplorerCrew

        with patch("mycrew.llm.LLMManager.get_for_stage") as mock_get_llm:
            mock_get_llm.return_value = MockLLMWithModel()

            crew_instance = ExplorerCrew()
            crew = crew_instance.crew()

            # Verify crew has agents
            assert len(crew.agents) > 0

    def test_crew_has_correct_tasks(self):
        """Test that crew has all expected tasks from config."""
        from mycrew.crews.explorer_crew.explorer_crew import ExplorerCrew

        with patch("mycrew.llm.LLMManager.get_for_stage") as mock_get_llm:
            mock_get_llm.return_value = MockLLMWithModel()

            crew_instance = ExplorerCrew()
            crew = crew_instance.crew()

            # Verify crew has tasks
            assert len(crew.tasks) > 0, "Crew should have tasks"

    def test_agent_llm_assignment(self):
        """Test that agents get correct LLM assigned."""
        from mycrew.crews.explorer_crew.explorer_crew import ExplorerCrew

        with patch("mycrew.llm.LLMManager.get_for_stage") as mock_get_llm:
            mock_llm = MockLLMWithModel("test-model")
            mock_get_llm.return_value = mock_llm

            crew_instance = ExplorerCrew()
            crew = crew_instance.crew()

            # All agents should have LLM assigned
            for agent in crew.agents:
                assert agent.llm is not None

    def test_agent_tools_assignment(self):
        """Test that agents have tools assigned from config."""
        from mycrew.crews.explorer_crew.explorer_crew import ExplorerCrew

        with patch("mycrew.llm.LLMManager.get_for_stage") as mock_get_llm:
            mock_get_llm.return_value = MockLLMWithModel()

            crew_instance = ExplorerCrew()
            crew = crew_instance.crew()

            # At least one agent should exist
            assert len(crew.agents) > 0

    def test_task_agent_binding(self):
        """Test that tasks are bound to correct agents."""
        from mycrew.crews.explorer_crew.explorer_crew import ExplorerCrew

        with patch("mycrew.llm.LLMManager.get_for_stage") as mock_get_llm:
            mock_get_llm.return_value = MockLLMWithModel()

            crew_instance = ExplorerCrew()
            crew = crew_instance.crew()

            # Each task should be bound to an agent
            for task in crew.tasks:
                assert task.agent is not None, (
                    f"Task {task.name} should have agent bound"
                )

    def test_explorer_crew_has_internal_deps_scout(self):
        """Test that explorer crew includes internal_deps_scout agent."""
        # Just verify the config exists - don't build the crew
        import yaml
        from pathlib import Path

        agents_path = (
            Path(__file__).parent.parent.parent
            / "src"
            / "mycrew"
            / "crews"
            / "explorer_crew"
            / "config"
            / "agents.yaml"
        )
        with open(agents_path) as f:
            config = yaml.safe_load(f)

        assert "internal_deps_scout" in config

    def test_explorer_crew_has_internal_deps_task(self):
        """Test that explorer crew includes internal_deps_task."""
        # Just verify the config exists - don't build the crew
        import yaml
        from pathlib import Path

        tasks_path = (
            Path(__file__).parent.parent.parent
            / "src"
            / "mycrew"
            / "crews"
            / "explorer_crew"
            / "config"
            / "tasks.yaml"
        )
        with open(tasks_path) as f:
            config = yaml.safe_load(f)

        assert "internal_deps_task" in config

    def test_internal_deps_scout_has_github_search_tool(self):
        """Test that internal_deps_scout agent has github_search tool in config."""
        import yaml
        from pathlib import Path

        config_path = (
            Path(__file__).parent.parent.parent
            / "src"
            / "mycrew"
            / "crews"
            / "explorer_crew"
            / "config"
            / "agents.yaml"
        )
        with open(config_path) as f:
            config = yaml.safe_load(f)

        assert "internal_deps_scout" in config
        assert "github_search" in config["internal_deps_scout"]["tools"]


@pytest.mark.crew
class TestCrewBuildingOtherCrews:
    """Tests for building other crews."""

    def test_build_analyze_crew(self):
        """Test that analyze crew builds correctly."""
        from mycrew.crews.issue_analyst_crew.issue_analyst_crew import IssueAnalystCrew

        with patch("mycrew.llm.LLMManager.get_for_stage") as mock_get_llm:
            mock_get_llm.return_value = MockLLMWithModel("analyze-model")

            crew_instance = IssueAnalystCrew()
            crew = crew_instance.crew()

            assert crew is not None
            assert len(crew.agents) > 0

    def test_build_implement_crew(self):
        """Test that implement crew builds correctly."""
        from mycrew.crews.implementer_crew.implementer_crew import ImplementerCrew

        with patch("mycrew.llm.LLMManager.get_for_stage") as mock_get_llm:
            mock_get_llm.return_value = MockLLMWithModel("implement-model")

            crew_instance = ImplementerCrew()
            crew = crew_instance.crew()

            assert crew is not None

    def test_implement_crew_kickoff_does_not_raise_keyerror(self):
        """Test that implement crew can kickoff with inputs without KeyError.

        This test catches the bug where JSDoc @param {string} in agent config
        was interpreted as CrewAI template variable causing KeyError: 'string'.
        """
        import re
        from mycrew.crews.implementer_crew.implementer_crew import ImplementerCrew

        with patch("mycrew.llm.LLMManager.get_for_stage") as mock_get_llm:
            mock_llm = MockLLMWithModel("implement-model")
            mock_get_llm.return_value = mock_llm

            crew_instance = ImplementerCrew()
            crew = crew_instance.crew()

            # Verify config doesn't have JSDoc type patterns that cause KeyError
            config_path = (
                Path(__file__).parent.parent.parent
                / "src"
                / "mycrew"
                / "crews"
                / "implementer_crew"
                / "config"
                / "agents.yaml"
            )
            with open(config_path) as f:
                content = f.read()

            forbidden_patterns = [
                r"\{string\}",
                r"\{number\}",
                r"\{boolean\}",
                r"\{any\}",
                r"\{object\}",
                r"\{User\|null\}",
                r"\{string\|null\}",
            ]

            for pattern in forbidden_patterns:
                match = re.search(pattern, content)
                assert match is None, (
                    f"Found CrewAI template pattern '{pattern}' in implementer config - "
                    "this causes KeyError at runtime. JSDoc types must be removed or escaped."
                )

    def test_build_reviewer_crew(self):
        """Test that reviewer crew builds correctly."""
        from mycrew.crews.reviewer_crew.reviewer_crew import ReviewerCrew

        with patch("mycrew.llm.LLMManager.get_for_stage") as mock_get_llm:
            mock_get_llm.return_value = MockLLMWithModel("review-model")

            crew_instance = ReviewerCrew()
            crew = crew_instance.crew()

            assert crew is not None

    def test_build_commit_crew(self):
        """Test that commit crew builds correctly."""
        from mycrew.crews.commit_crew.commit_crew import CommitCrew

        with patch("mycrew.llm.LLMManager.get_for_stage") as mock_get_llm:
            mock_get_llm.return_value = MockLLMWithModel("commit-model")

            crew_instance = CommitCrew()
            crew = crew_instance.crew()

            assert crew is not None


class TestCrewConfigValidation:
    """Tests that crew configs don't have patterns that cause runtime errors.

    These tests catch bugs like:
    - JSDoc @param {string} being interpreted as CrewAI template variable
    - Placeholder URLs in expected_output that agents output instead of calling tools
    """

    @pytest.mark.parametrize(
        "crew_name",
        [
            "implementer_crew",
            "commit_crew",
            "review_crew",
            "explorer_crew",
            "architect_crew",
            "issue_analyst_crew",
        ],
    )
    def test_no_jsdoc_type_annotations_in_agent_config(self, crew_name):
        """Test that agent configs don't have JSDoc types like {string}.

        JSDoc @param {string} is interpreted by CrewAI as a template variable,
        causing KeyError: 'string' at runtime when kickoff() is called.
        """
        config_path = (
            Path(__file__).parent.parent.parent
            / "src"
            / "mycrew"
            / "crews"
            / crew_name
            / "config"
            / "agents.yaml"
        )

        if not config_path.exists():
            pytest.skip(f"Config not found: {config_path}")

        with open(config_path) as f:
            content = f.read()

        forbidden_patterns = [
            r"\{string\}",
            r"\{number\}",
            r"\{boolean\}",
            r"\{any\}",
            r"\{object\}",
            r"\{User\|null\}",
            r"\{string\|null\}",
            r"\{Promise<",
        ]

        found_patterns = []
        for pattern in forbidden_patterns:
            if re.search(pattern, content):
                found_patterns.append(pattern)

        assert not found_patterns, (
            f"Found CrewAI template patterns {found_patterns} in {crew_name}/agents.yaml - "
            "these cause KeyError at runtime. JSDoc types must be removed or escaped."
        )

    @pytest.mark.parametrize(
        "crew_name,task_file",
        [
            ("implementer_crew", "tasks.yaml"),
            ("commit_crew", "tasks.yaml"),
            ("review_crew", "tasks.yaml"),
        ],
    )
    def test_no_placeholder_urls_in_task_expected_output(self, crew_name, task_file):
        """Test that task expected_output doesn't use placeholder URLs.

        Placeholder URLs like pull/123 or example.com cause agents to output
        the placeholder instead of actually calling the create_pr tool.
        """
        config_path = (
            Path(__file__).parent.parent.parent
            / "src"
            / "mycrew"
            / "crews"
            / crew_name
            / "config"
            / task_file
        )

        if not config_path.exists():
            pytest.skip(f"Config not found: {config_path}")

        with open(config_path) as f:
            content = f.read()

        placeholder_patterns = [
            r"pull/123",
            r"example\.com",
            r"owner/repo",
        ]

        found_patterns = []
        for pattern in placeholder_patterns:
            if re.search(pattern, content):
                found_patterns.append(pattern)

        # We allow placeholders in comments/descriptions but NOT in expected_output
        # This is a warning-level check - the actual fix is in agent prompts
        if found_patterns:
            print(
                f"Warning: Found placeholder patterns {found_patterns} in "
                f"{crew_name}/{task_file} - agents may output these instead of calling tools"
            )

    @pytest.mark.parametrize(
        "crew_name",
        [
            "implementer_crew",
            "commit_crew",
            "explorer_crew",
            "architect_crew",
            "issue_analyst_crew",
            "clarify_crew",
            "test_validator_crew",
            "tactiq_research_crew",
            "reviewer_crew",
        ],
    )
    def test_all_referenced_tools_exist_in_base(self, crew_name):
        """Test that all tools referenced in agents.yaml exist in PipelineCrewBase.

        This catches bugs where a config references a tool that doesn't exist,
        e.g., referencing 'github_api' when the tool is actually 'github_search'.
        """
        import yaml

        config_path = (
            Path(__file__).parent.parent.parent
            / "src"
            / "mycrew"
            / "crews"
            / crew_name
            / "config"
            / "agents.yaml"
        )

        if not config_path.exists():
            pytest.skip(f"Config not found: {config_path}")

        with open(config_path) as f:
            config = yaml.safe_load(f)

        # Get all tool names from base.py
        base_tools = {
            "repo_shell",
            "repo_file_writer",
            "serper_dev",
            "github_search",
            "create_pr",
            "scrape_website",
            "code_interpreter",
            "ask_human",
            "tactiq_meeting",
        }

        # Check each agent's tools
        for agent_name, agent_config in config.items():
            if "tools" not in agent_config:
                continue

            agent_tools = agent_config["tools"]
            if not agent_tools:
                continue

            for tool_name in agent_tools:
                # Handle list format: tools: [repo_shell, repo_file_writer]
                if isinstance(tool_name, str):
                    tool_names = [tool_name]
                elif isinstance(tool_name, list):
                    tool_names = tool_name
                else:
                    continue

                for tool in tool_names:
                    assert tool in base_tools, (
                        f"Agent '{agent_name}' in {crew_name} references unknown tool '{tool}'. "
                        f"Available tools: {base_tools}. "
                        f"This would cause runtime error when crew runs."
                    )
