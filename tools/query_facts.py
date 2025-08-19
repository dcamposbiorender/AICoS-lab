#!/usr/bin/env python3
"""
Unified Query CLI Tool - Agent C Implementation

Integrates all Phase 1 query engines into a cohesive command-line interface.
Provides time-based queries, person queries, pattern extraction, and statistics
with multiple output formats and excellent user experience.

Key Features:
- Time-based queries with natural language expressions
- Person-based queries with activity summaries  
- Pattern extraction (TODOs, mentions, deadlines)
- Calendar coordination and availability queries
- Statistics and aggregation queries
- Multiple output formats (JSON, CSV, table, markdown)
- Interactive mode with command history
- Graceful degradation when modules unavailable
- AICOS_TEST_MODE support for development

Usage:
    python tools/query_facts.py time "yesterday" --format json
    python tools/query_facts.py person "john@example.com" --time-range "last week"
    python tools/query_facts.py patterns --pattern-type todos
    python tools/query_facts.py calendar find-slots --attendees "alice@example.com,bob@example.com"
    python tools/query_facts.py --interactive

Integration:
- Uses Agent A query engines via abstract interfaces
- Uses Agent B calendar and statistics engines  
- Falls back to mock implementations in test mode
- Consistent error handling across all operations

References:
- tasks/phase1_agent_c_cli.md lines 398-448 for CLI specifications
- src/cli/interfaces.py for Agent A & B integration
- src/cli/errors.py for unified error handling
"""

import sys
import os
import time
import json
from pathlib import Path
from typing import Optional, List, Dict, Any

import click

# Add project root to Python path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import CLI utilities
from src.cli.errors import (
    CLIError, QueryError, ValidationError, DependencyError,
    handle_cli_error, check_test_mode, validate_date_range
)
from src.cli.interfaces import (
    get_query_engine, get_person_engine, get_pattern_extractor,
    get_availability_engine, get_activity_analyzer
)
from src.cli.formatters import (
    format_query_results, format_statistics, format_calendar_slots
)
from src.cli.interactive import (
    InteractiveSession, confirm_action, show_progress, StatusIndicator
)

# Version and metadata
__version__ = "1.0.0"
__author__ = "Agent C - CLI Integration Team"

# Global CLI context
cli_context = {
    'test_mode': check_test_mode(),
    'verbose': False,
    'start_time': time.time()
}


@click.group(invoke_without_command=True)
@click.option('--interactive', is_flag=True, 
              help='Start interactive query session')
@click.option('--format', 'output_format',
              type=click.Choice(['json', 'csv', 'table', 'markdown']), 
              default='table',
              help='Output format (default: table)')
@click.option('--verbose', is_flag=True,
              help='Show detailed metadata and performance info')
@click.option('--config', 'config_file', type=click.Path(exists=True),
              help='Configuration file path')
@click.version_option(version=__version__, prog_name='query-facts')
@click.pass_context
def cli(ctx, interactive, output_format, verbose, config_file):
    """
    AI Chief of Staff Unified Query Interface
    
    Query your organizational data across Slack, Calendar, Drive, and Employee records
    using natural language expressions and structured queries.
    
    \b
    Examples:
        query_facts.py time "yesterday" --format json
        query_facts.py person "alice@example.com" --time-range "last week"  
        query_facts.py patterns --pattern-type todos --time-range "today"
        query_facts.py calendar find-slots --attendees "alice@example.com,bob@example.com"
        query_facts.py stats --time-range "last week" --breakdown channel
        query_facts.py --interactive
    
    \b
    Supported Time Expressions:
        "today", "yesterday", "last week", "this week"
        "last month", "this month", "past 7 days"
        "2025-08-19", "August 2025"
    
    \b
    Environment Variables:
        AICOS_TEST_MODE=true    Use mock data for testing
        AICOS_CONFIG_DIR        Custom configuration directory
    """
    ctx.ensure_object(dict)
    ctx.obj['output_format'] = output_format
    ctx.obj['verbose'] = verbose
    ctx.obj['config_file'] = config_file
    
    cli_context['verbose'] = verbose
    
    # Show test mode warning
    if cli_context['test_mode'] and not ctx.invoked_subcommand:
        click.echo(f"🧪 {click.style('TEST MODE ACTIVE', fg='yellow', bold=True)} - Using mock data")
        click.echo()
    
    # If no subcommand and interactive mode requested, start interactive session
    if ctx.invoked_subcommand is None and interactive:
        start_interactive_mode(ctx)
    elif ctx.invoked_subcommand is None:
        # Show help if no command provided
        click.echo(ctx.get_help())


@cli.command()
@click.argument('time_expression')
@click.option('--source', type=click.Choice(['slack', 'calendar', 'drive', 'employees']),
              help='Filter results by source type')
@click.option('--limit', type=int, default=10,
              help='Maximum number of results (default: 10)')
@click.option('--include-metadata', is_flag=True,
              help='Include detailed metadata in results')
@click.pass_context
def time(ctx, time_expression, source, limit, include_metadata):
    """
    Query data by time expressions
    
    \b
    Time Expression Examples:
        "today"           - Today's activity
        "yesterday"       - Yesterday's activity  
        "last week"       - Past week's activity
        "this month"      - Current month's activity
        "past 7 days"     - Last 7 days
        "2025-08-19"      - Specific date
        
    \b
    Examples:
        query_facts.py time "yesterday" --source slack
        query_facts.py time "last week" --format json --limit 20
        query_facts.py time "today" --include-metadata
    """
    try:
        with StatusIndicator("Executing time-based query"):
            query_engine = get_query_engine()
            
            # Validate time expression
            if hasattr(query_engine, 'validate_time_expression'):
                if not query_engine.validate_time_expression(time_expression):
                    raise ValidationError(
                        f"Invalid time expression: {time_expression}",
                        suggestion="Use expressions like 'today', 'yesterday', 'last week', or specific dates like '2025-08-19'"
                    )
            
            # Execute query
            result = query_engine.query(
                time_expression=time_expression,
                source=source,
                limit=limit,
                include_metadata=include_metadata
            )
            
            # Format and display results
            formatted_output = format_query_results(
                result, 
                ctx.obj['output_format'],
                verbose=ctx.obj['verbose'] or include_metadata,
                query=time_expression
            )
            
            click.echo(formatted_output)
            
            # Show performance info in verbose mode
            if ctx.obj['verbose'] and hasattr(result, 'performance'):
                perf = result.performance
                exec_time = perf.get('execution_time_ms', 0)
                result_count = perf.get('result_count', len(result.results) if hasattr(result, 'results') else 0)
                
                click.echo(f"\n📊 Query executed in {exec_time}ms, returned {result_count} results", err=True)
            
    except Exception as e:
        exit_code = handle_cli_error(e, quiet=False, verbose=ctx.obj['verbose'])
        sys.exit(exit_code)


@cli.command()
@click.argument('person_id')
@click.option('--time-range', help='Time range for person activity (e.g., "last week")')
@click.option('--activity-summary', is_flag=True,
              help='Include aggregated activity summary')
@click.option('--include-interactions', is_flag=True,
              help='Include interaction details')
@click.pass_context
def person(ctx, person_id, time_range, activity_summary, include_interactions):
    """
    Query activity for a specific person
    
    \b
    Person ID Examples:
        "alice@example.com"    - Email address
        "U123456789"           - Slack user ID
        "Alice Johnson"        - Display name
        
    \b
    Examples:
        query_facts.py person "alice@example.com" --time-range "last week"
        query_facts.py person "bob@company.com" --activity-summary
        query_facts.py person "charlie@team.com" --include-interactions --format json
    """
    try:
        with StatusIndicator(f"Querying activity for {person_id}"):
            person_engine = get_person_engine()
            
            # Execute person query
            result = person_engine.query(
                person_id=person_id,
                time_range=time_range,
                include_activity_summary=activity_summary,
                include_interactions=include_interactions
            )
            
            # Format and display results
            formatted_output = format_query_results(
                result,
                ctx.obj['output_format'],
                verbose=ctx.obj['verbose'],
                query=person_id
            )
            
            click.echo(formatted_output)
            
            # Show activity summary if requested and available
            if activity_summary and hasattr(result, 'metadata') and 'activity_summary' in result.metadata:
                summary = result.metadata['activity_summary']
                click.echo(f"\n📈 {click.style('Activity Summary:', fg='blue', bold=True)}")
                click.echo(f"  Messages: {summary.get('message_count', 0)}")
                click.echo(f"  Meetings: {summary.get('meeting_count', 0)}")
                if summary.get('channels'):
                    channels = ', '.join(summary['channels'][:3])
                    click.echo(f"  Active channels: {channels}")
                    
    except Exception as e:
        exit_code = handle_cli_error(e, quiet=False, verbose=ctx.obj['verbose'])
        sys.exit(exit_code)


@cli.command()
@click.option('--pattern-type', 
              type=click.Choice(['todos', 'mentions', 'deadlines', 'decisions', 'action_items']),
              required=True,
              help='Type of pattern to extract')
@click.option('--time-range', help='Time range for pattern extraction')
@click.option('--person', help='Filter patterns by person')
@click.option('--limit', type=int, default=20,
              help='Maximum number of patterns to extract (default: 20)')
@click.pass_context
def patterns(ctx, pattern_type, time_range, person, limit):
    """
    Extract structured patterns from conversations
    
    \b
    Pattern Types:
        todos        - TODO items and task mentions
        mentions     - @mentions and references
        deadlines    - Deadline and due date mentions
        decisions    - Decision points and outcomes
        action_items - Action items and assignments
        
    \b
    Examples:
        query_facts.py patterns --pattern-type todos --time-range "today"
        query_facts.py patterns --pattern-type mentions --person "alice@example.com"
        query_facts.py patterns --pattern-type deadlines --format json
    """
    try:
        with StatusIndicator(f"Extracting {pattern_type} patterns"):
            extractor = get_pattern_extractor()
            
            # Execute pattern extraction
            result = extractor.extract_patterns(
                pattern_type=pattern_type,
                time_range=time_range,
                person=person,
                limit=limit
            )
            
            # Format and display results
            formatted_output = format_query_results(
                result,
                ctx.obj['output_format'],
                verbose=ctx.obj['verbose'],
                query=f"{pattern_type} patterns"
            )
            
            click.echo(formatted_output)
            
            # Show pattern statistics
            if ctx.obj['verbose'] and hasattr(result, 'results'):
                pattern_count = len(result.results)
                click.echo(f"\n📋 Found {pattern_count} {pattern_type} patterns", err=True)
                
                # Show pattern breakdown if available
                if hasattr(result, 'metadata') and 'pattern_breakdown' in result.metadata:
                    breakdown = result.metadata['pattern_breakdown']
                    click.echo("Pattern breakdown:", err=True)
                    for key, value in breakdown.items():
                        click.echo(f"  {key}: {value}", err=True)
                        
    except Exception as e:
        exit_code = handle_cli_error(e, quiet=False, verbose=ctx.obj['verbose'])
        sys.exit(exit_code)


@cli.group()
@click.pass_context
def calendar(ctx):
    """
    Calendar coordination and availability queries
    
    \b
    Subcommands:
        find-slots      - Find free time slots for meetings
        check-conflicts - Check for scheduling conflicts
        availability    - Show availability for person/team
        
    \b
    Examples:
        query_facts.py calendar find-slots --attendees "alice@example.com,bob@example.com"
        query_facts.py calendar check-conflicts --attendees "team@company.com" --date today
        query_facts.py calendar availability --person "alice@example.com" --week "2025-08-19"
    """
    pass


@calendar.command('find-slots')
@click.option('--attendees', required=True,
              help='Comma-separated list of attendee emails')
@click.option('--duration', type=int, default=60,
              help='Meeting duration in minutes (default: 60)')
@click.option('--date', help='Specific date to search (YYYY-MM-DD)')
@click.option('--date-range', help='Date range to search (YYYY-MM-DD,YYYY-MM-DD)')
@click.pass_context
def find_slots(ctx, attendees, duration, date, date_range):
    """
    Find free time slots for meeting with specified attendees
    
    \b
    Examples:
        query_facts.py calendar find-slots --attendees "alice@example.com,bob@example.com" --duration 30
        query_facts.py calendar find-slots --attendees "team@company.com" --date "2025-08-20"
        query_facts.py calendar find-slots --attendees "alice@example.com" --date-range "2025-08-20,2025-08-22"
    """
    try:
        attendee_list = [email.strip() for email in attendees.split(',')]
        
        # Parse date range
        search_range = None
        if date_range:
            start_date, end_date = validate_date_range(*date_range.split(','))
            search_range = (start_date, end_date)
        elif date:
            start_date, _ = validate_date_range(date, None)
            search_range = (start_date, start_date)
        
        with StatusIndicator(f"Finding {duration}-minute slots for {len(attendee_list)} attendees"):
            availability_engine = get_availability_engine()
            
            result = availability_engine.find_free_slots(
                attendees=attendee_list,
                duration=duration,
                date_range=search_range
            )
            
            # Format and display results
            formatted_output = format_calendar_slots(result, ctx.obj['output_format'])
            click.echo(formatted_output)
            
            # Show summary in verbose mode
            if ctx.obj['verbose']:
                slots_found = len(result.get('available_slots', []))
                click.echo(f"\n🕒 Found {slots_found} available slots", err=True)
                
    except Exception as e:
        exit_code = handle_cli_error(e, quiet=False, verbose=ctx.obj['verbose'])
        sys.exit(exit_code)


@calendar.command('check-conflicts')
@click.option('--attendees', required=True,
              help='Comma-separated list of attendee emails')
@click.option('--start-time', required=True,
              help='Proposed meeting start time (ISO format or YYYY-MM-DD HH:MM)')
@click.option('--duration', type=int, default=60,
              help='Meeting duration in minutes (default: 60)')
@click.pass_context
def check_conflicts(ctx, attendees, start_time, duration):
    """
    Check for scheduling conflicts at proposed meeting time
    
    \b
    Examples:
        query_facts.py calendar check-conflicts --attendees "alice@example.com,bob@example.com" \\
            --start-time "2025-08-20T14:00:00" --duration 30
        query_facts.py calendar check-conflicts --attendees "team@company.com" \\
            --start-time "2025-08-20 10:00" --duration 60
    """
    try:
        attendee_list = [email.strip() for email in attendees.split(',')]
        
        with StatusIndicator("Checking for scheduling conflicts"):
            availability_engine = get_availability_engine()
            
            result = availability_engine.check_conflicts(
                attendees=attendee_list,
                start_time=start_time,
                duration=duration
            )
            
            # Display conflict results
            if ctx.obj['output_format'] == 'json':
                click.echo(json.dumps(result, indent=2, default=str))
            else:
                conflicts_found = result.get('conflicts_found', False)
                
                if conflicts_found:
                    click.echo(f"⚠️ {click.style('Conflicts detected!', fg='red', bold=True)}")
                    
                    conflict_details = result.get('conflict_details', [])
                    for conflict in conflict_details:
                        attendee = conflict.get('attendee', 'Unknown')
                        conflict_time = conflict.get('conflict_time', 'Unknown')
                        click.echo(f"  • {attendee}: Conflict at {conflict_time}")
                else:
                    click.echo(f"✅ {click.style('No conflicts detected', fg='green', bold=True)}")
                
                click.echo(f"\nProposed meeting:")
                click.echo(f"  Time: {start_time}")
                click.echo(f"  Duration: {duration} minutes")
                click.echo(f"  Attendees: {', '.join(attendee_list)}")
                
    except Exception as e:
        exit_code = handle_cli_error(e, quiet=False, verbose=ctx.obj['verbose'])
        sys.exit(exit_code)


@calendar.command('availability')
@click.option('--person', required=True, help='Person email or ID')
@click.option('--date', help='Specific date (YYYY-MM-DD)')
@click.option('--week', help='Week starting date (YYYY-MM-DD)')
@click.pass_context
def availability(ctx, person, date, week):
    """
    Show availability for a person or team
    
    \b
    Examples:
        query_facts.py calendar availability --person "alice@example.com" --date "2025-08-20"
        query_facts.py calendar availability --person "bob@company.com" --week "2025-08-19"
    """
    try:
        # Note: This is a placeholder - actual implementation would depend on
        # Agent B's AvailabilityEngine having an availability report method
        click.echo(f"📅 Availability for {person}")
        
        if date:
            click.echo(f"Date: {date}")
        elif week:
            click.echo(f"Week starting: {week}")
        else:
            click.echo("Today")
        
        click.echo("\nThis feature requires Agent B implementation.")
        
    except Exception as e:
        exit_code = handle_cli_error(e, quiet=False, verbose=ctx.obj['verbose'])
        sys.exit(exit_code)


@cli.command()
@click.option('--time-range', required=True,
              help='Time range for statistics (e.g., "last week", "this month")')
@click.option('--breakdown', 
              type=click.Choice(['channel', 'person', 'source', 'time']),
              help='Breakdown statistics by category')
@click.option('--person-ranking', is_flag=True,
              help='Show person activity rankings')
@click.option('--include-trends', is_flag=True,
              help='Include trend analysis')
@click.pass_context
def stats(ctx, time_range, breakdown, person_ranking, include_trends):
    """
    Generate activity statistics and aggregations
    
    \b
    Examples:
        query_facts.py stats --time-range "last week" --breakdown channel
        query_facts.py stats --time-range "this month" --person-ranking
        query_facts.py stats --time-range "past 30 days" --include-trends --format json
    """
    try:
        with StatusIndicator(f"Generating statistics for {time_range}"):
            activity_analyzer = get_activity_analyzer()
            
            result = activity_analyzer.get_statistics(
                time_range=time_range,
                breakdown=breakdown,
                person_ranking=person_ranking,
                include_trends=include_trends
            )
            
            # Format and display statistics
            formatted_output = format_statistics(
                result,
                ctx.obj['output_format'],
                detailed=ctx.obj['verbose']
            )
            
            click.echo(formatted_output)
            
    except Exception as e:
        exit_code = handle_cli_error(e, quiet=False, verbose=ctx.obj['verbose'])
        sys.exit(exit_code)


def start_interactive_mode(ctx):
    """Start interactive query session"""
    session = InteractiveSession(
        title="AI Chief of Staff - Interactive Query Mode",
        prompt="Query> ",
        history_file="~/.aicos/query_history.txt"
    )
    
    # Register special commands
    session.register_command(
        'stats', 
        lambda: click.echo("Use 'stats --time-range \"last week\"' for statistics"),
        'Show usage for statistics commands'
    )
    
    click.echo(f"Output format: {click.style(ctx.obj['output_format'], fg='cyan')}")
    if cli_context['test_mode']:
        click.echo(f"Mode: {click.style('TEST MODE - Using mock data', fg='yellow')}")
    click.echo()
    
    try:
        for query_input in session.start():
            try:
                # Parse and execute query
                handle_interactive_query(query_input, ctx)
                
            except Exception as e:
                handle_cli_error(e, quiet=False, verbose=ctx.obj['verbose'])
                
    except KeyboardInterrupt:
        click.echo("\nGoodbye!")


def handle_interactive_query(query_input: str, ctx):
    """Handle queries in interactive mode"""
    parts = query_input.strip().split()
    if not parts:
        return
    
    command = parts[0].lower()
    
    # Route to appropriate command handler
    if command in ['time', 'today', 'yesterday']:
        if command in ['today', 'yesterday']:
            time_expression = command
        else:
            time_expression = ' '.join(parts[1:]) if len(parts) > 1 else 'today'
        
        # Execute time query
        try:
            query_engine = get_query_engine()
            result = query_engine.query(time_expression=time_expression, limit=5)
            
            formatted_output = format_query_results(
                result, ctx.obj['output_format'], query=time_expression
            )
            click.echo(formatted_output)
        except Exception as e:
            click.echo(f"Query error: {e}", err=True)
    
    elif command == 'person' and len(parts) > 1:
        person_id = parts[1]
        try:
            person_engine = get_person_engine()
            result = person_engine.query(person_id=person_id)
            
            formatted_output = format_query_results(
                result, ctx.obj['output_format'], query=person_id
            )
            click.echo(formatted_output)
        except Exception as e:
            click.echo(f"Person query error: {e}", err=True)
    
    elif command == 'patterns' and len(parts) > 1:
        pattern_type = parts[1]
        try:
            extractor = get_pattern_extractor()
            
            # Check if pattern type is supported
            if hasattr(extractor, 'get_supported_patterns'):
                supported = extractor.get_supported_patterns()
                if pattern_type not in supported:
                    click.echo(f"Unsupported pattern type. Supported: {', '.join(supported)}")
                    return
            
            result = extractor.extract_patterns(pattern_type=pattern_type)
            
            formatted_output = format_query_results(
                result, ctx.obj['output_format'], query=f"{pattern_type} patterns"
            )
            click.echo(formatted_output)
        except Exception as e:
            click.echo(f"Pattern extraction error: {e}", err=True)
    
    else:
        # Try as general search query
        click.echo(f"Unrecognized command: {command}")
        click.echo("Available commands: time <expression>, person <email>, patterns <type>")


if __name__ == '__main__':
    try:
        cli()
    except KeyboardInterrupt:
        click.echo("\nOperation cancelled by user", err=True)
        sys.exit(130)
    except Exception as e:
        exit_code = handle_cli_error(e, quiet=False, verbose=cli_context['verbose'])
        sys.exit(exit_code)