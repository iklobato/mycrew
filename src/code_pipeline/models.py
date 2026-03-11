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


# ============================================================================
# SIMPLEST POSSIBLE DATABASE SCHEMA
# ============================================================================

"""
SQL Schema (PostgreSQL with JSONB, but could be SQLite with TEXT + json_extract):

CREATE TABLE users (
    id TEXT PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    api_keys JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE pipeline_configs (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    name TEXT NOT NULL,
    description TEXT,
    pipeline_settings JSONB NOT NULL DEFAULT '{}'::jsonb,
    models JSONB NOT NULL DEFAULT '{}'::jsonb,
    tools JSONB NOT NULL DEFAULT '{}'::jsonb,
    agent_behavior JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE crew_templates (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    agents_yaml TEXT NOT NULL,
    tasks_yaml TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE dynamic_pipelines (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    user_id TEXT NOT NULL REFERENCES users(id),
    pipeline_config_id TEXT REFERENCES pipeline_configs(id),
    crew_template_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed')),
    input JSONB NOT NULL DEFAULT '{}'::jsonb,
    output JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE
);

-- Minimal indexes for the simplest queries
CREATE INDEX idx_dynamic_pipelines_user_id ON dynamic_pipelines(user_id);
CREATE INDEX idx_dynamic_pipelines_status ON dynamic_pipelines(status);
CREATE INDEX idx_dynamic_pipelines_created_at ON dynamic_pipelines(created_at DESC);

Note: This is the ABSOLUTE MINIMUM schema that enables:
1. Multi-user support (users table)
2. Dynamic pipeline configurations (pipeline_configs table)
3. Reusable crew templates (crew_templates table)
4. Pipeline execution tracking (dynamic_pipelines table)

Total: 4 tables, 3 indexes. No joins, no complex relationships.
"""


# ============================================================================
# MIGRATION UTILITIES
# ============================================================================


class MigrationHelper:
    """Helper for migrating from YAML files to database."""

    @staticmethod
    def crew_template_from_yaml_files(
        crew_id: str,
        name: str,
        agents_yaml_path: str,
        tasks_yaml_path: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> CrewTemplate:
        """Create a crew template from existing YAML files.

        This maintains 100% backward compatibility - we're just storing
        the YAML content in the database instead of reading from files.
        """
        import yaml
        from pathlib import Path

        # Read YAML files
        agents_content = Path(agents_yaml_path).read_text()
        tasks_content = Path(tasks_yaml_path).read_text()

        # Optionally validate YAML (but don't parse into objects - keep as text)
        try:
            yaml.safe_load(agents_content)
            yaml.safe_load(tasks_content)
        except yaml.YAMLError as e:
            raise ValueError(
                f"Invalid YAML in {agents_yaml_path or tasks_yaml_path}: {e}"
            )

        return CrewTemplate(
            id=crew_id,
            name=name,
            agents_yaml=agents_content,
            tasks_yaml=tasks_content,
            metadata=metadata or {},
        )

    @staticmethod
    def pipeline_config_from_yaml_file(
        config_id: str, name: str, config_yaml_path: str
    ) -> PipelineConfig:
        """Create a pipeline config from existing config.yaml."""
        import yaml
        from pathlib import Path

        content = Path(config_yaml_path).read_text()
        config_data = yaml.safe_load(content)

        return PipelineConfig(
            name=name,
            description=f"Migrated from {config_yaml_path}",
            pipeline_settings=config_data.get("pipeline", {}),
            models=config_data.get("models", {}),
            tools=config_data.get("tools", {}),
            agent_behavior=config_data.get("agents", {}),
        )


# ============================================================================
# BACKWARD COMPATIBILITY LAYER
# ============================================================================


class BackwardCompatibility:
    """Maintain backward compatibility with existing YAML configs."""

    def __init__(self, default_config_path: str = "config.yaml"):
        self.default_config_path = default_config_path

    def load_config(self) -> Dict[str, Any]:
        """Load config from YAML file (existing behavior)."""
        import yaml
        from pathlib import Path

        if Path(self.default_config_path).exists():
            with open(self.default_config_path) as f:
                return yaml.safe_load(f)
        return {}

    def get_crew_yaml(self, crew_dir: str) -> tuple[str, str]:
        """Get agents.yaml and tasks.yaml from crew directory."""
        from pathlib import Path

        agents_path = Path(crew_dir) / "config" / "agents.yaml"
        tasks_path = Path(crew_dir) / "config" / "tasks.yaml"

        if not agents_path.exists() or not tasks_path.exists():
            raise FileNotFoundError(
                f"Missing YAML files in {crew_dir}: {agents_path.name}, {tasks_path.name}"
            )

        return agents_path.read_text(), tasks_path.read_text()


# ============================================================================
# SIMPLEST AUTHENTICATION
# ============================================================================


class SimpleAuth:
    """Absolute minimum authentication for multi-user.

    Principle: Start with API key authentication only.
    No passwords, no OAuth, no sessions - just API keys.
    """

    @staticmethod
    def authenticate_user(api_key: str) -> Optional[User]:
        """Simplest possible authentication: lookup user by API key.

        In production, you'd want to:
        1. Hash API keys before storage
        2. Add rate limiting
        3. Add key rotation

        But for MVP: just check if key exists.
        """
        # This would query the database
        # For now, return a mock user
        return None

    @staticmethod
    def create_user(user_id: str, api_keys: Dict[str, str]) -> User:
        """Create a new user with API keys."""
        return User(id=user_id, api_keys=api_keys)
