"""Context agent: reviews PR context and understanding."""

from crewai import Agent, LLM, Task

from mycrew.llm import ModelMappings
from mycrew.settings import Settings, get_pipeline_context
from mycrew.tools import FileReadTool


class ContextAgent:
    def agent(self) -> Agent:
        ctx = get_pipeline_context()
        settings = Settings()
        return Agent(
            llm=LLM(
                model=ModelMappings.REVIEW.value.openrouter_model,
                api_key=settings.openrouter_api_key,
            ),
            role="Context Analyst",
            goal="Understand the PR's purpose, scope, and context",
            backstory="""You are a technical analyst specializing in PR context.
You evaluate description clarity, linked issues, scope appropriateness,
and change type identification.""",
            tools=[FileReadTool(directory=ctx.repo_path)],
        )

    def task(self) -> Task:
        return Task(
            description="""## Context Review

Review the PR for context and understanding.

### PR Information
- Title: {pr_title}
- Body: {pr_body}
- Author: {pr_author}
- Labels: {pr_labels}

### Changed Files
{changed_files}

### Diff
{pr_diff}

## Review Criteria
Analyze and report on:
1. Is the PR description clear and complete?
2. Is there a linked ticket/issue explaining the why?
3. What is the scope — focused or too broad?
4. Is this a feature, fix, refactor, or hotfix?
5. Are there dependencies on other PRs or services?
6. Any product/business constraints to be aware of?

Provide your findings as markdown.""",
            expected_output="Context analysis in markdown",
            agent=self.agent(),
            async_execution=True,
        )
