#!/usr/bin/env python
"""Code Pipeline - sequential crew execution."""

import argparse
import logging
import os


from mycrew.settings import set_pipeline_context, PipelineContext
from mycrew.crews.issue_analyst_crew.issue_analyst_crew import IssueAnalystCrew
from mycrew.crews.explorer_crew.explorer_crew import ExplorerCrew
from mycrew.crews.clarify_crew.clarify_crew import ClarifyCrew
from mycrew.crews.architect_crew.architect_crew import ArchitectCrew
from mycrew.crews.implementer_crew.implementer_crew import (
    ImplementerCrew,
    parse_code_blocks,
    write_files_from_specs,
)
from mycrew.crews.test_validator_crew.test_validator_crew import TestValidatorCrew
from mycrew.crews.reviewer_crew.reviewer_crew import ReviewerCrew
from mycrew.crews.commit_crew.commit_crew import CommitCrew

os.environ["LITELLM_REQUEST_TIMEOUT"] = "60"

logging.basicConfig(
    level=logging.INFO,
    format="%(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("mycrew")


def truncate_text(text: str, max_chars: int = 5000) -> str:
    """Truncate text to max characters."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n[truncated]"


def run_pipeline(issue_url, repo_path):
    # Setup
    if repo_path:
        repo_path = os.path.abspath(repo_path)
    else:
        repo_path = os.getcwd()

    set_pipeline_context(PipelineContext(repo_path=repo_path))

    # 1. Issue Analyst - only needs issue_url
    logger.info("[1/8] Starting Issue Analyst...")
    result = IssueAnalystCrew().crew().kickoff(inputs={"issue_url": issue_url})
    issue_analysis = result.raw
    logger.info("[1/8] Issue Analysis done")

    # 2. Explorer - needs issue_analysis + repo_path (truncated)
    logger.info("[2/8] Starting Explorer...")
    truncated_analysis = truncate_text(issue_analysis, max_chars=2000)
    result = (
        ExplorerCrew()
        .crew()
        .kickoff(
            inputs={
                "issue_analysis": truncated_analysis,
                "repo_path": repo_path,
            }
        )
    )
    exploration = result.raw
    logger.info("[2/8] Exploration done")

    # 3. Clarify - needs issue_analysis + exploration (both truncated)
    logger.info("[3/8] Starting Clarify...")
    result = (
        ClarifyCrew()
        .crew()
        .kickoff(
            inputs={
                "issue_analysis": truncate_text(issue_analysis, max_chars=1500),
                "exploration": truncate_text(exploration, max_chars=3000),
                "repo_path": repo_path,
            }
        )
    )
    clarifications = result.raw
    logger.info("[3/8] Clarification done")

    # 4. Architect - needs issue_analysis + exploration + clarifications (truncated)
    logger.info("[4/8] Starting Architect...")
    result = (
        ArchitectCrew()
        .crew()
        .kickoff(
            inputs={
                "issue_analysis": truncate_text(issue_analysis, max_chars=1000),
                "exploration": truncate_text(exploration, max_chars=2000),
                "clarifications": truncate_text(clarifications, max_chars=2000),
                "repo_path": repo_path,
            }
        )
    )
    plan = result.raw
    logger.info("[4/8] Planning done")

    # 5. Implementer - needs just the plan (truncated)
    logger.info("[5/8] Starting Implementer...")
    result = (
        ImplementerCrew()
        .crew()
        .kickoff(
            inputs={
                "plan": truncate_text(plan, max_chars=3000),
                "repo_path": repo_path,
            }
        )
    )
    implementation = result.raw
    logger.info("[5/8] Implementation done")

    # Parse and write files
    files_spec = parse_code_blocks(implementation)
    if files_spec:
        logger.info(f"[5/8] Writing {len(files_spec)} files to {repo_path}...")
        written = write_files_from_specs(files_spec, repo_path)
        logger.info(f"[5/8] Files written: {written}")
    else:
        logger.warning(
            "[5/8] No files to write - could not parse implementation output"
        )

    # 6. TestValidator - needs plan + implementation + repo_path
    logger.info("[6/8] Starting Test Validator...")
    result = (
        TestValidatorCrew()
        .crew()
        .kickoff(
            inputs={
                "plan": truncate_text(plan, max_chars=2000),
                "implementation": truncate_text(implementation, max_chars=3000),
                "repo_path": repo_path,
            }
        )
    )
    tests = result.raw
    logger.info("[6/8] Test validation done")

    # 7. Reviewer - needs implementation + tests + repo_path
    logger.info("[7/8] Starting Reviewer...")
    result = (
        ReviewerCrew()
        .crew()
        .kickoff(
            inputs={
                "implementation": truncate_text(implementation, max_chars=3000),
                "tests": truncate_text(tests, max_chars=2000),
                "repo_path": repo_path,
            }
        )
    )
    review = result.raw
    logger.info("[7/8] Review done")

    # 8. Commit - needs implementation + review + repo_path
    logger.info("[8/8] Starting Commit...")
    result = (
        CommitCrew()
        .crew()
        .kickoff(
            inputs={
                "implementation": truncate_text(implementation, max_chars=2000),
                "review": truncate_text(review, max_chars=1500),
                "repo_path": repo_path,
            }
        )
    )
    commit = result.raw
    logger.info("[8/8] Commit done")

    return {
        "issue_analysis": issue_analysis,
        "exploration": exploration,
        "clarifications": clarifications,
        "plan": plan,
        "implementation": implementation,
        "tests": tests,
        "review": review,
        "commit": commit,
    }


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

    run_pipeline(issue_url, args.repo_path)
    logger.info("Pipeline complete")


if __name__ == "__main__":
    main()
