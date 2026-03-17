#!/usr/bin/env python
"""Minimal Code Pipeline - sequential crew execution with context passing."""

import logging
import os

from pydantic import BaseModel

from mycrew.settings import set_pipeline_context, PipelineContext

logging.basicConfig(
    level=logging.INFO,
    format="%(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("mycrew")


def _truncate(text: str, max_len: int = 2000) -> str:
    """Truncate text to avoid token limits."""
    if not text:
        return ""
    return text[:max_len] if len(text) > max_len else text


class PipelineState(BaseModel):
    """Pipeline state."""

    issue_url: str = ""
    repo_path: str = ""
    issue_analysis: str = ""
    exploration: str = ""
    clarifications: str = ""
    plan: str = ""
    implementation: str = ""
    tests: str = ""
    review: str = ""
    commit: str = ""


def run_pipeline(issue_url: str, repo_path: str = "") -> PipelineState:
    """Run the full pipeline sequentially."""
    if not repo_path:
        repo_path = os.getcwd()
    repo_path = os.path.abspath(repo_path)

    ctx = PipelineContext(repo_path=repo_path)
    set_pipeline_context(ctx)

    state = PipelineState(issue_url=issue_url, repo_path=repo_path)

    # 1. Issue Analyst - receives issue_url
    from mycrew.crews.issue_analyst_crew.issue_analyst_crew import IssueAnalystCrew

    logger.info("[1/8] Starting Issue Analyst...")
    crew = IssueAnalystCrew().crew()
    result = crew.kickoff(inputs={"issue_url": issue_url})
    state.issue_analysis = result.raw[:1500] if result.raw else ""
    logger.info(f"[1/8] Issue Analysis done: {state.issue_analysis[:80]}...")

    # 2. Explorer - receives issue_analysis + repo_path via context
    from mycrew.crews.explorer_crew.explorer_crew import ExplorerCrew

    logger.info("[2/8] Starting Explorer...")
    crew = ExplorerCrew().crew()
    result = crew.kickoff(
        inputs={
            "issue_analysis": _truncate(state.issue_analysis),
            "repo_path": repo_path,
        }
    )
    state.exploration = result.raw[:1500] if result.raw else ""
    logger.info(f"[2/8] Exploration done: {state.exploration[:80]}...")

    # 3. Clarify - receives issue_analysis + exploration via context
    from mycrew.crews.clarify_crew.clarify_crew import ClarifyCrew

    logger.info("[3/8] Starting Clarify...")
    crew = ClarifyCrew().crew()
    result = crew.kickoff(
        inputs={
            "issue_analysis": _truncate(state.issue_analysis),
            "exploration": _truncate(state.exploration),
        }
    )
    state.clarifications = result.raw[:1500] if result.raw else ""
    logger.info(f"[3/8] Clarification done: {state.clarifications[:80]}...")

    # 4. Architect - receives all previous via context
    from mycrew.crews.architect_crew.architect_crew import ArchitectCrew

    logger.info("[4/8] Starting Architect...")
    crew = ArchitectCrew().crew()
    result = crew.kickoff(
        inputs={
            "issue_analysis": _truncate(state.issue_analysis),
            "exploration": _truncate(state.exploration),
            "clarifications": _truncate(state.clarifications),
        }
    )
    state.plan = result.raw[:1500] if result.raw else ""
    logger.info(f"[4/8] Planning done: {state.plan[:80]}...")

    # 5. Implementer - receives all previous via context
    from mycrew.crews.implementer_crew.implementer_crew import ImplementerCrew

    logger.info("[5/8] Starting Implementer...")
    crew = ImplementerCrew().crew()
    result = crew.kickoff(
        inputs={
            "issue_analysis": _truncate(state.issue_analysis),
            "exploration": _truncate(state.exploration),
            "clarifications": _truncate(state.clarifications),
            "plan": _truncate(state.plan),
        }
    )
    state.implementation = result.raw[:1500] if result.raw else ""
    logger.info(f"[5/8] Implementation done: {state.implementation[:80]}...")

    # 6. Test Validator - receives all previous via context
    from mycrew.crews.test_validator_crew.test_validator_crew import TestValidatorCrew

    logger.info("[6/8] Starting Test Validator...")
    crew = TestValidatorCrew().crew()
    result = crew.kickoff(
        inputs={
            "issue_analysis": _truncate(state.issue_analysis),
            "exploration": _truncate(state.exploration),
            "clarifications": _truncate(state.clarifications),
            "plan": _truncate(state.plan),
            "implementation": _truncate(state.implementation),
        }
    )
    state.tests = result.raw[:1500] if result.raw else ""
    logger.info(f"[6/8] Test validation done: {state.tests[:80]}...")

    # 7. Reviewer - receives all previous via context
    from mycrew.crews.reviewer_crew.reviewer_crew import ReviewerCrew

    logger.info("[7/8] Starting Reviewer...")
    crew = ReviewerCrew().crew()
    result = crew.kickoff(
        inputs={
            "issue_analysis": _truncate(state.issue_analysis),
            "exploration": _truncate(state.exploration),
            "clarifications": _truncate(state.clarifications),
            "plan": _truncate(state.plan),
            "implementation": _truncate(state.implementation),
            "tests": _truncate(state.tests),
        }
    )
    state.review = result.raw[:1500] if result.raw else ""
    logger.info(f"[7/8] Review done: {state.review[:80]}...")

    # 8. Commit - receives all previous via context
    from mycrew.crews.commit_crew.commit_crew import CommitCrew

    logger.info("[8/8] Starting Commit...")
    crew = CommitCrew().crew()
    result = crew.kickoff(
        inputs={
            "issue_analysis": _truncate(state.issue_analysis),
            "exploration": _truncate(state.exploration),
            "clarifications": _truncate(state.clarifications),
            "plan": _truncate(state.plan),
            "implementation": _truncate(state.implementation),
            "tests": _truncate(state.tests),
            "review": _truncate(state.review),
        }
    )
    state.commit = result.raw[:1500] if result.raw else ""
    logger.info(f"[8/8] Commit done: {state.commit[:80]}...")

    return state


def kickoff(issue_url: str, repo_path: str = "", **kwargs):
    """Programmatic entry point."""
    return run_pipeline(issue_url, repo_path)


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Code Pipeline")
    parser.add_argument("issue_url", nargs="?", help="GitHub issue URL")
    parser.add_argument(
        "--issue-url", dest="issue_url_alt", help="GitHub issue URL (alternative)"
    )
    parser.add_argument("--repo-path", help="Local repository path")
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose logging"
    )
    args = parser.parse_args()

    issue_url = args.issue_url or args.issue_url_alt or ""

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    result = kickoff(issue_url, repo_path=args.repo_path or "")
    logger.info(f"Result: {result}")


if __name__ == "__main__":
    main()
