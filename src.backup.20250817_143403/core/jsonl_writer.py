#!/usr/bin/env python3
"""
Centralized JSONL Writer for AI Chief of Staff Data Persistence
Provides simplified interface to ArchiveWriter for collector implementations
References: CLAUDE.md production quality commandments and existing ArchiveWriter patterns
"""

import json
import logging
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Union

from .archive_writer import ArchiveWriter, ArchiveError

# Configure logging
logger = logging.getLogger(__name__)


class JSONLWriter:
    """
    Centralized JSONL writer that provides simplified interface to ArchiveWriter
    for collector implementations to persist data in standardized JSONL format.
    
    Features:
    - Service-specific archive organization (slack/YYYY-MM-DD/, calendar/YYYY-MM-DD/, etc.)
    - Atomic write operations via existing ArchiveWriter
    - Automatic directory creation and date organization
    - Error handling and logging integration
    - Memory-efficient batch processing
    
    Usage:
        writer = JSONLWriter('slack')
        writer.write_messages(messages, channel_id)
        
        writer = JSONLWriter('calendar')  
        writer.write_events(events, calendar_id)
    """
    
    def __init__(self, service_name: str):
        """
        Initialize JSONL writer for specific service
        
        Args:
            service_name: Name of service (e.g., 'slack', 'calendar', 'drive')
            
        Raises:
            ArchiveError: If service name is invalid or ArchiveWriter creation fails
        """
        if not service_name or not service_name.strip():
            raise ArchiveError("Service name cannot be empty")
        
        self.service_name = service_name.strip().lower()
        self.archive_writer = ArchiveWriter(self.service_name)
        
        logger.info(f"JSONLWriter initialized for service '{self.service_name}'")
    
    def write_jsonl(self, data_list: List[Dict[str, Any]], target_date: Optional[date] = None) -> None:
        """
        Write list of data records to JSONL format
        
        Args:
            data_list: List of records to write (each must be JSON-serializable)
            target_date: Target date for archive (defaults to today)
            
        Raises:
            ArchiveError: If write operation fails
        """
        if not data_list:
            logger.debug(f"No data to write for service '{self.service_name}'")
            return
        
        # Validate all records before writing
        for i, record in enumerate(data_list):
            if not isinstance(record, dict):
                raise ArchiveError(f"Record {i} must be a dictionary, got {type(record)}")
        
        try:
            self.archive_writer.write_records(data_list, target_date)
            logger.info(f"Successfully wrote {len(data_list)} records to {self.service_name} archive")
            
        except Exception as e:
            error_msg = f"Failed to write {len(data_list)} records to {self.service_name} archive: {str(e)}"
            logger.error(error_msg)
            raise ArchiveError(error_msg) from e
    
    def append_jsonl(self, data: Dict[str, Any], target_date: Optional[date] = None) -> None:
        """
        Append single data record to JSONL format
        
        Args:
            data: Single record to append (must be JSON-serializable)
            target_date: Target date for archive (defaults to today)
            
        Raises:
            ArchiveError: If append operation fails
        """
        if not isinstance(data, dict):
            raise ArchiveError(f"Data must be a dictionary, got {type(data)}")
        
        self.write_jsonl([data], target_date)
    
    def create_archive_path(self, service: str, target_date: Optional[date] = None) -> Path:
        """
        Create standardized archive path for service and date
        
        Args:
            service: Service name (will be normalized to lowercase)
            target_date: Target date (defaults to today)
            
        Returns:
            Path to archive directory in format: data/archive/service/YYYY-MM-DD/
        """
        if target_date is None:
            target_date = date.today()
        
        # Create temporary writer to get path (reuses existing directory creation)
        temp_writer = ArchiveWriter(service.strip().lower())
        return temp_writer.get_archive_path(target_date)
    
    def write_messages_by_channel(self, messages_by_channel: Dict[str, List[Dict]], target_date: Optional[date] = None) -> Dict[str, int]:
        """
        Write messages organized by channel to separate JSONL files
        Specifically designed for Slack message persistence
        
        Args:
            messages_by_channel: Dictionary mapping channel_id -> list of messages
            target_date: Target date for archive (defaults to today)
            
        Returns:
            Dictionary mapping channel_id -> number of messages written
            
        Raises:
            ArchiveError: If write operation fails
        """
        if not messages_by_channel:
            logger.debug("No messages to write by channel")
            return {}
        
        results = {}
        total_messages = 0
        
        try:
            # Write all messages to main data.jsonl file with channel context
            all_messages = []
            for channel_id, messages in messages_by_channel.items():
                for message in messages:
                    # Add channel context to each message
                    message_with_context = dict(message)  # Don't modify original
                    message_with_context['_collection_context'] = {
                        'channel_id': channel_id,
                        'service': self.service_name,
                        'collected_at': datetime.now().isoformat()
                    }
                    all_messages.append(message_with_context)
                    
                results[channel_id] = len(messages)
                total_messages += len(messages)
            
            # Write all messages atomically
            self.write_jsonl(all_messages, target_date)
            
            logger.info(f"Successfully wrote {total_messages} messages across {len(messages_by_channel)} channels")
            return results
            
        except Exception as e:
            error_msg = f"Failed to write messages by channel: {str(e)}"
            logger.error(error_msg)
            raise ArchiveError(error_msg) from e
    
    def write_events_by_calendar(self, events_by_calendar: Dict[str, List[Dict]], target_date: Optional[date] = None) -> Dict[str, int]:
        """
        Write events organized by calendar to JSONL format
        Specifically designed for Calendar event persistence
        
        Args:
            events_by_calendar: Dictionary mapping calendar_id -> list of events  
            target_date: Target date for archive (defaults to today)
            
        Returns:
            Dictionary mapping calendar_id -> number of events written
            
        Raises:
            ArchiveError: If write operation fails
        """
        if not events_by_calendar:
            logger.debug("No events to write by calendar")
            return {}
        
        results = {}
        total_events = 0
        
        try:
            # Write all events to main data.jsonl file with calendar context
            all_events = []
            for calendar_id, events in events_by_calendar.items():
                for event in events:
                    # Add calendar context to each event
                    event_with_context = dict(event)  # Don't modify original
                    event_with_context['_collection_context'] = {
                        'calendar_id': calendar_id,
                        'service': self.service_name,
                        'collected_at': datetime.now().isoformat()
                    }
                    all_events.append(event_with_context)
                    
                results[calendar_id] = len(events)
                total_events += len(events)
            
            # Write all events atomically
            self.write_jsonl(all_events, target_date)
            
            logger.info(f"Successfully wrote {total_events} events across {len(events_by_calendar)} calendars")
            return results
            
        except Exception as e:
            error_msg = f"Failed to write events by calendar: {str(e)}"
            logger.error(error_msg)
            raise ArchiveError(error_msg) from e
    
    def write_files_metadata(self, files_metadata: List[Dict], target_date: Optional[date] = None) -> int:
        """
        Write file metadata for Drive collector
        Specifically designed for Drive metadata persistence (no content)
        
        Args:
            files_metadata: List of file metadata dictionaries
            target_date: Target date for archive (defaults to today)
            
        Returns:
            Number of file metadata records written
            
        Raises:
            ArchiveError: If write operation fails
        """
        if not files_metadata:
            logger.debug("No file metadata to write")
            return 0
        
        try:
            # Add service context to metadata
            enriched_metadata = []
            for file_meta in files_metadata:
                enriched_meta = dict(file_meta)  # Don't modify original
                enriched_meta['_collection_context'] = {
                    'service': self.service_name,
                    'collected_at': datetime.now().isoformat(),
                    'content_included': False  # Drive collector is metadata-only
                }
                enriched_metadata.append(enriched_meta)
            
            # Write all metadata atomically
            self.write_jsonl(enriched_metadata, target_date)
            
            logger.info(f"Successfully wrote {len(files_metadata)} file metadata records")
            return len(files_metadata)
            
        except Exception as e:
            error_msg = f"Failed to write file metadata: {str(e)}"
            logger.error(error_msg)
            raise ArchiveError(error_msg) from e
    
    def get_archive_stats(self, target_date: Optional[date] = None) -> Dict[str, Any]:
        """
        Get statistics about the archive for given date
        
        Args:
            target_date: Target date (defaults to today)
            
        Returns:
            Dictionary with archive statistics
        """
        try:
            metadata = self.archive_writer.get_metadata(target_date)
            
            # Add some additional context
            archive_path = self.archive_writer.get_archive_path(target_date)
            data_file = self.archive_writer.get_data_file_path(target_date)
            
            stats = {
                'service': self.service_name,
                'archive_date': (target_date or date.today()).isoformat(),
                'archive_path': str(archive_path),
                'data_file_exists': data_file.exists(),
                'metadata': metadata
            }
            
            return stats
            
        except Exception as e:
            logger.warning(f"Failed to get archive stats: {e}")
            return {
                'service': self.service_name,
                'archive_date': (target_date or date.today()).isoformat(),
                'error': str(e)
            }
    
    def read_records(self, target_date: Optional[date] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Read records from archive for given date
        
        Args:
            target_date: Target date (defaults to today)
            limit: Maximum number of records to read (None = all)
            
        Returns:
            List of records from the archive
        """
        try:
            return self.archive_writer.read_records(target_date, limit)
        except Exception as e:
            logger.error(f"Failed to read records from {self.service_name} archive: {e}")
            return []
    
    def __repr__(self) -> str:
        """String representation"""
        return f"JSONLWriter(service='{self.service_name}')"


# Convenience functions for common use cases

def create_slack_writer() -> JSONLWriter:
    """Create JSONLWriter for Slack service"""
    return JSONLWriter('slack')

def create_calendar_writer() -> JSONLWriter:
    """Create JSONLWriter for Calendar service"""
    return JSONLWriter('calendar')

def create_drive_writer() -> JSONLWriter:
    """Create JSONLWriter for Drive service"""
    return JSONLWriter('drive')

def create_employee_writer() -> JSONLWriter:
    """Create JSONLWriter for Employee service"""
    return JSONLWriter('employee')


# Export main classes and convenience functions
__all__ = [
    'JSONLWriter',
    'create_slack_writer',
    'create_calendar_writer', 
    'create_drive_writer',
    'create_employee_writer'
]