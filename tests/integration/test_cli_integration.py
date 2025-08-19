"""
Comprehensive CLI Integration Tests

End-to-end tests validating all CLI tools work together correctly,
including cross-tool data consistency, performance requirements,
and complete workflow validation.

Test Categories:
- End-to-end workflow integration
- Cross-module data consistency
- Performance across all tools
- Help system completeness
- Error handling consistency
- Test mode functionality
- Real vs mock data handling

References:
- tasks/phase1_agent_c_cli.md lines 454-541 for integration criteria
- All CLI tools: query_facts.py, daily_summary.py
- src/cli/* for shared utilities
"""

import pytest
import json
import time
import tempfile
import os
import sys
from pathlib import Path
from unittest.mock import patch
from click.testing import CliRunner

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import all CLI tools
from tools.query_facts import cli as query_cli
from tools.daily_summary import generate_summary as summary_cli

# Import CLI utilities for testing
from src.cli.errors import CLIError, check_test_mode
from src.cli.formatters import format_query_results, format_summary
from src.cli.interfaces import (
    get_query_engine, get_person_engine, get_activity_analyzer
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


@pytest.fixture
def temp_output_dir():
    """Temporary directory for output files"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


class TestCLIIntegration:
    """Test end-to-end CLI integration across all modules"""
    
    def test_full_workflow_integration(self, runner, test_mode_env):
        """Complete workflow: query → summarize → coordinate"""
        
        # Step 1: Query recent activity
        query_result = runner.invoke(query_cli, [
            'time', 'yesterday', '--format', 'json'
        ])
        assert query_result.exit_code == 0
        query_data = json.loads(query_result.output)
        assert query_data['count'] > 0
        
        # Step 2: Generate summary
        summary_result = runner.invoke(summary_cli, [
            '--date', 'yesterday', '--format', 'json'
        ])
        assert summary_result.exit_code == 0
        summary_data = json.loads(summary_result.output)
        assert 'slack_activity' in summary_data
        
        # Step 3: Find calendar slots
        slots_result = runner.invoke(query_cli, [
            'calendar', 'find-slots', 
            '--attendees', 'alice@example.com,bob@example.com',
            '--duration', '30',
            '--format', 'json'
        ])
        assert slots_result.exit_code == 0
        slots_data = json.loads(slots_result.output)
        assert 'available_slots' in slots_data
        
        # Step 4: Extract patterns
        patterns_result = runner.invoke(query_cli, [
            'patterns', '--pattern-type', 'todos', '--format', 'json'
        ])
        assert patterns_result.exit_code == 0
        patterns_data = json.loads(patterns_result.output)
        assert 'results' in patterns_data
        
        # All steps should complete successfully
        all_results = [query_result, summary_result, slots_result, patterns_result]
        assert all(result.exit_code == 0 for result in all_results)
        
        # All should indicate mock mode
        for data in [query_data, summary_data, patterns_data]:
            if 'metadata' in data:
                assert data['metadata'].get('mock_mode') is True
    
    def test_cross_module_data_consistency(self, runner, test_mode_env):
        """Data consistency between different CLI tools"""
        
        # Get person activity via query tool
        person_query = runner.invoke(query_cli, [
            'person', 'alice@example.com', '--format', 'json'
        ])
        assert person_query.exit_code == 0
        person_data = json.loads(person_query.output)
        
        # Get same person in daily summary
        summary_query = runner.invoke(summary_cli, [
            '--person', 'alice@example.com', '--format', 'json'
        ])
        assert summary_query.exit_code == 0
        summary_data = json.loads(summary_query.output)
        
        # Both should reference the same person
        assert person_data['metadata'].get('mock_mode') is True
        assert summary_data['person'] == 'alice@example.com'
        
        # In mock mode, we can verify consistent mock data
        person_metadata = person_data.get('metadata', {})
        if 'activity_summary' in person_metadata:
            person_summary = person_metadata['activity_summary']
            # Mock data should be consistent (42 messages)
            assert person_summary.get('message_count') == 42
        
        # Summary should also have consistent mock data
        slack_activity = summary_data.get('slack_activity', {})
        assert slack_activity.get('message_count') == 42
    
    def test_performance_across_tools(self, runner, test_mode_env):
        """All CLI tools meet performance requirements"""
        
        test_commands = [
            # Query tools (should be <3 seconds)
            (query_cli, ['time', 'last week'], 3.0),
            (query_cli, ['person', 'alice@example.com'], 3.0),
            (query_cli, ['patterns', '--pattern-type', 'todos'], 3.0),
            (query_cli, ['stats', '--time-range', 'last week'], 3.0),
            
            # Calendar operations (should be <5 seconds)
            (query_cli, ['calendar', 'find-slots', '--attendees', 'alice@example.com', '--duration', '30'], 5.0),
            
            # Summary generation (should be <10 seconds)
            (summary_cli, ['--date', '2025-08-19'], 10.0),
        ]
        
        for cli_tool, cmd, time_limit in test_commands:
            start_time = time.time()
            result = runner.invoke(cli_tool, cmd)
            end_time = time.time()
            
            assert result.exit_code == 0, f"Command failed: {cmd}"
            duration = end_time - start_time
            assert duration < time_limit, f"Command too slow ({duration:.2f}s > {time_limit}s): {cmd}"
    
    def test_help_system_completeness(self, runner):
        """All CLI tools provide comprehensive help"""
        
        # Main query CLI help
        result = runner.invoke(query_cli, ['--help'])
        assert result.exit_code == 0
        assert 'Usage:' in result.output
        assert 'Commands:' in result.output
        
        # Subcommand help
        subcommands = ['time', 'person', 'patterns', 'calendar', 'stats']
        for subcmd in subcommands:
            result = runner.invoke(query_cli, [subcmd, '--help'])
            assert result.exit_code == 0, f"Help failed for: {subcmd}"
            assert subcmd in result.output.lower()
            assert 'Examples:' in result.output
        
        # Calendar subcommands
        calendar_subcmds = ['find-slots', 'check-conflicts']
        for subcmd in calendar_subcmds:
            result = runner.invoke(query_cli, ['calendar', subcmd, '--help'])
            assert result.exit_code == 0, f"Calendar help failed for: {subcmd}"
        
        # Daily summary help
        result = runner.invoke(summary_cli, ['--help'])
        assert result.exit_code == 0
        assert 'Generate daily, weekly, or monthly' in result.output
    
    def test_error_handling_consistency(self, runner, test_mode_env):
        """Error handling is consistent across all CLI tools"""
        
        # Test various error conditions
        error_test_cases = [
            # Invalid arguments
            (query_cli, ['time'], 'Missing time expression'),
            (query_cli, ['person'], 'Missing person ID'),
            (query_cli, ['patterns'], 'Missing pattern type'),
            (query_cli, ['calendar', 'find-slots'], 'Missing attendees'),
            (summary_cli, ['--date', 'invalid-date'], 'Invalid date format'),
            
            # Invalid options
            (query_cli, ['time', 'today', '--format', 'invalid'], 'Invalid format'),
            (query_cli, ['patterns', '--pattern-type', 'invalid'], 'Invalid pattern'),
            (summary_cli, ['--period', 'invalid'], 'Invalid period'),
        ]
        
        for cli_tool, cmd, expected_context in error_test_cases:
            result = runner.invoke(cli_tool, cmd)
            
            # Should fail with non-zero exit code
            assert result.exit_code != 0, f"Should have failed: {cmd}"
            
            # Should provide some error information
            assert len(result.output) > 0, f"No error output for: {cmd}"
            
            # Should not crash with unhandled exceptions
            assert 'Traceback' not in result.output, f"Unhandled exception in: {cmd}"
    
    def test_output_format_consistency(self, runner, test_mode_env):
        """Output formats are consistent across tools"""
        
        # Test JSON format consistency
        json_commands = [
            (query_cli, ['time', 'today', '--format', 'json']),
            (query_cli, ['person', 'alice@example.com', '--format', 'json']),
            (query_cli, ['patterns', '--pattern-type', 'todos', '--format', 'json']),
            (query_cli, ['stats', '--time-range', 'last week', '--format', 'json']),
            (summary_cli, ['--format', 'json']),
        ]
        
        for cli_tool, cmd in json_commands:
            result = runner.invoke(cli_tool, cmd)
            assert result.exit_code == 0, f"JSON command failed: {cmd}"
            
            # Should be valid JSON
            try:
                data = json.loads(result.output)
                assert isinstance(data, dict), f"JSON should be object: {cmd}"
            except json.JSONDecodeError:
                pytest.fail(f"Invalid JSON output for: {cmd}")
        
        # Test table format consistency (default for most)
        table_commands = [
            (query_cli, ['time', 'today']),
            (query_cli, ['person', 'alice@example.com']),
            (summary_cli, []),
        ]
        
        for cli_tool, cmd in table_commands:
            result = runner.invoke(cli_tool, cmd)
            assert result.exit_code == 0, f"Table command failed: {cmd}"
            assert len(result.output.strip()) > 0, f"No table output: {cmd}"
    
    def test_test_mode_functionality(self, runner, test_mode_env):
        """Test mode works consistently across all tools"""
        
        # Verify test mode is detected
        assert check_test_mode() is True
        
        # All tools should work in test mode
        test_commands = [
            (query_cli, ['time', 'today', '--format', 'json']),
            (query_cli, ['person', 'alice@example.com', '--format', 'json']),
            (query_cli, ['patterns', '--pattern-type', 'todos', '--format', 'json']),
            (query_cli, ['calendar', 'find-slots', '--attendees', 'alice@example.com', '--duration', '30', '--format', 'json']),
            (summary_cli, ['--format', 'json']),
        ]
        
        for cli_tool, cmd in test_commands:
            result = runner.invoke(cli_tool, cmd)
            assert result.exit_code == 0, f"Test mode failed for: {cmd}"
            
            if cli_tool == query_cli and '--format' in cmd and 'json' in cmd:
                data = json.loads(result.output)
                # Should indicate mock mode for query tools
                if 'metadata' in data:
                    assert data['metadata'].get('mock_mode') is True
    
    def test_memory_and_resource_usage(self, runner, test_mode_env):
        """CLI tools don't exceed memory limits"""
        import psutil
        import os
        
        # Get current process
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Run several operations
        operations = [
            (query_cli, ['time', 'last month', '--limit', '100']),
            (query_cli, ['patterns', '--pattern-type', 'todos', '--limit', '50']),
            (summary_cli, ['--detailed']),
        ]
        
        max_memory = initial_memory
        for cli_tool, cmd in operations:
            result = runner.invoke(cli_tool, cmd)
            assert result.exit_code == 0
            
            current_memory = process.memory_info().rss / 1024 / 1024  # MB
            max_memory = max(max_memory, current_memory)
        
        # Memory increase should be reasonable (less than 150MB as per requirements)
        memory_increase = max_memory - initial_memory
        assert memory_increase < 150, f"Memory usage too high: {memory_increase:.1f}MB"
    
    def test_concurrent_tool_usage(self, runner, test_mode_env):
        """CLI tools can be used concurrently without conflicts"""
        import threading
        import queue
        
        results_queue = queue.Queue()
        
        def run_command(cli_tool, cmd):
            try:
                result = runner.invoke(cli_tool, cmd)
                results_queue.put(('success', result.exit_code, cmd))
            except Exception as e:
                results_queue.put(('error', str(e), cmd))
        
        # Start multiple commands concurrently
        threads = []
        commands = [
            (query_cli, ['time', 'today']),
            (query_cli, ['person', 'alice@example.com']),
            (summary_cli, ['--date', '2025-08-19']),
            (query_cli, ['patterns', '--pattern-type', 'todos']),
        ]
        
        for cli_tool, cmd in commands:
            thread = threading.Thread(target=run_command, args=(cli_tool, cmd))
            threads.append(thread)
            thread.start()
        
        # Wait for all to complete
        for thread in threads:
            thread.join(timeout=10)  # 10 second timeout
            assert not thread.is_alive(), "Thread didn't complete in time"
        
        # Check all results
        results = []
        while not results_queue.empty():
            results.append(results_queue.get())
        
        assert len(results) == len(commands), "Not all commands completed"
        
        for status, exit_code, cmd in results:
            assert status == 'success', f"Command failed: {cmd}"
            assert exit_code == 0, f"Non-zero exit code for: {cmd}"


class TestFormatterIntegration:
    """Test integration with formatter utilities"""
    
    def test_formatter_utility_integration(self, test_mode_env):
        """Formatter utilities work with CLI tool data"""
        
        # Get some mock data
        query_engine = get_query_engine()
        result = query_engine.query(time_expression='today', limit=3)
        
        # Test different formatters
        formats_to_test = ['json', 'csv', 'table', 'markdown']
        
        for fmt in formats_to_test:
            formatted = format_query_results(result, fmt, verbose=False)
            assert isinstance(formatted, str)
            assert len(formatted) > 0
        
        # Test summary formatter
        activity_analyzer = get_activity_analyzer()
        summary_data = activity_analyzer.generate_daily_summary(date='2025-08-19')
        
        formatted_summary = format_summary(summary_data, 'table')
        assert isinstance(formatted_summary, str)
        assert len(formatted_summary) > 0
    
    def test_formatter_error_handling(self, test_mode_env):
        """Formatters handle edge cases gracefully"""
        
        # Test with empty results
        empty_result = {'results': [], 'metadata': {}, 'count': 0}
        formatted = format_query_results(empty_result, 'table')
        assert 'No results found' in formatted or len(formatted.strip()) == 0
        
        # Test with malformed data
        try:
            format_query_results(None, 'json')
            # Should either work or raise a proper FormatterError
        except Exception as e:
            # Should be a proper exception, not a crash
            assert 'FormatterError' in str(type(e).__name__) or 'Error' in str(e)


class TestEndToEndScenarios:
    """Test complete end-to-end user scenarios"""
    
    def test_daily_workflow_scenario(self, runner, test_mode_env, temp_output_dir):
        """Complete daily workflow from start to finish"""
        
        # Morning: Check yesterday's activity
        yesterday_result = runner.invoke(query_cli, [
            'time', 'yesterday', '--format', 'json'
        ])
        assert yesterday_result.exit_code == 0
        yesterday_data = json.loads(yesterday_result.output)
        
        # Generate daily summary report
        summary_file = temp_output_dir / 'daily_summary.json'
        summary_result = runner.invoke(summary_cli, [
            '--date', 'yesterday', 
            '--format', 'json',
            '--output-file', str(summary_file)
        ])
        assert summary_result.exit_code == 0
        assert summary_file.exists()
        
        # Find available meeting slots for today
        slots_result = runner.invoke(query_cli, [
            'calendar', 'find-slots',
            '--attendees', 'alice@example.com,bob@example.com',
            '--duration', '60',
            '--format', 'json'
        ])
        assert slots_result.exit_code == 0
        slots_data = json.loads(slots_result.output)
        
        # Check for pending TODOs
        todo_result = runner.invoke(query_cli, [
            'patterns', '--pattern-type', 'todos',
            '--time-range', 'today',
            '--format', 'json'
        ])
        assert todo_result.exit_code == 0
        todo_data = json.loads(todo_result.output)
        
        # Generate weekly statistics
        stats_result = runner.invoke(query_cli, [
            'stats', '--time-range', 'this week',
            '--format', 'json'
        ])
        assert stats_result.exit_code == 0
        stats_data = json.loads(stats_result.output)
        
        # All operations should complete successfully
        assert all(data for data in [yesterday_data, slots_data, todo_data, stats_data])
        
        # Summary file should contain comprehensive data
        with open(summary_file) as f:
            summary_data = json.load(f)
            assert 'slack_activity' in summary_data
            assert 'calendar_activity' in summary_data
            assert 'key_highlights' in summary_data
    
    def test_team_coordination_scenario(self, runner, test_mode_env):
        """Team coordination workflow"""
        
        # Check team member activity
        team_members = ['alice@example.com', 'bob@example.com', 'charlie@example.com']
        member_activities = []
        
        for member in team_members:
            result = runner.invoke(query_cli, [
                'person', member,
                '--activity-summary',
                '--format', 'json'
            ])
            assert result.exit_code == 0
            member_data = json.loads(result.output)
            member_activities.append((member, member_data))
        
        # Find common meeting slots for the team
        team_slots = runner.invoke(query_cli, [
            'calendar', 'find-slots',
            '--attendees', ','.join(team_members),
            '--duration', '90',
            '--format', 'json'
        ])
        assert team_slots.exit_code == 0
        slots_data = json.loads(team_slots.output)
        
        # Check for team mentions and decisions
        mentions_result = runner.invoke(query_cli, [
            'patterns', '--pattern-type', 'mentions',
            '--time-range', 'this week',
            '--format', 'json'
        ])
        assert mentions_result.exit_code == 0
        
        decisions_result = runner.invoke(query_cli, [
            'patterns', '--pattern-type', 'decisions',
            '--time-range', 'this week', 
            '--format', 'json'
        ])
        assert decisions_result.exit_code == 0
        
        # Generate team summary
        team_summary = runner.invoke(summary_cli, [
            '--period', 'week',
            '--detailed',
            '--include-trends',
            '--format', 'json'
        ])
        assert team_summary.exit_code == 0
        
        # All team coordination operations should work
        assert all(result.exit_code == 0 for result in [
            team_slots, mentions_result, decisions_result, team_summary
        ])
    
    def test_reporting_and_analysis_scenario(self, runner, test_mode_env, temp_output_dir):
        """Comprehensive reporting and analysis workflow"""
        
        # Generate multiple report formats
        report_formats = ['json', 'markdown', 'table']
        generated_reports = []
        
        for fmt in report_formats:
            report_file = temp_output_dir / f'weekly_report.{fmt}'
            result = runner.invoke(summary_cli, [
                '--period', 'week',
                '--detailed',
                '--include-trends',
                '--compare-to', 'last week',
                '--format', fmt,
                '--output-file', str(report_file)
            ])
            assert result.exit_code == 0
            assert report_file.exists()
            generated_reports.append(report_file)
        
        # Generate activity statistics with different breakdowns
        breakdown_types = ['channel', 'person']
        
        for breakdown in breakdown_types:
            stats_result = runner.invoke(query_cli, [
                'stats', '--time-range', 'last week',
                '--breakdown', breakdown,
                '--format', 'json'
            ])
            assert stats_result.exit_code == 0
            stats_data = json.loads(stats_result.output)
            assert f'by_{breakdown}' in stats_data
        
        # Extract comprehensive patterns
        pattern_types = ['todos', 'mentions', 'deadlines', 'decisions']
        pattern_results = {}
        
        for pattern_type in pattern_types:
            result = runner.invoke(query_cli, [
                'patterns', '--pattern-type', pattern_type,
                '--time-range', 'last week',
                '--format', 'json'
            ])
            assert result.exit_code == 0
            pattern_data = json.loads(result.output)
            pattern_results[pattern_type] = pattern_data
        
        # All reports should be generated successfully
        assert len(generated_reports) == len(report_formats)
        assert len(pattern_results) == len(pattern_types)
        
        # Verify report contents
        for report_file in generated_reports:
            assert report_file.stat().st_size > 100  # Should have substantial content


if __name__ == '__main__':
    # Run with various markers for different test categories
    pytest.main([
        __file__, 
        '-v',
        '--tb=short',  # Shorter traceback format
        '-x',          # Stop on first failure for faster feedback
    ])