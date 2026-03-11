#!/usr/bin/env python
"""EXTREMELY SIMPLE webhook API for triggering code pipeline crews."""

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
    """Bare minimum request model for manual triggers."""

    task: str  # Only required field
    repo_path: Optional[str] = "."
    branch: Optional[str] = "main"
    dry_run: Optional[bool] = False
    test_command: Optional[str] = ""
    issue_id: Optional[str] = ""
    github_repo: Optional[str] = ""


@app.post("/webhook/trigger")
def trigger_pipeline(request: TriggerRequest):
    """Trigger pipeline - synchronous, blocking, simple."""
    try:
        logger.info("Manual trigger: %s", request.task[:100])

        # Run pipeline directly (blocking)
        result = kickoff(
            repo_path=request.repo_path or ".",
            task=request.task,
            branch=request.branch or "main",
            dry_run=request.dry_run or False,
            test_command=request.test_command or "",
            issue_id=request.issue_id or "",
            github_repo=request.github_repo or "",
        )

        return {
            "status": "success",
            "task": request.task,
            "result": str(result)[:500],  # Truncate if too long
        }

    except Exception as e:
        logger.error("Pipeline failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# GITHUB WEBHOOK ENDPOINT
# ============================================================================


def verify_github_signature(payload_body: bytes, signature_header: str) -> None:
    """Verify GitHub webhook signature using HMAC SHA-256."""
    secret = os.getenv("GITHUB_WEBHOOK_SECRET")
    if not secret:
        logger.debug("No GITHUB_WEBHOOK_SECRET set, skipping signature verification")
        return

    if not signature_header:
        raise HTTPException(status_code=401, detail="Missing signature header")

    # GitHub sends "sha256=..." format
    if not signature_header.startswith("sha256="):
        raise HTTPException(status_code=401, detail="Invalid signature format")

    # Compute expected signature
    hash_object = hmac.new(
        secret.encode("utf-8"), msg=payload_body, digestmod=hashlib.sha256
    )
    expected_signature = "sha256=" + hash_object.hexdigest()

    # Use compare_digest to prevent timing attacks
    if not hmac.compare_digest(expected_signature, signature_header):
        raise HTTPException(status_code=401, detail="Invalid signature")


def extract_pipeline_params_from_github(payload: dict) -> dict:
    """Extract pipeline parameters from GitHub issue assignment payload."""
    issue = payload.get("issue", {})
    repository = payload.get("repository", {})

    if not issue or not repository:
        raise HTTPException(
            status_code=400, detail="Missing required GitHub payload fields"
        )

    # Issue title becomes the task
    task = issue.get("title", "").strip()
    if not task:
        raise HTTPException(status_code=400, detail="Issue title is empty")

    # Extract repository info
    repo_full_name = repository.get("full_name", "")
    if not repo_full_name:
        raise HTTPException(status_code=400, detail="Repository full_name is empty")

    # Build pipeline parameters
    params = {
        "task": task,
        "repo_path": ".",  # Default to current directory
        "issue_id": f"#{issue.get('number', '')}",
        "github_repo": repo_full_name,
        "issue_url": issue.get("html_url", ""),
        "dry_run": os.getenv("DEFAULT_DRY_RUN", "false").lower() == "true",
        "branch": os.getenv("DEFAULT_BRANCH", "main"),
    }

    # Optional: Add issue body as context in metadata
    issue_body = issue.get("body", "")
    if issue_body:
        # Truncate very long issue bodies
        if len(issue_body) > 2000:
            issue_body = issue_body[:2000] + "..."
        params["metadata"] = {"github_issue_body": issue_body}

    logger.info(
        "Extracted params: task=%s, issue=%s, repo=%s",
        task[:80],
        params["issue_id"],
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
    """Handle GitHub webhook events - only processes issue assignment events."""

    # Get raw body for signature verification
    body_bytes = await request.body()

    try:
        # Verify signature if provided
        if x_hub_signature_256:
            verify_github_signature(body_bytes, x_hub_signature_256)

        # Parse JSON payload
        payload = await request.json()

        # Log basic info
        logger.info(
            "GitHub webhook: event=%s, delivery=%s",
            x_github_event,
            x_github_delivery[:8] if x_github_delivery else "unknown",
        )

        # Only process 'issues' events
        if x_github_event != "issues":
            return {
                "status": "ignored",
                "reason": f"Event '{x_github_event}' not supported",
            }

        # Only process 'assigned' actions
        action = payload.get("action", "")
        if action != "assigned":
            return {"status": "ignored", "reason": f"Action '{action}' not supported"}

        # Extract assignee info for logging
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

        # Extract pipeline parameters from GitHub payload
        pipeline_params = extract_pipeline_params_from_github(payload)

        # Trigger the pipeline synchronously
        # Note: This blocks until pipeline completes (GitHub expects response within 10s)
        result = kickoff(**pipeline_params)

        return {
            "status": "success",
            "issue": f"#{issue_number}",
            "assignee": assignee_login,
            "task": pipeline_params["task"][:100],
            "pipeline_result": str(result)[:200],
        }

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error("GitHub webhook processing failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


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
    logger.info(
        "GitHub webhook secret: %s", "configured" if has_secret else "not configured"
    )
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
