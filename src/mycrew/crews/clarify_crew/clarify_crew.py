"""Clarify crew: identify ambiguities and ask human for clarification."""

from crewai import Agent, Crew, LLM, Process, Task

from mycrew.llm import ModelMappings
from mycrew.settings import Settings


class ClarifyCrew:
    """Clarify crew: identify ambiguities and ask human for clarification."""

    def __init__(self):
        self.settings = Settings()

    def clarifier(self) -> Agent:
        return Agent(
            llm=LLM(
                model=ModelMappings.ANALYZE_ISSUE.value.openrouter_model,
                api_key=self.settings.openrouter_api_key,
            ),
            role="Clarifier",
            goal="Identify ambiguities and ask human for clarification",
            backstory="Expert at analyzing requirements and identifying gaps",
        )

    def clarify_task(self) -> Task:
        return Task(
            description="""You are running the CLARIFY phase. If the issue is simple and clear, proceed with reasonable assumptions. Keep response under 2000 characters.

## Structured issue analysis
{issue_analysis}

## Codebase exploration results
{exploration}

## Your process

1. Read both inputs carefully — issue analysis and exploration results.
2. If the issue is straightforward (like adding a simple function), proceed with sensible defaults.
3. Only ask questions if there are critical ambiguities that would cause wrong implementation.
4. Otherwise, produce development guidelines based on best practices.

## Output format

Produce a structured Clarifications & Development Guidelines document. If no clarification needed, state "No clarifications needed - proceeding with implementation.""",
            expected_output="A structured Clarifications & Development Guidelines document in Markdown.",
            agent=self.clarifier(),
        )

    def crew(self) -> Crew:
        return Crew(
            agents=[self.clarifier()],
            tasks=[self.clarify_task()],
            process=Process.sequential,
            memory=False,
        )
