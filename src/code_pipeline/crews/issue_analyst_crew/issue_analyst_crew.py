"""Issue Analyst crew: parses raw issue cards into structured requirements."""

from typing import List

from crewai import Agent, Crew, Process, Task
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai.project import CrewBase, agent, crew, task


@CrewBase
class IssueAnalystCrew:
    """Issue Analyst crew: extracts structured requirements from issue cards."""

    agents: List[BaseAgent]
    tasks: List[Task]

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def issue_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config["issue_analyst"],  # type: ignore[index]
            tools=[],
            verbose=True,
        )

    @task
    def analyze_task(self) -> Task:
        return Task(
            config=self.tasks_config["analyze_task"],  # type: ignore[index]
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
