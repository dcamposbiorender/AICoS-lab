"""
Circuit breaker pattern implementation for API failure handling.

This module provides a circuit breaker pattern to protect against cascading
failures when external APIs become unavailable or start failing consistently.

References:
- https://martinfowler.com/bliki/CircuitBreaker.html
- CLAUDE.md production quality requirements
"""

import time
import threading
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class CircuitBreaker:
    """
    Circuit breaker pattern implementation for API failure handling.
    
    States:
    - CLOSED: Normal operation, requests allowed
    - OPEN: Failure threshold exceeded, requests blocked  
    - HALF_OPEN: Testing if service recovered, limited requests allowed
    
    The circuit breaker automatically transitions between states based on
    success/failure rates and configurable timeouts.
    """
    
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            timeout: Seconds to wait before trying half-open state
        """
        if failure_threshold <= 0:
            raise ValueError("failure_threshold must be positive")
        if timeout <= 0:
            raise ValueError("timeout must be positive")
            
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self._lock = threading.Lock()
        
        logger.debug(f"Circuit breaker initialized: threshold={failure_threshold}, timeout={timeout}s")
    
    def record_failure(self) -> None:
        """Record a failure and potentially open the circuit."""
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
                logger.warning(f"Circuit breaker opened after {self.failure_count} failures")
    
    def open(self) -> None:
        """Force the circuit breaker to open state."""
        with self._lock:
            self.state = "OPEN"
            self.last_failure_time = time.time()
            logger.info("Circuit breaker manually opened")
    
    def record_success(self) -> None:
        """Record a success and reset the circuit breaker."""
        with self._lock:
            self.failure_count = 0
            self.state = "CLOSED"
            self.last_failure_time = None
            logger.info("Circuit breaker reset after successful call")
    
    def is_open(self) -> bool:
        """Check if circuit breaker is open (blocking requests)."""
        with self._lock:
            if self.state == "OPEN":
                # Check if we should transition to half-open
                if (self.last_failure_time and 
                    time.time() - self.last_failure_time >= self.timeout):
                    self.state = "HALF_OPEN"
                    logger.info("Circuit breaker transitioning to half-open")
                    return False
                return True
            return False
    
    def is_half_open(self) -> bool:
        """Check if circuit breaker is in half-open state."""
        with self._lock:
            return self.state == "HALF_OPEN"
    
    def can_execute(self) -> bool:
        """Check if requests can be executed."""
        return not self.is_open()
    
    def get_state(self) -> str:
        """Get current circuit breaker state."""
        with self._lock:
            return self.state
    
    def get_failure_count(self) -> int:
        """Get current failure count."""
        with self._lock:
            return self.failure_count
    
    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"<CircuitBreaker(state={self.state}, failures={self.failure_count}/{self.failure_threshold})>"