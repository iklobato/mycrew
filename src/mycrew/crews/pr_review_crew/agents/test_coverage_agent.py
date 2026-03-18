"""Test coverage agent: reviews test quality and coverage."""

from crewai import Agent, LLM, Task

from mycrew.llm import ModelMappings
from mycrew.settings import Settings, get_pipeline_context
from mycrew.tools import FileReadTool


class TestCoverageAgent:
    def agent(self) -> Agent:
        ctx = get_pipeline_context()
        settings = Settings()
        return Agent(
            llm=LLM(
                model=ModelMappings.REVIEW.value.openrouter_model,
                api_key=settings.openrouter_api_key,
            ),
            role="Test Coverage Reviewer",
            goal="Evaluate the PR's test quality and coverage",
            backstory="""You are a QA engineer specializing in test coverage.
You verify that tests cover happy paths, edge cases, and failure scenarios.""",
            tools=[FileReadTool(directory=ctx.repo_path)],
        )

    def task(self) -> Task:
        return Task(
            description="""## Test Coverage Review

Review the PR's test quality and coverage.

### PR Information
- Title: {pr_title}

### Changed Files
{changed_files}

### Diff
{pr_diff}

## Review Criteria
Analyze and report on:
1. Are unit tests present for new logic?
2. Are integration or end-to-end tests included where needed?
3. Are edge cases and failure scenarios tested, not just happy paths?
4. Do tests have meaningful assertions (not just "it doesn't throw")?
5. Are tests isolated and not dependent on external state or order?
6. Are mocks/stubs used appropriately and not hiding real behavior?
7. Do existing tests still pass and remain valid after the change?

Provide your findings as markdown.""",
            expected_output="Test coverage analysis in markdown",
            agent=self.agent(),
            async_execution=True,
        )
