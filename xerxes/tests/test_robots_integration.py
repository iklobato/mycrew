"""Integration and cache behavior tests for robots feature."""

import asyncio

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta, timezone
import httpx
from sqlalchemy.exc import OperationalError

from xerxes.config import app_settings
from xerxes.robots.evaluate import (
    RefreshFailureReason,
    _fetch_and_merge_robots_cache,
    check_robots_allowed,
    emit_robots_decision_observability,
)
from xerxes.types.robots import RobotsDecision, RobotsReason, RobotsCacheStatus
from almagest.models.monarch.xerxes import RobotsCache


@pytest.mark.asyncio
async def test_check_robots_enforcement_disabled(robots_enforce_disabled):
    """When disabled, always returns RobotsDecision with allowed=True."""
    decision = await check_robots_allowed("https://example.com/any")
    assert isinstance(decision, RobotsDecision)
    assert decision.allowed is True
    assert decision.reason == RobotsReason.ENFORCEMENT_DISABLED
    assert decision.cache_status == RobotsCacheStatus.ENFORCEMENT_DISABLED
    assert decision.matched_rule is None
    assert decision.ruleset_age_seconds is None


@pytest.mark.asyncio
async def test_check_robots_enforcement_enabled(robots_enforce_enabled, mock_cache_empty, mock_httpx_success):
    """When enabled, performs actual check and returns RobotsDecision."""
    decision = await check_robots_allowed("https://example.com/any")
    assert isinstance(decision, RobotsDecision)
    assert isinstance(decision.allowed, bool)
    assert decision.reason == RobotsReason.ALLOWED_BY_RULE
    assert decision.cache_status == RobotsCacheStatus.MISS
    assert decision.ruleset_age_seconds == 0.0


@pytest.mark.asyncio
async def test_check_robots_cache_hit_valid(robots_enforce_enabled, mock_cache_valid):
    """Valid cache entry returns cached decision."""
    mock_cache_valid.body = "User-agent: *\nDisallow: /admin/"

    decision = await check_robots_allowed("https://example.com/products")
    assert isinstance(decision, RobotsDecision)
    assert decision.allowed is True
    assert decision.reason == RobotsReason.ALLOWED_BY_RULE
    assert decision.cache_status == RobotsCacheStatus.HIT
    assert decision.matched_rule is None
    assert decision.ruleset_age_seconds is not None

    decision_blocked = await check_robots_allowed("https://example.com/admin/users")
    assert decision_blocked.allowed is False
    assert decision_blocked.reason == RobotsReason.BLOCKED_BY_RULE
    assert decision_blocked.matched_rule is None
    assert decision_blocked.ruleset_age_seconds is not None


@pytest.mark.asyncio
async def test_check_robots_cache_hit_expired(robots_enforce_enabled, mock_cache_expired, mock_httpx_success):
    """Expired cache serves stale body immediately (SWR), triggers background refresh."""
    mock_httpx_success.text = "User-agent: *\nDisallow: /new/"

    decision = await check_robots_allowed("https://example.com/test")
    assert isinstance(decision, RobotsDecision)
    assert decision.allowed is True
    assert decision.reason == RobotsReason.ALLOWED_BY_RULE
    assert decision.cache_status == RobotsCacheStatus.STALE
    assert decision.matched_rule is None
    assert decision.ruleset_age_seconds is not None
    assert decision.ruleset_age_seconds > 0


@pytest.mark.asyncio
async def test_check_robots_cache_hit_timezone_handling(robots_enforce_enabled, mock_robots_session):
    """Test timezone-aware vs naive datetime handling."""
    now = datetime.now(timezone.utc)
    cached_entry = MagicMock(spec=RobotsCache)
    cached_entry.expires_at = (now + timedelta(hours=1)).replace(tzinfo=None)
    cached_entry.fetched_at = (now - timedelta(minutes=30)).replace(tzinfo=None)
    cached_entry.body = "User-agent: *\nAllow: /"

    mock_robots_session.__aenter__.return_value.execute.return_value.scalars.return_value.first.return_value = cached_entry

    decision = await check_robots_allowed("https://example.com/test")
    assert isinstance(decision, RobotsDecision)
    assert decision.allowed is True


@pytest.mark.asyncio
async def test_check_robots_cache_hit_none_expires_at(robots_enforce_enabled, mock_robots_session, mock_httpx_success):
    """Handle None expires_at gracefully - treated as stale with SWR."""
    cached_entry = MagicMock(spec=RobotsCache)
    cached_entry.expires_at = None
    cached_entry.fetched_at = None
    cached_entry.body = "User-agent: *\nAllow: /"

    mock_robots_session.__aenter__.return_value.execute.return_value.scalars.return_value.first.return_value = cached_entry

    decision = await check_robots_allowed("https://example.com/test")
    assert isinstance(decision, RobotsDecision)
    assert isinstance(decision.allowed, bool)
    assert decision.cache_status == RobotsCacheStatus.STALE
    assert decision.reason == RobotsReason.ALLOWED_BY_RULE
    assert decision.ruleset_age_seconds is None


@pytest.mark.asyncio
async def test_check_robots_cache_miss_fetches(robots_enforce_enabled, mock_cache_empty, mock_httpx_success):
    """Cache miss triggers fetch."""
    mock_httpx_success.text = "User-agent: *\nAllow: /"

    decision = await check_robots_allowed("https://example.com/test")
    assert isinstance(decision, RobotsDecision)
    assert decision.allowed is True
    assert decision.cache_status == RobotsCacheStatus.MISS
    assert decision.reason == RobotsReason.ALLOWED_BY_RULE
    assert decision.ruleset_age_seconds == 0.0


@pytest.mark.asyncio
async def test_check_robots_cache_miss_stores_entry(robots_enforce_enabled, mock_cache_empty, mock_httpx_success):
    """Cache miss stores new entry with expected host and body."""
    mock_httpx_success.text = "User-agent: *\nAllow: /"
    mock_merge = AsyncMock()

    with patch("xerxes.robots.cache.RobotsCache.async_session") as mock_session:
        mock_session_ctx = AsyncMock()
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.return_value.first = MagicMock(return_value=None)
        mock_result.scalars = mock_scalars
        mock_session_ctx.__aenter__.return_value.execute = AsyncMock(return_value=mock_result)
        mock_session_ctx.__aenter__.return_value.merge = mock_merge
        mock_session_ctx.__aenter__.return_value.commit = AsyncMock()
        mock_session.return_value = mock_session_ctx

        decision = await check_robots_allowed("https://example.com/test")

    assert isinstance(decision, RobotsDecision)
    assert decision.allowed is True
    assert mock_merge.called
    cache_entry = mock_merge.call_args[0][0]
    assert cache_entry.host == "https://example.com"
    assert cache_entry.body == mock_httpx_success.text


@pytest.mark.asyncio
async def test_check_robots_cache_miss_24h_ttl_success(robots_enforce_enabled, mock_cache_empty, mock_httpx_success):
    """Successful fetch uses 24h TTL."""
    mock_httpx_success.text = "User-agent: *\nAllow: /"
    mock_merge = AsyncMock()

    with patch("xerxes.robots.cache.RobotsCache.async_session") as mock_session:
        mock_session_ctx = AsyncMock()
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.return_value.first = MagicMock(return_value=None)
        mock_result.scalars = mock_scalars
        mock_session_ctx.__aenter__.return_value.execute = AsyncMock(return_value=mock_result)
        mock_session_ctx.__aenter__.return_value.merge = mock_merge
        mock_session_ctx.__aenter__.return_value.commit = AsyncMock()
        mock_session.return_value = mock_session_ctx

        await check_robots_allowed("https://example.com/test")

        assert mock_merge.called
        cache_entry = mock_merge.call_args[0][0]
        now_naive = datetime.now(timezone.utc).replace(tzinfo=None)
        expected_expires = now_naive + timedelta(hours=24)
        assert abs((cache_entry.expires_at - expected_expires).total_seconds()) < 2


@pytest.mark.asyncio
async def test_check_robots_cache_miss_failure_no_merge(robots_enforce_enabled, mock_cache_empty, mock_httpx_500):
    """Failed fetch does not update cache on miss."""
    mock_merge = AsyncMock()

    with patch("xerxes.robots.cache.RobotsCache.async_session") as mock_session:
        mock_session_ctx = AsyncMock()
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.return_value.first = MagicMock(return_value=None)
        mock_result.scalars = mock_scalars
        mock_session_ctx.__aenter__.return_value.execute = AsyncMock(return_value=mock_result)
        mock_session_ctx.__aenter__.return_value.merge = mock_merge
        mock_session_ctx.__aenter__.return_value.commit = AsyncMock()
        mock_session.return_value = mock_session_ctx

        decision = await check_robots_allowed("https://example.com/test")

    assert decision.allowed is False
    assert not mock_merge.called


@pytest.mark.asyncio
async def test_check_robots_cache_miss_httpx_error_no_merge(robots_enforce_enabled, mock_cache_empty, mock_httpx_error):
    """Network/Connection error does not update cache on miss."""
    mock_merge = AsyncMock()

    with patch("xerxes.robots.cache.RobotsCache.async_session") as mock_session:
        mock_session_ctx = AsyncMock()
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.return_value.first = MagicMock(return_value=None)
        mock_result.scalars = mock_scalars
        mock_session_ctx.__aenter__.return_value.execute = AsyncMock(return_value=mock_result)
        mock_session_ctx.__aenter__.return_value.merge = mock_merge
        mock_session_ctx.__aenter__.return_value.commit = AsyncMock()
        mock_session.return_value = mock_session_ctx

        decision = await check_robots_allowed("https://example.com/test")

    assert decision.allowed is False
    assert not mock_merge.called


@pytest.mark.asyncio
async def test_check_robots_swr_background_task_triggered(robots_enforce_enabled, mock_cache_expired, mock_httpx_success):
    """SWR: Stale entry triggers background refresh task."""

    tasks_created = []

    def capture_task(coro, *args, **kwargs):
        task = asyncio.create_task(coro)
        tasks_created.append(task)
        return task

    with patch("xerxes.robots.evaluate.asyncio.create_task", side_effect=capture_task):
        decision = await check_robots_allowed("https://example.com/test")

    assert decision.cache_status == RobotsCacheStatus.STALE
    assert len(tasks_created) == 1

    if tasks_created:
        await asyncio.gather(*tasks_created)


@pytest.mark.asyncio
async def test_fetch_and_merge_robots_cache_success(robots_enforce_enabled, mock_robots_session, mock_httpx_success):
    """_fetch_and_merge_robots_cache merges on success with correct TTL."""
    mock_httpx_success.text = "User-agent: *\nAllow: /"
    mock_merge = AsyncMock()
    mock_robots_session.__aenter__.return_value.merge = mock_merge
    mock_robots_session.__aenter__.return_value.commit = AsyncMock()

    robots_txt, fetch_succeeded, failure_reason = await _fetch_and_merge_robots_cache(
        "https://example.com", app_settings.robots_user_agent, "https://example.com/test"
    )
    assert robots_txt == "User-agent: *\nAllow: /"
    assert fetch_succeeded is True
    assert failure_reason is None

    assert mock_merge.called
    cache_entry = mock_merge.call_args[0][0]
    now_naive = datetime.now(timezone.utc).replace(tzinfo=None)
    expected_expires = now_naive + timedelta(hours=24)
    assert abs((cache_entry.expires_at - expected_expires).total_seconds()) < 2


@pytest.mark.asyncio
async def test_fetch_and_merge_robots_cache_failure(robots_enforce_enabled, mock_robots_session, mock_httpx_500):
    """_fetch_and_merge_robots_cache does not update cache on failure; keeps stale value in use."""
    mock_merge = AsyncMock()
    mock_robots_session.__aenter__.return_value.merge = mock_merge
    mock_robots_session.__aenter__.return_value.commit = AsyncMock()

    robots_txt, fetch_succeeded, failure_reason = await _fetch_and_merge_robots_cache(
        "https://example.com", app_settings.robots_user_agent, "https://example.com/test"
    )
    assert robots_txt == ""
    assert fetch_succeeded is False
    assert failure_reason == RefreshFailureReason.HTTP_5XX

    assert not mock_merge.called
