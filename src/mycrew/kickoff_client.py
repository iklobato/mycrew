#!/usr/bin/env python
"""Kickoff client for triggering pipeline."""

import argparse
import httpx
from dataclasses import dataclass


@dataclass
class KickoffClient:
    """Client for interacting with kickoff webhook."""

    base_url: str = "http://localhost:8000"
    timeout: int = 30

    def run(
        self,
        issue_url: str,
        branch: str = "main",
        from_scratch: bool = False,
        max_retries: int = 3,
        dry_run: bool = False,
        programmatic: bool = False,
    ) -> dict:
        """Run the pipeline."""
        payload = {
            "issue_url": issue_url,
            "branch": branch,
            "from_scratch": from_scratch,
            "max_retries": max_retries,
            "dry_run": dry_run,
            "programmatic": programmatic,
        }

        response = httpx.post(
            f"{self.base_url}/webhook",
            json=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()


def main():
    parser = argparse.ArgumentParser(description="Kickoff Client")
    parser.add_argument("issue_url", help="GitHub issue URL")
    parser.add_argument("--branch", default="main", help="Branch name")
    parser.add_argument(
        "--from-scratch", action="store_true", help="Start from scratch"
    )
    parser.add_argument("--max-retries", type=int, default=3, help="Max retries")
    parser.add_argument("--dry-run", action="store_true", help="Dry run")
    parser.add_argument("--programmatic", action="store_true", help="Programmatic mode")
    parser.add_argument("--url", default="http://localhost:8000", help="Webhook URL")

    args = parser.parse_args()

    client = KickoffClient(base_url=args.url)
    result = client.run(
        issue_url=args.issue_url,
        branch=args.branch,
        from_scratch=args.from_scratch,
        max_retries=args.max_retries,
        dry_run=args.dry_run,
        programmatic=args.programmatic,
    )

    print(result)


if __name__ == "__main__":
    main()
