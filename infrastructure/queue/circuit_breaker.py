"""
Circuit Breaker pattern for fault tolerance

Implements the Circuit Breaker pattern to prevent cascading failures:
- CLOSED: Normal operation, requests pass through
- OPEN: Failures detected, requests blocked
- HALF_OPEN: Testing if service recovered

Protects against:
- Cascading failures
- Resource exhaustion
- Service overload
"""
import time
import threading
from enum import Enum
from typing import Callable, Any, Optional
from datetime import datetime, timedelta


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"        # Normal operation
    OPEN = "open"            # Blocking requests
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open"""
    pass


class CircuitBreaker:
    """
    Circuit Breaker implementation
    
    Features:
    - Automatic state transitions
    - Configurable thresholds
    - Recovery timeout
    - Thread-safe
    - Statistics tracking
    
    States:
    - CLOSED: Normal operation, track failures
    - OPEN: Block all requests, wait for timeout
    - HALF_OPEN: Allow one test request
    
    Transitions:
    - CLOSED → OPEN: failure_threshold exceeded
    - OPEN → HALF_OPEN: recovery_timeout elapsed
    - HALF_OPEN → CLOSED: test request succeeds
    - HALF_OPEN → OPEN: test request fails
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception
    ):
        """
        Initialize circuit breaker
        
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
            expected_exception: Exception type to catch
        
        Example:
            >>> cb = CircuitBreaker(
            ...     failure_threshold=5,
            ...     recovery_timeout=60
            ... )
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        # State
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: Optional[datetime] = None
        self._lock = threading.Lock()
        
        # Statistics
        self._total_calls = 0
        self._total_failures = 0
        self._total_successes = 0
        self._total_rejections = 0
    
    @property
    def state(self) -> CircuitState:
        """Get current state"""
        return self._state
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
        
        Returns:
            Any: Function result
        
        Raises:
            CircuitBreakerError: If circuit is open
            Exception: If function raises exception
        
        Example:
            >>> def risky_operation():
            ...     # Might fail
            ...     return "success"
            >>> 
            >>> result = cb.call(risky_operation)
        """
        with self._lock:
            self._total_calls += 1
            
            # Check if we should transition to HALF_OPEN
            if self._state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self._state = CircuitState.HALF_OPEN
                    print(f"🔄 Circuit breaker: OPEN → HALF_OPEN (testing recovery)")
                else:
                    self._total_rejections += 1
                    raise CircuitBreakerError(
                        f"Circuit breaker is OPEN. "
                        f"Retry after {self._time_until_reset()}s"
                    )
        
        # Execute function
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        
        except self.expected_exception as e:
            self._on_failure()
            raise
    
    def _on_success(self):
        """Handle successful call"""
        with self._lock:
            self._total_successes += 1
            
            if self._state == CircuitState.HALF_OPEN:
                # Recovery successful
                self._state = CircuitState.CLOSED
                self._failure_count = 0
                print(f"✅ Circuit breaker: HALF_OPEN → CLOSED (recovered)")
            
            # Reset failure count in closed state
            if self._state == CircuitState.CLOSED:
                self._failure_count = 0
    
    def _on_failure(self):
        """Handle failed call"""
        with self._lock:
            self._total_failures += 1
            self._failure_count += 1
            self._last_failure_time = datetime.utcnow()  # UTC for consistency
            
            if self._state == CircuitState.HALF_OPEN:
                # Recovery failed
                self._state = CircuitState.OPEN
                print(f"❌ Circuit breaker: HALF_OPEN → OPEN (recovery failed)")
            
            elif self._state == CircuitState.CLOSED:
                # Check if we should open
                if self._failure_count >= self.failure_threshold:
                    self._state = CircuitState.OPEN
                    print(f"⚠️  Circuit breaker: CLOSED → OPEN ({self._failure_count} failures)")
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        if self._last_failure_time is None:
            return True
        
        elapsed = (datetime.utcnow() - self._last_failure_time).total_seconds()
        return elapsed >= self.recovery_timeout
    
    def _time_until_reset(self) -> int:
        """Get seconds until reset attempt"""
        if self._last_failure_time is None:
            return 0
        
        elapsed = (datetime.utcnow() - self._last_failure_time).total_seconds()
        remaining = max(0, self.recovery_timeout - elapsed)
        return int(remaining)
    
    def reset(self):
        """Manually reset circuit breaker to CLOSED state"""
        with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._last_failure_time = None
            print(f"🔄 Circuit breaker manually reset to CLOSED")
    
    def get_stats(self) -> dict:
        """
        Get circuit breaker statistics
        
        Returns:
            dict: Statistics including state, calls, failures, etc.
        
        Example:
            >>> stats = cb.get_stats()
            >>> print(f"State: {stats['state']}")
            >>> print(f"Success rate: {stats['success_rate']}%")
        """
        with self._lock:
            success_rate = (
                (self._total_successes / self._total_calls * 100)
                if self._total_calls > 0 else 0
            )
            
            return {
                "state": self._state.value,
                "failure_count": self._failure_count,
                "failure_threshold": self.failure_threshold,
                "total_calls": self._total_calls,
                "total_successes": self._total_successes,
                "total_failures": self._total_failures,
                "total_rejections": self._total_rejections,
                "success_rate": round(success_rate, 2),
                "time_until_reset": self._time_until_reset() if self._state == CircuitState.OPEN else None
            }


# Decorator for easy use
def circuit_breaker(
    failure_threshold: int = 5,
    recovery_timeout: int = 60
):
    """
    Decorator to wrap function with circuit breaker
    
    Args:
        failure_threshold: Number of failures before opening
        recovery_timeout: Seconds to wait before recovery
    
    Example:
        >>> @circuit_breaker(failure_threshold=3, recovery_timeout=30)
        ... def unstable_api_call():
        ...     # Might fail
        ...     return requests.get("https://api.example.com")
    """
    cb = CircuitBreaker(
        failure_threshold=failure_threshold,
        recovery_timeout=recovery_timeout
    )
    
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            return cb.call(func, *args, **kwargs)
        
        # Attach circuit breaker for inspection
        wrapper.circuit_breaker = cb
        return wrapper
    
    return decorator
