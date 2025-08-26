#!/usr/bin/env python3
"""
Brief Command - Simple Direct Integration

Simple brief functionality that creates deterministic calls to daily_summary functionality.
No complex features, just working brief generation.
"""

import sys
import logging
from pathlib import Path
from datetime import date, datetime
from typing import Dict, List, Optional, Any

# Add project root for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.cli.interfaces import get_activity_analyzer
from src.cli.errors import check_test_mode

logger = logging.getLogger(__name__)

def execute_brief(period: str = "day", person: Optional[str] = None) -> Dict[str, Any]:
    """
    Execute brief command with direct activity analyzer integration
    
    Args:
        period: Brief period (day, week, month)
        person: Optional person to focus on
        
    Returns:
        Dict containing brief data or error information
    """
    try:
        # Get activity analyzer
        activity_analyzer = get_activity_analyzer()
        
        # Generate appropriate summary based on period
        target_date = date.today()
        
        if period == 'day':
            summary_data = activity_analyzer.generate_daily_summary(
                date=target_date.isoformat(),
                person=person,
                detailed=False,
                exclude_weekends=False
            )
        elif period == 'week':
            summary_data = activity_analyzer.generate_weekly_summary(
                week_start=target_date.isoformat(),
                person=person,
                include_trends=False,
                exclude_weekends=False
            )
        else:
            # Default to daily for unsupported periods
            summary_data = activity_analyzer.generate_daily_summary(
                date=target_date.isoformat(),
                person=person,
                detailed=False,
                exclude_weekends=False
            )
        
        # Add metadata
        summary_data['generation_metadata'] = {
            'generated_at': datetime.now().isoformat(),
            'target_date': target_date.isoformat(),
            'period': period,
            'person_focus': person,
            'test_mode': check_test_mode()
        }
        
        return {
            "period": period,
            "data": summary_data,
            "error": None
        }
        
    except Exception as e:
        logger.error(f"Brief generation error: {e}")
        return {
            "error": f"Brief generation failed: {str(e)}",
            "period": period,
            "data": None
        }

def format_brief_response(brief_result: Dict[str, Any]) -> str:
    """
    Format brief results for Slack response
    
    Args:
        brief_result: Result from execute_brief()
        
    Returns:
        Formatted string for Slack
    """
    if brief_result.get("error"):
        return f"❌ Brief Error: {brief_result['error']}"
    
    period = brief_result.get("period", "daily")
    data = brief_result.get("data", {})
    
    # Build response
    response = f"📋 **{period.title()} Brief**\n\n"
    
    # Extract key activity metrics
    if 'slack_activity' in data:
        slack = data['slack_activity']
        msg_count = slack.get('message_count', 0)
        channel_count = slack.get('active_channels', 0)
        response += f"💬 **Slack**: {msg_count} messages"
        if channel_count:
            response += f" across {channel_count} channels"
        response += "\n"
    
    if 'calendar_activity' in data:
        calendar = data['calendar_activity']
        meeting_count = calendar.get('meeting_count', 0)
        meeting_hours = calendar.get('meeting_hours', 0)
        response += f"📅 **Calendar**: {meeting_count} meetings"
        if meeting_hours:
            response += f" ({meeting_hours:.1f} hours)"
        response += "\n"
    
    if 'drive_activity' in data:
        drive = data['drive_activity']
        file_count = drive.get('files_modified', 0)
        if file_count > 0:
            response += f"📁 **Drive**: {file_count} files modified\n"
    
    # Add highlights if available
    if 'highlights' in data and data['highlights']:
        highlights = data['highlights'][:3]  # Top 3 highlights
        response += f"\n**Key Highlights:**\n"
        for i, highlight in enumerate(highlights, 1):
            response += f"{i}. {highlight}\n"
    
    # Add statistics if available
    if 'statistics' in data:
        stats = data['statistics']
        if 'productivity_score' in stats:
            score = stats['productivity_score']
            response += f"\n📊 Productivity Score: {score}/100"
    
    # Add test mode indicator
    metadata = data.get('generation_metadata', {})
    if metadata.get('test_mode'):
        response += f"\n\n_🧪 Note: This is test data for demonstration._"
    
    return response

# Simple test function
if __name__ == "__main__":
    # Test brief functionality
    result = execute_brief("day")
    print(f"Brief test result: {result.get('error', 'Success')}")
    
    formatted = format_brief_response(result)
    print(f"Formatted response:\n{formatted}")