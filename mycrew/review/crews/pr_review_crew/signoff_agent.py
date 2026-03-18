"""Signoff agent: compiles final review summary."""

from crewai import Agent, LLM, Task

from mycrew.shared.llm import ModelMappings
from mycrew.shared.settings import Settings, get_pipeline_context
from mycrew.shared.tools import FileReadTool


class SignoffAgent:
    def agent(self) -> Agent:
        ctx = get_pipeline_context()
        settings = Settings()
        return Agent(
            llm=LLM(
                model=ModelMappings.REVIEW.value.openrouter_model,
                api_key=settings.openrouter_api_key,
            ),
            role="Review Signoff",
            goal="Synthesize all reviews into a final recommendation",
            backstory="""You are a senior reviewer who synthesizes feedback.
You categorize findings as blockers, suggestions, or nits, and provide clear recommendations.""",
            tools=[FileReadTool(directory=ctx.repo_path)],
        )

    def task(self, context: list[Task]) -> Task:
        return Task(
            description="""## Final Sign-off

Review all agent outputs and produce a comprehensive summary.

### Agent Reviews
{context_output}
{architecture_output}
{correctness_output}
{security_output}
{performance_output}
{test_coverage_output}
{readability_output}
{consistency_output}
{error_handling_output}
{documentation_output}

## Output Format

### Summary Table
| Category | Verdict | Status |
|----------|---------|--------|

### Blockers (if any)
List critical issues that MUST be fixed before merge. Include file:line references.

### Suggestions (if any)
List improvements that are recommended but not blocking.

### Nits (if any)
List minor issues like style preferences or typos.

### Passed Categories
List categories that passed review without issues.

### Recommendation
APPROVE | REQUEST_CHANGES | BLOCK

Include specific file and line references where applicable.""",
            expected_output="Final review summary in markdown with clear recommendation",
            agent=self.agent(),
            context=context,
        )
