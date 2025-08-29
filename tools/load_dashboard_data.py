#!/usr/bin/env python3
"""
Dashboard Data Loader - Load real data for Streamlit dashboard

This script processes existing data files and writes JSON files for the dashboard:
- Calendar events from sample data
- Generated priorities from meeting subjects  
- Commitments derived from attendees and action items
- Applied C1/P1/M1 coding system

Usage:
    python tools/load_dashboard_data.py
    python tools/load_dashboard_data.py --output-dir /path/to/data
"""

import argparse
import json
import sys
import random
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def load_sample_calendar_data() -> List[Dict[str, Any]]:
    """Load calendar data with user personalization support"""
    from src.personalization.calendar_filter import load_user_calendar_data
    from src.core.user_identity import UserIdentity
    
    calendar_events = []
    
    # Check if PRIMARY_USER is configured for personalized experience
    try:
        user_identity = UserIdentity()
        primary_user = user_identity.get_primary_user()
        
        if primary_user:
            print(f"📅 Loading personalized calendar data for {primary_user['email']}")
            user_email = primary_user['email']
            
            # Try to load user's specific calendar file
            calendar_file = _find_user_calendar_file(user_email)
            if calendar_file:
                user_calendar_events = _load_user_calendar_file(calendar_file, primary_user)
                if user_calendar_events:
                    print(f"✅ Loaded {len(user_calendar_events)} events from user's calendar")
                    return user_calendar_events
            else:
                print(f"⚠️ User-specific calendar file not found for {user_email}")
                
    except Exception as e:
        print(f"⚠️ Could not load personalized calendar data: {e}")
    
    # Fallback to generic calendar loading
    print("📅 Loading generic calendar data (no personalization)")
    
    # Load sample events from Ryan's analysis
    sample_file = project_root / "experiments" / "ryan_time_analysis" / "sample_real_events.json"
    if sample_file.exists():
        with open(sample_file, 'r') as f:
            data = json.load(f)
            for event in data.get('authentic_calendar_events', []):
                # Convert to dashboard format
                calendar_events.append({
                    'id': event.get('event_id', f"cal_{len(calendar_events)}"),
                    'title': event.get('summary', 'Meeting'),
                    'start': event.get('datetime', datetime.now().isoformat()),
                    'end': (datetime.fromisoformat(event.get('datetime', datetime.now().isoformat()).replace('Z', '+00:00')) + timedelta(hours=1)).isoformat(),
                    'attendees': event.get('attendees', []),
                    'location': event.get('location', ''),
                    'description': event.get('description_excerpt', '')
                })
    
    # Load recent calendar data if available
    calendar_dir = project_root / "data" / "raw" / "calendar"
    if calendar_dir.exists():
        # Get the most recent date directory
        date_dirs = [d for d in calendar_dir.iterdir() if d.is_dir()]
        if date_dirs:
            latest_dir = max(date_dirs, key=lambda x: x.name)
            
            # Load a few employee calendar files
            count = 0
            for calendar_file in latest_dir.glob("employee_*.jsonl"):
                if count >= 3:  # Limit to 3 employees for demo
                    break
                    
                try:
                    with open(calendar_file, 'r') as f:
                        for line in f:
                            if count >= 20:  # Limit total events
                                break
                            event_data = json.loads(line.strip())
                            
                            # Convert to dashboard format
                            calendar_events.append({
                                'id': event_data.get('event_id', f"cal_{len(calendar_events)}"),
                                'title': event_data.get('summary', 'Meeting'),
                                'start': event_data.get('start_datetime', datetime.now().isoformat()),
                                'end': event_data.get('end_datetime', (datetime.now() + timedelta(hours=1)).isoformat()),
                                'attendees': event_data.get('attendees', []),
                                'location': event_data.get('location', ''),
                                'description': event_data.get('description', '')
                            })
                            count += 1
                except Exception as e:
                    print(f"Error loading calendar file {calendar_file}: {e}")
                    continue
    
    # Add some current/future events for demo
    today = datetime.now()
    demo_events = [
        {
            'id': 'demo_1',
            'title': 'Product Sync',
            'start': (today.replace(hour=9, minute=0)).isoformat(),
            'end': (today.replace(hour=10, minute=0)).isoformat(),
            'attendees': ['alice@company.com', 'bob@company.com'],
            'location': 'Conference Room A',
            'description': 'Weekly product team sync'
        },
        {
            'id': 'demo_2', 
            'title': '1:1 w/ Sarah',
            'start': (today.replace(hour=11, minute=0)).isoformat(),
            'end': (today.replace(hour=11, minute=30)).isoformat(),
            'attendees': ['sarah@company.com'],
            'location': 'Sarah\'s Office',
            'description': 'Monthly 1:1 check-in'
        },
        {
            'id': 'demo_3',
            'title': 'Budget Review',
            'start': (today.replace(hour=14, minute=0)).isoformat(),
            'end': (today.replace(hour=15, minute=0)).isoformat(),
            'attendees': ['finance@company.com', 'manager@company.com'],
            'location': 'Finance Office',
            'description': 'Q4 budget planning session'
        }
    ]
    
    calendar_events.extend(demo_events)
    return calendar_events

def _find_user_calendar_file(user_email: str) -> Optional[Path]:
    """Find the most recent calendar file for the user"""
    calendar_dir = project_root / "data" / "raw" / "calendar"
    if not calendar_dir.exists():
        return None
        
    # Get the most recent date directory
    date_dirs = [d for d in calendar_dir.iterdir() if d.is_dir()]
    if not date_dirs:
        return None
        
    latest_dir = max(date_dirs, key=lambda x: x.name)
    
    # Look for user's calendar file
    # File format: employee_{email_with_underscores}.jsonl
    safe_email = user_email.replace('@', '_at_').replace('.', '_')
    user_calendar_file = latest_dir / f"employee_{safe_email}.jsonl"
    
    if user_calendar_file.exists():
        return user_calendar_file
        
    return None

def _load_user_calendar_file(calendar_file: Path, user: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Load and personalize calendar events from user's file"""
    from src.personalization.calendar_filter import CalendarPersonalizer
    
    calendar_events = []
    
    try:
        with open(calendar_file, 'r') as f:
            for line in f:
                event_data = json.loads(line.strip())
                
                # Convert to dashboard format
                calendar_events.append({
                    'id': event_data.get('event_id', f"cal_{len(calendar_events)}"),
                    'title': event_data.get('summary', 'Meeting'),
                    'start': event_data.get('start_datetime', datetime.now().isoformat()),
                    'end': event_data.get('end_datetime', (datetime.now() + timedelta(hours=1)).isoformat()),
                    'attendees': event_data.get('attendees', []),
                    'organizer': event_data.get('organizer', {}),
                    'location': event_data.get('location', ''),
                    'description': event_data.get('description', ''),
                    'calendar': event_data.get('calendar', '')
                })
                
    except Exception as e:
        print(f"Error loading user calendar file {calendar_file}: {e}")
        return []
    
    # Apply personalization to filter and enhance user events
    if calendar_events:
        personalizer = CalendarPersonalizer()
        user_events = personalizer.filter_user_events(calendar_events, user)
        
        # Format for user-centric display
        display_events = personalizer.format_user_calendar_display(user_events)
        print(f"🎯 Filtered to {len(user_events)} user-relevant events")
        
        return user_events
        
    return calendar_events

def generate_priorities_from_calendar(calendar_events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Generate realistic priorities based on calendar events"""
    priorities = []
    
    # Generate priorities from meeting subjects
    priority_templates = [
        ("Review", "pending"),
        ("Follow up on", "pending"), 
        ("Complete", "partial"),
        ("Prepare for", "pending"),
        ("Send", "done"),
        ("Update", "pending"),
        ("Schedule", "pending")
    ]
    
    for event in calendar_events[:10]:  # Use first 10 events
        title = event['title']
        
        # Generate 1-2 priorities per event
        for i in range(random.randint(1, 2)):
            action, status = random.choice(priority_templates)
            priority = {
                'id': f"priority_{len(priorities)}",
                'title': f"{action} {title.lower()}",
                'status': status,
                'urgency': random.choice(['high', 'medium', 'low']),
                'due_date': event['start'],
                'related_event': event['id']
            }
            priorities.append(priority)
    
    # Add some standalone priorities
    standalone_priorities = [
        {'title': 'Q4 Planning Doc', 'status': 'done', 'urgency': 'high'},
        {'title': 'Budget Review', 'status': 'pending', 'urgency': 'high'},
        {'title': 'Hire Approval', 'status': 'partial', 'urgency': 'medium'},
        {'title': 'API v2 Spec', 'status': 'pending', 'urgency': 'medium'},
        {'title': 'Team Offsite Planning', 'status': 'pending', 'urgency': 'low'},
        {'title': 'Performance Reviews', 'status': 'partial', 'urgency': 'medium'},
        {'title': 'Customer Feedback Analysis', 'status': 'pending', 'urgency': 'high'}
    ]
    
    for i, priority in enumerate(standalone_priorities):
        priority.update({
            'id': f"priority_{len(priorities) + i}",
            'due_date': (datetime.now() + timedelta(days=random.randint(1, 14))).isoformat()
        })
    
    priorities.extend(standalone_priorities)
    return priorities

def generate_commitments(calendar_events: List[Dict[str, Any]], priorities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Generate commitments from calendar and priorities"""
    commitments = []
    
    # Generate commitments I owe based on meetings
    owe_templates = [
        "Budget slides → CFO (Fri)",
        "Hire decision → HR (Today)", 
        "Product roadmap → Team (Mon)",
        "Meeting notes → Attendees (Today)",
        "Action items → Sarah (Wed)",
        "Status update → Board (Thu)",
        "Demo prep → Engineering (Fri)"
    ]
    
    for i, template in enumerate(owe_templates[:5]):  # Limit for demo
        commitments.append({
            'id': f"owe_{i}",
            'description': template,
            'direction': 'I_OWE',
            'status': 'pending',
            'due_date': (datetime.now() + timedelta(days=random.randint(0, 5))).isoformat(),
            'assignee': 'me'
        })
    
    # Generate commitments owed to me
    owed_templates = [
        "Sales forecast ← Sarah (noon)",
        "Tech spec ← Eng (Thu)", 
        "Market analysis ← PM (Fri)",
        "Budget approval ← Finance (Mon)",
        "Design mockups ← UX Team (Wed)",
        "Customer feedback ← Support (Today)",
        "Performance data ← Analytics (Fri)",
        "Legal review ← Legal Team (Mon)"
    ]
    
    for i, template in enumerate(owed_templates[:6]):  # Limit for demo
        commitments.append({
            'id': f"owed_{i}",
            'description': template,
            'direction': 'OWED_TO_ME',
            'status': 'pending',
            'due_date': (datetime.now() + timedelta(days=random.randint(0, 7))).isoformat(),
            'assignee': template.split('←')[1].split('(')[0].strip() if '←' in template else 'Unknown'
        })
    
    return commitments

def write_json_files(output_dir: Path, data: Dict[str, Any]) -> bool:
    """Write processed data to JSON files for Streamlit dashboard"""
    try:
        # Create output directory if it doesn't exist
        output_dir.mkdir(exist_ok=True)
        
        # Write calendar events
        calendar_file = output_dir / "calendar_events.json"
        with calendar_file.open('w', encoding='utf-8') as f:
            json.dump(data['calendar'], f, indent=2, ensure_ascii=False)
            
        # Write priorities data
        priorities_file = output_dir / "priorities.json"
        with priorities_file.open('w', encoding='utf-8') as f:
            json.dump(data['priorities'], f, indent=2, ensure_ascii=False)
            
        # Write commitments data
        commitments_file = output_dir / "commitments.json"
        with commitments_file.open('w', encoding='utf-8') as f:
            json.dump(data['commitments'], f, indent=2, ensure_ascii=False)
            
        print("✅ Successfully wrote all JSON files")
        return True
        
    except (OSError, json.JSONEncodeError) as e:
        print(f"❌ Failed to write JSON files: {e}")
        return False

def main():
    """Main function to load and process data"""
    parser = argparse.ArgumentParser(description="Load real data for Streamlit dashboard")
    parser.add_argument('--output-dir', default='data', 
                       help='Output directory for JSON files (default: data)')
    
    args = parser.parse_args()
    
    print("🔄 Loading real data for Streamlit dashboard...")
    
    # Load calendar events
    print("📅 Loading calendar events...")
    calendar_events = load_sample_calendar_data()
    print(f"   Loaded {len(calendar_events)} calendar events")
    
    # Generate priorities
    print("📋 Generating priorities from calendar...")
    priorities = generate_priorities_from_calendar(calendar_events)
    print(f"   Generated {len(priorities)} priorities")
    
    # Generate commitments
    print("📝 Generating commitments...")
    commitments = generate_commitments(calendar_events, priorities)
    i_owe = [c for c in commitments if c['direction'] == 'I_OWE']
    owed_to_me = [c for c in commitments if c['direction'] == 'OWED_TO_ME']
    print(f"   Generated {len(i_owe)} commitments I owe")
    print(f"   Generated {len(owed_to_me)} commitments owed to me")
    
    # Prepare data structure for JSON files
    data = {
        'calendar': calendar_events,
        'priorities': priorities,
        'commitments': commitments
    }
    
    # Write JSON files to output directory
    output_dir = Path(args.output_dir)
    print(f"📁 Writing JSON files to {output_dir}...")
    success = write_json_files(output_dir, data)
    
    if success:
        print("🎉 Dashboard data generated successfully!")
        print("\n📊 Summary:")
        print(f"   📅 Calendar Events: {len(calendar_events)}")
        print(f"   📋 Priorities: {len(priorities)}")
        print(f"   📝 Commitments I Owe: {len(i_owe)}")
        print(f"   📝 Commitments Owed to Me: {len(owed_to_me)}")
        print(f"\n📁 Files written:")
        print(f"   {output_dir / 'calendar_events.json'}")
        print(f"   {output_dir / 'priorities.json'}")
        print(f"   {output_dir / 'commitments.json'}")
        print(f"\n🔗 Run: streamlit run app.py")
        return 0
    else:
        print("❌ Failed to write data files")
        return 1

if __name__ == "__main__":
    sys.exit(main())