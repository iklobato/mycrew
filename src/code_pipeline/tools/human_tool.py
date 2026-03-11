"""Human-in-the-loop tool for clarifying ambiguous aspects of a task."""

import logging
import re
import sys

from crewai.tools import tool
from rich.console import Console
from rich.syntax import Syntax

logger = logging.getLogger(__name__)


def _print_with_highlighted_code(text: str) -> None:
    """Print text, rendering markdown code blocks (```lang ... ```) with syntax highlighting."""
    console = Console()
    pattern = r"```(\w*)\n(.*?)```"
    matches = list(re.finditer(pattern, text, re.DOTALL))
    if not matches:
        console.print(text)
        return
    last_end = 0
    for m in matches:
        if m.start() > last_end:
            console.print(text[last_end : m.start()])
        lang = (m.group(1) or "text").strip().lower()
        code = m.group(2).rstrip()
        if lang in ("text", "plain"):
            console.print(code)
        else:
            try:
                syntax = Syntax(code, lang, theme="monokai", line_numbers=False)
                console.print(syntax)
            except Exception:
                console.print(code)
        last_end = m.end()
    if last_end < len(text):
        console.print(text[last_end:])


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
    The question parameter is the ONLY text the human sees. You MUST include 4-6
    options (Option A, Option B, etc.) with code snippets in ```language format —
    never pass a bare question without options. Use this tool when the task is
    ambiguous. Call once per question. Order options from best to least preferred.
    """
    print(" CLARIFICATION NEEDED")
    print(f"{'─' * 64}")
    _print_with_highlighted_code(question)
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
