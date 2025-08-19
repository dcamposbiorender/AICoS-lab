-- Phase 1 Baseline Schema
-- Establishes foundation for search, queries, and statistics
-- Compatible with existing Stage 3 data structure

-- Core message storage (FTS5 integration ready)
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL,           -- Searchable content
    source TEXT NOT NULL,            -- slack, calendar, drive, employee
    created_at TEXT NOT NULL,        -- ISO timestamp
    date TEXT NOT NULL,              -- Date for filtering (YYYY-MM-DD format)
    metadata TEXT,                   -- JSON metadata (separate from FTS5)
    person_id TEXT,                  -- Normalized person identifier
    channel_id TEXT,                 -- Channel/location identifier
    indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- FTS5 virtual table (performance optimized)
CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
    content,
    content=messages,
    content_rowid=id,
    tokenize='porter unicode61'     -- Stemming for better matching
);

-- Archive tracking table
CREATE TABLE IF NOT EXISTS archives (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT NOT NULL UNIQUE,
    source TEXT NOT NULL,
    indexed_at TEXT NOT NULL,
    record_count INTEGER DEFAULT 0,
    checksum TEXT,
    status TEXT DEFAULT 'active'
);

-- Search metadata and statistics
CREATE TABLE IF NOT EXISTS search_metadata (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at TEXT
);

-- FTS5 synchronization triggers (fixed for no recursion)
CREATE TRIGGER IF NOT EXISTS messages_ai AFTER INSERT ON messages BEGIN
    INSERT INTO messages_fts(rowid, content) 
    VALUES (new.id, new.content);
END;

CREATE TRIGGER IF NOT EXISTS messages_ad AFTER DELETE ON messages BEGIN
    INSERT INTO messages_fts(messages_fts, rowid, content) 
    VALUES('delete', old.id, old.content);
END;

CREATE TRIGGER IF NOT EXISTS messages_au AFTER UPDATE ON messages BEGIN
    INSERT INTO messages_fts(messages_fts, rowid, content) 
    VALUES('delete', old.id, old.content);
    INSERT INTO messages_fts(rowid, content) 
    VALUES (new.id, new.content);
END;

-- Basic indexes for core functionality
CREATE INDEX IF NOT EXISTS idx_archives_source ON archives(source);
CREATE INDEX IF NOT EXISTS idx_archives_indexed_at ON archives(indexed_at);
CREATE INDEX IF NOT EXISTS idx_messages_source ON messages(source);
CREATE INDEX IF NOT EXISTS idx_messages_date ON messages(date);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at);