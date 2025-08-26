#!/usr/bin/env python3
"""
Create analytical views for Slack analysis
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
    
    # 1. v_message_volume - Messages per hour/day/week
    print("Creating v_message_volume...")
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
    
    # 2. v_response_patterns - Response time analysis
    print("Creating v_response_patterns...")
    conn.execute("""
        CREATE OR REPLACE VIEW v_response_patterns AS
        WITH message_sequences AS (
            SELECT 
                message_id,
                user_id,
                channel_id,
                channel_name,
                timestamp,
                datetime,
                is_ryan_message,
                LAG(timestamp) OVER (PARTITION BY channel_id ORDER BY timestamp) as prev_timestamp,
                LAG(user_id) OVER (PARTITION BY channel_id ORDER BY timestamp) as prev_user_id,
                LAG(is_ryan_message) OVER (PARTITION BY channel_id ORDER BY timestamp) as prev_was_ryan
            FROM slack_messages
            WHERE user_id = 'UBL74SKU0'  -- Ryan's responses only
        )
        SELECT 
            channel_name,
            date,
            hour,
            COUNT(*) as response_count,
            AVG(timestamp - prev_timestamp) / 60 as avg_response_time_minutes,
            MEDIAN(timestamp - prev_timestamp) / 60 as median_response_time_minutes,
            MIN(timestamp - prev_timestamp) / 60 as fastest_response_minutes,
            MAX(timestamp - prev_timestamp) / 60 as slowest_response_minutes,
            COUNT(CASE WHEN (timestamp - prev_timestamp) < 300 THEN 1 END) as quick_responses_5min,
            COUNT(CASE WHEN (timestamp - prev_timestamp) < 900 THEN 1 END) as quick_responses_15min,
            COUNT(CASE WHEN (timestamp - prev_timestamp) > 3600 THEN 1 END) as delayed_responses_1hr
        FROM message_sequences
        WHERE prev_user_id IS NOT NULL 
            AND prev_user_id != 'UBL74SKU0'  -- Only responses to others
        GROUP BY channel_name, date, hour
        ORDER BY date, hour
    """)
    views_created.append("v_response_patterns")
    
    # 3. v_channel_activity - Activity by channel type
    print("Creating v_channel_activity...")
    conn.execute("""
        CREATE OR REPLACE VIEW v_channel_activity AS
        SELECT 
            c.channel_name,
            c.ryan_messages_count as expected_ryan_messages,
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
        FROM slack_channels c
        JOIN slack_messages m ON c.channel_id = m.channel_id
        GROUP BY c.channel_name, c.ryan_messages_count
        ORDER BY actual_total_messages DESC
    """)
    views_created.append("v_channel_activity")
    
    # 4. v_communication_intensity - Messages per day trends
    print("Creating v_communication_intensity...")
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
            -- Context switching indicators
            COUNT(DISTINCT CASE WHEN is_ryan_message THEN channel_id END) as ryan_channels_active
        FROM slack_messages
        GROUP BY date, day_of_week
        ORDER BY date
    """)
    views_created.append("v_communication_intensity")
    
    # 5. v_slack_load_heatmap - DoW x Hour message density
    print("Creating v_slack_load_heatmap...")
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
            -- Intensity metrics
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
    
    # 6. v_thread_participation - Threading behavior analysis
    print("Creating v_thread_participation...")
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
            -- Thread engagement metrics
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
    
    # 7. v_dm_vs_channel_ratio - Communication channel preference
    print("Creating v_dm_vs_channel_ratio...")
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
            -- Communication style indicators
            COUNT(DISTINCT CASE WHEN is_dm AND is_ryan_message THEN user_id END) as ryan_dm_partners,
            COUNT(DISTINCT CASE WHEN NOT is_dm AND is_ryan_message THEN channel_id END) as ryan_active_channels
        FROM slack_messages
        GROUP BY date, hour, day_of_week
        ORDER BY date, hour
    """)
    views_created.append("v_dm_vs_channel_ratio")
    
    # 8. v_after_hours_slack - Off-hours communication analysis
    print("Creating v_after_hours_slack...")
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
            -- After-hours intensity
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
    
    # 9. v_slack_context_switching - Rapid channel changes
    print("Creating v_slack_context_switching...")
    conn.execute("""
        CREATE OR REPLACE VIEW v_slack_context_switching AS
        WITH ryan_sequence AS (
            SELECT 
                message_id,
                channel_id,
                channel_name,
                timestamp,
                datetime,
                date,
                hour,
                LAG(channel_id) OVER (ORDER BY timestamp) as prev_channel,
                LAG(timestamp) OVER (ORDER BY timestamp) as prev_timestamp,
                LAG(channel_name) OVER (ORDER BY timestamp) as prev_channel_name
            FROM slack_messages
            WHERE is_ryan_message = true
            ORDER BY timestamp
        )
        SELECT 
            date,
            hour,
            day_of_week,
            COUNT(*) as ryan_messages,
            COUNT(CASE WHEN channel_id != prev_channel THEN 1 END) as channel_switches,
            COUNT(DISTINCT channel_id) as channels_used,
            -- Context switching intensity
            CASE 
                WHEN COUNT(*) > 0 
                THEN ROUND(COUNT(CASE WHEN channel_id != prev_channel THEN 1 END) * 100.0 / COUNT(*), 1)
                ELSE 0 
            END as context_switch_rate_pct,
            -- Rapid switching (within 5 minutes)
            COUNT(CASE WHEN channel_id != prev_channel AND (timestamp - prev_timestamp) < 300 THEN 1 END) as rapid_switches_5min,
            AVG(CASE WHEN channel_id != prev_channel THEN (timestamp - prev_timestamp) / 60 END) as avg_time_between_switches_min
        FROM ryan_sequence
        WHERE prev_channel IS NOT NULL
        GROUP BY date, hour, day_of_week
        ORDER BY date, hour
    """)
    views_created.append("v_slack_context_switching")
    
    # 10. v_collaboration_frequency - Top messaging partners
    print("Creating v_collaboration_frequency...")
    conn.execute("""
        CREATE OR REPLACE VIEW v_collaboration_frequency AS
        WITH dm_conversations AS (
            SELECT 
                CASE 
                    WHEN user_id = 'UBL74SKU0' THEN 'Ryan'
                    ELSE u.real_name 
                END as sender_name,
                CASE 
                    WHEN user_id = 'UBL74SKU0' THEN 'Ryan'
                    ELSE u.real_name 
                END as sender,
                channel_name,
                date,
                COUNT(*) as messages,
                user_id
            FROM slack_messages m
            LEFT JOIN slack_users u ON m.user_id = u.user_id
            WHERE channel_name = 'Direct Message'
            GROUP BY user_id, u.real_name, channel_name, date
        ),
        channel_interactions AS (
            SELECT 
                m.channel_name,
                u.real_name as participant,
                m.user_id,
                COUNT(*) as messages,
                COUNT(CASE WHEN m.user_id = 'UBL74SKU0' THEN 1 END) as ryan_messages,
                COUNT(CASE WHEN m.user_id != 'UBL74SKU0' THEN 1 END) as their_messages
            FROM slack_messages m
            LEFT JOIN slack_users u ON m.user_id = u.user_id
            WHERE channel_name != 'Direct Message'
            GROUP BY m.channel_name, u.real_name, m.user_id
        )
        SELECT 
            'DM' as interaction_type,
            sender_name as collaborator,
            channel_name,
            SUM(messages) as total_messages,
            COUNT(DISTINCT date) as days_active,
            ROUND(SUM(messages) * 1.0 / COUNT(DISTINCT date), 1) as avg_messages_per_day
        FROM dm_conversations
        WHERE sender_name != 'Ryan'
        GROUP BY sender_name, channel_name
        
        UNION ALL
        
        SELECT 
            'Channel' as interaction_type,
            participant as collaborator,
            channel_name,
            messages as total_messages,
            1 as days_active,  -- Approximation for channel data
            messages as avg_messages_per_day
        FROM channel_interactions  
        WHERE participant != 'Ryan Marien' AND participant IS NOT NULL
        
        ORDER BY total_messages DESC
    """)
    views_created.append("v_collaboration_frequency")
    
    # 11. v_proactive_vs_reactive - Initiated vs response messages
    print("Creating v_proactive_vs_reactive...")
    conn.execute("""
        CREATE OR REPLACE VIEW v_proactive_vs_reactive AS
        WITH message_context AS (
            SELECT 
                m.*,
                LAG(user_id) OVER (PARTITION BY channel_id ORDER BY timestamp) as prev_user,
                LAG(timestamp) OVER (PARTITION BY channel_id ORDER BY timestamp) as prev_timestamp,
                CASE 
                    WHEN LAG(user_id) OVER (PARTITION BY channel_id ORDER BY timestamp) IS NULL THEN 'Conversation Starter'
                    WHEN LAG(user_id) OVER (PARTITION BY channel_id ORDER BY timestamp) != user_id THEN 'Response'
                    WHEN LAG(user_id) OVER (PARTITION BY channel_id ORDER BY timestamp) = user_id THEN 'Continuation'
                    ELSE 'Unknown'
                END as message_context_type
            FROM slack_messages m
            WHERE is_ryan_message = true
        )
        SELECT 
            channel_name,
            date,
            day_of_week,
            hour,
            COUNT(CASE WHEN message_context_type = 'Conversation Starter' THEN 1 END) as proactive_messages,
            COUNT(CASE WHEN message_context_type = 'Response' THEN 1 END) as reactive_messages,
            COUNT(CASE WHEN message_context_type = 'Continuation' THEN 1 END) as continuation_messages,
            COUNT(*) as total_ryan_messages,
            ROUND(COUNT(CASE WHEN message_context_type = 'Conversation Starter' THEN 1 END) * 100.0 / COUNT(*), 1) as proactive_pct,
            ROUND(COUNT(CASE WHEN message_context_type = 'Response' THEN 1 END) * 100.0 / COUNT(*), 1) as reactive_pct,
            -- Response time analysis for reactive messages
            AVG(CASE WHEN message_context_type = 'Response' THEN (timestamp - prev_timestamp) / 60 END) as avg_response_time_minutes
        FROM message_context
        GROUP BY channel_name, date, day_of_week, hour
        ORDER BY date, hour, channel_name
    """)
    views_created.append("v_proactive_vs_reactive")
    
    # 12. v_weekly_communication_rhythm - Weekly patterns
    print("Creating v_weekly_communication_rhythm...")
    conn.execute("""
        CREATE OR REPLACE VIEW v_weekly_communication_rhythm AS
        SELECT 
            week,
            month,
            day_of_week,
            COUNT(*) as total_weekly_messages,
            COUNT(CASE WHEN is_ryan_message THEN 1 END) as ryan_weekly_messages,
            COUNT(CASE WHEN is_dm THEN 1 END) as dm_messages,
            COUNT(CASE WHEN NOT is_dm THEN 1 END) as channel_messages,
            COUNT(CASE WHEN is_business_hours THEN 1 END) as business_hours_messages,
            COUNT(CASE WHEN is_after_hours THEN 1 END) as after_hours_messages,
            COUNT(DISTINCT channel_id) as active_channels,
            COUNT(DISTINCT user_id) as active_users,
            AVG(message_length) as avg_message_length,
            -- Weekly intensity metrics
            COUNT(*) / 5.0 as avg_messages_per_weekday,  -- Assuming 5 workdays
            ROUND(COUNT(CASE WHEN is_after_hours THEN 1 END) * 100.0 / COUNT(*), 1) as after_hours_pct,
            -- Peak activity indicators
            MAX(COUNT(*)) OVER (PARTITION BY week) = COUNT(*) as is_peak_day_of_week
        FROM slack_messages
        GROUP BY week, month, day_of_week
        ORDER BY week, CASE day_of_week 
            WHEN 'Monday' THEN 1 
            WHEN 'Tuesday' THEN 2 
            WHEN 'Wednesday' THEN 3 
            WHEN 'Thursday' THEN 4 
            WHEN 'Friday' THEN 5 
            WHEN 'Saturday' THEN 6 
            WHEN 'Sunday' THEN 7 
        END
    """)
    views_created.append("v_weekly_communication_rhythm")
    
    # 13. v_communication_efficiency - Efficiency scoring
    print("Creating v_communication_efficiency...")
    conn.execute("""
        CREATE OR REPLACE VIEW v_communication_efficiency AS
        WITH daily_metrics AS (
            SELECT 
                date,
                day_of_week,
                COUNT(*) as total_messages,
                COUNT(CASE WHEN is_ryan_message THEN 1 END) as ryan_messages,
                COUNT(CASE WHEN is_dm THEN 1 END) as dm_messages,
                COUNT(CASE WHEN NOT is_dm THEN 1 END) as channel_messages,
                COUNT(DISTINCT channel_id) as channels_used,
                COUNT(CASE WHEN is_thread_reply THEN 1 END) as thread_usage,
                AVG(CASE WHEN is_ryan_message THEN message_length END) as avg_ryan_message_length,
                COUNT(CASE WHEN is_business_hours THEN 1 END) as business_hours_messages,
                COUNT(CASE WHEN is_after_hours THEN 1 END) as after_hours_messages
            FROM slack_messages
            GROUP BY date, day_of_week
        )
        SELECT 
            date,
            day_of_week,
            total_messages,
            ryan_messages,
            dm_messages,
            channel_messages,
            channels_used,
            thread_usage,
            avg_ryan_message_length,
            business_hours_messages,
            after_hours_messages,
            -- Efficiency scores (0-100 scale)
            CASE 
                WHEN ryan_messages > 0 
                THEN ROUND(LEAST(100, (dm_messages * 1.0 / ryan_messages) * 100), 1)
                ELSE 0 
            END as dm_efficiency_score,  -- Higher DM ratio = more efficient 1:1 communication
            
            CASE 
                WHEN total_messages > 0 
                THEN ROUND(LEAST(100, (thread_usage * 1.0 / total_messages) * 100 * 2), 1)
                ELSE 0 
            END as thread_organization_score,  -- Higher thread usage = better organization
            
            CASE 
                WHEN ryan_messages > 0 
                THEN ROUND(GREATEST(0, 100 - (channels_used * 10)), 1)
                ELSE 0 
            END as focus_score,  -- Lower channel switching = better focus
            
            CASE 
                WHEN total_messages > 0 
                THEN ROUND((business_hours_messages * 1.0 / total_messages) * 100, 1)
                ELSE 0 
            END as time_management_score  -- Higher business hours ratio = better time management
            
        FROM daily_metrics
        ORDER BY date
    """)
    views_created.append("v_communication_efficiency")
    
    # 14. v_strategic_vs_operational - Communication categorization
    print("Creating v_strategic_vs_operational...")
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
            -- Quality indicators
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
    
    # 15. v_peak_communication_hours - Peak activity identification
    print("Creating v_peak_communication_hours...")
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
    
    print(f"\n✅ Created {len(views_created)} analytical views:")
    for view in views_created:
        print(f"   • {view}")
    
    # Test a few views to ensure they work
    print("\n🧪 Testing views...")
    test_queries = [
        ("v_message_volume", "SELECT COUNT(*) as days FROM v_message_volume"),
        ("v_channel_activity", "SELECT channel_name, actual_ryan_messages FROM v_channel_activity ORDER BY actual_ryan_messages DESC LIMIT 3"),
        ("v_slack_load_heatmap", "SELECT day_of_week, SUM(ryan_messages) as ryan_msgs FROM v_slack_load_heatmap GROUP BY day_of_week ORDER BY ryan_msgs DESC LIMIT 3")
    ]
    
    for view_name, query in test_queries:
        try:
            result = conn.execute(query).fetchall()
            print(f"   ✓ {view_name}: {len(result)} rows")
        except Exception as e:
            print(f"   ❌ {view_name}: {str(e)}")
    
    conn.close()
    return views_created

if __name__ == "__main__":
    views = create_analytical_views()
    print(f"\n✅ All {len(views)} Slack analytical views created successfully!")