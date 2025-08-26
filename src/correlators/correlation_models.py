#!/usr/bin/env python3
"""
Correlation Models - Data Structures for Meeting-Email Correlation
Defines unified data structures for correlated meeting records

This module provides the data models used in Phase 3 of the meeting notes
processing workflow to represent correlated email-Google Doc pairs.

Architecture:
- CorrelatedMeeting: Main unified meeting record
- CorrelationMatch: Individual correlation result with confidence scoring
- CorrelationMetrics: Performance tracking for correlation algorithms
- OrphanedRecord: Uncorrelated email or Google Doc records

Usage:
    from src.correlators.correlation_models import CorrelatedMeeting
    meeting = CorrelatedMeeting.from_email_and_doc(email_record, doc_record, confidence)
"""

import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union
from enum import Enum


class CorrelationStatus(Enum):
    """Status of correlation attempts"""
    PENDING = "pending"           # Awaiting correlation
    MATCHED = "matched"           # Successfully correlated
    ORPHANED = "orphaned"         # No match found within timeout
    MANUAL_REVIEW = "manual_review"  # Requires human review


class MatchType(Enum):
    """Type of correlation match"""
    TEMPORAL = "temporal"         # Time-based matching
    PARTICIPANT = "participant"   # Participant-based matching
    CONTENT = "content"          # Content similarity matching
    COMPOSITE = "composite"      # Multiple matching criteria


@dataclass
class CorrelationMatch:
    """Individual correlation match result with confidence scoring"""
    email_id: str                # Unique identifier for email record
    doc_id: str                  # Unique identifier for Google Doc record
    match_type: MatchType        # Type of matching used
    confidence_score: float      # Confidence level (0.0-1.0)
    match_details: Dict[str, Any]  # Detailed matching information
    created_at: datetime         # When correlation was created
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = asdict(self)
        result['match_type'] = self.match_type.value
        result['created_at'] = self.created_at.isoformat()
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CorrelationMatch':
        """Create from dictionary"""
        data = data.copy()
        data['match_type'] = MatchType(data['match_type'])
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        return cls(**data)


@dataclass
class CorrelatedMeeting:
    """Unified meeting record combining email and Google Doc data"""
    correlation_id: str          # Unique identifier for correlated meeting
    meeting_title: str           # Combined/preferred meeting title
    meeting_datetime: Optional[datetime]  # Meeting date and time
    participants: List[str]      # Combined participant list
    
    # Source data
    email_record: Optional[Dict[str, Any]]    # Original email record
    doc_record: Optional[Dict[str, Any]]      # Original Google Doc record
    
    # Correlation metadata
    correlation_match: CorrelationMatch       # How they were matched
    correlation_status: CorrelationStatus     # Current status
    confidence_score: float                   # Overall confidence
    
    # Meeting content
    meeting_content: str                      # Combined/preferred content
    action_items: List[Dict[str, Any]]       # Extracted action items
    todos: List[Dict[str, Any]]              # Extracted todos
    deadlines: List[Dict[str, Any]]          # Extracted deadlines
    
    # Metadata
    created_at: datetime                     # When record was created
    updated_at: datetime                     # When record was last updated
    source_files: List[str]                  # Source file paths
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = asdict(self)
        result['correlation_status'] = self.correlation_status.value
        result['correlation_match'] = self.correlation_match.to_dict()
        result['meeting_datetime'] = self.meeting_datetime.isoformat() if self.meeting_datetime else None
        result['created_at'] = self.created_at.isoformat()
        result['updated_at'] = self.updated_at.isoformat()
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CorrelatedMeeting':
        """Create from dictionary"""
        data = data.copy()
        data['correlation_status'] = CorrelationStatus(data['correlation_status'])
        data['correlation_match'] = CorrelationMatch.from_dict(data['correlation_match'])
        
        if data.get('meeting_datetime'):
            data['meeting_datetime'] = datetime.fromisoformat(data['meeting_datetime'])
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        return cls(**data)
    
    @classmethod
    def from_email_and_doc(cls, email_record: Dict[str, Any], doc_record: Dict[str, Any], 
                          correlation_match: CorrelationMatch) -> 'CorrelatedMeeting':
        """Create correlated meeting from email and Google Doc records"""
        now = datetime.now(timezone.utc)
        
        # Combine meeting titles (prefer Google Doc title if available)
        doc_title = doc_record.get('title', '') if doc_record else ''
        email_title = email_record.get('title', '') if email_record else ''
        meeting_title = doc_title or email_title or 'Untitled Meeting'
        
        # Combine participants
        participants = set()
        if email_record and 'participants' in email_record:
            participants.update(email_record['participants'])
        if doc_record and 'meeting_metadata' in doc_record:
            doc_participants = doc_record['meeting_metadata'].get('participants', [])
            participants.update(doc_participants)
        
        # Get meeting datetime (prefer email timestamp)
        meeting_datetime = None
        if email_record and 'meeting_datetime' in email_record:
            meeting_datetime = email_record['meeting_datetime']
        elif doc_record and 'meeting_metadata' in doc_record:
            doc_date = doc_record['meeting_metadata'].get('date')
            if doc_date:
                meeting_datetime = datetime.combine(doc_date, datetime.min.time())
        
        # Get meeting content (prefer Google Doc content)
        meeting_content = ''
        if doc_record and 'content' in doc_record:
            meeting_content = doc_record['content']
        elif email_record and 'content' in email_record:
            meeting_content = email_record['content']
        
        # Source files
        source_files = []
        if email_record and 'source_file' in email_record:
            source_files.append(email_record['source_file'])
        if doc_record and 'source_file' in doc_record:
            source_files.append(doc_record['source_file'])
        
        return cls(
            correlation_id=f"meeting_{now.strftime('%Y%m%d_%H%M%S')}_{hash(meeting_title) % 10000:04d}",
            meeting_title=meeting_title,
            meeting_datetime=meeting_datetime,
            participants=list(participants),
            email_record=email_record,
            doc_record=doc_record,
            correlation_match=correlation_match,
            correlation_status=CorrelationStatus.MATCHED,
            confidence_score=correlation_match.confidence_score,
            meeting_content=meeting_content,
            action_items=[],  # Will be populated by StructuredExtractor
            todos=[],         # Will be populated by StructuredExtractor
            deadlines=[],     # Will be populated by StructuredExtractor
            created_at=now,
            updated_at=now,
            source_files=source_files
        )


@dataclass
class OrphanedRecord:
    """Record for emails or Google Docs that couldn't be correlated"""
    record_id: str                           # Unique identifier
    record_type: str                         # 'email' or 'google_doc'
    original_record: Dict[str, Any]          # Original record data
    correlation_attempts: List[Dict[str, Any]]  # Attempted correlations
    orphaned_at: datetime                    # When marked as orphaned
    created_at: datetime                     # When record was created
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = asdict(self)
        result['orphaned_at'] = self.orphaned_at.isoformat()
        result['created_at'] = self.created_at.isoformat()
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OrphanedRecord':
        """Create from dictionary"""
        data = data.copy()
        data['orphaned_at'] = datetime.fromisoformat(data['orphaned_at'])
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        return cls(**data)


@dataclass
class CorrelationMetrics:
    """Performance metrics for correlation algorithms"""
    total_emails: int                        # Total emails processed
    total_docs: int                          # Total Google Docs processed
    successful_correlations: int             # Successfully correlated pairs
    orphaned_emails: int                     # Emails without matches
    orphaned_docs: int                       # Google Docs without matches
    correlation_accuracy: float              # Accuracy percentage
    processing_time: float                   # Total processing time (seconds)
    average_confidence: float                # Average confidence score
    
    # Breakdown by match type
    temporal_matches: int                    # Time-based matches
    participant_matches: int                 # Participant-based matches
    content_matches: int                     # Content-based matches
    composite_matches: int                   # Multi-criteria matches
    
    created_at: datetime                     # When metrics were calculated
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = asdict(self)
        result['created_at'] = self.created_at.isoformat()
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CorrelationMetrics':
        """Create from dictionary"""
        data = data.copy()
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        return cls(**data)
    
    def calculate_accuracy(self):
        """Calculate correlation accuracy percentage"""
        total_records = self.total_emails + self.total_docs
        if total_records == 0:
            self.correlation_accuracy = 0.0
        else:
            # Accuracy based on successful correlations vs total possible pairs
            max_possible_pairs = min(self.total_emails, self.total_docs)
            if max_possible_pairs == 0:
                self.correlation_accuracy = 0.0
            else:
                self.correlation_accuracy = (self.successful_correlations / max_possible_pairs) * 100


# Utility functions
def generate_correlation_id(title: str, datetime_obj: Optional[datetime] = None) -> str:
    """Generate unique correlation ID for a meeting"""
    timestamp = datetime_obj or datetime.now(timezone.utc)
    title_hash = hash(title) % 10000
    return f"meeting_{timestamp.strftime('%Y%m%d_%H%M%S')}_{title_hash:04d}"


def serialize_correlation_record(record: Union[CorrelatedMeeting, OrphanedRecord, CorrelationMetrics]) -> str:
    """Serialize correlation record to JSON string"""
    return json.dumps(record.to_dict(), indent=2, default=str)


def deserialize_correlation_record(json_str: str, record_type: str) -> Union[CorrelatedMeeting, OrphanedRecord, CorrelationMetrics]:
    """Deserialize JSON string to correlation record"""
    data = json.loads(json_str)
    
    if record_type == 'correlated_meeting':
        return CorrelatedMeeting.from_dict(data)
    elif record_type == 'orphaned_record':
        return OrphanedRecord.from_dict(data)
    elif record_type == 'correlation_metrics':
        return CorrelationMetrics.from_dict(data)
    else:
        raise ValueError(f"Unknown record type: {record_type}")


# ==================== PHASE 5B: SLACK CONTEXT ENHANCEMENTS ====================

class SlackMatchType(Enum):
    """Extended match types including Slack correlation"""
    TEMPORAL = "temporal"         # Time-based matching
    PARTICIPANT = "participant"   # Participant-based matching
    CONTENT = "content"          # Content similarity matching
    COMPOSITE = "composite"      # Multiple matching criteria
    SLACK_TIMELINE = "slack_timeline"      # Slack conversation timeline matching
    SLACK_SCHEDULING = "slack_scheduling"   # Slack scheduling coordination matching
    SLACK_PARTICIPANT = "slack_participant" # Slack participant overlap matching


@dataclass
class SlackContext:
    """Slack conversation context for a meeting"""
    channel_id: str                          # Slack channel ID
    channel_name: str                        # Human-readable channel name
    channel_type: str                        # 'public', 'private', 'dm', 'mpim'
    
    # Message data
    total_messages: int                      # Total messages in relevant timeframe
    scheduling_messages: int                 # Messages related to scheduling
    follow_up_messages: int                  # Messages after meeting
    
    # Participant information
    slack_participants: List[str]            # Slack user IDs involved
    participant_overlap_score: float         # How well Slack participants match meeting attendees
    
    # Content analysis
    meeting_intent_count: int                # Number of meeting intents detected
    mention_count: int                       # Number of @mentions
    coordination_score: float                # Overall coordination activity score
    
    # Timeline information
    first_mention_timestamp: Optional[datetime]     # When meeting first mentioned
    last_scheduling_timestamp: Optional[datetime]   # When scheduling was finalized
    meeting_reminder_count: int              # Number of meeting reminders sent
    
    # Metadata
    analyzed_at: datetime                    # When this context was analyzed
    confidence_score: float                  # Confidence in Slack correlation
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = asdict(self)
        result['first_mention_timestamp'] = self.first_mention_timestamp.isoformat() if self.first_mention_timestamp else None
        result['last_scheduling_timestamp'] = self.last_scheduling_timestamp.isoformat() if self.last_scheduling_timestamp else None
        result['analyzed_at'] = self.analyzed_at.isoformat()
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SlackContext':
        """Create from dictionary"""
        data = data.copy()
        if data.get('first_mention_timestamp'):
            data['first_mention_timestamp'] = datetime.fromisoformat(data['first_mention_timestamp'])
        if data.get('last_scheduling_timestamp'):
            data['last_scheduling_timestamp'] = datetime.fromisoformat(data['last_scheduling_timestamp'])
        data['analyzed_at'] = datetime.fromisoformat(data['analyzed_at'])
        return cls(**data)


@dataclass  
class SlackCorrelationMatch(CorrelationMatch):
    """Extended correlation match including Slack context"""
    slack_context: Optional[SlackContext]     # Slack conversation context
    slack_match_types: List[SlackMatchType]   # Types of Slack matching used
    slack_confidence_boost: float             # Confidence boost from Slack correlation
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = super().to_dict()
        result['slack_context'] = self.slack_context.to_dict() if self.slack_context else None
        result['slack_match_types'] = [match_type.value for match_type in self.slack_match_types]
        result['slack_confidence_boost'] = self.slack_confidence_boost
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SlackCorrelationMatch':
        """Create from dictionary"""
        data = data.copy()
        data['match_type'] = MatchType(data['match_type'])
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        
        if data.get('slack_context'):
            data['slack_context'] = SlackContext.from_dict(data['slack_context'])
        
        data['slack_match_types'] = [SlackMatchType(mt) for mt in data.get('slack_match_types', [])]
        
        return cls(**data)


@dataclass
class SlackEnhancedMeeting(CorrelatedMeeting):
    """Enhanced correlated meeting with Slack timeline integration"""
    
    # Slack integration fields
    slack_contexts: List[SlackContext]        # Multiple Slack conversations (channels, DMs, etc.)
    primary_slack_channel: Optional[str]      # Main coordination channel
    scheduling_timeline: List[Dict[str, Any]] # Chronological scheduling discussion
    
    # Enhanced participant mapping
    slack_participant_mapping: Dict[str, str] # slack_user_id -> email/name mapping
    participant_resolution_score: float       # How well we resolved participants across systems
    
    # Meeting coordination analysis
    coordination_lead: Optional[str]          # Who initiated/drove the meeting
    scheduling_complexity: float             # How complex was the scheduling (0.0-1.0)
    pre_meeting_discussions: int             # Number of preparatory discussions
    post_meeting_actions: int                # Number of follow-up actions in Slack
    
    # Intelligence scores
    meeting_importance_score: float          # Calculated importance based on all signals
    coordination_effectiveness_score: float  # How well the meeting was coordinated
    follow_through_score: float             # How well follow-ups were handled
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = super().to_dict()
        
        # Add Slack-specific fields
        result['slack_contexts'] = [ctx.to_dict() for ctx in self.slack_contexts]
        result['primary_slack_channel'] = self.primary_slack_channel
        result['scheduling_timeline'] = self.scheduling_timeline
        result['slack_participant_mapping'] = self.slack_participant_mapping
        result['participant_resolution_score'] = self.participant_resolution_score
        result['coordination_lead'] = self.coordination_lead
        result['scheduling_complexity'] = self.scheduling_complexity
        result['pre_meeting_discussions'] = self.pre_meeting_discussions
        result['post_meeting_actions'] = self.post_meeting_actions
        result['meeting_importance_score'] = self.meeting_importance_score
        result['coordination_effectiveness_score'] = self.coordination_effectiveness_score
        result['follow_through_score'] = self.follow_through_score
        
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SlackEnhancedMeeting':
        """Create from dictionary"""
        data = data.copy()
        
        # Handle base class fields
        data['correlation_status'] = CorrelationStatus(data['correlation_status'])
        data['correlation_match'] = CorrelationMatch.from_dict(data['correlation_match'])
        
        if data.get('meeting_datetime'):
            data['meeting_datetime'] = datetime.fromisoformat(data['meeting_datetime'])
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        
        # Handle Slack-specific fields
        if data.get('slack_contexts'):
            data['slack_contexts'] = [SlackContext.from_dict(ctx) for ctx in data['slack_contexts']]
        else:
            data['slack_contexts'] = []
            
        # Set defaults for any missing Slack fields
        slack_defaults = {
            'primary_slack_channel': None,
            'scheduling_timeline': [],
            'slack_participant_mapping': {},
            'participant_resolution_score': 0.0,
            'coordination_lead': None,
            'scheduling_complexity': 0.0,
            'pre_meeting_discussions': 0,
            'post_meeting_actions': 0,
            'meeting_importance_score': 0.0,
            'coordination_effectiveness_score': 0.0,
            'follow_through_score': 0.0
        }
        
        for key, default_value in slack_defaults.items():
            if key not in data:
                data[key] = default_value
        
        return cls(**data)
    
    def get_coordination_summary(self) -> Dict[str, Any]:
        """Generate a summary of meeting coordination effectiveness"""
        return {
            'overall_coordination_score': (
                self.coordination_effectiveness_score + 
                self.follow_through_score + 
                self.participant_resolution_score
            ) / 3.0,
            'coordination_lead': self.coordination_lead,
            'primary_channel': self.primary_slack_channel,
            'scheduling_complexity': self.scheduling_complexity,
            'total_slack_contexts': len(self.slack_contexts),
            'scheduling_messages': len(self.scheduling_timeline),
            'follow_up_actions': self.post_meeting_actions,
            'participant_mapping_quality': self.participant_resolution_score
        }


@dataclass
class SlackCorrelationMetrics(CorrelationMetrics):
    """Extended correlation metrics including Slack integration stats"""
    
    # Slack-specific metrics
    slack_enhanced_meetings: int             # Meetings enhanced with Slack context
    slack_correlation_success_rate: float    # Success rate of Slack correlation
    average_slack_channels_per_meeting: float # Average Slack contexts per meeting
    
    # Timeline analysis metrics  
    meetings_with_scheduling_timeline: int   # Meetings with detectable scheduling
    meetings_with_follow_ups: int           # Meetings with Slack follow-ups
    average_coordination_score: float       # Average coordination effectiveness
    
    # Participant resolution metrics
    participant_resolution_success_rate: float # How often we resolve Slack users
    average_participant_overlap: float       # Average overlap between systems
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = super().to_dict()
        
        # Add Slack-specific metrics
        result['slack_enhanced_meetings'] = self.slack_enhanced_meetings
        result['slack_correlation_success_rate'] = self.slack_correlation_success_rate
        result['average_slack_channels_per_meeting'] = self.average_slack_channels_per_meeting
        result['meetings_with_scheduling_timeline'] = self.meetings_with_scheduling_timeline
        result['meetings_with_follow_ups'] = self.meetings_with_follow_ups
        result['average_coordination_score'] = self.average_coordination_score
        result['participant_resolution_success_rate'] = self.participant_resolution_success_rate
        result['average_participant_overlap'] = self.average_participant_overlap
        
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SlackCorrelationMetrics':
        """Create from dictionary"""
        data = data.copy()
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        
        # Set defaults for any missing Slack metrics
        slack_metric_defaults = {
            'slack_enhanced_meetings': 0,
            'slack_correlation_success_rate': 0.0,
            'average_slack_channels_per_meeting': 0.0,
            'meetings_with_scheduling_timeline': 0,
            'meetings_with_follow_ups': 0,
            'average_coordination_score': 0.0,
            'participant_resolution_success_rate': 0.0,
            'average_participant_overlap': 0.0
        }
        
        for key, default_value in slack_metric_defaults.items():
            if key not in data:
                data[key] = default_value
        
        return cls(**data)


# Utility functions for Slack-enhanced correlation

def create_slack_enhanced_meeting_from_correlated(
    correlated_meeting: CorrelatedMeeting,
    slack_contexts: List[SlackContext],
    scheduling_timeline: List[Dict[str, Any]],
    participant_mapping: Dict[str, str]
) -> SlackEnhancedMeeting:
    """Convert a CorrelatedMeeting to a SlackEnhancedMeeting"""
    
    # Calculate intelligence scores
    importance_score = _calculate_importance_score(correlated_meeting, slack_contexts)
    coordination_score = _calculate_coordination_effectiveness(scheduling_timeline, slack_contexts)
    follow_through_score = _calculate_follow_through_score(slack_contexts)
    
    # Determine primary channel and coordination lead
    primary_channel = _determine_primary_channel(slack_contexts)
    coordination_lead = _identify_coordination_lead(scheduling_timeline)
    
    # Calculate complexity metrics
    complexity = _calculate_scheduling_complexity(scheduling_timeline)
    
    return SlackEnhancedMeeting(
        # Base fields from CorrelatedMeeting
        correlation_id=correlated_meeting.correlation_id,
        meeting_title=correlated_meeting.meeting_title,
        meeting_datetime=correlated_meeting.meeting_datetime,
        participants=correlated_meeting.participants,
        email_record=correlated_meeting.email_record,
        doc_record=correlated_meeting.doc_record,
        correlation_match=correlated_meeting.correlation_match,
        correlation_status=correlated_meeting.correlation_status,
        confidence_score=correlated_meeting.confidence_score,
        meeting_content=correlated_meeting.meeting_content,
        action_items=correlated_meeting.action_items,
        todos=correlated_meeting.todos,
        deadlines=correlated_meeting.deadlines,
        created_at=correlated_meeting.created_at,
        updated_at=datetime.now(timezone.utc),
        source_files=correlated_meeting.source_files,
        
        # Slack enhancement fields
        slack_contexts=slack_contexts,
        primary_slack_channel=primary_channel,
        scheduling_timeline=scheduling_timeline,
        slack_participant_mapping=participant_mapping,
        participant_resolution_score=len(participant_mapping) / max(len(correlated_meeting.participants), 1),
        coordination_lead=coordination_lead,
        scheduling_complexity=complexity,
        pre_meeting_discussions=sum(ctx.meeting_intent_count for ctx in slack_contexts),
        post_meeting_actions=sum(ctx.follow_up_messages for ctx in slack_contexts),
        meeting_importance_score=importance_score,
        coordination_effectiveness_score=coordination_score,
        follow_through_score=follow_through_score
    )


def _calculate_importance_score(meeting: CorrelatedMeeting, slack_contexts: List[SlackContext]) -> float:
    """Calculate meeting importance based on all available signals"""
    score = 0.0
    
    # Base score from correlation confidence
    score += meeting.confidence_score * 0.3
    
    # Participant count (more people = more important)
    score += min(len(meeting.participants) * 0.1, 0.3)
    
    # Slack activity level
    if slack_contexts:
        avg_coordination = sum(ctx.coordination_score for ctx in slack_contexts) / len(slack_contexts)
        score += avg_coordination * 0.2
        
        # Multiple channels suggests importance
        if len(slack_contexts) > 1:
            score += 0.1
    
    # Action items and todos suggest importance
    score += min((len(meeting.action_items) + len(meeting.todos)) * 0.05, 0.2)
    
    return min(score, 1.0)


def _calculate_coordination_effectiveness(scheduling_timeline: List[Dict[str, Any]], 
                                        slack_contexts: List[SlackContext]) -> float:
    """Calculate how effectively the meeting was coordinated"""
    score = 0.0
    
    # Having a scheduling timeline is good
    if scheduling_timeline:
        score += 0.4
        
        # More coordination messages = better organization
        score += min(len(scheduling_timeline) * 0.1, 0.3)
    
    # High coordination scores in Slack contexts
    if slack_contexts:
        avg_coordination = sum(ctx.coordination_score for ctx in slack_contexts) / len(slack_contexts)
        score += avg_coordination * 0.3
    
    return min(score, 1.0)


def _calculate_follow_through_score(slack_contexts: List[SlackContext]) -> float:
    """Calculate follow-through effectiveness based on post-meeting activity"""
    if not slack_contexts:
        return 0.0
    
    total_follow_ups = sum(ctx.follow_up_messages for ctx in slack_contexts)
    
    # Some follow-up is good, too much might indicate problems
    if total_follow_ups == 0:
        return 0.0
    elif total_follow_ups <= 5:
        return 0.8
    elif total_follow_ups <= 10:
        return 1.0
    else:
        return 0.6  # Too many follow-ups might indicate confusion


def _determine_primary_channel(slack_contexts: List[SlackContext]) -> Optional[str]:
    """Determine the primary Slack channel for coordination"""
    if not slack_contexts:
        return None
    
    # Channel with highest coordination score
    primary = max(slack_contexts, key=lambda ctx: ctx.coordination_score)
    return primary.channel_id


def _identify_coordination_lead(scheduling_timeline: List[Dict[str, Any]]) -> Optional[str]:
    """Identify who led the meeting coordination"""
    if not scheduling_timeline:
        return None
    
    # Count messages per user in scheduling timeline
    user_counts = {}
    for msg in scheduling_timeline:
        user_id = msg.get('user', 'unknown')
        user_counts[user_id] = user_counts.get(user_id, 0) + 1
    
    if user_counts:
        # Person who sent the most scheduling messages
        return max(user_counts, key=user_counts.get)
    
    return None


def _calculate_scheduling_complexity(scheduling_timeline: List[Dict[str, Any]]) -> float:
    """Calculate how complex the scheduling process was"""
    if not scheduling_timeline:
        return 0.0
    
    # Simple heuristic based on number of scheduling messages
    message_count = len(scheduling_timeline)
    
    if message_count <= 2:
        return 0.2  # Very simple
    elif message_count <= 5:
        return 0.5  # Moderate
    elif message_count <= 10:
        return 0.8  # Complex
    else:
        return 1.0  # Very complex


# Example usage
if __name__ == "__main__":
    # Example correlation match
    match = CorrelationMatch(
        email_id="email_001",
        doc_id="doc_001", 
        match_type=MatchType.TEMPORAL,
        confidence_score=0.85,
        match_details={
            "time_diff_minutes": 2,
            "participant_overlap": 0.75,
            "title_similarity": 0.60
        },
        created_at=datetime.now(timezone.utc)
    )
    
    # Example correlated meeting
    email_record = {
        "title": "Weekly Team Sync",
        "participants": ["david@company.com", "sarah@company.com"],
        "meeting_datetime": datetime.now(timezone.utc),
        "content": "Meeting agenda and discussion points..."
    }
    
    doc_record = {
        "title": "Weekly Team Sync Notes",
        "content": "Meeting notes and action items...",
        "meeting_metadata": {
            "participants": ["David", "Sarah"],
            "date": datetime.now().date()
        }
    }
    
    correlated_meeting = CorrelatedMeeting.from_email_and_doc(
        email_record, doc_record, match
    )
    
    print("Example correlated meeting:")
    print(serialize_correlation_record(correlated_meeting))