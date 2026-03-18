"""Review pipeline CLI."""

import argparse
import logging

from mycrew.pipelines.review.review_runner import ReviewRunner

logging.basicConfig(
    level=logging.INFO,
    format="%(name)s - %(levelname)s - %(message)s",
)


def main():
    parser = argparse.ArgumentParser(description="Review Pipeline")
    parser.add_argument("pr_url", nargs="?", help="GitHub/GitLab PR URL")
    parser.add_argument("--review-url", dest="pr_url_alt", help="GitHub/GitLab PR URL")
    parser.add_argument("--repo-path", help="Local repository path")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    pr_url = args.pr_url
    if pr_url is None:
        pr_url = args.pr_url_alt
    if pr_url is None:
        print("Error: --review-url is required")
        return

    ReviewRunner(args.repo_path).run(pr_url)


if __name__ == "__main__":
    main()
