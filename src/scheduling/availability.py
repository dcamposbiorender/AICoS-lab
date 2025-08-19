"""
Calendar Availability Engine - Timezone-Aware Free Slot Finding
CRITICAL FIX: All datetime objects are timezone-aware using pytz

References:
- src/core/compression.py - Atomic operation patterns for data safety
- tests/fixtures/mock_calendar_data.py - Calendar event structure
- src/collectors/calendar_collector.py - Calendar data format
"""

import pytz
import logging
from datetime import datetime, timedelta, time
from typing import List, Dict, Any, Optional, Tuple, Union
from dataclasses import dataclass
import warnings

logger = logging.getLogger(__name__)


@dataclass
class FreeSlot:
    """
    Represents a free time slot with timezone awareness
    CRITICAL: All datetime fields are timezone-aware
    """
    start: datetime
    end: datetime
    duration_minutes: int
    timezone: str
    
    def __post_init__(self):
        """Validate timezone awareness after initialization"""
        if self.start.tzinfo is None or self.end.tzinfo is None:
            raise ValueError("FreeSlot datetimes must be timezone-aware")
    
    @property
    def duration_hours(self) -> float:
        """Duration in hours (decimal)"""
        return self.duration_minutes / 60.0
    
    def overlaps_with(self, other: 'FreeSlot') -> bool:
        """Check if this slot overlaps with another slot"""
        return (
            self.start < other.end and 
            self.end > other.start
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'start': self.start.isoformat(),
            'end': self.end.isoformat(),
            'duration_minutes': self.duration_minutes,
            'duration_hours': self.duration_hours,
            'timezone': self.timezone
        }


class AvailabilityEngine:
    """
    CRITICAL FIX: Timezone-aware calendar availability engine
    Uses efficient algorithms and proper timezone handling
    """
    
    def __init__(self):
        """Initialize availability engine with timezone safety"""
        self.logger = logging.getLogger(__name__ + '.AvailabilityEngine')
        self._validate_pytz_available()
    
    def _validate_pytz_available(self):
        """Ensure pytz is available for timezone operations"""
        try:
            pytz.UTC
        except AttributeError:
            raise ImportError("pytz library is required for timezone-aware operations")
    
    def find_free_slots(
        self,
        calendars: List[List[Dict[str, Any]]],
        duration_minutes: int,
        working_hours: Tuple[int, int] = (9, 17),
        date: Optional[object] = None,
        timezone: str = 'UTC',
        buffer_minutes: int = 0
    ) -> List[FreeSlot]:
        """
        Find free slots across multiple calendars with timezone awareness
        CRITICAL FIX: All operations use timezone-aware datetimes
        
        Args:
            calendars: List of calendar event lists
            duration_minutes: Minimum slot duration required
            working_hours: (start_hour, end_hour) in specified timezone
            date: Target date (date object)
            timezone: Target timezone for results
            buffer_minutes: Buffer time required between meetings
            
        Returns:
            List of available time slots
        """
        if not calendars:
            return []
        
        # Validate and normalize timezone
        try:
            target_tz = pytz.timezone(timezone)
        except pytz.exceptions.UnknownTimeZoneError:
            raise ValueError(f"Invalid timezone: {timezone}")
        
        # Use today if no date specified
        if date is None:
            date = datetime.now(target_tz).date()
        
        # Create working day boundaries in target timezone
        work_start = target_tz.localize(
            datetime.combine(date, time(working_hours[0]))
        )
        work_end = target_tz.localize(
            datetime.combine(date, time(working_hours[1]))
        )
        
        self.logger.debug(f"Finding slots for {date} in {timezone}, working hours {working_hours}")
        
        # Collect and normalize all events to target timezone
        all_events = []
        for calendar in calendars:
            for event in calendar:
                normalized_event = self._normalize_event_to_timezone(event, timezone)
                if normalized_event and self._event_overlaps_date(normalized_event, date):
                    all_events.append(normalized_event)
        
        # Sort events by start time for efficient processing
        all_events.sort(key=lambda e: e.get('start', datetime.min.replace(tzinfo=target_tz)))
        
        # Use sweep line algorithm for O(N log N) performance
        free_slots = self._find_gaps_sweep_line(
            events=all_events,
            work_start=work_start,
            work_end=work_end,
            min_duration_minutes=duration_minutes,
            buffer_minutes=buffer_minutes,
            target_tz=target_tz
        )
        
        self.logger.info(f"Found {len(free_slots)} free slots of {duration_minutes}+ minutes")
        return free_slots
    
    def find_common_slots(
        self,
        calendars: List[List[Dict[str, Any]]],
        duration_minutes: int,
        working_hours: Tuple[int, int] = (9, 17),
        timezone: str = 'UTC',
        date: Optional[object] = None
    ) -> List[FreeSlot]:
        """
        Find time slots that are free across ALL calendars
        CRITICAL: Uses timezone normalization for accurate intersection
        
        Args:
            calendars: List of calendar event lists
            duration_minutes: Minimum slot duration required
            working_hours: (start_hour, end_hour) in specified timezone
            timezone: Target timezone for results
            date: Target date (date object)
            
        Returns:
            List of commonly available time slots
        """
        if not calendars:
            return []
        
        # Get free slots for each calendar individually
        calendar_slots = []
        for calendar in calendars:
            slots = self.find_free_slots(
                calendars=[calendar],
                duration_minutes=duration_minutes,
                working_hours=working_hours,
                date=date,
                timezone=timezone
            )
            calendar_slots.append(slots)
        
        if not calendar_slots:
            return []
        
        # Find intersection of all slot lists
        common_slots = calendar_slots[0]  # Start with first calendar's slots
        
        for other_slots in calendar_slots[1:]:
            common_slots = self._intersect_slot_lists(common_slots, other_slots)
        
        # Filter by minimum duration requirement
        common_slots = [
            slot for slot in common_slots 
            if slot.duration_minutes >= duration_minutes
        ]
        
        self.logger.info(f"Found {len(common_slots)} common slots across {len(calendars)} calendars")
        return common_slots
    
    def detect_timezone_conflict(
        self, 
        event1: Dict[str, Any], 
        event2: Dict[str, Any]
    ) -> bool:
        """
        Detect if two events conflict when normalized to UTC
        CRITICAL: Handles timezone conversion for accurate conflict detection
        
        Args:
            event1: First event with timezone info
            event2: Second event with timezone info
            
        Returns:
            True if events conflict in actual time
        """
        # Normalize both events to UTC for comparison
        utc_event1 = self._normalize_event_to_timezone(event1, 'UTC')
        utc_event2 = self._normalize_event_to_timezone(event2, 'UTC')
        
        if not utc_event1 or not utc_event2:
            return False
        
        # Check overlap in UTC time
        start1 = utc_event1.get('start')
        end1 = utc_event1.get('end')
        start2 = utc_event2.get('start')
        end2 = utc_event2.get('end')
        
        if not all([start1, end1, start2, end2]):
            return False
        
        # Events conflict if they overlap in time
        return start1 < end2 and end1 > start2
    
    def normalize_to_timezone(
        self, 
        event: Dict[str, Any], 
        target_timezone: str
    ) -> Dict[str, Any]:
        """
        Normalize event to target timezone
        CRITICAL: Maintains timezone awareness throughout
        
        Args:
            event: Event with datetime fields
            target_timezone: Target timezone string
            
        Returns:
            Event with datetimes in target timezone
        """
        return self._normalize_event_to_timezone(event, target_timezone)
    
    def _normalize_event_to_timezone(
        self, 
        event: Dict[str, Any], 
        target_timezone: str
    ) -> Optional[Dict[str, Any]]:
        """
        Normalize event datetime fields to target timezone
        CRITICAL FIX: Handles naive datetimes and timezone conversion safely
        
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
        
        # Process start time
        start = event.get('start')
        if start:
            normalized_start = self._normalize_datetime_field(start, target_tz, event.get('timezone'))
            if normalized_start:
                normalized['start'] = normalized_start
            else:
                return None  # Invalid start time
        
        # Process end time
        end = event.get('end')
        if end:
            normalized_end = self._normalize_datetime_field(end, target_tz, event.get('timezone'))
            if normalized_end:
                normalized['end'] = normalized_end
            else:
                return None  # Invalid end time
        
        return normalized
    
    def _normalize_datetime_field(
        self, 
        dt_value: Any, 
        target_tz: pytz.timezone, 
        source_timezone: Optional[str] = None
    ) -> Optional[datetime]:
        """
        Normalize a single datetime field to target timezone
        CRITICAL: Handles various datetime formats and timezone scenarios
        
        Args:
            dt_value: Datetime value (could be datetime, string, or dict)
            target_tz: Target timezone
            source_timezone: Source timezone hint
            
        Returns:
            Normalized timezone-aware datetime or None if invalid
        """
        if isinstance(dt_value, datetime):
            # Handle datetime objects
            if dt_value.tzinfo is None:
                # Naive datetime - issue warning and attempt to localize
                warnings.warn(
                    "Naive datetime detected. Assuming source timezone or UTC.",
                    UserWarning
                )
                if source_timezone:
                    try:
                        source_tz = pytz.timezone(source_timezone)
                        dt_value = source_tz.localize(dt_value)
                    except pytz.exceptions.UnknownTimeZoneError:
                        dt_value = pytz.UTC.localize(dt_value)
                else:
                    dt_value = pytz.UTC.localize(dt_value)
            
            # Convert to target timezone
            return dt_value.astimezone(target_tz)
        
        elif isinstance(dt_value, str):
            # Handle ISO string format
            try:
                dt = datetime.fromisoformat(dt_value.replace('Z', '+00:00'))
                if dt.tzinfo is None:
                    dt = pytz.UTC.localize(dt)
                return dt.astimezone(target_tz)
            except ValueError:
                self.logger.warning(f"Invalid datetime string: {dt_value}")
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
                except (ValueError, pytz.exceptions.UnknownTimeZoneError) as e:
                    self.logger.warning(f"Error parsing datetime dict: {e}")
                    return None
            elif 'date' in dt_value:
                # All-day event - create start of day in target timezone
                try:
                    date_str = dt_value['date']
                    date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                    return target_tz.localize(datetime.combine(date_obj, time.min))
                except ValueError as e:
                    self.logger.warning(f"Error parsing date: {e}")
                    return None
        
        self.logger.warning(f"Unhandled datetime format: {type(dt_value)} - {dt_value}")
        return None
    
    def _event_overlaps_date(self, event: Dict[str, Any], target_date: object) -> bool:
        """Check if event overlaps with target date"""
        start = event.get('start')
        end = event.get('end')
        
        if not start or not end:
            return False
        
        event_start_date = start.date()
        event_end_date = end.date()
        
        # Event overlaps if target date is within event date range
        return event_start_date <= target_date <= event_end_date
    
    def _find_gaps_sweep_line(
        self,
        events: List[Dict[str, Any]],
        work_start: datetime,
        work_end: datetime,
        min_duration_minutes: int,
        buffer_minutes: int,
        target_tz: pytz.timezone
    ) -> List[FreeSlot]:
        """
        CRITICAL FIX: Use sweep line algorithm for O(N log N) performance
        Find gaps between events using efficient interval processing
        
        Args:
            events: Sorted list of events
            work_start: Working day start (timezone-aware)
            work_end: Working day end (timezone-aware)
            min_duration_minutes: Minimum slot duration
            buffer_minutes: Buffer time between meetings
            target_tz: Target timezone
            
        Returns:
            List of free slots
        """
        if not events:
            # No events - entire working day is free
            total_minutes = int((work_end - work_start).total_seconds() / 60)
            if total_minutes >= min_duration_minutes:
                return [FreeSlot(
                    start=work_start,
                    end=work_end,
                    duration_minutes=total_minutes,
                    timezone=str(target_tz)
                )]
            return []
        
        free_slots = []
        current_time = work_start
        
        # Process each event to find gaps
        for event in events:
            event_start = event.get('start')
            event_end = event.get('end')
            
            if not event_start or not event_end:
                continue
            
            # Skip events that are outside working hours
            if event_end <= work_start or event_start >= work_end:
                continue
            
            # Clip event to working hours
            clipped_start = max(event_start, work_start)
            clipped_end = min(event_end, work_end)
            
            # Check for gap before this event
            if current_time < clipped_start:
                gap_end = clipped_start
                if buffer_minutes > 0:
                    gap_end = gap_end - timedelta(minutes=buffer_minutes)
                    gap_end = max(gap_end, current_time)  # Don't go backwards
                
                gap_duration = int((gap_end - current_time).total_seconds() / 60)
                if gap_duration >= min_duration_minutes:
                    free_slots.append(FreeSlot(
                        start=current_time,
                        end=gap_end,
                        duration_minutes=gap_duration,
                        timezone=str(target_tz)
                    ))
            
            # Move current time to end of this event (plus buffer)
            new_current = clipped_end
            if buffer_minutes > 0:
                new_current = new_current + timedelta(minutes=buffer_minutes)
            current_time = max(current_time, new_current)
        
        # Check for gap after last event
        if current_time < work_end:
            gap_duration = int((work_end - current_time).total_seconds() / 60)
            if gap_duration >= min_duration_minutes:
                free_slots.append(FreeSlot(
                    start=current_time,
                    end=work_end,
                    duration_minutes=gap_duration,
                    timezone=str(target_tz)
                ))
        
        # Merge adjacent slots if buffer allows
        merged_slots = self._merge_adjacent_slots(free_slots, buffer_minutes)
        
        return merged_slots
    
    def _merge_adjacent_slots(self, slots: List[FreeSlot], buffer_minutes: int) -> List[FreeSlot]:
        """
        Merge adjacent free slots that are close enough
        Optimizes slot list for better user experience
        
        Args:
            slots: List of free slots
            buffer_minutes: Maximum gap to merge across
            
        Returns:
            List of merged slots
        """
        if not slots:
            return slots
        
        merged = []
        current_slot = slots[0]
        
        for next_slot in slots[1:]:
            # Check if slots can be merged
            gap_minutes = (next_slot.start - current_slot.end).total_seconds() / 60
            
            if gap_minutes <= buffer_minutes:
                # Merge slots
                total_duration = (
                    current_slot.duration_minutes + 
                    next_slot.duration_minutes + 
                    int(gap_minutes)
                )
                current_slot = FreeSlot(
                    start=current_slot.start,
                    end=next_slot.end,
                    duration_minutes=total_duration,
                    timezone=current_slot.timezone
                )
            else:
                # Can't merge - save current and move to next
                merged.append(current_slot)
                current_slot = next_slot
        
        # Add the last slot
        merged.append(current_slot)
        return merged
    
    def _intersect_slot_lists(
        self, 
        slots1: List[FreeSlot], 
        slots2: List[FreeSlot]
    ) -> List[FreeSlot]:
        """
        Find intersection between two lists of free slots
        CRITICAL: Uses efficient interval intersection algorithm
        
        Args:
            slots1: First list of slots
            slots2: Second list of slots
            
        Returns:
            List of intersecting slots
        """
        intersections = []
        
        # Use two-pointer technique for efficient intersection
        i, j = 0, 0
        while i < len(slots1) and j < len(slots2):
            slot1 = slots1[i]
            slot2 = slots2[j]
            
            # Find overlap
            overlap_start = max(slot1.start, slot2.start)
            overlap_end = min(slot1.end, slot2.end)
            
            if overlap_start < overlap_end:
                # Valid intersection
                overlap_minutes = int((overlap_end - overlap_start).total_seconds() / 60)
                intersections.append(FreeSlot(
                    start=overlap_start,
                    end=overlap_end,
                    duration_minutes=overlap_minutes,
                    timezone=slot1.timezone  # Assume same timezone
                ))
            
            # Move pointer for slot that ends earlier
            if slot1.end <= slot2.end:
                i += 1
            else:
                j += 1
        
        return intersections