"""Architect crew: creates implementation plans."""

from crewai import Agent, Crew, LLM, Process, Task

from mycrew.shared.llm import ModelMappings
from mycrew.shared.settings import Settings
from mycrew.shared.base import BaseCrew


class ArchitectCrew(BaseCrew):
    """Architect crew: creates implementation plans."""

    name = "Architect"

    def __init__(self):
        self.settings = Settings()

    def architect_agent(self) -> Agent:
        return Agent(
            llm=LLM(
                model="openrouter/anthropic/claude-3.5-sonnet",
                api_key=self.settings.openrouter_api_key,
            ),
            role="Technical Lead",
            goal="Create detailed implementation plans at the file level",
            backstory="""You are a technical lead who writes implementation plans that
engineers can execute directly. Your plans are precise, actionable, and include
specific file paths, line numbers, and code snippets where needed.""",
        )

    def advisor_agent(self) -> Agent:
        return Agent(
            llm=LLM(
                model=ModelMappings.PLAN.value.openrouter_model,
                api_key=self.settings.openrouter_api_key,
            ),
            role="Technical Advisor",
            goal="Analyze risks and provide migration guidance",
            backstory="""You are an expert at risk assessment and technical debt analysis.
You identify potential pitfalls, breaking changes, and migration paths.""",
        )

    def plan_task(self) -> Task:
        return Task(
            description="""## Task: Create Implementation Plan

**Original Issue Requirements:**
{issue_description}

**Analysis Summary:**
{issue_analysis}

**Codebase Exploration:**
{exploration}

**Clarifications:**
{clarifications}

## CRITICAL: Acceptance Criteria

The issue MUST implement the following acceptance criteria. Your plan must address EACH one:

1. **Identify which files need changes to support conditional GET**
2. **What HTTP headers to add (If-None-Match, If-Modified-Since)**
3. **How to handle HTTP 304 responses**
4. **How to update etag and last_modified fields**
5. **What tests are needed (200, 304, fallback behavior)**

## Output Format

Create a structured implementation plan:

### 1. Files to Create
| File Path | Purpose | Key Logic |
|-----------|---------|-----------|

### 2. Files to Modify
| File Path | Changes Required | Specific Changes |
|-----------|------------------|------------------|

### 3. Dependencies
- Any new packages needed

### 4. Implementation Steps
Step-by-step how to implement each acceptance criterion

### 5. Tests
What test cases to add for each acceptance criterion

## Guidelines
- Be SPECIFIC about file paths
- Focus on ACTIONABLE steps
- Keep response under 3000 characters

## Architecture Review Considerations

Before finalizing your plan, consider:

- Is there a simpler approach than the first one that comes to mind?
- Does the change fit into the existing architecture?
- Does it follow existing architectural patterns in the codebase?
- Are responsibilities properly separated (single responsibility principle)?
- Does it introduce tight coupling between unrelated modules?
- Could this decision create technical debt or scaling problems?
- Have you estimated effort and flagged if the card seems larger than expected?
- Should architectural decisions be recorded (ADRs)?
- Are you thinking about backward compatibility and breaking changes?""",
            expected_output="Structured implementation plan addressing all acceptance criteria",
            agent=self.architect_agent(),
        )

    def advisor_task(self) -> Task:
        return Task(
            description="""## Task: Risk Analysis

Based on the implementation plan from the previous task, analyze potential risks.

Provide:
1. RISKS: List of potential issues (breaking changes, performance, security)
2. MITIGATIONS: How to address each risk
3. TESTING: What tests should be added to catch these issues

Output as structured markdown.""",
            expected_output="Risk analysis with mitigations",
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
