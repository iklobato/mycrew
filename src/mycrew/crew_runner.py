"""Crew runner with sequential and parallel execution support.

Classes:
- CrewRunner: Abstract base for running crews
- SequentialRunner: Runs crews sequentially
- ParallelRunner: Runs crews in parallel using asyncio
- GroupRunner: Runs multiple crews as a group (sequential or parallel)
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any

from mycrew.result import StageResult, StageStatus
from mycrew.settings import set_pipeline_context, PipelineContext

logger = logging.getLogger("mycrew.crew_runner")


class CrewRunner(ABC):
    """Abstract base class for crew runners."""

    @abstractmethod
    def run(
        self, crew_class: type, state: Any, inputs: dict | None = None
    ) -> StageResult:
        """Run a crew and return result."""
        pass

    def _build_context(self, state: Any) -> PipelineContext:
        """Build pipeline context from state."""
        github_repo = ""
        if state.issue_data and isinstance(state.issue_data, dict):
            github_repo = state.issue_data.get("github_repo", "")

        return PipelineContext(
            repo_path=state.repo_root or state.repo_path,
            github_repo=github_repo,
            issue_url=state.issue_url,
            programmatic=state.programmatic,
        )

    def _execute_crew(
        self, crew_class: type, state: Any, inputs: dict | None = None
    ) -> StageResult:
        """Execute a single crew with context setup."""
        ctx = self._build_context(state)
        set_pipeline_context(ctx)

        try:
            crew_instance = crew_class()
            final_inputs = crew_instance.build_inputs(state, inputs)
            crew = crew_instance.crew()
            result = crew.kickoff(inputs=final_inputs)
            return StageResult(status=StageStatus.COMPLETED, data={"raw": result})
        except Exception as e:
            logger.error(f"Crew execution failed: {e}")
            return StageResult(status=StageStatus.FAILED, error=str(e))


class SequentialRunner(CrewRunner):
    """Runs crews sequentially."""

    def run(
        self, crew_class: type, state: Any, inputs: dict | None = None
    ) -> StageResult:
        """Run a single crew sequentially."""
        return self._execute_crew(crew_class, state, inputs)


class ParallelRunner(CrewRunner):
    """Runs crews in parallel using asyncio."""

    async def _run_async(
        self, crew_class: type, state: Any, inputs: dict | None = None
    ) -> StageResult:
        """Run crew asynchronously."""
        return await asyncio.to_thread(self._execute_crew, crew_class, state, inputs)

    def run(
        self, crew_class: type, state: Any, inputs: dict | None = None
    ) -> StageResult:
        """Run crew in async context."""
        return asyncio.run(self._run_async(crew_class, state, inputs))


class GroupRunner:
    """Runs multiple crews as a group with optional parallel execution."""

    def __init__(self, parallel: bool = False):
        self.parallel = parallel
        self._runner = ParallelRunner() if parallel else SequentialRunner()

    def run_multiple(
        self,
        crew_configs: list[tuple[type, dict | None]],
        state: Any,
    ) -> list[StageResult]:
        """Run multiple crews either sequentially or in parallel.

        Args:
            crew_configs: List of (crew_class, inputs) tuples
            state: Pipeline state

        Returns:
            List of StageResult for each crew
        """
        if self.parallel:
            return self._run_parallel(crew_configs, state)
        return self._run_sequential(crew_configs, state)

    def _run_sequential(
        self,
        crew_configs: list[tuple[type, dict | None]],
        state: Any,
    ) -> list[StageResult]:
        """Run crews sequentially."""
        results = []
        for crew_class, inputs in crew_configs:
            result = self._runner.run(crew_class, state, inputs)
            results.append(result)
        return results

    def _run_parallel(
        self,
        crew_configs: list[tuple[type, dict | None]],
        state: Any,
    ) -> list[StageResult]:
        """Run crews in parallel using asyncio."""

        async def run_all():
            tasks = [
                asyncio.to_thread(self._runner.run, crew_class, state, inputs)
                for crew_class, inputs in crew_configs
            ]
            return await asyncio.gather(*tasks)

        return asyncio.run(run_all())
