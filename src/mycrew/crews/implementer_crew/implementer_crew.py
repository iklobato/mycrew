"""Implementer crew: executes implementation plan."""

import json
import logging
import os
import re

from crewai import Agent, Crew, LLM, Process, Task

from mycrew.settings import Settings


logger = logging.getLogger("mycrew")


def parse_code_blocks(text: str) -> list[dict[str, str]]:
    """Parse markdown code blocks into file specs.

    Expected format:
    ```json
    [
      {"path": "xerxes/utils/hello.py", "content": "..."},
      {"path": "xerxes/models/user.py", "content": "..."}
    ]
    ```
    """
    files = []

    json_match = re.search(r"```json\s*(\[[\s\S]*?\])\s*```", text)
    if json_match:
        try:
            data = json.loads(json_match.group(1))
            for item in data:
                if isinstance(item, dict) and "path" in item and "content" in item:
                    files.append(item)
            if files:
                return files
        except json.JSONDecodeError:
            pass

    for line in text.split("\n"):
        if "|" in line:
            parts = line.split("|")
            if len(parts) >= 2:
                path = parts[0].strip()
                content = "|".join(parts[1:]).strip()
                if path and content and not path.startswith("#"):
                    files.append({"path": path, "content": content})

    return files


def write_files_from_specs(files: list[dict[str, str]], base_path: str) -> list[str]:
    """Write files to disk based on specs."""
    written = []
    for spec in files:
        rel_path = spec["path"]
        content = spec["content"]

        if not rel_path.startswith("xerxes/") and not rel_path.startswith("src/"):
            rel_path = f"xerxes/{rel_path}"

        full_path = os.path.join(base_path, rel_path)

        try:
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w") as f:
                f.write(content)
            written.append(rel_path)
            logger.info(f"Wrote file: {rel_path}")
        except Exception as e:
            logger.error(f"Failed to write {rel_path}: {e}")

    return written


class ImplementerCrew:
    """Implementer crew: executes implementation plan by outputting structured code."""

    def __init__(self):
        self.settings = Settings()

    def implementer_agent(self) -> Agent:
        return Agent(
            llm=LLM(
                model="openrouter/anthropic/claude-3.5-sonnet",
                api_key=self.settings.openrouter_api_key,
            ),
            role="Software Implementer",
            goal="Write code files based on implementation plan",
            backstory="Expert at writing code that solves problems",
            tools=[],
            max_iter=2,
            max_execution_time=120,
        )

    def implement_task(self) -> Task:
        return Task(
            description="""Execute the implementation plan. Issue: {plan}.
Working directory: {repo_path}.

IMPORTANT: Output your implementation as a JSON array of files to create.
Each file must have:
- "path": relative path from repo root (e.g., "xerxes/utils/hello.py")
- "content": the complete file content

Format your response as:
```json
[
  {"path": "xerxes/utils/hello.py", "content": "print('hello world')"},
  {"path": "xerxes/models/user.py", "content": "class User:\\n    pass"}
]
```

Do NOT write anything else - only output the JSON code block.""",
            expected_output="JSON array of files created with paths and content",
            agent=self.implementer_agent(),
        )

    def crew(self) -> Crew:
        return Crew(
            agents=[self.implementer_agent()],
            tasks=[self.implement_task()],
            process=Process.sequential,
            memory=False,
        )
