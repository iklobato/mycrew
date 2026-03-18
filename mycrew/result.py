"""Stage result dataclasses with enum fields."""

from dataclasses import dataclass, field

from enum import StrEnum


class StageStatus(StrEnum):
    """Stage execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Verdict(StrEnum):
    """Review verdict values."""

    APPROVED = "APPROVED"
    ISSUES = "ISSUES"


@dataclass
class StageResult:
    """Base result for any stage."""

    status: StageStatus = StageStatus.PENDING
    data: dict | None = None
    error: str | None = None


@dataclass
class ReviewResult(StageResult):
    """Review stage result with verdict."""

    verdict: Verdict = Verdict.ISSUES
    issues: list[str] = field(default_factory=list)


@dataclass
class ValidationResult(StageResult):
    """Test validation result."""

    passed: bool = False
    output: str = ""
