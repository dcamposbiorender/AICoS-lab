"""
Integration tests for Slack DM (Direct Message) collection functionality.
Tests the complete flow from SlackCollector through SlackArchiveWrapper.
Ensures DMs are properly collected, processed, and archived.
"""

import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch

# Import test fixtures
from tests.fixtures.mock_slack_data import (
    get_mock_channels, get_mock_messages, get_mock_users,
    get_mock_collection_result
)

# Import the components we're testing
from src.collectors.slack_wrapper import SlackArchiveWrapper


class TestSlackDMCollection:
    """Integration tests for DM collection and processing."""
    
    def setup_method(self):
        """Set up test fixtures for each test."""
        self.mock_config = {
            'requests_per_second': 10,  # Higher for testing
            'channels_per_minute': 60,
            'rolling_window_hours': 24,
            'collection_rules': {
                'include_all_channels': True,
                'include_dms': True,  # Enable DM collection
                'include_mpims': True,  # Enable MPIM collection
                'exclude_patterns': [],
                'must_include': [],
                'member_only': False,  # Disable for testing
                'include_private': True
            }
        }
        
        self.wrapper = SlackArchiveWrapper(config=self.mock_config)
    
    def test_dm_collection_enabled_by_default(self):
        """DM collection is enabled by default in configuration."""
        # Test with default config
        default_wrapper = SlackArchiveWrapper(config=None)
        
        # The mock SlackCollector should have include_dms=True by default
        assert hasattr(default_wrapper.scavenge_collector, 'config')
        rules = default_wrapper.scavenge_collector.config.get('collection_rules', {})
        assert rules.get('include_dms', False) is True, "DM collection should be enabled by default"
    
    def test_dm_channels_processed_separately(self):
        """DM channels are processed separately from regular channels."""
        # Mock the scavenge collector to return test data
        mock_result = get_mock_collection_result()
        
        # Separate the channels into DMs, MPIMs, and regular channels 
        all_channels = get_mock_channels()
        dm_channels = [c for c in all_channels if c.get('is_im', False)]
        mpim_channels = [c for c in all_channels if c.get('is_mpim', False)]
        regular_channels = [c for c in all_channels if not c.get('is_im', False) and not c.get('is_mpim', False)]
        
        # Update mock result to include separated data
        mock_result['channel_results'] = {
            'collected_data': {
                'C1234567890': {  # Regular channel data
                    'channel_info': {'id': 'C1234567890', 'name': 'general'},
                    'messages': get_mock_messages()[:5]  # Some messages
                }
            }
        }
        
        # Add the channels data structure that the wrapper expects
        mock_result['channels'] = all_channels
        mock_result['users'] = get_mock_users()
        
        with patch.object(self.wrapper.scavenge_collector, 'collect_all_slack_data', return_value=mock_result):
            result = self.wrapper.collect()
            
            data = result['data']
            
            # Should have channels, dms, and mpims fields
            assert 'channels' in data, "Result should have 'channels' field"
            assert 'dms' in data, "Result should have 'dms' field for DM channels"
            assert 'mpims' in data, "Result should have 'mpims' field for MPIM channels"
            
            # DMs should be populated
            dms = data['dms']
            assert len(dms) >= 3, f"Should have at least 3 DMs, got {len(dms)}"
            
            # MPIMs should be populated
            mpims = data['mpims']
            assert len(mpims) >= 3, f"Should have at least 3 MPIMs, got {len(mpims)}"
            
            # Each DM should have proper classification
            for dm in dms:
                assert 'dm_classification' in dm, f"DM {dm['id']} missing classification"
                classification = dm['dm_classification']
                assert classification['is_dm'] is True
                assert 'other_user_id' in classification
                assert 'created_timestamp' in classification
            
            # Each MPIM should have proper classification
            for mpim in mpims:
                assert 'mpim_classification' in mpim, f"MPIM {mpim['id']} missing classification"
                classification = mpim['mpim_classification']
                assert classification['is_mpim'] is True
                assert 'participant_count' in classification
                assert 'members' in classification
                assert classification['participant_count'] >= 3
    
    def test_dm_data_integrity_tracking(self):
        """DM and MPIM processing is tracked in data integrity metadata."""
        # Mock data with known counts
        mock_result = get_mock_collection_result()
        all_channels = get_mock_channels()
        dm_count = len([c for c in all_channels if c.get('is_im', False)])
        mpim_count = len([c for c in all_channels if c.get('is_mpim', False)])
        
        mock_result['channels'] = all_channels
        mock_result['users'] = get_mock_users()
        mock_result['messages'] = get_mock_messages()
        
        with patch.object(self.wrapper.scavenge_collector, 'collect_all_slack_data', return_value=mock_result):
            result = self.wrapper.collect()
            
            data = result['data']
            integrity = data['archive_transformation']['data_integrity']
            
            # Should track DMs and MPIMs processed
            assert 'dms_processed' in integrity, "Should track DMs processed"
            assert 'mpims_processed' in integrity, "Should track MPIMs processed"
            assert integrity['dms_processed'] == dm_count, f"Should track {dm_count} DMs processed"
            assert integrity['mpims_processed'] == mpim_count, f"Should track {mpim_count} MPIMs processed"
            
            # Should track regular channels separately
            regular_channel_count = len([c for c in all_channels if not c.get('is_im', False) and not c.get('is_mpim', False)])
            assert integrity['channels_processed'] == regular_channel_count
    
    def test_dm_messages_preserved(self):
        """DM messages are properly preserved in the archive."""
        mock_result = get_mock_collection_result()
        all_messages = get_mock_messages()
        dm_messages = [m for m in all_messages if m.get('channel', '').startswith('D')]
        
        mock_result['channels'] = get_mock_channels()
        mock_result['users'] = get_mock_users()
        mock_result['messages'] = all_messages
        
        with patch.object(self.wrapper.scavenge_collector, 'collect_all_slack_data', return_value=mock_result):
            result = self.wrapper.collect()
            
            data = result['data']
            archived_messages = data.get('messages', [])
            
            # Find DM messages in archived data
            archived_dm_messages = [m for m in archived_messages if m.get('channel', '').startswith('D')]
            
            assert len(archived_dm_messages) >= len(dm_messages), "All DM messages should be preserved"
            
            # Check that DM messages have proper metadata
            for msg in archived_dm_messages:
                assert msg.get('channel', '').startswith('D'), "DM message should be in D channel"
                assert 'message_classification' in msg, "DM message should have classification"
    
    def test_dm_collection_can_be_disabled(self):
        """DM collection can be disabled via configuration."""
        # Test with DM collection disabled
        no_dm_config = self.mock_config.copy()
        no_dm_config['collection_rules']['include_dms'] = False
        
        wrapper_no_dms = SlackArchiveWrapper(config=no_dm_config)
        
        # Mock the scavenge collector to simulate no DM collection
        mock_result = get_mock_collection_result()
        all_channels = get_mock_channels()
        
        # Filter out DMs from the mock result
        regular_channels_only = [c for c in all_channels if not c.get('is_im', False)]
        mock_result['channels'] = regular_channels_only
        mock_result['users'] = get_mock_users()
        mock_result['messages'] = get_mock_messages()
        
        with patch.object(wrapper_no_dms.scavenge_collector, 'collect_all_slack_data', return_value=mock_result):
            result = wrapper_no_dms.collect()
            
            data = result['data']
            
            # Should still have dms field but it should be empty
            assert 'dms' in data, "Result should have 'dms' field even when disabled"
            assert len(data['dms']) == 0, "DMs list should be empty when collection disabled"
            
            # Data integrity should show 0 DMs processed
            integrity = data['archive_transformation']['data_integrity']
            assert integrity.get('dms_processed', 0) == 0, "Should show 0 DMs processed when disabled"
    
    def test_dm_privacy_fields_preserved(self):
        """DM-specific privacy and metadata fields are preserved."""
        mock_result = get_mock_collection_result()
        all_channels = get_mock_channels()
        dm_channels = [c for c in all_channels if c.get('is_im', False)]
        
        mock_result['channels'] = all_channels
        mock_result['users'] = get_mock_users()
        
        with patch.object(self.wrapper.scavenge_collector, 'collect_all_slack_data', return_value=mock_result):
            result = self.wrapper.collect()
            
            data = result['data']
            dms = data['dms']
            
            for dm in dms:
                classification = dm['dm_classification']
                
                # Privacy and state fields should be preserved
                assert 'is_user_deleted' in classification
                assert 'is_open' in classification
                assert 'priority' in classification
                assert 'is_org_shared' in classification
                
                # Timestamp fields should be properly handled
                if classification.get('created_timestamp', 0) > 0:
                    assert 'created_iso' in classification, f"DM {dm['id']} missing ISO timestamp"
    
    def test_dm_transformation_json_serializable(self):
        """DM transformation results are JSON serializable for archive storage."""
        mock_result = get_mock_collection_result()
        mock_result['channels'] = get_mock_channels()
        mock_result['users'] = get_mock_users()
        
        with patch.object(self.wrapper.scavenge_collector, 'collect_all_slack_data', return_value=mock_result):
            result = self.wrapper.collect()
            
            # Should be able to serialize entire result to JSON
            try:
                json_str = json.dumps(result)
                assert len(json_str) > 0, "Should produce non-empty JSON"
                
                # Should be able to deserialize back
                reloaded = json.loads(json_str)
                assert 'data' in reloaded
                assert 'dms' in reloaded['data']
                
            except (TypeError, ValueError) as e:
                pytest.fail(f"DM transformation result not JSON serializable: {e}")


class TestSlackDMConfigurationEdgeCases:
    """Test edge cases in DM configuration and error handling."""
    
    def test_missing_dm_config_defaults_to_enabled(self):
        """Missing DM configuration defaults to enabled."""
        config_without_dm_setting = {
            'collection_rules': {
                'include_all_channels': True
                # Missing 'include_dms' setting
            }
        }
        
        wrapper = SlackArchiveWrapper(config=config_without_dm_setting)
        
        # Should default to True
        rules = wrapper.scavenge_collector.config.get('collection_rules', {})
        assert rules.get('include_dms', False) is True, "Should default to DM collection enabled"
    
    def test_invalid_dm_config_handled_gracefully(self):
        """Invalid DM configuration values are handled gracefully."""
        invalid_configs = [
            {'collection_rules': {'include_dms': 'invalid_string'}},
            {'collection_rules': {'include_dms': 123}},
            {'collection_rules': {'include_dms': []}},
            {'collection_rules': {'include_dms': None}},
        ]
        
        for invalid_config in invalid_configs:
            # Should not raise exception during initialization
            try:
                wrapper = SlackArchiveWrapper(config=invalid_config)
                # Should handle invalid config gracefully in actual collection
                # (This would be tested with the actual scavenge collector)
            except Exception as e:
                pytest.fail(f"Should handle invalid DM config gracefully, but got: {e}")


if __name__ == "__main__":
    # Run the tests directly for debugging
    print("Running Slack DM collection integration tests...")
    
    test_collection = TestSlackDMCollection()
    test_collection.setup_method()
    
    print("✓ Testing DM collection enabled by default...")
    test_collection.test_dm_collection_enabled_by_default()
    
    print("✓ Testing DM channels processed separately...")
    test_collection.test_dm_channels_processed_separately()
    
    print("✓ Testing DM data integrity tracking...")  
    test_collection.test_dm_data_integrity_tracking()
    
    print("✓ Testing DM collection can be disabled...")
    test_collection.test_dm_collection_can_be_disabled()
    
    print("✓ Testing DM transformation JSON serializable...")
    test_collection.test_dm_transformation_json_serializable()
    
    print("\nRunning configuration edge case tests...")
    test_config = TestSlackDMConfigurationEdgeCases()
    
    print("✓ Testing missing DM config defaults...")
    test_config.test_missing_dm_config_defaults_to_enabled()
    
    print("✓ Testing invalid DM config handling...")
    test_config.test_invalid_dm_config_handled_gracefully()
    
    print("All Slack DM integration tests passed! ✅")