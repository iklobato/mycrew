"""Unit tests for code_pipeline.settings."""

import os

import pytest

from code_pipeline.settings import (
    PipelineContext,
    get_pipeline_context,
    get_settings,
    init_settings_from_config,
    set_pipeline_context,
)


def test_get_settings_returns_singleton():
    """get_settings returns same instance on multiple calls."""
    a = get_settings()
    b = get_settings()
    assert a is b


def test_pipeline_context_defaults():
    """PipelineContext has default empty strings and False booleans."""
    ctx = PipelineContext()
    assert ctx.repo_path == ""
    assert ctx.github_repo == ""
    assert ctx.issue_url == ""
    assert ctx.serper_enabled is False
    assert ctx.programmatic is False


def test_pipeline_context_frozen():
    """PipelineContext is frozen; assignment raises."""
    ctx = PipelineContext(repo_path="/x", github_repo="a/b")
    with pytest.raises((AttributeError, ValueError)):  # Pydantic frozen model
        ctx.repo_path = "/y"


def test_set_and_get_pipeline_context():
    """set_pipeline_context and get_pipeline_context roundtrip."""
    ctx = PipelineContext(
        repo_path="/abs/repo",
        github_repo="owner/repo",
        issue_url="https://github.com/o/r/issues/1",
        serper_enabled=True,
    )
    set_pipeline_context(ctx)
    try:
        result = get_pipeline_context()
        assert result.repo_path == os.path.abspath("/abs/repo")
        assert result.github_repo == "owner/repo"
        assert result.issue_url == "https://github.com/o/r/issues/1"
        assert result.serper_enabled is True
    finally:
        set_pipeline_context(None)


def test_get_pipeline_context_none_returns_default():
    """get_pipeline_context when not set returns default context."""
    set_pipeline_context(None)
    ctx = get_pipeline_context()
    assert ctx.repo_path == os.path.abspath(os.getcwd())
    assert ctx.github_repo == ""
    assert ctx.issue_url == ""


def test_init_settings_from_config_api_keys(monkeypatch):
    """init_settings_from_config updates api_keys from config."""
    monkeypatch.setenv("TEST_GH_TOKEN", "secret123")
    init_settings_from_config(
        {
            "api_keys": {
                "github_token": "${TEST_GH_TOKEN}",
            },
        }
    )
    # Settings singleton is updated
    stg = get_settings()
    assert stg.github_token == "secret123"


def test_init_settings_from_config_logging():
    """init_settings_from_config updates logging level."""
    init_settings_from_config(
        {
            "logging": {
                "level": "DEBUG",
            },
        }
    )
    stg = get_settings()
    assert stg.code_pipeline_log_level == "DEBUG"
