"""
Comprehensive test suite for person-based query functionality
Tests person identification, cross-system mapping, and activity aggregation

References:
- src/queries/person_queries.py - Person query utilities to be implemented  
- src/collectors/employee_collector.py - Employee roster data patterns
- src/search/database.py - SQLite FTS5 search infrastructure
- tests/fixtures/mock_slack_data.py - Mock data structure patterns
"""

import pytest
import json
import sqlite3
import tempfile
import os
from datetime import datetime, date, timedelta
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, List, Any

# Import modules to be implemented
from src.queries.person_queries import PersonResolver, PersonQueryEngine
from src.collectors.employee_collector import EmployeeCollector


class TestPersonResolver:
    """Test person identification and cross-system ID mapping"""
    
    def setup_method(self):
        """Setup for each test method with mock employee data"""
        # Mock employee roster data matching the collector patterns
        self.mock_employee_data = {
            "employees": [
                {
                    "email": "john.doe@company.com",
                    "slack_id": "U12345ABC",
                    "calendar_id": "john.doe@company.com",
                    "name": "John Doe",
                    "display_name": "John D.",
                    "real_name": "John Doe",
                    "status": "active"
                },
                {
                    "email": "jane.smith@company.com", 
                    "slack_id": "U67890DEF",
                    "calendar_id": "jane.smith@company.com",
                    "name": "Jane Smith",
                    "display_name": "Jane S.",
                    "real_name": "Jane Smith",
                    "status": "active"
                },
                {
                    "email": "archived.user@company.com",
                    "slack_id": "U99999ZZZ",
                    "calendar_id": "archived.user@company.com", 
                    "name": "Archived User",
                    "display_name": "Archived User",
                    "real_name": "Archived User",
                    "status": "archived"
                }
            ]
        }
        
        # Create PersonResolver with mock data
        self.resolver = PersonResolver(employee_data=self.mock_employee_data)
    
    def test_person_lookup_by_email(self):
        """Find person by email address accurately"""
        person = self.resolver.find_person("john.doe@company.com")
        
        assert person is not None
        assert person['email'] == "john.doe@company.com"
        assert person['slack_id'] == "U12345ABC"
        assert person['calendar_id'] == "john.doe@company.com"
        assert person['name'] == "John Doe"
        assert person['status'] == "active"
    
    def test_person_lookup_by_slack_id(self):
        """Find person by Slack user ID"""
        person = self.resolver.find_person("U67890DEF")
        
        assert person is not None
        assert person['slack_id'] == "U67890DEF"
        assert person['email'] == "jane.smith@company.com"
        assert person['name'] == "Jane Smith"
    
    def test_person_lookup_by_name(self):
        """Find person by display name or real name"""
        # Test display name
        person1 = self.resolver.find_person("John D.")
        assert person1 is not None
        assert person1['email'] == "john.doe@company.com"
        
        # Test real name
        person2 = self.resolver.find_person("Jane Smith")
        assert person2 is not None
        assert person2['email'] == "jane.smith@company.com"
    
    def test_case_insensitive_lookup(self):
        """Handle case-insensitive person searches"""
        person1 = self.resolver.find_person("JOHN.DOE@COMPANY.COM")
        person2 = self.resolver.find_person("john doe")
        
        assert person1 is not None
        assert person1['email'] == "john.doe@company.com"
        
        assert person2 is not None  
        assert person2['email'] == "john.doe@company.com"
    
    def test_cross_system_id_mapping(self):
        """Verify all system IDs are properly cross-referenced"""
        person = self.resolver.find_person("john.doe@company.com")
        
        # Verify all required ID fields present
        assert 'slack_id' in person
        assert 'calendar_id' in person
        assert 'email' in person
        
        # Verify Google workspace pattern (calendar_id == email)
        assert person['calendar_id'] == person['email']
        
        # Verify Slack ID format
        assert person['slack_id'].startswith('U')
        assert len(person['slack_id']) == 9  # Standard Slack ID length
    
    def test_nonexistent_person_handling(self):
        """Handle searches for nonexistent persons gracefully"""
        person = self.resolver.find_person("nonexistent@company.com")
        assert person is None
        
        person = self.resolver.find_person("U00000000")  # Nonexistent Slack ID
        assert person is None
        
        person = self.resolver.find_person("Unknown Person")
        assert person is None
    
    def test_archived_user_handling(self):
        """Handle archived/inactive users appropriately"""
        person = self.resolver.find_person("archived.user@company.com")
        
        assert person is not None
        assert person['status'] == "archived"
        
        # Test with include_archived flag
        person_excluded = self.resolver.find_person(
            "archived.user@company.com", 
            include_archived=False
        )
        assert person_excluded is None
        
        person_included = self.resolver.find_person(
            "archived.user@company.com",
            include_archived=True  
        )
        assert person_included is not None
    
    def test_fuzzy_name_matching(self):
        """Test fuzzy matching for name variations"""
        # Test partial matches
        person = self.resolver.find_person("John")
        # Should find John Doe (first match)
        assert person is not None
        assert "john" in person['name'].lower()
        
        # Test with multiple potential matches
        matches = self.resolver.find_all_matching("J")  
        assert len(matches) >= 2  # Should find John and Jane
    
    def test_employee_data_loading(self):
        """Test loading employee data from collector"""
        # Test with empty data (graceful fallback)
        resolver_empty = PersonResolver(employee_data={"employees": []})
        person = resolver_empty.find_person("anyone@company.com")
        assert person is None
        
        # Test with malformed data
        resolver_malformed = PersonResolver(employee_data={"invalid": "data"})
        person = resolver_malformed.find_person("anyone@company.com")
        assert person is None
    
    def test_performance_with_large_dataset(self):
        """Test performance with larger employee dataset"""
        import time
        
        # Create large mock dataset
        large_dataset = {"employees": []}
        for i in range(1000):
            large_dataset["employees"].append({
                "email": f"user{i}@company.com",
                "slack_id": f"U{i:07d}",
                "calendar_id": f"user{i}@company.com", 
                "name": f"User {i}",
                "display_name": f"User{i}",
                "real_name": f"User {i}",
                "status": "active"
            })
        
        resolver = PersonResolver(employee_data=large_dataset)
        
        # Test lookup performance
        start = time.time()
        person = resolver.find_person("user500@company.com")
        end = time.time()
        
        assert person is not None
        assert (end - start) < 0.1  # Should be fast even with 1000 employees


class TestPersonQueryEngine:
    """Test person-based data retrieval and aggregation from database"""
    
    def setup_method(self):
        """Setup test database with person-related data"""
        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.temp_db.close()
        self.db_path = self.temp_db.name
        
        # Initialize test database with person activity data
        self._setup_test_database()
        
        # Create mock employee data
        self.mock_employee_data = {
            "employees": [
                {
                    "email": "john.doe@company.com",
                    "slack_id": "U12345ABC", 
                    "calendar_id": "john.doe@company.com",
                    "name": "John Doe"
                }
            ]
        }
        
        # Create PersonQueryEngine instance
        self.engine = PersonQueryEngine(
            db_path=self.db_path,
            employee_data=self.mock_employee_data
        )
    
    def teardown_method(self):
        """Clean up after each test method"""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
    
    def _setup_test_database(self):
        """Create test database with person activity data"""
        conn = sqlite3.connect(self.db_path)
        
        # Create messages table structure
        conn.execute("""
            CREATE TABLE messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                source TEXT NOT NULL,
                date TEXT NOT NULL,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create calendar events table
        conn.execute("""
            CREATE TABLE calendar_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                attendees TEXT NOT NULL,  -- JSON array
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                organizer TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create drive activity table
        conn.execute("""
            CREATE TABLE drive_activity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_name TEXT NOT NULL,
                action TEXT NOT NULL,
                user_email TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Insert test messages with person attribution
        test_messages = [
            ("Hey team, let's schedule a meeting", "slack", 
             json.dumps({"author": "U12345ABC", "author_email": "john.doe@company.com"}),
             datetime.now().isoformat()),
            ("I'll send the report by EOD", "slack",
             json.dumps({"author": "U12345ABC", "author_email": "john.doe@company.com"}), 
             (datetime.now() - timedelta(hours=2)).isoformat()),
            ("Thanks for the update", "slack",
             json.dumps({"author": "U67890DEF", "author_email": "jane.smith@company.com"}),
             (datetime.now() - timedelta(days=1)).isoformat()),
        ]
        
        for content, source, metadata, date_str in test_messages:
            conn.execute(
                "INSERT INTO messages (content, source, metadata, date) VALUES (?, ?, ?, ?)",
                (content, source, metadata, date_str)
            )
        
        # Insert test calendar events
        test_events = [
            ("Team Standup", '["john.doe@company.com", "jane.smith@company.com"]',
             datetime.now().isoformat(), (datetime.now() + timedelta(hours=1)).isoformat(),
             "john.doe@company.com"),
            ("Project Review", '["john.doe@company.com"]',
             (datetime.now() - timedelta(days=1)).isoformat(), 
             (datetime.now() - timedelta(days=1, hours=-1)).isoformat(),
             "john.doe@company.com"),
        ]
        
        for title, attendees, start, end, organizer in test_events:
            conn.execute(
                "INSERT INTO calendar_events (title, attendees, start_time, end_time, organizer) VALUES (?, ?, ?, ?, ?)",
                (title, attendees, start, end, organizer)
            )
        
        # Insert test drive activity
        test_drive = [
            ("project_plan.docx", "modified", "john.doe@company.com", datetime.now().isoformat()),
            ("budget.xlsx", "created", "john.doe@company.com", 
             (datetime.now() - timedelta(hours=3)).isoformat()),
        ]
        
        for filename, action, user_email, timestamp in test_drive:
            conn.execute(
                "INSERT INTO drive_activity (file_name, action, user_email, timestamp) VALUES (?, ?, ?, ?)",
                (filename, action, user_email, timestamp)
            )
        
        conn.commit()
        conn.close()
    
    def test_person_activity_aggregation(self):
        """Aggregate activity metrics per person over time"""
        stats = self.engine.get_person_activity("john.doe@company.com", "past 7 days")
        
        # Verify required fields present
        required_fields = ['message_count', 'meetings_attended', 'files_modified', 'channels_active']
        assert all(field in stats for field in required_fields)
        assert all(isinstance(stats[field], int) for field in required_fields)
        
        # Verify reasonable values based on test data
        assert stats['message_count'] >= 2  # John sent 2 messages
        assert stats['meetings_attended'] >= 1  # John attended meetings
        assert stats['files_modified'] >= 1  # John modified files
    
    def test_person_message_history(self):
        """Retrieve paginated message history for specific person"""
        messages = self.engine.get_messages_by_person("john.doe@company.com", limit=50)
        
        assert isinstance(messages, list)
        assert len(messages) >= 2  # John sent at least 2 messages
        assert len(messages) <= 50  # Respects limit
        
        # Verify message structure
        for msg in messages:
            assert 'content' in msg
            assert 'timestamp' in msg or 'date' in msg
            assert 'source' in msg
            
            # Verify author attribution
            if 'metadata' in msg and msg['metadata']:
                metadata = json.loads(msg['metadata']) if isinstance(msg['metadata'], str) else msg['metadata']
                assert metadata.get('author_email') == "john.doe@company.com"
    
    def test_person_meeting_participation(self):
        """Track meeting participation patterns"""
        meetings = self.engine.get_meetings_for_person("john.doe@company.com", "past 30 days")
        
        assert isinstance(meetings, list)
        assert len(meetings) >= 1  # John attended meetings
        
        # Verify meeting structure
        for meeting in meetings:
            assert 'title' in meeting
            assert 'attendees' in meeting
            assert 'start_time' in meeting
            
            # Verify John is in attendees list
            attendees = json.loads(meeting['attendees']) if isinstance(meeting['attendees'], str) else meeting['attendees']
            assert "john.doe@company.com" in attendees
    
    def test_cross_source_activity_correlation(self):
        """Correlate activity across Slack, Calendar, and Drive"""
        correlation = self.engine.get_cross_source_activity("john.doe@company.com", "today")
        
        assert 'slack_activity' in correlation
        assert 'calendar_activity' in correlation
        assert 'drive_activity' in correlation
        assert 'total_interactions' in correlation
        
        assert isinstance(correlation['total_interactions'], int)
        assert correlation['total_interactions'] >= 0
        
        # Verify individual source data structure
        assert isinstance(correlation['slack_activity'], dict)
        assert isinstance(correlation['calendar_activity'], dict)
        assert isinstance(correlation['drive_activity'], dict)
    
    def test_nonexistent_person_queries(self):
        """Handle queries for nonexistent persons gracefully"""
        # Test with invalid email
        stats = self.engine.get_person_activity("nonexistent@company.com", "past 7 days")
        assert isinstance(stats, dict)
        assert all(stats[field] == 0 for field in stats if field.endswith('_count'))
        
        # Test message history for nonexistent person  
        messages = self.engine.get_messages_by_person("nonexistent@company.com", limit=50)
        assert messages == []
        
        # Test meetings for nonexistent person
        meetings = self.engine.get_meetings_for_person("nonexistent@company.com", "past 30 days")
        assert meetings == []
    
    def test_time_range_filtering_accuracy(self):
        """Verify accurate time range filtering in person queries"""
        # Test with very narrow time range (last hour)
        recent_activity = self.engine.get_person_activity("john.doe@company.com", "past 1 hour")
        
        # Test with broader time range (last week)  
        week_activity = self.engine.get_person_activity("john.doe@company.com", "past 7 days")
        
        # Week activity should be >= recent activity
        assert week_activity['message_count'] >= recent_activity['message_count']
        assert week_activity['files_modified'] >= recent_activity['files_modified']
    
    def test_query_performance_requirements(self):
        """Verify person queries meet performance requirements (<2 seconds)"""
        import time
        
        start = time.time()
        stats = self.engine.get_person_activity("john.doe@company.com", "past 30 days")
        end = time.time()
        
        assert (end - start) < 2.0  # Must complete within 2 seconds
        assert isinstance(stats, dict)
    
    def test_activity_aggregation_edge_cases(self):
        """Test edge cases in activity aggregation"""
        # Test with person who has no activity
        stats = self.engine.get_person_activity("inactive@company.com", "past 7 days")
        assert stats['message_count'] == 0
        assert stats['meetings_attended'] == 0
        assert stats['files_modified'] == 0
        
        # Test with invalid time expressions
        with pytest.raises(Exception):  # Should raise TimeParsingError or similar
            self.engine.get_person_activity("john.doe@company.com", "invalid time")
    
    def test_database_error_handling(self):
        """Test handling of database connection errors"""
        # Create engine with invalid database path
        engine = PersonQueryEngine(
            db_path="/nonexistent/path.db",
            employee_data=self.mock_employee_data
        )
        
        # Should handle database errors gracefully
        with pytest.raises(Exception):  # Database connection error expected
            engine.get_person_activity("john.doe@company.com", "today")
    
    def test_result_format_consistency(self):
        """Ensure all person query results have consistent format"""
        # Test activity stats format
        stats = self.engine.get_person_activity("john.doe@company.com", "past 7 days")
        expected_fields = ['message_count', 'meetings_attended', 'files_modified', 'channels_active']
        
        for field in expected_fields:
            assert field in stats
            assert isinstance(stats[field], int)
            assert stats[field] >= 0
        
        # Test message format
        messages = self.engine.get_messages_by_person("john.doe@company.com", limit=10)
        for msg in messages:
            assert 'content' in msg
            assert 'source' in msg  
            assert 'date' in msg or 'timestamp' in msg


class TestPersonQueryIntegration:
    """Test integration with employee collector and existing systems"""
    
    def setup_method(self):
        """Setup integration test environment"""
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.temp_db.close()
        self.db_path = self.temp_db.name
    
    def teardown_method(self):
        """Clean up after each test method"""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
    
    @patch('src.collectors.employee_collector.EmployeeCollector')
    def test_employee_collector_integration(self, mock_collector_class):
        """Test integration with EmployeeCollector"""
        # Mock collector instance and response
        mock_collector = Mock()
        mock_collector.collect.return_value = {
            "employees": [
                {
                    "email": "test@company.com",
                    "slack_id": "U12345", 
                    "name": "Test User"
                }
            ]
        }
        mock_collector_class.return_value = mock_collector
        
        # Test PersonResolver loading from collector
        resolver = PersonResolver()  # Should auto-load from collector
        resolver.load_from_collector()
        
        # Verify data loaded correctly
        person = resolver.find_person("test@company.com")
        assert person is not None
        assert person['slack_id'] == "U12345"
    
    def test_graceful_fallback_with_missing_employee_data(self):
        """Test graceful operation when employee data unavailable"""
        # Test with no employee data
        resolver = PersonResolver(employee_data=None)
        
        # Should not crash, but return None for all lookups
        person = resolver.find_person("anyone@company.com")
        assert person is None
        
        # Test PersonQueryEngine with missing employee data
        engine = PersonQueryEngine(db_path=":memory:", employee_data=None)
        
        # Should still work but with limited person resolution
        stats = engine.get_person_activity("test@company.com", "today")
        assert isinstance(stats, dict)  # Should return empty/default stats
    
    def test_real_vs_mock_data_compatibility(self):
        """Ensure compatibility between real employee collector data and mock data"""
        # Test that PersonResolver works with both mock and real data formats
        mock_data = {
            "employees": [{"email": "mock@test.com", "slack_id": "U123", "name": "Mock User"}]
        }
        
        # Should work with mock data format
        resolver_mock = PersonResolver(employee_data=mock_data)
        person = resolver_mock.find_person("mock@test.com")
        assert person is not None
        
        # Should also work with employee collector format (when available)
        # This test ensures backward compatibility