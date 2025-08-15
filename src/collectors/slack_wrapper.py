"""
SlackArchiveWrapper - Wrapper for existing scavenge SlackCollector.

This wrapper integrates the existing scavenge/src/collectors/slack.py collector
with the new BaseArchiveCollector interface, transforming output to JSONL format
while preserving all functionality and data.
"""

import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging

# Import our base collector
from src.collectors.base import BaseArchiveCollector

# Import the existing scavenge collector
scavenge_path = Path(__file__).parent.parent.parent / "scavenge" / "src" / "collectors"
sys.path.insert(0, str(scavenge_path))

try:
    from slack import SlackCollector
except ImportError as e:
    logging.warning(f"Could not import SlackCollector: {e}")
    SlackCollector = None

logger = logging.getLogger(__name__)


class SlackArchiveWrapper(BaseArchiveCollector):
    """
    Wrapper for scavenge SlackCollector that provides BaseArchiveCollector interface.
    
    Uses composition pattern to wrap the existing collector while adding:
    - JSONL transformation for archive storage
    - BaseArchiveCollector interface compliance
    - Circuit breaker and retry logic from base class
    - State management integration
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize SlackArchiveWrapper with configuration validation.
        
        Args:
            config: Configuration dictionary for both wrapper and scavenge collector
        """
        super().__init__("slack", config or {})
        
        # Validate configuration
        self._validate_wrapper_config(config or {})
        
        # Initialize the underlying scavenge collector
        if SlackCollector is None:
            raise ImportError("SlackCollector could not be imported from scavenge/")
        
        self.scavenge_collector = SlackCollector(config_path=None)
        
        # Validate scavenge collector has expected components
        self._validate_scavenge_collector()
        
        logger.info("SlackArchiveWrapper initialized with scavenge collector")
    
    def collect(self) -> Dict[str, Any]:
        """
        Collect Slack data using the scavenge collector and transform to archive format.
        
        This method integrates with the existing scavenge collector's rate limiting
        and adds comprehensive validation of results before transformation.
        
        Returns:
            Dictionary containing transformed data and metadata in BaseArchiveCollector format:
            {
                'data': {...},      # Transformed scavenge collector output
                'metadata': {...}   # Collection metadata
            }
        """
        logger.info("Starting Slack collection via scavenge collector")
        
        try:
            # Validate rate limiter is available (rate limiting integration check)
            if hasattr(self.scavenge_collector, 'rate_limiter'):
                rate_limiter = self.scavenge_collector.rate_limiter
                logger.info(f"Rate limiting: {rate_limiter.requests_per_second} req/sec, {rate_limiter.channels_per_minute} channels/min")
            else:
                logger.warning("Rate limiter not found in scavenge collector - proceeding without rate limit validation")
            
            # Call the existing scavenge collector (inherits its rate limiting)
            scavenge_results = self.scavenge_collector.collect_all_slack_data()
            
            # Validate the scavenge collector output
            if not self._validate_scavenge_output(scavenge_results):
                raise ValueError(f"Invalid output from scavenge collector: {type(scavenge_results)}")
            
            # Check if collection failed
            if isinstance(scavenge_results, dict) and scavenge_results.get('error'):
                raise Exception(f"Scavenge collector failed: {scavenge_results['error']}")
            
            # Transform the results to our expected format
            transformed_data = self._transform_to_archive_format(scavenge_results)
            
            # Final validation of transformed data
            if not self._validate_transformed_output(transformed_data):
                raise ValueError("Transformation produced invalid output format")
            
            # Return in BaseArchiveCollector format
            return {
                'data': transformed_data,
                'metadata': self.get_metadata()
            }
            
        except Exception as e:
            logger.error(f"Slack collection failed: {str(e)}")
            raise
    
    def get_state(self) -> Dict[str, Any]:
        """
        Get current collection state.
        
        Returns:
            Dictionary containing cursor and state information
        """
        with self._state_lock:
            # Base state from parent class
            base_state = self._state.copy()
            
            # Add Slack-specific state if available
            if hasattr(self.scavenge_collector, 'collection_results'):
                try:
                    scavenge_state = self.scavenge_collector.collection_results
                    if isinstance(scavenge_state, dict):
                        base_state.update({
                            'scavenge_cursor': scavenge_state.get('next_cursor'),
                            'channels_discovered': scavenge_state.get('discovered', {}).get('channels', 0),
                            'users_discovered': scavenge_state.get('discovered', {}).get('users', 0),
                            'messages_collected': scavenge_state.get('collected', {}).get('messages', 0)
                        })
                except (AttributeError, TypeError):
                    # Handle case where scavenge collector is mocked or doesn't have expected structure
                    pass
            
            return base_state
    
    def set_state(self, state: Dict[str, Any]) -> None:
        """
        Update collection state.
        
        Args:
            state: New state dictionary to merge with current state
        """
        with self._state_lock:
            self._state.update(state)
            
            # Pass relevant state to scavenge collector if needed
            if hasattr(self.scavenge_collector, 'collection_results') and 'scavenge_cursor' in state:
                self.scavenge_collector.collection_results['next_cursor'] = state['scavenge_cursor']
    
    def _transform_to_archive_format(self, scavenge_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform scavenge collector output to archive-compatible format.
        
        This method preserves all data from the scavenge collector while ensuring
        it's compatible with JSONL storage and our archive structure. It handles:
        - Thread relationship preservation
        - Special message types (bot, system, deleted)
        - All metadata fields from scavenge collector
        - Error cases and malformed data
        
        Args:
            scavenge_data: Output from scavenge collector
            
        Returns:
            Transformed data ready for archive storage
        """
        if not isinstance(scavenge_data, dict):
            logger.warning(f"Unexpected scavenge data type: {type(scavenge_data)}")
            return {'raw_data': scavenge_data}
        
        # Start with the original data structure
        transformed = {}
        
        # Handle different data structures that might come from scavenge collector
        if 'error' in scavenge_data:
            # Error case - preserve error information
            transformed = {
                'collection_status': 'error',
                'error_details': scavenge_data,
                'transformation_timestamp': datetime.now().isoformat()
            }
        else:
            # Successful collection - preserve all fields
            transformed = scavenge_data.copy()
            
            # Ensure consistent structure for archive storage
            if 'messages' not in transformed:
                transformed['messages'] = []
            if 'channels' not in transformed:
                transformed['channels'] = []
            if 'users' not in transformed:
                transformed['users'] = []
            
            # Process messages to ensure thread relationships are preserved
            messages = transformed.get('messages', [])
            if messages is None:
                messages = []
                transformed['messages'] = []
            elif isinstance(messages, list) and messages:
                transformed['messages'] = self._process_messages_for_archive(messages)
            
            # Process channels to ensure all metadata is preserved
            channels = transformed.get('channels', [])
            if channels is None:
                channels = []
                transformed['channels'] = []
            elif isinstance(channels, list) and channels:
                transformed['channels'] = self._process_channels_for_archive(channels)
            
            # Process users to ensure all profile data is preserved
            users = transformed.get('users', [])
            if users is None:
                users = []
                transformed['users'] = []
            elif isinstance(users, list) and users:
                transformed['users'] = self._process_users_for_archive(users)
            
            # Add transformation metadata
            transformed['archive_transformation'] = {
                'transformer': 'SlackArchiveWrapper',
                'version': '1.0',
                'original_format': 'scavenge_collector',
                'preservation_method': 'field_by_field_copy_with_processing',
                'transformation_timestamp': datetime.now().isoformat(),
                'data_integrity': {
                    'messages_processed': len(messages) if isinstance(messages, list) else 0,
                    'channels_processed': len(channels) if isinstance(channels, list) else 0,
                    'users_processed': len(users) if isinstance(users, list) else 0,
                    'thread_relationships_preserved': sum(1 for msg in messages if isinstance(msg, dict) and msg.get('thread_ts')) if isinstance(messages, list) else 0,
                    'special_message_types': self._count_special_message_types(messages) if isinstance(messages, list) else {}
                }
            }
        
        logger.debug(f"Transformed {len(str(scavenge_data))} chars to {len(str(transformed))} chars")
        return transformed
    
    def _validate_scavenge_output(self, data: Dict[str, Any]) -> bool:
        """
        Validate that scavenge collector output contains expected structure.
        
        This validation ensures the scavenge collector returned data in a format
        we can process, without being overly strict about the exact schema.
        
        Args:
            data: Output from scavenge collector
            
        Returns:
            True if data structure is valid, False otherwise
        """
        if not isinstance(data, dict):
            logger.warning(f"Scavenge collector output is not a dict: {type(data)}")
            return False
        
        # If there's an error, it's still valid (error case)
        if 'error' in data:
            logger.info("Scavenge collector returned error - treating as valid error response")
            return True
        
        # For successful collection, check for basic expected fields
        # We're flexible about exact structure but want some basic validation
        expected_fields = ['channels', 'users', 'messages']
        found_fields = []
        
        for field in expected_fields:
            if field in data:
                found_fields.append(field)
        
        if len(found_fields) == 0:
            logger.warning(f"No expected fields found in scavenge output. Available keys: {list(data.keys())}")
            # Still allow it - might be a different format we can handle
        
        logger.debug(f"Validation found {len(found_fields)} expected fields: {found_fields}")
        return True  # Accept any dict structure - preserve everything
    
    def _validate_transformed_output(self, data: Dict[str, Any]) -> bool:
        """
        Validate that transformed output is in correct format for archiving.
        
        This validation ensures our transformation produced valid output that
        can be serialized to JSONL and stored in the archive system.
        
        Args:
            data: Transformed data output
            
        Returns:
            True if transformed data is valid, False otherwise
        """
        if not isinstance(data, dict):
            logger.error(f"Transformed output is not a dict: {type(data)}")
            return False
        
        # Check for required structure
        if 'collection_status' in data and data['collection_status'] == 'error':
            # Error case - should have error_details
            if 'error_details' not in data:
                logger.error("Error case missing error_details")
                return False
            logger.debug("Validated error case transformation")
            return True
        
        # Success case - should have basic structure
        required_fields = ['messages', 'channels', 'users', 'archive_transformation']
        missing_fields = []
        
        for field in required_fields:
            if field not in data:
                missing_fields.append(field)
        
        if missing_fields:
            logger.error(f"Transformed output missing required fields: {missing_fields}")
            return False
        
        # Validate archive transformation metadata
        archive_meta = data.get('archive_transformation', {})
        required_meta = ['transformer', 'version', 'transformation_timestamp']
        missing_meta = []
        
        for meta_field in required_meta:
            if meta_field not in archive_meta:
                missing_meta.append(meta_field)
        
        if missing_meta:
            logger.error(f"Archive transformation metadata missing fields: {missing_meta}")
            return False
        
        # Check JSON serializability (critical for JSONL storage)
        try:
            import json
            json.dumps(data)
            logger.debug("Transformed output is JSON serializable")
        except (TypeError, ValueError) as e:
            logger.error(f"Transformed output is not JSON serializable: {e}")
            return False
        
        logger.debug("Transformed output validation successful")
        return True
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get collection statistics from the underlying scavenge collector.
        
        Returns:
            Dictionary with collection statistics
        """
        if hasattr(self.scavenge_collector, 'collection_results'):
            return self.scavenge_collector.collection_results.copy()
        
        return {
            'status': 'unknown',
            'discovered': {'channels': 0, 'users': 0},
            'collected': {'channels': 0, 'messages': 0}
        }
    
    def _process_messages_for_archive(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process messages to ensure proper archive format and thread preservation.
        
        Args:
            messages: List of message dictionaries from scavenge collector
            
        Returns:
            Processed messages with enhanced metadata
        """
        processed_messages = []
        
        for message in messages:
            if not isinstance(message, dict):
                continue
            
            # Start with original message
            processed_msg = message.copy()
            
            # Ensure thread relationship fields are preserved
            if 'thread_ts' in message:
                processed_msg['is_thread_reply'] = True
                processed_msg['thread_parent_ts'] = message['thread_ts']
            else:
                processed_msg['is_thread_reply'] = False
            
            # Add message classification
            processed_msg['message_classification'] = {
                'is_bot': message.get('subtype') == 'bot_message',
                'is_system': message.get('subtype') in ['channel_join', 'channel_leave', 'channel_purpose', 'channel_topic'],
                'is_deleted': message.get('subtype') == 'message_deleted',
                'is_edited': message.get('subtype') == 'message_changed',
                'has_file': 'files' in message and len(message.get('files', [])) > 0,
                'has_reactions': 'reactions' in message and len(message.get('reactions', [])) > 0
            }
            
            # Ensure timestamp is properly formatted
            if 'ts' in message:
                try:
                    ts_float = float(message['ts'])
                    processed_msg['timestamp_iso'] = datetime.fromtimestamp(ts_float).isoformat()
                except (ValueError, TypeError):
                    pass
            
            processed_messages.append(processed_msg)
        
        return processed_messages
    
    def _process_channels_for_archive(self, channels: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process channels to ensure all metadata is preserved for archive.
        
        Args:
            channels: List of channel dictionaries from scavenge collector
            
        Returns:
            Processed channels with consistent format
        """
        processed_channels = []
        
        for channel in channels:
            if not isinstance(channel, dict):
                continue
            
            processed_channel = channel.copy()
            
            # Add channel classification
            processed_channel['channel_classification'] = {
                'is_private': channel.get('is_private', False),
                'is_archived': channel.get('is_archived', False),
                'is_member': channel.get('is_member', False),
                'is_general': channel.get('is_general', False),
                'member_count': channel.get('num_members', 0)
            }
            
            processed_channels.append(processed_channel)
        
        return processed_channels
    
    def _process_users_for_archive(self, users: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process users to ensure profile data is preserved for archive.
        
        Args:
            users: List of user dictionaries from scavenge collector
            
        Returns:
            Processed users with consistent format
        """
        processed_users = []
        
        for user in users:
            if not isinstance(user, dict):
                continue
            
            processed_user = user.copy()
            
            # Add user classification
            processed_user['user_classification'] = {
                'is_bot': user.get('is_bot', False),
                'is_app_user': user.get('is_app_user', False),
                'is_admin': user.get('is_admin', False),
                'is_owner': user.get('is_owner', False),
                'is_deleted': user.get('deleted', False),
                'has_profile_image': 'profile' in user and 'image_24' in user.get('profile', {})
            }
            
            processed_users.append(processed_user)
        
        return processed_users
    
    def _count_special_message_types(self, messages: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Count special message types for transformation metadata.
        
        Args:
            messages: List of message dictionaries
            
        Returns:
            Dictionary with counts of special message types
        """
        counts = {
            'bot_messages': 0,
            'system_messages': 0,
            'deleted_messages': 0,
            'edited_messages': 0,
            'thread_replies': 0,
            'messages_with_files': 0,
            'messages_with_reactions': 0
        }
        
        for message in messages:
            if not isinstance(message, dict):
                continue
            
            subtype = message.get('subtype')
            if subtype == 'bot_message':
                counts['bot_messages'] += 1
            elif subtype in ['channel_join', 'channel_leave', 'channel_purpose', 'channel_topic']:
                counts['system_messages'] += 1
            elif subtype == 'message_deleted':
                counts['deleted_messages'] += 1
            elif subtype == 'message_changed':
                counts['edited_messages'] += 1
            
            if message.get('thread_ts'):
                counts['thread_replies'] += 1
            
            if message.get('files'):
                counts['messages_with_files'] += 1
            
            if message.get('reactions'):
                counts['messages_with_reactions'] += 1
        
        return counts

    def _validate_wrapper_config(self, config: Dict[str, Any]) -> None:
        """
        Validate wrapper configuration parameters.
        
        Args:
            config: Configuration dictionary to validate
            
        Raises:
            ValueError: If configuration is invalid
        """
        if not isinstance(config, dict):
            raise ValueError(f"Configuration must be a dictionary, got {type(config)}")
        
        # Validate rate limiting configuration if provided
        if 'requests_per_second' in config:
            rps = config['requests_per_second']
            if not isinstance(rps, (int, float)) or rps <= 0:
                raise ValueError(f"requests_per_second must be a positive number, got {rps}")
        
        if 'channels_per_minute' in config:
            cpm = config['channels_per_minute']
            if not isinstance(cpm, (int, float)) or cpm <= 0:
                raise ValueError(f"channels_per_minute must be a positive number, got {cpm}")
        
        # Validate rolling window configuration
        if 'rolling_window_hours' in config:
            rwh = config['rolling_window_hours']
            if not isinstance(rwh, (int, float)) or rwh <= 0:
                raise ValueError(f"rolling_window_hours must be a positive number, got {rwh}")
        
        logger.debug(f"Configuration validation passed for {len(config)} settings")
    
    def _validate_scavenge_collector(self) -> None:
        """
        Validate that the scavenge collector has expected components for integration.
        
        This validates that rate limiting and other expected functionality is available.
        
        Raises:
            ValueError: If scavenge collector is missing expected components
        """
        if not hasattr(self.scavenge_collector, 'collect_all_slack_data'):
            raise ValueError("Scavenge collector missing collect_all_slack_data method")
        
        if not hasattr(self.scavenge_collector, 'rate_limiter'):
            logger.warning("Scavenge collector missing rate_limiter attribute - rate limiting validation may not work")
        else:
            # Validate rate limiter has expected methods
            rate_limiter = self.scavenge_collector.rate_limiter
            required_methods = ['wait_for_api_limit', 'wait_for_channel_limit']
            missing_methods = []
            
            for method in required_methods:
                if not hasattr(rate_limiter, method):
                    missing_methods.append(method)
            
            if missing_methods:
                logger.warning(f"Rate limiter missing methods: {missing_methods}")
        
        logger.debug("Scavenge collector validation completed")

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"<SlackArchiveWrapper(scavenge_collector={self.scavenge_collector}, state={self.get_state()})>"


# Convenience function for creating wrapper instances
def create_slack_wrapper(config: Optional[Dict[str, Any]] = None) -> SlackArchiveWrapper:
    """
    Create a SlackArchiveWrapper instance with optional configuration.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Configured SlackArchiveWrapper instance
    """
    return SlackArchiveWrapper(config)