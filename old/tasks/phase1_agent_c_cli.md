# Agent C: CLI Tools & Integration - Phase 1 Completion

**Date Created**: 2025-08-19  
**Owner**: Agent C (CLI Integration Team)  
**Status**: PENDING  
**Estimated Time**: 3 days (24 hours) - Updated based on dependency analysis  
**Dependencies**: Agent A (Query Engines) ⚠️ NEEDS INTERFACES, Agent B (Calendar & Statistics) ⚠️ NEEDS INTERFACES

## CRITICAL FIXES REQUIRED (From Architecture Review)

### Fix 1: Missing Foundation Modules - BLOCKER
- **Problem**: Agent A & B modules don't exist yet (`src/queries/time_queries.py`, `src/calendar/availability.py`)
- **Solution**: Create abstract interfaces first, implement stubs for parallel development
- **Timeline**: Add 1 day for interface creation

### Fix 2: Inconsistent Error Handling
- **Problem**: Three different error handling approaches across CLI tools
- **Solution**: Create unified error framework in `src/cli/errors.py`
- **Impact**: Consistent user experience across all tools

### Fix 3: Authentication Bypass Issue
- **Problem**: Test mode doesn't propagate to CLI operations
- **Solution**: Add test mode support to all CLI tools
- **Security**: Ensure development mode works without production credentials

## Executive Summary

Create user-facing CLI tools that integrate all Phase 1 modules into a cohesive interface. These tools provide immediate value by making search, calendar coordination, and statistics accessible through intuitive command-line interfaces.

**Core Philosophy**: Production-ready CLI tools with excellent UX - clear help text, multiple output formats, error handling, and integration with all Phase 1 components.

## Module Architecture

### Relevant Files for CLI Integration

**Read for Context:**
- `tools/search_cli.py` - Existing search CLI patterns and structure
- `tools/manage_archives.py` - CLI argument parsing and output formatting
- `src/queries/time_queries.py` - Time query engine APIs (from Agent A)
- `src/queries/person_queries.py` - Person query engine APIs (from Agent A)
- `src/calendar/availability.py` - Calendar coordination APIs (from Agent B)
- `src/aggregators/basic_stats.py` - Statistics APIs (from Agent B)

**Files to Create:**
- `tools/query_facts.py` - Unified query CLI integrating all engines
- `tools/daily_summary.py` - Daily report generation tool
- `tools/find_slots.py` - Calendar coordination CLI (enhance Agent B's base)
- `src/cli/__init__.py` - CLI utilities module
- `src/cli/formatters.py` - Output formatting utilities  
- `src/cli/interactive.py` - Interactive mode utilities
- `tests/integration/test_query_cli.py` - Query CLI test suite
- `tests/integration/test_daily_summary.py` - Summary tool test suite
- `tests/integration/test_cli_integration.py` - End-to-end CLI tests

**Reference Patterns:**
- `tools/search_cli.py:50-100` - Argument parsing with subcommands
- `tools/manage_archives.py:200-250` - Progress indicators and colored output
- `src/search/database.py:458-500` - Database integration patterns

## Test-Driven Development Plan

### Phase C1: Unified Query CLI (6 hours)

#### Test Acceptance Criteria (Write FIRST)

**File**: `tests/integration/test_query_cli.py`
```python
import pytest
import json
from click.testing import CliRunner
from tools.query_facts import cli as query_cli

class TestQueryFactsCLI:
    """Test unified query CLI tool integration"""
    
    def setup_method(self):
        """Setup test environment"""
        self.runner = CliRunner()
    
    def test_time_query_command(self):
        """CLI handles time-based queries from Agent A"""
        result = self.runner.invoke(query_cli, [
            'time', 'yesterday', 
            '--format', 'json',
            '--source', 'slack'
        ])
        
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert 'results' in data
        assert 'metadata' in data
        assert data['metadata']['query_type'] == 'time'
        assert data['metadata']['time_expression'] == 'yesterday'
    
    def test_person_query_command(self):
        """CLI handles person-based queries from Agent A"""  
        result = self.runner.invoke(query_cli, [
            'person', 'john@example.com',
            '--time-range', 'last week',
            '--format', 'table'
        ])
        
        assert result.exit_code == 0
        assert 'john@example.com' in result.output
        assert 'messages' in result.output
        assert 'meetings' in result.output
    
    def test_structured_query_command(self):
        """CLI handles structured pattern queries from Agent A"""
        result = self.runner.invoke(query_cli, [
            'patterns',
            '--pattern-type', 'todos',
            '--time-range', 'past 7 days',
            '--format', 'csv'
        ])
        
        assert result.exit_code == 0
        assert 'TODO' in result.output.upper()
        assert result.output.count(',') > 0  # CSV format
    
    def test_output_format_support(self):
        """CLI supports multiple output formats"""
        base_cmd = ['time', 'today']
        
        for fmt in ['json', 'csv', 'table', 'markdown']:
            result = self.runner.invoke(query_cli, base_cmd + ['--format', fmt])
            assert result.exit_code == 0
            
            if fmt == 'json':
                json.loads(result.output)  # Should parse as valid JSON
            elif fmt == 'csv':
                assert ',' in result.output
            elif fmt == 'table':
                assert '|' in result.output or '─' in result.output
    
    def test_interactive_mode(self):
        """CLI supports interactive query mode"""
        result = self.runner.invoke(query_cli, ['--interactive'], input='yesterday\nq\n')
        
        assert result.exit_code == 0
        assert 'Query:' in result.output
        assert 'results' in result.output.lower()
    
    def test_error_handling(self):
        """CLI handles errors gracefully"""
        # Invalid time expression
        result = self.runner.invoke(query_cli, ['time', 'invalid-time'])
        assert result.exit_code != 0
        assert 'error' in result.output.lower()
        
        # Invalid person
        result = self.runner.invoke(query_cli, ['person', 'nonexistent@example.com'])
        assert result.exit_code != 0
        assert 'not found' in result.output.lower()
    
    def test_performance_requirements(self):
        """CLI queries meet performance targets"""
        start_time = time.time()
        
        result = self.runner.invoke(query_cli, ['time', 'last week', '--format', 'json'])
        
        end_time = time.time()
        assert (end_time - start_time) < 3.0  # Including CLI overhead
        assert result.exit_code == 0

class TestQueryOutput:
    """Test query result formatting and presentation"""
    
    def test_json_output_schema(self):
        """JSON output follows consistent schema"""
        runner = CliRunner()
        result = runner.invoke(query_cli, ['time', 'today', '--format', 'json'])
        
        data = json.loads(result.output)
        required_fields = ['query', 'results', 'metadata', 'performance']
        assert all(field in data for field in required_fields)
        
        assert 'query_type' in data['metadata']
        assert 'execution_time_ms' in data['performance']
        assert 'result_count' in data['performance']
    
    def test_csv_export_functionality(self):
        """CSV output suitable for external analysis"""
        runner = CliRunner()
        result = runner.invoke(query_cli, ['person', 'john@example.com', '--format', 'csv'])
        
        lines = result.output.strip().split('\n')
        header = lines[0].split(',')
        
        # Should have proper CSV headers
        expected_headers = ['timestamp', 'source', 'type', 'content', 'channel']
        for expected in expected_headers:
            assert any(expected.lower() in h.lower() for h in header)
    
    def test_table_formatting(self):
        """Table output readable and properly aligned"""
        runner = CliRunner()
        result = runner.invoke(query_cli, ['time', 'yesterday', '--format', 'table'])
        
        lines = result.output.split('\n')
        
        # Should have table structure
        assert any('─' in line or '|' in line for line in lines)
        assert any('Time' in line or 'Source' in line for line in lines)
```

#### Implementation Tasks

**Task C1.1: CLI Framework Setup (1.5 hours)**
- Create tools/query_facts.py with click framework
- Implement subcommand structure (time, person, patterns)
- Add global options (format, interactive, verbose)
- Set up logging and error handling

**Task C1.2: Query Engine Integration (2 hours)**
- Integrate Agent A's TimeQueryEngine
- Integrate Agent A's PersonQueryEngine  
- Integrate Agent A's StructuredExtractor
- Add query validation and preprocessing

**Task C1.3: Output Formatting System (1.5 hours)**
- Create src/cli/formatters.py module
- Implement JSON, CSV, table, markdown formatters
- Add proper column alignment and headers
- Create interactive pagination for large results

**Task C1.4: Interactive Mode (1 hour)**
- Implement interactive query session
- Add history and autocomplete (if possible)
- Create help system and command suggestions
- Add session state and context preservation

### Phase C2: Daily Summary & Calendar Tools (6 hours)

#### Test Acceptance Criteria (Write FIRST)

**File**: `tests/integration/test_daily_summary.py`
```python
import pytest
import json
from datetime import date, timedelta
from click.testing import CliRunner
from tools.daily_summary import cli as summary_cli

class TestDailySummaryCLI:
    """Test daily summary generation tool"""
    
    def test_basic_summary_generation(self):
        """Generate daily summary with all activity types"""
        runner = CliRunner()
        result = runner.invoke(summary_cli, [
            '--date', date.today().isoformat(),
            '--format', 'json'
        ])
        
        assert result.exit_code == 0
        data = json.loads(result.output)
        
        required_sections = [
            'date', 'slack_activity', 'calendar_activity', 
            'drive_activity', 'key_highlights', 'statistics'
        ]
        assert all(section in data for section in required_sections)
    
    def test_weekly_summary_generation(self):
        """Generate weekly rollup summary"""
        runner = CliRunner()
        result = runner.invoke(summary_cli, [
            '--period', 'week',
            '--format', 'markdown'
        ])
        
        assert result.exit_code == 0
        assert '# Weekly Summary' in result.output
        assert 'Messages' in result.output
        assert 'Meetings' in result.output
    
    def test_person_focused_summary(self):
        """Generate summary focused on specific person"""
        runner = CliRunner()
        result = runner.invoke(summary_cli, [
            '--person', 'john@example.com',
            '--days', '7'
        ])
        
        assert result.exit_code == 0
        assert 'john@example.com' in result.output
        assert 'activity' in result.output.lower()
    
    def test_scheduled_execution_mode(self):
        """Support scheduled/automated summary generation"""
        runner = CliRunner()
        result = runner.invoke(summary_cli, [
            '--scheduled',
            '--output-file', '/tmp/daily_summary.json'
        ])
        
        assert result.exit_code == 0
        assert 'Summary saved' in result.output
        
        # Verify file was created
        import os
        assert os.path.exists('/tmp/daily_summary.json')

class TestCalendarCoordination:
    """Test enhanced calendar coordination CLI"""
    
    def test_find_slots_command(self):
        """Find free slots with attendee constraints"""
        runner = CliRunner()
        result = runner.invoke(query_cli, [
            'calendar', 'find-slots',
            '--attendees', 'john@example.com,jane@example.com',
            '--duration', '60',
            '--date', date.today().isoformat()
        ])
        
        assert result.exit_code == 0
        assert 'Available slots' in result.output
        assert '60 minutes' in result.output
    
    def test_conflict_checking(self):
        """Check for meeting conflicts"""
        runner = CliRunner()
        result = runner.invoke(query_cli, [
            'calendar', 'check-conflicts',
            '--date', date.today().isoformat(),
            '--attendees', 'john@example.com'
        ])
        
        assert result.exit_code == 0
        # Should show conflicts or "No conflicts found"
        assert 'conflict' in result.output.lower()
    
    def test_availability_report(self):
        """Generate availability report for person/team"""
        runner = CliRunner()
        result = runner.invoke(query_cli, [
            'calendar', 'availability',
            '--person', 'john@example.com',
            '--week', date.today().isoformat()
        ])
        
        assert result.exit_code == 0
        assert 'availability' in result.output.lower()
        assert 'free' in result.output.lower() or 'busy' in result.output.lower()
```

#### Implementation Tasks

**Task C2.1: Daily Summary Tool (2 hours)**
- Create tools/daily_summary.py CLI
- Integrate Agent B's ActivityAnalyzer
- Implement templated summary generation
- Add scheduling and automation support

**Task C2.2: Enhanced Calendar CLI (2 hours)**
- Enhance find_slots.py with Agent B's AvailabilityEngine
- Add interactive slot selection and booking
- Implement conflict checking and validation
- Create availability reporting

**Task C2.3: Output Enhancement (1 hour)**
- Create src/cli/formatters.py with advanced formatting
- Add table rendering with proper alignment
- Implement markdown export for documentation
- Add color coding and visual indicators

**Task C2.4: Integration Testing (1 hour)**
- Create comprehensive end-to-end tests
- Verify integration with all Agent A & B modules
- Test error propagation and handling
- Benchmark performance of combined operations

## Integration Architecture

### Agent A Integration Points
- **TimeQueryEngine**: Integrated via `query_facts.py time` subcommand
- **PersonQueryEngine**: Integrated via `query_facts.py person` subcommand  
- **StructuredExtractor**: Integrated via `query_facts.py patterns` subcommand
- **Error Handling**: Consistent error formatting across all query types

### Agent B Integration Points
- **AvailabilityEngine**: Integrated via calendar coordination commands
- **ConflictDetector**: Used for meeting conflict checking
- **ActivityAnalyzer**: Core engine for daily_summary.py tool
- **Statistical Functions**: Exported via query_facts.py stats subcommand

### Database Integration
- All CLI tools use existing SQLite FTS5 database
- Results maintain source attribution and audit trail
- Performance optimized with proper query planning
- Consistent error handling for database issues

## CLI Tool Specifications

### tools/query_facts.py - Unified Query Interface
```bash
# Time-based queries
python tools/query_facts.py time "yesterday" --format json
python tools/query_facts.py time "last week" --source slack --format table

# Person-based queries  
python tools/query_facts.py person "john@example.com" --time-range "past 7 days"
python tools/query_facts.py person "john@example.com" --activity-summary

# Pattern extraction
python tools/query_facts.py patterns --pattern-type todos --time-range "today"
python tools/query_facts.py patterns --pattern-type mentions --person "jane@example.com"

# Statistics and aggregation
python tools/query_facts.py stats --time-range "last week" --breakdown channel
python tools/query_facts.py stats --person-ranking --time-range "past 30 days"

# Interactive mode
python tools/query_facts.py --interactive
```

### tools/daily_summary.py - Automated Reports
```bash
# Generate daily summary
python tools/daily_summary.py --date 2025-08-19 --format markdown

# Weekly summary 
python tools/daily_summary.py --period week --person "john@example.com"

# Scheduled execution
python tools/daily_summary.py --scheduled --output-file reports/daily_$(date +%Y%m%d).json

# Comparative summary
python tools/daily_summary.py --compare-to "last week" --format table
```

### Enhanced tools/find_slots.py - Calendar Coordination
```bash
# Find meeting slots
python tools/find_slots.py --attendees "john@example.com,jane@example.com" --duration 60

# Check conflicts
python tools/find_slots.py check-conflicts --date 2025-08-19 --person "john@example.com"

# Availability report
python tools/find_slots.py availability --person "john@example.com" --week 2025-08-19

# Interactive scheduling
python tools/find_slots.py --interactive
```

## Test Acceptance Criteria

### CLI Functionality Tests (Write FIRST)

**File**: `tests/integration/test_cli_integration.py`
```python
import pytest
import json
import tempfile
from click.testing import CliRunner
from tools.query_facts import cli as query_cli
from tools.daily_summary import cli as summary_cli

class TestCLIIntegration:
    """Test end-to-end CLI integration across all modules"""
    
    def test_full_workflow_integration(self):
        """Complete workflow: query → summarize → coordinate"""
        runner = CliRunner()
        
        # Step 1: Query recent activity
        query_result = runner.invoke(query_cli, [
            'time', 'yesterday', '--format', 'json'
        ])
        assert query_result.exit_code == 0
        
        # Step 2: Generate summary
        summary_result = runner.invoke(summary_cli, [
            '--date', 'yesterday', '--format', 'json'
        ])
        assert summary_result.exit_code == 0
        
        # Step 3: Find calendar slots
        slots_result = runner.invoke(query_cli, [
            'calendar', 'find-slots', '--duration', '30'
        ])
        assert slots_result.exit_code == 0
        
        # All steps should complete successfully
        assert all(result.exit_code == 0 for result in [query_result, summary_result, slots_result])
    
    def test_cross_module_data_consistency(self):
        """Data consistency between different CLI tools"""
        runner = CliRunner()
        
        # Get person activity via query tool
        person_query = runner.invoke(query_cli, [
            'person', 'john@example.com', '--format', 'json'
        ])
        person_data = json.loads(person_query.output)
        
        # Get same person in daily summary
        summary_query = runner.invoke(summary_cli, [
            '--person', 'john@example.com', '--format', 'json'
        ])
        summary_data = json.loads(summary_query.output)
        
        # Message counts should be consistent
        assert person_data['message_count'] == summary_data['slack_activity']['message_count']
    
    def test_performance_across_tools(self):
        """All CLI tools meet performance requirements"""
        runner = CliRunner()
        
        test_commands = [
            ['time', 'last week'],
            ['person', 'john@example.com'],
            ['patterns', '--pattern-type', 'todos']
        ]
        
        for cmd in test_commands:
            start_time = time.time()
            result = runner.invoke(query_cli, cmd)
            end_time = time.time()
            
            assert result.exit_code == 0
            assert (end_time - start_time) < 5.0  # 5-second limit including overhead
    
    def test_help_and_documentation(self):
        """CLI provides comprehensive help"""
        runner = CliRunner()
        
        # Main help
        result = runner.invoke(query_cli, ['--help'])
        assert result.exit_code == 0
        assert 'Usage:' in result.output
        
        # Subcommand help
        for subcmd in ['time', 'person', 'patterns', 'calendar']:
            result = runner.invoke(query_cli, [subcmd, '--help'])
            assert result.exit_code == 0
            assert subcmd in result.output.lower()
```

## Implementation Tasks

### Task C1: Unified Query CLI (6 hours)

**Task C1.1: CLI Framework (1.5 hours)**
- Create tools/query_facts.py with click framework
- Implement subcommand structure (time, person, patterns, calendar, stats)
- Add global options (format, interactive, verbose, config)
- Set up comprehensive help system

**Task C1.2: Query Engine Integration (2 hours)**
- Integrate TimeQueryEngine from Agent A
- Integrate PersonQueryEngine from Agent A
- Integrate StructuredExtractor from Agent A  
- Add query preprocessing and validation

**Task C1.3: Output Formatting (1.5 hours)**
- Create src/cli/formatters.py module
- Implement JSON, CSV, table, markdown formatters
- Add proper column alignment and header formatting
- Create pagination for large result sets

**Task C1.4: Interactive Mode (1 hour)**
- Implement interactive query session
- Add command history and basic autocomplete
- Create contextual help and suggestions
- Add session state persistence

### Task C2: Daily Summary Tool (3 hours)

**Task C2.1: Summary Generator Core (1.5 hours)**
- Create tools/daily_summary.py CLI
- Integrate Agent B's ActivityAnalyzer
- Implement template-based summary generation
- Add configurable summary sections

**Task C2.2: Scheduling Integration (1 hour)**
- Add scheduled execution support (cron-friendly)
- Implement file output and delivery options
- Create summary comparison functionality
- Add alerting for significant changes

**Task C2.3: Calendar Integration Enhancement (30 minutes)**
- Enhance existing find_slots.py with Agent B's engines
- Add interactive slot selection workflow
- Implement conflict checking commands
- Create availability reporting

### Task C3: CLI Utilities & Polish (3 hours)

**Task C3.1: Shared CLI Utilities (1 hour)**
- Create src/cli/interactive.py for shared interactive features
- Implement progress indicators and status updates
- Add colored output and visual formatting
- Create consistent error reporting

**Task C3.2: Integration Testing (1.5 hours)**
- Write comprehensive integration test suite
- Test all CLI tools work together correctly
- Verify data consistency across tools
- Benchmark performance of complex operations

**Task C3.3: Documentation & Help (30 minutes)**
- Add comprehensive help text for all commands
- Create usage examples and common workflows
- Add troubleshooting guide for CLI issues
- Document performance characteristics

## Integration Requirements

### Agent Dependencies
- **Agent A**: Must provide working query engines with stable APIs
- **Agent B**: Must provide calendar and statistics engines with performance guarantees
- **Agent D**: CLI tools should work with migration system

### Database Requirements
- Use existing SQLite FTS5 database from Stage 3
- Maintain read-only access patterns (no database modifications)
- Handle database lock contention gracefully
- Support concurrent CLI tool usage

### Configuration Integration
- Use existing config system from Stage 1a
- Support all configuration options and overrides
- Validate configuration before operations
- Provide clear error messages for config issues

## Success Criteria

### CLI Functionality Validation ✅
- [ ] All query types accessible via intuitive CLI commands
- [ ] Output formats work correctly (JSON, CSV, table, markdown)
- [ ] Interactive mode provides good user experience
- [ ] Error handling prevents crashes and provides helpful messages

### Integration Validation ✅
- [ ] Agent A query engines properly integrated
- [ ] Agent B calendar/statistics engines properly integrated
- [ ] Cross-module data consistency maintained
- [ ] Performance targets met for all operations

### User Experience Validation ✅
- [ ] Help system comprehensive and useful
- [ ] CLI follows UNIX conventions and best practices
- [ ] Output formatting readable and professional
- [ ] Tools provide immediate value for Phase 1 objectives

## Performance Requirements

- Query operations complete in <3 seconds (including CLI overhead)
- Summary generation completes in <10 seconds
- Calendar operations complete in <5 seconds
- Memory usage <150MB for typical operations
- Graceful handling of large result sets

## Delivery Checklist

Before marking complete:
- [ ] All CLI tools functional and tested
- [ ] Integration with Agent A & B modules working
- [ ] Help documentation comprehensive
- [ ] Performance requirements met
- [ ] Error handling prevents user frustration
- [ ] Output formatting professional and useful

---

**Contact Agent C Team Lead for questions or clarification**
**Final Integration**: Agent D will test all CLI tools as part of end-to-end validation