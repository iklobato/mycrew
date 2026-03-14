"""Pipeline input builder - constructs standard inputs for all crews."""

from typing import Any

from mycrew.utils import build_repo_context


class PipelineInputBuilder:
    """Builds standard inputs for pipeline crews from pipeline state.

    This class centralizes the construction of common inputs that all crews need,
    ensuring consistency across the pipeline. It builds inputs from the pipeline
    state and merges them with any custom inputs provided by the caller.

    Usage:
        builder = PipelineInputBuilder()
        inputs = builder.build(state, custom_inputs)
    """

    def build(
        self,
        state: Any,
        custom_inputs: dict | None = None,
    ) -> dict[str, Any]:
        """Build standard inputs for a crew from pipeline state.

        Args:
            state: PipelineState containing all pipeline data
            custom_inputs: Additional inputs specific to this crew (optional)

        Returns:
            Dictionary of inputs to pass to crew.kickoff()
        """
        if custom_inputs is None:
            custom_inputs = {}

        # Build github_repo from issue_data
        github_repo = self._extract_github_repo(state)

        # Build standard inputs from state
        inputs = self._build_standard_inputs(state, github_repo)

        # Merge with custom inputs (custom takes precedence)
        inputs.update(custom_inputs)

        return inputs

    def _extract_github_repo(self, state: Any) -> str:
        """Extract github_repo from state.issue_data."""
        github_repo = ""
        if state.issue_data and isinstance(state.issue_data, dict):
            github_repo = state.issue_data.get("github_repo", "")
        return github_repo or ""

    def _build_standard_inputs(
        self,
        state: Any,
        github_repo: str,
    ) -> dict[str, Any]:
        """Build the standard set of inputs that all crews need."""
        repo_path = state.repo_root or state.repo_path

        return {
            "repo_context": build_repo_context(
                repo_path=repo_path,
                github_repo=github_repo,
                issue_url=state.issue_url,
            ),
            "github_repo": github_repo,
            "issue_url": state.issue_url,
            "focus_paths": "",
            "exclude_paths": "",
            "task": self._extract_task(state),
            "issue_analysis": state.issue_data if state.issue_data else None,
        }

    def _extract_task(self, state: Any) -> str:
        """Extract task description from state."""
        if state.issue_data and isinstance(state.issue_data, dict):
            return state.issue_data.get("task", "")
        return ""
