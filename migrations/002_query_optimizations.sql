-- Agent A Query Engine Optimizations
-- Indexes and views to support time, person, and structured queries

-- Schema version tracking table (ensure exists)
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at TEXT DEFAULT CURRENT_TIMESTAMP,
    description TEXT,
    checksum TEXT
);

-- Time-based query optimization
CREATE INDEX IF NOT EXISTS idx_messages_created_at_source ON messages(created_at, source);
CREATE INDEX IF NOT EXISTS idx_messages_date_person ON messages(date, person_id);

-- Person query optimization  
CREATE INDEX IF NOT EXISTS idx_messages_person_created ON messages(person_id, created_at);
CREATE INDEX IF NOT EXISTS idx_messages_person_date ON messages(person_id, date);

-- Structured pattern query optimization
CREATE INDEX IF NOT EXISTS idx_messages_content_prefix ON messages(
    substr(content, 1, 100)  -- Index first 100 chars for pattern matching
);

-- Channel activity optimization
CREATE INDEX IF NOT EXISTS idx_messages_channel_date ON messages(channel_id, date);

-- Composite indexes for complex queries
CREATE INDEX IF NOT EXISTS idx_messages_source_date_person ON messages(source, date, person_id);

-- Views for common query patterns
CREATE VIEW IF NOT EXISTS daily_activity AS
SELECT 
    date as activity_date,
    source,
    person_id,
    COUNT(*) as activity_count,
    COUNT(DISTINCT channel_id) as channels_active
FROM messages 
GROUP BY date, source, person_id;

-- Time range optimization view
CREATE VIEW IF NOT EXISTS weekly_activity AS
SELECT 
    strftime('%Y-%W', date) as week,
    source,
    person_id,
    COUNT(*) as activity_count,
    MIN(date) as week_start,
    MAX(date) as week_end
FROM messages
GROUP BY strftime('%Y-%W', date), source, person_id;

-- Record version 2
INSERT OR REPLACE INTO schema_migrations (version, description, checksum) 
VALUES (2, 'Agent A query engine optimizations', 'sha256:agent-a-opt');