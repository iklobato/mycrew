#!/usr/bin/env python
"""Configure GitHub webhook and DigitalOcean App Platform via API."""

import argparse
import logging
import os
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)

DO_APP_ID = "5a45a942-e0c3-4648-aad0-6b45ae0efbcd"
WEBHOOK_URL = "https://mycrew-gw68v.ondigitalocean.app/webhook"


def _ensure_env(*names: str) -> dict[str, str]:
    out = {}
    for n in names:
        v = os.environ.get(n, "").strip()
        if not v:
            logger.error("Required env var %s is not set", n)
            sys.exit(1)
        out[n] = v
    return out


def configure_github(repo: str, token: str, secret: str) -> bool:
    """Register webhook at GitHub. Returns True on success."""
    from mycrew.register_webhook import register_webhook

    return (
        register_webhook(repo, token=token, secret=secret, webhook_url=WEBHOOK_URL) == 0
    )


def _env_obj(
    key: str, value: str, scope: str = "RUN_TIME", secret: bool = True
) -> dict:
    return {
        "key": key,
        "value": value,
        "scope": scope,
        "type": "SECRET" if secret else "GENERAL",
    }


def configure_do(
    do_token: str,
    github_token: str | None = None,
    github_webhook_secret: str | None = None,
    openrouter_api_key: str | None = None,
) -> bool:
    """Update DigitalOcean App Platform env vars. Returns True on success."""
    try:
        import httpx
    except ImportError:
        logger.error("httpx required. Run: uv sync")
        return False

    api_base = "https://api.digitalocean.com/v2"
    headers = {
        "Authorization": f"Bearer {do_token}",
        "Content-Type": "application/json",
    }

    with httpx.Client(timeout=60) as client:
        # GET current app spec
        resp = client.get(f"{api_base}/apps/{DO_APP_ID}", headers=headers)
        resp.raise_for_status()
        data = resp.json()
        app = data.get("app", {})
        spec = app.get("spec", {})
        if not spec:
            logger.error("App spec is empty")
            return False

        # Build env vars to set (only non-empty)
        new_envs: list[dict] = []
        if github_token:
            new_envs.append(_env_obj("GITHUB_TOKEN", github_token))
        if github_webhook_secret:
            new_envs.append(_env_obj("GITHUB_WEBHOOK_SECRET", github_webhook_secret))
        if openrouter_api_key:
            new_envs.append(_env_obj("OPENROUTER_API_KEY", openrouter_api_key))

        if not new_envs:
            logger.info("No env vars to set on DO App Platform (all optional)")
            return True

        # Merge new env vars into the first service (typically the webhook service)
        services = spec.get("services", [])
        if not services:
            logger.warning("No services in app spec, cannot add env vars")
        else:
            svc = services[0]
            envs: list[dict] = list(svc.get("envs", []))
            env_by_key = {e.get("key"): e for e in envs}
            for e in new_envs:
                env_by_key[e["key"]] = e
            svc["envs"] = list(env_by_key.values())
            logger.info("Merged env vars into service %s", svc.get("name", "?"))

        # PUT updated spec
        put_resp = client.put(
            f"{api_base}/apps/{DO_APP_ID}",
            headers=headers,
            json={"spec": spec},
        )
        if put_resp.status_code not in (200, 201):
            logger.error(
                "DO app update failed: %s %s", put_resp.status_code, put_resp.text[:300]
            )
            return False
        logger.info("DigitalOcean App Platform updated successfully")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Configure GitHub webhook and DO App Platform for mycrew"
    )
    parser.add_argument(
        "repo", nargs="?", default="iklobato/mycrew", help="GitHub repo owner/repo"
    )
    parser.add_argument(
        "--github-only", action="store_true", help="Only configure GitHub"
    )
    parser.add_argument(
        "--do-only", action="store_true", help="Only configure DigitalOcean"
    )
    args = parser.parse_args()

    try:
        from mycrew.settings import get_settings

        stg = get_settings()
        gh_token = os.environ.get("GITHUB_TOKEN", "").strip() or stg.github_token or ""
        gh_secret = (
            os.environ.get("GITHUB_WEBHOOK_SECRET", "").strip()
            or stg.github_webhook_secret
            or ""
        )
    except Exception:
        gh_token = os.environ.get("GITHUB_TOKEN", "").strip()
        gh_secret = os.environ.get("GITHUB_WEBHOOK_SECRET", "").strip()
    do_token = os.environ.get("DO_TOKEN", "").strip()
    openrouter = os.environ.get("OPENROUTER_API_KEY", "").strip()

    ok = True
    if not args.do_only:
        if not gh_token or not gh_secret:
            logger.error("For GitHub: set GITHUB_TOKEN and GITHUB_WEBHOOK_SECRET")
            ok = False
        elif not configure_github(args.repo, gh_token, gh_secret):
            ok = False

    if not args.github_only and ok:
        if not do_token:
            logger.error("For DO: set DO_TOKEN")
            ok = False
        elif not configure_do(
            do_token,
            github_token=gh_token or None,
            github_webhook_secret=gh_secret or None,
            openrouter_api_key=openrouter or None,
        ):
            ok = False

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
