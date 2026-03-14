"""Shared LLM configuration for OpenRouter with stage-specific models and fallbacks."""

import logging
import yaml
from dataclasses import dataclass
from enum import Enum, StrEnum
from pathlib import Path
from typing import Any

from crewai import LLM

from code_pipeline.providers import create_provider
from code_pipeline.utils import log_exceptions

logger = logging.getLogger(__name__)


# LiteLLM: when True, inserts user continue message if last message is assistant
# (fixes Anthropic "assistant message prefill" error when using OpenRouter/Claude)
try:
    import litellm
    from litellm.integrations.custom_logger import CustomLogger

    litellm.modify_params = True

    class _OpenRouterLogger(CustomLogger):
        """Log all OpenRouter API calls via logging.info."""

        def log_pre_api_call(
            self, model: str, messages: list[Any], kwargs: dict[str, Any]
        ) -> None:
            if model and str(model).startswith("openrouter/"):
                if messages:
                    n = len(messages)
                else:
                    n = 0
                logger.info(
                    "OpenRouter pre_call model=%s messages=%d",
                    model,
                    n,
                )

        def log_success_event(
            self,
            kwargs: dict[str, Any],
            response_obj: object,
            start_time: float | None,
            end_time: float | None,
        ) -> None:
            model = kwargs.get("model", "")
            if not str(model).startswith("openrouter/"):
                return
            duration = ""
            if start_time is not None and end_time is not None:
                delta = end_time - start_time
                secs = getattr(delta, "total_seconds", lambda: float(delta))()
                duration = " duration=%.2fs" % secs
            usage = getattr(response_obj, "usage", None)
            tokens = ""
            if usage:
                total = getattr(usage, "total_tokens", None)
                if total is None and isinstance(usage, dict):
                    total = usage.get("total_tokens")
                if total is not None:
                    tokens = " tokens=%s" % total
            logger.info(
                "OpenRouter success model=%s%s%s",
                model,
                duration,
                tokens,
            )

        def log_failure_event(
            self,
            kwargs: dict[str, Any],
            response_obj: object,
            start_time: float | None,
            end_time: float | None,
        ) -> None:
            model = kwargs.get("model", "")
            if not str(model).startswith("openrouter/"):
                return
            if response_obj:
                err = str(response_obj)
            else:
                err = "unknown"
            logger.info(
                "OpenRouter failure model=%s error=%s",
                model,
                err[:200],
            )

    _existing = getattr(litellm, "callbacks", None)
    if _existing is not None:
        _callbacks_list = list(_existing)
    else:
        _callbacks_list = []
    litellm.callbacks = _callbacks_list + [_OpenRouterLogger()]
except ImportError as e:
    logging.getLogger(__name__).info(
        "litellm import failed (modify_params/callbacks unavailable): %s", e
    )

# Monkey-patch: Anthropic requires the conversation to end with a user message.
# CrewAI only fixes the first message; we add the last-message fix (like Mistral/Ollama).
_original_format_messages = LLM._format_messages_for_provider


@log_exceptions("_patched_format_messages")
def _patched_format_messages(self, messages: list[Any]) -> list[dict[str, Any]]:
    result = _original_format_messages(self, messages)
    # Many providers (Anthropic, Mistral, Ollama) require the last message to be user.
    if result and result[-1].get("role") == "assistant":
        return [*result, {"role": "user", "content": "Please continue."}]
    return result


LLM._format_messages_for_provider = _patched_format_messages


class PipelineStage(StrEnum):
    """Pipeline stage names. StrEnum ensures value equals string for backward compatibility."""

    ANALYZE_ISSUE = "analyze_issue"
    EXPLORE = "explore"
    PLAN = "plan"
    IMPLEMENT = "implement"
    REVIEW = "review"
    COMMIT = "commit"
    PUBLISH = "publish"
    AUXILIARY = "auxiliary"
    SECURITY = "security"
    TEST_VALIDATION = "test_validation"


class ProviderType(StrEnum):
    """Provider type for LLM backend. Used to select stage and model source."""

    OPENROUTER = "openrouter"
    HUGGINGFACE = "huggingface"

    @staticmethod
    def default_stage(provider_type: str | None = None) -> PipelineStage:
        """Return default pipeline stage for the given provider type."""
        return PipelineStage.ANALYZE_ISSUE


@dataclass(frozen=True)
class StageModelConfig:
    """Primary model and fallbacks for a pipeline stage."""

    primary: str
    fallbacks: tuple[str, ...]


@dataclass(frozen=True)
class _StageMapping:
    """Per-stage model config: OpenRouter primary + fallbacks + HuggingFace model."""

    openrouter_model: str
    openrouter_fallbacks: tuple[str, ...]
    huggingface_model: str

    def to_stage_config(self) -> StageModelConfig:
        """Return StageModelConfig for OpenRouter (primary + fallbacks)."""
        return StageModelConfig(
            primary=self.openrouter_model,
            fallbacks=self.openrouter_fallbacks,
        )


class ModelMappings(Enum):
    """Unified enum: model IDs (value=str) and stage mappings (value=_StageMapping).
    Single source for OpenRouter models and per-stage config."""

    # Model IDs (value = str)
    DEEPSEEK_R1 = "openrouter/deepseek/deepseek-r1"
    DEEPSEEK_V3_2 = "openrouter/deepseek/deepseek-v3.2"
    GEMINI_3_FLASH = "openrouter/google/gemini-3-flash-preview"
    QWEN3_CODER = "openrouter/qwen/qwen3-coder"
    DEEPSEEK_CHAT = "openrouter/deepseek/deepseek-chat"
    GEMINI_2_FLASH = "openrouter/google/gemini-2.0-flash-001"
    QWEN2_5_CODER = "openrouter/qwen/qwen-2.5-coder-32b-instruct"
    MISTRAL_SMALL = "openrouter/mistralai/mistral-small-24b-instruct-2501"
    LLAMA_3_3_70B = "openrouter/meta-llama/llama-3.3-70b-instruct"
    MAGISTRAL_SMALL = "openrouter/mistralai/magistral-small-latest"
    QWEN3_235B_A22B = "openrouter/qwen/qwen3-235b-a22b-2507"
    DEVSTRAL_SMALL = "openrouter/mistralai/devstral-small"
    GPT_5_NANO = "openrouter/openai/gpt-5-nano"
    KIMI_K25 = "openrouter/moonshotai/kimi-k2.5"
    QWEN3_235B_THINKING = "openrouter/qwen/qwen3-235b-a22b-thinking-2507"
    QWEN3_NEXT_80B = "openrouter/qwen/qwen3-next-80b-a3b-instruct"
    TRINITY_MINI = "openrouter/arcee-ai/trinity-mini"

    # Stage mappings (value = _StageMapping)
    ANALYZE_ISSUE = _StageMapping(
        openrouter_model="openrouter/qwen/qwen3-235b-a22b-2507",
        openrouter_fallbacks=(
            "openrouter/deepseek/deepseek-v3.2",
            "openrouter/mistralai/magistral-small-latest",
        ),
        huggingface_model="deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct",
    )
    EXPLORE = _StageMapping(
        openrouter_model="openrouter/qwen/qwen3-235b-a22b-2507",
        openrouter_fallbacks=(
            "openrouter/deepseek/deepseek-v3.2",
            "openrouter/mistralai/magistral-small-latest",
        ),
        huggingface_model="Qwen/Qwen2.5-Coder-32B-Instruct",
    )
    PLAN = _StageMapping(
        openrouter_model="openrouter/mistralai/devstral-small",
        openrouter_fallbacks=(
            "openrouter/qwen/qwen3-235b-a22b-2507",
            "openrouter/mistralai/magistral-small-latest",
        ),
        huggingface_model="google/gemma-2-2b-it",
    )
    IMPLEMENT = _StageMapping(
        openrouter_model="openrouter/mistralai/devstral-small",
        openrouter_fallbacks=(
            "openrouter/qwen/qwen3-235b-a22b-2507",
            "openrouter/deepseek/deepseek-v3.2",
        ),
        huggingface_model="Qwen/Qwen2.5-Coder-32B-Instruct",
    )
    REVIEW = _StageMapping(
        openrouter_model="openrouter/deepseek/deepseek-v3.2",
        openrouter_fallbacks=(
            "openrouter/qwen/qwen3-235b-a22b-2507",
            "openrouter/mistralai/magistral-small-latest",
        ),
        huggingface_model="deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct",
    )
    COMMIT = _StageMapping(
        openrouter_model="openrouter/mistralai/magistral-small-latest",
        openrouter_fallbacks=(
            "openrouter/mistralai/devstral-small",
            "openrouter/qwen/qwen3-235b-a22b-2507",
        ),
        huggingface_model="mistralai/Mistral-7B-Instruct-v0.3",
    )
    PUBLISH = _StageMapping(
        openrouter_model="openrouter/mistralai/magistral-small-latest",
        openrouter_fallbacks=(
            "openrouter/mistralai/devstral-small",
            "openrouter/qwen/qwen3-235b-a22b-2507",
        ),
        huggingface_model="mistralai/Mistral-7B-Instruct-v0.3",
    )
    AUXILIARY = _StageMapping(
        openrouter_model="openrouter/mistralai/magistral-small-latest",
        openrouter_fallbacks=(
            "openrouter/mistralai/devstral-small",
            "openrouter/qwen/qwen3-235b-a22b-2507",
        ),
        huggingface_model="mistralai/Mistral-7B-Instruct-v0.3",
    )
    SECURITY = _StageMapping(
        openrouter_model="openrouter/deepseek/deepseek-v3.2",
        openrouter_fallbacks=(
            "openrouter/qwen/qwen3-235b-a22b-2507",
            "openrouter/mistralai/magistral-small-latest",
        ),
        huggingface_model="deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct",
    )
    TEST_VALIDATION = _StageMapping(
        openrouter_model="openrouter/mistralai/devstral-small",
        openrouter_fallbacks=(
            "openrouter/deepseek/deepseek-v3.2",
            "openrouter/qwen/qwen3-235b-a22b-2507",
        ),
        huggingface_model="Qwen/Qwen2.5-Coder-32B-Instruct",
    )

    @classmethod
    def normalize_model(cls, model: str) -> str:
        """Prepend openrouter/ if not present. Use when parsing config or external input."""
        if model.startswith("openrouter/"):
            return model
        return f"openrouter/{model}"

    @classmethod
    def all_model_ids(cls) -> set[str]:
        """Return all unique OpenRouter model IDs from model members and stage mappings."""
        ids: set[str] = set()
        for member in cls:
            val = member.value
            if isinstance(val, str):
                ids.add(val)
            elif isinstance(val, _StageMapping):
                ids.add(val.openrouter_model)
                ids.update(val.openrouter_fallbacks)
        return ids

    @classmethod
    def for_stage(cls, stage: PipelineStage) -> _StageMapping:
        """Get stage mapping for pipeline stage. Fallback to ANALYZE_ISSUE."""
        member = getattr(cls, stage.name, cls.ANALYZE_ISSUE)
        val = member.value
        if isinstance(val, _StageMapping):
            return val
        return cls.ANALYZE_ISSUE.value


# Stage config derived from ModelMappings (used when config file has no models section)
DEFAULT_PIPELINE_MODELS: dict[PipelineStage, StageModelConfig] = {
    stage: ModelMappings.for_stage(stage).to_stage_config() for stage in PipelineStage
}


def _load_model_config_from_file(
    config_path: str | Path | None = None,
) -> dict[PipelineStage, StageModelConfig]:
    """Load model configuration from YAML config file, falling back to defaults."""
    if config_path is None:
        config_path = Path(__file__).parent.parent.parent / "config.yaml"

    config_path = Path(config_path)
    if not config_path.exists():
        logger.debug("Config file not found at %s, using default models", config_path)
        return DEFAULT_PIPELINE_MODELS

    try:
        with open(config_path, "r") as f:
            config_data = yaml.safe_load(f)

        models_config = config_data.get("models", {})
        if not models_config:
            logger.debug("No 'models' section found in config, using default models")
            return DEFAULT_PIPELINE_MODELS

        pipeline_models = DEFAULT_PIPELINE_MODELS.copy()

        for stage_name, stage_config in models_config.items():
            try:
                stage_enum = PipelineStage(stage_name)
                primary = stage_config.get("primary", "")
                fallbacks = stage_config.get("fallbacks", [])

                if not primary:
                    logger.warning(
                        "No primary model specified for stage %s, keeping default",
                        stage_name,
                    )
                    continue

                # Match against ModelMappings model IDs or normalize custom string
                primary_model = None
                for member in ModelMappings:
                    if isinstance(member.value, str) and member.value == primary:
                        primary_model = member.value
                        break

                if primary_model is None:
                    primary_model = ModelMappings.normalize_model(primary)
                    logger.info("Using custom model not in enum: %s", primary)

                # Match fallbacks against ModelMappings or normalize custom string
                fallback_models = []
                for fb in fallbacks:
                    fb_model = None
                    for member in ModelMappings:
                        if isinstance(member.value, str) and member.value == fb:
                            fb_model = member.value
                            break
                    if fb_model is None:
                        fb_model = ModelMappings.normalize_model(fb)
                        logger.info("Using custom fallback model not in enum: %s", fb)
                    fallback_models.append(fb_model)

                pipeline_models[stage_enum] = StageModelConfig(
                    primary=primary_model, fallbacks=tuple(fallback_models)
                )
                logger.info(
                    "Loaded model config for stage %s: primary=%s", stage_name, primary
                )

            except ValueError:
                logger.warning("Invalid pipeline stage name in config: %s", stage_name)
                continue

        logger.info("Successfully loaded model configuration from %s", config_path)
        return pipeline_models

    except Exception as e:
        logger.error("Failed to load model config from %s: %s", config_path, e)
        return DEFAULT_PIPELINE_MODELS


# Load models on module import (can be overridden)
PIPELINE_MODELS = _load_model_config_from_file()


# Agent-specific configuration cache
_agent_model_cache: dict[str, StageModelConfig] = {}


def update_model_config(config_data: dict[str, Any] | None = None) -> None:
    """Update the global model configuration with new data."""
    global PIPELINE_MODELS, _agent_model_cache

    if config_data and "models" in config_data:
        # Parse config data
        pipeline_models = DEFAULT_PIPELINE_MODELS.copy()

        for stage_name, stage_config in config_data["models"].items():
            try:
                stage_enum = PipelineStage(stage_name)

                # Parse primary model
                primary = stage_config.get("primary")
                if not primary:
                    logger.warning(
                        "No primary model specified for stage %s", stage_name
                    )
                    continue

                primary_model = None
                for member in ModelMappings:
                    if isinstance(member.value, str) and member.value == primary:
                        primary_model = member.value
                        break
                if primary_model is None:
                    primary_model = ModelMappings.normalize_model(primary)
                    logger.info("Using custom primary model not in enum: %s", primary)

                # Parse fallback models
                fallback_models = []
                for fb in stage_config.get("fallbacks", []):
                    fb_model = None
                    for member in ModelMappings:
                        if isinstance(member.value, str) and member.value == fb:
                            fb_model = member.value
                            break
                    if fb_model is None:
                        fb_model = ModelMappings.normalize_model(fb)
                        logger.info("Using custom fallback model not in enum: %s", fb)
                    fallback_models.append(fb_model)

                pipeline_models[stage_enum] = StageModelConfig(
                    primary=primary_model, fallbacks=tuple(fallback_models)
                )
                logger.info(
                    "Updated model config for stage %s: primary=%s", stage_name, primary
                )

            except ValueError:
                logger.warning("Invalid pipeline stage name in config: %s", stage_name)
                continue

        PIPELINE_MODELS = pipeline_models
        _agent_model_cache.clear()  # Clear agent cache
        logger.info("Model configuration updated successfully")
    elif config_data:
        logger.warning(
            "No 'models' section in config data, keeping existing configuration"
        )


def _get_agent_model_config(stage: PipelineStage, agent_name: str) -> StageModelConfig:
    """Get model configuration for a specific agent, falling back to stage configuration."""
    cache_key = f"{stage.value}:{agent_name}"

    if cache_key in _agent_model_cache:
        return _agent_model_cache[cache_key]

    # Try to load agent-specific config from models.<stage>.agents.<agent_name>
    config_path = Path(__file__).parent.parent.parent / "config.yaml"
    if config_path.exists():
        try:
            with open(config_path, "r") as f:
                config_data = yaml.safe_load(f)

            models_config = config_data.get("models", {})
            stage_config = models_config.get(stage.value, {})

            # Check if there's an agent-specific configuration
            agents_config = stage_config.get("agents", {})
            agent_config = agents_config.get(agent_name, {})

            if agent_config and agent_config.get("primary"):
                primary = agent_config.get("primary", "")
                fallbacks = agent_config.get("fallbacks", [])

                # Match against ModelMappings model IDs or normalize custom string
                primary_model = None
                for member in ModelMappings:
                    if isinstance(member.value, str) and member.value == primary:
                        primary_model = member.value
                        break

                if primary_model is None:
                    primary_model = ModelMappings.normalize_model(primary)
                    logger.info(
                        "Using custom agent model not in enum: %s for %s",
                        primary,
                        agent_name,
                    )

                # Match fallbacks against ModelMappings or normalize custom string
                fallback_models = []
                for fb in fallbacks:
                    fb_model = None
                    for member in ModelMappings:
                        if isinstance(member.value, str) and member.value == fb:
                            fb_model = member.value
                            break
                    if fb_model is None:
                        fb_model = ModelMappings.normalize_model(fb)
                    fallback_models.append(fb_model)

                agent_model_config = StageModelConfig(
                    primary=primary_model, fallbacks=tuple(fallback_models)
                )
                _agent_model_cache[cache_key] = agent_model_config
                logger.info(
                    "Loaded agent-specific config for %s in stage %s",
                    agent_name,
                    stage.value,
                )
                return agent_model_config

        except Exception as e:
            logger.error("Failed to load agent-specific config: %s", e)

    # Fall back to stage configuration from ModelMappings or config
    stage_config = PIPELINE_MODELS.get(
        stage, ModelMappings.for_stage(stage).to_stage_config()
    )
    _agent_model_cache[cache_key] = stage_config
    return stage_config  # type: ignore[return-value]


def llm_with_fallback(
    *models: str,
    context_text: str = "",
    stage_name: str = "",
    estimated_context_tokens: int = 0,
    provider_type: str | None = None,
) -> LLM:
    """Try models in order, return the first that works with smart retry strategy.

    Args:
        *models: Models to try in order
        context_text: Text that will be in the context/prompt (for token estimation)
        stage_name: Pipeline stage name (for stage-specific adjustments)
        estimated_context_tokens: Pre-estimated token count (optional, will estimate if not provided)
        provider_type: Explicit provider type ("openrouter" or "huggingface"). If None, auto-detects.
    """
    # Create provider based on type or auto-detection
    provider = create_provider(provider_type)

    logger.info(
        "┌─[ LLM SELECTION ]─ Trying %d model(s) with %s provider: %s",
        len(models),
        provider.__class__.__name__,
        ", ".join(str(m) for m in models),
    )

    # Conservative default max_tokens
    max_tokens = 2048

    logger.info(
        "│ Using conservative max_tokens: %d",
        max_tokens,
    )

    last_error = None
    for idx, model in enumerate(models):
        model_str = str(model)
        attempt = idx + 1
        total = len(models)

        logger.info("│ Attempt %d/%d: %s", attempt, total, model_str)

        try:
            # Create LLM using provider
            llm = provider.create_llm(
                model=model_str,
                max_tokens=max_tokens,
            )
            logger.info(
                "└─[ LLM SUCCESS ]─ Selected: %s (attempt %d/%d, max_tokens: %d)",
                model_str,
                attempt,
                total,
                max_tokens,
            )
            return llm
        except Exception as e:
            last_error = e
            error_msg = str(e)
            if "429" in error_msg or "RateLimitError" in error_msg:
                logger.info("│ Model %s rate limited, trying next...", model_str)
                if "free" in model_str.lower():
                    logger.info(
                        "│ Free model rate limited, waiting 30s before next attempt..."
                    )
                    import time

                    time.sleep(30)
            elif "None or empty" in error_msg or "Invalid response" in error_msg:
                logger.info(
                    "│ Model %s returned empty response, trying next...", model_str
                )
            else:
                logger.info("│ Model %s failed: %s", model_str, error_msg[:100])
            continue

    if last_error is not None:
        logger.info("└─[ LLM FAILED ]─ All models failed")
        raise Exception("All models failed") from last_error
    raise Exception("All models failed")


def get_llm_for_stage(
    stage: str | PipelineStage,
    agent_name: str | None = None,
    context_text: str = "",
    estimated_context_tokens: int = 0,
    provider_type: str | None = None,
) -> LLM:
    """Return LLM for the given pipeline stage. Uses primary + fallbacks from PIPELINE_MODELS.

    Args:
        stage: Pipeline stage name or enum
        agent_name: Optional agent name for agent-specific configuration
        context_text: Text that will be in the context/prompt (for token estimation)
        estimated_context_tokens: Pre-estimated token count (optional)
        provider_type: Explicit provider type ("openrouter" or "huggingface"). If None, auto-detects.
    """
    if isinstance(stage, str):
        stage_enum = PipelineStage(stage)
    else:
        stage_enum = stage
    logger.debug("get_llm_for_stage: stage=%s, agent=%s", stage_enum, agent_name)

    if agent_name:
        # Use agent-specific configuration if available
        config = _get_agent_model_config(stage_enum, agent_name)
    else:
        # Use stage-level configuration
        config = PIPELINE_MODELS.get(
            stage_enum, ModelMappings.for_stage(stage_enum).to_stage_config()
        )

    # Get models based on provider type
    if provider_type and provider_type.lower() == "huggingface":
        model_mapping = ModelMappings.for_stage(stage_enum)
        models: tuple[str, ...] = (model_mapping.huggingface_model,)
    else:
        # Use OpenRouter models (default)
        models: tuple[str, ...] = (config.primary,) + config.fallbacks

    return llm_with_fallback(
        *models,
        context_text=context_text,
        stage_name=stage_enum.value,
        estimated_context_tokens=estimated_context_tokens,
        provider_type=provider_type,
    )


__all__ = [
    "PipelineStage",
    "ProviderType",
    "StageModelConfig",
    "PIPELINE_MODELS",
    "ModelMappings",
    "get_llm_for_stage",
    "llm_with_fallback",
]
