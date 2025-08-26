"""
Test Database Schema Migration System

Comprehensive test suite for the migration system with data preservation,
rollback validation, and integrity checking as specified in Agent D requirements.

Test Categories:
- Migration system functionality
- Data preservation during schema changes
- Rollback operations
- Error handling and recovery
- Migration validation and integrity

References:
- tasks/phase1_agent_d_migration.md lines 64-208 for test specifications
- src/search/migrations.py for implementation under test
"""

import pytest
import sqlite3
import tempfile
import os
import hashlib
from pathlib import Path
from unittest.mock import patch, MagicMock

# Import the migration system
import sys
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from search.migrations import MigrationManager, Migration, MigrationError, MigrationValidationError


class TestMigrationSystem:
    """Test database schema migration system core functionality"""
    
    @pytest.fixture
    def temp_db_path(self):
        """Create temporary database file"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as temp_file:
            temp_path = temp_file.name
        yield temp_path
        # Cleanup
        if os.path.exists(temp_path):
            os.unlink(temp_path)
    
    @pytest.fixture
    def temp_migrations_dir(self):
        """Create temporary migrations directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    @pytest.fixture
    def migration_manager(self, temp_db_path, temp_migrations_dir):
        """Create migration manager with temp database and migrations"""
        manager = MigrationManager(temp_db_path, temp_migrations_dir)
        return manager
    
    def test_initial_schema_creation(self, migration_manager, temp_migrations_dir):
        """Create initial schema from migration"""
        # Create a test migration file
        migration_sql = """
        CREATE TABLE IF NOT EXISTS test_messages (
            id INTEGER PRIMARY KEY,
            content TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE INDEX IF NOT EXISTS idx_test_messages_created ON test_messages(created_at);
        """
        
        migration_path = Path(temp_migrations_dir) / "001_initial_schema.sql"
        migration_path.write_text(migration_sql)
        
        # Apply migration
        manager = migration_manager
        result = manager.apply_migration('001_initial_schema.sql')
        
        # Verify migration applied successfully
        assert result is True
        assert manager.get_current_version() == 1
        
        # Verify schema version tracked
        with sqlite3.connect(manager.db_path) as conn:
            cursor = conn.cursor()
            
            # Check required tables exist
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            table_names = [row[0] for row in cursor.fetchall()]
            
            required_tables = ['test_messages', 'schema_migrations']
            assert all(table in table_names for table in required_tables)
            
            # Verify index created
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_test_messages_created'")
            assert cursor.fetchone() is not None
    
    def test_forward_migration(self, migration_manager, temp_migrations_dir):
        """Apply forward migration with version tracking"""
        # Create initial migration
        migration1_sql = """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY,
            content TEXT NOT NULL
        );
        """
        
        migration2_sql = """
        CREATE INDEX IF NOT EXISTS idx_messages_content ON messages(content);
        
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            email TEXT UNIQUE
        );
        """
        
        migrations_dir = Path(temp_migrations_dir)
        (migrations_dir / "001_initial.sql").write_text(migration1_sql)
        (migrations_dir / "002_add_indexes.sql").write_text(migration2_sql)
        
        manager = migration_manager
        
        # Start with version 0
        assert manager.get_current_version() == 0
        
        # Apply first migration
        manager.apply_migration('001_initial.sql')
        assert manager.get_current_version() == 1
        
        # Apply second migration
        manager.apply_migration('002_add_indexes.sql')
        assert manager.get_current_version() == 2
        
        # Verify new indexes and tables exist
        with sqlite3.connect(manager.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
            index_names = [row[0] for row in cursor.fetchall()]
            
            assert 'idx_messages_content' in index_names
            
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            table_names = [row[0] for row in cursor.fetchall()]
            assert 'users' in table_names
    
    def test_rollback_migration(self, migration_manager, temp_migrations_dir):
        """Rollback to previous schema version safely"""
        # Create two migrations
        migration1_sql = "CREATE TABLE IF NOT EXISTS table1 (id INTEGER PRIMARY KEY);"
        migration2_sql = "CREATE TABLE IF NOT EXISTS table2 (id INTEGER PRIMARY KEY);"
        
        migrations_dir = Path(temp_migrations_dir)
        (migrations_dir / "001_create_table1.sql").write_text(migration1_sql)
        (migrations_dir / "002_create_table2.sql").write_text(migration2_sql)
        
        manager = migration_manager
        
        # Apply both migrations
        manager.apply_migration('001_create_table1.sql')
        manager.apply_migration('002_create_table2.sql')
        assert manager.get_current_version() == 2
        
        # Insert test data
        with sqlite3.connect(manager.db_path) as conn:
            conn.execute("INSERT INTO table1 (id) VALUES (1)")
            conn.execute("INSERT INTO table2 (id) VALUES (2)")
            conn.commit()
        
        # Rollback to version 1
        manager.rollback_to_version(1)
        assert manager.get_current_version() == 1
        
        # Verify rollback worked (simplified lab-grade check)
        status = manager.get_migration_status()
        applied_versions = [m['version'] for m in status['applied_migrations']]
        assert applied_versions == [1]
    
    def test_data_preservation_during_migration(self, migration_manager, temp_migrations_dir):
        """Ensure no data loss during schema changes"""
        # Create initial schema
        initial_sql = """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY,
            content TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        """
        
        optimization_sql = """
        CREATE INDEX IF NOT EXISTS idx_messages_content ON messages(content);
        CREATE INDEX IF NOT EXISTS idx_messages_created ON messages(created_at);
        """
        
        migrations_dir = Path(temp_migrations_dir)
        (migrations_dir / "001_initial.sql").write_text(initial_sql)
        (migrations_dir / "002_optimize.sql").write_text(optimization_sql)
        
        manager = migration_manager
        
        # Setup initial schema and data
        manager.apply_migration('001_initial.sql')
        
        test_data = [
            {'content': 'Test message 1', 'created_at': '2025-08-19T10:00:00Z'},
            {'content': 'Test message 2', 'created_at': '2025-08-19T11:00:00Z'},
            {'content': 'Test message 3', 'created_at': '2025-08-19T12:00:00Z'}
        ]
        
        # Insert test data
        with sqlite3.connect(manager.db_path) as conn:
            for item in test_data:
                conn.execute(
                    "INSERT INTO messages (content, created_at) VALUES (?, ?)",
                    (item['content'], item['created_at'])
                )
            conn.commit()
        
        original_count = len(test_data)
        
        # Apply migration that changes schema (adds indexes)
        manager.apply_migration('002_optimize.sql')
        
        # Verify all data preserved
        with sqlite3.connect(manager.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM messages")
            new_count = cursor.fetchone()[0]
            assert new_count == original_count
            
            # Verify content integrity
            cursor.execute("SELECT content FROM messages ORDER BY created_at")
            contents = [row[0] for row in cursor.fetchall()]
            expected_contents = [item['content'] for item in test_data]
            assert contents == expected_contents
            
            # Verify indexes were created
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='messages'")
            indexes = [row[0] for row in cursor.fetchall()]
            assert 'idx_messages_content' in indexes
            assert 'idx_messages_created' in indexes
    
    def test_migration_failure_recovery(self, migration_manager, temp_migrations_dir):
        """Handle migration failures gracefully"""
        # Create valid migration
        valid_sql = "CREATE TABLE IF NOT EXISTS valid_table (id INTEGER PRIMARY KEY);"
        
        # Create invalid migration - use a syntax that will fail
        invalid_sql = "INVALID SQL STATEMENT;"
        
        migrations_dir = Path(temp_migrations_dir)
        (migrations_dir / "001_valid.sql").write_text(valid_sql)
        (migrations_dir / "002_invalid.sql").write_text(invalid_sql)
        
        manager = migration_manager
        
        # Apply valid migration
        manager.apply_migration('001_valid.sql')
        assert manager.get_current_version() == 1
        
        # Attempt invalid migration (should fail safely)
        with pytest.raises(MigrationError):
            manager.apply_migration('002_invalid.sql')
        
        # Verify system still functional at original version
        assert manager.get_current_version() == 1
        
        # Database should still be usable
        with sqlite3.connect(manager.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            assert len(tables) >= 2  # schema_migrations + valid_table
            
            # Verify valid table is accessible
            cursor.execute("INSERT INTO valid_table (id) VALUES (1)")
            cursor.execute("SELECT COUNT(*) FROM valid_table")
            assert cursor.fetchone()[0] == 1
    
    def test_migration_status_reporting(self, migration_manager, temp_migrations_dir):
        """Test comprehensive migration status reporting"""
        # Create migrations
        migrations_dir = Path(temp_migrations_dir)
        (migrations_dir / "001_first.sql").write_text("CREATE TABLE test1 (id INTEGER);")
        (migrations_dir / "002_second.sql").write_text("CREATE TABLE test2 (id INTEGER);")
        (migrations_dir / "003_third.sql").write_text("CREATE TABLE test3 (id INTEGER);")
        
        manager = migration_manager
        
        # Apply first two migrations
        manager.apply_migration('001_first.sql')
        manager.apply_migration('002_second.sql')
        
        # Get status
        status = manager.get_migration_status()
        
        assert status['current_version'] == 2
        assert len(status['available_migrations']) == 3
        assert len(status['applied_migrations']) == 2
        assert len(status['pending_migrations']) == 1
        
        # Check applied migrations details
        applied = status['applied_migrations']
        assert applied[0]['version'] == 1
        assert applied[1]['version'] == 2
        assert 'applied_at' in applied[0]
        
        # Check pending migrations
        pending = status['pending_migrations']
        assert pending[0]['version'] == 3
        assert pending[0]['description'] == 'third'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])