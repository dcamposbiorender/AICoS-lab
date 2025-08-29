#!/usr/bin/env python3
"""
Realistic Test Data Generator for End-to-End Tests

Generates realistic Slack conversations, Calendar events, Drive activity, and Employee data
to simulate authentic executive workflows and usage patterns.

This module creates comprehensive test scenarios that mirror real organizational behavior:
- Natural conversation patterns with commitment language
- Realistic meeting schedules with conflicts and coordination
- Document activity reflecting business workflows
- Employee interactions with hierarchical relationships
"""

import json
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple
from pathlib import Path


class RealisticTestDataGenerator:
    """Generate realistic test data for executive AI assistant testing"""
    
    def __init__(self, base_date: datetime = None):
        """Initialize with configurable base date for temporal data"""
        self.base_date = base_date or datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
        
        # Executive personas and team structure
        self.executives = [
            {"id": "U001", "name": "Sarah Chen", "email": "sarah@company.com", "role": "CEO"},
            {"id": "U002", "name": "Marcus Rodriguez", "email": "marcus@company.com", "role": "CTO"},
            {"id": "U003", "name": "Jennifer Walsh", "email": "jennifer@company.com", "role": "VP Sales"}
        ]
        
        self.team_members = [
            {"id": "U101", "name": "David Kim", "email": "david@company.com", "role": "Engineering Manager"},
            {"id": "U102", "name": "Lisa Zhang", "email": "lisa@company.com", "role": "Product Manager"},
            {"id": "U103", "name": "Tom Johnson", "email": "tom@company.com", "role": "Sales Director"},
            {"id": "U104", "name": "Rachel Williams", "email": "rachel@company.com", "role": "Marketing Director"},
            {"id": "U105", "name": "Alex Thompson", "email": "alex@company.com", "role": "Finance Manager"}
        ]
        
        self.all_people = self.executives + self.team_members
        
        # Channels representing different organizational contexts
        self.channels = [
            {"id": "C001", "name": "exec-team", "purpose": "Executive team coordination"},
            {"id": "C002", "name": "product-strategy", "purpose": "Product planning and strategy"},
            {"id": "C003", "name": "sales-updates", "purpose": "Sales team updates and metrics"},
            {"id": "C004", "name": "engineering", "purpose": "Engineering team coordination"},
            {"id": "C005", "name": "all-hands", "purpose": "Company-wide announcements"}
        ]
        
        # Commitment patterns executives commonly use
        self.commitment_patterns = [
            "I'll {action} by {deadline}",
            "Let me {action} and get back to you {timeframe}",
            "I'll have {person} {action} by {deadline}",
            "We need to {action} before {deadline}",
            "I'll make sure {action} happens {timeframe}",
            "Can you {action} by {deadline}?",
            "I'll follow up on {topic} {timeframe}",
            "Let's schedule a {meeting_type} to discuss {topic}"
        ]
        
        # Meeting types and contexts
        self.meeting_types = [
            {"type": "1:1", "duration": 30, "frequency": "weekly"},
            {"type": "team standup", "duration": 15, "frequency": "daily"},
            {"type": "strategy session", "duration": 60, "frequency": "monthly"},
            {"type": "board meeting", "duration": 120, "frequency": "quarterly"},
            {"type": "product review", "duration": 45, "frequency": "biweekly"},
            {"type": "sales forecast", "duration": 30, "frequency": "monthly"},
            {"type": "all hands", "duration": 60, "frequency": "monthly"}
        ]

    def generate_executive_day_scenario(self, days_back: int = 0) -> Dict[str, Any]:
        """
        Generate a complete day's worth of realistic executive activity
        
        Returns comprehensive scenario with:
        - Morning briefing context
        - Slack conversations with commitments
        - Calendar events with coordination needs
        - Drive activity reflecting document workflows
        """
        scenario_date = self.base_date - timedelta(days=days_back)
        
        return {
            "date": scenario_date.isoformat(),
            "slack_messages": self._generate_executive_slack_day(scenario_date),
            "calendar_events": self._generate_executive_calendar_day(scenario_date),
            "drive_activity": self._generate_executive_drive_day(scenario_date),
            "commitments_expected": self._extract_expected_commitments(),
            "search_scenarios": self._generate_search_scenarios(scenario_date)
        }

    def _generate_executive_slack_day(self, date: datetime) -> List[Dict[str, Any]]:
        """Generate realistic Slack conversations for an executive's day"""
        messages = []
        
        # Early morning urgent coordination
        messages.extend(self._create_conversation_thread(
            channel="C001",  # exec-team
            start_time=date.replace(hour=7, minute=15),
            thread_context="urgent budget discussion",
            participants=["U001", "U002", "U005"],  # CEO, CTO, Finance Manager
            message_count=8,
            include_commitments=True
        ))
        
        # Mid-morning product strategy discussion
        messages.extend(self._create_conversation_thread(
            channel="C002",  # product-strategy
            start_time=date.replace(hour=9, minute=45),
            thread_context="Q4 product roadmap",
            participants=["U001", "U002", "U102"],  # CEO, CTO, Product Manager
            message_count=12,
            include_commitments=True
        ))
        
        # Afternoon sales coordination
        messages.extend(self._create_conversation_thread(
            channel="C003",  # sales-updates
            start_time=date.replace(hour=2, minute=30),
            thread_context="large enterprise deal",
            participants=["U001", "U003", "U103"],  # CEO, VP Sales, Sales Director
            message_count=6,
            include_commitments=True
        ))
        
        # Evening follow-up and planning
        messages.extend(self._create_conversation_thread(
            channel="C001",  # exec-team
            start_time=date.replace(hour=17, minute=45),
            thread_context="tomorrow's board presentation",
            participants=["U001", "U002", "U003"],  # Executive team
            message_count=10,
            include_commitments=True
        ))
        
        return messages

    def _generate_executive_calendar_day(self, date: datetime) -> List[Dict[str, Any]]:
        """Generate realistic calendar events for executive coordination testing"""
        events = []
        
        # Morning executive team meeting
        events.append(self._create_calendar_event(
            summary="Executive Team Weekly Sync",
            start_time=date.replace(hour=8, minute=0),
            duration_minutes=60,
            attendees=["sarah@company.com", "marcus@company.com", "jennifer@company.com"],
            event_type="recurring",
            description="Weekly executive alignment and decision-making"
        ))
        
        # Mid-morning 1:1 with key direct report
        events.append(self._create_calendar_event(
            summary="1:1 - Product Strategy Review",
            start_time=date.replace(hour=10, minute=30),
            duration_minutes=30,
            attendees=["sarah@company.com", "lisa@company.com"],
            event_type="1:1",
            description="Product roadmap and resource allocation discussion"
        ))
        
        # Lunch meeting with potential partner
        events.append(self._create_calendar_event(
            summary="Partnership Discussion - TechCorp",
            start_time=date.replace(hour=12, minute=0),
            duration_minutes=90,
            attendees=["sarah@company.com", "external@techcorp.com"],
            event_type="external",
            description="Strategic partnership exploration"
        ))
        
        # Afternoon board prep session
        events.append(self._create_calendar_event(
            summary="Board Meeting Preparation",
            start_time=date.replace(hour=15, minute=0),
            duration_minutes=60,
            attendees=["sarah@company.com", "marcus@company.com", "alex@company.com"],
            event_type="preparation",
            description="Review metrics and presentation materials"
        ))
        
        # Scheduling conflict scenario
        events.append(self._create_calendar_event(
            summary="CONFLICT: Customer Escalation Call",
            start_time=date.replace(hour=15, minute=30),  # Overlaps with board prep
            duration_minutes=30,
            attendees=["sarah@company.com", "jennifer@company.com", "tom@company.com"],
            event_type="conflict",
            description="Urgent customer issue requiring immediate attention"
        ))
        
        return events

    def _generate_executive_drive_day(self, date: datetime) -> List[Dict[str, Any]]:
        """Generate Drive activity reflecting executive document workflows"""
        activities = []
        
        # Morning document preparation
        activities.append({
            "id": f"drive_activity_{date.strftime('%Y%m%d')}_001",
            "type": "document_edit",
            "file_name": "Q4 Board Presentation.pptx",
            "file_id": "1BxY2zZqW3eR4tY5uI6oP7aS8dF9gH0jK",
            "timestamp": date.replace(hour=6, minute=45).isoformat(),
            "activity": "Major revisions to financial projections",
            "user": "sarah@company.com",
            "changes": 47,
            "collaborators": ["marcus@company.com", "alex@company.com"]
        })
        
        # Mid-day document sharing
        activities.append({
            "id": f"drive_activity_{date.strftime('%Y%m%d')}_002",
            "type": "document_share",
            "file_name": "Product Roadmap Q4-Q1.docx",
            "file_id": "2CzA3aAqX4fS5uZ6vJ7pQ8bT9eG0hI1jL",
            "timestamp": date.replace(hour=11, minute=15).isoformat(),
            "activity": "Shared with engineering team for feedback",
            "user": "sarah@company.com",
            "shared_with": ["david@company.com", "lisa@company.com", "marcus@company.com"],
            "permissions": "comment"
        })
        
        # Afternoon document creation
        activities.append({
            "id": f"drive_activity_{date.strftime('%Y%m%d')}_003",
            "type": "document_create",
            "file_name": "Partnership Agreement - TechCorp Draft.docx",
            "file_id": "3DaB4bBqY5gT6vA7wK8qR9cU0fH1iJ2kM",
            "timestamp": date.replace(hour=14, minute=30).isoformat(),
            "activity": "Initial draft based on lunch meeting",
            "user": "sarah@company.com",
            "template_used": "Standard Partnership Template",
            "sections": ["Terms", "Responsibilities", "Timeline", "Success Metrics"]
        })
        
        return activities

    def _create_conversation_thread(self, channel: str, start_time: datetime, 
                                  thread_context: str, participants: List[str],
                                  message_count: int, include_commitments: bool = True) -> List[Dict[str, Any]]:
        """Create realistic conversation thread with natural flow"""
        messages = []
        thread_ts = str(start_time.timestamp())
        
        # Initial message setting context
        initial_user = participants[0]
        messages.append({
            "id": f"msg_{thread_ts}",
            "type": "message",
            "text": self._generate_context_setting_message(thread_context),
            "user": initial_user,
            "channel": channel,
            "ts": thread_ts,
            "created_at": start_time.isoformat(),
            "source": "slack",
            "thread_ts": thread_ts if message_count > 1 else None
        })
        
        # Follow-up messages in thread
        for i in range(1, message_count):
            message_time = start_time + timedelta(minutes=random.randint(2, 15))
            user = random.choice(participants)
            
            message_text = self._generate_thread_response(
                thread_context, i, message_count, include_commitments and i > message_count//2
            )
            
            messages.append({
                "id": f"msg_{thread_ts}_{i}",
                "type": "message", 
                "text": message_text,
                "user": user,
                "channel": channel,
                "ts": f"{message_time.timestamp()}",
                "created_at": message_time.isoformat(),
                "source": "slack",
                "thread_ts": thread_ts
            })
            
            start_time = message_time
        
        return messages

    def _create_calendar_event(self, summary: str, start_time: datetime,
                             duration_minutes: int, attendees: List[str],
                             event_type: str, description: str) -> Dict[str, Any]:
        """Create realistic calendar event with proper metadata"""
        end_time = start_time + timedelta(minutes=duration_minutes)
        
        return {
            "id": f"event_{start_time.strftime('%Y%m%d_%H%M')}_{random.randint(1000,9999)}",
            "summary": summary,
            "description": description,
            "start": {
                "dateTime": start_time.isoformat(),
                "timeZone": "America/Los_Angeles"
            },
            "end": {
                "dateTime": end_time.isoformat(),
                "timeZone": "America/Los_Angeles"
            },
            "attendees": [{"email": email, "responseStatus": "accepted"} for email in attendees],
            "created_at": (start_time - timedelta(hours=24)).isoformat(),
            "source": "calendar",
            "event_type": event_type,
            "location": self._get_meeting_location(event_type),
            "conference_data": self._get_conference_details(event_type) if event_type != "external" else None
        }

    def _generate_context_setting_message(self, context: str) -> str:
        """Generate natural opening message for conversation context"""
        templates = {
            "urgent budget discussion": [
                "We need to talk about the Q4 budget numbers - they're not looking good",
                "Just got off a call with the board about budget concerns",
                "Can we jump on a quick call about the budget situation?"
            ],
            "Q4 product roadmap": [
                "Team, we need to finalize the Q4 roadmap by EOD",
                "The product roadmap discussion from yesterday needs follow-up",
                "I've been thinking about our Q4 priorities and have some concerns"
            ],
            "large enterprise deal": [
                "Update on the TechCorp deal - they want to move fast",
                "The enterprise deal we discussed is heating up",
                "Need to coordinate on the big customer opportunity"
            ],
            "tomorrow's board presentation": [
                "Final review of tomorrow's board deck - are we ready?",
                "Board presentation needs last-minute updates",
                "Can we do a quick run-through of the board materials?"
            ]
        }
        
        return random.choice(templates.get(context, ["Let's discuss " + context]))

    def _generate_thread_response(self, context: str, message_index: int, 
                                total_messages: int, include_commitment: bool) -> str:
        """Generate natural thread response with optional commitment"""
        
        # Early messages are questions/clarifications
        if message_index < total_messages // 3:
            responses = [
                "Can you clarify the timeline on this?",
                "What are the key blockers we're facing?",
                "Who else needs to be involved in this decision?",
                "Do we have the budget allocated for this?"
            ]
        
        # Middle messages provide information/analysis
        elif message_index < 2 * total_messages // 3:
            responses = [
                "Based on the data I'm seeing, we have a few options",
                "I've been looking at this and here's what I found",
                "The numbers show we need to adjust our approach",
                "I talked to the team and they're aligned on this direction"
            ]
        
        # Later messages include commitments and action items
        else:
            if include_commitment:
                responses = [
                    "I'll send the updated numbers by end of day",
                    "Let me follow up with legal and get back to you by Thursday",
                    "I'll have my team prepare the analysis by Monday morning",
                    "I'll schedule a follow-up meeting with all stakeholders for next week",
                    "Let me get the contract reviewed and circulate by Friday"
                ]
            else:
                responses = [
                    "That sounds like the right approach",
                    "I agree with the direction we're taking",
                    "This aligns with what we discussed earlier",
                    "Good point, let's move forward with this plan"
                ]
        
        return random.choice(responses)

    def _extract_expected_commitments(self) -> List[Dict[str, Any]]:
        """Extract expected commitments that should be found in generated messages"""
        return [
            {
                "text": "I'll send the updated numbers by end of day",
                "person": "Sarah Chen",
                "action": "send updated numbers",
                "deadline": "end of day",
                "type": "delivery"
            },
            {
                "text": "Let me follow up with legal and get back to you by Thursday",
                "person": "Marcus Rodriguez", 
                "action": "follow up with legal",
                "deadline": "Thursday",
                "type": "follow_up"
            },
            {
                "text": "I'll have my team prepare the analysis by Monday morning",
                "person": "Jennifer Walsh",
                "action": "prepare analysis",
                "deadline": "Monday morning",
                "type": "delegation"
            }
        ]

    def _generate_search_scenarios(self, date: datetime) -> List[Dict[str, Any]]:
        """Generate realistic search scenarios executives would perform"""
        return [
            {
                "query": "What did we decide about the budget yesterday?",
                "intent": "decision_lookup",
                "expected_sources": ["slack", "calendar"],
                "time_range": "yesterday",
                "expected_results": 3
            },
            {
                "query": "Find all commitments from Jennifer about the sales forecast",
                "intent": "commitment_lookup",
                "expected_sources": ["slack"],
                "person_filter": "Jennifer Walsh",
                "expected_results": 2
            },
            {
                "query": "Show me the product roadmap documents updated this week",
                "intent": "document_search",
                "expected_sources": ["drive"],
                "time_range": "this week",
                "expected_results": 1
            },
            {
                "query": "When is my next 1:1 with Lisa?",
                "intent": "calendar_lookup",
                "expected_sources": ["calendar"],
                "person_filter": "Lisa Zhang",
                "expected_results": 1
            }
        ]

    def _get_meeting_location(self, event_type: str) -> str:
        """Get realistic meeting location based on event type"""
        locations = {
            "recurring": "Conference Room A",
            "1:1": "Sarah's Office", 
            "external": "Downtown Restaurant",
            "preparation": "Conference Room B",
            "conflict": "Video Call"
        }
        return locations.get(event_type, "TBD")

    def _get_conference_details(self, event_type: str) -> Dict[str, Any]:
        """Get conference call details for internal meetings"""
        if event_type in ["external"]:
            return None
            
        return {
            "conferenceId": f"meet-{random.randint(100000, 999999)}",
            "conferenceSolution": {
                "name": "Google Meet",
                "iconUri": "https://meet.google.com/favicon.ico"
            },
            "entryPoints": [{
                "entryPointType": "video",
                "uri": f"https://meet.google.com/abc-def-{random.choice(['ghi', 'jkl', 'mno'])}"
            }]
        }

    def generate_30_day_historical_data(self) -> Dict[str, Any]:
        """Generate 30 days of historical data for comprehensive testing"""
        historical_data = {
            "date_range": {
                "start": (self.base_date - timedelta(days=30)).isoformat(),
                "end": self.base_date.isoformat()
            },
            "daily_scenarios": [],
            "summary_stats": {
                "total_messages": 0,
                "total_events": 0,
                "total_drive_activities": 0,
                "expected_commitments": 0
            }
        }
        
        for days_back in range(30, 0, -1):
            daily_scenario = self.generate_executive_day_scenario(days_back)
            historical_data["daily_scenarios"].append(daily_scenario)
            
            # Update summary stats
            historical_data["summary_stats"]["total_messages"] += len(daily_scenario["slack_messages"])
            historical_data["summary_stats"]["total_events"] += len(daily_scenario["calendar_events"])
            historical_data["summary_stats"]["total_drive_activities"] += len(daily_scenario["drive_activity"])
            historical_data["summary_stats"]["expected_commitments"] += len(daily_scenario["commitments_expected"])
        
        return historical_data

    def save_test_data_to_files(self, output_dir: Path, scenario_name: str = "executive_30day"):
        """Save generated test data to files for use in E2E tests"""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate comprehensive historical data
        historical_data = self.generate_30_day_historical_data()
        
        # Save main scenario file
        scenario_file = output_dir / f"{scenario_name}.json"
        with open(scenario_file, 'w') as f:
            json.dump(historical_data, f, indent=2)
        
        # Save individual daily files for targeted testing
        daily_dir = output_dir / "daily_scenarios"
        daily_dir.mkdir(exist_ok=True)
        
        for i, daily_scenario in enumerate(historical_data["daily_scenarios"]):
            daily_file = daily_dir / f"day_{30-i:02d}.json"
            with open(daily_file, 'w') as f:
                json.dump(daily_scenario, f, indent=2)
        
        print(f"✅ Generated test data saved to {output_dir}")
        print(f"   📊 Total scenarios: {len(historical_data['daily_scenarios'])}")
        print(f"   📧 Total messages: {historical_data['summary_stats']['total_messages']}")
        print(f"   📅 Total events: {historical_data['summary_stats']['total_events']}")
        print(f"   📁 Total drive activities: {historical_data['summary_stats']['total_drive_activities']}")
        print(f"   ✅ Expected commitments: {historical_data['summary_stats']['expected_commitments']}")


def main():
    """Generate test data for development and testing"""
    generator = RealisticTestDataGenerator()
    
    # Save to fixtures directory
    fixtures_dir = Path(__file__).parent
    generator.save_test_data_to_files(fixtures_dir / "generated", "executive_workflow")
    
    print("🎉 Realistic test data generation complete!")


if __name__ == "__main__":
    main()