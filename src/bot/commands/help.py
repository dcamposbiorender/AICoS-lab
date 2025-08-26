#!/usr/bin/env python3
"""
Help Command - Simple Command Reference

Simple help functionality that shows available commands and usage.
"""

import sys
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

# Add project root for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

logger = logging.getLogger(__name__)

def get_help_text() -> str:
    """
    Get help text for the bot commands
    
    Returns:
        Formatted help text for Slack
    """
    help_text = """🤖 **AI Chief of Staff Bot**

**Available Commands:**
• `/cos search [query]` - Search across all communications and data
• `/cos brief` - Get today's activity summary
• `/cos help` - Show this help message

**Search Examples:**
• `/cos search project deadlines`
• `/cos search meeting notes from last week`
• `/cos search "exact phrase in quotes"`

**Brief Examples:**
• `/cos brief` - Get today's summary
• `/cos brief week` - Get weekly summary (if available)

**Features:**
✅ Direct SearchDatabase integration (340K+ records)
✅ Real-time activity summaries
✅ Simple interface for existing CLI tools
✅ Deterministic calls to working systems

**Technical Details:**
This bot creates direct calls to existing CLI systems without subprocess overhead.
It uses the same SearchDatabase and activity analyzers that power the command-line tools.

**Need Help?**
If you encounter issues, check that:
- The search database exists (search.db)
- Authentication tokens are configured
- Data collection has been run recently

This bot is designed for simple, reliable operation."""
    
    return help_text

def execute_help(topic: Optional[str] = None) -> Dict[str, Any]:
    """
    Execute help command
    
    Args:
        topic: Optional specific help topic
        
    Returns:
        Dict containing help information
    """
    try:
        if topic == "search":
            help_content = """🔍 **Search Command Help**

**Basic Usage:**
`/cos search [your search query]`

**Examples:**
• `/cos search team meeting` - Find team meetings
• `/cos search project deadline` - Find project deadlines
• `/cos search "exact phrase"` - Search for exact phrase

**Tips:**
- Use specific keywords for best results
- Quotes around phrases for exact matches
- Search works across Slack, Calendar, Drive, and Employee data
- Results are returned from the 340K+ record database"""
            
        elif topic == "brief":
            help_content = """📋 **Brief Command Help**

**Basic Usage:**
`/cos brief`

**What it includes:**
• Slack message activity
• Calendar meetings and events  
• Drive file modifications
• Key highlights from recent activity
• Productivity metrics (if available)

**Examples:**
• `/cos brief` - Get today's activity summary
• `/cos brief week` - Weekly summary (if supported)

**Note:**
Briefs use the same daily summary generation as the CLI tools,
providing consistent data across interfaces."""
            
        else:
            # Default help
            help_content = get_help_text()
        
        return {
            "help_topic": topic,
            "content": help_content,
            "error": None
        }
        
    except Exception as e:
        logger.error(f"Help generation error: {e}")
        return {
            "error": f"Help generation failed: {str(e)}",
            "help_topic": topic,
            "content": get_help_text()  # Fallback to basic help
        }

def format_help_response(help_result: Dict[str, Any]) -> str:
    """
    Format help results for Slack response
    
    Args:
        help_result: Result from execute_help()
        
    Returns:
        Formatted string for Slack
    """
    if help_result.get("error"):
        logger.warning(f"Help error: {help_result['error']}")
        # Still show help even if there was an error
    
    return help_result.get("content", get_help_text())

# Simple test function
if __name__ == "__main__":
    # Test help functionality
    result = execute_help()
    print(f"Help test result: {result.get('error', 'Success')}")
    
    formatted = format_help_response(result)
    print(f"Formatted response:\n{formatted}")
    
    # Test specific help topics
    for topic in ["search", "brief"]:
        print(f"\n--- {topic.title()} Help ---")
        topic_result = execute_help(topic)
        topic_formatted = format_help_response(topic_result)
        print(topic_formatted)