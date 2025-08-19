"""
Basic Statistics and Activity Analysis
Deterministic calculations without AI/LLM dependencies

References:
- src/search/database.py - Database connection and query patterns (lines 45-80)
- src/core/compression.py - Error handling and atomic operations (lines 95-120)
- src/collectors/calendar_collector.py - Calendar event structure (lines 185-210)
"""

import sqlite3
import logging
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union
from collections import defaultdict, Counter
import json
import statistics
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ActivityMetrics:
    """Container for standardized activity metrics"""
    total_count: int
    unique_participants: int
    time_span_hours: float
    average_per_hour: float
    peak_hour: Optional[int]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'total_count': self.total_count,
            'unique_participants': self.unique_participants,
            'time_span_hours': self.time_span_hours,
            'average_per_hour': self.average_per_hour,
            'peak_hour': self.peak_hour
        }


class MessageStatsCalculator:
    """
    Pure mathematical message statistics calculator
    No database dependencies - works with in-memory data
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__ + '.MessageStatsCalculator')
    
    def calculate_volume_stats(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate basic volume statistics from message list
        
        Args:
            messages: List of message dictionaries
            
        Returns:
            Dictionary with volume statistics
        """
        if not messages:
            return self._empty_volume_stats()
        
        # Extract basic counts
        total_messages = len(messages)
        unique_authors = len(set(
            msg.get('author', 'unknown') for msg in messages 
            if msg and msg.get('author')
        ))
        unique_channels = len(set(
            msg.get('channel', 'unknown') for msg in messages 
            if msg and msg.get('channel')
        ))
        
        # Calculate temporal patterns
        timestamps = [
            self._parse_timestamp(msg.get('timestamp'))
            for msg in messages if msg
        ]
        valid_timestamps = [ts for ts in timestamps if ts]
        
        avg_per_hour = 0.0
        if valid_timestamps:
            time_span = self._calculate_time_span_hours(valid_timestamps)
            if time_span > 0:
                avg_per_hour = total_messages / time_span
        
        return {
            'total_messages': total_messages,
            'unique_authors': unique_authors,
            'channels_active': unique_channels,
            'avg_messages_per_hour': round(avg_per_hour, 2),
            'by_channel': self._count_by_field(messages, 'channel'),
            'by_author': self._count_by_field(messages, 'author'),
            'temporal_distribution': self._analyze_temporal_distribution(valid_timestamps)
        }
    
    def calculate_channel_rankings(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Rank channels by activity level with scoring
        
        Args:
            messages: List of message dictionaries
            
        Returns:
            List of channel statistics sorted by activity
        """
        channel_stats = defaultdict(lambda: {
            'message_count': 0,
            'unique_authors': set(),
            'timestamps': []
        })
        
        # Aggregate data by channel
        for msg in messages:
            channel = msg.get('channel', 'unknown')
            if channel:
                channel_stats[channel]['message_count'] += 1
                if msg.get('author'):
                    channel_stats[channel]['unique_authors'].add(msg.get('author'))
                
                timestamp = self._parse_timestamp(msg.get('timestamp'))
                if timestamp:
                    channel_stats[channel]['timestamps'].append(timestamp)
        
        # Calculate rankings
        rankings = []
        for channel, stats in channel_stats.items():
            unique_authors = len(stats['unique_authors'])
            message_count = stats['message_count']
            
            # Calculate activity score (0-1)
            activity_score = self._calculate_activity_score(
                message_count, unique_authors, stats['timestamps']
            )
            
            rankings.append({
                'channel_name': channel,
                'message_count': message_count,
                'unique_authors': unique_authors,
                'activity_score': round(activity_score, 2)
            })
        
        # Sort by message count (primary) and activity score (secondary)
        rankings.sort(key=lambda x: (x['message_count'], x['activity_score']), reverse=True)
        return rankings
    
    def _empty_volume_stats(self) -> Dict[str, Any]:
        """Return empty statistics structure"""
        return {
            'total_messages': 0,
            'unique_authors': 0,
            'channels_active': 0,
            'avg_messages_per_hour': 0.0,
            'by_channel': {},
            'by_author': {},
            'temporal_distribution': {}
        }
    
    def _count_by_field(self, messages: List[Dict[str, Any]], field: str) -> Dict[str, int]:
        """Count messages by a specific field"""
        counter = Counter()
        for msg in messages:
            if msg:  # Handle None messages
                value = msg.get(field)
                if value:
                    counter[value] += 1
        return dict(counter)
    
    def _parse_timestamp(self, timestamp: Any) -> Optional[datetime]:
        """Parse various timestamp formats into datetime"""
        if not timestamp:
            return None
        
        if isinstance(timestamp, datetime):
            return timestamp
        elif isinstance(timestamp, str):
            try:
                # Handle ISO format
                return datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except ValueError:
                try:
                    # Handle other common formats
                    return datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    return None
        
        return None
    
    def _calculate_time_span_hours(self, timestamps: List[datetime]) -> float:
        """Calculate time span in hours"""
        if len(timestamps) < 2:
            return 24.0  # Default to 1 day if insufficient data
        
        min_time = min(timestamps)
        max_time = max(timestamps)
        
        time_diff = max_time - min_time
        return time_diff.total_seconds() / 3600.0
    
    def _analyze_temporal_distribution(self, timestamps: List[datetime]) -> Dict[str, Any]:
        """Analyze when messages are sent (hour of day patterns)"""
        if not timestamps:
            return {}
        
        hour_counts = Counter(ts.hour for ts in timestamps)
        
        return {
            'by_hour': dict(hour_counts),
            'peak_hour': hour_counts.most_common(1)[0][0] if hour_counts else None,
            'total_hours_active': len(hour_counts)
        }
    
    def _calculate_activity_score(
        self, 
        message_count: int, 
        unique_authors: int, 
        timestamps: List[datetime]
    ) -> float:
        """
        Calculate activity score (0-1) based on multiple factors
        
        Args:
            message_count: Total messages
            unique_authors: Number of unique participants
            timestamps: List of message timestamps
            
        Returns:
            Activity score between 0.0 and 1.0
        """
        if message_count == 0:
            return 0.0
        
        # Base score from message volume (normalize to reasonable scale)
        volume_score = min(message_count / 100.0, 1.0)  # 100 messages = max volume score
        
        # Participation score from unique authors
        participation_score = min(unique_authors / 10.0, 1.0)  # 10 authors = max participation score
        
        # Temporal consistency score (how spread out are the messages)
        consistency_score = 0.0
        if timestamps:
            time_span = self._calculate_time_span_hours(timestamps)
            if time_span > 0:
                # Higher score for consistent activity over time
                consistency_score = min(time_span / 168.0, 1.0)  # 1 week = max consistency score
        
        # Weighted combination
        activity_score = (
            volume_score * 0.5 +
            participation_score * 0.3 +
            consistency_score * 0.2
        )
        
        return min(activity_score, 1.0)


class ActivityAnalyzer:
    """
    Comprehensive activity analyzer with database integration
    Provides deterministic statistics across all data sources
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize activity analyzer
        
        Args:
            db_path: Path to SQLite database (optional)
        """
        self.db_path = db_path or self._get_default_db_path()
        self.logger = logging.getLogger(__name__ + '.ActivityAnalyzer')
        self.message_calculator = MessageStatsCalculator()
        
        # Initialize database connection if path exists
        self._init_database_connection()
    
    def _get_default_db_path(self) -> str:
        """Get default database path"""
        project_root = Path(__file__).parent.parent.parent
        return str(project_root / "data" / "search" / "search_database.db")
    
    def _init_database_connection(self):
        """Initialize database connection with error handling"""
        try:
            if Path(self.db_path).exists():
                # Test connection
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                    tables = cursor.fetchall()
                    self.logger.debug(f"Connected to database with {len(tables)} tables")
            else:
                self.logger.warning(f"Database not found at {self.db_path}")
        except Exception as e:
            self.logger.error(f"Database connection failed: {e}")
    
    def calculate_message_stats(
        self, 
        messages: List[Dict[str, Any]], 
        time_period: str
    ) -> Dict[str, Any]:
        """
        Calculate message statistics for given time period
        
        Args:
            messages: List of message dictionaries
            time_period: Time period identifier
            
        Returns:
            Message statistics dictionary
        """
        stats = self.message_calculator.calculate_volume_stats(messages)
        stats['time_period'] = time_period
        stats['calculation_timestamp'] = datetime.now().isoformat()
        
        return stats
    
    def analyze_temporal_patterns(
        self, 
        messages: List[Dict[str, Any]], 
        granularity: str = "daily"
    ) -> List[Dict[str, Any]]:
        """
        Analyze temporal patterns in message data
        
        Args:
            messages: List of message dictionaries
            granularity: Analysis granularity ("daily", "hourly", "weekly")
            
        Returns:
            List of temporal pattern records
        """
        if not messages:
            return []
        
        # Group messages by time period
        if granularity == "daily":
            return self._analyze_daily_patterns(messages)
        elif granularity == "hourly":
            return self._analyze_hourly_patterns(messages)
        elif granularity == "weekly":
            return self._analyze_weekly_patterns(messages)
        else:
            raise ValueError(f"Unsupported granularity: {granularity}")
    
    def calculate_cross_source_activity(self, activity_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate activity correlation across multiple data sources
        
        Args:
            activity_data: List of activity records with source breakdown
            
        Returns:
            Cross-source activity correlation
        """
        if not activity_data:
            return self._empty_cross_source_stats()
        
        # Aggregate totals
        total_slack = sum(record.get('slack_messages', 0) for record in activity_data)
        total_calendar = sum(record.get('calendar_meetings', 0) for record in activity_data)
        total_drive = sum(record.get('drive_file_changes', 0) for record in activity_data)
        
        total_interactions = total_slack + total_calendar + total_drive
        
        # Calculate collaboration score (0-1)
        collaboration_score = self._calculate_collaboration_score(
            total_slack, total_calendar, total_drive
        )
        
        return {
            'total_interactions': total_interactions,
            'collaboration_score': round(collaboration_score, 2),
            'productivity_indicators': {
                'communication': total_slack,
                'meetings': total_calendar,
                'document_activity': total_drive
            },
            'source_breakdown': {
                'slack_percentage': (total_slack / total_interactions * 100) if total_interactions > 0 else 0,
                'calendar_percentage': (total_calendar / total_interactions * 100) if total_interactions > 0 else 0,
                'drive_percentage': (total_drive / total_interactions * 100) if total_interactions > 0 else 0
            }
        }
    
    def analyze_meeting_patterns(
        self, 
        meetings: List[Dict[str, Any]], 
        time_period: str
    ) -> Dict[str, Any]:
        """
        Analyze meeting patterns and characteristics
        
        Args:
            meetings: List of meeting/calendar event dictionaries
            time_period: Time period for analysis
            
        Returns:
            Meeting pattern analysis
        """
        if not meetings:
            return self._empty_meeting_stats()
        
        total_meetings = len(meetings)
        total_duration_minutes = sum(
            meeting.get('duration_minutes', 0) for meeting in meetings
        )
        total_duration_hours = total_duration_minutes / 60.0
        
        # Analyze attendee patterns
        all_attendees = []
        for meeting in meetings:
            attendees = meeting.get('attendees', [])
            if isinstance(attendees, list):
                all_attendees.extend(attendees)
        
        average_attendees = len(all_attendees) / total_meetings if total_meetings > 0 else 0
        
        # Categorize meeting types
        meeting_types = self._categorize_meetings(meetings)
        
        return {
            'total_meetings': total_meetings,
            'total_duration_hours': round(total_duration_hours, 2),
            'average_duration_minutes': total_duration_minutes / total_meetings if total_meetings > 0 else 0,
            'average_attendees': round(average_attendees, 2),
            'meeting_types': meeting_types,
            'time_period': time_period
        }
    
    def detect_recurring_patterns(self, meetings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Detect recurring meeting patterns
        
        Args:
            meetings: List of meeting dictionaries with start times
            
        Returns:
            List of detected recurring patterns
        """
        if not meetings:
            return []
        
        # Group by title similarity
        title_groups = defaultdict(list)
        for meeting in meetings:
            title = meeting.get('title', '').strip().lower()
            # Simple title normalization
            normalized_title = self._normalize_meeting_title(title)
            title_groups[normalized_title].append(meeting)
        
        patterns = []
        for title, meeting_group in title_groups.items():
            if len(meeting_group) >= 3:  # Need at least 3 occurrences to detect pattern
                pattern = self._analyze_meeting_recurrence(title, meeting_group)
                if pattern:
                    patterns.append(pattern)
        
        return patterns
    
    def calculate_resource_utilization(self, meetings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate meeting room and resource utilization
        
        Args:
            meetings: List of meeting dictionaries
            
        Returns:
            Resource utilization statistics
        """
        if not meetings:
            return {'total_meeting_hours': 0}
        
        resource_usage = defaultdict(lambda: {
            'total_hours': 0,
            'booking_count': 0
        })
        
        virtual_meetings = 0
        total_hours = 0
        
        for meeting in meetings:
            duration_minutes = meeting.get('duration_minutes', 0)
            duration_hours = duration_minutes / 60.0
            total_hours += duration_hours
            
            location = meeting.get('location', '').strip()
            if location:
                if self._is_virtual_location(location):
                    virtual_meetings += 1
                else:
                    resource_usage[location]['total_hours'] += duration_hours
                    resource_usage[location]['booking_count'] += 1
        
        result = dict(resource_usage)
        result['virtual_meetings'] = {
            'count': virtual_meetings,
            'total_hours': sum(
                meeting.get('duration_minutes', 0) / 60.0
                for meeting in meetings
                if self._is_virtual_location(meeting.get('location', ''))
            )
        }
        result['total_meeting_hours'] = round(total_hours, 2)
        
        return result
    
    def generate_daily_timeline(self, activities: List[Dict[str, Any]], days: int = 7) -> List[Dict[str, Any]]:
        """
        Generate daily activity timeline
        
        Args:
            activities: List of activity records with dates
            days: Number of days to generate
            
        Returns:
            List of daily activity summaries
        """
        # Group activities by date
        daily_activities = defaultdict(list)
        for activity in activities:
            activity_date = activity.get('date')
            if activity_date:
                daily_activities[activity_date].append(activity)
        
        # Generate timeline for requested days
        timeline = []
        current_date = date.today()
        
        for i in range(days):
            day_date = current_date - timedelta(days=i)
            day_str = day_date.isoformat()
            
            day_activities = daily_activities.get(day_str, [])
            total_activities = sum(activity.get('count', 1) for activity in day_activities)
            
            # Breakdown by activity type
            breakdown = defaultdict(int)
            for activity in day_activities:
                activity_type = activity.get('type', 'unknown')
                breakdown[activity_type] += activity.get('count', 1)
            
            # Calculate productivity score (0-1)
            productivity_score = self._calculate_daily_productivity_score(day_activities)
            
            timeline.append({
                'date': day_str,
                'total_activities': total_activities,
                'breakdown': dict(breakdown),
                'productivity_score': round(productivity_score, 2),
                'day_of_week': day_date.strftime('%A')
            })
        
        return timeline
    
    def generate_weekly_summary(self, start_date: Optional[date] = None) -> Dict[str, Any]:
        """
        Generate weekly activity summary
        
        Args:
            start_date: Week start date (defaults to last Monday)
            
        Returns:
            Weekly summary statistics
        """
        if start_date is None:
            today = date.today()
            start_date = today - timedelta(days=today.weekday())
        
        end_date = start_date + timedelta(days=6)
        
        # Mock weekly data (in real implementation, query database)
        weekly_data = self._query_weekly_data(start_date, end_date)
        
        return {
            'week_start': start_date.isoformat(),
            'week_end': end_date.isoformat(),
            'total_messages': weekly_data.get('messages', 0),
            'total_meetings': weekly_data.get('meetings', 0),
            'active_channels': weekly_data.get('active_channels', 0),
            'unique_participants': weekly_data.get('unique_participants', 0),
            'productivity_score': self._calculate_weekly_productivity_score(weekly_data)
        }
    
    def compare_periods(self, period1: str, period2: str) -> Dict[str, Any]:
        """
        Compare activity between two time periods
        
        Args:
            period1: First time period identifier
            period2: Second time period identifier
            
        Returns:
            Comparison analysis
        """
        # Get stats for both periods
        period1_stats = self._get_period_stats(period1)
        period2_stats = self._get_period_stats(period2)
        
        # Calculate changes
        changes = {}
        for key in period1_stats:
            if key in period2_stats and isinstance(period1_stats[key], (int, float)):
                old_value = period2_stats[key]
                new_value = period1_stats[key]
                
                absolute_change = new_value - old_value
                percentage_change = self._calculate_growth_rate(old_value, new_value)
                
                changes[key] = {
                    'absolute': absolute_change,
                    'percentage': percentage_change
                }
        
        return {
            'period1_stats': period1_stats,
            'period2_stats': period2_stats,
            'changes': changes,
            'growth_rate': changes.get('messages', {}).get('percentage', 0)
        }
    
    def get_message_stats(self, time_period: str) -> Dict[str, Any]:
        """
        Get message statistics for specified time period
        
        Args:
            time_period: Time period identifier
            
        Returns:
            Message statistics
        """
        # Query database or return mock data
        stats = self._query_period_stats(time_period)
        
        return {
            'total_messages': stats.get('messages', 0),
            'unique_authors': stats.get('authors', 0),
            'channels_active': stats.get('channels', 0),
            'avg_messages_per_hour': stats.get('avg_per_hour', 0.0)
        }
    
    def get_channel_rankings(self, time_period: str) -> List[Dict[str, Any]]:
        """
        Get channel activity rankings
        
        Args:
            time_period: Time period identifier
            
        Returns:
            List of ranked channels
        """
        return self._query_channel_stats(time_period)
    
    def get_person_activity(self, person_email: str, time_period: str) -> Dict[str, Any]:
        """
        Get activity summary for specific person
        
        Args:
            person_email: Person's email address
            time_period: Time period identifier
            
        Returns:
            Person activity statistics
        """
        return self._query_person_stats(person_email, time_period)
    
    def calculate_productivity_indicators(self, time_period: str) -> Dict[str, Any]:
        """
        Calculate productivity indicators for time period
        
        Args:
            time_period: Time period identifier
            
        Returns:
            Productivity indicators
        """
        return self._calculate_productivity_metrics(time_period)
    
    # Helper methods for mathematical calculations
    
    def _calculate_growth_rate(self, old_value: float, new_value: float) -> Optional[float]:
        """Calculate percentage growth rate"""
        if old_value == 0:
            return None if new_value == 0 else float('inf')
        return ((new_value - old_value) / old_value) * 100
    
    def _calculate_average(self, values: List[float]) -> float:
        """Calculate average with empty list handling"""
        if not values:
            return 0.0
        return sum(values) / len(values)
    
    def _calculate_duration_minutes(self, start_time: datetime, end_time: datetime) -> int:
        """Calculate duration between two datetimes in minutes"""
        duration = end_time - start_time
        return int(duration.total_seconds() / 60)
    
    # Database query methods (mock implementations)
    
    def _query_period_stats(self, time_period: str) -> Dict[str, Any]:
        """Query database for period statistics (mock implementation)"""
        # Mock data for testing
        mock_data = {
            'today': {'messages': 25, 'authors': 5, 'channels': 3, 'avg_per_hour': 3.1},
            'last_week': {'messages': 180, 'authors': 12, 'channels': 8, 'avg_per_hour': 1.07},
            'past_30_days': {'messages': 850, 'authors': 25, 'channels': 15, 'avg_per_hour': 1.18}
        }
        return mock_data.get(time_period, {'messages': 0, 'authors': 0, 'channels': 0, 'avg_per_hour': 0.0})
    
    def _query_channel_stats(self, time_period: str) -> List[Dict[str, Any]]:
        """Query database for channel statistics (mock implementation)"""
        return [
            {'channel_name': 'general', 'message_count': 150, 'unique_authors': 12, 'activity_score': 0.95},
            {'channel_name': 'engineering', 'message_count': 120, 'unique_authors': 8, 'activity_score': 0.85},
            {'channel_name': 'random', 'message_count': 80, 'unique_authors': 15, 'activity_score': 0.65},
        ]
    
    def _query_person_stats(self, person_email: str, time_period: str) -> Dict[str, Any]:
        """Query database for person statistics (mock implementation)"""
        return {
            'slack_messages_sent': 45,
            'slack_channels_active': 6,
            'meetings_attended': 8,
            'meetings_organized': 2,
            'drive_files_modified': 12,
            'total_interactions': 67
        }
    
    def _calculate_productivity_metrics(self, time_period: str) -> Dict[str, Any]:
        """Calculate productivity metrics (mock implementation)"""
        return {
            'communication_volume': 150,
            'collaboration_score': 0.75,
            'meeting_efficiency': 0.68,
            'response_time_avg': 2.3,
            'active_work_hours': 7.5,
            'cross_channel_engagement': 0.85
        }
    
    def _query_weekly_data(self, start_date: date, end_date: date) -> Dict[str, Any]:
        """Query database for weekly data (mock implementation)"""
        return {
            'messages': 150,
            'meetings': 12,
            'drive_changes': 25,
            'active_channels': 8,
            'unique_participants': 15
        }
    
    def _get_period_stats(self, period: str) -> Dict[str, Any]:
        """Get statistics for a specific period (mock implementation)"""
        if period == "this_week":
            return {'messages': 100, 'meetings': 10, 'drive_changes': 20}
        elif period == "last_week":
            return {'messages': 80, 'meetings': 8, 'drive_changes': 15}
        else:
            return {'messages': 0, 'meetings': 0, 'drive_changes': 0}
    
    # Helper methods for complex calculations
    
    def _analyze_daily_patterns(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze daily message patterns"""
        daily_counts = defaultdict(int)
        
        for message in messages:
            timestamp = self.message_calculator._parse_timestamp(message.get('timestamp'))
            if timestamp:
                date_str = timestamp.date().isoformat()
                daily_counts[date_str] += 1
        
        # Convert to list format
        patterns = []
        for date_str in sorted(daily_counts.keys(), reverse=True):
            patterns.append({
                'date': date_str,
                'message_count': daily_counts[date_str]
            })
        
        return patterns[:7]  # Last 7 days
    
    def _analyze_hourly_patterns(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze hourly message patterns"""
        hourly_counts = defaultdict(int)
        
        for message in messages:
            timestamp = self.message_calculator._parse_timestamp(message.get('timestamp'))
            if timestamp:
                hour = timestamp.hour
                hourly_counts[hour] += 1
        
        patterns = []
        for hour in range(24):
            patterns.append({
                'hour': hour,
                'message_count': hourly_counts[hour]
            })
        
        return patterns
    
    def _analyze_weekly_patterns(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze weekly message patterns"""
        # Similar to daily but group by week
        weekly_counts = defaultdict(int)
        
        for message in messages:
            timestamp = self.message_calculator._parse_timestamp(message.get('timestamp'))
            if timestamp:
                # Get week start date (Monday)
                week_start = timestamp.date() - timedelta(days=timestamp.weekday())
                week_str = week_start.isoformat()
                weekly_counts[week_str] += 1
        
        patterns = []
        for week_str in sorted(weekly_counts.keys(), reverse=True):
            patterns.append({
                'week_start': week_str,
                'message_count': weekly_counts[week_str]
            })
        
        return patterns[:4]  # Last 4 weeks
    
    def _calculate_collaboration_score(
        self, 
        slack_messages: int, 
        calendar_meetings: int, 
        drive_changes: int
    ) -> float:
        """Calculate collaboration score based on activity distribution"""
        total_activity = slack_messages + calendar_meetings + drive_changes
        
        if total_activity == 0:
            return 0.0
        
        # Calculate diversity score (higher when activities are balanced)
        ratios = [
            slack_messages / total_activity,
            calendar_meetings / total_activity,
            drive_changes / total_activity
        ]
        
        # Use Shannon entropy concept for diversity
        import math
        entropy = 0.0
        for ratio in ratios:
            if ratio > 0:
                entropy -= ratio * math.log2(ratio)  # Shannon entropy formula
        
        # Normalize to 0-1 scale
        max_entropy = 1.58  # log2(3) for 3 equally distributed sources
        return min(entropy / max_entropy, 1.0)
    
    def _categorize_meetings(self, meetings: List[Dict[str, Any]]) -> Dict[str, int]:
        """Categorize meetings by type"""
        categories = defaultdict(int)
        
        for meeting in meetings:
            attendee_count = len(meeting.get('attendees', []))
            
            # Also check title for specific patterns
            title = meeting.get('title', '').lower()
            
            if '1:1' in title or (attendee_count <= 2):
                categories['1:1'] += 1
            elif attendee_count <= 10 or any(keyword in title for keyword in ['team', 'standup', 'weekly', 'review']):
                categories['team'] += 1
            elif attendee_count > 10:
                categories['large_group'] += 1
            else:
                categories['small_group'] += 1
        
        return dict(categories)
    
    def _normalize_meeting_title(self, title: str) -> str:
        """Normalize meeting title for pattern detection"""
        # Remove dates, times, and other variable elements
        import re
        
        # Remove common variable patterns
        title = re.sub(r'\d{1,2}/\d{1,2}(/\d{2,4})?', '', title)  # Dates
        title = re.sub(r'\d{1,2}:\d{2}', '', title)  # Times
        title = re.sub(r'#\d+', '', title)  # Issue numbers
        title = re.sub(r'\(\d+\)', '', title)  # Numbers in parentheses
        
        # Clean up whitespace
        title = ' '.join(title.split())
        
        return title.strip()
    
    def _analyze_meeting_recurrence(self, title: str, meetings: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Analyze if meetings follow a recurring pattern"""
        if len(meetings) < 3:
            return None
        
        # Extract start times
        start_times = []
        for meeting in meetings:
            start = meeting.get('start')
            if isinstance(start, datetime):
                start_times.append(start)
            elif isinstance(start, str):
                try:
                    dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                    start_times.append(dt)
                except ValueError:
                    continue
        
        if len(start_times) < 3:
            return None
        
        # Sort by start time
        start_times.sort()
        
        # Calculate intervals between meetings
        intervals = []
        for i in range(1, len(start_times)):
            interval = start_times[i] - start_times[i-1]
            intervals.append(interval.days)
        
        # Detect pattern (weekly = 7 days, daily = 1 day, etc.)
        if intervals:
            avg_interval = sum(intervals) / len(intervals)
            
            if 6 <= avg_interval <= 8:
                pattern_type = "weekly"
            elif 13 <= avg_interval <= 15:
                pattern_type = "biweekly"
            elif 25 <= avg_interval <= 35:
                pattern_type = "monthly"
            elif avg_interval == 1:
                pattern_type = "daily"
            else:
                pattern_type = "irregular"
            
            # Calculate confidence based on consistency
            variance = statistics.variance(intervals) if len(intervals) > 1 else 0
            confidence = max(0, 1 - (variance / avg_interval)) if avg_interval > 0 else 0
            
            return {
                'title': title,
                'pattern_type': pattern_type,
                'occurrence_count': len(meetings),
                'average_interval_days': round(avg_interval, 1),
                'confidence': round(confidence, 2)
            }
        
        return None
    
    def _is_virtual_location(self, location: str) -> bool:
        """Check if meeting location is virtual"""
        virtual_keywords = [
            'zoom', 'meet', 'teams', 'webex', 'skype', 
            'hangouts', 'virtual', 'online', 'remote'
        ]
        location_lower = location.lower()
        return any(keyword in location_lower for keyword in virtual_keywords)
    
    def _calculate_daily_productivity_score(self, activities: List[Dict[str, Any]]) -> float:
        """Calculate daily productivity score (0-1)"""
        if not activities:
            return 0.0
        
        total_activities = sum(activity.get('count', 1) for activity in activities)
        
        # Simple scoring based on activity volume and diversity
        volume_score = min(total_activities / 50.0, 1.0)  # 50 activities = max score
        diversity_score = min(len(activities) / 10.0, 1.0)  # 10 different activity types = max score
        
        return (volume_score * 0.7) + (diversity_score * 0.3)
    
    def _calculate_weekly_productivity_score(self, weekly_data: Dict[str, Any]) -> float:
        """Calculate weekly productivity score (0-1)"""
        messages = weekly_data.get('messages', 0)
        meetings = weekly_data.get('meetings', 0)
        participants = weekly_data.get('unique_participants', 0)
        
        # Balanced scoring across multiple dimensions
        communication_score = min(messages / 200.0, 1.0)  # 200 messages = max score
        collaboration_score = min(meetings / 20.0, 1.0)  # 20 meetings = max score
        engagement_score = min(participants / 20.0, 1.0)  # 20 participants = max score
        
        return round(
            (communication_score * 0.4) + 
            (collaboration_score * 0.3) + 
            (engagement_score * 0.3),
            2
        )
    
    def _empty_cross_source_stats(self) -> Dict[str, Any]:
        """Return empty cross-source statistics"""
        return {
            'total_interactions': 0,
            'collaboration_score': 0.0,
            'productivity_indicators': {
                'communication': 0,
                'meetings': 0,
                'document_activity': 0
            },
            'source_breakdown': {
                'slack_percentage': 0,
                'calendar_percentage': 0,
                'drive_percentage': 0
            }
        }
    
    def _empty_meeting_stats(self) -> Dict[str, Any]:
        """Return empty meeting statistics"""
        return {
            'total_meetings': 0,
            'total_duration_hours': 0.0,
            'average_duration_minutes': 0,
            'average_attendees': 0.0,
            'meeting_types': {},
            'time_period': 'unknown'
        }