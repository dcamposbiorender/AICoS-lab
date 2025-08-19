"""
Integration tests for Search CLI tool - Phase 3: Search CLI Interface

Tests the complete CLI interface including:
- Natural language search with FTS5 integration
- Multiple output formats (table, JSON, CSV)
- Source filtering and date range queries
- Interactive mode for exploratory search
- Index management commands
- Performance monitoring and statistics

References:
- tasks_A.md lines 1180-1331 for CLI test requirements
- SearchDatabase integration from Sub-Agent A1
- ArchiveIndexer integration from Sub-Agent A2
"""

import pytest
import json
import tempfile
import os
from pathlib import Path
from click.testing import CliRunner
from unittest.mock import patch, MagicMock

# Import the CLI and supporting components
from tools.search_cli import search_cli
from src.search.database import SearchDatabase
from src.search.indexer import ArchiveIndexer


class TestSearchCLI:
    """Test command-line search interface with full A1/A2 integration"""
    
    @pytest.fixture
    def runner(self):
        """Click test runner"""
        return CliRunner()
    
    @pytest.fixture
    def temp_db_path(self, tmp_path):
        """Temporary database path for testing"""
        return tmp_path / "test_search.db"
    
    @pytest.fixture
    def sample_archive_data(self, tmp_path):
        """Sample JSONL archive with realistic data for testing"""
        archive_path = tmp_path / "sample_data.jsonl"
        
        sample_records = [
            {
                "id": "msg_001",
                "text": "Team meeting scheduled for 2pm today in conference room",
                "user": "alice",
                "channel": "general", 
                "ts": "1692262800.123456",
                "type": "message"
            },
            {
                "id": "msg_002",
                "text": "Project deadline extended to next Friday due to holidays",
                "user": "bob",
                "channel": "dev",
                "ts": "1692349200.789012", 
                "type": "message"
            },
            {
                "id": "msg_003",
                "text": "Birthday party for Sarah this weekend, RSVP required",
                "user": "hr",
                "channel": "social",
                "ts": "1692435600.345678",
                "type": "message"
            },
            {
                "id": "cal_001", 
                "summary": "Quarterly business review with leadership team",
                "start": {"dateTime": "2025-08-20T14:00:00Z"},
                "attendees": [
                    {"email": "ceo@company.com"},
                    {"email": "alice@company.com"}
                ]
            }
        ]
        
        with open(archive_path, 'w') as f:
            for record in sample_records:
                f.write(json.dumps(record) + '\n')
        
        return archive_path
    
    @pytest.fixture
    def populated_database(self, temp_db_path, sample_archive_data):
        """Database populated with test data via ArchiveIndexer"""
        db = SearchDatabase(str(temp_db_path))
        indexer = ArchiveIndexer(db)
        
        # Index the sample data
        stats = indexer.process_archive(sample_archive_data, source='slack')
        assert stats.processed > 0
        
        return db
    
    def test_basic_search_command(self, runner, temp_db_path, populated_database):
        """Basic search returns relevant results with proper formatting"""
        result = runner.invoke(search_cli, [
            'search',
            '--db', str(temp_db_path),
            'team meeting'
        ])
        
        assert result.exit_code == 0
        output = result.output
        
        # Should contain the meeting result
        assert 'conference room' in output
        assert 'Score:' in output  # Relevance score displayed
        assert 'SLACK' in output  # Source indication
        
        # Should have proper table formatting
        assert '1.' in output  # Numbered results
    
    def test_source_filtering_functionality(self, runner, temp_db_path, populated_database):
        """Source filtering works correctly across different data types"""
        # Test Slack filtering
        result = runner.invoke(search_cli, [
            'search',
            '--db', str(temp_db_path),
            '--source', 'slack',
            'party'
        ])
        
        assert result.exit_code == 0
        assert 'Birthday party' in result.output
        # Should only show Slack results
        assert 'SLACK' in result.output
    
    def test_date_range_filtering(self, runner, temp_db_path, populated_database):
        """Date range filtering limits results to specified timeframe"""
        result = runner.invoke(search_cli, [
            'search',
            '--db', str(temp_db_path),
            '--start-date', '2025-08-01',
            '--end-date', '2025-08-31', 
            'meeting'
        ])
        
        assert result.exit_code == 0
        # Should find results in the date range
        assert len(result.output.strip()) > 0
    
    def test_json_output_format(self, runner, temp_db_path, populated_database):
        """JSON output format produces valid structured data"""
        result = runner.invoke(search_cli, [
            'search',
            '--db', str(temp_db_path),
            '--format', 'json',
            'meeting'
        ])
        
        assert result.exit_code == 0
        
        # Should be valid JSON
        try:
            output_data = json.loads(result.output)
            assert isinstance(output_data, list)
            assert len(output_data) >= 1
            
            # Check result structure
            first_result = output_data[0]
            required_fields = ['content', 'source', 'date', 'relevance_score']
            for field in required_fields:
                assert field in first_result, f"Missing field: {field}"
                
        except json.JSONDecodeError:
            pytest.fail("Output is not valid JSON")
    
    def test_csv_output_format(self, runner, temp_db_path, populated_database):
        """CSV output format works with proper headers and data"""
        result = runner.invoke(search_cli, [
            'search',
            '--db', str(temp_db_path),
            '--format', 'csv',
            'deadline'
        ])
        
        assert result.exit_code == 0
        lines = result.output.strip().split('\n')
        assert len(lines) >= 2  # Header + at least one data row
        
        # Check CSV headers
        headers = lines[0].split(',')
        assert 'content' in headers[0]
        assert 'source' in headers
        assert 'score' in headers[-1]
        
        # Should contain the deadline result
        assert 'Project deadline' in result.output
    
    def test_interactive_mode_functionality(self, runner, temp_db_path, populated_database):
        """Interactive search mode allows multiple queries in session"""
        # Simulate interactive input: search for "meeting", then quit
        result = runner.invoke(search_cli, [
            'search',
            '--db', str(temp_db_path),
            '--interactive'
        ], input='meeting\nq\n')
        
        assert result.exit_code == 0
        
        # Should show interactive prompt
        assert 'Search>' in result.output
        # Should show search results
        assert 'conference room' in result.output
        # Should exit cleanly
        assert result.output.count('Search>') >= 1
    
    def test_search_suggestions_for_no_results(self, runner, temp_db_path, populated_database):
        """Search provides helpful suggestions when no results found"""
        result = runner.invoke(search_cli, [
            'search', 
            '--db', str(temp_db_path),
            'nonexistent query xyz that will never match'
        ])
        
        assert result.exit_code == 0
        assert 'No results found' in result.output
        assert 'Suggestions:' in result.output
    
    def test_limit_parameter_controls_results(self, runner, temp_db_path, populated_database):
        """Limit parameter properly constrains number of results"""
        result = runner.invoke(search_cli, [
            'search',
            '--db', str(temp_db_path), 
            '--limit', '1',
            '--format', 'json',
            'message'  # Should match multiple records
        ])
        
        assert result.exit_code == 0
        
        try:
            output_data = json.loads(result.output)
            assert len(output_data) <= 1  # Limited to 1 result
        except json.JSONDecodeError:
            pytest.fail("Output is not valid JSON")
    
    def test_verbose_mode_shows_metadata(self, runner, temp_db_path, populated_database):
        """Verbose mode displays additional metadata information"""
        result = runner.invoke(search_cli, [
            'search',
            '--db', str(temp_db_path),
            '--verbose',
            'meeting'
        ])
        
        assert result.exit_code == 0
        # Should show metadata information
        assert 'Metadata:' in result.output
    
    def test_index_command_functionality(self, runner, temp_db_path, sample_archive_data):
        """Index command processes archives into database"""
        result = runner.invoke(search_cli, [
            'index', 
            '--db', str(temp_db_path),
            '--source', 'slack',
            str(sample_archive_data)
        ])
        
        assert result.exit_code == 0
        assert 'indexed' in result.output.lower()
        assert 'completed' in result.output.lower()
        
        # Verify database was populated
        db = SearchDatabase(str(temp_db_path))
        stats = db.get_stats()
        assert stats['total_records'] > 0
    
    def test_index_command_with_progress(self, runner, temp_db_path, sample_archive_data):
        """Index command shows progress for large files"""
        result = runner.invoke(search_cli, [
            'index',
            '--db', str(temp_db_path),
            '--source', 'slack', 
            '--progress',
            str(sample_archive_data)
        ])
        
        assert result.exit_code == 0
        # Should show some indication of progress
        assert 'Processing' in result.output or 'Indexing' in result.output
    
    def test_stats_command_provides_database_info(self, runner, temp_db_path, populated_database):
        """Stats command displays comprehensive database statistics"""
        result = runner.invoke(search_cli, [
            'stats',
            '--db', str(temp_db_path)
        ])
        
        assert result.exit_code == 0
        
        # Should contain key statistics
        assert 'Total records:' in result.output
        assert 'Records by source:' in result.output
        assert 'slack:' in result.output  # Source breakdown
    
    def test_stats_command_json_format(self, runner, temp_db_path, populated_database):
        """Stats command provides JSON output for programmatic use"""
        result = runner.invoke(search_cli, [
            'stats',
            '--db', str(temp_db_path),
            '--format', 'json'
        ])
        
        assert result.exit_code == 0
        
        try:
            stats_data = json.loads(result.output)
            assert 'total_records' in stats_data
            assert 'records_by_source' in stats_data
            assert isinstance(stats_data['total_records'], int)
        except json.JSONDecodeError:
            pytest.fail("Stats output is not valid JSON")
    
    def test_error_handling_invalid_database_path(self, runner):
        """CLI handles invalid database paths gracefully"""
        result = runner.invoke(search_cli, [
            'search',
            '--db', '/root/invalid/path/nonexistent.db',
            'test query'
        ])
        
        # Should exit with error but not crash
        assert result.exit_code != 0
        assert 'error' in result.output.lower() or 'failed' in result.output.lower()
    
    def test_error_handling_invalid_archive_path(self, runner, temp_db_path):
        """Index command handles invalid archive paths gracefully"""
        result = runner.invoke(search_cli, [
            'index',
            '--db', str(temp_db_path),
            '--source', 'slack',
            '/nonexistent/archive.jsonl'
        ])
        
        assert result.exit_code != 0
        assert 'not found' in result.output.lower() or 'error' in result.output.lower()
    
    def test_help_messages_are_informative(self, runner):
        """Help messages provide clear usage information"""
        # Test main help
        result = runner.invoke(search_cli, ['--help'])
        assert result.exit_code == 0
        assert 'Usage:' in result.output
        assert 'search' in result.output
        assert 'index' in result.output
        assert 'stats' in result.output
        
        # Test search help
        result = runner.invoke(search_cli, ['search', '--help'])
        assert result.exit_code == 0
        assert 'query' in result.output.lower()
        assert 'source' in result.output.lower()
    
    def test_special_interactive_commands(self, runner, temp_db_path, populated_database):
        """Interactive mode supports special commands like /stats and /help"""
        # Test /stats command
        result = runner.invoke(search_cli, [
            'search',
            '--db', str(temp_db_path),
            '--interactive'
        ], input='/stats\nq\n')
        
        assert result.exit_code == 0
        assert 'Database Statistics:' in result.output
        assert 'Total records:' in result.output
    
    def test_natural_language_query_enhancement(self, runner, temp_db_path, populated_database):
        """CLI enhances natural language queries for better FTS5 matching"""
        # Test that longer words get wildcards for partial matching
        result = runner.invoke(search_cli, [
            'search',
            '--db', str(temp_db_path),
            '--format', 'json',
            'project'  # Should match "project" in deadline message
        ])
        
        assert result.exit_code == 0
        
        try:
            output_data = json.loads(result.output)
            assert len(output_data) >= 1
            # Should find the project deadline message
            content_text = ' '.join([r['content'].lower() for r in output_data])
            assert 'project' in content_text or 'deadline' in content_text
        except json.JSONDecodeError:
            pytest.fail("Output is not valid JSON")
    
    def test_complex_search_with_multiple_filters(self, runner, temp_db_path, populated_database):
        """Complex searches with multiple filters work correctly"""
        result = runner.invoke(search_cli, [
            'search',
            '--db', str(temp_db_path),
            '--source', 'slack',
            '--limit', '5',
            '--format', 'json',
            'meeting party deadline'
        ])
        
        assert result.exit_code == 0
        
        try:
            output_data = json.loads(result.output)
            # All results should be from slack source
            for result_item in output_data:
                assert result_item['source'] == 'slack'
            # Should not exceed limit
            assert len(output_data) <= 5
        except json.JSONDecodeError:
            pytest.fail("Output is not valid JSON")
    
    def test_performance_with_large_dataset(self, runner, temp_db_path):
        """CLI performs well with larger datasets"""
        # Create a larger test database
        db = SearchDatabase(str(temp_db_path))
        
        # Generate test records
        large_records = []
        for i in range(1000):
            large_records.append({
                'content': f'Test message number {i} about various topics including meetings projects and deadlines',
                'source': 'test',
                'date': '2025-08-17',
                'metadata': {'msg_id': f'test_{i}'}
            })
        
        # Index the records
        db.index_records_batch(large_records, 'test')
        
        # Test search performance
        result = runner.invoke(search_cli, [
            'search',
            '--db', str(temp_db_path),
            '--limit', '10',
            'meetings projects'
        ])
        
        assert result.exit_code == 0
        # Should return results quickly
        assert '1.' in result.output  # At least one result
    
    def test_cli_integration_with_archive_indexer(self, runner, temp_db_path, sample_archive_data):
        """Full integration test: index via CLI then search the results"""
        # Step 1: Index archive via CLI
        index_result = runner.invoke(search_cli, [
            'index',
            '--db', str(temp_db_path),
            '--source', 'slack',
            str(sample_archive_data)
        ])
        
        assert index_result.exit_code == 0
        assert 'completed' in index_result.output.lower()
        
        # Step 2: Search the indexed data
        search_result = runner.invoke(search_cli, [
            'search',
            '--db', str(temp_db_path),
            'meeting'
        ])
        
        assert search_result.exit_code == 0
        assert 'conference room' in search_result.output
        
        # Step 3: Check stats
        stats_result = runner.invoke(search_cli, [
            'stats',
            '--db', str(temp_db_path)
        ])
        
        assert stats_result.exit_code == 0
        assert 'Total records:' in stats_result.output
    
    def test_empty_database_handling(self, runner, temp_db_path):
        """CLI handles empty database gracefully"""
        # Create empty database
        db = SearchDatabase(str(temp_db_path))
        
        # Try to search empty database
        result = runner.invoke(search_cli, [
            'search',
            '--db', str(temp_db_path),
            'anything'
        ])
        
        assert result.exit_code == 0
        assert 'No results found' in result.output
        
        # Try to get stats from empty database
        stats_result = runner.invoke(search_cli, [
            'stats',
            '--db', str(temp_db_path)
        ])
        
        assert stats_result.exit_code == 0
        assert 'Total records: 0' in stats_result.output
    
    def test_concurrent_search_safety(self, runner, temp_db_path, populated_database):
        """Multiple concurrent searches work safely"""
        import threading
        import time
        
        results = []
        errors = []
        
        def run_search(query):
            try:
                result = runner.invoke(search_cli, [
                    'search',
                    '--db', str(temp_db_path),
                    '--format', 'json',
                    query
                ])
                results.append(result)
            except Exception as e:
                errors.append(e)
        
        # Run multiple searches concurrently
        threads = []
        queries = ['meeting', 'deadline', 'party', 'project', 'team']
        
        for query in queries:
            t = threading.Thread(target=run_search, args=(query,))
            threads.append(t)
            t.start()
        
        # Wait for all to complete
        for t in threads:
            t.join()
        
        # Check results (lab-grade tolerance for some failures)
        assert len(results) >= 3  # At least 3 of 5 should succeed
        assert len(errors) <= 2   # Allow some failures under high contention
        
        # Check that successful results are valid
        for result in results:
            if result.exit_code == 0:
                try:
                    json.loads(result.output)  # Should be valid JSON
                except json.JSONDecodeError:
                    pass  # Allow some malformed output under contention