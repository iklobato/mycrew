"""Shared LLM configuration for OpenRouter with stage-specific models and fallbacks."""

import logging
import os
import yaml
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from crewai import LLM

from code_pipeline.settings import get_settings
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


class OpenRouterModel(StrEnum):
    """OpenRouter model IDs. Single source of truth for reuse across stages."""

    # Expensive models (keep for fallback)
    DEEPSEEK_R1 = "openrouter/deepseek/deepseek-r1"
    DEEPSEEK_V3_2 = "openrouter/deepseek/deepseek-v3.2"
    GEMINI_3_FLASH = "openrouter/google/gemini-3-flash-preview"
    QWEN3_CODER = "openrouter/qwen/qwen3-coder"

    # Cheaper alternatives (primary recommendations)
    DEEPSEEK_CHAT = "openrouter/deepseek/deepseek-chat"  # ~70% cheaper than v3.2
    GEMINI_2_FLASH = "openrouter/google/gemini-2.0-flash-001"  # Cheaper than gemini-3
    QWEN2_5_CODER = (
        "openrouter/qwen/qwen-2.5-coder-32b-instruct"  # ~60% cheaper than qwen3-coder
    )
    MISTRAL_SMALL = "openrouter/mistralai/mistral-small-24b-instruct-2501"  # Available mistral small model
    LLAMA_3_3_70B = (
        "openrouter/meta-llama/llama-3.3-70b-instruct"  # Good for complex tasks
    )

    # Legacy/fallback options
    GPT_5_NANO = "openrouter/openai/gpt-5-nano"
    KIMI_K25 = "openrouter/moonshotai/kimi-k2.5"
    QWEN3_235B_THINKING = "openrouter/qwen/qwen3-235b-a22b-thinking-2507"
    QWEN3_NEXT_80B = "openrouter/qwen/qwen3-next-80b-a3b-instruct"
    TRINITY_MINI = "openrouter/arcee-ai/trinity-mini"


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


@dataclass(frozen=True)
class StageModelConfig:
    """Primary model and fallbacks for a pipeline stage."""

    primary: OpenRouterModel
    fallbacks: tuple[OpenRouterModel, ...]


# Default model configuration - optimized for MAXIMUM cost-effectiveness using cheapest non-free models
# Using only 4 cheapest models: DeepSeek Chat, Qwen2.5 Coder, Gemini 2.0 Flash, Mistral Small
DEFAULT_PIPELINE_MODELS: dict[PipelineStage, StageModelConfig] = {
    # Issue Analysis: Needs reasoning + GitHub issue understanding
    # DeepSeek Chat is the cheapest good reasoning model
    PipelineStage.ANALYZE_ISSUE: StageModelConfig(
        primary=OpenRouterModel.DEEPSEEK_CHAT,
        fallbacks=(
            OpenRouterModel.QWEN2_5_CODER,  # Cheaper coding alternative
            OpenRouterModel.MISTRAL_SMALL,  # Cheapest general alternative
        ),
    ),
    # Exploration: Needs code understanding + tech stack analysis
    # Qwen2.5 Coder is the cheapest specialized coding model
    PipelineStage.EXPLORE: StageModelConfig(
        primary=OpenRouterModel.QWEN2_5_CODER,
        fallbacks=(
            OpenRouterModel.DEEPSEEK_CHAT,  # Cheaper reasoning alternative
            OpenRouterModel.MISTRAL_SMALL,  # Cheapest general alternative
        ),
    ),
    # Planning: Needs design thinking + architecture planning
    # Gemini 2.0 Flash is the cheapest fast brainstorming model
    PipelineStage.PLAN: StageModelConfig(
        primary=OpenRouterModel.GEMINI_2_FLASH,
        fallbacks=(
            OpenRouterModel.MISTRAL_SMALL,  # Cheapest alternative
            OpenRouterModel.DEEPSEEK_CHAT,  # Cheaper reasoning alternative
        ),
    ),
    # Implementation: Needs coding excellence + precision
    # Qwen2.5 Coder is the cheapest specialized coding model
    PipelineStage.IMPLEMENT: StageModelConfig(
        primary=OpenRouterModel.QWEN2_5_CODER,
        fallbacks=(
            OpenRouterModel.DEEPSEEK_CHAT,  # Cheaper reasoning alternative
            OpenRouterModel.MISTRAL_SMALL,  # Cheapest general alternative
        ),
    ),
    # Review: Needs critical thinking + code review skills
    # DeepSeek Chat is the cheapest good reasoning model
    PipelineStage.REVIEW: StageModelConfig(
        primary=OpenRouterModel.DEEPSEEK_CHAT,
        fallbacks=(
            OpenRouterModel.QWEN2_5_CODER,  # Cheaper coding alternative for code-specific reviews
            OpenRouterModel.MISTRAL_SMALL,  # Cheapest general alternative
        ),
    ),
    # Commit: Needs concise, clear writing for commit messages
    # Gemini 2.0 Flash is the cheapest fast text generation model
    PipelineStage.COMMIT: StageModelConfig(
        primary=OpenRouterModel.GEMINI_2_FLASH,
        fallbacks=(
            OpenRouterModel.MISTRAL_SMALL,  # Cheapest alternative
            OpenRouterModel.DEEPSEEK_CHAT,  # Cheaper reasoning alternative
        ),
    ),
    # Publish: Needs PR description writing + communication
    # Gemini 2.0 Flash is the cheapest fast text generation model
    PipelineStage.PUBLISH: StageModelConfig(
        primary=OpenRouterModel.GEMINI_2_FLASH,
        fallbacks=(
            OpenRouterModel.MISTRAL_SMALL,  # Cheapest alternative
            OpenRouterModel.DEEPSEEK_CHAT,  # Cheaper reasoning alternative
        ),
    ),
    # Auxiliary: General-purpose tasks, needs to be cheapest possible
    # Mistral Small is the cheapest general-purpose model
    PipelineStage.AUXILIARY: StageModelConfig(
        primary=OpenRouterModel.MISTRAL_SMALL,
        fallbacks=(
            OpenRouterModel.GEMINI_2_FLASH,  # Cheapest fast alternative
            OpenRouterModel.DEEPSEEK_CHAT,  # Cheaper reasoning alternative
        ),
    ),
    # Security: Needs security reasoning + vulnerability analysis
    # DeepSeek Chat is cheapest good reasoning model (security doesn't need expensive Llama)
    PipelineStage.SECURITY: StageModelConfig(
        primary=OpenRouterModel.DEEPSEEK_CHAT,
        fallbacks=(
            OpenRouterModel.QWEN2_5_CODER,  # Cheaper coding alternative for code security
            OpenRouterModel.MISTRAL_SMALL,  # Cheapest general alternative
        ),
    ),
    # Test Validation: Needs test writing and validation
    # Qwen2.5 Coder is cheapest specialized coding model for test writing
    PipelineStage.TEST_VALIDATION: StageModelConfig(
        primary=OpenRouterModel.QWEN2_5_CODER,
        fallbacks=(
            OpenRouterModel.DEEPSEEK_CHAT,  # Cheaper reasoning alternative
            OpenRouterModel.MISTRAL_SMALL,  # Cheapest general alternative
        ),
    ),
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

                # Convert string to OpenRouterModel enum if it exists
                primary_model = None
                for model in OpenRouterModel:
                    if model.value == primary:
                        primary_model = model
                        break

                if primary_model is None:
                    # If not in enum, use as string
                    primary_model = primary
                    logger.info("Using custom model not in enum: %s", primary)

                # Convert fallbacks to OpenRouterModel enums or strings
                fallback_models = []
                for fb in fallbacks:
                    fb_model = None
                    for model in OpenRouterModel:
                        if model.value == fb:
                            fb_model = model
                            break
                    if fb_model is None:
                        fb_model = fb
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
                for model in OpenRouterModel:
                    if model.value == primary:
                        primary_model = model
                        break
                if primary_model is None:
                    primary_model = primary
                    logger.info("Using custom primary model not in enum: %s", primary)

                # Parse fallback models
                fallback_models = []
                for fb in stage_config.get("fallbacks", []):
                    fb_model = None
                    for model in OpenRouterModel:
                        if model.value == fb:
                            fb_model = model
                            break
                    if fb_model is None:
                        fb_model = fb
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

    # Try to load agent-specific config from current PIPELINE_MODELS
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

                # Convert string to OpenRouterModel enum if it exists
                primary_model = None
                for model in OpenRouterModel:
                    if model.value == primary:
                        primary_model = model
                        break

                if primary_model is None:
                    primary_model = primary
                    logger.info(
                        "Using custom agent model not in enum: %s for %s",
                        primary,
                        agent_name,
                    )

                # Convert fallbacks to OpenRouterModel enums or strings
                fallback_models = []
                for fb in fallbacks:
                    fb_model = None
                    for model in OpenRouterModel:
                        if model.value == fb:
                            fb_model = model
                            break
                    if fb_model is None:
                        fb_model = fb
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

    # Fall back to stage configuration
    stage_config = PIPELINE_MODELS.get(
        stage, DEFAULT_PIPELINE_MODELS[PipelineStage.ANALYZE_ISSUE]
    )
    _agent_model_cache[cache_key] = stage_config
    return stage_config  # type: ignore[return-value]


def llm_with_fallback(*models: str | OpenRouterModel) -> LLM:
    """Try models in order, return the first that works with smart retry strategy."""
    api_key = get_settings().openrouter_api_key
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY environment variable is required")

    os.environ["OPENROUTER_API_KEY"] = api_key

    logger.info(
        "┌─[ LLM SELECTION ]─ Trying %d model(s): %s",
        len(models),
        ", ".join(str(m) for m in models),
    )

    last_error = None
    for idx, model in enumerate(models):
        model_str = str(model)
        attempt = idx + 1
        total = len(models)

        logger.info("│ Attempt %d/%d: %s", attempt, total, model_str)

        try:
            # Configure retry strategy based on model type
            retry_config = _get_retry_config_for_model(model_str)

            # Configure LLM for OpenRouter
            llm_config = {
                "model": model_str,
                "num_retries": retry_config["num_retries"],
                "time_between_retries": retry_config["time_between_retries"],
                "timeout": 120,
                "max_tokens": 8192,
                "stream": False,  # Avoid empty responses from streaming with some OpenRouter models
                # LiteLLM: ensure last message is user (fixes Anthropic assistant prefill error)
                "additional_params": {
                    "user_continue_message": {
                        "role": "user",
                        "content": "Please continue.",
                    },
                    "ensure_alternating_roles": True,
                },
            }

            # Add API key and base URL if available
            if api_key:
                llm_config["api_key"] = api_key
                # OpenRouter requires specific base URL
                llm_config["base_url"] = "https://openrouter.ai/api/v1"

            llm = LLM(**llm_config)
            logger.info(
                "└─[ LLM SUCCESS ]─ Selected: %s (attempt %d/%d)",
                model_str,
                attempt,
                total,
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


def _get_retry_config_for_model(model_str: str) -> dict[str, int]:
    """Get retry configuration optimized for specific model types."""
    model_lower = model_str.lower()

    # Free models have stricter rate limits - need more conservative retry strategy
    if "free" in model_lower:
        return {
            "num_retries": 3,  # Fewer retries for free models
            "time_between_retries": 30,  # Longer wait between retries (30 seconds)
        }
    # Paid models can have more aggressive retry
    elif any(
        paid_model in model_lower for paid_model in ["gpt-", "claude-", "gemini-"]
    ):
        return {
            "num_retries": 5,
            "time_between_retries": 10,  # 10 seconds for paid models
        }
    # Default for other models
    else:
        return {
            "num_retries": 4,
            "time_between_retries": 15,  # 15 seconds default
        }


def get_llm_for_stage(stage: str | PipelineStage, agent_name: str | None = None) -> LLM:
    """Return LLM for the given pipeline stage. Uses primary + fallbacks from PIPELINE_MODELS."""
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
            stage_enum, DEFAULT_PIPELINE_MODELS[PipelineStage.ANALYZE_ISSUE]
        )

    models: tuple[str | OpenRouterModel, ...] = (config.primary,) + config.fallbacks
    return llm_with_fallback(*models)


def get_llm() -> LLM:
    """Return default LLM (analyze_issue model). Prefer get_llm_for_stage for stage-specific models."""
    return get_llm_for_stage(PipelineStage.ANALYZE_ISSUE)


__all__ = [
    "OpenRouterModel",
    "PipelineStage",
    "StageModelConfig",
    "PIPELINE_MODELS",
    "get_llm",
    "get_llm_for_stage",
    "llm_with_fallback",
]
