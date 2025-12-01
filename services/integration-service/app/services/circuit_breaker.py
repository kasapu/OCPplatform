"""
Circuit Breaker Pattern Implementation

Prevents cascading failures by temporarily blocking requests to failing services.

States:
- CLOSED: Normal operation, requests pass through
- OPEN: Service is failing, requests are blocked
- HALF_OPEN: Testing if service has recovered
"""

import time
import logging
from enum import Enum
from typing import Dict, Optional, Callable, Any
from dataclasses import dataclass, field

from app.core.config import settings

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Blocking requests
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitBreaker:
    """
    Circuit breaker for a specific integration

    Usage:
        circuit = CircuitBreaker(name="salesforce-api")

        if circuit.can_execute():
            try:
                result = await make_api_call()
                circuit.record_success()
            except Exception as e:
                circuit.record_failure()
                raise
    """
    name: str
    failure_threshold: int = settings.CIRCUIT_BREAKER_FAILURE_THRESHOLD
    timeout: int = settings.CIRCUIT_BREAKER_TIMEOUT
    half_open_max_calls: int = settings.CIRCUIT_BREAKER_HALF_OPEN_MAX_CALLS

    state: CircuitState = field(default=CircuitState.CLOSED)
    failure_count: int = field(default=0)
    success_count: int = field(default=0)
    last_failure_time: Optional[float] = field(default=None)
    half_open_calls: int = field(default=0)

    def can_execute(self) -> bool:
        """Check if request can be executed"""
        current_time = time.time()

        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            # Check if timeout has passed
            if self.last_failure_time and (current_time - self.last_failure_time) >= self.timeout:
                logger.info(f"Circuit breaker [{self.name}] transitioning to HALF_OPEN")
                self.state = CircuitState.HALF_OPEN
                self.half_open_calls = 0
                return True
            return False

        if self.state == CircuitState.HALF_OPEN:
            # Allow limited calls in half-open state
            if self.half_open_calls < self.half_open_max_calls:
                self.half_open_calls += 1
                return True
            return False

        return False

    def record_success(self):
        """Record successful request"""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.half_open_max_calls:
                logger.info(f"Circuit breaker [{self.name}] transitioning to CLOSED (recovered)")
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.success_count = 0
                self.half_open_calls = 0
        else:
            self.failure_count = max(0, self.failure_count - 1)

    def record_failure(self):
        """Record failed request"""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.state == CircuitState.HALF_OPEN:
            logger.warning(f"Circuit breaker [{self.name}] transitioning back to OPEN (recovery failed)")
            self.state = CircuitState.OPEN
            self.half_open_calls = 0
            self.success_count = 0
        elif self.state == CircuitState.CLOSED:
            if self.failure_count >= self.failure_threshold:
                logger.error(
                    f"Circuit breaker [{self.name}] transitioning to OPEN "
                    f"(failures: {self.failure_count}/{self.failure_threshold})"
                )
                self.state = CircuitState.OPEN

    def reset(self):
        """Manually reset circuit breaker"""
        logger.info(f"Circuit breaker [{self.name}] manually reset")
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.half_open_calls = 0
        self.last_failure_time = None

    def get_status(self) -> Dict[str, Any]:
        """Get current circuit breaker status"""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time,
            "can_execute": self.can_execute()
        }


class CircuitBreakerRegistry:
    """
    Registry to manage multiple circuit breakers

    Usage:
        registry = CircuitBreakerRegistry()
        circuit = registry.get_circuit("salesforce-api")
    """

    def __init__(self):
        self._circuits: Dict[str, CircuitBreaker] = {}

    def get_circuit(self, name: str) -> CircuitBreaker:
        """Get or create circuit breaker for integration"""
        if name not in self._circuits:
            self._circuits[name] = CircuitBreaker(name=name)
        return self._circuits[name]

    def reset_circuit(self, name: str):
        """Reset specific circuit breaker"""
        if name in self._circuits:
            self._circuits[name].reset()

    def reset_all(self):
        """Reset all circuit breakers"""
        for circuit in self._circuits.values():
            circuit.reset()

    def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all circuit breakers"""
        return {
            name: circuit.get_status()
            for name, circuit in self._circuits.items()
        }

    def remove_circuit(self, name: str):
        """Remove circuit breaker"""
        if name in self._circuits:
            del self._circuits[name]


# Decorator for circuit breaker
def with_circuit_breaker(integration_id: str):
    """
    Decorator to wrap functions with circuit breaker

    Usage:
        @with_circuit_breaker("salesforce-api")
        async def call_salesforce():
            ...
    """
    def decorator(func: Callable):
        async def wrapper(*args, **kwargs):
            # Get circuit breaker from app state
            # This will be set during app startup
            from fastapi import Request

            # Find Request in args/kwargs
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            if not request:
                request = kwargs.get('request')

            if not request:
                # No request context, execute without circuit breaker
                return await func(*args, **kwargs)

            registry: CircuitBreakerRegistry = request.app.state.circuit_breaker_registry
            circuit = registry.get_circuit(integration_id)

            if not circuit.can_execute():
                raise Exception(f"Circuit breaker is OPEN for integration: {integration_id}")

            try:
                result = await func(*args, **kwargs)
                circuit.record_success()
                return result
            except Exception as e:
                circuit.record_failure()
                raise

        return wrapper
    return decorator
