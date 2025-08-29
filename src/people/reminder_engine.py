"""
Reminder Engine - Proactive commitment and relationship management

References:
- src/people/models.py - ActionItem and reminder data structures
- src/people/crm_directory.py - CRM database operations
- src/people/interaction_manager.py - Interaction analysis patterns
- src/core/config.py - Configuration management

Core Philosophy: Proactively surface action items, upcoming deadlines, and
relationship maintenance opportunities to prevent things from falling through
the cracks in busy executive schedules.
"""

import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

from .models import ActionItem, ActionStatus, ActionDirection, CRMPerson
from .crm_directory import CRMDirectory
from .interaction_manager import InteractionManager

logger = logging.getLogger(__name__)


class ReminderType(Enum):
    """Types of reminders the engine can generate"""
    OVERDUE_ACTION = "overdue_action"
    UPCOMING_DEADLINE = "upcoming_deadline"
    FOLLOW_UP_NEEDED = "follow_up_needed"
    RELATIONSHIP_MAINTENANCE = "relationship_maintenance"
    STALE_COMMITMENT = "stale_commitment"
    RESPONSE_OVERDUE = "response_overdue"


class ReminderPriority(Enum):
    """Priority levels for reminders"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class Reminder:
    """A proactive reminder about an action or relationship"""
    id: str
    type: ReminderType
    priority: ReminderPriority
    title: str
    description: str
    person_email: str
    person_name: str
    action_item_id: Optional[str] = None
    due_date: Optional[datetime] = None
    days_overdue: Optional[int] = None
    suggested_actions: List[str] = None
    context: Dict[str, Any] = None
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.suggested_actions is None:
            self.suggested_actions = []
        if self.context is None:
            self.context = {}


class ReminderEngine:
    """
    Proactive reminder system for commitment and relationship management
    
    Features:
    - Scans for overdue and upcoming action items
    - Identifies stale relationships needing attention
    - Suggests follow-up actions based on interaction patterns
    - Prioritizes reminders based on urgency and relationship importance
    - Tracks reminder history to avoid notification fatigue
    """
    
    def __init__(self, crm_db_path: Optional[str] = None, search_db_path: Optional[str] = None, crm_instance: Optional['CRMDirectory'] = None):
        """Initialize reminder engine with CRM and interaction data"""
        self.crm = crm_instance if crm_instance else CRMDirectory(crm_db_path)
        self.interaction_manager = InteractionManager(search_db_path, crm_db_path, self.crm)
        
        # Reminder configuration
        self.config = {
            'overdue_threshold_days': 0,  # Consider overdue immediately after due date
            'upcoming_threshold_days': 3,  # Warn 3 days before due date
            'stale_relationship_days': 30,  # No interaction for 30 days
            'follow_up_threshold_days': 7,  # Follow up after 7 days of no response
            'max_reminders_per_person': 5,  # Limit to prevent overwhelm
            'priority_escalation_days': 7  # Escalate priority after 7 days overdue
        }
        
        logger.info("ReminderEngine initialized")
    
    def generate_daily_reminders(self) -> List[Reminder]:
        """
        Generate comprehensive daily reminders
        
        Returns:
            List of prioritized reminders for today
        """
        all_reminders = []
        
        # Get overdue actions
        all_reminders.extend(self._get_overdue_action_reminders())
        
        # Get upcoming deadlines
        all_reminders.extend(self._get_upcoming_deadline_reminders())
        
        # Get stale relationships
        all_reminders.extend(self._get_relationship_maintenance_reminders())
        
        # Get follow-up reminders
        all_reminders.extend(self._get_follow_up_reminders())
        
        # Get stale commitment reminders
        all_reminders.extend(self._get_stale_commitment_reminders())
        
        # Sort by priority and limit per person
        prioritized_reminders = self._prioritize_and_limit_reminders(all_reminders)
        
        logger.info(f"Generated {len(prioritized_reminders)} daily reminders "
                   f"from {len(all_reminders)} total candidates")
        
        return prioritized_reminders
    
    def _get_overdue_action_reminders(self) -> List[Reminder]:
        """Generate reminders for overdue action items"""
        reminders = []
        
        # Get all pending actions I owe
        overdue_actions = []
        i_owe_actions = self.crm.get_actions_i_owe(status=ActionStatus.PENDING)
        
        today = datetime.now()
        
        for action in i_owe_actions:
            if action.due_date and action.due_date < today:
                days_overdue = (today - action.due_date).days
                
                # Determine priority based on how overdue
                if days_overdue > self.config['priority_escalation_days']:
                    priority = ReminderPriority.URGENT
                elif days_overdue > 3:
                    priority = ReminderPriority.HIGH
                else:
                    priority = ReminderPriority.MEDIUM
                
                person = self.crm.get_person_by_email(action.counterparty)
                person_name = person.name if person else action.counterparty
                
                reminder = Reminder(
                    id=f"overdue_{action.id}",
                    type=ReminderType.OVERDUE_ACTION,
                    priority=priority,
                    title=f"Overdue: {action.description[:50]}{'...' if len(action.description) > 50 else ''}",
                    description=f"Action item is {days_overdue} days overdue",
                    person_email=action.counterparty,
                    person_name=person_name,
                    action_item_id=action.id,
                    due_date=action.due_date,
                    days_overdue=days_overdue,
                    suggested_actions=[
                        f"Complete: {action.description}",
                        f"Message {person_name} about delay",
                        "Update due date if needed",
                        "Mark as completed if already done"
                    ],
                    context={
                        'action_priority': action.priority,
                        'source': action.source,
                        'created_at': action.created_at
                    }
                )
                
                reminders.append(reminder)
        
        return reminders
    
    def _get_upcoming_deadline_reminders(self) -> List[Reminder]:
        """Generate reminders for upcoming deadlines"""
        reminders = []
        
        # Get all pending actions I owe
        i_owe_actions = self.crm.get_actions_i_owe(status=ActionStatus.PENDING)
        
        today = datetime.now()
        upcoming_threshold = today + timedelta(days=self.config['upcoming_threshold_days'])
        
        for action in i_owe_actions:
            if (action.due_date and 
                action.due_date >= today and 
                action.due_date <= upcoming_threshold):
                
                days_until_due = (action.due_date - today).days
                
                # Determine priority based on urgency
                if days_until_due <= 1:
                    priority = ReminderPriority.HIGH
                else:
                    priority = ReminderPriority.MEDIUM
                
                person = self.crm.get_person_by_email(action.counterparty)
                person_name = person.name if person else action.counterparty
                
                reminder = Reminder(
                    id=f"upcoming_{action.id}",
                    type=ReminderType.UPCOMING_DEADLINE,
                    priority=priority,
                    title=f"Due {days_until_due} day{'s' if days_until_due != 1 else ''}: {action.description[:50]}",
                    description=f"Action item due on {action.due_date.strftime('%B %d')}",
                    person_email=action.counterparty,
                    person_name=person_name,
                    action_item_id=action.id,
                    due_date=action.due_date,
                    suggested_actions=[
                        f"Work on: {action.description}",
                        f"Schedule time to complete",
                        f"Notify {person_name} if delay expected"
                    ],
                    context={
                        'days_until_due': days_until_due,
                        'action_priority': action.priority
                    }
                )
                
                reminders.append(reminder)
        
        return reminders
    
    def _get_relationship_maintenance_reminders(self) -> List[Reminder]:
        """Generate reminders for relationship maintenance"""
        reminders = []
        
        today = datetime.now()
        stale_threshold = today - timedelta(days=self.config['stale_relationship_days'])
        
        # Stream process people in batches to avoid memory issues
        try:
            offset = 0
            batch_size = 100
            max_reminders = 20  # Limit total reminders to prevent overwhelm
            
            while len(reminders) < max_reminders:
                with self.crm._get_connection() as conn:
                    people_batch = conn.execute("""
                        SELECT email, name, last_interaction 
                        FROM people 
                        WHERE last_interaction IS NOT NULL
                        ORDER BY last_interaction DESC
                        LIMIT ? OFFSET ?
                    """, (batch_size, offset)).fetchall()
                
                # If no more people, break
                if not people_batch:
                    break
                
                # Process this batch
                for person_row in people_batch:
                    if len(reminders) >= max_reminders:
                        break
                    
                    person_data = dict(person_row)
                    
                    try:
                        last_interaction_str = person_data.get('last_interaction')
                        if not last_interaction_str:
                            continue
                        
                        last_interaction = datetime.fromisoformat(last_interaction_str)
                        
                        if last_interaction < stale_threshold:
                            days_since = (today - last_interaction).days
                            
                            # Skip if too long (might be inactive relationship)
                            if days_since > 180:
                                continue
                            
                            priority = ReminderPriority.LOW
                            if days_since > 60:
                                priority = ReminderPriority.MEDIUM
                            
                            reminder = Reminder(
                                id=f"stale_relationship_{person_data['email']}",
                                type=ReminderType.RELATIONSHIP_MAINTENANCE,
                                priority=priority,
                                title=f"Haven't connected with {person_data['name']} in {days_since} days",
                                description=f"Last interaction was on {last_interaction.strftime('%B %d')}",
                                person_email=person_data['email'],
                                person_name=person_data['name'],
                                suggested_actions=[
                                    f"Send a check-in message to {person_data['name']}",
                                    "Schedule a coffee chat or brief call",
                                    "Share something relevant to their interests",
                                    "Invite to upcoming team events"
                                ],
                                context={
                                    'days_since_interaction': days_since,
                                    'last_interaction_date': last_interaction.isoformat()
                                }
                            )
                            
                            reminders.append(reminder)
                            
                    except Exception as e:
                        logger.error(f"Failed to process person {person_data.get('email', 'unknown')}: {e}")
                        continue
                
                # Move to next batch
                offset += batch_size
                
        except Exception as e:
            logger.error(f"Failed to get people for relationship maintenance: {e}")
            return reminders
        
        return reminders
    
    def _get_follow_up_reminders(self) -> List[Reminder]:
        """Generate reminders for follow-ups on actions others owe me"""
        reminders = []
        
        # Get actions others owe me that are pending
        they_owe_actions = self.crm.get_actions_they_owe_me(status=ActionStatus.PENDING)
        
        today = datetime.now()
        follow_up_threshold = timedelta(days=self.config['follow_up_threshold_days'])
        
        for action in they_owe_actions:
            # Check if enough time has passed since creation for follow-up
            time_since_created = today - action.created_at
            
            if time_since_created > follow_up_threshold:
                # Check if we haven't reminded recently
                last_reminded = action.last_reminded
                if last_reminded:
                    time_since_reminded = today - last_reminded
                    if time_since_reminded < timedelta(days=3):  # Don't spam
                        continue
                
                person = self.crm.get_person_by_email(action.counterparty)
                person_name = person.name if person else action.counterparty
                
                days_waiting = time_since_created.days
                
                priority = ReminderPriority.LOW
                if days_waiting > 14:
                    priority = ReminderPriority.MEDIUM
                elif action.due_date and action.due_date < today:
                    priority = ReminderPriority.HIGH
                
                reminder = Reminder(
                    id=f"follow_up_{action.id}",
                    type=ReminderType.FOLLOW_UP_NEEDED,
                    priority=priority,
                    title=f"Follow up with {person_name}: {action.description[:40]}",
                    description=f"Waiting {days_waiting} days for response",
                    person_email=action.counterparty,
                    person_name=person_name,
                    action_item_id=action.id,
                    suggested_actions=[
                        f"Send friendly reminder to {person_name}",
                        "Offer assistance or clarification",
                        "Adjust timeline if needed",
                        "Escalate if critical and overdue"
                    ],
                    context={
                        'days_waiting': days_waiting,
                        'due_date': action.due_date.isoformat() if action.due_date else None
                    }
                )
                
                reminders.append(reminder)
        
        return reminders
    
    def _get_stale_commitment_reminders(self) -> List[Reminder]:
        """Generate reminders for commitments that haven't been acted on"""
        reminders = []
        
        # Get all pending actions (both directions)
        all_pending = (self.crm.get_actions_i_owe(status=ActionStatus.PENDING) + 
                      self.crm.get_actions_they_owe_me(status=ActionStatus.PENDING))
        
        today = datetime.now()
        stale_threshold = timedelta(days=21)  # 3 weeks
        
        for action in all_pending:
            time_since_created = today - action.created_at
            
            # Skip if has due date (handled by other reminder types)
            if action.due_date:
                continue
            
            if time_since_created > stale_threshold:
                person = self.crm.get_person_by_email(action.counterparty)
                person_name = person.name if person else action.counterparty
                
                days_stale = time_since_created.days
                
                reminder = Reminder(
                    id=f"stale_commitment_{action.id}",
                    type=ReminderType.STALE_COMMITMENT,
                    priority=ReminderPriority.LOW,
                    title=f"Stale commitment: {action.description[:50]}",
                    description=f"No progress for {days_stale} days",
                    person_email=action.counterparty,
                    person_name=person_name,
                    action_item_id=action.id,
                    suggested_actions=[
                        "Set a specific due date",
                        "Break into smaller actionable steps",
                        "Clarify requirements with counterparty",
                        "Mark as completed if already done",
                        "Cancel if no longer relevant"
                    ],
                    context={
                        'days_stale': days_stale,
                        'direction': action.direction.value
                    }
                )
                
                reminders.append(reminder)
        
        return reminders
    
    def _prioritize_and_limit_reminders(self, reminders: List[Reminder]) -> List[Reminder]:
        """Prioritize reminders and limit to prevent overwhelm"""
        
        # Sort by priority (urgent first) then by creation date
        priority_order = {
            ReminderPriority.URGENT: 0,
            ReminderPriority.HIGH: 1,
            ReminderPriority.MEDIUM: 2,
            ReminderPriority.LOW: 3
        }
        
        sorted_reminders = sorted(
            reminders,
            key=lambda r: (priority_order[r.priority], r.created_at)
        )
        
        # Limit per person to avoid overwhelming about any single relationship
        person_counts = {}
        filtered_reminders = []
        
        for reminder in sorted_reminders:
            person_email = reminder.person_email
            count = person_counts.get(person_email, 0)
            
            if count < self.config['max_reminders_per_person']:
                filtered_reminders.append(reminder)
                person_counts[person_email] = count + 1
        
        # Global limit to prevent daily overwhelm
        return filtered_reminders[:20]
    
    def mark_reminder_acted_upon(self, reminder_id: str, action_taken: str = None):
        """Mark a reminder as acted upon to update tracking"""
        # This would update the underlying action item or relationship
        # For now, we'll just log it
        logger.info(f"Reminder {reminder_id} marked as acted upon: {action_taken}")
        
        # In full implementation, we might:
        # - Update last_reminded timestamp
        # - Add note to person's profile
        # - Update action item status
        # - Track reminder effectiveness metrics
    
    def get_reminder_stats(self) -> Dict[str, Any]:
        """Get statistics about reminders and their effectiveness"""
        return {
            'config': self.config,
            'crm_people_count': self.crm.count_people(),
            'total_pending_actions': len(self.crm.get_actions_i_owe(status=ActionStatus.PENDING)),
            'actions_they_owe': len(self.crm.get_actions_they_owe_me(status=ActionStatus.PENDING))
        }