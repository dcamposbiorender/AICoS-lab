#!/usr/bin/env python3
"""
Brief Personalizer - Brief Content Personalization for AI Chief of Staff

Personalizes daily briefs to focus on PRIMARY_USER's activities, commitments, and mentions.
Transforms generic briefs into user-centric actionable insights.

References:
- src/personalization/simple_filter.py - Core filtering patterns
- src/bot/commands/brief.py - Brief generation structure
- src/bot/commands/filtered_brief.py - Brief filtering patterns
- tasks/phase6_agent_l_personalization.md - Complete specification
"""

import logging
from typing import Any, Dict, List, Optional, Set, Tuple
from collections import Counter, defaultdict
from datetime import datetime, date
from .simple_filter import SimpleFilter

logger = logging.getLogger(__name__)

class BriefPersonalizer:
    """
    Personalize brief content for PRIMARY_USER
    
    Features:
    - Prioritizes user's activities and commitments in briefs
    - Extracts user-specific highlights and action items
    - Personalizes Slack, calendar, and drive activity summaries
    - Maintains backwards compatibility without PRIMARY_USER
    - Integrates seamlessly with existing brief generation
    
    Usage:
        personalizer = BriefPersonalizer()
        personalized_data = personalizer.personalize_brief_data(brief_data)
        highlights = personalizer.extract_user_highlights(brief_data)
    """
    
    def __init__(self, simple_filter: Optional[SimpleFilter] = None):
        """
        Initialize BriefPersonalizer
        
        Args:
            simple_filter: Optional SimpleFilter instance for user detection
        """
        self.filter = simple_filter or SimpleFilter()
        
        if self.filter.primary_user:
            logger.info(f"✅ BriefPersonalizer initialized with PRIMARY_USER: {self.filter.primary_user['email']}")
        else:
            logger.info("ℹ️ BriefPersonalizer initialized without PRIMARY_USER (no personalization)")
    
    def personalize_brief_data(self, brief_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply personalization to brief data
        
        Args:
            brief_data: Raw brief data from activity analyzer
            
        Returns:
            Personalized brief data with user highlights
        """
        if not brief_data:
            return brief_data
            
        if not self.filter.primary_user:
            return brief_data  # No personalization without PRIMARY_USER
            
        logger.debug("🎯 Applying brief personalization")
        
        # Create personalized copy
        personalized_data = brief_data.copy()
        
        # Personalize individual sections
        if 'slack_activity' in personalized_data:
            personalized_data['slack_activity'] = self.personalize_slack_activity(
                personalized_data['slack_activity']
            )
            
        if 'calendar_activity' in personalized_data:
            personalized_data['calendar_activity'] = self.personalize_calendar_activity(
                personalized_data['calendar_activity']
            )
            
        if 'drive_activity' in personalized_data:
            personalized_data['drive_activity'] = self.personalize_drive_activity(
                personalized_data['drive_activity']
            )
            
        # Add user-specific highlights section
        user_highlights = self.extract_user_highlights(brief_data)
        if user_highlights:
            personalized_data['user_highlights'] = user_highlights
            
        # Add personalization metadata
        personalized_data['personalization_applied'] = True
        personalized_data['primary_user'] = self.filter.primary_user['email']
        
        logger.info(f"✅ Brief personalized with {len(user_highlights)} user highlights")
        
        return personalized_data
    
    def personalize_slack_activity(self, slack_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Focus on user's Slack activity
        
        Args:
            slack_data: Slack activity data from brief
            
        Returns:
            Personalized Slack activity data
        """
        if not slack_data or not self.filter.primary_user:
            return slack_data
            
        user = self.filter.primary_user
        personalized_slack = slack_data.copy()
        
        # Analyze messages for user involvement
        messages = slack_data.get('messages', [])
        user_messages = []
        mentions_of_user = []
        
        user_slack_id = user.get('slack_id')
        user_name = user.get('name', '').split()[0].lower() if user.get('name') else ""
        
        for message in messages:
            # Count user's own messages
            if user_slack_id and message.get('user') == user_slack_id:
                user_messages.append(message)
                
            # Find mentions of the user
            text = message.get('text', '').lower()
            if (user_slack_id and user_slack_id in text) or \
               (user_name and f'@{user_name}' in text):
                mentions_of_user.append(message)
        
        # Add user-specific metrics
        personalized_slack['user_message_count'] = len(user_messages)
        personalized_slack['mentions_of_user'] = len(mentions_of_user)
        personalized_slack['user_participation_rate'] = (
            len(user_messages) / len(messages) * 100 if messages else 0
        )
        
        # Highlight active channels for user
        user_channels = Counter()
        for message in user_messages:
            channel = message.get('channel', 'unknown')
            user_channels[channel] += 1
            
        personalized_slack['user_active_channels'] = list(user_channels.keys())
        personalized_slack['user_top_channels'] = user_channels.most_common(3)
        
        return personalized_slack
    
    def personalize_calendar_activity(self, calendar_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Focus on user's calendar activity
        
        Args:
            calendar_data: Calendar activity data from brief
            
        Returns:
            Personalized calendar activity data
        """
        if not calendar_data or not self.filter.primary_user:
            return calendar_data
            
        user = self.filter.primary_user
        personalized_calendar = calendar_data.copy()
        
        # Analyze meetings for user involvement
        meetings = calendar_data.get('meetings', [])
        user_organized = []
        user_attended = []
        
        user_email = user.get('email', '').lower()
        
        for meeting in meetings:
            # Check if user organized the meeting
            organizer = meeting.get('organizer', {})
            if isinstance(organizer, dict):
                organizer_email = organizer.get('email', '').lower()
            else:
                organizer_email = str(organizer).lower()
                
            if organizer_email == user_email:
                user_organized.append(meeting)
                
            # Check if user attended
            attendees = meeting.get('attendees', [])
            user_attended_meeting = False
            for attendee in attendees:
                attendee_email = ""
                if isinstance(attendee, dict):
                    attendee_email = attendee.get('email', '').lower()
                else:
                    attendee_email = str(attendee).lower()
                    
                if attendee_email == user_email:
                    user_attended_meeting = True
                    user_attended.append(meeting)
                    break
        
        # Add user-specific metrics
        personalized_calendar['meetings_organized'] = len(user_organized)
        personalized_calendar['meetings_attended'] = len(user_attended)
        personalized_calendar['user_meeting_load'] = len(set(
            [m.get('id') for m in user_organized] + [m.get('id') for m in user_attended]
        ))
        
        # Calculate user's meeting time
        user_meeting_hours = self._calculate_user_meeting_time(user_organized + user_attended)
        personalized_calendar['user_meeting_hours'] = user_meeting_hours
        
        return personalized_calendar
    
    def personalize_drive_activity(self, drive_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Focus on user's Drive activity
        
        Args:
            drive_data: Drive activity data from brief
            
        Returns:
            Personalized Drive activity data
        """
        if not drive_data or not self.filter.primary_user:
            return drive_data
            
        user = self.filter.primary_user
        personalized_drive = drive_data.copy()
        
        # Analyze files for user involvement
        files = drive_data.get('files', [])
        user_created = []
        user_modified = []
        
        user_email = user.get('email', '').lower()
        
        for file_info in files:
            author = file_info.get('author', '').lower()
            last_modified_by = file_info.get('last_modified_by', '').lower()
            
            if author == user_email:
                user_created.append(file_info)
                
            if last_modified_by == user_email:
                user_modified.append(file_info)
        
        # Add user-specific metrics
        personalized_drive['files_created_by_user'] = len(user_created)
        personalized_drive['files_modified_by_user'] = len(user_modified)
        personalized_drive['user_file_activity'] = len(set(
            [f.get('id', f.get('name')) for f in user_created + user_modified]
        ))
        
        return personalized_drive
    
    def extract_user_highlights(self, brief_data: Dict[str, Any]) -> List[str]:
        """
        Extract highlights relevant to the user
        
        Args:
            brief_data: Complete brief data
            
        Returns:
            List of user-specific highlights (max 5)
        """
        if not self.filter.primary_user or not brief_data:
            return []
            
        highlights = []
        user = self.filter.primary_user
        
        # Extract highlights from each section
        highlights.extend(self._extract_slack_highlights(brief_data))
        highlights.extend(self._extract_calendar_highlights(brief_data))
        highlights.extend(self._extract_drive_highlights(brief_data))
        highlights.extend(self._extract_commitment_highlights(brief_data))
        
        # Sort by relevance and return top 5
        prioritized_highlights = self._prioritize_highlights(highlights)
        return prioritized_highlights[:5]
    
    def _extract_slack_highlights(self, brief_data: Dict[str, Any]) -> List[str]:
        """Extract user-relevant Slack highlights"""
        highlights = []
        slack_data = brief_data.get('slack_activity', {})
        
        if not slack_data:
            return highlights
            
        user_messages = slack_data.get('user_message_count', 0)
        mentions = slack_data.get('mentions_of_user', 0)
        participation_rate = slack_data.get('user_participation_rate', 0)
        
        if user_messages > 0:
            highlights.append(f"You sent {user_messages} messages across Slack")
            
        if mentions > 0:
            highlights.append(f"You were mentioned {mentions} times in conversations")
            
        if participation_rate > 50:
            highlights.append(f"High Slack engagement: {participation_rate:.0f}% of messages")
            
        # Active channels
        user_channels = slack_data.get('user_active_channels', [])
        if len(user_channels) > 3:
            highlights.append(f"Active in {len(user_channels)} channels today")
            
        return highlights
    
    def _extract_calendar_highlights(self, brief_data: Dict[str, Any]) -> List[str]:
        """Extract user-relevant calendar highlights"""
        highlights = []
        calendar_data = brief_data.get('calendar_activity', {})
        
        if not calendar_data:
            return highlights
            
        organized = calendar_data.get('meetings_organized', 0)
        attended = calendar_data.get('meetings_attended', 0)
        meeting_hours = calendar_data.get('user_meeting_hours', 0)
        
        if organized > 0:
            highlights.append(f"You organized {organized} meeting{'s' if organized != 1 else ''}")
            
        if attended > 0:
            highlights.append(f"You attended {attended} meeting{'s' if attended != 1 else ''}")
            
        if meeting_hours > 4:
            highlights.append(f"Heavy meeting day: {meeting_hours:.1f} hours in meetings")
        elif meeting_hours > 0:
            highlights.append(f"{meeting_hours:.1f} hours in meetings today")
            
        return highlights
    
    def _extract_drive_highlights(self, brief_data: Dict[str, Any]) -> List[str]:
        """Extract user-relevant Drive highlights"""
        highlights = []
        drive_data = brief_data.get('drive_activity', {})
        
        if not drive_data:
            return highlights
            
        created = drive_data.get('files_created_by_user', 0)
        modified = drive_data.get('files_modified_by_user', 0)
        
        if created > 0:
            highlights.append(f"You created {created} new document{'s' if created != 1 else ''}")
            
        if modified > 0:
            highlights.append(f"You modified {modified} document{'s' if modified != 1 else ''}")
            
        return highlights
    
    def _extract_commitment_highlights(self, brief_data: Dict[str, Any]) -> List[str]:
        """Extract commitment-related highlights"""
        highlights = []
        
        # Look for commitment indicators in various sections
        # This is a simplified version - could be enhanced with commitment extraction
        
        slack_data = brief_data.get('slack_activity', {})
        messages = slack_data.get('messages', [])
        
        commitment_keywords = ['will', 'todo', 'task', 'deadline', 'deliver', 'complete']
        user_slack_id = self.filter.primary_user.get('slack_id')
        
        user_commitments = 0
        for message in messages:
            if message.get('user') == user_slack_id:
                text = message.get('text', '').lower()
                if any(keyword in text for keyword in commitment_keywords):
                    user_commitments += 1
                    
        if user_commitments > 0:
            highlights.append(f"Made {user_commitments} commitment{'s' if user_commitments != 1 else ''} in Slack")
            
        return highlights
    
    def _prioritize_highlights(self, highlights: List[str]) -> List[str]:
        """Sort highlights by importance/relevance"""
        if not highlights:
            return []
            
        # Simple prioritization - could be enhanced with scoring
        priority_keywords = {
            'organized': 3,
            'mentioned': 3,
            'commitment': 3,
            'heavy': 2,
            'created': 2,
            'attended': 1,
            'modified': 1,
            'active': 1
        }
        
        def highlight_score(highlight: str) -> int:
            score = 0
            highlight_lower = highlight.lower()
            for keyword, points in priority_keywords.items():
                if keyword in highlight_lower:
                    score += points
            return score
        
        # Sort by score, then alphabetically for consistency
        return sorted(highlights, key=lambda h: (-highlight_score(h), h))
    
    def _calculate_user_meeting_time(self, meetings: List[Dict[str, Any]]) -> float:
        """Calculate total meeting time for user"""
        total_minutes = 0
        
        for meeting in meetings:
            start_time = meeting.get('start_datetime') or meeting.get('start')
            end_time = meeting.get('end_datetime') or meeting.get('end')
            
            if start_time and end_time:
                try:
                    if isinstance(start_time, str):
                        start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    else:
                        start_dt = start_time
                        
                    if isinstance(end_time, str):
                        end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                    else:
                        end_dt = end_time
                        
                    duration = end_dt - start_dt
                    total_minutes += duration.total_seconds() / 60
                    
                except (ValueError, TypeError):
                    total_minutes += 60  # Default 1 hour
            else:
                total_minutes += 60  # Default 1 hour
                
        return total_minutes / 60  # Convert to hours
    
    def get_personalization_summary(self, original_data: Dict[str, Any], 
                                  personalized_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate summary of personalization applied
        
        Args:
            original_data: Original brief data
            personalized_data: Personalized brief data
            
        Returns:
            Summary of personalization changes
        """
        if not self.filter.primary_user:
            return {"personalization_applied": False}
            
        user_highlights = personalized_data.get('user_highlights', [])
        slack_personalized = 'user_message_count' in personalized_data.get('slack_activity', {})
        calendar_personalized = 'meetings_organized' in personalized_data.get('calendar_activity', {})
        drive_personalized = 'files_created_by_user' in personalized_data.get('drive_activity', {})
        
        return {
            "personalization_applied": True,
            "primary_user": self.filter.primary_user['email'],
            "user_highlights_count": len(user_highlights),
            "slack_personalized": slack_personalized,
            "calendar_personalized": calendar_personalized,
            "drive_personalized": drive_personalized,
            "enhancement_areas": [
                area for area, enabled in [
                    ("slack", slack_personalized),
                    ("calendar", calendar_personalized), 
                    ("drive", drive_personalized)
                ] if enabled
            ]
        }

# Convenience function for brief integration
def apply_brief_personalization(brief_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience function to apply personalization to brief data
    
    Args:
        brief_data: Raw brief data from activity analyzer
        
    Returns:
        Personalized brief data
    """
    personalizer = BriefPersonalizer()
    return personalizer.personalize_brief_data(brief_data)

if __name__ == "__main__":
    # Test the BriefPersonalizer system
    print("🧪 Testing BriefPersonalizer System")
    print("=" * 40)
    
    # Initialize personalizer
    personalizer = BriefPersonalizer()
    
    if personalizer.filter.primary_user:
        user_email = personalizer.filter.primary_user['email']
        user_slack_id = personalizer.filter.primary_user.get('slack_id', 'U123456789')
        print(f"✅ PRIMARY_USER configured: {user_email}")
        
        # Create test brief data
        test_brief_data = {
            'slack_activity': {
                'message_count': 50,
                'messages': [
                    {'user': user_slack_id, 'text': 'User message', 'channel': '#leadership'},
                    {'user': 'U987654321', 'text': f'Message mentioning {user_email}', 'channel': '#general'},
                    {'user': user_slack_id, 'text': 'Another user message with deadline', 'channel': '#team'}
                ]
            },
            'calendar_activity': {
                'meeting_count': 5,
                'meetings': [
                    {'organizer': {'email': user_email}, 'title': 'User organized meeting',
                     'start_datetime': '2025-08-28T09:00:00', 'end_datetime': '2025-08-28T10:00:00'},
                    {'attendees': [{'email': user_email}, {'email': 'other@company.com'}], 
                     'title': 'User attended meeting',
                     'start_datetime': '2025-08-28T11:00:00', 'end_datetime': '2025-08-28T12:00:00'},
                ]
            },
            'drive_activity': {
                'files_modified': 10,
                'files': [
                    {'author': user_email, 'name': 'User document'},
                    {'author': 'other@company.com', 'name': 'Other document'}
                ]
            }
        }
        
        # Apply personalization
        personalized_data = personalizer.personalize_brief_data(test_brief_data)
        
        print(f"\n🎯 Personalization results:")
        print(f"  User highlights: {len(personalized_data.get('user_highlights', []))}")
        
        for highlight in personalized_data.get('user_highlights', []):
            print(f"    • {highlight}")
        
        # Show personalized metrics
        slack_data = personalized_data.get('slack_activity', {})
        print(f"\n💬 Slack personalization:")
        print(f"  User messages: {slack_data.get('user_message_count', 0)}")
        print(f"  Mentions of user: {slack_data.get('mentions_of_user', 0)}")
        
        calendar_data = personalized_data.get('calendar_activity', {})
        print(f"\n📅 Calendar personalization:")
        print(f"  Meetings organized: {calendar_data.get('meetings_organized', 0)}")
        print(f"  Meetings attended: {calendar_data.get('meetings_attended', 0)}")
        
        # Get personalization summary
        summary = personalizer.get_personalization_summary(test_brief_data, personalized_data)
        print(f"\n📊 Personalization summary:")
        print(f"  Enhanced areas: {', '.join(summary.get('enhancement_areas', []))}")
        
    else:
        print("ℹ️ No PRIMARY_USER configured (no personalization)")
        print("  Briefs will be generated without user focus")
        
    print("\n✅ BriefPersonalizer system test complete")