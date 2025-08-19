-- Agent A Query Engine Optimizations
-- Indexes and views to support time, person, and structured queries
-- Performance optimizations for Phase 1 query requirements

-- Time-based query optimization (compound indexes)
CREATE INDEX IF NOT EXISTS idx_messages_created_at_source ON messages(created_at, source);
CREATE INDEX IF NOT EXISTS idx_messages_date_person ON messages(date, person_id);
CREATE INDEX IF NOT EXISTS idx_messages_date_source ON messages(date, source);

-- Person query optimization  
CREATE INDEX IF NOT EXISTS idx_messages_person_created ON messages(person_id, created_at);
CREATE INDEX IF NOT EXISTS idx_messages_person_source ON messages(person_id, source);

-- Structured pattern query optimization
CREATE INDEX IF NOT EXISTS idx_messages_content_prefix ON messages(
    CASE 
        WHEN length(content) > 50 THEN substr(content, 1, 50)
        ELSE content 
    END
);

-- Channel/location based queries
CREATE INDEX IF NOT EXISTS idx_messages_channel_created ON messages(channel_id, created_at);
CREATE INDEX IF NOT EXISTS idx_messages_channel_source ON messages(channel_id, source);

-- Views for common query patterns (Agent A requirements)
CREATE VIEW IF NOT EXISTS daily_activity AS
SELECT 
    date(created_at) as activity_date,
    source,
    person_id,
    channel_id,
    COUNT(*) as activity_count,
    MIN(created_at) as first_activity,
    MAX(created_at) as last_activity
FROM messages 
GROUP BY date(created_at), source, person_id, channel_id;

-- Time-range query optimization view
CREATE VIEW IF NOT EXISTS time_range_summary AS
SELECT 
    strftime('%Y-%m', created_at) as month,
    strftime('%Y-%W', created_at) as week, 
    date(created_at) as day,
    source,
    COUNT(*) as message_count,
    COUNT(DISTINCT person_id) as unique_people,
    COUNT(DISTINCT channel_id) as unique_channels
FROM messages
GROUP BY strftime('%Y-%m', created_at), strftime('%Y-%W', created_at), date(created_at), source;

-- Person activity summary view (optimized for Agent A person queries)
CREATE VIEW IF NOT EXISTS person_activity_summary AS
SELECT 
    person_id,
    source,
    COUNT(*) as total_messages,
    COUNT(DISTINCT date(created_at)) as active_days,
    COUNT(DISTINCT channel_id) as channels_participated,
    MIN(created_at) as first_seen,
    MAX(created_at) as last_seen,
    AVG(length(content)) as avg_message_length
FROM messages 
WHERE person_id IS NOT NULL
GROUP BY person_id, source;