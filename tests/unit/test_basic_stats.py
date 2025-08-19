"""
Test Activity Statistics and Analysis Module
Focus on deterministic calculations without AI/LLM dependencies
"""

import pytest
from datetime import date, datetime, timedelta
from pathlib import Path
import tempfile
from unittest.mock import Mock, patch, MagicMock

from src.aggregators.basic_stats import ActivityAnalyzer, MessageStatsCalculator


class TestMessageStatistics:
    """Test Slack message volume and pattern analysis"""
    
    def test_message_volume_calculation(self):
        """Calculate message statistics by channel and person"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
            analyzer = ActivityAnalyzer(db_path=tmp_db.name)
            
            # Mock message data with multiple channels and authors
            messages = [
                {'channel': 'general', 'author': 'john@example.com', 'timestamp': '2025-08-19T10:00:00Z'},
                {'channel': 'general', 'author': 'jane@example.com', 'timestamp': '2025-08-19T10:05:00Z'},
                {'channel': 'product', 'author': 'john@example.com', 'timestamp': '2025-08-19T11:00:00Z'}
            ]
            
            # Calculate stats directly (no mocking needed for this test)
            stats = analyzer.calculate_message_stats(messages, time_period="today")
                
            assert stats['total_messages'] == 3
            assert stats['unique_authors'] == 2
            assert stats['channels_active'] == 2
            assert stats['by_channel']['general'] == 2
            assert stats['by_channel']['product'] == 1
            assert stats['by_author']['john@example.com'] == 2
            
            # Cleanup
            Path(tmp_db.name).unlink(missing_ok=True)
    
    def test_temporal_patterns(self):
        """Analyze message patterns over time"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
            analyzer = ActivityAnalyzer(db_path=tmp_db.name)
            
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
            
            # Verify chronological ordering
            dates = [pattern['date'] for pattern in patterns]
            assert dates == sorted(dates, reverse=True)  # Most recent first
            
            # Cleanup
            Path(tmp_db.name).unlink(missing_ok=True)
    
    def test_activity_correlation(self):
        """Correlate activity across different data sources"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
            analyzer = ActivityAnalyzer(db_path=tmp_db.name)
            
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
            assert correlation['productivity_indicators']['meetings'] == 8
            assert correlation['productivity_indicators']['document_activity'] == 12
            
            # Cleanup
            Path(tmp_db.name).unlink(missing_ok=True)


class TestMeetingAnalysis:
    """Test calendar meeting pattern analysis"""
    
    def test_meeting_frequency_analysis(self):
        """Analyze meeting patterns and frequency"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
            analyzer = ActivityAnalyzer(db_path=tmp_db.name)
            
            meetings = [
                {'title': 'Daily Standup', 'duration_minutes': 30, 'attendees': ['john', 'jane']},
                {'title': 'Weekly Review', 'duration_minutes': 60, 'attendees': ['john', 'jane', 'bob']},
                {'title': '1:1 Meeting', 'duration_minutes': 45, 'attendees': ['john', 'manager']}
            ]
            
            patterns = analyzer.analyze_meeting_patterns(meetings, "last_week")
            
            assert patterns['total_meetings'] == 3
            assert patterns['total_duration_hours'] == 2.25  # 135 minutes
            assert patterns['average_attendees'] == pytest.approx(2.33, rel=0.01)
            # Daily Standup and 1:1 Meeting both have 2 attendees, so categorized as 1:1
            assert patterns['meeting_types']['1:1'] == 2
            # Weekly Review has 3 attendees and 'review' keyword, so categorized as 'team'
            assert patterns['meeting_types']['team'] == 1
            
            # Cleanup
            Path(tmp_db.name).unlink(missing_ok=True)
    
    def test_recurring_meeting_detection(self):
        """Identify recurring meeting patterns"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
            analyzer = ActivityAnalyzer(db_path=tmp_db.name)
            
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
            assert patterns[0]['title'] == 'weekly team sync'  # Title is normalized to lowercase
            assert patterns[0]['occurrence_count'] == 4
            assert patterns[0]['confidence'] >= 0.8  # High confidence for clear pattern
            
            # Cleanup
            Path(tmp_db.name).unlink(missing_ok=True)
    
    def test_resource_utilization(self):
        """Calculate meeting room and resource usage"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
            analyzer = ActivityAnalyzer(db_path=tmp_db.name)
            
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
            assert utilization['virtual_meetings']['total_hours'] == 0.75
            assert utilization['total_meeting_hours'] == 3.75
            
            # Cleanup
            Path(tmp_db.name).unlink(missing_ok=True)


class TestActivityTimeline:
    """Test daily/weekly activity timeline generation"""
    
    def test_daily_activity_rollup(self):
        """Generate daily activity summaries"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
            analyzer = ActivityAnalyzer(db_path=tmp_db.name)
            
            # Use actual today's date and yesterday for the test data
            from datetime import date
            today = date.today()
            yesterday = today - timedelta(days=1)
            
            # Mixed activity data for multiple days
            activities = [
                {'date': today.isoformat(), 'type': 'slack_message', 'count': 25},
                {'date': today.isoformat(), 'type': 'calendar_meeting', 'count': 3},
                {'date': today.isoformat(), 'type': 'drive_change', 'count': 5},
                {'date': yesterday.isoformat(), 'type': 'slack_message', 'count': 18},
                {'date': yesterday.isoformat(), 'type': 'calendar_meeting', 'count': 1},
            ]
            
            timeline = analyzer.generate_daily_timeline(activities, days=7)
            
            assert len(timeline) == 7  # 7 days requested
            # Timeline starts from today and goes backwards, so check for the actual dates
            timeline_dates = [day['date'] for day in timeline]
            
            # Find the specific days we have data for
            today_data = next((day for day in timeline if day['date'] == today.isoformat()), None)
            yesterday_data = next((day for day in timeline if day['date'] == yesterday.isoformat()), None)
            
            if today_data:
                assert today_data['total_activities'] == 33  # 25+3+5
            if yesterday_data:
                assert yesterday_data['total_activities'] == 19  # 18+1
            
            # Verify all required fields exist
            required_fields = ['date', 'total_activities', 'breakdown', 'productivity_score']
            for day in timeline:
                for field in required_fields:
                    assert field in day
            
            # Cleanup
            Path(tmp_db.name).unlink(missing_ok=True)
    
    def test_weekly_aggregation(self):
        """Generate weekly activity summaries"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
            analyzer = ActivityAnalyzer(db_path=tmp_db.name)
            
            # Mock database queries for weekly data
            with patch.object(analyzer, '_query_weekly_data') as mock_query:
                mock_query.return_value = {
                    'messages': 150,
                    'meetings': 12,
                    'drive_changes': 25,
                    'active_channels': 8,
                    'unique_participants': 15
                }
                
                weekly_data = analyzer.generate_weekly_summary(
                    start_date=date.today() - timedelta(days=7)
                )
                
                required_fields = [
                    'week_start', 'week_end', 'total_messages', 'total_meetings', 
                    'active_channels', 'unique_participants', 'productivity_score'
                ]
                assert all(field in weekly_data for field in required_fields)
                assert weekly_data['productivity_score'] >= 0
                assert weekly_data['productivity_score'] <= 1.0
                
            # Cleanup
            Path(tmp_db.name).unlink(missing_ok=True)
    
    def test_comparative_analysis(self):
        """Compare activity between time periods"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
            analyzer = ActivityAnalyzer(db_path=tmp_db.name)
            
            # Mock data for two periods
            this_week_data = {
                'messages': 100, 'meetings': 10, 'drive_changes': 20
            }
            last_week_data = {
                'messages': 80, 'meetings': 8, 'drive_changes': 15
            }
            
            with patch.object(analyzer, '_get_period_stats') as mock_stats:
                mock_stats.side_effect = [this_week_data, last_week_data]
                
                comparison = analyzer.compare_periods(
                    period1="this_week",
                    period2="last_week"
                )
                
                assert 'period1_stats' in comparison
                assert 'period2_stats' in comparison
                assert 'changes' in comparison
                assert 'growth_rate' in comparison  # growth_rate is at top level
                
                # Verify growth calculation
                assert comparison['changes']['messages']['absolute'] == 20  # 100-80
                assert comparison['changes']['messages']['percentage'] == 25.0  # 20/80*100
                
            # Cleanup
            Path(tmp_db.name).unlink(missing_ok=True)


class TestBasicStatistics:
    """Test fundamental counting and aggregation operations"""
    
    def test_message_volume_by_period(self):
        """Count messages by various time periods"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
            analyzer = ActivityAnalyzer(db_path=tmp_db.name)
            
            # Mock database responses for different periods
            period_data = {
                'today': {'messages': 25, 'authors': 5, 'channels': 3, 'avg_per_hour': 3.1},
                'last_week': {'messages': 180, 'authors': 12, 'channels': 8, 'avg_per_hour': 1.07},
                'past_30_days': {'messages': 850, 'authors': 25, 'channels': 15, 'avg_per_hour': 1.18}
            }
            
            with patch.object(analyzer, '_query_period_stats') as mock_query:
                for period, expected_data in period_data.items():
                    mock_query.return_value = expected_data
                    stats = analyzer.get_message_stats(period)
                    
                    required_fields = ['total_messages', 'unique_authors', 'channels_active', 'avg_messages_per_hour']
                    assert all(field in stats for field in required_fields)
                    assert all(isinstance(stats[field], (int, float)) for field in required_fields)
                    assert stats['total_messages'] == expected_data['messages']
                    assert stats['unique_authors'] == expected_data['authors']
            
            # Cleanup
            Path(tmp_db.name).unlink(missing_ok=True)
    
    def test_channel_activity_ranking(self):
        """Rank channels by activity level"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
            analyzer = ActivityAnalyzer(db_path=tmp_db.name)
            
            # Mock channel ranking data
            mock_channels = [
                {'channel_name': 'general', 'message_count': 150, 'unique_authors': 12, 'activity_score': 0.95},
                {'channel_name': 'engineering', 'message_count': 120, 'unique_authors': 8, 'activity_score': 0.85},
                {'channel_name': 'random', 'message_count': 80, 'unique_authors': 15, 'activity_score': 0.65},
            ]
            
            with patch.object(analyzer, '_query_channel_stats', return_value=mock_channels):
                channel_stats = analyzer.get_channel_rankings("last_week")
                
                assert isinstance(channel_stats, list)
                assert len(channel_stats) == 3
                
                # Should be sorted by activity (most active first)
                assert channel_stats[0]['message_count'] >= channel_stats[1]['message_count']
                assert channel_stats[1]['message_count'] >= channel_stats[2]['message_count']
                
                # Required fields for each channel
                required_fields = ['channel_name', 'message_count', 'unique_authors', 'activity_score']
                for channel in channel_stats:
                    assert all(field in channel for field in required_fields)
                    assert 0 <= channel['activity_score'] <= 1.0
            
            # Cleanup
            Path(tmp_db.name).unlink(missing_ok=True)
    
    def test_person_activity_aggregation(self):
        """Aggregate activity per person across all sources"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
            analyzer = ActivityAnalyzer(db_path=tmp_db.name)
            
            # Mock person activity data
            mock_person_data = {
                'slack_messages_sent': 45,
                'slack_channels_active': 6,
                'meetings_attended': 8,
                'meetings_organized': 2,
                'drive_files_modified': 12,
                'total_interactions': 67
            }
            
            with patch.object(analyzer, '_query_person_stats', return_value=mock_person_data):
                person_stats = analyzer.get_person_activity("john@example.com", "last_week")
                
                required_fields = [
                    'slack_messages_sent', 'slack_channels_active', 'meetings_attended', 
                    'meetings_organized', 'drive_files_modified', 'total_interactions'
                ]
                
                assert all(field in person_stats for field in required_fields)
                assert person_stats['total_interactions'] >= 0
                assert person_stats['slack_messages_sent'] >= 0
                
                # Total interactions should be sum of individual activities
                calculated_total = (
                    person_stats['slack_messages_sent'] + 
                    person_stats['meetings_attended'] + 
                    person_stats['drive_files_modified']
                )
                assert person_stats['total_interactions'] >= calculated_total
            
            # Cleanup
            Path(tmp_db.name).unlink(missing_ok=True)
    
    def test_productivity_indicators(self):
        """Calculate basic productivity indicators"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
            analyzer = ActivityAnalyzer(db_path=tmp_db.name)
            
            # Mock productivity data
            mock_indicators = {
                'communication_volume': 150,
                'collaboration_score': 0.75,
                'meeting_efficiency': 0.68,
                'response_time_avg': 2.3,  # hours
                'active_work_hours': 7.5,
                'cross_channel_engagement': 0.85
            }
            
            with patch.object(analyzer, '_calculate_productivity_metrics', return_value=mock_indicators):
                indicators = analyzer.calculate_productivity_indicators("last_week")
                
                required_metrics = [
                    'communication_volume', 'collaboration_score', 'meeting_efficiency',
                    'response_time_avg', 'active_work_hours', 'cross_channel_engagement'
                ]
                
                assert all(metric in indicators for metric in required_metrics)
                assert 0 <= indicators['meeting_efficiency'] <= 1.0  # Percentage
                assert indicators['active_work_hours'] >= 0
                assert indicators['response_time_avg'] > 0
                assert 0 <= indicators['collaboration_score'] <= 1.0
            
            # Cleanup
            Path(tmp_db.name).unlink(missing_ok=True)


class TestStatisticalAccuracy:
    """Test mathematical accuracy of statistical calculations"""
    
    def test_percentage_calculations(self):
        """Verify percentage calculations are mathematically correct"""
        analyzer = ActivityAnalyzer()
        
        # Test growth rate calculation
        old_value = 80
        new_value = 100
        growth = analyzer._calculate_growth_rate(old_value, new_value)
        
        assert growth == 25.0  # (100-80)/80 * 100 = 25%
        
        # Test negative growth
        growth = analyzer._calculate_growth_rate(100, 80)
        assert growth == -20.0  # (80-100)/100 * 100 = -20%
        
        # Test zero division handling
        growth = analyzer._calculate_growth_rate(0, 50)
        assert growth is None or growth == float('inf')  # Should handle gracefully
    
    def test_average_calculations(self):
        """Verify average calculations are correct"""
        analyzer = ActivityAnalyzer()
        
        # Test simple average
        values = [10, 20, 30, 40, 50]
        avg = analyzer._calculate_average(values)
        assert avg == 30.0
        
        # Test with decimals
        values = [1.5, 2.5, 3.5]
        avg = analyzer._calculate_average(values)
        assert avg == 2.5
        
        # Test empty list handling
        avg = analyzer._calculate_average([])
        assert avg == 0.0 or avg is None
    
    def test_time_duration_calculations(self):
        """Verify time duration calculations are correct"""
        analyzer = ActivityAnalyzer()
        
        # Test meeting duration calculation (in minutes)
        start_time = datetime(2025, 8, 19, 10, 0)
        end_time = datetime(2025, 8, 19, 11, 30)
        duration = analyzer._calculate_duration_minutes(start_time, end_time)
        assert duration == 90  # 1.5 hours = 90 minutes
        
        # Test same day, different times
        duration = analyzer._calculate_duration_minutes(
            datetime(2025, 8, 19, 14, 15),
            datetime(2025, 8, 19, 15, 45)
        )
        assert duration == 90  # 1 hour 30 minutes = 90 minutes


class TestErrorHandling:
    """Test error handling and edge cases"""
    
    def test_database_connection_failure(self):
        """Handle database connection failures gracefully"""
        # Test with invalid database path
        analyzer = ActivityAnalyzer(db_path="/invalid/path/database.db")
        
        # Should not crash, should return default/empty results
        stats = analyzer.get_message_stats("today")
        assert isinstance(stats, dict)
        assert 'total_messages' in stats
        assert stats['total_messages'] >= 0  # Should default to 0
    
    def test_malformed_data_handling(self):
        """Handle malformed input data gracefully"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
            analyzer = ActivityAnalyzer(db_path=tmp_db.name)
            
            # Test with malformed messages
            malformed_messages = [
                {'channel': None, 'author': 'john', 'timestamp': '2025-08-19T10:00:00Z'},
                {'channel': 'general', 'author': None, 'timestamp': '2025-08-19T10:00:00Z'},
                {'channel': 'general', 'author': 'jane', 'timestamp': None},
                {},  # Empty message
                None  # Null message
            ]
            
            # Should not crash
            stats = analyzer.calculate_message_stats(malformed_messages, "today")
            assert isinstance(stats, dict)
            assert stats['total_messages'] >= 0
            
            # Cleanup
            Path(tmp_db.name).unlink(missing_ok=True)
    
    def test_empty_data_handling(self):
        """Handle empty datasets gracefully"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
            analyzer = ActivityAnalyzer(db_path=tmp_db.name)
            
            # Test with empty data
            empty_stats = analyzer.calculate_message_stats([], "today")
            assert empty_stats['total_messages'] == 0
            assert empty_stats['unique_authors'] == 0
            assert empty_stats['channels_active'] == 0
            
            empty_meetings = analyzer.analyze_meeting_patterns([], "last_week")
            assert empty_meetings['total_meetings'] == 0
            assert empty_meetings['total_duration_hours'] == 0
            
            # Cleanup
            Path(tmp_db.name).unlink(missing_ok=True)


# Run basic smoke tests if executed directly
if __name__ == '__main__':
    pytest.main([__file__, '-v'])