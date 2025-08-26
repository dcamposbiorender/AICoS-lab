#!/usr/bin/env python3
"""
Slack Timeline Correlator - Phase 5B Enhancement
Extends the Phase 3 correlator to integrate Slack conversation timelines with meeting records.
Provides temporal and contextual correlation between meetings and Slack discussions.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum

from .meeting_correlator import MeetingCorrelator, CorrelationStrategy, CompositeMatchResult
from .correlation_models import CorrelatedMeeting, CorrelationMatch, MatchType, CorrelationStatus
from ..collectors.slack_intelligence import SlackIntelligence, MeetingIntent
from ..extractors.slack_structured import SlackStructuredExtractor, SlackMentionContext

logger = logging.getLogger(__name__)


@dataclass
class SlackTimelineContext:
    """Context from Slack conversations around meeting timeframe"""
    channel_id: str
    channel_name: str
    messages: List[Dict[str, Any]]
    meeting_intents: List[MeetingIntent]
    mention_contexts: List[SlackMentionContext]
    conversation_score: float
    time_range: Tuple[datetime, datetime]
    participants: Set[str]


@dataclass
class SlackCorrelationMatch(CorrelationMatch):
    """Extended correlation match including Slack timeline context"""
    slack_context: Optional[SlackTimelineContext] = None
    pre_meeting_discussions: List[Dict[str, Any]] = field(default_factory=list)
    post_meeting_discussions: List[Dict[str, Any]] = field(default_factory=list)
    scheduling_messages: List[Dict[str, Any]] = field(default_factory=list)
    slack_confidence_boost: float = 0.0


@dataclass
class EnhancedCorrelatedMeeting(CorrelatedMeeting):
    """Enhanced correlated meeting with Slack timeline integration"""
    slack_timeline: Optional[SlackTimelineContext] = None
    scheduling_timeline: List[Dict[str, Any]] = field(default_factory=list)
    discussion_summary: Optional[str] = None
    slack_participant_mapping: Dict[str, str] = field(default_factory=dict)  # slack_id -> name/email
    meeting_coordination_score: float = 0.0


class SlackTimelineCorrelator(MeetingCorrelator):
    """
    Enhanced correlator that integrates Slack conversation timelines
    with meeting records from Phase 3 correlation
    """
    
    def __init__(self, 
                 slack_intelligence: SlackIntelligence,
                 slack_extractor: SlackStructuredExtractor,
                 correlation_strategy: CorrelationStrategy = CorrelationStrategy.COMPOSITE):
        super().__init__(correlation_strategy)
        self.slack_intelligence = slack_intelligence
        self.slack_extractor = slack_extractor
        
        # Timeline analysis settings
        self.pre_meeting_window_hours = 72  # Look 3 days before meeting
        self.post_meeting_window_hours = 24  # Look 1 day after meeting
        self.scheduling_window_hours = 168  # Look 1 week for scheduling discussions
        
        # Correlation thresholds
        self.slack_correlation_threshold = 0.6
        self.participant_overlap_threshold = 0.3
    
    def correlate_with_slack_timeline(self, 
                                     correlated_meetings: List[CorrelatedMeeting],
                                     slack_conversations: Dict[str, List[Dict[str, Any]]]) -> List[EnhancedCorrelatedMeeting]:
        """
        Enhance existing correlated meetings with Slack timeline context
        """
        enhanced_meetings = []
        
        print(f"🔗 Enhancing {len(correlated_meetings)} meetings with Slack timeline context")
        
        for meeting in correlated_meetings:
            enhanced = self._enhance_meeting_with_slack(meeting, slack_conversations)
            enhanced_meetings.append(enhanced)
        
        print(f"✅ Enhanced {len(enhanced_meetings)} meetings with Slack context")
        
        return enhanced_meetings
    
    def find_slack_meeting_discussions(self, 
                                     meeting_time: datetime,
                                     participants: List[str],
                                     slack_conversations: Dict[str, List[Dict[str, Any]]]) -> List[SlackTimelineContext]:
        """
        Find Slack discussions related to a specific meeting
        """
        timeline_contexts = []
        
        # Calculate search windows
        pre_window_start = meeting_time - timedelta(hours=self.pre_meeting_window_hours)
        post_window_end = meeting_time + timedelta(hours=self.post_meeting_window_hours)
        
        for channel_id, messages in slack_conversations.items():
            context = self._analyze_channel_for_meeting(
                channel_id, messages, meeting_time, participants, 
                pre_window_start, post_window_end
            )
            
            if context and context.conversation_score >= self.slack_correlation_threshold:
                timeline_contexts.append(context)
        
        # Sort by conversation relevance score
        timeline_contexts.sort(key=lambda x: x.conversation_score, reverse=True)
        
        return timeline_contexts
    
    def identify_scheduling_conversations(self,
                                        meeting_time: datetime,
                                        participants: List[str],
                                        slack_conversations: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """
        Identify Slack conversations that were used to schedule the meeting
        """
        scheduling_messages = []
        
        # Look for scheduling discussions in the weeks before the meeting
        scheduling_window_start = meeting_time - timedelta(hours=self.scheduling_window_hours)
        
        for channel_id, messages in slack_conversations.items():
            channel_scheduling = self._find_scheduling_messages(
                messages, scheduling_window_start, meeting_time, participants
            )
            
            for msg in channel_scheduling:
                msg['channel_id'] = channel_id
                scheduling_messages.append(msg)
        
        # Sort chronologically (earliest scheduling first)
        scheduling_messages.sort(key=lambda x: x.get('ts', 0))
        
        return scheduling_messages
    
    def _enhance_meeting_with_slack(self, 
                                   meeting: CorrelatedMeeting,
                                   slack_conversations: Dict[str, List[Dict[str, Any]]]) -> EnhancedCorrelatedMeeting:
        """
        Enhance a single meeting with Slack timeline context
        """
        # Extract meeting time from email or doc metadata
        meeting_time = self._extract_meeting_time(meeting)
        if not meeting_time:
            # If we can't determine meeting time, return basic enhancement
            return EnhancedCorrelatedMeeting(
                **meeting.__dict__,
                slack_timeline=None,
                scheduling_timeline=[],
                discussion_summary=None,
                slack_participant_mapping={},
                meeting_coordination_score=0.0
            )
        
        # Get participants list
        participants = self._extract_participants(meeting)
        
        # Find related Slack discussions
        timeline_contexts = self.find_slack_meeting_discussions(
            meeting_time, participants, slack_conversations
        )
        
        # Find scheduling conversations
        scheduling_timeline = self.identify_scheduling_conversations(
            meeting_time, participants, slack_conversations
        )
        
        # Select best timeline context
        primary_context = timeline_contexts[0] if timeline_contexts else None
        
        # Generate discussion summary if we have context
        discussion_summary = None
        if primary_context:
            discussion_summary = self._generate_discussion_summary(primary_context)
        
        # Create participant mapping
        slack_participant_mapping = self._create_participant_mapping(
            participants, timeline_contexts + ([primary_context] if primary_context else [])
        )
        
        # Calculate meeting coordination score
        coordination_score = self._calculate_coordination_score(
            meeting, timeline_contexts, scheduling_timeline
        )
        
        return EnhancedCorrelatedMeeting(
            **meeting.__dict__,
            slack_timeline=primary_context,
            scheduling_timeline=scheduling_timeline,
            discussion_summary=discussion_summary,
            slack_participant_mapping=slack_participant_mapping,
            meeting_coordination_score=coordination_score
        )
    
    def _analyze_channel_for_meeting(self,
                                   channel_id: str,
                                   messages: List[Dict[str, Any]],
                                   meeting_time: datetime,
                                   participants: List[str],
                                   start_time: datetime,
                                   end_time: datetime) -> Optional[SlackTimelineContext]:
        """
        Analyze a Slack channel for meeting-related discussions
        """
        # Filter messages to time window
        relevant_messages = []
        for msg in messages:
            msg_time = datetime.fromtimestamp(float(msg.get('ts', 0)), tz=timezone.utc)
            if start_time <= msg_time <= end_time:
                relevant_messages.append(msg)
        
        if not relevant_messages:
            return None
        
        # Analyze messages for meeting content
        meeting_intents = []
        mention_contexts = []
        conversation_participants = set()
        
        for msg in relevant_messages:
            # Use slack intelligence to detect meeting intents
            enhanced_data = self.slack_intelligence.enhance_conversation_analytics({
                'messages': [msg],
                'channel_info': {'id': channel_id, 'name': f'channel_{channel_id}'}
            })
            
            if 'meeting_intents' in enhanced_data:
                meeting_intents.extend(enhanced_data['meeting_intents'])
            
            # Extract mention contexts
            msg_mentions = self.slack_extractor.extract_slack_mentions_with_context(msg)
            mention_contexts.extend(msg_mentions)
            
            # Track participants
            if msg.get('user'):
                conversation_participants.add(msg.get('user'))
        
        # Calculate conversation relevance score
        conversation_score = self._calculate_conversation_relevance(
            relevant_messages, meeting_intents, mention_contexts, 
            participants, conversation_participants
        )
        
        if conversation_score < self.slack_correlation_threshold:
            return None
        
        return SlackTimelineContext(
            channel_id=channel_id,
            channel_name=f'channel_{channel_id}',  # Would be enhanced with actual channel names
            messages=relevant_messages,
            meeting_intents=meeting_intents,
            mention_contexts=mention_contexts,
            conversation_score=conversation_score,
            time_range=(start_time, end_time),
            participants=conversation_participants
        )
    
    def _find_scheduling_messages(self,
                                messages: List[Dict[str, Any]],
                                start_time: datetime,
                                meeting_time: datetime,
                                participants: List[str]) -> List[Dict[str, Any]]:
        """
        Find messages that were part of scheduling the meeting
        """
        scheduling_messages = []
        
        for msg in messages:
            msg_time = datetime.fromtimestamp(float(msg.get('ts', 0)), tz=timezone.utc)
            
            # Must be in scheduling window
            if not (start_time <= msg_time <= meeting_time):
                continue
            
            # Check for scheduling patterns
            coordination_patterns = self.slack_extractor.extract_meeting_coordination_patterns(msg)
            
            if coordination_patterns:
                # Score the scheduling relevance
                scheduling_score = self._calculate_scheduling_score(msg, coordination_patterns, participants)
                if scheduling_score >= 0.7:
                    msg_copy = dict(msg)
                    msg_copy['scheduling_score'] = scheduling_score
                    msg_copy['coordination_patterns'] = coordination_patterns
                    scheduling_messages.append(msg_copy)
        
        return scheduling_messages
    
    def _calculate_conversation_relevance(self,
                                       messages: List[Dict[str, Any]],
                                       meeting_intents: List[MeetingIntent],
                                       mention_contexts: List[SlackMentionContext],
                                       meeting_participants: List[str],
                                       slack_participants: Set[str]) -> float:
        """
        Calculate how relevant a Slack conversation is to a meeting
        """
        score = 0.0
        
        # Base score for having any messages
        score += 0.2
        
        # Meeting intents boost
        if meeting_intents:
            score += min(len(meeting_intents) * 0.15, 0.4)
        
        # Participant overlap boost
        if meeting_participants and slack_participants:
            # Convert meeting participants to comparable format (would need actual mapping)
            overlap = len(slack_participants) / max(len(meeting_participants), 1)
            score += overlap * 0.3
        
        # Mention context boost
        if mention_contexts:
            score += min(len(mention_contexts) * 0.1, 0.2)
        
        # Message volume boost (more discussion = more relevance)
        message_boost = min(len(messages) * 0.02, 0.3)
        score += message_boost
        
        return min(score, 1.0)
    
    def _calculate_scheduling_score(self,
                                  message: Dict[str, Any],
                                  coordination_patterns: List[Dict[str, Any]],
                                  participants: List[str]) -> float:
        """
        Calculate how likely a message is to be part of scheduling coordination
        """
        score = 0.0
        
        # Base score for having coordination patterns
        score += 0.4
        
        # Higher score for more patterns
        score += min(len(coordination_patterns) * 0.2, 0.4)
        
        # Check pattern confidence
        for pattern in coordination_patterns:
            score += pattern.get('confidence', 0.0) * 0.1
        
        # Time mentions boost scheduling score
        text = message.get('text', '').lower()
        time_keywords = ['today', 'tomorrow', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday']
        if any(keyword in text for keyword in time_keywords):
            score += 0.2
        
        # Question format boosts (scheduling often involves questions)
        if '?' in text:
            score += 0.1
        
        return min(score, 1.0)
    
    def _extract_meeting_time(self, meeting: CorrelatedMeeting) -> Optional[datetime]:
        """
        Extract meeting time from correlated meeting data
        """
        # Try to get from email first
        if meeting.email_record and meeting.email_record.get('meeting_time'):
            return meeting.email_record['meeting_time']
        
        # Try to get from doc metadata
        if meeting.doc_record and meeting.doc_record.get('extracted_metadata', {}).get('meeting_date'):
            return meeting.doc_record['extracted_metadata']['meeting_date']
        
        # Fallback to correlation timestamp
        if hasattr(meeting, 'correlation_timestamp'):
            return meeting.correlation_timestamp
        
        return None
    
    def _extract_participants(self, meeting: CorrelatedMeeting) -> List[str]:
        """
        Extract participant list from correlated meeting
        """
        participants = []
        
        # Get from email
        if meeting.email_record:
            if meeting.email_record.get('attendees'):
                participants.extend(meeting.email_record['attendees'])
            if meeting.email_record.get('participants'):
                participants.extend(meeting.email_record['participants'])
        
        # Get from doc
        if meeting.doc_record and meeting.doc_record.get('extracted_metadata', {}).get('participants'):
            participants.extend(meeting.doc_record['extracted_metadata']['participants'])
        
        # Remove duplicates and return
        return list(set(participants))
    
    def _generate_discussion_summary(self, context: SlackTimelineContext) -> str:
        """
        Generate a brief summary of the Slack discussion
        """
        if not context.messages:
            return "No discussion found"
        
        # Count key elements
        message_count = len(context.messages)
        intent_count = len(context.meeting_intents)
        participant_count = len(context.participants)
        
        # Identify discussion themes
        themes = []
        for intent in context.meeting_intents:
            if intent.intent_type not in themes:
                themes.append(intent.intent_type)
        
        summary = f"{message_count} messages from {participant_count} participants"
        if themes:
            theme_str = ", ".join(themes[:3])  # Top 3 themes
            summary += f". Discussion themes: {theme_str}"
        
        if intent_count > 0:
            summary += f". {intent_count} meeting coordination activities detected"
        
        return summary
    
    def _create_participant_mapping(self,
                                   meeting_participants: List[str],
                                   timeline_contexts: List[SlackTimelineContext]) -> Dict[str, str]:
        """
        Create mapping between Slack user IDs and meeting participant names
        """
        mapping = {}
        
        # This would be enhanced with actual participant resolution
        # For now, create basic mapping structure
        slack_users = set()
        for context in timeline_contexts:
            slack_users.update(context.participants)
        
        # Basic mapping (would be enhanced with user lookup)
        for i, slack_user in enumerate(sorted(slack_users)):
            if i < len(meeting_participants):
                mapping[slack_user] = meeting_participants[i]
        
        return mapping
    
    def _calculate_coordination_score(self,
                                    meeting: CorrelatedMeeting,
                                    timeline_contexts: List[SlackTimelineContext],
                                    scheduling_timeline: List[Dict[str, Any]]) -> float:
        """
        Calculate overall meeting coordination score based on Slack activity
        """
        score = 0.0
        
        # Base meeting correlation score
        if hasattr(meeting, 'composite_score'):
            score += meeting.composite_score * 0.4
        
        # Timeline context contribution
        if timeline_contexts:
            avg_conversation_score = sum(ctx.conversation_score for ctx in timeline_contexts) / len(timeline_contexts)
            score += avg_conversation_score * 0.3
        
        # Scheduling timeline contribution
        if scheduling_timeline:
            scheduling_score = min(len(scheduling_timeline) * 0.1, 0.3)
            score += scheduling_score
        
        return min(score, 1.0)