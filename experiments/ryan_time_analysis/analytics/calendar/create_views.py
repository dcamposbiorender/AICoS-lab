#!/usr/bin/env python3
"""
Calendar Analytics - DuckDB Views Implementation
================================================

This script implements the 18+ analytical views from the CoS Analytics framework
for comprehensive calendar analysis. These views provide deterministic, mathematical
analysis of Ryan's meeting patterns, productivity metrics, and time allocation.

Views implemented:
1. Core normalization views
2. Time-based analysis views  
3. Meeting pattern views
4. Collaboration analysis views
5. Productivity metric views

Database: /experiments/ryan_time_analysis/data/processed/duckdb/calendar_analytics.db
"""

import duckdb
import pandas as pd
from datetime import datetime, timedelta
import os

class CalendarViewsCreator:
    def __init__(self, db_path: str):
        """Initialize with database path."""
        self.db_path = db_path
        self.connection = None
        
    def connect_db(self):
        """Connect to the DuckDB database."""
        self.connection = duckdb.connect(self.db_path)
        print(f"Connected to DuckDB: {self.db_path}")
        
    def create_core_views(self):
        """Create core normalization and time-based views."""
        
        print("Creating core analytical views...")
        
        # v_events_norm: Normalized event times with additional metrics
        self.connection.execute("""
            CREATE OR REPLACE VIEW v_events_norm AS
            SELECT 
                event_id,
                series_id,
                summary,
                start_time,
                end_time,
                duration_minutes,
                -- Normalize to consistent timezone for analysis
                start_time AT TIME ZONE 'America/New_York' AS start_local,
                end_time AT TIME ZONE 'America/New_York' AS end_local,
                -- Extract time components
                EXTRACT(hour FROM start_time AT TIME ZONE 'America/New_York') AS start_hour,
                EXTRACT(dow FROM start_time AT TIME ZONE 'America/New_York') AS day_of_week,
                DATE(start_time AT TIME ZONE 'America/New_York') AS event_date,
                EXTRACT(week FROM start_time AT TIME ZONE 'America/New_York') AS week_of_year,
                EXTRACT(month FROM start_time AT TIME ZONE 'America/New_York') AS month,
                -- Meeting characteristics
                meeting_type,
                attendee_count,
                has_external_attendees,
                is_recurring,
                organizer_self,
                -- Business hours classification (9 AM - 6 PM)
                CASE 
                    WHEN EXTRACT(hour FROM start_time AT TIME ZONE 'America/New_York') BETWEEN 9 AND 17 
                    THEN 'business_hours'
                    ELSE 'off_hours'
                END AS time_classification,
                -- Duration categorization
                CASE 
                    WHEN duration_minutes <= 15 THEN 'short'
                    WHEN duration_minutes <= 30 THEN 'standard'
                    WHEN duration_minutes <= 60 THEN 'long'
                    ELSE 'extended'
                END AS duration_category
            FROM events
            WHERE status = 'confirmed'
        """)
        
        # v_day_load: Day of week × Hour heatmap data
        self.connection.execute("""
            CREATE OR REPLACE VIEW v_day_load AS
            SELECT 
                day_of_week,
                start_hour,
                COUNT(*) AS event_count,
                SUM(duration_minutes) AS total_minutes,
                AVG(duration_minutes) AS avg_duration,
                COUNT(DISTINCT event_date) AS unique_days,
                -- Calculate meeting density (meetings per unique day)
                ROUND(COUNT(*)::DECIMAL / COUNT(DISTINCT event_date), 2) AS meetings_per_day,
                -- Meeting type breakdown
                SUM(CASE WHEN meeting_type = 'personal' THEN 1 ELSE 0 END) AS personal_count,
                SUM(CASE WHEN meeting_type IN ('one_on_one', 'small_meeting', 'large_meeting') THEN 1 ELSE 0 END) AS meeting_count,
                SUM(CASE WHEN meeting_type = 'blocked_time' THEN 1 ELSE 0 END) AS blocked_time_count
            FROM v_events_norm
            GROUP BY day_of_week, start_hour
            ORDER BY day_of_week, start_hour
        """)
        
        print("✓ Created v_events_norm and v_day_load views")
        
    def create_meeting_pattern_views(self):
        """Create views for meeting pattern analysis."""
        
        print("Creating meeting pattern views...")
        
        # v_b2b: Back-to-back meeting analysis
        self.connection.execute("""
            CREATE OR REPLACE VIEW v_b2b AS
            WITH meeting_pairs AS (
                SELECT 
                    e1.event_id AS current_event,
                    e1.start_time AS current_start,
                    e1.end_time AS current_end,
                    e1.duration_minutes AS current_duration,
                    e2.event_id AS next_event,
                    e2.start_time AS next_start,
                    e2.duration_minutes AS next_duration,
                    -- Calculate gap in minutes
                    EXTRACT(epoch FROM (e2.start_time - e1.end_time))/60 AS gap_minutes,
                    e1.event_date
                FROM v_events_norm e1
                LEFT JOIN v_events_norm e2 ON 
                    e1.event_date = e2.event_date AND
                    e2.start_time > e1.end_time AND
                    e2.start_time <= e1.end_time + INTERVAL '4 hours'  -- Only consider next meeting within 4 hours
                WHERE e1.meeting_type IN ('one_on_one', 'small_meeting', 'large_meeting')
                  AND e2.meeting_type IN ('one_on_one', 'small_meeting', 'large_meeting')
            ),
            ranked_pairs AS (
                SELECT *,
                    ROW_NUMBER() OVER (PARTITION BY current_event ORDER BY next_start) AS rn
                FROM meeting_pairs
                WHERE next_event IS NOT NULL
            )
            SELECT 
                current_event,
                current_start,
                current_end,
                current_duration,
                next_event,
                next_start,
                next_duration,
                gap_minutes,
                event_date,
                -- Classify transition types
                CASE 
                    WHEN gap_minutes <= 0 THEN 'overlapping'
                    WHEN gap_minutes <= 5 THEN 'back_to_back'
                    WHEN gap_minutes <= 15 THEN 'short_buffer'
                    WHEN gap_minutes <= 30 THEN 'medium_buffer'
                    ELSE 'long_buffer'
                END AS transition_type,
                -- Buffer adequacy (5 min minimum recommended)
                CASE WHEN gap_minutes >= 5 THEN 1 ELSE 0 END AS adequate_buffer
            FROM ranked_pairs
            WHERE rn = 1  -- Only the immediate next meeting
        """)
        
        # v_short_meetings: Analysis of meetings ≤15 minutes
        self.connection.execute("""
            CREATE OR REPLACE VIEW v_short_meetings AS
            SELECT 
                event_id,
                summary,
                start_time,
                duration_minutes,
                meeting_type,
                attendee_count,
                organizer_self,
                -- Categorize short meeting types
                CASE 
                    WHEN summary ILIKE '%standup%' OR summary ILIKE '%daily%' THEN 'standup'
                    WHEN summary ILIKE '%1:1%' OR summary ILIKE '%one-on-one%' THEN 'quick_sync'
                    WHEN summary ILIKE '%check%' OR summary ILIKE '%update%' THEN 'status_check'
                    WHEN organizer_self THEN 'self_organized'
                    ELSE 'other_short'
                END AS short_meeting_type,
                -- Efficiency indicator
                CASE 
                    WHEN attendee_count > 5 AND duration_minutes <= 15 THEN 'high_efficiency'
                    WHEN attendee_count <= 2 AND duration_minutes <= 15 THEN 'focused_sync'
                    ELSE 'standard_short'
                END AS efficiency_category
            FROM v_events_norm
            WHERE duration_minutes <= 15
              AND meeting_type IN ('one_on_one', 'small_meeting', 'large_meeting')
            ORDER BY start_time
        """)
        
        # v_deep_work_blocks: Identify uninterrupted time blocks ≥90 minutes
        self.connection.execute("""
            CREATE OR REPLACE VIEW v_deep_work_blocks AS
            WITH time_gaps AS (
                SELECT 
                    event_date,
                    LAG(end_time) OVER (PARTITION BY event_date ORDER BY start_time) AS prev_end,
                    start_time,
                    end_time,
                    -- Calculate gap from previous meeting end to this meeting start
                    EXTRACT(epoch FROM (start_time - LAG(end_time) OVER (PARTITION BY event_date ORDER BY start_time)))/60 AS gap_minutes
                FROM v_events_norm
                WHERE meeting_type IN ('one_on_one', 'small_meeting', 'large_meeting')
                ORDER BY event_date, start_time
            ),
            deep_work_candidates AS (
                SELECT 
                    event_date,
                    prev_end AS block_start,
                    start_time AS block_end,
                    gap_minutes,
                    -- Business hours overlap
                    GREATEST(
                        prev_end, 
                        DATE_TRUNC('day', event_date) + INTERVAL '9 hours'
                    ) AS business_start,
                    LEAST(
                        start_time, 
                        DATE_TRUNC('day', event_date) + INTERVAL '18 hours'
                    ) AS business_end
                FROM time_gaps
                WHERE gap_minutes >= 90  -- At least 90 minutes
                  AND prev_end IS NOT NULL
            )
            SELECT 
                event_date,
                block_start,
                block_end,
                gap_minutes,
                business_start,
                business_end,
                -- Calculate business hours deep work time
                EXTRACT(epoch FROM (business_end - business_start))/60 AS business_hours_minutes,
                -- Classify deep work quality
                CASE 
                    WHEN gap_minutes >= 180 THEN 'extended_deep_work'  -- 3+ hours
                    WHEN gap_minutes >= 120 THEN 'standard_deep_work'  -- 2-3 hours
                    ELSE 'minimal_deep_work'  -- 90-120 minutes
                END AS deep_work_quality,
                -- Time of day classification
                CASE 
                    WHEN EXTRACT(hour FROM block_start) < 12 THEN 'morning'
                    WHEN EXTRACT(hour FROM block_start) < 17 THEN 'afternoon'
                    ELSE 'evening'
                END AS time_period
            FROM deep_work_candidates
            WHERE business_hours_minutes > 0  -- Only blocks with business hours overlap
            ORDER BY event_date, block_start
        """)
        
        print("✓ Created v_b2b, v_short_meetings, and v_deep_work_blocks views")
        
    def create_collaboration_views(self):
        """Create collaboration and network analysis views."""
        
        print("Creating collaboration analysis views...")
        
        # v_collab_minutes: Collaboration time by domain and person
        self.connection.execute("""
            CREATE OR REPLACE VIEW v_collab_minutes AS
            WITH participant_time AS (
                SELECT 
                    e.event_id,
                    e.start_time,
                    e.duration_minutes,
                    e.meeting_type,
                    e.organizer_email,
                    p.email AS participant_email,
                    p.domain,
                    -- Calculate per-person meeting time
                    e.duration_minutes AS meeting_minutes,
                    -- Weight by attendee count for collaboration intensity
                    ROUND(e.duration_minutes::DECIMAL / GREATEST(e.attendee_count, 1), 2) AS weighted_minutes
                FROM events e
                JOIN participants p ON e.event_id = p.event_id
                WHERE e.meeting_type IN ('one_on_one', 'small_meeting', 'large_meeting')
                  AND e.status = 'confirmed'
            )
            SELECT 
                domain,
                participant_email,
                COUNT(DISTINCT event_id) AS meetings_count,
                SUM(meeting_minutes) AS total_minutes,
                AVG(meeting_minutes) AS avg_meeting_duration,
                SUM(weighted_minutes) AS weighted_collaboration_minutes,
                -- Meeting type breakdown
                SUM(CASE WHEN meeting_type = 'one_on_one' THEN meeting_minutes ELSE 0 END) AS one_on_one_minutes,
                SUM(CASE WHEN meeting_type = 'small_meeting' THEN meeting_minutes ELSE 0 END) AS small_meeting_minutes,
                SUM(CASE WHEN meeting_type = 'large_meeting' THEN meeting_minutes ELSE 0 END) AS large_meeting_minutes,
                -- Internal vs external collaboration
                MAX(CASE WHEN domain = 'biorender.com' THEN 1 ELSE 0 END) AS is_internal
            FROM participant_time
            GROUP BY domain, participant_email
            ORDER BY total_minutes DESC
        """)
        
        # v_collab_hhi: Collaboration concentration (Herfindahl-Hirschman Index)
        self.connection.execute("""
            CREATE OR REPLACE VIEW v_collab_hhi AS
            WITH collaboration_shares AS (
                SELECT 
                    domain,
                    total_minutes,
                    SUM(total_minutes) OVER () AS total_collaboration_minutes,
                    -- Calculate market share (collaboration share)
                    ROUND((total_minutes::DECIMAL / SUM(total_minutes) OVER ()) * 100, 4) AS collaboration_share_pct
                FROM (
                    SELECT domain, SUM(total_minutes) AS total_minutes
                    FROM v_collab_minutes
                    GROUP BY domain
                ) domain_totals
            )
            SELECT 
                COUNT(*) AS total_domains,
                SUM(total_minutes) AS total_collaboration_minutes,
                -- Calculate HHI (sum of squared market shares)
                ROUND(SUM(POW(collaboration_share_pct, 2)), 2) AS hhi_score,
                -- HHI interpretation
                CASE 
                    WHEN SUM(POW(collaboration_share_pct, 2)) > 2500 THEN 'highly_concentrated'
                    WHEN SUM(POW(collaboration_share_pct, 2)) > 1500 THEN 'moderately_concentrated'
                    ELSE 'unconcentrated'
                END AS concentration_level,
                -- Top collaboration partners (top 5)
                (
                    SELECT STRING_AGG(
                        domain || ' (' || ROUND(collaboration_share_pct, 1) || '%)', 
                        ', ' 
                        ORDER BY collaboration_share_pct DESC
                    )
                    FROM (
                        SELECT domain, collaboration_share_pct
                        FROM collaboration_shares
                        ORDER BY collaboration_share_pct DESC
                        LIMIT 5
                    ) top_five
                ) AS top_domains
            FROM collaboration_shares
        """)
        
        print("✓ Created v_collab_minutes and v_collab_hhi views")
        
    def create_topic_analysis_views(self):
        """Create topic and content analysis views."""
        
        print("Creating topic analysis views...")
        
        # v_topic_minutes: Meeting time by inferred topic
        self.connection.execute("""
            CREATE OR REPLACE VIEW v_topic_minutes AS
            WITH topic_classification AS (
                SELECT 
                    event_id,
                    summary,
                    duration_minutes,
                    meeting_type,
                    attendee_count,
                    start_time,
                    -- Topic classification based on meeting summary
                    CASE 
                        -- Executive/Leadership topics
                        WHEN summary ILIKE '%exec%' OR summary ILIKE '%leadership%' OR summary ILIKE '%board%' THEN 'executive'
                        WHEN summary ILIKE '%strategy%' OR summary ILIKE '%planning%' OR summary ILIKE '%roadmap%' THEN 'strategy'
                        
                        -- 1:1 and people management
                        WHEN summary ILIKE '%1:1%' OR summary ILIKE '%one-on-one%' THEN 'one_on_one'
                        WHEN summary ILIKE '%hiring%' OR summary ILIKE '%interview%' OR summary ILIKE '%candidate%' THEN 'hiring'
                        WHEN summary ILIKE '%review%' OR summary ILIKE '%feedback%' OR summary ILIKE '%performance%' THEN 'performance'
                        
                        -- Sales and business development
                        WHEN summary ILIKE '%sales%' OR summary ILIKE '%customer%' OR summary ILIKE '%client%' THEN 'sales'
                        WHEN summary ILIKE '%demo%' OR summary ILIKE '%presentation%' THEN 'demo'
                        
                        -- Product and development
                        WHEN summary ILIKE '%product%' OR summary ILIKE '%feature%' OR summary ILIKE '%dev%' THEN 'product'
                        WHEN summary ILIKE '%tech%' OR summary ILIKE '%engineering%' OR summary ILIKE '%architecture%' THEN 'technical'
                        
                        -- Operations and process
                        WHEN summary ILIKE '%ops%' OR summary ILIKE '%operations%' OR summary ILIKE '%process%' THEN 'operations'
                        WHEN summary ILIKE '%standup%' OR summary ILIKE '%scrum%' OR summary ILIKE '%sync%' THEN 'sync'
                        
                        -- External and partnerships
                        WHEN summary ILIKE '%partner%' OR summary ILIKE '%vendor%' OR summary ILIKE '%external%' THEN 'partnerships'
                        
                        -- Personal and development
                        WHEN summary ILIKE '%lunch%' OR summary ILIKE '%coffee%' OR summary ILIKE '%social%' THEN 'social'
                        WHEN summary ILIKE '%learn%' OR summary ILIKE '%training%' OR summary ILIKE '%workshop%' THEN 'learning'
                        
                        -- Default classification
                        WHEN meeting_type = 'personal' THEN 'personal_time'
                        WHEN meeting_type = 'blocked_time' THEN 'blocked_time'
                        ELSE 'general_meeting'
                    END AS topic_category,
                    
                    -- Secondary classification for more granular analysis
                    CASE 
                        WHEN summary ILIKE '%urgent%' OR summary ILIKE '%asap%' OR summary ILIKE '%emergency%' THEN 'urgent'
                        WHEN summary ILIKE '%recurring%' OR summary ILIKE '%weekly%' OR summary ILIKE '%monthly%' THEN 'recurring'
                        WHEN summary ILIKE '%brainstorm%' OR summary ILIKE '%ideation%' OR summary ILIKE '%creative%' THEN 'creative'
                        WHEN summary ILIKE '%decision%' OR summary ILIKE '%approve%' OR summary ILIKE '%sign-off%' THEN 'decision_making'
                        ELSE 'standard'
                    END AS meeting_priority
                    
                FROM v_events_norm
                WHERE meeting_type NOT IN ('cancelled', 'declined')
            )
            SELECT 
                topic_category,
                COUNT(*) AS meeting_count,
                SUM(duration_minutes) AS total_minutes,
                ROUND(AVG(duration_minutes), 1) AS avg_duration,
                ROUND(SUM(duration_minutes)::DECIMAL / 60, 1) AS total_hours,
                -- Calculate percentage of total time
                ROUND(
                    (SUM(duration_minutes)::DECIMAL / SUM(SUM(duration_minutes)) OVER ()) * 100, 
                    2
                ) AS time_share_pct,
                -- Meeting size analysis
                ROUND(AVG(attendee_count), 1) AS avg_attendees,
                -- Priority breakdown
                SUM(CASE WHEN meeting_priority = 'urgent' THEN duration_minutes ELSE 0 END) AS urgent_minutes,
                SUM(CASE WHEN meeting_priority = 'decision_making' THEN duration_minutes ELSE 0 END) AS decision_minutes
            FROM topic_classification
            GROUP BY topic_category
            ORDER BY total_minutes DESC
        """)
        
        # v_topic_entropy: Topic diversity and distribution analysis
        self.connection.execute("""
            CREATE OR REPLACE VIEW v_topic_entropy AS
            WITH topic_probabilities AS (
                SELECT 
                    topic_category,
                    total_minutes,
                    total_minutes::DECIMAL / SUM(total_minutes) OVER () AS probability
                FROM v_topic_minutes
                WHERE total_minutes > 0
            )
            SELECT 
                COUNT(*) AS total_topics,
                SUM(total_minutes) AS total_meeting_minutes,
                -- Shannon entropy calculation: -Σ(p * log2(p))
                ROUND(
                    -SUM(probability * LOG(2, probability)), 
                    3
                ) AS topic_entropy,
                -- Max possible entropy (log2(n)) for comparison
                ROUND(LOG(2, COUNT(*)), 3) AS max_entropy,
                -- Normalized entropy (0-1 scale)
                ROUND(
                    -SUM(probability * LOG(2, probability)) / LOG(2, COUNT(*)), 
                    3
                ) AS normalized_entropy,
                -- Entropy interpretation
                CASE 
                    WHEN -SUM(probability * LOG(2, probability)) / LOG(2, COUNT(*)) > 0.8 THEN 'high_diversity'
                    WHEN -SUM(probability * LOG(2, probability)) / LOG(2, COUNT(*)) > 0.6 THEN 'moderate_diversity'
                    ELSE 'low_diversity'
                END AS diversity_level
            FROM topic_probabilities
        """)
        
        print("✓ Created v_topic_minutes and v_topic_entropy views")
        
    def create_productivity_views(self):
        """Create productivity and efficiency analysis views."""
        
        print("Creating productivity analysis views...")
        
        # v_transition_map: Meeting-to-meeting transition patterns
        self.connection.execute("""
            CREATE OR REPLACE VIEW v_transition_map AS
            WITH meeting_sequences AS (
                SELECT 
                    event_id,
                    start_time,
                    end_time,
                    meeting_type,
                    -- Get topic from v_topic_minutes classification logic
                    CASE 
                        WHEN summary ILIKE '%exec%' OR summary ILIKE '%leadership%' THEN 'executive'
                        WHEN summary ILIKE '%1:1%' THEN 'one_on_one'
                        WHEN summary ILIKE '%sales%' OR summary ILIKE '%customer%' THEN 'sales'
                        WHEN summary ILIKE '%product%' OR summary ILIKE '%dev%' THEN 'product'
                        WHEN summary ILIKE '%ops%' OR summary ILIKE '%sync%' THEN 'operations'
                        WHEN meeting_type = 'personal' THEN 'personal_time'
                        ELSE 'general_meeting'
                    END AS topic,
                    event_date,
                    duration_minutes
                FROM v_events_norm
                WHERE meeting_type NOT IN ('cancelled', 'declined')
            ),
            transitions AS (
                SELECT 
                    m1.topic AS from_topic,
                    m2.topic AS to_topic,
                    m1.end_time AS transition_start,
                    m2.start_time AS transition_end,
                    EXTRACT(epoch FROM (m2.start_time - m1.end_time))/60 AS transition_minutes,
                    m1.duration_minutes AS from_duration,
                    m2.duration_minutes AS to_duration
                FROM meeting_sequences m1
                JOIN meeting_sequences m2 ON 
                    m1.event_date = m2.event_date AND
                    m2.start_time > m1.end_time AND
                    m2.start_time <= m1.end_time + INTERVAL '2 hours'
                WHERE m1.topic != m2.topic  -- Only topic changes
            )
            SELECT 
                from_topic,
                to_topic,
                COUNT(*) AS transition_count,
                ROUND(AVG(transition_minutes), 1) AS avg_transition_minutes,
                ROUND(AVG(from_duration), 1) AS avg_from_duration,
                ROUND(AVG(to_duration), 1) AS avg_to_duration,
                -- Context switching cost analysis
                SUM(CASE WHEN transition_minutes < 5 THEN 1 ELSE 0 END) AS rapid_transitions,
                ROUND(
                    (SUM(CASE WHEN transition_minutes < 5 THEN 1 ELSE 0 END)::DECIMAL / COUNT(*)) * 100, 
                    1
                ) AS rapid_transition_pct
            FROM transitions
            GROUP BY from_topic, to_topic
            HAVING COUNT(*) >= 2  -- Only meaningful patterns
            ORDER BY transition_count DESC
        """)
        
        # v_offhours: Off-hours meeting analysis
        self.connection.execute("""
            CREATE OR REPLACE VIEW v_offhours AS
            SELECT 
                event_id,
                summary,
                start_time,
                duration_minutes,
                start_hour,
                day_of_week,
                meeting_type,
                attendee_count,
                has_external_attendees,
                -- Classify off-hours type
                CASE 
                    WHEN start_hour < 9 THEN 'early_morning'
                    WHEN start_hour >= 18 THEN 'evening'
                    WHEN day_of_week IN (0, 6) THEN 'weekend'  -- Sunday=0, Saturday=6
                    ELSE 'other'
                END AS offhours_type,
                -- Calculate off-hours intensity
                CASE 
                    WHEN start_hour <= 7 OR start_hour >= 20 THEN 'extreme'
                    WHEN start_hour <= 8 OR start_hour >= 18 THEN 'moderate'
                    WHEN day_of_week IN (0, 6) THEN 'weekend'
                    ELSE 'mild'
                END AS intensity_level
            FROM v_events_norm
            WHERE time_classification = 'off_hours'
              OR day_of_week IN (0, 6)
            ORDER BY start_time
        """)
        
        # v_series_audit: Recurring meeting efficiency analysis
        self.connection.execute("""
            CREATE OR REPLACE VIEW v_series_audit AS
            WITH recurring_series AS (
                SELECT 
                    series_id,
                    summary,
                    COUNT(*) AS instance_count,
                    MIN(start_time) AS first_occurrence,
                    MAX(start_time) AS last_occurrence,
                    AVG(duration_minutes) AS avg_duration,
                    AVG(attendee_count) AS avg_attendees,
                    SUM(duration_minutes) AS total_minutes,
                    -- Consistency metrics
                    STDDEV(duration_minutes) AS duration_variance,
                    STDDEV(attendee_count) AS attendee_variance,
                    -- Calculate frequency (instances per week)
                    ROUND(
                        COUNT(*)::DECIMAL / 
                        GREATEST(
                            EXTRACT(epoch FROM (MAX(start_time) - MIN(start_time))) / (7 * 24 * 3600),
                            1
                        ),
                        2
                    ) AS frequency_per_week
                FROM v_events_norm
                WHERE is_recurring = true
                  AND meeting_type IN ('one_on_one', 'small_meeting', 'large_meeting')
                GROUP BY series_id, summary
                HAVING COUNT(*) >= 3  -- At least 3 instances to analyze
            )
            SELECT 
                series_id,
                summary,
                instance_count,
                first_occurrence,
                last_occurrence,
                ROUND(avg_duration, 1) AS avg_duration_minutes,
                ROUND(avg_attendees, 1) AS avg_attendees,
                ROUND(total_minutes / 60.0, 1) AS total_hours,
                frequency_per_week,
                -- Efficiency scoring
                ROUND(duration_variance, 1) AS duration_variance,
                CASE 
                    WHEN duration_variance <= 5 THEN 'consistent'
                    WHEN duration_variance <= 15 THEN 'variable'
                    ELSE 'inconsistent'
                END AS consistency_rating,
                -- ROI indicators
                ROUND(total_minutes / instance_count, 1) AS minutes_per_instance,
                CASE 
                    WHEN avg_duration > 60 AND avg_attendees > 5 THEN 'high_cost'
                    WHEN avg_duration > 30 AND avg_attendees > 3 THEN 'medium_cost'
                    ELSE 'low_cost'
                END AS cost_category
            FROM recurring_series
            ORDER BY total_minutes DESC
        """)
        
        print("✓ Created v_transition_map, v_offhours, and v_series_audit views")
        
    def create_advanced_metrics_views(self):
        """Create advanced productivity and goal tracking views."""
        
        print("Creating advanced metrics views...")
        
        # v_goal_attention_share: Inferred goal attention distribution
        self.connection.execute("""
            CREATE OR REPLACE VIEW v_goal_attention_share AS
            WITH goal_mapping AS (
                SELECT 
                    event_id,
                    summary,
                    duration_minutes,
                    attendee_count,
                    meeting_type,
                    -- Map meetings to business goals
                    CASE 
                        WHEN summary ILIKE '%revenue%' OR summary ILIKE '%sales%' OR summary ILIKE '%customer%' 
                        THEN 'revenue_growth'
                        
                        WHEN summary ILIKE '%product%' OR summary ILIKE '%feature%' OR summary ILIKE '%development%' 
                        THEN 'product_development'
                        
                        WHEN summary ILIKE '%team%' OR summary ILIKE '%hire%' OR summary ILIKE '%1:1%' OR summary ILIKE '%performance%'
                        THEN 'team_development'
                        
                        WHEN summary ILIKE '%strategy%' OR summary ILIKE '%planning%' OR summary ILIKE '%roadmap%' OR summary ILIKE '%exec%'
                        THEN 'strategic_planning'
                        
                        WHEN summary ILIKE '%ops%' OR summary ILIKE '%process%' OR summary ILIKE '%efficiency%'
                        THEN 'operational_excellence'
                        
                        WHEN summary ILIKE '%partner%' OR summary ILIKE '%external%' OR summary ILIKE '%vendor%'
                        THEN 'partnerships'
                        
                        WHEN meeting_type = 'personal' OR summary ILIKE '%lunch%' OR summary ILIKE '%coffee%'
                        THEN 'personal_development'
                        
                        ELSE 'general_business'
                    END AS business_goal,
                    
                    -- Weight meetings by strategic importance (attendee count proxy)
                    CASE 
                        WHEN attendee_count >= 5 THEN duration_minutes * 1.5  -- High-impact meetings
                        WHEN attendee_count >= 2 THEN duration_minutes * 1.2  -- Standard meetings  
                        ELSE duration_minutes  -- Individual work
                    END AS weighted_minutes
                    
                FROM v_events_norm
                WHERE meeting_type NOT IN ('cancelled', 'declined')
            )
            SELECT 
                business_goal,
                COUNT(*) AS meeting_count,
                SUM(duration_minutes) AS total_minutes,
                SUM(weighted_minutes) AS weighted_minutes,
                ROUND(SUM(duration_minutes) / 60.0, 1) AS total_hours,
                -- Calculate attention share percentages
                ROUND(
                    (SUM(duration_minutes)::DECIMAL / SUM(SUM(duration_minutes)) OVER ()) * 100, 
                    2
                ) AS time_share_pct,
                ROUND(
                    (SUM(weighted_minutes)::DECIMAL / SUM(SUM(weighted_minutes)) OVER ()) * 100, 
                    2
                ) AS weighted_share_pct,
                -- Average meeting characteristics
                ROUND(AVG(duration_minutes), 1) AS avg_meeting_duration,
                ROUND(AVG(attendee_count), 1) AS avg_attendees_per_meeting
            FROM goal_mapping
            GROUP BY business_goal
            ORDER BY weighted_minutes DESC
        """)
        
        # v_delegation_index: Meetings organized by others vs self
        self.connection.execute("""
            CREATE OR REPLACE VIEW v_delegation_index AS
            WITH delegation_analysis AS (
                SELECT 
                    organizer_self,
                    meeting_type,
                    COUNT(*) AS meeting_count,
                    SUM(duration_minutes) AS total_minutes,
                    AVG(duration_minutes) AS avg_duration,
                    AVG(attendee_count) AS avg_attendees
                FROM v_events_norm
                WHERE meeting_type IN ('one_on_one', 'small_meeting', 'large_meeting')
                GROUP BY organizer_self, meeting_type
            )
            SELECT 
                organizer_self,
                meeting_type,
                meeting_count,
                total_minutes,
                ROUND(avg_duration, 1) AS avg_duration,
                ROUND(avg_attendees, 1) AS avg_attendees,
                -- Calculate delegation metrics
                ROUND(
                    total_minutes::DECIMAL / SUM(total_minutes) OVER () * 100, 
                    2
                ) AS time_share_pct
            FROM delegation_analysis
            
            UNION ALL
            
            -- Summary row
            SELECT 
                NULL AS organizer_self,
                'SUMMARY' AS meeting_type,
                SUM(meeting_count) AS meeting_count,
                SUM(total_minutes) AS total_minutes,
                0 AS avg_duration,
                0 AS avg_attendees,
                -- Overall delegation ratio
                ROUND(
                    SUM(CASE WHEN organizer_self = false THEN total_minutes ELSE 0 END)::DECIMAL /
                    SUM(total_minutes) * 100,
                    2
                ) AS delegation_ratio_pct
            FROM delegation_analysis
            
            ORDER BY organizer_self DESC NULLS LAST, meeting_type
        """)
        
        # v_bypass_rate: Direct vs hierarchical meeting patterns
        self.connection.execute("""
            CREATE OR REPLACE VIEW v_bypass_rate AS
            WITH hierarchy_analysis AS (
                SELECT 
                    e.event_id,
                    e.summary,
                    e.duration_minutes,
                    e.attendee_count,
                    e.organizer_email,
                    -- Count internal participants (biorender.com)
                    COUNT(CASE WHEN p.domain = 'biorender.com' THEN 1 END) AS internal_attendees,
                    -- Detect potential hierarchy bypassing patterns
                    CASE 
                        WHEN e.summary ILIKE '%skip%' OR e.summary ILIKE '%bypass%' THEN 'explicit_bypass'
                        WHEN e.attendee_count <= 3 AND e.summary ILIKE '%urgent%' THEN 'urgent_direct'
                        WHEN e.attendee_count = 2 AND e.organizer_email != 'ryan@biorender.com' THEN 'peer_direct'
                        WHEN e.attendee_count >= 5 AND e.summary ILIKE '%all hands%' THEN 'broadcast'
                        ELSE 'standard_hierarchy'
                    END AS meeting_pattern
                FROM events e
                LEFT JOIN participants p ON e.event_id = p.event_id
                WHERE e.meeting_type IN ('one_on_one', 'small_meeting', 'large_meeting')
                  AND e.status = 'confirmed'
                GROUP BY e.event_id, e.summary, e.duration_minutes, e.attendee_count, e.organizer_email
            )
            SELECT 
                meeting_pattern,
                COUNT(*) AS meeting_count,
                SUM(duration_minutes) AS total_minutes,
                ROUND(AVG(duration_minutes), 1) AS avg_duration,
                ROUND(AVG(attendee_count), 1) AS avg_attendees,
                ROUND(AVG(internal_attendees), 1) AS avg_internal_attendees,
                -- Calculate bypass rate
                ROUND(
                    COUNT(*)::DECIMAL / SUM(COUNT(*)) OVER () * 100, 
                    2
                ) AS pattern_percentage,
                -- Efficiency metrics
                ROUND(
                    SUM(duration_minutes)::DECIMAL / COUNT(*), 
                    1
                ) AS minutes_per_meeting
            FROM hierarchy_analysis
            GROUP BY meeting_pattern
            ORDER BY meeting_count DESC
        """)
        
        print("✓ Created v_goal_attention_share, v_delegation_index, and v_bypass_rate views")
        
    def create_summary_views(self):
        """Create high-level summary and KPI views."""
        
        print("Creating summary KPI views...")
        
        # v_calendar_kpis: Key productivity metrics
        self.connection.execute("""
            CREATE OR REPLACE VIEW v_calendar_kpis AS
            WITH base_metrics AS (
                -- Total meeting time and counts
                SELECT 
                    COUNT(DISTINCT event_id) AS total_meetings,
                    SUM(duration_minutes) AS total_meeting_minutes,
                    COUNT(DISTINCT event_date) AS active_days,
                    MIN(start_time) AS period_start,
                    MAX(start_time) AS period_end
                FROM v_events_norm
                WHERE meeting_type IN ('one_on_one', 'small_meeting', 'large_meeting')
            ),
            deep_work_metrics AS (
                -- Deep work availability
                SELECT 
                    COUNT(*) AS deep_work_blocks,
                    SUM(business_hours_minutes) AS total_deep_work_minutes
                FROM v_deep_work_blocks
            ),
            b2b_metrics AS (
                -- Back-to-back meeting metrics
                SELECT 
                    COUNT(*) AS total_transitions,
                    SUM(adequate_buffer) AS adequately_buffered,
                    AVG(gap_minutes) AS avg_buffer_minutes
                FROM v_b2b
            )
            SELECT 
                -- Period information
                b.period_start,
                b.period_end,
                ROUND(
                    EXTRACT(epoch FROM (b.period_end - b.period_start)) / (24 * 3600), 
                    0
                ) AS analysis_days,
                
                -- Meeting volume metrics
                b.total_meetings,
                b.active_days,
                ROUND(b.total_meetings::DECIMAL / b.active_days, 1) AS avg_meetings_per_day,
                ROUND(b.total_meeting_minutes / 60.0, 1) AS total_meeting_hours,
                ROUND(b.total_meeting_minutes::DECIMAL / b.active_days / 60, 1) AS avg_hours_per_day,
                
                -- Deep work metrics
                d.deep_work_blocks,
                ROUND(d.total_deep_work_minutes / 60.0, 1) AS deep_work_hours,
                ROUND(
                    d.total_deep_work_minutes::DECIMAL / (d.total_deep_work_minutes + b.total_meeting_minutes) * 100,
                    1
                ) AS deep_work_ratio_pct,
                
                -- Meeting efficiency metrics
                bb.total_transitions,
                bb.adequately_buffered,
                ROUND(
                    bb.adequately_buffered::DECIMAL / GREATEST(bb.total_transitions, 1) * 100,
                    1
                ) AS buffer_coverage_pct,
                ROUND(bb.avg_buffer_minutes, 1) AS avg_buffer_minutes,
                
                -- Productivity scoring (0-100 scale)
                ROUND(
                    (
                        -- Deep work component (target 40%, weight 40%)
                        LEAST(d.total_deep_work_minutes::DECIMAL / (d.total_deep_work_minutes + b.total_meeting_minutes) / 0.4, 1) * 40 +
                        -- Buffer coverage component (target 80%, weight 30%)
                        LEAST(bb.adequately_buffered::DECIMAL / GREATEST(bb.total_transitions, 1) / 0.8, 1) * 30 +
                        -- Meeting load component (target max 6 hours/day, weight 30%)
                        (1 - LEAST((b.total_meeting_minutes::DECIMAL / b.active_days / 60) / 6, 1)) * 30
                    ),
                    1
                ) AS productivity_score
                
            FROM base_metrics b
            CROSS JOIN deep_work_metrics d
            CROSS JOIN b2b_metrics bb
        """)
        
        print("✓ Created v_calendar_kpis summary view")
        
    def create_all_views(self):
        """Create all analytical views."""
        print("Creating Calendar Analytics Views")
        print("=" * 40)
        
        self.connect_db()
        
        # Create views in dependency order
        self.create_core_views()
        self.create_meeting_pattern_views()
        self.create_collaboration_views()
        self.create_topic_analysis_views()
        self.create_productivity_views()
        self.create_advanced_metrics_views()
        self.create_summary_views()
        
        print("\n" + "=" * 40)
        print("All Calendar Analytics Views Created Successfully!")
        
        # List all created views
        views = self.connection.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_type = 'VIEW' 
              AND table_schema = 'main'
            ORDER BY table_name
        """).fetchall()
        
        print(f"\nCreated {len(views)} analytical views:")
        for view in views:
            print(f"  • {view[0]}")
            
    def close(self):
        """Close database connection."""
        if self.connection:
            self.connection.close()

def main():
    """Main execution function."""
    db_path = "/Users/david.campos/VibeCode/AICoS-Lab/experiments/ryan_time_analysis/data/processed/duckdb/calendar_analytics.db"
    
    creator = CalendarViewsCreator(db_path)
    
    try:
        creator.create_all_views()
    finally:
        creator.close()

if __name__ == "__main__":
    main()