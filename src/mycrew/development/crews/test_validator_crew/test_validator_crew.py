"""Test Validator crew: writes tests and validates they catch bugs."""

from crewai import Agent, Crew, LLM, Process, Task

from mycrew.shared.llm import ModelMappings
from mycrew.shared.settings import Settings, get_pipeline_context
from mycrew.shared.tools import DirectoryReadTool, FileReadTool, FileWriterTool
from mycrew.shared.base import BaseCrew


class TestValidatorCrew(BaseCrew):
    """Test Validator crew: writes tests and validates they catch bugs."""

    name = "Test Validator"

    def __init__(self):
        self.settings = Settings()

    def test_implementer(self) -> Agent:
        ctx = get_pipeline_context()
        return Agent(
            llm=LLM(
                model=ModelMappings.TEST_VALIDATION.value.openrouter_model,
                api_key=self.settings.openrouter_api_key,
            ),
            role="QA Engineer",
            goal="Write comprehensive tests that catch implementation bugs",
            backstory="""You are a QA engineer who writes tests that fail when code breaks
and pass when it works correctly. You follow the project's existing test patterns
and conventions. You write tests for happy path, edge cases, and error handling.""",
            tools=[
                DirectoryReadTool(directory=ctx.repo_path),
                FileReadTool(),
                FileWriterTool(),
            ],
            max_iter=2,
        )

    def test_implement_task(self) -> Task:
        return Task(
            description="""## Task: Write Tests for Implementation

**Plan:**
{plan}

**Implementation:**
{implementation}

**Working Directory:** {repo_path}

## Process

1. Read existing test files in tests/ to understand:
   - Test file naming conventions
   - Test framework used (pytest, unittest, etc.)
   - Test structure and patterns
   - Fixtures and mocks used

2. Identify what needs to be tested based on implementation

3. Write tests covering:
   - Happy path functionality
   - Edge cases from requirements
   - Error handling
   - Boundary conditions

## Output Format

Output as JSON array of test files:
```json
[
  {
    "path": "tests/test_module.py",
    "content": "import pytest\\n\\ndef test_function():\\n    assert function() == expected\\n"
  }
]
```

If no tests needed, output:
```json
[]
```""",
            expected_output="JSON array of test files written with paths and content",
            agent=self.test_implementer(),
        )

    def crew(self) -> Crew:
        return Crew(
            agents=[self.test_implementer()],
            tasks=[self.test_implement_task()],
            process=Process.sequential,
            memory=False,
        )
