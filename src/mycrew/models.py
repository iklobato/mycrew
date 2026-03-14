"""Absolute minimum database models for dynamic pipelines.

Guided by Principle 0: Simplicity First — Never Overengineer
1. Do the simplest thing that solves the CURRENT problem
2. JSONB fields instead of normalized tables when possible
3. No premature abstraction
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, validator


# ============================================================================
# CORE MODELS
# ============================================================================


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


class PipelineConfig(BaseModel):
    """Complete pipeline configuration stored as JSONB.

    Principle: Store everything in one JSON field instead of multiple tables.
    This matches the existing YAML structure exactly.
    """

    name: str = Field(
        description="Pipeline name (e.g., 'code-review', 'feature-implementation')"
    )
    description: Optional[str] = None

    # Pipeline-level settings (matches config.yaml)
    pipeline_settings: Dict[str, Any] = Field(
        default_factory=dict,
        description="Pipeline settings from config.yaml 'pipeline' section",
    )

    # Model configurations (matches config.yaml 'models' section)
    models: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict, description="Model configurations per stage"
    )

    # Tool configurations (matches config.yaml 'tools' section)
    tools: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict, description="Tool configurations"
    )

    # Agent configurations (matches config.yaml 'agents' section)
    agent_behavior: Dict[str, Any] = Field(
        default_factory=dict, description="Agent behavior tuning"
    )

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(frozen=True)

    @validator("name")
    def validate_name(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Pipeline name cannot be empty")
        return v.strip()


class CrewTemplate(BaseModel):
    """Simplest crew template - just the YAML content.

    Principle: Instead of parsing YAML into complex structures,
    store the YAML as-is and parse at runtime.
    This maintains 100% backward compatibility.
    """

    id: str = Field(
        description="Unique crew ID (e.g., 'explorer_crew', 'implementer_crew')"
    )
    name: str = Field(description="Human-readable name")

    # Store the actual YAML content
    agents_yaml: str = Field(description="agents.yaml content")
    tasks_yaml: str = Field(description="tasks.yaml content")

    # Optional metadata for dynamic assembly
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Optional metadata for dynamic assembly"
    )

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(frozen=True)

    @validator("id")
    def validate_id(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Crew ID cannot be empty")
        return v.strip().lower().replace(" ", "_")

    @validator("agents_yaml", "tasks_yaml")
    def validate_yaml_content(cls, v: str) -> str:
        """Simple validation - just ensure content is not empty."""
        if not v.strip():
            raise ValueError("YAML content cannot be empty")
        return v


class DynamicPipeline(BaseModel):
    """Dynamic pipeline instance linking users, configs, and crews.

    Principle: One table to rule them all. Instead of multiple join tables,
    store references and let the application handle relationships.
    """

    id: str = Field(description="Unique pipeline instance ID")
    user_id: str = Field(description="User who owns/triggered this pipeline")

    # Configuration references (all optional for flexibility)
    pipeline_config_id: Optional[str] = None
    crew_template_ids: List[str] = Field(
        default_factory=list,
        description="List of crew template IDs to execute in order",
    )

    # Runtime state
    status: str = Field(
        default="pending",
        description="Pipeline status: pending, running, completed, failed",
    )

    # Input/Output
    input: Dict[str, Any] = Field(
        default_factory=dict, description="Pipeline input (task, repo_path, etc.)"
    )

    output: Dict[str, Any] = Field(
        default_factory=dict, description="Pipeline output (results, artifacts, etc.)"
    )

    # Metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(frozen=True)

    @validator("id")
    def validate_id(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Pipeline ID cannot be empty")
        return v.strip()

    @validator("status")
    def validate_status(cls, v: str) -> str:
        valid_statuses = {"pending", "running", "completed", "failed"}
        if v not in valid_statuses:
            raise ValueError(f"Status must be one of: {valid_statuses}")
        return v
