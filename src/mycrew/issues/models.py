"""Issue data models."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class IssueSourceType(Enum):
    """Supported issue tracker types."""

    GITHUB = "github"
    GITLAB = "gitlab"


@dataclass(frozen=True)
class IssueSource:
    """Identifies where an issue lives."""

    source_type: IssueSourceType
    owner: str
    repo: str
    issue_number: int
    web_url: str


@dataclass(frozen=True)
class IssueContent:
    """Parsed issue content from an issue tracker."""

    title: str
    body: str
    author: str
    labels: list[str]
    state: str
    created_at: datetime
    source: IssueSource
