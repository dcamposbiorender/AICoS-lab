#!/usr/bin/env python3
"""
Simple Filter - Core Personalization Filtering for AI Chief of Staff

Provides user-centric data filtering and content boosting based on PRIMARY_USER configuration.
Maintains backwards compatibility when PRIMARY_USER is not configured.

References:
- src/core/user_identity.py - PRIMARY_USER configuration and identity mapping
- tasks/phase6_agent_l_personalization.md - Complete specification
- src/bot/commands/brief.py - Brief generation patterns
"""

import re
import logging
from typing import Any, Dict, List, Optional, Set
from pathlib import Path

logger = logging.getLogger(__name__)

class SimpleFilter:
    """
    Core personalization filtering for user-centric data presentation
    
    Features:
    - Identifies user-relevant data items across different sources
    - Boosts relevance scores for user-related content
    - Filters and organizes items with user content prioritized
    - Maintains backwards compatibility without PRIMARY_USER
    
    Usage:
        filter = SimpleFilter()
        if filter.is_user_relevant(data_item):
            # Prioritize this item
        boosted_items = filter.boost_user_content(items)
        filtered_items = filter.filter_for_user(items, user_first=True)
    """
    
    def __init__(self):
        """Initialize SimpleFilter with UserIdentity integration"""
        try:
            from src.core.user_identity import UserIdentity
            self.user_identity = UserIdentity()
            self.primary_user = self.user_identity.get_primary_user()
            
            if self.primary_user:
                logger.info(f"✅ SimpleFilter initialized with PRIMARY_USER: {self.primary_user['email']}")
            else:
                logger.info("ℹ️ SimpleFilter initialized without PRIMARY_USER (backwards compatible mode)")
                
        except Exception as e:
            logger.warning(f"⚠️ Could not initialize UserIdentity: {e}")
            self.user_identity = None
            self.primary_user = None
    
    def is_user_relevant(self, data_item: Any) -> bool:
        """
        Check if data item is relevant to primary user
        
        Args:
            data_item: Dictionary or object containing data item to check
            
        Returns:
            True if item involves primary user, True if no PRIMARY_USER configured
        """
        if not self.primary_user:
            return True  # No filtering if no PRIMARY_USER configured
            
        if not data_item:
            return False
            
        # Convert object to dictionary for consistent handling
        if hasattr(data_item, '__dict__') and not isinstance(data_item, dict):
            data_dict = vars(data_item)
        elif isinstance(data_item, dict):
            data_dict = data_item
        else:
            return False
            
        # Check various user identifiers
        return (
            self.involves_user_email(data_dict) or
            self.involves_user_slack(data_dict) or
            self.involves_user_calendar(data_dict) or
            self.involves_user_metadata(data_dict)
        )
    
    def involves_user_email(self, data_item: Dict[str, Any]) -> bool:
        """Check if data item involves user's email"""
        if not self.primary_user:
            return False
            
        user_email = self.primary_user.get("email", "").lower()
        if not user_email:
            return False
            
        # Check common email fields
        email_fields = [
            "email", "user_email", "author", "organizer", 
            "from_email", "sender", "creator"
        ]
        
        for field in email_fields:
            value = data_item.get(field)
            if value and isinstance(value, str) and value.lower() == user_email:
                return True
                
        # Check email in content/text
        content_fields = ["content", "text", "body", "description", "message"]
        for field in content_fields:
            content = data_item.get(field)
            if content and isinstance(content, str) and user_email in content.lower():
                return True
                
        # Check nested organizer object (calendar events)
        organizer = data_item.get("organizer")
        if isinstance(organizer, dict) and organizer.get("email", "").lower() == user_email:
            return True
            
        return False
    
    def involves_user_slack(self, data_item: Dict[str, Any]) -> bool:
        """Check if data item involves user's Slack ID"""
        if not self.primary_user:
            return False
            
        user_slack_id = self.primary_user.get("slack_id")
        if not user_slack_id:
            return False
            
        # Check common Slack ID fields
        slack_fields = ["user", "user_id", "slack_id", "sender_id", "author_id"]
        
        for field in slack_fields:
            value = data_item.get(field)
            if value and str(value) == str(user_slack_id):
                return True
                
        # Check Slack ID in content/text
        content_fields = ["content", "text", "body", "message"]
        for field in content_fields:
            content = data_item.get(field)
            if content and isinstance(content, str) and user_slack_id in content:
                return True
                
        # Check mentions pattern @username
        user_name = self.primary_user.get("name", "")
        if user_name and content_fields:
            first_name = user_name.split()[0].lower() if user_name else ""
            for field in content_fields:
                content = data_item.get(field)
                if content and isinstance(content, str):
                    mention_pattern = f"@{first_name}"
                    if mention_pattern in content.lower():
                        return True
                        
        return False
    
    def involves_user_calendar(self, data_item: Dict[str, Any]) -> bool:
        """Check if data item involves user in calendar context"""
        if not self.primary_user:
            return False
            
        user_email = self.primary_user.get("email", "").lower()
        if not user_email:
            return False
            
        # Check attendees list
        attendees = data_item.get("attendees", [])
        if isinstance(attendees, list):
            for attendee in attendees:
                if isinstance(attendee, str) and attendee.lower() == user_email:
                    return True
                elif isinstance(attendee, dict) and attendee.get("email", "").lower() == user_email:
                    return True
                    
        # Check calendar-specific fields
        calendar_fields = ["calendar_id", "calendar", "owner"]
        for field in calendar_fields:
            value = data_item.get(field)
            if value and isinstance(value, str) and value.lower() == user_email:
                return True
                
        return False
    
    def involves_user_metadata(self, data_item: Dict[str, Any]) -> bool:
        """Check if data item involves user in metadata"""
        if not self.primary_user:
            return False
            
        metadata = data_item.get("metadata", {})
        if not isinstance(metadata, dict):
            return False
            
        user_email = self.primary_user.get("email", "").lower()
        user_slack_id = self.primary_user.get("slack_id")
        
        # Check metadata fields
        if user_email:
            metadata_email_fields = ["author", "creator", "owner", "user_email"]
            for field in metadata_email_fields:
                value = metadata.get(field)
                if value and isinstance(value, str) and value.lower() == user_email:
                    return True
                    
            # Check attendees in metadata
            attendees = metadata.get("attendees", [])
            if isinstance(attendees, list) and user_email in [str(a).lower() for a in attendees]:
                return True
                
        if user_slack_id:
            if metadata.get("user_id") == user_slack_id:
                return True
                
        return False
    
    def boost_user_content(self, items: List[Any], boost_factor: float = 1.5) -> List[Any]:
        """
        Boost relevance of user-related items
        
        Args:
            items: List of items to boost
            boost_factor: Multiplication factor for boosting (default 1.5)
            
        Returns:
            List of items with boosted scores, sorted by score descending
        """
        if not items:
            return []
            
        if not self.primary_user:
            return items  # No boosting without PRIMARY_USER
            
        # Apply boosting to user-relevant items
        for item in items:
            if self.is_user_relevant(item):
                # Boost score or relevance attribute
                if hasattr(item, 'score') and item.score is not None:
                    item.score *= boost_factor
                    if not hasattr(item, 'boosted'):
                        item.boosted = True
                elif hasattr(item, 'relevance') and item.relevance is not None:
                    item.relevance *= boost_factor
                    if not hasattr(item, 'boosted'):
                        item.boosted = True
                elif isinstance(item, dict):
                    # Handle dictionary items
                    if 'score' in item and item['score'] is not None:
                        item['score'] *= boost_factor
                        item['boosted'] = True
                    elif 'relevance' in item and item['relevance'] is not None:
                        item['relevance'] *= boost_factor
                        item['boosted'] = True
                        
        # Sort by score/relevance descending
        def get_sort_key(item):
            if hasattr(item, 'score') and item.score is not None:
                return item.score
            elif hasattr(item, 'relevance') and item.relevance is not None:
                return item.relevance
            elif isinstance(item, dict):
                return item.get('score', item.get('relevance', 0))
            return 0
            
        return sorted(items, key=get_sort_key, reverse=True)
    
    def filter_for_user(self, items: List[Any], include_others: bool = True, 
                       user_first: bool = True) -> List[Any]:
        """
        Filter and organize items with user content prioritized
        
        Args:
            items: List of items to filter
            include_others: Whether to include non-user items (default True)
            user_first: Whether to put user items first (default True)
            
        Returns:
            Filtered and organized list of items
        """
        if not items:
            return []
            
        if not self.primary_user:
            return items  # No filtering without PRIMARY_USER
            
        # Separate user-relevant and other items
        user_items = [item for item in items if self.is_user_relevant(item)]
        other_items = [item for item in items if not self.is_user_relevant(item)]
        
        # Return based on parameters
        if not include_others:
            return user_items
        elif user_first:
            # User items first, then limited others
            return user_items + other_items[:10]  # Limit other items to 10
        else:
            # Return all items unchanged
            return items

    def get_user_activity_summary(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate summary of user's activity from filtered items
        
        Args:
            items: List of data items to analyze
            
        Returns:
            Dictionary with user activity summary
        """
        if not self.primary_user or not items:
            return {}
            
        user_items = [item for item in items if self.is_user_relevant(item)]
        
        summary = {
            'total_items': len(items),
            'user_items': len(user_items),
            'user_percentage': (len(user_items) / len(items)) * 100 if items else 0,
            'primary_user': self.primary_user['email']
        }
        
        # Analyze by type
        type_counts = {}
        for item in user_items:
            item_type = item.get('type', 'unknown')
            type_counts[item_type] = type_counts.get(item_type, 0) + 1
            
        summary['activity_by_type'] = type_counts
        
        return summary

if __name__ == "__main__":
    # Test the SimpleFilter system
    print("🧪 Testing SimpleFilter System")
    print("=" * 40)
    
    # Initialize filter
    filter_instance = SimpleFilter()
    
    if filter_instance.primary_user:
        print(f"✅ PRIMARY_USER configured: {filter_instance.primary_user['email']}")
        
        # Test with sample data
        test_items = [
            {
                "type": "slack_message",
                "user_email": filter_instance.primary_user['email'],
                "content": "Test message from primary user"
            },
            {
                "type": "calendar_event", 
                "attendees": [filter_instance.primary_user['email'], "other@company.com"],
                "title": "Meeting with primary user"
            },
            {
                "type": "drive_file",
                "author": "other@company.com", 
                "content": "Document without primary user"
            }
        ]
        
        print(f"\n🔍 Testing relevance detection:")
        for i, item in enumerate(test_items):
            relevant = filter_instance.is_user_relevant(item)
            print(f"  Item {i+1}: {relevant}")
            
        print(f"\n📊 User activity summary:")
        summary = filter_instance.get_user_activity_summary(test_items)
        print(f"  User items: {summary['user_items']}/{summary['total_items']} ({summary['user_percentage']:.1f}%)")
        
    else:
        print("ℹ️ No PRIMARY_USER configured (backwards compatible mode)")
        print("  All items will be treated equally")
        
    print("\n✅ SimpleFilter system test complete")