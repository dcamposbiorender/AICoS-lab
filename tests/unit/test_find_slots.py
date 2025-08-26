"""
Test Calendar Availability Engine and Free Slot Finding
CRITICAL FIX: All datetime objects are timezone-aware using pytz
"""

import pytest
import pytz
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

# Import the modules we'll be testing
from src.calendar.availability import AvailabilityEngine, FreeSlot
from src.calendar.conflicts import ConflictDetector


class TestAvailabilityEngine:
    """Test free slot finding across multiple calendars with proper timezone handling"""
    
    def test_single_calendar_free_slots(self):
        """Find free slots in single calendar with timezone awareness"""
        # CRITICAL FIX: Use timezone-aware datetime objects
        eastern_tz = pytz.timezone('America/New_York')
        test_date = datetime(2025, 8, 19)
        
        # Mock calendar with 9am-5pm working hours, 2pm-3pm meeting (Eastern timezone)
        calendar_events = [{
            'start': eastern_tz.localize(datetime(2025, 8, 19, 14, 0)),  # 2pm EST - timezone-aware
            'end': eastern_tz.localize(datetime(2025, 8, 19, 15, 0)),    # 3pm EST - timezone-aware
            'timezone': 'America/New_York'
        }]
        
        engine = AvailabilityEngine()
        slots = engine.find_free_slots(
            calendars=[calendar_events],
            duration_minutes=60,
            working_hours=(9, 17),  # 9am-5pm
            date=test_date.date(),
            timezone='America/New_York'
        )
        
        # Should find slots: 9am-2pm (5 hours) and 3pm-5pm (2 hours)
        assert len(slots) >= 2
        assert any(slot.duration_hours >= 4.5 for slot in slots)  # Morning block (accounting for some buffer)
        assert any(slot.duration_hours >= 1.5 for slot in slots)  # Afternoon block
        
        # Verify timezone consistency
        for slot in slots:
            assert slot.start.tzinfo is not None, "All slots should be timezone-aware"
            assert slot.end.tzinfo is not None, "All slots should be timezone-aware"
    
    def test_multi_calendar_intersection(self):
        """Find common free time across multiple calendars with timezone normalization"""
        # CRITICAL FIX: Use timezone-aware datetime objects
        eastern_tz = pytz.timezone('America/New_York')
        pacific_tz = pytz.timezone('America/Los_Angeles')
        
        calendar1 = [{
            'start': eastern_tz.localize(datetime(2025, 8, 19, 10, 0)),  # 10am EST
            'end': eastern_tz.localize(datetime(2025, 8, 19, 11, 0)),    # 11am EST
            'timezone': 'America/New_York'
        }]
        calendar2 = [{
            'start': pacific_tz.localize(datetime(2025, 8, 19, 11, 0)),  # 11am PST (2pm EST)
            'end': pacific_tz.localize(datetime(2025, 8, 19, 12, 0)),    # 12pm PST (3pm EST)
            'timezone': 'America/Los_Angeles'
        }]
        calendar3 = [{
            'start': eastern_tz.localize(datetime(2025, 8, 19, 16, 0)),  # 4pm EST
            'end': eastern_tz.localize(datetime(2025, 8, 19, 17, 0)),    # 5pm EST
            'timezone': 'America/New_York'
        }]
        
        engine = AvailabilityEngine()
        common_slots = engine.find_common_slots(
            calendars=[calendar1, calendar2, calendar3],
            duration_minutes=60,
            working_hours=(9, 17),  # 9am-5pm Eastern
            timezone='America/New_York'
        )
        
        # Should find slots when ALL calendars are free
        assert len(common_slots) >= 1
        assert all(slot.duration_minutes >= 60 for slot in common_slots)
        
        # All slots should be in requested timezone (Eastern)
        for slot in common_slots:
            assert str(slot.start.tzinfo) == 'America/New_York'
    
    def test_timezone_normalization(self):
        """Handle multi-timezone calendar coordination with proper pytz usage"""
        # CRITICAL FIX: Use timezone-aware datetime objects
        pst_tz = pytz.timezone('America/Los_Angeles')
        est_tz = pytz.timezone('America/New_York')
        
        pst_event = {
            'start': pst_tz.localize(datetime(2025, 8, 19, 14, 0)),  # 2pm PST - timezone-aware
            'end': pst_tz.localize(datetime(2025, 8, 19, 15, 0)),    # 3pm PST - timezone-aware
            'timezone': 'America/Los_Angeles'
        }
        
        # EST calendar event at same time as PST event (conflict)
        est_event = {
            'start': est_tz.localize(datetime(2025, 8, 19, 17, 0)),  # 5pm EST (2pm PST)
            'end': est_tz.localize(datetime(2025, 8, 19, 18, 0)),    # 6pm EST (3pm PST)
            'timezone': 'America/New_York'
        }
        
        engine = AvailabilityEngine()
        conflict = engine.detect_timezone_conflict(pst_event, est_event)
        
        assert conflict == True  # Same time in different zones should conflict
        
        # Test timezone normalization
        normalized_pst = engine.normalize_to_timezone(pst_event, 'America/New_York')
        normalized_est = engine.normalize_to_timezone(est_event, 'America/New_York')
        
        assert normalized_pst['start'].hour == 17  # 2pm PST = 5pm EST
        assert normalized_est['start'].hour == 17  # 5pm EST = 5pm EST
    
    def test_buffer_time_handling(self):
        """Add buffer time between meetings with timezone awareness"""
        # CRITICAL FIX: Use timezone-aware datetime objects
        eastern_tz = pytz.timezone('America/New_York')
        
        meetings = [
            {
                'start': eastern_tz.localize(datetime(2025, 8, 19, 10, 0)),
                'end': eastern_tz.localize(datetime(2025, 8, 19, 11, 0)),
                'timezone': 'America/New_York'
            },
            {
                'start': eastern_tz.localize(datetime(2025, 8, 19, 11, 0)),  # Back-to-back
                'end': eastern_tz.localize(datetime(2025, 8, 19, 12, 0)),
                'timezone': 'America/New_York'
            }
        ]
        
        engine = AvailabilityEngine()
        slots = engine.find_free_slots(
            calendars=[meetings],
            duration_minutes=30,
            buffer_minutes=15,  # 15-minute buffer between meetings
            timezone='America/New_York',
            working_hours=(9, 17),
            date=datetime(2025, 8, 19).date()
        )
        
        # Should not suggest 11:00-11:30 due to buffer requirement
        conflicting_slots = [slot for slot in slots if slot.start.hour == 11 and slot.start.minute == 0]
        assert len(conflicting_slots) == 0, "Should not suggest slots that violate buffer time"
    
    def test_working_hours_timezone_handling(self):
        """Test working hours respect for different timezones"""
        eastern_tz = pytz.timezone('America/New_York')
        
        # No existing meetings, just test working hours
        engine = AvailabilityEngine()
        slots = engine.find_free_slots(
            calendars=[[]],  # No meetings
            duration_minutes=60,
            working_hours=(9, 17),  # 9am-5pm Eastern
            timezone='America/New_York',
            date=datetime(2025, 8, 19).date()
        )
        
        # All slots should be within working hours
        for slot in slots:
            assert 9 <= slot.start.hour < 17, f"Slot starts outside working hours: {slot.start.hour}"
            assert 9 < slot.end.hour <= 17, f"Slot ends outside working hours: {slot.end.hour}"


class TestConflictDetection:
    """Test meeting conflict detection and validation with timezone safety"""
    
    def test_overlap_detection(self):
        """Detect overlapping meetings with timezone awareness"""
        eastern_tz = pytz.timezone('America/New_York')
        
        meeting1 = {
            'start': eastern_tz.localize(datetime(2025, 8, 19, 14, 0)),
            'end': eastern_tz.localize(datetime(2025, 8, 19, 15, 0)),
            'timezone': 'America/New_York'
        }
        meeting2 = {
            'start': eastern_tz.localize(datetime(2025, 8, 19, 14, 30)),
            'end': eastern_tz.localize(datetime(2025, 8, 19, 15, 30)),
            'timezone': 'America/New_York'
        }
        
        detector = ConflictDetector()
        conflict = detector.has_conflict(meeting1, meeting2)
        
        assert conflict == True
        assert detector.overlap_minutes(meeting1, meeting2) == 30
    
    def test_cross_timezone_conflict_detection(self):
        """Detect conflicts across different timezones"""
        pst_tz = pytz.timezone('America/Los_Angeles')
        est_tz = pytz.timezone('America/New_York')
        
        pst_meeting = {
            'start': pst_tz.localize(datetime(2025, 8, 19, 14, 0)),  # 2pm PST
            'end': pst_tz.localize(datetime(2025, 8, 19, 15, 0)),    # 3pm PST
            'timezone': 'America/Los_Angeles'
        }
        est_meeting = {
            'start': est_tz.localize(datetime(2025, 8, 19, 17, 0)),  # 5pm EST (2pm PST)
            'end': est_tz.localize(datetime(2025, 8, 19, 18, 0)),    # 6pm EST (3pm PST)
            'timezone': 'America/New_York'
        }
        
        detector = ConflictDetector()
        conflict = detector.has_conflict(pst_meeting, est_meeting)
        
        assert conflict == True, "Should detect conflict between same UTC times in different zones"
    
    def test_attendee_conflicts(self):
        """Detect attendee double-booking with timezone awareness"""
        eastern_tz = pytz.timezone('America/New_York')
        
        meeting1 = {
            'attendees': ['john@example.com', 'jane@example.com'],
            'start': eastern_tz.localize(datetime(2025, 8, 19, 14, 0)),
            'end': eastern_tz.localize(datetime(2025, 8, 19, 15, 0)),
            'timezone': 'America/New_York'
        }
        meeting2 = {
            'attendees': ['john@example.com', 'bob@example.com'],
            'start': eastern_tz.localize(datetime(2025, 8, 19, 14, 30)),
            'end': eastern_tz.localize(datetime(2025, 8, 19, 15, 30)),
            'timezone': 'America/New_York'
        }
        
        detector = ConflictDetector()
        conflicts = detector.find_attendee_conflicts([meeting1, meeting2])
        
        assert len(conflicts) == 1
        assert conflicts[0]['person'] == 'john@example.com'
        assert len(conflicts[0]['meetings']) == 2
    
    def test_no_conflict_different_days(self):
        """Ensure no conflicts detected for different days"""
        eastern_tz = pytz.timezone('America/New_York')
        
        meeting1 = {
            'start': eastern_tz.localize(datetime(2025, 8, 19, 14, 0)),
            'end': eastern_tz.localize(datetime(2025, 8, 19, 15, 0)),
            'timezone': 'America/New_York'
        }
        meeting2 = {
            'start': eastern_tz.localize(datetime(2025, 8, 20, 14, 0)),  # Next day
            'end': eastern_tz.localize(datetime(2025, 8, 20, 15, 0)),
            'timezone': 'America/New_York'
        }
        
        detector = ConflictDetector()
        conflict = detector.has_conflict(meeting1, meeting2)
        
        assert conflict == False


class TestTimezoneSafety:
    """Additional tests specifically for timezone safety and edge cases"""
    
    def test_naive_datetime_rejection(self):
        """Engine should warn about naive datetime objects"""
        engine = AvailabilityEngine()
        
        # Try to create event with naive datetime (should warn)
        naive_event = {
            'start': datetime(2025, 8, 19, 14, 0),  # Naive datetime - no timezone
            'end': datetime(2025, 8, 19, 15, 0),
            'timezone': 'America/New_York'
        }
        
        # The engine should warn about naive datetimes
        with pytest.warns(UserWarning, match="Naive datetime detected"):
            slots = engine.find_free_slots(
                calendars=[[naive_event]],
                duration_minutes=60,
                working_hours=(9, 17),
                date=datetime(2025, 8, 19).date()
            )
            # Should still return slots (after conversion)
            assert isinstance(slots, list)
    
    def test_dst_transition_handling(self):
        """Handle daylight saving time transitions correctly"""
        eastern_tz = pytz.timezone('America/New_York')
        
        # Test around DST transition dates (this would need actual DST dates)
        engine = AvailabilityEngine()
        
        # For now, just verify timezone awareness is maintained
        dst_event = {
            'start': eastern_tz.localize(datetime(2025, 8, 19, 14, 0)),
            'end': eastern_tz.localize(datetime(2025, 8, 19, 15, 0)),
            'timezone': 'America/New_York'
        }
        
        slots = engine.find_free_slots(
            calendars=[[dst_event]],
            duration_minutes=60,
            working_hours=(9, 17),
            timezone='America/New_York',
            date=datetime(2025, 8, 19).date()
        )
        
        # All returned slots should maintain timezone awareness
        for slot in slots:
            assert slot.start.tzinfo is not None
            assert slot.end.tzinfo is not None


class TestErrorHandling:
    """Test error handling and edge cases"""
    
    def test_invalid_timezone_handling(self):
        """Handle invalid timezone strings gracefully"""
        engine = AvailabilityEngine()
        
        with pytest.raises(ValueError):
            engine.find_free_slots(
                calendars=[[]],
                duration_minutes=60,
                working_hours=(9, 17),
                timezone='Invalid/Timezone',
                date=datetime(2025, 8, 19).date()
            )
    
    def test_empty_calendar_handling(self):
        """Handle empty calendars gracefully"""
        engine = AvailabilityEngine()
        
        slots = engine.find_free_slots(
            calendars=[[], [], []],  # Multiple empty calendars
            duration_minutes=60,
            working_hours=(9, 17),
            timezone='America/New_York',
            date=datetime(2025, 8, 19).date()
        )
        
        # Should return the full working day as available
        assert len(slots) >= 1
        total_minutes = sum(slot.duration_minutes for slot in slots)
        assert total_minutes >= 420  # At least 7 hours (420 minutes) of working time
    
    def test_malformed_event_handling(self):
        """Handle malformed calendar events gracefully"""
        engine = AvailabilityEngine()
        
        malformed_events = [
            {'start': None, 'end': None},  # Missing datetimes
            {'start': 'invalid', 'end': 'invalid'},  # Invalid format
            {},  # Empty event
            {'start': pytz.UTC.localize(datetime(2025, 8, 19, 14, 0))}  # Missing end time
        ]
        
        # Should not crash, should skip malformed events
        slots = engine.find_free_slots(
            calendars=[malformed_events],
            duration_minutes=60,
            working_hours=(9, 17),
            timezone='America/New_York',
            date=datetime(2025, 8, 19).date()
        )
        
        # Should get reasonable results despite malformed data
        assert isinstance(slots, list)


# Run basic smoke tests if executed directly
if __name__ == '__main__':
    pytest.main([__file__, '-v'])