#!/usr/bin/env python
"""Code Pipeline - sequential crew execution."""

import argparse
import logging
import os

from mycrew.pipeline_runner import PipelineRunner

os.environ["LITELLM_REQUEST_TIMEOUT"] = "60"

logging.basicConfig(
    level=logging.INFO,
    format="%(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("mycrew")


def main():
    parser = argparse.ArgumentParser(description="Code Pipeline")
    parser.add_argument("issue_url", nargs="?", help="GitHub issue URL")
    parser.add_argument("--issue-url", dest="issue_url_alt", help="GitHub issue URL")
    parser.add_argument("--repo-path", help="Local repository path")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    issue_url = args.issue_url
    if issue_url is None:
        issue_url = args.issue_url_alt
    if issue_url is None:
        issue_url = ""

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    PipelineRunner(args.repo_path).run(issue_url)


if __name__ == "__main__":
    main()
