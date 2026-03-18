"""Reviewer crew: reviews implementation against plan and task."""

from crewai import Agent, Crew, LLM, Process, Task

from mycrew.shared.llm import ModelMappings
from mycrew.shared.settings import Settings, get_pipeline_context
from mycrew.shared.tools import DirectoryReadTool, FileReadTool
from mycrew.shared.base import BaseCrew


class ReviewerCrew(BaseCrew):
    """Reviewer crew: reviews implementation against plan and task."""

    name = "Reviewer"

    def __init__(self):
        self.settings = Settings()

    def reviewer_agent(self) -> Agent:
        ctx = get_pipeline_context()
        return Agent(
            llm=LLM(
                model=ModelMappings.REVIEW.value.openrouter_model,
                api_key=self.settings.openrouter_api_key,
            ),
            role="Senior Code Reviewer",
            goal="Ensure implementation matches plan and is production-ready",
            backstory="""You are a senior engineer who catches bugs before they reach 
production. You review for correctness, security, performance, and 
maintainability. You provide specific, actionable feedback.""",
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
            role="Security Engineer",
            goal="Check implementation for security and performance issues",
            backstory="""You are a security expert who identifies vulnerabilities,
performance issues, and compliance concerns in code changes.""",
            tools=[
                DirectoryReadTool(directory=ctx.repo_path),
                FileReadTool(),
            ],
        )

    def review_task(self) -> Task:
        return Task(
            description="""## Task: Code Review

Review the implementation against the plan.

**Implementation:**
{implementation}

**Tests:**
{tests}

**Working Directory:** {repo_path}

## Review Checklist

You MUST check EACH of the following:

- [ ] All files from the plan were created
- [ ] All modifications from the plan were applied
- [ ] Code follows project conventions (naming, formatting)
- [ ] No security vulnerabilities (injection, hardcoded secrets, auth bypass)
- [ ] Error handling is present and appropriate
- [ ] Tests cover main functionality
- [ ] No obvious bugs or logic errors
- [ ] Imports are correct and complete
- [ ] Type hints are present where needed

## Output Format

```
## Review Results

### Checklist
- [x] Item: PASS
- [ ] Item: FAIL - reason

### Issues Found
1. **SEVERITY** (CRITICAL/HIGH/MEDIUM/LOW): Description
   - File: path/to/file.py
   - Fix: Specific fix required

### Verdict
APPROVED | NEEDS_REVISION
```

If NEEDS_REVISION, list specific files and required changes.
Keep response under 2000 characters.

## Code Review Checklist

Before submitting your review, consider:

- Have you re-read every line of your own diff with fresh eyes?
- Is the code doing anything unrelated to the card's scope?
- Does it work end-to-end in your local environment?
- Have you tested the happy path, edge cases, and failure scenarios manually?
- Are there any obvious performance or security issues you'd flag in someone else's PR?
- Is the PR description clear — explaining what changed and why?
- Are related docs, READMEs, or wikis updated?
- Have all linting, formatting, and CI checks been run?
- Is feedback on others' PRs categorized (blocker vs. suggestion vs. nitpick)?
- Are all CI/CD checks passing?""",
            expected_output="Review results with checklist and verdict",
            agent=self.reviewer_agent(),
        )

    def compliance_task(self) -> Task:
        return Task(
            description="""## Task: Security and Performance Review

Review implementation for security and performance issues.

**Implementation:**
{implementation}

**Working Directory:** {repo_path}

Check for:
1. SQL injection vulnerabilities
2. Hardcoded credentials or secrets
3. Authentication/authorization issues
4. Performance bottlenecks (N+1 queries, missing indexes)
5. Resource leaks (unclosed connections, handles)
6. Input validation

Output:
```
## Security Issues
- Issue: Description | File: path | Severity: ...

## Performance Issues
- Issue: Description | File: path | Impact: ...

## Verdict
SAFE | NEEDS_CHANGES
```""",
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
