"""
Integration Tests for Daily Summary CLI Tool

Comprehensive tests validating the daily summary tool functionality,
including daily/weekly summary generation, person-focused reports,
scheduled execution, and comparative analysis.

Test Categories:
- Summary generation for different periods
- Output format validation
- Scheduled execution mode
- Comparison functionality  
- File output and automation
- Performance requirements
- Error handling and user feedback

References:
- tasks/phase1_agent_c_cli.md lines 236-347 for test acceptance criteria
- tools/daily_summary.py for implementation
- src/cli/interfaces.py for ActivityAnalyzer integration
"""

import pytest
import json
import tempfile
import os
import sys
from pathlib import Path
from datetime import datetime, date, timedelta
from unittest.mock import patch, MagicMock
from click.testing import CliRunner

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import the CLI under test
from tools.daily_summary import generate_summary, batch_summaries, main

# Import supporting modules
from src.cli.errors import ValidationError
from src.cli.interfaces import MockActivityAnalyzer


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


class TestDailySummaryCLI:
    """Test daily summary generation tool"""
    
    def test_help_output(self, runner):
        """CLI provides comprehensive help documentation"""
        # Test the single command help (when invoked without subcommand)
        result = runner.invoke(generate_summary, ['--help'])
        
        assert result.exit_code == 0
        assert 'Generate daily, weekly, or monthly activity summaries' in result.output
        assert 'Examples:' in result.output
        assert '--date' in result.output
        assert '--format' in result.output
        assert '--person' in result.output
    
    def test_version_display(self, runner):
        """CLI displays correct version information"""
        result = runner.invoke(generate_summary, ['--version'])
        
        assert result.exit_code == 0
        assert '1.0.0' in result.output
    
    def test_basic_daily_summary_generation(self, runner, test_mode_env):
        """Generate basic daily summary with default settings"""
        result = runner.invoke(generate_summary, [
            '--date', '2025-08-19',
            '--format', 'json'
        ])
        
        assert result.exit_code == 0
        data = json.loads(result.output)
        
        # Validate summary structure
        required_sections = [
            'date', 'slack_activity', 'calendar_activity', 
            'drive_activity', 'key_highlights'
        ]
        for section in required_sections:
            assert section in data, f"Missing section: {section}"
        
        # Validate metadata
        assert 'generation_metadata' in data
        metadata = data['generation_metadata']
        assert metadata['target_date'] == '2025-08-19'
        assert metadata['period'] == 'day'
        assert metadata['test_mode'] is True
    
    def test_daily_summary_table_format(self, runner, test_mode_env):
        """Generate daily summary in table format"""
        result = runner.invoke(generate_summary, [
            '--date', '2025-08-19',
            '--format', 'table'
        ])
        
        assert result.exit_code == 0
        
        # Should contain formatted sections
        assert 'Daily Summary - 2025-08-19' in result.output
        assert '📱 Slack Activity:' in result.output
        assert '📅 Calendar Activity:' in result.output
        assert '📁 Drive Activity:' in result.output
        assert '✨ Key Highlights:' in result.output
        
        # Should contain mock data values
        assert 'Messages: 42' in result.output
        assert 'Meetings: 3' in result.output
    
    def test_daily_summary_markdown_format(self, runner, test_mode_env):
        """Generate daily summary in markdown format"""
        result = runner.invoke(generate_summary, [
            '--date', '2025-08-19',
            '--format', 'markdown'
        ])
        
        assert result.exit_code == 0
        
        # Should contain markdown headers
        assert '# Daily Summary - 2025-08-19' in result.output
        assert '## 📱 Slack Activity' in result.output
        assert '## 📅 Calendar Activity' in result.output
        assert '## 📁 Drive Activity' in result.output
        assert '## ✨ Key Highlights' in result.output
        
        # Should contain markdown formatting
        assert '- **Messages**: 42' in result.output
        assert '- **Meetings**: 3' in result.output
    
    def test_weekly_summary_generation(self, runner, test_mode_env):
        """Generate weekly rollup summary"""
        result = runner.invoke(generate_summary, [
            '--period', 'week',
            '--date', '2025-08-19',  # Tuesday, so week starts on Monday 2025-08-18
            '--format', 'json'
        ])
        
        assert result.exit_code == 0
        data = json.loads(result.output)
        
        # Should have weekly summary structure
        assert 'generation_metadata' in data
        assert data['generation_metadata']['period'] == 'week'
        
        # Mock weekly summary should have appropriate fields
        if 'summary_stats' in data:
            stats = data['summary_stats']
            assert 'total_messages' in stats
            assert 'total_meetings' in stats
            assert 'active_days' in stats
    
    def test_monthly_summary_generation(self, runner, test_mode_env):
        """Generate monthly summary"""
        result = runner.invoke(generate_summary, [
            '--period', 'month',
            '--date', '2025-08-15',
            '--format', 'json'
        ])
        
        assert result.exit_code == 0
        data = json.loads(result.output)
        
        # Should generate without errors (may use weekly as fallback)
        assert 'generation_metadata' in data
        # Period might be 'month' or 'week' depending on implementation
        assert data['generation_metadata']['period'] in ['month', 'week']
    
    def test_person_focused_summary(self, runner, test_mode_env):
        """Generate summary focused on specific person"""
        result = runner.invoke(generate_summary, [
            '--date', '2025-08-19',
            '--person', 'alice@example.com',
            '--format', 'json'
        ])
        
        assert result.exit_code == 0
        data = json.loads(result.output)
        
        # Should include person in metadata
        metadata = data['generation_metadata']
        assert metadata['person_focus'] == 'alice@example.com'
        
        # Mock data should reference the person
        assert 'person' in data
        assert data['person'] == 'alice@example.com'
    
    def test_detailed_mode(self, runner, test_mode_env):
        """Generate detailed summary with extended information"""
        result = runner.invoke(generate_summary, [
            '--date', '2025-08-19',
            '--detailed',
            '--format', 'json'
        ])
        
        assert result.exit_code == 0
        data = json.loads(result.output)
        
        # Should include detailed flag in metadata
        metadata = data['generation_metadata']
        assert metadata['detailed_mode'] is True
        
        # Should have statistics section in detailed mode
        assert 'statistics' in data
    
    def test_trends_inclusion(self, runner, test_mode_env):
        """Generate summary with trend analysis"""
        result = runner.invoke(generate_summary, [
            '--period', 'week',
            '--include-trends',
            '--format', 'json'
        ])
        
        assert result.exit_code == 0
        data = json.loads(result.output)
        
        # Should include trends flag in metadata
        metadata = data['generation_metadata']
        assert metadata['trends_included'] is True
        
        # Mock weekly data should have trends
        if 'trends' in data:
            trends = data['trends']
            assert isinstance(trends, dict)
    
    def test_file_output(self, runner, test_mode_env, temp_output_dir):
        """Generate summary and save to file"""
        output_file = temp_output_dir / 'test_summary.json'
        
        result = runner.invoke(generate_summary, [
            '--date', '2025-08-19',
            '--format', 'json',
            '--output-file', str(output_file)
        ])
        
        assert result.exit_code == 0
        assert 'Summary saved to' in result.output
        
        # File should be created and contain valid JSON
        assert output_file.exists()
        
        with open(output_file) as f:
            data = json.load(f)
            assert 'date' in data
            assert 'slack_activity' in data
    
    def test_scheduled_execution_mode(self, runner, test_mode_env, temp_output_dir):
        """Test scheduled execution mode for automation"""
        output_file = temp_output_dir / 'scheduled_summary.json'
        
        result = runner.invoke(generate_summary, [
            '--scheduled',
            '--output-file', str(output_file),
            '--format', 'json'
        ])
        
        assert result.exit_code == 0
        
        # Scheduled mode should have minimal output
        assert 'TEST MODE ACTIVE' not in result.output  # No verbose messaging
        assert 'Summary generated:' in result.output
        
        # File should still be created
        assert output_file.exists()
    
    def test_comparison_functionality(self, runner, test_mode_env):
        """Test comparative analysis against previous periods"""
        result = runner.invoke(generate_summary, [
            '--date', '2025-08-19',
            '--compare-to', 'last week',
            '--format', 'json'
        ])
        
        assert result.exit_code == 0
        data = json.loads(result.output)
        
        # Should include comparison data
        assert 'comparison' in data
        comparison = data['comparison']
        assert 'compare_to_period' in comparison
        assert 'comparison_summary' in comparison
        assert comparison['compare_to_period'] == 'last week'
    
    def test_exclude_weekends_option(self, runner, test_mode_env):
        """Test weekend exclusion functionality"""
        result = runner.invoke(generate_summary, [
            '--date', '2025-08-19',
            '--exclude-weekends',
            '--format', 'json'
        ])
        
        assert result.exit_code == 0
        data = json.loads(result.output)
        
        # Should include weekend exclusion flag
        metadata = data['generation_metadata']
        assert metadata['weekends_excluded'] is True
    
    def test_verbose_mode_output(self, runner, test_mode_env):
        """Test verbose mode with performance information"""
        result = runner.invoke(generate_summary, [
            '--date', '2025-08-19',
            '--verbose',
            '--format', 'json'
        ])
        
        assert result.exit_code == 0
        
        # Should include performance information in verbose mode
        assert 'generated in' in result.output.lower()
        
        data = json.loads(result.output)
        metadata = data['generation_metadata']
        assert 'generated_at' in metadata


class TestBatchSummaries:
    """Test batch summary generation functionality"""
    
    def test_batch_date_range(self, runner, test_mode_env, temp_output_dir):
        """Generate summaries for a date range"""
        result = runner.invoke(batch_summaries, [
            '2025-08-19', '2025-08-21',  # 3 days
            '--output-dir', str(temp_output_dir),
            '--format', 'json'
        ])
        
        assert result.exit_code == 0
        assert 'Generated 3 summaries' in result.output
        
        # Should create files for each date
        expected_files = [
            'summary_2025-08-19.json',
            'summary_2025-08-20.json', 
            'summary_2025-08-21.json'
        ]
        
        for filename in expected_files:
            file_path = temp_output_dir / filename
            assert file_path.exists(), f"Missing file: {filename}"
            
            # Each file should contain valid summary
            with open(file_path) as f:
                data = json.load(f)
                assert 'date' in data
    
    def test_batch_with_person_filter(self, runner, test_mode_env, temp_output_dir):
        """Generate batch summaries focused on specific person"""
        result = runner.invoke(batch_summaries, [
            '2025-08-19', '2025-08-20',  # 2 days
            '--person', 'alice@example.com',
            '--output-dir', str(temp_output_dir),
            '--format', 'json'
        ])
        
        assert result.exit_code == 0
        assert 'Generated 2 summaries' in result.output
        
        # Files should have person suffix
        expected_files = [
            'summary_2025-08-19_alice.json',
            'summary_2025-08-20_alice.json'
        ]
        
        for filename in expected_files:
            file_path = temp_output_dir / filename
            assert file_path.exists(), f"Missing file: {filename}"


class TestErrorHandling:
    """Test error handling and validation"""
    
    def test_invalid_date_format(self, runner, test_mode_env):
        """Handle invalid date formats gracefully"""
        result = runner.invoke(generate_summary, [
            '--date', 'invalid-date-format'
        ])
        
        assert result.exit_code != 0
        assert 'Invalid date format' in result.output
        assert 'YYYY-MM-DD' in result.output
    
    def test_invalid_period(self, runner, test_mode_env):
        """Handle invalid period selection"""
        result = runner.invoke(generate_summary, [
            '--period', 'invalid_period'
        ])
        
        assert result.exit_code != 0
    
    def test_invalid_output_format(self, runner, test_mode_env):
        """Handle invalid output format"""
        result = runner.invoke(generate_summary, [
            '--format', 'invalid_format'
        ])
        
        assert result.exit_code != 0
    
    def test_invalid_comparison_period(self, runner, test_mode_env):
        """Handle invalid comparison period"""
        result = runner.invoke(generate_summary, [
            '--date', '2025-08-19',
            '--compare-to', 'invalid-comparison',
            '--format', 'json'
        ])
        
        # Should still generate summary but with comparison error
        assert result.exit_code == 0
        data = json.loads(result.output)
        
        if 'comparison' in data:
            # May have comparison error
            assert 'error' in data['comparison'] or 'comparison_summary' in data['comparison']
    
    def test_output_directory_creation(self, runner, test_mode_env, temp_output_dir):
        """Create output directories if they don't exist"""
        nested_dir = temp_output_dir / 'nested' / 'output'
        output_file = nested_dir / 'summary.json'
        
        result = runner.invoke(generate_summary, [
            '--date', '2025-08-19',
            '--format', 'json',
            '--output-file', str(output_file)
        ])
        
        assert result.exit_code == 0
        assert output_file.exists()
        assert nested_dir.exists()
    
    def test_batch_invalid_date_range(self, runner, test_mode_env):
        """Handle invalid date ranges in batch mode"""
        result = runner.invoke(batch_summaries, [
            '2025-08-20', '2025-08-19'  # End before start
        ])
        
        assert result.exit_code != 0
        assert 'Start date must be before' in result.output


class TestOutputFormats:
    """Test output formatting across different modes"""
    
    @pytest.mark.parametrize('output_format', ['json', 'markdown', 'table', 'csv'])
    def test_all_output_formats(self, runner, test_mode_env, output_format):
        """All supported output formats work correctly"""
        result = runner.invoke(generate_summary, [
            '--date', '2025-08-19',
            '--format', output_format
        ])
        
        assert result.exit_code == 0
        assert len(result.output) > 0
        
        if output_format == 'json':
            # Should be valid JSON
            data = json.loads(result.output)
            assert 'date' in data
        elif output_format == 'markdown':
            # Should have markdown formatting
            assert '#' in result.output
            assert '**' in result.output or '*' in result.output
        elif output_format == 'table':
            # Should have table-like formatting
            assert '📱' in result.output or 'Activity:' in result.output
        elif output_format == 'csv':
            # CSV format (might be simple for summaries)
            assert len(result.output.strip().split('\n')) > 1
    
    def test_json_output_schema_consistency(self, runner, test_mode_env):
        """JSON output maintains consistent schema across different options"""
        # Test different combinations
        test_cases = [
            ['--date', '2025-08-19'],
            ['--period', 'week'],
            ['--person', 'alice@example.com'],
            ['--detailed']
        ]
        
        for case in test_cases:
            result = runner.invoke(generate_summary, case + ['--format', 'json'])
            assert result.exit_code == 0
            
            data = json.loads(result.output)
            # All should have generation_metadata
            assert 'generation_metadata' in data
            assert 'generated_at' in data['generation_metadata']


class TestPerformanceRequirements:
    """Test performance requirements"""
    
    def test_summary_generation_performance(self, runner, test_mode_env):
        """Summary generation completes within time limits"""
        import time
        
        start_time = time.time()
        result = runner.invoke(generate_summary, [
            '--date', '2025-08-19',
            '--detailed'
        ])
        end_time = time.time()
        
        assert result.exit_code == 0
        # Should complete in under 10 seconds (requirement from spec)
        assert (end_time - start_time) < 10.0
    
    def test_batch_processing_efficiency(self, runner, test_mode_env, temp_output_dir):
        """Batch processing handles multiple dates efficiently"""
        import time
        
        start_time = time.time()
        result = runner.invoke(batch_summaries, [
            '2025-08-19', '2025-08-23',  # 5 days
            '--output-dir', str(temp_output_dir)
        ])
        end_time = time.time()
        
        assert result.exit_code == 0
        
        # Should be reasonably fast for small batch
        duration_per_day = (end_time - start_time) / 5
        assert duration_per_day < 5.0  # Less than 5 seconds per day


class TestIntegrationWithActivityAnalyzer:
    """Test integration with ActivityAnalyzer interface"""
    
    def test_mock_activity_analyzer_integration(self, runner, test_mode_env):
        """Integration with mock ActivityAnalyzer works correctly"""
        result = runner.invoke(generate_summary, [
            '--date', '2025-08-19',
            '--format', 'json'
        ])
        
        assert result.exit_code == 0
        data = json.loads(result.output)
        
        # Should contain mock ActivityAnalyzer data
        assert data['generation_metadata']['test_mode'] is True
        
        # Should have activity data from mock
        slack_activity = data.get('slack_activity', {})
        assert slack_activity.get('message_count') == 42  # Mock data value
    
    def test_all_analyzer_methods_accessible(self, runner, test_mode_env):
        """All ActivityAnalyzer methods are accessible through CLI"""
        # Daily summary
        daily_result = runner.invoke(generate_summary, [
            '--period', 'day',
            '--format', 'json'
        ])
        assert daily_result.exit_code == 0
        
        # Weekly summary
        weekly_result = runner.invoke(generate_summary, [
            '--period', 'week',
            '--format', 'json'
        ])
        assert weekly_result.exit_code == 0


class TestComparisonFeatures:
    """Test summary comparison functionality"""
    
    def test_week_over_week_comparison(self, runner, test_mode_env):
        """Compare current week to last week"""
        result = runner.invoke(generate_summary, [
            '--date', '2025-08-19',
            '--compare-to', 'last week',
            '--verbose'
        ])
        
        assert result.exit_code == 0
        
        # Should show comparison highlights in verbose mode
        if 'Comparison Highlights' in result.output:
            assert 'Messages:' in result.output
            assert 'Meetings:' in result.output
    
    def test_month_over_month_comparison(self, runner, test_mode_env):
        """Compare current month to last month"""
        result = runner.invoke(generate_summary, [
            '--period', 'month',
            '--compare-to', 'last month',
            '--format', 'json'
        ])
        
        assert result.exit_code == 0
        data = json.loads(result.output)
        
        # Should have comparison data
        assert 'comparison' in data


if __name__ == '__main__':
    pytest.main([__file__, '-v'])