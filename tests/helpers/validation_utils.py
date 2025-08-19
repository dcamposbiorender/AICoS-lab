"""
Validation utilities for deterministic testing

These utilities validate data completeness and structure WITHOUT making up any data.
All validation is based on actual collected data structure and required fields.
"""

from typing import Dict, List, Tuple, Any, Optional
import json
from datetime import datetime


def validate_slack_message(message: Dict) -> Tuple[bool, List[str]]:
    """
    Validate Slack message structure for required fields
    
    Args:
        message: Slack message object from API
        
    Returns:
        Tuple of (is_valid, list_of_missing_fields)
    """
    required_fields = ['ts', 'type', 'user', 'text']
    missing_fields = []
    
    for field in required_fields:
        if field not in message:
            missing_fields.append(field)
    
    # Additional validation for field types
    if 'ts' in message:
        try:
            float(message['ts'])  # Should be timestamp
        except (ValueError, TypeError):
            missing_fields.append('ts (invalid timestamp)')
    
    return len(missing_fields) == 0, missing_fields


def validate_calendar_event(event: Dict) -> Tuple[bool, List[str]]:
    """
    Validate calendar event structure for required fields
    
    Args:
        event: Calendar event object from Google Calendar API
        
    Returns:
        Tuple of (is_valid, list_of_missing_fields)
    """
    required_fields = ['id', 'summary', 'start', 'end']
    missing_fields = []
    
    for field in required_fields:
        if field not in event:
            missing_fields.append(field)
    
    # Validate start/end have datetime or date
    for time_field in ['start', 'end']:
        if time_field in event and isinstance(event[time_field], dict):
            if 'dateTime' not in event[time_field] and 'date' not in event[time_field]:
                missing_fields.append(f'{time_field} (missing dateTime/date)')
    
    return len(missing_fields) == 0, missing_fields


def validate_drive_file(file: Dict) -> Tuple[bool, List[str]]:
    """
    Validate Drive file metadata for required fields
    
    Args:
        file: Drive file object from Google Drive API
        
    Returns:
        Tuple of (is_valid, list_of_missing_fields)
    """
    required_fields = ['id', 'name', 'mimeType', 'modifiedTime']
    missing_fields = []
    
    for field in required_fields:
        if field not in file:
            missing_fields.append(field)
    
    # Validate modifiedTime is valid ISO format
    if 'modifiedTime' in file:
        try:
            datetime.fromisoformat(file['modifiedTime'].replace('Z', '+00:00'))
        except (ValueError, TypeError):
            missing_fields.append('modifiedTime (invalid ISO format)')
    
    return len(missing_fields) == 0, missing_fields


def count_entities_deterministic(data: Any, entity_type: str) -> int:
    """
    Count entities in data WITHOUT making up any numbers
    
    Args:
        data: Data structure containing entities
        entity_type: Type of entity to count
        
    Returns:
        Actual count of entities found
    """
    if not data:
        return 0
    
    if entity_type == "channels":
        if isinstance(data, dict):
            # Count items that look like channels
            return len([item for item in data.values() 
                       if isinstance(item, dict) and 'id' in item])
        elif isinstance(data, list):
            return len([item for item in data 
                       if isinstance(item, dict) and 'id' in item])
    
    elif entity_type == "users":
        if isinstance(data, dict):
            # Count items that look like users (not bots, not deleted)
            return len([item for item in data.values() 
                       if isinstance(item, dict) and 
                       not item.get('is_bot', False) and 
                       not item.get('deleted', False)])
        elif isinstance(data, list):
            return len([item for item in data 
                       if isinstance(item, dict) and 
                       not item.get('is_bot', False) and 
                       not item.get('deleted', False)])
    
    elif entity_type == "messages":
        if isinstance(data, list):
            return len([item for item in data 
                       if isinstance(item, dict) and 'ts' in item])
        elif isinstance(data, dict):
            # Might be nested under channels
            total = 0
            for value in data.values():
                if isinstance(value, dict) and 'messages' in value:
                    total += len(value['messages'])
            return total
    
    elif entity_type == "events":
        if isinstance(data, list):
            return len([item for item in data 
                       if isinstance(item, dict) and 'id' in item])
        elif isinstance(data, dict):
            # Might be nested under calendars
            total = 0
            for value in data.values():
                if isinstance(value, list):
                    total += len(value)
            return total
    
    elif entity_type == "files":
        if isinstance(data, dict):
            return len([item for item in data.values() 
                       if isinstance(item, dict) and 'id' in item and 'mimeType' in item])
        elif isinstance(data, list):
            return len([item for item in data 
                       if isinstance(item, dict) and 'id' in item and 'mimeType' in item])
    
    # Default: if it's a dict, count keys; if list, count items
    if isinstance(data, dict):
        return len(data)
    elif isinstance(data, list):
        return len(data)
    else:
        return 0


def validate_rate_limiting(request_log: List[Dict], expected_rate: float) -> Tuple[bool, str]:
    """
    Validate that rate limiting was properly enforced
    
    Args:
        request_log: List of request timestamps/durations
        expected_rate: Expected requests per second
        
    Returns:
        Tuple of (is_valid, explanation)
    """
    if len(request_log) < 2:
        return True, "Insufficient requests to validate rate limiting"
    
    # Calculate actual rate
    total_time = 0
    for entry in request_log:
        if 'duration' in entry:
            total_time += entry['duration']
        elif 'wait_time' in entry:
            total_time += entry['wait_time']
    
    if total_time == 0:
        return False, "No timing data found in request log"
    
    actual_rate = len(request_log) / total_time
    expected_min_rate = expected_rate * 0.8  # Allow 20% variance
    expected_max_rate = expected_rate * 1.2
    
    if expected_min_rate <= actual_rate <= expected_max_rate:
        return True, f"Rate limiting valid: {actual_rate:.2f} req/sec (expected ~{expected_rate:.2f})"
    else:
        return False, f"Rate limiting invalid: {actual_rate:.2f} req/sec (expected {expected_rate:.2f} ±20%)"


def validate_data_completeness(collected_data: Dict, source_type: str) -> Tuple[bool, Dict]:
    """
    Validate that collected data appears complete based on its structure
    
    Args:
        collected_data: The data that was collected
        source_type: Type of source (slack, calendar, drive)
        
    Returns:
        Tuple of (is_complete, validation_details)
    """
    validation_details = {
        "source_type": source_type,
        "total_entities": 0,
        "validation_errors": [],
        "warnings": []
    }
    
    if not collected_data:
        validation_details["validation_errors"].append("No data collected")
        return False, validation_details
    
    if source_type == "slack":
        # Validate Slack data structure
        channel_count = 0
        message_count = 0
        
        for channel_id, channel_data in collected_data.items():
            if isinstance(channel_data, dict):
                channel_count += 1
                
                # Validate channel has expected structure
                if 'messages' in channel_data:
                    messages = channel_data['messages']
                    message_count += len(messages)
                    
                    # Validate each message
                    for i, message in enumerate(messages[:5]):  # Check first 5 messages
                        is_valid, missing_fields = validate_slack_message(message)
                        if not is_valid:
                            validation_details["validation_errors"].append(
                                f"Channel {channel_id} message {i}: missing {missing_fields}"
                            )
                
                # Check for analytics
                if 'analytics' not in channel_data:
                    validation_details["warnings"].append(
                        f"Channel {channel_id} missing analytics"
                    )
        
        validation_details["total_entities"] = message_count
        validation_details["channels"] = channel_count
        validation_details["messages"] = message_count
    
    elif source_type == "calendar":
        # Validate Calendar data structure
        calendar_count = 0
        event_count = 0
        
        for calendar_id, events in collected_data.items():
            calendar_count += 1
            if isinstance(events, list):
                event_count += len(events)
                
                # Validate each event  
                for i, event in enumerate(events[:5]):  # Check first 5 events
                    is_valid, missing_fields = validate_calendar_event(event)
                    if not is_valid:
                        validation_details["validation_errors"].append(
                            f"Calendar {calendar_id} event {i}: missing {missing_fields}"
                        )
        
        validation_details["total_entities"] = event_count
        validation_details["calendars"] = calendar_count  
        validation_details["events"] = event_count
    
    elif source_type == "drive":
        # Validate Drive data structure
        if 'changes' in collected_data:
            changes = collected_data['changes']
            change_count = len(changes)
            
            # Validate each change
            for i, change in enumerate(changes[:5]):  # Check first 5 changes
                if not isinstance(change, dict) or 'fileId' not in change:
                    validation_details["validation_errors"].append(
                        f"Change {i}: invalid structure or missing fileId"
                    )
            
            validation_details["total_entities"] = change_count
            validation_details["changes"] = change_count
        else:
            validation_details["validation_errors"].append("No changes found in drive data")
    
    # Determine if validation passed
    is_complete = (
        validation_details["total_entities"] > 0 and 
        len(validation_details["validation_errors"]) == 0
    )
    
    return is_complete, validation_details


def generate_data_summary(data: Any, source_type: str) -> Dict:
    """
    Generate a summary of collected data for reporting
    
    Args:
        data: Collected data
        source_type: Type of data source
        
    Returns:
        Dictionary with data summary metrics
    """
    summary = {
        "source_type": source_type,
        "timestamp": datetime.now().isoformat(),
        "data_present": data is not None and data != {},
        "summary_stats": {}
    }
    
    if not data:
        summary["summary_stats"]["total_entities"] = 0
        return summary
    
    if source_type == "slack":
        channels = count_entities_deterministic(data, "channels")
        messages = count_entities_deterministic(data, "messages") 
        users = count_entities_deterministic(data, "users")
        
        summary["summary_stats"] = {
            "channels": channels,
            "messages": messages, 
            "users": users,
            "avg_messages_per_channel": messages / channels if channels > 0 else 0
        }
    
    elif source_type == "calendar":
        calendars = len(data) if isinstance(data, dict) else 0
        events = count_entities_deterministic(data, "events")
        
        summary["summary_stats"] = {
            "calendars": calendars,
            "events": events,
            "avg_events_per_calendar": events / calendars if calendars > 0 else 0
        }
    
    elif source_type == "drive":
        if isinstance(data, dict) and 'changes' in data:
            changes = len(data['changes'])
        else:
            changes = count_entities_deterministic(data, "files")
        
        summary["summary_stats"] = {
            "total_changes": changes
        }
    
    return summary