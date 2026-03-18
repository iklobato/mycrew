from crewai import Agent, Crew, LLM, Process, Task

from mycrew.llm import ModelMappings
from mycrew.settings import Settings


class ArchitectCrew:
    """Architect crew: creates implementation plans."""

    def __init__(self):
        self.settings = Settings()

    def architect_agent(self) -> Agent:
        return Agent(
            llm=LLM(
                model=ModelMappings.PLAN.value.openrouter_model,
                api_key=self.settings.openrouter_api_key,
            ),
            role="Software Architect",
            goal="Create implementation plans",
            backstory="Expert at system design",
        )

    def advisor_agent(self) -> Agent:
        return Agent(
            llm=LLM(
                model=ModelMappings.PLAN.value.openrouter_model,
                api_key=self.settings.openrouter_api_key,
            ),
            role="Technical Advisor",
            goal="Analyze risks and migration",
            backstory="Expert at risk assessment",
        )

    def plan_task(self) -> Task:
        return Task(
            description="""Create implementation plan based on: Keep response under 2000 characters.
- Issue requirements: {issue_analysis}
- Codebase exploration: {exploration}
- Clarifications: {clarifications}

Focus on WHAT files need to change and HOW, not detailed code.""",
            expected_output="Implementation plan document",
            agent=self.architect_agent(),
        )

    def advisor_task(self) -> Task:
        return Task(
            description="Analyze implementation risks from the plan",
            expected_output="Risk analysis document",
            agent=self.advisor_agent(),
            context=[self.plan_task()],
        )

    def crew(self) -> Crew:
        return Crew(
            agents=[self.architect_agent(), self.advisor_agent()],
            tasks=[self.plan_task(), self.advisor_task()],
            process=Process.sequential,
            memory=False,
        )
