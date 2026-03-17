"""Explorer crew: repo exploration."""

from crewai import Agent, Crew, LLM, Process, Task

from mycrew.llm import ModelMappings
from mycrew.settings import Settings, get_pipeline_context


class ExplorerCrew:
    """Explorer crew: repo exploration."""

    def __init__(self):
        self.settings = Settings()

    def explorer_agent(self) -> Agent:
        ctx = get_pipeline_context()
        return Agent(
            llm=LLM(
                model=ModelMappings.EXPLORE.value.openrouter_model,
                api_key=self.settings.openrouter_api_key,
            ),
            role="Repository Explorer",
            goal="Analyze codebase structure and identify relevant files",
            backstory="Expert at understanding codebases",
        )

    def explore_task(self) -> Task:
        ctx = get_pipeline_context()
        return Task(
            description="""Explore the codebase at {repo_path} based on issue requirements.

Issue requirements: {issue_analysis}

Provide:
1. Project structure overview (main directories and their purposes)
2. Key files that are likely relevant to the implementation
3. Tech stack (framework, language, dependencies)
4. Test file locations and patterns
5. Configuration files

Do NOT attempt to read all files - just provide analysis based on typical project structures.""",
            expected_output="Structured exploration document with project structure, tech stack, relevant files, and test patterns",
            agent=self.explorer_agent(),
        )

    def crew(self) -> Crew:
        return Crew(
            agents=[self.explorer_agent()],
            tasks=[self.explore_task()],
            process=Process.sequential,
            memory=False,
        )
