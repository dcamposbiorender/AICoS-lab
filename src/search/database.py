"""
SQLite FTS5 database for search functionality
Provides connection pooling, transactions, and search indexing

CRITICAL FIXES APPLIED (per user feedback):
1. FTS5 Trigger Recursion Bug Fixed - content field separate from metadata
2. Connection Pool Simplified - lab-grade single-user optimization  
3. Schema Migration Implemented - proper version handling
4. Missing Critical Index Added - idx_messages_created_at for performance
5. Batch Size Optimized - increased to 10,000 for better performance
6. Error Recovery Added - individual record error handling
"""

import sqlite3
import threading
import time
import json
import logging
import hashlib
import atexit
import weakref
from pathlib import Path
from typing import Any, Dict, List, Optional, Generator
from contextlib import contextmanager
from queue import Queue, Empty
from datetime import datetime

logger = logging.getLogger(__name__)

class DatabaseError(Exception):
    """Raised when database operations fail"""
    pass

class SearchDatabase:
    """
    SQLite FTS5 database for indexing and searching archive content
    
    CRITICAL FIXES APPLIED:
    - Fixed FTS5 trigger recursion by separating content from metadata
    - Simplified connection pooling for single-user lab deployment
    - Added missing critical index for date-range query performance
    - Implemented proper schema migration with version handling
    - Added batch processing with optimized 10,000 record batches
    - Enhanced error recovery with individual record handling
    """
    
    CURRENT_SCHEMA_VERSION = 2  # Incremented due to schema fixes
    
    def __init__(self, db_path: str = "search.db", pool_size: int = 3):
        """
        Initialize search database with critical fixes applied
        
        Args:
            db_path: Path to SQLite database file
            pool_size: Connection pool size (simplified for lab use)
        """
        self.db_path = Path(db_path)
        self.pool_size = pool_size
        self.pool = Queue(maxsize=pool_size)
        self._pool_lock = threading.Lock()
        self._thread_local = threading.local()
        self._active_connections = set()  # Track all connections
        self._cleanup_registered = False
        self._stats = {
            'connections_created': 0,
            'connections_reused': 0,
            'queries_executed': 0,
            'records_indexed': 0
        }
        
        # Register cleanup handlers
        self._register_cleanup()
        
        # Initialize database and schema with fixes
        self.initialize_schema()
        
        # Pre-populate connection pool (simplified)
        for _ in range(min(pool_size, 2)):  # Limit for lab use
            conn = self._create_connection()
            self.pool.put(conn)
    
    def initialize_schema(self):
        """Create database schema with critical fixes"""
        try:
            with self._create_connection() as conn:
                # Check current schema version
                cursor = conn.execute("PRAGMA user_version")
                current_version = cursor.fetchone()[0]
                
                if current_version == 0:
                    # Fresh database - create all tables with fixes
                    self._create_initial_schema(conn)
                    conn.execute(f"PRAGMA user_version = {self.CURRENT_SCHEMA_VERSION}")
                    logger.info(f"Created new database schema version {self.CURRENT_SCHEMA_VERSION}")
                elif current_version < self.CURRENT_SCHEMA_VERSION:
                    # Needs migration
                    self._migrate_schema(conn, current_version)
                    logger.info(f"Migrated database from version {current_version} to {self.CURRENT_SCHEMA_VERSION}")
        except Exception as e:
            raise DatabaseError(f"Failed to initialize database schema: {str(e)}")
    
    def _create_initial_schema(self, conn: sqlite3.Connection):
        """Create initial database schema with critical fixes applied"""
        
        # CRITICAL FIX #1: Separate content field from metadata to avoid recursion
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,          -- FIXED: Dedicated content field
                source TEXT NOT NULL,
                date TEXT NOT NULL,
                metadata TEXT,                  -- FIXED: Separate metadata JSON
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # CRITICAL FIX #2: FTS5 table with corrected content handling
        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
                content,
                content=messages,
                content_rowid=id,
                tokenize='porter unicode61'
            )
        """)
        
        # Archive tracking table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS archives (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT NOT NULL UNIQUE,
                source TEXT NOT NULL,
                indexed_at TEXT NOT NULL,
                record_count INTEGER DEFAULT 0,
                checksum TEXT,
                status TEXT DEFAULT 'active'
            )
        """)
        
        # Search metadata and statistics
        conn.execute("""
            CREATE TABLE IF NOT EXISTS search_metadata (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TEXT
            )
        """)
        
        # CRITICAL FIX #3: Corrected triggers - no recursion
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS messages_ai AFTER INSERT ON messages BEGIN
                INSERT INTO messages_fts(rowid, content) 
                VALUES (new.id, new.content);
            END
        """)
        
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS messages_ad AFTER DELETE ON messages BEGIN
                INSERT INTO messages_fts(messages_fts, rowid, content) 
                VALUES('delete', old.id, old.content);
            END
        """)
        
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS messages_au AFTER UPDATE ON messages BEGIN
                INSERT INTO messages_fts(messages_fts, rowid, content) 
                VALUES('delete', old.id, old.content);
                INSERT INTO messages_fts(rowid, content) 
                VALUES (new.id, new.content);
            END
        """)
        
        # CRITICAL FIX #4: Add missing critical indexes for performance
        conn.execute("CREATE INDEX IF NOT EXISTS idx_archives_source ON archives(source)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_archives_indexed_at ON archives(indexed_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_source ON messages(source)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_date ON messages(date)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at)")  # CRITICAL MISSING INDEX
        
        logger.info("Created initial search database schema with all critical fixes applied")
    
    def _migrate_schema(self, conn: sqlite3.Connection, from_version: int):
        """
        CRITICAL FIX #5: Implement actual migration logic (was empty)
        
        Migrate schema from old version with proper error handling
        """
        if from_version < 2:
            logger.info("Migrating to schema version 2: Adding critical fixes")
            
            # Add missing created_at column if it doesn't exist
            try:
                conn.execute("ALTER TABLE messages ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
            except sqlite3.OperationalError as e:
                if "duplicate column" not in str(e).lower():
                    raise
            
            # Add missing critical index
            conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at)")
            
            # Update schema version
            conn.execute(f"PRAGMA user_version = {self.CURRENT_SCHEMA_VERSION}")
            
        logger.info(f"Schema migration completed to version {self.CURRENT_SCHEMA_VERSION}")
    
    def _register_cleanup(self):
        """Register cleanup handlers for proper connection cleanup"""
        if not self._cleanup_registered:
            atexit.register(self._cleanup_all_connections)
            self._cleanup_registered = True
    
    def _cleanup_all_connections(self):
        """Clean up all active connections during shutdown"""
        logger.info("Cleaning up all database connections...")
        
        # Close pooled connections
        while not self.pool.empty():
            try:
                conn = self.pool.get_nowait()
                conn.close()
            except Empty:
                break
        
        # Close any remaining active connections
        for conn in list(self._active_connections):
            try:
                conn.close()
            except Exception:
                pass
        
        # Clear the connections set
        self._active_connections.clear()
        
        logger.info("Database connection cleanup completed")
    
    def _cleanup_thread_connection(self):
        """Clean up thread-local connection"""
        if hasattr(self._thread_local, 'connection'):
            try:
                self._thread_local.connection.close()
                logger.debug("Cleaned up thread-local connection")
            except Exception:
                pass
            finally:
                delattr(self._thread_local, 'connection')
    
    def _check_schema_version(self):
        """Check current database schema version"""
        with self._create_connection() as conn:
            cursor = conn.execute("PRAGMA user_version")
            return cursor.fetchone()[0]
    
    def _create_connection(self) -> sqlite3.Connection:
        """Create a new database connection with optimal settings and tracking"""
        try:
            conn = sqlite3.connect(
                self.db_path,
                timeout=30.0,
                check_same_thread=False  # Allow sharing between threads
            )
        except Exception as e:
            raise DatabaseError(f"Failed to create database connection: {str(e)}")
        
        # Optimize SQLite for our use case (simplified for lab)
        conn.execute("PRAGMA journal_mode=WAL")  # Better concurrency
        conn.execute("PRAGMA synchronous=NORMAL")  # Balance safety/speed
        conn.execute("PRAGMA cache_size=10000")  # 40MB cache
        conn.execute("PRAGMA temp_store=MEMORY")  # Temp tables in RAM
        conn.execute("PRAGMA foreign_keys=ON")  # Enable foreign keys
        
        # Track the connection for cleanup
        self._active_connections.add(conn)
        
        self._stats['connections_created'] += 1
        logger.debug(f"Created new database connection (total: {self._stats['connections_created']})")
        return conn
    
    def get_connection(self, timeout: float = 5.0) -> sqlite3.Connection:
        """
        CRITICAL FIX #7: Enhanced connection management with thread-local support
        
        Get connection with proper cleanup and thread safety
        """
        # Check if we have a thread-local connection that's still valid
        if hasattr(self._thread_local, 'connection'):
            try:
                conn = self._thread_local.connection
                # Test if connection is still valid
                conn.execute("SELECT 1")
                self._stats['connections_reused'] += 1
                return conn
            except Exception:
                # Connection is broken, clean it up
                self._cleanup_thread_connection()
        
        # Try to get from pool
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # Try to get from pool first
                conn = self.pool.get_nowait()
                # Test connection validity
                conn.execute("SELECT 1")
                self._stats['connections_reused'] += 1
                return conn
            except Empty:
                # Pool empty, create new connection if under reasonable limit
                if self._stats['connections_created'] < self.pool_size * 2:  # Reduced overflow
                    try:
                        return self._create_connection()
                    except Exception as e:
                        logger.warning(f"Failed to create connection: {e}")
                        time.sleep(0.05)
                        continue
                
                # Wait a bit and try again
                time.sleep(0.01)
            except Exception:
                # Connection from pool was invalid, try another
                continue
        
        raise DatabaseError(f"No database connection available within {timeout}s")
    
    def return_connection(self, conn: sqlite3.Connection):
        """Return connection to pool with proper cleanup"""
        if not conn:
            return
            
        try:
            # Check if connection is still valid
            conn.execute("SELECT 1")
            # Try to return to pool
            self.pool.put_nowait(conn)
            logger.debug("Returned connection to pool")
        except Empty:
            # Pool is full, close the connection
            conn.close()
            self._active_connections.discard(conn)
            logger.debug("Pool full, closed connection")
        except Exception:
            # Connection broken or other error, close it
            try:
                conn.close()
                # Remove from active connections tracking
                self._active_connections.discard(conn)
            except Exception:
                pass
            logger.debug("Connection invalid, closed")
    
    @contextmanager
    def connection(self):
        """
        CRITICAL FIX #8: Enhanced connection context manager with guaranteed cleanup
        
        Context manager for database connections with automatic return/cleanup
        """
        conn = self.get_connection()
        try:
            yield conn
        finally:
            self.return_connection(conn)
    
    @contextmanager
    def transaction(self):
        """
        Context manager for database transactions with automatic rollback and cleanup
        """
        conn = self.get_connection()
        try:
            conn.execute("BEGIN")
            yield conn
            conn.commit()
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass  # Connection might be broken
            raise
        finally:
            self.return_connection(conn)
    
    def index_records_batch(self, records: List[Dict], source: str, batch_size: int = 10000):
        """
        CRITICAL FIX #7: Optimized batch size and error handling
        
        Index records in batches with individual error handling
        """
        if not source:
            # If source is None, extract from first record or use default
            if records and 'source' in records[0]:
                source = records[0]['source']
            else:
                source = 'unknown'
        
        total = len(records)
        indexed = 0
        errors = []
        
        logger.info(f"Starting batch indexing of {total} records from {source}")
        
        for i in range(0, total, batch_size):
            batch = records[i:i+batch_size]
            batch_indexed, batch_errors = self._index_batch_internal(batch, source)
            indexed += batch_indexed
            errors.extend(batch_errors)
            
            # Progress indicator
            if indexed % 50000 == 0:
                logger.info(f"Indexed {indexed}/{total} records...")
        
        self._stats['records_indexed'] += indexed
        
        result = {
            'indexed': indexed,
            'errors': len(errors),
            'error_details': errors,
            'duration': 0  # Will be set by caller
        }
        
        logger.info(f"Batch indexing complete: {indexed} indexed, {len(errors)} errors")
        return result
    
    def _index_batch_internal(self, batch: List[Dict], source: str):
        """
        CRITICAL FIX #8: Individual record error handling with retry logic
        
        Internal batch indexing with per-record error recovery
        """
        indexed = 0
        errors = []
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                with self.transaction() as conn:
                    for record in batch:
                        try:
                            # Extract content using fixed method
                            content = self._extract_searchable_content(record)
                            if not content:
                                continue
                            
                            # FIXED: Use separate content field (no recursion)
                            conn.execute("""
                                INSERT INTO messages (content, source, created_at, date, metadata)
                                VALUES (?, ?, ?, ?, ?)
                            """, (
                                content,
                                source,
                                record.get('created_at', record.get('timestamp', '')),
                                self._extract_date(record),
                                json.dumps(record)
                            ))
                            
                            indexed += 1
                            
                        except Exception as e:
                            errors.append({
                                'record_id': record.get('id', 'unknown'),
                                'error': str(e),
                                'record_snippet': str(record)[:100] + '...' if len(str(record)) > 100 else str(record)
                            })
                            continue
                    
                break  # Success, exit retry loop
                    
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e) and attempt < max_retries - 1:
                    # Retry with exponential backoff
                    wait_time = 0.1 * (2 ** attempt)
                    time.sleep(wait_time)
                    logger.warning(f"Database locked, retrying in {wait_time}s (attempt {attempt + 1})")
                    continue
                else:
                    # Final retry failed or different error
                    for record in batch:
                        errors.append({
                            'record_id': record.get('id', 'unknown'),
                            'error': f"Database error: {str(e)}",
                            'record_snippet': str(record)[:100] + '...' if len(str(record)) > 100 else str(record)
                        })
                    break
        
        return indexed, errors
    
    def _extract_searchable_content(self, record: Dict[str, Any]) -> str:
        """Extract searchable text from record (improved method)"""
        content_parts = []
        
        # Common text fields (order matters - 'content' first since it's most likely)
        for field in ['content', 'text', 'message', 'title', 'subject', 'name']:
            if field in record and record[field]:
                content_parts.append(str(record[field]))
                # Don't break - we want all relevant content
        
        # Handle specific source types
        if 'attendees' in record:  # Calendar event
            attendees = record['attendees']
            if isinstance(attendees, list):
                for attendee in attendees:
                    if isinstance(attendee, dict) and 'email' in attendee:
                        content_parts.append(attendee['email'])
        
        result = ' '.join(content_parts)
        if not result:
            # Fallback: try to get any string value from the record
            for key, value in record.items():
                if isinstance(value, str) and len(value.strip()) > 0:
                    result = value.strip()
                    break
        
        return result
    
    def _extract_date(self, record: Dict[str, Any]) -> str:
        """Extract date from record for filtering (improved method)"""
        # Try various date fields
        for field in ['date', 'timestamp', 'ts', 'created_at', 'start']:
            if field in record and record[field]:
                date_val = record[field]
                
                # Handle different date formats
                if isinstance(date_val, str):
                    if 'T' in date_val:  # ISO format
                        return date_val.split('T')[0]
                    elif '-' in date_val:  # YYYY-MM-DD
                        return date_val.split(' ')[0]  # Remove time part
                
                # Handle Unix timestamp
                elif isinstance(date_val, (int, float)):
                    dt = datetime.fromtimestamp(date_val)
                    return dt.strftime('%Y-%m-%d')
        
        # Default to today
        return datetime.now().strftime('%Y-%m-%d')
    
    def search(self, query: str, source: str = None, date_range: tuple = None, 
              limit: int = 100) -> List[Dict[str, Any]]:
        """
        Search indexed content with improved query handling
        
        Args:
            query: Search query string
            source: Filter by source type
            date_range: Tuple of (start_date, end_date)
            limit: Maximum results to return
            
        Returns:
            List of matching records with relevance scores
        """
        with self.connection() as conn:
            # Build query using proper joins (FIXED: no recursion issues)
            sql_parts = ["""
                SELECT m.content, m.source, m.date, m.metadata, fts.rank
                FROM messages m
                JOIN messages_fts fts ON m.id = fts.rowid
            """]
            params = []
            where_parts = []
            
            # FTS5 query
            where_parts.append("messages_fts MATCH ?")
            params.append(query)
            
            # Source filter
            if source:
                where_parts.append("m.source = ?")
                params.append(source)
            
            # Date range filter (uses critical index)
            if date_range:
                start_date, end_date = date_range
                where_parts.append("m.date BETWEEN ? AND ?")
                params.extend([start_date, end_date])
            
            # Combine query
            if where_parts:
                sql_parts.append("WHERE " + " AND ".join(where_parts))
            
            sql_parts.append("ORDER BY fts.rank LIMIT ?")
            params.append(limit)
            
            sql = " ".join(sql_parts)
            
            cursor = conn.execute(sql, params)
            results = []
            
            for row in cursor.fetchall():
                content, source_val, date, metadata_json, rank = row
                try:
                    metadata = json.loads(metadata_json) if metadata_json else {}
                except json.JSONDecodeError:
                    metadata = {}
                
                results.append({
                    'content': content,
                    'source': source_val,
                    'date': date,
                    'metadata': metadata,
                    'relevance_score': rank
                })
            
            self._stats['queries_executed'] += 1
            return results
    
    def search_personalized(self, query: str, source: str = None, date_range: tuple = None, 
                          limit: int = 100, boost_factor: float = 1.5) -> List[Dict[str, Any]]:
        """
        Search with personalization for PRIMARY_USER
        
        Args:
            query: Search query string
            source: Filter by source type
            date_range: Tuple of (start_date, end_date)
            limit: Maximum results to return
            boost_factor: Boost factor for user-relevant results
            
        Returns:
            List of matching records with personalized relevance boosting
        """
        # Get extra results to account for boosting reordering
        raw_limit = min(limit * 2, 500)  # Cap at 500 to prevent excessive queries
        
        # Perform base search
        results = self.search(query, source, date_range, raw_limit)
        
        if not results:
            return results
            
        # Apply personalization boosting
        try:
            from src.personalization.relevance_boost import RelevanceBooster
            
            booster = RelevanceBooster()
            
            if booster.filter.primary_user:
                # Convert to compatible format for boosting
                class SearchResult:
                    def __init__(self, data):
                        self.content = data['content']
                        self.metadata = data['metadata']
                        self.score = data['relevance_score']
                        self.source = data['source']
                        self.date = data['date']
                        self.boosted = False
                        
                # Convert results
                result_objects = [SearchResult(result) for result in results]
                
                # Apply boosting
                boosted_objects = booster.boost_search_results(result_objects, boost_factor)
                
                # Convert back to dictionaries
                boosted_results = []
                for obj in boosted_objects:
                    boosted_results.append({
                        'content': obj.content,
                        'source': obj.source,
                        'date': obj.date,
                        'metadata': obj.metadata,
                        'relevance_score': obj.score,
                        'boosted': getattr(obj, 'boosted', False)
                    })
                
                # Log boosting info
                boosting_info = booster.get_boosted_results_info(boosted_objects)
                logger.info(f"🎯 Search personalization: {boosting_info['boosted_results']}/{boosting_info['total_results']} results boosted")
                
                return boosted_results[:limit]
                
        except Exception as e:
            logger.warning(f"⚠️ Search personalization failed: {e}")
            # Fall back to regular results
            
        return results[:limit]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        stats = dict(self._stats)
        
        with self.connection() as conn:
            # Record counts
            cursor = conn.execute("SELECT COUNT(*) FROM messages")
            stats['total_records'] = cursor.fetchone()[0]
            
            cursor = conn.execute("SELECT COUNT(*) FROM archives")
            stats['archives_tracked'] = cursor.fetchone()[0]
            
            # Source breakdown
            cursor = conn.execute("""
                SELECT source, COUNT(*) FROM messages GROUP BY source
            """)
            stats['records_by_source'] = dict(cursor.fetchall())
        
        return stats
    
    def close(self):
        """Close all connections with enhanced cleanup"""
        self._cleanup_all_connections()
        
    def __del__(self):
        """Destructor to ensure cleanup"""
        try:
            self.close()
        except Exception:
            pass