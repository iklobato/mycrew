"""PR Review crew: comprehensive code review with 10 parallel agents + signoff."""

from crewai import Agent, Crew, Process, Task

from mycrew.shared.settings import Settings
from mycrew.shared.base import BaseCrew
from mycrew.review.crews.pr_review_crew.agents import (
    ContextAgent,
    ArchitectureAgent,
    CorrectnessAgent,
    SecurityAgent,
    PerformanceAgent,
    TestCoverageAgent,
    ReadabilityAgent,
    ConsistencyAgent,
    ErrorHandlingAgent,
    DocumentationAgent,
    SignoffAgent,
)


class PRReviewCrew(BaseCrew):
    """Comprehensive PR review with 10 parallel agents and final signoff."""

    name = "PRReview"

    def __init__(self):
        self.settings = Settings()
        self.context_agent = ContextAgent()
        self.architecture_agent = ArchitectureAgent()
        self.correctness_agent = CorrectnessAgent()
        self.security_agent = SecurityAgent()
        self.performance_agent = PerformanceAgent()
        self.test_coverage_agent = TestCoverageAgent()
        self.readability_agent = ReadabilityAgent()
        self.consistency_agent = ConsistencyAgent()
        self.error_handling_agent = ErrorHandlingAgent()
        self.documentation_agent = DocumentationAgent()
        self.signoff_agent = SignoffAgent()

    def context_agent_method(self) -> Agent:
        return self.context_agent.agent()

    def context_task(self) -> Task:
        return self.context_agent.task()

    def architecture_agent_method(self) -> Agent:
        return self.architecture_agent.agent()

    def architecture_task(self) -> Task:
        return self.architecture_agent.task()

    def correctness_agent_method(self) -> Agent:
        return self.correctness_agent.agent()

    def correctness_task(self) -> Task:
        return self.correctness_agent.task()

    def security_agent_method(self) -> Agent:
        return self.security_agent.agent()

    def security_task(self) -> Task:
        return self.security_agent.task()

    def performance_agent_method(self) -> Agent:
        return self.performance_agent.agent()

    def performance_task(self) -> Task:
        return self.performance_agent.task()

    def test_coverage_agent_method(self) -> Agent:
        return self.test_coverage_agent.agent()

    def test_coverage_task(self) -> Task:
        return self.test_coverage_agent.task()

    def readability_agent_method(self) -> Agent:
        return self.readability_agent.agent()

    def readability_task(self) -> Task:
        return self.readability_agent.task()

    def consistency_agent_method(self) -> Agent:
        return self.consistency_agent.agent()

    def consistency_task(self) -> Task:
        return self.consistency_agent.task()

    def error_handling_agent_method(self) -> Agent:
        return self.error_handling_agent.agent()

    def error_handling_task(self) -> Task:
        return self.error_handling_agent.task()

    def documentation_agent_method(self) -> Agent:
        return self.documentation_agent.agent()

    def documentation_task(self) -> Task:
        return self.documentation_agent.task()

    def signoff_task(self) -> Task:
        return self.signoff_agent.task(
            context=[
                self.context_task(),
                self.architecture_task(),
                self.correctness_task(),
                self.security_task(),
                self.performance_task(),
                self.test_coverage_task(),
                self.readability_task(),
                self.consistency_task(),
                self.error_handling_task(),
                self.documentation_task(),
            ]
        )

    def crew(self) -> Crew:
        return Crew(
            agents=[
                self.context_agent_method(),
                self.architecture_agent_method(),
                self.correctness_agent_method(),
                self.security_agent_method(),
                self.performance_agent_method(),
                self.test_coverage_agent_method(),
                self.readability_agent_method(),
                self.consistency_agent_method(),
                self.error_handling_agent_method(),
                self.documentation_agent_method(),
                self.signoff_agent.agent(),
            ],
            tasks=[
                self.context_task(),
                self.architecture_task(),
                self.correctness_task(),
                self.security_task(),
                self.performance_task(),
                self.test_coverage_task(),
                self.readability_task(),
                self.consistency_task(),
                self.error_handling_task(),
                self.documentation_task(),
                self.signoff_task(),
            ],
            process=Process.sequential,
            memory=False,
        )
