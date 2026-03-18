"""Readability agent: reviews code clarity and maintainability."""

from crewai import Agent, LLM, Task

from mycrew.shared.llm import ModelMappings
from mycrew.shared.settings import Settings, get_pipeline_context
from mycrew.shared.tools import FileReadTool


class ReadabilityAgent:
    def agent(self) -> Agent:
        ctx = get_pipeline_context()
        settings = Settings()
        return Agent(
            llm=LLM(
                model=ModelMappings.REVIEW.value.openrouter_model,
                api_key=settings.openrouter_api_key,
            ),
            role="Readability Reviewer",
            goal="Assess code clarity, readability, and maintainability",
            backstory="""You are a code quality expert who evaluates readability.
You check for clear naming, appropriate function size, and minimal complexity.""",
            tools=[FileReadTool(directory=ctx.repo_path)],
        )

    def task(self) -> Task:
        return Task(
            description="""## Readability Review

Review the PR for code readability and maintainability.

### PR Information
- Title: {pr_title}

### Changed Files
{changed_files}

### Diff
{pr_diff}

## Review Criteria
Analyze and report on:
1. Are variable, function, and class names descriptive and consistent?
2. Are functions small and focused on a single task?
3. Is there duplicated logic that should be extracted?
4. Is complex logic broken into readable steps with clear intent?
5. Are magic numbers or strings replaced with named constants?
6. Is the code free of dead code, commented-out blocks, and TODOs without tickets?
7. Would someone unfamiliar with the code understand it quickly?

Provide your findings as markdown.""",
            expected_output="Readability analysis in markdown",
            agent=self.agent(),
            async_execution=True,
        )
