"""Centralized configuration from environment and config file.

All env/config MUST be accessed via get_settings() or get_pipeline_context().
No os.environ.get outside this module.
"""

import os
from contextvars import ContextVar
from typing import Any

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Context var for per-flow runtime context (set by main before each crew)
_pipeline_context_var: ContextVar["PipelineContext | None"] = ContextVar(
    "pipeline_context", default=None
)

# Global settings instance (initialized once, optionally updated from config)
_settings: "Settings | None" = None


class PipelineContext(BaseModel):
    """Runtime context for the current flow. Set before each crew run."""

    model_config = {"frozen": True}

    repo_path: str = ""
    github_repo: str = ""
    issue_url: str = ""
    serper_enabled: bool = False
    programmatic: bool = False


class Settings(BaseSettings):
    """Centralized settings from environment variables.

    Load once at startup. Config file can update via init_settings_from_config().
    """

    model_config = SettingsConfigDict(
        env_prefix="",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # API keys (required for pipeline, optional for serper)
    openrouter_api_key: str = Field(default="", alias="OPENROUTER_API_KEY")
    huggingface_api_key: str = Field(default="", alias="HUGGINGFACE_API_KEY")
    github_token: str = Field(default="", alias="GITHUB_TOKEN")
    serper_api_key: str = Field(default="", alias="SERPER_API_KEY")

    # Webhook defaults
    github_webhook_secret: str = Field(default="", alias="GITHUB_WEBHOOK_SECRET")
    default_dry_run: bool = Field(default=False, alias="DEFAULT_DRY_RUN")
    default_branch: str = Field(default="main", alias="DEFAULT_BRANCH")

    # Webhook server
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")

    # Redis URL (optional)
    redis_url: str = Field(default="", alias="REDIS_URL")

    # Logging
    code_pipeline_log_level: str = Field(
        default="INFO", alias="CODE_PIPELINE_LOG_LEVEL"
    )
    crewai_telemetry: bool = Field(default=False, alias="CREWAI_TRACING_ENABLED")

    # Provider configuration
    provider_type: str | None = Field(default=None, alias="PROVIDER_TYPE")

    def apply_crewai_telemetry(self) -> None:
        """Apply crewai_telemetry to os.environ for CrewAI library."""
        import os

        os.environ["CREWAI_TRACING_ENABLED"] = str(self.crewai_telemetry).lower()


def get_settings() -> Settings:
    """Return the singleton Settings. Initializes from env if not yet loaded."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def init_settings_from_config(config_data: dict[str, Any]) -> None:
    """Update settings from parsed config file. Call after loading YAML."""
    import os

    global _settings
    settings = get_settings()

    # API keys: expand ${VAR} from env, or use literal
    if "api_keys" in config_data:
        api_keys = config_data["api_keys"]
        for config_key, attr_name in [
            ("openrouter_api_key", "openrouter_api_key"),
            ("huggingface_api_key", "huggingface_api_key"),
            ("github_token", "github_token"),
            ("serper_api_key", "serper_api_key"),
        ]:
            if config_key not in api_keys:
                continue
            val = api_keys[config_key]
            if not isinstance(val, str):
                continue
            if val.strip().startswith("${") and val.strip().endswith("}"):
                var_name = val.strip()[2:-1]
                val = os.environ.get(var_name, "")
            if val:
                object.__setattr__(settings, attr_name, str(val).strip())

    # Provider type
    if "provider_type" in config_data:
        val = config_data["provider_type"]
        if val:
            object.__setattr__(settings, "provider_type", str(val).strip())

    # Logging
    if "logging" in config_data:
        log_cfg = config_data["logging"]
        if log_cfg.get("level"):
            object.__setattr__(
                settings, "code_pipeline_log_level", str(log_cfg["level"]).upper()
            )
        if log_cfg.get("crewai_telemetry"):
            object.__setattr__(settings, "crewai_telemetry", True)

    _settings = settings


def set_pipeline_context(ctx: PipelineContext) -> None:
    """Set the current flow's context. Call before each crew run."""
    _pipeline_context_var.set(ctx)


def get_pipeline_context() -> PipelineContext:
    """Return the current flow's context with resolved repo_path and github_repo.

    repo_path is always absolute. github_repo is stripped (empty string if unset).
    Crews can use ctx.repo_path, ctx.github_repo, ctx.serper_enabled directly.
    """
    ctx = _pipeline_context_var.get()
    if ctx is None:
        ctx = PipelineContext()
    rp = ctx.repo_path
    if rp is None or rp == "":
        rp = os.getcwd()
    gh = ctx.github_repo
    if gh is None:
        gh = ""
    iu = ctx.issue_url
    if iu is None:
        iu = ""
    return PipelineContext(
        repo_path=os.path.abspath(rp),
        github_repo=gh.strip(),
        issue_url=iu.strip(),
        serper_enabled=ctx.serper_enabled,
        programmatic=ctx.programmatic,
    )
