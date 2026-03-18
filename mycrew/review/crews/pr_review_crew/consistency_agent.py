"""Consistency agent: reviews style and pattern consistency."""

from crewai import Agent, LLM, Task

from mycrew.shared.llm import ModelMappings
from mycrew.shared.settings import Settings, get_pipeline_context
from mycrew.shared.tools import FileReadTool


class ConsistencyAgent:
    def agent(self) -> Agent:
        ctx = get_pipeline_context()
        settings = Settings()
        return Agent(
            llm=LLM(
                model=ModelMappings.REVIEW.value.openrouter_model,
                api_key=settings.openrouter_api_key,
            ),
            role="Consistency Reviewer",
            goal="Ensure the PR follows team style guides and patterns",
            backstory="""You are a code style expert who ensures consistency.
You verify adherence to naming conventions, patterns, and formatting rules.""",
            tools=[FileReadTool(directory=ctx.repo_path)],
        )

    def task(self) -> Task:
        return Task(
            description="""## Consistency Review

Review the PR for style and pattern consistency.

### PR Information
- Title: {pr_title}

### Changed Files
{changed_files}

### Diff
{pr_diff}

## Review Criteria
Analyze and report on:
1. Does the code follow the team's style guide and linting rules?
2. Are naming conventions consistent with the rest of the codebase?
3. Are the same patterns used for similar problems elsewhere in the project?
4. Are imports, file structure, and module organization consistent?
5. Is error handling done the same way as in other parts of the code?
6. Are API response shapes consistent with existing endpoints?

Provide your findings as markdown.""",
            expected_output="Consistency analysis in markdown",
            agent=self.agent(),
            async_execution=True,
        )
