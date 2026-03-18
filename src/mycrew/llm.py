"""Shared LLM configuration for OpenRouter with stage-specific models and fallbacks."""

import logging
import yaml
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from crewai import LLM

from mycrew.exceptions import ModelUnavailableError
from mycrew.providers import create_provider
from mycrew.settings import get_settings

logger = logging.getLogger(__name__)

# LiteLLM: when True, inserts user continue message if last message is assistant
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
                n = len(messages) if messages else 0
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
            err = str(response_obj) if response_obj else "unknown"
            logger.info(
                "OpenRouter failure model=%s error=%s",
                model,
                err[:200],
            )

    _existing = getattr(litellm, "callbacks", None)
    _callbacks_list = list(_existing) if _existing is not None else []
    litellm.callbacks = _callbacks_list + [_OpenRouterLogger()]
except ImportError as e:
    logging.getLogger(__name__).info(
        "litellm import failed (modify_params/callbacks unavailable): %s", e
    )

# Monkey-patch: Anthropic requires the conversation to end with a user message.
_original_format_messages = LLM._format_messages_for_provider


def _patched_format_messages(self, messages: list[Any]) -> list[dict[str, Any]]:
    try:
        result = _original_format_messages(self, messages)
        if result and result[-1].get("role") == "assistant":
            return [*result, {"role": "user", "content": "Please continue."}]
        return result
    except Exception:
        raise


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
    """Provider type for LLM backend."""

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


from enum import Enum


class ModelMappings(Enum):
    """Unified enum: model IDs and stage mappings. Single source for OpenRouter models and per-stage config."""

    DEEPSEEK_R1 = "openrouter/deepseek/deepseek-r1"
    DEEPSEEK_V3_2 = "openrouter/deepseek/deepseek-v3.2"
    GEMINI_3_FLASH = "openrouter/google/gemini-3-flash-preview"
    QWEN3_CODER = "openrouter/qwen/qwen3-coder"
    DEEPSEEK_CHAT = "openrouter/deepseek/deepseek-chat"
    GEMINI_2_FLASH = "openrouter/google/gemini-2.0-flash-001"
    QWEN2_5_CODER = "openrouter/qwen/qwen-2.5-coder-32b-instruct"
    MISTRAL_SMALL = "openrouter/mistralai/mistral-small-24b-instruct-2501"
    MISTRAL_SMALL_3_1 = "openrouter/mistralai/mistral-small-3.1-24b-instruct"
    LLAMA_3_3_70B = "openrouter/meta-llama/llama-3.3-70b-instruct"
    MAGISTRAL_SMALL = "openrouter/mistralai/magistral-small-latest"
    QWEN3_235B_A22B = "openrouter/qwen/qwen3-235b-a22b-2507"
    DEVSTRAL_SMALL = "openrouter/mistralai/devstral-small"
    GPT_5_NANO = "openrouter/openai/gpt-5-nano"
    KIMI_K25 = "openrouter/moonshotai/kimi-k2.5"
    QWEN3_235B_THINKING = "openrouter/qwen/qwen3-235b-a22b-thinking-2507"
    QWEN3_NEXT_80B = "openrouter/qwen/qwen3-next-80b-a3b-instruct"
    TRINITY_MINI = "openrouter/arcee-ai/trinity-mini"
    GEMMA_3_27B = "openrouter/google/gemma-3-27b-it"

    ANALYZE_ISSUE = _StageMapping(
        openrouter_model="openrouter/google/gemini-2.0-flash-001",
        openrouter_fallbacks=(
            "openrouter/deepseek/deepseek-r1",
            "openrouter/qwen/qwen3-coder",
        ),
        huggingface_model="deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct",
    )
    EXPLORE = _StageMapping(
        openrouter_model="openrouter/x-ai/grok-4.1-fast",
        openrouter_fallbacks=(
            "openrouter/google/gemini-2.0-flash-001",
            "openrouter/deepseek/deepseek-r1",
        ),
        huggingface_model="deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct",
    )
    PLAN = _StageMapping(
        openrouter_model="openrouter/google/gemini-2.0-flash-001",
        openrouter_fallbacks=(
            "openrouter/deepseek/deepseek-r1",
            "openrouter/qwen/qwen3-coder",
        ),
        huggingface_model="google/gemma-2-2b-it",
    )
    IMPLEMENT = _StageMapping(
        openrouter_model="openrouter/google/gemini-2.0-flash-001",
        openrouter_fallbacks=(
            "openrouter/qwen/qwen3-coder",
            "openrouter/deepseek/deepseek-r1",
        ),
        huggingface_model="Qwen/Qwen2.5-Coder-32B-Instruct",
    )
    REVIEW = _StageMapping(
        openrouter_model="openrouter/google/gemini-2.0-flash-001",
        openrouter_fallbacks=(
            "openrouter/deepseek/deepseek-r1",
            "openrouter/qwen/qwen3-coder",
        ),
        huggingface_model="deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct",
    )
    COMMIT = _StageMapping(
        openrouter_model="openrouter/google/gemini-2.0-flash-001",
        openrouter_fallbacks=(
            "openrouter/deepseek/deepseek-r1",
            "openrouter/qwen/qwen3-coder",
        ),
        huggingface_model="mistralai/Mistral-7B-Instruct-v0.3",
    )
    PUBLISH = _StageMapping(
        openrouter_model="openrouter/google/gemini-2.0-flash-001",
        openrouter_fallbacks=(
            "openrouter/deepseek/deepseek-r1",
            "openrouter/qwen/qwen3-coder",
        ),
        huggingface_model="mistralai/Mistral-7B-Instruct-v0.3",
    )
    AUXILIARY = _StageMapping(
        openrouter_model="openrouter/google/gemini-2.0-flash-001",
        openrouter_fallbacks=(
            "openrouter/deepseek/deepseek-r1",
            "openrouter/qwen/qwen3-coder",
        ),
        huggingface_model="deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct",
    )
    SECURITY = _StageMapping(
        openrouter_model="openrouter/google/gemini-2.0-flash-001",
        openrouter_fallbacks=(
            "openrouter/deepseek/deepseek-r1",
            "openrouter/qwen/qwen3-coder",
        ),
        huggingface_model="deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct",
    )
    TEST_VALIDATION = _StageMapping(
        openrouter_model="openrouter/google/gemini-2.0-flash-001",
        openrouter_fallbacks=(
            "openrouter/deepseek/deepseek-r1",
            "openrouter/qwen/qwen3-coder",
        ),
        huggingface_model="Qwen/Qwen2.5-Coder-32B-Instruct",
    )

    @classmethod
    def normalize_model(cls, model: str) -> str:
        """Prepend openrouter/ if not present."""
        if model.startswith("openrouter/"):
            return model
        return f"openrouter/{model}"

    @classmethod
    def all_model_ids(cls) -> set[str]:
        """Return all unique OpenRouter model IDs."""
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
        """Get stage mapping for pipeline stage."""
        member = getattr(cls, stage.name, cls.ANALYZE_ISSUE)
        val = member.value
        if isinstance(val, _StageMapping):
            return val
        return cls.ANALYZE_ISSUE.value


DEFAULT_PIPELINE_MODELS: dict[PipelineStage, StageModelConfig] = {
    stage: ModelMappings.for_stage(stage).to_stage_config() for stage in PipelineStage
}


class LLMConfigLoader:
    """Loads LLM configuration from YAML file."""

    @staticmethod
    def load(
        config_path: str | Path | None = None,
    ) -> dict[PipelineStage, StageModelConfig]:
        """Load model configuration from YAML config file, falling back to defaults."""
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / "defaults.yaml"

        config_path = Path(config_path)
        if not config_path.exists():
            logger.info(
                "Config file not found at %s, using default models", config_path
            )
            return DEFAULT_PIPELINE_MODELS

        try:
            with open(config_path, "r") as f:
                config_data = yaml.safe_load(f)

            models_config = config_data.get("models", {})
            if not models_config:
                logger.info("No 'models' section found in config, using default models")
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

                    primary_model = None
                    for member in ModelMappings:
                        if isinstance(member.value, str) and member.value == primary:
                            primary_model = member.value
                            break

                    if primary_model is None:
                        primary_model = ModelMappings.normalize_model(primary)
                        logger.info("Using custom model not in enum: %s", primary_model)

                    fallback_models = []
                    for fb in fallbacks:
                        fb_model = None
                        for member in ModelMappings:
                            if isinstance(member.value, str) and member.value == fb:
                                fb_model = member.value
                                break
                        if fb_model is None:
                            fb_model = ModelMappings.normalize_model(fb)
                            logger.info(
                                "Using custom fallback model not in enum: %s", fb
                            )
                        fallback_models.append(fb_model)

                    pipeline_models[stage_enum] = StageModelConfig(
                        primary=primary_model, fallbacks=tuple(fallback_models)
                    )
                    logger.info(
                        "Loaded model config for stage %s: primary=%s",
                        stage_name,
                        primary,
                    )

                except ValueError:
                    logger.warning(
                        "Invalid pipeline stage name in config: %s", stage_name
                    )
                    continue

            logger.info("Successfully loaded model configuration from %s", config_path)
            return pipeline_models

        except Exception as e:
            logger.error("Failed to load model config from %s: %s", config_path, e)
            return DEFAULT_PIPELINE_MODELS


class LLMConfigManager:
    """Manages LLM configuration cache for agents."""

    _cache: dict[str, StageModelConfig] = {}

    @classmethod
    def get_agent_config(
        cls, stage: PipelineStage, agent_name: str
    ) -> StageModelConfig:
        """Get model configuration for a specific agent, falling back to stage configuration."""
        cache_key = f"{stage.value}:{agent_name}"

        if cache_key in cls._cache:
            return cls._cache[cache_key]

        stage_config = PIPELINE_MODELS.get(stage)
        if stage_config:
            cls._cache[cache_key] = stage_config
            return stage_config

        return PIPELINE_MODELS.get(
            PipelineStage.AUXILIARY,
            StageModelConfig(
                primary="openrouter/mistralai/mistral-small-24b-instruct-2501",
                fallbacks=(),
            ),
        )

    @classmethod
    def extract_all_models(cls) -> set[str]:
        """Extract all required model IDs from PIPELINE_MODELS."""
        models: set[str] = set()
        for stage_config in PIPELINE_MODELS.values():
            models.add(stage_config.primary)
            models.update(stage_config.fallbacks)
        return models


class LLMManager:
    """Manages LLM creation with fallback support."""

    @classmethod
    def create_with_fallback(
        cls,
        *models: str,
        context_text: str = "",
        stage_name: str = "",
        estimated_context_tokens: int = 0,
        provider_type: str | None = None,
    ) -> LLM:
        """Try models in order, return the first that works."""
        provider = create_provider(provider_type)

        logger.info(
            "┌─[ LLM SELECTION ]─ Trying %d model(s) with %s provider: %s",
            len(models),
            provider.__class__.__name__,
            ", ".join(str(m) for m in models),
        )

        max_tokens = 2048

        logger.info("│ Using conservative max_tokens: %d", max_tokens)

        last_error = None
        for idx, model in enumerate(models):
            model_str = str(model)
            attempt = idx + 1
            total = len(models)

            logger.info(f"LLM request: {model_str}")

            try:
                llm = provider.create_llm(model=model_str, max_tokens=max_tokens)
                return llm
            except Exception as e:
                last_error = e
                error_msg = str(e)
                if "429" in error_msg or "RateLimitError" in error_msg:
                    logger.warning(f"Rate limited")
                    if "free" in model_str.lower():
                        import time

                        time.sleep(30)
                elif "None or empty" in error_msg or "Invalid response" in error_msg:
                    pass
                else:
                    logger.error(f"LLM failed: {error_msg[:100]}")
                continue

        if last_error is not None:
            logger.error(f"LLM failed: {last_error}")
            raise Exception("All models failed") from last_error
        raise Exception("All models failed")

    @classmethod
    def get_for_stage(
        cls,
        stage: str | PipelineStage,
        agent_name: str | None = None,
        context_text: str = "",
        estimated_context_tokens: int = 0,
        provider_type: str | None = None,
        custom_model: str | None = None,
    ) -> LLM:
        """Return LLM for the given pipeline stage."""
        # If custom_model is provided, use it directly
        if custom_model:
            provider = create_provider(provider_type)
            return provider.create_llm(model=custom_model, max_tokens=2048)

        if isinstance(stage, str):
            stage_enum = PipelineStage(stage)
        else:
            stage_enum = stage
        logger.debug("get_llm_for_stage: stage=%s, agent=%s", stage_enum, agent_name)

        if agent_name:
            config = LLMConfigManager.get_agent_config(stage_enum, agent_name)
        else:
            config = PIPELINE_MODELS.get(
                stage_enum, ModelMappings.for_stage(stage_enum).to_stage_config()
            )

        if provider_type and provider_type.lower() == "huggingface":
            model_mapping = ModelMappings.for_stage(stage_enum)
            models: tuple[str, ...] = (model_mapping.huggingface_model,)
        else:
            models = (config.primary,) + config.fallbacks

        return cls.create_with_fallback(
            *models,
            context_text=context_text,
            stage_name=stage_enum.value,
            estimated_context_tokens=estimated_context_tokens,
            provider_type=provider_type,
        )


class LLMValidator:
    """Validates LLM configuration."""

    @classmethod
    def validate(cls) -> None:
        """Validate all required models are available for the configured provider."""
        settings = get_settings()

        if not settings.openrouter_api_key:
            logger.info("No OpenRouter API key, skipping model validation")
            return

        provider_type = settings.provider_type
        if provider_type and provider_type.lower() == "huggingface":
            logger.info("Skipping OpenRouter model validation for HuggingFace provider")
            return

        required_models = LLMConfigManager.extract_all_models()
        logger.info(
            "Validating %d required models against OpenRouter",
            len(required_models),
        )

        provider = create_provider(provider_type="openrouter")
        result = provider.validate_models(required_models)

        if result["unavailable"]:
            raise ModelUnavailableError(result["unavailable"])

        logger.info("All %d required models are available", len(result["available"]))


# Load models on module import
PIPELINE_MODELS = LLMConfigLoader.load()


def _load_model_config_from_file(
    config_path: str | Path | None = None,
) -> dict[PipelineStage, StageModelConfig]:
    """Load model configuration from YAML config file."""
    return LLMConfigLoader.load(config_path)


def _get_agent_model_config(stage: PipelineStage, agent_name: str) -> StageModelConfig:
    """Get model configuration for a specific agent."""
    return LLMConfigManager.get_agent_config(stage, agent_name)


def llm_with_fallback(
    *models: str,
    context_text: str = "",
    stage_name: str = "",
    estimated_context_tokens: int = 0,
    provider_type: str | None = None,
) -> LLM:
    """Try models in order, return the first that works."""
    return LLMManager.create_with_fallback(
        *models,
        context_text=context_text,
        stage_name=stage_name,
        estimated_context_tokens=estimated_context_tokens,
        provider_type=provider_type,
    )


def get_llm_for_stage(
    stage: str | PipelineStage,
    agent_name: str | None = None,
    context_text: str = "",
    estimated_context_tokens: int = 0,
    provider_type: str | None = None,
    custom_model: str | None = None,
) -> LLM:
    """Return LLM for the given pipeline stage."""
    return LLMManager.get_for_stage(
        stage,
        agent_name=agent_name,
        context_text=context_text,
        estimated_context_tokens=estimated_context_tokens,
        provider_type=provider_type,
        custom_model=custom_model,
    )


def _extract_all_required_models() -> set[str]:
    """Extract all required model IDs from PIPELINE_MODELS."""
    return LLMConfigManager.extract_all_models()


def validate_required_models() -> None:
    """Validate all required models are available."""
    LLMValidator.validate()


__all__ = [
    "PipelineStage",
    "ProviderType",
    "StageModelConfig",
    "PIPELINE_MODELS",
    "ModelMappings",
    "get_llm_for_stage",
    "llm_with_fallback",
    "validate_required_models",
]
