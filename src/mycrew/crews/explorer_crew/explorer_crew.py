"""Explorer crew: repo exploration."""

import os

from crewai import Agent, Crew, LLM, Process, Task

from mycrew.llm import ModelMappings
from mycrew.settings import Settings, get_pipeline_context
from mycrew.tools import DirectoryReadTool, FileReadTool


def get_repo_structure(repo_path: str, max_depth: int = 2) -> str:
    """Generate a tree-like structure of the repo."""
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
    return "\n".join(lines[:100])


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
            role="Codebase Explorer",
            goal="Understand project structure, read relevant files, identify patterns",
            backstory="""You are a principal engineer who quickly understands large codebases.
You identify relevant files, read their contents, and understand existing patterns,
tests, and architecture decisions.""",
            tools=[
                DirectoryReadTool(directory=ctx.repo_path),
                FileReadTool(),
            ],
        )

    def explore_task(self) -> Task:
        ctx = get_pipeline_context()
        repo_structure = get_repo_structure(ctx.repo_path)
        return Task(
            description=f"""## Task: Explore Codebase

Explore the codebase to understand its structure for implementing:

**Requirements:**
{{issue_analysis}}

## Repository Structure:
{repo_structure}

## Your Process

1. Use DirectoryReadTool to explore the repo structure
2. Identify 5-10 most relevant files for the issue
3. Use FileReadTool to read key files:
   - Existing patterns and conventions
   - Test file structure and patterns
   - Architecture decisions
   - Model/schema definitions
   - API/service patterns

## Output Format

For each relevant file found:

### File: path/to/file.py
- **Purpose**: What this file does
- **Key Patterns**: Code patterns used
- **Relevant Code**: Important code snippets for implementation

## Also Provide:
- New files that should be created
- Test locations and patterns
- Dependencies needed
- Configuration changes""",
            expected_output="Structured exploration with file contents, patterns, and architecture analysis",
            agent=self.explorer_agent(),
        )

    def crew(self) -> Crew:
        return Crew(
            agents=[self.explorer_agent()],
            tasks=[self.explore_task()],
            process=Process.sequential,
            memory=False,
        )
