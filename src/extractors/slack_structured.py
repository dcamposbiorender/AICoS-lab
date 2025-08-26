#!/usr/bin/env python3
"""
Enhanced Slack-Specific Structured Extractor - Phase 5A
Extends the base StructuredExtractor with Slack-specific patterns and intelligence integration.
Focuses on meeting coordination, @mention context, and Slack-native patterns.
"""

import re
from datetime import datetime
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass

from ..queries.structured import StructuredExtractor, PatternType, ExtractedPattern


@dataclass
class SlackMentionContext:
    """Context information for @mentions in Slack messages"""
    mention: str
    user_id: Optional[str]
    display_name: Optional[str]
    context_before: str
    context_after: str
    intent_type: str  # 'assignment', 'question', 'notification', 'meeting_invite'
    confidence: float
    message_timestamp: float
    channel_id: str


@dataclass
class SlackThreadContext:
    """Context for threading and conversation flow"""
    thread_ts: Optional[str]
    parent_user: Optional[str]
    reply_count: int
    participants: Set[str]
    meeting_indicators: int
    escalation_level: float  # How heated/urgent the conversation gets


class SlackStructuredExtractor(StructuredExtractor):
    """
    Slack-specific structured extractor with enhanced @mention processing
    and meeting coordination pattern detection
    """
    
    def __init__(self, case_sensitive: bool = False):
        super().__init__(case_sensitive)
        self._compile_slack_patterns()
    
    def _compile_slack_patterns(self):
        """Compile Slack-specific regex patterns"""
        flags = 0 if self.case_sensitive else re.IGNORECASE
        
        # Slack user mentions with display names: <@U123456789|username>
        self.slack_mention_with_name_pattern = re.compile(
            r'<@([A-Z0-9]{9,11})\|([^>]+)>',
            flags
        )
        
        # Slack channel mentions: <#C123456789|channelname>
        self.slack_channel_mention_pattern = re.compile(
            r'<#([A-Z0-9]{9,11})\|([^>]+)>',
            flags
        )
        
        # Meeting coordination patterns specific to Slack
        self.meeting_coordination_patterns = [
            re.compile(r'can\s+(?:we|you|everyone|y\'?all)\s+(?:meet|sync|chat|call)', flags),
            re.compile(r'let\'?s\s+(?:meet|sync|chat|call|schedule)', flags),
            re.compile(r'available\s+(?:for|to)\s+(?:meet|sync|call)', flags),
            re.compile(r'(?:book|schedule|set\s+up)\s+(?:a|the)?\s*(?:meeting|call|sync)', flags),
            re.compile(r'(?:zoom|google\s+meet|teams|slack\s+call)', flags),
        ]
        
        # Assignment patterns in Slack context
        self.slack_assignment_patterns = [
            re.compile(r'<@([A-Z0-9]{9,11})(?:\|[^>]+)?>\s+(?:can\s+you|could\s+you|please)', flags),
            re.compile(r'<@([A-Z0-9]{9,11})(?:\|[^>]+)?>\s+(?:will|to)\s+([^@\n.!?]+)', flags),
            re.compile(r'(?:assign(?:ed|ing)?|task(?:ed)?)\s+<@([A-Z0-9]{9,11})(?:\|[^>]+)?>', flags),
        ]
        
        # Question patterns directed at users
        self.question_patterns = [
            re.compile(r'<@([A-Z0-9]{9,11})(?:\|[^>]+)?>\s+(?:what|when|where|why|how|can|could|would|should)', flags),
            re.compile(r'(?:what|when|where|why|how|can|could|would|should).{1,50}?<@([A-Z0-9]{9,11})(?:\|[^>]+)?>', flags),
        ]
        
        # Escalation and urgency patterns
        self.escalation_patterns = [
            re.compile(r'\b(?:urgent|asap|critical|emergency|now|immediately)\b', flags),
            re.compile(r'\b(?:please\s+respond|need\s+answer|waiting\s+for)\b', flags),
            re.compile(r'\b(?:follow\s+up|following\s+up|ping)\b', flags),
        ]
    
    def extract_slack_mentions_with_context(self, message: Dict[str, Any]) -> List[SlackMentionContext]:
        """
        Extract @mentions with full Slack context including intent classification
        """
        text = message.get('text', '')
        user_id = message.get('user', '')
        channel_id = message.get('channel', '')
        timestamp = float(message.get('ts', 0))
        
        if not text:
            return []
        
        mentions = []
        
        # Extract both <@U123> and <@U123|username> formats
        simple_mentions = self.slack_mention_pattern.findall(text)
        named_mentions = self.slack_mention_with_name_pattern.findall(text)
        
        # Process simple mentions
        for mention_match in self.slack_mention_pattern.finditer(text):
            mention_user_id = mention_match.group(1)
            start = mention_match.start()
            end = mention_match.end()
            
            context = self._extract_mention_context(text, start, end)
            intent = self._classify_mention_intent(text, mention_match)
            confidence = self._calculate_mention_confidence(intent, context)
            
            mentions.append(SlackMentionContext(
                mention=mention_match.group(0),
                user_id=mention_user_id,
                display_name=None,
                context_before=context['before'],
                context_after=context['after'],
                intent_type=intent,
                confidence=confidence,
                message_timestamp=timestamp,
                channel_id=channel_id
            ))
        
        # Process mentions with display names
        for mention_match in self.slack_mention_with_name_pattern.finditer(text):
            mention_user_id = mention_match.group(1)
            display_name = mention_match.group(2)
            start = mention_match.start()
            end = mention_match.end()
            
            context = self._extract_mention_context(text, start, end)
            intent = self._classify_mention_intent(text, mention_match)
            confidence = self._calculate_mention_confidence(intent, context)
            
            mentions.append(SlackMentionContext(
                mention=mention_match.group(0),
                user_id=mention_user_id,
                display_name=display_name,
                context_before=context['before'],
                context_after=context['after'],
                intent_type=intent,
                confidence=confidence,
                message_timestamp=timestamp,
                channel_id=channel_id
            ))
        
        return mentions
    
    def extract_meeting_coordination_patterns(self, message: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract meeting coordination patterns from Slack message
        """
        text = message.get('text', '')
        if not text:
            return []
        
        coordination_patterns = []
        
        for i, pattern in enumerate(self.meeting_coordination_patterns):
            for match in pattern.finditer(text):
                # Get context around the match
                start = max(0, match.start() - 30)
                end = min(len(text), match.end() + 30)
                context = text[start:end]
                
                # Look for time mentions in context
                time_mentions = self._extract_time_mentions(context)
                
                # Look for participant mentions in context
                participant_mentions = self.slack_mention_pattern.findall(context)
                
                coordination_patterns.append({
                    'pattern_type': f'meeting_coordination_{i}',
                    'matched_text': match.group(0),
                    'context': context,
                    'time_mentions': time_mentions,
                    'participant_mentions': participant_mentions,
                    'confidence': self._calculate_coordination_confidence(match.group(0), context),
                    'position': match.start(),
                    'length': match.end() - match.start()
                })
        
        return coordination_patterns
    
    def analyze_thread_context(self, messages: List[Dict[str, Any]]) -> SlackThreadContext:
        """
        Analyze thread context for meeting coordination and escalation
        """
        if not messages:
            return SlackThreadContext(None, None, 0, set(), 0, 0.0)
        
        # Determine if this is a thread
        thread_ts = None
        parent_user = None
        reply_count = len(messages)
        
        for message in messages:
            if message.get('thread_ts'):
                thread_ts = message.get('thread_ts')
                break
        
        # If thread, find parent message
        if thread_ts:
            parent_messages = [m for m in messages if m.get('ts') == thread_ts]
            if parent_messages:
                parent_user = parent_messages[0].get('user')
        
        # Analyze participants
        participants = set()
        meeting_indicators = 0
        escalation_scores = []
        
        for message in messages:
            user_id = message.get('user')
            if user_id:
                participants.add(user_id)
            
            text = message.get('text', '').lower()
            
            # Count meeting indicators
            for pattern in self.meeting_coordination_patterns:
                if pattern.search(text):
                    meeting_indicators += 1
                    break
            
            # Calculate escalation for this message
            escalation = self._calculate_message_escalation(text)
            escalation_scores.append(escalation)
        
        # Overall escalation is the maximum escalation in the thread
        escalation_level = max(escalation_scores) if escalation_scores else 0.0
        
        return SlackThreadContext(
            thread_ts=thread_ts,
            parent_user=parent_user,
            reply_count=reply_count,
            participants=participants,
            meeting_indicators=meeting_indicators,
            escalation_level=escalation_level
        )
    
    def extract_slack_assignments(self, message: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract task assignments from Slack message using Slack-specific patterns
        """
        text = message.get('text', '')
        if not text:
            return []
        
        assignments = []
        
        for pattern in self.slack_assignment_patterns:
            for match in pattern.finditer(text):
                # Extract assignee user ID
                assignee_id = match.group(1)
                
                # Extract task text (varies by pattern)
                if len(match.groups()) > 1:
                    task_text = match.group(2).strip()
                else:
                    # Extract task from context after the mention
                    task_start = match.end()
                    task_end = text.find('\n', task_start)
                    if task_end == -1:
                        task_end = len(text)
                    task_text = text[task_start:task_end].strip()
                
                # Clean up task text
                task_text = re.sub(r'^(can you|could you|please|to)\s+', '', task_text, flags=re.IGNORECASE)
                
                if task_text:
                    assignments.append({
                        'assignee_id': assignee_id,
                        'task': task_text,
                        'assignment_type': 'slack_mention',
                        'confidence': self._calculate_assignment_confidence(match.group(0), task_text),
                        'position': match.start(),
                        'length': match.end() - match.start()
                    })
        
        return assignments
    
    def extract_slack_questions(self, message: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract questions directed at specific users
        """
        text = message.get('text', '')
        if not text:
            return []
        
        questions = []
        
        for pattern in self.question_patterns:
            for match in pattern.finditer(text):
                # Extract the user ID from the match
                user_id = None
                for group in match.groups():
                    if group and re.match(r'^[A-Z0-9]{9,11}$', group):
                        user_id = group
                        break
                
                if user_id:
                    # Extract question context
                    question_start = max(0, match.start() - 10)
                    question_end = min(len(text), match.end() + 50)
                    question_context = text[question_start:question_end].strip()
                    
                    questions.append({
                        'target_user_id': user_id,
                        'question_context': question_context,
                        'question_type': self._classify_question_type(question_context),
                        'confidence': 0.8,  # Questions are usually clear
                        'position': match.start(),
                        'length': match.end() - match.start()
                    })
        
        return questions
    
    # Private helper methods
    
    def _extract_mention_context(self, text: str, start: int, end: int) -> Dict[str, str]:
        """Extract context before and after a mention"""
        context_size = 30
        
        before_start = max(0, start - context_size)
        before = text[before_start:start]
        
        after_end = min(len(text), end + context_size)
        after = text[end:after_end]
        
        return {'before': before.strip(), 'after': after.strip()}
    
    def _classify_mention_intent(self, text: str, mention_match: re.Match) -> str:
        """Classify the intent behind a mention"""
        before = text[:mention_match.start()].lower()
        after = text[mention_match.end():].lower()
        context = f"{before} {after}"
        
        # Assignment patterns
        if any(word in before for word in ['can you', 'could you', 'please', 'task', 'assign']):
            return 'assignment'
        
        # Question patterns
        if any(word in context for word in ['what', 'when', 'where', 'why', 'how', '?']):
            return 'question'
        
        # Meeting patterns
        if any(word in context for word in ['meet', 'sync', 'call', 'available', 'schedule']):
            return 'meeting_invite'
        
        # Default to notification
        return 'notification'
    
    def _calculate_mention_confidence(self, intent: str, context: Dict[str, str]) -> float:
        """Calculate confidence for mention intent classification"""
        base_confidence = 0.6
        
        # Higher confidence for clear patterns
        if intent == 'assignment':
            if any(word in context['before'].lower() for word in ['can you', 'please']):
                base_confidence = 0.9
        elif intent == 'question':
            if '?' in context['after']:
                base_confidence = 0.95
        elif intent == 'meeting_invite':
            if any(word in context['after'].lower() for word in ['meet', 'call', 'sync']):
                base_confidence = 0.85
        
        return base_confidence
    
    def _extract_time_mentions(self, context: str) -> List[str]:
        """Extract time mentions from context"""
        time_patterns = [
            r'\b\d{1,2}(?::\d{2})?\s*(?:am|pm|AM|PM)\b',
            r'\b(?:today|tomorrow|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',
            r'\b\d{1,2}\/\d{1,2}(?:\/\d{2,4})?\b',
        ]
        
        time_mentions = []
        for pattern in time_patterns:
            matches = re.findall(pattern, context)
            time_mentions.extend(matches)
        
        return time_mentions
    
    def _calculate_coordination_confidence(self, matched_text: str, context: str) -> float:
        """Calculate confidence for meeting coordination detection"""
        base_confidence = 0.7
        
        # Boost confidence for explicit words
        if any(word in matched_text.lower() for word in ['let\'s meet', 'schedule', 'book']):
            base_confidence = 0.9
        
        # Boost for time context
        if re.search(r'\b\d{1,2}(?::\d{2})?\s*(?:am|pm)\b', context):
            base_confidence += 0.1
        
        # Boost for participant context
        if '<@' in context:
            base_confidence += 0.05
        
        return min(base_confidence, 1.0)
    
    def _calculate_message_escalation(self, text: str) -> float:
        """Calculate escalation level for a message"""
        escalation = 0.0
        
        for pattern in self.escalation_patterns:
            matches = len(pattern.findall(text))
            escalation += matches * 0.2
        
        # Check for repeated punctuation (!!!, ???)
        exclamation_count = text.count('!')
        question_count = text.count('?')
        if exclamation_count > 1:
            escalation += 0.3
        if question_count > 1:
            escalation += 0.2
        
        # Check for ALL CAPS words
        words = text.split()
        caps_words = sum(1 for word in words if word.isupper() and len(word) > 2)
        escalation += caps_words * 0.1
        
        return min(escalation, 1.0)
    
    def _calculate_assignment_confidence(self, matched_text: str, task_text: str) -> float:
        """Calculate confidence for task assignment detection"""
        base_confidence = 0.7
        
        # Higher confidence for clear assignment language
        if any(word in matched_text.lower() for word in ['can you', 'please', 'assign']):
            base_confidence = 0.9
        
        # Lower confidence for very short tasks (likely false positives)
        if len(task_text.strip()) < 10:
            base_confidence *= 0.7
        
        # Higher confidence for action-oriented tasks
        if any(word in task_text.lower() for word in ['send', 'update', 'create', 'review', 'check']):
            base_confidence += 0.1
        
        return min(base_confidence, 1.0)
    
    def _classify_question_type(self, question_context: str) -> str:
        """Classify the type of question being asked"""
        context_lower = question_context.lower()
        
        if 'when' in context_lower or 'time' in context_lower:
            return 'timing'
        elif 'what' in context_lower:
            return 'information'
        elif 'where' in context_lower:
            return 'location'
        elif 'how' in context_lower:
            return 'process'
        elif 'why' in context_lower:
            return 'reason'
        elif any(word in context_lower for word in ['can', 'could', 'would']):
            return 'request'
        else:
            return 'general'