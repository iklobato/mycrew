"""Security agent: reviews for security vulnerabilities."""

from crewai import Agent, LLM, Task

from mycrew.shared.llm import ModelMappings
from mycrew.shared.settings import Settings, get_pipeline_context
from mycrew.shared.tools import FileReadTool


class SecurityAgent:
    def agent(self) -> Agent:
        ctx = get_pipeline_context()
        settings = Settings()
        return Agent(
            llm=LLM(
                model=ModelMappings.REVIEW.value.openrouter_model,
                api_key=settings.openrouter_api_key,
            ),
            role="Security Reviewer",
            goal="Identify security vulnerabilities and risks in the PR",
            backstory="""You are a security expert who identifies vulnerabilities.
You check for injection risks, exposed secrets, auth issues, and CVEs.""",
            tools=[FileReadTool(directory=ctx.repo_path)],
        )

    def task(self) -> Task:
        return Task(
            description="""## Security Review

Review the PR for security vulnerabilities.

### PR Information
- Title: {pr_title}

### Changed Files
{changed_files}

### Diff
{pr_diff}

## Review Criteria
Analyze and report on:
1. Is user input validated and sanitized?
2. Are there SQL injection, XSS, or command injection risks?
3. Are secrets, credentials, or tokens hardcoded or exposed?
4. Is authentication and authorization enforced at every entry point?
5. Are third-party dependencies up to date and free of known CVEs?
6. Is sensitive data encrypted at rest and in transit?
7. Are error messages leaking internal implementation details?
8. Are file uploads or external URLs handled safely?

Provide your findings as markdown.""",
            expected_output="Security analysis in markdown",
            agent=self.agent(),
            async_execution=True,
        )
