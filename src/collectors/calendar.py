"""
CalendarArchiveWrapper - Wrapper for existing scavenge CalendarCollector.

This wrapper integrates the existing scavenge/src/collectors/calendar.py collector
with the new BaseArchiveCollector interface, adding timezone conversion to UTC
and preserving all calendar functionality and data.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging
import pytz

# Import our base collector
from src.collectors.base import BaseArchiveCollector

# Import the existing scavenge collector
scavenge_path = Path(__file__).parent.parent.parent / "scavenge" / "src" / "collectors"
sys.path.insert(0, str(scavenge_path))

try:
    from calendar import CalendarCollector
except ImportError as e:
    logging.warning(f"Could not import CalendarCollector: {e}")
    CalendarCollector = None

logger = logging.getLogger(__name__)


class CalendarArchiveWrapper(BaseArchiveCollector):
    """
    Wrapper for scavenge CalendarCollector that provides BaseArchiveCollector interface.
    
    Uses composition pattern to wrap the existing collector while adding:
    - Timezone conversion to UTC for all datetime fields
    - BaseArchiveCollector interface compliance
    - Circuit breaker and retry logic from base class
    - State management integration
    - Enhanced event metadata and attendee processing
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize CalendarArchiveWrapper with configuration validation.
        
        Args:
            config: Configuration dictionary for both wrapper and scavenge collector
        """
        super().__init__("calendar", config or {})
        
        # Validate configuration
        self._validate_wrapper_config(config or {})
        
        # Initialize the underlying scavenge collector
        if CalendarCollector is None:
            raise ImportError("CalendarCollector could not be imported from scavenge/")
        
        self.scavenge_collector = CalendarCollector(config_path=None)
        
        # Validate scavenge collector has expected components
        self._validate_scavenge_collector()
        
        # Target timezone for conversion (default UTC)
        self.target_timezone = timezone.utc
        
        logger.info("CalendarArchiveWrapper initialized with scavenge collector")
    
    def collect(self) -> Dict[str, Any]:
        """
        Collect calendar data using the scavenge collector and transform to archive format.
        
        This method integrates with the existing scavenge collector's rate limiting
        and adds comprehensive timezone conversion and validation of results.
        
        Returns:
            Dictionary containing transformed data and metadata in BaseArchiveCollector format:
            {
                'data': {...},      # Transformed scavenge collector output
                'metadata': {...}   # Collection metadata
            }
        """
        logger.info("Starting Calendar collection via scavenge collector")
        
        try:
            # Validate rate limiter is available (rate limiting integration check)
            if hasattr(self.scavenge_collector, 'rate_limiter'):
                rate_limiter = self.scavenge_collector.rate_limiter
                logger.info(f"Rate limiting: {rate_limiter.requests_per_second} req/sec")
            else:
                logger.warning("Rate limiter not found in scavenge collector - proceeding without rate limit validation")
            
            # Call the existing scavenge collector (inherits its rate limiting)
            scavenge_results = self.scavenge_collector.collect_all_calendar_data()
            
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
            logger.error(f"Calendar collection failed: {str(e)}")
            raise Exception(f"Calendar collection failed: {str(e)}")
    
    def get_state(self) -> Dict[str, Any]:
        """
        Get current collection state.
        
        Returns:
            Dictionary containing cursor and state information
        """
        with self._state_lock:
            # Base state from parent class
            base_state = self._state.copy()
            
            # Add Calendar-specific state if available
            if hasattr(self.scavenge_collector, 'collection_results'):
                try:
                    scavenge_state = self.scavenge_collector.collection_results
                    if isinstance(scavenge_state, dict):
                        base_state.update({
                            'scavenge_cursor': scavenge_state.get('next_cursor'),
                            'calendars_discovered': scavenge_state.get('discovered', {}).get('calendars', 0),
                            'events_collected': scavenge_state.get('collected', {}).get('events', 0),
                            'sync_token': scavenge_state.get('next_cursor')  # Calendar-specific cursor
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
            if hasattr(self.scavenge_collector, 'collection_results'):
                if 'scavenge_cursor' in state:
                    self.scavenge_collector.collection_results['next_cursor'] = state['scavenge_cursor']
                elif 'sync_token' in state:
                    self.scavenge_collector.collection_results['next_cursor'] = state['sync_token']
    
    def _transform_to_archive_format(self, scavenge_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform scavenge collector output to archive-compatible format.
        
        This method preserves all data from the scavenge collector while ensuring
        it's compatible with JSONL storage and our archive structure. It handles:
        - Timezone conversion to UTC for all datetime fields
        - Event metadata enhancement and attendee processing
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
                'transformation_timestamp': datetime.now(timezone.utc).isoformat()
            }
        else:
            # Successful collection - preserve all fields
            transformed = scavenge_data.copy()
            
            # Ensure consistent structure for archive storage
            if 'events' not in transformed:
                transformed['events'] = []
            if 'calendars' not in transformed:
                transformed['calendars'] = []
            
            # Process events with timezone conversion
            events = transformed.get('events', [])
            if events is None:
                events = []
                transformed['events'] = []
            elif isinstance(events, list) and events:
                transformed['events'] = self._process_events_for_archive(events)
            
            # Process calendars to ensure all metadata is preserved
            calendars = transformed.get('calendars', [])
            if calendars is None:
                calendars = []
                transformed['calendars'] = []
            elif isinstance(calendars, list) and calendars:
                transformed['calendars'] = self._process_calendars_for_archive(calendars)
            
            # Add transformation metadata
            transformed['archive_transformation'] = {
                'transformer': 'CalendarArchiveWrapper',
                'version': '1.0',
                'original_format': 'scavenge_collector',
                'timezone_conversion': 'all_datetimes_to_utc',
                'transformation_timestamp': datetime.now(timezone.utc).isoformat(),
                'data_integrity': {
                    'events_processed': len(events) if isinstance(events, list) else 0,
                    'calendars_processed': len(calendars) if isinstance(calendars, list) else 0,
                    'timezone_conversions': self._count_timezone_conversions(events) if isinstance(events, list) else 0,
                    'recurring_events': sum(1 for e in events if isinstance(e, dict) and e.get('recurrence')) if isinstance(events, list) else 0,
                    'all_day_events': sum(1 for e in events if isinstance(e, dict) and 'date' in e.get('start', {})) if isinstance(events, list) else 0
                }
            }
        
        logger.debug(f"Transformed {len(str(scavenge_data))} chars to {len(str(transformed))} chars")
        return transformed
    
    def _convert_events_to_utc(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Convert all event datetime fields to UTC timezone.
        
        Args:
            events: List of calendar event dictionaries
            
        Returns:
            List of events with UTC-converted datetimes and preserved timezone metadata
        """
        converted_events = []
        
        for event in events:
            if not isinstance(event, dict):
                continue
            
            converted_event = event.copy()
            
            # Track original timezone for event-level metadata
            original_timezone = None
            
            # Convert start datetime
            if 'start' in event:
                converted_start = self._convert_datetime_to_utc(
                    event['start'], 'start', event.get('id', 'unknown')
                )
                converted_event['start'] = converted_start
                # Extract original timezone from start field
                if 'original_timezone' in converted_start:
                    original_timezone = converted_start['original_timezone']
            
            # Convert end datetime  
            if 'end' in event:
                converted_end = self._convert_datetime_to_utc(
                    event['end'], 'end', event.get('id', 'unknown')
                )
                converted_event['end'] = converted_end
                # Extract original timezone from end field if not already set
                if not original_timezone and 'original_timezone' in converted_end:
                    original_timezone = converted_end['original_timezone']
            
            # Add event-level timezone metadata if conversion occurred
            if original_timezone:
                converted_event['original_timezone'] = original_timezone
                converted_event['timezone_conversion'] = {
                    'converted_to': 'UTC',
                    'original_timezone': original_timezone,
                    'conversion_timestamp': datetime.now(timezone.utc).isoformat()
                }
            
            # Convert created/updated timestamps if present
            for timestamp_field in ['created', 'updated']:
                if timestamp_field in event:
                    try:
                        dt = datetime.fromisoformat(event[timestamp_field].replace('Z', '+00:00'))
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=timezone.utc)
                        else:
                            dt = dt.astimezone(timezone.utc)
                        converted_event[timestamp_field] = dt.isoformat()
                    except (ValueError, AttributeError):
                        # Keep original if conversion fails
                        pass
            
            converted_events.append(converted_event)
        
        return converted_events
    
    def _convert_datetime_to_utc(self, datetime_obj: Dict[str, Any], field_name: str, event_id: str) -> Dict[str, Any]:
        """
        Convert a Google Calendar datetime object to UTC.
        
        Args:
            datetime_obj: Google Calendar datetime object (start/end)
            field_name: Name of the field being converted (for logging)
            event_id: Event ID for logging
            
        Returns:
            Converted datetime object with UTC timezone and original timezone metadata
        """
        if not isinstance(datetime_obj, dict):
            return datetime_obj
        
        converted_obj = datetime_obj.copy()
        
        # All-day events have 'date' field, not 'dateTime' - don't convert
        if 'date' in datetime_obj:
            # All-day event - preserve as-is
            return converted_obj
        
        if 'dateTime' not in datetime_obj:
            return converted_obj
        
        try:
            # Parse the datetime string
            dt_str = datetime_obj['dateTime']
            dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
            
            # Store original timezone info
            original_timezone = None
            if 'timeZone' in datetime_obj:
                original_timezone = datetime_obj['timeZone']
            elif dt.tzinfo:
                original_timezone = str(dt.tzinfo)
            
            # Convert to UTC
            if dt.tzinfo is None:
                # No timezone info - assume UTC
                dt = dt.replace(tzinfo=timezone.utc)
            else:
                dt = dt.astimezone(timezone.utc)
            
            # Update the datetime object
            converted_obj['dateTime'] = dt.isoformat()
            
            # Preserve original timezone information in metadata
            if original_timezone:
                converted_obj['original_timezone'] = original_timezone
                converted_obj['timezone_conversion'] = {
                    'converted_to': 'UTC',
                    'original_timezone': original_timezone,
                    'conversion_timestamp': datetime.now(timezone.utc).isoformat()
                }
            
        except (ValueError, AttributeError) as e:
            logger.warning(f"Failed to convert {field_name} datetime for event {event_id}: {e}")
            # Keep original datetime if conversion fails
        
        return converted_obj
    
    def _process_events_for_archive(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process events for archive storage with timezone conversion and metadata enhancement.
        
        Args:
            events: List of event dictionaries from scavenge collector
            
        Returns:
            Processed events with UTC timezones and enhanced metadata
        """
        # First convert timezones
        processed_events = self._convert_events_to_utc(events)
        
        # Then enhance with metadata
        for event in processed_events:
            if not isinstance(event, dict):
                continue
            
            # Add event classification
            event['event_classification'] = {
                'is_recurring': 'recurrence' in event,
                'is_all_day': 'date' in event.get('start', {}),
                'has_attendees': 'attendees' in event and len(event.get('attendees', [])) > 0,
                'privacy_level': event.get('visibility', 'default'),
                'is_private': event.get('visibility') == 'private',
                'has_location': 'location' in event and event.get('location', '').strip(),
                'has_description': 'description' in event and event.get('description', '').strip()
            }
            
            # Process attendees if present
            if 'attendees' in event:
                event['attendee_summary'] = self._summarize_attendees(event['attendees'])
                
                # Add organizer information
                organizer = event.get('organizer', {})
                event['attendee_summary']['organizer_email'] = organizer.get('email', 'unknown')
                event['attendee_summary']['organizer_display_name'] = organizer.get('displayName', 'Unknown')
            
            # Add recurrence information if present
            if 'recurrence' in event:
                event['recurrence_info'] = {
                    'has_recurrence_rules': True,
                    'rule_count': len(event['recurrence']),
                    'rules': event['recurrence']
                }
            
        return processed_events
    
    def _process_calendars_for_archive(self, calendars: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process calendars to ensure all metadata is preserved for archive.
        
        Args:
            calendars: List of calendar dictionaries from scavenge collector
            
        Returns:
            Processed calendars with consistent format
        """
        processed_calendars = []
        
        for calendar in calendars:
            if not isinstance(calendar, dict):
                continue
            
            processed_calendar = calendar.copy()
            
            # Add calendar classification
            processed_calendar['calendar_classification'] = {
                'is_primary': calendar.get('primary', False),
                'is_selected': calendar.get('selected', True),
                'access_role': calendar.get('accessRole', 'unknown'),
                'is_shared': calendar.get('accessRole') in ['reader', 'writer', 'owner'] and not calendar.get('primary', False),
                'has_timezone': 'timeZone' in calendar,
                'timezone': calendar.get('timeZone', 'unknown')
            }
            
            processed_calendars.append(processed_calendar)
        
        return processed_calendars
    
    def _summarize_attendees(self, attendees: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Summarize attendee information for an event.
        
        Args:
            attendees: List of attendee dictionaries
            
        Returns:
            Summary of attendee information
        """
        if not attendees:
            return {'total_count': 0, 'response_status': {}}
        
        status_counts = {}
        required_count = 0
        optional_count = 0
        
        for attendee in attendees:
            if not isinstance(attendee, dict):
                continue
            
            # Count response statuses
            status = attendee.get('responseStatus', 'needsAction')
            status_counts[status] = status_counts.get(status, 0) + 1
            
            # Count required vs optional
            if attendee.get('optional', False):
                optional_count += 1
            else:
                required_count += 1
        
        return {
            'total_count': len(attendees),
            'required_count': required_count,
            'optional_count': optional_count,
            'response_status': status_counts,
            'accepted_count': status_counts.get('accepted', 0),
            'declined_count': status_counts.get('declined', 0),
            'tentative_count': status_counts.get('tentative', 0),
            'needs_action_count': status_counts.get('needsAction', 0)
        }
    
    def _count_timezone_conversions(self, events: List[Dict[str, Any]]) -> int:
        """Count how many timezone conversions were performed."""
        count = 0
        for event in events:
            if isinstance(event, dict):
                if event.get('start', {}).get('timezone_conversion'):
                    count += 1
                if event.get('end', {}).get('timezone_conversion'):
                    count += 1
        return count
    
    def _validate_scavenge_output(self, data: Dict[str, Any]) -> bool:
        """
        Validate that scavenge collector output contains expected structure.
        
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
        
        # For successful collection, be flexible about structure
        logger.debug(f"Validation found calendar data with keys: {list(data.keys())}")
        return True  # Accept any dict structure - preserve everything
    
    def _validate_transformed_output(self, data: Dict[str, Any]) -> bool:
        """
        Validate that transformed output is in correct format for archiving.
        
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
        required_fields = ['events', 'calendars', 'archive_transformation']
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
            'discovered': {'calendars': 0, 'users': 0},
            'collected': {'calendars': 0, 'events': 0}
        }
    
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
        
        # Validate timezone configuration
        if 'target_timezone' in config:
            tz_str = config['target_timezone']
            if tz_str != 'UTC':
                try:
                    pytz.timezone(tz_str)
                except pytz.exceptions.UnknownTimeZoneError:
                    raise ValueError(f"Invalid configuration: unknown timezone '{tz_str}'")
        
        # Validate lookback/lookahead days
        for setting in ['lookback_days', 'lookahead_days']:
            if setting in config:
                value = config[setting]
                if not isinstance(value, int) or value < 0:
                    raise ValueError(f"Invalid configuration: {setting} must be a non-negative integer")
        
        logger.debug(f"Configuration validation passed for {len(config)} settings")
    
    def _validate_scavenge_collector(self) -> None:
        """
        Validate that the scavenge collector has expected components for integration.
        
        Raises:
            ValueError: If scavenge collector is missing expected components
        """
        if not hasattr(self.scavenge_collector, 'collect_all_calendar_data'):
            raise ValueError("Scavenge collector missing collect_all_calendar_data method")
        
        if not hasattr(self.scavenge_collector, 'rate_limiter'):
            logger.warning("Scavenge collector missing rate_limiter attribute - rate limiting validation may not work")
        else:
            # Validate rate limiter has expected methods
            rate_limiter = self.scavenge_collector.rate_limiter
            required_methods = ['wait_for_rate_limit']
            missing_methods = []
            
            for method in required_methods:
                if not hasattr(rate_limiter, method):
                    missing_methods.append(method)
            
            if missing_methods:
                logger.warning(f"Rate limiter missing methods: {missing_methods}")
        
        logger.debug("Scavenge collector validation completed")
    
    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"<CalendarArchiveWrapper(scavenge_collector={self.scavenge_collector}, state={self.get_state()})>"


# Convenience function for creating wrapper instances
def create_calendar_wrapper(config: Optional[Dict[str, Any]] = None) -> CalendarArchiveWrapper:
    """
    Create a CalendarArchiveWrapper instance with optional configuration.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Configured CalendarArchiveWrapper instance
    """
    return CalendarArchiveWrapper(config)