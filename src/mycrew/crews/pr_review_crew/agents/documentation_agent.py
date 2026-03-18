"""Documentation agent: reviews documentation completeness."""

from crewai import Agent, LLM, Task

from mycrew.llm import ModelMappings
from mycrew.settings import Settings, get_pipeline_context
from mycrew.tools import FileReadTool


class DocumentationAgent:
    def agent(self) -> Agent:
        ctx = get_pipeline_context()
        settings = Settings()
        return Agent(
            llm=LLM(
                model=ModelMappings.REVIEW.value.openrouter_model,
                api_key=settings.openrouter_api_key,
            ),
            role="Documentation Reviewer",
            goal="Assess documentation completeness and accuracy",
            backstory="""You are a technical writer who evaluates documentation.
You verify that APIs, complex logic, and decisions are properly documented.""",
            tools=[FileReadTool(directory=ctx.repo_path)],
        )

    def task(self) -> Task:
        return Task(
            description="""## Documentation Review

Review the PR's documentation.

### PR Information
- Title: {pr_title}
- Body: {pr_body}

### Changed Files
{changed_files}

### Diff
{pr_diff}

## Review Criteria
Analyze and report on:
1. Are complex or non-obvious sections of code commented?
2. Are public APIs, functions, and classes documented?
3. Is the README updated if behavior, setup, or configuration changed?
4. Is there a migration guide if there are breaking changes?
5. Is a changelog entry needed?
6. Are architectural decisions recorded (e.g., ADRs)?

Provide your findings as markdown.""",
            expected_output="Documentation analysis in markdown",
            agent=self.agent(),
            async_execution=True,
        )
