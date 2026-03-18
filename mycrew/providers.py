"""Abstract provider interface for multiple LLM backends (OpenRouter, HuggingFace)."""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from mycrew.shared.settings import get_settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ModelMapping:
    """Mapping between OpenRouter and HuggingFace models for a pipeline stage."""

    openrouter_model: str
    huggingface_model: str


class IProvider(ABC):
    """Abstract interface for LLM providers."""

    @abstractmethod
    def generate(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        """Generate a response from the LLM.

        Args:
            messages: List of message dicts with 'role' and 'content'
            **kwargs: Additional provider-specific parameters

        Returns:
            Generated text response
        """
        pass

    @abstractmethod
    def create_llm(self, **kwargs: Any) -> Any:
        """Create a CrewAI LLM instance configured for this provider.

        Args:
            **kwargs: Additional configuration parameters

        Returns:
            CrewAI LLM instance
        """
        pass

    def convert_messages(self, messages: list[dict[str, str]]) -> list[dict[str, str]]:
        """Convert messages to provider-specific format.

        Args:
            messages: List of message dicts with 'role' and 'content'

        Returns:
            Converted messages in provider format
        """
        return messages

    def handle_error(self, error: Exception, model: str) -> None:
        """Handle and log errors from provider API calls.

        Args:
            error: Exception that occurred
            model: Model name that failed
        """
        logger.error("Provider error for model %s: %s", model, error, exc_info=True)

    @abstractmethod
    def validate_models(self, required_models: set[str]) -> dict[str, list[str]]:
        """Validate required models are available.

        Args:
            required_models: Set of model IDs to check availability

        Returns:
            Dict with "available" and "unavailable" model lists
        """
        pass


class OpenRouterProvider(IProvider):
    """OpenRouter provider implementation."""

    def __init__(self) -> None:
        self.api_key = get_settings().openrouter_api_key
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable is required")

        self.base_url = "https://openrouter.ai/api/v1"
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """Create HTTP session with retry configuration."""
        session = requests.Session()
        retry = Retry(
            total=4,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["POST"],
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def generate(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        """Generate a response from OpenRouter API."""
        model = kwargs.get("model", "openrouter/deepseek/deepseek-chat")
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/anomalyco/opencode",
        }

        payload = {
            "model": model,
            "messages": self.convert_messages(messages),
            "max_tokens": kwargs.get("max_tokens", 2048),
            "temperature": kwargs.get("temperature", 0.7),
            "stream": False,
        }

        try:
            response = self.session.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=90,
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            self.handle_error(e, model)
            raise

    def create_llm(self, **kwargs: Any) -> Any:
        """Create a CrewAI LLM instance for OpenRouter."""
        from crewai import LLM

        llm_config = {
            "model": kwargs.get("model", "openrouter/deepseek/deepseek-chat"),
            "api_key": self.api_key,
            "base_url": self.base_url,
            "num_retries": 4,
            "time_between_retries": 15,
            "timeout": 90,
            "max_tokens": kwargs.get("max_tokens", 2048),
            "stream": False,
            "additional_params": {
                "transforms": ["middle-out"],
                "user_continue_message": {"role": "user", "content": "Continue."},
                "ensure_alternating_roles": True,
            },
        }
        return LLM(**llm_config)

    def validate_models(self, required_models: set[str]) -> dict[str, list[str]]:
        """Validate required models are available on OpenRouter.

        Args:
            required_models: Set of model IDs to check availability

        Returns:
            Dict with "available" and "unavailable" model lists
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/anomalyco/opencode",
        }

        def normalize_model_id(model_id: str) -> str:
            """Normalize model ID by stripping openrouter/ prefix."""
            prefix = "openrouter/"
            if model_id.startswith(prefix):
                return model_id[len(prefix) :]
            return model_id

        try:
            response = self.session.get(
                f"{self.base_url}/models",
                headers=headers,
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()

            available_model_ids: set[str] = set()
            for model in data.get("data", []):
                model_id = model.get("id", "")
                if model_id:
                    available_model_ids.add(normalize_model_id(model_id))

            required_list = list(required_models)
            normalized_required = {normalize_model_id(m) for m in required_list}

            available = [
                m for m in required_list if normalize_model_id(m) in available_model_ids
            ]
            unavailable = [
                m
                for m in required_list
                if normalize_model_id(m) not in available_model_ids
            ]

            logger.info(
                "Model validation: %d available, %d unavailable out of %d required",
                len(available),
                len(unavailable),
                len(required_models),
            )

            return {"available": available, "unavailable": unavailable}

        except Exception as e:
            logger.error("Failed to validate models: %s", e)
            raise


class HuggingFaceProvider(IProvider):
    """HuggingFace provider implementation."""

    def __init__(self) -> None:
        self.api_key = get_settings().huggingface_api_key
        if not self.api_key:
            raise ValueError("HUGGINGFACE_API_KEY environment variable is required")

        self.base_url = "https://api-inference.huggingface.co/models"
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """Create HTTP session with retry configuration."""
        session = requests.Session()
        retry = Retry(
            total=4,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["POST"],
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def generate(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        """Generate a response from HuggingFace API."""
        model = kwargs.get("model", "meta-llama/Llama-3.3-70B-Instruct")
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # Convert messages to HuggingFace format
        prompt = self.convert_messages_to_prompt(messages)
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": kwargs.get("max_tokens", 2048),
                "temperature": kwargs.get("temperature", 0.7),
                "return_full_text": False,
            },
        }

        try:
            response = self.session.post(
                f"{self.base_url}/{model}",
                headers=headers,
                json=payload,
                timeout=90,
            )
            response.raise_for_status()
            data = response.json()
            if isinstance(data, list) and len(data) > 0:
                return data[0]["generated_text"]
            elif isinstance(data, dict) and "generated_text" in data:
                return data["generated_text"]
            else:
                raise ValueError(f"Unexpected response format: {data}")
        except Exception as e:
            self.handle_error(e, model)
            raise

    def convert_messages_to_prompt(self, messages: list[dict[str, str]]) -> str:
        """Convert messages to HuggingFace prompt format."""
        prompt_parts = []
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            if role == "system":
                prompt_parts.append(f"<|system|>\n{content}</s>")
            elif role == "user":
                prompt_parts.append(f"<|user|>\n{content}</s>")
            elif role == "assistant":
                prompt_parts.append(f"<|assistant|>\n{content}</s>")
        prompt_parts.append("<|assistant|>\n")
        return "\n".join(prompt_parts)

    def create_llm(self, **kwargs: Any) -> Any:
        """Create a CrewAI LLM instance for HuggingFace."""
        from crewai import LLM

        model = kwargs.get("model", "meta-llama/Llama-3.3-70B-Instruct")
        llm_config = {
            "model": model,
            "api_key": self.api_key,
            "base_url": "https://api-inference.huggingface.co/v1",
            "num_retries": 4,
            "time_between_retries": 15,
            "timeout": 90,
            "max_tokens": kwargs.get("max_tokens", 2048),
            "stream": False,
        }
        return LLM(**llm_config)

    def validate_models(self, required_models: set[str]) -> dict[str, list[str]]:
        """Validate required models are available on HuggingFace.

        TODO: Implement HuggingFace model validation.

        Args:
            required_models: Set of model IDs to check availability

        Returns:
            Dict with "available" and "unavailable" model lists
        """
        # TODO: Implement validation for HuggingFace provider
        # For now, assume all models are available
        return {"available": list(required_models), "unavailable": []}


def create_provider(provider_type: str | None = None) -> IProvider:
    """Factory function to create provider based on environment or explicit type.

    Args:
        provider_type: Explicit provider type ("openrouter" or "huggingface").
                       If None, uses HUGGINGFACE_API_KEY presence as fallback.

    Returns:
        IProvider instance
    """
    settings = get_settings()

    if provider_type:
        if provider_type.lower() == "openrouter":
            return OpenRouterProvider()
        elif provider_type.lower() == "huggingface":
            return HuggingFaceProvider()
        else:
            raise ValueError(f"Unknown provider type: {provider_type}")

    # Auto-detect based on available API keys
    if settings.openrouter_api_key:
        return OpenRouterProvider()
    elif settings.huggingface_api_key:
        return HuggingFaceProvider()
    else:
        raise ValueError(
            "No provider API key found. Set OPENROUTER_API_KEY or HUGGINGFACE_API_KEY"
        )
