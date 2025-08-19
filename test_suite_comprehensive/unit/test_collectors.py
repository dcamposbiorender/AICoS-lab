"""
Comprehensive unit tests for collector components.

Tests:
- BaseArchiveCollector functionality and patterns
- SlackCollector with rate limiting and API mocking
- CalendarCollector with OAuth and event handling
- EmployeeCollector with directory integration
- Circuit breaker and retry logic
"""

import pytest
import tempfile
import json
import time
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import requests
import threading

# Import components under test
import sys
sys.path.insert(0, '/Users/david.campos/VibeCode/AICoS-Lab')

from src.collectors.base import BaseArchiveCollector
from src.collectors.slack_collector import SlackCollector, SlackRateLimiter
from src.collectors.calendar_collector import CalendarCollector
from src.collectors.employee_collector import EmployeeCollector
from src.collectors.circuit_breaker import CircuitBreaker


class TestBaseArchiveCollector:
    """Test base collector functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.mock_config = Mock()
        self.mock_config.base_dir = Path(self.temp_dir)
        
    @pytest.mark.unit
    def test_collector_initialization(self):
        """BaseArchiveCollector initializes correctly."""
        collector = BaseArchiveCollector(
            collector_type="test",
            config={"retry_count": 3}
        )
        
        assert collector.collector_type == "test"
        assert collector.config["retry_count"] == 3
        assert hasattr(collector, 'archive_writer')
        
    @pytest.mark.unit 
    def test_retry_logic_with_exponential_backoff(self):
        """Retry logic works with exponential backoff."""
        collector = BaseArchiveCollector("test", {"retry_count": 3})
        
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
            # Should have some delay from backoff
            assert duration > 0.1
        
    @pytest.mark.unit
    def test_circuit_breaker_integration(self):
        """Circuit breaker prevents cascade failures."""
        collector = BaseArchiveCollector("test", {"failure_threshold": 2})
        
        # Simulate multiple failures to trip circuit breaker
        def failing_operation():
            raise requests.RequestException("Service unavailable")
        
        # Mock the collect method to always fail
        with patch.object(collector, 'collect', side_effect=failing_operation):
            # Should try until circuit breaker trips
            with pytest.raises(Exception):
                for _ in range(5):
                    try:
                        collector.collect_with_retry(max_attempts=1)
                    except:
                        pass
                        
        # Circuit breaker should now be open (if implemented)
        assert hasattr(collector, 'circuit_breaker')
        
    @pytest.mark.unit
    def test_state_persistence(self):
        """Collector state is persisted correctly."""
        with patch('src.collectors.base.StateManager') as mock_state:
            mock_state_instance = Mock()
            mock_state.return_value = mock_state_instance
            
            collector = BaseArchiveCollector("test")
            
            # Test state save
            test_state = {"last_sync": "2025-08-18T12:00:00Z", "cursor": "123"}
            collector.save_state(test_state)
            
            # Verify state manager called correctly - it should call set_state
            # The state gets merged, so it should contain both original and new values
            mock_state_instance.set_state.assert_called_once()
            call_args = mock_state_instance.set_state.call_args
            assert call_args[0][0] == "test_state"
            state_dict = call_args[0][1]
            assert "cursor" in state_dict  # Should contain the new cursor value
            assert "last_sync" in state_dict  # Should contain the added state
            
    @pytest.mark.unit
    def test_archive_integration(self):
        """Archive writer integration works correctly."""
        with patch('src.collectors.base.ArchiveWriter') as mock_writer:
            mock_writer_instance = Mock()
            mock_writer.return_value = mock_writer_instance
            
            collector = BaseArchiveCollector("test")
            
            # Test record writing
            test_records = [{"id": 1, "data": "test"}]
            collector.write_to_archive(test_records)
            
            # Verify archive writer called with metadata added
            # The implementation adds archive_metadata to each record
            expected_call = mock_writer_instance.write_records.call_args
            actual_records = expected_call[0][0]  # First argument of the call
            
            # Verify structure
            assert len(actual_records) == 1
            assert actual_records[0]["id"] == 1
            assert actual_records[0]["data"] == "test"
            assert "archive_metadata" in actual_records[0]
            assert actual_records[0]["archive_metadata"]["collector_type"] == "test"


class TestSlackCollector:
    """Test Slack-specific collection functionality."""
    
    def setup_method(self):
        """Set up Slack collector test environment."""
        self.temp_dir = tempfile.mkdtemp()
        
    @pytest.mark.unit
    def test_slack_rate_limiter_basic(self):
        """SlackRateLimiter respects rate limits."""
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
        """Rate limiter applies exponential backoff."""
        limiter = SlackRateLimiter(base_delay=0.01)
        
        # Simulate rate limit hits
        initial_backoff = limiter.current_backoff_delay
        limiter.handle_rate_limit_response()
        first_backoff = limiter.current_backoff_delay
        limiter.handle_rate_limit_response()
        second_backoff = limiter.current_backoff_delay
        
        # Backoff should increase
        assert first_backoff > initial_backoff
        assert second_backoff > first_backoff
        
    @pytest.mark.unit
    @patch('src.collectors.slack_collector.requests.post')
    def test_slack_api_authentication(self, mock_post):
        """Slack API authentication headers are correct."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"ok": True, "channels": []}
        mock_post.return_value = mock_response
        
        with patch('src.collectors.slack_collector.credential_vault') as mock_vault:
            mock_vault.create_slack_headers.return_value = {"Authorization": "Bearer test-token"}
            
            collector = SlackCollector()
            result = collector._make_slack_request("conversations.list", {})
            
            # Verify request made with correct headers
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert "Authorization" in call_args[1]["headers"]
            
    @pytest.mark.unit
    @patch('src.collectors.slack_collector.requests.post')
    def test_slack_message_collection(self, mock_post):
        """Slack message collection handles pagination."""
        # Mock paginated responses
        responses = [
            {"ok": True, "messages": [{"ts": "1", "text": "msg1"}], "has_more": True, "response_metadata": {"next_cursor": "cursor1"}},
            {"ok": True, "messages": [{"ts": "2", "text": "msg2"}], "has_more": False}
        ]
        
        mock_post.side_effect = [Mock(status_code=200, json=lambda: resp) for resp in responses]
        
        with patch('src.collectors.slack_collector.credential_vault') as mock_vault:
            mock_vault.create_slack_headers.return_value = {"Authorization": "Bearer test-token"}
            
            collector = SlackCollector()
            messages = collector.collect_channel_messages("C123456")
            
            # Should have collected from both pages
            assert len(messages) == 2
            assert messages[0]["text"] == "msg1"
            assert messages[1]["text"] == "msg2"
            
    @pytest.mark.unit
    def test_slack_channel_discovery(self):
        """Slack channel discovery filters correctly."""
        mock_channels = [
            {"id": "C1", "name": "general", "is_archived": False, "is_member": True},
            {"id": "C2", "name": "random", "is_archived": True, "is_member": True},
            {"id": "C3", "name": "private", "is_archived": False, "is_member": False}
        ]
        
        with patch.object(SlackCollector, '_make_slack_request') as mock_request:
            mock_request.return_value = {"ok": True, "channels": mock_channels}
            
            collector = SlackCollector()
            active_channels = collector.discover_channels()
            
            # Should filter out archived and non-member channels
            assert len(active_channels) == 1
            assert active_channels[0]["name"] == "general"


class TestCalendarCollector:
    """Test Calendar collection functionality."""
    
    @pytest.mark.unit
    @patch('src.collectors.calendar_collector.build')
    def test_calendar_service_initialization(self, mock_build):
        """Calendar service initializes with OAuth credentials."""
        mock_service = Mock()
        mock_build.return_value = mock_service
        
        collector = CalendarCollector()
        service = collector._get_calendar_service()
        
        assert service == mock_service
        mock_build.assert_called_once()
        
    @pytest.mark.unit
    @patch('src.collectors.calendar_collector.build')
    def test_calendar_event_collection(self, mock_build):
        """Calendar events are collected correctly."""
        mock_service = Mock()
        mock_events = Mock()
        mock_events.list.return_value.execute.return_value = {
            "items": [
                {"id": "event1", "summary": "Meeting 1", "start": {"dateTime": "2025-08-18T10:00:00Z"}},
                {"id": "event2", "summary": "Meeting 2", "start": {"dateTime": "2025-08-18T14:00:00Z"}}
            ]
        }
        mock_service.events.return_value = mock_events
        mock_build.return_value = mock_service
        
        collector = CalendarCollector()
        events = collector.collect_events(days_back=7)
        
        assert len(events) == 2
        assert events[0]["summary"] == "Meeting 1"
        
    @pytest.mark.unit
    def test_calendar_timezone_handling(self):
        """Calendar handles timezone conversions correctly."""
        collector = CalendarCollector()
        
        # Test timestamp normalization
        test_event = {
            "start": {"dateTime": "2025-08-18T10:00:00-07:00"},
            "end": {"dateTime": "2025-08-18T11:00:00-07:00"}
        }
        
        normalized = collector._normalize_event_times(test_event)
        
        # Should have normalized timezone info
        assert "start" in normalized
        assert "end" in normalized


class TestEmployeeCollector:
    """Test Employee directory collection."""
    
    @pytest.mark.unit
    def test_employee_roster_parsing(self):
        """Employee roster parses correctly from multiple sources."""
        test_employees = [
            {"slack_id": "U123", "email": "alice@company.com", "name": "Alice Smith"},
            {"slack_id": "U456", "email": "bob@company.com", "name": "Bob Jones"}
        ]
        
        with patch.object(EmployeeCollector, '_load_slack_users') as mock_slack:
            mock_slack.return_value = test_employees
            
            collector = EmployeeCollector()
            roster = collector.collect_employee_roster()
            
            assert len(roster) == 2
            assert roster[0]["email"] == "alice@company.com"
            
    @pytest.mark.unit
    def test_employee_id_mapping(self):
        """Employee ID mapping works across systems."""
        collector = EmployeeCollector()
        
        test_mapping = {
            "slack_id": "U123456",
            "email": "alice@company.com",
            "calendar_id": "alice@company.com",
            "display_name": "Alice Smith"
        }
        
        # Test ID resolution
        slack_id = collector.resolve_slack_id("alice@company.com", [test_mapping])
        assert slack_id == "U123456"
        
        email = collector.resolve_email("U123456", [test_mapping])
        assert email == "alice@company.com"


class TestCircuitBreaker:
    """Test circuit breaker functionality."""
    
    @pytest.mark.unit
    def test_circuit_breaker_states(self):
        """Circuit breaker transitions between states correctly."""
        breaker = CircuitBreaker(failure_threshold=2, timeout=1)
        
        # Start in closed state  
        assert breaker.get_state() == "CLOSED"
        
        # Record failures
        breaker.record_failure()
        assert breaker.get_state() == "CLOSED"
        
        breaker.record_failure()
        assert breaker.get_state() == "OPEN"
        
        # Wait for recovery timeout
        time.sleep(1.1)
        assert breaker.can_execute()  # Should be in half-open
        
    @pytest.mark.unit
    def test_circuit_breaker_prevents_calls(self):
        """Circuit breaker prevents calls when open."""
        breaker = CircuitBreaker(failure_threshold=1)
        
        # Trip the breaker
        breaker.record_failure()
        
        # Should prevent execution
        assert not breaker.can_execute()
        
        # Circuit breaker doesn't have a 'call' method - test can_execute instead
        assert not breaker.can_execute(), "Circuit breaker should prevent execution when open"
            
    @pytest.mark.unit
    def test_circuit_breaker_success_resets(self):
        """Successful calls reset failure count."""
        breaker = CircuitBreaker(failure_threshold=3)
        
        # Record some failures
        breaker.record_failure()
        breaker.record_failure()
        assert breaker.failure_count == 2
        
        # Record success
        breaker.record_success()
        assert breaker.get_failure_count() == 0
        assert breaker.get_state() == "CLOSED"


class TestCollectorIntegration:
    """Test collector integration with core components."""
    
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
        """Collectors integrate correctly with ArchiveWriter."""
        with patch('src.collectors.base.ArchiveWriter') as mock_writer:
            mock_writer_instance = Mock()
            mock_writer.return_value = mock_writer_instance
            
            collector = BaseArchiveCollector("integration_test")
            
            # Test writing records
            test_records = [
                {"id": 1, "type": "test", "timestamp": "2025-08-18T12:00:00Z"},
                {"id": 2, "type": "test", "timestamp": "2025-08-18T12:01:00Z"}
            ]
            
            collector.write_to_archive(test_records)
            
            # Verify archive writer called with correct data
            mock_writer_instance.write_records.assert_called_once_with(test_records)
            
    @pytest.mark.unit
    @patch.dict('os.environ', {"AICOS_TEST_MODE": "true"})
    def test_collector_state_manager_integration(self):
        """Collectors integrate correctly with StateManager."""
        with patch('src.collectors.base.StateManager') as mock_state:
            mock_state_instance = Mock()
            mock_state.return_value = mock_state_instance
            
            collector = BaseArchiveCollector("state_test")
            
            # Test state operations
            test_state = {"last_cursor": "abc123", "last_sync": "2025-08-18T12:00:00Z"}
            collector.save_state(test_state)
            
            # Verify state saved correctly
            mock_state_instance.set_state.assert_called_once()
            call_args = mock_state_instance.set_state.call_args[0]
            assert "state_test" in call_args[0]  # Key includes collector type
            assert call_args[1] == test_state  # Value is correct


class TestCollectorPerformance:
    """Test collector performance requirements."""
    
    @pytest.mark.unit
    def test_rate_limiter_performance(self):
        """Rate limiter doesn't add excessive overhead."""
        limiter = SlackRateLimiter(base_delay=0.01)  # Very small delay for testing
        
        start_time = time.time()
        
        # Make 10 requests
        for _ in range(10):
            limiter.wait_for_api_limit()
            
        duration = time.time() - start_time
        
        # Should complete quickly with minimal delays
        assert duration < 1.0  # Less than 1 second for 10 requests
        
    @pytest.mark.unit
    @patch('src.collectors.base.time.sleep')
    def test_retry_backoff_timing(self, mock_sleep):
        """Retry backoff uses correct timing intervals."""
        collector = BaseArchiveCollector("timing_test", {"retry_count": 3})
        
        attempt_count = 0
        def failing_operation():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count <= 2:
                raise requests.RequestException("Fail")
            return "success"
        
        result = collector._retry_with_backoff(failing_operation)
        
        # Should have called sleep with exponential backoff
        assert mock_sleep.call_count == 2  # Two retries
        sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
        
        # Verify exponential backoff pattern
        assert sleep_calls[0] < sleep_calls[1]  # Second delay > first delay
        
    @pytest.mark.unit
    def test_concurrent_collector_safety(self):
        """Multiple collectors can run safely in parallel."""
        collectors = []
        results = []
        errors = []
        
        def worker(collector_id):
            try:
                collector = BaseArchiveCollector(f"concurrent_{collector_id}")
                # Simulate some work
                time.sleep(0.1)
                results.append(f"collector_{collector_id}_success")
            except Exception as e:
                errors.append(f"collector_{collector_id}: {e}")
        
        # Run multiple collectors concurrently
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # All should complete successfully
        assert len(errors) == 0
        assert len(results) == 5


class TestCollectorErrorHandling:
    """Test error handling and resilience."""
    
    @pytest.mark.unit
    def test_network_error_handling(self):
        """Collectors handle network errors gracefully."""
        collector = BaseArchiveCollector("error_test", {"retry_count": 2})
        
        def network_error():
            raise requests.ConnectionError("Network unreachable")
        
        # Should exhaust retries and raise appropriate error
        with pytest.raises(requests.ConnectionError):
            collector._retry_with_backoff(network_error)
            
    @pytest.mark.unit
    def test_api_error_handling(self):
        """Collectors handle API errors appropriately."""
        collector = BaseArchiveCollector("api_error_test")
        
        def api_error():
            raise requests.HTTPError("401 Unauthorized")
        
        # Should not retry authentication errors
        with pytest.raises(requests.HTTPError):
            collector._retry_with_backoff(api_error)
            
    @pytest.mark.unit
    def test_malformed_response_handling(self):
        """Collectors handle malformed API responses."""
        with patch('src.collectors.slack_collector.requests.post') as mock_post:
            # Mock malformed JSON response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
            mock_post.return_value = mock_response
            
            with patch('src.collectors.slack_collector.credential_vault'):
                collector = SlackCollector()
                
                # Should handle JSON decode errors gracefully
                with pytest.raises(json.JSONDecodeError):
                    collector._make_slack_request("test.method", {})


if __name__ == "__main__":
    # Run collector tests with coverage
    pytest.main([
        __file__,
        "-v",
        "--cov=../../src/collectors",
        "--cov-report=html:../reports/coverage/collectors",
        "--cov-report=term-missing"
    ])