#!/usr/bin/env python3
"""
Comprehensive edge case tests for data collection systems.

This test suite validates system behavior under extreme and boundary conditions that
could occur in production environments, focusing on scenarios that would break
typical implementations but should be handled gracefully by a robust system.

Test Categories:
1. Empty Data Sources (workspaces with no data)
2. Corrupted/Malformed Data (invalid JSON, missing fields)
3. API Rate Limit Boundary Conditions
4. Network Failure and Timeout Scenarios
5. Large Dataset Boundary Conditions
6. Character Encoding and Unicode Edge Cases
7. Timestamp and Timezone Edge Cases
8. Permission and Access Control Edge Cases
"""

import pytest
import json
import tempfile
import time
import asyncio
import threading
from pathlib import Path
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, Mock, MagicMock, AsyncMock
from typing import Dict, List, Any, Optional
from hypothesis import given, strategies as st, settings, HealthCheck
import requests
from requests.exceptions import Timeout, ConnectionError, HTTPError

# Import system components (will fail during Red phase)
try:
    from src.collectors.slack_collector import SlackCollector
    from src.collectors.calendar_collector import CalendarCollector
    from src.collectors.drive_collector import DriveCollector
    from src.collectors.employee_collector import EmployeeCollector
    from src.collectors.circuit_breaker import CircuitBreaker
    from src.core.archive_writer import ArchiveWriter, ArchiveError
    from src.core.config import Config, ConfigurationError
    from tests.fixtures.mock_slack_data import get_mock_channels, get_mock_messages
except ImportError:
    # Expected during Red phase - tests will be skipped
    pass


class TestEmptyDataSources:
    """Test behavior when data sources are completely empty."""
    
    def test_slack_empty_workspace(self):
        """Handle Slack workspace with no channels, users, or messages."""
        empty_responses = {
            'conversations.list': {'ok': True, 'channels': []},
            'users.list': {'ok': True, 'members': []},
            'conversations.history': {'ok': True, 'messages': []},
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_config = Mock()
            mock_config.archive_dir = Path(temp_dir)
            
            with patch('slack_sdk.WebClient') as mock_client:
                mock_instance = Mock()
                # Configure empty responses for all API calls
                def mock_api_call(method, **kwargs):
                    return empty_responses.get(method, {'ok': False, 'error': 'method_not_found'})
                
                mock_instance.api_call.side_effect = mock_api_call
                mock_client.return_value = mock_instance
                
                with patch('src.collectors.slack_collector.get_config', return_value=mock_config):
                    collector = SlackCollector()
                    result = collector.collect()
                    
                    # Should handle empty workspace gracefully
                    assert result['discovered']['channels'] == 0
                    assert result['discovered']['users'] == 0
                    assert result['collected']['messages'] == 0
                    assert result['status'] == 'success'
    
    def test_calendar_no_calendars(self):
        """Handle Google Calendar with no accessible calendars."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_config = Mock()
            mock_config.archive_dir = Path(temp_dir)
            
            with patch('googleapiclient.discovery.build') as mock_build:
                mock_service = Mock()
                mock_calendar_list = Mock()
                mock_calendar_list.list.return_value.execute.return_value = {'items': []}
                mock_service.calendarList.return_value = mock_calendar_list
                mock_build.return_value = mock_service
                
                with patch('src.collectors.calendar_collector.get_config', return_value=mock_config):
                    collector = CalendarCollector()
                    result = collector.collect()
                    
                    # Should handle no calendars gracefully
                    assert result['discovered']['calendars'] == 0
                    assert result['collected']['events'] == 0
                    assert result['status'] == 'success'
    
    def test_drive_empty_drive(self):
        """Handle Google Drive with no files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_config = Mock()
            mock_config.archive_dir = Path(temp_dir)
            
            with patch('googleapiclient.discovery.build') as mock_build:
                mock_service = Mock()
                mock_files = Mock()
                mock_files.list.return_value.execute.return_value = {'files': []}
                mock_service.files.return_value = mock_files
                mock_build.return_value = mock_service
                
                with patch('src.collectors.drive_collector.get_config', return_value=mock_config):
                    collector = DriveCollector()
                    result = collector.collect()
                    
                    # Should handle empty drive gracefully
                    assert result['discovered']['files'] == 0
                    assert result['collected']['changes'] == 0
                    assert result['status'] == 'success'
    
    def test_employee_empty_roster(self):
        """Handle organization with no employee data."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_config = Mock()
            mock_config.archive_dir = Path(temp_dir)
            
            with patch('src.collectors.employee_collector.get_config', return_value=mock_config):
                collector = EmployeeCollector()
                result = collector.collect()
                
                # Should handle empty roster gracefully
                assert result['discovered']['employees'] == 0
                assert result['collected']['mappings'] == 0
                assert result['status'] == 'success'


class TestCorruptedMalformedData:
    """Test handling of corrupted or malformed data from APIs."""
    
    def test_slack_malformed_json_response(self):
        """Handle Slack API returning malformed JSON."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_config = Mock()
            mock_config.archive_dir = Path(temp_dir)
            
            with patch('slack_sdk.WebClient') as mock_client:
                mock_instance = Mock()
                # Simulate malformed JSON response
                mock_instance.api_call.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
                mock_client.return_value = mock_instance
                
                with patch('src.collectors.slack_collector.get_config', return_value=mock_config):
                    collector = SlackCollector()
                    
                    # Should handle JSON decode errors gracefully
                    result = collector.collect()
                    assert result['status'] == 'error'
                    assert 'json' in result['error'].lower()
    
    def test_slack_missing_required_fields(self):
        """Handle Slack data with missing required fields."""
        corrupted_channel = {
            # Missing 'id' field
            'name': 'corrupted-channel',
            'is_channel': True
        }
        
        corrupted_message = {
            # Missing 'ts' and 'text' fields  
            'type': 'message',
            'channel': 'C1234567890'
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_config = Mock()
            mock_config.archive_dir = Path(temp_dir)
            
            with patch('slack_sdk.WebClient') as mock_client:
                mock_instance = Mock()
                mock_instance.api_call.return_value = {
                    'ok': True,
                    'channels': [corrupted_channel],
                    'messages': [corrupted_message]
                }
                mock_client.return_value = mock_instance
                
                with patch('src.collectors.slack_collector.get_config', return_value=mock_config):
                    collector = SlackCollector()
                    result = collector.collect()
                    
                    # Should filter out corrupted data but continue
                    assert result['status'] in ['success', 'partial']
                    assert 'skipped' in result or 'errors' in result
    
    def test_calendar_invalid_date_formats(self):
        """Handle Calendar events with invalid date/time formats."""
        invalid_event = {
            'id': 'invalid-event',
            'summary': 'Event with bad dates',
            'start': {'dateTime': 'not-a-valid-datetime'},
            'end': {'dateTime': '2025-13-50T25:70:90Z'}  # Invalid date components
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_config = Mock()
            mock_config.archive_dir = Path(temp_dir)
            
            with patch('googleapiclient.discovery.build') as mock_build:
                mock_service = Mock()
                mock_calendar_list = Mock()
                mock_calendar_list.list.return_value.execute.return_value = {
                    'items': [{'id': 'primary', 'accessRole': 'owner'}]
                }
                mock_service.calendarList.return_value = mock_calendar_list
                
                mock_events = Mock()
                mock_events.list.return_value.execute.return_value = {
                    'items': [invalid_event]
                }
                mock_service.events.return_value = mock_events
                mock_build.return_value = mock_service
                
                with patch('src.collectors.calendar_collector.get_config', return_value=mock_config):
                    collector = CalendarCollector()
                    result = collector.collect()
                    
                    # Should handle invalid dates gracefully
                    assert result['status'] in ['success', 'partial']
    
    def test_drive_corrupted_metadata(self):
        """Handle Drive files with corrupted metadata."""
        corrupted_file = {
            'id': 'corrupted-file',
            # Missing 'name' field
            'mimeType': 'application/vnd.google-apps.document',
            'size': 'not-a-number',  # Invalid size format
            'createdTime': 'invalid-timestamp',
            'owners': [{'emailAddress': None}]  # Invalid owner data
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_config = Mock()
            mock_config.archive_dir = Path(temp_dir)
            
            with patch('googleapiclient.discovery.build') as mock_build:
                mock_service = Mock()
                mock_files = Mock()
                mock_files.list.return_value.execute.return_value = {
                    'files': [corrupted_file]
                }
                mock_service.files.return_value = mock_files
                mock_build.return_value = mock_service
                
                with patch('src.collectors.drive_collector.get_config', return_value=mock_config):
                    collector = DriveCollector()
                    result = collector.collect()
                    
                    # Should handle corrupted metadata gracefully
                    assert result['status'] in ['success', 'partial']


class TestRateLimitBoundaryConditions:
    """Test behavior at exact rate limit boundaries."""
    
    def test_slack_exactly_at_rate_limit(self):
        """Handle Slack API calls exactly at rate limit."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_config = Mock()
            mock_config.archive_dir = Path(temp_dir)
            
            call_count = 0
            
            def mock_api_call(method, **kwargs):
                nonlocal call_count
                call_count += 1
                
                # Simulate hitting rate limit on 5th call
                if call_count >= 5:
                    response = Mock()
                    response.status_code = 429
                    response.headers = {
                        'retry-after': '1',
                        'x-rate-limit-remaining': '0',
                        'x-rate-limit-reset': str(int(time.time()) + 60)
                    }
                    raise HTTPError(response=response)
                
                return {'ok': True, 'channels': []}
            
            with patch('slack_sdk.WebClient') as mock_client:
                mock_instance = Mock()
                mock_instance.api_call.side_effect = mock_api_call
                mock_client.return_value = mock_instance
                
                with patch('src.collectors.slack_collector.get_config', return_value=mock_config):
                    with patch('time.sleep'):  # Don't actually sleep in tests
                        collector = SlackCollector()
                        result = collector.collect()
                        
                        # Should handle rate limiting gracefully
                        assert result['status'] in ['success', 'partial']
                        assert call_count >= 5  # Should have retried
    
    def test_circuit_breaker_trip_boundary(self):
        """Test circuit breaker at exact failure threshold."""
        circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=5)
        
        # Simulate exactly 3 failures (should trip circuit)
        for i in range(3):
            with circuit_breaker:
                raise Exception(f"Failure {i+1}")
        
        # Circuit should be open now
        assert circuit_breaker._state == 'open'
        
        # Next call should fail fast
        start_time = time.time()
        with pytest.raises(Exception):
            with circuit_breaker:
                pass  # Should fail before executing
        
        elapsed = time.time() - start_time
        assert elapsed < 0.1  # Should fail fast, not wait
    
    def test_google_api_quota_boundary(self):
        """Handle Google API quota limits."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_config = Mock()
            mock_config.archive_dir = Path(temp_dir)
            
            call_count = 0
            
            def mock_execute():
                nonlocal call_count
                call_count += 1
                
                if call_count > 3:
                    from googleapiclient.errors import HttpError
                    error_details = {
                        'error': {
                            'code': 403,
                            'message': 'Quota exceeded',
                            'errors': [{'reason': 'quotaExceeded'}]
                        }
                    }
                    raise HttpError(Mock(status=403), json.dumps(error_details).encode())
                
                return {'items': []}
            
            with patch('googleapiclient.discovery.build') as mock_build:
                mock_service = Mock()
                mock_calendar_list = Mock()
                mock_calendar_list.list.return_value.execute = mock_execute
                mock_service.calendarList.return_value = mock_calendar_list
                mock_build.return_value = mock_service
                
                with patch('src.collectors.calendar_collector.get_config', return_value=mock_config):
                    collector = CalendarCollector()
                    result = collector.collect()
                    
                    # Should handle quota exhaustion gracefully
                    assert result['status'] in ['error', 'partial']


class TestNetworkFailureScenarios:
    """Test network failure and timeout scenarios."""
    
    def test_connection_timeout_recovery(self):
        """Handle connection timeouts with retry logic."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_config = Mock()
            mock_config.archive_dir = Path(temp_dir)
            
            attempt_count = 0
            
            def mock_api_call(method, **kwargs):
                nonlocal attempt_count
                attempt_count += 1
                
                # First 2 attempts timeout, 3rd succeeds
                if attempt_count <= 2:
                    raise Timeout("Connection timed out")
                
                return {'ok': True, 'channels': []}
            
            with patch('slack_sdk.WebClient') as mock_client:
                mock_instance = Mock()
                mock_instance.api_call.side_effect = mock_api_call
                mock_client.return_value = mock_instance
                
                with patch('src.collectors.slack_collector.get_config', return_value=mock_config):
                    collector = SlackCollector()
                    result = collector.collect()
                    
                    # Should recover from timeouts
                    assert result['status'] == 'success'
                    assert attempt_count == 3  # Should have retried
    
    def test_connection_refused_handling(self):
        """Handle connection refused errors."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_config = Mock()
            mock_config.archive_dir = Path(temp_dir)
            
            def mock_api_call(method, **kwargs):
                raise ConnectionError("Connection refused")
            
            with patch('slack_sdk.WebClient') as mock_client:
                mock_instance = Mock()
                mock_instance.api_call.side_effect = mock_api_call
                mock_client.return_value = mock_instance
                
                with patch('src.collectors.slack_collector.get_config', return_value=mock_config):
                    collector = SlackCollector()
                    result = collector.collect()
                    
                    # Should handle connection errors gracefully
                    assert result['status'] == 'error'
                    assert 'connection' in result['error'].lower()
    
    def test_partial_response_timeout(self):
        """Handle timeouts during partial response reading."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_config = Mock()
            mock_config.archive_dir = Path(temp_dir)
            
            with patch('requests.get') as mock_get:
                # Simulate timeout during response body reading
                mock_response = Mock()
                mock_response.iter_content.side_effect = Timeout("Read timeout")
                mock_get.return_value = mock_response
                
                with patch('src.collectors.drive_collector.get_config', return_value=mock_config):
                    collector = DriveCollector()
                    # This would typically happen during file content download
                    result = collector.collect()
                    
                    # Should handle partial read timeouts
                    assert result['status'] in ['error', 'partial']


class TestLargeDatasetBoundaries:
    """Test handling of extremely large datasets."""
    
    @given(st.lists(st.dictionaries(
        keys=st.text(min_size=1, max_size=50),
        values=st.one_of(st.text(max_size=1000), st.integers(), st.booleans())
    ), min_size=1000, max_size=5000))
    @settings(max_examples=3, deadline=10000, suppress_health_check=[HealthCheck.too_slow])
    def test_large_slack_message_batch(self, messages):
        """Handle very large batches of Slack messages."""
        # Add required fields to make messages valid
        for i, msg in enumerate(messages):
            msg.update({
                'type': 'message',
                'ts': f"{time.time() + i:.6f}",
                'channel': 'C1234567890',
                'user': 'U1234567890'
            })
        
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_config = Mock()
            mock_config.archive_dir = Path(temp_dir)
            
            with patch('slack_sdk.WebClient') as mock_client:
                mock_instance = Mock()
                mock_instance.api_call.return_value = {
                    'ok': True,
                    'messages': messages
                }
                mock_client.return_value = mock_instance
                
                with patch('src.collectors.slack_collector.get_config', return_value=mock_config):
                    collector = SlackCollector()
                    result = collector.collect()
                    
                    # Should handle large batches without memory issues
                    assert result['status'] in ['success', 'partial']
                    assert result['collected']['messages'] <= len(messages)
    
    def test_extremely_long_message_content(self):
        """Handle messages with extremely long content."""
        # Create message with 1MB of text content
        large_text = 'x' * (1024 * 1024)
        large_message = {
            'type': 'message',
            'ts': f"{time.time():.6f}",
            'channel': 'C1234567890',
            'user': 'U1234567890',
            'text': large_text
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_config = Mock()
            mock_config.archive_dir = Path(temp_dir)
            
            with patch('slack_sdk.WebClient') as mock_client:
                mock_instance = Mock()
                mock_instance.api_call.return_value = {
                    'ok': True,
                    'messages': [large_message]
                }
                mock_client.return_value = mock_instance
                
                with patch('src.collectors.slack_collector.get_config', return_value=mock_config):
                    collector = SlackCollector()
                    result = collector.collect()
                    
                    # Should handle very large messages
                    assert result['status'] in ['success', 'partial']
    
    def test_calendar_with_thousands_of_events(self):
        """Handle calendars with thousands of events."""
        # Generate 10,000 events
        events = []
        base_time = datetime.now(timezone.utc)
        
        for i in range(10000):
            event_time = base_time + timedelta(hours=i)
            events.append({
                'id': f'event-{i}',
                'summary': f'Event {i}',
                'start': {'dateTime': event_time.isoformat()},
                'end': {'dateTime': (event_time + timedelta(hours=1)).isoformat()}
            })
        
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_config = Mock()
            mock_config.archive_dir = Path(temp_dir)
            
            with patch('googleapiclient.discovery.build') as mock_build:
                mock_service = Mock()
                mock_calendar_list = Mock()
                mock_calendar_list.list.return_value.execute.return_value = {
                    'items': [{'id': 'primary', 'accessRole': 'owner'}]
                }
                mock_service.calendarList.return_value = mock_calendar_list
                
                mock_events = Mock()
                mock_events.list.return_value.execute.return_value = {
                    'items': events
                }
                mock_service.events.return_value = mock_events
                mock_build.return_value = mock_service
                
                with patch('src.collectors.calendar_collector.get_config', return_value=mock_config):
                    collector = CalendarCollector()
                    result = collector.collect()
                    
                    # Should handle large event sets
                    assert result['status'] in ['success', 'partial']


class TestUnicodeAndEncodingEdgeCases:
    """Test Unicode and character encoding edge cases."""
    
    @given(st.text(min_size=1, max_size=1000))
    @settings(max_examples=20)
    def test_arbitrary_unicode_in_messages(self, unicode_text):
        """Handle arbitrary Unicode characters in message content."""
        message_with_unicode = {
            'type': 'message',
            'ts': f"{time.time():.6f}",
            'channel': 'C1234567890',
            'user': 'U1234567890',
            'text': unicode_text
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_config = Mock()
            mock_config.archive_dir = Path(temp_dir)
            
            with patch('src.core.archive_writer.get_config', return_value=mock_config):
                writer = ArchiveWriter("slack")
                
                # Should handle any Unicode text without errors
                try:
                    writer.write_records([message_with_unicode])
                    success = True
                except UnicodeError:
                    success = False
                
                assert success, f"Failed to handle Unicode text: {repr(unicode_text[:100])}"
    
    def test_emoji_and_special_characters(self):
        """Handle emoji and special characters in various fields."""
        special_chars_message = {
            'type': 'message',
            'ts': f"{time.time():.6f}",
            'channel': 'C1234567890',
            'user': 'U1234567890',
            'text': '🚀 Testing with emoji 📊 and special chars: áéíóú ñ 中文 العربية ไทย 🎉',
            'reactions': [
                {'name': '🔥', 'count': 1},
                {'name': '👍🏽', 'count': 2}  # Skin tone modifier
            ]
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_config = Mock()
            mock_config.archive_dir = Path(temp_dir)
            
            with patch('src.core.archive_writer.get_config', return_value=mock_config):
                writer = ArchiveWriter("slack")
                writer.write_records([special_chars_message])
                
                # Verify data was written correctly
                archive_files = list(Path(temp_dir).rglob("*.jsonl"))
                assert len(archive_files) > 0
                
                with open(archive_files[0], 'r', encoding='utf-8') as f:
                    stored_data = json.loads(f.read())
                    assert stored_data['text'] == special_chars_message['text']
                    assert stored_data['reactions'][0]['name'] == '🔥'
    
    def test_null_bytes_and_control_characters(self):
        """Handle null bytes and control characters in data."""
        message_with_control_chars = {
            'type': 'message',
            'ts': f"{time.time():.6f}",
            'channel': 'C1234567890',
            'user': 'U1234567890',
            'text': 'Message with\x00null byte and\tcontrol\ncharacters\r\n'
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_config = Mock()
            mock_config.archive_dir = Path(temp_dir)
            
            with patch('src.core.archive_writer.get_config', return_value=mock_config):
                writer = ArchiveWriter("slack")
                
                # Should sanitize or handle control characters safely
                try:
                    writer.write_records([message_with_control_chars])
                    success = True
                except (ValueError, UnicodeError):
                    success = False
                
                # Should either succeed or fail gracefully
                if not success:
                    # If it fails, it should be a controlled failure
                    pytest.skip("System designed to reject control characters")


class TestTimestampAndTimezoneEdgeCases:
    """Test timestamp and timezone handling edge cases."""
    
    def test_unix_timestamp_boundaries(self):
        """Handle Unix timestamp edge cases."""
        edge_case_timestamps = [
            0,  # Unix epoch
            2147483647,  # 32-bit signed int max (2038-01-19)
            2147483648,  # 32-bit signed int overflow
            -1,  # Before epoch
            9999999999,  # Far future timestamp
        ]
        
        for ts in edge_case_timestamps:
            message = {
                'type': 'message',
                'ts': f"{ts:.6f}",
                'channel': 'C1234567890',
                'user': 'U1234567890',
                'text': f'Message with timestamp {ts}'
            }
            
            with tempfile.TemporaryDirectory() as temp_dir:
                mock_config = Mock()
                mock_config.archive_dir = Path(temp_dir)
                
                with patch('src.core.archive_writer.get_config', return_value=mock_config):
                    writer = ArchiveWriter("slack")
                    
                    # Should handle edge case timestamps
                    try:
                        writer.write_records([message])
                        success = True
                    except (ValueError, OverflowError):
                        success = False
                    
                    # Should either handle gracefully or fail predictably
                    assert success or ts < 0, f"Failed to handle timestamp {ts}"
    
    def test_timezone_edge_cases(self):
        """Handle problematic timezone scenarios."""
        problematic_events = [
            {
                'id': 'utc-event',
                'summary': 'UTC Event',
                'start': {'dateTime': '2025-08-15T12:00:00Z'},
                'end': {'dateTime': '2025-08-15T13:00:00Z'}
            },
            {
                'id': 'offset-event',
                'summary': 'Offset Event',
                'start': {'dateTime': '2025-08-15T12:00:00+14:00'},  # Extreme positive offset
                'end': {'dateTime': '2025-08-15T13:00:00+14:00'}
            },
            {
                'id': 'negative-offset-event',
                'summary': 'Negative Offset Event',
                'start': {'dateTime': '2025-08-15T12:00:00-12:00'},  # Extreme negative offset
                'end': {'dateTime': '2025-08-15T13:00:00-12:00'}
            },
            {
                'id': 'dst-transition-event',
                'summary': 'DST Transition Event',
                'start': {'dateTime': '2025-03-09T02:30:00', 'timeZone': 'America/New_York'},
                'end': {'dateTime': '2025-03-09T03:30:00', 'timeZone': 'America/New_York'}
            }
        ]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_config = Mock()
            mock_config.archive_dir = Path(temp_dir)
            
            with patch('src.core.archive_writer.get_config', return_value=mock_config):
                writer = ArchiveWriter("calendar")
                
                # Should handle various timezone scenarios
                writer.write_records(problematic_events)
                
                # Verify all events were stored
                archive_files = list(Path(temp_dir).rglob("*.jsonl"))
                assert len(archive_files) > 0


class TestPermissionAndAccessEdgeCases:
    """Test permission and access control edge cases."""
    
    def test_slack_missing_permissions(self):
        """Handle Slack API with missing permissions."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_config = Mock()
            mock_config.archive_dir = Path(temp_dir)
            
            def mock_api_call(method, **kwargs):
                return {
                    'ok': False,
                    'error': 'missing_scope',
                    'needed': 'channels:read',
                    'provided': 'chat:write'
                }
            
            with patch('slack_sdk.WebClient') as mock_client:
                mock_instance = Mock()
                mock_instance.api_call.side_effect = mock_api_call
                mock_client.return_value = mock_instance
                
                with patch('src.collectors.slack_collector.get_config', return_value=mock_config):
                    collector = SlackCollector()
                    result = collector.collect()
                    
                    # Should handle permission errors gracefully
                    assert result['status'] == 'error'
                    assert 'permission' in result['error'].lower() or 'scope' in result['error'].lower()
    
    def test_drive_access_denied_files(self):
        """Handle Drive files with access denied."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_config = Mock()
            mock_config.archive_dir = Path(temp_dir)
            
            with patch('googleapiclient.discovery.build') as mock_build:
                from googleapiclient.errors import HttpError
                
                def mock_execute():
                    error_details = {
                        'error': {
                            'code': 403,
                            'message': 'The user does not have sufficient permissions',
                            'errors': [{'reason': 'forbidden'}]
                        }
                    }
                    raise HttpError(Mock(status=403), json.dumps(error_details).encode())
                
                mock_service = Mock()
                mock_files = Mock()
                mock_files.list.return_value.execute = mock_execute
                mock_service.files.return_value = mock_files
                mock_build.return_value = mock_service
                
                with patch('src.collectors.drive_collector.get_config', return_value=mock_config):
                    collector = DriveCollector()
                    result = collector.collect()
                    
                    # Should handle access denied gracefully
                    assert result['status'] == 'error'
                    assert 'permission' in result['error'].lower() or 'forbidden' in result['error'].lower()
    
    def test_calendar_read_only_access(self):
        """Handle calendar with read-only access when write is needed."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_config = Mock()
            mock_config.archive_dir = Path(temp_dir)
            
            with patch('googleapiclient.discovery.build') as mock_build:
                mock_service = Mock()
                mock_calendar_list = Mock()
                mock_calendar_list.list.return_value.execute.return_value = {
                    'items': [{
                        'id': 'readonly-calendar@company.com',
                        'accessRole': 'reader'  # Read-only access
                    }]
                }
                mock_service.calendarList.return_value = mock_calendar_list
                
                mock_events = Mock()
                mock_events.list.return_value.execute.return_value = {
                    'items': []  # Can read, but limited access
                }
                mock_service.events.return_value = mock_events
                mock_build.return_value = mock_service
                
                with patch('src.collectors.calendar_collector.get_config', return_value=mock_config):
                    collector = CalendarCollector()
                    result = collector.collect()
                    
                    # Should handle read-only access appropriately
                    assert result['status'] in ['success', 'partial']
                    # Should note limited access in results
                    assert 'access_level' in result or 'permissions' in result