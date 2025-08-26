#!/usr/bin/env python3
"""
Setup DuckDB for Slack Analytics
Loads Slack CSV data and creates base tables for analysis
"""

import duckdb
import pandas as pd
from pathlib import Path
import json
from datetime import datetime

# Define paths
BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / "data" / "processed"
DB_PATH = BASE_DIR / "data" / "processed" / "duckdb" / "slack_analytics.db"

def setup_slack_database():
    """Initialize DuckDB database for Slack analytics"""
    
    # Ensure database directory exists
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    # Connect to DuckDB
    conn = duckdb.connect(str(DB_PATH))
    
    print(f"Setting up DuckDB at: {DB_PATH}")
    
    # Load Slack messages
    messages_path = DATA_DIR / "slack_messages.csv"
    print(f"Loading messages from: {messages_path}")
    
    conn.execute(f"""
        CREATE OR REPLACE TABLE slack_messages AS 
        SELECT * FROM read_csv_auto('{messages_path}')
    """)
    
    # Load Slack channels
    channels_path = DATA_DIR / "slack_channels.csv"
    print(f"Loading channels from: {channels_path}")
    
    conn.execute(f"""
        CREATE OR REPLACE TABLE slack_channels AS 
        SELECT * FROM read_csv_auto('{channels_path}')
    """)
    
    # Load Slack users
    users_path = DATA_DIR / "slack_users.csv"
    print(f"Loading users from: {users_path}")
    
    conn.execute(f"""
        CREATE OR REPLACE TABLE slack_users AS 
        SELECT * FROM read_csv_auto('{users_path}')
    """)
    
    # Add computed columns for analysis
    conn.execute("""
        ALTER TABLE slack_messages ADD COLUMN IF NOT EXISTS is_ryan_message BOOLEAN;
        ALTER TABLE slack_messages ADD COLUMN IF NOT EXISTS is_dm BOOLEAN;
        ALTER TABLE slack_messages ADD COLUMN IF NOT EXISTS is_business_hours BOOLEAN;
        ALTER TABLE slack_messages ADD COLUMN IF NOT EXISTS is_after_hours BOOLEAN;
        ALTER TABLE slack_messages ADD COLUMN IF NOT EXISTS is_thread_reply BOOLEAN;
        ALTER TABLE slack_messages ADD COLUMN IF NOT EXISTS message_length INTEGER;
    """)
    
    # Update computed columns
    conn.execute("""
        UPDATE slack_messages SET 
            is_ryan_message = (user_id = 'UBL74SKU0'),
            is_dm = (channel_name = 'Direct Message'),
            is_business_hours = (hour >= 9 AND hour <= 17 AND day_of_week NOT IN ('Saturday', 'Sunday')),
            is_after_hours = NOT (hour >= 9 AND hour <= 17 AND day_of_week NOT IN ('Saturday', 'Sunday')),
            is_thread_reply = (thread_ts IS NOT NULL AND thread_ts != ''),
            message_length = LENGTH(text)
    """)
    
    # Create indexes for performance
    conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_user_id ON slack_messages(user_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_channel_id ON slack_messages(channel_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON slack_messages(timestamp)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_datetime ON slack_messages(datetime)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_is_ryan ON slack_messages(is_ryan_message)")
    
    # Validate data loading
    message_count = conn.execute("SELECT COUNT(*) FROM slack_messages").fetchone()[0]
    channel_count = conn.execute("SELECT COUNT(*) FROM slack_channels").fetchone()[0] 
    user_count = conn.execute("SELECT COUNT(*) FROM slack_users").fetchone()[0]
    
    ryan_message_count = conn.execute("""
        SELECT COUNT(*) FROM slack_messages WHERE is_ryan_message = true
    """).fetchone()[0]
    
    print(f"\n=== Database Setup Complete ===")
    print(f"Total messages: {message_count:,}")
    print(f"Ryan's messages: {ryan_message_count:,}")
    print(f"Channels: {channel_count}")
    print(f"Users: {user_count}")
    
    # Generate basic stats for verification
    stats = {}
    
    # Messages by channel type
    channel_stats = conn.execute("""
        SELECT 
            channel_name,
            COUNT(*) as message_count,
            COUNT(CASE WHEN is_ryan_message THEN 1 END) as ryan_messages
        FROM slack_messages 
        GROUP BY channel_name 
        ORDER BY message_count DESC
    """).fetchall()
    
    stats['channel_distribution'] = [
        {
            'channel': row[0],
            'total_messages': row[1], 
            'ryan_messages': row[2]
        }
        for row in channel_stats
    ]
    
    # Business hours vs after hours
    hours_stats = conn.execute("""
        SELECT 
            is_business_hours,
            COUNT(*) as message_count,
            COUNT(CASE WHEN is_ryan_message THEN 1 END) as ryan_messages
        FROM slack_messages 
        GROUP BY is_business_hours
    """).fetchall()
    
    stats['business_hours_split'] = [
        {
            'period': 'Business Hours' if row[0] else 'After Hours',
            'total_messages': row[1],
            'ryan_messages': row[2]
        }
        for row in hours_stats
    ]
    
    # Most active days
    daily_stats = conn.execute("""
        SELECT 
            day_of_week,
            COUNT(*) as message_count,
            COUNT(CASE WHEN is_ryan_message THEN 1 END) as ryan_messages
        FROM slack_messages 
        GROUP BY day_of_week 
        ORDER BY message_count DESC
    """).fetchall()
    
    stats['daily_activity'] = [
        {
            'day': row[0],
            'total_messages': row[1],
            'ryan_messages': row[2]
        }
        for row in daily_stats
    ]
    
    # Save setup summary
    summary = {
        'setup_timestamp': datetime.now().isoformat(),
        'database_path': str(DB_PATH),
        'total_messages': message_count,
        'ryan_messages': ryan_message_count,
        'channels': channel_count,
        'users': user_count,
        'ryan_message_percentage': round(ryan_message_count / message_count * 100, 1),
        'statistics': stats
    }
    
    summary_path = Path(__file__).parent / "slack_setup_summary.json"
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"Setup summary saved to: {summary_path}")
    print(f"Ryan's message percentage: {summary['ryan_message_percentage']}%")
    
    conn.close()
    return summary

if __name__ == "__main__":
    summary = setup_slack_database()
    print("\n✅ Slack database setup complete!")