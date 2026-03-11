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
        repo_path = request.repo_path if request.repo_path else "."
        branch = request.branch if request.branch else "main"
        dry_run = request.dry_run if request.dry_run is not None else False
        test_command = request.test_command if request.test_command else ""
        issue_id = request.issue_id if request.issue_id else ""
        github_repo = request.github_repo if request.github_repo else ""

        result = kickoff(
            repo_path=repo_path,
            task=request.task,
            branch=branch,
            dry_run=dry_run,
            test_command=test_command,
            issue_id=issue_id,
            github_repo=github_repo,
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
        raise HTTPException(status_code=403, detail="Missing signature header")

    if not signature_header.startswith("sha256="):
        raise HTTPException(status_code=403, detail="Invalid signature format")

    hash_object = hmac.new(
        secret.encode("utf-8"), msg=payload_body, digestmod=hashlib.sha256
    )
    expected_signature = "sha256=" + hash_object.hexdigest()

    if not hmac.compare_digest(expected_signature, signature_header):
        logger.error("Error: Request signature does not match expected signature")
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

    task = issue.get("title", "").strip()
    if not task:
        raise HTTPException(status_code=400, detail="Issue title is empty")

    issue_number = issue.get("number", "")
    issue_url = issue.get("html_url", "")
    issue_body = issue.get("body", "")

    dry_run_env = os.getenv("DEFAULT_DRY_RUN", "false")
    if dry_run_env.lower() == "true":
        dry_run = True
    else:
        dry_run = False

    branch = os.getenv("DEFAULT_BRANCH", "main")

    params = {
        "task": task,
        "repo_path": ".",
        "issue_id": f"#{issue_number}",
        "github_repo": repo_full_name,
        "issue_url": issue_url,
        "dry_run": dry_run,
        "branch": branch,
    }

    if issue_body:
        if len(issue_body) > 2000:
            truncated_body = issue_body[:2000] + "..."
        else:
            truncated_body = issue_body
        params["metadata"] = {"github_issue_body": truncated_body}

    logger.info(
        "Extracted from issue: task=%s, issue=%s, repo=%s",
        task[:80],
        params["issue_id"],
        repo_full_name,
    )

    return params


def _extract_pr_comment_params(payload: dict, repo_full_name: str) -> dict:
    """Extract parameters from PR comment payload."""
    comment = payload.get("comment", {})
    pull_request = payload.get("pull_request", {})

    if not comment or not pull_request:
        raise HTTPException(
            status_code=400, detail="Missing comment or pull_request in payload"
        )

    comment_body = comment.get("body", "").strip()
    if not comment_body:
        raise HTTPException(status_code=400, detail="Comment body is empty")

    pr_title = pull_request.get("title", "").strip()
    pr_number = pull_request.get("number", "")
    comment_url = comment.get("html_url", "")
    comment_author = comment.get("user", {}).get("login", "")
    pr_body = pull_request.get("body", "")

    if pr_title:
        task = f"Address PR comment on '{pr_title}': {comment_body[:100]}"
    else:
        task = f"Address PR comment: {comment_body[:150]}"

    dry_run_env = os.getenv("DEFAULT_DRY_RUN", "false")
    if dry_run_env.lower() == "true":
        dry_run = True
    else:
        dry_run = False

    branch = os.getenv("DEFAULT_BRANCH", "main")

    params = {
        "task": task,
        "repo_path": ".",
        "issue_id": f"PR#{pr_number}",
        "github_repo": repo_full_name,
        "issue_url": comment_url,
        "dry_run": dry_run,
        "branch": branch,
    }

    metadata = {}

    if len(comment_body) > 2000:
        metadata["github_comment_body"] = comment_body[:2000] + "..."
    else:
        metadata["github_comment_body"] = comment_body

    metadata["github_pr_title"] = pr_title
    metadata["github_pr_number"] = pr_number
    metadata["github_comment_author"] = comment_author

    if pr_body:
        if len(pr_body) > 2000:
            metadata["github_pr_body"] = pr_body[:2000] + "..."
        else:
            metadata["github_pr_body"] = pr_body

    params["metadata"] = metadata

    logger.info(
        "Extracted from PR comment: task=%s, PR=%s, repo=%s",
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
                "task": pipeline_params["task"][:100],
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
                "task": pipeline_params["task"][:100],
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
