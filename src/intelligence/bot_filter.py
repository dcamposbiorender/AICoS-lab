#!/usr/bin/env python3
"""
Bot Filter - Simple and Effective Bot Detection for AI Chief of Staff

This module provides three-layer bot detection:
1. Known bot blocklist (hardcoded spam accounts)  
2. Slack metadata check (is_bot, is_app_user flags)
3. Pattern detection (bot-like IDs and message content)

References:
- User metadata from slack collector (users.json)
- Message patterns from commitment extractor analysis
- ID patterns observed in production Slack workspaces
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from collections import Counter

logger = logging.getLogger(__name__)


class BotFilter:
    """
    Three-layer bot detection system for filtering automated/spam messages
    
    Designed for high accuracy with minimal complexity - focuses on the
    most obvious bots that generate the most noise in communication analysis.
    """
    
    def __init__(self, users_data_path: Optional[str] = None):
        """
        Initialize bot filter with known patterns and user metadata
        
        Args:
            users_data_path: Optional path to users.json file
        """
        # Layer 1: Known spam/bot accounts
        self.known_bots = {
            'U029AEQSRGX',  # Upgrade spam bot - 1094 messages
            'U085JS424D6',  # Update notifications - 213 messages  
            'U07K6MX167P',  # Incident bot
            'U081KDFTFDZ',  # On-call bot  
            'U08UXCV6EAU',  # Devin bot
            'USLACKBOT',    # Slack system bot
            'U08J5R35RMJ',  # Deal notification bot - 545 messages
        }
        
        # Layer 2: Load user metadata for is_bot flags
        self.users_data = {}
        if users_data_path:
            self.load_user_metadata(users_data_path)
        
        # Layer 3: Compile bot patterns
        self._compile_bot_patterns()
        
        logger.info(f"Bot Filter initialized with {len(self.known_bots)} known bots")
    
    def load_user_metadata(self, users_file: str) -> None:
        """Load user metadata from Slack users.json file"""
        try:
            users_path = Path(users_file)
            if users_path.exists():
                with open(users_path) as f:
                    self.users_data = json.load(f)
                logger.info(f"Loaded {len(self.users_data)} users from metadata")
            else:
                logger.warning(f"Users file not found: {users_file}")
        except Exception as e:
            logger.error(f"Error loading user metadata: {e}")
            self.users_data = {}
    
    def _compile_bot_patterns(self) -> None:
        """Compile patterns for bot detection"""
        
        # Message content patterns that indicate bots
        self.bot_message_patterns = [
            'Whoo upgrade!',
            'New Deal Closed',
            'Incident #',
            'on call',
            'created an update',
            'Devin is available',
            'Zendesk ticket #',
        ]
        
        # User ID patterns that suggest bots
        self.bot_id_keywords = [
            'BOT', 'APP', 'SLACK', 'SERVICE',
            'SYSTEM', 'ALERT', 'NOTIFY', 'AUTO'
        ]
        
        logger.info("Compiled bot detection patterns")
    
    def is_bot(self, user_id: str, message_text: Optional[str] = None, 
               metadata: Optional[Dict] = None) -> bool:
        """
        Determine if a user/message is from a bot using three-layer detection
        
        Args:
            user_id: Slack user ID
            message_text: Optional message content to analyze
            metadata: Optional additional metadata
            
        Returns:
            True if bot, False if human
        """
        # Layer 1: Known bot blocklist
        if user_id in self.known_bots:
            return True
        
        # Layer 2: Slack metadata check
        if self._check_slack_metadata(user_id):
            return True
        
        # Layer 3: Pattern detection
        if self._looks_like_bot_id(user_id):
            return True
            
        if message_text and self._has_bot_message_pattern(message_text):
            return True
        
        return False
    
    def _check_slack_metadata(self, user_id: str) -> bool:
        """Check Slack's is_bot and is_app_user flags"""
        if user_id in self.users_data:
            user_data = self.users_data[user_id]
            if user_data.get('is_bot', False):
                return True
            if user_data.get('is_app_user', False):
                return True
        return False
    
    def _looks_like_bot_id(self, user_id: str) -> bool:
        """Detect bot-like user IDs through pattern analysis"""
        
        # Check for bot-related keywords in ID
        user_upper = user_id.upper()
        if any(keyword in user_upper for keyword in self.bot_id_keywords):
            return True
        
        # Check for high entropy (random-looking IDs)
        # Human IDs sometimes have memorable patterns, bots are often pure random
        if len(user_id) > 8:  # Long IDs only
            digit_count = sum(1 for c in user_id if c.isdigit())
            letter_count = sum(1 for c in user_id if c.isalpha())
            
            # High digit + letter count suggests random generation
            if digit_count >= 6 and letter_count >= 6:
                # Additional check: no repeated patterns (humans sometimes have these)
                if not any(char * 2 in user_id for char in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'):
                    return True
        
        return False
    
    def _has_bot_message_pattern(self, message_text: str) -> bool:
        """Check if message content matches bot patterns"""
        for pattern in self.bot_message_patterns:
            if pattern in message_text:
                return True
        return False
    
    def filter_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter out bot messages from a list of messages
        
        Args:
            messages: List of message dictionaries with 'user' and 'text' keys
            
        Returns:
            List of human messages only
        """
        human_messages = []
        for msg in messages:
            user_id = msg.get('user', '')
            message_text = msg.get('text', '')
            
            if not self.is_bot(user_id, message_text):
                human_messages.append(msg)
        
        return human_messages
    
    def get_bot_statistics(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate statistics about bot vs human message distribution
        
        Args:
            messages: List of all messages
            
        Returns:
            Dictionary with bot filtering statistics
        """
        total_messages = len(messages)
        bot_count = 0
        human_count = 0
        bot_users = set()
        human_users = set()
        
        for msg in messages:
            user_id = msg.get('user', '')
            message_text = msg.get('text', '')
            
            if self.is_bot(user_id, message_text):
                bot_count += 1
                bot_users.add(user_id)
            else:
                human_count += 1
                human_users.add(user_id)
        
        return {
            'total_messages': total_messages,
            'bot_messages': bot_count,
            'human_messages': human_count,
            'bot_percentage': (bot_count / total_messages * 100) if total_messages > 0 else 0,
            'bot_users': len(bot_users),
            'human_users': len(human_users),
            'filtering_effectiveness': {
                'messages_removed': bot_count,
                'noise_reduction': f"{bot_count / total_messages * 100:.1f}%" if total_messages > 0 else "0%"
            }
        }
    
    def add_known_bot(self, user_id: str) -> None:
        """Add a user ID to the known bots list"""
        self.known_bots.add(user_id)
        logger.info(f"Added {user_id} to known bots list")
    
    def get_known_bots(self) -> Set[str]:
        """Get the current set of known bot IDs"""
        return self.known_bots.copy()


def create_bot_filter(users_data_path: Optional[str] = None) -> BotFilter:
    """
    Factory function to create a bot filter instance
    
    Args:
        users_data_path: Optional path to users.json
        
    Returns:
        Configured BotFilter instance
    """
    return BotFilter(users_data_path)


# CLI interface for testing
if __name__ == "__main__":
    print("🤖 Bot Filter - Testing Mode")
    print("=" * 50)
    
    # Test with sample data
    filter_instance = BotFilter()
    
    # Test known bots
    test_cases = [
        ('U029AEQSRGX', 'Whoo upgrade!', True),   # Known spam bot
        ('USLACKBOT', 'Reminder message', True),   # System bot  
        ('U02AHB5BH2P', 'Hey team, how is everyone?', False),  # Human message
        ('U12345RANDOM', 'New Deal Closed Won!!!', True),  # Pattern match
        ('USERBOT123', 'Hello world', True),  # ID pattern
    ]
    
    print("Testing bot detection:")
    for user_id, message, expected in test_cases:
        result = filter_instance.is_bot(user_id, message)
        status = "✅" if result == expected else "❌"
        print(f"{status} {user_id}: {result} (expected {expected})")
    
    print("\n🎯 Bot Filter ready for integration!")