"""Commit crew: runs git add, commit, then pushes and creates PR."""

from crewai import Agent, Crew, LLM, Process, Task

from mycrew.llm import ModelMappings
from mycrew.settings import Settings


class CommitCrew:
    """Commit crew: creates branch, commits, then pushes and creates PR via publish agent."""

    def __init__(self):
        self.settings = Settings()

    def git_agent(self) -> Agent:
        return Agent(
            llm=LLM(
                model=ModelMappings.COMMIT.value.openrouter_model,
                api_key=self.settings.openrouter_api_key,
            ),
            role="Git Agent",
            goal="Create feature branch and commit changes",
            backstory="Expert at git operations",
        )

    def publish_agent(self) -> Agent:
        return Agent(
            llm=LLM(
                model=ModelMappings.PUBLISH.value.openrouter_model,
                api_key=self.settings.openrouter_api_key,
            ),
            role="Publish Agent",
            goal="Push branch and create PR",
            backstory="Expert at GitHub operations",
        )

    def commit_task(self) -> Task:
        return Task(
            description="""Create a feature branch and commit changes.

Context: {repo_context}

Base branch (branch from): {branch}
Feature branch (create and commit to): {feature_branch}
Dry run: {dry_run}
Issue ID (include in commit message if provided): {issue_id}

Steps:
1. git stash -u  (stash all changes including untracked files)
2. git checkout {branch}  (ensure we're on base branch)
3. git checkout -b {feature_branch}  (create and switch to feature branch)
4. git stash pop  (apply stashed changes to new branch)

If conflicts occur at step 4:
- Run git status to see conflicting files
- For each conflict, open the file and look for <<< === >>> markers
- Keep your changes (the stashed changes), remove conflict markers
- Run git add <file> for each resolved file
- Continue with git stash drop

5. git add -A && git reset -- .code_pipeline
6. git commit -m "your message"

Exclude .code_pipeline from the commit (pipeline state, not application code).
If issue_id is provided, include "fixes #X" or similar in the commit message.

If dry_run is "true", do NOT run git commands. List: the feature branch
you would create, files that would be staged, and the commit message.
If dry_run is "false", run the steps above.

ALWAYS use Conventional Commits format for the commit message:
  <type>[optional scope]: <description>

Conventions:
  - feat: new feature
  - fix: bug fix  
  - docs: documentation only
  - style: formatting, whitespace, no code change
  - refactor: code change that neither fixes nor adds a feature
  - test: adding or updating tests
  - chore: maintenance, deps, tooling
  - perf: performance improvement
  - ci: CI config or scripts

Avoid committing .env, secrets, or large binaries; check git status first.""",
            expected_output="Either the git commit output (including the new branch name) or a message listing the feature branch, files to stage, and proposed commit message (if dry_run).",
            agent=self.git_agent(),
        )

    def publish_task(self) -> Task:
        return Task(
            description="""After the commit is done, publish the branch and create a PR.

Context: {repo_context}
Dry run: {dry_run}
Feature branch: {feature_branch}
Base branch: {branch}
Task: {task}
Implementation: {implementation}
Plan: {plan}
Review_verdict: {review_verdict}

Steps:
1. Check for conflicts: git fetch origin {branch} && git merge-base origin/{branch} HEAD
2. If conflicts exist or branch diverged significantly, analyze and resolve intelligently
3. Merge or rebase as appropriate to ensure clean integration
4. Run tests if test_command is available
5. If dry_run is "true" OR github_repo is empty, do NOT create PR.
   Output: "PR creation skipped (dry_run)" or "PR creation skipped (no github_repo)".
6. If dry_run is "false" AND github_repo is set, push the branch and create the PR.

Return the actual PR URL from the tool output.""",
            expected_output="The actual PR URL (e.g. https://github.com/owner/repo/pull/456) - must contain a real PR number. Or 'PR creation skipped (dry_run)' or 'PR creation skipped (no github_repo)' if applicable.",
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
