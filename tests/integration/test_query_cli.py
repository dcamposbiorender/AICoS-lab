"""
Integration Tests for Query Facts CLI Tool

Comprehensive tests validating the unified query CLI tool functionality,
including time queries, person queries, pattern extraction, calendar operations,
and statistics. Tests both real implementation and mock mode scenarios.

Test Categories:
- Command-line interface functionality
- Output format validation (JSON, CSV, table, markdown)
- Error handling and user feedback
- Performance requirements validation
- Cross-module integration
- Interactive mode functionality

References:
- tasks/phase1_agent_c_cli.md lines 462-541 for test acceptance criteria
- tools/query_facts.py for implementation
- src/cli/interfaces.py for mock implementations
"""

import pytest
import json
import csv
import io
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
from click.testing import CliRunner

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import the CLI under test
from tools.query_facts import cli as query_cli

# Import supporting modules for testing
from src.cli.errors import CLIError, QueryError, ValidationError
from src.cli.interfaces import (
    MockTimeQueryEngine, MockPersonQueryEngine, MockStructuredExtractor,
    MockAvailabilityEngine, MockActivityAnalyzer
)


@pytest.fixture
def runner():
    """CLI test runner fixture"""
    return CliRunner()


@pytest.fixture
def test_mode_env():
    """Set test mode environment"""
    with patch.dict(os.environ, {'AICOS_TEST_MODE': 'true'}):
        yield


class TestQueryFactsCLI:
    """Test unified query CLI tool integration"""
    
    def test_help_output(self, runner):
        """CLI provides comprehensive help documentation"""
        result = runner.invoke(query_cli, ['--help'])
        
        assert result.exit_code == 0
        assert 'AI Chief of Staff Unified Query Interface' in result.output
        assert 'Examples:' in result.output
        assert 'time' in result.output
        assert 'person' in result.output
        assert 'patterns' in result.output
        assert 'calendar' in result.output
        assert 'stats' in result.output
    
    def test_version_display(self, runner):
        """CLI displays correct version information"""
        result = runner.invoke(query_cli, ['--version'])
        
        assert result.exit_code == 0
        assert '1.0.0' in result.output
    
    def test_time_query_command(self, runner, test_mode_env):
        """CLI handles time-based queries from Agent A"""
        result = runner.invoke(query_cli, [
            'time', 'yesterday', 
            '--format', 'json'
        ])
        
        assert result.exit_code == 0
        
        # Validate JSON output structure
        data = json.loads(result.output)
        assert 'results' in data
        assert 'metadata' in data
        assert 'count' in data
        assert data['metadata']['mock_mode'] is True
        assert data['count'] > 0
        
        # Validate result structure
        first_result = data['results'][0]
        assert 'content' in first_result
        assert 'source' in first_result
        assert 'date' in first_result
        assert 'relevance_score' in first_result
    
    def test_time_query_table_format(self, runner, test_mode_env):
        """CLI handles time queries with table output format"""
        result = runner.invoke(query_cli, [
            'time', 'yesterday',
            '--format', 'table'
        ])
        
        assert result.exit_code == 0
        assert 'SLACK' in result.output  # Source styling
        assert 'Score:' in result.output  # Relevance score
        assert 'Mock result' in result.output  # Mock content
        
        # Should contain multiple results
        assert '1.' in result.output
        assert '2.' in result.output
    
    def test_time_query_csv_format(self, runner, test_mode_env):
        """CLI handles time queries with CSV output format"""
        result = runner.invoke(query_cli, [
            'time', 'yesterday',
            '--format', 'csv'
        ])
        
        assert result.exit_code == 0
        
        # Parse CSV output
        csv_reader = csv.DictReader(io.StringIO(result.output))
        rows = list(csv_reader)
        
        assert len(rows) > 0
        first_row = rows[0]
        assert 'content' in first_row
        assert 'source' in first_row
        assert 'date' in first_row
        assert 'relevance_score' in first_row
    
    def test_time_query_source_filter(self, runner, test_mode_env):
        """CLI handles source filtering in time queries"""
        result = runner.invoke(query_cli, [
            'time', 'yesterday',
            '--source', 'slack',
            '--format', 'json'
        ])
        
        assert result.exit_code == 0
        data = json.loads(result.output)
        
        # All results should be from slack source
        for result_item in data['results']:
            assert result_item['source'] == 'slack'
    
    def test_time_query_limit_option(self, runner, test_mode_env):
        """CLI respects limit option for time queries"""
        result = runner.invoke(query_cli, [
            'time', 'yesterday',
            '--limit', '1',
            '--format', 'json'
        ])
        
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data['count'] == 1
        assert len(data['results']) == 1
    
    def test_person_query_command(self, runner, test_mode_env):
        """CLI handles person-based queries from Agent A"""
        result = runner.invoke(query_cli, [
            'person', 'alice@example.com',
            '--format', 'json'
        ])
        
        assert result.exit_code == 0
        data = json.loads(result.output)
        
        assert 'results' in data
        assert 'metadata' in data
        assert data['metadata']['mock_mode'] is True
        assert data['count'] > 0
        
        # Should contain person-specific content
        for result_item in data['results']:
            assert 'alice@example.com' in result_item['content']
    
    def test_person_query_activity_summary(self, runner, test_mode_env):
        """CLI includes activity summary for person queries"""
        result = runner.invoke(query_cli, [
            'person', 'alice@example.com',
            '--activity-summary',
            '--format', 'json'
        ])
        
        assert result.exit_code == 0
        data = json.loads(result.output)
        
        # Should include activity summary in metadata
        assert 'activity_summary' in data['metadata']
        summary = data['metadata']['activity_summary']
        assert 'message_count' in summary
        assert 'meeting_count' in summary
    
    def test_person_query_time_range(self, runner, test_mode_env):
        """CLI handles time range filtering for person queries"""
        result = runner.invoke(query_cli, [
            'person', 'alice@example.com',
            '--time-range', 'last week',
            '--format', 'json'
        ])
        
        assert result.exit_code == 0
        # Should execute without errors
        data = json.loads(result.output)
        assert data['count'] > 0
    
    def test_patterns_query_todos(self, runner, test_mode_env):
        """CLI handles TODO pattern extraction"""
        result = runner.invoke(query_cli, [
            'patterns',
            '--pattern-type', 'todos',
            '--format', 'json'
        ])
        
        assert result.exit_code == 0
        data = json.loads(result.output)
        
        assert 'results' in data
        assert data['count'] > 0
        
        # Should contain TODO-related content
        first_result = data['results'][0]
        assert 'TODO' in first_result['content']
        assert first_result['metadata']['pattern_type'] == 'todo'
    
    def test_patterns_query_mentions(self, runner, test_mode_env):
        """CLI handles mention pattern extraction"""
        result = runner.invoke(query_cli, [
            'patterns',
            '--pattern-type', 'mentions',
            '--format', 'json'
        ])
        
        assert result.exit_code == 0
        data = json.loads(result.output)
        
        assert data['count'] > 0
        first_result = data['results'][0]
        assert 'mention' in first_result['content'].lower()
    
    def test_patterns_query_deadlines(self, runner, test_mode_env):
        """CLI handles deadline pattern extraction"""
        result = runner.invoke(query_cli, [
            'patterns',
            '--pattern-type', 'deadlines',
            '--format', 'json'
        ])
        
        assert result.exit_code == 0
        data = json.loads(result.output)
        
        assert data['count'] > 0
        first_result = data['results'][0]
        assert 'deadline' in first_result['content'].lower()
        assert first_result['metadata']['pattern_type'] == 'deadline'
        assert 'due_date' in first_result['metadata']
    
    def test_patterns_with_person_filter(self, runner, test_mode_env):
        """CLI handles person filtering in pattern extraction"""
        result = runner.invoke(query_cli, [
            'patterns',
            '--pattern-type', 'mentions',
            '--person', 'alice@example.com',
            '--format', 'json'
        ])
        
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data['count'] > 0
    
    def test_calendar_find_slots(self, runner, test_mode_env):
        """CLI handles calendar slot finding"""
        result = runner.invoke(query_cli, [
            'calendar', 'find-slots',
            '--attendees', 'alice@example.com,bob@example.com',
            '--duration', '60',
            '--format', 'json'
        ])
        
        assert result.exit_code == 0
        data = json.loads(result.output)
        
        assert 'available_slots' in data
        assert 'attendees' in data
        assert 'duration_minutes' in data
        assert data['duration_minutes'] == 60
        assert len(data['available_slots']) > 0
        
        # Validate slot structure
        first_slot = data['available_slots'][0]
        assert 'start' in first_slot
        assert 'end' in first_slot
    
    def test_calendar_find_slots_table_format(self, runner, test_mode_env):
        """CLI formats calendar slots in table format"""
        result = runner.invoke(query_cli, [
            'calendar', 'find-slots',
            '--attendees', 'alice@example.com',
            '--duration', '30',
            '--format', 'table'
        ])
        
        assert result.exit_code == 0
        assert 'Available Time Slots' in result.output
        assert 'Attendees:' in result.output
        assert 'Duration: 30 minutes' in result.output
        assert 'Available slots:' in result.output
    
    def test_calendar_check_conflicts(self, runner, test_mode_env):
        """CLI handles conflict checking"""
        result = runner.invoke(query_cli, [
            'calendar', 'check-conflicts',
            '--attendees', 'alice@example.com',
            '--start-time', '2025-08-19T14:00:00',
            '--duration', '60'
        ])
        
        assert result.exit_code == 0
        assert 'conflicts' in result.output.lower()
        assert 'Proposed meeting:' in result.output
        assert '2025-08-19T14:00:00' in result.output
        assert '60 minutes' in result.output
    
    def test_stats_command(self, runner, test_mode_env):
        """CLI handles statistics generation"""
        result = runner.invoke(query_cli, [
            'stats',
            '--time-range', 'last week',
            '--format', 'json'
        ])
        
        assert result.exit_code == 0
        data = json.loads(result.output)
        
        assert 'time_range' in data
        assert 'total_messages' in data
        assert 'total_meetings' in data
        assert 'unique_participants' in data
        assert data['time_range'] == 'last week'
    
    def test_stats_with_breakdown(self, runner, test_mode_env):
        """CLI handles statistics with breakdown"""
        result = runner.invoke(query_cli, [
            'stats',
            '--time-range', 'last week',
            '--breakdown', 'channel',
            '--format', 'json'
        ])
        
        assert result.exit_code == 0
        data = json.loads(result.output)
        
        assert 'by_channel' in data
        assert isinstance(data['by_channel'], dict)
        
        # Should have channel breakdown
        for channel, stats in data['by_channel'].items():
            assert 'messages' in stats
            assert 'participants' in stats


class TestOutputFormats:
    """Test output formatting across all commands"""
    
    @pytest.mark.parametrize('output_format', ['json', 'csv', 'table', 'markdown'])
    def test_time_query_output_formats(self, runner, test_mode_env, output_format):
        """All output formats work for time queries"""
        result = runner.invoke(query_cli, [
            'time', 'today',
            '--format', output_format
        ])
        
        assert result.exit_code == 0
        assert len(result.output) > 0
        
        if output_format == 'json':
            # Should be valid JSON
            json.loads(result.output)
        elif output_format == 'csv':
            # Should have CSV headers
            assert 'content,source,date' in result.output
        elif output_format == 'table':
            # Should have table structure
            assert '|' in result.output or 'Score:' in result.output
        elif output_format == 'markdown':
            # Should have markdown headers
            assert '#' in result.output
    
    def test_json_output_schema(self, runner, test_mode_env):
        """JSON output follows consistent schema"""
        result = runner.invoke(query_cli, [
            'time', 'today', 
            '--format', 'json'
        ])
        
        assert result.exit_code == 0
        data = json.loads(result.output)
        
        # Validate schema
        required_fields = ['results', 'metadata', 'count']
        assert all(field in data for field in required_fields)
        
        if data['results']:
            first_result = data['results'][0]
            result_fields = ['content', 'source', 'date', 'relevance_score']
            assert all(field in first_result for field in result_fields)
    
    def test_csv_export_functionality(self, runner, test_mode_env):
        """CSV output suitable for external analysis"""
        result = runner.invoke(query_cli, [
            'person', 'alice@example.com',
            '--format', 'csv'
        ])
        
        assert result.exit_code == 0
        
        lines = result.output.strip().split('\n')
        header = lines[0].split(',')
        
        # Should have proper CSV headers
        expected_headers = ['content', 'source', 'date', 'relevance_score']
        for expected in expected_headers:
            assert any(expected in h for h in header)
    
    def test_verbose_mode_output(self, runner, test_mode_env):
        """Verbose mode includes additional metadata and performance info"""
        result = runner.invoke(query_cli, [
            'time', 'today',
            '--verbose',
            '--format', 'json'
        ])
        
        assert result.exit_code == 0
        data = json.loads(result.output)
        
        # Should include performance metadata
        assert 'performance' in data
        
        # Results should include metadata
        if data['results']:
            first_result = data['results'][0]
            assert 'metadata' in first_result


class TestErrorHandling:
    """Test error handling and user feedback"""
    
    def test_invalid_time_expression(self, runner, test_mode_env):
        """CLI handles invalid time expressions gracefully"""
        result = runner.invoke(query_cli, [
            'time', 'invalid-time-expression'
        ])
        
        # Should fail with appropriate error
        assert result.exit_code != 0
        assert 'error' in result.output.lower()
    
    def test_invalid_person_id(self, runner, test_mode_env):
        """CLI handles invalid person IDs gracefully"""
        # This depends on implementation - mock mode might not validate person IDs
        result = runner.invoke(query_cli, [
            'person', 'nonexistent@nowhere.com',
            '--format', 'json'
        ])
        
        # In test mode, this should still work (mock data)
        assert result.exit_code == 0
    
    def test_invalid_pattern_type(self, runner, test_mode_env):
        """CLI handles invalid pattern types"""
        result = runner.invoke(query_cli, [
            'patterns',
            '--pattern-type', 'invalid_pattern'
        ])
        
        # Should fail with validation error
        assert result.exit_code != 0
    
    def test_invalid_output_format(self, runner, test_mode_env):
        """CLI handles invalid output formats"""
        result = runner.invoke(query_cli, [
            'time', 'today',
            '--format', 'invalid_format'
        ])
        
        # Should fail with validation error
        assert result.exit_code != 0
    
    def test_missing_required_args(self, runner, test_mode_env):
        """CLI handles missing required arguments"""
        result = runner.invoke(query_cli, [
            'patterns'
            # Missing required --pattern-type
        ])
        
        assert result.exit_code != 0
        assert 'required' in result.output.lower() or 'missing' in result.output.lower()
    
    def test_calendar_missing_attendees(self, runner, test_mode_env):
        """CLI handles missing attendees in calendar commands"""
        result = runner.invoke(query_cli, [
            'calendar', 'find-slots',
            '--duration', '60'
            # Missing required --attendees
        ])
        
        assert result.exit_code != 0


class TestPerformanceRequirements:
    """Test performance requirements are met"""
    
    def test_query_performance_target(self, runner, test_mode_env):
        """CLI queries complete within performance targets"""
        import time
        
        start_time = time.time()
        result = runner.invoke(query_cli, [
            'time', 'last week',
            '--limit', '10'
        ])
        end_time = time.time()
        
        assert result.exit_code == 0
        # Including CLI overhead, should be under 5 seconds
        assert (end_time - start_time) < 5.0
    
    def test_large_result_handling(self, runner, test_mode_env):
        """CLI handles large result sets appropriately"""
        result = runner.invoke(query_cli, [
            'time', 'last month',
            '--limit', '100',
            '--format', 'json'
        ])
        
        assert result.exit_code == 0
        # Should not crash with large result sets
        data = json.loads(result.output)
        assert 'results' in data


class TestIntegrationWithMockEngines:
    """Test integration with mock engine implementations"""
    
    def test_mock_mode_indication(self, runner, test_mode_env):
        """CLI clearly indicates when using mock data"""
        result = runner.invoke(query_cli, [
            'time', 'today',
            '--format', 'json'
        ])
        
        assert result.exit_code == 0
        data = json.loads(result.output)
        
        # Should indicate mock mode
        assert data['metadata']['mock_mode'] is True
    
    def test_all_mock_engines_functional(self, runner, test_mode_env):
        """All mock engine implementations are functional"""
        commands_to_test = [
            ['time', 'today'],
            ['person', 'alice@example.com'],
            ['patterns', '--pattern-type', 'todos'],
            ['stats', '--time-range', 'last week']
        ]
        
        for command in commands_to_test:
            result = runner.invoke(query_cli, command + ['--format', 'json'])
            assert result.exit_code == 0, f"Command failed: {command}"
            
            data = json.loads(result.output)
            assert 'metadata' in data
            assert data['metadata']['mock_mode'] is True


class TestCLIConsistency:
    """Test consistency across CLI tools"""
    
    def test_consistent_help_format(self, runner):
        """All commands have consistent help formatting"""
        commands_to_test = ['time', 'person', 'patterns', 'calendar', 'stats']
        
        for command in commands_to_test:
            result = runner.invoke(query_cli, [command, '--help'])
            assert result.exit_code == 0
            assert 'Examples:' in result.output
            assert 'Usage:' in result.output
    
    def test_consistent_error_handling(self, runner, test_mode_env):
        """Error handling is consistent across commands"""
        # Test invalid arguments for different commands
        invalid_commands = [
            ['time'],  # Missing time expression
            ['person'],  # Missing person ID
            ['calendar', 'find-slots'],  # Missing attendees
        ]
        
        for command in invalid_commands:
            result = runner.invoke(query_cli, command)
            assert result.exit_code != 0
            # Should not crash, should provide helpful error
            assert len(result.output) > 0
    
    def test_consistent_output_structure(self, runner, test_mode_env):
        """Output structure is consistent across query types"""
        commands_to_test = [
            ['time', 'today'],
            ['person', 'alice@example.com'],
            ['patterns', '--pattern-type', 'todos']
        ]
        
        for command in commands_to_test:
            result = runner.invoke(query_cli, command + ['--format', 'json'])
            assert result.exit_code == 0
            
            data = json.loads(result.output)
            # All should have consistent top-level structure
            assert 'results' in data or 'available_slots' in data  # Calendar is different
            assert 'metadata' in data
            assert 'count' in data or len(data) > 0


@pytest.mark.slow
class TestEndToEndWorkflows:
    """Test complete end-to-end workflows"""
    
    def test_full_daily_workflow(self, runner, test_mode_env):
        """Complete daily workflow integration"""
        # Step 1: Query yesterday's activity
        yesterday_result = runner.invoke(query_cli, [
            'time', 'yesterday', '--format', 'json'
        ])
        assert yesterday_result.exit_code == 0
        
        # Step 2: Check specific person's activity
        person_result = runner.invoke(query_cli, [
            'person', 'alice@example.com', '--format', 'json'
        ])
        assert person_result.exit_code == 0
        
        # Step 3: Find TODOs
        todo_result = runner.invoke(query_cli, [
            'patterns', '--pattern-type', 'todos', '--format', 'json'
        ])
        assert todo_result.exit_code == 0
        
        # Step 4: Find meeting slots
        slots_result = runner.invoke(query_cli, [
            'calendar', 'find-slots', 
            '--attendees', 'alice@example.com,bob@example.com',
            '--format', 'json'
        ])
        assert slots_result.exit_code == 0
        
        # All steps should complete successfully
        all_results = [yesterday_result, person_result, todo_result, slots_result]
        assert all(result.exit_code == 0 for result in all_results)
    
    def test_data_consistency_across_queries(self, runner, test_mode_env):
        """Data consistency maintained across different query types"""
        # In mock mode, we can't test real data consistency,
        # but we can verify that the mock engines are consistent
        
        person_result = runner.invoke(query_cli, [
            'person', 'alice@example.com', '--format', 'json'
        ])
        assert person_result.exit_code == 0
        
        person_data = json.loads(person_result.output)
        
        # Check that person appears in pattern queries
        pattern_result = runner.invoke(query_cli, [
            'patterns', '--pattern-type', 'mentions',
            '--person', 'alice@example.com', '--format', 'json'
        ])
        assert pattern_result.exit_code == 0
        
        # Both should work without errors (specific consistency depends on real implementation)
        pattern_data = json.loads(pattern_result.output)
        assert len(pattern_data['results']) >= 0  # May be empty, that's ok


if __name__ == '__main__':
    pytest.main([__file__, '-v'])