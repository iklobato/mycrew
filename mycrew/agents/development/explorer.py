"""Explorer crew: repo exploration."""

import os

from crewai import Agent, Crew, LLM, Process, Task

from mycrew.shared.llm import ModelMappings
from mycrew.shared.settings import Settings, get_pipeline_context
from mycrew.shared.tools import DirectoryReadTool, FileReadTool
from mycrew.shared.base import BaseCrew


def get_repo_structure(repo_path: str, max_depth: int = 3) -> str:
    """Generate a tree-like structure of the repo without truncation."""
    lines = []
    for root, dirs, files in os.walk(repo_path):
        level = root.replace(repo_path, "").count(os.sep)
        if level > max_depth:
            continue
        indent = "  " * level
        folder_name = os.path.basename(root)
        if folder_name.startswith("."):
            continue
        lines.append(f"{indent}{folder_name}/")
        if level < max_depth:
            file_indent = "  " * (level + 1)
            for f in sorted(files):
                if f.startswith("."):
                    continue
                lines.append(f"{file_indent}{f}")
    return "\n".join(lines)


class ExplorerCrew(BaseCrew):
    """Explorer crew: repo exploration."""

    name = "Explorer"

    def __init__(self):
        self.settings = Settings()

    def explorer_agent(self) -> Agent:
        ctx = get_pipeline_context()
        return Agent(
            llm=LLM(
                model=ModelMappings.EXPLORE.value.openrouter_model,
                api_key=self.settings.openrouter_api_key,
            ),
            role="Codebase Explorer",
            goal="Understand project structure, read relevant files, identify patterns",
            backstory="""You are a principal engineer who quickly understands large codebases.
You identify relevant files, read their contents, and understand existing patterns,
tests, and architecture decisions.""",
            tools=[
                DirectoryReadTool(directory=ctx.repo_path),
                FileReadTool(),
            ],
            max_execution_time=600,
        )

    def explore_task(self) -> Task:
        ctx = get_pipeline_context()
        repo_structure = get_repo_structure(ctx.repo_path)
        return Task(
            description=f"""## Task: Deep Codebase Exploration

You MUST follow this systematic process to understand the codebase:

### Step 1: Project Overview
Read these files to understand the project:
- pyproject.toml / setup.py / setup.cfg → tech stack, dependencies
- README.md / README.rst → project purpose and usage
- main.py / __main__.py / app.py → entry point
- config.py / settings.py → configuration

### Step 2: Test Patterns
Read 3-5 test files in tests/ directory to understand:
- Testing framework (pytest, unittest)
- Test file organization and naming
- Fixtures and mocks usage
- Assertion patterns

### Step 3: Architecture Exploration
Explore source directories to understand:
- Code organization (models/, services/, utils/, core/)
- Data models and schemas
- API patterns
- Error handling patterns
- Import conventions

### Step 4: Issue-Relevant Files
Based on the requirements below, identify:
- Files that need to be modified
- Files that need to be created
- Existing implementations to extend

### Requirements to Implement:
{{issue_analysis}}

### Repository Structure:
{repo_structure}

## Your Process

1. Use DirectoryReadTool to explore the full repo structure
2. Read pyproject.toml, README.md, and entry point files
3. Read 3-5 test files to understand testing patterns
4. Read relevant source files for the issue
5. Provide detailed analysis

## Output Format

### Project Overview
- Tech Stack: [from pyproject.toml]
- Dependencies: [key dependencies]
- Entry Point: [main file]
- Configuration: [config approach]

### Code Patterns
- Testing: [pytest fixtures, Mock usage]
- Models: [Pydantic, dataclasses, etc.]
- Services: [business logic patterns]
- Error Handling: [exception patterns]
- Imports: [absolute vs relative]

### Relevant Files for Implementation
For each file:
- Path: xerxes/cache.py
- Purpose: Cache implementation
- Key Code: [important code snippets]
- Changes Needed: [what to modify]

### Implementation Recommendations
- New files to create
- Existing files to modify
- Test strategy
- Patterns to follow
- Dependencies (if any)

## Environment & Setup Considerations

Before implementing, verify:

- Is your local environment up to date (latest branch)?
- Are environment variables or config changes needed?
- Are dependencies installed and up to date?
- Is the feature flag, if any, configured locally?
- Do you know how to run the relevant parts of the app and tests locally?
- Are you following existing patterns and conventions in the codebase?
- Are new dependencies vetted and necessary?
""",
            expected_output="Deep exploration with project overview, code patterns, relevant files, and implementation recommendations",
            agent=self.explorer_agent(),
        )

    def crew(self) -> Crew:
        return Crew(
            agents=[self.explorer_agent()],
            tasks=[self.explore_task()],
            process=Process.sequential,
            memory=False,
        )
