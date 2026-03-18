"""Test Validator crew: writes tests and validates they catch bugs."""

from crewai import Agent, Crew, LLM, Process, Task

from mycrew.llm import ModelMappings
from mycrew.settings import Settings, get_pipeline_context
from mycrew.tools import DirectoryReadTool, FileReadTool, FileWriterTool


class TestValidatorCrew:
    """Test Validator crew: writes tests and validates they catch bugs."""

    def __init__(self):
        self.settings = Settings()

    def test_implementer(self) -> Agent:
        ctx = get_pipeline_context()
        return Agent(
            llm=LLM(
                model=ModelMappings.TEST_VALIDATION.value.openrouter_model,
                api_key=self.settings.openrouter_api_key,
            ),
            role="Test Implementer",
            goal="Write tests for the implementation",
            backstory="Expert at writing test cases",
            tools=[
                DirectoryReadTool(directory=ctx.repo_path),
                FileReadTool(),
                FileWriterTool(),
            ],
            max_iter=2,
        )

    def test_implement_task(self) -> Task:
        return Task(
            description="""Write tests for the implementation based on: Keep response under 2000 characters.
- Plan: {plan}
- Implementation: {implementation}

Use FileReadTool to read existing test patterns, then FileWriterTool to write tests.
Working directory: {repo_path}

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
