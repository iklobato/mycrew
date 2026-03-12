"""Valkey/Redis cache for offloading large pipeline data from in-process memory."""

import gzip
import logging
from typing import Any

logger = logging.getLogger(__name__)

KEY_PREFIX = "code_pipeline:"
TTL_SECONDS = 24 * 3600  # 24 hours


class ValkeyCache:
    """Valkey/Redis-backed cache. Stores compressed data with TTL."""

    def __init__(self, redis_url: str) -> None:
        """Initialize with Redis/Valkey connection URL."""
        self._redis_url = redis_url.strip()
        self._client: Any = None

    def _get_client(self) -> Any | None:
        """Lazy connection. Returns None on failure."""
        if self._client is not None:
            return self._client
        if not self._redis_url:
            return None
        try:
            import redis

            self._client = redis.from_url(self._redis_url, decode_responses=False)
            self._client.ping()
            logger.debug("ValkeyCache connected")
            return self._client
        except Exception as e:
            logger.warning("ValkeyCache connection failed: %s", e)
            return None

    def _full_key(self, key: str) -> str:
        """Return namespaced key."""
        return f"{KEY_PREFIX}{key}"

    def store(
        self, key: str, data: str | bytes, ttl_seconds: int = TTL_SECONDS
    ) -> bool:
        """Compress and store data. Returns True on success."""
        client = self._get_client()
        if client is None:
            return False
        try:
            if isinstance(data, str):
                data = data.encode("utf-8")
            compressed = gzip.compress(data, compresslevel=6)
            full_key = self._full_key(key)
            client.setex(full_key, ttl_seconds, compressed)
            logger.debug(
                "ValkeyCache stored key=%s (%d -> %d bytes)",
                key,
                len(data),
                len(compressed),
            )
            return True
        except Exception as e:
            logger.warning("ValkeyCache store failed for key=%s: %s", key, e)
            return False

    def retrieve(self, key: str) -> str | None:
        """Fetch and decompress data. Returns None on miss or error."""
        client = self._get_client()
        if client is None:
            return None
        try:
            full_key = self._full_key(key)
            raw = client.get(full_key)
            if raw is None:
                return None
            decompressed = gzip.decompress(raw).decode("utf-8")
            return decompressed
        except Exception as e:
            logger.warning("ValkeyCache retrieve failed for key=%s: %s", key, e)
            return None

    def delete(self, key: str) -> None:
        """Delete key. Ignores errors."""
        client = self._get_client()
        if client is None:
            return
        try:
            client.delete(self._full_key(key))
        except Exception as e:
            logger.debug("ValkeyCache delete failed for key=%s: %s", key, e)


_cached_valkey: ValkeyCache | None = None


def get_valkey_cache() -> ValkeyCache | None:
    """Return ValkeyCache if REDIS_URL is set, else None."""
    global _cached_valkey
    if _cached_valkey is not None:
        return _cached_valkey
    from code_pipeline.settings import get_settings

    url = get_settings().redis_url
    if not url or not url.strip():
        return None
    _cached_valkey = ValkeyCache(url)
    return _cached_valkey
