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
            description="""You are running the CLARIFY phase. Ask the human specific questions with options, starting with highest impact.

## Task description
{task}

## Structured issue analysis
{issue_analysis}

## Codebase exploration results
{exploration}

## Your process

1. Read all three inputs carefully — task, requirements, and exploration results.
2. Cross-reference: look for tensions between what the spec asks for and what the
   codebase currently looks like. Flag anything that could cause the architect to
   make a wrong assumption.
3. For each open question, ask ONE focused question.
   The question string MUST include the full question plus Option A, Option B (and Option C/D if needed).
4. Based on the answers, decide if follow-ups are needed.
5. Do NOT ask about things already clearly answered in the issue analysis.
6. Do NOT ask generic questions that ignore the exploration findings.
7. Do NOT ask more than one question per turn.

## Output format

Produce a structured Clarifications & Development Guidelines document.""",
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
