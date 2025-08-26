#!/usr/bin/env python3
"""
Slack DM Extraction Script for Workstream Analysis

Extracts direct messages and group conversations involving david.campos@biorender.com
from the Slack archive to analyze communication patterns related to workstreams.

Key Features:
- Extracts DMs and group messages involving the target user
- Identifies conversation partners and frequency
- Maps conversations to key workstream stakeholders
- Exports structured data for workstream analysis

Usage:
    python extract_slack_dms.py
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Set, Any
from collections import defaultdict, Counter

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Target email for analysis
TARGET_EMAIL = "david.campos@biorender.com"

# Key stakeholders by workstream from the user's plan
WORKSTREAM_STAKEHOLDERS = {
    "gtm_efficiency": [
        "charlie@biorender.com",      # Pipeline Council organizer
        "ryan.gerstein@biorender.com", # Pipeline Council attendee
        "stefan@biorender.com",       # Pipeline Council attendee
        "michael.litwin@biorender.com", # Pipeline Council attendee
        "francesca@biorender.com",    # Pipeline Council attendee
        "lucas@biorender.com",        # Pipeline Council attendee
        "walid@biorender.com",        # Pipeline Council attendee
        "paige.anderson@biorender.com", # Pipeline Council attendee
        "livia.guo@biorender.com",    # Pipeline Council attendee
        "matthew.smith@biorender.com", # Pipeline Council attendee
        "chris.hemberger@biorender.com" # Pipeline Council attendee
    ],
    "data_platform": [
        "adam.shapiro@biorender.com"   # Data Platform lead
    ],
    "icp_expansion": [
        "michael.edmonson@biorender.com", # Exec team - likely involved in ICP decisions
    ],
    "ai_transformation": [
        "katya@biorender.com",        # AI governance
        "jon.fan@biorender.com"       # AI governance (assuming Jon = jon.fan)
    ],
    "ai_bizops_team": [
        "meghana.reddy@biorender.com" # AI BizOps hiring lead
    ],
    "executive": [
        "philip@biorender.com",       # Exec team
        "katya@biorender.com",        # Exec team
        "meghana.reddy@biorender.com", # Exec team
        "michael.edmonson@biorender.com", # Exec team
        "omri@biorender.com",         # Exec team (assuming from context)
        "shiz@biorender.com",         # Exec team
        "natalie@biorender.com"       # Exec team organizer
    ]
}

def load_roster(base_path: Path) -> Dict[str, Dict[str, Any]]:
    """Load employee roster to map between Slack IDs and emails"""
    roster_path = base_path / "data" / "processed" / "roster.json"
    
    try:
        with open(roster_path, 'r') as f:
            roster_data = json.load(f)
            return roster_data.get("roster_data", {}).get("employees", {})
    except FileNotFoundError:
        print(f"Warning: Roster file not found at {roster_path}")
        return {}

def find_slack_archive(base_path: Path) -> Optional[Path]:
    """Find the most recent Slack archive"""
    archive_paths = [
        base_path / "data" / "archive" / "slack" / "2025-08-16" / "data.jsonl",
        base_path / "data" / "raw" / "slack",
    ]
    
    for path in archive_paths:
        if path.exists():
            if path.is_file():
                return path
            else:
                # Look for JSONL files in directory
                jsonl_files = list(path.glob("**/*.jsonl"))
                if jsonl_files:
                    return jsonl_files[0]  # Return first found
    
    return None

def extract_user_conversations(archive_path: Path, roster: Dict[str, Any], target_email: str) -> Dict[str, Any]:
    """Extract conversations involving the target user"""
    
    # Find target user's Slack ID
    target_slack_id = None
    target_user_data = roster.get(target_email, {})
    if target_user_data:
        target_slack_id = target_user_data.get("slack_id")
    
    if not target_slack_id:
        print(f"Warning: Could not find Slack ID for {target_email}")
        return {}
    
    print(f"Analyzing conversations for {target_email} (Slack ID: {target_slack_id})")
    
    # Statistics
    total_messages = 0
    target_messages = 0
    conversations = defaultdict(list)
    conversation_partners = Counter()
    channel_activity = defaultdict(int)
    
    # Process messages (JSONL format - one JSON object per line)
    with open(archive_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f):
            try:
                line = line.strip()
                if not line:
                    continue
                    
                message = json.loads(line)
                total_messages += 1
                
                # Skip if not involving target user
                user_id = message.get('user')
                channel_id = message.get('channel')
                
                # Check if target user is involved (as sender or in mentions)
                is_target_involved = (
                    user_id == target_slack_id or
                    target_slack_id in message.get('text', '').replace('<@', '').replace('>', '')
                )
                
                if not is_target_involved:
                    continue
                
                target_messages += 1
                
                # Extract conversation info
                conversation_key = f"{channel_id}_{user_id}"
                message_data = {
                    'timestamp': message.get('ts'),
                    'user': user_id,
                    'channel': channel_id,
                    'text': message.get('text', ''),
                    'message_type': message.get('type', 'message'),
                    'thread_ts': message.get('thread_ts'),
                    'reactions': message.get('reactions', [])
                }
                
                conversations[channel_id].append(message_data)
                
                # Track conversation partners
                if user_id != target_slack_id:
                    conversation_partners[user_id] += 1
                
                # Track channel activity
                channel_activity[channel_id] += 1
                
            except json.JSONDecodeError as e:
                print(f"Warning: Could not parse line {line_num + 1}: {e}")
                continue
    
    return {
        'statistics': {
            'total_messages_processed': total_messages,
            'target_user_messages': target_messages,
            'unique_conversations': len(conversations),
            'unique_partners': len(conversation_partners),
            'extraction_timestamp': datetime.now().isoformat()
        },
        'conversations': dict(conversations),
        'conversation_partners': dict(conversation_partners),
        'channel_activity': dict(channel_activity),
        'target_user': {
            'email': target_email,
            'slack_id': target_slack_id
        }
    }

def map_conversations_to_workstreams(conversations: Dict[str, Any], roster: Dict[str, Any]) -> Dict[str, Any]:
    """Map conversations to workstreams based on participants"""
    
    # Create reverse mapping from Slack ID to email
    slack_to_email = {}
    for email, user_data in roster.items():
        slack_id = user_data.get('slack_id')
        if slack_id:
            slack_to_email[slack_id] = email
    
    workstream_activity = defaultdict(lambda: {
        'conversations': 0,
        'messages': 0,
        'participants': set(),
        'channels': set()
    })
    
    # Process each conversation
    for channel_id, messages in conversations['conversations'].items():
        channel_participants = set()
        
        # Get all participants in this channel
        for message in messages:
            user_id = message.get('user')
            if user_id:
                email = slack_to_email.get(user_id)
                if email:
                    channel_participants.add(email)
        
        # Map to workstreams based on participants
        for workstream, stakeholders in WORKSTREAM_STAKEHOLDERS.items():
            stakeholder_overlap = channel_participants.intersection(set(stakeholders))
            
            if stakeholder_overlap:
                workstream_activity[workstream]['conversations'] += 1
                workstream_activity[workstream]['messages'] += len(messages)
                workstream_activity[workstream]['participants'].update(stakeholder_overlap)
                workstream_activity[workstream]['channels'].add(channel_id)
    
    # Convert sets to lists for JSON serialization
    for workstream_data in workstream_activity.values():
        workstream_data['participants'] = list(workstream_data['participants'])
        workstream_data['channels'] = list(workstream_data['channels'])
    
    return dict(workstream_activity)

def main():
    """Main execution function"""
    print("Starting Slack DM extraction for workstream analysis...")
    
    # Setup paths
    base_path = Path(__file__).parent.parent.parent.parent
    output_path = Path(__file__).parent.parent / "data_extraction"
    
    # Load roster
    print("Loading employee roster...")
    roster = load_roster(base_path)
    print(f"Loaded {len(roster)} employees")
    
    # Find Slack archive
    print("Finding Slack archive...")
    archive_path = find_slack_archive(base_path)
    
    if not archive_path:
        print("ERROR: Could not find Slack archive")
        return
    
    print(f"Using archive: {archive_path}")
    
    # Extract conversations
    print(f"Extracting conversations for {TARGET_EMAIL}...")
    conversations = extract_user_conversations(archive_path, roster, TARGET_EMAIL)
    
    if not conversations:
        print("ERROR: No conversations extracted")
        return
    
    # Map to workstreams
    print("Mapping conversations to workstreams...")
    workstream_mapping = map_conversations_to_workstreams(conversations, roster)
    
    # Save results
    output_file = output_path / "slack_dms_analysis.json"
    output_data = {
        'analysis_metadata': {
            'target_user': TARGET_EMAIL,
            'archive_path': str(archive_path),
            'analysis_timestamp': datetime.now().isoformat()
        },
        'conversations': conversations,
        'workstream_mapping': workstream_mapping
    }
    
    output_path.mkdir(exist_ok=True)
    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)
    
    # Print summary
    print(f"\n=== EXTRACTION SUMMARY ===")
    print(f"Total messages processed: {conversations['statistics']['total_messages_processed']:,}")
    print(f"Messages involving target user: {conversations['statistics']['target_user_messages']:,}")
    print(f"Unique conversations: {conversations['statistics']['unique_conversations']}")
    print(f"Unique conversation partners: {conversations['statistics']['unique_partners']}")
    
    print(f"\n=== WORKSTREAM ACTIVITY ===")
    for workstream, data in workstream_mapping.items():
        print(f"{workstream}: {data['conversations']} conversations, {data['messages']} messages")
        print(f"  Key participants: {', '.join(data['participants'][:5])}")
    
    print(f"\nResults saved to: {output_file}")

if __name__ == "__main__":
    main()