"""Pipeline state - minimal top-level fields with stage results."""

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path


logger = logging.getLogger(__name__)


class PipelineStep(str, Enum):
    """Pipeline step names for step-by-step execution."""

    EXPLORE = "EXPLORE"
    ANALYZE = "ANALYZE"
    ARCHITECT = "ARCHITECT"
    IMPLEMENT = "IMPLEMENT"
    REVIEW = "REVIEW"
    VALIDATE_TESTS = "VALIDATE_TESTS"
    COMMIT = "COMMIT"


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


class PipelineStateManager:
    """Manages pipeline state persistence - SRP for state I/O."""

    STATE_DIR = os.path.expanduser("~/.mycrew/state")

    @classmethod
    def ensure_state_dir(cls) -> None:
        """Ensure state directory exists."""
        os.makedirs(cls.STATE_DIR, exist_ok=True)

    @classmethod
    def save_step_result(cls, step: PipelineStep, data: dict) -> str:
        """Save step result to JSON file. Returns file path."""
        cls.ensure_state_dir()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{step.value}_{timestamp}.json"
        filepath = os.path.join(cls.STATE_DIR, filename)

        output = {
            "step": step.value,
            "timestamp": datetime.now().isoformat(),
            "data": data,
        }

        with open(filepath, "w") as f:
            json.dump(output, f, indent=2)

        logger.info(f"Saved step result to: {filepath}")
        return filepath

    @classmethod
    def load_step_result(cls, filepath: str) -> dict | None:
        """Load step result from a specific file path."""
        try:
            with open(filepath, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Failed to load step result from {filepath}: {e}")
            return None

    @classmethod
    def get_latest_result_for_step(cls, step: PipelineStep) -> dict | None:
        """Find and load latest result file for a step in state dir."""
        cls.ensure_state_dir()

        # Find all files matching the step pattern
        pattern = f"{step.value}_*.json"
        files = sorted(
            Path(cls.STATE_DIR).glob(pattern),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

        if not files:
            logger.warning(f"No previous result found for step: {step.value}")
            return None

        latest_file = files[0]
        logger.info(f"Loading latest result for {step.value} from: {latest_file}")
        return cls.load_step_result(str(latest_file))


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
    current_stage: Stage = Stage.EXPLORE  # type: ignore[assignment]
    retry_count: int = 0
    tactiq_meeting_id: str = ""
    repo_path_cloned: bool = False

    # Step-by-step execution
    target_steps: list[PipelineStep] | None = None
    input_file: str = ""

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
