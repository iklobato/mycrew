#!/usr/bin/env python
"""EXTREMELY SIMPLE webhook API for triggering code pipeline crews."""

import hashlib
import hmac
import logging
import os
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Header, Request
from pydantic import BaseModel

from code_pipeline.main import kickoff

logger = logging.getLogger(__name__)
app = FastAPI(title="Code Pipeline Webhook", version="1.0")


# ============================================================================
# GITHUB EVENT HANDLER ABSTRACTION
# ============================================================================


class GitHubEventHandler(ABC):
    """Abstract base class for GitHub event handlers."""

    def __init__(self, payload: Dict[str, Any], repo_full_name: str):
        self.payload = payload
        self.repo_full_name = repo_full_name

    @abstractmethod
    def validate(self) -> None:
        """Validate the payload for this event type."""
        pass

    @abstractmethod
    def extract_task(self) -> str:
        """Extract the task description from the payload."""
        pass

    @abstractmethod
    def extract_issue_id(self) -> str:
        """Extract the issue/PR identifier from the payload."""
        pass

    @abstractmethod
    def extract_issue_url(self) -> str:
        """Extract the issue/PR URL from the payload."""
        pass

    def extract_metadata(self) -> Dict[str, Any]:
        """Extract metadata from the payload (can be overridden)."""
        return {}

    def get_pipeline_params(self) -> Dict[str, Any]:
        """Get all pipeline parameters for this event."""
        self.validate()

        params = {
            "task": self.extract_task(),
            "repo_path": ".",  # Default to current directory
            "issue_id": self.extract_issue_id(),
            "github_repo": self.repo_full_name,
            "issue_url": self.extract_issue_url(),
            "dry_run": os.getenv("DEFAULT_DRY_RUN", "false").lower() == "true",
            "branch": os.getenv("DEFAULT_BRANCH", "main"),
        }

        metadata = self.extract_metadata()
        if metadata:
            params["metadata"] = metadata

        return params

    def log_extraction(self) -> None:
        """Log the extraction details."""
        task = self.extract_task()
        issue_id = self.extract_issue_id()
        logger.info(
            "Extracted from %s: task=%s, issue=%s, repo=%s",
            self.__class__.__name__,
            task[:80],
            issue_id,
            self.repo_full_name,
        )


class IssueAssignedHandler(GitHubEventHandler):
    """Handler for issue assignment events."""

    def validate(self) -> None:
        """Validate issue assignment payload."""
        issue = self.payload.get("issue", {})
        if not issue:
            raise HTTPException(status_code=400, detail="Missing issue in payload")

        task = issue.get("title", "").strip()
        if not task:
            raise HTTPException(status_code=400, detail="Issue title is empty")

    def extract_task(self) -> str:
        """Extract task from issue title."""
        issue = self.payload.get("issue", {})
        return issue.get("title", "").strip()

    def extract_issue_id(self) -> str:
        """Extract issue number."""
        issue = self.payload.get("issue", {})
        return f"#{issue.get('number', '')}"

    def extract_issue_url(self) -> str:
        """Extract issue URL."""
        issue = self.payload.get("issue", {})
        return issue.get("html_url", "")

    def extract_metadata(self) -> Dict[str, Any]:
        """Extract issue metadata."""
        issue = self.payload.get("issue", {})
        metadata = {}

        issue_body = issue.get("body", "")
        if issue_body:
            if len(issue_body) > 2000:
                issue_body = issue_body[:2000] + "..."
            metadata["github_issue_body"] = issue_body

        return metadata


class PRCommentCreatedHandler(GitHubEventHandler):
    """Handler for PR comment creation events."""

    def validate(self) -> None:
        """Validate PR comment payload."""
        comment = self.payload.get("comment", {})
        pull_request = self.payload.get("pull_request", {})

        if not comment or not pull_request:
            raise HTTPException(
                status_code=400, detail="Missing comment or pull_request in payload"
            )

        comment_body = comment.get("body", "").strip()
        if not comment_body:
            raise HTTPException(status_code=400, detail="Comment body is empty")

    def extract_task(self) -> str:
        """Create task from PR title and comment."""
        comment = self.payload.get("comment", {})
        pull_request = self.payload.get("pull_request", {})

        comment_body = comment.get("body", "").strip()
        pr_title = pull_request.get("title", "").strip()

        if pr_title:
            return f"Address PR comment on '{pr_title}': {comment_body[:100]}"
        else:
            return f"Address PR comment: {comment_body[:150]}"

    def extract_issue_id(self) -> str:
        """Extract PR number."""
        pull_request = self.payload.get("pull_request", {})
        return f"PR#{pull_request.get('number', '')}"

    def extract_issue_url(self) -> str:
        """Extract comment URL."""
        comment = self.payload.get("comment", {})
        return comment.get("html_url", "")

    def extract_metadata(self) -> Dict[str, Any]:
        """Extract PR comment metadata."""
        comment = self.payload.get("comment", {})
        pull_request = self.payload.get("pull_request", {})

        comment_body = comment.get("body", "").strip()
        pr_title = pull_request.get("title", "").strip()
        pr_body = pull_request.get("body", "")
        comment_author = comment.get("user", {}).get("login", "")

        metadata = {
            "github_comment_body": comment_body[:2000] + "..."
            if len(comment_body) > 2000
            else comment_body,
            "github_pr_title": pr_title,
            "github_pr_number": pull_request.get("number", ""),
            "github_comment_author": comment_author,
        }

        if pr_body:
            metadata["github_pr_body"] = (
                pr_body[:2000] + "..." if len(pr_body) > 2000 else pr_body
            )

        return metadata


# Event handler registry
EVENT_HANDLERS = {
    "issues": IssueAssignedHandler,
    "pull_request_review_comment": PRCommentCreatedHandler,
}


def get_event_handler(
    event_type: str, payload: Dict[str, Any], repo_full_name: str
) -> GitHubEventHandler:
    """Get the appropriate event handler for the given event type."""
    handler_class = EVENT_HANDLERS.get(event_type)
    if not handler_class:
        raise HTTPException(
            status_code=400, detail=f"Unsupported event type: {event_type}"
        )

    return handler_class(payload, repo_full_name)


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


def extract_pipeline_params_from_github(payload: dict, event_type: str) -> dict:
    """Extract pipeline parameters from GitHub webhook payload using event handlers."""
    repository = payload.get("repository", {})

    if not repository:
        raise HTTPException(
            status_code=400, detail="Missing required GitHub payload fields"
        )

    # Extract repository info
    repo_full_name = repository.get("full_name", "")
    if not repo_full_name:
        raise HTTPException(status_code=400, detail="Repository full_name is empty")

    # Get appropriate event handler
    handler = get_event_handler(event_type, payload, repo_full_name)

    # Get pipeline parameters
    params = handler.get_pipeline_params()

    # Log extraction details
    handler.log_extraction()

    return params


def _extract_from_pr_comment(payload: dict, repo_full_name: str) -> dict:
    """Extract pipeline parameters from PR comment payload."""
    comment = payload.get("comment", {})
    pull_request = payload.get("pull_request", {})

    if not comment or not pull_request:
        raise HTTPException(
            status_code=400, detail="Missing comment or pull_request in payload"
        )

    # Comment body becomes the task (or part of it)
    comment_body = comment.get("body", "").strip()
    if not comment_body:
        raise HTTPException(status_code=400, detail="Comment body is empty")

    # PR title provides context
    pr_title = pull_request.get("title", "").strip()

    # Create a task from PR title and comment
    if pr_title:
        task = f"Address PR comment on '{pr_title}': {comment_body[:100]}"
    else:
        task = f"Address PR comment: {comment_body[:150]}"

    # Build pipeline parameters
    params = {
        "task": task,
        "repo_path": ".",  # Default to current directory
        "issue_id": f"PR#{pull_request.get('number', '')}",
        "github_repo": repo_full_name,
        "issue_url": comment.get("html_url", ""),
        "dry_run": os.getenv("DEFAULT_DRY_RUN", "false").lower() == "true",
        "branch": os.getenv("DEFAULT_BRANCH", "main"),
    }

    # Add comment and PR info to metadata
    metadata = {
        "github_comment_body": comment_body[:2000] + "..."
        if len(comment_body) > 2000
        else comment_body,
        "github_pr_title": pr_title,
        "github_pr_number": pull_request.get("number", ""),
        "github_comment_author": comment.get("user", {}).get("login", ""),
    }

    # Add PR body if available
    pr_body = pull_request.get("body", "")
    if pr_body:
        metadata["github_pr_body"] = (
            pr_body[:2000] + "..." if len(pr_body) > 2000 else pr_body
        )

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

        # Only process supported events
        supported_events = {"issues", "pull_request_review_comment"}
        if x_github_event not in supported_events:
            return {
                "status": "ignored",
                "reason": f"Event '{x_github_event}' not supported",
            }

        # For issues events, only process 'assigned' actions
        if x_github_event == "issues":
            action = payload.get("action", "")
            if action != "assigned":
                return {
                    "status": "ignored",
                    "reason": f"Action '{action}' not supported",
                }

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

        # For PR comment events, only process 'created' actions
        elif x_github_event == "pull_request_review_comment":
            action = payload.get("action", "")
            if action != "created":
                return {
                    "status": "ignored",
                    "reason": f"Action '{action}' not supported",
                }

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

        # Extract pipeline parameters from GitHub payload
        pipeline_params = extract_pipeline_params_from_github(payload, x_github_event)

        # Trigger the pipeline synchronously
        # Note: This blocks until pipeline completes (GitHub expects response within 10s)
        result = kickoff(**pipeline_params)

        # Build response based on event type
        if x_github_event == "issues":
            assignee = payload.get("assignee", {})
            assignee_login = assignee.get("login", "unknown")
            issue = payload.get("issue", {})
            issue_number = issue.get("number", "unknown")

            return {
                "status": "success",
                "event": "issue_assigned",
                "issue": f"#{issue_number}",
                "assignee": assignee_login,
                "task": pipeline_params["task"][:100],
                "pipeline_result": str(result)[:200],
            }
        elif x_github_event == "pull_request_review_comment":
            comment = payload.get("comment", {})
            pull_request = payload.get("pull_request", {})
            comment_id = comment.get("id", "unknown")
            pr_number = pull_request.get("number", "unknown")
            comment_author = comment.get("user", {}).get("login", "unknown")

            return {
                "status": "success",
                "event": "pr_comment_created",
                "pr": f"#{pr_number}",
                "comment_id": comment_id,
                "comment_author": comment_author,
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
