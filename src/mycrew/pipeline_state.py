"""Pipeline state - minimal top-level fields with stage results."""

from dataclasses import dataclass


class Stage:
    """Pipeline stage names - simple class to avoid circular import."""

    EXPLORE = "explore"
    ANALYZE = "analyze"
    ARCHITECT = "architect"
    IMPLEMENT = "implement"
    REVIEW = "review"
    VALIDATE_TESTS = "validate_tests"
    COMMIT = "commit"


# Import after class definition to avoid circular imports
from mycrew.result import StageResult, ReviewResult, ValidationResult, StageStatus  # noqa: E402


@dataclass
class PipelineState:
    """Minimal pipeline state container."""

    id: str = ""
    issue_url: str = ""
    branch: str = ""
    max_retries: int = 3
    dry_run: bool = False
    programmatic: bool = False
    repo_path: str = ""
    repo_root: str | None = None
    issue_data: dict | None = None
    current_stage: Stage = Stage.EXPLORE
    retry_count: int = 0
    tactiq_meeting_id: str = ""
    repo_path_cloned: bool = False

    # Stage results - set as attributes after creation
    explore_result: "StageResult | None" = None
    analyze_result: "StageResult | None" = None
    architect_result: "StageResult | None" = None
    implement_result: "StageResult | None" = None
    review_result: "ReviewResult | None" = None
    validation_result: "ValidationResult | None" = None
    commit_result: "StageResult | None" = None
    tactiq_result: "StageResult | None" = None

    def get_result_for_stage(self, stage: Stage) -> "StageResult | None":
        """Get result for a given stage."""
        stage_attr = f"{stage.value}_result"
        return getattr(self, stage_attr, None)

    def set_result_for_stage(self, stage: Stage, result: "StageResult"):
        """Set result for a given stage."""
        stage_attr = f"{stage.value}_result"
        setattr(self, stage_attr, result)
