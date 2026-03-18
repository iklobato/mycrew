"""PR models."""

from dataclasses import dataclass
from enum import Enum


class PRSourceType(Enum):
    GITHUB = "github"
    GITLAB = "gitlab"


@dataclass(frozen=True)
class PRSource:
    source_type: PRSourceType
    owner: str
    repo: str
    pr_number: int
    web_url: str


@dataclass(frozen=True)
class PRContent:
    title: str
    body: str
    author: str
    labels: list[str]
    state: str
    source: PRSource
    diff: str
    files_changed: list[str]
