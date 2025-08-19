"""
Tests for database schema migration system
Following test-driven development - write tests FIRST
"""

import pytest
import sqlite3
import tempfile
import hashlib
import json
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.search.migrations import MigrationManager, Migration, MigrationError
from src.search.schema_validator import SchemaValidator


class TestMigrationSystem:
    """Test database schema migration system with safety enhancements"""
    
    def setup_method(self):
        """Setup test database and migration manager"""
        # Create temporary directory for test database
        self.test_dir = Path(tempfile.mkdtemp())
        self.db_path = self.test_dir / 'test.db'
        self.migration_dir = self.test_dir / 'migrations'
        self.migration_dir.mkdir(exist_ok=True)
        
        # Create migration manager
        self.migration_manager = MigrationManager(
            db_path=str(self.db_path),
            migration_dir=str(self.migration_dir)
        )
        
    def teardown_method(self):
        """Cleanup test files"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_initial_schema_creation(self):
        """Create initial schema from migration"""
        # Create initial migration file
        migration_content = """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            source TEXT NOT NULL,
            created_at TEXT NOT NULL,
            metadata TEXT
        );
        
        CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
            content,
            content=messages,
            content_rowid=id
        );
        
        CREATE TABLE IF NOT EXISTS archives (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT NOT NULL UNIQUE,
            source TEXT NOT NULL,
            indexed_at TEXT NOT NULL,
            checksum TEXT
        );
        """
        
        migration_file = self.migration_dir / '001_initial_schema.sql'
        migration_file.write_text(migration_content)
        
        # Apply migration
        result = self.migration_manager.apply_migration('001_initial_schema.sql')
        
        # Verify migration applied successfully
        assert result['success'] is True
        assert self.migration_manager.get_current_version() == 1
        
        # Verify core tables exist
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Check required tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            table_names = [row[0] for row in cursor.fetchall()]
            
            required_tables = ['messages', 'messages_fts', 'archives', 'schema_migrations']
            assert all(table in table_names for table in required_tables)
    
    def test_forward_migration_with_version_tracking(self):
        """Apply forward migration with version tracking"""
        # Create initial migration
        initial_migration = """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY,
            content TEXT NOT NULL,
            source TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """
        
        migration_file_1 = self.migration_dir / '001_initial_schema.sql'
        migration_file_1.write_text(initial_migration)
        
        # Create second migration (add indexes)
        optimization_migration = """
        CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at);
        CREATE INDEX IF NOT EXISTS idx_messages_source ON messages(source);
        
        CREATE VIEW IF NOT EXISTS daily_activity AS
        SELECT 
            date(created_at) as activity_date,
            source,
            COUNT(*) as activity_count
        FROM messages 
        GROUP BY date(created_at), source;
        """
        
        migration_file_2 = self.migration_dir / '002_query_optimizations.sql'
        migration_file_2.write_text(optimization_migration)
        
        # Apply migrations in sequence
        self.migration_manager.apply_migration('001_initial_schema.sql')
        assert self.migration_manager.get_current_version() == 1
        
        self.migration_manager.apply_migration('002_query_optimizations.sql')
        assert self.migration_manager.get_current_version() == 2
        
        # Verify new indexes exist
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
            index_names = [row[0] for row in cursor.fetchall()]
            
            assert 'idx_messages_created_at' in index_names
            assert 'idx_messages_source' in index_names
    
    def test_data_preservation_during_migration(self):
        """Ensure no data loss during schema changes"""
        # Setup initial schema and data
        initial_migration = """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY,
            content TEXT NOT NULL,
            source TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """
        
        migration_file_1 = self.migration_dir / '001_initial_schema.sql'
        migration_file_1.write_text(initial_migration)
        
        self.migration_manager.apply_migration('001_initial_schema.sql')
        
        # Insert test data
        test_data = [
            {'content': 'Test message 1', 'source': 'slack', 'created_at': '2025-08-19T10:00:00Z'},
            {'content': 'Test message 2', 'source': 'calendar', 'created_at': '2025-08-19T11:00:00Z'},
            {'content': 'Test message 3', 'source': 'drive', 'created_at': '2025-08-19T12:00:00Z'}
        ]
        
        with sqlite3.connect(self.db_path) as conn:
            for item in test_data:
                conn.execute(
                    "INSERT INTO messages (content, source, created_at) VALUES (?, ?, ?)",
                    (item['content'], item['source'], item['created_at'])
                )
            conn.commit()
        
        original_count = len(test_data)
        
        # Calculate data checksum before migration
        pre_migration_checksum = self._calculate_data_checksum()
        
        # Apply migration that changes schema
        optimization_migration = """
        CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at);
        ALTER TABLE messages ADD COLUMN metadata TEXT;
        """
        
        migration_file_2 = self.migration_dir / '002_add_metadata.sql'
        migration_file_2.write_text(optimization_migration)
        
        result = self.migration_manager.apply_migration('002_add_metadata.sql')
        assert result['success'] is True
        
        # Verify all data preserved
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM messages")
            new_count = cursor.fetchone()[0]
            assert new_count == original_count
            
            # Verify content integrity
            cursor.execute("SELECT content FROM messages ORDER BY created_at")
            contents = [row[0] for row in cursor.fetchall()]
            expected_contents = [item['content'] for item in test_data]
            assert contents == expected_contents
        
        # Verify data integrity via checksum (ignoring new column)
        post_migration_checksum = self._calculate_data_checksum(ignore_columns=['metadata'])
        assert pre_migration_checksum == post_migration_checksum
    
    def test_rollback_migration_with_validation(self):
        """Rollback to previous schema version safely with data validation"""
        # Apply multiple migrations
        migrations = [
            ('001_initial.sql', """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY,
                    content TEXT NOT NULL,
                    source TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
            """),
            ('002_add_indexes.sql', """
                CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at);
                CREATE INDEX IF NOT EXISTS idx_messages_source ON messages(source);
            """),
            ('003_add_metadata.sql', """
                ALTER TABLE messages ADD COLUMN metadata TEXT;
                CREATE INDEX IF NOT EXISTS idx_messages_metadata ON messages(metadata);
            """)
        ]
        
        for filename, content in migrations:
            migration_file = self.migration_dir / filename
            migration_file.write_text(content)
            self.migration_manager.apply_migration(filename)
        
        assert self.migration_manager.get_current_version() == 3
        
        # Insert test data
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO messages (content, source, created_at, metadata) VALUES (?, ?, ?, ?)",
                ('test', 'slack', '2025-08-19T10:00:00Z', '{"test": true}')
            )
            conn.commit()
        
        # Calculate pre-rollback checksum
        pre_rollback_checksum = self._calculate_data_checksum()
        
        # Rollback to version 2
        result = self.migration_manager.rollback_to_version(2)
        assert result['success'] is True
        assert self.migration_manager.get_current_version() == 2
        
        # Verify core data preserved (metadata column should be gone)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT content FROM messages WHERE content = 'test'")
            assert cursor.fetchone() is not None
            
            # Verify metadata column no longer exists
            cursor.execute("PRAGMA table_info(messages)")
            columns = [row[1] for row in cursor.fetchall()]
            assert 'metadata' not in columns
        
        # Verify rollback integrity
        assert result.get('data_integrity_verified') is True
    
    def test_migration_failure_recovery(self):
        """Handle migration failures gracefully with recovery"""
        # Apply valid migration first
        valid_migration = """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY,
            content TEXT NOT NULL,
            source TEXT NOT NULL
        );
        """
        
        migration_file_1 = self.migration_dir / '001_valid.sql'
        migration_file_1.write_text(valid_migration)
        
        self.migration_manager.apply_migration('001_valid.sql')
        assert self.migration_manager.get_current_version() == 1
        
        # Create invalid migration (syntax error)
        invalid_migration = """
        INVALID SQL SYNTAX HERE;
        CREATE TABLE broken_table (
            invalid_column NONEXISTENT_TYPE
        );
        """
        
        migration_file_2 = self.migration_dir / '002_invalid.sql'
        migration_file_2.write_text(invalid_migration)
        
        # Attempt invalid migration (should fail safely)
        with pytest.raises(MigrationError):
            self.migration_manager.apply_migration('002_invalid.sql')
        
        # Verify system still functional at original version
        assert self.migration_manager.get_current_version() == 1
        
        # Database should still be usable
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            assert len(tables) > 0  # Database not corrupted
            
            # Original table should still exist and be functional
            cursor.execute("INSERT INTO messages (content, source) VALUES ('test', 'test')")
            conn.commit()
    
    def test_concurrent_migration_protection(self):
        """Test file locking prevents concurrent migrations"""
        # This test verifies lab-grade simple file locking
        lock_file = self.test_dir / '.migration.lock'
        
        # Create a lock file manually
        lock_file.write_text('test_process')
        
        # Try to start migration while locked
        with pytest.raises(MigrationError, match="Migration already in progress"):
            second_manager = MigrationManager(
                db_path=str(self.db_path),
                migration_dir=str(self.migration_dir)
            )
            
            migration_content = "CREATE TABLE test (id INTEGER);"
            migration_file = self.migration_dir / '001_test.sql'
            migration_file.write_text(migration_content)
            
            second_manager.apply_migration('001_test.sql')
    
    def test_schema_validation_integration(self):
        """Test schema validator integration with migration system"""
        # Create migration with schema validation
        migration_content = """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY,
            content TEXT NOT NULL,
            source TEXT NOT NULL CHECK (source IN ('slack', 'calendar', 'drive')),
            created_at TEXT NOT NULL
        );
        
        CREATE INDEX IF NOT EXISTS idx_messages_source ON messages(source);
        """
        
        migration_file = self.migration_dir / '001_with_validation.sql'
        migration_file.write_text(migration_content)
        
        # Apply migration
        result = self.migration_manager.apply_migration('001_with_validation.sql')
        assert result['success'] is True
        
        # Verify schema validation passes
        validator = SchemaValidator(str(self.db_path))
        validation_result = validator.validate_schema()
        
        assert validation_result['valid'] is True
        assert 'messages' in validation_result['tables']
        assert 'idx_messages_source' in validation_result['indexes']
    
    def test_data_integrity_checksums(self):
        """Test SHA256 checksum validation for data integrity"""
        # Setup initial data
        migration_content = """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY,
            content TEXT NOT NULL,
            source TEXT NOT NULL
        );
        """
        
        migration_file = self.migration_dir / '001_initial.sql'
        migration_file.write_text(migration_content)
        
        self.migration_manager.apply_migration('001_initial.sql')
        
        # Insert test data
        test_data = [
            ('Message 1', 'slack'),
            ('Message 2', 'calendar'),
            ('Message 3', 'drive')
        ]
        
        with sqlite3.connect(self.db_path) as conn:
            for content, source in test_data:
                conn.execute(
                    "INSERT INTO messages (content, source) VALUES (?, ?)",
                    (content, source)
                )
            conn.commit()
        
        # Calculate initial checksum
        initial_checksum = self.migration_manager._calculate_table_checksum('messages')
        assert len(initial_checksum) == 64  # SHA256 hex digest length
        
        # Apply schema-only migration (should not change data checksum)
        schema_migration = """
        CREATE INDEX IF NOT EXISTS idx_messages_content ON messages(content);
        """
        
        migration_file_2 = self.migration_dir / '002_index_only.sql'
        migration_file_2.write_text(schema_migration)
        
        result = self.migration_manager.apply_migration('002_index_only.sql')
        assert result['success'] is True
        
        # Verify data checksum unchanged
        post_migration_checksum = self.migration_manager._calculate_table_checksum('messages')
        assert initial_checksum == post_migration_checksum
    
    def test_migration_resume_after_interruption(self):
        """Test migration system can resume after interruption"""
        # Create multi-step migration
        complex_migration = """
        -- Step 1: Create table
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY,
            content TEXT NOT NULL
        );
        
        -- Step 2: Add indexes
        CREATE INDEX IF NOT EXISTS idx_messages_content ON messages(content);
        
        -- Step 3: Create view
        CREATE VIEW IF NOT EXISTS message_summary AS
        SELECT COUNT(*) as total_messages FROM messages;
        """
        
        migration_file = self.migration_dir / '001_complex.sql'
        migration_file.write_text(complex_migration)
        
        # Simulate interruption by mocking database connection failure
        with patch.object(self.migration_manager, '_execute_migration_sql') as mock_execute:
            # First call succeeds (table creation)
            # Second call fails (simulated interruption)
            mock_execute.side_effect = [None, sqlite3.OperationalError("Simulated interruption")]
            
            with pytest.raises(MigrationError):
                self.migration_manager.apply_migration('001_complex.sql')
        
        # Verify partial migration state is tracked
        migration_state = self.migration_manager._get_migration_state('001_complex.sql')
        assert migration_state is not None
        assert migration_state['status'] == 'failed'
        
        # Resume migration (should complete successfully)
        result = self.migration_manager.resume_migration('001_complex.sql')
        assert result['success'] is True
        assert self.migration_manager.get_current_version() == 1
    
    def _calculate_data_checksum(self, ignore_columns=None):
        """Helper method to calculate data checksum for testing"""
        ignore_columns = ignore_columns or []
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get table schema
            cursor.execute("PRAGMA table_info(messages)")
            columns = [row[1] for row in cursor.fetchall() if row[1] not in ignore_columns]
            
            # Get all data using parameterized query for security
            # Note: Column names can't be parameterized, but we validate them first
            safe_columns = []
            for col in columns:
                # Validate column names contain only alphanumeric and underscore
                if not col.replace('_', '').isalnum():
                    raise ValueError(f"Invalid column name: {col}")
                safe_columns.append(col)
            
            column_list = ', '.join(f'"{col}"' for col in safe_columns)
            query = f"SELECT {column_list} FROM messages ORDER BY id"
            cursor.execute(query)
            data = cursor.fetchall()
            
            # Calculate checksum
            data_str = json.dumps(data, sort_keys=True)
            return hashlib.sha256(data_str.encode()).hexdigest()


class TestSchemaValidator:
    """Test schema validation system"""
    
    def setup_method(self):
        """Setup test database"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.db_path = self.test_dir / 'test.db'
        
    def teardown_method(self):
        """Cleanup test files"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_schema_validation_success(self):
        """Test successful schema validation"""
        # Create valid database schema
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE messages (
                    id INTEGER PRIMARY KEY,
                    content TEXT NOT NULL,
                    source TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            
            conn.execute("CREATE INDEX idx_messages_source ON messages(source)")
            conn.commit()
        
        # Validate schema
        validator = SchemaValidator(str(self.db_path))
        result = validator.validate_schema()
        
        assert result['valid'] is True
        assert 'messages' in result['tables']
        assert 'idx_messages_source' in result['indexes']
    
    def test_foreign_key_validation(self):
        """Test foreign key constraint validation"""
        # Create schema with foreign key
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            
            conn.execute("""
                CREATE TABLE sources (
                    id INTEGER PRIMARY KEY,
                    name TEXT UNIQUE NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE TABLE messages (
                    id INTEGER PRIMARY KEY,
                    content TEXT NOT NULL,
                    source_id INTEGER,
                    FOREIGN KEY (source_id) REFERENCES sources(id)
                )
            """)
            
            # Insert valid data
            conn.execute("INSERT INTO sources (name) VALUES ('slack')")
            conn.execute("INSERT INTO messages (content, source_id) VALUES ('test', 1)")
            conn.commit()
        
        # Validate schema and foreign keys
        validator = SchemaValidator(str(self.db_path))
        result = validator.validate_foreign_keys()
        
        assert result['valid'] is True
        assert len(result['violations']) == 0
    
    def test_index_existence_verification(self):
        """Test index existence and performance validation"""
        # Create table without required indexes
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE messages (
                    id INTEGER PRIMARY KEY,
                    content TEXT NOT NULL,
                    source TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            conn.commit()
        
        # Validate missing indexes
        validator = SchemaValidator(str(self.db_path))
        required_indexes = {
            'idx_messages_created_at': 'messages(created_at)',
            'idx_messages_source': 'messages(source)'
        }
        
        result = validator.validate_required_indexes(required_indexes)
        
        assert result['valid'] is False
        assert len(result['missing_indexes']) == 2
        assert 'idx_messages_created_at' in result['missing_indexes']
        assert 'idx_messages_source' in result['missing_indexes']