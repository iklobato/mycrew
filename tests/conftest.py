"""Shared pytest fixtures and configuration."""

import pytest


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "integration: marks tests requiring running server and/or external APIs (deselect with '-m \"not integration\"')",
    )


@pytest.fixture(autouse=True)
def webhook_env(monkeypatch):
    """Set default webhook-related env vars for tests."""
    monkeypatch.setenv("DEFAULT_DRY_RUN", "false")
    monkeypatch.setenv("DEFAULT_BRANCH", "main")


@pytest.fixture
def github_token(monkeypatch):
    """Set GITHUB_TOKEN for tests that need it."""
    monkeypatch.setenv("GITHUB_TOKEN", "test-token")
