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
            description="""Create a feature branch and commit changes based on the implementation. Keep response under 2000 characters.

Implementation summary: {implementation}
Review verdict: {review}
Working directory: {repo_path}

Steps:
1. git status - see what files changed
2. git stash -u - stash all changes
3. git checkout main (or develop)
4. git checkout -b feature/issue-description
5. git stash pop
6. git add -A && git reset -- .code_pipeline
7. git commit -m "feat: implemented issue"

Use Conventional Commits format. Exclude .code_pipeline from commit.""",
            expected_output="Git commit output with branch name",
            agent=self.git_agent(),
        )

    def publish_task(self) -> Task:
        return Task(
            description="""After commit, push branch and create PR.

Review verdict: {review}
Working directory: {repo_path}

If github_repo is not available, output 'PR creation skipped'.
Otherwise, push branch and create PR using gh CLI.""",
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
