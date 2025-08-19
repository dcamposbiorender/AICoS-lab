"""
Output Formatting Utilities for CLI Tools

Provides consistent output formatting across all CLI tools with support for
multiple formats: JSON, CSV, table, and markdown. Includes proper column
alignment, pagination for large results, and professional presentation.

Usage:
    from src.cli.formatters import format_query_results, format_summary
    
    formatted = format_query_results(results, 'table', verbose=True)
    click.echo(formatted)
"""

import json
import csv
import io
import re
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from dataclasses import asdict

import click


class FormatterError(Exception):
    """Exception raised by formatting operations"""
    pass


def format_query_results(results: Union[List[Dict[str, Any]], Dict[str, Any]], 
                        output_format: str = 'table',
                        verbose: bool = False,
                        query: Optional[str] = None,
                        max_content_length: int = 300) -> str:
    """
    Format query results in the specified output format
    
    Args:
        results: Query results to format (list of dicts or QueryResponse object)
        output_format: Output format ('json', 'csv', 'table', 'markdown')
        verbose: Include detailed metadata
        query: Optional query string for highlighting
        max_content_length: Maximum content length before truncation
        
    Returns:
        Formatted string ready for output
        
    Raises:
        FormatterError: If formatting fails
    """
    try:
        # Handle QueryResponse objects (from interfaces.py)
        if hasattr(results, 'results'):
            results_list = [asdict(r) for r in results.results]
            metadata = results.metadata
            performance = results.performance
        elif isinstance(results, dict) and 'results' in results:
            results_list = results['results']
            metadata = results.get('metadata', {})
            performance = results.get('performance', {})
        else:
            results_list = results if isinstance(results, list) else [results]
            metadata = {}
            performance = {}
        
        if not results_list:
            return _format_empty_results(output_format)
        
        if output_format == 'json':
            return _format_json(results_list, metadata, performance, verbose)
        elif output_format == 'csv':
            return _format_csv(results_list, verbose)
        elif output_format == 'table':
            return _format_table(results_list, verbose, query, max_content_length)
        elif output_format == 'markdown':
            return _format_markdown(results_list, verbose, query, max_content_length)
        else:
            raise FormatterError(f"Unsupported output format: {output_format}")
            
    except Exception as e:
        raise FormatterError(f"Failed to format results: {str(e)}")


def format_summary(summary_data: Dict[str, Any], 
                  output_format: str = 'table',
                  detailed: bool = False) -> str:
    """
    Format summary data (daily/weekly summaries)
    
    Args:
        summary_data: Summary data dictionary
        output_format: Output format ('json', 'markdown', 'table')
        detailed: Include detailed breakdown
        
    Returns:
        Formatted summary string
    """
    try:
        if output_format == 'json':
            return json.dumps(summary_data, indent=2, ensure_ascii=False, default=str)
        elif output_format == 'markdown':
            return _format_summary_markdown(summary_data, detailed)
        else:  # table format
            return _format_summary_table(summary_data, detailed)
            
    except Exception as e:
        raise FormatterError(f"Failed to format summary: {str(e)}")


def format_statistics(stats_data: Dict[str, Any],
                     output_format: str = 'table',
                     detailed: bool = False) -> str:
    """
    Format statistics data
    
    Args:
        stats_data: Statistics data dictionary
        output_format: Output format ('json', 'table')
        detailed: Include detailed breakdown
        
    Returns:
        Formatted statistics string
    """
    try:
        if output_format == 'json':
            return json.dumps(stats_data, indent=2, ensure_ascii=False, default=str)
        else:  # table format
            return _format_statistics_table(stats_data, detailed)
            
    except Exception as e:
        raise FormatterError(f"Failed to format statistics: {str(e)}")


def format_calendar_slots(slots_data: Dict[str, Any],
                         output_format: str = 'table') -> str:
    """
    Format calendar availability slots
    
    Args:
        slots_data: Calendar slots data
        output_format: Output format ('json', 'table', 'markdown')
        
    Returns:
        Formatted slots string
    """
    try:
        if output_format == 'json':
            return json.dumps(slots_data, indent=2, ensure_ascii=False, default=str)
        elif output_format == 'markdown':
            return _format_slots_markdown(slots_data)
        else:  # table format
            return _format_slots_table(slots_data)
            
    except Exception as e:
        raise FormatterError(f"Failed to format calendar slots: {str(e)}")


# Private formatting functions

def _format_empty_results(output_format: str) -> str:
    """Format empty results message"""
    if output_format == 'json':
        return json.dumps({'results': [], 'message': 'No results found'}, indent=2)
    elif output_format == 'csv':
        return 'content,source,date,score\n'  # Headers only
    else:
        return click.style("No results found.", fg='yellow')


def _format_json(results: List[Dict], metadata: Dict, performance: Dict, verbose: bool) -> str:
    """Format results as JSON"""
    output = {
        'results': results,
        'metadata': metadata,
        'performance': performance,
        'count': len(results)
    }
    
    if not verbose:
        # Remove verbose fields in non-verbose mode
        for result in output['results']:
            if 'metadata' in result and not verbose:
                result.pop('metadata', None)
    
    return json.dumps(output, indent=2, ensure_ascii=False, default=str)


def _format_csv(results: List[Dict], verbose: bool) -> str:
    """Format results as CSV"""
    if not results:
        return 'content,source,date,score\n'
    
    output = io.StringIO()
    
    # Define CSV columns
    fieldnames = ['content', 'source', 'date', 'relevance_score']
    if verbose:
        fieldnames.extend(['metadata', 'channel', 'author'])
    
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')
    writer.writeheader()
    
    for result in results:
        row = {
            'content': _truncate_text(result.get('content', ''), 200),
            'source': result.get('source', ''),
            'date': result.get('date', ''),
            'relevance_score': f"{result.get('relevance_score', 0):.3f}"
        }
        
        if verbose:
            metadata = result.get('metadata', {})
            row['metadata'] = json.dumps(metadata) if metadata else ''
            row['channel'] = metadata.get('channel', '')
            row['author'] = metadata.get('author', '')
        
        writer.writerow(row)
    
    return output.getvalue()


def _format_table(results: List[Dict], verbose: bool, query: Optional[str], 
                  max_content_length: int) -> str:
    """Format results as human-readable table"""
    if not results:
        return click.style("No results found.", fg='yellow')
    
    lines = []
    
    for i, result in enumerate(results, 1):
        # Header with result number, source, date, and score
        source_styled = click.style(result.get('source', 'unknown').upper(), fg='blue', bold=True)
        score = result.get('relevance_score', 0)
        score_styled = click.style(f"{score:.3f}", fg='cyan')
        date = result.get('date', 'unknown')
        
        lines.append(f"{i}. {source_styled} | {date} | Score: {score_styled}")
        
        # Content with highlighting
        content = result.get('content', '')
        if query and len(query) > 2:
            content = _highlight_query_terms(content, query)
        
        # Truncate long content
        if len(content) > max_content_length:
            content = content[:max_content_length-3] + '...'
        
        lines.append(f"   {content}")
        
        # Show metadata if verbose mode
        if verbose and result.get('metadata'):
            metadata = result['metadata']
            if isinstance(metadata, dict):
                meta_items = []
                for key, value in metadata.items():
                    # Skip large or complex metadata fields
                    if key not in ['original_record', 'blocks', 'attachments'] and value:
                        if len(str(value)) < 50:  # Keep metadata concise
                            meta_items.append(f"{key}={value}")
                
                if meta_items:
                    meta_text = ', '.join(meta_items[:5])  # Max 5 metadata items
                    lines.append(f"   {click.style('Metadata:', dim=True)} {meta_text}")
        
        # Add spacing between results (except for last)
        if i < len(results):
            lines.append('')
    
    return '\n'.join(lines)


def _format_markdown(results: List[Dict], verbose: bool, query: Optional[str], 
                    max_content_length: int) -> str:
    """Format results as markdown"""
    if not results:
        return "_No results found._\n"
    
    lines = ["# Query Results\n"]
    
    for i, result in enumerate(results, 1):
        source = result.get('source', 'unknown').upper()
        score = result.get('relevance_score', 0)
        date = result.get('date', 'unknown')
        
        lines.append(f"## {i}. {source} | {date} | Score: {score:.3f}\n")
        
        content = result.get('content', '')
        if len(content) > max_content_length:
            content = content[:max_content_length-3] + '...'
        
        lines.append(f"{content}\n")
        
        if verbose and result.get('metadata'):
            lines.append("**Metadata:**")
            metadata = result['metadata']
            if isinstance(metadata, dict):
                for key, value in metadata.items():
                    if key not in ['original_record', 'blocks'] and value:
                        lines.append(f"- {key}: {value}")
            lines.append("")
    
    return '\n'.join(lines)


def _format_summary_markdown(summary_data: Dict[str, Any], detailed: bool) -> str:
    """Format summary data as markdown"""
    lines = []
    
    # Title
    date = summary_data.get('date', 'Unknown')
    person = summary_data.get('person')
    if person:
        lines.append(f"# Daily Summary for {person} - {date}\n")
    else:
        lines.append(f"# Daily Summary - {date}\n")
    
    # Slack Activity
    if 'slack_activity' in summary_data:
        slack = summary_data['slack_activity']
        lines.append("## 📱 Slack Activity\n")
        lines.append(f"- **Messages**: {slack.get('message_count', 0)}")
        
        if slack.get('channels_active'):
            channels = ', '.join(slack['channels_active'][:5])
            lines.append(f"- **Active Channels**: {channels}")
        
        if slack.get('top_participants') and detailed:
            participants = ', '.join(slack['top_participants'][:3])
            lines.append(f"- **Top Participants**: {participants}")
        
        lines.append("")
    
    # Calendar Activity
    if 'calendar_activity' in summary_data:
        calendar = summary_data['calendar_activity']
        lines.append("## 📅 Calendar Activity\n")
        lines.append(f"- **Meetings**: {calendar.get('meeting_count', 0)}")
        
        duration = calendar.get('total_duration_minutes', 0)
        lines.append(f"- **Total Duration**: {duration} minutes ({duration//60}h {duration%60}m)")
        
        if calendar.get('meeting_types'):
            types = ', '.join(calendar['meeting_types'])
            lines.append(f"- **Meeting Types**: {types}")
        
        lines.append("")
    
    # Drive Activity
    if 'drive_activity' in summary_data:
        drive = summary_data['drive_activity']
        lines.append("## 📁 Drive Activity\n")
        lines.append(f"- **Files Modified**: {drive.get('files_modified', 0)}")
        lines.append(f"- **Files Created**: {drive.get('files_created', 0)}")
        lines.append(f"- **Collaborations**: {drive.get('collaborations', 0)}")
        lines.append("")
    
    # Key Highlights
    if 'key_highlights' in summary_data:
        lines.append("## ✨ Key Highlights\n")
        for highlight in summary_data['key_highlights'][:5]:
            lines.append(f"- {highlight}")
        lines.append("")
    
    # Statistics (if detailed)
    if detailed and 'statistics' in summary_data:
        stats = summary_data['statistics']
        lines.append("## 📊 Statistics\n")
        for key, value in stats.items():
            key_formatted = key.replace('_', ' ').title()
            lines.append(f"- **{key_formatted}**: {value}")
        lines.append("")
    
    return '\n'.join(lines)


def _format_summary_table(summary_data: Dict[str, Any], detailed: bool) -> str:
    """Format summary data as table"""
    lines = []
    
    # Title
    date = summary_data.get('date', 'Unknown')
    person = summary_data.get('person')
    if person:
        lines.append(f"{click.style(f'Daily Summary for {person} - {date}', fg='cyan', bold=True)}")
    else:
        lines.append(f"{click.style(f'Daily Summary - {date}', fg='cyan', bold=True)}")
    lines.append("")
    
    # Slack Activity
    if 'slack_activity' in summary_data:
        slack = summary_data['slack_activity']
        lines.append(f"{click.style('📱 Slack Activity:', fg='blue', bold=True)}")
        lines.append(f"  Messages: {click.style(str(slack.get('message_count', 0)), fg='green')}")
        
        if slack.get('channels_active'):
            channels = ', '.join(slack['channels_active'][:3])
            lines.append(f"  Active channels: {channels}")
        
        if slack.get('peak_activity_hour'):
            lines.append(f"  Peak activity: {slack['peak_activity_hour']}:00")
        lines.append("")
    
    # Calendar Activity
    if 'calendar_activity' in summary_data:
        calendar = summary_data['calendar_activity']
        lines.append(f"{click.style('📅 Calendar Activity:', fg='blue', bold=True)}")
        lines.append(f"  Meetings: {click.style(str(calendar.get('meeting_count', 0)), fg='green')}")
        
        duration = calendar.get('total_duration_minutes', 0)
        duration_str = f"{duration//60}h {duration%60}m" if duration >= 60 else f"{duration}m"
        lines.append(f"  Duration: {click.style(duration_str, fg='green')}")
        
        if calendar.get('meeting_types'):
            types = ', '.join(calendar['meeting_types'][:3])
            lines.append(f"  Types: {types}")
        lines.append("")
    
    # Drive Activity
    if 'drive_activity' in summary_data:
        drive = summary_data['drive_activity']
        lines.append(f"{click.style('📁 Drive Activity:', fg='blue', bold=True)}")
        lines.append(f"  Files modified: {click.style(str(drive.get('files_modified', 0)), fg='green')}")
        lines.append(f"  Files created: {click.style(str(drive.get('files_created', 0)), fg='green')}")
        lines.append("")
    
    # Key Highlights
    if 'key_highlights' in summary_data:
        lines.append(f"{click.style('✨ Key Highlights:', fg='yellow', bold=True)}")
        for highlight in summary_data['key_highlights'][:3]:
            lines.append(f"  • {highlight}")
        lines.append("")
    
    # Statistics (if detailed)
    if detailed and 'statistics' in summary_data:
        stats = summary_data['statistics']
        lines.append(f"{click.style('📊 Statistics:', fg='cyan', bold=True)}")
        for key, value in list(stats.items())[:5]:
            key_formatted = key.replace('_', ' ').title()
            if isinstance(value, (int, float)):
                value_styled = click.style(str(value), fg='green')
            else:
                value_styled = str(value)
            lines.append(f"  {key_formatted}: {value_styled}")
    
    return '\n'.join(lines)


def _format_statistics_table(stats_data: Dict[str, Any], detailed: bool) -> str:
    """Format statistics data as table"""
    lines = []
    lines.append(f"{click.style('📊 Statistics:', fg='cyan', bold=True)}")
    
    # Basic stats
    time_range = stats_data.get('time_range', 'Unknown')
    lines.append(f"Time range: {time_range}")
    lines.append(f"Total messages: {click.style(str(stats_data.get('total_messages', 0)), fg='green')}")
    lines.append(f"Total meetings: {click.style(str(stats_data.get('total_meetings', 0)), fg='green')}")
    lines.append(f"Unique participants: {click.style(str(stats_data.get('unique_participants', 0)), fg='green')}")
    lines.append("")
    
    # Breakdown by channel
    if detailed and stats_data.get('by_channel'):
        lines.append(f"{click.style('By Channel:', fg='blue', bold=True)}")
        for channel, data in stats_data['by_channel'].items():
            lines.append(f"  {channel}:")
            lines.append(f"    Messages: {data.get('messages', 0)}")
            lines.append(f"    Participants: {data.get('participants', 0)}")
    
    # Breakdown by person
    if detailed and stats_data.get('by_person'):
        lines.append(f"{click.style('By Person:', fg='blue', bold=True)}")
        for person, data in list(stats_data['by_person'].items())[:5]:
            lines.append(f"  {person}:")
            lines.append(f"    Messages: {data.get('messages', 0)}")
            lines.append(f"    Meetings: {data.get('meetings', 0)}")
    
    return '\n'.join(lines)


def _format_slots_table(slots_data: Dict[str, Any]) -> str:
    """Format calendar slots as table"""
    lines = []
    lines.append(f"{click.style('📅 Available Time Slots:', fg='cyan', bold=True)}")
    
    attendees = slots_data.get('attendees', [])
    duration = slots_data.get('duration_minutes', 0)
    
    lines.append(f"Attendees: {', '.join(attendees)}")
    lines.append(f"Duration: {duration} minutes")
    lines.append("")
    
    slots = slots_data.get('available_slots', [])
    if not slots:
        lines.append(click.style("No available slots found.", fg='yellow'))
    else:
        lines.append(f"{click.style('Available slots:', fg='green', bold=True)}")
        for i, slot in enumerate(slots, 1):
            start = slot.get('start', '')
            end = slot.get('end', '')
            confidence = slot.get('confidence', 1.0)
            
            # Format time nicely
            try:
                from datetime import datetime
                start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(end.replace('Z', '+00:00'))
                start_str = start_dt.strftime('%I:%M %p')
                end_str = end_dt.strftime('%I:%M %p')
                date_str = start_dt.strftime('%A, %B %d')
                
                confidence_color = 'green' if confidence > 0.8 else 'yellow' if confidence > 0.6 else 'red'
                confidence_styled = click.style(f"{confidence:.0%}", fg=confidence_color)
                
                lines.append(f"  {i}. {date_str}: {start_str} - {end_str} ({confidence_styled} confidence)")
            except:
                lines.append(f"  {i}. {start} - {end}")
    
    return '\n'.join(lines)


def _format_slots_markdown(slots_data: Dict[str, Any]) -> str:
    """Format calendar slots as markdown"""
    lines = ["# Available Time Slots\n"]
    
    attendees = slots_data.get('attendees', [])
    duration = slots_data.get('duration_minutes', 0)
    
    lines.append(f"**Attendees**: {', '.join(attendees)}")
    lines.append(f"**Duration**: {duration} minutes\n")
    
    slots = slots_data.get('available_slots', [])
    if not slots:
        lines.append("_No available slots found._")
    else:
        lines.append("## Available Slots\n")
        for i, slot in enumerate(slots, 1):
            start = slot.get('start', '')
            end = slot.get('end', '')
            confidence = slot.get('confidence', 1.0)
            
            lines.append(f"{i}. **{start} - {end}** (Confidence: {confidence:.0%})")
    
    return '\n'.join(lines)


def _highlight_query_terms(content: str, query: str) -> str:
    """Highlight query terms in content"""
    try:
        # Extract meaningful terms from query (skip operators and short words)
        terms = []
        for word in query.split():
            if ':' not in word and len(word) > 2:
                # Remove wildcards and special characters for highlighting
                clean_word = word.rstrip('*').strip('"')
                if clean_word:
                    terms.append(clean_word)
        
        # Highlight each term (case-insensitive)
        highlighted = content
        for term in terms:
            pattern = re.compile(re.escape(term), re.IGNORECASE)
            highlighted = pattern.sub(
                lambda m: click.style(m.group(), bg='yellow', fg='black'), 
                highlighted
            )
        
        return highlighted
        
    except Exception:
        # If highlighting fails, return original content
        return content


def _truncate_text(text: str, max_length: int) -> str:
    """Truncate text to maximum length with ellipsis"""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + '...'


def format_size(size_bytes: int) -> str:
    """Format file size in human-readable format"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"


def create_progress_bar(iterable, desc: str, disable: bool = False):
    """Create progress bar with fallback for environments without tqdm"""
    try:
        from tqdm import tqdm
        if not disable:
            return tqdm(iterable, desc=desc, unit='items')
    except ImportError:
        pass
    
    # Fallback: just return the iterable
    return iterable


def paginate_output(content: str, page_size: int = 20) -> List[str]:
    """
    Paginate long output into chunks
    
    Args:
        content: Content to paginate
        page_size: Lines per page
        
    Returns:
        List of page strings
    """
    lines = content.split('\n')
    pages = []
    
    for i in range(0, len(lines), page_size):
        page_lines = lines[i:i + page_size]
        page = '\n'.join(page_lines)
        pages.append(page)
    
    return pages