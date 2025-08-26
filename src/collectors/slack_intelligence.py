#!/usr/bin/env python3
"""
Enhanced Slack Intelligence Module - Phase 5A
Builds on existing SlackCollector capabilities to add meeting detection and smart scheduling intelligence.
Maintains deterministic approach while adding advanced pattern recognition.
"""

import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
import time

from .slack_collector import SlackCollector

# Meeting detection patterns based on real Slack usage patterns
MEETING_INDICATORS = [
    # Direct meeting words
    r'\b(?:meeting|call|sync|standup|checkin|1:1|one.on.one)\b',
    
    # Time-specific patterns
    r'\b(?:at|@)\s*\d{1,2}(?::\d{2})?\s*(?:am|pm|AM|PM)?\b',
    r'\b(?:tomorrow|today|monday|tuesday|wednesday|thursday|friday)\s+at\b',
    r'\b\d{1,2}\/\d{1,2}(?:\/\d{2,4})?\s+at\b',
    
    # Calendar/scheduling language
    r'\b(?:schedule|book|calendar|available|free|busy|conflict)\b',
    r'\b(?:zoom|google meet|teams|slack call|hangouts)\b',
    
    # Action-oriented scheduling
    r'\b(?:let\'s meet|shall we meet|can we meet|want to meet)\b',
    r'\b(?:set up|arrange|coordinate|plan)\s+(?:a|the)?\s*(?:meeting|call|sync)\b'
]

SCHEDULING_KEYWORDS = [
    'schedule', 'calendar', 'available', 'free time', 'book', 'meeting',
    'call', 'sync', 'standup', 'checkin', '1:1', 'zoom', 'google meet'
]

@dataclass
class MeetingIntent:
    """Represents a detected meeting intent in Slack conversations"""
    message_id: str
    channel_id: str
    user_id: str
    timestamp: float
    intent_type: str  # 'schedule_request', 'time_suggestion', 'confirmation', 'reschedule'
    confidence: float
    participants: List[str]
    suggested_times: List[str]
    meeting_topic: Optional[str]
    urgency_indicators: List[str]
    context_messages: List[str]  # Related messages for full context

@dataclass
class ConversationContext:
    """Context window for analyzing conversation patterns"""
    channel_id: str
    messages: List[Dict]
    participants: Set[str]
    time_window_hours: int
    meeting_indicators_found: int
    scheduling_density: float  # Messages with scheduling keywords / total messages

class SlackIntelligence:
    """
    Enhanced intelligence layer for SlackCollector
    Focuses on meeting detection, scheduling pattern recognition, and conversation analytics
    """
    
    def __init__(self, slack_collector: SlackCollector):
        self.slack_collector = slack_collector
        
        # Compile regex patterns for performance
        self.meeting_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in MEETING_INDICATORS]
        self.scheduling_keywords_lower = [kw.lower() for kw in SCHEDULING_KEYWORDS]
        
        # Analytics tracking
        self.analytics = {
            'messages_analyzed': 0,
            'meeting_intents_detected': 0,
            'scheduling_conversations': 0,
            'high_priority_threads': 0
        }
    
    def enhance_conversation_analytics(self, conversation_data: Dict) -> Dict:
        """
        Enhance existing conversation analytics with meeting detection capabilities
        Builds on SlackCollector's _calculate_conversation_analytics method
        """
        enhanced_data = dict(conversation_data)  # Don't modify original
        messages = conversation_data.get('messages', [])
        
        if not messages:
            return enhanced_data
        
        # Analyze messages for meeting patterns
        meeting_analysis = self._analyze_meeting_patterns(messages)
        scheduling_analysis = self._analyze_scheduling_patterns(messages)
        conversation_context = self._build_conversation_context(messages, conversation_data.get('channel_info', {}))
        
        # Add enhanced analytics to existing structure
        if 'analytics' not in enhanced_data:
            enhanced_data['analytics'] = {}
            
        enhanced_data['analytics']['meeting_intelligence'] = {
            'meeting_intents_detected': len(meeting_analysis['intents']),
            'scheduling_conversations': scheduling_analysis['conversation_count'],
            'meeting_density': meeting_analysis['density'],
            'scheduling_keywords_frequency': scheduling_analysis['keyword_frequency'],
            'high_priority_threads': len([t for t in conversation_data.get('threads', []) if t.get('priority_score', 0) > 8.0]),
            'conversation_context': {
                'participants_count': len(conversation_context.participants),
                'time_window_coverage': conversation_context.time_window_hours,
                'scheduling_density': conversation_context.scheduling_density
            }
        }
        
        # Add detected meeting intents
        enhanced_data['meeting_intents'] = meeting_analysis['intents']
        enhanced_data['scheduling_patterns'] = scheduling_analysis['patterns']
        
        self.analytics['messages_analyzed'] += len(messages)
        self.analytics['meeting_intents_detected'] += len(meeting_analysis['intents'])
        
        return enhanced_data
    
    def _analyze_meeting_patterns(self, messages: List[Dict]) -> Dict:
        """Detect meeting-related patterns in message content"""
        intents = []
        total_messages = len(messages)
        meeting_message_count = 0
        
        for message in messages:
            content = message.get('text', '').lower()
            user_id = message.get('user', '')
            message_ts = float(message.get('ts', 0))
            
            # Check for meeting patterns
            meeting_indicators = []
            for pattern in self.meeting_patterns:
                if pattern.search(content):
                    meeting_indicators.append(pattern.pattern)
            
            if meeting_indicators:
                meeting_message_count += 1
                
                # Detect specific intent types
                intent_type = self._classify_meeting_intent(content)
                confidence = self._calculate_confidence(content, meeting_indicators)
                
                # Extract participants from @mentions in the message
                participants = self._extract_mentions(content)
                
                # Extract suggested times
                suggested_times = self._extract_time_suggestions(content)
                
                # Determine meeting topic from context
                meeting_topic = self._extract_meeting_topic(content)
                
                # Check urgency indicators
                urgency_indicators = self._detect_urgency(content)
                
                intent = MeetingIntent(
                    message_id=message.get('client_msg_id', message.get('ts', '')),
                    channel_id=message.get('channel', ''),
                    user_id=user_id,
                    timestamp=message_ts,
                    intent_type=intent_type,
                    confidence=confidence,
                    participants=participants,
                    suggested_times=suggested_times,
                    meeting_topic=meeting_topic,
                    urgency_indicators=urgency_indicators,
                    context_messages=[]  # Will be filled by context analysis
                )
                
                intents.append(intent)
        
        density = meeting_message_count / total_messages if total_messages > 0 else 0
        
        return {
            'intents': intents,
            'density': density,
            'total_meeting_messages': meeting_message_count,
            'total_messages': total_messages
        }
    
    def _analyze_scheduling_patterns(self, messages: List[Dict]) -> Dict:
        """Analyze scheduling conversation patterns"""
        scheduling_messages = []
        keyword_frequency = {}
        conversation_threads = {}
        
        for message in messages:
            content = message.get('text', '').lower()
            thread_ts = message.get('thread_ts')
            
            # Count scheduling keywords
            for keyword in self.scheduling_keywords_lower:
                count = content.count(keyword)
                if count > 0:
                    keyword_frequency[keyword] = keyword_frequency.get(keyword, 0) + count
                    scheduling_messages.append(message)
                    
                    # Track thread-level scheduling conversations
                    thread_key = thread_ts or message.get('ts')
                    if thread_key not in conversation_threads:
                        conversation_threads[thread_key] = {
                            'messages': [],
                            'participants': set(),
                            'scheduling_intensity': 0
                        }
                    conversation_threads[thread_key]['messages'].append(message)
                    conversation_threads[thread_key]['participants'].add(message.get('user', ''))
                    conversation_threads[thread_key]['scheduling_intensity'] += count
                    break  # Don't double-count messages
        
        # Identify high-intensity scheduling conversations
        patterns = []
        for thread_key, thread_data in conversation_threads.items():
            if thread_data['scheduling_intensity'] >= 3 or len(thread_data['participants']) >= 3:
                patterns.append({
                    'thread_id': thread_key,
                    'participants': list(thread_data['participants']),
                    'message_count': len(thread_data['messages']),
                    'scheduling_intensity': thread_data['scheduling_intensity'],
                    'pattern_type': 'high_intensity_scheduling'
                })
        
        return {
            'conversation_count': len(conversation_threads),
            'keyword_frequency': keyword_frequency,
            'scheduling_message_count': len(scheduling_messages),
            'patterns': patterns
        }
    
    def _build_conversation_context(self, messages: List[Dict], channel_info: Dict) -> ConversationContext:
        """Build context window for conversation analysis"""
        if not messages:
            return ConversationContext('', [], set(), 0, 0, 0.0)
        
        # Calculate time window
        timestamps = [float(m.get('ts', 0)) for m in messages if m.get('ts')]
        if timestamps:
            earliest = min(timestamps)
            latest = max(timestamps)
            time_window_hours = (latest - earliest) / 3600
        else:
            time_window_hours = 0
        
        # Extract participants
        participants = set(m.get('user', '') for m in messages if m.get('user'))
        
        # Count meeting indicators
        meeting_indicators = 0
        scheduling_messages = 0
        
        for message in messages:
            content = message.get('text', '').lower()
            
            # Count meeting patterns
            for pattern in self.meeting_patterns:
                if pattern.search(content):
                    meeting_indicators += 1
                    break
            
            # Count scheduling keywords
            if any(keyword in content for keyword in self.scheduling_keywords_lower):
                scheduling_messages += 1
        
        scheduling_density = scheduling_messages / len(messages) if messages else 0
        
        return ConversationContext(
            channel_id=channel_info.get('id', ''),
            messages=messages,
            participants=participants,
            time_window_hours=int(time_window_hours),
            meeting_indicators_found=meeting_indicators,
            scheduling_density=scheduling_density
        )
    
    def _classify_meeting_intent(self, content: str) -> str:
        """Classify the type of meeting intent from message content"""
        content_lower = content.lower()
        
        if any(word in content_lower for word in ['can we', 'shall we', 'let\'s meet', 'want to meet']):
            return 'schedule_request'
        elif any(word in content_lower for word in ['at ', 'tomorrow', 'today', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday']):
            return 'time_suggestion'
        elif any(word in content_lower for word in ['confirmed', 'confirmed', 'sounds good', 'perfect', 'yes, let\'s']):
            return 'confirmation'
        elif any(word in content_lower for word in ['reschedule', 'move', 'change', 'postpone', 'cancel']):
            return 'reschedule'
        else:
            return 'general_meeting'
    
    def _calculate_confidence(self, content: str, meeting_indicators: List[str]) -> float:
        """Calculate confidence score for meeting intent detection"""
        base_confidence = 0.3
        
        # More patterns = higher confidence
        pattern_bonus = min(len(meeting_indicators) * 0.15, 0.4)
        
        # Specific high-confidence phrases
        high_conf_phrases = ['let\'s meet', 'schedule a meeting', 'book a call', '1:1', 'standup']
        phrase_bonus = 0.2 if any(phrase in content.lower() for phrase in high_conf_phrases) else 0
        
        # Time-specific mentions boost confidence
        time_bonus = 0.15 if re.search(r'\b\d{1,2}(?::\d{2})?\s*(?:am|pm)\b', content.lower()) else 0
        
        # @mentions suggest meeting coordination
        mention_bonus = 0.1 if '@' in content else 0
        
        total_confidence = base_confidence + pattern_bonus + phrase_bonus + time_bonus + mention_bonus
        return min(total_confidence, 1.0)
    
    def _extract_mentions(self, content: str) -> List[str]:
        """Extract @mentions from message content"""
        # Slack mentions are in format <@U123456789>
        mention_pattern = r'<@([A-Z0-9]+)>'
        mentions = re.findall(mention_pattern, content)
        
        # Also catch @username format
        username_pattern = r'@([a-zA-Z0-9_.-]+)'
        usernames = re.findall(username_pattern, content)
        
        return mentions + usernames
    
    def _extract_time_suggestions(self, content: str) -> List[str]:
        """Extract suggested meeting times from content"""
        time_patterns = [
            r'\b\d{1,2}(?::\d{2})?\s*(?:am|pm|AM|PM)\b',
            r'\b(?:tomorrow|today|monday|tuesday|wednesday|thursday|friday)\s+at\s+\d{1,2}(?::\d{2})?\s*(?:am|pm|AM|PM)?\b',
            r'\b\d{1,2}\/\d{1,2}(?:\/\d{2,4})?\s+at\s+\d{1,2}(?::\d{2})?\s*(?:am|pm|AM|PM)?\b'
        ]
        
        suggestions = []
        for pattern in time_patterns:
            matches = re.findall(pattern, content)
            suggestions.extend(matches)
        
        return suggestions
    
    def _extract_meeting_topic(self, content: str) -> Optional[str]:
        """Extract likely meeting topic from message content"""
        # Look for phrases like "meeting about X" or "sync on Y"
        topic_patterns = [
            r'meeting about (.{1,50}?)(?:\.|,|$)',
            r'sync on (.{1,50}?)(?:\.|,|$)',
            r'discuss (.{1,50}?)(?:\.|,|$)',
            r'talk about (.{1,50}?)(?:\.|,|$)'
        ]
        
        for pattern in topic_patterns:
            match = re.search(pattern, content.lower())
            if match:
                return match.group(1).strip()
        
        return None
    
    def _detect_urgency(self, content: str) -> List[str]:
        """Detect urgency indicators in message content"""
        urgency_patterns = [
            'urgent', 'asap', 'today', 'now', 'immediately', 'critical',
            'important', 'priority', 'deadline', 'emergency', 'quickly'
        ]
        
        found_indicators = []
        content_lower = content.lower()
        
        for indicator in urgency_patterns:
            if indicator in content_lower:
                found_indicators.append(indicator)
        
        return found_indicators
    
    def analyze_executive_participation(self, conversation_data: Dict) -> Dict:
        """Analyze executive participation patterns for priority scoring"""
        messages = conversation_data.get('messages', [])
        threads = conversation_data.get('threads', [])
        
        # This would integrate with the employee collector to identify executives
        # For now, using heuristics based on message patterns and thread priority
        
        executive_indicators = {
            'high_priority_participants': [],
            'decision_makers': [],
            'frequent_meeting_requesters': []
        }
        
        user_activity = {}
        for message in messages:
            user_id = message.get('user', '')
            if not user_id:
                continue
                
            if user_id not in user_activity:
                user_activity[user_id] = {
                    'message_count': 0,
                    'meeting_requests': 0,
                    'decision_language': 0,
                    'urgency_usage': 0
                }
            
            user_activity[user_id]['message_count'] += 1
            
            content = message.get('text', '').lower()
            
            # Count meeting request language
            if any(phrase in content for phrase in ['let\'s meet', 'schedule', 'can we sync']):
                user_activity[user_id]['meeting_requests'] += 1
            
            # Count decision-making language
            if any(phrase in content for phrase in ['we should', 'let\'s do', 'i think we need', 'decision']):
                user_activity[user_id]['decision_language'] += 1
            
            # Count urgency language
            if any(phrase in content for phrase in ['urgent', 'asap', 'critical', 'important']):
                user_activity[user_id]['urgency_usage'] += 1
        
        # Score users based on activity patterns
        for user_id, activity in user_activity.items():
            if activity['meeting_requests'] >= 2:
                executive_indicators['frequent_meeting_requesters'].append(user_id)
            if activity['decision_language'] >= 2:
                executive_indicators['decision_makers'].append(user_id)
            if activity['urgency_usage'] >= 1 and activity['message_count'] >= 3:
                executive_indicators['high_priority_participants'].append(user_id)
        
        return executive_indicators
    
    def get_analytics_summary(self) -> Dict:
        """Get summary of intelligence analytics"""
        return dict(self.analytics)