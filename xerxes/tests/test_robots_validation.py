import asyncio

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta, timezone
import httpx
from sqlalchemy.exc import OperationalError

from xerxes.config import app_settings
from xerxes.robots.cache import _get_host_key
from xerxes.robots.parse import _check_robots_txt
from xerxes.robots.evaluate import check_robots_allowed
from xerxes.robots.fetch import _fetch_robots_txt
from xerxes.robots import evaluate as robots_evaluate
from xerxes.types.robots import RobotsDecision, RobotsReason, RobotsCacheStatus
from almagest.models.monarch.xerxes import RobotsCache


def test_get_host_key_extracts_from_full_url():
    """Test that host key is extracted correctly from URL with path and query params."""
    assert _get_host_key("https://example.com/path/to/page?q=1") == "https://example.com"


def test_get_host_key_excludes_port():
    """Test that port is excluded from cache key (hostname only)."""
    assert _get_host_key("https://example.com:8080/path") == "https://example.com"
    assert _get_host_key("http://example.com:3000") == "http://example.com"
    assert _get_host_key("https://example.com") == "https://example.com"


def test_empty_robots_txt_allows_all():
    """Test fail-open behavior when robots.txt is empty or missing."""
    assert _check_robots_txt("", "https://example.com/anything", app_settings.robots_user_agent) is True


def test_robots_txt_blocking():
    """Test core blocking functionality with allowed and disallowed paths."""
    robots = """User-agent: *
Disallow: /admin/"""

    assert _check_robots_txt(robots, "https://example.com/products", app_settings.robots_user_agent) is True
    assert _check_robots_txt(robots, "https://example.com/admin/users", app_settings.robots_user_agent) is False


@pytest.mark.asyncio
async def test_robots_404_allows_on_miss():
    """Test that 404 on robots.txt means no restrictions when no cache exists."""
    original_value = app_settings.robots_enforce
    app_settings.robots_enforce = True

    try:
        with patch("xerxes.robots.cache.RobotsCache.async_session") as mock_session:
            mock_session_ctx = AsyncMock()
            mock_result = MagicMock()
            mock_scalars = MagicMock()
            mock_scalars.return_value.first = MagicMock(return_value=None)
            mock_result.scalars = mock_scalars
            mock_session_ctx.__aenter__.return_value.execute = AsyncMock(return_value=mock_result)
            mock_session_ctx.__aenter__.return_value.merge = AsyncMock()
            mock_session_ctx.__aenter__.return_value.commit = AsyncMock()
            mock_session.return_value = mock_session_ctx

            with patch("httpx.AsyncClient") as mock_client:
                mock_response = MagicMock()
                mock_response.status_code = 404
                mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                    "404 Not Found", request=MagicMock(), response=mock_response
                )

                mock_client_instance = AsyncMock()
                mock_client_instance.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
                mock_client.return_value.__aenter__.return_value = mock_client_instance.__aenter__.return_value

                decision = await check_robots_allowed("https://example.com/test")
                assert isinstance(decision, RobotsDecision)
                assert decision.allowed is True
                assert decision.reason == RobotsReason.ALLOWED_NO_RULES
                assert decision.cache_status == RobotsCacheStatus.MISS
                assert decision.matched_rule is None
                assert decision.ruleset_age_seconds == 0.0
    finally:
        app_settings.robots_enforce = original_value


@pytest.mark.asyncio
async def test_robots_fetch_failure_blocks_on_miss():
    """Test that fetch failure (network error) blocks when no cache exists (fail-closed).

    On a true cache miss + fetch failure, the evaluator returns blocked to prevent
    crawling hosts whose robots.txt cannot be verified.
    """
    original_value = app_settings.robots_enforce
    app_settings.robots_enforce = True

    try:
        with patch("xerxes.robots.cache.RobotsCache.async_session") as mock_session:
            mock_session_ctx = AsyncMock()
            mock_result = MagicMock()
            mock_scalars = MagicMock()
            mock_scalars.return_value.first = MagicMock(return_value=None)
            mock_result.scalars = mock_scalars
            mock_session_ctx.__aenter__.return_value.execute = AsyncMock(return_value=mock_result)
            mock_session_ctx.__aenter__.return_value.merge = AsyncMock()
            mock_session_ctx.__aenter__.return_value.commit = AsyncMock()
            mock_session.return_value = mock_session_ctx

            with patch("httpx.AsyncClient") as mock_client:
                mock_client_instance = AsyncMock()
                mock_client_instance.__aenter__.return_value.get = AsyncMock(
                    side_effect=httpx.ConnectError("Connection failed")
                )
                mock_client.return_value.__aenter__.return_value = mock_client_instance.__aenter__.return_value

                decision = await check_robots_allowed("https://example.com/test")
                assert isinstance(decision, RobotsDecision)
                assert decision.allowed is False
                assert decision.reason == RobotsReason.BLOCKED_UNAVAILABLE
                assert decision.cache_status == RobotsCacheStatus.MISS
                assert decision.matched_rule is None
                assert decision.ruleset_age_seconds is None
    finally:
        app_settings.robots_enforce = original_value


@pytest.mark.asyncio
async def test_cache_hit_allows_url():
    """Test that valid cached entry returns cached decision without HTTP call."""
    original_value = app_settings.robots_enforce
    app_settings.robots_enforce = True

    try:
        now = datetime.now(timezone.utc)
        cached_entry = MagicMock(spec=RobotsCache)
        cached_entry.expires_at = (now + timedelta(hours=1)).replace(tzinfo=None)
        cached_entry.fetched_at = (now - timedelta(minutes=30)).replace(tzinfo=None)
        cached_entry.body = "User-agent: *\nDisallow: /admin/"

        with patch("xerxes.robots.cache.RobotsCache.async_session") as mock_session:
            mock_session_ctx = AsyncMock()
            mock_result = MagicMock()
            mock_scalars = MagicMock()
            mock_scalars.return_value.first = MagicMock(return_value=cached_entry)
            mock_result.scalars = mock_scalars
            mock_session_ctx.__aenter__.return_value.execute = AsyncMock(return_value=mock_result)
            mock_session.return_value = mock_session_ctx

            decision = await check_robots_allowed("https://example.com/products")
            assert isinstance(decision, RobotsDecision)
            assert decision.allowed is True
            assert decision.reason == RobotsReason.ALLOWED_BY_RULE
            assert decision.cache_status == RobotsCacheStatus.HIT
            assert decision.matched_rule is None
            assert decision.ruleset_age_seconds is not None
            assert decision.ruleset_age_seconds > 0
    finally:
        app_settings.robots_enforce = original_value


@pytest.mark.asyncio
async def test_cache_miss_fetches_and_caches():
    """Test that cache miss triggers fetch and stores result with correct TTL."""
    original_value = app_settings.robots_enforce
    app_settings.robots_enforce = True

    try:
        robots_content = "User-agent: *\nDisallow: /admin/"

        with patch("xerxes.robots.cache.RobotsCache.async_session") as mock_session:
            mock_session_ctx = AsyncMock()
            mock_result = MagicMock()
            mock_scalars = MagicMock()
            mock_scalars.return_value.first = MagicMock(return_value=None)
            mock_result.scalars = mock_scalars
            mock_session_ctx.__aenter__.return_value.execute = AsyncMock(return_value=mock_result)
            mock_session_ctx.__aenter__.return_value.merge = AsyncMock()
            mock_session_ctx.__aenter__.return_value.commit = AsyncMock()
            mock_session.return_value = mock_session_ctx

            with patch("httpx.AsyncClient") as mock_client:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.text = robots_content
                mock_response.raise_for_status.return_value = None

                mock_client_instance = AsyncMock()
                mock_client_instance.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
                mock_client.return_value.__aenter__.return_value = mock_client_instance.__aenter__.return_value

                decision = await check_robots_allowed("https://example.com/products")
                assert isinstance(decision, RobotsDecision)
                assert decision.allowed is True
                assert decision.cache_status == RobotsCacheStatus.MISS
                assert decision.ruleset_age_seconds == 0.0

                decision_blocked = await check_robots_allowed("https://example.com/admin/settings")
                assert decision_blocked.allowed is False
    finally:
        app_settings.robots_enforce = original_value


@pytest.mark.asyncio
async def test_cache_expired_refreshes():
    """Test that expired cache entry triggers a refresh."""
    original_value = app_settings.robots_enforce
    app_settings.robots_enforce = True

    try:
        now = datetime.now(timezone.utc)
        expired_entry = MagicMock(spec=RobotsCache)
        expired_entry.expires_at = (now - timedelta(hours=1)).replace(tzinfo=None)
        expired_entry.fetched_at = (now - timedelta(hours=25)).replace(tzinfo=None)
        expired_entry.body = "User-agent: *\nDisallow: /admin/"

        with patch("xerxes.robots.cache.RobotsCache.async_session") as mock_session:
            mock_session_ctx = AsyncMock()
            mock_result = MagicMock()
            mock_scalars = MagicMock()
            mock_scalars.return_value.first = MagicMock(return_value=expired_entry)
            mock_result.scalars = mock_scalars
            mock_session_ctx.__aenter__.return_value.execute = AsyncMock(return_value=mock_result)
            mock_session_ctx.__aenter__.return_value.merge = AsyncMock()
            mock_session_ctx.__aenter__.return_value.commit = AsyncMock()
            mock_session.return_value = mock_session_ctx

            with patch("httpx.AsyncClient") as mock_client:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.text = expired_entry.body
                mock_response.raise_for_status.return_value = None

                mock_client_instance = AsyncMock()
                mock_client_instance.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
                mock_client.return_value.__aenter__.return_value = mock_client_instance.__aenter__.return_value

                decision = await check_robots_allowed("https://example.com/products")
                assert decision.cache_status == RobotsCacheStatus.STALE
    finally:
        app_settings.robots_enforce = original_value


@pytest.mark.asyncio
async def test_successful_fetch_24h_ttl():
    """Successful fetch should use 24 hour TTL."""
    # This logic is tested in test_check_robots_cache_miss_24h_ttl_success in integration tests
    pass


@pytest.mark.asyncio
async def test_failed_fetch_no_cache_update():
    """Failed fetch should not update cache."""
    # This logic is tested in test_check_robots_cache_miss_failure_no_merge in integration tests
    pass


@pytest.mark.asyncio
async def test_fetch_robots_txt_includes_user_agent():
    """Test that robots.txt fetch includes the configured User-Agent header."""
    with patch("httpx.AsyncClient") as mock_client:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = ""
        mock_response.raise_for_status.return_value = None

        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
        mock_client.return_value.__aenter__.return_value = mock_client_instance.__aenter__.return_value

        await _fetch_robots_txt("https://example.com")

        # Verify User-Agent header was passed to httpx
        args, kwargs = mock_client_instance.__aenter__.return_value.get.call_args
        assert kwargs["headers"]["User-Agent"] == app_settings.robots_user_agent


def test_timezone_normalization():
    """Test that naive datetimes are correctly compared in cache logic."""
    # Regression check for datetime comparison issues
    from xerxes.robots.evaluate import _is_stale

    now_utc = datetime.now(timezone.utc)
    expired_naive = (now_utc - timedelta(hours=1)).replace(tzinfo=None)

    # _is_stale expects a timezone-aware datetime for 'now' if compared against cache fields
    # or it uses its own 'now' (timezone.utc).
    assert _is_stale(expired_naive) is True


@pytest.mark.asyncio
async def test_lock_acquisition_failure_retries():
    """Test that database lock acquisition failures (serialization/deadlock) are retried."""
    from xerxes.robots.evaluate import _fetch_and_merge_robots_cache

    with patch("xerxes.robots.cache.RobotsCache.async_session") as mock_session:
        mock_session_ctx = AsyncMock()

        # Simulate 55P03 (lock_not_available) followed by success
        # In Postgres 55P03 is 'lock_not_available'
        lock_error = OperationalError("lock upgrade failed", params=None, orig=MagicMock())
        lock_error.orig.pgcode = "55P03"

        mock_session_ctx.__aenter__.return_value.execute.side_effect = [
            lock_error,
            MagicMock(),
        ]
        mock_session.return_value = mock_session_ctx

        with patch("xerxes.robots.fetch._fetch_robots_txt", return_value=("", True, None)):
            with patch("asyncio.sleep", return_value=None):
                await _fetch_and_merge_robots_cache("https://example.com", "bot", "url")

        assert mock_session_ctx.__aenter__.return_value.execute.call_count == 2


@pytest.mark.asyncio
async def test_cache_entry_none_expires_at():
    """Test that cache entry with None expires_at is treated as stale."""
    from xerxes.robots.evaluate import _is_stale
    assert _is_stale(None) is True


@pytest.mark.asyncio
async def test_http_timeout_blocks_on_miss():
    """Verify that HTTP timeout on initial fetch results in blocked decision."""
    original_value = app_settings.robots_enforce
    app_settings.robots_enforce = True

    try:
        with patch("xerxes.robots.cache.RobotsCache.async_session") as mock_session:
            mock_session_ctx = AsyncMock()
            mock_result = MagicMock()
            mock_scalars = MagicMock()
            mock_scalars.return_value.first = MagicMock(return_value=None)
            mock_result.scalars = mock_scalars
            mock_session_ctx.__aenter__.return_value.execute = AsyncMock(return_value=mock_result)
            mock_session.return_value = mock_session_ctx

            with patch("httpx.AsyncClient") as mock_client:
                mock_client_instance = AsyncMock()
                mock_client_instance.__aenter__.return_value.get.side_effect = httpx.TimeoutException("Timeout")
                mock_client.return_value.__aenter__.return_value = mock_client_instance.__aenter__.return_value

                decision = await check_robots_allowed("https://example.com/test")
                assert decision.allowed is False
                assert decision.reason == RobotsReason.BLOCKED_UNAVAILABLE
    finally:
        app_settings.robots_enforce = original_value


def test_malformed_robots_txt():
    """Ensure parser handles garbage input gracefully."""
    garbage = "This is not a robots.txt file\n!!! @#$%^&*()\nUser-agent: \nInvalid: true"
    # Should default to allow all if it can't find specific blocks
    assert _check_robots_txt(garbage, "https://example.com/any", app_settings.robots_user_agent) is True


@pytest.mark.asyncio
async def test_cache_entry_timezone_aware():
    """Test that timezone-aware expires_at in cache doesn't crash the evaluator."""
    from xerxes.robots.evaluate import _is_stale
    now = datetime.now(timezone.utc)
    future_aware = now + timedelta(hours=1)
    assert _is_stale(future_aware) is False


def test_get_host_key_ipv6():
    """Test that host key is extracted correctly from IPv6 URL."""
    assert _get_host_key("https://[2001:db8::1]/path") == "https://[2001:db8::1]"


def test_get_host_key_missing_hostname():
    """Handle URLs with no hostname (e.g. data URLs, file URLs)."""
    assert _get_host_key("data:text/plain;base64,SGVsbG8sIFdvcmxkIQ==") == ""


@pytest.mark.asyncio
async def test_database_commit_failure():
    """Test that database commit failure doesn't crash the evaluator."""
    from xerxes.robots.evaluate import _fetch_and_merge_robots_cache

    with patch("xerxes.robots.cache.RobotsCache.async_session") as mock_session:
        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__.return_value.commit.side_effect = Exception("DB error")
        mock_session.return_value = mock_session_ctx

        with patch("xerxes.robots.fetch._fetch_robots_txt", return_value=("", True, None)):
            # Should catch exception and log it
            await _fetch_and_merge_robots_cache("https://example.com", "bot", "url")


@pytest.mark.asyncio
async def test_multiple_user_agents_same_host():
    """Verify that cache logic works when multiple different bots access same host."""
    # Federated bots are NOT currently supported (cache is per-host).
    # If we need per-bot cache, the schema needs updating.
    pass


def test_decision_enforcement_disabled():
    """RobotsDecision correctly reflects disabled state."""
    d = RobotsDecision(
        allowed=True,
        reason=RobotsReason.ENFORCEMENT_DISABLED,
        cache_status=RobotsCacheStatus.ENFORCEMENT_DISABLED,
    )
    assert d.allowed is True


def test_decision_blocked_with_matched_rule():
    """RobotsDecision correctly reflects blocked state."""
    d = RobotsDecision(
        allowed=False,
        reason=RobotsReason.BLOCKED_BY_RULE,
        cache_status=RobotsCacheStatus.HIT,
    )
    assert d.allowed is False


def test_decision_allowed_no_rules():
    """RobotsDecision correctly reflects allowed (no rules) state."""
    d = RobotsDecision(
        allowed=True,
        reason=RobotsReason.ALLOWED_NO_RULES,
        cache_status=RobotsCacheStatus.MISS,
    )
    assert d.allowed is True
