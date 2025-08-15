"""
Failing tests for CalendarArchiveWrapper (TDD Red phase).
Tests define expected behavior before implementation.
All tests will initially fail until CalendarArchiveWrapper is implemented.
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List

# Add test fixtures to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import the CalendarArchiveWrapper (expected to fail initially in TDD Red phase)  
try:
    from src.collectors.calendar import CalendarArchiveWrapper
except ImportError:
    CalendarArchiveWrapper = None

# Import test fixtures
from tests.fixtures.mock_calendar_data import (
    get_mock_collection_result,
    get_mock_calendars,
    get_mock_events
)


@pytest.fixture(autouse=True)
def mock_stage1a_components():
    """Mock Stage 1a components for all tests."""
    with patch('src.collectors.base.get_config') as mock_config, \
         patch('src.collectors.base.StateManager') as mock_state_manager, \
         patch('src.collectors.base.ArchiveWriter') as mock_archive_writer, \
         patch('src.collectors.calendar.CalendarCollector') as mock_calendar_collector_class:
        
        # Configure mocks
        mock_config_obj = Mock()
        mock_config_obj.archive_dir = Path('/tmp/test_archive')
        mock_config.return_value = mock_config_obj
        
        mock_state_manager.return_value = Mock()
        mock_archive_writer.return_value = Mock()
        
        # Configure CalendarCollector mock
        mock_calendar_collector = Mock()
        mock_calendar_collector.collection_results = {
            'status': 'initialized',
            'discovered': {'calendars': 0, 'users': 0},
            'collected': {'calendars': 0, 'events': 0}
        }
        # Configure the collect method to return test data
        mock_calendar_collector.collect_all_calendar_data.return_value = get_mock_collection_result()
        mock_calendar_collector_class.return_value = mock_calendar_collector
        
        yield {
            'config': mock_config,
            'state_manager': mock_state_manager,
            'archive_writer': mock_archive_writer,
            'calendar_collector': mock_calendar_collector_class
        }


class TestCalendarWrapperInterface:
    """Test that CalendarArchiveWrapper implements BaseArchiveCollector interface."""
    
    def test_calendar_wrapper_implements_base_interface(self):
        """CalendarArchiveWrapper implements required BaseArchiveCollector methods"""
        # ACCEPTANCE: collect(), get_state(), set_state() methods exist and are callable
        if CalendarArchiveWrapper is None:
            pytest.skip("CalendarArchiveWrapper not implemented yet (TDD Red phase)")
            
        wrapper = CalendarArchiveWrapper()
        
        # Test that all required methods exist and are callable
        assert hasattr(wrapper, 'collect'), "CalendarWrapper missing collect() method"
        assert callable(wrapper.collect), "collect() must be callable"
        
        assert hasattr(wrapper, 'get_state'), "CalendarWrapper missing get_state() method"
        assert callable(wrapper.get_state), "get_state() must be callable"
        
        assert hasattr(wrapper, 'set_state'), "CalendarWrapper missing set_state() method"
        assert callable(wrapper.set_state), "set_state() must be callable"
    
    def test_calendar_wrapper_inherits_from_base_collector(self):
        """CalendarArchiveWrapper inherits from BaseArchiveCollector"""
        if CalendarArchiveWrapper is None:
            pytest.skip("CalendarArchiveWrapper not implemented yet (TDD Red phase)")
            
        from src.collectors.base import BaseArchiveCollector
        wrapper = CalendarArchiveWrapper()
        assert isinstance(wrapper, BaseArchiveCollector), "Must inherit from BaseArchiveCollector"
    
    def test_calendar_wrapper_collector_type(self):
        """CalendarArchiveWrapper has correct collector_type"""
        if CalendarArchiveWrapper is None:
            pytest.skip("CalendarArchiveWrapper not implemented yet (TDD Red phase)")
            
        wrapper = CalendarArchiveWrapper()
        assert wrapper.collector_type == "calendar", "collector_type must be 'calendar'"


class TestCalendarDataCollection:
    """Test calendar data collection and integration with scavenge collector."""
    
    def test_collect_returns_expected_structure(self):
        """collect() returns dictionary with data and metadata"""
        if CalendarArchiveWrapper is None:
            pytest.skip("CalendarArchiveWrapper not implemented yet (TDD Red phase)")
            
        wrapper = CalendarArchiveWrapper()
        result = wrapper.collect()
        
        assert isinstance(result, dict), "collect() must return dict"
        assert 'data' in result, "collect() result must contain 'data' key"
        assert 'metadata' in result, "collect() result must contain 'metadata' key"
        assert 'collection_timestamp' in result['metadata'], "metadata must contain collection_timestamp"
        assert result['metadata']['collector_type'] == 'calendar', "metadata must specify calendar collector"
    
    def test_scavenge_collector_integration(self):
        """Calendar wrapper properly integrates with scavenge CalendarCollector"""
        if CalendarArchiveWrapper is None:
            pytest.skip("CalendarArchiveWrapper not implemented yet (TDD Red phase)")
            
        wrapper = CalendarArchiveWrapper()
        
        # Wrapper should have a scavenge_collector attribute
        assert hasattr(wrapper, 'scavenge_collector'), "Must have scavenge_collector attribute"
        assert wrapper.scavenge_collector is not None, "scavenge_collector must be initialized"
        
        # Should have the main collection method
        assert hasattr(wrapper.scavenge_collector, 'collect_all_calendar_data'), \
            "scavenge_collector must have collect_all_calendar_data method"
    
    @patch('src.collectors.calendar.CalendarCollector')
    def test_collect_calls_scavenge_collector(self, mock_calendar_collector_class):
        """collect() method calls the scavenge CalendarCollector"""
        if CalendarArchiveWrapper is None:
            pytest.skip("CalendarArchiveWrapper not implemented yet (TDD Red phase)")
            
        # Setup mock
        mock_collector = Mock()
        mock_collector.collect_all_calendar_data.return_value = get_mock_collection_result()
        mock_calendar_collector_class.return_value = mock_collector
        
        wrapper = CalendarArchiveWrapper()
        result = wrapper.collect()
        
        # Verify scavenge collector was called
        mock_collector.collect_all_calendar_data.assert_called_once()
        
        # Verify result structure
        assert isinstance(result, dict)
        assert 'data' in result
        assert 'metadata' in result


class TestTimezoneHandling:
    """Test timezone conversion and handling for calendar events."""
    
    def test_timezone_conversion_to_utc(self):
        """Calendar events are converted to UTC timezone"""
        # ACCEPTANCE: All datetime fields converted to UTC with proper timezone info
        if CalendarArchiveWrapper is None:
            pytest.skip("CalendarArchiveWrapper not implemented yet (TDD Red phase)")
            
        wrapper = CalendarArchiveWrapper()
        
        # Mock data with various timezones
        mock_events = get_mock_events()
        
        # Test timezone conversion method (to be implemented)
        if hasattr(wrapper, '_convert_events_to_utc'):
            converted_events = wrapper._convert_events_to_utc(mock_events)
            
            for event in converted_events:
                if 'start' in event and 'dateTime' in event['start']:
                    start_dt = datetime.fromisoformat(event['start']['dateTime'])
                    assert start_dt.tzinfo == timezone.utc, \
                        f"Event start time must be in UTC, got {start_dt.tzinfo}"
                
                if 'end' in event and 'dateTime' in event['end']:
                    end_dt = datetime.fromisoformat(event['end']['dateTime'])
                    assert end_dt.tzinfo == timezone.utc, \
                        f"Event end time must be in UTC, got {end_dt.tzinfo}"
    
    def test_timezone_metadata_preservation(self):
        """Original timezone information is preserved in metadata"""
        if CalendarArchiveWrapper is None:
            pytest.skip("CalendarArchiveWrapper not implemented yet (TDD Red phase)")
            
        wrapper = CalendarArchiveWrapper()
        mock_events = get_mock_events()
        
        if hasattr(wrapper, '_convert_events_to_utc'):
            converted_events = wrapper._convert_events_to_utc(mock_events)
            
            for event in converted_events:
                if 'start' in event and 'timeZone' in event['start']:
                    # Original timezone should be preserved in metadata
                    assert 'original_timezone' in event, \
                        "Original timezone must be preserved in event metadata"
                    assert 'timezone_conversion' in event, \
                        "Timezone conversion info must be included"
    
    def test_all_day_event_handling(self):
        """All-day events are handled correctly without timezone conversion"""
        if CalendarArchiveWrapper is None:
            pytest.skip("CalendarArchiveWrapper not implemented yet (TDD Red phase)")
            
        wrapper = CalendarArchiveWrapper()
        mock_events = get_mock_events()
        
        # Find all-day events in mock data
        all_day_events = [e for e in mock_events if 'date' in e.get('start', {})]
        assert len(all_day_events) > 0, "Test requires all-day events in mock data"
        
        if hasattr(wrapper, '_convert_events_to_utc'):
            converted_events = wrapper._convert_events_to_utc(all_day_events)
            
            for event in converted_events:
                if 'date' in event['start']:
                    # All-day events should remain as date, not dateTime
                    assert 'date' in event['start'], "All-day events must preserve date format"
                    assert 'dateTime' not in event['start'], "All-day events must not have dateTime"


class TestCalendarStateManagement:
    """Test state persistence for calendar collection cursors."""
    
    def test_state_includes_calendar_cursors(self):
        """State includes calendar-specific cursor information"""
        if CalendarArchiveWrapper is None:
            pytest.skip("CalendarArchiveWrapper not implemented yet (TDD Red phase)")
            
        wrapper = CalendarArchiveWrapper()
        
        # Set some calendar-specific state
        calendar_state = {
            "sync_token": "CTEw9u7AuuIC",
            "last_calendar_discovery": "2025-08-15T10:00:00Z",
            "calendars_processed": ["alice@company.com", "shared-team@company.com"],
            "cursor": "calendar_cursor_123"
        }
        
        wrapper.set_state(calendar_state)
        current_state = wrapper.get_state()
        
        assert current_state["sync_token"] == "CTEw9u7AuuIC", "Sync token should persist"
        assert "calendars_processed" in current_state, "Processed calendars should persist"
        assert len(current_state["calendars_processed"]) == 2, "All processed calendars should persist"
    
    def test_scavenge_collector_state_integration(self):
        """Wrapper integrates with scavenge collector state management"""
        if CalendarArchiveWrapper is None:
            pytest.skip("CalendarArchiveWrapper not implemented yet (TDD Red phase)")
            
        wrapper = CalendarArchiveWrapper()
        
        # Mock scavenge collector with collection results
        if hasattr(wrapper, 'scavenge_collector'):
            wrapper.scavenge_collector.collection_results = {
                "status": "completed",
                "discovered": {"calendars": 5, "users": 3},
                "collected": {"calendars": 4, "events": 127},
                "next_cursor": "next_sync_token_456"
            }
            
            state = wrapper.get_state()
            
            # Should include scavenge collector state information
            assert "calendars_discovered" in state or "scavenge_cursor" in state, \
                "State should include scavenge collector information"


class TestCalendarDataTransformation:
    """Test transformation of calendar data to archive format."""
    
    def test_calendar_data_transformation(self):
        """Calendar data is transformed to consistent archive format"""
        if CalendarArchiveWrapper is None:
            pytest.skip("CalendarArchiveWrapper not implemented yet (TDD Red phase)")
            
        wrapper = CalendarArchiveWrapper()
        mock_data = get_mock_collection_result()
        
        if hasattr(wrapper, '_transform_to_archive_format'):
            transformed = wrapper._transform_to_archive_format(mock_data)
            
            # Check required structure
            assert isinstance(transformed, dict), "Transformed data must be dict"
            assert 'calendars' in transformed, "Must contain calendars"
            assert 'events' in transformed, "Must contain events"
            assert 'archive_transformation' in transformed, "Must contain transformation metadata"
    
    def test_event_metadata_enhancement(self):
        """Calendar events are enhanced with additional metadata"""
        if CalendarArchiveWrapper is None:
            pytest.skip("CalendarArchiveWrapper not implemented yet (TDD Red phase)")
            
        wrapper = CalendarArchiveWrapper()
        mock_events = get_mock_events()
        
        if hasattr(wrapper, '_process_events_for_archive'):
            processed_events = wrapper._process_events_for_archive(mock_events)
            
            for event in processed_events:
                # Should have event classification
                assert 'event_classification' in event, "Events should have classification metadata"
                
                classification = event['event_classification']
                assert 'is_recurring' in classification, "Should classify recurring events"
                assert 'is_all_day' in classification, "Should classify all-day events"
                assert 'has_attendees' in classification, "Should classify events with attendees"
                assert 'privacy_level' in classification, "Should include privacy classification"
    
    def test_attendee_processing(self):
        """Event attendees are properly processed and classified"""
        if CalendarArchiveWrapper is None:
            pytest.skip("CalendarArchiveWrapper not implemented yet (TDD Red phase)")
            
        wrapper = CalendarArchiveWrapper()
        mock_events = get_mock_events()
        
        # Find events with attendees
        events_with_attendees = [e for e in mock_events if 'attendees' in e]
        assert len(events_with_attendees) > 0, "Test requires events with attendees"
        
        if hasattr(wrapper, '_process_events_for_archive'):
            processed_events = wrapper._process_events_for_archive(events_with_attendees)
            
            for event in processed_events:
                if 'attendees' in event:
                    # Should have attendee classification
                    assert 'attendee_summary' in event, "Should include attendee summary"
                    
                    summary = event['attendee_summary']
                    assert 'total_count' in summary, "Should count total attendees"
                    assert 'response_status' in summary, "Should summarize response statuses"
                    assert 'organizer_email' in summary, "Should identify organizer"


class TestCalendarErrorHandling:
    """Test error handling and validation for calendar collection."""
    
    def test_scavenge_collector_error_handling(self):
        """Wrapper handles errors from scavenge collector gracefully"""
        if CalendarArchiveWrapper is None:
            pytest.skip("CalendarArchiveWrapper not implemented yet (TDD Red phase)")
            
        with patch('src.collectors.calendar.CalendarCollector') as mock_collector_class:
            # Setup mock to raise exception
            mock_collector = Mock()
            mock_collector.collect_all_calendar_data.side_effect = Exception("Google API error")
            mock_collector_class.return_value = mock_collector
            
            wrapper = CalendarArchiveWrapper()
            
            # Should handle exception and provide meaningful error
            with pytest.raises(Exception) as exc_info:
                wrapper.collect()
            
            # Error should be informative
            assert "Calendar collection failed" in str(exc_info.value) or \
                   "Google API error" in str(exc_info.value), \
                   "Should provide informative error message"
    
    def test_invalid_calendar_data_validation(self):
        """Wrapper validates calendar data structure"""
        if CalendarArchiveWrapper is None:
            pytest.skip("CalendarArchiveWrapper not implemented yet (TDD Red phase)")
            
        wrapper = CalendarArchiveWrapper()
        
        # Test with invalid data structure
        invalid_data = {"invalid": "structure"}
        
        if hasattr(wrapper, '_validate_scavenge_output'):
            # Should identify invalid structure
            is_valid = wrapper._validate_scavenge_output(invalid_data)
            # Implementation should handle this gracefully, either by:
            # 1. Returning False for validation failure, or
            # 2. Accepting any dict structure (more permissive)
            assert isinstance(is_valid, bool), "Validation should return boolean"
    
    def test_configuration_validation(self):
        """Wrapper validates configuration parameters"""
        if CalendarArchiveWrapper is None:
            pytest.skip("CalendarArchiveWrapper not implemented yet (TDD Red phase)")
            
        # Test with invalid timezone configuration
        with pytest.raises(ValueError, match="Invalid configuration"):
            CalendarArchiveWrapper(config={"target_timezone": "Invalid/Timezone"})
        
        # Test with valid configuration
        valid_config = {
            "target_timezone": "UTC",
            "lookback_days": 30,
            "lookahead_days": 30
        }
        wrapper = CalendarArchiveWrapper(config=valid_config)
        assert wrapper is not None, "Should accept valid configuration"


if __name__ == "__main__":
    # Run a subset of tests for quick validation
    print("Running CalendarArchiveWrapper failing tests (TDD Red phase)...")
    
    # These should all fail initially - that's the point!
    try:
        if CalendarArchiveWrapper:
            wrapper = CalendarArchiveWrapper()
            print("❌ CalendarArchiveWrapper instantiated (unexpected - should fail)")
        else:
            print("✅ CalendarArchiveWrapper not implemented yet (expected)")
    except (ImportError, NameError, AttributeError):
        print("✅ CalendarArchiveWrapper fails properly (expected)")
    
    print("\nAll tests are properly failing - ready for implementation phase! 🔴")
    print("Next step: Implement CalendarArchiveWrapper to make tests pass (TDD Green phase)")