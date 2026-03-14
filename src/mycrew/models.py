"""Absolute minimum database models for dynamic pipelines.

Guided by Principle 0: Simplicity First — Never Overengineer
1. Do the simplest thing that solves the CURRENT problem
2. JSONB fields instead of normalized tables when possible
3. No premature abstraction
"""

from datetime import datetime, timezone
from typing import Any, Dict

from pydantic import BaseModel, ConfigDict, Field, validator


class User(BaseModel):
    """Absolute minimum user model for multi-user support.

    Principle: Start with the simplest authentication that works.
    We only need to identify users, not implement complex auth flows.
    """

    id: str = Field(description="Unique user ID (e.g., GitHub username, email)")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    api_keys: Dict[str, str] = Field(
        default_factory=dict,
        description="API keys for services (OpenRouter, GitHub, etc.)",
    )

    model_config = ConfigDict(frozen=True)

    @validator("id")
    def validate_id(cls, v: str) -> str:
        """Simple validation - just ensure it's not empty."""
        if not v.strip():
            raise ValueError("User ID cannot be empty")
        return v.strip()
