"""Error handling agent: reviews error handling and logging."""

from crewai import Agent, LLM, Task

from mycrew.llm import ModelMappings
from mycrew.settings import Settings, get_pipeline_context
from mycrew.tools import FileReadTool


class ErrorHandlingAgent:
    def agent(self) -> Agent:
        ctx = get_pipeline_context()
        settings = Settings()
        return Agent(
            llm=LLM(
                model=ModelMappings.REVIEW.value.openrouter_model,
                api_key=settings.openrouter_api_key,
            ),
            role="Error Handling Reviewer",
            goal="Evaluate error handling and logging practices",
            backstory="""You are an observability expert who reviews error handling.
You check for graceful failures, proper logging, and retry logic.""",
            tools=[FileReadTool(directory=ctx.repo_path)],
        )

    def task(self) -> Task:
        return Task(
            description="""## Error Handling Review

Review the PR's error handling and logging.

### PR Information
- Title: {pr_title}

### Changed Files
{changed_files}

### Diff
{pr_diff}

## Review Criteria
Analyze and report on:
1. Are all foreseeable errors explicitly caught and handled?
2. Are errors propagated correctly up the call stack?
3. Are user-facing error messages clear and non-technical?
4. Are internal errors logged with enough context to debug?
5. Is there a difference between expected errors (validation) and unexpected ones (crashes)?
6. Are retries implemented where appropriate (e.g., transient network failures)?
7. Is logging free of sensitive data (PII, tokens, passwords)?

Provide your findings as markdown.""",
            expected_output="Error handling analysis in markdown",
            agent=self.agent(),
            async_execution=True,
        )
