"""
CRM Data Models - Extend existing PersonResolver with rich CRM capabilities

References:
- src/queries/person_queries.py - PersonResolver for cross-system ID mapping
- src/core/config.py - Configuration management patterns
- tests/fixtures/mock_data.py - Test data structure patterns

Core Philosophy: Extend existing infrastructure rather than replace it
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime, date
from enum import Enum
import json
import uuid


class ActionDirection(Enum):
    """Direction of commitment/action item"""
    I_OWE = "i_owe"
    THEY_OWE = "they_owe"


class ActionStatus(Enum):
    """Status of action item"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    OVERDUE = "overdue"


class InteractionType(Enum):
    """Types of interactions"""
    SLACK_MESSAGE = "slack_message"
    SLACK_THREAD = "slack_thread"
    EMAIL = "email"
    MEETING = "meeting"
    PHONE_CALL = "phone_call"
    DOCUMENT = "document"
    NOTE = "note"


@dataclass
class CRMPerson:
    """
    Enhanced person profile extending PersonResolver data
    
    Builds on existing 209-person roster with rich CRM fields
    """
    # Core fields (from existing PersonResolver)
    email: str
    name: str
    slack_id: Optional[str] = None
    
    # Professional information
    company: str = ""
    role: str = ""
    department: str = ""
    phone: str = ""
    location: str = ""
    timezone: str = ""
    
    # Contact preferences
    linkedin: str = ""
    twitter: str = ""
    github: str = ""
    website: str = ""
    
    # Rich profile data
    background: str = ""
    interests: List[str] = field(default_factory=list)
    expertise: List[str] = field(default_factory=list)
    
    # Relationship data
    reports_to: Optional[str] = None
    team_members: List[str] = field(default_factory=list)
    key_relationships: Dict[str, str] = field(default_factory=dict)  # email -> relationship_type
    
    # Communication metadata
    preferred_channel: str = "email"  # email, slack, phone
    response_time: str = "same_day"  # immediate, same_day, 24h, week
    meeting_preference: str = "video"  # in_person, video, phone
    
    # Important dates
    important_dates: List[Dict[str, str]] = field(default_factory=list)  # [{"date": "MM-DD", "description": "Birthday"}]
    
    # CRM metadata
    tags: List[str] = field(default_factory=list)
    first_seen: Optional[datetime] = None
    last_interaction: Optional[datetime] = None
    interaction_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Set timestamps if not provided"""
        now = datetime.now()
        if self.created_at is None:
            self.created_at = now
        if self.updated_at is None:
            self.updated_at = now
    
    def update_field(self, field_name: str, new_value: Any, author: str = "system"):
        """Update a field with audit tracking"""
        if hasattr(self, field_name):
            setattr(self, field_name, new_value)
            self.updated_at = datetime.now()
            # Note: Audit trail will be handled by CRMDirectory
    
    def add_tag(self, tag: str):
        """Add a tag if not already present"""
        if tag not in self.tags:
            self.tags.append(tag)
            self.updated_at = datetime.now()
    
    def remove_tag(self, tag: str):
        """Remove a tag if present"""
        if tag in self.tags:
            self.tags.remove(tag)
            self.updated_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        data = {}
        for field_name, field_value in self.__dict__.items():
            if isinstance(field_value, datetime):
                data[field_name] = field_value.isoformat()
            elif isinstance(field_value, date):
                data[field_name] = field_value.isoformat()
            else:
                data[field_name] = field_value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CRMPerson':
        """Create instance from dictionary"""
        # Convert datetime strings back to datetime objects
        datetime_fields = ['first_seen', 'last_interaction', 'created_at', 'updated_at']
        for field in datetime_fields:
            if field in data and data[field]:
                if isinstance(data[field], str):
                    data[field] = datetime.fromisoformat(data[field])
        
        return cls(**data)


@dataclass
class Note:
    """Note about a person"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    person_email: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    author: str = "system"
    content: str = ""
    source: str = "manual"  # manual, extracted, meeting, etc.
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "id": self.id,
            "person_email": self.person_email,
            "timestamp": self.timestamp.isoformat(),
            "author": self.author,
            "content": self.content,
            "source": self.source,
            "tags": self.tags,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Note':
        """Create instance from dictionary"""
        if isinstance(data['timestamp'], str):
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


@dataclass
class ActionItem:
    """Bidirectional commitment/action item tracking"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    direction: ActionDirection = ActionDirection.I_OWE
    counterparty: str = ""  # email of the other person
    description: str = ""
    due_date: Optional[datetime] = None
    status: ActionStatus = ActionStatus.PENDING
    priority: str = "medium"  # low, medium, high, urgent
    
    # Source tracking
    source: str = ""  # Reference to where this came from (slack://, cal://, etc.)
    context: str = ""  # Additional context about the commitment
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    last_reminded: Optional[datetime] = None
    
    # Extraction metadata (for automatically extracted items)
    confidence: float = 1.0  # 0.0 to 1.0 confidence score
    extraction_method: str = "manual"  # manual, pattern, llm, etc.
    
    # Reminder settings
    reminder_dates: List[datetime] = field(default_factory=list)
    follow_up_required: bool = False
    
    # Additional metadata
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_overdue(self) -> bool:
        """Check if action item is overdue"""
        if not self.due_date:
            return False
        return self.due_date < datetime.now() and self.status not in [ActionStatus.COMPLETED, ActionStatus.CANCELLED]
    
    def days_until_due(self) -> Optional[int]:
        """Calculate days until due date"""
        if not self.due_date:
            return None
        delta = self.due_date - datetime.now()
        return delta.days
    
    def update_status(self, new_status: ActionStatus, note: str = "", author: str = "system"):
        """Update status with validation"""
        # Status transition validation
        valid_transitions = {
            ActionStatus.PENDING: [ActionStatus.IN_PROGRESS, ActionStatus.COMPLETED, ActionStatus.CANCELLED],
            ActionStatus.IN_PROGRESS: [ActionStatus.COMPLETED, ActionStatus.CANCELLED, ActionStatus.PENDING],
            ActionStatus.COMPLETED: [],  # Completed items cannot change
            ActionStatus.CANCELLED: [ActionStatus.PENDING, ActionStatus.IN_PROGRESS],
            ActionStatus.OVERDUE: [ActionStatus.IN_PROGRESS, ActionStatus.COMPLETED, ActionStatus.CANCELLED]
        }
        
        if new_status not in valid_transitions.get(self.status, []):
            raise ValueError(f"Invalid status transition from {self.status} to {new_status}")
        
        self.status = new_status
        if new_status == ActionStatus.COMPLETED:
            self.completed_at = datetime.now()
        
        # Store status change in metadata for audit trail
        if 'status_history' not in self.metadata:
            self.metadata['status_history'] = []
        
        self.metadata['status_history'].append({
            'from_status': self.status.value if self.status else None,
            'to_status': new_status.value,
            'timestamp': datetime.now().isoformat(),
            'note': note,
            'author': author
        })
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        data = {
            'id': self.id,
            'direction': self.direction.value,
            'counterparty': self.counterparty,
            'description': self.description,
            'status': self.status.value,
            'priority': self.priority,
            'source': self.source,
            'context': self.context,
            'confidence': self.confidence,
            'extraction_method': self.extraction_method,
            'follow_up_required': self.follow_up_required,
            'tags': self.tags,
            'metadata': self.metadata
        }
        
        # Handle datetime fields
        datetime_fields = ['due_date', 'created_at', 'completed_at', 'last_reminded']
        for field in datetime_fields:
            value = getattr(self, field)
            if value:
                data[field] = value.isoformat()
            else:
                data[field] = None
        
        # Handle reminder dates
        data['reminder_dates'] = [rd.isoformat() for rd in self.reminder_dates]
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ActionItem':
        """Create instance from dictionary"""
        # Convert enum strings back to enums
        if 'direction' in data:
            data['direction'] = ActionDirection(data['direction'])
        if 'status' in data:
            data['status'] = ActionStatus(data['status'])
        
        # Convert datetime strings back to datetime objects
        datetime_fields = ['due_date', 'created_at', 'completed_at', 'last_reminded']
        for field in datetime_fields:
            if field in data and data[field]:
                if isinstance(data[field], str):
                    data[field] = datetime.fromisoformat(data[field])
        
        # Handle reminder dates
        if 'reminder_dates' in data:
            data['reminder_dates'] = [
                datetime.fromisoformat(rd) if isinstance(rd, str) else rd 
                for rd in data['reminder_dates']
            ]
        
        return cls(**data)


@dataclass
class Interaction:
    """Interaction/communication record"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    person_email: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    interaction_type: InteractionType = InteractionType.NOTE
    
    # Content
    summary: str = ""
    content: str = ""
    
    # Source information
    source: str = ""  # slack, calendar, drive, email
    source_id: str = ""  # Message ID, event ID, etc.
    reference: str = ""  # Full reference (slack://C123/p456)
    
    # Context
    channel: str = ""  # Slack channel, meeting room, etc.
    participants: List[str] = field(default_factory=list)  # Other participants
    duration_minutes: Optional[int] = None
    
    # Analysis
    key_topics: List[str] = field(default_factory=list)
    sentiment_score: Optional[float] = None  # -1.0 to 1.0
    follow_up_required: bool = False
    
    # Threading (for related interactions)
    parent_interaction_id: Optional[str] = None
    thread_id: Optional[str] = None
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        data = self.__dict__.copy()
        data['timestamp'] = self.timestamp.isoformat()
        data['interaction_type'] = self.interaction_type.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Interaction':
        """Create instance from dictionary"""
        if isinstance(data['timestamp'], str):
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        if isinstance(data['interaction_type'], str):
            data['interaction_type'] = InteractionType(data['interaction_type'])
        return cls(**data)


@dataclass
class Relationship:
    """Relationship between two people"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    from_person: str = ""  # email
    to_person: str = ""  # email
    relationship_type: str = ""  # manager, peer, client, vendor, etc.
    strength: float = 0.5  # 0.0 to 1.0
    context: str = ""  # How do they know each other
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    last_interaction: Optional[datetime] = None
    
    # Metadata
    mutual: bool = False  # Is this a mutual relationship
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        data = self.__dict__.copy()
        data['created_at'] = self.created_at.isoformat()
        if self.last_interaction:
            data['last_interaction'] = self.last_interaction.isoformat()
        else:
            data['last_interaction'] = None
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Relationship':
        """Create instance from dictionary"""
        if isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if data.get('last_interaction') and isinstance(data['last_interaction'], str):
            data['last_interaction'] = datetime.fromisoformat(data['last_interaction'])
        return cls(**data)