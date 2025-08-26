#!/usr/bin/env python3
"""
Unified Analytics Setup for Cross-Platform Correlation Analysis
Sub-Agent 4: Integrated Calendar & Slack Analysis

This script establishes the unified correlation framework by:
1. Loading both calendar and Slack DuckDB databases
2. Creating temporal alignment views
3. Setting up cross-platform analytical infrastructure
"""

import duckdb
import pandas as pd
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

class UnifiedAnalyticsSetup:
    def __init__(self, base_path="/Users/david.campos/VibeCode/AICoS-Lab/experiments/ryan_time_analysis"):
        self.base_path = Path(base_path)
        self.calendar_db_path = self.base_path / "data/processed/duckdb/calendar_analytics.db"
        self.slack_db_path = self.base_path / "data/processed/duckdb/slack_analytics.db"
        self.integrated_db_path = self.base_path / "analytics/integrated/unified_analytics.db"
        
        # Initialize connection
        self.conn = duckdb.connect(str(self.integrated_db_path))
        
        print(f"🔧 Setting up Unified Analytics Framework")
        print(f"📅 Calendar DB: {self.calendar_db_path}")
        print(f"💬 Slack DB: {self.slack_db_path}")
        print(f"🔗 Integrated DB: {self.integrated_db_path}")
    
    def attach_databases(self):
        """Attach both source databases to the integrated database."""
        print("\n📎 Attaching source databases...")
        
        try:
            # Attach calendar database
            self.conn.execute(f"ATTACH '{self.calendar_db_path}' AS calendar_db")
            print("✅ Calendar database attached")
            
            # Attach slack database  
            self.conn.execute(f"ATTACH '{self.slack_db_path}' AS slack_db")
            print("✅ Slack database attached")
            
            # List available tables from both databases
            calendar_tables = self.conn.execute("SELECT table_name FROM calendar_db.information_schema.tables WHERE table_schema = 'main'").fetchall()
            slack_tables = self.conn.execute("SELECT table_name FROM slack_db.information_schema.tables WHERE table_schema = 'main'").fetchall()
            
            print(f"📅 Calendar tables available: {[t[0] for t in calendar_tables]}")
            print(f"💬 Slack tables available: {[t[0] for t in slack_tables]}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error attaching databases: {e}")
            return False
    
    def create_temporal_alignment_views(self):
        """Create temporal alignment views for cross-platform correlation."""
        print("\n⏰ Creating temporal alignment views...")
        
        # Base temporal alignment view
        temporal_alignment_query = """
        CREATE OR REPLACE VIEW v_temporal_alignment AS
        WITH calendar_hourly AS (
            SELECT 
                DATE_TRUNC('hour', start_time) as hour_timestamp,
                COUNT(*) as meeting_count,
                SUM(duration_minutes) as total_meeting_minutes,
                COUNT(CASE WHEN duration_minutes >= 120 THEN 1 END) as deep_work_blocks,
                COUNT(CASE WHEN attendee_count >= 5 THEN 1 END) as large_meetings
            FROM calendar_db.events 
            WHERE start_time IS NOT NULL
            GROUP BY DATE_TRUNC('hour', start_time)
        ),
        slack_hourly AS (
            SELECT 
                DATE_TRUNC('hour', datetime) as hour_timestamp,
                COUNT(*) as message_count,
                COUNT(DISTINCT channel_id) as active_channels,
                COUNT(DISTINCT user_id) as active_users,
                AVG(message_length) as avg_message_length,
                COUNT(CASE WHEN is_dm = true THEN 1 END) as dm_count
            FROM slack_db.slack_messages 
            WHERE datetime IS NOT NULL
                AND is_ryan_message = true
            GROUP BY DATE_TRUNC('hour', datetime)
        )
        SELECT 
            COALESCE(c.hour_timestamp, s.hour_timestamp) as hour_timestamp,
            EXTRACT('year' FROM COALESCE(c.hour_timestamp, s.hour_timestamp)) as year,
            EXTRACT('month' FROM COALESCE(c.hour_timestamp, s.hour_timestamp)) as month,
            EXTRACT('day' FROM COALESCE(c.hour_timestamp, s.hour_timestamp)) as day,
            EXTRACT('hour' FROM COALESCE(c.hour_timestamp, s.hour_timestamp)) as hour,
            EXTRACT('dow' FROM COALESCE(c.hour_timestamp, s.hour_timestamp)) as day_of_week,
            
            -- Calendar metrics
            COALESCE(c.meeting_count, 0) as meeting_count,
            COALESCE(c.total_meeting_minutes, 0) as meeting_minutes,
            COALESCE(c.deep_work_blocks, 0) as deep_work_blocks,
            COALESCE(c.large_meetings, 0) as large_meetings,
            
            -- Slack metrics
            COALESCE(s.message_count, 0) as message_count,
            COALESCE(s.active_channels, 0) as active_channels,
            COALESCE(s.active_users, 0) as active_users,
            COALESCE(s.avg_message_length, 0) as avg_message_length,
            COALESCE(s.dm_count, 0) as dm_count,
            
            -- Combined metrics
            (COALESCE(c.total_meeting_minutes, 0) + COALESCE(s.message_count, 0) * 2) as total_engagement_score,
            CASE 
                WHEN COALESCE(c.meeting_count, 0) > 0 AND COALESCE(s.message_count, 0) > 0 THEN 'high_activity'
                WHEN COALESCE(c.meeting_count, 0) > 0 OR COALESCE(s.message_count, 0) > 0 THEN 'moderate_activity'
                ELSE 'low_activity'
            END as activity_level
        FROM calendar_hourly c
        FULL OUTER JOIN slack_hourly s ON c.hour_timestamp = s.hour_timestamp
        ORDER BY hour_timestamp;
        """
        
        try:
            self.conn.execute(temporal_alignment_query)
            print("✅ Created v_temporal_alignment view")
            
            # Create daily alignment view
            daily_alignment_query = """
            CREATE OR REPLACE VIEW v_daily_alignment AS
            SELECT 
                DATE_TRUNC('day', hour_timestamp) as date,
                year, month, day, day_of_week,
                
                -- Aggregated calendar metrics
                SUM(meeting_count) as total_meetings,
                SUM(meeting_minutes) as total_meeting_minutes,
                SUM(deep_work_blocks) as total_deep_work_blocks,
                SUM(large_meetings) as total_large_meetings,
                
                -- Aggregated slack metrics  
                SUM(message_count) as total_messages,
                AVG(active_channels) as avg_active_channels,
                MAX(active_channels) as max_active_channels,
                AVG(avg_message_length) as avg_message_length,
                SUM(dm_count) as total_dm_count,
                
                -- Combined daily metrics
                SUM(total_engagement_score) as daily_engagement_score,
                
                -- Activity distribution
                COUNT(CASE WHEN activity_level = 'high_activity' THEN 1 END) as high_activity_hours,
                COUNT(CASE WHEN activity_level = 'moderate_activity' THEN 1 END) as moderate_activity_hours,
                COUNT(CASE WHEN activity_level = 'low_activity' THEN 1 END) as low_activity_hours,
                
                -- Working hours analysis (9 AM to 6 PM)
                SUM(CASE WHEN hour BETWEEN 9 AND 18 THEN meeting_minutes ELSE 0 END) as business_hours_meeting_minutes,
                SUM(CASE WHEN hour BETWEEN 9 AND 18 THEN message_count ELSE 0 END) as business_hours_messages,
                SUM(CASE WHEN hour NOT BETWEEN 9 AND 18 THEN meeting_minutes ELSE 0 END) as after_hours_meeting_minutes,
                SUM(CASE WHEN hour NOT BETWEEN 9 AND 18 THEN message_count ELSE 0 END) as after_hours_messages
            FROM v_temporal_alignment
            GROUP BY DATE_TRUNC('day', hour_timestamp), year, month, day, day_of_week
            ORDER BY date;
            """
            
            self.conn.execute(daily_alignment_query)
            print("✅ Created v_daily_alignment view")
            
            return True
            
        except Exception as e:
            print(f"❌ Error creating temporal alignment views: {e}")
            return False
    
    def validate_data_alignment(self):
        """Validate that both datasets have overlapping time periods."""
        print("\n🔍 Validating data alignment...")
        
        try:
            # Get date ranges from both sources
            calendar_range = self.conn.execute("""
                SELECT 
                    MIN(start_time) as min_date,
                    MAX(start_time) as max_date,
                    COUNT(*) as total_events
                FROM calendar_db.events
            """).fetchone()
            
            slack_range = self.conn.execute("""
                SELECT 
                    MIN(datetime) as min_date,
                    MAX(datetime) as max_date,
                    COUNT(*) as total_messages
                FROM slack_db.slack_messages
                WHERE is_ryan_message = true
            """).fetchone()
            
            print(f"📅 Calendar data: {calendar_range[2]} events from {calendar_range[0]} to {calendar_range[1]}")
            print(f"💬 Slack data: {slack_range[2]} messages from {slack_range[0]} to {slack_range[1]}")
            
            # Find overlap period
            overlap_query = """
            SELECT 
                COUNT(*) as overlapping_hours,
                MIN(hour_timestamp) as overlap_start,
                MAX(hour_timestamp) as overlap_end
            FROM v_temporal_alignment 
            WHERE meeting_count > 0 AND message_count > 0
            """
            
            overlap = self.conn.execute(overlap_query).fetchone()
            print(f"🔗 Overlapping activity: {overlap[0]} hours from {overlap[1]} to {overlap[2]}")
            
            # Sample the alignment view
            sample_query = """
            SELECT * FROM v_temporal_alignment 
            WHERE meeting_count > 0 OR message_count > 0 
            ORDER BY hour_timestamp 
            LIMIT 10
            """
            
            sample = self.conn.execute(sample_query).fetchdf()
            print(f"\n📊 Sample alignment data:")
            print(sample[['hour_timestamp', 'meeting_count', 'message_count', 'activity_level']].to_string())
            
            return True
            
        except Exception as e:
            print(f"❌ Error validating data alignment: {e}")
            return False
    
    def create_summary_statistics(self):
        """Create summary statistics for the integrated dataset."""
        print("\n📊 Creating summary statistics...")
        
        try:
            summary_stats = {}
            
            # Overall statistics
            overall_stats = self.conn.execute("""
                SELECT 
                    COUNT(*) as total_hours,
                    SUM(meeting_count) as total_meetings,
                    SUM(meeting_minutes) as total_meeting_minutes,
                    SUM(message_count) as total_messages,
                    COUNT(DISTINCT DATE_TRUNC('day', hour_timestamp)) as active_days,
                    AVG(total_engagement_score) as avg_engagement_score
                FROM v_temporal_alignment
                WHERE meeting_count > 0 OR message_count > 0
            """).fetchone()
            
            summary_stats['overall'] = {
                'total_hours': overall_stats[0],
                'total_meetings': overall_stats[1], 
                'total_meeting_minutes': overall_stats[2],
                'total_messages': overall_stats[3],
                'active_days': overall_stats[4],
                'avg_engagement_score': round(overall_stats[5], 2) if overall_stats[5] else 0
            }
            
            # Daily averages
            daily_stats = self.conn.execute("""
                SELECT 
                    AVG(total_meetings) as avg_daily_meetings,
                    AVG(total_meeting_minutes) as avg_daily_meeting_minutes, 
                    AVG(total_messages) as avg_daily_messages,
                    AVG(daily_engagement_score) as avg_daily_engagement
                FROM v_daily_alignment
            """).fetchone()
            
            summary_stats['daily_averages'] = {
                'meetings_per_day': round(daily_stats[0], 1),
                'meeting_minutes_per_day': round(daily_stats[1], 1),
                'messages_per_day': round(daily_stats[2], 1),
                'engagement_score_per_day': round(daily_stats[3], 1)
            }
            
            # Activity level distribution
            activity_dist = self.conn.execute("""
                SELECT 
                    activity_level,
                    COUNT(*) as hour_count,
                    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage
                FROM v_temporal_alignment
                WHERE meeting_count > 0 OR message_count > 0
                GROUP BY activity_level
                ORDER BY hour_count DESC
            """).fetchall()
            
            summary_stats['activity_distribution'] = {
                level[0]: {'hours': level[1], 'percentage': level[2]} 
                for level in activity_dist
            }
            
            # Save summary statistics
            summary_file = self.base_path / "analytics/integrated/summary_statistics.json"
            with open(summary_file, 'w') as f:
                json.dump(summary_stats, f, indent=2, default=str)
            
            print("✅ Summary statistics created and saved")
            print(f"📈 Total active hours: {summary_stats['overall']['total_hours']}")
            print(f"📅 Average meetings/day: {summary_stats['daily_averages']['meetings_per_day']}")
            print(f"💬 Average messages/day: {summary_stats['daily_averages']['messages_per_day']}")
            
            return summary_stats
            
        except Exception as e:
            print(f"❌ Error creating summary statistics: {e}")
            return None
    
    def run_setup(self):
        """Run the complete unified analytics setup."""
        print("🚀 Starting Unified Analytics Setup...")
        
        success_steps = []
        
        # Step 1: Attach databases
        if self.attach_databases():
            success_steps.append("Database attachment")
        
        # Step 2: Create temporal alignment views
        if self.create_temporal_alignment_views():
            success_steps.append("Temporal alignment views")
        
        # Step 3: Validate data alignment
        if self.validate_data_alignment():
            success_steps.append("Data alignment validation")
        
        # Step 4: Create summary statistics
        if self.create_summary_statistics():
            success_steps.append("Summary statistics")
        
        print(f"\n✅ Setup completed successfully!")
        print(f"📊 Completed steps: {', '.join(success_steps)}")
        print(f"🗄️ Integrated database created at: {self.integrated_db_path}")
        
        return len(success_steps) == 4

if __name__ == "__main__":
    setup = UnifiedAnalyticsSetup()
    setup.run_setup()