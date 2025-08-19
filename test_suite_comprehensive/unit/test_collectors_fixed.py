"""
Fixed comprehensive unit tests for collector components.

Tests that match the actual implementation APIs:
- BaseArchiveCollector functionality with correct method signatures
- SlackCollector with actual rate limiting and real collection methods
- CircuitBreaker with correct state management
- Real integration tests without over-mocking
"""

import pytest
import tempfile
import json
import time
import os
from unittest.mock import Mock, patch, MagicMock, call
from pathlib import Path
import requests
import threading

# Import components under test
import sys
sys.path.insert(0, '/Users/david.campos/VibeCode/AICoS-Lab')

from src.collectors.base import BaseArchiveCollector
from src.collectors.slack_collector import SlackCollector, SlackRateLimiter
from src.collectors.circuit_breaker import CircuitBreaker


class TestBaseArchiveCollectorFixed:
    """Test base collector functionality with correct APIs."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_env = {
            "AICOS_BASE_DIR": self.temp_dir,
            "AICOS_TEST_MODE": "true"
        }
        
    @pytest.mark.unit
    @patch.dict('os.environ', {"AICOS_TEST_MODE": "true"})
    def test_collector_initialization(self):
        """BaseArchiveCollector initializes correctly with Stage 1a components."""
        with patch('src.collectors.base.StateManager') as mock_state:
            with patch('src.collectors.base.ArchiveWriter') as mock_writer:
                collector = BaseArchiveCollector("test", {"retry_count": 3})
                
                assert collector.collector_type == "test"
                assert collector.config["retry_count"] == 3
                assert hasattr(collector, 'archive_writer')
                assert hasattr(collector, 'state_manager')
                assert hasattr(collector, 'circuit_breaker')
                assert collector.max_retries == 3  # Default value
        
    @pytest.mark.unit
    @patch.dict('os.environ', {"AICOS_TEST_MODE": "true"})
    def test_retry_logic_with_exponential_backoff(self):
        """Retry logic works with exponential backoff using actual collect_with_retry."""
        with patch('src.collectors.base.StateManager'):
            with patch('src.collectors.base.ArchiveWriter'):
                collector = BaseArchiveCollector("test", {"max_retries": 3, "backoff_factor": 2.0})
                
                # Mock the collect method to fail twice then succeed
                attempt_count = 0
                def mock_collect():
                    nonlocal attempt_count
                    attempt_count += 1
                    if attempt_count < 3:
                        raise requests.RequestException("Temporary failure")
                    return {"success": True, "records": []}
                
                # Test retry mechanism using actual collect_with_retry method
                with patch.object(collector, 'collect', side_effect=mock_collect):
                    start_time = time.time()
                    result = collector.collect_with_retry(max_attempts=3)
                    duration = time.time() - start_time
                    
                    assert result == {"success": True, "records": []}
                    assert attempt_count == 3
                    # Should have backoff delay: 2^0 + 2^1 = 3 seconds minimum
                    assert duration >= 3.0
        
    @pytest.mark.unit
    @patch.dict('os.environ', {"AICOS_TEST_MODE": "true"})
    def test_circuit_breaker_integration(self):
        """Circuit breaker prevents cascade failures correctly."""
        with patch('src.collectors.base.StateManager'):
            with patch('src.collectors.base.ArchiveWriter'):
                collector = BaseArchiveCollector("test", {"circuit_breaker_threshold": 2})
                
                # Simulate multiple failures to trip circuit breaker
                def failing_operation():
                    raise requests.RequestException("Service unavailable")
                
                # Mock the collect method to always fail
                with patch.object(collector, 'collect', side_effect=failing_operation):
                    # First few attempts should fail but retry
                    for i in range(5):
                        try:
                            collector.collect_with_retry(max_attempts=1)
                        except Exception:
                            pass
                    
                    # Circuit breaker should now be open
                    assert collector.circuit_breaker.is_open()
                    
                    # Further calls should be blocked by circuit breaker
                    with pytest.raises(Exception, match="Circuit breaker is open"):
                        collector.collect_with_retry(max_attempts=1)
        
    @pytest.mark.unit
    @patch.dict('os.environ', {"AICOS_TEST_MODE": "true"})
    def test_state_persistence(self):
        """Collector state is persisted correctly using StateManager."""
        with patch('src.collectors.base.StateManager') as mock_state:
            mock_state_instance = Mock()
            mock_state.return_value = mock_state_instance
            
            with patch('src.collectors.base.ArchiveWriter'):
                collector = BaseArchiveCollector("test")
                
                # Test state save - save_state() takes no parameters, saves current state
                collector.set_state({"last_sync": "2025-08-18T12:00:00Z", "cursor": "123"})
                collector.save_state()
                
                # Verify state manager called correctly with key and state
                mock_state_instance.write_state.assert_called_once()
                call_args = mock_state_instance.write_state.call_args[0]
                assert call_args[0] == "test_state"  # Key includes collector type
                assert "last_sync" in call_args[1]  # State includes our update
                assert "cursor" in call_args[1]
                
    @pytest.mark.unit
    @patch.dict('os.environ', {"AICOS_TEST_MODE": "true"})
    def test_archive_integration(self):
        """Archive writer integration works with correct record format."""
        with patch('src.collectors.base.StateManager'):
            with patch('src.collectors.base.ArchiveWriter') as mock_writer:
                mock_writer_instance = Mock()
                mock_writer.return_value = mock_writer_instance
                
                collector = BaseArchiveCollector("test")
                
                # Test record writing - write_to_archive expects collection result format
                test_data = {
                    "data": [
                        {"id": 1, "type": "test", "timestamp": "2025-08-18T12:00:00Z"},
                        {"id": 2, "type": "test", "timestamp": "2025-08-18T12:01:00Z"}
                    ]
                }
                collector.write_to_archive(test_data)
                
                # Verify archive writer called with enhanced records
                mock_writer_instance.write_records.assert_called_once()
                call_args = mock_writer_instance.write_records.call_args[0][0]
                assert len(call_args) == 2
                # Each record should have archive metadata
                for record in call_args:
                    assert 'archive_metadata' in record
                    assert record['archive_metadata']['collector_type'] == 'test'
                    assert 'archived_at' in record['archive_metadata']


class TestSlackCollectorFixed:
    """Test Slack-specific collection functionality with real APIs."""
    
    def setup_method(self):
        """Set up Slack collector test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_env = {
            "AICOS_BASE_DIR": self.temp_dir,
            "AICOS_TEST_MODE": "true"
        }
        
    @pytest.mark.unit
    def test_slack_rate_limiter_basic(self):
        """SlackRateLimiter respects rate limits with correct API."""
        limiter = SlackRateLimiter(base_delay=0.1, channels_per_minute=60)
        
        start_time = time.time()
        
        # Make two requests
        limiter.wait_for_api_limit()
        first_request_time = time.time()
        
        limiter.wait_for_api_limit()
        second_request_time = time.time()
        
        # Should have delay between requests
        delay = second_request_time - first_request_time
        assert delay >= 0.1
        
    @pytest.mark.unit
    def test_slack_rate_limiter_exponential_backoff(self):
        """Rate limiter applies exponential backoff correctly."""
        limiter = SlackRateLimiter(base_delay=0.01)
        
        # Test backoff state tracking
        initial_backoff = limiter.current_backoff_delay
        assert initial_backoff == 0
        
        # Simulate rate limit response
        mock_response = Mock()
        mock_response.status_code = 429
        limiter.handle_rate_limit_response(mock_response)
        
        # Should have increased backoff
        assert limiter.current_backoff_delay > initial_backoff
        assert limiter.consecutive_rate_limits > 0
        
        # Test recovery
        mock_success_response = Mock()
        mock_success_response.status_code = 200
        limiter.handle_rate_limit_response(mock_success_response)
        
        assert limiter.current_backoff_delay == 0
        assert limiter.consecutive_rate_limits == 0
        
    @pytest.mark.unit
    @patch.dict('os.environ', {"AICOS_TEST_MODE": "true"})
    def test_slack_collector_initialization(self):
        """SlackCollector initializes with proper configuration."""
        with patch('src.collectors.slack_collector.credential_vault') as mock_vault:
            mock_vault.get_slack_credentials.return_value = {
                "bot_token": "xoxb-test-token",
                "user_token": "xoxp-test-token"
            }
            
            collector = SlackCollector()
            
            # Verify initialization components
            assert collector.collector_type == "slack"
            assert isinstance(collector.rate_limiter, SlackRateLimiter)
            assert hasattr(collector, 'collection_results')
            assert collector.collection_results["status"] == "initialized"
            assert hasattr(collector, 'channel_cache')
            assert hasattr(collector, 'user_cache')
            
    @pytest.mark.unit
    @patch.dict('os.environ', {"AICOS_TEST_MODE": "true"})
    def test_slack_collector_configuration(self):
        """SlackCollector loads and validates configuration properly."""
        config_dir = Path(self.temp_dir) / "config"
        config_dir.mkdir(exist_ok=True)
        
        # Create test configuration
        config_file = config_dir / "slack_collection.json"
        test_config = {
            "base_delay_seconds": 1.5,
            "channels_per_minute": 20,
            "include_archived": False
        }
        with open(config_file, 'w') as f:
            json.dump(test_config, f)
            
        with patch('src.collectors.slack_collector.credential_vault') as mock_vault:
            mock_vault.get_slack_credentials.return_value = {
                "bot_token": "xoxb-test-token",
                "user_token": "xoxp-test-token"  
            }
            
            collector = SlackCollector(config_path=config_file)
            
            # Verify configuration loaded
            assert collector.config["base_delay_seconds"] == 1.5
            assert collector.config["channels_per_minute"] == 20
            assert collector.rate_limiter.base_delay == 1.5
            assert collector.rate_limiter.channels_per_minute == 20


class TestCircuitBreakerFixed:
    """Test circuit breaker functionality with correct state API."""
    
    @pytest.mark.unit
    def test_circuit_breaker_initialization(self):
        """Circuit breaker initializes with correct default state."""
        breaker = CircuitBreaker(failure_threshold=3, timeout=60)
        
        assert breaker.get_state() == "CLOSED"
        assert breaker.get_failure_count() == 0
        assert breaker.can_execute() is True
        assert breaker.is_open() is False
        
    @pytest.mark.unit
    def test_circuit_breaker_state_transitions(self):
        """Circuit breaker transitions between states correctly."""
        breaker = CircuitBreaker(failure_threshold=2, timeout=1)
        
        # Start in closed state
        assert breaker.get_state() == "CLOSED"
        assert breaker.can_execute() is True
        
        # Record failures - should stay closed until threshold
        breaker.record_failure()
        assert breaker.get_state() == "CLOSED"
        assert breaker.get_failure_count() == 1
        
        # Hit threshold - should open
        breaker.record_failure()
        assert breaker.get_state() == "OPEN"
        assert breaker.get_failure_count() == 2
        assert breaker.can_execute() is False
        assert breaker.is_open() is True
        
    @pytest.mark.unit
    def test_circuit_breaker_recovery(self):
        """Circuit breaker recovers after timeout period."""
        breaker = CircuitBreaker(failure_threshold=1, timeout=1)
        
        # Trip the breaker
        breaker.record_failure()
        assert breaker.get_state() == "OPEN"
        assert breaker.can_execute() is False
        
        # Wait for timeout
        time.sleep(1.1)
        
        # Should transition to half-open and allow execution
        assert breaker.can_execute() is True
        assert breaker.is_half_open() is True
        
        # Successful call should reset to closed
        breaker.record_success()
        assert breaker.get_state() == "CLOSED"
        assert breaker.get_failure_count() == 0
        
    @pytest.mark.unit
    def test_circuit_breaker_prevents_execution(self):
        """Circuit breaker prevents execution when open."""
        breaker = CircuitBreaker(failure_threshold=1)
        
        # Trip the breaker
        breaker.record_failure()
        assert breaker.is_open() is True
        
        # Should prevent execution
        assert breaker.can_execute() is False
        
    @pytest.mark.unit
    def test_circuit_breaker_thread_safety(self):
        """Circuit breaker is thread-safe for concurrent access."""
        breaker = CircuitBreaker(failure_threshold=10, timeout=1)
        results = []
        
        def worker():
            try:
                # Each thread records failures and checks state
                for _ in range(5):
                    breaker.record_failure()
                    can_execute = breaker.can_execute()
                    results.append(can_execute)
            except Exception as e:
                results.append(f"Error: {e}")
                
        # Start multiple threads
        threads = [threading.Thread(target=worker) for _ in range(3)]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
            
        # Should complete without errors
        assert len(results) == 15  # 3 threads * 5 operations each
        assert all(isinstance(r, bool) for r in results)
        
        # Final state should be consistent
        total_failures = breaker.get_failure_count()
        assert total_failures == 15  # All failures recorded


class TestCollectorIntegrationFixed:
    """Test collector integration with correct component APIs."""
    
    def setup_method(self):
        """Set up integration test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_env = {
            "AICOS_BASE_DIR": self.temp_dir,
            "AICOS_TEST_MODE": "true"
        }
        
    @pytest.mark.unit
    @patch.dict('os.environ', {"AICOS_TEST_MODE": "true"})
    def test_collector_archive_writer_integration(self):
        """Collectors integrate correctly with ArchiveWriter using real format."""
        with patch('src.collectors.base.StateManager'):
            with patch('src.collectors.base.ArchiveWriter') as mock_writer:
                mock_writer_instance = Mock()
                mock_writer.return_value = mock_writer_instance
                
                collector = BaseArchiveCollector("integration_test")
                
                # Test writing collection data (not direct records)
                collection_data = {
                    "data": [
                        {"id": 1, "type": "test", "timestamp": "2025-08-18T12:00:00Z"},
                        {"id": 2, "type": "test", "timestamp": "2025-08-18T12:01:00Z"}
                    ],
                    "metadata": {"collection_time": "2025-08-18T12:00:00Z"}
                }
                
                collector.write_to_archive(collection_data)
                
                # Verify archive writer called with enhanced records
                mock_writer_instance.write_records.assert_called_once()
                written_records = mock_writer_instance.write_records.call_args[0][0]
                assert len(written_records) == 2
                
                # Each record should be enhanced with metadata
                for record in written_records:
                    assert "archive_metadata" in record
                    assert record["archive_metadata"]["collector_type"] == "integration_test"
                    
    @pytest.mark.unit
    @patch.dict('os.environ', {"AICOS_TEST_MODE": "true"})
    def test_collector_state_manager_integration(self):
        """Collectors integrate correctly with StateManager using real API."""
        with patch('src.collectors.base.StateManager') as mock_state:
            mock_state_instance = Mock()
            mock_state.return_value = mock_state_instance
            
            with patch('src.collectors.base.ArchiveWriter'):
                collector = BaseArchiveCollector("state_test")
                
                # Test state operations using actual API
                collector.set_state({"last_cursor": "abc123", "last_sync": "2025-08-18T12:00:00Z"})
                collector.save_state()
                
                # Verify state saved with correct key format
                mock_state_instance.write_state.assert_called_once()
                call_args = mock_state_instance.write_state.call_args[0]
                assert call_args[0] == "state_test_state"  # Key format: {type}_state
                
                # State should include both set values and defaults
                state_data = call_args[1]
                assert "last_cursor" in state_data
                assert "last_sync" in state_data
                assert "status" in state_data  # Default from BaseArchiveCollector
                
    @pytest.mark.unit
    @patch.dict('os.environ', {"AICOS_TEST_MODE": "true"})
    def test_end_to_end_collection_flow(self):
        """Test complete collection flow with all components."""
        with patch('src.collectors.base.StateManager') as mock_state:
            with patch('src.collectors.base.ArchiveWriter') as mock_writer:
                mock_state_instance = Mock()
                mock_state.return_value = mock_state_instance
                mock_writer_instance = Mock()
                mock_writer.return_value = mock_writer_instance
                
                collector = BaseArchiveCollector("e2e_test")
                
                # Mock successful collection
                test_collection_result = {
                    "success": True,
                    "data": [
                        {"id": "msg1", "content": "test message", "timestamp": "2025-08-18T12:00:00Z"},
                        {"id": "msg2", "content": "another test", "timestamp": "2025-08-18T12:01:00Z"}
                    ],
                    "cursor": "next_page_token"
                }
                
                with patch.object(collector, 'collect', return_value=test_collection_result):
                    # Run complete collection cycle
                    result = collector.collect_with_retry()
                    
                    # Update state with results
                    collector.set_state({"cursor": result["cursor"], "last_run": time.time()})
                    
                    # Write to archive
                    collector.write_to_archive(result)
                    
                    # Save state
                    collector.save_state()
                    
                # Verify complete workflow executed
                assert result == test_collection_result
                mock_writer_instance.write_records.assert_called_once()
                mock_state_instance.write_state.assert_called_once()
                
                # Circuit breaker should record success
                assert not collector.circuit_breaker.is_open()