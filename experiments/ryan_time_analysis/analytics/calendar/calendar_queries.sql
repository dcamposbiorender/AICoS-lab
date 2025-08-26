-- Calendar Analytics SQL Queries
-- Generated on: 2025-08-19T20:46:37.867838
-- Database: /Users/david.campos/VibeCode/AICoS-Lab/experiments/ryan_time_analysis/data/processed/duckdb/calendar_analytics.db
-- 
-- This file contains all the analytical views and sample queries
-- for comprehensive calendar analysis using DuckDB.

-- ===========================================
-- ANALYTICAL VIEWS AVAILABLE
-- ===========================================

-- Total Views Created: 16

-- • v_b2b
-- • v_bypass_rate
-- • v_calendar_kpis
-- • v_collab_hhi
-- • v_collab_minutes
-- • v_day_load
-- • v_deep_work_blocks
-- • v_delegation_index
-- • v_events_norm
-- • v_goal_attention_share
-- • v_offhours
-- • v_series_audit
-- • v_short_meetings
-- • v_topic_entropy
-- • v_topic_minutes
-- • v_transition_map

-- View Descriptions:
-- v_events_norm: Normalized events with time classifications
-- v_day_load: Day-of-week × hour meeting density heatmap
-- v_b2b: Back-to-back meeting transitions and buffer analysis
-- v_short_meetings: Analysis of meetings ≤15 minutes
-- v_deep_work_blocks: Uninterrupted time blocks ≥90 minutes
-- v_collab_minutes: Collaboration time by partner and domain
-- v_collab_hhi: Collaboration concentration (HHI) metrics
-- v_topic_minutes: Meeting time distribution by inferred topic
-- v_topic_entropy: Topic diversity and distribution analysis
-- v_transition_map: Meeting-to-meeting topic transitions
-- v_offhours: Off-hours meeting patterns and impact
-- v_series_audit: Recurring meeting efficiency analysis
-- v_goal_attention_share: Business goal attention distribution
-- v_delegation_index: Self-organized vs delegated meetings
-- v_bypass_rate: Hierarchy bypass and direct communication
-- v_calendar_kpis: Executive summary metrics dashboard


-- ===========================================
-- SAMPLE ANALYSIS QUERIES
-- ===========================================

-- Executive Summary Query
-- Get overall calendar health metrics
SELECT 
    total_meetings,
    avg_meetings_per_day,
    avg_hours_per_day,
    deep_work_ratio_pct,
    buffer_coverage_pct,
    productivity_score
FROM v_calendar_kpis;

-- Weekly Pattern Analysis
-- Identify peak meeting times and quiet periods
SELECT 
    CASE day_of_week
        WHEN 0 THEN 'Sunday'
        WHEN 1 THEN 'Monday' 
        WHEN 2 THEN 'Tuesday'
        WHEN 3 THEN 'Wednesday'
        WHEN 4 THEN 'Thursday'
        WHEN 5 THEN 'Friday'
        WHEN 6 THEN 'Saturday'
    END as day_name,
    start_hour,
    meetings_per_day,
    total_minutes
FROM v_day_load
WHERE meetings_per_day > 0
ORDER BY meetings_per_day DESC
LIMIT 20;

-- Top Time Consumers
-- Find meetings and topics consuming most time
SELECT 
    topic_category,
    total_hours,
    time_share_pct,
    meeting_count,
    avg_duration
FROM v_topic_minutes
ORDER BY total_hours DESC
LIMIT 10;

-- Collaboration Network Analysis
-- Identify key collaboration partners
SELECT 
    participant_email,
    domain,
    total_minutes / 60.0 as total_hours,
    meetings_count,
    CASE WHEN is_internal = 1 THEN 'Internal' ELSE 'External' END as partner_type
FROM v_collab_minutes
WHERE total_minutes >= 120  -- At least 2 hours
ORDER BY total_minutes DESC
LIMIT 15;

-- Deep Work Opportunities
-- Find available blocks for focused work
SELECT 
    event_date,
    block_start,
    block_end,
    business_hours_minutes / 60.0 as available_hours,
    deep_work_quality,
    time_period
FROM v_deep_work_blocks
WHERE business_hours_minutes >= 90  -- At least 1.5 hours
ORDER BY event_date, block_start;

-- Meeting Efficiency Analysis
-- Identify potential optimization opportunities
SELECT 
    series_id,
    summary,
    instance_count,
    frequency_per_week,
    total_hours,
    avg_duration_minutes,
    cost_category,
    consistency_rating
FROM v_series_audit
WHERE total_hours >= 2  -- Focus on significant time investments
ORDER BY total_hours DESC;

-- Back-to-Back Meeting Stress
-- Analyze meeting transitions and buffer adequacy
SELECT 
    transition_type,
    COUNT(*) as transition_count,
    AVG(gap_minutes) as avg_gap_minutes,
    ROUND(AVG(adequate_buffer) * 100, 1) as adequate_buffer_pct
FROM v_b2b
GROUP BY transition_type
ORDER BY transition_count DESC;

-- Context Switching Analysis
-- Measure topic transition frequency and cost
SELECT 
    from_topic,
    to_topic,
    transition_count,
    avg_transition_minutes,
    rapid_transition_pct
FROM v_transition_map
WHERE transition_count >= 3
ORDER BY rapid_transition_pct DESC;

-- Off-Hours Work Impact
-- Assess work-life balance implications
SELECT 
    offhours_type,
    COUNT(*) as meeting_count,
    SUM(duration_minutes) / 60.0 as total_hours,
    AVG(duration_minutes) as avg_duration,
    intensity_level
FROM v_offhours
GROUP BY offhours_type, intensity_level
ORDER BY total_hours DESC;

-- Goal Attention Distribution
-- Strategic vs operational focus analysis
SELECT 
    business_goal,
    total_hours,
    weighted_share_pct,
    meeting_count,
    avg_attendees_per_meeting
FROM v_goal_attention_share
ORDER BY weighted_share_pct DESC;

-- Meeting Size vs Duration Efficiency
-- Identify potential over-engineered meetings
SELECT 
    attendee_count,
    duration_category,
    COUNT(*) as meeting_count,
    AVG(duration_minutes) as avg_duration,
    meeting_type
FROM v_events_norm
WHERE meeting_type IN ('small_meeting', 'large_meeting')
GROUP BY attendee_count, duration_category, meeting_type
HAVING COUNT(*) >= 5
ORDER BY attendee_count, avg_duration DESC;

-- Daily Productivity Patterns
-- Compare different types of days
SELECT 
    event_date,
    COUNT(*) as total_events,
    SUM(CASE WHEN meeting_type IN ('one_on_one', 'small_meeting', 'large_meeting') THEN duration_minutes ELSE 0 END) / 60.0 as meeting_hours,
    SUM(CASE WHEN meeting_type = 'personal' THEN duration_minutes ELSE 0 END) / 60.0 as personal_hours,
    SUM(CASE WHEN meeting_type = 'blocked_time' THEN duration_minutes ELSE 0 END) / 60.0 as blocked_hours
FROM v_events_norm
GROUP BY event_date
ORDER BY meeting_hours DESC;

-- Recurring Meeting ROI Analysis
-- Evaluate regular commitments for optimization potential
SELECT 
    summary,
    frequency_per_week,
    avg_duration_minutes,
    avg_attendees,
    total_hours,
    (total_hours * avg_attendees) as person_hours_invested,
    consistency_rating,
    cost_category
FROM v_series_audit
WHERE frequency_per_week >= 0.5  -- Regular meetings
ORDER BY person_hours_invested DESC;

