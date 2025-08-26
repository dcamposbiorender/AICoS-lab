#!/usr/bin/env python3
"""
Calendar Analysis Script for Workstream Analysis

Analyzes David's calendar data to understand time allocation across workstreams
based on meeting content, attendees, and patterns.

Key Features:
- Maps meetings to workstreams based on attendees and content
- Analyzes time allocation patterns
- Identifies key meetings and stakeholders
- Extracts meeting notes and action items from linked documents

Usage:
    python analyze_calendar.py
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any
from collections import defaultdict, Counter
import re

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Target email for analysis
TARGET_EMAIL = "david.campos@biorender.com"

# Meeting patterns that indicate workstreams
WORKSTREAM_MEETING_PATTERNS = {
    "gtm_efficiency": {
        "keywords": ["pipeline", "sales", "gtm", "revenue", "funnel", "conversion", "quota", "forecast"],
        "meeting_names": ["Pipeline Council", "Sales Review", "Revenue Review", "Forecast Review"],
        "key_attendees": [
            "charlie@biorender.com",
            "ryan.gerstein@biorender.com", 
            "stefan@biorender.com",
            "michael.litwin@biorender.com",
            "francesca@biorender.com",
            "lucas@biorender.com",
            "walid@biorender.com",
            "paige.anderson@biorender.com",
            "livia.guo@biorender.com",
            "matthew.smith@biorender.com",
            "chris.hemberger@biorender.com"
        ]
    },
    "data_platform": {
        "keywords": ["data", "analytics", "dashboard", "metrics", "looker", "signal", "insights"],
        "meeting_names": ["Data Review", "Analytics", "Dashboard"],
        "key_attendees": ["adam.shapiro@biorender.com"]
    },
    "ai_transformation": {
        "keywords": ["ai", "artificial intelligence", "automation", "agent", "governance", "ml", "machine learning"],
        "meeting_names": ["AI Council", "AI Review", "Automation"],
        "key_attendees": ["katya@biorender.com", "jon.fan@biorender.com"]
    },
    "executive": {
        "keywords": ["exec", "leadership", "strategy", "board", "offsites"],
        "meeting_names": ["Exec Weekly", "Executive", "Leadership", "Board", "Strategy"],
        "key_attendees": [
            "philip@biorender.com",
            "katya@biorender.com",
            "meghana.reddy@biorender.com",
            "michael.edmonson@biorender.com",
            "omri@biorender.com",
            "shiz@biorender.com", 
            "natalie@biorender.com"
        ]
    },
    "cost_optimization": {
        "keywords": ["cost", "budget", "efficiency", "optimization", "spend", "savings"],
        "meeting_names": ["Budget Review", "Cost Review", "Financial Review"],
        "key_attendees": []  # Cross-functional
    }
}

def find_calendar_file(base_path: Path, target_email: str) -> Optional[Path]:
    """Find the calendar file for the target user"""
    calendar_paths = [
        base_path / "data" / "raw" / "calendar",
        base_path / "data" / "archive" / "calendar"
    ]
    
    target_filename = target_email.replace("@", "_at_").replace(".", "_") + ".jsonl"
    
    for base_calendar_path in calendar_paths:
        if not base_calendar_path.exists():
            continue
            
        # Look in date subdirectories
        for date_dir in base_calendar_path.glob("2025-*"):
            if date_dir.is_dir():
                calendar_file = date_dir / f"employee_{target_filename}"
                if calendar_file.exists():
                    return calendar_file
    
    return None

def analyze_meeting_workstream(meeting: Dict[str, Any]) -> Dict[str, float]:
    """Determine which workstream(s) a meeting belongs to"""
    scores = defaultdict(float)
    
    meeting_title = meeting.get('summary', '').lower()
    description = meeting.get('description', '').lower()
    attendee_emails = [
        attendee.get('email', '').lower() 
        for attendee in meeting.get('attendees', [])
    ]
    
    for workstream, patterns in WORKSTREAM_MEETING_PATTERNS.items():
        # Score based on meeting title/description keywords
        for keyword in patterns['keywords']:
            if keyword in meeting_title or keyword in description:
                scores[workstream] += 2.0
        
        # Score based on meeting name patterns
        for meeting_pattern in patterns['meeting_names']:
            if meeting_pattern.lower() in meeting_title:
                scores[workstream] += 5.0
        
        # Score based on key attendees
        key_attendee_overlap = set(attendee_emails).intersection(
            set(patterns['key_attendees'])
        )
        scores[workstream] += len(key_attendee_overlap) * 3.0
    
    return dict(scores)

def extract_meeting_duration(meeting: Dict[str, Any]) -> float:
    """Extract meeting duration in hours"""
    try:
        start_str = meeting.get('start', {}).get('dateTime')
        end_str = meeting.get('end', {}).get('dateTime')
        
        if not start_str or not end_str:
            return 0.0
        
        # Parse ISO datetime strings
        start = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
        end = datetime.fromisoformat(end_str.replace('Z', '+00:00'))
        
        duration = end - start
        return duration.total_seconds() / 3600  # Convert to hours
    except Exception:
        return 0.0

def extract_linked_documents(meeting: Dict[str, Any]) -> List[Dict[str, str]]:
    """Extract linked Google Docs/Drive documents from meeting"""
    documents = []
    
    # Check attachments
    for attachment in meeting.get('attachments', []):
        if 'docs.google.com' in attachment.get('fileUrl', ''):
            documents.append({
                'title': attachment.get('title', ''),
                'url': attachment.get('fileUrl', ''),
                'type': attachment.get('mimeType', ''),
                'file_id': attachment.get('fileId', '')
            })
    
    # Check description for Google Docs links
    description = meeting.get('description', '')
    google_doc_pattern = r'https://docs\.google\.com/[^)\s]+'
    for match in re.finditer(google_doc_pattern, description):
        documents.append({
            'title': 'Document from description',
            'url': match.group(),
            'type': 'inferred',
            'file_id': ''
        })
    
    return documents

def analyze_calendar_data(calendar_file: Path) -> Dict[str, Any]:
    """Analyze calendar data for workstream insights"""
    
    meetings = []
    workstream_time = defaultdict(float)
    workstream_meetings = defaultdict(int)
    meeting_frequency = defaultdict(list)
    key_stakeholders = Counter()
    
    # Load and process calendar events
    with open(calendar_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f):
            try:
                line = line.strip()
                if not line:
                    continue
                
                meeting = json.loads(line)
                
                # Skip non-events or events without proper time
                if meeting.get('kind') != 'calendar#event':
                    continue
                
                # Analyze workstream relevance
                workstream_scores = analyze_meeting_workstream(meeting)
                
                # Get meeting duration
                duration = extract_meeting_duration(meeting)
                
                # Get attendees
                attendees = [
                    attendee.get('email', '') 
                    for attendee in meeting.get('attendees', [])
                ]
                
                # Extract documents
                documents = extract_linked_documents(meeting)
                
                # Create meeting record
                meeting_record = {
                    'id': meeting.get('id'),
                    'title': meeting.get('summary', ''),
                    'start': meeting.get('start', {}).get('dateTime'),
                    'duration_hours': duration,
                    'attendees': attendees,
                    'workstream_scores': workstream_scores,
                    'primary_workstream': max(workstream_scores, key=workstream_scores.get) if workstream_scores else 'unclassified',
                    'documents': documents,
                    'description': meeting.get('description', ''),
                    'meeting_url': meeting.get('hangoutLink', ''),
                    'recurring': bool(meeting.get('recurringEventId'))
                }
                
                meetings.append(meeting_record)
                
                # Accumulate workstream time
                if workstream_scores:
                    primary_workstream = max(workstream_scores, key=workstream_scores.get)
                    workstream_time[primary_workstream] += duration
                    workstream_meetings[primary_workstream] += 1
                
                # Track key stakeholders
                for attendee in attendees:
                    if attendee != TARGET_EMAIL:
                        key_stakeholders[attendee] += 1
                
                # Track meeting frequency
                if meeting.get('start', {}).get('dateTime'):
                    date_str = meeting['start']['dateTime'][:10]  # YYYY-MM-DD
                    meeting_frequency[date_str].append(meeting_record['title'])
                
            except json.JSONDecodeError as e:
                print(f"Warning: Could not parse line {line_num + 1}: {e}")
                continue
    
    return {
        'meetings': meetings,
        'workstream_time_allocation': dict(workstream_time),
        'workstream_meeting_counts': dict(workstream_meetings),
        'key_stakeholders': dict(key_stakeholders),
        'meeting_frequency': dict(meeting_frequency),
        'analysis_stats': {
            'total_meetings': len(meetings),
            'total_hours': sum(workstream_time.values()),
            'classified_meetings': len([m for m in meetings if m['primary_workstream'] != 'unclassified']),
            'meetings_with_documents': len([m for m in meetings if m['documents']]),
        }
    }

def generate_calendar_insights(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Generate insights from calendar analysis"""
    
    workstream_time = analysis['workstream_time_allocation']
    total_time = sum(workstream_time.values())
    
    insights = {
        'time_allocation_percentage': {
            workstream: (hours / total_time * 100) if total_time > 0 else 0
            for workstream, hours in workstream_time.items()
        },
        'top_workstreams_by_time': sorted(
            workstream_time.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5],
        'most_frequent_stakeholders': sorted(
            analysis['key_stakeholders'].items(),
            key=lambda x: x[1],
            reverse=True
        )[:10],
        'recurring_meetings': [
            meeting for meeting in analysis['meetings']
            if meeting['recurring']
        ],
        'document_rich_meetings': [
            meeting for meeting in analysis['meetings']
            if len(meeting['documents']) > 0
        ]
    }
    
    return insights

def main():
    """Main execution function"""
    print("Starting calendar analysis for workstream mapping...")
    
    # Setup paths
    base_path = Path(__file__).parent.parent.parent.parent
    output_path = Path(__file__).parent.parent / "data_extraction"
    
    # Find calendar file
    print(f"Looking for calendar data for {TARGET_EMAIL}...")
    calendar_file = find_calendar_file(base_path, TARGET_EMAIL)
    
    if not calendar_file:
        print(f"ERROR: Could not find calendar file for {TARGET_EMAIL}")
        return
    
    print(f"Using calendar file: {calendar_file}")
    
    # Analyze calendar data
    print("Analyzing calendar data...")
    analysis = analyze_calendar_data(calendar_file)
    
    # Generate insights
    print("Generating insights...")
    insights = generate_calendar_insights(analysis)
    
    # Save results
    output_file = output_path / "calendar_analysis.json"
    output_data = {
        'analysis_metadata': {
            'target_user': TARGET_EMAIL,
            'calendar_file': str(calendar_file),
            'analysis_timestamp': datetime.now().isoformat()
        },
        'analysis': analysis,
        'insights': insights
    }
    
    output_path.mkdir(exist_ok=True)
    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)
    
    # Print summary
    print(f"\n=== CALENDAR ANALYSIS SUMMARY ===")
    print(f"Total meetings analyzed: {analysis['analysis_stats']['total_meetings']}")
    print(f"Total meeting hours: {analysis['analysis_stats']['total_hours']:.1f}")
    print(f"Classified meetings: {analysis['analysis_stats']['classified_meetings']}")
    print(f"Meetings with documents: {analysis['analysis_stats']['meetings_with_documents']}")
    
    print(f"\n=== TOP WORKSTREAMS BY TIME ===")
    for workstream, percentage in list(insights['time_allocation_percentage'].items())[:5]:
        hours = analysis['workstream_time_allocation'].get(workstream, 0)
        print(f"{workstream}: {percentage:.1f}% ({hours:.1f} hours)")
    
    print(f"\n=== TOP STAKEHOLDERS ===")
    for stakeholder, count in insights['most_frequent_stakeholders'][:5]:
        print(f"{stakeholder}: {count} meetings")
    
    print(f"\nResults saved to: {output_file}")

if __name__ == "__main__":
    main()