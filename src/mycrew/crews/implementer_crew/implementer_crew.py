from crewai import Agent, Crew, LLM, Process, Task

from mycrew.llm import ModelMappings
from mycrew.settings import Settings, get_pipeline_context
from mycrew.tools import DirectoryReadTool, FileReadTool


class ImplementerCrew:
    """Implementer crew: executes implementation plan."""

    def __init__(self):
        self.settings = Settings()

    def implementer_agent(self) -> Agent:
        ctx = get_pipeline_context()
        return Agent(
            llm=LLM(
                model=ModelMappings.IMPLEMENT.value.openrouter_model,
                api_key=self.settings.openrouter_api_key,
            ),
            role="Software Implementer",
            goal="Execute implementation plans",
            backstory="Expert at writing code",
            tools=[
                DirectoryReadTool(directory=ctx.repo_path),
                FileReadTool(),
            ],
        )

    def polisher_agent(self) -> Agent:
        ctx = get_pipeline_context()
        return Agent(
            llm=LLM(
                model=ModelMappings.IMPLEMENT.value.openrouter_model,
                api_key=self.settings.openrouter_api_key,
            ),
            role="Code Polisher",
            goal="Add docs and fix lint",
            backstory="Expert at code quality",
            tools=[
                DirectoryReadTool(directory=ctx.repo_path),
                FileReadTool(),
            ],
        )

    def implement_task(self) -> Task:
        return Task(
            description="""Execute the implementation plan based on:
- Plan: {plan}
- Implementation context from previous: {implementation}

Focus on writing the actual code changes.""",
            expected_output="Implementation complete",
            agent=self.implementer_agent(),
        )

    def polish_task(self) -> Task:
        return Task(
            description="Add docstrings and fix linting for the implemented code",
            expected_output="Code polished",
            agent=self.polisher_agent(),
            context=[self.implement_task()],  # Receives output from implement_task
        )

    def crew(self) -> Crew:
        return Crew(
            agents=[self.implementer_agent(), self.polisher_agent()],
            tasks=[self.implement_task(), self.polish_task()],
            process=Process.sequential,
            memory=False,
        )
