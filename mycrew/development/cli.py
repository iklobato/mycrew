"""Development pipeline CLI."""

import argparse
import logging

from mycrew.development.pipeline_runner import PipelineRunner

logging.basicConfig(
    level=logging.INFO,
    format="%(name)s - %(levelname)s - %(message)s",
)


def main():
    parser = argparse.ArgumentParser(description="Development Pipeline")
    parser.add_argument("issue_url", nargs="?", help="GitHub issue URL")
    parser.add_argument("--issue-url", dest="issue_url_alt", help="GitHub issue URL")
    parser.add_argument("--repo-path", help="Local repository path")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    issue_url = args.issue_url
    if issue_url is None:
        issue_url = args.issue_url_alt
    if issue_url is None:
        issue_url = ""

    PipelineRunner(args.repo_path).run(issue_url)


if __name__ == "__main__":
    main()
