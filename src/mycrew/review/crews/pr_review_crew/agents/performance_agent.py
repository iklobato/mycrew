"""Performance agent: reviews for performance bottlenecks."""

from crewai import Agent, LLM, Task

from mycrew.shared.llm import ModelMappings
from mycrew.shared.settings import Settings, get_pipeline_context
from mycrew.shared.tools import FileReadTool


class PerformanceAgent:
    def agent(self) -> Agent:
        ctx = get_pipeline_context()
        settings = Settings()
        return Agent(
            llm=LLM(
                model=ModelMappings.REVIEW.value.openrouter_model,
                api_key=settings.openrouter_api_key,
            ),
            role="Performance Reviewer",
            goal="Identify potential performance bottlenecks in the PR",
            backstory="""You are a performance engineer who identifies bottlenecks.
You check for N+1 queries, blocking calls, memory issues, and missing indexes.""",
            tools=[FileReadTool(directory=ctx.repo_path)],
        )

    def task(self) -> Task:
        return Task(
            description="""## Performance Review

Review the PR for performance issues.

### PR Information
- Title: {pr_title}

### Changed Files
{changed_files}

### Diff
{pr_diff}

## Review Criteria
Analyze and report on:
1. Are there any unnecessary or redundant database queries (N+1)?
2. Are expensive operations cached where appropriate?
3. Are large datasets paginated or streamed instead of loaded fully into memory?
4. Are there blocking synchronous calls that should be async?
5. Are indexes in place for new query patterns?
6. Are loops or nested iterations avoidable with better data structures?
7. Could this change degrade performance under high load?

Provide your findings as markdown.""",
            expected_output="Performance analysis in markdown",
            agent=self.agent(),
            async_execution=True,
        )
