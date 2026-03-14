#!/usr/bin/env python
"""Register GitHub repository webhook for code pipeline (issues assigned, PR review comments)."""

import argparse
import httpx
import logging
import sys

from mycrew.settings import get_settings

logger = logging.getLogger(__name__)

DEFAULT_WEBHOOK_URL = "https://mycrew-gw68v.ondigitalocean.app/webhook"
WEBHOOK_EVENTS = ["issues", "pull_request_review_comment"]


def register_webhook(
    repo: str,
    *,
    webhook_url: str = DEFAULT_WEBHOOK_URL,
    token: str | None = None,
    secret: str | None = None,
) -> int:
    """
    Create or update repository webhook via GitHub API.

    Returns 0 on success, 1 on error.
    """
    if "/" not in repo or repo.count("/") != 1:
        logger.error("Invalid repo: expected owner/repo (e.g. octocat/Hello-World)")
        return 1

    owner, repo_name = repo.split("/", 1)
    token_val = token or get_settings().github_token.strip()
    secret_val = secret or get_settings().github_webhook_secret.strip()

    if not token_val:
        logger.error(
            "GITHUB_TOKEN required. Set it in env or config with admin:repo_hook scope."
        )
        return 1

    if not secret_val:
        logger.error(
            "GITHUB_WEBHOOK_SECRET required. Must match the secret on your remote server."
        )
        return 1

    api_url = f"https://api.github.com/repos/{owner}/{repo_name}/hooks"
    headers = {
        "Authorization": f"Bearer {token_val}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    payload = {
        "name": "web",
        "active": True,
        "events": WEBHOOK_EVENTS,
        "config": {
            "url": webhook_url,
            "content_type": "json",
            "secret": secret_val,
            "insecure_ssl": "0",
        },
    }

    with httpx.Client(timeout=30) as client:
        # Check for existing webhook to same URL
        resp = client.get(api_url, headers=headers)
        resp.raise_for_status()
        hooks = resp.json()
        existing = next(
            (h for h in hooks if h.get("config", {}).get("url") == webhook_url),
            None,
        )

        if existing:
            hook_id = existing["id"]
            logger.info("Updating existing webhook (id=%d)", hook_id)
            patch_resp = client.patch(
                f"{api_url}/{hook_id}",
                headers=headers,
                json={
                    "events": WEBHOOK_EVENTS,
                    "config": {
                        "url": webhook_url,
                        "content_type": "json",
                        "secret": secret_val,
                        "insecure_ssl": "0",
                    },
                },
            )
            if patch_resp.status_code not in (200, 204):
                logger.error(
                    "Webhook update failed: %s %s",
                    patch_resp.status_code,
                    patch_resp.text[:200],
                )
                return 1
            logger.info("Webhook updated. URL: %s", webhook_url)
        else:
            create_resp = client.post(api_url, headers=headers, json=payload)
            if create_resp.status_code not in (200, 201):
                logger.error(
                    "Webhook create failed: %s %s",
                    create_resp.status_code,
                    create_resp.text[:200],
                )
                return 1
            data = create_resp.json()
            logger.info("Webhook created (id=%s). URL: %s", data.get("id"), webhook_url)

    logger.info(
        "Events subscribed: %s. GitHub will send a ping to verify.",
        ", ".join(WEBHOOK_EVENTS),
    )
    return 0


def main() -> None:
    """CLI entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
    )
    parser = argparse.ArgumentParser(
        description="Register GitHub repo webhook for code pipeline (issues, PR review comments)"
    )
    parser.add_argument(
        "repo",
        help="Repository in owner/repo format (e.g. octocat/Hello-World)",
    )
    parser.add_argument(
        "--url",
        default=DEFAULT_WEBHOOK_URL,
        help="Webhook payload URL (default: %(default)s)",
    )
    parser.add_argument(
        "--token",
        default=None,
        help="GITHUB_TOKEN (default: from env or config)",
    )
    parser.add_argument(
        "--secret",
        default=None,
        help="GITHUB_WEBHOOK_SECRET (default: from env or config)",
    )
    args = parser.parse_args()

    sys.exit(
        register_webhook(
            args.repo,
            webhook_url=args.url,
            token=args.token,
            secret=args.secret,
        )
    )


if __name__ == "__main__":
    main()
