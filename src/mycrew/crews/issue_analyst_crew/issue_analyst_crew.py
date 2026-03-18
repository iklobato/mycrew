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
            role="Senior Requirements Analyst",
            goal="Extract structured, actionable requirements from GitHub issues",
            backstory="""You are a senior technical analyst with 15+ years experience
breaking down GitHub issues into implementation-ready specifications.
You specialize in identifying implicit requirements, edge cases, and
acceptance criteria that developers often miss.""",
        )

    def synthesize_task(self) -> Task:
        return Task(
            description="""## Task: Analyze Issue

Analyze the issue content below:

{issue_description}

## Output Requirements

Provide a structured analysis with the following sections:

### 1. PROBLEM STATEMENT
One sentence describing what needs to be built or fixed.

### 2. ACCEPTANCE CRITERIA
Numbered list of measurable success conditions.
- Each criterion should be testable/verifiable

### 3. TECHNICAL CONSTRAINTS
- Specific technologies, frameworks, or patterns required
- Any performance or security requirements
- Dependencies that must be used or avoided

### 4. EDGE CASES
Potential failure modes or boundary conditions that need handling.

### 5. RELATED FILES
Any files, components, or systems mentioned or likely affected.

Format as markdown. Keep total response under 2000 characters.""",
            expected_output="Structured requirements analysis with problem statement, acceptance criteria, constraints, edge cases, and related files",
            agent=self.synthesizer_agent(),
        )

    def crew(self) -> Crew:
        return Crew(
            agents=[self.synthesizer_agent()],
            tasks=[self.synthesize_task()],
            process=Process.sequential,
            verbose=False,
        )
