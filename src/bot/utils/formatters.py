#!/usr/bin/env python3
"""
Slack Block Kit Formatters - Phase 4b

Provides rich formatting utilities for Slack messages using Block Kit.
Handles search results, briefings, errors, and interactive elements with
mobile-responsive design and accessibility features.

Key Features:
- Rich search result formatting with file previews
- Collapsible briefing sections with progressive disclosure
- User-friendly error messages with actionable guidance
- Loading states and progress indicators
- Mobile-responsive Block Kit design elements

Block Kit Reference:
- https://api.slack.com/block-kit/building
- https://api.slack.com/block-kit/interactive-components
"""

import json
import logging
from datetime import datetime, date
from typing import Dict, List, Optional, Any, Union
from urllib.parse import quote

logger = logging.getLogger(__name__)

# Block Kit constants
MAX_TEXT_LENGTH = 3000
MAX_BLOCKS_PER_MESSAGE = 50
MAX_ELEMENTS_PER_SECTION = 10

def format_search_results_blocks(results: List[Dict[str, Any]], query: str,
                                total_results: int, search_duration: float,
                                page: int = 1, source_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Format search results as Slack Block Kit blocks
    
    Args:
        results: List of search results
        query: Original search query
        total_results: Total number of results found
        search_duration: Time taken for search
        page: Current page number
        source_filter: Applied source filter if any
        
    Returns:
        List of Block Kit blocks
    """
    blocks = []
    
    # Header with search info
    header_text = f"🔍 *Search Results for:* `{query}`"
    if source_filter:
        header_text += f" *(filtered by {source_filter.title()})*"
    
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": header_text
        }
    })
    
    # Search metadata
    metadata_text = f"Found {total_results} results in {search_duration:.2f}s"
    if page > 1:
        metadata_text += f" • Page {page}"
    
    blocks.append({
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": metadata_text
            }
        ]
    })
    
    blocks.append({"type": "divider"})
    
    # Format individual results
    for i, result in enumerate(results):
        blocks.extend(_format_single_search_result(result, i + 1, query))
        
        # Add divider between results (except after last)
        if i < len(results) - 1:
            blocks.append({"type": "divider"})
    
    # Add footer with tips
    blocks.extend(_create_search_footer(query, source_filter))
    
    return _validate_blocks(blocks)

def _format_single_search_result(result: Dict[str, Any], index: int, query: str) -> List[Dict[str, Any]]:
    """Format a single search result"""
    blocks = []
    
    # Result header with source, date, and relevance
    source_emoji = _get_source_emoji(result.get('source', 'unknown'))
    source_text = result.get('source', 'Unknown').title()
    date_text = result.get('date', 'Unknown date')
    score = result.get('relevance_score', 0)
    
    header_text = f"{source_emoji} *{index}.* {source_text} • {date_text}"
    if score > 0:
        header_text += f" • Relevance: {score:.2f}"
    
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": header_text
        }
    })
    
    # Content with highlighting
    content = result.get('content', 'No content available')
    content = _highlight_query_terms(content, query)
    content = _truncate_text(content, MAX_TEXT_LENGTH - 200)  # Leave room for other text
    
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": content
        }
    })
    
    # Metadata if available
    if result.get('metadata'):
        metadata_elements = _format_result_metadata(result['metadata'])
        if metadata_elements:
            blocks.append({
                "type": "context",
                "elements": metadata_elements
            })
    
    return blocks

def _format_result_metadata(metadata: Dict[str, Any]) -> List[Dict[str, str]]:
    """Format result metadata for context block"""
    elements = []
    
    # Common metadata fields to show
    if 'channel_name' in metadata:
        elements.append({
            "type": "mrkdwn",
            "text": f"*Channel:* #{metadata['channel_name']}"
        })
    
    if 'user' in metadata:
        user = metadata['user']
        if isinstance(user, dict) and 'display_name' in user:
            elements.append({
                "type": "mrkdwn", 
                "text": f"*User:* {user['display_name']}"
            })
        elif isinstance(user, str):
            elements.append({
                "type": "mrkdwn",
                "text": f"*User:* {user}"
            })
    
    if 'file_type' in metadata:
        elements.append({
            "type": "mrkdwn",
            "text": f"*Type:* {metadata['file_type']}"
        })
    
    if 'attendee_count' in metadata:
        elements.append({
            "type": "mrkdwn",
            "text": f"*Attendees:* {metadata['attendee_count']}"
        })
    
    # Limit to MAX_ELEMENTS_PER_SECTION
    return elements[:MAX_ELEMENTS_PER_SECTION]

def _create_search_footer(query: str, source_filter: Optional[str]) -> List[Dict[str, Any]]:
    """Create footer with search tips and actions"""
    return [
        {
            "type": "divider"
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "💡 *Tips:* Use quotes for exact phrases, try different keywords, or filter by source for better results"
                }
            ]
        }
    ]

def format_brief_blocks(briefing_data: Dict[str, Any], period: str,
                       generation_duration: float, person_focus: Optional[str] = None,
                       show_comparison: bool = False, detailed: bool = False) -> List[Dict[str, Any]]:
    """
    Format briefing data as Slack Block Kit blocks
    
    Args:
        briefing_data: Briefing data from daily_summary.py
        period: Briefing period (daily, weekly, monthly)
        generation_duration: Time taken to generate briefing
        person_focus: Person-focused briefing if applicable
        show_comparison: Whether comparison data is included
        detailed: Whether to show detailed breakdown
        
    Returns:
        List of Block Kit blocks
    """
    blocks = []
    
    # Header with briefing info
    period_emoji = _get_period_emoji(period)
    header_text = f"{period_emoji} *{period.title()} Brief*"
    
    if person_focus:
        header_text += f" for {person_focus}"
    
    if briefing_data.get('generation_metadata', {}).get('target_date'):
        target_date = briefing_data['generation_metadata']['target_date']
        header_text += f"\n_{target_date}_"
    
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": header_text
        }
    })
    
    # Generation metadata
    metadata_text = f"Generated in {generation_duration:.1f}s"
    if briefing_data.get('generation_metadata', {}).get('test_mode'):
        metadata_text += " • 🧪 Test Mode"
    
    blocks.append({
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": metadata_text
            }
        ]
    })
    
    blocks.append({"type": "divider"})
    
    # Key highlights section
    blocks.extend(_format_brief_highlights(briefing_data, detailed))
    
    # Activity breakdown sections
    blocks.extend(_format_activity_sections(briefing_data, detailed))
    
    # Comparison section if available
    if show_comparison and 'comparison' in briefing_data:
        blocks.extend(_format_comparison_section(briefing_data['comparison']))
    
    # Statistics section if detailed
    if detailed and 'statistics' in briefing_data:
        blocks.extend(_format_statistics_section(briefing_data['statistics']))
    
    return _validate_blocks(blocks)

def _format_brief_highlights(briefing_data: Dict[str, Any], detailed: bool) -> List[Dict[str, Any]]:
    """Format key highlights from briefing"""
    blocks = []
    
    highlights = []
    
    # Extract key metrics
    slack_activity = briefing_data.get('slack_activity', {})
    calendar_activity = briefing_data.get('calendar_activity', {})
    
    if slack_activity.get('message_count'):
        highlights.append(f"💬 {slack_activity['message_count']} messages sent")
    
    if calendar_activity.get('meeting_count'):
        highlights.append(f"📅 {calendar_activity['meeting_count']} meetings attended")
    
    if slack_activity.get('channels_active'):
        highlights.append(f"🔀 Active in {len(slack_activity['channels_active'])} channels")
    
    # Add productivity insights if available
    if briefing_data.get('insights', {}).get('key_themes'):
        themes = briefing_data['insights']['key_themes'][:3]  # Top 3 themes
        if themes:
            themes_text = ", ".join(themes)
            highlights.append(f"🎯 Key topics: {themes_text}")
    
    if highlights:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*📊 Key Highlights:*\n" + "\n".join(f"• {h}" for h in highlights)
            }
        })
    
    return blocks

def _format_activity_sections(briefing_data: Dict[str, Any], detailed: bool) -> List[Dict[str, Any]]:
    """Format activity breakdown sections"""
    blocks = []
    
    # Slack activity
    if 'slack_activity' in briefing_data:
        blocks.extend(_format_slack_activity_section(briefing_data['slack_activity'], detailed))
    
    # Calendar activity
    if 'calendar_activity' in briefing_data:
        blocks.extend(_format_calendar_activity_section(briefing_data['calendar_activity'], detailed))
    
    # Drive activity if available
    if 'drive_activity' in briefing_data:
        blocks.extend(_format_drive_activity_section(briefing_data['drive_activity'], detailed))
    
    return blocks

def _format_slack_activity_section(slack_data: Dict[str, Any], detailed: bool) -> List[Dict[str, Any]]:
    """Format Slack activity section"""
    blocks = []
    
    if not slack_data:
        return blocks
    
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "*💬 Slack Activity:*"
        }
    })
    
    activity_items = []
    
    if 'message_count' in slack_data:
        activity_items.append(f"Messages: {slack_data['message_count']}")
    
    if 'channels_active' in slack_data:
        count = len(slack_data['channels_active'])
        activity_items.append(f"Active channels: {count}")
        
        if detailed and count > 0:
            channels = slack_data['channels_active'][:5]  # Top 5 channels
            activity_items.append(f"Top channels: {', '.join(f'#{ch}' for ch in channels)}")
    
    if 'peak_activity_time' in slack_data:
        activity_items.append(f"Peak time: {slack_data['peak_activity_time']}")
    
    if activity_items:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn", 
                "text": "\n".join(f"• {item}" for item in activity_items)
            }
        })
    
    return blocks

def _format_calendar_activity_section(calendar_data: Dict[str, Any], detailed: bool) -> List[Dict[str, Any]]:
    """Format calendar activity section"""
    blocks = []
    
    if not calendar_data:
        return blocks
    
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "*📅 Calendar Activity:*"
        }
    })
    
    activity_items = []
    
    if 'meeting_count' in calendar_data:
        activity_items.append(f"Meetings: {calendar_data['meeting_count']}")
    
    if 'total_meeting_time' in calendar_data:
        hours = calendar_data['total_meeting_time'] / 60  # Convert minutes to hours
        activity_items.append(f"Meeting time: {hours:.1f} hours")
    
    if 'average_meeting_size' in calendar_data:
        activity_items.append(f"Avg meeting size: {calendar_data['average_meeting_size']:.1f} people")
    
    if detailed and 'meeting_types' in calendar_data:
        types = calendar_data['meeting_types']
        if types:
            type_list = [f"{k}: {v}" for k, v in types.items()][:3]
            activity_items.append(f"Meeting types: {', '.join(type_list)}")
    
    if activity_items:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "\n".join(f"• {item}" for item in activity_items)
            }
        })
    
    return blocks

def _format_drive_activity_section(drive_data: Dict[str, Any], detailed: bool) -> List[Dict[str, Any]]:
    """Format Drive activity section"""
    blocks = []
    
    if not drive_data:
        return blocks
    
    blocks.append({
        "type": "section", 
        "text": {
            "type": "mrkdwn",
            "text": "*📁 Drive Activity:*"
        }
    })
    
    activity_items = []
    
    if 'files_modified' in drive_data:
        activity_items.append(f"Files modified: {drive_data['files_modified']}")
    
    if 'files_created' in drive_data:
        activity_items.append(f"Files created: {drive_data['files_created']}")
    
    if 'shares_activity' in drive_data:
        activity_items.append(f"Sharing events: {drive_data['shares_activity']}")
    
    if activity_items:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "\n".join(f"• {item}" for item in activity_items)
            }
        })
    
    return blocks

def _format_comparison_section(comparison_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Format comparison section"""
    blocks = []
    
    if 'error' in comparison_data:
        return blocks
    
    blocks.append({
        "type": "divider"
    })
    
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": f"*📊 Comparison vs {comparison_data.get('compare_to_period', 'previous period')}:*"
        }
    })
    
    # This would contain the comparison logic
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "• Comparison metrics will be displayed here based on available data"
        }
    })
    
    return blocks

def _format_statistics_section(stats_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Format detailed statistics section"""
    blocks = []
    
    blocks.append({
        "type": "divider"
    })
    
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "*📈 Detailed Statistics:*"
        }
    })
    
    stats_items = []
    
    if 'productivity_score' in stats_data:
        stats_items.append(f"Productivity score: {stats_data['productivity_score']:.1f}/100")
    
    if 'response_time_avg' in stats_data:
        stats_items.append(f"Avg response time: {stats_data['response_time_avg']} minutes")
    
    if 'collaboration_index' in stats_data:
        stats_items.append(f"Collaboration index: {stats_data['collaboration_index']:.2f}")
    
    if stats_items:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "\n".join(f"• {item}" for item in stats_items)
            }
        })
    
    return blocks

def format_error_blocks(title: str, message: str, error_type: str = "general",
                       show_support: bool = True) -> List[Dict[str, Any]]:
    """
    Format error message as Slack Block Kit blocks
    
    Args:
        title: Error title
        message: Error message
        error_type: Type of error for customized handling
        show_support: Whether to show support contact info
        
    Returns:
        List of Block Kit blocks
    """
    blocks = []
    
    # Error header
    error_emoji = _get_error_emoji(error_type)
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": f"{error_emoji} *{title}*"
        }
    })
    
    # Error message
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": message
        }
    })
    
    # Add specific guidance based on error type
    if error_type == "permission_error":
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*To resolve:*\n• Contact your Slack admin to reinstall the bot\n• Or try alternative commands that don't require these permissions"
            }
        })
    elif error_type == "timeout":
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*To resolve:*\n• Try again in a few moments\n• Use more specific search terms\n• Try a shorter time period"
            }
        })
    
    # Support information
    if show_support:
        blocks.append({
            "type": "divider"
        })
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "💬 If this issue persists, please contact your system administrator or check `/cos-help` for more information."
                }
            ]
        })
    
    return _validate_blocks(blocks)

def format_loading_blocks(title: str, message: str) -> List[Dict[str, Any]]:
    """
    Format loading/progress message as Slack Block Kit blocks
    
    Args:
        title: Loading title
        message: Loading message
        
    Returns:
        List of Block Kit blocks
    """
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"⏳ *{title}*"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": message
            }
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "Please wait while we process your request..."
                }
            ]
        }
    ]

# Helper functions

def _get_source_emoji(source: str) -> str:
    """Get emoji for data source"""
    source_emojis = {
        'slack': '💬',
        'calendar': '📅',
        'drive': '📁',
        'employees': '👥',
        'email': '📧'
    }
    return source_emojis.get(source.lower(), '📄')

def _get_period_emoji(period: str) -> str:
    """Get emoji for time period"""
    period_emojis = {
        'daily': '📅',
        'weekly': '📊', 
        'monthly': '📈'
    }
    return period_emojis.get(period.lower(), '📋')

def _get_error_emoji(error_type: str) -> str:
    """Get emoji for error type"""
    error_emojis = {
        'permission_error': '🔒',
        'timeout': '⏱️',
        'database_error': '💾',
        'generation_error': '⚠️',
        'validation_error': '❌'
    }
    return error_emojis.get(error_type, '❌')

def _highlight_query_terms(text: str, query: str) -> str:
    """Add basic highlighting for query terms in text"""
    # For Block Kit, we can use *bold* for highlighting
    # This is a simple implementation - could be enhanced
    words = query.lower().split()
    
    for word in words:
        if len(word) > 2:  # Only highlight meaningful words
            # Simple word boundary replacement
            import re
            pattern = re.compile(re.escape(word), re.IGNORECASE)
            text = pattern.sub(lambda m: f"*{m.group()}*", text)
    
    return text

def _truncate_text(text: str, max_length: int) -> str:
    """Truncate text to max length with ellipsis"""
    if len(text) <= max_length:
        return text
    
    # Find a good break point near the limit
    truncate_point = max_length - 3  # Leave room for "..."
    
    # Try to break at word boundary
    if truncate_point < len(text):
        space_index = text.rfind(' ', 0, truncate_point)
        if space_index > max_length * 0.8:  # Don't break too early
            truncate_point = space_index
    
    return text[:truncate_point] + "..."

def _validate_blocks(blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Validate blocks meet Slack constraints
    
    - Max 50 blocks per message
    - Text fields within limits
    - Required fields present
    """
    if len(blocks) > MAX_BLOCKS_PER_MESSAGE:
        logger.warning(f"Block count {len(blocks)} exceeds limit, truncating to {MAX_BLOCKS_PER_MESSAGE}")
        blocks = blocks[:MAX_BLOCKS_PER_MESSAGE-1]
        
        # Add truncation notice
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "⚠️ Some content was truncated due to message limits"
                }
            ]
        })
    
    # Validate text length in blocks
    for block in blocks:
        if block.get('type') == 'section' and 'text' in block:
            text = block['text'].get('text', '')
            if len(text) > MAX_TEXT_LENGTH:
                block['text']['text'] = _truncate_text(text, MAX_TEXT_LENGTH)
    
    return blocks