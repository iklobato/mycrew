"""Base crew class with automatic logging."""

import logging
from abc import ABC, abstractmethod
from typing import Any

from crewai import Crew

logger = logging.getLogger("mycrew")


class BaseCrew(ABC):
    """Base crew with automatic logging for start/end."""

    name: str = "Crew"

    @abstractmethod
    def crew(self) -> Crew:
        """Return the Crew instance - override in subclasses."""
        pass

    def run(self, inputs: dict) -> Any:
        """Run crew with automatic logging."""
        logger.info(f"Starting {self.name}...")
        result = self.crew().kickoff(inputs=inputs)
        logger.info(f"{self.name} done")
        return result
