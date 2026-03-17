"""Test Validator crew: writes tests and validates they catch bugs."""

from crewai import Agent, Crew, LLM, Process, Task

from mycrew.llm import ModelMappings
from mycrew.settings import Settings


class TestValidatorCrew:
    """Test Validator crew: writes tests and validates they catch bugs."""

    def __init__(self):
        self.settings = Settings()

    def test_implementer(self) -> Agent:
        return Agent(
            llm=LLM(
                model=ModelMappings.TEST_VALIDATION.value.openrouter_model,
                api_key=self.settings.openrouter_api_key,
            ),
            role="Test Implementer",
            goal="Write tests for the implementation",
            backstory="Expert at writing test cases",
        )

    def test_implement_task(self) -> Task:
        return Task(
            description="""Write tests for the implementation.

Context: {repo_context}

Plan: {plan}
Implementation: {implementation}
Exploration (Test Layout): {exploration}

If test_command is empty, output "Test writing skipped (no test_command)".

Otherwise:
1. Read the plan to identify files that need tests
2. Check exploration for test patterns and conventions
3. Write tests following project test patterns

Output "Tests written: [list of files with test counts]".""",
            expected_output="List of test files written with test counts, or skip message.",
            agent=self.test_implementer(),
        )

    def crew(self) -> Crew:
        return Crew(
            agents=[self.test_implementer()],
            tasks=[self.test_implement_task()],
            process=Process.sequential,
            memory=False,
        )
