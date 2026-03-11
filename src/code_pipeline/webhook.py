#!/usr/bin/env python
"""Simple webhook API for triggering code pipeline crews."""

import hashlib
import hmac
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from code_pipeline.main import kickoff

logger = logging.getLogger(__name__)
app = FastAPI(title="Code Pipeline Webhook", version="1.0")


# ============================================================================
# ENUMS
# ============================================================================


@dataclass(frozen=True)
class _EventConfig:
    """Config for extracting params from a GitHub webhook event."""

    path: tuple[str, ...]
    validations: list[tuple[str, str, str]]
    event: str
    action: str


class GitHubWebhookEvent(Enum):
    """Supported GitHub webhook events. Each member holds extraction config."""

    ISSUES_ASSIGNED = _EventConfig(
        path=("issue", "html_url"),
        validations=[],
        event="issues",
        action="assigned",
    )
    PR_REVIEW_COMMENT_CREATED = _EventConfig(
        path=("pull_request", "html_url"),
        validations=[("comment", "body", "Comment body is empty")],
        event="pull_request_review_comment",
        action="created",
    )

    @classmethod
    def from_event_action(cls, event: str, action: str) -> "GitHubWebhookEvent | None":
        """Return enum member for event/action pair, or None if unsupported."""
        for member in cls:
            cfg = member.value
            if cfg.event == event and cfg.action == action:
                return member
        return None


# ============================================================================
# MODELS
# ============================================================================


class PipelineParams(BaseModel):
    """Pipeline inputs. Used by both manual trigger and webhook extraction."""

    model_config = {"frozen": True}
    issue_url: str
    branch: str = "main"
    dry_run: bool = False
    test_command: str = ""


class TriggerRequest(BaseModel):
    """Request model for manual triggers. issue_url is the only work input."""

    issue_url: str  # Required: GitHub issue or PR URL
    branch: Optional[str] = "main"
    dry_run: Optional[bool] = False
    test_command: Optional[str] = ""


# ============================================================================
# GITHUB WEBHOOK
# ============================================================================


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
) -> PipelineParams | None:
    """Extract pipeline params from GitHub webhook payload. Returns None if event/action not supported."""
    webhook_event = GitHubWebhookEvent.from_event_action(event_type, action)
    if webhook_event is None:
        return None
    cfg = webhook_event.value
    issue_url = _get_nested(payload, cfg.path)
    if not issue_url or not str(issue_url).strip():
        raise HTTPException(status_code=400, detail="Missing or empty issue URL")
    for vpath, vfield, vmsg in cfg.validations:
        val = _get_nested(payload, (vpath, vfield))
        if not (val and str(val).strip()):
            raise HTTPException(status_code=400, detail=vmsg)
    return PipelineParams(issue_url=str(issue_url).strip(), **_default_params())


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
    background_tasks.add_task(_run_kickoff_background, **params.model_dump())
    return JSONResponse(
        status_code=202,
        content={
            "status": "accepted",
            "issue_url": params.issue_url[:100],
            "message": "Pipeline queued",
        },
    )


# ============================================================================
# ROUTES
# ============================================================================


@app.post("/webhook/trigger", response_model=None)
def trigger_pipeline(
    request: TriggerRequest, background_tasks: BackgroundTasks
) -> JSONResponse:
    """Trigger pipeline - queued in background, returns 202 immediately."""
    logger.info("Manual trigger: %s", request.issue_url[:80])
    params = PipelineParams(
        issue_url=request.issue_url,
        branch=request.branch or "main",
        dry_run=request.dry_run if request.dry_run is not None else False,
        test_command=request.test_command or "",
    )
    background_tasks.add_task(_run_kickoff_background, **params.model_dump())
    return JSONResponse(
        status_code=202,
        content={
            "status": "accepted",
            "issue_url": request.issue_url,
            "message": "Pipeline queued",
        },
    )


@app.post("/webhook", response_model=None)
async def webhook(request: Request, background_tasks: BackgroundTasks) -> JSONResponse:
    """Single webhook endpoint. Provider detected from headers."""
    body = await request.body()
    payload = await request.json()

    headers = {k.lower(): v for k, v in request.headers.items()}

    if headers.get("x-github-event"):
        return _handle_github(body, headers, payload, background_tasks)

    raise HTTPException(status_code=400, detail="Unknown webhook provider")


@app.get("/")
def root() -> dict[str, str]:
    """Simple root endpoint."""
    return {"status": "ok"}


@app.get("/health")
def health_check() -> dict[str, str]:
    """Simple health check endpoint."""
    return {"status": "healthy"}


# ============================================================================
# MAIN
# ============================================================================


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
