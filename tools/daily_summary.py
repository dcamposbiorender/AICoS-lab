#!/usr/bin/env python3
"""
Daily Summary CLI Tool - Agent C Implementation

Automated report generation tool that creates daily and weekly summaries
of organizational activity across all data sources. Integrates with Agent B's
ActivityAnalyzer for comprehensive analysis and insights.

Key Features:
- Daily activity summaries with key highlights
- Weekly rollup summaries with trends
- Person-focused summaries and activity analysis
- Scheduled execution support for automation
- Comparative analysis (compare to previous periods)
- Multiple output formats with professional presentation
- Configurable summary sections and detail levels

Usage:
    python tools/daily_summary.py --date 2025-08-19 --format markdown
    python tools/daily_summary.py --period week --person "alice@example.com"
    python tools/daily_summary.py --scheduled --output-file reports/daily.json
    python tools/daily_summary.py --compare-to "last week" --format table

Integration:
- Uses Agent B's ActivityAnalyzer for core analysis
- Falls back to mock implementation in test mode
- Supports AICOS_TEST_MODE for development
- Consistent error handling and user experience

References:
- tasks/phase1_agent_c_cli.md lines 419-432 for CLI specifications  
- src/cli/interfaces.py for Agent B integration
- src/cli/formatters.py for summary formatting
"""

import sys
import os
import json
import csv
from pathlib import Path
from datetime import datetime, timedelta, date
from typing import Optional, Dict, Any, List

import click

# Add project root to Python path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import CLI utilities
from src.cli.errors import (
    CLIError, ValidationError, handle_cli_error, check_test_mode, validate_date_range
)
from src.cli.interfaces import get_activity_analyzer
from src.cli.formatters import format_summary
from src.cli.interactive import StatusIndicator, confirm_action, format_duration

# Version and metadata
__version__ = "1.0.0"
__author__ = "Agent C - CLI Integration Team"


@click.command()
@click.option('--date', 'date_param', type=str, default=None,
              help='Specific date for summary (YYYY-MM-DD, default: yesterday)')
@click.option('--period', type=click.Choice(['day', 'week', 'month']),
              default='day', help='Summary period (default: day)')
@click.option('--person', help='Focus summary on specific person (email)')
@click.option('--format', 'output_format',
              type=click.Choice(['json', 'markdown', 'table', 'csv']),
              default='table', help='Output format (default: table)')
@click.option('--output-file', type=click.Path(),
              help='Save summary to file instead of displaying')
@click.option('--scheduled', is_flag=True,
              help='Scheduled execution mode (minimal output)')
@click.option('--compare-to', help='Compare to previous period (e.g., "last week")')
@click.option('--detailed', is_flag=True,
              help='Include detailed breakdown and statistics')
@click.option('--include-trends', is_flag=True,
              help='Include trend analysis (weekly/monthly summaries)')
@click.option('--exclude-weekends', is_flag=True,
              help='Exclude weekend activity from summaries')
@click.option('--verbose', is_flag=True,
              help='Show detailed progress and metadata')
@click.version_option(version=__version__, prog_name='daily-summary')
def generate_summary(date_param, period, person, output_format, output_file,
                    scheduled, compare_to, detailed, include_trends,
                    exclude_weekends, verbose):
    """
    Generate daily, weekly, or monthly activity summaries
    
    Creates comprehensive reports of organizational activity across Slack,
    Calendar, Drive, and other data sources with key highlights and insights.
    
    \b
    Examples:
        daily_summary.py --date 2025-08-19 --format markdown
        daily_summary.py --period week --person "alice@example.com"
        daily_summary.py --scheduled --output-file reports/daily_$(date +%Y%m%d).json
        daily_summary.py --compare-to "last week" --detailed --format table
        daily_summary.py --period month --include-trends --format json
    
    \b
    Scheduled Execution:
        Use --scheduled flag for cron jobs and automation:
        0 8 * * * cd /path/to/aicos && python tools/daily_summary.py --scheduled --output-file reports/daily.json
    
    \b
    Environment Variables:
        AICOS_TEST_MODE=true     Use mock data for testing
        AICOS_REPORTS_DIR        Default directory for report files
    """
    
    # Determine target date
    if date_param:
        try:
            target_date = datetime.strptime(date_param, '%Y-%m-%d').date()
        except ValueError:
            raise ValidationError(
                f"Invalid date format: {date_param}",
                suggestion="Use YYYY-MM-DD format (e.g., 2025-08-19)"
            )
    else:
        # Default to yesterday for daily summaries, appropriate period for others
        if period == 'day':
            target_date = date.today() - timedelta(days=1)
        elif period == 'week':
            # Start of current week (Monday)
            today = date.today()
            target_date = today - timedelta(days=today.weekday())
        else:  # month
            # Start of current month
            today = date.today()
            target_date = date(today.year, today.month, 1)
    
    test_mode = check_test_mode()
    
    # Show test mode warning if not in scheduled mode
    if test_mode and not scheduled:
        click.echo(f"🧪 {click.style('TEST MODE ACTIVE', fg='yellow', bold=True)} - Using mock data")
        click.echo()
    
    try:
        # Generate the summary
        start_time = datetime.now()
        
        if not scheduled:
            status_msg = f"Generating {period} summary for {target_date}"
            if person:
                status_msg += f" (focused on {person})"
        
        with StatusIndicator(status_msg if not scheduled else "Generating summary"):
            summary_data = _generate_summary_data(
                target_date=target_date,
                period=period, 
                person=person,
                detailed=detailed,
                include_trends=include_trends,
                exclude_weekends=exclude_weekends,
                compare_to=compare_to,
                verbose=verbose
            )
        
        generation_time = datetime.now() - start_time
        
        # Format the summary
        formatted_summary = format_summary(
            summary_data,
            output_format=output_format,
            detailed=detailed or verbose
        )
        
        # Output handling
        if output_file:
            output_path = Path(output_file)
            
            # Create directory if needed
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write to file
            with open(output_path, 'w') as f:
                f.write(formatted_summary)
            
            if not scheduled:
                click.echo(f"✅ Summary saved to {click.style(str(output_path), fg='green')}")
                click.echo(f"📊 Generated in {format_duration(generation_time.total_seconds())}")
            else:
                # Scheduled mode: minimal output
                print(f"Summary generated: {output_path}")
        else:
            # Display to console
            click.echo(formatted_summary)
            
            if verbose and not scheduled:
                click.echo(f"\n📊 Summary generated in {format_duration(generation_time.total_seconds())}", err=True)
        
        # Show comparison if requested
        if compare_to and not scheduled:
            _show_comparison_highlights(summary_data, compare_to, verbose)
            
    except Exception as e:
        if scheduled:
            # In scheduled mode, just print error and exit
            print(f"ERROR: {str(e)}")
            sys.exit(1)
        else:
            exit_code = handle_cli_error(e, quiet=False, verbose=verbose)
            sys.exit(exit_code)


def _generate_summary_data(target_date: date, period: str, person: Optional[str],
                          detailed: bool, include_trends: bool, exclude_weekends: bool,
                          compare_to: Optional[str], verbose: bool) -> Dict[str, Any]:
    """Generate summary data using ActivityAnalyzer"""
    
    activity_analyzer = get_activity_analyzer()
    
    # Generate appropriate summary based on period
    if period == 'day':
        summary_data = activity_analyzer.generate_daily_summary(
            date=target_date.isoformat(),
            person=person,
            detailed=detailed,
            exclude_weekends=exclude_weekends
        )
    elif period == 'week':
        summary_data = activity_analyzer.generate_weekly_summary(
            week_start=target_date.isoformat(),
            person=person,
            include_trends=include_trends,
            exclude_weekends=exclude_weekends
        )
    else:  # month
        # Note: This assumes ActivityAnalyzer has a generate_monthly_summary method
        # In the mock implementation, we'll use weekly summary as a fallback
        if hasattr(activity_analyzer, 'generate_monthly_summary'):
            summary_data = activity_analyzer.generate_monthly_summary(
                month_start=target_date.isoformat(),
                person=person,
                include_trends=include_trends
            )
        else:
            # Fallback to weekly summary
            summary_data = activity_analyzer.generate_weekly_summary(
                week_start=target_date.isoformat(),
                person=person,
                include_trends=include_trends
            )
            summary_data['period'] = 'month'  # Mark as monthly
    
    # Add metadata
    summary_data['generation_metadata'] = {
        'generated_at': datetime.now().isoformat(),
        'target_date': target_date.isoformat(),
        'period': period,
        'person_focus': person,
        'detailed_mode': detailed,
        'trends_included': include_trends,
        'weekends_excluded': exclude_weekends,
        'test_mode': check_test_mode()
    }
    
    # Add comparison data if requested
    if compare_to:
        summary_data['comparison'] = _generate_comparison_data(
            target_date, period, compare_to, activity_analyzer, person
        )
    
    return summary_data


def _generate_comparison_data(target_date: date, period: str, compare_to: str,
                             activity_analyzer, person: Optional[str]) -> Dict[str, Any]:
    """Generate comparison data for the summary"""
    
    # Parse compare_to expression and calculate comparison date
    try:
        if compare_to.lower() == 'last week':
            compare_date = target_date - timedelta(weeks=1)
        elif compare_to.lower() == 'last month':
            # Subtract approximately one month
            if target_date.month == 1:
                compare_date = target_date.replace(year=target_date.year-1, month=12)
            else:
                compare_date = target_date.replace(month=target_date.month-1)
        elif compare_to.lower() in ['yesterday', 'previous day']:
            compare_date = target_date - timedelta(days=1)
        else:
            # Try to parse as specific date
            compare_date = datetime.strptime(compare_to, '%Y-%m-%d').date()
    except ValueError:
        # If we can't parse the comparison, skip it
        return {'error': f'Could not parse comparison period: {compare_to}'}
    
    # Generate comparison summary
    if period == 'day':
        comparison_data = activity_analyzer.generate_daily_summary(
            date=compare_date.isoformat(),
            person=person
        )
    else:  # week or month
        comparison_data = activity_analyzer.generate_weekly_summary(
            week_start=compare_date.isoformat(),
            person=person
        )
    
    return {
        'compare_to_period': compare_to,
        'compare_date': compare_date.isoformat(),
        'comparison_summary': comparison_data
    }


def _show_comparison_highlights(summary_data: Dict[str, Any], compare_to: str, verbose: bool):
    """Show key comparison highlights"""
    
    if 'comparison' not in summary_data:
        return
    
    comparison = summary_data['comparison']
    
    if 'error' in comparison:
        click.echo(f"\n⚠️ {click.style('Comparison Error:', fg='yellow')} {comparison['error']}")
        return
    
    click.echo(f"\n📊 {click.style('Comparison Highlights', fg='blue', bold=True)} (vs {compare_to}):")
    
    current = summary_data
    previous = comparison['comparison_summary']
    
    # Compare message counts
    current_msgs = current.get('slack_activity', {}).get('message_count', 0)
    previous_msgs = previous.get('slack_activity', {}).get('message_count', 0)
    
    if current_msgs and previous_msgs:
        change = current_msgs - previous_msgs
        change_pct = (change / previous_msgs) * 100 if previous_msgs > 0 else 0
        
        if change > 0:
            click.echo(f"  📈 Messages: +{change} ({change_pct:+.1f}%)")
        elif change < 0:
            click.echo(f"  📉 Messages: {change} ({change_pct:+.1f}%)")
        else:
            click.echo(f"  📊 Messages: No change ({current_msgs})")
    
    # Compare meeting counts
    current_meetings = current.get('calendar_activity', {}).get('meeting_count', 0)
    previous_meetings = previous.get('calendar_activity', {}).get('meeting_count', 0)
    
    if current_meetings is not None and previous_meetings is not None:
        change = current_meetings - previous_meetings
        
        if change > 0:
            click.echo(f"  📅 Meetings: +{change} more meetings")
        elif change < 0:
            click.echo(f"  📅 Meetings: {abs(change)} fewer meetings")
        else:
            click.echo(f"  📅 Meetings: Same number ({current_meetings})")
    
    # Compare productivity metrics if available
    current_stats = current.get('statistics', {})
    previous_stats = previous.get('statistics', {})
    
    if 'productivity_score' in current_stats and 'productivity_score' in previous_stats:
        current_score = current_stats['productivity_score']
        previous_score = previous_stats['productivity_score']
        change = current_score - previous_score
        
        if abs(change) >= 5:  # Only show if significant change
            if change > 0:
                click.echo(f"  📈 Productivity: +{change:.1f} points (improved)")
            else:
                click.echo(f"  📉 Productivity: {change:.1f} points (decreased)")


@click.command()
@click.argument('start_date')
@click.argument('end_date') 
@click.option('--person', help='Focus on specific person')
@click.option('--format', 'output_format', default='table',
              type=click.Choice(['json', 'csv', 'table']),
              help='Output format (default: table)')
@click.option('--output-dir', type=click.Path(), default='reports',
              help='Output directory for batch reports (default: reports)')
@click.version_option(version=__version__)
def batch_summaries(start_date, end_date, person, output_format, output_dir):
    """
    Generate summaries for a date range (batch mode)
    
    \b
    Examples:
        daily_summary.py batch 2025-08-01 2025-08-31 --format json
        daily_summary.py batch 2025-08-15 2025-08-21 --person "alice@example.com"
    """
    
    try:
        start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()
    except ValueError:
        raise ValidationError("Dates must be in YYYY-MM-DD format")
    
    if start_dt > end_dt:
        raise ValidationError("Start date must be before or equal to end date")
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    current_date = start_dt
    generated_files = []
    
    try:
        while current_date <= end_dt:
            # Generate summary for this date
            with StatusIndicator(f"Generating summary for {current_date}"):
                summary_data = _generate_summary_data(
                    target_date=current_date,
                    period='day',
                    person=person,
                    detailed=False,
                    include_trends=False,
                    exclude_weekends=False,
                    compare_to=None,
                    verbose=False
                )
            
            # Format and save
            formatted_summary = format_summary(summary_data, output_format)
            
            # Create filename
            person_suffix = f"_{person.split('@')[0]}" if person else ""
            filename = f"summary_{current_date.isoformat()}{person_suffix}.{output_format}"
            file_path = output_path / filename
            
            with open(file_path, 'w') as f:
                f.write(formatted_summary)
            
            generated_files.append(file_path)
            current_date += timedelta(days=1)
        
        click.echo(f"✅ Generated {len(generated_files)} summaries in {output_path}")
        
        if len(generated_files) <= 10:
            click.echo("\nGenerated files:")
            for file_path in generated_files:
                click.echo(f"  {file_path.name}")
        
    except Exception as e:
        exit_code = handle_cli_error(e, quiet=False, verbose=False)
        sys.exit(exit_code)


# Create a CLI group to handle both single and batch modes
@click.group(invoke_without_command=True)
@click.pass_context
def main(ctx):
    """Daily Summary Generator - Create activity reports and insights"""
    if ctx.invoked_subcommand is None:
        # If no subcommand, run single summary generation
        generate_summary.main(standalone_mode=False)


@main.command('batch')
@click.argument('start_date')
@click.argument('end_date')
@click.option('--person', help='Focus on specific person')
@click.option('--format', 'output_format', default='table',
              type=click.Choice(['json', 'csv', 'table']),
              help='Output format (default: table)')
@click.option('--output-dir', type=click.Path(), default='reports',
              help='Output directory for batch reports (default: reports)')
def batch_command(start_date, end_date, person, output_format, output_dir):
    """Generate summaries for a date range"""
    batch_summaries.main([start_date, end_date], standalone_mode=False)


if __name__ == '__main__':
    try:
        # Check if we have batch arguments
        if len(sys.argv) > 2 and sys.argv[1] not in ['--help', '-h', 'batch']:
            # Assume batch mode if we have two date-like arguments
            if len(sys.argv) >= 3:
                try:
                    datetime.strptime(sys.argv[1], '%Y-%m-%d')
                    datetime.strptime(sys.argv[2], '%Y-%m-%d')
                    # Looks like batch mode
                    batch_summaries()
                except ValueError:
                    # Not batch mode, use regular single mode
                    generate_summary()
            else:
                generate_summary()
        else:
            # Use group interface
            main()
    except KeyboardInterrupt:
        click.echo("\nOperation cancelled by user", err=True)
        sys.exit(130)
    except Exception as e:
        exit_code = handle_cli_error(e, quiet=False, verbose=False)
        sys.exit(exit_code)