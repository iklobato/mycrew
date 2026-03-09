"""Human-in-the-loop tool for clarifying ambiguous aspects of a task."""

import logging
import sys

from crewai.tools import tool

logger = logging.getLogger(__name__)


def _is_interactive() -> bool:
    """True if stdin is attached to a TTY and we can safely use input()."""
    try:
        return sys.stdin.isatty()
    except Exception as e:
        logger.error("sys.stdin.isatty() failed: %s", e, exc_info=True)
        return False


@tool("ask_human")
def ask_human(question: str) -> str:
    """
    Ask the human operator a clarifying question and return their answer.
    Use this tool whenever any aspect of the task is ambiguous: scope, constraints,
    tech stack choices, expected behavior, edge cases, or acceptance criteria.
    Call this tool once per question — never bundle multiple questions in one call.
    Always provide 2–4 concrete options when possible, ordered from top
    recommendation to last (best first, least preferred last). The human can pick quickly.
    """
    print(f"\n{'─' * 64}")
    print(f"❓  CLARIFICATION NEEDED")
    print(f"{'─' * 64}")
    print(question)
    print(f"{'─' * 64}")

    if not _is_interactive():
        logger.info("ask_human: non-interactive mode, skipping input")
        print(
            "(Non-interactive mode: stdin not attached. Skipping human input. "
            "Run from a terminal for interactive clarification.)"
        )
        return "(no answer - non-interactive mode, continuing without clarification)"

    try:
        answer = input("Your answer: ").strip()
        return answer if answer else "(no answer provided)"
    except EOFError as e:
        logger.error("ask_human: EOFError (stdin closed): %s", e, exc_info=True)
        print("(stdin closed, continuing without answer)")
        return "(no answer - stdin closed)"
