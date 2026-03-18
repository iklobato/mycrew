"""Architecture agent: reviews high-level design and architecture."""

from crewai import Agent, LLM, Task

from mycrew.shared.llm import ModelMappings
from mycrew.shared.settings import Settings, get_pipeline_context
from mycrew.shared.tools import FileReadTool


class ArchitectureAgent:
    def agent(self) -> Agent:
        ctx = get_pipeline_context()
        settings = Settings()
        return Agent(
            llm=LLM(
                model=ModelMappings.REVIEW.value.openrouter_model,
                api_key=settings.openrouter_api_key,
            ),
            role="Architecture Reviewer",
            goal="Assess the PR's architectural approach and design decisions",
            backstory="""You are a principal engineer who evaluates architectural decisions.
You check for simplicity, adherence to patterns, proper separation of concerns,
and avoidance of technical debt.""",
            tools=[FileReadTool(directory=ctx.repo_path)],
        )

    def task(self) -> Task:
        return Task(
            description="""## Architecture Review

Review the PR's high-level architecture and design decisions.

### PR Information
- Title: {pr_title}
- Body: {pr_body}

### Changed Files
{changed_files}

### Diff
{pr_diff}

## Review Criteria
Analyze and report on:
1. Is the chosen approach the simplest one that solves the problem?
2. Does it introduce unnecessary complexity or over-engineering?
3. Does it follow existing architectural patterns in the codebase?
4. Are responsibilities properly separated (single responsibility)?
5. Does it introduce tight coupling between unrelated modules?
6. Could this decision create technical debt or scaling problems?
7. Should this change be broken into smaller PRs?

Provide your findings as markdown.""",
            expected_output="Architecture analysis in markdown",
            agent=self.agent(),
            async_execution=True,
        )
