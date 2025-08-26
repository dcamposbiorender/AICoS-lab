-- Agent B Statistics & Calendar Optimization
-- Views and aggregations for activity analysis

-- Schema version tracking table (ensure exists)
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at TEXT DEFAULT CURRENT_TIMESTAMP,
    description TEXT,
    checksum TEXT
);

-- Channel activity aggregation
CREATE VIEW IF NOT EXISTS channel_stats AS
SELECT 
    channel_id,
    source,
    COUNT(*) as message_count,
    COUNT(DISTINCT person_id) as unique_participants,
    MIN(created_at) as first_activity,
    MAX(created_at) as last_activity,
    MIN(date) as first_activity_date,
    MAX(date) as last_activity_date
FROM messages 
WHERE channel_id IS NOT NULL
GROUP BY channel_id, source;

-- Person activity aggregation
CREATE VIEW IF NOT EXISTS person_stats AS  
SELECT
    person_id,
    source,
    COUNT(*) as total_activity,
    COUNT(DISTINCT channel_id) as channels_active,
    COUNT(DISTINCT date) as active_days,
    MIN(date) as first_activity_date,
    MAX(date) as last_activity_date
FROM messages
WHERE person_id IS NOT NULL
GROUP BY person_id, source;

-- Temporal activity patterns (for Agent B statistics)
CREATE VIEW IF NOT EXISTS temporal_patterns AS
SELECT
    date as activity_date,
    strftime('%H', created_at) as hour_of_day,
    strftime('%w', created_at) as day_of_week,
    source,
    COUNT(*) as activity_count
FROM messages
GROUP BY date, strftime('%H', created_at), strftime('%w', created_at), source;

-- Daily summary view for quick statistics
CREATE VIEW IF NOT EXISTS daily_summary AS
SELECT
    date as summary_date,
    source,
    COUNT(*) as total_messages,
    COUNT(DISTINCT person_id) as active_people,
    COUNT(DISTINCT channel_id) as active_channels,
    MIN(created_at) as first_activity,
    MAX(created_at) as last_activity
FROM messages
GROUP BY date, source;

-- Weekly rollup for trending analysis
CREATE VIEW IF NOT EXISTS weekly_summary AS
SELECT
    strftime('%Y-%W', date) as week_number,
    strftime('%Y', date) as year,
    MIN(date) as week_start,
    MAX(date) as week_end,
    source,
    COUNT(*) as total_messages,
    COUNT(DISTINCT person_id) as active_people,
    COUNT(DISTINCT channel_id) as active_channels,
    AVG(
        CAST(strftime('%H', created_at) AS INTEGER)
    ) as avg_hour_of_activity
FROM messages
GROUP BY strftime('%Y-%W', date), source;

-- Cross-source activity correlation view
CREATE VIEW IF NOT EXISTS cross_source_activity AS
SELECT
    date as activity_date,
    person_id,
    SUM(CASE WHEN source = 'slack' THEN 1 ELSE 0 END) as slack_messages,
    SUM(CASE WHEN source = 'calendar' THEN 1 ELSE 0 END) as calendar_events,
    SUM(CASE WHEN source = 'drive' THEN 1 ELSE 0 END) as drive_activities,
    COUNT(*) as total_activities
FROM messages
WHERE person_id IS NOT NULL
GROUP BY date, person_id;

-- Performance indexes for statistics views
CREATE INDEX IF NOT EXISTS idx_messages_date_source ON messages(date, source);
CREATE INDEX IF NOT EXISTS idx_messages_week_source ON messages(strftime('%Y-%W', date), source);
CREATE INDEX IF NOT EXISTS idx_messages_hour ON messages(strftime('%H', created_at));

-- Record version 3
INSERT OR REPLACE INTO schema_migrations (version, description, checksum) 
VALUES (3, 'Agent B statistics and calendar views', 'sha256:agent-b-stats');