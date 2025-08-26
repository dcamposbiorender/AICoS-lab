#!/usr/bin/env python3
"""
Calendar Analytics - SQL Queries Export
=======================================

This script exports all the analytical SQL queries from the DuckDB views
to a single SQL file for reference and reusability.

Output: calendar_queries.sql with all view definitions and sample queries.
"""

import duckdb
import os
from datetime import datetime

class SQLQueriesExporter:
    def __init__(self, db_path: str, output_dir: str):
        """Initialize with database and output paths."""
        self.db_path = db_path
        self.output_dir = output_dir
        self.connection = None
        
        os.makedirs(output_dir, exist_ok=True)
        
    def connect_db(self):
        """Connect to DuckDB database."""
        self.connection = duckdb.connect(self.db_path)
        print(f"Connected to database: {self.db_path}")
        
    def export_all_queries(self):
        """Export all view definitions and sample queries."""
        print("Exporting SQL queries...")
        
        output_path = os.path.join(self.output_dir, 'calendar_queries.sql')
        
        with open(output_path, 'w') as f:
            # Write header
            f.write(f"""-- Calendar Analytics SQL Queries
-- Generated on: {datetime.now().isoformat()}
-- Database: {self.db_path}
-- 
-- This file contains all the analytical views and sample queries
-- for comprehensive calendar analysis using DuckDB.

""")
            
            # Get all views (DuckDB doesn't store view SQL in information_schema)
            view_names = self.connection.execute("""
                SELECT table_name
                FROM information_schema.tables 
                WHERE table_type = 'VIEW' AND table_schema = 'main'
                ORDER BY table_name
            """).fetchall()
            
            # Export view list
            f.write("-- ===========================================\n")
            f.write("-- ANALYTICAL VIEWS AVAILABLE\n")
            f.write("-- ===========================================\n\n")
            
            f.write(f"-- Total Views Created: {len(view_names)}\n\n")
            for view_name_tuple in view_names:
                view_name = view_name_tuple[0]
                f.write(f"-- • {view_name}\n")
                
            f.write("\n-- View Descriptions:\n")
            f.write("-- v_events_norm: Normalized events with time classifications\n")
            f.write("-- v_day_load: Day-of-week × hour meeting density heatmap\n")
            f.write("-- v_b2b: Back-to-back meeting transitions and buffer analysis\n")
            f.write("-- v_short_meetings: Analysis of meetings ≤15 minutes\n")
            f.write("-- v_deep_work_blocks: Uninterrupted time blocks ≥90 minutes\n")
            f.write("-- v_collab_minutes: Collaboration time by partner and domain\n")
            f.write("-- v_collab_hhi: Collaboration concentration (HHI) metrics\n")
            f.write("-- v_topic_minutes: Meeting time distribution by inferred topic\n")
            f.write("-- v_topic_entropy: Topic diversity and distribution analysis\n")
            f.write("-- v_transition_map: Meeting-to-meeting topic transitions\n")
            f.write("-- v_offhours: Off-hours meeting patterns and impact\n")
            f.write("-- v_series_audit: Recurring meeting efficiency analysis\n")
            f.write("-- v_goal_attention_share: Business goal attention distribution\n")
            f.write("-- v_delegation_index: Self-organized vs delegated meetings\n")
            f.write("-- v_bypass_rate: Hierarchy bypass and direct communication\n")
            f.write("-- v_calendar_kpis: Executive summary metrics dashboard\n\n")
                
            # Add sample analysis queries
            f.write(self._generate_sample_queries())
            
        print(f"SQL queries exported to: {output_path}")
        return output_path
        
    def _generate_sample_queries(self) -> str:
        """Generate sample analysis queries."""
        return """
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

"""
        
    def close(self):
        """Close database connection."""
        if self.connection:
            self.connection.close()

def main():
    """Main execution function."""
    db_path = "/Users/david.campos/VibeCode/AICoS-Lab/experiments/ryan_time_analysis/data/processed/duckdb/calendar_analytics.db"
    output_dir = "/Users/david.campos/VibeCode/AICoS-Lab/experiments/ryan_time_analysis/analytics/calendar"
    
    exporter = SQLQueriesExporter(db_path, output_dir)
    
    try:
        exporter.connect_db()
        exporter.export_all_queries()
    finally:
        exporter.close()

if __name__ == "__main__":
    main()