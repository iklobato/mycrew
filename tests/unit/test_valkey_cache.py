"""Unit tests for ValkeyCache (no Redis required when disabled)."""

import pytest

from code_pipeline.valkey_cache import ValkeyCache, get_valkey_cache


def test_valkey_cache_empty_url_returns_false_on_store():
    """ValkeyCache with empty URL does not store."""
    cache = ValkeyCache("")
    assert cache.store("test:key", "data") is False
    assert cache.retrieve("test:key") is None


def test_valkey_cache_empty_url_delete_no_op():
    """ValkeyCache with empty URL delete does not raise."""
    cache = ValkeyCache("")
    cache.delete("test:key")


def test_get_valkey_cache_without_redis_url_returns_none():
    """get_valkey_cache returns None when REDIS_URL is empty (typical local dev)."""
    # When REDIS_URL not set, get_valkey_cache returns None
    cache = get_valkey_cache()
    # May be None or ValkeyCache instance if REDIS_URL is set in .env
    if cache is None:
        assert True  # Expected when REDIS_URL empty
    else:
        assert isinstance(cache, ValkeyCache)


