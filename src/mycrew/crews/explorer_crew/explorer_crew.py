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
            role="Repository Explorer",
            goal="Analyze codebase structure and identify relevant files",
            backstory="Expert at understanding codebases",
        )

    def explore_task(self) -> Task:
        ctx = get_pipeline_context()
        repo_structure = get_repo_structure(ctx.repo_path)
        return Task(
            description=f"""Explore the codebase based on issue requirements. Keep response under 2000 characters.

## Repository Structure (first 100 lines):
{repo_structure}

## Issue requirements: {{issue_analysis}}

Provide:
1. Project structure overview (main directories and their purposes)
2. Key files that are likely relevant to the implementation
3. Tech stack (framework, language, dependencies)
4. Test file locations and patterns
5. Configuration files""",
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
