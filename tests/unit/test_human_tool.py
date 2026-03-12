"""Tests for human_tool module."""

from unittest.mock import patch

from code_pipeline.tools.human_tool import ask_human


@patch("code_pipeline.settings.get_pipeline_context")
def test_ask_human_programmatic_returns_assumed_answer(mock_get_context):
    """ask_human returns canned response when programmatic is True."""
    ctx = type("Ctx", (), {"programmatic": True})()
    mock_get_context.return_value = ctx

    result = ask_human.run(question="Where should we add the endpoint?")

    assert result == (
        "(Programmatic mode: proceeding with best assumption from exploration. "
        "Use Option A / recommended approach.)"
    )
    mock_get_context.assert_called_once()
