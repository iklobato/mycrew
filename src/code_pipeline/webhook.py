#!/usr/bin/env python
"""Simple webhook API for triggering code pipeline crews."""

import hashlib
import hmac
import json
import logging
from datetime import datetime
from typing import Any

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from code_pipeline.main import kickoff

logger = logging.getLogger(__name__)
app = FastAPI(title="Code Pipeline Webhook", version="1.0")

# Headers to redact in logs (CS-30: no tokens/secrets)
_REDACT_HEADERS = frozenset({"authorization", "x-hub-signature-256"})


def _sanitize_headers(headers: dict[str, str]) -> dict[str, str]:
    """Redact sensitive headers for logging."""
    result = {}
    for k, v in headers.items():
        if k in _REDACT_HEADERS:
            result[k] = "(redacted)"
        else:
            result[k] = v
    return result


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log all incoming requests with method, host, path, params, and body."""

    async def dispatch(self, request: Request, call_next):
        body = await request.body()
        headers = {k.lower(): v for k, v in request.headers.items()}
        client = request.client
        if client:
            client_str = f"{client.host}:{client.port}"
        else:
            client_str = "(unknown)"

        # Parse body for logging (truncate if large)
        body_preview: str | dict[str, Any] = ""
        if body:
            try:
                parsed = json.loads(body)
                body_str = json.dumps(parsed)
                if len(body_str) <= 2000:
                    body_preview = parsed
                else:
                    body_preview = body_str[:2000] + "..."
            except json.JSONDecodeError:
                body_preview = body[:500].decode("utf-8", errors="replace")
                if len(body) > 500:
                    body_preview += "..."

        url = str(request.url)
        logger.info(
            "Request: method=%s url=%s client=%s query=%s headers=%s body=%s",
            request.method,
            url,
            client_str,
            dict(request.query_params),
            _sanitize_headers(headers),
            body_preview,
        )

        async def receive():
            return {"type": "http.request", "body": body}

        request = Request(request.scope, receive)
        return await call_next(request)


app.add_middleware(RequestLoggingMiddleware)


# Event/action -> path to issue_url in payload
_GITHUB_PATHS: dict[tuple[str, str], tuple[str, ...]] = {
    ("issues", "assigned"): ("issue", "html_url"),
    ("pull_request_review_comment", "created"): ("pull_request", "html_url"),
}


def _default_params() -> dict[str, Any]:
    """Default pipeline params from settings."""
    from code_pipeline.settings import get_settings

    stg = get_settings()
    return {
        "branch": stg.default_branch,
        "dry_run": stg.default_dry_run,
        "programmatic": False,
    }


def _get_nested(obj: dict[str, Any], path: tuple[str, ...]) -> Any:
    """Get nested value from dict by path. Returns None if any key missing."""
    current: Any = obj
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


def _send_callback(callback_url: str, status: str, details: dict[str, Any]) -> None:
    """Send callback to external URL. Logs errors but doesn't raise."""
    try:
        import httpx

        payload = {"status": status, "timestamp": datetime.now().isoformat(), **details}

        # Use sync client since we're in background thread
        response = httpx.post(callback_url, json=payload, timeout=30)
        response.raise_for_status()
        logger.debug("Callback sent to %s", callback_url)
    except Exception as e:
        logger.error("Failed to send callback to %s: %s", callback_url, e)


def _run_kickoff_background(**params: Any) -> None:
    """Run kickoff in background. Logs and swallows exceptions (CS-45: must log)."""
    issue_url = params.get("issue_url", "")
    logger.info(
        "Background kickoff started: issue_url=%s", issue_url[:80] if issue_url else ""
    )

    # Extract callback_url from params
    callback_url = params.pop("callback_url", None)

    try:
        result = kickoff(**params)
        # Send success callback if URL provided
        if callback_url:
            _send_callback(
                callback_url,
                "completed",
                {"result": str(result)[:500] if result else "Pipeline completed"},
            )
    except Exception as e:
        logger.error("Background kickoff failed: %s", e, exc_info=True)
        # Send error callback if URL provided
        if callback_url:
            _send_callback(callback_url, "failed", {"error": str(e)[:500]})


def verify_github_signature(payload_body: bytes, signature_header: str) -> None:
    """Verify GitHub webhook signature."""
    from code_pipeline.settings import get_settings

    secret = get_settings().github_webhook_secret
    if not secret:
        return

    if not signature_header or not signature_header.startswith("sha256="):
        raise HTTPException(status_code=403, detail="Invalid signature")

    hash_object = hmac.new(secret.encode(), msg=payload_body, digestmod=hashlib.sha256)
    expected_signature = "sha256=" + hash_object.hexdigest()

    if not hmac.compare_digest(expected_signature, signature_header):
        raise HTTPException(status_code=403, detail="Invalid signature")


def _extract_github_params(
    payload: dict[str, Any], event_type: str, action: str
) -> dict[str, Any] | None:
    """Extract pipeline params from GitHub webhook payload. Returns None if event/action not supported."""
    path = _GITHUB_PATHS.get((event_type, action))
    if path is None:
        return None
    issue_url = _get_nested(payload, path)
    if not issue_url or not str(issue_url).strip():
        raise HTTPException(status_code=400, detail="Missing or empty issue URL")
    return {
        "issue_url": str(issue_url).strip(),
        "callback_url": payload.get("callback_url"),
        **_default_params(),
    }


def _handle_github(
    body: bytes,
    headers: dict[str, str],
    payload: dict[str, Any],
    background_tasks: BackgroundTasks,
) -> JSONResponse:
    """Handle GitHub webhook: verify, extract, queue kickoff, return 202."""
    verify_github_signature(body, headers.get("x-hub-signature-256", ""))
    event = headers.get("x-github-event", "")
    action = payload.get("action", "")
    params = _extract_github_params(payload, event, action)
    if params is None:
        return JSONResponse(
            status_code=200,
            content={
                "status": "ignored",
                "reason": f"Event {event}/{action} not supported",
            },
        )
    logger.info(
        "GitHub webhook accepted: event=%s action=%s issue_url=%s",
        event,
        action,
        params["issue_url"][:80],
    )
    background_tasks.add_task(_run_kickoff_background, **params)
    return JSONResponse(
        status_code=202,
        content={
            "status": "accepted",
            "issue_url": params["issue_url"][:100],
            "message": "Pipeline queued",
        },
    )


def _accepted_response(issue_url: str) -> JSONResponse:
    """Common 202 response."""
    return JSONResponse(
        status_code=202,
        content={
            "status": "accepted",
            "issue_url": issue_url[:100],
            "message": "Pipeline queued",
        },
    )


@app.post("/webhook", response_model=None)
async def webhook(request: Request, background_tasks: BackgroundTasks) -> JSONResponse:
    """Single endpoint: GitHub webhook (X-GitHub-Event) or manual trigger (JSON with issue_url)."""
    headers = {k.lower(): v for k, v in request.headers.items()}
    body = await request.body()

    try:
        if body:
            payload = json.loads(body)
        else:
            payload = {}
    except json.JSONDecodeError:
        payload = {}

    if headers.get("x-github-event"):
        return _handle_github(body, headers, payload, background_tasks)

    # Manual trigger
    iu_raw = payload.get("issue_url")
    if iu_raw is not None:
        issue_url = iu_raw.strip()
    else:
        issue_url = ""
    if not issue_url:
        raise HTTPException(status_code=400, detail="issue_url required")
    branch_raw = payload.get("branch")
    if branch_raw is not None:
        branch_val = branch_raw
    else:
        branch_val = "main"
    params = {
        "issue_url": issue_url,
        "branch": branch_val,
        "dry_run": payload.get("dry_run", False),
        "programmatic": payload.get("programmatic", False),
        "callback_url": payload.get("callback_url"),
        "from_scratch": payload.get("from_scratch", False),
        "max_retries": payload.get("max_retries", 3),
    }
    logger.info("Manual trigger: %s", issue_url[:80])
    background_tasks.add_task(_run_kickoff_background, **params)
    return _accepted_response(issue_url)


@app.get("/health")
def health_check() -> dict[str, str]:
    """Health check for load balancers."""
    return {"status": "healthy"}


def main() -> None:
    """Run the simple webhook server."""
    import uvicorn

    from code_pipeline.settings import get_settings

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    stg = get_settings()
    logger.info("Starting webhook server")
    if stg.github_webhook_secret:
        secret_status = "configured"
    else:
        secret_status = "not configured"
    logger.info("GitHub webhook secret: %s", secret_status)
    logger.info("Default branch: %s", stg.default_branch)
    logger.info("Default dry_run: %s", stg.default_dry_run)
    uvicorn.run(app, host=stg.host, port=stg.port, log_level="info")


if __name__ == "__main__":
    main()
