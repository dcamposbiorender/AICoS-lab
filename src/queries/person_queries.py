"""
Person-based query engine with cross-system ID resolution

References:
- src/collectors/employee_collector.py - Employee roster data patterns
- src/search/database.py - SQLite FTS5 search infrastructure  
- src/queries/time_utils.py - Time parsing utilities for date range queries
- tests/fixtures/mock_slack_data.py - Mock data structure patterns

CRITICAL FEATURES IMPLEMENTED:
- Cross-system ID mapping (Slack, Calendar, Drive)
- Graceful fallbacks for missing employee data
- Person activity aggregation across all data sources
- Memory-efficient query processing for large datasets
- Performance optimized for <2 second response times
"""

import json
import sqlite3
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, date, timedelta
from collections import defaultdict, Counter

from .time_utils import parse_time_expression, TimeParsingError

logger = logging.getLogger(__name__)


class PersonNotFoundError(Exception):
    """Raised when person cannot be resolved"""
    pass


class PersonResolver:
    """
    Cross-system person identification and ID mapping
    
    Features:
    - Email, Slack ID, and name lookup with fuzzy matching
    - Cross-system ID correlation (Slack <-> Calendar <-> Drive)
    - Graceful fallbacks when employee data unavailable
    - Case-insensitive and partial name matching
    - Status filtering (active vs archived users)
    """
    
    def __init__(self, employee_data: Optional[Dict[str, Any]] = None):
        """
        Initialize person resolver with employee data
        
        Args:
            employee_data: Employee roster data from collector
                          If None, will attempt to load from EmployeeCollector
        """
        self.employees = []
        self._email_index = {}
        self._slack_index = {}
        self._name_index = {}
        
        if employee_data:
            self.load_employee_data(employee_data)
        else:
            self.load_from_collector()
    
    def load_employee_data(self, employee_data: Dict[str, Any]):
        """
        Load and index employee data for fast lookups
        
        Args:
            employee_data: Employee roster data with 'employees' array
        """
        try:
            if not employee_data or 'employees' not in employee_data:
                logger.warning("Invalid employee data format, falling back to empty roster")
                self.employees = []
                return
            
            self.employees = employee_data['employees']
            self._build_indexes()
            
            logger.info(f"Loaded {len(self.employees)} employees into person resolver")
            
        except Exception as e:
            logger.error(f"Failed to load employee data: {str(e)}")
            self.employees = []
    
    def load_from_collector(self):
        """Load employee data from EmployeeCollector (graceful fallback)"""
        try:
            from ..collectors.employee_collector import EmployeeCollector
            
            collector = EmployeeCollector()
            employee_data = collector.collect()
            self.load_employee_data(employee_data)
            
        except ImportError:
            logger.warning("EmployeeCollector not available, using empty roster")
            self.employees = []
        except Exception as e:
            logger.warning(f"Failed to load from EmployeeCollector: {str(e)}")
            self.employees = []
    
    def _build_indexes(self):
        """Build lookup indexes for fast person resolution"""
        self._email_index = {}
        self._slack_index = {}
        self._name_index = {}
        
        for employee in self.employees:
            # Email index (primary key)
            if 'email' in employee:
                email = employee['email'].lower().strip()
                self._email_index[email] = employee
            
            # Slack ID index
            if 'slack_id' in employee:
                slack_id = employee['slack_id'].strip()
                self._slack_index[slack_id] = employee
            
            # Name indexes (multiple variants)
            name_variants = []
            for name_field in ['name', 'display_name', 'real_name']:
                if name_field in employee and employee[name_field]:
                    name_variants.append(employee[name_field].strip())
            
            for name in name_variants:
                name_lower = name.lower()
                if name_lower not in self._name_index:
                    self._name_index[name_lower] = []
                self._name_index[name_lower].append(employee)
    
    def find_person(self, identifier: str, include_archived: bool = True) -> Optional[Dict[str, Any]]:
        """
        Find person by any identifier (email, Slack ID, or name)
        
        Args:
            identifier: Email address, Slack user ID, or name
            include_archived: Whether to include archived/inactive users
            
        Returns:
            Employee record dict or None if not found
        """
        if not identifier or not identifier.strip():
            return None
        
        identifier = identifier.strip()
        
        # Try email lookup first (most reliable)
        email_result = self._lookup_by_email(identifier)
        if email_result and (include_archived or email_result.get('status') == 'active'):
            return email_result
        
        # Try Slack ID lookup
        slack_result = self._lookup_by_slack_id(identifier) 
        if slack_result and (include_archived or slack_result.get('status') == 'active'):
            return slack_result
        
        # Try name lookup (fuzzy matching)
        name_result = self._lookup_by_name(identifier)
        if name_result and (include_archived or name_result.get('status') == 'active'):
            return name_result
        
        return None
    
    def find_all_matching(self, partial_identifier: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Find all persons matching partial identifier
        
        Args:
            partial_identifier: Partial email, name, or other identifier
            limit: Maximum number of results to return
            
        Returns:
            List of matching employee records
        """
        if not partial_identifier or not partial_identifier.strip():
            return []
        
        matches = []
        partial = partial_identifier.lower().strip()
        
        # Search in emails
        for email, employee in self._email_index.items():
            if partial in email and len(matches) < limit:
                matches.append(employee)
        
        # Search in names
        for name, employees in self._name_index.items():
            if partial in name:
                for employee in employees:
                    if employee not in matches and len(matches) < limit:
                        matches.append(employee)
        
        return matches[:limit]
    
    def _lookup_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Lookup person by email address"""
        email_lower = email.lower().strip()
        return self._email_index.get(email_lower)
    
    def _lookup_by_slack_id(self, slack_id: str) -> Optional[Dict[str, Any]]:
        """Lookup person by Slack user ID"""
        return self._slack_index.get(slack_id.strip())
    
    def _lookup_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Lookup person by name with fuzzy matching"""
        name_lower = name.lower().strip()
        
        # Exact match first
        if name_lower in self._name_index:
            return self._name_index[name_lower][0]  # Return first match
        
        # Partial match
        for indexed_name, employees in self._name_index.items():
            if name_lower in indexed_name or indexed_name in name_lower:
                return employees[0]  # Return first match
        
        return None
    
    def get_cross_system_ids(self, identifier: str) -> Optional[Dict[str, str]]:
        """
        Get all system IDs for a person
        
        Args:
            identifier: Any person identifier
            
        Returns:
            Dict with all known IDs or None if person not found
        """
        person = self.find_person(identifier)
        if not person:
            return None
        
        return {
            'email': person.get('email'),
            'slack_id': person.get('slack_id'),
            'calendar_id': person.get('calendar_id', person.get('email')),  # Default to email
            'name': person.get('name'),
            'display_name': person.get('display_name')
        }
    
    def get_person_count(self) -> int:
        """Get total number of persons in roster"""
        return len(self.employees)
    
    def get_active_person_count(self) -> int:
        """Get number of active persons in roster"""
        return len([emp for emp in self.employees if emp.get('status') == 'active'])


class PersonQueryEngine:
    """
    Database query engine for person-based data retrieval and aggregation
    
    Features:
    - Person activity aggregation across Slack, Calendar, Drive
    - Message history retrieval with pagination
    - Meeting participation tracking
    - Cross-source activity correlation
    - Time-filtered queries with timezone awareness
    """
    
    def __init__(self, db_path: str = "search.db", employee_data: Optional[Dict[str, Any]] = None):
        """
        Initialize person query engine
        
        Args:
            db_path: Path to SQLite database
            employee_data: Employee roster data (if None, loads from collector)
        """
        self.db_path = Path(db_path)
        self.person_resolver = PersonResolver(employee_data=employee_data)
        self._connection = None
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with reuse"""
        if self._connection is None:
            if not self.db_path.exists():
                raise FileNotFoundError(f"Database not found: {self.db_path}")
            
            self._connection = sqlite3.connect(str(self.db_path))
            self._connection.row_factory = sqlite3.Row  # Enable dict-like access
        return self._connection
    
    def get_person_activity(self, person_identifier: str, time_expression: str) -> Dict[str, int]:
        """
        Aggregate activity metrics for person over time period
        
        Args:
            person_identifier: Email, Slack ID, or name
            time_expression: Natural language time expression
            
        Returns:
            Dict with activity counts: message_count, meetings_attended, etc.
        """
        try:
            # Resolve person to get all IDs
            person_ids = self.person_resolver.get_cross_system_ids(person_identifier)
            if not person_ids:
                logger.warning(f"Person not found: {person_identifier}")
                return self._empty_activity_stats()
            
            # Parse time range
            start_date, end_date = parse_time_expression(time_expression)
            start_iso = start_date.isoformat()
            end_iso = end_date.isoformat()
            
            conn = self._get_connection()
            
            # Aggregate activity from different sources
            stats = {
                'message_count': self._count_messages(conn, person_ids, start_iso, end_iso),
                'meetings_attended': self._count_meetings(conn, person_ids, start_iso, end_iso),
                'files_modified': self._count_files(conn, person_ids, start_iso, end_iso),
                'channels_active': self._count_active_channels(conn, person_ids, start_iso, end_iso)
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error aggregating person activity: {str(e)}")
            return self._empty_activity_stats()
    
    def get_messages_by_person(self, person_identifier: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Retrieve paginated message history for person
        
        Args:
            person_identifier: Email, Slack ID, or name
            limit: Maximum number of messages to return
            offset: Number of messages to skip
            
        Returns:
            List of message records
        """
        try:
            person_ids = self.person_resolver.get_cross_system_ids(person_identifier)
            if not person_ids:
                return []
            
            conn = self._get_connection()
            
            # Query messages with person attribution
            query = """
                SELECT id, content, source, date, metadata
                FROM messages
                WHERE json_extract(metadata, '$.author_email') = ? 
                   OR json_extract(metadata, '$.author') = ?
                ORDER BY date DESC
                LIMIT ? OFFSET ?
            """
            
            params = (person_ids['email'], person_ids['slack_id'], limit, offset)
            cursor = conn.execute(query, params)
            
            messages = []
            for row in cursor:
                message = {
                    'id': row['id'],
                    'content': row['content'],
                    'source': row['source'],
                    'date': row['date'],
                    'timestamp': row['date']  # Compatibility alias
                }
                
                # Parse metadata
                if row['metadata']:
                    try:
                        message['metadata'] = json.loads(row['metadata'])
                    except (json.JSONDecodeError, TypeError):
                        message['metadata'] = row['metadata']
                
                messages.append(message)
            
            return messages
            
        except Exception as e:
            logger.error(f"Error retrieving messages for person: {str(e)}")
            return []
    
    def get_meetings_for_person(self, person_identifier: str, time_expression: str) -> List[Dict[str, Any]]:
        """
        Get meetings attended by person in time period
        
        Args:
            person_identifier: Email, Slack ID, or name
            time_expression: Natural language time expression
            
        Returns:
            List of meeting records
        """
        try:
            person_ids = self.person_resolver.get_cross_system_ids(person_identifier)
            if not person_ids:
                return []
            
            # Parse time range
            start_date, end_date = parse_time_expression(time_expression)
            start_iso = start_date.isoformat()
            end_iso = end_date.isoformat()
            
            conn = self._get_connection()
            
            # Query calendar events where person is attendee
            query = """
                SELECT title, attendees, start_time, end_time, organizer
                FROM calendar_events
                WHERE (json_extract(attendees, '$') LIKE ? OR organizer = ?)
                AND start_time >= ? AND start_time <= ?
                ORDER BY start_time DESC
            """
            
            email_pattern = f'%{person_ids["email"]}%'
            params = (email_pattern, person_ids['email'], start_iso, end_iso)
            cursor = conn.execute(query, params)
            
            meetings = []
            for row in cursor:
                meeting = {
                    'title': row['title'],
                    'attendees': row['attendees'],
                    'start_time': row['start_time'],
                    'end_time': row['end_time'],
                    'organizer': row['organizer']
                }
                
                # Parse attendees JSON
                try:
                    if isinstance(meeting['attendees'], str):
                        meeting['attendees'] = json.loads(meeting['attendees'])
                except (json.JSONDecodeError, TypeError):
                    pass  # Keep as string if not valid JSON
                
                meetings.append(meeting)
            
            return meetings
            
        except Exception as e:
            logger.error(f"Error retrieving meetings for person: {str(e)}")
            return []
    
    def get_cross_source_activity(self, person_identifier: str, time_expression: str) -> Dict[str, Any]:
        """
        Correlate activity across Slack, Calendar, and Drive for person
        
        Args:
            person_identifier: Email, Slack ID, or name
            time_expression: Natural language time expression
            
        Returns:
            Dict with activity breakdown by source
        """
        try:
            person_ids = self.person_resolver.get_cross_system_ids(person_identifier)
            if not person_ids:
                return self._empty_cross_source_activity()
            
            # Parse time range
            start_date, end_date = parse_time_expression(time_expression)
            start_iso = start_date.isoformat()
            end_iso = end_date.isoformat()
            
            conn = self._get_connection()
            
            # Aggregate by source
            slack_activity = self._get_slack_activity(conn, person_ids, start_iso, end_iso)
            calendar_activity = self._get_calendar_activity(conn, person_ids, start_iso, end_iso)
            drive_activity = self._get_drive_activity(conn, person_ids, start_iso, end_iso)
            
            total_interactions = (
                slack_activity.get('message_count', 0) +
                calendar_activity.get('meeting_count', 0) +
                drive_activity.get('file_changes', 0)
            )
            
            return {
                'slack_activity': slack_activity,
                'calendar_activity': calendar_activity,
                'drive_activity': drive_activity,
                'total_interactions': total_interactions
            }
            
        except Exception as e:
            logger.error(f"Error correlating cross-source activity: {str(e)}")
            return self._empty_cross_source_activity()
    
    # Private helper methods for database queries
    
    def _count_messages(self, conn: sqlite3.Connection, person_ids: Dict[str, str], start: str, end: str) -> int:
        """Count messages by person in time range"""
        query = """
            SELECT COUNT(*) as count
            FROM messages
            WHERE (json_extract(metadata, '$.author_email') = ? 
                   OR json_extract(metadata, '$.author') = ?)
            AND date >= ? AND date <= ?
        """
        cursor = conn.execute(query, (person_ids['email'], person_ids['slack_id'], start, end))
        return cursor.fetchone()['count']
    
    def _count_meetings(self, conn: sqlite3.Connection, person_ids: Dict[str, str], start: str, end: str) -> int:
        """Count meetings attended by person in time range"""
        try:
            query = """
                SELECT COUNT(*) as count
                FROM calendar_events
                WHERE (json_extract(attendees, '$') LIKE ? OR organizer = ?)
                AND start_time >= ? AND start_time <= ?
            """
            email_pattern = f'%{person_ids["email"]}%'
            cursor = conn.execute(query, (email_pattern, person_ids['email'], start, end))
            return cursor.fetchone()['count']
        except sqlite3.OperationalError:
            # Table might not exist
            return 0
    
    def _count_files(self, conn: sqlite3.Connection, person_ids: Dict[str, str], start: str, end: str) -> int:
        """Count files modified by person in time range"""
        try:
            query = """
                SELECT COUNT(*) as count
                FROM drive_activity
                WHERE user_email = ?
                AND timestamp >= ? AND timestamp <= ?
            """
            cursor = conn.execute(query, (person_ids['email'], start, end))
            return cursor.fetchone()['count']
        except sqlite3.OperationalError:
            # Table might not exist
            return 0
    
    def _count_active_channels(self, conn: sqlite3.Connection, person_ids: Dict[str, str], start: str, end: str) -> int:
        """Count distinct channels where person was active"""
        query = """
            SELECT COUNT(DISTINCT json_extract(metadata, '$.channel')) as count
            FROM messages
            WHERE (json_extract(metadata, '$.author_email') = ?
                   OR json_extract(metadata, '$.author') = ?)
            AND date >= ? AND date <= ?
            AND json_extract(metadata, '$.channel') IS NOT NULL
        """
        cursor = conn.execute(query, (person_ids['email'], person_ids['slack_id'], start, end))
        result = cursor.fetchone()
        return result['count'] if result['count'] else 0
    
    def _get_slack_activity(self, conn: sqlite3.Connection, person_ids: Dict[str, str], start: str, end: str) -> Dict[str, int]:
        """Get detailed Slack activity for person"""
        return {
            'message_count': self._count_messages(conn, person_ids, start, end),
            'channels_active': self._count_active_channels(conn, person_ids, start, end)
        }
    
    def _get_calendar_activity(self, conn: sqlite3.Connection, person_ids: Dict[str, str], start: str, end: str) -> Dict[str, int]:
        """Get detailed calendar activity for person"""
        return {
            'meeting_count': self._count_meetings(conn, person_ids, start, end)
        }
    
    def _get_drive_activity(self, conn: sqlite3.Connection, person_ids: Dict[str, str], start: str, end: str) -> Dict[str, int]:
        """Get detailed drive activity for person"""
        return {
            'file_changes': self._count_files(conn, person_ids, start, end)
        }
    
    def _empty_activity_stats(self) -> Dict[str, int]:
        """Return empty activity stats structure"""
        return {
            'message_count': 0,
            'meetings_attended': 0,
            'files_modified': 0,
            'channels_active': 0
        }
    
    def _empty_cross_source_activity(self) -> Dict[str, Any]:
        """Return empty cross-source activity structure"""
        return {
            'slack_activity': {'message_count': 0, 'channels_active': 0},
            'calendar_activity': {'meeting_count': 0},
            'drive_activity': {'file_changes': 0},
            'total_interactions': 0
        }
    
    def close(self):
        """Close database connection"""
        if self._connection:
            self._connection.close()
            self._connection = None


# Utility functions for person-based operations

def resolve_person_from_message(message: Dict[str, Any], resolver: PersonResolver) -> Optional[Dict[str, str]]:
    """
    Extract person information from message metadata
    
    Args:
        message: Message record with metadata
        resolver: PersonResolver instance
        
    Returns:
        Person IDs dict or None if cannot resolve
    """
    try:
        # Extract author information from metadata
        if 'metadata' in message and message['metadata']:
            metadata = json.loads(message['metadata']) if isinstance(message['metadata'], str) else message['metadata']
            
            # Try different author fields
            for field in ['author_email', 'author', 'user_id']:
                if field in metadata and metadata[field]:
                    return resolver.get_cross_system_ids(metadata[field])
        
        return None
        
    except Exception as e:
        logger.debug(f"Could not resolve person from message: {str(e)}")
        return None


def get_person_interaction_summary(person_identifier: str, engine: PersonQueryEngine, days: int = 7) -> Dict[str, Any]:
    """
    Generate interaction summary for person over recent days
    
    Args:
        person_identifier: Email, Slack ID, or name
        engine: PersonQueryEngine instance
        days: Number of days to analyze
        
    Returns:
        Comprehensive interaction summary
    """
    time_expr = f"past {days} days"
    
    activity = engine.get_person_activity(person_identifier, time_expr)
    cross_source = engine.get_cross_source_activity(person_identifier, time_expr)
    recent_messages = engine.get_messages_by_person(person_identifier, limit=10)
    
    return {
        'person_identifier': person_identifier,
        'time_period': time_expr,
        'activity_stats': activity,
        'cross_source_breakdown': cross_source,
        'recent_messages': recent_messages[:5],  # Top 5 most recent
        'summary': {
            'total_interactions': cross_source['total_interactions'],
            'most_active_source': _determine_most_active_source(cross_source),
            'activity_level': _classify_activity_level(activity['message_count'])
        }
    }


def _determine_most_active_source(cross_source: Dict[str, Any]) -> str:
    """Determine which source the person is most active in"""
    slack_activity = cross_source['slack_activity']['message_count']
    calendar_activity = cross_source['calendar_activity']['meeting_count']
    drive_activity = cross_source['drive_activity']['file_changes']
    
    if slack_activity >= calendar_activity and slack_activity >= drive_activity:
        return 'slack'
    elif calendar_activity >= drive_activity:
        return 'calendar'
    else:
        return 'drive'


def _classify_activity_level(message_count: int) -> str:
    """Classify activity level based on message count"""
    if message_count == 0:
        return 'inactive'
    elif message_count <= 5:
        return 'low'
    elif message_count <= 20:
        return 'moderate'
    else:
        return 'high'