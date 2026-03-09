"""Shared utilities for the code pipeline."""

import functools
import logging
from typing import Callable, TypeVar

F = TypeVar("F", bound=Callable[..., object])


def log_exceptions(
    message: str | F | None = None,
) -> Callable[[F], F] | F:
    """Decorator that logs any exception with exc_info=True and re-raises.

    Use as @log_exceptions or @log_exceptions("custom message").
    """

    msg_prefix: str | None = message if isinstance(message, str) else None

    def decorator(fn: F) -> F:
        @functools.wraps(fn)
        def wrapper(*args: object, **kwargs: object) -> object:
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                log = logging.getLogger(fn.__module__)
                msg = msg_prefix or f"{fn.__qualname__} failed"
                log.error("%s: %s", msg, e, exc_info=True)
                raise

        return wrapper  # type: ignore[return-value]

    if message is not None and callable(message) and not isinstance(message, str):
        return decorator(message)  # type: ignore[return-value]
    return decorator  # type: ignore[return-value]
