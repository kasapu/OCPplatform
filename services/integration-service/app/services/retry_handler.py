"""
Retry Handler with Exponential Backoff

Automatically retries failed requests with increasing delays
"""

import asyncio
import logging
from typing import Callable, Any, Optional, List
from functools import wraps

from app.core.config import settings

logger = logging.getLogger(__name__)


class RetryHandler:
    """
    Retry handler with exponential backoff

    Usage:
        retry_handler = RetryHandler(max_attempts=3)
        result = await retry_handler.execute(async_function, *args, **kwargs)
    """

    def __init__(
        self,
        max_attempts: int = settings.RETRY_MAX_ATTEMPTS,
        initial_delay: float = settings.RETRY_INITIAL_DELAY,
        max_delay: float = settings.RETRY_MAX_DELAY,
        exponential_base: float = settings.RETRY_EXPONENTIAL_BASE,
        retryable_exceptions: Optional[List[type]] = None
    ):
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.retryable_exceptions = retryable_exceptions or [Exception]

    async def execute(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute function with retry logic

        Args:
            func: Async function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Result from func

        Raises:
            Exception: Last exception if all retries fail
        """
        last_exception = None
        attempt = 0

        while attempt < self.max_attempts:
            attempt += 1

            try:
                result = await func(*args, **kwargs)
                if attempt > 1:
                    logger.info(f"✓ Retry successful on attempt {attempt}/{self.max_attempts}")
                return result

            except tuple(self.retryable_exceptions) as e:
                last_exception = e

                if attempt >= self.max_attempts:
                    logger.error(
                        f"✗ All {self.max_attempts} retry attempts failed. "
                        f"Last error: {str(e)}"
                    )
                    break

                # Calculate delay with exponential backoff
                delay = min(
                    self.initial_delay * (self.exponential_base ** (attempt - 1)),
                    self.max_delay
                )

                logger.warning(
                    f"⚠ Attempt {attempt}/{self.max_attempts} failed: {str(e)}. "
                    f"Retrying in {delay:.2f}s..."
                )

                await asyncio.sleep(delay)

        # All retries failed, raise last exception
        raise last_exception


def with_retry(
    max_attempts: int = settings.RETRY_MAX_ATTEMPTS,
    initial_delay: float = settings.RETRY_INITIAL_DELAY,
    max_delay: float = settings.RETRY_MAX_DELAY,
    exponential_base: float = settings.RETRY_EXPONENTIAL_BASE,
    retryable_exceptions: Optional[List[type]] = None
):
    """
    Decorator to add retry logic to async functions

    Usage:
        @with_retry(max_attempts=3, initial_delay=1.0)
        async def make_api_call():
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            retry_handler = RetryHandler(
                max_attempts=max_attempts,
                initial_delay=initial_delay,
                max_delay=max_delay,
                exponential_base=exponential_base,
                retryable_exceptions=retryable_exceptions
            )
            return await retry_handler.execute(func, *args, **kwargs)
        return wrapper
    return decorator


# Predefined retry strategies

def with_aggressive_retry():
    """Retry quickly with many attempts (good for transient errors)"""
    return with_retry(
        max_attempts=5,
        initial_delay=0.5,
        max_delay=10.0,
        exponential_base=1.5
    )


def with_conservative_retry():
    """Retry slowly with fewer attempts (good for rate-limited APIs)"""
    return with_retry(
        max_attempts=2,
        initial_delay=5.0,
        max_delay=60.0,
        exponential_base=3.0
    )


def with_no_retry():
    """No retry (useful for overriding default behavior)"""
    return with_retry(max_attempts=1)
