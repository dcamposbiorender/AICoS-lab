-- Agent B Statistics & Calendar Optimization
-- Views and aggregations for activity analysis and calendar coordination
-- Supports basic statistics generation without AI dependencies

-- Channel activity aggregation (Agent B statistics requirement)
CREATE VIEW IF NOT EXISTS channel_stats AS
SELECT 
    channel_id,
    source,
    COUNT(*) as message_count,
    COUNT(DISTINCT person_id) as unique_participants,
    MIN(created_at) as first_activity,
    MAX(created_at) as last_activity,
    AVG(length(content)) as avg_message_length,
    COUNT(DISTINCT date(created_at)) as active_days
FROM messages 
WHERE channel_id IS NOT NULL
GROUP BY channel_id, source;

-- Person activity aggregation (enhanced for Agent B)
CREATE VIEW IF NOT EXISTS person_stats AS  
SELECT
    person_id,
    source,
    COUNT(*) as total_activity,
    COUNT(DISTINCT channel_id) as channels_active,
    COUNT(DISTINCT date(created_at)) as active_days,
    MIN(created_at) as first_activity,
    MAX(created_at) as last_activity,
    strftime('%w', created_at) as most_active_day_of_week,
    strftime('%H', created_at) as most_active_hour
FROM messages
WHERE person_id IS NOT NULL
GROUP BY person_id, source;

-- Temporal activity patterns (for calendar coordination)
CREATE VIEW IF NOT EXISTS temporal_patterns AS
SELECT
    date(created_at) as activity_date,
    strftime('%H', created_at) as hour_of_day,
    strftime('%w', created_at) as day_of_week,
    strftime('%Y-%m', created_at) as month,
    source,
    person_id,
    COUNT(*) as activity_count,
    AVG(length(content)) as avg_content_length
FROM messages
GROUP BY date(created_at), strftime('%H', created_at), strftime('%w', created_at), 
         strftime('%Y-%m', created_at), source, person_id;

-- Communication patterns (for calendar coordination insights)
CREATE VIEW IF NOT EXISTS communication_patterns AS
SELECT 
    person_id,
    channel_id,
    source,
    COUNT(*) as interaction_count,
    COUNT(DISTINCT date(created_at)) as interaction_days,
    MIN(created_at) as first_interaction,
    MAX(created_at) as last_interaction,
    -- Peak activity hours
    (SELECT strftime('%H', created_at) 
     FROM messages m2 
     WHERE m2.person_id = messages.person_id 
     GROUP BY strftime('%H', created_at) 
     ORDER BY COUNT(*) DESC 
     LIMIT 1) as peak_hour
FROM messages
WHERE person_id IS NOT NULL AND channel_id IS NOT NULL
GROUP BY person_id, channel_id, source;

-- Weekly activity summary (for calendar coordination)
CREATE VIEW IF NOT EXISTS weekly_activity AS
SELECT 
    strftime('%Y-%W', created_at) as week,
    strftime('%w', created_at) as day_of_week,
    person_id,
    source,
    COUNT(*) as daily_activity,
    COUNT(DISTINCT channel_id) as channels_used,
    MIN(strftime('%H:%M', created_at)) as first_activity_time,
    MAX(strftime('%H:%M', created_at)) as last_activity_time
FROM messages
WHERE person_id IS NOT NULL
GROUP BY strftime('%Y-%W', created_at), strftime('%w', created_at), person_id, source;

-- Cross-source activity correlation (multi-source insights)
CREATE VIEW IF NOT EXISTS cross_source_activity AS
SELECT 
    person_id,
    date(created_at) as activity_date,
    COUNT(CASE WHEN source = 'slack' THEN 1 END) as slack_activity,
    COUNT(CASE WHEN source = 'calendar' THEN 1 END) as calendar_activity,
    COUNT(CASE WHEN source = 'drive' THEN 1 END) as drive_activity,
    COUNT(DISTINCT source) as sources_used,
    COUNT(*) as total_activity
FROM messages
WHERE person_id IS NOT NULL
GROUP BY person_id, date(created_at);

-- Activity intensity scoring (for basic scheduling insights)
CREATE VIEW IF NOT EXISTS activity_intensity AS
SELECT 
    person_id,
    date(created_at) as activity_date,
    strftime('%H', created_at) as hour,
    COUNT(*) as hourly_activity,
    -- Simple intensity scoring
    CASE 
        WHEN COUNT(*) > 20 THEN 'high'
        WHEN COUNT(*) > 10 THEN 'medium'
        WHEN COUNT(*) > 0 THEN 'low'
        ELSE 'none'
    END as intensity_level
FROM messages
WHERE person_id IS NOT NULL
GROUP BY person_id, date(created_at), strftime('%H', created_at);

-- Source distribution summary (system health monitoring)
CREATE VIEW IF NOT EXISTS source_distribution AS
SELECT 
    source,
    COUNT(*) as total_records,
    COUNT(DISTINCT person_id) as unique_people,
    COUNT(DISTINCT channel_id) as unique_locations,
    COUNT(DISTINCT date(created_at)) as active_days,
    MIN(created_at) as earliest_record,
    MAX(created_at) as latest_record,
    -- Data freshness indicator
    CASE 
        WHEN julianday('now') - julianday(MAX(created_at)) < 1 THEN 'fresh'
        WHEN julianday('now') - julianday(MAX(created_at)) < 7 THEN 'recent'
        ELSE 'stale'
    END as freshness_status
FROM messages
GROUP BY source;