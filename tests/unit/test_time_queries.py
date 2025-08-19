"""
Comprehensive test suite for time query functionality
Tests natural language time parsing, timezone handling, and database integration

References:
- src/queries/time_utils.py - Time parsing utilities to be implemented
- src/intelligence/query_engine.py - Existing QueryEngine to extend
- src/search/database.py - SQLite FTS5 search infrastructure
"""

import pytest
import pytz
from datetime import datetime, date, timedelta, timezone
from unittest.mock import Mock, patch, MagicMock
import sqlite3
import tempfile
import os

# Import modules to be implemented
from src.queries.time_utils import parse_time_expression, normalize_timezone, TimeQueryEngine
from src.intelligence.query_engine import QueryEngine


class TestTimeExpressionParsing:
    """Test natural language time expression parsing with timezone awareness"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.today = date.today()
        self.now = datetime.now(timezone.utc)
        
    def test_basic_relative_dates(self):
        """Parse basic relative date expressions accurately"""
        # Today
        start, end = parse_time_expression("today")
        assert start.date() == self.today
        assert end.date() == self.today
        assert start.time() == datetime.min.time()
        assert end.time() == datetime.max.time()
        
        # Yesterday  
        start, end = parse_time_expression("yesterday")
        expected_date = self.today - timedelta(days=1)
        assert start.date() == expected_date
        assert end.date() == expected_date
        
        # Tomorrow
        start, end = parse_time_expression("tomorrow")
        expected_date = self.today + timedelta(days=1)
        assert start.date() == expected_date
        assert end.date() == expected_date
    
    def test_relative_week_expressions(self):
        """Parse week-based relative expressions"""
        # This week
        start, end = parse_time_expression("this week")
        assert start.weekday() == 0  # Monday
        assert end.weekday() == 6    # Sunday
        
        # Last week
        start, end = parse_time_expression("last week")
        this_week_start = self.today - timedelta(days=self.today.weekday())
        expected_start = this_week_start - timedelta(weeks=1)
        assert start.date() == expected_start
        
        # Past 7 days
        start, end = parse_time_expression("past 7 days")
        assert (end.date() - start.date()).days == 7
        assert end.date() == self.today
    
    def test_numeric_time_ranges(self):
        """Parse numeric time range expressions"""
        # Past N days
        start, end = parse_time_expression("past 30 days")
        assert (end.date() - start.date()).days == 30
        assert end.date() == self.today
        
        start, end = parse_time_expression("past 3 days")
        assert (end.date() - start.date()).days == 3
        
        # Past N weeks
        start, end = parse_time_expression("past 2 weeks")
        assert (end.date() - start.date()).days == 14
        
        # Past N months (approximate)
        start, end = parse_time_expression("past 3 months")
        assert (end.date() - start.date()).days >= 85  # ~3 months
        assert (end.date() - start.date()).days <= 95  # Account for month variations
    
    def test_month_year_expressions(self):
        """Parse month and year references"""
        # This month
        start, end = parse_time_expression("this month")
        assert start.month == self.today.month
        assert start.year == self.today.year
        assert start.day == 1
        assert end.month == self.today.month
        assert end.year == self.today.year
        
        # Last month
        start, end = parse_time_expression("last month")
        if self.today.month == 1:
            assert start.month == 12
            assert start.year == self.today.year - 1
        else:
            assert start.month == self.today.month - 1
            assert start.year == self.today.year
    
    def test_timezone_handling(self):
        """Test timezone-aware parsing and conversion"""
        # UTC timezone
        start, end = parse_time_expression("yesterday UTC")
        assert start.tzinfo is not None
        assert start.tzinfo.zone == 'UTC'
        
        # PST timezone
        start, end = parse_time_expression("yesterday PST")
        assert start.tzinfo is not None
        assert 'Pacific' in str(start.tzinfo)
        
        # EST timezone
        start, end = parse_time_expression("yesterday EST")
        assert start.tzinfo is not None
        assert 'Eastern' in str(start.tzinfo)
        
        # Different timezones should produce different times
        utc_time = parse_time_expression("yesterday UTC")[0]
        pst_time = parse_time_expression("yesterday PST")[0]
        assert utc_time.utctimetuple() != pst_time.utctimetuple()
    
    def test_timezone_normalization(self):
        """Test timezone normalization utility function"""
        # Test UTC normalization
        dt_naive = datetime(2025, 8, 19, 12, 0, 0)
        dt_utc = normalize_timezone(dt_naive, 'UTC')
        assert dt_utc.tzinfo.zone == 'UTC'
        
        # Test PST normalization
        dt_pst = normalize_timezone(dt_naive, 'US/Pacific')
        assert dt_pst.tzinfo is not None
        assert 'Pacific' in str(dt_pst.tzinfo)
        
        # Test with already timezone-aware datetime
        dt_aware = datetime.now(timezone.utc)
        dt_normalized = normalize_timezone(dt_aware, 'US/Eastern')
        assert dt_normalized.tzinfo is not None
    
    def test_invalid_expressions(self):
        """Test handling of invalid time expressions"""
        # Complete gibberish
        with pytest.raises(ValueError, match="Invalid time expression"):
            parse_time_expression("gibberish nonsense")
        
        # Empty string
        result = parse_time_expression("")
        assert result is None
        
        # None input
        result = parse_time_expression(None)
        assert result is None
        
        # Malformed expressions
        with pytest.raises(ValueError):
            parse_time_expression("past -5 days")
        
        with pytest.raises(ValueError):
            parse_time_expression("past 0 days")
    
    def test_edge_cases(self):
        """Test edge cases in time expression parsing"""
        # Leap year handling
        with patch('src.queries.time_utils.date') as mock_date:
            mock_date.today.return_value = date(2024, 2, 29)  # Leap year
            start, end = parse_time_expression("yesterday")
            assert start.date() == date(2024, 2, 28)
        
        # Year boundary crossing
        with patch('src.queries.time_utils.date') as mock_date:
            mock_date.today.return_value = date(2025, 1, 1)
            start, end = parse_time_expression("last month")
            assert start.month == 12
            assert start.year == 2024


class TestTimeQueryEngine:
    """Test time-based database query functionality"""
    
    def setup_method(self):
        """Setup test database for each test method"""
        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.temp_db.close()
        self.db_path = self.temp_db.name
        
        # Initialize test database with sample data
        self._setup_test_database()
        
        # Create TimeQueryEngine instance
        self.engine = TimeQueryEngine(db_path=self.db_path)
    
    def teardown_method(self):
        """Clean up after each test method"""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
    
    def _setup_test_database(self):
        """Create test database with sample time-based data"""
        conn = sqlite3.connect(self.db_path)
        
        # Create messages table structure matching search database
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
        
        # Create FTS5 table
        conn.execute("""
            CREATE VIRTUAL TABLE messages_fts USING fts5(
                content,
                content=messages,
                content_rowid=id,
                tokenize='porter unicode61'
            )
        """)
        
        # Insert test data spanning multiple days
        test_data = [
            ("Test message from today", "slack", datetime.now().isoformat()),
            ("Test message from yesterday", "slack", (datetime.now() - timedelta(days=1)).isoformat()),
            ("Meeting notes last week", "calendar", (datetime.now() - timedelta(days=7)).isoformat()),
            ("Old message from last month", "slack", (datetime.now() - timedelta(days=30)).isoformat()),
            ("Recent meeting discussion", "calendar", (datetime.now() - timedelta(hours=2)).isoformat()),
        ]
        
        for content, source, date_str in test_data:
            conn.execute(
                "INSERT INTO messages (content, source, date) VALUES (?, ?, ?)",
                (content, source, date_str)
            )
        
        conn.commit()
        conn.close()
    
    def test_query_by_time_basic(self):
        """Test basic time-filtered queries"""
        # Query for today's messages
        results = self.engine.query_by_time("messages from today")
        assert isinstance(results, list)
        assert len(results) >= 1
        assert all('timestamp' in r or 'date' in r for r in results)
        
        # Query for yesterday's messages
        results = self.engine.query_by_time("messages from yesterday")
        assert isinstance(results, list)
        assert len(results) >= 0  # May not have yesterday's data
    
    def test_query_date_range(self):
        """Test date range queries with specific start and end dates"""
        start_date = date.today() - timedelta(days=7)
        end_date = date.today()
        
        results = self.engine.query_date_range(
            start=start_date,
            end=end_date,
            content_filter="meeting"
        )
        
        assert isinstance(results, list)
        # Should find messages containing "meeting" within the date range
        for result in results:
            assert 'meeting' in result.get('content', '').lower()
    
    def test_query_with_source_filter(self):
        """Test time queries with source filtering"""
        results = self.engine.query_by_time_and_source(
            time_expression="past 7 days",
            source="slack"
        )
        
        assert isinstance(results, list)
        for result in results:
            assert result.get('source') == 'slack'
    
    def test_performance_requirements(self):
        """Test query performance meets Phase 1 requirements (<2 seconds)"""
        import time
        
        start_time = time.time()
        results = self.engine.query_by_time("messages from last week")
        end_time = time.time()
        
        # Must complete within 2 seconds
        assert (end_time - start_time) < 2.0
        assert isinstance(results, list)
    
    def test_timezone_query_integration(self):
        """Test timezone handling in database queries"""
        # Query with timezone specification
        results = self.engine.query_by_time("yesterday PST")
        assert isinstance(results, list)
        
        # Results should be timezone-aware
        for result in results:
            if 'timestamp' in result:
                # Parse timestamp and verify timezone handling
                assert result['timestamp'] is not None
    
    def test_empty_results_handling(self):
        """Test handling of queries that return no results"""
        # Query for future date (should return empty)
        results = self.engine.query_by_time("messages from next week")
        assert results == []
        
        # Query for very old date (should return empty)  
        results = self.engine.query_by_time("messages from 2020")
        assert results == []
    
    def test_malformed_query_handling(self):
        """Test handling of malformed queries"""
        # Invalid time expression
        with pytest.raises(ValueError):
            self.engine.query_by_time("messages from gibberish")
        
        # None query
        results = self.engine.query_by_time(None)
        assert results == []
    
    def test_database_connection_error_handling(self):
        """Test handling of database connection errors"""
        # Create engine with invalid database path
        engine = TimeQueryEngine(db_path="/nonexistent/path.db")
        
        with pytest.raises(Exception):
            engine.query_by_time("today")
    
    def test_result_format_consistency(self):
        """Test that all query results have consistent format"""
        results = self.engine.query_by_time("messages from past 7 days")
        
        for result in results:
            # Each result should have required fields
            assert 'content' in result
            assert 'source' in result
            assert 'date' in result or 'timestamp' in result
            
            # Metadata should be properly formatted
            if 'metadata' in result:
                assert isinstance(result['metadata'], (dict, str, type(None)))


class TestQueryEngineExtension:
    """Test integration with existing QueryEngine class"""
    
    def setup_method(self):
        """Setup test environment"""
        self.query_engine = QueryEngine()
    
    def test_existing_functionality_preserved(self):
        """Ensure existing QueryEngine functionality is not broken"""
        # Test existing parse_query method
        parsed = self.query_engine.parse_query("find messages about meeting")
        assert hasattr(parsed, 'original_query')
        assert hasattr(parsed, 'intent')
        assert hasattr(parsed, 'keywords')
    
    def test_new_time_methods_added(self):
        """Test that new deterministic time query methods are available"""
        # These methods should be added to the existing QueryEngine
        assert hasattr(self.query_engine, 'query_by_time_deterministic')
        assert hasattr(self.query_engine, 'query_date_range_deterministic')
    
    def test_deterministic_vs_nlp_methods(self):
        """Test distinction between deterministic and NLP methods"""
        # Deterministic method should work without LLM parsing
        with patch('src.intelligence.query_parser.NLQueryParser') as mock_parser:
            # Even if NLP parser is mocked out, deterministic methods should work
            result = self.query_engine.query_by_time_deterministic(
                time_expression="today",
                db_path=":memory:"
            )
            assert isinstance(result, list)
    
    @pytest.mark.performance
    def test_performance_comparison(self):
        """Compare performance of deterministic vs NLP query methods"""
        import time
        
        # Time deterministic method
        start = time.time()
        self.query_engine.query_by_time_deterministic("today", db_path=":memory:")
        deterministic_time = time.time() - start
        
        # Time NLP method (if available)
        start = time.time()
        self.query_engine.parse_query("messages from today")
        nlp_time = time.time() - start
        
        # Deterministic should be faster
        assert deterministic_time <= nlp_time + 0.1  # Allow small margin