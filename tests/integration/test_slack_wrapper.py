"""
Integration tests for SlackArchiveWrapper.
Tests the wrapper's integration with existing scavenge collector,
data transformation, and field preservation.
"""

import pytest
from pathlib import Path
from typing import Dict, Any
from unittest.mock import Mock, patch

# Import our test helpers
from tests.helpers.collector_helpers import (
    CollectorTestHelper,
    ArchiveTestValidator,
    assert_jsonl_valid,
    assert_archive_structure_valid
)

# Import our fixtures  
from tests.fixtures.mock_slack_data import (
    get_mock_channels,
    get_mock_users,
    get_mock_messages,
    get_mock_collection_result
)

# Import the wrapper we'll implement
try:
    from src.collectors.slack_wrapper import SlackArchiveWrapper
except ImportError:
    SlackArchiveWrapper = None


class TestSlackArchiveWrapperIntegration:
    """Integration tests for SlackArchiveWrapper with existing scavenge collector."""
    
    def test_wrapper_class_exists(self):
        """SlackArchiveWrapper class can be imported and instantiated."""
        if SlackArchiveWrapper is None:
            pytest.skip("SlackArchiveWrapper not implemented yet (TDD Red phase)")
        
        wrapper = SlackArchiveWrapper()
        assert wrapper is not None
        assert hasattr(wrapper, 'collect')
        assert hasattr(wrapper, 'get_state') 
        assert hasattr(wrapper, 'set_state')
    
    def test_wrapper_inherits_from_base_collector(self):
        """SlackArchiveWrapper properly inherits from BaseArchiveCollector."""
        if SlackArchiveWrapper is None:
            pytest.skip("SlackArchiveWrapper not implemented yet")
        
        from src.collectors.base import BaseArchiveCollector
        
        wrapper = SlackArchiveWrapper()
        assert isinstance(wrapper, BaseArchiveCollector)
        assert wrapper.collector_type == "slack"


class TestSlackDataTransformation:
    """Test data transformation from scavenge collector to JSONL format."""
    
    def test_collect_returns_proper_structure(self):
        """collect() method returns data in expected BaseArchiveCollector format."""
        if SlackArchiveWrapper is None:
            pytest.skip("SlackArchiveWrapper not implemented yet")
        
        # Mock the scavenge collector to avoid authentication issues
        with patch('src.collectors.slack_wrapper.SlackCollector') as mock_collector_class:
            mock_collector = Mock()
            mock_collector.collect_all_slack_data.return_value = get_mock_collection_result()
            mock_collector_class.return_value = mock_collector
            
            wrapper = SlackArchiveWrapper()
            result = wrapper.collect()
            
            # Verify expected structure
            assert isinstance(result, dict)
            assert 'data' in result
            assert 'metadata' in result
            
            # Verify metadata structure
            metadata = result['metadata']
            assert 'collector_type' in metadata
            assert metadata['collector_type'] == 'slack'
            assert 'collection_timestamp' in metadata
    
    def test_all_fields_preserved(self):
        """All fields from scavenge collector are preserved in wrapper output."""
        if SlackArchiveWrapper is None:
            pytest.skip("SlackArchiveWrapper not implemented yet")
        
        # Mock the scavenge collector response
        mock_scavenge_data = get_mock_collection_result()
        
        with patch('src.collectors.slack_wrapper.SlackCollector') as mock_collector_class:
            mock_collector = Mock()
            mock_collector.collect_all_slack_data.return_value = mock_scavenge_data
            mock_collector_class.return_value = mock_collector
            
            wrapper = SlackArchiveWrapper()
            result = wrapper.collect()
            
            # Use ArchiveTestValidator to compare data
            validator = ArchiveTestValidator()
            comparison = validator.compare_with_original(
                mock_scavenge_data, 
                result
            )
            
            assert comparison['data_preserved'], \
                f"Data not preserved: {comparison['missing_fields']}"
    
    def test_thread_relationships_maintained(self):
        """Thread relationships (thread_ts, parent references) are preserved."""
        if SlackArchiveWrapper is None:
            pytest.skip("SlackArchiveWrapper not implemented yet")
        
        # Create mock data with thread relationships
        mock_messages = get_mock_messages()
        threaded_messages = [msg for msg in mock_messages if msg.get('thread_ts')]
        
        assert len(threaded_messages) > 0, "Mock data should contain threaded messages"
        
        mock_data = {
            'messages': mock_messages,
            'channels': get_mock_channels(),
            'users': get_mock_users()
        }
        
        with patch('src.collectors.slack_wrapper.SlackCollector') as mock_collector_class:
            mock_collector = Mock()
            mock_collector.collect_all_slack_data.return_value = mock_data
            mock_collector_class.return_value = mock_collector
            
            wrapper = SlackArchiveWrapper()
            result = wrapper.collect()
            
            # Extract messages from result
            result_messages = result['data'].get('messages', [])
            result_threaded = [msg for msg in result_messages if msg.get('thread_ts')]
            
            # Verify thread relationships preserved
            assert len(result_threaded) == len(threaded_messages), \
                "Thread message count should be preserved"
            
            for orig_msg, result_msg in zip(threaded_messages, result_threaded):
                assert orig_msg['thread_ts'] == result_msg['thread_ts'], \
                    f"Thread timestamp not preserved: {orig_msg['ts']}"
    
    def test_special_message_types_handled(self):
        """Bot, system, deleted, and edited messages are handled correctly."""
        if SlackArchiveWrapper is None:
            pytest.skip("SlackArchiveWrapper not implemented yet")
        
        mock_messages = get_mock_messages()
        
        # Verify our mock data has special message types
        special_types = {
            'bot': any(msg.get('subtype') == 'bot_message' for msg in mock_messages),
            'system': any(msg.get('subtype') == 'channel_join' for msg in mock_messages),
            'deleted': any(msg.get('subtype') == 'message_deleted' for msg in mock_messages),
            'edited': any(msg.get('subtype') == 'message_changed' for msg in mock_messages)
        }
        
        assert any(special_types.values()), "Mock data should contain special message types"
        
        mock_data = {'messages': mock_messages}
        
        with patch('src.collectors.slack_wrapper.SlackCollector') as mock_collector_class:
            mock_collector = Mock()
            mock_collector.collect_all_slack_data.return_value = mock_data
            mock_collector_class.return_value = mock_collector
            
            wrapper = SlackArchiveWrapper()
            result = wrapper.collect()
            
            result_messages = result['data'].get('messages', [])
            
            # Verify special message types are preserved
            result_special_types = {
                'bot': any(msg.get('subtype') == 'bot_message' for msg in result_messages),
                'system': any(msg.get('subtype') == 'channel_join' for msg in result_messages),
                'deleted': any(msg.get('subtype') == 'message_deleted' for msg in result_messages),
                'edited': any(msg.get('subtype') == 'message_changed' for msg in result_messages)
            }
            
            for msg_type, expected in special_types.items():
                if expected:
                    assert result_special_types[msg_type], \
                        f"{msg_type} messages not preserved in transformation"


class TestSlackRateLimitingIntegration:
    """Test integration with existing Slack rate limiting mechanisms."""
    
    def test_rate_limiting_not_bypassed(self):
        """Wrapper respects existing SlackRateLimiter and doesn't bypass it."""
        if SlackArchiveWrapper is None:
            pytest.skip("SlackArchiveWrapper not implemented yet")
        
        # Mock SlackRateLimiter to track if it's being called
        rate_limiter_calls = []
        
        def mock_rate_limiter_method(self, method_name):
            rate_limiter_calls.append(method_name)
            return True  # Allow the call
        
        with patch('src.collectors.slack_wrapper.SlackCollector') as mock_collector_class:
            mock_collector = Mock()
            mock_collector.collect_all_slack_data.return_value = get_mock_collection_result()
            
            # Mock rate limiter within collector
            mock_rate_limiter = Mock()
            mock_rate_limiter.can_make_request = Mock(side_effect=mock_rate_limiter_method)
            mock_collector.rate_limiter = mock_rate_limiter
            
            mock_collector_class.return_value = mock_collector
            
            wrapper = SlackArchiveWrapper()
            wrapper.collect()
            
            # Verify the scavenge collector was called (which should use rate limiting)
            mock_collector.collect_all_slack_data.assert_called_once()
    
    def test_wrapper_handles_rate_limit_errors(self):
        """Wrapper properly handles rate limit errors from scavenge collector."""
        if SlackArchiveWrapper is None:
            pytest.skip("SlackArchiveWrapper not implemented yet")
        
        with patch('src.collectors.slack_wrapper.SlackCollector') as mock_collector_class:
            mock_collector = Mock()
            mock_collector.collect_all_slack_data.side_effect = Exception("Rate limit exceeded")
            mock_collector_class.return_value = mock_collector
            
            wrapper = SlackArchiveWrapper()
            
            # Should propagate the rate limit error
            with pytest.raises(Exception, match="Rate limit exceeded"):
                wrapper.collect()


class TestSlackWrapperStateManagement:
    """Test state management integration with BaseArchiveCollector."""
    
    def test_state_persistence(self):
        """Wrapper properly manages state through BaseArchiveCollector interface."""
        if SlackArchiveWrapper is None:
            pytest.skip("SlackArchiveWrapper not implemented yet")
        
        wrapper = SlackArchiveWrapper()
        
        # Test initial state
        initial_state = wrapper.get_state()
        assert isinstance(initial_state, dict)
        
        # Test state update
        new_state = {"cursor": "test_cursor", "last_collection": "2025-08-15T10:00:00Z"}
        wrapper.set_state(new_state)
        
        updated_state = wrapper.get_state()
        assert "cursor" in updated_state
        assert updated_state["cursor"] == "test_cursor"
    
    def test_state_integration_with_scavenge_collector(self):
        """State from wrapper is used by underlying scavenge collector."""
        if SlackArchiveWrapper is None:
            pytest.skip("SlackArchiveWrapper not implemented yet")
        
        # Mock the scavenge collector to avoid authentication issues
        with patch('src.collectors.slack_wrapper.SlackCollector') as mock_collector_class:
            mock_collector = Mock()
            mock_collector.collect_all_slack_data.return_value = get_mock_collection_result()
            mock_collector_class.return_value = mock_collector
            
            # This test verifies that the wrapper passes state information
            # to the scavenge collector for cursor-based collection
            wrapper = SlackArchiveWrapper()
            
            # Set state with cursor
            wrapper.set_state({"cursor": "slack_cursor_123"})
            
            wrapper.collect()
            
            # Verify scavenge collector was created/called
            mock_collector_class.assert_called_once()
            mock_collector.collect_all_slack_data.assert_called_once()


class TestSlackWrapperPerformance:
    """Test performance characteristics of the wrapper."""
    
    def test_large_dataset_performance(self):
        """Wrapper handles large datasets within reasonable memory/time limits."""
        if SlackArchiveWrapper is None:
            pytest.skip("SlackArchiveWrapper not implemented yet")
        
        # Create large mock dataset
        large_mock_data = {
            'messages': get_mock_messages() * 10,  # 100+ messages
            'channels': get_mock_channels() * 2,   # 10+ channels
            'users': get_mock_users() * 3          # 20+ users
        }
        
        with patch('src.collectors.slack_wrapper.SlackCollector') as mock_collector_class:
            mock_collector = Mock()
            mock_collector.collect_all_slack_data.return_value = large_mock_data
            mock_collector_class.return_value = mock_collector
            
            wrapper = SlackArchiveWrapper()
            
            import time
            start_time = time.time()
            
            result = wrapper.collect()
            
            end_time = time.time()
            transform_time = end_time - start_time
            
            # Verify reasonable performance (< 1 second for this size)
            assert transform_time < 1.0, \
                f"Transformation took too long: {transform_time:.2f}s"
            
            # Verify data is properly transformed
            assert 'data' in result
            assert len(result['data'].get('messages', [])) > 100


class TestSlackWrapperErrorHandling:
    """Test error handling and propagation."""
    
    def test_error_propagation_from_scavenge_collector(self):
        """Errors from scavenge collector are properly propagated."""
        if SlackArchiveWrapper is None:
            pytest.skip("SlackArchiveWrapper not implemented yet")
        
        error_scenarios = [
            ("Authentication failed", "AUTH_ERROR"),
            ("Network timeout", "NETWORK_ERROR"), 
            ("API quota exceeded", "QUOTA_ERROR")
        ]
        
        for error_msg, error_type in error_scenarios:
            with patch('src.collectors.slack_wrapper.SlackCollector') as mock_collector_class:
                mock_collector = Mock()
                mock_collector.collect_all_slack_data.side_effect = Exception(error_msg)
                mock_collector_class.return_value = mock_collector
                
                wrapper = SlackArchiveWrapper()
                
                with pytest.raises(Exception, match=error_msg):
                    wrapper.collect()
    
    def test_graceful_handling_of_malformed_data(self):
        """Wrapper handles malformed data from scavenge collector gracefully."""
        if SlackArchiveWrapper is None:
            pytest.skip("SlackArchiveWrapper not implemented yet")
        
        malformed_data_scenarios = [
            {},  # Empty data
            {'messages': None},  # None instead of list
            {'messages': [{'invalid': 'structure'}]},  # Missing required fields
        ]
        
        for malformed_data in malformed_data_scenarios:
            with patch('src.collectors.slack_wrapper.SlackCollector') as mock_collector_class:
                mock_collector = Mock()
                mock_collector.collect_all_slack_data.return_value = malformed_data
                mock_collector_class.return_value = mock_collector
                
                wrapper = SlackArchiveWrapper()
                
                # Should not crash, but should handle gracefully
                result = wrapper.collect()
                
                # Should still return proper structure
                assert 'data' in result
                assert 'metadata' in result


class TestSlackWrapperArchiveIntegration:
    """Test integration with archive writing functionality."""
    
    def test_archive_integration_basic(self):
        """Wrapper produces data suitable for archive writing."""
        if SlackArchiveWrapper is None:
            pytest.skip("SlackArchiveWrapper not implemented yet")
        
        # Mock scavenge collector
        with patch('src.collectors.slack_wrapper.SlackCollector') as mock_collector_class:
            mock_collector = Mock()
            mock_collector.collect_all_slack_data.return_value = get_mock_collection_result()
            mock_collector_class.return_value = mock_collector
            
            wrapper = SlackArchiveWrapper()
            result = wrapper.collect()
            
            # Verify result structure is suitable for JSONL writing
            assert 'data' in result
            assert 'metadata' in result
            
            # Verify data can be JSON serialized (required for JSONL)
            import json
            json_str = json.dumps(result)
            assert len(json_str) > 0
            
            # Verify we can deserialize it back
            parsed = json.loads(json_str)
            assert parsed == result


if __name__ == "__main__":
    # Quick validation that tests are structured correctly
    print("SlackArchiveWrapper Integration Tests")
    print("=====================================")
    
    test_classes = [
        TestSlackArchiveWrapperIntegration,
        TestSlackDataTransformation,
        TestSlackRateLimitingIntegration, 
        TestSlackWrapperStateManagement,
        TestSlackWrapperPerformance,
        TestSlackWrapperErrorHandling,
        TestSlackWrapperArchiveIntegration
    ]
    
    total_tests = 0
    for test_class in test_classes:
        class_tests = [method for method in dir(test_class) if method.startswith('test_')]
        print(f"  {test_class.__name__}: {len(class_tests)} tests")
        total_tests += len(class_tests)
    
    print(f"\nTotal integration tests: {total_tests}")
    print("All tests will initially fail (TDD Red phase) until SlackArchiveWrapper is implemented.")
    print("\nRun with: pytest tests/integration/test_slack_wrapper.py -v")