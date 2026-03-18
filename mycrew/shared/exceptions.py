"""Application exceptions."""


class AppError(Exception):
    """Base exception for all application errors."""

    pass


class ModelUnavailableError(AppError):
    """Raised when required models are not available on the provider."""

    def __init__(
        self, unavailable_models: list[str], provider: str = "OpenRouter"
    ) -> None:
        self.unavailable_models = unavailable_models
        self.provider = provider
        model_list = ", ".join(unavailable_models)
        super().__init__(
            f"The following models are not available on {provider}: {model_list}"
        )
