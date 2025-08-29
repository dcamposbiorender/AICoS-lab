#!/usr/bin/env python3
"""
Calendar Personalizer - Calendar Display Personalization for AI Chief of Staff

Personalizes calendar display to focus on PRIMARY_USER's events and activities.
Provides user-centric calendar filtering while maintaining backwards compatibility.

References:
- src/personalization/simple_filter.py - Core filtering patterns
- tools/load_dashboard_data.py - Dashboard data loading patterns
- tasks/phase6_agent_l_personalization.md - Complete specification
"""

import logging
from typing import Any, Dict, List, Optional, Set
from datetime import datetime, timedelta
from pathlib import Path
from .simple_filter import SimpleFilter

logger = logging.getLogger(__name__)

class CalendarPersonalizer:
    """
    Personalize calendar display for PRIMARY_USER
    
    Features:
    - Filters calendar events to focus on user's meetings
    - Identifies user role in events (organizer/attendee/optional)
    - Enhances events with user context and highlighting
    - Provides availability and conflict analysis
    - Maintains backwards compatibility without PRIMARY_USER
    
    Usage:
        personalizer = CalendarPersonalizer()
        user_events = personalizer.filter_user_events(all_events, user)
        enhanced_events = personalizer.enhance_calendar_display(events)
    """
    
    def __init__(self, simple_filter: Optional[SimpleFilter] = None):
        """
        Initialize CalendarPersonalizer
        
        Args:
            simple_filter: Optional SimpleFilter instance for user detection
        """
        self.filter = simple_filter or SimpleFilter()
        
        if self.filter.primary_user:
            logger.info(f"✅ CalendarPersonalizer initialized with PRIMARY_USER: {self.filter.primary_user['email']}")
        else:
            logger.info("ℹ️ CalendarPersonalizer initialized without PRIMARY_USER (no personalization)")
    
    def filter_user_events(self, events: List[Dict[str, Any]], user: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Filter events involving the user
        
        Args:
            events: List of calendar events
            user: User configuration (uses PRIMARY_USER if None)
            
        Returns:
            List of events involving the user
        """
        if not events:
            return []
            
        target_user = user or self.filter.primary_user
        if not target_user:
            return events  # Return all events if no user specified
            
        user_events = []
        for event in events:
            if self.is_user_event(event, target_user):
                enhanced_event = self.enhance_user_event(event, target_user)
                user_events.append(enhanced_event)
                
        logger.debug(f"📅 Filtered {len(user_events)} user events from {len(events)} total events")
        return user_events
    
    def is_user_event(self, event: Dict[str, Any], user: Dict[str, Any]) -> bool:
        """
        Check if event involves the user
        
        Args:
            event: Calendar event data
            user: User configuration
            
        Returns:
            True if user is involved in the event
        """
        if not event or not user:
            return False
            
        user_email = user.get("email", "").lower()
        if not user_email:
            return False
            
        # Check if user is organizer
        if self._is_user_organizer(event, user_email):
            return True
            
        # Check if user is attendee
        if self._is_user_attendee(event, user_email):
            return True
            
        # Check calendar ownership
        if self._is_user_calendar(event, user_email):
            return True
            
        return False
    
    def _is_user_organizer(self, event: Dict[str, Any], user_email: str) -> bool:
        """Check if user is the organizer of the event"""
        organizer = event.get("organizer")
        
        # Handle string organizer
        if isinstance(organizer, str):
            return organizer.lower() == user_email
            
        # Handle organizer object
        if isinstance(organizer, dict):
            organizer_email = organizer.get("email", "")
            return organizer_email.lower() == user_email
            
        # Check common organizer fields
        organizer_fields = ["organizer_email", "creator", "owner"]
        for field in organizer_fields:
            value = event.get(field)
            if value and isinstance(value, str) and value.lower() == user_email:
                return True
                
        return False
    
    def _is_user_attendee(self, event: Dict[str, Any], user_email: str) -> bool:
        """Check if user is an attendee of the event"""
        attendees = event.get("attendees", [])
        
        if not isinstance(attendees, list):
            return False
            
        for attendee in attendees:
            # Handle string attendee
            if isinstance(attendee, str):
                if attendee.lower() == user_email:
                    return True
            # Handle attendee object
            elif isinstance(attendee, dict):
                attendee_email = attendee.get("email", "")
                if attendee_email.lower() == user_email:
                    return True
                    
        return False
    
    def _is_user_calendar(self, event: Dict[str, Any], user_email: str) -> bool:
        """Check if event is on user's calendar"""
        calendar_fields = ["calendar", "calendar_id", "calendar_email"]
        
        for field in calendar_fields:
            value = event.get(field)
            if value and isinstance(value, str) and value.lower() == user_email:
                return True
                
        return False
    
    def enhance_user_event(self, event: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add user context to event display
        
        Args:
            event: Calendar event data
            user: User configuration
            
        Returns:
            Enhanced event with user context
        """
        # Create a copy to avoid modifying original
        enhanced_event = event.copy()
        user_email = user.get("email", "").lower()
        
        # Determine user role
        user_role = self._determine_user_role(event, user_email)
        enhanced_event["user_role"] = user_role
        
        # Add user-centric enhancements
        enhanced_event["is_user_event"] = True
        enhanced_event["primary_user_email"] = user.get("email")
        
        # Enhance title with user context
        if user_role == "organizer":
            enhanced_event["display_title"] = f"{event.get('title', 'Meeting')} (You're organizing)"
        elif user_role == "attendee":
            enhanced_event["display_title"] = f"{event.get('title', 'Meeting')} (You're attending)"
        elif user_role == "optional":
            enhanced_event["display_title"] = f"{event.get('title', 'Meeting')} (Optional)"
        else:
            enhanced_event["display_title"] = event.get('title', 'Meeting')
            
        # Add conflict detection
        enhanced_event["has_conflicts"] = self._detect_conflicts(event)
        
        # Add preparation time indicator
        enhanced_event["needs_prep"] = self._needs_preparation(event, user_role)
        
        return enhanced_event
    
    def _determine_user_role(self, event: Dict[str, Any], user_email: str) -> str:
        """Determine user's role in the event"""
        if self._is_user_organizer(event, user_email):
            return "organizer"
        elif self._is_user_attendee(event, user_email):
            # Check if optional attendee
            attendees = event.get("attendees", [])
            for attendee in attendees:
                if isinstance(attendee, dict):
                    attendee_email = attendee.get("email", "").lower()
                    if attendee_email == user_email:
                        response_status = attendee.get("responseStatus", "")
                        if response_status == "tentative":
                            return "optional"
            return "attendee"
        else:
            return "unknown"
    
    def _detect_conflicts(self, event: Dict[str, Any]) -> bool:
        """Simple conflict detection (placeholder for now)"""
        # This could be enhanced with actual conflict detection logic
        # For now, return False as no conflicts detected
        return False
    
    def _needs_preparation(self, event: Dict[str, Any], user_role: str) -> bool:
        """Determine if event needs preparation"""
        if user_role == "organizer":
            return True  # Organizers usually need to prepare
            
        # Check for keywords suggesting preparation needed
        title = event.get("title", "").lower()
        description = event.get("description", "").lower()
        
        prep_keywords = [
            "demo", "presentation", "pitch", "review", "interview",
            "training", "workshop", "planning", "strategy"
        ]
        
        for keyword in prep_keywords:
            if keyword in title or keyword in description:
                return True
                
        return False
    
    def get_calendar_summary(self, events: List[Dict[str, Any]], user: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate calendar summary for the user
        
        Args:
            events: List of calendar events
            user: User configuration (uses PRIMARY_USER if None)
            
        Returns:
            Dictionary with calendar summary
        """
        target_user = user or self.filter.primary_user
        if not target_user or not events:
            return {}
            
        user_events = self.filter_user_events(events, target_user)
        
        # Categorize events by user role
        role_counts = {"organizer": 0, "attendee": 0, "optional": 0}
        prep_needed = 0
        conflicts = 0
        
        for event in user_events:
            role = event.get("user_role", "unknown")
            if role in role_counts:
                role_counts[role] += 1
                
            if event.get("needs_prep", False):
                prep_needed += 1
                
            if event.get("has_conflicts", False):
                conflicts += 1
        
        # Calculate time commitment
        total_hours = self._calculate_meeting_hours(user_events)
        
        return {
            "total_events": len(events),
            "user_events": len(user_events),
            "organizing": role_counts["organizer"],
            "attending": role_counts["attendee"],
            "optional": role_counts["optional"],
            "needs_preparation": prep_needed,
            "conflicts": conflicts,
            "total_hours": total_hours,
            "primary_user": target_user.get("email")
        }
    
    def _calculate_meeting_hours(self, events: List[Dict[str, Any]]) -> float:
        """Calculate total hours for meetings"""
        total_minutes = 0
        
        for event in events:
            start_time = event.get("start_datetime") or event.get("start")
            end_time = event.get("end_datetime") or event.get("end")
            
            if start_time and end_time:
                try:
                    # Parse datetime strings
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
                    # Default to 1 hour if parsing fails
                    total_minutes += 60
            else:
                # Default to 1 hour if no times available
                total_minutes += 60
                
        return total_minutes / 60  # Convert to hours
    
    def format_user_calendar_display(self, events: List[Dict[str, Any]]) -> List[str]:
        """
        Format calendar events for user-centric display
        
        Args:
            events: List of enhanced calendar events
            
        Returns:
            List of formatted event strings
        """
        if not events:
            return ["📅 No meetings scheduled"]
            
        formatted_events = []
        
        for event in events:
            # Get display components
            title = event.get("display_title", event.get("title", "Meeting"))
            start_time = event.get("start_datetime") or event.get("start", "")
            user_role = event.get("user_role", "")
            
            # Format time
            time_str = ""
            if start_time:
                try:
                    if isinstance(start_time, str):
                        dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                        time_str = dt.strftime("%I:%M %p")
                except (ValueError, TypeError):
                    time_str = start_time[:5] if len(start_time) >= 5 else start_time
            
            # Add role indicator
            role_indicator = ""
            if user_role == "organizer":
                role_indicator = " 🎯"
            elif event.get("needs_prep", False):
                role_indicator = " 📋"
                
            # Combine components
            display_line = f"• {time_str} - {title}{role_indicator}"
            formatted_events.append(display_line)
            
        return formatted_events

# Convenience function for dashboard integration
def load_user_calendar_data(calendar_data: List[Dict[str, Any]], user: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Process calendar data with user personalization
    
    Args:
        calendar_data: Raw calendar event data
        user: User configuration (uses PRIMARY_USER if None)
        
    Returns:
        Personalized calendar data for display
    """
    personalizer = CalendarPersonalizer()
    
    # Filter and enhance user events
    user_events = personalizer.filter_user_events(calendar_data, user)
    
    # Get calendar summary
    summary = personalizer.get_calendar_summary(calendar_data, user)
    
    # Format for display
    display_events = personalizer.format_user_calendar_display(user_events)
    
    return {
        "user_events": user_events,
        "summary": summary,
        "display_events": display_events,
        "personalized": bool(personalizer.filter.primary_user)
    }

if __name__ == "__main__":
    # Test the CalendarPersonalizer system
    print("🧪 Testing CalendarPersonalizer System")
    print("=" * 40)
    
    # Initialize personalizer
    personalizer = CalendarPersonalizer()
    
    if personalizer.filter.primary_user:
        user_email = personalizer.filter.primary_user['email']
        print(f"✅ PRIMARY_USER configured: {user_email}")
        
        # Create test events
        test_events = [
            {
                "id": "event1",
                "title": "Team meeting", 
                "organizer": {"email": user_email},
                "attendees": [{"email": user_email}, {"email": "other@company.com"}],
                "start_datetime": "2025-08-28T09:00:00",
                "end_datetime": "2025-08-28T10:00:00"
            },
            {
                "id": "event2",
                "title": "Other meeting",
                "organizer": {"email": "other@company.com"},
                "attendees": [{"email": "other@company.com"}],
                "start_datetime": "2025-08-28T11:00:00",
                "end_datetime": "2025-08-28T12:00:00"
            },
            {
                "id": "event3", 
                "title": "1:1 with manager",
                "organizer": {"email": "manager@company.com"},
                "attendees": [{"email": user_email}, {"email": "manager@company.com"}],
                "start_datetime": "2025-08-28T14:00:00",
                "end_datetime": "2025-08-28T14:30:00"
            }
        ]
        
        # Filter user events
        user_events = personalizer.filter_user_events(test_events)
        print(f"\n📅 User events: {len(user_events)}/{len(test_events)}")
        
        for event in user_events:
            role = event.get("user_role", "unknown")
            title = event.get("display_title", event.get("title", "Meeting"))
            print(f"  • {title} (Role: {role})")
        
        # Get calendar summary
        summary = personalizer.get_calendar_summary(test_events)
        print(f"\n📊 Calendar summary:")
        print(f"  Organizing: {summary.get('organizing', 0)}")
        print(f"  Attending: {summary.get('attending', 0)}")
        print(f"  Total hours: {summary.get('total_hours', 0):.1f}")
        
    else:
        print("ℹ️ No PRIMARY_USER configured (no personalization)")
        print("  Calendar will show all events equally")
        
    print("\n✅ CalendarPersonalizer system test complete")