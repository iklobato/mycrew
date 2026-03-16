"""Tests for app."""

from app import hello, add


def test_hello():
    assert hello() == "Hello, World!"


def test_add():
    assert add(1, 2) == 3
    assert add(-1, 1) == 0
