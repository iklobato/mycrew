# ADR-001: Redis/Valkey for Memory Offload

**Status:** Accepted
**Date:** 2026-03-12
**Context:** Pipeline state (exploration, plan, implementation) can exceed 50KB each, held in RAM. Need to offload large strings to external store.

## Decision

Add optional `redis` package and `REDIS_URL` setting. When configured, store large pipeline fields in Valkey/Redis instead of in-process memory. Fetch on demand when downstream stages need full content.

## Rationale

- Stdlib cannot provide remote key-value store; httpx alone is insufficient for Redis protocol.
- Valkey is Redis-compatible; `redis-py` is the standard client.
- REDIS_URL is optional; when empty, behavior unchanged (no new network calls).
- Per AGENTS.md: new external dependency requires ADR.

## Consequences

- New dependency: `redis>=5.0,<6.0`
- Requires REDIS_URL (or equivalent) for Valkey connection when deployed
- Connection failures must be handled gracefully; pipeline degrades to in-memory when Valkey unavailable
