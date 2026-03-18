#!/usr/bin/env python
"""CLI for mycrew pipelines - supports development and review pipelines."""

import argparse
import logging
import os
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("mycrew")


def run_development(args: argparse.Namespace) -> None:
    from mycrew.pipelines.development.pipeline_runner import PipelineRunner

    issue_url = args.issue_url or args.issue_url_alt or ""
    PipelineRunner(args.repo_path).run(issue_url)


def run_review(args: argparse.Namespace) -> None:
    from mycrew.pipelines.review.review_runner import ReviewRunner

    if not args.pr_url and not args.pr_url_alt:
        print("Error: PR URL is required for review pipeline")
        sys.exit(1)

    pr_url = args.pr_url or args.pr_url_alt
    ReviewRunner(args.repo_path).run(pr_url)


def main():
    parser = argparse.ArgumentParser(
        description="mycrew - AI-powered development pipelines"
    )
    subparsers = parser.add_subparsers(dest="pipeline", help="Pipeline to run")

    dev_parser = subparsers.add_parser(
        "development",
        aliases=["dev"],
        help="Issue to implementation pipeline",
    )
    dev_parser.add_argument("issue_url", nargs="?", help="GitHub issue URL")
    dev_parser.add_argument(
        "--issue-url", dest="issue_url_alt", help="GitHub issue URL"
    )
    dev_parser.add_argument("--repo-path", help="Local repository path")
    dev_parser.add_argument("-v", "--verbose", action="store_true")
    dev_parser.set_defaults(func=run_development)

    review_parser = subparsers.add_parser(
        "review",
        aliases=["rev"],
        help="PR review pipeline",
    )
    review_parser.add_argument("pr_url", nargs="?", help="GitHub/GitLab PR URL")
    review_parser.add_argument(
        "--review-url", dest="pr_url_alt", help="GitHub/GitLab PR URL"
    )
    review_parser.add_argument("--repo-path", help="Local repository path")
    review_parser.add_argument("-v", "--verbose", action="store_true")
    review_parser.set_defaults(func=run_review)

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()
        print("")
        print("Usage examples:")
        print("  ./cli.py development <issue-url>")
        print("  ./cli.py dev <issue-url> --repo-path /path/to/repo")
        print("  ./cli.py review <pr-url>")
        print("  ./cli.py rev <pr-url> --repo-path /path/to/repo")
        sys.exit(1)


if __name__ == "__main__":
    main()
