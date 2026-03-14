from abc import abstractmethod
from typing import List, ClassVar

from crewai import Agent, Crew, Task


class ABCrew:
    """Abstract base class for all crews.

    Subclasses must define the required agents and tasks via the
    ``required_agents`` and ``required_tasks`` properties.  The concrete
    implementation of ``_build_agent`` and ``_build_task`` is provided by the
    concrete base class.
    """

    stage: ClassVar[str] = ""  # Must be set by subclasses

    @property
    @abstractmethod
    def required_agents(self) -> List[str]:
        """List of agent keys this crew requires."""
        pass

    @property
    @abstractmethod
    def required_tasks(self) -> List[str]:
        """List of task keys this crew requires."""
        pass

    @abstractmethod
    def _build_agent(self, agent_key: str) -> Agent:
        """Build an agent for the given key."""
        pass

    @abstractmethod
    def _build_task(self, task_key: str) -> Task:
        """Build a task for the given key."""
        pass

    @abstractmethod
    def crew(self) -> Crew:
        """Return the Crew instance with agents and tasks."""
        pass
