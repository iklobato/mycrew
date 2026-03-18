#!/usr/bin/env python
"""Code Pipeline - dispatches to development or review pipelines."""

import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(name)s - %(levelname)s - %(message)s",
)


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m mycrew [development|review] [options]")
        print("")
        print("Pipelines:")
        print("  development  - Issue to implementation pipeline")
        print("  review       - PR review pipeline")
        print("")
        print(
            "Run 'python -m mycrew.development --help' or 'python -m mycrew.review --help' for options"
        )
        sys.exit(1)

    pipeline = sys.argv[1]

    if pipeline == "development":
        from mycrew.pipelines.development.cli import main as dev_main

        dev_main()
    elif pipeline == "review":
        from mycrew.pipelines.review.cli import main as review_main

        review_main()
    else:
        print(f"Unknown pipeline: {pipeline}")
        print("Valid pipelines: development, review")
        sys.exit(1)


if __name__ == "__main__":
    main()
