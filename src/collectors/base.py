"""
BaseArchiveCollector abstract class for unified data collection.
Provides retry logic, circuit breaker, archive writing, and state persistence.

This is the foundation for all collector wrappers that integrate existing scavenge/
collectors with the AI Chief of Staff archive system.

References:
- Stage 1a ArchiveWriter integration
- Stage 1a Config and StateManager integration
- CLAUDE.md production quality requirements
"""

import time
import threading
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import logging

# Import Stage 1a components
from src.core.config import get_config
from src.core.state import StateManager
from src.core.archive_writer import ArchiveWriter, ArchiveError

# Import circuit breaker
from src.collectors.circuit_breaker import CircuitBreaker

logger = logging.getLogger(__name__)


class BaseArchiveCollector(ABC):
    """
    Abstract base class for all archive collectors.
    
    Provides unified interface for data collection with built-in:
    - Retry logic with exponential backoff  
    - Circuit breaker for API failure handling
    - ArchiveWriter integration for JSONL archives
    - StateManager integration for persistent state
    - Thread-safe concurrent collection
    - Config integration for paths and settings
    """
    
    def __init__(self, collector_type: str, config: Optional[Dict[str, Any]] = None, 
                 system_config=None, state_manager=None, archive_writer=None):
        """
        Initialize base collector with Stage 1a component integration.
        
        Args:
            collector_type: Type identifier (slack, calendar, drive, employee)
            config: Configuration dictionary with retry/circuit breaker settings
            system_config: Override system config (for testing)
            state_manager: Override state manager (for testing)
            archive_writer: Override archive writer (for testing)
        """
        self.collector_type = collector_type
        self.config = config or {}
        
        # Validate configuration
        self._validate_config()
        
        # Initialize Stage 1a components (allow injection for testing)
        try:
            if system_config is None:
                self.system_config = get_config()
            else:
                self.system_config = system_config
                
            if state_manager is None:
                self.state_manager = StateManager()
            else:
                self.state_manager = state_manager
                
            if archive_writer is None:
                self.archive_writer = ArchiveWriter(source_name=collector_type)
            else:
                self.archive_writer = archive_writer
                
        except Exception as e:
            logger.error(f"Failed to initialize Stage 1a components: {e}")
            raise
        
        # Initialize retry and circuit breaker settings
        self.max_retries = self.config.get('max_retries', 3)
        self.backoff_factor = self.config.get('backoff_factor', 2.0)
        self.circuit_breaker_threshold = self.config.get('circuit_breaker_threshold', 5)
        
        # Initialize circuit breaker
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=self.circuit_breaker_threshold,
            timeout=self.config.get('circuit_breaker_timeout', 60)
        )
        
        # Initialize state and thread safety
        self._state_lock = threading.Lock()
        self._state = {
            "cursor": None,
            "last_run": None,
            "status": "initialized"
        }
        
        logger.info(f"Initialized {collector_type} collector with Stage 1a integration")
    
    def _validate_config(self) -> None:
        """Validate collector configuration."""
        if not isinstance(self.config, dict):
            raise ValueError("Invalid configuration: must be dictionary")
        
        # Validate numeric settings
        numeric_settings = ['max_retries', 'backoff_factor', 'circuit_breaker_threshold']
        for setting in numeric_settings:
            if setting in self.config:
                if not isinstance(self.config[setting], (int, float)):
                    raise ValueError(f"Invalid configuration: {setting} must be numeric")
                if self.config[setting] <= 0:
                    raise ValueError(f"Invalid configuration: {setting} must be positive")
    
    @abstractmethod
    def collect(self) -> Dict[str, Any]:
        """
        Collect data from the source system.
        
        Returns:
            Dictionary containing collected data and metadata
            
        Must implement:
        {
            'data': [...],  # Raw collected data
            'metadata': {
                'collector_type': str,
                'collection_timestamp': str,
                'version': str,
                'state': dict
            }
        }
        """
        pass
    
    @abstractmethod
    def get_state(self) -> Dict[str, Any]:
        """
        Get current collector state.
        
        Returns:
            Dictionary containing cursor, timestamps, and other state data
        """
        pass
    
    @abstractmethod
    def set_state(self, state: Dict[str, Any]) -> None:
        """
        Update collector state.
        
        Args:
            state: New state dictionary to merge with current state
        """
        pass
    
    def collect_with_retry(self, max_attempts: Optional[int] = None) -> Dict[str, Any]:
        """
        Collect data with retry logic and exponential backoff.
        
        Args:
            max_attempts: Override default max retry attempts
            
        Returns:
            Collection result dictionary
            
        Raises:
            Exception: If max retries exceeded or circuit breaker is open
        """
        if not self.circuit_breaker.can_execute():
            raise Exception("Circuit breaker is open - API calls blocked")
        
        max_attempts = max_attempts or self.max_retries
        last_exception = None
        
        for attempt in range(max_attempts):
            try:
                logger.debug(f"Collection attempt {attempt + 1}/{max_attempts}")
                
                result = self.collect()
                
                # Success - reset circuit breaker and return
                self.circuit_breaker.record_success()
                return result
                
            except Exception as e:
                last_exception = e
                logger.warning(f"Collection attempt {attempt + 1} failed: {e}")
                
                # Record failure for circuit breaker
                self.circuit_breaker.record_failure()
                
                # Don't wait after the final attempt
                if attempt < max_attempts - 1:
                    delay = self._calculate_backoff_delay(attempt)
                    logger.info(f"Waiting {delay}s before retry attempt {attempt + 2}")
                    time.sleep(delay)
        
        # All attempts failed
        raise Exception(f"Max retries exceeded after {max_attempts} attempts. Last error: {last_exception}")
    
    def _calculate_backoff_delay(self, attempt: int) -> float:
        """
        Calculate exponential backoff delay for retry attempts.
        
        Args:
            attempt: Zero-based attempt number
            
        Returns:
            Delay in seconds (1, 2, 4, 8, 16, ...)
        """
        return self.backoff_factor ** attempt
    
    def record_failure(self) -> None:
        """Record a failure for circuit breaker tracking."""
        self.circuit_breaker.record_failure()
    
    def record_success(self) -> None:
        """Record a success for circuit breaker tracking.""" 
        self.circuit_breaker.record_success()
    
    def write_to_archive(self, data: Dict[str, Any]) -> None:
        """
        Write collected data to JSONL archive using Stage 1a ArchiveWriter.
        
        Args:
            data: Collection result to archive
        """
        try:
            # Transform data to list of records for ArchiveWriter
            if 'data' in data:
                # Handle structured collection result
                records = []
                collection_data = data['data']
                
                if isinstance(collection_data, list):
                    records = collection_data
                elif isinstance(collection_data, dict):
                    records = [collection_data]
                else:
                    records = [{'raw_data': collection_data}]
            else:
                # Handle direct data
                records = [data]
            
            # Add metadata to each record
            for record in records:
                if not isinstance(record, dict):
                    record = {'raw_data': record}
                
                record['archive_metadata'] = {
                    'collector_type': self.collector_type,
                    'archived_at': time.time(),
                    'archive_version': '1.0'
                }
            
            # Use Stage 1a ArchiveWriter for atomic JSONL writing
            self.archive_writer.write_records(records)
            
            logger.info(f"Archived {len(records)} records using Stage 1a ArchiveWriter")
            
        except ArchiveError as e:
            logger.error(f"Archive write failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during archive write: {e}")
            raise
    
    def save_state(self) -> None:
        """Save current state using Stage 1a StateManager."""
        try:
            current_state = self.get_state()
            state_key = f"{self.collector_type}_state"
            
            self.state_manager.write_state(state_key, current_state)
            logger.debug(f"Saved state using Stage 1a StateManager: {state_key}")
            
        except Exception as e:
            logger.error(f"Failed to save state: {e}")
            raise
    
    def load_state(self) -> None:
        """Load state using Stage 1a StateManager."""
        try:
            state_key = f"{self.collector_type}_state"
            saved_state = self.state_manager.read_state(state_key)
            
            if saved_state:
                self.set_state(saved_state)
                logger.info(f"Loaded state using Stage 1a StateManager: {state_key}")
            else:
                logger.debug(f"No saved state found for {state_key}")
                
        except Exception as e:
            logger.warning(f"Failed to load state: {e}")
            logger.info("Using default state instead")
            # Don't raise - gracefully fall back to default state
    
    def get_metadata(self) -> Dict[str, Any]:
        """
        Get standard metadata for collection results.
        
        Returns:
            Metadata dictionary with collector info, timestamp, and state
        """
        return {
            'collector_type': self.collector_type,
            'collection_timestamp': time.time(),
            'version': '1.0',
            'state': self.get_state(),
            'config': {
                'max_retries': self.max_retries,
                'backoff_factor': self.backoff_factor,
                'circuit_breaker_threshold': self.circuit_breaker_threshold
            },
            'system_integration': {
                'stage_1a_components': True,
                'archive_writer': True,
                'state_manager': True,
                'config_manager': True
            }
        }
    
    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"<{self.__class__.__name__}(type={self.collector_type}, state={self.get_state()})>"