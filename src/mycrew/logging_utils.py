"""Logging utilities following SOLID principles.

This module provides structured logging for the pipeline with:
- SRP: Dedicated logging functionality separate from business logic
- OCP: Extensible via decorators and context managers
- DIP: Abstractions (ILogger) for testability
- ISP: Focused interfaces (log_input, log_output, log_step)
"""

import logging
from typing import Any, Protocol

logger = logging.getLogger(__name__)


class ILogger(Protocol):
    """Logging interface following DIP - depend on abstractions."""

    def log_input(self, context: str, data: Any) -> None: ...
    def log_output(self, context: str, data: Any) -> None: ...
    def log_step(self, context: str, message: str) -> None: ...


class PipelineLogger:
    """Concrete logging implementation for pipeline operations.

    Follows SRP - only responsible for logging formatting and output.
    """

    MAX_LENGTH = 1000

    @staticmethod
    def to_one_line(text: Any, max_length: int = MAX_LENGTH) -> str:
        """Convert multi-line text to one line for logging.

        Args:
            text: Any data to convert
            max_length: Maximum length of output (default 1000)

        Returns:
            Single-line string suitable for logging
        """
        if text is None:
            return "None"
        s = str(text).strip()
        one_line = " ".join(s.split())
        if len(one_line) > max_length:
            one_line = one_line[:max_length] + "..."
        return one_line

    def log_input(self, context: str, data: Any) -> None:
        """Log input data at DEBUG level.

        Args:
            context: Step or component name (e.g., 'EXPLORE', 'RepoShellTool')
            data: Input data to log
        """
        logger.debug(f"[{context}] INPUT: {self.to_one_line(data)}")

    def log_output(self, context: str, data: Any) -> None:
        """Log output data at DEBUG level.

        Args:
            context: Step or component name
            data: Output data to log
        """
        logger.debug(f"[{context}] OUTPUT: {self.to_one_line(data)}")

    def log_step(self, context: str, message: str) -> None:
        """Log step-level message at INFO level.

        Args:
            context: Step name (e.g., 'EXPLORE', 'ARCHITECT')
            message: Message to log
        """
        logger.info(f"[{context}] {message}")


class StepContext:
    """Context manager for step-specific logging.

    Provides OCP extension - logging behavior can be extended
    without modifying individual step implementations.

    Usage:
        with StepContext("EXPLORE") as step:
            step.log_input(inputs)
            # ... do work ...
            step.log_output(result)
    """

    def __init__(self, step_name: str, log: PipelineLogger | None = None):
        """Initialize step context.

        Args:
            step_name: Name of the step (e.g., 'EXPLORE', 'ANALYZE')
            log: Optional logger instance (uses PipelineLogger default)
        """
        self.step_name = step_name.upper()
        self.log = log or PipelineLogger()

    def __enter__(self):
        """Enter context - log step start."""
        self.log.log_step(self.step_name, f"=== STARTING: {self.step_name} ===")
        return self

    def __exit__(self, *args):
        """Exit context - log step completion."""
        self.log.log_step(self.step_name, f"=== COMPLETED: {self.step_name} ===")

    def log_input(self, data: Any) -> None:
        """Log input data for this step."""
        self.log.log_input(self.step_name, data)

    def log_output(self, data: Any) -> None:
        """Log output data for this step."""
        self.log.log_output(self.step_name, data)


def log_tool_calls(cls):
    """Decorator to add logging to tool classes.

    Follows OCP - adds logging behavior without modifying tool implementations.

    Usage:
        @log_tool_calls
        class MyTool(BaseTool):
            def _run(self, ...):
                ...

    Args:
        cls: Tool class to decorate

    Returns:
        Decorated class with logging
    """
    original_run = cls._run

    def logged_run(self, *args, **kwargs):
        tool_name = self.__class__.__name__
        log = PipelineLogger()

        # Log input
        input_data = args[1] if len(args) > 1 else kwargs
        log.log_input(tool_name, input_data)

        # Execute original method
        result = original_run(self, *args, **kwargs)

        # Log output
        log.log_output(tool_name, result)

        return result

    cls._run = logged_run
    return cls


# Module-level convenience function
def to_one_line(text: Any, max_length: int = 1000) -> str:
    """Convert multi-line text to one line for logging.

    Args:
        text: Any data to convert
        max_length: Maximum length of output (default 1000)

    Returns:
        Single-line string suitable for logging
    """
    return PipelineLogger.to_one_line(text, max_length)


# Global instance for convenience
pipeline_logger = PipelineLogger()
