"""Unit tests for mycrew.models."""

import pytest

from mycrew.models import User


def test_user_empty_id_raises():
    """User with empty id raises ValueError."""
    with pytest.raises(ValueError, match="User ID cannot be empty"):
        User(id="")
    with pytest.raises(ValueError, match="User ID cannot be empty"):
        User(id="   ")


def test_user_valid_creates():
    """User with valid id and api_keys creates successfully."""
    u = User(id="alice", api_keys={"github": "gh123"})
    assert u.id == "alice"
    assert u.api_keys == {"github": "gh123"}
    assert u.created_at is not None


def test_user_strips_id():
    """User id is stripped of whitespace."""
    u = User(id="  bob  ")
    assert u.id == "bob"


def test_user_default_api_keys():
    """User api_keys defaults to empty dict."""
    u = User(id="charlie")
    assert u.api_keys == {}
