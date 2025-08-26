#!/usr/bin/env python3
"""
Cross-Platform Correlation Views Creation
Sub-Agent 4: Integrated Calendar & Slack Analysis

Creates 15+ analytical views for identifying correlations and patterns
between calendar and Slack activity.
"""

import duckdb
import json
from pathlib import Path

class CorrelationViewsCreator:
    def __init__(self, base_path="/Users/david.campos/VibeCode/AICoS-Lab/experiments/ryan_time_analysis"):
        self.base_path = Path(base_path)
        self.calendar_db_path = self.base_path / "data/processed/duckdb/calendar_analytics.db"
        self.slack_db_path = self.base_path / "data/processed/duckdb/slack_analytics.db"
        self.integrated_db_path = self.base_path / "analytics/integrated/unified_analytics.db"
        self.conn = duckdb.connect(str(self.integrated_db_path))
        
        # Attach source databases
        self.conn.execute(f"ATTACH '{self.calendar_db_path}' AS calendar_db")
        self.conn.execute(f"ATTACH '{self.slack_db_path}' AS slack_db")
        
        print("🔗 Creating Cross-Platform Correlation Views")
        print(f"📊 Database: {self.integrated_db_path}")
        print("✅ Source databases attached")
    
    def create_temporal_correlation_views(self):
        """Create temporal correlation views between meetings and Slack."""
        print("\n⏰ Creating temporal correlation views...")
        
        views_created = []
        
        # 1. Hourly correlation view
        hourly_correlation = """
        CREATE OR REPLACE VIEW v_hourly_correlation AS
        SELECT 
            hour_timestamp,
            year, month, day, hour, day_of_week,
            meeting_count,
            meeting_minutes,
            message_count,
            active_channels,
            dm_count,
            
            -- Correlation metrics
            (meeting_minutes + message_count * 2) as combined_workload_score,
            CASE 
                WHEN meeting_count > 0 AND message_count > 0 THEN 'concurrent_activity'
                WHEN meeting_count > 0 AND message_count = 0 THEN 'meeting_only'
                WHEN meeting_count = 0 AND message_count > 0 THEN 'slack_only'
                ELSE 'inactive'
            END as activity_pattern,
            
            -- Intensity scoring
            CASE 
                WHEN meeting_minutes >= 60 AND message_count >= 5 THEN 'very_high'
                WHEN meeting_minutes >= 30 AND message_count >= 3 THEN 'high'
                WHEN meeting_minutes > 0 OR message_count > 0 THEN 'moderate'
                ELSE 'low'
            END as intensity_level,
            
            -- Business hours flag
            CASE WHEN hour BETWEEN 9 AND 17 THEN true ELSE false END as is_business_hours
        FROM v_temporal_alignment
        ORDER BY hour_timestamp;
        """
        
        self.conn.execute(hourly_correlation)
        views_created.append("v_hourly_correlation")
        print("✅ Created v_hourly_correlation")
        
        # 2. Daily workload view
        daily_workload = """
        CREATE OR REPLACE VIEW v_daily_workload AS
        SELECT 
            DATE_TRUNC('day', hour_timestamp) as date,
            day_of_week,
            
            -- Calendar metrics
            SUM(meeting_count) as total_meetings,
            SUM(meeting_minutes) as total_meeting_minutes,
            
            -- Slack metrics
            SUM(message_count) as total_messages,
            AVG(active_channels) as avg_active_channels,
            MAX(active_channels) as max_active_channels,
            SUM(dm_count) as total_dm_count,
            
            -- Combined workload metrics
            SUM(meeting_minutes + message_count * 2) as combined_workload_score,
            
            -- Activity pattern distribution
            COUNT(CASE WHEN activity_pattern = 'concurrent_activity' THEN 1 END) as concurrent_hours,
            COUNT(CASE WHEN activity_pattern = 'meeting_only' THEN 1 END) as meeting_only_hours,
            COUNT(CASE WHEN activity_pattern = 'slack_only' THEN 1 END) as slack_only_hours,
            COUNT(CASE WHEN activity_pattern = 'inactive' THEN 1 END) as inactive_hours,
            
            -- Intensity distribution
            COUNT(CASE WHEN intensity_level = 'very_high' THEN 1 END) as very_high_intensity_hours,
            COUNT(CASE WHEN intensity_level = 'high' THEN 1 END) as high_intensity_hours,
            COUNT(CASE WHEN intensity_level = 'moderate' THEN 1 END) as moderate_intensity_hours,
            
            -- Business vs after hours
            SUM(CASE WHEN is_business_hours THEN meeting_minutes ELSE 0 END) as business_hours_meeting_minutes,
            SUM(CASE WHEN is_business_hours THEN message_count ELSE 0 END) as business_hours_messages,
            SUM(CASE WHEN NOT is_business_hours THEN meeting_minutes ELSE 0 END) as after_hours_meeting_minutes,
            SUM(CASE WHEN NOT is_business_hours THEN message_count ELSE 0 END) as after_hours_messages
        FROM v_hourly_correlation
        GROUP BY DATE_TRUNC('day', hour_timestamp), day_of_week
        ORDER BY date;
        """
        
        self.conn.execute(daily_workload)
        views_created.append("v_daily_workload")
        print("✅ Created v_daily_workload")
        
        # 3. Pre-meeting activity view
        pre_meeting_activity = """
        CREATE OR REPLACE VIEW v_pre_meeting_activity AS
        WITH meeting_starts AS (
            SELECT 
                start_time,
                event_id,
                summary,
                duration_minutes,
                attendee_count,
                meeting_type
            FROM calendar_db.events
            WHERE duration_minutes >= 30  -- Focus on substantial meetings
        ),
        pre_meeting_slack AS (
            SELECT 
                ms.event_id,
                ms.summary as meeting_summary,
                ms.start_time as meeting_start,
                ms.duration_minutes,
                ms.attendee_count,
                ms.meeting_type,
                COUNT(sm.message_id) as messages_1hr_before,
                COUNT(CASE WHEN sm.datetime >= ms.start_time - INTERVAL '30 minutes' THEN 1 END) as messages_30min_before,
                COUNT(CASE WHEN sm.datetime >= ms.start_time - INTERVAL '15 minutes' THEN 1 END) as messages_15min_before,
                COUNT(DISTINCT sm.channel_id) as channels_active_before,
                AVG(sm.message_length) as avg_message_length_before
            FROM meeting_starts ms
            LEFT JOIN slack_db.slack_messages sm ON 
                sm.datetime BETWEEN ms.start_time - INTERVAL '1 hour' AND ms.start_time
                AND sm.is_ryan_message = true
            GROUP BY ms.event_id, ms.summary, ms.start_time, ms.duration_minutes, ms.attendee_count, ms.meeting_type
        )
        SELECT 
            *,
            CASE 
                WHEN messages_1hr_before >= 10 THEN 'high_prep'
                WHEN messages_1hr_before >= 5 THEN 'moderate_prep' 
                WHEN messages_1hr_before >= 1 THEN 'light_prep'
                ELSE 'no_prep'
            END as preparation_level,
            CASE 
                WHEN messages_15min_before >= 3 THEN 'last_minute_activity'
                WHEN messages_30min_before >= 3 THEN 'recent_activity'
                ELSE 'quiet_approach'
            END as pre_meeting_pattern
        FROM pre_meeting_slack
        ORDER BY meeting_start;
        """
        
        self.conn.execute(pre_meeting_activity)
        views_created.append("v_pre_meeting_activity")
        print("✅ Created v_pre_meeting_activity")
        
        # 4. Post-meeting followup view
        post_meeting_followup = """
        CREATE OR REPLACE VIEW v_post_meeting_followup AS
        WITH meeting_ends AS (
            SELECT 
                event_id,
                summary,
                start_time,
                end_time,
                duration_minutes,
                attendee_count,
                meeting_type,
                has_external_attendees
            FROM calendar_db.events
            WHERE duration_minutes >= 30  -- Focus on substantial meetings
        ),
        post_meeting_slack AS (
            SELECT 
                me.event_id,
                me.summary as meeting_summary,
                me.start_time,
                me.end_time,
                me.duration_minutes,
                me.attendee_count,
                me.meeting_type,
                me.has_external_attendees,
                COUNT(sm.message_id) as messages_1hr_after,
                COUNT(CASE WHEN sm.datetime <= me.end_time + INTERVAL '30 minutes' THEN 1 END) as messages_30min_after,
                COUNT(CASE WHEN sm.datetime <= me.end_time + INTERVAL '15 minutes' THEN 1 END) as messages_15min_after,
                COUNT(DISTINCT sm.channel_id) as channels_active_after,
                AVG(sm.message_length) as avg_message_length_after,
                COUNT(CASE WHEN sm.is_dm = true THEN 1 END) as dm_messages_after
            FROM meeting_ends me
            LEFT JOIN slack_db.slack_messages sm ON 
                sm.datetime BETWEEN me.end_time AND me.end_time + INTERVAL '1 hour'
                AND sm.is_ryan_message = true
            GROUP BY me.event_id, me.summary, me.start_time, me.end_time, me.duration_minutes, 
                     me.attendee_count, me.meeting_type, me.has_external_attendees
        )
        SELECT 
            *,
            CASE 
                WHEN messages_1hr_after >= 10 THEN 'high_followup'
                WHEN messages_1hr_after >= 5 THEN 'moderate_followup'
                WHEN messages_1hr_after >= 1 THEN 'light_followup'
                ELSE 'no_followup'
            END as followup_level,
            CASE 
                WHEN messages_15min_after >= 3 THEN 'immediate_action'
                WHEN messages_30min_after >= 3 THEN 'quick_followup'
                ELSE 'delayed_followup'
            END as followup_pattern,
            CASE 
                WHEN dm_messages_after >= messages_1hr_after * 0.5 THEN 'dm_focused'
                WHEN channels_active_after >= 3 THEN 'broadcast_focused'
                ELSE 'mixed_communication'
            END as followup_style
        FROM post_meeting_slack
        ORDER BY start_time;
        """
        
        self.conn.execute(post_meeting_followup)
        views_created.append("v_post_meeting_followup")
        print("✅ Created v_post_meeting_followup")
        
        # 5. Context switching combined view
        context_switching = """
        CREATE OR REPLACE VIEW v_context_switching_combined AS
        WITH hourly_transitions AS (
            SELECT 
                DATE_TRUNC('day', hour_timestamp) as date,
                hour,
                meeting_count,
                active_channels,
                message_count,
                LAG(active_channels) OVER (PARTITION BY DATE_TRUNC('day', hour_timestamp) ORDER BY hour) as prev_channels,
                LAG(meeting_count) OVER (PARTITION BY DATE_TRUNC('day', hour_timestamp) ORDER BY hour) as prev_meetings,
                
                -- Calculate transitions
                CASE 
                    WHEN active_channels != COALESCE(LAG(active_channels) OVER (PARTITION BY DATE_TRUNC('day', hour_timestamp) ORDER BY hour), 0)
                    THEN ABS(active_channels - COALESCE(LAG(active_channels) OVER (PARTITION BY DATE_TRUNC('day', hour_timestamp) ORDER BY hour), 0))
                    ELSE 0
                END as channel_switches,
                
                CASE 
                    WHEN meeting_count > 0 AND COALESCE(LAG(meeting_count) OVER (PARTITION BY DATE_TRUNC('day', hour_timestamp) ORDER BY hour), 0) = 0 THEN 1
                    WHEN meeting_count = 0 AND COALESCE(LAG(meeting_count) OVER (PARTITION BY DATE_TRUNC('day', hour_timestamp) ORDER BY hour), 0) > 0 THEN 1
                    ELSE 0
                END as meeting_context_switch
            FROM v_hourly_correlation
            WHERE meeting_count > 0 OR message_count > 0
        )
        SELECT 
            date,
            SUM(channel_switches) as total_channel_switches,
            SUM(meeting_context_switch) as total_meeting_context_switches,
            SUM(channel_switches + meeting_context_switch) as total_context_switches,
            AVG(active_channels) as avg_channels_per_hour,
            MAX(active_channels) as max_channels_per_hour,
            COUNT(*) as active_hours,
            
            -- Context switching intensity
            CASE 
                WHEN SUM(channel_switches + meeting_context_switch) >= 8 THEN 'very_high'
                WHEN SUM(channel_switches + meeting_context_switch) >= 5 THEN 'high'
                WHEN SUM(channel_switches + meeting_context_switch) >= 2 THEN 'moderate'
                ELSE 'low'
            END as switching_intensity
        FROM hourly_transitions
        GROUP BY date
        ORDER BY date;
        """
        
        self.conn.execute(context_switching)
        views_created.append("v_context_switching_combined")
        print("✅ Created v_context_switching_combined")
        
        return views_created
    
    def create_communication_meeting_integration_views(self):
        """Create views that integrate communication and meeting patterns."""
        print("\n💬 Creating communication-meeting integration views...")
        
        views_created = []
        
        # 6. Meeting-Slack overlap view
        meeting_slack_overlap = """
        CREATE OR REPLACE VIEW v_meeting_slack_overlap AS
        WITH meeting_periods AS (
            SELECT 
                event_id,
                summary,
                start_time,
                end_time,
                duration_minutes,
                attendee_count,
                meeting_type
            FROM calendar_db.events
        ),
        concurrent_activity AS (
            SELECT 
                mp.event_id,
                mp.summary as meeting_summary,
                mp.start_time,
                mp.end_time,
                mp.duration_minutes,
                mp.attendee_count,
                mp.meeting_type,
                COUNT(sm.message_id) as messages_during_meeting,
                COUNT(DISTINCT sm.channel_id) as channels_active_during,
                AVG(sm.message_length) as avg_message_length_during,
                COUNT(CASE WHEN sm.is_dm = true THEN 1 END) as dm_messages_during,
                COUNT(CASE WHEN sm.is_dm = false THEN 1 END) as channel_messages_during
            FROM meeting_periods mp
            LEFT JOIN slack_db.slack_messages sm ON 
                sm.datetime BETWEEN mp.start_time AND mp.end_time
                AND sm.is_ryan_message = true
            GROUP BY mp.event_id, mp.summary, mp.start_time, mp.end_time, 
                     mp.duration_minutes, mp.attendee_count, mp.meeting_type
        )
        SELECT 
            *,
            ROUND(messages_during_meeting::FLOAT / NULLIF(duration_minutes, 0) * 60, 2) as messages_per_hour_rate,
            CASE 
                WHEN messages_during_meeting >= 5 THEN 'high_multitasking'
                WHEN messages_during_meeting >= 2 THEN 'moderate_multitasking'
                WHEN messages_during_meeting >= 1 THEN 'light_multitasking'
                ELSE 'focused_meeting'
            END as multitasking_level,
            CASE 
                WHEN dm_messages_during > channel_messages_during THEN 'private_communication'
                WHEN channel_messages_during > dm_messages_during THEN 'public_communication'
                WHEN messages_during_meeting > 0 THEN 'mixed_communication'
                ELSE 'no_communication'
            END as communication_style
        FROM concurrent_activity
        ORDER BY start_time;
        """
        
        self.conn.execute(meeting_slack_overlap)
        views_created.append("v_meeting_slack_overlap")
        print("✅ Created v_meeting_slack_overlap")
        
        # 7. Preparation patterns view
        preparation_patterns = """
        CREATE OR REPLACE VIEW v_preparation_patterns AS
        WITH strategic_meetings AS (
            SELECT 
                event_id,
                summary,
                start_time,
                duration_minutes,
                attendee_count,
                meeting_type,
                has_external_attendees
            FROM calendar_db.events
            WHERE (attendee_count >= 5 OR has_external_attendees = true OR duration_minutes >= 60)
              AND meeting_type != 'personal'
        )
        SELECT 
            sm.event_id,
            sm.summary,
            sm.start_time,
            sm.duration_minutes,
            sm.attendee_count,
            sm.meeting_type,
            sm.has_external_attendees,
            pma.messages_1hr_before,
            pma.messages_30min_before,
            pma.messages_15min_before,
            pma.channels_active_before,
            pma.preparation_level,
            pma.pre_meeting_pattern,
            
            -- Meeting importance scoring
            CASE 
                WHEN sm.has_external_attendees = true AND sm.attendee_count >= 5 THEN 'critical'
                WHEN sm.duration_minutes >= 90 OR sm.attendee_count >= 8 THEN 'high_importance'
                WHEN sm.attendee_count >= 3 OR sm.duration_minutes >= 60 THEN 'moderate_importance'
                ELSE 'standard'
            END as meeting_importance,
            
            -- Preparation efficiency score
            CASE 
                WHEN sm.has_external_attendees = true AND pma.preparation_level IN ('high_prep', 'moderate_prep') THEN 'well_prepared'
                WHEN sm.attendee_count >= 5 AND pma.preparation_level != 'no_prep' THEN 'adequately_prepared'
                WHEN pma.preparation_level = 'no_prep' THEN 'unprepared'
                ELSE 'standard_prep'
            END as preparation_efficiency
        FROM strategic_meetings sm
        LEFT JOIN v_pre_meeting_activity pma ON sm.event_id = pma.event_id
        ORDER BY sm.start_time;
        """
        
        self.conn.execute(preparation_patterns)
        views_created.append("v_preparation_patterns")
        print("✅ Created v_preparation_patterns")
        
        # 8. Followup efficiency view
        followup_efficiency = """
        CREATE OR REPLACE VIEW v_followup_efficiency AS
        SELECT 
            pmf.event_id,
            pmf.meeting_summary,
            pmf.start_time,
            pmf.duration_minutes,
            pmf.attendee_count,
            pmf.meeting_type,
            pmf.has_external_attendees,
            pmf.messages_1hr_after,
            pmf.messages_30min_after,
            pmf.messages_15min_after,
            pmf.channels_active_after,
            pmf.dm_messages_after,
            pmf.followup_level,
            pmf.followup_pattern,
            pmf.followup_style,
            
            -- Meeting action requirement scoring
            CASE 
                WHEN pmf.has_external_attendees = true THEN 'external_followup_required'
                WHEN pmf.attendee_count >= 5 THEN 'coordination_required'
                WHEN pmf.duration_minutes >= 60 THEN 'decision_followup_likely'
                ELSE 'standard_meeting'
            END as action_requirement,
            
            -- Followup appropriateness
            CASE 
                WHEN pmf.has_external_attendees = true AND pmf.followup_level IN ('high_followup', 'moderate_followup') THEN 'appropriate'
                WHEN pmf.attendee_count >= 5 AND pmf.followup_level != 'no_followup' THEN 'appropriate'
                WHEN pmf.duration_minutes >= 60 AND pmf.followup_level = 'no_followup' THEN 'missed_opportunity'
                WHEN pmf.meeting_type = 'personal' AND pmf.followup_level = 'high_followup' THEN 'over_communication'
                ELSE 'standard'
            END as followup_appropriateness,
            
            -- Efficiency score
            CASE 
                WHEN pmf.followup_pattern = 'immediate_action' AND pmf.followup_style = 'dm_focused' THEN 'highly_efficient'
                WHEN pmf.followup_pattern = 'quick_followup' THEN 'efficient'
                WHEN pmf.followup_level = 'no_followup' AND pmf.has_external_attendees = true THEN 'inefficient'
                ELSE 'standard_efficiency'
            END as efficiency_rating
        FROM v_post_meeting_followup pmf
        ORDER BY pmf.start_time;
        """
        
        self.conn.execute(followup_efficiency)
        views_created.append("v_followup_efficiency")
        print("✅ Created v_followup_efficiency")
        
        # 9. Total collaboration time view
        total_collaboration_time = """
        CREATE OR REPLACE VIEW v_total_collaboration_time AS
        SELECT 
            dw.date,
            dw.day_of_week,
            
            -- Calendar collaboration
            dw.total_meeting_minutes as meeting_collaboration_minutes,
            dw.total_meetings,
            
            -- Slack collaboration (estimate 2 minutes per message)
            dw.total_messages * 2 as slack_collaboration_minutes,
            dw.total_messages,
            dw.total_dm_count,
            
            -- Total collaboration time
            dw.total_meeting_minutes + (dw.total_messages * 2) as total_collaboration_minutes,
            ROUND((dw.total_meeting_minutes + (dw.total_messages * 2))::FLOAT / 60, 1) as total_collaboration_hours,
            
            -- Collaboration distribution
            ROUND(dw.total_meeting_minutes::FLOAT / NULLIF(dw.total_meeting_minutes + (dw.total_messages * 2), 0) * 100, 1) as meeting_collaboration_pct,
            ROUND((dw.total_messages * 2)::FLOAT / NULLIF(dw.total_meeting_minutes + (dw.total_messages * 2), 0) * 100, 1) as slack_collaboration_pct,
            
            -- Quality indicators
            dw.concurrent_hours,
            dw.very_high_intensity_hours + dw.high_intensity_hours as high_intensity_hours,
            
            -- Business vs after hours distribution
            dw.business_hours_meeting_minutes + (dw.business_hours_messages * 2) as business_hours_collaboration_minutes,
            dw.after_hours_meeting_minutes + (dw.after_hours_messages * 2) as after_hours_collaboration_minutes,
            
            ROUND((dw.after_hours_meeting_minutes + (dw.after_hours_messages * 2))::FLOAT / 
                  NULLIF(dw.total_meeting_minutes + (dw.total_messages * 2), 0) * 100, 1) as after_hours_collaboration_pct,
            
            -- Collaboration intensity
            CASE 
                WHEN (dw.total_meeting_minutes + (dw.total_messages * 2)) >= 600 THEN 'very_high'  -- 10+ hours
                WHEN (dw.total_meeting_minutes + (dw.total_messages * 2)) >= 480 THEN 'high'      -- 8+ hours
                WHEN (dw.total_meeting_minutes + (dw.total_messages * 2)) >= 360 THEN 'moderate'  -- 6+ hours
                ELSE 'low'
            END as collaboration_intensity
        FROM v_daily_workload dw
        ORDER BY dw.date;
        """
        
        self.conn.execute(total_collaboration_time)
        views_created.append("v_total_collaboration_time")
        print("✅ Created v_total_collaboration_time")
        
        # 10. Communication gaps view
        communication_gaps = """
        CREATE OR REPLACE VIEW v_communication_gaps AS
        WITH hourly_activity AS (
            SELECT 
                hour_timestamp,
                DATE_TRUNC('day', hour_timestamp) as date,
                hour,
                meeting_count,
                message_count,
                CASE WHEN meeting_count > 0 OR message_count > 0 THEN 1 ELSE 0 END as has_activity,
                CASE WHEN hour BETWEEN 9 AND 17 THEN 1 ELSE 0 END as is_business_hour
            FROM v_hourly_correlation
        ),
        gap_analysis AS (
            SELECT 
                *,
                LAG(has_activity) OVER (PARTITION BY date ORDER BY hour) as prev_hour_activity,
                LEAD(has_activity) OVER (PARTITION BY date ORDER BY hour) as next_hour_activity,
                
                -- Identify gaps (no activity for this hour but activity before/after)
                CASE 
                    WHEN has_activity = 0 
                         AND (COALESCE(LAG(has_activity) OVER (PARTITION BY date ORDER BY hour), 0) = 1 
                              OR COALESCE(LEAD(has_activity) OVER (PARTITION BY date ORDER BY hour), 0) = 1)
                         AND is_business_hour = 1
                    THEN 1 
                    ELSE 0 
                END as is_gap_hour
            FROM hourly_activity
        )
        SELECT 
            date,
            SUM(has_activity) as active_hours,
            COUNT(*) - SUM(has_activity) as inactive_hours,
            SUM(is_gap_hour) as gap_hours,
            SUM(CASE WHEN is_business_hour = 1 THEN has_activity ELSE 0 END) as business_active_hours,
            SUM(CASE WHEN is_business_hour = 1 THEN 1 - has_activity ELSE 0 END) as business_inactive_hours,
            SUM(CASE WHEN is_business_hour = 1 THEN is_gap_hour ELSE 0 END) as business_gap_hours,
            
            -- Calculate actual quiet periods (consecutive inactive hours during business)
            COUNT(*) as total_hours,
            ROUND(SUM(has_activity)::FLOAT / COUNT(*) * 100, 1) as activity_coverage_pct,
            ROUND(SUM(CASE WHEN is_business_hour = 1 THEN has_activity ELSE 0 END)::FLOAT / 
                  NULLIF(SUM(is_business_hour), 0) * 100, 1) as business_activity_coverage_pct,
            
            -- Gap classification
            CASE 
                WHEN SUM(CASE WHEN is_business_hour = 1 THEN is_gap_hour ELSE 0 END) >= 4 THEN 'frequent_gaps'
                WHEN SUM(CASE WHEN is_business_hour = 1 THEN is_gap_hour ELSE 0 END) >= 2 THEN 'moderate_gaps'
                WHEN SUM(CASE WHEN is_business_hour = 1 THEN is_gap_hour ELSE 0 END) >= 1 THEN 'few_gaps'
                ELSE 'no_gaps'
            END as gap_pattern
        FROM gap_analysis
        GROUP BY date
        ORDER BY date;
        """
        
        self.conn.execute(communication_gaps)
        views_created.append("v_communication_gaps")
        print("✅ Created v_communication_gaps")
        
        return views_created
    
    def create_executive_pattern_views(self):
        """Create executive-specific pattern analysis views."""
        print("\n👔 Creating executive pattern views...")
        
        views_created = []
        
        # 11. Strategic time allocation view
        strategic_time_allocation = """
        CREATE OR REPLACE VIEW v_strategic_time_allocation AS
        WITH strategic_meetings AS (
            SELECT 
                event_date,
                SUM(CASE WHEN meeting_type IN ('large_meeting', 'small_meeting') AND attendee_count >= 3 THEN duration_minutes ELSE 0 END) as strategic_meeting_minutes,
                SUM(CASE WHEN meeting_type = 'one_on_one' THEN duration_minutes ELSE 0 END) as coaching_meeting_minutes,
                SUM(CASE WHEN meeting_type = 'personal' OR attendee_count = 0 THEN duration_minutes ELSE 0 END) as personal_time_minutes
            FROM calendar_db.v_events_norm
            GROUP BY event_date
        ),
        strategic_slack AS (
            SELECT 
                date,
                SUM(CASE WHEN channel_name IN ('executive-team', 'leadership') THEN 1 ELSE 0 END) * 2 as strategic_slack_minutes,
                SUM(CASE WHEN channel_name = 'Direct Message' THEN 1 ELSE 0 END) * 2 as coaching_slack_minutes,
                SUM(CASE WHEN channel_name NOT IN ('executive-team', 'leadership', 'Direct Message') THEN 1 ELSE 0 END) * 2 as operational_slack_minutes
            FROM slack_db.v_strategic_vs_operational
            WHERE ryan_messages > 0
            GROUP BY date
        )
        SELECT 
            COALESCE(sm.event_date, ss.date) as date,
            
            -- Meeting time allocation
            COALESCE(sm.strategic_meeting_minutes, 0) as strategic_meeting_minutes,
            COALESCE(sm.coaching_meeting_minutes, 0) as coaching_meeting_minutes,
            COALESCE(sm.personal_time_minutes, 0) as personal_time_minutes,
            
            -- Slack time allocation 
            COALESCE(ss.strategic_slack_minutes, 0) as strategic_slack_minutes,
            COALESCE(ss.coaching_slack_minutes, 0) as coaching_slack_minutes,
            COALESCE(ss.operational_slack_minutes, 0) as operational_slack_minutes,
            
            -- Combined strategic allocation
            COALESCE(sm.strategic_meeting_minutes, 0) + COALESCE(ss.strategic_slack_minutes, 0) as total_strategic_minutes,
            COALESCE(sm.coaching_meeting_minutes, 0) + COALESCE(ss.coaching_slack_minutes, 0) as total_coaching_minutes,
            COALESCE(sm.personal_time_minutes, 0) + COALESCE(ss.operational_slack_minutes, 0) as total_operational_minutes,
            
            -- Total engagement
            COALESCE(sm.strategic_meeting_minutes, 0) + COALESCE(sm.coaching_meeting_minutes, 0) + COALESCE(sm.personal_time_minutes, 0) +
            COALESCE(ss.strategic_slack_minutes, 0) + COALESCE(ss.coaching_slack_minutes, 0) + COALESCE(ss.operational_slack_minutes, 0) as total_engagement_minutes,
            
            -- Strategic allocation percentages
            ROUND((COALESCE(sm.strategic_meeting_minutes, 0) + COALESCE(ss.strategic_slack_minutes, 0))::FLOAT /
                  NULLIF(COALESCE(sm.strategic_meeting_minutes, 0) + COALESCE(sm.coaching_meeting_minutes, 0) + COALESCE(sm.personal_time_minutes, 0) +
                         COALESCE(ss.strategic_slack_minutes, 0) + COALESCE(ss.coaching_slack_minutes, 0) + COALESCE(ss.operational_slack_minutes, 0), 0) * 100, 1) as strategic_allocation_pct
        FROM strategic_meetings sm
        FULL OUTER JOIN strategic_slack ss ON sm.event_date = ss.date
        ORDER BY date;
        """
        
        self.conn.execute(strategic_time_allocation)
        views_created.append("v_strategic_time_allocation")
        print("✅ Created v_strategic_time_allocation")
        
        # 12. Reactive vs proactive view
        reactive_vs_proactive = """
        CREATE OR REPLACE VIEW v_reactive_vs_proactive AS
        WITH meeting_initiation AS (
            SELECT 
                event_date,
                SUM(CASE WHEN organizer_self = true THEN duration_minutes ELSE 0 END) as self_organized_meeting_minutes,
                SUM(CASE WHEN organizer_self = false THEN duration_minutes ELSE 0 END) as invited_meeting_minutes,
                COUNT(CASE WHEN organizer_self = true THEN 1 END) as self_organized_meetings,
                COUNT(CASE WHEN organizer_self = false THEN 1 END) as invited_meetings
            FROM calendar_db.v_events_norm
            GROUP BY event_date
        ),
        slack_initiation AS (
            SELECT 
                date,
                -- Approximate proactive vs reactive based on message patterns and channels
                SUM(CASE WHEN is_dm = true THEN 1 ELSE 0 END) * 2 as proactive_slack_minutes,  -- DMs are typically more proactive
                SUM(CASE WHEN is_dm = false THEN 1 ELSE 0 END) * 2 as reactive_slack_minutes,  -- Channel messages often reactive
                COUNT(CASE WHEN is_dm = true THEN 1 END) as proactive_messages,
                COUNT(CASE WHEN is_dm = false THEN 1 END) as reactive_messages
            FROM slack_db.slack_messages
            WHERE is_ryan_message = true
            GROUP BY date
        )
        SELECT 
            COALESCE(mi.event_date, si.date) as date,
            
            -- Meeting patterns
            COALESCE(mi.self_organized_meeting_minutes, 0) as proactive_meeting_minutes,
            COALESCE(mi.invited_meeting_minutes, 0) as reactive_meeting_minutes,
            COALESCE(mi.self_organized_meetings, 0) as proactive_meetings,
            COALESCE(mi.invited_meetings, 0) as reactive_meetings,
            
            -- Slack patterns
            COALESCE(si.proactive_slack_minutes, 0) as proactive_slack_minutes,
            COALESCE(si.reactive_slack_minutes, 0) as reactive_slack_minutes,
            COALESCE(si.proactive_messages, 0) as proactive_messages,
            COALESCE(si.reactive_messages, 0) as reactive_messages,
            
            -- Combined proactive vs reactive
            COALESCE(mi.self_organized_meeting_minutes, 0) + COALESCE(si.proactive_slack_minutes, 0) as total_proactive_minutes,
            COALESCE(mi.invited_meeting_minutes, 0) + COALESCE(si.reactive_slack_minutes, 0) as total_reactive_minutes,
            
            -- Calculate ratios
            ROUND((COALESCE(mi.self_organized_meeting_minutes, 0) + COALESCE(si.proactive_slack_minutes, 0))::FLOAT /
                  NULLIF(COALESCE(mi.self_organized_meeting_minutes, 0) + COALESCE(si.proactive_slack_minutes, 0) +
                         COALESCE(mi.invited_meeting_minutes, 0) + COALESCE(si.reactive_slack_minutes, 0), 0) * 100, 1) as proactive_ratio_pct,
            
            -- Executive control score
            CASE 
                WHEN (COALESCE(mi.self_organized_meeting_minutes, 0) + COALESCE(si.proactive_slack_minutes, 0))::FLOAT /
                     NULLIF(COALESCE(mi.self_organized_meeting_minutes, 0) + COALESCE(si.proactive_slack_minutes, 0) +
                            COALESCE(mi.invited_meeting_minutes, 0) + COALESCE(si.reactive_slack_minutes, 0), 0) >= 0.6 THEN 'high_control'
                WHEN (COALESCE(mi.self_organized_meeting_minutes, 0) + COALESCE(si.proactive_slack_minutes, 0))::FLOAT /
                     NULLIF(COALESCE(mi.self_organized_meeting_minutes, 0) + COALESCE(si.proactive_slack_minutes, 0) +
                            COALESCE(mi.invited_meeting_minutes, 0) + COALESCE(si.reactive_slack_minutes, 0), 0) >= 0.4 THEN 'moderate_control'
                ELSE 'low_control'
            END as control_level
        FROM meeting_initiation mi
        FULL OUTER JOIN slack_initiation si ON mi.event_date = si.date
        ORDER BY date;
        """
        
        self.conn.execute(reactive_vs_proactive)
        views_created.append("v_reactive_vs_proactive")
        print("✅ Created v_reactive_vs_proactive")
        
        # 13. Workload intensity view
        workload_intensity = """
        CREATE OR REPLACE VIEW v_workload_intensity AS
        SELECT 
            tct.date,
            tct.day_of_week,
            tct.total_collaboration_hours,
            tct.collaboration_intensity,
            
            -- Context switching metrics from previous view
            csc.total_context_switches,
            csc.switching_intensity,
            
            -- Busy trap indicators
            CASE WHEN tct.total_collaboration_hours >= 10 THEN 1 ELSE 0 END as meeting_overload_indicator,
            CASE WHEN tct.concurrent_hours >= 3 THEN 1 ELSE 0 END as multitasking_indicator,
            CASE WHEN csc.total_context_switches >= 8 THEN 1 ELSE 0 END as switching_overload_indicator,
            CASE WHEN tct.after_hours_collaboration_pct >= 25 THEN 1 ELSE 0 END as after_hours_indicator,
            
            -- Combined busy trap score (0-4)
            (CASE WHEN tct.total_collaboration_hours >= 10 THEN 1 ELSE 0 END +
             CASE WHEN tct.concurrent_hours >= 3 THEN 1 ELSE 0 END +
             CASE WHEN csc.total_context_switches >= 8 THEN 1 ELSE 0 END +
             CASE WHEN tct.after_hours_collaboration_pct >= 25 THEN 1 ELSE 0 END) as busy_trap_score,
            
            -- Workload quality
            tct.meeting_collaboration_pct,
            tct.slack_collaboration_pct,
            tct.high_intensity_hours,
            
            -- Overall assessment
            CASE 
                WHEN (CASE WHEN tct.total_collaboration_hours >= 10 THEN 1 ELSE 0 END +
                      CASE WHEN tct.concurrent_hours >= 3 THEN 1 ELSE 0 END +
                      CASE WHEN csc.total_context_switches >= 8 THEN 1 ELSE 0 END +
                      CASE WHEN tct.after_hours_collaboration_pct >= 25 THEN 1 ELSE 0 END) >= 3 THEN 'severe_overload'
                WHEN (CASE WHEN tct.total_collaboration_hours >= 10 THEN 1 ELSE 0 END +
                      CASE WHEN tct.concurrent_hours >= 3 THEN 1 ELSE 0 END +
                      CASE WHEN csc.total_context_switches >= 8 THEN 1 ELSE 0 END +
                      CASE WHEN tct.after_hours_collaboration_pct >= 25 THEN 1 ELSE 0 END) >= 2 THEN 'moderate_overload'
                WHEN (CASE WHEN tct.total_collaboration_hours >= 10 THEN 1 ELSE 0 END +
                      CASE WHEN tct.concurrent_hours >= 3 THEN 1 ELSE 0 END +
                      CASE WHEN csc.total_context_switches >= 8 THEN 1 ELSE 0 END +
                      CASE WHEN tct.after_hours_collaboration_pct >= 25 THEN 1 ELSE 0 END) >= 1 THEN 'mild_overload'
                ELSE 'sustainable'
            END as workload_assessment
        FROM v_total_collaboration_time tct
        LEFT JOIN v_context_switching_combined csc ON tct.date = csc.date
        ORDER BY tct.date;
        """
        
        self.conn.execute(workload_intensity)
        views_created.append("v_workload_intensity")
        print("✅ Created v_workload_intensity")
        
        # 14. Collaboration network unified view
        collaboration_network = """
        CREATE OR REPLACE VIEW v_collaboration_network_unified AS
        WITH meeting_partners AS (
            SELECT 
                p.email as partner_email,
                p.display_name as partner_name,
                p.domain,
                COUNT(DISTINCT e.event_id) as meeting_count,
                SUM(e.duration_minutes) as total_meeting_minutes,
                AVG(e.duration_minutes) as avg_meeting_duration,
                COUNT(CASE WHEN e.meeting_type = 'one_on_one' THEN 1 END) as one_on_one_count
            FROM calendar_db.events e
            JOIN calendar_db.participants p ON e.event_id = p.event_id
            WHERE p.email != 'ryan@biorender.com'  -- Exclude Ryan himself
            GROUP BY p.email, p.display_name, p.domain
        ),
        slack_partners AS (
            SELECT 
                -- Approximate partner identification through channel activity patterns
                'unknown@' || channel_name as partner_email,
                channel_name as partner_name,
                'slack_channel' as domain,
                COUNT(*) as message_interactions,
                COUNT(*) * 2 as estimated_collaboration_minutes,
                AVG(message_length) as avg_message_length,
                COUNT(CASE WHEN is_dm = true THEN 1 END) as dm_interactions
            FROM slack_db.slack_messages
            WHERE is_ryan_message = true
            GROUP BY channel_name
        )
        SELECT 
            COALESCE(mp.partner_email, sp.partner_email) as partner_email,
            COALESCE(mp.partner_name, sp.partner_name) as partner_name,
            COALESCE(mp.domain, sp.domain) as domain,
            
            -- Meeting collaboration
            COALESCE(mp.meeting_count, 0) as meeting_count,
            COALESCE(mp.total_meeting_minutes, 0) as meeting_minutes,
            COALESCE(mp.one_on_one_count, 0) as one_on_one_meetings,
            
            -- Slack collaboration
            COALESCE(sp.message_interactions, 0) as slack_interactions,
            COALESCE(sp.estimated_collaboration_minutes, 0) as slack_minutes,
            COALESCE(sp.dm_interactions, 0) as dm_interactions,
            
            -- Combined metrics
            COALESCE(mp.total_meeting_minutes, 0) + COALESCE(sp.estimated_collaboration_minutes, 0) as total_collaboration_minutes,
            ROUND((COALESCE(mp.total_meeting_minutes, 0) + COALESCE(sp.estimated_collaboration_minutes, 0))::FLOAT / 60, 1) as total_collaboration_hours,
            
            -- Relationship strength
            CASE 
                WHEN COALESCE(mp.total_meeting_minutes, 0) + COALESCE(sp.estimated_collaboration_minutes, 0) >= 1200 THEN 'primary_collaborator'  -- 20+ hours
                WHEN COALESCE(mp.total_meeting_minutes, 0) + COALESCE(sp.estimated_collaboration_minutes, 0) >= 600 THEN 'frequent_collaborator'   -- 10+ hours
                WHEN COALESCE(mp.total_meeting_minutes, 0) + COALESCE(sp.estimated_collaboration_minutes, 0) >= 180 THEN 'regular_collaborator'    -- 3+ hours
                ELSE 'occasional_collaborator'
            END as relationship_strength,
            
            -- Communication preference
            CASE 
                WHEN COALESCE(mp.total_meeting_minutes, 0) > COALESCE(sp.estimated_collaboration_minutes, 0) * 2 THEN 'meeting_focused'
                WHEN COALESCE(sp.estimated_collaboration_minutes, 0) > COALESCE(mp.total_meeting_minutes, 0) * 2 THEN 'slack_focused'
                ELSE 'balanced_communication'
            END as communication_preference
        FROM meeting_partners mp
        FULL OUTER JOIN slack_partners sp ON mp.partner_email = sp.partner_email
        WHERE COALESCE(mp.total_meeting_minutes, 0) + COALESCE(sp.estimated_collaboration_minutes, 0) > 0
        ORDER BY total_collaboration_minutes DESC;
        """
        
        self.conn.execute(collaboration_network)
        views_created.append("v_collaboration_network_unified")
        print("✅ Created v_collaboration_network_unified")
        
        # 15. Efficiency correlation view
        efficiency_correlation = """
        CREATE OR REPLACE VIEW v_efficiency_correlation AS
        WITH calendar_efficiency AS (
            SELECT 
                DATE_TRUNC('day', start_time) as date,
                COUNT(*) as daily_meetings,
                SUM(duration_minutes) as daily_meeting_minutes,
                AVG(duration_minutes) as avg_meeting_duration,
                COUNT(CASE WHEN attendee_count >= 5 THEN 1 END) as large_meetings,
                COUNT(CASE WHEN duration_minutes <= 30 THEN 1 END) as short_meetings,
                SUM(CASE WHEN meeting_type = 'personal' OR attendee_count = 0 THEN duration_minutes ELSE 0 END) as focus_time_minutes
            FROM calendar_db.events
            GROUP BY DATE_TRUNC('day', start_time)
        ),
        slack_efficiency AS (
            SELECT 
                date,
                COUNT(*) as daily_messages,
                AVG(message_length) as avg_message_length,
                COUNT(DISTINCT channel_id) as channels_used,
                COUNT(CASE WHEN is_dm = true THEN 1 END) as dm_messages,
                COUNT(CASE WHEN is_after_hours = true THEN 1 END) as after_hours_messages
            FROM slack_db.slack_messages
            WHERE is_ryan_message = true
            GROUP BY date
        )
        SELECT 
            COALESCE(ce.date, se.date) as date,
            
            -- Calendar efficiency metrics
            COALESCE(ce.daily_meetings, 0) as daily_meetings,
            COALESCE(ce.daily_meeting_minutes, 0) as daily_meeting_minutes,
            COALESCE(ce.avg_meeting_duration, 0) as avg_meeting_duration,
            COALESCE(ce.focus_time_minutes, 0) as focus_time_minutes,
            
            -- Slack efficiency metrics
            COALESCE(se.daily_messages, 0) as daily_messages,
            COALESCE(se.avg_message_length, 0) as avg_message_length,
            COALESCE(se.channels_used, 0) as channels_used,
            COALESCE(se.dm_messages, 0) as dm_messages,
            
            -- Combined efficiency scores
            -- Calendar efficiency (lower meetings, more focus time, shorter average duration = better)
            CASE 
                WHEN COALESCE(ce.daily_meetings, 0) <= 4 AND COALESCE(ce.focus_time_minutes, 0) >= 120 THEN 'high_calendar_efficiency'
                WHEN COALESCE(ce.daily_meetings, 0) <= 6 AND COALESCE(ce.focus_time_minutes, 0) >= 60 THEN 'moderate_calendar_efficiency'
                ELSE 'low_calendar_efficiency'
            END as calendar_efficiency,
            
            -- Slack efficiency (fewer context switches, more DMs, appropriate message length = better)
            CASE 
                WHEN COALESCE(se.channels_used, 0) <= 3 AND COALESCE(se.dm_messages, 0)::FLOAT / NULLIF(COALESCE(se.daily_messages, 1), 0) >= 0.4 THEN 'high_slack_efficiency'
                WHEN COALESCE(se.channels_used, 0) <= 5 THEN 'moderate_slack_efficiency'
                ELSE 'low_slack_efficiency'
            END as slack_efficiency,
            
            -- Overall daily efficiency
            CASE 
                WHEN (COALESCE(ce.daily_meetings, 0) <= 4 AND COALESCE(ce.focus_time_minutes, 0) >= 120) 
                     AND (COALESCE(se.channels_used, 0) <= 3 AND COALESCE(se.dm_messages, 0)::FLOAT / NULLIF(COALESCE(se.daily_messages, 1), 0) >= 0.4)
                THEN 'high_overall_efficiency'
                WHEN (COALESCE(ce.daily_meetings, 0) <= 6 AND COALESCE(ce.focus_time_minutes, 0) >= 60) 
                     AND (COALESCE(se.channels_used, 0) <= 5)
                THEN 'moderate_overall_efficiency'
                ELSE 'low_overall_efficiency'
            END as overall_efficiency,
            
            -- Correlation indicators
            CASE 
                WHEN COALESCE(ce.daily_meetings, 0) > 6 AND COALESCE(se.daily_messages, 0) > 15 THEN 'high_volume_both'
                WHEN COALESCE(ce.daily_meetings, 0) <= 4 AND COALESCE(se.daily_messages, 0) <= 8 THEN 'low_volume_both'
                WHEN COALESCE(ce.daily_meetings, 0) > 6 AND COALESCE(se.daily_messages, 0) <= 8 THEN 'meeting_heavy'
                WHEN COALESCE(ce.daily_meetings, 0) <= 4 AND COALESCE(se.daily_messages, 0) > 15 THEN 'slack_heavy'
                ELSE 'balanced'
            END as volume_correlation
        FROM calendar_efficiency ce
        FULL OUTER JOIN slack_efficiency se ON ce.date = se.date
        ORDER BY date;
        """
        
        self.conn.execute(efficiency_correlation)
        views_created.append("v_efficiency_correlation")
        print("✅ Created v_efficiency_correlation")
        
        return views_created
    
    def create_summary_and_export(self):
        """Create summary of all views and export metadata."""
        print("\n📋 Creating views summary and export...")
        
        try:
            # Get all views created
            views_query = """
            SELECT table_name, table_type 
            FROM information_schema.tables 
            WHERE table_schema = 'main' AND table_name LIKE 'v_%'
            ORDER BY table_name;
            """
            
            views = self.conn.execute(views_query).fetchall()
            
            # Create summary
            summary = {
                "correlation_views_created": len(views),
                "creation_timestamp": "2025-08-19",
                "views": []
            }
            
            for view in views:
                view_name = view[0]
                
                # Get row count for each view
                try:
                    count = self.conn.execute(f"SELECT COUNT(*) FROM {view_name}").fetchone()[0]
                    
                    # Get sample data
                    sample = self.conn.execute(f"SELECT * FROM {view_name} LIMIT 1").fetchall()
                    
                    summary["views"].append({
                        "name": view_name,
                        "type": view[1],
                        "row_count": count,
                        "has_data": count > 0
                    })
                    
                except Exception as e:
                    summary["views"].append({
                        "name": view_name,
                        "type": view[1],
                        "row_count": 0,
                        "error": str(e),
                        "has_data": False
                    })
            
            # Export summary
            summary_file = self.base_path / "analytics/integrated/correlation_views_summary.json"
            with open(summary_file, 'w') as f:
                json.dump(summary, f, indent=2, default=str)
            
            print(f"✅ Views summary exported to {summary_file}")
            print(f"📊 Total correlation views created: {len(views)}")
            print(f"🔍 Views with data: {sum(1 for v in summary['views'] if v['has_data'])}")
            
            return summary
            
        except Exception as e:
            print(f"❌ Error creating summary: {e}")
            return None
    
    def run_creation(self):
        """Run the complete correlation views creation process."""
        print("🚀 Starting Correlation Views Creation...")
        
        all_views_created = []
        
        # Create temporal correlation views
        temporal_views = self.create_temporal_correlation_views()
        all_views_created.extend(temporal_views)
        
        # Create communication-meeting integration views
        integration_views = self.create_communication_meeting_integration_views()
        all_views_created.extend(integration_views)
        
        # Create executive pattern views
        executive_views = self.create_executive_pattern_views()
        all_views_created.extend(executive_views)
        
        # Create summary
        summary = self.create_summary_and_export()
        
        print(f"\n✅ Correlation Views Creation Completed!")
        print(f"📊 Total views created: {len(all_views_created)}")
        print(f"🎯 Categories covered:")
        print(f"   - Temporal Correlation: {len(temporal_views)} views")
        print(f"   - Communication-Meeting Integration: {len(integration_views)} views")  
        print(f"   - Executive Patterns: {len(executive_views)} views")
        
        return len(all_views_created) >= 15

if __name__ == "__main__":
    creator = CorrelationViewsCreator()
    creator.run_creation()