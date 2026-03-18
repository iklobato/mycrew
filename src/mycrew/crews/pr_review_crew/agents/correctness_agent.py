"""Correctness agent: reviews logic correctness and edge cases."""

from crewai import Agent, LLM, Task

from mycrew.llm import ModelMappings
from mycrew.settings import Settings, get_pipeline_context
from mycrew.tools import FileReadTool


class CorrectnessAgent:
    def agent(self) -> Agent:
        ctx = get_pipeline_context()
        settings = Settings()
        return Agent(
            llm=LLM(
                model=ModelMappings.REVIEW.value.openrouter_model,
                api_key=settings.openrouter_api_key,
            ),
            role="Correctness Reviewer",
            goal="Verify the PR's logic is correct and handles edge cases",
            backstory="""You are a senior engineer specializing in logic verification.
You check for off-by-one errors, null handling, race conditions,
and proper conditional logic.""",
            tools=[FileReadTool(directory=ctx.repo_path)],
        )

    def task(self) -> Task:
        return Task(
            description="""## Correctness Review

Review the PR for logic correctness and edge case handling.

### PR Information
- Title: {pr_title}

### Changed Files
{changed_files}

### Diff
{pr_diff}

## Review Criteria
Analyze and report on:
1. Does the logic match the requirements?
2. Are edge cases handled (empty inputs, nulls, boundary values)?
3. Are there off-by-one errors in loops or ranges?
4. Is conditional logic correct and not overly complex?
5. Are asynchronous operations handled properly (race conditions, await/callbacks)?
6. Is state managed correctly, especially in concurrent scenarios?
7. Are type coercions or implicit conversions causing unexpected behavior?

Provide your findings as markdown.""",
            expected_output="Correctness analysis in markdown",
            agent=self.agent(),
            async_execution=True,
        )
