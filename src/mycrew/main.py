#!/usr/bin/env python
"""Code Pipeline - sequential crew execution."""

import argparse
import logging
import os


from mycrew.settings import get_settings, set_pipeline_context, PipelineContext
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
from mycrew.issues import IssueHandlerFactory
from mycrew.issues.exceptions import IssueFetchError, IssueParseError

os.environ["LITELLM_REQUEST_TIMEOUT"] = "60"

logging.basicConfig(
    level=logging.INFO,
    format="%(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("mycrew")


def run_pipeline(issue_url, repo_path):
    # Setup
    if repo_path:
        repo_path = os.path.abspath(repo_path)
    else:
        repo_path = os.getcwd()

    set_pipeline_context(PipelineContext(repo_path=repo_path))
    settings = get_settings()

    # Fetch issue using SOLID IssueHandler
    logger.info("[1/8] Fetching issue...")
    try:
        handler = IssueHandlerFactory.create(
            github_token=settings.github_token or None,
            gitlab_token=settings.gitlab_token or settings.github_token or None,
        )
        issue_content = handler.process(issue_url)
        logger.info(f"[1/8] Issue fetched: {issue_content.title}")
    except (IssueParseError, IssueFetchError) as e:
        logger.error(f"Failed to fetch issue: {e}")
        raise

    # Format issue content for crews
    issue_description = f"""# {issue_content.title}

{issue_content.body}

**Author:** {issue_content.author}
**Labels:** {", ".join(issue_content.labels) if issue_content.labels else "none"}
**State:** {issue_content.state}
**Source:** {issue_content.source.web_url}
"""

    # Extract issue number from URL for commit branch naming
    import re

    issue_number = "unknown"
    match = re.search(r"/issues/(\d+)", issue_url)
    if match:
        issue_number = match.group(1)

    # 3. Issue Analyst - needs structured issue content
    logger.info("[3/8] Starting Issue Analyst...")
    result = (
        IssueAnalystCrew()
        .crew()
        .kickoff(inputs={"issue_description": issue_description})
    )
    issue_analysis = result.raw
    logger.info("[3/8] Issue Analysis done")

    # 4. Explorer - needs issue_analysis + repo_path
    logger.info("[4/8] Starting Explorer...")
    result = (
        ExplorerCrew()
        .crew()
        .kickoff(
            inputs={
                "issue_analysis": issue_analysis,
                "repo_path": repo_path,
            }
        )
    )
    exploration = result.raw
    logger.info("[4/8] Exploration done")

    # 5. Clarify - needs issue_analysis + exploration
    logger.info("[5/8] Starting Clarify...")
    result = (
        ClarifyCrew()
        .crew()
        .kickoff(
            inputs={
                "issue_analysis": issue_analysis,
                "exploration": exploration,
                "repo_path": repo_path,
            }
        )
    )
    clarifications = result.raw
    logger.info("[5/8] Clarification done")

    # 6. Architect - needs all context (full, no truncation)
    logger.info("[6/8] Starting Architect...")
    result = (
        ArchitectCrew()
        .crew()
        .kickoff(
            inputs={
                "issue_description": issue_description,
                "issue_analysis": issue_analysis,
                "exploration": exploration,
                "clarifications": clarifications,
                "repo_path": repo_path,
            }
        )
    )
    plan = result.raw
    logger.info("[6/8] Planning done")

    # 7. Implementer - needs issue + plan (full context)
    logger.info("[7/8] Starting Implementer...")
    result = (
        ImplementerCrew()
        .crew()
        .kickoff(
            inputs={
                "issue_description": issue_description,
                "plan": plan,
                "repo_path": repo_path,
            }
        )
    )
    implementation = result.raw
    logger.info("[7/8] Implementation done")

    # Parse and write files
    files_spec = parse_code_blocks(implementation)
    if files_spec:
        logger.info(f"[7/8] Writing {len(files_spec)} files to {repo_path}...")
        written = write_files_from_specs(files_spec, repo_path)
        logger.info(f"[7/8] Files written: {written}")
    else:
        logger.warning(
            "[7/8] No files to write - could not parse implementation output"
        )

    # 8. TestValidator - needs plan + implementation + repo_path
    logger.info("[8/8] Starting Test Validator...")
    result = (
        TestValidatorCrew()
        .crew()
        .kickoff(
            inputs={
                "plan": plan,
                "implementation": implementation,
                "repo_path": repo_path,
            }
        )
    )
    tests = result.raw
    logger.info("[8/8] Test validation done")

    # 9. Reviewer - needs implementation + tests + repo_path
    logger.info("[9/8] Starting Reviewer...")
    result = (
        ReviewerCrew()
        .crew()
        .kickoff(
            inputs={
                "implementation": implementation,
                "tests": tests,
                "repo_path": repo_path,
            }
        )
    )
    review = result.raw
    logger.info("[9/8] Review done")

    # 10. Commit - needs implementation + review + repo_path + issue_number
    logger.info("[10/8] Starting Commit...")
    result = (
        CommitCrew()
        .crew()
        .kickoff(
            inputs={
                "implementation": implementation,
                "review": review,
                "repo_path": repo_path,
                "issue_number": issue_number,
            }
        )
    )
    commit = result.raw
    logger.info("[10/8] Commit done")

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
