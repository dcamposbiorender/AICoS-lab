#!/usr/bin/env python3
"""
Filtered Brief Command - Bot-Filtered Daily Briefing

Generates daily briefings using bot filtering to focus on human communication.
This provides clean, actionable insights without automated noise.

References:
- src/intelligence/bot_filter.py - Bot detection and filtering
- src/bot/commands/brief.py - Original brief command structure
- src/aggregators/basic_stats.py - Statistics calculation patterns
"""

import sys
import json
import logging
from pathlib import Path
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import Counter, defaultdict

# Add project root for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.intelligence.bot_filter import BotFilter

logger = logging.getLogger(__name__)


def execute_filtered_brief(period: str = "day", person: Optional[str] = None) -> Dict[str, Any]:
    """
    Execute brief command with bot filtering for clean human insights
    
    Args:
        period: Brief period (day, week, month)
        person: Optional person to focus on
        
    Returns:
        Dict containing filtered brief data or error information
    """
    try:
        # Load data from yesterday (most recent complete data)
        data_date = "2025-08-25"  # Use existing collected data
        channels_file = Path(f'data/raw/slack/{data_date}/channels.json')
        users_file = Path(f'data/raw/slack/{data_date}/users.json')
        
        if not channels_file.exists():
            return {
                "error": f"No data found for {data_date}",
                "period": period,
                "data": None
            }
        
        # Initialize bot filter
        bot_filter = BotFilter(str(users_file) if users_file.exists() else None)
        
        # Load channel data
        with open(channels_file) as f:
            channels = json.load(f)
        
        # Collect all messages
        all_messages = []
        for ch_id, ch_data in channels.items():
            ch_name = ch_data.get('name', ch_id)
            for msg in ch_data.get('messages', []):
                all_messages.append({
                    'user': msg.get('user', ''),
                    'text': msg.get('text', ''),
                    'channel': ch_name,
                    'timestamp': msg.get('ts', ''),
                    'type': msg.get('type', 'message')
                })
        
        # Filter out bot messages
        human_messages = bot_filter.filter_messages(all_messages)
        
        # Generate statistics
        bot_stats = bot_filter.get_bot_statistics(all_messages)
        human_stats = _analyze_human_communication(human_messages)
        commitment_stats = _analyze_commitments(human_messages)
        
        # Build summary data
        summary_data = {
            'filtering_results': {
                'total_messages': bot_stats['total_messages'],
                'human_messages': bot_stats['human_messages'],
                'bot_messages_filtered': bot_stats['bot_messages'],
                'noise_reduction': bot_stats['filtering_effectiveness']['noise_reduction']
            },
            'slack_activity': {
                'message_count': human_stats['total_messages'],
                'active_channels': human_stats['active_channels'],
                'active_users': human_stats['active_users'],
                'avg_messages_per_user': human_stats['avg_messages_per_user'],
                'top_channels': human_stats['top_channels'][:5],
                'top_contributors': human_stats['top_contributors'][:5],
                'messages': all_messages  # Add messages for personalization
            },
            'communication_insights': {
                'commitment_indicators': commitment_stats['potential_commitments'],
                'questions_asked': commitment_stats['questions'],
                'decisions_mentioned': commitment_stats['decisions'],
                'content_themes': human_stats['content_themes'][:10]
            },
            'generation_metadata': {
                'generated_at': datetime.now().isoformat(),
                'data_date': data_date,
                'period': period,
                'person_focus': person,
                'filtering_enabled': True
            }
        }
        
        # Apply personalization if PRIMARY_USER configured
        try:
            from src.personalization.brief_personalizer import BriefPersonalizer
            personalizer = BriefPersonalizer()
            
            if personalizer.filter.primary_user:
                logger.info(f"🎯 Applying filtered brief personalization for {personalizer.filter.primary_user['email']}")
                summary_data = personalizer.personalize_brief_data(summary_data)
            else:
                logger.debug("ℹ️ No PRIMARY_USER configured - generating generic filtered brief")
                
        except Exception as e:
            logger.warning(f"⚠️ Filtered brief personalization failed: {e}")
            # Continue with unpersonalized brief
        
        return {
            "period": period,
            "data": summary_data,
            "error": None
        }
        
    except Exception as e:
        logger.error(f"Filtered brief generation error: {e}")
        return {
            "error": f"Brief generation failed: {str(e)}",
            "period": period,
            "data": None
        }


def _analyze_human_communication(messages: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze patterns in human-only messages"""
    
    if not messages:
        return {
            'total_messages': 0,
            'active_channels': 0,
            'active_users': 0,
            'avg_messages_per_user': 0,
            'top_channels': [],
            'top_contributors': [],
            'content_themes': []
        }
    
    # Channel activity
    channel_counts = Counter(msg['channel'] for msg in messages)
    
    # User activity  
    user_counts = Counter(msg['user'] for msg in messages)
    
    # Content analysis
    word_frequency = Counter()
    for msg in messages:
        text = msg.get('text', '').lower()
        # Simple word extraction, filter short words
        words = [w for w in text.split() if len(w) > 4 and not w.startswith(('http', 'mailto'))]
        word_frequency.update(words)
    
    return {
        'total_messages': len(messages),
        'active_channels': len(channel_counts),
        'active_users': len(user_counts),
        'avg_messages_per_user': len(messages) / len(user_counts) if user_counts else 0,
        'top_channels': [(ch, count) for ch, count in channel_counts.most_common(10)],
        'top_contributors': [(user, count) for user, count in user_counts.most_common(10)],
        'content_themes': [(word, count) for word, count in word_frequency.most_common(15)]
    }


def _analyze_commitments(messages: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze commitment patterns in human messages"""
    
    commitment_keywords = ['will', 'todo', 'task', 'deadline', 'by', 'deliver', 'complete', 'finish']
    question_keywords = ['?', 'how', 'what', 'when', 'where', 'why', 'can you', 'could you']  
    decision_keywords = ['decided', 'agreed', 'approved', 'rejected', 'confirmed', 'chosen']
    
    commitments = 0
    questions = 0
    decisions = 0
    
    for msg in messages:
        text = msg.get('text', '').lower()
        
        # Check for commitment indicators
        if any(keyword in text for keyword in commitment_keywords):
            commitments += 1
            
        # Check for questions
        if any(keyword in text for keyword in question_keywords):
            questions += 1
            
        # Check for decisions
        if any(keyword in text for keyword in decision_keywords):
            decisions += 1
    
    return {
        'potential_commitments': commitments,
        'questions': questions,  
        'decisions': decisions
    }


def format_filtered_brief_response(brief_result: Dict[str, Any]) -> str:
    """
    Format filtered brief results for display
    
    Args:
        brief_result: Result from execute_filtered_brief()
        
    Returns:
        Formatted string for display
    """
    if brief_result.get("error"):
        return f"❌ Brief Error: {brief_result['error']}"
    
    period = brief_result.get("period", "daily")
    data = brief_result.get("data", {})
    
    # Build response with filtering info and personalization awareness
    is_personalized = data.get('personalization_applied', False)
    
    if is_personalized:
        response = f"📋 **{period.title()} Brief** (Bot-Filtered + Personalized)\n\n"
        
        # Show user highlights first if available
        if 'user_highlights' in data and data['user_highlights']:
            user_highlights = data['user_highlights'][:5]  # Top 5 user highlights
            response += f"🎯 **Your Key Activities:**\n"
            for i, highlight in enumerate(user_highlights, 1):
                response += f"{i}. {highlight}\n"
            response += "\n"
    else:
        response = f"📋 **{period.title()} Brief** (Bot-Filtered)\n\n"
    
    # Show filtering effectiveness
    filtering = data.get('filtering_results', {})
    if filtering:
        response += f"🤖 **Bot Filtering**: Removed {filtering['noise_reduction']} noise\n"
        response += f"   ({filtering['bot_messages_filtered']} bot messages filtered out)\n\n"
    
    # Slack activity
    if 'slack_activity' in data:
        slack = data['slack_activity']
        response += f"💬 **Human Communication**: {slack['message_count']} messages\n"
        response += f"   📢 Active channels: {slack['active_channels']}\n"
        response += f"   👥 Active users: {slack['active_users']}\n"
        response += f"   📊 Avg per user: {slack['avg_messages_per_user']:.1f} messages\n\n"
        
        # Top channels
        if slack.get('top_channels'):
            response += f"**Most Active Channels:**\n"
            for i, (channel, count) in enumerate(slack['top_channels'][:3], 1):
                response += f"   {i}. #{channel}: {count} messages\n"
            response += "\n"
    
    # Communication insights
    if 'communication_insights' in data:
        insights = data['communication_insights']
        response += f"🎯 **Communication Insights**:\n"
        response += f"   💼 Potential commitments: {insights['commitment_indicators']}\n"
        response += f"   ❓ Questions asked: {insights['questions_asked']}\n"
        response += f"   ✅ Decisions mentioned: {insights['decisions_mentioned']}\n\n"
        
        # Content themes
        if insights.get('content_themes'):
            response += f"**Trending Topics:**\n"
            for word, count in insights['content_themes'][:5]:
                response += f"   • \"{word}\": {count} mentions\n"
    
    # Add generation metadata
    metadata = data.get('generation_metadata', {})
    if metadata.get('data_date'):
        response += f"\n📅 *Data from {metadata['data_date']}*"
    
    return response


# CLI interface for testing
if __name__ == "__main__":
    print("📋 Filtered Brief Command - Testing Mode")
    print("=" * 50)
    
    try:
        result = execute_filtered_brief("day")
        print(f"Brief generation: {'✅ Success' if not result.get('error') else '❌ Error'}")
        
        if result.get('error'):
            print(f"Error: {result['error']}")
        else:
            formatted = format_filtered_brief_response(result)
            print("\nFormatted Brief:")
            print("-" * 30)
            print(formatted)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()