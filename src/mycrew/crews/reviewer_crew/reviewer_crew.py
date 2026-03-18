"""Reviewer crew: reviews implementation against plan and task."""

from crewai import Agent, Crew, LLM, Process, Task

from mycrew.llm import ModelMappings
from mycrew.settings import Settings, get_pipeline_context
from mycrew.tools import DirectoryReadTool, FileReadTool


class ReviewerCrew:
    """Reviewer crew: reviews implementation and checks compliance."""

    def __init__(self):
        self.settings = Settings()

    def reviewer_agent(self) -> Agent:
        ctx = get_pipeline_context()
        return Agent(
            llm=LLM(
                model=ModelMappings.REVIEW.value.openrouter_model,
                api_key=self.settings.openrouter_api_key,
            ),
            role="Code Reviewer",
            goal="Review implementation against plan",
            backstory="Expert at code review",
            tools=[
                DirectoryReadTool(directory=ctx.repo_path),
                FileReadTool(),
            ],
        )

    def compliance_agent(self) -> Agent:
        ctx = get_pipeline_context()
        return Agent(
            llm=LLM(
                model=ModelMappings.REVIEW.value.openrouter_model,
                api_key=self.settings.openrouter_api_key,
            ),
            role="Compliance Checker",
            goal="Check security and performance",
            backstory="Expert at security",
            tools=[
                DirectoryReadTool(directory=ctx.repo_path),
                FileReadTool(),
            ],
        )

    def review_task(self) -> Task:
        return Task(
            description="""Review implementation and tests. Keep response under 2000 characters.

Implementation: {implementation}
Tests: {tests}
Working directory: {repo_path}

Use FileReadTool to read changed files and review them.

Provide: APPROVED or ISSUES: list of issues found.""",
            expected_output="APPROVED or ISSUES:",
            agent=self.reviewer_agent(),
        )

    def compliance_task(self) -> Task:
        return Task(
            description="Check implementation for security and performance issues using FileReadTool",
            expected_output="Security and performance analysis",
            agent=self.compliance_agent(),
            context=[self.review_task()],
        )

    def crew(self) -> Crew:
        return Crew(
            agents=[self.reviewer_agent(), self.compliance_agent()],
            tasks=[self.review_task(), self.compliance_task()],
            process=Process.sequential,
            memory=False,
        )
