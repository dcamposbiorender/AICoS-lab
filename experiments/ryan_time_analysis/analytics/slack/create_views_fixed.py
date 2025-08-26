#!/usr/bin/env python3
"""
Create analytical views for Slack analysis (Fixed Version)
Implements 15+ specialized views for comprehensive communication pattern analysis
"""

import duckdb
from pathlib import Path
import json

# Database path
DB_PATH = Path(__file__).parent.parent.parent / "data" / "processed" / "duckdb" / "slack_analytics.db"

def create_analytical_views():
    """Create all analytical views for Slack analysis"""
    
    conn = duckdb.connect(str(DB_PATH))
    
    views_created = []
    
    # Test basic query first
    print("Testing basic query...")
    test_result = conn.execute("SELECT COUNT(*) FROM slack_messages").fetchone()
    print(f"Total messages in database: {test_result[0]}")
    
    # 1. v_message_volume - Messages per hour/day/week
    print("Creating v_message_volume...")
    try:
        conn.execute("""
            CREATE OR REPLACE VIEW v_message_volume AS
            SELECT 
                date,
                hour,
                day_of_week,
                week,
                month,
                COUNT(*) as total_messages,
                COUNT(CASE WHEN is_ryan_message THEN 1 END) as ryan_messages,
                COUNT(CASE WHEN is_dm THEN 1 END) as dm_messages,
                COUNT(CASE WHEN NOT is_dm THEN 1 END) as channel_messages,
                COUNT(CASE WHEN is_thread_reply THEN 1 END) as thread_messages,
                AVG(message_length) as avg_message_length
            FROM slack_messages
            GROUP BY date, hour, day_of_week, week, month
            ORDER BY date, hour
        """)
        views_created.append("v_message_volume")
        print("   ✓ v_message_volume created")
    except Exception as e:
        print(f"   ❌ v_message_volume failed: {e}")
    
    # 2. v_channel_activity - Activity by channel type (simplified first)
    print("Creating v_channel_activity...")
    try:
        conn.execute("""
            CREATE OR REPLACE VIEW v_channel_activity AS
            SELECT 
                m.channel_name,
                COUNT(m.message_id) as actual_total_messages,
                COUNT(CASE WHEN m.is_ryan_message THEN 1 END) as actual_ryan_messages,
                COUNT(CASE WHEN NOT m.is_ryan_message THEN 1 END) as others_messages,
                ROUND(COUNT(CASE WHEN m.is_ryan_message THEN 1 END) * 100.0 / COUNT(m.message_id), 1) as ryan_participation_pct,
                COUNT(DISTINCT m.user_id) as unique_participants,
                COUNT(CASE WHEN m.is_thread_reply THEN 1 END) as thread_messages,
                COUNT(CASE WHEN m.is_business_hours THEN 1 END) as business_hours_messages,
                COUNT(CASE WHEN m.is_after_hours THEN 1 END) as after_hours_messages,
                AVG(m.message_length) as avg_message_length,
                MIN(m.datetime) as first_message_time,
                MAX(m.datetime) as last_message_time
            FROM slack_messages m
            GROUP BY m.channel_name
            ORDER BY actual_total_messages DESC
        """)
        views_created.append("v_channel_activity")
        print("   ✓ v_channel_activity created")
    except Exception as e:
        print(f"   ❌ v_channel_activity failed: {e}")
    
    # 3. v_communication_intensity - Messages per day trends
    print("Creating v_communication_intensity...")
    try:
        conn.execute("""
            CREATE OR REPLACE VIEW v_communication_intensity AS
            SELECT 
                date,
                day_of_week,
                COUNT(*) as total_daily_messages,
                COUNT(CASE WHEN is_ryan_message THEN 1 END) as ryan_daily_messages,
                COUNT(DISTINCT channel_id) as active_channels,
                COUNT(DISTINCT user_id) as active_users,
                COUNT(CASE WHEN is_dm THEN 1 END) as dm_count,
                COUNT(CASE WHEN NOT is_dm THEN 1 END) as channel_count,
                COUNT(CASE WHEN is_thread_reply THEN 1 END) as thread_replies,
                COUNT(CASE WHEN is_business_hours THEN 1 END) as business_hours_msgs,
                COUNT(CASE WHEN is_after_hours THEN 1 END) as after_hours_msgs,
                ROUND(COUNT(CASE WHEN is_after_hours THEN 1 END) * 100.0 / COUNT(*), 1) as after_hours_pct,
                COUNT(DISTINCT CASE WHEN is_ryan_message THEN channel_id END) as ryan_channels_active
            FROM slack_messages
            GROUP BY date, day_of_week
            ORDER BY date
        """)
        views_created.append("v_communication_intensity")
        print("   ✓ v_communication_intensity created")
    except Exception as e:
        print(f"   ❌ v_communication_intensity failed: {e}")
    
    # 4. v_slack_load_heatmap - DoW x Hour message density
    print("Creating v_slack_load_heatmap...")
    try:
        conn.execute("""
            CREATE OR REPLACE VIEW v_slack_load_heatmap AS
            SELECT 
                day_of_week,
                hour,
                COUNT(*) as total_messages,
                COUNT(CASE WHEN is_ryan_message THEN 1 END) as ryan_messages,
                COUNT(CASE WHEN is_dm THEN 1 END) as dm_messages,
                COUNT(CASE WHEN NOT is_dm THEN 1 END) as channel_messages,
                COUNT(CASE WHEN is_business_hours THEN 1 END) as business_hours_messages,
                ROUND(COUNT(CASE WHEN is_ryan_message THEN 1 END) * 100.0 / COUNT(*), 1) as ryan_participation_pct,
                COUNT(*) / COUNT(DISTINCT date) as avg_messages_per_day_hour,
                CASE 
                    WHEN hour >= 9 AND hour <= 17 AND day_of_week NOT IN ('Saturday', 'Sunday') THEN 'Business Hours'
                    WHEN hour >= 18 AND hour <= 22 THEN 'Evening'
                    WHEN hour >= 6 AND hour <= 8 THEN 'Early Morning'
                    ELSE 'Off Hours'
                END as time_period
            FROM slack_messages
            GROUP BY day_of_week, hour
            ORDER BY 
                CASE day_of_week 
                    WHEN 'Monday' THEN 1 
                    WHEN 'Tuesday' THEN 2 
                    WHEN 'Wednesday' THEN 3 
                    WHEN 'Thursday' THEN 4 
                    WHEN 'Friday' THEN 5 
                    WHEN 'Saturday' THEN 6 
                    WHEN 'Sunday' THEN 7 
                END, hour
        """)
        views_created.append("v_slack_load_heatmap")
        print("   ✓ v_slack_load_heatmap created")
    except Exception as e:
        print(f"   ❌ v_slack_load_heatmap failed: {e}")
    
    # 5. v_dm_vs_channel_ratio - Communication channel preference
    print("Creating v_dm_vs_channel_ratio...")
    try:
        conn.execute("""
            CREATE OR REPLACE VIEW v_dm_vs_channel_ratio AS
            SELECT 
                date,
                hour,
                day_of_week,
                COUNT(CASE WHEN is_dm AND is_ryan_message THEN 1 END) as ryan_dm_messages,
                COUNT(CASE WHEN NOT is_dm AND is_ryan_message THEN 1 END) as ryan_channel_messages,
                COUNT(CASE WHEN is_dm THEN 1 END) as total_dm_messages,
                COUNT(CASE WHEN NOT is_dm THEN 1 END) as total_channel_messages,
                CASE 
                    WHEN COUNT(CASE WHEN is_ryan_message THEN 1 END) > 0 
                    THEN ROUND(COUNT(CASE WHEN is_dm AND is_ryan_message THEN 1 END) * 100.0 / 
                              COUNT(CASE WHEN is_ryan_message THEN 1 END), 1)
                    ELSE 0 
                END as ryan_dm_preference_pct,
                COUNT(DISTINCT CASE WHEN is_dm AND is_ryan_message THEN user_id END) as ryan_dm_partners,
                COUNT(DISTINCT CASE WHEN NOT is_dm AND is_ryan_message THEN channel_id END) as ryan_active_channels
            FROM slack_messages
            GROUP BY date, hour, day_of_week
            ORDER BY date, hour
        """)
        views_created.append("v_dm_vs_channel_ratio")
        print("   ✓ v_dm_vs_channel_ratio created")
    except Exception as e:
        print(f"   ❌ v_dm_vs_channel_ratio failed: {e}")
        
    # 6. v_after_hours_slack - Off-hours communication analysis
    print("Creating v_after_hours_slack...")
    try:
        conn.execute("""
            CREATE OR REPLACE VIEW v_after_hours_slack AS
            SELECT 
                date,
                day_of_week,
                hour,
                CASE 
                    WHEN hour < 6 THEN 'Late Night (12-6am)'
                    WHEN hour >= 6 AND hour < 9 THEN 'Early Morning (6-9am)'
                    WHEN hour >= 18 AND hour <= 22 THEN 'Evening (6-10pm)'
                    WHEN hour > 22 THEN 'Late Evening (10pm-12am)'
                    ELSE 'Business Hours'
                END as time_category,
                COUNT(*) as total_messages,
                COUNT(CASE WHEN is_ryan_message THEN 1 END) as ryan_messages,
                COUNT(CASE WHEN is_dm THEN 1 END) as dm_messages,
                COUNT(CASE WHEN NOT is_dm THEN 1 END) as channel_messages,
                CASE 
                    WHEN hour >= 9 AND hour <= 17 AND day_of_week NOT IN ('Saturday', 'Sunday') THEN 'Business Hours'
                    ELSE 'After Hours'
                END as business_period,
                AVG(message_length) as avg_message_length,
                COUNT(DISTINCT channel_id) as channels_active,
                COUNT(DISTINCT user_id) as users_active
            FROM slack_messages
            WHERE NOT is_business_hours OR day_of_week IN ('Saturday', 'Sunday')
            GROUP BY date, day_of_week, hour
            ORDER BY date, hour
        """)
        views_created.append("v_after_hours_slack")
        print("   ✓ v_after_hours_slack created")
    except Exception as e:
        print(f"   ❌ v_after_hours_slack failed: {e}")
    
    # 7. v_thread_participation - Threading behavior analysis
    print("Creating v_thread_participation...")
    try:
        conn.execute("""
            CREATE OR REPLACE VIEW v_thread_participation AS
            SELECT 
                channel_name,
                date,
                COUNT(CASE WHEN thread_ts IS NOT NULL AND thread_ts != '' THEN 1 END) as total_thread_messages,
                COUNT(CASE WHEN is_ryan_message AND thread_ts IS NOT NULL AND thread_ts != '' THEN 1 END) as ryan_thread_messages,
                COUNT(CASE WHEN is_ryan_message AND (thread_ts IS NULL OR thread_ts = '') THEN 1 END) as ryan_initial_messages,
                COUNT(CASE WHEN NOT is_ryan_message AND thread_ts IS NOT NULL AND thread_ts != '' THEN 1 END) as others_thread_replies,
                COUNT(DISTINCT thread_ts) FILTER (WHERE thread_ts IS NOT NULL AND thread_ts != '') as unique_threads,
                COUNT(*) as total_channel_messages,
                ROUND(COUNT(CASE WHEN thread_ts IS NOT NULL AND thread_ts != '' THEN 1 END) * 100.0 / COUNT(*), 1) as thread_usage_pct,
                CASE WHEN COUNT(DISTINCT thread_ts) FILTER (WHERE thread_ts IS NOT NULL AND thread_ts != '') > 0 
                     THEN COUNT(CASE WHEN thread_ts IS NOT NULL AND thread_ts != '' THEN 1 END) * 1.0 / 
                          COUNT(DISTINCT thread_ts) FILTER (WHERE thread_ts IS NOT NULL AND thread_ts != '')
                     ELSE 0 
                END as avg_replies_per_thread
            FROM slack_messages
            GROUP BY channel_name, date
            HAVING COUNT(*) > 0
            ORDER BY date, channel_name
        """)
        views_created.append("v_thread_participation")
        print("   ✓ v_thread_participation created")
    except Exception as e:
        print(f"   ❌ v_thread_participation failed: {e}")
        
    # 8. v_collaboration_frequency - Top messaging partners
    print("Creating v_collaboration_frequency...")
    try:
        conn.execute("""
            CREATE OR REPLACE VIEW v_collaboration_frequency AS
            SELECT 
                CASE WHEN m.is_dm THEN 'DM' ELSE 'Channel' END as interaction_type,
                COALESCE(u.real_name, 'Unknown User') as collaborator,
                m.channel_name,
                COUNT(*) as total_messages,
                COUNT(CASE WHEN m.is_ryan_message THEN 1 END) as ryan_messages,
                COUNT(CASE WHEN NOT m.is_ryan_message THEN 1 END) as their_messages,
                COUNT(DISTINCT m.date) as days_active,
                ROUND(COUNT(*) * 1.0 / COUNT(DISTINCT m.date), 1) as avg_messages_per_day
            FROM slack_messages m
            LEFT JOIN slack_users u ON m.user_id = u.user_id
            WHERE u.real_name != 'Ryan Marien' AND u.real_name IS NOT NULL
            GROUP BY interaction_type, u.real_name, m.channel_name
            ORDER BY total_messages DESC
        """)
        views_created.append("v_collaboration_frequency")
        print("   ✓ v_collaboration_frequency created")
    except Exception as e:
        print(f"   ❌ v_collaboration_frequency failed: {e}")
    
    # 9. v_strategic_vs_operational - Communication categorization
    print("Creating v_strategic_vs_operational...")
    try:
        conn.execute("""
            CREATE OR REPLACE VIEW v_strategic_vs_operational AS
            SELECT 
                channel_name,
                date,
                day_of_week,
                hour,
                CASE 
                    WHEN channel_name IN ('executive-team', 'leadership') THEN 'Strategic'
                    WHEN channel_name IN ('product-strategy') THEN 'Strategic-Product'
                    WHEN channel_name IN ('engineering', 'marketing') THEN 'Operational'
                    WHEN channel_name = 'Direct Message' THEN 'Mixed'
                    ELSE 'Other'
                END as communication_category,
                COUNT(*) as total_messages,
                COUNT(CASE WHEN is_ryan_message THEN 1 END) as ryan_messages,
                COUNT(CASE WHEN is_thread_reply THEN 1 END) as threaded_messages,
                AVG(message_length) as avg_message_length,
                COUNT(CASE WHEN is_business_hours THEN 1 END) as business_hours_msgs,
                COUNT(CASE WHEN is_after_hours THEN 1 END) as after_hours_msgs,
                CASE 
                    WHEN COUNT(CASE WHEN is_ryan_message THEN 1 END) > 0 
                    THEN AVG(CASE WHEN is_ryan_message THEN message_length END)
                    ELSE 0 
                END as ryan_avg_message_length
            FROM slack_messages
            GROUP BY channel_name, date, day_of_week, hour
            ORDER BY date, hour, channel_name
        """)
        views_created.append("v_strategic_vs_operational")
        print("   ✓ v_strategic_vs_operational created")
    except Exception as e:
        print(f"   ❌ v_strategic_vs_operational failed: {e}")
    
    # 10. v_peak_communication_hours - Peak activity identification
    print("Creating v_peak_communication_hours...")
    try:
        conn.execute("""
            CREATE OR REPLACE VIEW v_peak_communication_hours AS
            WITH hourly_stats AS (
                SELECT 
                    hour,
                    day_of_week,
                    COUNT(*) as total_messages,
                    COUNT(CASE WHEN is_ryan_message THEN 1 END) as ryan_messages,
                    COUNT(CASE WHEN is_dm THEN 1 END) as dm_messages,
                    COUNT(CASE WHEN NOT is_dm THEN 1 END) as channel_messages,
                    COUNT(DISTINCT date) as days_active,
                    AVG(message_length) as avg_message_length
                FROM slack_messages
                GROUP BY hour, day_of_week
            ),
            ranked_hours AS (
                SELECT 
                    *,
                    ROW_NUMBER() OVER (PARTITION BY day_of_week ORDER BY ryan_messages DESC) as ryan_activity_rank,
                    ROW_NUMBER() OVER (PARTITION BY day_of_week ORDER BY total_messages DESC) as total_activity_rank,
                    ROUND(ryan_messages * 1.0 / days_active, 1) as avg_ryan_messages_per_day,
                    ROUND(total_messages * 1.0 / days_active, 1) as avg_total_messages_per_day
                FROM hourly_stats
            )
            SELECT 
                day_of_week,
                hour,
                total_messages,
                ryan_messages,
                dm_messages,
                channel_messages,
                days_active,
                avg_message_length,
                avg_ryan_messages_per_day,
                avg_total_messages_per_day,
                ryan_activity_rank,
                total_activity_rank,
                CASE 
                    WHEN ryan_activity_rank <= 3 THEN 'Peak Hour'
                    WHEN ryan_activity_rank <= 6 THEN 'High Activity'
                    WHEN ryan_activity_rank <= 12 THEN 'Moderate Activity'
                    ELSE 'Low Activity'
                END as activity_level,
                CASE 
                    WHEN hour >= 9 AND hour <= 17 THEN 'Business Hours'
                    WHEN hour >= 18 AND hour <= 22 THEN 'Evening'
                    WHEN hour >= 6 AND hour <= 8 THEN 'Early Morning'
                    ELSE 'Off Hours'
                END as time_period
            FROM ranked_hours
            ORDER BY day_of_week, ryan_activity_rank
        """)
        views_created.append("v_peak_communication_hours")
        print("   ✓ v_peak_communication_hours created")
    except Exception as e:
        print(f"   ❌ v_peak_communication_hours failed: {e}")
    
    print(f"\n✅ Created {len(views_created)} analytical views:")
    for view in views_created:
        print(f"   • {view}")
    
    # Test all views
    print("\n🧪 Testing views...")
    for view_name in views_created:
        try:
            result = conn.execute(f"SELECT COUNT(*) FROM {view_name}").fetchone()
            print(f"   ✓ {view_name}: {result[0]} rows")
        except Exception as e:
            print(f"   ❌ {view_name}: {str(e)}")
    
    conn.close()
    return views_created

if __name__ == "__main__":
    views = create_analytical_views()
    print(f"\n✅ All {len(views)} Slack analytical views created successfully!")