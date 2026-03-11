#!/usr/bin/env python
"""Simple webhook API for triggering code pipeline crews."""

import hashlib
import hmac
import logging
import os
from typing import Optional

from fastapi import FastAPI, HTTPException, Header, Request
from pydantic import BaseModel

from code_pipeline.main import kickoff

logger = logging.getLogger(__name__)
app = FastAPI(title="Code Pipeline Webhook", version="1.0")


# ============================================================================
# SIMPLE MANUAL TRIGGER ENDPOINT
# ============================================================================


class TriggerRequest(BaseModel):
    """Request model for manual triggers. issue_url is the only work input."""

    issue_url: str  # Required: GitHub issue or PR URL
    branch: Optional[str] = "main"
    dry_run: Optional[bool] = False
    test_command: Optional[str] = ""


@app.post("/webhook/trigger")
def trigger_pipeline(request: TriggerRequest):
    """Trigger pipeline - synchronous, blocking, simple."""
    try:
        logger.info("Manual trigger: %s", request.issue_url[:80])

        result = kickoff(
            issue_url=request.issue_url,
            branch=request.branch or "main",
            dry_run=request.dry_run if request.dry_run is not None else False,
            test_command=request.test_command or "",
        )

        return {
            "status": "success",
            "issue_url": request.issue_url,
            "result": str(result)[:500],  # Truncate if too long
        }

    except Exception as e:
        logger.error("Pipeline failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# GITHUB WEBHOOK ENDPOINT
# ============================================================================


def verify_github_signature(payload_body: bytes, signature_header: str) -> None:
    """Verify GitHub webhook signature."""
    secret = os.getenv("GITHUB_WEBHOOK_SECRET")
    if not secret:
        return

    if not signature_header or not signature_header.startswith("sha256="):
        raise HTTPException(status_code=403, detail="Invalid signature")

    hash_object = hmac.new(secret.encode(), msg=payload_body, digestmod=hashlib.sha256)
    expected_signature = "sha256=" + hash_object.hexdigest()

    if not hmac.compare_digest(expected_signature, signature_header):
        raise HTTPException(status_code=403, detail="Invalid signature")


def extract_pipeline_params_from_github(payload: dict, event_type: str) -> dict:
    """Extract pipeline parameters from GitHub webhook payload."""
    repository = payload.get("repository", {})

    if not repository:
        raise HTTPException(
            status_code=400, detail="Missing required GitHub payload fields"
        )

    repo_full_name = repository.get("full_name", "")
    if not repo_full_name:
        raise HTTPException(status_code=400, detail="Repository full_name is empty")

    match event_type:
        case "issues":
            return _extract_issue_params(payload, repo_full_name)
        case "pull_request_review_comment":
            return _extract_pr_comment_params(payload, repo_full_name)
        case _:
            raise HTTPException(
                status_code=400, detail=f"Unsupported event type: {event_type}"
            )


def _extract_issue_params(payload: dict, repo_full_name: str) -> dict:
    """Extract parameters from issue assignment payload."""
    issue = payload.get("issue", {})

    if not issue:
        raise HTTPException(status_code=400, detail="Missing issue in payload")

    issue_url = issue.get("html_url", "").strip()
    if not issue_url:
        raise HTTPException(status_code=400, detail="Issue has no html_url")

    dry_run_env = os.getenv("DEFAULT_DRY_RUN", "false")
    dry_run = dry_run_env.lower() == "true"
    branch = os.getenv("DEFAULT_BRANCH", "main")

    params = {
        "issue_url": issue_url,
        "dry_run": dry_run,
        "branch": branch,
    }

    logger.info(
        "Extracted from issue: issue_url=%s, repo=%s",
        issue_url[:80],
        repo_full_name,
    )

    return params


def _extract_pr_comment_params(payload: dict, repo_full_name: str) -> dict:
    """Extract parameters from PR comment payload. Uses PR URL as issue_url."""
    comment = payload.get("comment", {})
    pull_request = payload.get("pull_request", {})

    if not comment or not pull_request:
        raise HTTPException(
            status_code=400, detail="Missing comment or pull_request in payload"
        )

    if not comment.get("body", "").strip():
        raise HTTPException(status_code=400, detail="Comment body is empty")

    issue_url = pull_request.get("html_url", "").strip()
    if not issue_url:
        raise HTTPException(status_code=400, detail="Pull request has no html_url")

    dry_run_env = os.getenv("DEFAULT_DRY_RUN", "false")
    dry_run = dry_run_env.lower() == "true"
    branch = os.getenv("DEFAULT_BRANCH", "main")

    params = {
        "issue_url": issue_url,
        "dry_run": dry_run,
        "branch": branch,
    }

    logger.info(
        "Extracted from PR comment: issue_url=%s, repo=%s",
        issue_url[:80],
        repo_full_name,
    )

    return params


@app.post("/github/webhook")
async def github_webhook(
    request: Request,
    x_github_event: Optional[str] = Header(None, alias="X-GitHub-Event"),
    x_hub_signature_256: Optional[str] = Header(None, alias="X-Hub-Signature-256"),
    x_github_delivery: Optional[str] = Header(None, alias="X-GitHub-Delivery"),
):
    """Handle GitHub webhook events."""
    body_bytes = await request.body()

    try:
        if x_hub_signature_256:
            verify_github_signature(body_bytes, x_hub_signature_256)

        payload = await request.json()

        if x_github_delivery:
            delivery_id = x_github_delivery[:8]
        else:
            delivery_id = "unknown"

        logger.info(
            "GitHub webhook: event=%s, delivery=%s",
            x_github_event,
            delivery_id,
        )

        match x_github_event:
            case "issues":
                return _handle_issue_event(payload)
            case "pull_request_review_comment":
                return _handle_pr_comment_event(payload)
            case _:
                return {
                    "status": "ignored",
                    "reason": f"Event '{x_github_event}' not supported",
                }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("GitHub webhook processing failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


def _handle_issue_event(payload: dict) -> dict:
    """Handle issue assignment events."""
    action = payload.get("action", "")

    match action:
        case "assigned":
            assignee = payload.get("assignee", {})
            assignee_login = assignee.get("login", "unknown")
            issue = payload.get("issue", {})
            issue_number = issue.get("number", "unknown")

            logger.info(
                "Issue #%s assigned to %s: %s",
                issue_number,
                assignee_login,
                issue.get("title", "no title")[:100],
            )

            pipeline_params = extract_pipeline_params_from_github(payload, "issues")
            result = kickoff(**pipeline_params)

            return {
                "status": "success",
                "event": "issue_assigned",
                "issue": f"#{issue_number}",
                "assignee": assignee_login,
                "issue_url": pipeline_params["issue_url"][:100],
                "pipeline_result": str(result)[:200],
            }
        case _:
            return {"status": "ignored", "reason": f"Action '{action}' not supported"}


def _handle_pr_comment_event(payload: dict) -> dict:
    """Handle PR comment creation events."""
    action = payload.get("action", "")

    match action:
        case "created":
            comment = payload.get("comment", {})
            pull_request = payload.get("pull_request", {})
            comment_id = comment.get("id", "unknown")
            pr_number = pull_request.get("number", "unknown")
            comment_author = comment.get("user", {}).get("login", "unknown")

            logger.info(
                "PR #%s comment #%s by %s: %s",
                pr_number,
                comment_id,
                comment_author,
                comment.get("body", "no body")[:100],
            )

            pipeline_params = extract_pipeline_params_from_github(
                payload, "pull_request_review_comment"
            )
            result = kickoff(**pipeline_params)

            return {
                "status": "success",
                "event": "pr_comment_created",
                "pr": f"#{pr_number}",
                "comment_id": comment_id,
                "comment_author": comment_author,
                "issue_url": pipeline_params["issue_url"][:100],
                "pipeline_result": str(result)[:200],
            }
        case _:
            return {"status": "ignored", "reason": f"Action '{action}' not supported"}


# ============================================================================
# HEALTH CHECK & ROOT ENDPOINTS
# ============================================================================


@app.get("/")
def root():
    """Simple root endpoint."""
    return {"status": "ok"}


@app.get("/health")
def health_check():
    """Simple health check endpoint."""
    return {"status": "healthy"}


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================


def main():
    """Run the simple webhook server."""
    import uvicorn

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Log configuration
    has_secret = bool(os.getenv("GITHUB_WEBHOOK_SECRET"))
    logger.info("Starting webhook server")
    if has_secret:
        secret_status = "configured"
    else:
        secret_status = "not configured"
    logger.info("GitHub webhook secret: %s", secret_status)
    logger.info("Default branch: %s", os.getenv("DEFAULT_BRANCH", "main"))
    logger.info("Default dry_run: %s", os.getenv("DEFAULT_DRY_RUN", "false"))

    # Run server
    uvicorn.run(
        app,
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        log_level="info",
    )


if __name__ == "__main__":
    main()
