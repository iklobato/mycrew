#!/usr/bin/env python
"""Simple webhook API for triggering code pipeline crews."""

import hashlib
import hmac
import json
import logging
from typing import Any

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from code_pipeline.main import kickoff

logger = logging.getLogger(__name__)
app = FastAPI(title="Code Pipeline Webhook", version="1.0")


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
        "test_command": "",
    }


def _get_nested(obj: dict[str, Any], path: tuple[str, ...]) -> Any:
    """Get nested value from dict by path. Returns None if any key missing."""
    current: Any = obj
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


def _run_kickoff_background(**params: Any) -> None:
    """Run kickoff in background. Logs and swallows exceptions (CS-45: must log)."""
    try:
        kickoff(**params)
    except Exception as e:
        logger.error("Background kickoff failed: %s", e, exc_info=True)


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
    return {"issue_url": str(issue_url).strip(), **_default_params()}


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
        content={"status": "accepted", "issue_url": issue_url[:100], "message": "Pipeline queued"},
    )


@app.post("/webhook", response_model=None)
async def webhook(request: Request, background_tasks: BackgroundTasks) -> JSONResponse:
    """Single endpoint: GitHub webhook (X-GitHub-Event) or manual trigger (JSON with issue_url)."""
    headers = {k.lower(): v for k, v in request.headers.items()}
    body = await request.body()

    try:
        payload = json.loads(body) if body else {}
    except json.JSONDecodeError:
        payload = {}

    if headers.get("x-github-event"):
        return _handle_github(body, headers, payload, background_tasks)

    # Manual trigger
    issue_url = (payload.get("issue_url") or "").strip()
    if not issue_url:
        raise HTTPException(status_code=400, detail="issue_url required")
    params = {
        "issue_url": issue_url,
        "branch": (payload.get("branch") or "main"),
        "dry_run": bool(payload.get("dry_run", False)),
        "test_command": (payload.get("test_command") or ""),
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
    logger.info(
        "GitHub webhook secret: %s",
        "configured" if stg.github_webhook_secret else "not configured",
    )
    logger.info("Default branch: %s", stg.default_branch)
    logger.info("Default dry_run: %s", stg.default_dry_run)
    uvicorn.run(app, host=stg.host, port=stg.port, log_level="info")


if __name__ == "__main__":
    main()
