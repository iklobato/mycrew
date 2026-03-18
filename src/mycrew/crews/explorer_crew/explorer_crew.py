"""Explorer crew: repo exploration."""

import os
from crewai import Agent, Crew, LLM, Process, Task

from mycrew.llm import ModelMappings
from mycrew.settings import Settings, get_pipeline_context


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
    return "\n".join(lines[:100])  # Limit to first 100 lines


class ExplorerCrew:
    """Explorer crew: repo exploration."""

    def __init__(self):
        self.settings = Settings()

    def explorer_agent(self) -> Agent:
        return Agent(
            llm=LLM(
                model=ModelMappings.EXPLORE.value.openrouter_model,
                api_key=self.settings.openrouter_api_key,
            ),
            role="Codebase Architect",
            goal="Map codebase structure to implementation requirements",
            backstory="""You are a principal engineer who can quickly understand large
codebases. You identify not just WHAT files exist, but their roles,
dependencies, and how they relate to feature implementation.""",
        )

    def explore_task(self) -> Task:
        ctx = get_pipeline_context()
        repo_structure = get_repo_structure(ctx.repo_path)
        return Task(
            description=f"""## Task: Explore Codebase

Explore the codebase to understand its structure for implementing the following requirements:

**Requirements:**
{{issue_analysis}}

## Repository Structure (first 100 lines):
{repo_structure}

## Required Output

For each requirement, provide:

### 1. AFFECTED FILES
Specific file paths that need changes (existing files to modify)

### 2. NEW FILES
Any new files that should be created

### 3. DEPENDENCIES
Any new dependencies required (or confirmation none needed)

### 4. TEST LOCATIONS
Where tests should be added - identify existing test directories and patterns

### 5. CONFIG CHANGES
Any configuration updates needed

### 6. MIGRATION NOTES
If existing data/models need updating, describe the migration

Output as structured markdown with clear sections for each requirement point.""",
            expected_output="Structured exploration with affected files, new files, dependencies, test locations, config changes, and migration notes",
            agent=self.explorer_agent(),
        )

    def crew(self) -> Crew:
        return Crew(
            agents=[self.explorer_agent()],
            tasks=[self.explore_task()],
            process=Process.sequential,
            memory=False,
        )
