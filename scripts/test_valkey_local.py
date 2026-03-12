#!/usr/bin/env python
"""Test Valkey integration locally. Run: uv run python scripts/test_valkey_local.py

Set REDIS_URL in .env to test live connection (e.g. financialdata-valkey).
Without REDIS_URL, verifies graceful degradation.
"""

from code_pipeline.settings import get_settings
from code_pipeline.valkey_cache import ValkeyCache, get_valkey_cache


def main() -> None:
    url = get_settings().redis_url
    print("REDIS_URL:", "set" if url and url.strip() else "not set")
    print()

    # Always test empty URL
    cache = ValkeyCache("")
    assert cache.store("test:x", "hi") is False
    assert cache.retrieve("test:x") is None
    print("1. ValkeyCache(empty): store=False, retrieve=None (OK)")
    print()

    # Test get_valkey_cache
    global_cache = get_valkey_cache()
    if global_cache is None:
        print("2. get_valkey_cache(): None (REDIS_URL empty - expected)")
        print()
        print("To test with live Valkey, add to .env:")
        print("  REDIS_URL=rediss://default:PASSWORD@financialdata-valkey-do-user-...a.db.ondigitalocean.com:25061")
        return

    # Live test
    print("2. get_valkey_cache(): connected")
    ok = global_cache.store("test:local_script", "hello-valkey", ttl_seconds=60)
    print("   store:", ok)
    if ok:
        got = global_cache.retrieve("test:local_script")
        print("   retrieve:", repr(got))
        assert got == "hello-valkey"
        print("   Roundtrip: OK")
    print()
    print("Valkey live test: passed")


if __name__ == "__main__":
    main()
