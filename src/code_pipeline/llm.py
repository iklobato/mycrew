"""Shared LLM configuration for OpenRouter with stage-specific models and fallbacks."""

import logging
import os
from dataclasses import dataclass
from enum import StrEnum

from crewai import LLM

from code_pipeline.utils import log_exceptions

logger = logging.getLogger(__name__)

# LiteLLM: when True, inserts user continue message if last message is assistant
# (fixes Anthropic "assistant message prefill" error when using OpenRouter/Claude)
try:
    import litellm

    litellm.modify_params = True
except ImportError as e:
    logging.getLogger(__name__).error(
        "litellm import failed (modify_params unavailable): %s", e, exc_info=True
    )

# Monkey-patch: Anthropic requires the conversation to end with a user message.
# CrewAI only fixes the first message; we add the last-message fix (like Mistral/Ollama).
_original_format_messages = LLM._format_messages_for_provider


@log_exceptions("_patched_format_messages")
def _patched_format_messages(self, messages):
    result = _original_format_messages(self, messages)
    # Many providers (Anthropic, Mistral, Ollama) require the last message to be user.
    if result and result[-1].get("role") == "assistant":
        return [*result, {"role": "user", "content": "Please continue."}]
    return result


LLM._format_messages_for_provider = _patched_format_messages


class OpenRouterModel(StrEnum):
    """OpenRouter model IDs. Single source of truth for reuse across stages."""

    DEEPSEEK_R1 = "openrouter/deepseek/deepseek-r1"
    DEEPSEEK_V3_2 = "openrouter/deepseek/deepseek-v3.2"
    GEMINI_3_FLASH = "openrouter/google/gemini-3-flash-preview"
    GPT_5_NANO = "openrouter/openai/gpt-5-nano"
    KIMI_K25 = "openrouter/moonshotai/kimi-k2.5"
    QWEN3_235B_THINKING = "openrouter/qwen/qwen3-235b-a22b-thinking-2507"
    QWEN3_CODER = "openrouter/qwen/qwen3-coder:free"
    QWEN3_NEXT_80B = "openrouter/qwen/qwen3-next-80b-a3b-instruct:free"
    TRINITY_MINI = "openrouter/arcee-ai/trinity-mini:free"


class PipelineStage(StrEnum):
    """Pipeline stage names. StrEnum ensures value equals string for backward compatibility."""

    ANALYZE_ISSUE = "analyze_issue"
    EXPLORE = "explore"
    PLAN = "plan"
    IMPLEMENT = "implement"
    REVIEW = "review"
    COMMIT = "commit"


@dataclass(frozen=True)
class StageModelConfig:
    """Primary model and fallbacks for a pipeline stage."""

    primary: OpenRouterModel
    fallbacks: tuple[OpenRouterModel, ...]


# Prefer stable models as primary; preview models (gpt-5-nano, trinity-mini) can return empty
PIPELINE_MODELS: dict[PipelineStage, StageModelConfig] = {
    PipelineStage.ANALYZE_ISSUE: StageModelConfig(
        primary=OpenRouterModel.GEMINI_3_FLASH,
        fallbacks=(
            OpenRouterModel.DEEPSEEK_R1,
            OpenRouterModel.GPT_5_NANO,
            OpenRouterModel.QWEN3_NEXT_80B,
        ),
    ),
    PipelineStage.EXPLORE: StageModelConfig(
        primary=OpenRouterModel.GEMINI_3_FLASH,
        fallbacks=(
            OpenRouterModel.DEEPSEEK_R1,
            OpenRouterModel.GPT_5_NANO,
            OpenRouterModel.KIMI_K25,
            OpenRouterModel.QWEN3_CODER,
        ),
    ),
    PipelineStage.PLAN: StageModelConfig(
        primary=OpenRouterModel.DEEPSEEK_V3_2,
        fallbacks=(
            OpenRouterModel.GEMINI_3_FLASH,
            OpenRouterModel.DEEPSEEK_R1,
            OpenRouterModel.QWEN3_235B_THINKING,
        ),
    ),
    PipelineStage.IMPLEMENT: StageModelConfig(
        primary=OpenRouterModel.DEEPSEEK_V3_2,
        fallbacks=(
            OpenRouterModel.GEMINI_3_FLASH,
            OpenRouterModel.KIMI_K25,
            OpenRouterModel.DEEPSEEK_R1,
            OpenRouterModel.QWEN3_CODER,
        ),
    ),
    PipelineStage.REVIEW: StageModelConfig(
        primary=OpenRouterModel.DEEPSEEK_V3_2,
        fallbacks=(
            OpenRouterModel.GEMINI_3_FLASH,
            OpenRouterModel.DEEPSEEK_R1,
            OpenRouterModel.QWEN3_235B_THINKING,
        ),
    ),
    PipelineStage.COMMIT: StageModelConfig(
        primary=OpenRouterModel.GEMINI_3_FLASH,
        fallbacks=(
            OpenRouterModel.GPT_5_NANO,
            OpenRouterModel.TRINITY_MINI,
            OpenRouterModel.DEEPSEEK_R1,
        ),
    ),
}


def llm_with_fallback(*models: str | OpenRouterModel) -> LLM:
    """Try models in order, return the first that works."""
    api_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if api_key:
        os.environ["OPENROUTER_API_KEY"] = api_key
    last_error = None
    for model in models:
        try:
            model_str = str(model)
            llm = LLM(
                model=model_str,
                num_retries=5,
                time_between_retries=8,
                timeout=120,
                max_tokens=8192,
                stream=False,  # Avoid empty responses from streaming with some OpenRouter models
                # LiteLLM: ensure last message is user (fixes Anthropic assistant prefill error)
                additional_params={
                    "user_continue_message": {
                        "role": "user",
                        "content": "Please continue.",
                    },
                    "ensure_alternating_roles": True,
                },
            )
            logger.info("LLM initialized: %s", model_str)
            return llm
        except Exception as e:
            last_error = e
            logger.error("LLM model %s failed: %s", model_str, e, exc_info=True)
            continue
    if last_error is not None:
        raise Exception("All models failed") from last_error
    raise Exception("All models failed")


def get_llm_for_stage(stage: str | PipelineStage) -> LLM:
    """Return LLM for the given pipeline stage. Uses primary + fallbacks from PIPELINE_MODELS."""
    stage_enum = PipelineStage(stage) if isinstance(stage, str) else stage
    logger.debug("get_llm_for_stage: stage=%s", stage_enum)
    config = PIPELINE_MODELS.get(
        stage_enum, PIPELINE_MODELS[PipelineStage.ANALYZE_ISSUE]
    )
    models: tuple[OpenRouterModel, ...] = (config.primary,) + config.fallbacks
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
