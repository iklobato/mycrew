"""Implementer crew: executes implementation plan."""

import json
import logging
import os
import re

from crewai import Agent, Crew, LLM, Process, Task

from mycrew.shared.settings import Settings
from mycrew.shared.base import BaseCrew


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


class ImplementerCrew(BaseCrew):
    """Implementer crew: executes implementation plan by outputting structured code."""

    name = "Implementer"

    def __init__(self):
        self.settings = Settings()

    def implementer_agent(self) -> Agent:
        return Agent(
            llm=LLM(
                model="openrouter/anthropic/claude-3.5-sonnet",
                api_key=self.settings.openrouter_api_key,
            ),
            role="Senior Software Engineer",
            goal="Write complete, working code files from implementation plans",
            backstory="""You are a senior software engineer who writes production-ready code 
that passes review the first time. You follow project conventions, include necessary 
imports, error handling, and type hints. Your code is clean, testable, and maintainable.""",
            tools=[],
            max_iter=2,
            max_execution_time=120,
        )

    def implement_task(self) -> Task:
        return Task(
            description="""## Task: Implement the following plan

**Original Issue Requirements:**
{issue_description}

**Implementation Plan:**
{plan}

**Working Directory:** {repo_path}

## CRITICAL: You MUST implement ALL acceptance criteria from the issue:

1. Robots fetch requests include If-None-Match and/or If-Modified-Since when validators are available
2. HTTP 304 updates cache freshness/expiry without rewriting unchanged body
3. HTTP 200 updates body and validator fields (etag, last_modified) correctly
4. Tests cover 200, 304, and fallback behavior when validators are absent

## Output Format

You MUST output a JSON array of files to create. Each file must have:
- "path": relative path from repo root (e.g., "xerxes/utils/hello.py")
- "content": complete file content as a JSON string

### JSON Format Requirements:
1. Use triple backticks with "json" language tag
2. Escape newlines as \\n, quotes as \", backslashes as \\\\
3. Each file's "content" must be a properly escaped JSON string
4. Include ALL necessary imports, docstrings, and type hints

### Output Format:
```json
[
  {
    "path": "xerxes/utils/hello.py",
    "content": "def hello() -> str:\\n    \\\"\\\"\\\"Return a greeting.\\\"\\\"\\\"\\n    return \\\"Hello, World!\\\"\\n"
  }
]
```

### Before Outputting:
- Verify each file's code is syntactically correct
- Ensure the code addresses ALL acceptance criteria
- Do NOT output anything except the JSON code block

## Implementation Quality Checklist

Before writing each piece of code, consider:

### Simplicity & Design
- Are you avoiding over-engineering?
- Are functions and components small and focused?
- Are you avoiding hardcoded values?

### Correctness & Edge Cases
- Are all edge cases handled (nulls, empty states, boundary values)?
- Are errors handled explicitly, not silently swallowed?

### Security
- Are you validating and sanitizing all inputs?
- Are credentials and secrets in environment variables, never in code?
- Are you enforcing proper authorization, not just authentication?

### Performance
- Are you avoiding unnecessary database calls or API requests?
- Are queries optimized and using appropriate indexes?
- Are you avoiding blocking the main thread?
- Is caching used where it makes sense?

### Observability
- Are you avoiding exposing sensitive data in logs or responses?""",
            expected_output="JSON array of files implementing all acceptance criteria",
            agent=self.implementer_agent(),
        )

    def crew(self) -> Crew:
        return Crew(
            agents=[self.implementer_agent()],
            tasks=[self.implement_task()],
            process=Process.sequential,
            memory=False,
        )
