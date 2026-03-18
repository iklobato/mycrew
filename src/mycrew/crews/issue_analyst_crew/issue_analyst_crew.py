"""Issue Analyst crew: parses raw issue cards into structured requirements."""

from crewai import Agent, Crew, LLM, Process, Task

from mycrew.llm import ModelMappings
from mycrew.settings import Settings


class IssueAnalystCrew:
    """Issue Analyst crew: synthesizes issues and validates scope."""

    def __init__(self):
        self.settings = Settings()

    def synthesizer_agent(self) -> Agent:
        return Agent(
            llm=LLM(
                model=ModelMappings.ANALYZE_ISSUE.value.openrouter_model,
                api_key=self.settings.openrouter_api_key,
            ),
            role="Issue Analyzer",
            goal="Parse issue requirements quickly",
            backstory="Expert at analyzing GitHub issues",
        )

    def synthesize_task(self) -> Task:
        return Task(
            description="Summarize this GitHub issue in 3-5 bullet points. Keep response under 2000 characters. Issue URL: {issue_url}",
            expected_output="Brief requirements summary",
            agent=self.synthesizer_agent(),
        )

    def crew(self) -> Crew:
        return Crew(
            agents=[self.synthesizer_agent()],
            tasks=[self.synthesize_task()],
            process=Process.sequential,
            verbose=False,
        )
