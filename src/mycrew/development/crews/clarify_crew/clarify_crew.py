"""Clarify crew: identify ambiguities and ask human for clarification."""

from crewai import Agent, Crew, LLM, Process, Task

from mycrew.shared.llm import ModelMappings
from mycrew.shared.settings import Settings
from mycrew.shared.base import BaseCrew


class ClarifyCrew(BaseCrew):
    """Clarify crew: identify ambiguities and ask human for clarification."""

    name = "Clarify"

    def __init__(self):
        self.settings = Settings()

    def clarifier(self) -> Agent:
        return Agent(
            llm=LLM(
                model=ModelMappings.ANALYZE_ISSUE.value.openrouter_model,
                api_key=self.settings.openrouter_api_key,
            ),
            role="Technical Product Manager",
            goal="Resolve ambiguities or confirm assumptions before implementation",
            backstory="""You are a TPM who bridges engineering and product. You know
when to proceed with assumptions vs. when to block for clarification. You are
pragmatic - you don't ask questions for trivial matters.""",
        )

    def clarify_task(self) -> Task:
        return Task(
            description="""## Task: Clarification Phase

Analyze the issue and codebase to determine if clarification is needed.

**Issue Analysis:**
{issue_analysis}

**Codebase Exploration:**
{exploration}

## Decision Process

1. Review the issue requirements carefully
2. Compare with what you know about the codebase
3. Identify gaps, conflicts, or missing information

## Decision Rules

- **BLOCKING**: Missing critical information that would cause WRONG implementation
  - Unclear API contracts or data models
  - Missing security requirements
  - Ambiguous acceptance criteria

- **OPTIONAL**: Nice to have but can proceed without
  - Naming preferences
  - Exact UI details
  - Performance targets

## Output Format

```
## Clarifications Needed

### Blocking (cannot proceed without answers)
1. Question: ...
   Why: Explain what wrong implementation would result

### Optional (can proceed without answers)
1. Question: ...

## Assumptions Made
- Assumption: ... (only if proceeding)

## Decision
PROCEED | BLOCK

## Implementation Guidelines (only if PROCEED)
- Note any assumptions made that developers should know
- Specific guidance for edge cases
```

If NO clarification is needed, output:
```
## Clarifications Needed
No clarifications needed.

## Decision
PROCEED

## Implementation Guidelines
- Follow standard patterns in the codebase
- Use existing conventions for naming and structure
```

Keep response under 2000 characters.""",
            expected_output="Structured clarification document with decision",
            agent=self.clarifier(),
        )

    def crew(self) -> Crew:
        return Crew(
            agents=[self.clarifier()],
            tasks=[self.clarify_task()],
            process=Process.sequential,
            memory=False,
        )
