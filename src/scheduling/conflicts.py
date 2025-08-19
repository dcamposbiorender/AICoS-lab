"""
Calendar Conflict Detection System - Timezone-Aware Meeting Overlap Detection
CRITICAL: All datetime operations use timezone-aware objects

References:
- src/scheduling/availability.py - Timezone normalization patterns
- src/core/compression.py - Error handling patterns
"""

import pytz
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Conflict:
    """Represents a scheduling conflict between events"""
    event1: Dict[str, Any]
    event2: Dict[str, Any]
    overlap_minutes: int
    conflict_type: str
    severity: float  # 0.0 to 1.0
    affected_attendees: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'event1_id': self.event1.get('id', 'unknown'),
            'event1_summary': self.event1.get('summary', 'Unknown Event'),
            'event2_id': self.event2.get('id', 'unknown'),
            'event2_summary': self.event2.get('summary', 'Unknown Event'),
            'overlap_minutes': self.overlap_minutes,
            'conflict_type': self.conflict_type,
            'severity': self.severity,
            'affected_attendees': self.affected_attendees,
            'event1_start': self.event1.get('start', {}).get('dateTime') if isinstance(self.event1.get('start'), dict) else str(self.event1.get('start')),
            'event2_start': self.event2.get('start', {}).get('dateTime') if isinstance(self.event2.get('start'), dict) else str(self.event2.get('start'))
        }


class ConflictDetector:
    """
    CRITICAL FIX: Timezone-aware meeting conflict detection system
    Detects overlapping meetings, double-booking, and resource conflicts
    """
    
    def __init__(self):
        """Initialize conflict detector with timezone safety"""
        self.logger = logging.getLogger(__name__ + '.ConflictDetector')
        self._validate_pytz_available()
    
    def _validate_pytz_available(self):
        """Ensure pytz is available for timezone operations"""
        try:
            pytz.UTC
        except AttributeError:
            raise ImportError("pytz library is required for timezone-aware operations")
    
    def has_conflict(
        self, 
        event1: Dict[str, Any], 
        event2: Dict[str, Any],
        timezone: str = 'UTC'
    ) -> bool:
        """
        Check if two events have a time conflict
        CRITICAL: Uses timezone normalization for accurate comparison
        
        Args:
            event1: First event
            event2: Second event
            timezone: Reference timezone for comparison
            
        Returns:
            True if events overlap in time
        """
        # Normalize both events to same timezone
        norm_event1 = self._normalize_event_to_timezone(event1, timezone)
        norm_event2 = self._normalize_event_to_timezone(event2, timezone)
        
        if not norm_event1 or not norm_event2:
            return False
        
        start1 = norm_event1.get('start')
        end1 = norm_event1.get('end')
        start2 = norm_event2.get('start')
        end2 = norm_event2.get('end')
        
        if not all([start1, end1, start2, end2]):
            return False
        
        # Check for overlap: events overlap if start1 < end2 and start2 < end1
        return start1 < end2 and start2 < end1
    
    def overlap_minutes(
        self, 
        event1: Dict[str, Any], 
        event2: Dict[str, Any],
        timezone: str = 'UTC'
    ) -> int:
        """
        Calculate overlap duration between two events in minutes
        CRITICAL: Uses timezone-aware datetime arithmetic
        
        Args:
            event1: First event
            event2: Second event
            timezone: Reference timezone for calculation
            
        Returns:
            Overlap duration in minutes, 0 if no overlap
        """
        if not self.has_conflict(event1, event2, timezone):
            return 0
        
        # Normalize events to same timezone
        norm_event1 = self._normalize_event_to_timezone(event1, timezone)
        norm_event2 = self._normalize_event_to_timezone(event2, timezone)
        
        if not norm_event1 or not norm_event2:
            return 0
        
        start1 = norm_event1.get('start')
        end1 = norm_event1.get('end')
        start2 = norm_event2.get('start')
        end2 = norm_event2.get('end')
        
        # Calculate overlap period
        overlap_start = max(start1, start2)
        overlap_end = min(end1, end2)
        
        if overlap_start >= overlap_end:
            return 0
        
        overlap_duration = overlap_end - overlap_start
        return int(overlap_duration.total_seconds() / 60)
    
    def find_attendee_conflicts(
        self, 
        events: List[Dict[str, Any]],
        timezone: str = 'UTC'
    ) -> List[Dict[str, Any]]:
        """
        Find attendees who are double-booked across events
        CRITICAL: Handles timezone normalization for accurate conflict detection
        
        Args:
            events: List of events to check
            timezone: Reference timezone for comparison
            
        Returns:
            List of conflicts with attendee information
        """
        conflicts = []
        attendee_conflicts = {}  # attendee -> list of conflicting events
        
        # Normalize all events first
        normalized_events = []
        for event in events:
            norm_event = self._normalize_event_to_timezone(event, timezone)
            if norm_event:
                normalized_events.append((event, norm_event))  # Keep both original and normalized
        
        # Check each pair of events for conflicts
        for i in range(len(normalized_events)):
            for j in range(i + 1, len(normalized_events)):
                orig_event1, norm_event1 = normalized_events[i]
                orig_event2, norm_event2 = normalized_events[j]
                
                if self.has_conflict(norm_event1, norm_event2, timezone):
                    # Find common attendees
                    attendees1 = set(self._extract_attendee_emails(orig_event1))
                    attendees2 = set(self._extract_attendee_emails(orig_event2))
                    common_attendees = attendees1.intersection(attendees2)
                    
                    # Record conflicts for each common attendee
                    for attendee in common_attendees:
                        if attendee not in attendee_conflicts:
                            attendee_conflicts[attendee] = []
                        attendee_conflicts[attendee].extend([orig_event1, orig_event2])
        
        # Convert to conflict format
        for attendee, conflicted_events in attendee_conflicts.items():
            # Remove duplicates while preserving order
            unique_events = []
            seen_ids = set()
            for event in conflicted_events:
                event_id = event.get('id', str(hash(str(event))))
                if event_id not in seen_ids:
                    unique_events.append(event)
                    seen_ids.add(event_id)
            
            if len(unique_events) > 1:
                conflicts.append({
                    'person': attendee,
                    'meetings': unique_events,
                    'conflict_count': len(unique_events)
                })
        
        self.logger.info(f"Found attendee conflicts for {len(conflicts)} people")
        return conflicts
    
    def detect_all_conflicts(
        self, 
        events: List[Dict[str, Any]],
        timezone: str = 'UTC',
        include_resource_conflicts: bool = True
    ) -> List[Conflict]:
        """
        Comprehensive conflict detection across all event types
        
        Args:
            events: List of events to analyze
            timezone: Reference timezone for comparison
            include_resource_conflicts: Whether to check for room/resource conflicts
            
        Returns:
            List of detected conflicts with severity scoring
        """
        all_conflicts = []
        
        # Normalize all events first for consistent processing
        normalized_events = []
        for event in events:
            norm_event = self._normalize_event_to_timezone(event, timezone)
            if norm_event:
                normalized_events.append((event, norm_event))
        
        # Check all event pairs for time conflicts
        for i in range(len(normalized_events)):
            for j in range(i + 1, len(normalized_events)):
                orig_event1, norm_event1 = normalized_events[i]
                orig_event2, norm_event2 = normalized_events[j]
                
                if self.has_conflict(norm_event1, norm_event2, timezone):
                    overlap_mins = self.overlap_minutes(norm_event1, norm_event2, timezone)
                    
                    # Determine conflict type and severity
                    conflict_type, severity = self._classify_conflict(orig_event1, orig_event2, overlap_mins)
                    
                    # Find affected attendees
                    attendees1 = set(self._extract_attendee_emails(orig_event1))
                    attendees2 = set(self._extract_attendee_emails(orig_event2))
                    affected = list(attendees1.intersection(attendees2))
                    
                    conflict = Conflict(
                        event1=orig_event1,
                        event2=orig_event2,
                        overlap_minutes=overlap_mins,
                        conflict_type=conflict_type,
                        severity=severity,
                        affected_attendees=affected
                    )
                    all_conflicts.append(conflict)
        
        # Add resource conflicts if requested
        if include_resource_conflicts:
            resource_conflicts = self._detect_resource_conflicts(events, timezone)
            all_conflicts.extend(resource_conflicts)
        
        # Sort by severity (highest first)
        all_conflicts.sort(key=lambda c: c.severity, reverse=True)
        
        self.logger.info(f"Detected {len(all_conflicts)} total conflicts")
        return all_conflicts
    
    def _normalize_event_to_timezone(
        self, 
        event: Dict[str, Any], 
        target_timezone: str
    ) -> Optional[Dict[str, Any]]:
        """
        Normalize event datetime fields to target timezone
        CRITICAL FIX: Handles timezone conversion safely
        
        Args:
            event: Event dictionary
            target_timezone: Target timezone string
            
        Returns:
            Event with normalized datetimes or None if invalid
        """
        if not event:
            return None
        
        try:
            target_tz = pytz.timezone(target_timezone)
        except pytz.exceptions.UnknownTimeZoneError:
            self.logger.warning(f"Invalid target timezone: {target_timezone}")
            return None
        
        normalized = dict(event)  # Don't modify original
        
        # Process start and end times
        for field in ['start', 'end']:
            dt_value = event.get(field)
            if dt_value:
                normalized_dt = self._normalize_datetime_field(dt_value, target_tz, event.get('timezone'))
                if normalized_dt:
                    normalized[field] = normalized_dt
                else:
                    return None  # Invalid datetime
        
        return normalized
    
    def _normalize_datetime_field(
        self, 
        dt_value: Any, 
        target_tz: pytz.timezone,
        source_timezone: Optional[str] = None
    ) -> Optional[datetime]:
        """
        Normalize a single datetime field to target timezone
        CRITICAL: Consistent with availability.py patterns
        
        Args:
            dt_value: Datetime value (various formats)
            target_tz: Target timezone
            source_timezone: Source timezone hint
            
        Returns:
            Normalized timezone-aware datetime or None if invalid
        """
        if isinstance(dt_value, datetime):
            # Handle datetime objects
            if dt_value.tzinfo is None:
                # Naive datetime - try to localize
                if source_timezone:
                    try:
                        source_tz = pytz.timezone(source_timezone)
                        dt_value = source_tz.localize(dt_value)
                    except pytz.exceptions.UnknownTimeZoneError:
                        dt_value = pytz.UTC.localize(dt_value)
                else:
                    dt_value = pytz.UTC.localize(dt_value)
            
            return dt_value.astimezone(target_tz)
        
        elif isinstance(dt_value, str):
            # Handle ISO string format
            try:
                dt = datetime.fromisoformat(dt_value.replace('Z', '+00:00'))
                if dt.tzinfo is None:
                    dt = pytz.UTC.localize(dt)
                return dt.astimezone(target_tz)
            except ValueError:
                return None
        
        elif isinstance(dt_value, dict):
            # Handle Google Calendar API format
            if 'dateTime' in dt_value:
                try:
                    dt_str = dt_value['dateTime']
                    dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
                    if dt.tzinfo is None and 'timeZone' in dt_value:
                        tz = pytz.timezone(dt_value['timeZone'])
                        dt = tz.localize(dt)
                    elif dt.tzinfo is None:
                        dt = pytz.UTC.localize(dt)
                    return dt.astimezone(target_tz)
                except (ValueError, pytz.exceptions.UnknownTimeZoneError):
                    return None
            elif 'date' in dt_value:
                # All-day event
                try:
                    from datetime import time
                    date_str = dt_value['date']
                    date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                    return target_tz.localize(datetime.combine(date_obj, time.min))
                except ValueError:
                    return None
        
        return None
    
    def _extract_attendee_emails(self, event: Dict[str, Any]) -> List[str]:
        """Extract attendee email addresses from event"""
        attendees = event.get('attendees', [])
        if not isinstance(attendees, list):
            return []
        
        emails = []
        for attendee in attendees:
            if isinstance(attendee, dict):
                email = attendee.get('email')
                if email and isinstance(email, str):
                    emails.append(email.lower().strip())
            elif isinstance(attendee, str):
                # Handle case where attendees is just a list of emails
                emails.append(attendee.lower().strip())
        
        return emails
    
    def _classify_conflict(
        self, 
        event1: Dict[str, Any], 
        event2: Dict[str, Any], 
        overlap_minutes: int
    ) -> Tuple[str, float]:
        """
        Classify conflict type and calculate severity score
        
        Args:
            event1: First event
            event2: Second event
            overlap_minutes: Minutes of overlap
            
        Returns:
            (conflict_type, severity_score)
        """
        # Determine conflict type
        attendees1 = set(self._extract_attendee_emails(event1))
        attendees2 = set(self._extract_attendee_emails(event2))
        common_attendees = attendees1.intersection(attendees2)
        
        location1 = event1.get('location', '').lower()
        location2 = event2.get('location', '').lower()
        
        if common_attendees and location1 == location2 and location1:
            conflict_type = "person_and_resource"
        elif common_attendees:
            conflict_type = "person_double_booking"
        elif location1 == location2 and location1 and 'room' in location1:
            conflict_type = "resource_double_booking"
        else:
            conflict_type = "time_overlap"
        
        # Calculate severity (0.0 to 1.0)
        severity = 0.0
        
        # Base severity from overlap duration
        if overlap_minutes > 0:
            severity = min(overlap_minutes / 60.0, 1.0)  # Normalize to hours, cap at 1.0
        
        # Increase severity for person conflicts
        if common_attendees:
            severity = min(severity + 0.3, 1.0)
        
        # Increase severity for complete overlaps
        duration1 = self._get_event_duration_minutes(event1)
        duration2 = self._get_event_duration_minutes(event2)
        if duration1 and duration2:
            max_duration = max(duration1, duration2)
            if overlap_minutes >= max_duration * 0.8:  # 80%+ overlap
                severity = min(severity + 0.2, 1.0)
        
        # Increase severity for important meetings
        if self._is_important_event(event1) or self._is_important_event(event2):
            severity = min(severity + 0.1, 1.0)
        
        return conflict_type, severity
    
    def _detect_resource_conflicts(
        self, 
        events: List[Dict[str, Any]],
        timezone: str = 'UTC'
    ) -> List[Conflict]:
        """
        Detect conflicts for shared resources (rooms, equipment)
        
        Args:
            events: List of events to check
            timezone: Reference timezone
            
        Returns:
            List of resource conflicts
        """
        resource_conflicts = []
        
        # Group events by resource/location
        resources = {}
        for event in events:
            location = event.get('location', '').strip().lower()
            if location and not self._is_virtual_location(location):
                if location not in resources:
                    resources[location] = []
                resources[location].append(event)
        
        # Check for conflicts within each resource group
        for resource, resource_events in resources.items():
            if len(resource_events) < 2:
                continue
            
            # Check all pairs in this resource group
            for i in range(len(resource_events)):
                for j in range(i + 1, len(resource_events)):
                    event1, event2 = resource_events[i], resource_events[j]
                    
                    if self.has_conflict(event1, event2, timezone):
                        overlap_mins = self.overlap_minutes(event1, event2, timezone)
                        
                        conflict = Conflict(
                            event1=event1,
                            event2=event2,
                            overlap_minutes=overlap_mins,
                            conflict_type="resource_double_booking",
                            severity=0.7,  # Resource conflicts are generally serious
                            affected_attendees=[]  # No specific attendees affected
                        )
                        resource_conflicts.append(conflict)
        
        return resource_conflicts
    
    def _get_event_duration_minutes(self, event: Dict[str, Any]) -> Optional[int]:
        """Get event duration in minutes"""
        start = event.get('start')
        end = event.get('end')
        
        if not start or not end:
            return None
        
        # Try to get duration from processed events
        if isinstance(start, datetime) and isinstance(end, datetime):
            return int((end - start).total_seconds() / 60)
        
        # Handle dict format
        if isinstance(start, dict) and isinstance(end, dict):
            try:
                start_dt = self._normalize_datetime_field(start, pytz.UTC)
                end_dt = self._normalize_datetime_field(end, pytz.UTC)
                if start_dt and end_dt:
                    return int((end_dt - start_dt).total_seconds() / 60)
            except:
                pass
        
        return None
    
    def _is_important_event(self, event: Dict[str, Any]) -> bool:
        """Determine if event is important based on heuristics"""
        summary = event.get('summary', '').lower()
        
        # Keywords that suggest importance
        important_keywords = [
            'board', 'executive', 'ceo', 'cto', 'presentation', 
            'client', 'customer', 'demo', 'interview', 'urgent',
            'critical', 'important', 'annual', 'quarterly'
        ]
        
        # Check if any important keywords are in the title
        for keyword in important_keywords:
            if keyword in summary:
                return True
        
        # Check attendee count (large meetings might be important)
        attendee_count = len(event.get('attendees', []))
        if attendee_count > 10:
            return True
        
        # Check if marked as private (might be important)
        visibility = event.get('visibility', '').lower()
        if visibility == 'private':
            return True
        
        return False
    
    def _is_virtual_location(self, location: str) -> bool:
        """Check if location is virtual (not a physical resource)"""
        virtual_indicators = [
            'zoom', 'meet', 'teams', 'webex', 'skype', 'hangouts',
            'https://', 'http://', 'virtual', 'online', 'remote'
        ]
        
        location_lower = location.lower()
        return any(indicator in location_lower for indicator in virtual_indicators)