"""Unit tests for code_pipeline.llm."""

from unittest.mock import MagicMock, patch

import pytest

from code_pipeline.llm import (
    DEFAULT_PIPELINE_MODELS,
    ModelMappings,
    PipelineStage,
    ProviderType,
    _load_model_config_from_file,
    get_llm_for_stage,
    update_model_config,
)


def test_pipeline_stage_valid_values():
    """PipelineStage has expected string values."""
    assert PipelineStage.ANALYZE_ISSUE == "analyze_issue"
    assert PipelineStage.IMPLEMENT == "implement"
    assert PipelineStage.REVIEW == "review"


def test_pipeline_stage_invalid_raises():
    """PipelineStage with invalid name raises ValueError."""
    with pytest.raises(ValueError):
        PipelineStage("invalid_stage")


def test_model_mappings_model_ids_are_strings():
    """ModelMappings model ID members have non-empty string values."""
    for member in ModelMappings:
        if isinstance(member.value, str):
            assert member.value
            assert member.value.startswith("openrouter/")


def test_stage_model_config_primary_and_fallbacks():
    """StageModelConfig has primary and fallbacks."""
    cfg = DEFAULT_PIPELINE_MODELS[PipelineStage.ANALYZE_ISSUE]
    assert cfg.primary is not None
    assert isinstance(cfg.fallbacks, tuple)


def test_load_model_config_missing_file_returns_default():
    """Missing config file returns DEFAULT_PIPELINE_MODELS."""
    result = _load_model_config_from_file("/nonexistent/config.yaml")
    assert result == DEFAULT_PIPELINE_MODELS


def test_load_model_config_valid_yaml_updates_models(tmp_path):
    """Valid YAML with models section updates config."""
    config = tmp_path / "config.yaml"
    config.write_text("""
models:
  analyze_issue:
    primary: openrouter/deepseek/deepseek-chat
    fallbacks: []
  implement:
    primary: openrouter/deepseek/deepseek-chat
    fallbacks: []
""")
    result = _load_model_config_from_file(str(config))
    assert PipelineStage.ANALYZE_ISSUE in result
    assert PipelineStage.IMPLEMENT in result


def test_load_model_config_invalid_stage_skipped(tmp_path):
    """Invalid stage name in YAML is skipped with warning."""
    config = tmp_path / "config.yaml"
    config.write_text("""
models:
  invalid_stage_xyz:
    primary: openrouter/deepseek/deepseek-chat
    fallbacks: []
""")
    result = _load_model_config_from_file(str(config))
    # invalid_stage_xyz is skipped, so we get defaults
    assert PipelineStage.ANALYZE_ISSUE in result


@patch("crewai.LLM")
@patch("code_pipeline.providers.get_settings")
def test_update_model_config_with_models_section(mock_settings, mock_llm_class):
    """update_model_config with models section updates PIPELINE_MODELS."""
    mock_settings.return_value.openrouter_api_key = "key"
    mock_llm_class.return_value = MagicMock()

    update_model_config(
        {
            "models": {
                "analyze_issue": {
                    "primary": "openrouter/deepseek/deepseek-chat",
                    "fallbacks": [],
                },
            },
        }
    )
    result = get_llm_for_stage(PipelineStage.ANALYZE_ISSUE)
    assert result is mock_llm_class.return_value
    mock_llm_class.assert_called_once()


@patch("crewai.LLM")
@patch("code_pipeline.providers.get_settings")
def test_update_model_config_no_models_keeps_existing(mock_settings, mock_llm_class):
    """update_model_config without models section does nothing."""
    mock_settings.return_value.openrouter_api_key = "key"
    mock_llm_class.return_value = MagicMock()

    update_model_config({"pipeline": {"branch": "main"}})
    result = get_llm_for_stage(PipelineStage.ANALYZE_ISSUE)
    assert result is mock_llm_class.return_value
    mock_llm_class.assert_called_once()


@patch("crewai.LLM")
@patch("code_pipeline.providers.get_settings")
def test_get_llm_for_stage_returns_llm(mock_settings, mock_llm_class):
    """get_llm_for_stage returns LLM instance when API key set."""
    mock_settings.return_value.openrouter_api_key = "test-key"
    mock_llm_class.return_value = MagicMock()

    result = get_llm_for_stage(PipelineStage.ANALYZE_ISSUE)

    mock_llm_class.assert_called_once()
    assert result is mock_llm_class.return_value


@patch("crewai.LLM")
@patch("code_pipeline.providers.get_settings")
def test_get_llm_for_stage_with_string(mock_settings, mock_llm_class):
    """get_llm_for_stage accepts string stage name."""
    mock_settings.return_value.openrouter_api_key = "test-key"
    mock_llm_class.return_value = MagicMock()

    result = get_llm_for_stage("explore")

    mock_llm_class.assert_called_once()
    assert result is mock_llm_class.return_value


def test_provider_type_default_stage():
    """ProviderType.default_stage returns ANALYZE_ISSUE."""
    assert ProviderType.default_stage() == PipelineStage.ANALYZE_ISSUE
    assert ProviderType.default_stage("openrouter") == PipelineStage.ANALYZE_ISSUE
    assert ProviderType.default_stage("huggingface") == PipelineStage.ANALYZE_ISSUE


@patch("code_pipeline.providers.get_settings")
def test_llm_with_fallback_no_api_key_raises(mock_settings):
    """llm_with_fallback raises when no provider API key found."""
    from code_pipeline.llm import llm_with_fallback

    mock_settings.return_value.openrouter_api_key = ""
    mock_settings.return_value.huggingface_api_key = ""

    with pytest.raises(ValueError, match="No provider API key found"):
        llm_with_fallback("openrouter/deepseek/deepseek-chat")
