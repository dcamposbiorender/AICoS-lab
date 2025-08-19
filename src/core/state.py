#!/usr/bin/env python3
"""
SQLite-based state management for AI Chief of Staff
Provides safe concurrent access with better performance and reliability than file-based state
"""

import sqlite3
import json
import logging
import threading
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class StateError(Exception):
    """Raised when state operations fail"""
    pass


class StateManager:
    """
    SQLite-based state manager with proper concurrency control
    
    Features:
    - SQLite with WAL mode for better concurrency
    - Thread-safe operations
    - Atomic transactions
    - Automatic schema migration
    - State history tracking
    - Backup and recovery capabilities
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        """Initialize StateManager with SQLite database"""
        if db_path is None:
            try:
                from src.core.config import get_config
                config = get_config()
                db_path = config.state_dir / "state.db"
            except Exception:
                # Fallback for testing or standalone use
                db_path = Path("data/state/state.db")
        
        # Ensure directory exists
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.db_path = db_path
        self._local = threading.local()
        self._init_database()
        
        logger.info(f"StateManager initialized with SQLite: {db_path}")
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection"""
        if not hasattr(self._local, 'connection'):
            conn = sqlite3.connect(
                str(self.db_path),
                timeout=30.0,
                check_same_thread=False
            )
            
            # Enable WAL mode for better concurrency
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA temp_store=MEMORY")
            
            self._local.connection = conn
        
        return self._local.connection
    
    def _init_database(self):
        """Initialize database schema"""
        with self._get_connection() as conn:
            # Main state table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS state (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            
            # State history table for audit trail
            conn.execute("""
                CREATE TABLE IF NOT EXISTS state_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
            """)
            
            # Index for performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_state_updated ON state(updated_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_history_key ON state_history(key)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_history_timestamp ON state_history(timestamp)")
            
            conn.commit()
    
    @contextmanager
    def transaction(self):
        """Context manager for atomic transactions"""
        conn = self._get_connection()
        try:
            conn.execute("BEGIN")
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Transaction failed: {e}")
            raise StateError(f"Transaction failed: {e}")
    
    def get_state(self, key: str, default: Any = None) -> Any:
        """
        Get state value for key
        
        Args:
            key: State key
            default: Default value if key doesn't exist
            
        Returns:
            State value or default
        """
        try:
            conn = self._get_connection()
            cursor = conn.execute(
                "SELECT value FROM state WHERE key = ?",
                (key,)
            )
            row = cursor.fetchone()
            
            if row is None:
                return default
            
            # Parse JSON value
            try:
                return json.loads(row[0])
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON in state key '{key}', returning raw value")
                return row[0]
                
        except Exception as e:
            logger.error(f"Failed to get state '{key}': {e}")
            raise StateError(f"Failed to get state '{key}': {e}")
    
    def set_state(self, key: str, value: Any) -> None:
        """
        Set state value for key
        
        Args:
            key: State key
            value: Value to store (will be JSON serialized)
        """
        try:
            # Serialize value to JSON
            if isinstance(value, (dict, list, bool, int, float, str, type(None))):
                json_value = json.dumps(value, default=str)
            else:
                json_value = json.dumps(str(value))
            
            timestamp = datetime.now().isoformat()
            
            with self.transaction() as conn:
                # Check if key exists
                cursor = conn.execute("SELECT key FROM state WHERE key = ?", (key,))
                exists = cursor.fetchone() is not None
                
                if exists:
                    # Update existing
                    conn.execute("""
                        UPDATE state 
                        SET value = ?, updated_at = ?
                        WHERE key = ?
                    """, (json_value, timestamp, key))
                    operation = "UPDATE"
                else:
                    # Insert new
                    conn.execute("""
                        INSERT INTO state (key, value, updated_at, created_at)
                        VALUES (?, ?, ?, ?)
                    """, (key, json_value, timestamp, timestamp))
                    operation = "INSERT"
                
                # Record in history
                conn.execute("""
                    INSERT INTO state_history (key, value, operation, timestamp)
                    VALUES (?, ?, ?, ?)
                """, (key, json_value, operation, timestamp))
            
            logger.debug(f"State updated: {key} = {value}")
            
        except Exception as e:
            logger.error(f"Failed to set state '{key}': {e}")
            raise StateError(f"Failed to set state '{key}': {e}")
    
    def delete_state(self, key: str) -> bool:
        """
        Delete state key
        
        Args:
            key: State key to delete
            
        Returns:
            True if key existed and was deleted
        """
        try:
            timestamp = datetime.now().isoformat()
            
            with self.transaction() as conn:
                # Get current value for history
                cursor = conn.execute("SELECT value FROM state WHERE key = ?", (key,))
                row = cursor.fetchone()
                
                if row is None:
                    return False
                
                # Delete the key
                conn.execute("DELETE FROM state WHERE key = ?", (key,))
                
                # Record in history
                conn.execute("""
                    INSERT INTO state_history (key, value, operation, timestamp)
                    VALUES (?, ?, ?, ?)
                """, (key, row[0], "DELETE", timestamp))
            
            logger.debug(f"State deleted: {key}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete state '{key}': {e}")
            raise StateError(f"Failed to delete state '{key}': {e}")
    
    def get_all_state(self) -> Dict[str, Any]:
        """
        Get all state as dictionary
        
        Returns:
            Dictionary of all state key-value pairs
        """
        try:
            conn = self._get_connection()
            cursor = conn.execute("SELECT key, value FROM state")
            
            result = {}
            for key, value in cursor.fetchall():
                try:
                    result[key] = json.loads(value)
                except json.JSONDecodeError:
                    result[key] = value
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get all state: {e}")
            raise StateError(f"Failed to get all state: {e}")
    
    def clear_all_state(self) -> None:
        """Clear all state (dangerous operation)"""
        try:
            timestamp = datetime.now().isoformat()
            
            with self.transaction() as conn:
                # Record all deletes in history
                cursor = conn.execute("SELECT key, value FROM state")
                for key, value in cursor.fetchall():
                    conn.execute("""
                        INSERT INTO state_history (key, value, operation, timestamp)
                        VALUES (?, ?, ?, ?)
                    """, (key, value, "CLEAR", timestamp))
                
                # Clear all state
                conn.execute("DELETE FROM state")
            
            logger.warning("All state cleared")
            
        except Exception as e:
            logger.error(f"Failed to clear state: {e}")
            raise StateError(f"Failed to clear state: {e}")
    
    def get_state_history(self, key: str, limit: int = 100) -> list:
        """
        Get state change history for a key
        
        Args:
            key: State key
            limit: Maximum number of history entries
            
        Returns:
            List of history entries (newest first)
        """
        try:
            conn = self._get_connection()
            cursor = conn.execute("""
                SELECT value, operation, timestamp 
                FROM state_history 
                WHERE key = ? 
                ORDER BY id DESC 
                LIMIT ?
            """, (key, limit))
            
            history = []
            for value, operation, timestamp in cursor.fetchall():
                try:
                    parsed_value = json.loads(value)
                except json.JSONDecodeError:
                    parsed_value = value
                
                history.append({
                    'value': parsed_value,
                    'operation': operation,
                    'timestamp': timestamp
                })
            
            return history
            
        except Exception as e:
            logger.error(f"Failed to get history for '{key}': {e}")
            raise StateError(f"Failed to get history for '{key}': {e}")
    
    def backup_database(self, backup_path: Optional[Path] = None) -> Path:
        """
        Create backup of state database
        
        Args:
            backup_path: Optional path for backup file
            
        Returns:
            Path to backup file
        """
        if backup_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.db_path.parent / f"state_backup_{timestamp}.db"
        
        try:
            # Use SQLite backup API
            source = self._get_connection()
            backup_conn = sqlite3.connect(str(backup_path))
            
            source.backup(backup_conn)
            backup_conn.close()
            
            logger.info(f"State database backed up to: {backup_path}")
            return backup_path
            
        except Exception as e:
            logger.error(f"Failed to backup database: {e}")
            raise StateError(f"Failed to backup database: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get state database statistics"""
        try:
            conn = self._get_connection()
            
            # Count states
            cursor = conn.execute("SELECT COUNT(*) FROM state")
            state_count = cursor.fetchone()[0]
            
            # Count history entries  
            cursor = conn.execute("SELECT COUNT(*) FROM state_history")
            history_count = cursor.fetchone()[0]
            
            # Database file size
            db_size = self.db_path.stat().st_size if self.db_path.exists() else 0
            
            return {
                'state_count': state_count,
                'history_count': history_count,
                'db_size_mb': db_size / 1024**2,
                'db_path': str(self.db_path)
            }
            
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {'error': str(e)}
    
    def close(self):
        """Close database connections"""
        if hasattr(self._local, 'connection'):
            self._local.connection.close()
            del self._local.connection


# Global state manager instance
_state_manager = None


def get_state_manager() -> StateManager:
    """Get global state manager instance"""
    global _state_manager
    if _state_manager is None:
        _state_manager = StateManager()
    return _state_manager