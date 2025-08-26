#!/usr/bin/env python3
"""
Normalize Ryan's Slack Data for Analytics
Transform raw Slack data into structured tables for DuckDB analysis

Creates normalized tables:
- slack_messages: All messages with standard schema
- slack_channels: Channel information 
- slack_users: User information
"""

import json
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Dict, List

def normalize_slack_data():
    """Transform raw Slack data into normalized tables"""
    
    # Define paths
    base_path = Path(__file__).parent.parent
    raw_path = base_path / "data" / "raw" / "slack"
    processed_path = base_path / "data" / "processed"
    processed_path.mkdir(parents=True, exist_ok=True)
    
    print(f"🔄 NORMALIZING RYAN'S SLACK DATA")
    print(f"📂 Source: {raw_path}")
    print(f"📂 Output: {processed_path}")
    
    # Load raw data
    try:
        # Load collection summary
        with open(raw_path / "collection_summary.json") as f:
            summary = json.load(f)
        
        # Load users data
        with open(raw_path / "users.json") as f:
            users_data = json.load(f)
        
        # Load Ryan activity data
        with open(raw_path / "ryan_activity.json") as f:
            ryan_data = json.load(f)
        
        print(f"✅ Loaded raw data files")
        
    except Exception as e:
        print(f"❌ Failed to load raw data: {e}")
        return False
    
    # 1. Create normalized slack_users table
    users_df = create_users_table(users_data)
    users_file = processed_path / "slack_users.csv"
    users_df.to_csv(users_file, index=False)
    print(f"💾 Created slack_users table: {len(users_df)} users → {users_file}")
    
    # 2. Create normalized slack_channels table  
    channels_df = create_channels_table(ryan_data["ryan_data"])
    channels_file = processed_path / "slack_channels.csv"
    channels_df.to_csv(channels_file, index=False)
    print(f"💾 Created slack_channels table: {len(channels_df)} channels → {channels_file}")
    
    # 3. Create normalized slack_messages table
    messages_df = create_messages_table(ryan_data["ryan_data"], summary["date_range"])
    messages_file = processed_path / "slack_messages.csv"
    messages_df.to_csv(messages_file, index=False)
    print(f"💾 Created slack_messages table: {len(messages_df)} messages → {messages_file}")
    
    # 4. Create data summary
    create_data_summary(users_df, channels_df, messages_df, summary, processed_path)
    
    print(f"\n🎉 SLACK DATA NORMALIZATION COMPLETE!")
    print(f"📊 Ready for DuckDB analysis")
    
    return True


def create_users_table(users_data: Dict) -> pd.DataFrame:
    """Create normalized slack_users table"""
    
    users_list = []
    for user_id, user_info in users_data.items():
        users_list.append({
            "user_id": user_id,
            "username": user_info.get("name", ""),
            "real_name": user_info.get("real_name", ""),
            "display_name": user_info.get("display_name", ""),
            "email": user_info.get("email", ""),
            "is_admin": user_info.get("is_admin", False),
            "is_owner": user_info.get("is_owner", False), 
            "is_primary_owner": user_info.get("is_primary_owner", False),
            "timezone": user_info.get("timezone", "")
        })
    
    return pd.DataFrame(users_list)


def create_channels_table(ryan_data: Dict) -> pd.DataFrame:
    """Create normalized slack_channels table"""
    
    channels_list = []
    for channel_id, channel_data in ryan_data.items():
        channel_info = channel_data.get("channel_info", {})
        
        channels_list.append({
            "channel_id": channel_id,
            "channel_name": channel_data.get("channel_name", ""),
            "ryan_messages_count": channel_data.get("ryan_messages", 0),
            "ryan_mentions_count": channel_data.get("ryan_mentions", 0),
            "ryan_threads_count": channel_data.get("ryan_threads", 0),
            "collection_timestamp": channel_info.get("collection_timestamp", ""),
            "rolling_window_hours": channel_info.get("rolling_window_hours", 0)
        })
    
    return pd.DataFrame(channels_list)


def create_messages_table(ryan_data: Dict, date_range: Dict) -> pd.DataFrame:
    """Create normalized slack_messages table"""
    
    messages_list = []
    
    for channel_id, channel_data in ryan_data.items():
        channel_name = channel_data.get("channel_name", "")
        
        # Process Ryan's own messages
        for message in channel_data.get("messages", []):
            normalized_msg = normalize_message(message, channel_id, channel_name, "ryan_message")
            if normalized_msg:
                messages_list.append(normalized_msg)
        
        # Process messages mentioning Ryan
        for message in channel_data.get("mentions", []):
            normalized_msg = normalize_message(message, channel_id, channel_name, "ryan_mention")
            if normalized_msg:
                messages_list.append(normalized_msg)
        
        # Process thread messages
        for thread in channel_data.get("threads", []):
            thread_ts = thread.get("thread_ts", "")
            
            # Ryan's messages in threads
            for message in thread.get("ryan_messages", []):
                normalized_msg = normalize_message(
                    message, channel_id, channel_name, "ryan_thread_message", thread_ts
                )
                if normalized_msg:
                    messages_list.append(normalized_msg)
            
            # Mentions in threads
            for message in thread.get("mentions", []):
                normalized_msg = normalize_message(
                    message, channel_id, channel_name, "ryan_thread_mention", thread_ts
                )
                if normalized_msg:
                    messages_list.append(normalized_msg)
    
    df = pd.DataFrame(messages_list)
    
    # Filter to date range and add date columns for analysis
    if not df.empty:
        # Convert timestamp to datetime
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='s')
        
        # Filter to target date range
        start_date = pd.to_datetime(date_range["start"])
        end_date = pd.to_datetime(date_range["end"]) + pd.Timedelta(days=1)  # Include end date
        
        df = df[(df['datetime'] >= start_date) & (df['datetime'] < end_date)]
        
        # Add date analysis columns
        df['date'] = df['datetime'].dt.date
        df['hour'] = df['datetime'].dt.hour
        df['day_of_week'] = df['datetime'].dt.day_name()
        df['week'] = df['datetime'].dt.isocalendar().week
        df['month'] = df['datetime'].dt.to_period('M').astype(str)
        
        # Sort by timestamp
        df = df.sort_values('timestamp')
    
    return df


def normalize_message(message: Dict, channel_id: str, channel_name: str, 
                     message_type: str, thread_ts: str = None) -> Dict:
    """Normalize a single message to standard schema"""
    
    try:
        # Extract timestamp
        ts = message.get('ts', '0')
        timestamp = float(ts)
        
        # Extract basic message info
        normalized = {
            "message_id": message.get('client_msg_id', ts),  # Use timestamp as fallback ID
            "user_id": message.get('user', ''),
            "channel_id": channel_id,
            "channel_name": channel_name,
            "timestamp": timestamp,
            "text": message.get('text', ''),
            "message_type": message_type,
            "thread_ts": thread_ts or message.get('thread_ts', ''),
            "reply_count": message.get('reply_count', 0),
            "reply_users_count": message.get('reply_users_count', 0),
            "latest_reply": message.get('latest_reply', ''),
            "subtype": message.get('subtype', ''),
            "bot_id": message.get('bot_id', ''),
            "app_id": message.get('app_id', ''),
            "edited": bool(message.get('edited')),
            "has_reactions": bool(message.get('reactions')),
            "reaction_count": len(message.get('reactions', [])),
            "has_files": bool(message.get('files')),
            "file_count": len(message.get('files', []))
        }
        
        return normalized
        
    except Exception as e:
        print(f"⚠️ Failed to normalize message: {e}")
        return None


def create_data_summary(users_df: pd.DataFrame, channels_df: pd.DataFrame, 
                       messages_df: pd.DataFrame, collection_summary: Dict, 
                       output_path: Path):
    """Create comprehensive data summary for the normalized data"""
    
    # Calculate summary statistics
    summary = {
        "normalization_timestamp": datetime.now().isoformat(),
        "original_collection": collection_summary,
        "normalized_data": {
            "users": {
                "total_users": len(users_df),
                "ryan_user_id": "UBL74SKU0",
                "admins": int(users_df['is_admin'].sum()),
                "owners": int(users_df['is_owner'].sum())
            },
            "channels": {
                "total_channels": len(channels_df),
                "channels_with_ryan_messages": int((channels_df['ryan_messages_count'] > 0).sum()),
                "channels_with_ryan_mentions": int((channels_df['ryan_mentions_count'] > 0).sum()),
                "total_ryan_messages": int(channels_df['ryan_messages_count'].sum()),
                "total_ryan_mentions": int(channels_df['ryan_mentions_count'].sum())
            },
            "messages": {
                "total_messages": len(messages_df),
                "ryan_own_messages": len(messages_df[messages_df['message_type'].str.contains('ryan_message')]),
                "ryan_mentions": len(messages_df[messages_df['message_type'].str.contains('mention')]),
                "thread_messages": len(messages_df[messages_df['message_type'].str.contains('thread')]),
                "date_range_coverage": {
                    "start": str(messages_df['date'].min()) if not messages_df.empty else None,
                    "end": str(messages_df['date'].max()) if not messages_df.empty else None,
                    "total_days": int((messages_df['date'].max() - messages_df['date'].min()).days) if not messages_df.empty else 0
                }
            }
        }
    }
    
    # Add time-based analysis if messages exist
    if not messages_df.empty:
        summary["normalized_data"]["temporal_analysis"] = {
            "messages_by_month": messages_df.groupby('month').size().to_dict(),
            "messages_by_day_of_week": messages_df.groupby('day_of_week').size().to_dict(),
            "messages_by_hour": messages_df.groupby('hour').size().to_dict(),
            "busiest_day": str(messages_df.groupby('date').size().idxmax()),
            "average_messages_per_day": round(len(messages_df) / len(messages_df['date'].unique()), 2)
        }
    
    # Save summary
    summary_file = output_path / "normalization_summary.json"
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"📊 Data Summary:")
    print(f"  Users: {summary['normalized_data']['users']['total_users']}")
    print(f"  Channels: {summary['normalized_data']['channels']['total_channels']} ({summary['normalized_data']['channels']['channels_with_ryan_messages']} with Ryan messages)")
    print(f"  Messages: {summary['normalized_data']['messages']['total_messages']} ({summary['normalized_data']['messages']['ryan_own_messages']} by Ryan)")
    print(f"💾 Summary saved: {summary_file}")


if __name__ == "__main__":
    success = normalize_slack_data()
    if not success:
        exit(1)
    print(f"✅ Normalization complete - data ready for DuckDB analysis!")