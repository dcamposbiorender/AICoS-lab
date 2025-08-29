"""
Dossier Generator - Comprehensive person profiles for micro-CRM

References:
- src/people/interaction_manager.py - Interaction extraction from SearchDatabase
- src/people/crm_directory.py - Person profiles and action items
- src/queries/person_queries.py - PersonQueries for activity analysis
- src/aggregators/basic_stats.py - Activity statistics patterns

Core Philosophy: Generate rich, actionable dossiers by combining all available data sources.
Provides executives with complete context about any person in their network.
"""

import json
import logging
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict, Counter
from pathlib import Path

from .interaction_manager import InteractionManager
from .crm_directory import CRMDirectory
from .models import CRMPerson, ActionItem, Interaction, ActionDirection, ActionStatus
from ..core.config import get_config

logger = logging.getLogger(__name__)


class DossierGenerator:
    """
    Generate comprehensive person dossiers combining all available data
    
    Features:
    - Rich person profiles with background and interests
    - Complete interaction history from SearchDatabase
    - Bidirectional action item tracking
    - Communication patterns and preferences
    - Relationship mapping and context
    - Activity summaries and insights
    """
    
    def __init__(self, crm_db_path: Optional[str] = None, search_db_path: Optional[str] = None, crm_instance: Optional['CRMDirectory'] = None):
        """Initialize dossier generator with CRM and interaction data"""
        self.crm = crm_instance if crm_instance else CRMDirectory(crm_db_path)
        self.interaction_manager = InteractionManager(search_db_path, crm_db_path, self.crm)
        
        # Performance settings
        self.default_interaction_days = 30
        self.max_interactions_display = 20
        self.max_action_items_display = 50
        
        logger.info("DossierGenerator initialized")
        logger.info(f"CRM people count: {self.crm.count_people()}")
    
    def generate_dossier(self, email: str, interaction_days: int = None) -> Dict[str, Any]:
        """
        Generate comprehensive dossier for a person
        
        Args:
            email: Person's email address
            interaction_days: Days of interaction history to include
            
        Returns:
            Complete dossier dictionary
        """
        if interaction_days is None:
            interaction_days = self.default_interaction_days
        
        start_time = datetime.now()
        
        # Get base person profile from CRM
        person = self.crm.get_person_by_email(email)
        if not person:
            # Try to find in existing resolver and import
            try:
                imported = self.crm.enrich_from_resolver()
                if imported > 0:
                    person = self.crm.get_person_by_email(email)
            except Exception as e:
                logger.error(f"Failed to import from resolver: {e}")
        
        if not person:
            return self._generate_minimal_dossier(email)
        
        # Get recent interactions
        interactions = self.interaction_manager.get_person_interactions(
            email, days=interaction_days, limit=self.max_interactions_display
        )
        
        # Get action items
        i_owe = self.crm.get_actions_i_owe_person(email) if hasattr(self.crm, 'get_actions_i_owe_person') else []
        they_owe = self.crm.get_actions_they_owe_me(email) if hasattr(self.crm, 'get_actions_they_owe_me') else []
        
        # Get notes
        notes = self.crm.get_person_notes(email, limit=10)
        
        # Generate communication insights
        communication_insights = self._analyze_communication_patterns(interactions)
        
        # Generate activity summary
        activity_summary = self._generate_activity_summary(interactions, interaction_days)
        
        # Generate relationship context
        relationship_context = self._analyze_relationships(person, interactions)
        
        # Generate quick stats
        quick_stats = self._generate_quick_stats(person, interactions, i_owe, they_owe)
        
        # Build complete dossier
        dossier = {
            "profile": {
                "email": person.email,
                "name": person.name,
                "title": person.role,
                "company": person.company,
                "department": person.department,
                "location": person.location,
                "timezone": person.timezone,
                "phone": person.phone,
                "linkedin": person.linkedin,
                "twitter": person.twitter,
                "background": person.background,
                "interests": person.interests,
                "expertise": person.expertise,
                "tags": person.tags,
                "preferred_channel": person.preferred_channel,
                "response_time": person.response_time,
                "meeting_preference": person.meeting_preference
            },
            "quick_stats": quick_stats,
            "recent_interactions": {
                "count": len(interactions),
                "days_covered": interaction_days,
                "interactions": [self._format_interaction_summary(i) for i in interactions[:10]]
            },
            "action_items": {
                "i_owe": [self._format_action_item(a) for a in i_owe[:25]],
                "they_owe": [self._format_action_item(a) for a in they_owe[:25]],
                "summary": {
                    "total_i_owe": len(i_owe),
                    "total_they_owe": len(they_owe),
                    "overdue_i_owe": len([a for a in i_owe if a.is_overdue()]),
                    "overdue_they_owe": len([a for a in they_owe if a.is_overdue()])
                }
            },
            "communication_insights": communication_insights,
            "activity_summary": activity_summary,
            "relationship_context": relationship_context,
            "notes": [self._format_note(n) for n in notes],
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "generation_time": (datetime.now() - start_time).total_seconds(),
                "data_freshness": {
                    "last_interaction": person.last_interaction.isoformat() if person.last_interaction else None,
                    "profile_updated": person.updated_at.isoformat(),
                    "interaction_search_days": interaction_days
                }
            }
        }
        
        logger.info(f"Generated dossier for {email} in {dossier['metadata']['generation_time']:.2f}s")
        
        return dossier
    
    def _generate_minimal_dossier(self, email: str) -> Dict[str, Any]:
        """Generate minimal dossier for unknown person"""
        return {
            "profile": {
                "email": email,
                "name": email.split('@')[0].replace('.', ' ').title(),
                "title": "Unknown",
                "company": "",
                "status": "not_in_crm"
            },
            "quick_stats": {
                "total_interactions": 0,
                "total_action_items": 0,
                "last_contact": None
            },
            "recent_interactions": {"count": 0, "interactions": []},
            "action_items": {"i_owe": [], "they_owe": [], "summary": {"total_i_owe": 0, "total_they_owe": 0}},
            "communication_insights": {},
            "activity_summary": {},
            "relationship_context": {},
            "notes": [],
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "status": "person_not_found",
                "suggestion": "Consider adding this person to the CRM manually"
            }
        }
    
    def _analyze_communication_patterns(self, interactions: List[Interaction]) -> Dict[str, Any]:
        """Analyze communication patterns from interactions"""
        if not interactions:
            return {}
        
        # Channel distribution
        channel_counts = Counter(i.source for i in interactions)
        
        # Time patterns (hour of day)
        hour_counts = Counter(i.timestamp.hour for i in interactions)
        
        # Day of week patterns
        weekday_counts = Counter(i.timestamp.strftime('%A') for i in interactions)
        
        # Response time analysis (simplified)
        interaction_gaps = []
        sorted_interactions = sorted(interactions, key=lambda x: x.timestamp)
        for i in range(1, len(sorted_interactions)):
            gap = (sorted_interactions[i].timestamp - sorted_interactions[i-1].timestamp).total_seconds() / 3600  # hours
            if gap < 168:  # Less than a week
                interaction_gaps.append(gap)
        
        avg_response_time = sum(interaction_gaps) / len(interaction_gaps) if interaction_gaps else 0
        
        # Communication frequency
        days_span = (interactions[0].timestamp - interactions[-1].timestamp).days if len(interactions) > 1 else 1
        frequency = len(interactions) / max(days_span, 1)  # interactions per day
        
        return {
            "preferred_channels": dict(channel_counts.most_common()),
            "peak_hours": dict(sorted(hour_counts.items())),
            "active_days": dict(weekday_counts.most_common()),
            "avg_response_time_hours": round(avg_response_time, 1),
            "communication_frequency": round(frequency, 2),
            "total_interactions": len(interactions),
            "analysis_period_days": days_span
        }
    
    def _generate_activity_summary(self, interactions: List[Interaction], days: int) -> Dict[str, Any]:
        """Generate activity summary from interactions"""
        if not interactions:
            return {"activity_level": "none", "summary": "No recent activity"}
        
        # Activity level calculation
        activity_per_day = len(interactions) / days
        
        if activity_per_day >= 2:
            activity_level = "high"
        elif activity_per_day >= 0.5:
            activity_level = "medium"
        else:
            activity_level = "low"
        
        # Topic analysis
        all_topics = []
        for interaction in interactions:
            all_topics.extend(interaction.key_topics)
        
        top_topics = Counter(all_topics).most_common(10)
        
        # Meeting vs message ratio
        meetings = len([i for i in interactions if i.interaction_type.name == 'MEETING'])
        messages = len([i for i in interactions if 'MESSAGE' in i.interaction_type.name])
        documents = len([i for i in interactions if i.interaction_type.name == 'DOCUMENT'])
        
        # Recent trend
        if len(interactions) >= 10:
            recent_half = interactions[:len(interactions)//2]
            older_half = interactions[len(interactions)//2:]
            
            recent_days = (recent_half[0].timestamp - recent_half[-1].timestamp).days or 1
            older_days = (older_half[0].timestamp - older_half[-1].timestamp).days or 1
            
            recent_rate = len(recent_half) / recent_days
            older_rate = len(older_half) / older_days
            
            if recent_rate > older_rate * 1.2:
                trend = "increasing"
            elif recent_rate < older_rate * 0.8:
                trend = "decreasing"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"
        
        summary_text = f"{activity_level.title()} activity with {len(interactions)} interactions over {days} days"
        if top_topics:
            summary_text += f". Main topics: {', '.join([t[0] for t in top_topics[:3]])}"
        
        return {
            "activity_level": activity_level,
            "interactions_per_day": round(activity_per_day, 1),
            "trend": trend,
            "interaction_types": {
                "meetings": meetings,
                "messages": messages,
                "documents": documents
            },
            "top_topics": dict(top_topics),
            "summary": summary_text
        }
    
    def _analyze_relationships(self, person: CRMPerson, interactions: List[Interaction]) -> Dict[str, Any]:
        """Analyze relationship context from person profile and interactions"""
        context = {}
        
        # Direct relationships from profile
        if person.reports_to:
            context["manager"] = person.reports_to
        
        if person.team_members:
            context["direct_reports"] = person.team_members
        
        if person.key_relationships:
            context["key_relationships"] = person.key_relationships
        
        # Interaction-based relationships
        if interactions:
            # Most frequent collaborators
            all_participants = []
            for interaction in interactions:
                all_participants.extend(interaction.participants)
            
            frequent_contacts = Counter(all_participants).most_common(10)
            # Filter out the person themselves
            frequent_contacts = [(email, count) for email, count in frequent_contacts 
                               if email.lower() != person.email.lower()]
            
            context["frequent_collaborators"] = dict(frequent_contacts[:5])
            
            # Recent contacts (last 7 days)
            recent_cutoff = datetime.now() - timedelta(days=7)
            recent_interactions = [i for i in interactions if i.timestamp > recent_cutoff]
            
            recent_contacts = set()
            for interaction in recent_interactions:
                recent_contacts.update(interaction.participants)
            
            recent_contacts.discard(person.email.lower())
            context["recent_contacts"] = list(recent_contacts)[:10]
        
        return context
    
    def _generate_quick_stats(self, person: CRMPerson, interactions: List[Interaction], 
                            i_owe: List[ActionItem], they_owe: List[ActionItem]) -> Dict[str, Any]:
        """Generate quick overview statistics"""
        return {
            "total_interactions": len(interactions),
            "last_contact": interactions[0].timestamp.isoformat() if interactions else None,
            "days_since_contact": (datetime.now() - interactions[0].timestamp).days if interactions else None,
            "total_action_items": len(i_owe) + len(they_owe),
            "active_commitments": len([a for a in i_owe + they_owe if a.status == ActionStatus.PENDING]),
            "overdue_items": len([a for a in i_owe + they_owe if a.is_overdue()]),
            "notes_count": len(self.crm.get_person_notes(person.email)),
            "crm_updated": person.updated_at.isoformat(),
            "interaction_count": person.interaction_count,
            "profile_completeness": self._calculate_profile_completeness(person)
        }
    
    def _calculate_profile_completeness(self, person: CRMPerson) -> int:
        """Calculate profile completeness percentage"""
        total_fields = 15  # Key profile fields
        filled_fields = 0
        
        if person.name and person.name != person.email.split('@')[0]:
            filled_fields += 1
        if person.role:
            filled_fields += 1
        if person.company:
            filled_fields += 1
        if person.department:
            filled_fields += 1
        if person.location:
            filled_fields += 1
        if person.phone:
            filled_fields += 1
        if person.linkedin:
            filled_fields += 1
        if person.background:
            filled_fields += 1
        if person.interests:
            filled_fields += 1
        if person.expertise:
            filled_fields += 1
        if person.preferred_channel:
            filled_fields += 1
        if person.response_time:
            filled_fields += 1
        if person.meeting_preference:
            filled_fields += 1
        if person.tags:
            filled_fields += 1
        if person.important_dates:
            filled_fields += 1
        
        return int((filled_fields / total_fields) * 100)
    
    def _format_interaction_summary(self, interaction: Interaction) -> Dict[str, Any]:
        """Format interaction for dossier display"""
        return {
            "timestamp": interaction.timestamp.isoformat(),
            "type": interaction.interaction_type.value,
            "source": interaction.source,
            "summary": interaction.summary,
            "channel": interaction.channel,
            "participants": interaction.participants[:5],  # Limit participants
            "key_topics": interaction.key_topics[:5],  # Limit topics
            "reference": interaction.reference,
            "duration_minutes": interaction.duration_minutes
        }
    
    def _format_action_item(self, action: ActionItem) -> Dict[str, Any]:
        """Format action item for dossier display"""
        return {
            "id": action.id,
            "description": action.description,
            "due_date": action.due_date.isoformat() if action.due_date else None,
            "status": action.status.value,
            "priority": action.priority,
            "days_until_due": action.days_until_due(),
            "is_overdue": action.is_overdue(),
            "source": action.source,
            "context": action.context,
            "created_at": action.created_at.isoformat(),
            "confidence": action.confidence,
            "tags": action.tags
        }
    
    def _format_note(self, note) -> Dict[str, Any]:
        """Format note for dossier display"""
        return {
            "id": note.id,
            "timestamp": note.timestamp.isoformat(),
            "author": note.author,
            "content": note.content,
            "source": note.source,
            "tags": note.tags
        }
    
    def generate_bulk_dossiers(self, emails: List[str], interaction_days: int = 30) -> Dict[str, Dict]:
        """Generate dossiers for multiple people efficiently"""
        start_time = datetime.now()
        dossiers = {}
        
        for email in emails:
            try:
                dossier = self.generate_dossier(email, interaction_days)
                dossiers[email] = dossier
            except Exception as e:
                logger.error(f"Failed to generate dossier for {email}: {e}")
                dossiers[email] = {"error": str(e), "email": email}
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Add bulk operation metadata
        bulk_metadata = {
            "total_dossiers": len(emails),
            "successful": len([d for d in dossiers.values() if "error" not in d]),
            "failed": len([d for d in dossiers.values() if "error" in d]),
            "total_processing_time": processing_time,
            "avg_time_per_dossier": processing_time / len(emails) if emails else 0,
            "generated_at": datetime.now().isoformat()
        }
        
        return {
            "dossiers": dossiers,
            "bulk_metadata": bulk_metadata
        }
    
    def get_dossier_summary(self, email: str) -> Dict[str, Any]:
        """Get a lightweight summary version of a dossier"""
        person = self.crm.get_person_by_email(email)
        if not person:
            return {"error": "Person not found", "email": email}
        
        # Get minimal interaction data
        interactions = self.interaction_manager.get_person_interactions(email, days=7, limit=5)
        
        # Get action counts
        i_owe = self.crm.get_actions_i_owe() if hasattr(self.crm, 'get_actions_i_owe') else []
        they_owe = self.crm.get_actions_they_owe_me(email) if hasattr(self.crm, 'get_actions_they_owe_me') else []
        
        i_owe_count = len([a for a in i_owe if a.counterparty == email])
        
        return {
            "email": email,
            "name": person.name,
            "title": person.role,
            "company": person.company,
            "last_contact": interactions[0].timestamp.isoformat() if interactions else None,
            "interaction_count_7d": len(interactions),
            "action_items": {
                "i_owe": i_owe_count,
                "they_owe": len(they_owe),
                "overdue": len([a for a in i_owe + they_owe if a.is_overdue()])
            },
            "profile_completeness": self._calculate_profile_completeness(person),
            "tags": person.tags[:5]  # Top 5 tags
        }
    
    def search_dossiers(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for people and return dossier summaries"""
        # Use CRM search to find matching people
        people = self.crm.search_people(query)
        
        # Generate summaries for matches
        summaries = []
        for person in people[:limit]:
            try:
                summary = self.get_dossier_summary(person.email)
                summaries.append(summary)
            except Exception as e:
                logger.error(f"Failed to generate summary for {person.email}: {e}")
                continue
        
        return summaries