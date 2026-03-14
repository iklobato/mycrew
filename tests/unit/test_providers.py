"""Unit tests for mycrew.providers."""

from unittest.mock import MagicMock, patch

import pytest

from mycrew.providers import (
    IProvider,
    OpenRouterProvider,
    HuggingFaceProvider,
    create_provider,
    ModelMapping,
)


@pytest.fixture(autouse=True)
def clean_settings_singleton():
    """Clear the settings singleton before each test."""
    import mycrew.providers as providers_module

    # Reload settings to clear singleton
    import importlib
    import mycrew.settings as settings_module

    importlib.reload(settings_module)
    providers_module._settings = None
    yield
    # Cleanup after test
    providers_module._settings = None


class TestModelMapping:
    """Tests for ModelMapping dataclass."""

    def test_model_mapping_creation(self):
        """ModelMapping can be created with openrouter and huggingface models."""
        mapping = ModelMapping(
            openrouter_model="openrouter/deepseek/deepseek-chat",
            huggingface_model="deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct",
        )
        assert mapping.openrouter_model == "openrouter/deepseek/deepseek-chat"
        assert (
            mapping.huggingface_model == "deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct"
        )


class TestIProvider:
    """Tests for IProvider abstract interface."""

    def test_interface_methods(self):
        """IProvider has required abstract methods."""
        # Can't instantiate abstract class
        with pytest.raises(TypeError):
            IProvider()

        # Check abstract methods
        assert "generate" in IProvider.__abstractmethods__
        assert "create_llm" in IProvider.__abstractmethods__

    def test_concrete_methods(self):
        """IProvider has concrete helper methods."""

        # Create a concrete implementation for testing
        class TestProvider(IProvider):
            def generate(self, messages, **kwargs):
                return "test"

            def create_llm(self, **kwargs):
                return MagicMock()

        provider = TestProvider()

        # Test convert_messages (default implementation)
        messages = [{"role": "user", "content": "Hello"}]
        result = provider.convert_messages(messages)
        assert result == messages

        # Test handle_error (default implementation)
        with patch("mycrew.providers.logger") as mock_logger:
            error = ValueError("Test error")
            provider.handle_error(error, "test-model")
            mock_logger.error.assert_called_once()


class TestOpenRouterProvider:
    """Tests for OpenRouterProvider."""

    def test_init_requires_api_key(self, monkeypatch):
        """OpenRouterProvider requires OPENROUTER_API_KEY."""
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        monkeypatch.setenv("OPENROUTER_API_KEY", "")

        with patch("mycrew.providers.get_settings") as mock_get_settings:
            from mycrew.settings import Settings

            mock_get_settings.return_value = Settings()
            mock_get_settings.return_value.openrouter_api_key = ""

            with pytest.raises(ValueError, match="OPENROUTER_API_KEY"):
                OpenRouterProvider()

    def test_init_with_api_key(self, monkeypatch):
        """OpenRouterProvider initializes with valid API key."""
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

        provider = OpenRouterProvider()
        assert provider.api_key is not None
        assert provider.base_url == "https://openrouter.ai/api/v1"
        assert provider.session is not None

    def test_create_session(self, monkeypatch):
        """Session is created with retry configuration."""
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

        provider = OpenRouterProvider()
        session = provider._create_session()

        # Check session has adapters mounted
        assert "http://" in session.adapters
        assert "https://" in session.adapters

    @patch("mycrew.providers.requests.Session.post")
    def test_generate_success(self, mock_post, monkeypatch):
        """generate() makes API call and returns response."""
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Test response"}}]
        }
        mock_post.return_value = mock_response

        provider = OpenRouterProvider()
        messages = [{"role": "user", "content": "Hello"}]
        result = provider.generate(messages, model="test-model")

        assert result == "Test response"
        mock_post.assert_called_once()

    @patch("mycrew.providers.requests.Session.post")
    def test_generate_error(self, mock_post, monkeypatch):
        """generate() raises exception on API error."""
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

        mock_post.side_effect = Exception("API error")

        provider = OpenRouterProvider()
        messages = [{"role": "user", "content": "Hello"}]

        with pytest.raises(Exception, match="API error"):
            provider.generate(messages)

    def test_create_llm(self, monkeypatch):
        """create_llm() returns CrewAI LLM instance."""
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

        provider = OpenRouterProvider()
        llm = provider.create_llm(model="test-model", max_tokens=1024)

        assert llm is not None
        assert llm.model == "test-model"
        assert llm.api_key is not None
        assert llm.max_tokens == 1024


class TestHuggingFaceProvider:
    """Tests for HuggingFaceProvider."""

    def test_init_requires_api_key(self, monkeypatch):
        """HuggingFaceProvider requires HUGGINGFACE_API_KEY."""
        monkeypatch.delenv("HUGGINGFACE_API_KEY", raising=False)
        monkeypatch.setenv("HUGGINGFACE_API_KEY", "")

        with pytest.raises(ValueError, match="HUGGINGFACE_API_KEY"):
            HuggingFaceProvider()

    def test_init_with_api_key(self, monkeypatch):
        """HuggingFaceProvider initializes with valid API key."""
        monkeypatch.delenv("HUGGINGFACE_API_KEY", raising=False)
        monkeypatch.setenv("HUGGINGFACE_API_KEY", "test-key")

        provider = HuggingFaceProvider()
        assert provider.api_key == "test-key"
        assert provider.base_url == "https://api-inference.huggingface.co/models"
        assert provider.session is not None

    def test_convert_messages_to_prompt(self, monkeypatch):
        """convert_messages_to_prompt() formats messages correctly."""
        monkeypatch.delenv("HUGGINGFACE_API_KEY", raising=False)
        monkeypatch.setenv("HUGGINGFACE_API_KEY", "test-key")

        provider = HuggingFaceProvider()
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
            {"role": "user", "content": "How are you?"},
        ]

        prompt = provider.convert_messages_to_prompt(messages)

        assert "<|system|>" in prompt
        assert "<|user|>" in prompt
        assert "<|assistant|>" in prompt
        assert "You are a helpful assistant." in prompt
        assert "Hello" in prompt
        assert "Hi there!" in prompt
        assert "How are you?" in prompt

    @patch("mycrew.providers.requests.Session.post")
    def test_generate_success_list_response(self, mock_post, monkeypatch):
        """generate() handles list response format."""
        monkeypatch.delenv("HUGGINGFACE_API_KEY", raising=False)
        monkeypatch.setenv("HUGGINGFACE_API_KEY", "test-key")

        # Mock response (list format)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"generated_text": "Test response from list"}
        ]
        mock_post.return_value = mock_response

        provider = HuggingFaceProvider()
        messages = [{"role": "user", "content": "Hello"}]
        result = provider.generate(messages, model="test-model")

        assert result == "Test response from list"
        mock_post.assert_called_once()

    @patch("mycrew.providers.requests.Session.post")
    def test_generate_success_dict_response(self, mock_post, monkeypatch):
        """generate() handles dict response format."""
        monkeypatch.delenv("HUGGINGFACE_API_KEY", raising=False)
        monkeypatch.setenv("HUGGINGFACE_API_KEY", "test-key")

        # Mock response (dict format)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"generated_text": "Test response from dict"}
        mock_post.return_value = mock_response

        provider = HuggingFaceProvider()
        messages = [{"role": "user", "content": "Hello"}]
        result = provider.generate(messages, model="test-model")

        assert result == "Test response from dict"
        mock_post.assert_called_once()

    @patch("mycrew.providers.requests.Session.post")
    def test_generate_unexpected_format(self, mock_post, monkeypatch):
        """generate() raises ValueError for unexpected response format."""
        monkeypatch.delenv("HUGGINGFACE_API_KEY", raising=False)
        monkeypatch.setenv("HUGGINGFACE_API_KEY", "test-key")

        # Mock unexpected response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"unexpected": "format"}
        mock_post.return_value = mock_response

        provider = HuggingFaceProvider()
        messages = [{"role": "user", "content": "Hello"}]

        with pytest.raises(ValueError, match="Unexpected response format"):
            provider.generate(messages)

    def test_create_llm(self, monkeypatch):
        """create_llm() returns CrewAI LLM instance."""
        monkeypatch.delenv("HUGGINGFACE_API_KEY", raising=False)
        monkeypatch.setenv("HUGGINGFACE_API_KEY", "test-key")

        provider = HuggingFaceProvider()
        llm = provider.create_llm(model="test-model", max_tokens=1024)

        assert llm is not None
        assert llm.model == "test-model"
        assert llm.api_key == "test-key"
        assert llm.max_tokens == 1024


class TestCreateProvider:
    """Tests for create_provider factory function."""

    def test_create_openrouter_explicit(self, monkeypatch):
        """create_provider() creates OpenRouterProvider when specified."""
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

        provider = create_provider("openrouter")
        assert isinstance(provider, OpenRouterProvider)

    def test_create_huggingface_explicit(self, monkeypatch):
        """create_provider() creates HuggingFaceProvider when specified."""
        monkeypatch.delenv("HUGGINGFACE_API_KEY", raising=False)
        monkeypatch.setenv("HUGGINGFACE_API_KEY", "test-key")

        provider = create_provider("huggingface")
        assert isinstance(provider, HuggingFaceProvider)

    def test_create_auto_detect_openrouter(self, monkeypatch):
        """create_provider() auto-detects OpenRouterProvider when OPENROUTER_API_KEY is set."""
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        monkeypatch.delenv("HUGGINGFACE_API_KEY", raising=False)
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

        provider = create_provider()
        assert isinstance(provider, OpenRouterProvider)

    def test_create_auto_detect_huggingface(self, monkeypatch):
        """create_provider() auto-detects HuggingFaceProvider when HUGGINGFACE_API_KEY is set."""
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        monkeypatch.delenv("HUGGINGFACE_API_KEY", raising=False)
        monkeypatch.setenv("HUGGINGFACE_API_KEY", "test-key")

        provider = create_provider()
        assert isinstance(provider, HuggingFaceProvider)

    def test_create_no_api_keys(self, monkeypatch):
        """create_provider() raises ValueError when no API keys are set."""
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        monkeypatch.delenv("HUGGINGFACE_API_KEY", raising=False)
        monkeypatch.setenv("OPENROUTER_API_KEY", "")
        monkeypatch.setenv("HUGGINGFACE_API_KEY", "")

        with pytest.raises(ValueError, match="No provider API key found"):
            create_provider()

    def test_create_unknown_provider(self, monkeypatch):
        """create_provider() raises ValueError for unknown provider type."""
        with pytest.raises(ValueError, match="Unknown provider type"):
            create_provider("unknown")
