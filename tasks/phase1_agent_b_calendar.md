# Agent B: Calendar Coordination & Statistics - Phase 1 Completion

**Date Created**: 2025-08-19  
**Owner**: Agent B (Calendar & Analytics Team)  
**Status**: PENDING  
**Estimated Time**: 2 days (16 hours)  
**Dependencies**: Calendar collector data ✅, Employee roster ✅

## Executive Summary

Implement deterministic calendar coordination and activity statistics without AI dependencies. This provides immediate value through basic scheduling assistance and data insights using pure mathematical algorithms and counting operations.

**Core Philosophy**: No AI interpretation - only deterministic calculations, pure datetime math, and transparent statistical aggregations.

## CRITICAL FIXES REQUIRED (From Architecture Review)

### Fix 1: Timezone Handling - CRITICAL
- **Problem**: Tests use naive datetime objects causing 3-hour scheduling errors
- **Solution**: Use pytz library for all timezone-aware datetime operations
- **Required**: All datetime objects must be timezone-aware from creation

### Fix 2: Calendar Algorithm Performance
- **Problem**: Naive O(N²) complexity will not scale for multi-calendar coordination
- **Solution**: Implement interval tree or sweep line algorithm for O(N log N) performance
- **Target**: Handle 50 calendars × 100 events efficiently

### Fix 3: Input Validation Framework
- **Problem**: No validation of calendar event data integrity
- **Solution**: Add comprehensive input validation for all calendar operations
- **Security**: Prevent malformed events from crashing scheduling algorithm

## Module Architecture

### Relevant Files for Calendar & Statistics

**Read for Context:**
- `src/collectors/calendar_collector.py` - Calendar data structure and collection
- `src/collectors/employee_collector.py` - Employee roster for attendee mapping
- `src/search/database.py` - Database structure for queries
- `tests/fixtures/mock_calendar_data.py` - Calendar event patterns

**Files to Create:**
- `tools/find_slots.py` - CLI tool for calendar coordination
- `src/calendar/__init__.py` - Calendar module initialization
- `src/calendar/availability.py` - Free/busy calculation engine  
- `src/calendar/conflicts.py` - Meeting conflict detection
- `src/aggregators/__init__.py` - Statistics module initialization
- `src/aggregators/basic_stats.py` - Deterministic activity statistics
- `tests/unit/test_find_slots.py` - Calendar coordination test suite
- `tests/unit/test_basic_stats.py` - Statistics test suite

**Reference Patterns:**
- `src/search/database.py:165-170` - Index creation patterns for performance
- `src/collectors/base.py:43-55` - Constructor validation patterns
- `src/core/config.py` - Configuration management and validation

## Test-Driven Development Plan

### Phase B1: Calendar Availability Engine (8 hours)

#### Test Acceptance Criteria (Write FIRST)

**File**: `tests/unit/test_find_slots.py`
```python
import pytest
from datetime import datetime, timedelta
from src.calendar.availability import AvailabilityEngine, find_free_slots
from src.calendar.conflicts import ConflictDetector

class TestAvailabilityEngine:
    """Test free slot finding across multiple calendars"""
    
    def test_single_calendar_free_slots(self):
        """Find free slots in single calendar"""
        # Mock calendar with 9am-5pm working hours, 2pm-3pm meeting
        calendar_events = [
            {'start': datetime(2025, 8, 19, 14, 0), 'end': datetime(2025, 8, 19, 15, 0)}
        ]
        
        engine = AvailabilityEngine()
        slots = engine.find_free_slots(
            calendars=[calendar_events],
            duration_minutes=60,
            working_hours=(9, 17),  # 9am-5pm
            date=datetime(2025, 8, 19).date()
        )
        
        # Should find slots: 9am-2pm (5 hours) and 3pm-5pm (2 hours)
        assert len(slots) >= 2
        assert any(slot.duration_hours >= 5 for slot in slots)  # Morning block
        assert any(slot.duration_hours >= 2 for slot in slots)  # Afternoon block
    
    def test_multi_calendar_intersection(self):
        """Find common free time across multiple calendars"""
        calendar1 = [{'start': datetime(2025, 8, 19, 10, 0), 'end': datetime(2025, 8, 19, 11, 0)}]
        calendar2 = [{'start': datetime(2025, 8, 19, 14, 0), 'end': datetime(2025, 8, 19, 15, 0)}]
        calendar3 = [{'start': datetime(2025, 8, 19, 16, 0), 'end': datetime(2025, 8, 19, 17, 0)}]
        
        engine = AvailabilityEngine()
        common_slots = engine.find_common_slots(
            calendars=[calendar1, calendar2, calendar3],
            duration_minutes=60,
            working_hours=(9, 17)
        )
        
        # Should find slots when ALL calendars are free
        assert len(common_slots) >= 1
        assert all(slot.duration_minutes >= 60 for slot in common_slots)
    
    def test_timezone_normalization(self):
        """Handle multi-timezone calendar coordination"""
        # FIXED: Use timezone-aware datetime objects
        import pytz
        pst_tz = pytz.timezone('America/Los_Angeles')
        
        pst_event = {
            'start': pst_tz.localize(datetime(2025, 8, 19, 14, 0)),  # 2pm PST - timezone-aware
            'end': pst_tz.localize(datetime(2025, 8, 19, 15, 0)),    # 3pm PST - timezone-aware
            'timezone': 'America/Los_Angeles'
        }
        
        # EST calendar event  
        est_event = {
            'start': datetime(2025, 8, 19, 17, 0),  # 5pm EST (2pm PST)
            'end': datetime(2025, 8, 19, 18, 0),    # 6pm EST (3pm PST)
            'timezone': 'America/New_York'
        }
        
        engine = AvailabilityEngine()
        conflict = engine.detect_timezone_conflict(pst_event, est_event)
        
        assert conflict == True  # Same time in different zones
    
    def test_buffer_time_handling(self):
        """Add buffer time between meetings"""
        meetings = [
            {'start': datetime(2025, 8, 19, 10, 0), 'end': datetime(2025, 8, 19, 11, 0)},
            {'start': datetime(2025, 8, 19, 11, 0), 'end': datetime(2025, 8, 19, 12, 0)}  # Back-to-back
        ]
        
        engine = AvailabilityEngine()
        slots = engine.find_free_slots(
            calendars=[meetings],
            duration_minutes=30,
            buffer_minutes=15  # 15-minute buffer between meetings
        )
        
        # Should not suggest 11:00-11:30 due to buffer requirement
        assert not any(slot.start.hour == 11 and slot.start.minute == 0 for slot in slots)

class TestConflictDetection:
    """Test meeting conflict detection and validation"""
    
    def test_overlap_detection(self):
        """Detect overlapping meetings"""
        meeting1 = {'start': datetime(2025, 8, 19, 14, 0), 'end': datetime(2025, 8, 19, 15, 0)}
        meeting2 = {'start': datetime(2025, 8, 19, 14, 30), 'end': datetime(2025, 8, 19, 15, 30)}
        
        detector = ConflictDetector()
        conflict = detector.has_conflict(meeting1, meeting2)
        
        assert conflict == True
        assert detector.overlap_minutes(meeting1, meeting2) == 30
    
    def test_attendee_conflicts(self):
        """Detect attendee double-booking"""
        meeting1 = {
            'attendees': ['john@example.com', 'jane@example.com'],
            'start': datetime(2025, 8, 19, 14, 0),
            'end': datetime(2025, 8, 19, 15, 0)
        }
        meeting2 = {
            'attendees': ['john@example.com', 'bob@example.com'],
            'start': datetime(2025, 8, 19, 14, 30),
            'end': datetime(2025, 8, 19, 15, 30)
        }
        
        detector = ConflictDetector()
        conflicts = detector.find_attendee_conflicts([meeting1, meeting2])
        
        assert len(conflicts) == 1
        assert conflicts[0]['person'] == 'john@example.com'
        assert conflicts[0]['meetings'] == [meeting1, meeting2]
```

#### Implementation Tasks

**Task B1.1: Availability Engine Core (3 hours)**
- Create AvailabilityEngine class
- Implement free/busy calculation algorithm
- Add working hours and break time support
- Handle all-day events and vacation time

**Task B1.2: Multi-Calendar Intersection (2 hours)**
- Implement common slot finding across calendars
- Add attendee availability checking
- Create timezone normalization logic
- Optimize for performance with large calendar sets

**Task B1.3: Conflict Detection System (2 hours)**
- Create ConflictDetector class
- Implement overlap detection algorithms
- Add attendee double-booking detection
- Create conflict severity scoring

**Task B1.4: CLI Tool Implementation (1 hour)**
- Create find_slots.py CLI tool
- Add interactive slot selection
- Implement output formatting (JSON, table)
- Add date range and attendee filtering

### Phase B2: Activity Statistics Module (8 hours)

#### Test Acceptance Criteria (Write FIRST)

**File**: `tests/unit/test_basic_stats.py`
```python
import pytest
from datetime import date, timedelta
from src.aggregators.basic_stats import ActivityAnalyzer, MessageStatsCalculator

class TestMessageStatistics:
    """Test Slack message volume and pattern analysis"""
    
    def test_message_volume_calculation(self):
        """Calculate message statistics by channel and person"""
        analyzer = ActivityAnalyzer()
        
        # Mock message data with multiple channels and authors
        messages = [
            {'channel': 'general', 'author': 'john@example.com', 'timestamp': '2025-08-19T10:00:00Z'},
            {'channel': 'general', 'author': 'jane@example.com', 'timestamp': '2025-08-19T10:05:00Z'},
            {'channel': 'product', 'author': 'john@example.com', 'timestamp': '2025-08-19T11:00:00Z'}
        ]
        
        stats = analyzer.calculate_message_stats(messages, time_period="today")
        
        assert stats['total_messages'] == 3
        assert stats['unique_authors'] == 2
        assert stats['channels_active'] == 2
        assert stats['by_channel']['general'] == 2
        assert stats['by_channel']['product'] == 1
        assert stats['by_author']['john@example.com'] == 2
    
    def test_temporal_patterns(self):
        """Analyze message patterns over time"""
        analyzer = ActivityAnalyzer()
        
        # Messages spread across week
        messages = []
        for day in range(7):
            messages.append({
                'timestamp': (date.today() - timedelta(days=day)).isoformat() + 'T10:00:00Z',
                'channel': 'general',
                'author': 'john@example.com'
            })
        
        patterns = analyzer.analyze_temporal_patterns(messages, "daily")
        
        assert len(patterns) == 7  # 7 days of data
        assert all('date' in day for day in patterns)
        assert all('message_count' in day for day in patterns)
    
    def test_activity_correlation(self):
        """Correlate activity across different data sources"""
        analyzer = ActivityAnalyzer()
        
        # Combined Slack + Calendar + Drive activity
        activity_data = {
            'slack_messages': 50,
            'calendar_meetings': 8,
            'drive_file_changes': 12,
            'date': date.today()
        }
        
        correlation = analyzer.calculate_cross_source_activity([activity_data])
        
        assert correlation['total_interactions'] == 70
        assert correlation['collaboration_score'] > 0
        assert correlation['productivity_indicators']['communication'] == 50

class TestMeetingAnalysis:
    """Test calendar meeting pattern analysis"""
    
    def test_meeting_frequency_analysis(self):
        """Analyze meeting patterns and frequency"""
        analyzer = ActivityAnalyzer()
        
        meetings = [
            {'title': 'Daily Standup', 'duration_minutes': 30, 'attendees': ['john', 'jane']},
            {'title': 'Weekly Review', 'duration_minutes': 60, 'attendees': ['john', 'jane', 'bob']},
            {'title': '1:1 Meeting', 'duration_minutes': 45, 'attendees': ['john', 'manager']}
        ]
        
        patterns = analyzer.analyze_meeting_patterns(meetings, "last_week")
        
        assert patterns['total_meetings'] == 3
        assert patterns['total_duration_hours'] == 2.25  # 135 minutes
        assert patterns['average_attendees'] == 2.33
        assert patterns['meeting_types']['1:1'] == 1
        assert patterns['meeting_types']['team'] == 2
    
    def test_recurring_meeting_detection(self):
        """Identify recurring meeting patterns"""
        analyzer = ActivityAnalyzer()
        
        # Weekly meeting pattern
        recurring_meetings = []
        for week in range(4):
            recurring_meetings.append({
                'title': 'Weekly Team Sync',
                'start': datetime(2025, 8, 5 + (week * 7), 10, 0),  # Mondays at 10am
                'attendees': ['john', 'jane', 'bob']
            })
        
        patterns = analyzer.detect_recurring_patterns(recurring_meetings)
        
        assert len(patterns) == 1
        assert patterns[0]['pattern_type'] == 'weekly'
        assert patterns[0]['title'] == 'Weekly Team Sync'
        assert patterns[0]['occurrence_count'] == 4
    
    def test_resource_utilization(self):
        """Calculate meeting room and resource usage"""
        analyzer = ActivityAnalyzer()
        
        meetings = [
            {'location': 'Conference Room A', 'duration_minutes': 60},
            {'location': 'Conference Room A', 'duration_minutes': 30},
            {'location': 'Conference Room B', 'duration_minutes': 90},
            {'location': 'Zoom', 'duration_minutes': 45}
        ]
        
        utilization = analyzer.calculate_resource_utilization(meetings)
        
        assert utilization['Conference Room A']['total_hours'] == 1.5
        assert utilization['Conference Room A']['booking_count'] == 2
        assert utilization['virtual_meetings']['count'] == 1
        assert utilization['total_meeting_hours'] == 3.75

class TestActivityTimeline:
    """Test daily/weekly activity timeline generation"""
    
    def test_daily_activity_rollup(self):
        """Generate daily activity summaries"""
        analyzer = ActivityAnalyzer()
        
        # Mixed activity data for multiple days
        activities = [
            {'date': '2025-08-19', 'type': 'slack_message', 'count': 25},
            {'date': '2025-08-19', 'type': 'calendar_meeting', 'count': 3},
            {'date': '2025-08-19', 'type': 'drive_change', 'count': 5},
            {'date': '2025-08-18', 'type': 'slack_message', 'count': 18},
            {'date': '2025-08-18', 'type': 'calendar_meeting', 'count': 1},
        ]
        
        timeline = analyzer.generate_daily_timeline(activities, days=7)
        
        assert len(timeline) == 7  # 7 days requested
        assert timeline[0]['date'] == '2025-08-19'  # Most recent first
        assert timeline[0]['total_activities'] == 33  # 25+3+5
        assert timeline[1]['total_activities'] == 19  # 18+1
    
    def test_weekly_aggregation(self):
        """Generate weekly activity summaries"""
        analyzer = ActivityAnalyzer()
        
        weekly_data = analyzer.generate_weekly_summary(start_date=date.today() - timedelta(days=7))
        
        required_fields = [
            'week_start', 'week_end', 'total_messages', 'total_meetings', 
            'active_channels', 'unique_participants', 'productivity_score'
        ]
        assert all(field in weekly_data for field in required_fields)
        assert weekly_data['productivity_score'] >= 0
    
    def test_comparative_analysis(self):
        """Compare activity between time periods"""
        analyzer = ActivityAnalyzer()
        
        comparison = analyzer.compare_periods(
            period1="this_week",
            period2="last_week"
        )
        
        assert 'period1_stats' in comparison
        assert 'period2_stats' in comparison
        assert 'changes' in comparison
        assert 'growth_rate' in comparison['changes']
```

#### Implementation Tasks

**Task B1.1: Availability Algorithm Core (3 hours)**
- Create AvailabilityEngine class
- Implement time slot intersection algorithm
- Add working hours and break time logic
- Handle timezone conversion and normalization

**Task B1.2: Multi-Calendar Processing (2 hours)**
- Implement common availability finder
- Add attendee constraint handling
- Create calendar priority and weighting system
- Optimize for performance with many calendars

**Task B1.3: Conflict Detection Engine (2 hours)**
- Create ConflictDetector class
- Implement overlap detection algorithms
- Add resource conflict detection (rooms, equipment)
- Create conflict severity and impact scoring

**Task B1.4: CLI Integration (1 hour)**
- Create find_slots.py CLI tool
- Add interactive date/time selection
- Implement output formatting and filtering
- Add conflict checking and validation

### Phase B2: Activity Statistics Engine (8 hours)

#### Test Acceptance Criteria (Write FIRST)

**File**: `tests/unit/test_basic_stats.py`
```python
import pytest
from datetime import date, timedelta
from src.aggregators.basic_stats import ActivityAnalyzer

class TestBasicStatistics:
    """Test fundamental counting and aggregation operations"""
    
    def test_message_volume_by_period(self):
        """Count messages by various time periods"""
        analyzer = ActivityAnalyzer(db_path="test.db")
        
        # Test different time periods
        daily_stats = analyzer.get_message_stats("today")
        weekly_stats = analyzer.get_message_stats("last_week")
        monthly_stats = analyzer.get_message_stats("past_30_days")
        
        required_fields = ['total_messages', 'unique_authors', 'channels_active', 'avg_messages_per_hour']
        
        for stats in [daily_stats, weekly_stats, monthly_stats]:
            assert all(field in stats for field in required_fields)
            assert all(isinstance(stats[field], (int, float)) for field in required_fields)
    
    def test_channel_activity_ranking(self):
        """Rank channels by activity level"""
        analyzer = ActivityAnalyzer(db_path="test.db")
        
        channel_stats = analyzer.get_channel_rankings("last_week")
        
        assert isinstance(channel_stats, list)
        assert len(channel_stats) > 0
        
        # Should be sorted by activity (most active first)
        if len(channel_stats) > 1:
            assert channel_stats[0]['message_count'] >= channel_stats[1]['message_count']
        
        # Required fields for each channel
        required_fields = ['channel_name', 'message_count', 'unique_authors', 'activity_score']
        for channel in channel_stats:
            assert all(field in channel for field in required_fields)
    
    def test_person_activity_aggregation(self):
        """Aggregate activity per person across all sources"""
        analyzer = ActivityAnalyzer(db_path="test.db")
        
        person_stats = analyzer.get_person_activity("john@example.com", "last_week")
        
        required_fields = [
            'slack_messages_sent', 'slack_channels_active', 'meetings_attended', 
            'meetings_organized', 'drive_files_modified', 'total_interactions'
        ]
        
        assert all(field in person_stats for field in required_fields)
        assert person_stats['total_interactions'] >= 0
        assert person_stats['slack_messages_sent'] >= 0
    
    def test_productivity_indicators(self):
        """Calculate basic productivity indicators"""
        analyzer = ActivityAnalyzer(db_path="test.db")
        
        indicators = analyzer.calculate_productivity_indicators("last_week")
        
        required_metrics = [
            'communication_volume', 'collaboration_score', 'meeting_efficiency',
            'response_time_avg', 'active_work_hours', 'cross_channel_engagement'
        ]
        
        assert all(metric in indicators for metric in required_metrics)
        assert 0 <= indicators['meeting_efficiency'] <= 1.0  # Percentage
        assert indicators['active_work_hours'] >= 0
```

#### Implementation Tasks

**Task B2.1: Message Statistics Calculator (2 hours)**
- Create ActivityAnalyzer class with database integration
- Implement message counting by time period, channel, person
- Add channel activity ranking algorithms
- Create temporal pattern analysis

**Task B2.2: Meeting Pattern Analysis (2 hours)**
- Implement meeting frequency and duration statistics
- Add recurring meeting detection
- Create attendee participation analysis
- Calculate meeting efficiency metrics

**Task B2.3: Cross-Source Activity Correlation (2 hours)**
- Implement unified activity scoring across Slack/Calendar/Drive
- Create productivity indicator calculations
- Add collaboration scoring algorithms
- Generate comparative analysis between time periods

**Task B2.4: Statistical Aggregation Pipeline (2 hours)**
- Create daily/weekly/monthly rollup generators
- Implement statistical aggregation functions (avg, median, percentiles)
- Add trend detection for activity changes
- Create export functionality for external analysis

## Integration Requirements

### Database Integration
- Use existing SQLite FTS5 database for all queries
- Create optimized views for statistical aggregations
- Add proper indexes for time-based and person-based queries
- Maintain audit trail with source attribution

### Calendar Data Integration
- Parse calendar collector JSONL files
- Handle Google Calendar API format and timezone data
- Integrate with employee roster for attendee ID mapping
- Support multiple calendar sources per person

### Performance Requirements
- Calendar coordination completes in <5 seconds
- Statistics generation completes in <10 seconds
- Memory usage <200MB for typical operations
- Efficient batch processing for large datasets

## Success Criteria

### Calendar Coordination Validation ✅
- [ ] Find valid free slots across multiple calendars
- [ ] Handle timezone conversions correctly
- [ ] Detect conflicts and double-booking accurately
- [ ] CLI tool provides useful interactive experience

### Statistics Validation ✅
- [ ] Message statistics accurate against raw data
- [ ] Meeting patterns properly identified
- [ ] Cross-source correlation makes logical sense
- [ ] Performance targets met for all calculations

### Integration Validation ✅
- [ ] Agent A time queries integrate with calendar filtering
- [ ] Agent C CLI tools can consume all statistics
- [ ] No performance degradation in existing search
- [ ] All results include proper source attribution

## Delivery Checklist

Before marking complete:
- [ ] All test suites written and passing
- [ ] Calendar coordination working with real data
- [ ] Statistics calculations validated against known data
- [ ] Performance benchmarks documented
- [ ] CLI tools functional and user-friendly
- [ ] Integration points clearly defined for Agent C

---

**Contact Agent B Team Lead for questions or clarification**
**Integration Point**: Agent C depends on calendar/statistics APIs