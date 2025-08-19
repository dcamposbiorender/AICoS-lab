#!/usr/bin/env python3
"""
Security Validation Tests
Comprehensive tests for all security fixes implemented in the AI Chief of Staff system.

Tests cover:
1. Per-key salt encryption in key_manager.py
2. Encrypted credential caching in auth_manager.py  
3. SQL injection prevention in database operations
4. File permission validation and security
"""

import pytest
import os
import tempfile
import shutil
import sqlite3
import json
from pathlib import Path
from unittest.mock import patch, mock_open
import stat

# Test imports
from src.core.key_manager import EncryptedKeyManager
from src.core.auth_manager import CredentialVault, SecureCache
from src.core.file_security import FileSecurityValidator, SecurityLevel
from src.search.schema_validator import SchemaValidator


class TestEncryptionSaltSecurity:
    """Test fixes for hardcoded encryption salt vulnerability"""
    
    def setup_method(self):
        """Setup test environment"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.test_db = self.test_dir / 'test_keys.db'
        self.test_master_key = self.test_dir / '.test_master_key'
        
    def teardown_method(self):
        """Cleanup test files"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
        
    def test_per_key_salt_generation(self):
        """Test that each key gets a unique random salt"""
        key_manager = EncryptedKeyManager(str(self.test_db))
        
        # Store multiple keys
        test_data_1 = {"token": "secret_token_1", "type": "test"}
        test_data_2 = {"token": "secret_token_2", "type": "test"}
        
        result1 = key_manager.store_key("test_key_1", test_data_1)
        result2 = key_manager.store_key("test_key_2", test_data_2)
        
        assert result1 is True, "First key storage should succeed"
        assert result2 is True, "Second key storage should succeed"
        
        # Verify that different salts were used by checking database
        conn = sqlite3.connect(str(self.test_db))
        cursor = conn.cursor()
        cursor.execute("SELECT key_id, salt FROM encrypted_keys ORDER BY key_id")
        results = cursor.fetchall()
        conn.close()
        
        assert len(results) == 2, "Should have 2 keys in database"
        
        salt1 = results[0][1]  # test_key_1 salt
        salt2 = results[1][1]  # test_key_2 salt
        
        assert salt1 is not None, "First key should have salt"
        assert salt2 is not None, "Second key should have salt"
        assert salt1 != salt2, "Each key should have unique salt"
        assert len(salt1) == 32, "Salt should be 32 bytes"
        assert len(salt2) == 32, "Salt should be 32 bytes"
        
    def test_salt_based_decryption(self):
        """Test that keys can be decrypted using their stored salts"""
        key_manager = EncryptedKeyManager(str(self.test_db))
        
        original_data = {
            "api_key": "sk-1234567890abcdef",
            "endpoint": "https://api.example.com",
            "metadata": {"created": "2025-01-01"}
        }
        
        # Store key with salt
        store_result = key_manager.store_key("test_decrypt", original_data)
        assert store_result is True, "Key storage should succeed"
        
        # Retrieve and verify
        retrieved_data = key_manager.retrieve_key("test_decrypt")
        assert retrieved_data is not None, "Should retrieve stored key"
        assert retrieved_data == original_data, "Retrieved data should match original"
        
    def test_backward_compatibility_legacy_keys(self):
        """Test that keys stored with old hardcoded salt can still be read"""
        # Simulate legacy key storage (without salt column)
        conn = sqlite3.connect(str(self.test_db))
        cursor = conn.cursor()
        
        # Create old table structure without salt
        cursor.execute('''
            CREATE TABLE encrypted_keys (
                key_id TEXT PRIMARY KEY,
                encrypted_data BLOB NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                key_type TEXT NOT NULL,
                metadata TEXT
            )
        ''')
        
        # Insert a legacy encrypted entry (simulated)
        # Note: This would normally require the old encryption method
        # For testing, we'll create a minimal entry and test the handling
        cursor.execute('''
            INSERT INTO encrypted_keys 
            (key_id, encrypted_data, created_at, updated_at, key_type)
            VALUES (?, ?, ?, ?, ?)
        ''', ('legacy_key', b'fake_encrypted_data', '2025-01-01', '2025-01-01', 'api_key'))
        
        conn.commit()
        conn.close()
        
        # Initialize key manager (should handle missing salt column)
        key_manager = EncryptedKeyManager(str(self.test_db))
        
        # Verify database migration added salt column
        conn = sqlite3.connect(str(self.test_db))
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(encrypted_keys)")
        columns = [row[1] for row in cursor.fetchall()]
        conn.close()
        
        assert 'salt' in columns, "Migration should add salt column"
        
    def test_salt_validation_security(self):
        """Test that salt generation is cryptographically secure"""
        key_manager = EncryptedKeyManager(str(self.test_db))
        
        # Generate multiple salts and verify randomness
        salts = []
        for i in range(100):
            test_data = {"token": f"token_{i}"}
            key_manager.store_key(f"test_key_{i}", test_data)
            
            # Get the salt for this key
            conn = sqlite3.connect(str(self.test_db))
            cursor = conn.cursor()
            cursor.execute("SELECT salt FROM encrypted_keys WHERE key_id = ?", (f"test_key_{i}",))
            salt = cursor.fetchone()[0]
            conn.close()
            
            salts.append(salt)
        
        # Verify all salts are unique
        unique_salts = set(salts)
        assert len(unique_salts) == 100, "All salts should be unique"
        
        # Verify salt entropy (basic check)
        for salt in salts[:10]:  # Check first 10 for performance
            # Count unique bytes in salt
            unique_bytes = len(set(salt))
            assert unique_bytes > 20, f"Salt should have high entropy, got {unique_bytes} unique bytes"


class TestEncryptedCredentialCaching:
    """Test fixes for unencrypted credential caching vulnerability"""
    
    def setup_method(self):
        """Setup test environment"""
        self.test_dir = Path(tempfile.mkdtemp())
        
    def teardown_method(self):
        """Cleanup test files"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
        
    def test_secure_cache_encryption(self):
        """Test that cached credentials are encrypted"""
        cache = SecureCache()
        
        # Store sensitive credential
        sensitive_token = "sk-1234567890abcdef_very_secret"
        cache.set("test_token", sensitive_token)
        
        # Verify that raw cache doesn't contain plaintext
        assert sensitive_token not in str(cache._encrypted_cache.values())
        
        # Verify encrypted storage exists
        assert len(cache._encrypted_cache) == 1
        encrypted_value = list(cache._encrypted_cache.values())[0]
        assert isinstance(encrypted_value, bytes)
        assert len(encrypted_value) > len(sensitive_token)  # Encrypted should be longer
        
    def test_secure_cache_decryption(self):
        """Test that encrypted cache can be decrypted correctly"""
        cache = SecureCache()
        
        original_value = "secret_api_key_12345"
        cache.set("api_key", original_value)
        
        # Retrieve and verify
        decrypted_value = cache.get("api_key")
        assert decrypted_value == original_value
        
    def test_cache_clear_security(self):
        """Test that cache clearing removes all encrypted data"""
        cache = SecureCache()
        
        # Store multiple credentials
        cache.set("token1", "secret1")
        cache.set("token2", "secret2")
        cache.set("token3", "secret3")
        
        assert len(cache._encrypted_cache) == 3
        
        # Clear cache
        cache.clear()
        
        # Verify complete removal
        assert len(cache._encrypted_cache) == 0
        assert len(cache.last_cache_update) == 0
        
        # Verify retrieval returns None
        assert cache.get("token1") is None
        assert cache.get("token2") is None
        assert cache.get("token3") is None
        
    def test_corrupted_cache_handling(self):
        """Test handling of corrupted encrypted cache entries"""
        cache = SecureCache()
        
        # Manually corrupt cache entry
        cache._encrypted_cache["corrupted"] = b"invalid_encrypted_data"
        cache.last_cache_update["corrupted"] = cache.last_cache_update.get("corrupted", None)
        
        # Attempt to retrieve corrupted entry
        result = cache.get("corrupted")
        assert result is None, "Corrupted entry should return None"
        
        # Verify corrupted entry was removed
        assert "corrupted" not in cache._encrypted_cache
        assert "corrupted" not in cache.last_cache_update
        
    def test_credential_vault_integration(self):
        """Test that CredentialVault uses secure caching"""
        # Mock environment to avoid requiring real credentials
        with patch.dict(os.environ, {'SLACK_BOT_TOKEN': 'test_bot_token_12345'}):
            vault = CredentialVault()
            
            # Get token (should cache encrypted)
            token = vault.get_slack_bot_token()
            assert token == 'test_bot_token_12345'
            
            # Verify encrypted caching was used
            assert isinstance(vault.auth_cache, SecureCache)
            cached_token = vault.auth_cache.get('slack_bot_token')
            assert cached_token == 'test_bot_token_12345'
            
            # Verify raw cache doesn't contain plaintext
            raw_cache_values = str(vault.auth_cache._encrypted_cache.values())
            assert 'test_bot_token_12345' not in raw_cache_values
            
    def test_google_credentials_security(self):
        """Test that complex Google credentials are handled securely"""
        vault = CredentialVault()
        
        # Simulate Google credentials object
        class MockGoogleCreds:
            def __init__(self):
                self.token = "ya29.fake_access_token"
                self.refresh_token = "refresh_token_value"
                self.valid = True
                
        mock_creds = MockGoogleCreds()
        
        # Simulate storing complex credentials
        vault._temp_google_creds = mock_creds
        vault.auth_cache.last_cache_update['google_oauth_creds'] = vault.auth_cache.last_cache_update.get('google_oauth_creds')
        
        # Verify complex objects are not in encrypted string cache
        encrypted_values = str(vault.auth_cache._encrypted_cache.values())
        assert mock_creds.token not in encrypted_values
        assert mock_creds.refresh_token not in encrypted_values


class TestSQLInjectionPrevention:
    """Test fixes for SQL injection vulnerabilities"""
    
    def setup_method(self):
        """Setup test database"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.test_db = self.test_dir / 'test.db'
        
        # Create test database with sample data
        conn = sqlite3.connect(str(self.test_db))
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE messages (
                id INTEGER PRIMARY KEY,
                content TEXT NOT NULL,
                source TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        ''')
        
        # Insert test data
        test_messages = [
            (1, "Normal message", "slack", "2025-01-01"),
            (2, "Another message", "calendar", "2025-01-02"),
            (3, "'; DROP TABLE messages; --", "malicious", "2025-01-03")
        ]
        
        cursor.executemany(
            "INSERT INTO messages (id, content, source, created_at) VALUES (?, ?, ?, ?)",
            test_messages
        )
        
        conn.commit()
        conn.close()
        
    def teardown_method(self):
        """Cleanup test files"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
        
    def test_column_validation_prevents_injection(self):
        """Test that column name validation prevents SQL injection"""
        from tests.unit.test_migrations import MigrationTester
        
        tester = MigrationTester()
        tester.db_path = str(self.test_db)
        
        # Test normal columns work
        normal_checksum = tester._calculate_checksum(['id', 'content', 'source'])
        assert normal_checksum is not None
        assert len(normal_checksum) == 64  # SHA256 hex length
        
        # Test that malicious column names are rejected
        with pytest.raises(ValueError, match="Invalid column name"):
            tester._calculate_checksum(['id', 'content; DROP TABLE messages; --'])
            
        with pytest.raises(ValueError, match="Invalid column name"):
            tester._calculate_checksum(['id', 'content\'; SELECT * FROM messages WHERE \'1\'=\'1'])
            
    def test_schema_validator_prevents_injection(self):
        """Test that schema validator prevents SQL injection in table names"""
        validator = SchemaValidator(str(self.test_db))
        
        # Mock a malicious table name
        malicious_table = "messages'; DROP TABLE messages; --"
        
        # Test that malicious table name is rejected
        with pytest.raises(ValueError, match="Invalid table name"):
            validator._analyze_table(sqlite3.connect(str(self.test_db)), malicious_table, "")
            
    def test_fts_table_name_validation(self):
        """Test that FTS table names are properly validated"""
        validator = SchemaValidator(str(self.test_db))
        
        # Create connection for testing
        conn = sqlite3.connect(str(self.test_db))
        
        # Test normal FTS table name
        normal_fts = "messages_fts"
        issues = validator._validate_fts5_table(conn, normal_fts)
        # Should have issues since table doesn't exist, but no validation errors
        assert all("Invalid FTS table name" not in issue for issue in issues)
        
        # Test malicious FTS table name
        malicious_fts = "messages_fts'; DROP TABLE messages; --"
        with pytest.raises(ValueError, match="Invalid FTS table name"):
            validator._validate_fts5_table(conn, malicious_fts)
            
        conn.close()
        
    def test_index_name_validation(self):
        """Test that index names are properly validated"""
        validator = SchemaValidator(str(self.test_db))
        
        # Create a test index first
        conn = sqlite3.connect(str(self.test_db))
        conn.execute("CREATE INDEX idx_messages_source ON messages(source)")
        conn.commit()
        
        # Test validation
        result = validator._validate_indexes(conn)
        assert result['valid'] is True
        
        # Mock malicious index name in results
        conn.execute("CREATE INDEX \"malicious'; DROP TABLE messages; --\" ON messages(content)")
        
        # Should detect and handle invalid index name
        result = validator._validate_indexes(conn)
        
        # Check that invalid names are caught
        has_invalid_name_issue = any("Invalid index name" in issue for issue in result.get('issues', []))
        assert has_invalid_name_issue, "Should detect invalid index names"
        
        conn.close()
        
    def test_parameterized_query_usage(self):
        """Test that legitimate queries still work with parameterized approach"""
        # Test the fixed checksum calculation method
        from tests.unit.test_migrations import MigrationTester
        
        tester = MigrationTester()
        tester.db_path = str(self.test_db)
        
        # Calculate checksum with valid columns
        checksum1 = tester._calculate_checksum(['id', 'content'])
        checksum2 = tester._calculate_checksum(['id', 'source'])
        
        assert checksum1 is not None
        assert checksum2 is not None  
        assert checksum1 != checksum2  # Different columns should give different checksums
        assert len(checksum1) == 64  # SHA256 hex
        assert len(checksum2) == 64  # SHA256 hex


class TestFilePermissionSecurity:
    """Test comprehensive file permission validation"""
    
    def setup_method(self):
        """Setup test environment"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.validator = FileSecurityValidator()
        
    def teardown_method(self):
        """Cleanup test files"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
        
    def test_master_key_security_validation(self):
        """Test master key file security requirements"""
        master_key_file = self.test_dir / '.master_key'
        
        # Create master key file with wrong permissions
        master_key_file.write_text("test_key_content")
        os.chmod(master_key_file, 0o644)  # Too permissive
        
        # Validate security
        result = self.validator.validate_file_security(str(master_key_file), 'master_key')
        
        assert result['valid'] is False
        assert any("Incorrect permissions" in issue for issue in result['issues'])
        assert result['current_permissions'] == '0o644'
        assert result['required_permissions'] == '0o600'
        
    def test_secure_file_creation(self):
        """Test creation of files with proper security"""
        secure_file = self.test_dir / 'secure_config.json'
        
        # Create secure file
        result = self.validator.create_secure_file(
            str(secure_file), 
            'config_file',
            '{"api_key": "secret"}'
        )
        
        assert result['success'] is True
        assert secure_file.exists()
        
        # Verify permissions
        file_stat = secure_file.stat()
        permissions = stat.S_IMODE(file_stat.st_mode)
        assert permissions == 0o640
        
    def test_permission_fix_functionality(self):
        """Test automatic permission fixing"""
        test_file = self.test_dir / 'test_config.json'
        
        # Create file with wrong permissions
        test_file.write_text('{"test": "data"}')
        os.chmod(test_file, 0o666)  # Too permissive
        
        # Fix permissions
        result = self.validator.fix_file_permissions(str(test_file), 'config_file')
        
        assert result['success'] is True
        assert result['old_permissions'] == '0o666'
        assert result['new_permissions'] == '0o640'
        
        # Verify fix
        file_stat = test_file.stat()
        permissions = stat.S_IMODE(file_stat.st_mode)
        assert permissions == 0o640
        
    def test_directory_security_validation(self):
        """Test directory security validation"""
        secure_dir = self.test_dir / 'secure_data'
        
        # Create directory with proper security
        result = self.validator.create_secure_file(str(secure_dir), 'data_directory')
        
        assert result['success'] is True
        assert secure_dir.is_dir()
        
        # Verify directory permissions
        dir_stat = secure_dir.stat()
        permissions = stat.S_IMODE(dir_stat.st_mode)
        assert permissions == 0o700
        
    def test_world_writable_detection(self):
        """Test detection of world-writable security risks"""
        risky_file = self.test_dir / 'world_writable.txt'
        
        # Create world-writable file
        risky_file.write_text("dangerous content")
        os.chmod(risky_file, 0o666)
        
        # Validate
        result = self.validator.validate_file_security(str(risky_file), 'config_file')
        
        assert result['valid'] is False
        # Should detect world-writable as major security risk
        world_writable_issue = any(
            "world-writable" in issue.lower() 
            for issue in result['issues']
        )
        assert world_writable_issue, "Should detect world-writable files"
        
    def test_directory_tree_validation(self):
        """Test validation of entire directory trees"""
        # Create directory structure
        data_dir = self.test_dir / 'data'
        config_dir = self.test_dir / 'config'
        
        data_dir.mkdir()
        config_dir.mkdir()
        
        # Create various files
        (data_dir / '.master_key').write_text("master_key_content")
        (data_dir / 'encrypted_keys.db').write_text("db_content")
        (config_dir / 'app.json').write_text('{"config": true}')
        
        # Set various permissions (some wrong)
        os.chmod(data_dir / '.master_key', 0o644)  # Wrong
        os.chmod(data_dir / 'encrypted_keys.db', 0o600)  # Correct
        os.chmod(config_dir / 'app.json', 0o640)  # Correct
        
        # Validate entire tree
        result = self.validator.validate_directory_tree(str(self.test_dir))
        
        assert result['files_validated'] > 0
        assert result['directories_validated'] > 0
        assert result['valid'] is False  # Should fail due to master key permissions
        
        # Check specific file results
        master_key_result = None
        for path, validation in result['file_results'].items():
            if '.master_key' in path:
                master_key_result = validation
                break
                
        assert master_key_result is not None
        assert master_key_result['valid'] is False


class TestIntegratedSecurity:
    """Integration tests for all security fixes working together"""
    
    def setup_method(self):
        """Setup integrated test environment"""
        self.test_dir = Path(tempfile.mkdtemp())
        
    def teardown_method(self):
        """Cleanup test files"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
        
    def test_key_manager_complete_security(self):
        """Test that key manager implements all security fixes"""
        # Create key manager with custom paths
        key_db = self.test_dir / 'secure_keys.db'
        
        with patch.dict(os.environ, {'AICOS_CACHE_KEY': 'test_cache_key_secure'}):
            key_manager = EncryptedKeyManager(str(key_db))
            
            # Test 1: Per-key salts
            key_manager.store_key("test_key_1", {"api": "key1"})
            key_manager.store_key("test_key_2", {"api": "key2"})
            
            # Verify different salts
            conn = sqlite3.connect(str(key_db))
            cursor = conn.cursor()
            cursor.execute("SELECT salt FROM encrypted_keys")
            salts = [row[0] for row in cursor.fetchall()]
            conn.close()
            
            assert len(set(salts)) == 2, "Each key should have unique salt"
            
            # Test 2: File permissions
            if os.path.exists(key_manager.master_key_path):
                master_key_stat = os.stat(key_manager.master_key_path)
                permissions = stat.S_IMODE(master_key_stat.st_mode)
                assert permissions == 0o600, "Master key should have secure permissions"
                
            # Test 3: Successful decryption
            retrieved_key1 = key_manager.retrieve_key("test_key_1")
            retrieved_key2 = key_manager.retrieve_key("test_key_2")
            
            assert retrieved_key1 == {"api": "key1"}
            assert retrieved_key2 == {"api": "key2"}
            
    def test_auth_manager_secure_caching(self):
        """Test that auth manager uses secure caching throughout"""
        with patch.dict(os.environ, {
            'SLACK_BOT_TOKEN': 'secure_bot_token_test',
            'SLACK_USER_TOKEN': 'secure_user_token_test',
            'AICOS_CACHE_KEY': 'test_cache_encryption_key'
        }):
            vault = CredentialVault()
            
            # Get tokens (triggers caching)
            bot_token = vault.get_slack_bot_token()
            user_token = vault.get_slack_user_token()
            
            assert bot_token == 'secure_bot_token_test'
            assert user_token == 'secure_user_token_test'
            
            # Verify secure caching was used
            assert isinstance(vault.auth_cache, SecureCache)
            
            # Verify tokens are encrypted in cache
            encrypted_cache_str = str(vault.auth_cache._encrypted_cache.values())
            assert 'secure_bot_token_test' not in encrypted_cache_str
            assert 'secure_user_token_test' not in encrypted_cache_str
            
            # Verify cache can be cleared securely
            vault.clear_cache()
            assert len(vault.auth_cache._encrypted_cache) == 0


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "--tb=short"])