#!/usr/bin/env python3
"""
Create Ryan Slack Demo Schema and Sample Data
Since we don't have historical data from Aug 2024 - Feb 2025,
this creates the normalized schema with sample data to demonstrate
the structure and analysis capabilities.
"""

import json
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import random

def create_slack_demo_schema():
    """Create demo normalized Slack tables with sample Ryan data"""
    
    # Define paths
    base_path = Path(__file__).parent.parent
    processed_path = base_path / "data" / "processed"
    processed_path.mkdir(parents=True, exist_ok=True)
    
    print(f"🎯 CREATING SLACK DEMO SCHEMA FOR RYAN ANALYSIS")
    print(f"📂 Output: {processed_path}")
    
    # Create demo users table
    users_df = create_demo_users_table()
    users_file = processed_path / "slack_users.csv"
    users_df.to_csv(users_file, index=False)
    print(f"💾 Created slack_users table: {len(users_df)} users → {users_file}")
    
    # Create demo channels table
    channels_df = create_demo_channels_table()
    channels_file = processed_path / "slack_channels.csv"
    channels_df.to_csv(channels_file, index=False)
    print(f"💾 Created slack_channels table: {len(channels_df)} channels → {channels_file}")
    
    # Create demo messages table (with realistic patterns for Ryan)
    messages_df = create_demo_messages_table()
    messages_file = processed_path / "slack_messages.csv"
    messages_df.to_csv(messages_file, index=False)
    print(f"💾 Created slack_messages table: {len(messages_df)} messages → {messages_file}")
    
    # Create schema documentation
    create_schema_documentation(processed_path)
    
    # Create data summary
    create_demo_summary(users_df, channels_df, messages_df, processed_path)
    
    print(f"\n🎉 SLACK DEMO SCHEMA COMPLETE!")
    print(f"📊 Ready for DuckDB analysis and time pattern identification")
    
    return True


def create_demo_users_table() -> pd.DataFrame:
    """Create demo users table with key BioRender team members"""
    
    users_data = [
        {
            "user_id": "UBL74SKU0",
            "username": "ryan",
            "real_name": "Ryan Marien",
            "display_name": "Ryan",
            "email": "ryan@biorender.com",
            "is_admin": True,
            "is_owner": True,
            "is_primary_owner": False,
            "timezone": "America/New_York"
        },
        {
            "user_id": "UASL5BT1V",
            "username": "shiz",
            "real_name": "Shiz Aoki",
            "display_name": "Shiz",
            "email": "shiz@biorender.com",
            "is_admin": True,
            "is_owner": True,
            "is_primary_owner": True,
            "timezone": "America/New_York"
        },
        {
            "user_id": "UAKLL5BPT",
            "username": "katya",
            "real_name": "Katya Shteyn",
            "display_name": "katya",
            "email": "katya@biorender.com",
            "is_admin": True,
            "is_owner": True,
            "is_primary_owner": False,
            "timezone": "America/Los_Angeles"
        },
        {
            "user_id": "UE3J27A9Z",
            "username": "rodney",
            "real_name": "Rodney Draaisma",
            "display_name": "rodney",
            "email": "rodney@biorender.com",
            "is_admin": False,
            "is_owner": False,
            "is_primary_owner": False,
            "timezone": "America/New_York"
        }
    ]
    
    # Add some additional team members for realistic analysis
    for i in range(5, 25):
        users_data.append({
            "user_id": f"U{i:08X}",
            "username": f"user{i}",
            "real_name": f"Team Member {i}",
            "display_name": f"member{i}",
            "email": f"team{i}@biorender.com",
            "is_admin": False,
            "is_owner": False,
            "is_primary_owner": False,
            "timezone": "America/New_York"
        })
    
    return pd.DataFrame(users_data)


def create_demo_channels_table() -> pd.DataFrame:
    """Create demo channels table with realistic BioRender channels"""
    
    channels_data = [
        {
            "channel_id": "C123EXEC",
            "channel_name": "executive-team",
            "ryan_messages_count": 145,
            "ryan_mentions_count": 67,
            "ryan_threads_count": 23,
            "collection_timestamp": "2025-08-19T20:30:00",
            "rolling_window_hours": 4368  # 6 months
        },
        {
            "channel_id": "C123LEAD",
            "channel_name": "leadership",
            "ryan_messages_count": 198,
            "ryan_mentions_count": 89,
            "ryan_threads_count": 34,
            "collection_timestamp": "2025-08-19T20:30:00",
            "rolling_window_hours": 4368
        },
        {
            "channel_id": "C123PROD",
            "channel_name": "product-strategy",
            "ryan_messages_count": 76,
            "ryan_mentions_count": 45,
            "ryan_threads_count": 12,
            "collection_timestamp": "2025-08-19T20:30:00",
            "rolling_window_hours": 4368
        },
        {
            "channel_id": "C123ENGG",
            "channel_name": "engineering",
            "ryan_messages_count": 23,
            "ryan_mentions_count": 78,
            "ryan_threads_count": 5,
            "collection_timestamp": "2025-08-19T20:30:00",
            "rolling_window_hours": 4368
        },
        {
            "channel_id": "DM_RYAN_SHIZ",
            "channel_name": "Direct Message",
            "ryan_messages_count": 234,
            "ryan_mentions_count": 0,
            "ryan_threads_count": 8,
            "collection_timestamp": "2025-08-19T20:30:00",
            "rolling_window_hours": 4368
        },
        {
            "channel_id": "C123MKTA",
            "channel_name": "marketing",
            "ryan_messages_count": 12,
            "ryan_mentions_count": 34,
            "ryan_threads_count": 2,
            "collection_timestamp": "2025-08-19T20:30:00",
            "rolling_window_hours": 4368
        }
    ]
    
    return pd.DataFrame(channels_data)


def create_demo_messages_table() -> pd.DataFrame:
    """Create demo messages table with realistic Ryan activity patterns"""
    
    messages = []
    
    # Define date range: August 2024 - February 2025
    start_date = datetime(2024, 8, 20)
    end_date = datetime(2025, 2, 7)
    
    # Define Ryan's typical communication patterns
    ryan_channels = [
        ("C123EXEC", "executive-team", 0.8),  # High activity
        ("C123LEAD", "leadership", 0.7),     # High activity  
        ("DM_RYAN_SHIZ", "Direct Message", 0.9),  # Very high activity
        ("C123PROD", "product-strategy", 0.4),  # Medium activity
        ("C123ENGG", "engineering", 0.1),    # Low activity (mentions mostly)
        ("C123MKTA", "marketing", 0.05)      # Very low activity
    ]
    
    # Generate messages across the 6-month period
    current_date = start_date
    message_id_counter = 1
    
    while current_date <= end_date:
        # Skip weekends for most business communication
        if current_date.weekday() < 5:  # Monday = 0, Friday = 4
            
            # Generate messages for each channel based on activity level
            for channel_id, channel_name, activity_level in ryan_channels:
                
                # Determine number of messages for this day
                base_messages = int(activity_level * 5)  # Base messages per day
                daily_messages = random.randint(max(1, base_messages-2), base_messages+3)
                
                for _ in range(daily_messages):
                    # Generate realistic timestamps during business hours
                    hour = random.choices(
                        range(24), 
                        weights=[0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1,  # 0-7
                                0.3, 1.0, 1.5, 2.0, 1.8, 1.2,              # 8-13  
                                1.8, 2.2, 2.0, 1.5, 0.8, 0.4,              # 14-19
                                0.2, 0.1, 0.1, 0.1]                        # 20-23
                    )[0]
                    minute = random.randint(0, 59)
                    second = random.randint(0, 59)
                    
                    msg_datetime = current_date.replace(hour=hour, minute=minute, second=second)
                    timestamp = msg_datetime.timestamp()
                    
                    # Determine if Ryan is sending or being mentioned
                    is_ryan_message = random.random() < activity_level
                    
                    if is_ryan_message:
                        user_id = "UBL74SKU0"  # Ryan
                        message_type = "ryan_message"
                    else:
                        # Someone else mentioning Ryan
                        other_users = ["UASL5BT1V", "UAKLL5BPT", "UE3J27A9Z"] + [f"U{i:08X}" for i in range(5, 10)]
                        user_id = random.choice(other_users)
                        message_type = "ryan_mention"
                    
                    # Create message entry
                    message = {
                        "message_id": f"msg_{message_id_counter:06d}",
                        "user_id": user_id,
                        "channel_id": channel_id,
                        "channel_name": channel_name,
                        "timestamp": timestamp,
                        "text": generate_sample_message_text(message_type, channel_name),
                        "message_type": message_type,
                        "thread_ts": "",  # Most messages aren't threads for simplicity
                        "reply_count": random.choice([0, 0, 0, 1, 2]) if is_ryan_message else 0,
                        "reply_users_count": 0,
                        "latest_reply": "",
                        "subtype": "",
                        "bot_id": "",
                        "app_id": "",
                        "edited": random.choice([True, False]) if random.random() < 0.1 else False,
                        "has_reactions": random.choice([True, False]) if random.random() < 0.3 else False,
                        "reaction_count": random.choice([0, 1, 2, 3]) if random.random() < 0.3 else 0,
                        "has_files": random.choice([True, False]) if random.random() < 0.05 else False,
                        "file_count": random.choice([0, 1]) if random.random() < 0.05 else 0,
                        "datetime": msg_datetime.isoformat(),
                        "date": msg_datetime.date().isoformat(),
                        "hour": hour,
                        "day_of_week": msg_datetime.strftime("%A"),
                        "week": msg_datetime.isocalendar()[1],
                        "month": msg_datetime.strftime("%Y-%m")
                    }
                    
                    messages.append(message)
                    message_id_counter += 1
        
        current_date += timedelta(days=1)
    
    # Create DataFrame and sort by timestamp
    df = pd.DataFrame(messages)
    df = df.sort_values('timestamp').reset_index(drop=True)
    
    return df


def generate_sample_message_text(message_type: str, channel_name: str) -> str:
    """Generate realistic sample message text"""
    
    if message_type == "ryan_message":
        if channel_name == "executive-team":
            templates = [
                "Updated roadmap priorities for Q1 - focus on enterprise features",
                "Team sync went well - shipping the new workflow next week",
                "Can we review the customer feedback before Friday's board meeting?",
                "Great progress on the integration project. Thanks team!",
                "Need to discuss budget allocations for the new initiatives"
            ]
        elif channel_name == "leadership":
            templates = [
                "Strategy review complete - let's align on next steps",
                "Customer interview insights attached. Key takeaways in thread.",
                "Quarterly planning session scheduled for next Tuesday",
                "Market analysis looks promising for our new features",
                "Team performance reviews are due end of week"
            ]
        elif channel_name == "Direct Message":
            templates = [
                "Can you review the proposal before the meeting?",
                "Great work on the presentation yesterday",
                "Quick sync at 2pm to discuss the roadmap?",
                "The customer call went really well - they're interested",
                "Draft agenda for tomorrow's leadership meeting attached"
            ]
        else:
            templates = [
                "Thanks for the update on this",
                "Let's schedule time to discuss this further",
                "Great insights - this aligns with our strategy",
                "Can we get metrics on this initiative?",
                "Approved - please proceed with implementation"
            ]
    else:  # ryan_mention
        templates = [
            "@ryan what are your thoughts on this approach?",
            "Ryan mentioned this in yesterday's leadership meeting",
            "@ryan can you review when you have a moment?",
            "As Ryan suggested, we should prioritize the customer feedback",
            "@ryan this relates to our Q1 OKRs discussion"
        ]
    
    return random.choice(templates)


def create_schema_documentation(output_path: Path):
    """Create documentation explaining the Slack schema"""
    
    schema_doc = {
        "slack_schema_documentation": {
            "created": datetime.now().isoformat(),
            "purpose": "Normalized Slack data for Ryan Marien time analysis (Aug 2024 - Feb 2025)",
            "tables": {
                "slack_users": {
                    "description": "All workspace users with profile information",
                    "key_fields": {
                        "user_id": "Unique Slack user identifier",
                        "username": "Slack username",
                        "real_name": "Full name",
                        "email": "Email address",
                        "is_admin": "Administrative privileges",
                        "timezone": "User timezone"
                    },
                    "analysis_use": "Identify team roles, map communications to individuals"
                },
                "slack_channels": {
                    "description": "Channels with Ryan activity summary",
                    "key_fields": {
                        "channel_id": "Unique channel identifier", 
                        "channel_name": "Channel name",
                        "ryan_messages_count": "Messages sent by Ryan",
                        "ryan_mentions_count": "Messages mentioning Ryan",
                        "ryan_threads_count": "Thread conversations involving Ryan"
                    },
                    "analysis_use": "Identify Ryan's communication patterns by context/team"
                },
                "slack_messages": {
                    "description": "All messages sent by or mentioning Ryan",
                    "key_fields": {
                        "message_id": "Unique message identifier",
                        "user_id": "Message sender",
                        "channel_id": "Channel where message was sent",
                        "timestamp": "Unix timestamp",
                        "datetime": "Parsed datetime",
                        "message_type": "ryan_message | ryan_mention | ryan_thread_*",
                        "hour": "Hour of day (0-23)",
                        "day_of_week": "Day name",
                        "month": "YYYY-MM format"
                    },
                    "analysis_use": "Time pattern analysis, communication volume trends, context analysis"
                }
            },
            "analysis_patterns": {
                "communication_volume": "Messages by hour/day to identify peak activity times",
                "channel_focus": "Which channels Ryan engages with most",
                "collaboration_patterns": "Who Ryan communicates with most frequently",
                "response_patterns": "Thread participation and response timing",
                "context_switching": "Movement between different communication contexts",
                "meeting_correlation": "Compare Slack activity with calendar data"
            }
        }
    }
    
    doc_file = output_path / "slack_schema_documentation.json"
    with open(doc_file, 'w') as f:
        json.dump(schema_doc, f, indent=2)
    
    print(f"📚 Schema documentation: {doc_file}")


def create_demo_summary(users_df: pd.DataFrame, channels_df: pd.DataFrame, 
                       messages_df: pd.DataFrame, output_path: Path):
    """Create comprehensive summary of the demo data"""
    
    # Calculate temporal patterns
    temporal_analysis = {}
    if not messages_df.empty:
        temporal_analysis = {
            "messages_by_month": messages_df.groupby('month').size().to_dict(),
            "messages_by_day_of_week": messages_df.groupby('day_of_week').size().to_dict(),
            "messages_by_hour": messages_df.groupby('hour').size().to_dict(),
            "peak_communication_hour": int(messages_df.groupby('hour').size().idxmax()),
            "average_messages_per_day": round(len(messages_df) / len(messages_df['date'].unique()), 2)
        }
        
        # Ryan's own vs mentions
        ryan_own = len(messages_df[messages_df['message_type'] == 'ryan_message'])
        ryan_mentions = len(messages_df[messages_df['message_type'] == 'ryan_mention'])
        
        temporal_analysis["ryan_communication_split"] = {
            "ryan_own_messages": ryan_own,
            "messages_mentioning_ryan": ryan_mentions,
            "ryan_to_mentions_ratio": round(ryan_own / max(ryan_mentions, 1), 2)
        }
    
    summary = {
        "demo_data_summary": {
            "created": datetime.now().isoformat(),
            "target_user": "Ryan Marien (ryan@biorender.com)",
            "date_range": "2024-08-20 to 2025-02-07 (6 months)",
            "data_tables": {
                "users": len(users_df),
                "channels": len(channels_df),
                "messages": len(messages_df)
            },
            "slack_activity_overview": {
                "channels_with_ryan_activity": len(channels_df[channels_df['ryan_messages_count'] > 0]),
                "total_ryan_messages": int(channels_df['ryan_messages_count'].sum()),
                "total_ryan_mentions": int(channels_df['ryan_mentions_count'].sum()),
                "most_active_channel": channels_df.loc[channels_df['ryan_messages_count'].idxmax(), 'channel_name'] if not channels_df.empty else None
            },
            "temporal_patterns": temporal_analysis,
            "analysis_ready": {
                "duckdb_compatible": True,
                "time_series_analysis": True,
                "correlation_with_calendar": True,
                "executive_pattern_identification": True
            }
        }
    }
    
    summary_file = output_path / "slack_demo_summary.json"
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"📊 Demo Data Summary:")
    print(f"  Total Messages: {len(messages_df)}")
    print(f"  Date Range: {messages_df['date'].min()} to {messages_df['date'].max()}")
    print(f"  Channels: {len(channels_df)} ({len(channels_df[channels_df['ryan_messages_count'] > 0])} with Ryan activity)")
    print(f"  Peak Hour: {temporal_analysis.get('peak_communication_hour', 'N/A')}")
    print(f"  Avg Messages/Day: {temporal_analysis.get('average_messages_per_day', 'N/A')}")
    print(f"💾 Summary saved: {summary_file}")


if __name__ == "__main__":
    success = create_slack_demo_schema()
    if not success:
        exit(1)
    print(f"✅ Demo schema creation complete - ready for DuckDB analysis!")