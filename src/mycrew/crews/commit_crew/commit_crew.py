"""Commit crew: runs git add, commit, then pushes and creates PR."""

from crewai import Agent, Crew, LLM, Process, Task

from mycrew.llm import ModelMappings
from mycrew.settings import Settings
from mycrew.crews.base import BaseCrew


class CommitCrew(BaseCrew):
    """Commit crew: creates branch, commits, then pushes and creates PR via publish agent."""

    name = "Commit"

    def __init__(self):
        self.settings = Settings()

    def git_agent(self) -> Agent:
        return Agent(
            llm=LLM(
                model=ModelMappings.COMMIT.value.openrouter_model,
                api_key=self.settings.openrouter_api_key,
            ),
            role="DevOps Engineer",
            goal="Safely create branches and commits with proper conventions",
            backstory="""You are a DevOps engineer who ensures all Git operations follow
team conventions. You handle errors gracefully and provide clear feedback.
You use Conventional Commits format.""",
        )

    def publish_agent(self) -> Agent:
        return Agent(
            llm=LLM(
                model=ModelMappings.PUBLISH.value.openrouter_model,
                api_key=self.settings.openrouter_api_key,
            ),
            role="Release Engineer",
            goal="Push branch and create PR following team workflows",
            backstory="""You are a release engineer who creates PRs using gh CLI.
You ensure PRs have proper titles, descriptions, and labels.""",
        )

    def commit_task(self) -> Task:
        return Task(
            description="""## Task: Create Branch and Commit

**Implementation Summary:**
{implementation}

**Review Verdict:**
{review}

**Working Directory:** {repo_path}

## Process

1. Run `git status` to see all changes
2. Create branch: `feature/issue-{issue_number}-implementation`
   - Use lowercase, hyphens only
3. Stage files: `git add -A` then `git reset -- .code_pipeline`
4. Create commit with Conventional Commits format:
   - `feat:` for new features
   - `fix:` for bug fixes
   - `refactor:` for code improvements
   - `test:` for test additions
   - `docs:` for documentation
5. Output the branch name and commit hash

## Error Handling

- If merge conflicts: output "CONFLICTS: [list files]"
- If git not available: output "SKIPPED: git not available"
- If no changes: output "SKIPPED: no changes to commit"

## Output Format

```
Branch: feature/issue-838-description
Commit: feat: add system profile visibility toggle
```
Keep under 2000 characters.""",
            expected_output="Git branch and commit information",
            agent=self.git_agent(),
        )

    def publish_task(self) -> Task:
        return Task(
            description="""## Task: Push Branch and Create PR

**Review Verdict:**
{review}

**Working Directory:** {repo_path}

## Process

1. Push branch to remote: `git push -u origin feature/branch-name`
2. Create PR using gh CLI:
   ```
   gh pr create --title "feat: description" --body "Description"
   ```

## Error Handling

- If github_repo not available: output "SKIPPED: github_repo not available"
- If PR creation fails: output "ERROR: [reason]"

## Output Format

```
PR: https://github.com/owner/repo/pull/123
```

Or if skipped:
```
SKIPPED: github_repo not available
```""",
            expected_output="PR URL or skip message",
            agent=self.publish_agent(),
            context=[self.commit_task()],
        )

    def crew(self) -> Crew:
        return Crew(
            agents=[self.git_agent(), self.publish_agent()],
            tasks=[self.commit_task(), self.publish_task()],
            process=Process.sequential,
            memory=False,
        )
