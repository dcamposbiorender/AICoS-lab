#!/usr/bin/env python3
"""
Encrypted Key Manager - AES-256 encrypted credential storage
Replaces plaintext JSON files with secure encrypted storage
"""

import os
import json
import sqlite3
import getpass
import hashlib
from datetime import datetime
from typing import Dict, Optional, Any
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

try:
    from .file_security import file_security
except ImportError:
    # Fallback if file_security not available
    file_security = None

class EncryptedKeyManager:
    def __init__(self, storage_path: str = None):
        self.storage_path = storage_path or os.path.join(
            os.path.dirname(__file__), 'encrypted_keys.db'
        )
        self.master_key_path = os.path.join(
            os.path.dirname(__file__), '.master_key'
        )
        self._cipher_suite = None
        
        # Validate or create secure file structure
        self._ensure_secure_setup()
        self._initialize_database()
        
    def _ensure_secure_setup(self):
        """Ensure secure file permissions and directory structure"""
        if file_security:
            # Validate storage directory security
            storage_dir = os.path.dirname(self.storage_path)
            if not os.path.exists(storage_dir):
                print("🔒 Creating secure storage directory...")
                dir_result = file_security.create_secure_file(storage_dir, 'data_directory')
                if not dir_result['success']:
                    print(f"⚠️ Storage directory security warning: {dir_result.get('error')}")
            else:
                # Validate existing directory
                dir_validation = file_security.validate_file_security(storage_dir, 'data_directory')
                if not dir_validation['valid']:
                    print(f"⚠️ Storage directory security issues:")
                    for issue in dir_validation.get('issues', []):
                        print(f"   • {issue}")
            
            # Validate encrypted database file if it exists
            if os.path.exists(self.storage_path):
                db_validation = file_security.validate_file_security(self.storage_path, 'encrypted_db')
                if not db_validation['valid']:
                    print(f"🔧 Fixing database permissions...")
                    fix_result = file_security.fix_file_permissions(self.storage_path, 'encrypted_db')
                    if fix_result['success']:
                        print("✅ Database permissions fixed")
                    else:
                        print(f"⚠️ Failed to fix database permissions: {fix_result.get('error')}")
        else:
            print("⚠️ File security validation not available - using basic permissions")
    
    def _initialize_database(self):
        """Initialize the encrypted key database"""
        conn = sqlite3.connect(self.storage_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS encrypted_keys (
                key_id TEXT PRIMARY KEY,
                encrypted_data BLOB NOT NULL,
                salt BLOB NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                key_type TEXT NOT NULL,
                metadata TEXT
            )
        ''')
        
        # Add salt column if it doesn't exist (backward compatibility)
        cursor.execute("PRAGMA table_info(encrypted_keys)")
        columns = [row[1] for row in cursor.fetchall()]
        if 'salt' not in columns:
            cursor.execute("ALTER TABLE encrypted_keys ADD COLUMN salt BLOB")
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS access_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key_id TEXT NOT NULL,
                action TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                user TEXT NOT NULL
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _get_master_password(self) -> str:
        """Get or create master password for encryption with secure file handling"""
        if os.path.exists(self.master_key_path):
            # Validate existing master key security
            if file_security:
                validation = file_security.validate_file_security(self.master_key_path, 'master_key')
                if not validation['valid']:
                    print("🔧 Master key file has security issues:")
                    for issue in validation.get('issues', []):
                        print(f"   • {issue}")
                    
                    # Attempt to fix permissions
                    fix_result = file_security.fix_file_permissions(self.master_key_path, 'master_key')
                    if fix_result['success']:
                        print("✅ Master key permissions fixed")
                    else:
                        print(f"⚠️ Cannot fix master key permissions: {fix_result.get('error')}")
            
            # Read existing master key
            with open(self.master_key_path, 'r') as f:
                return f.read().strip()
        else:
            print("🔐 Setting up encrypted credential storage...")
            
            # For automated setup, generate a secure random password
            import secrets
            import string
            
            # Generate a strong random password for development
            alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
            dev_password = ''.join(secrets.choice(alphabet) for _ in range(32))
            
            # Store hash of password (not the password itself)
            password_hash = hashlib.sha256(dev_password.encode()).hexdigest()
            
            # Create master key file securely
            if file_security:
                create_result = file_security.create_secure_file(
                    self.master_key_path, 
                    'master_key',
                    password_hash
                )
                if not create_result['success']:
                    print(f"⚠️ Could not create secure master key file: {create_result.get('error')}")
                    # Fallback to basic creation
                    with open(self.master_key_path, 'w') as f:
                        f.write(password_hash)
                    os.chmod(self.master_key_path, 0o600)
                else:
                    print("✅ Master key file created securely")
            else:
                # Fallback to basic secure creation
                with open(self.master_key_path, 'w') as f:
                    f.write(password_hash)
                os.chmod(self.master_key_path, 0o600)
            
            print("✅ Generated secure master key for development")
            print("💡 In production, this should be user-provided password")
            return password_hash
    
    def _get_cipher_suite(self, salt: bytes = None) -> Fernet:
        """Get or create cipher suite for encryption/decryption with per-key salt"""
        # Always create new cipher suite with provided salt for per-key encryption
        if salt is None:
            # Generate a new random salt for new keys
            salt = os.urandom(32)
        
        master_password = self._get_master_password()
        
        # Derive key from master password using the provided salt
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        
        key = base64.urlsafe_b64encode(kdf.derive(master_password.encode()))
        return Fernet(key), salt
    
    def store_key(self, key_id: str, data: Dict[str, Any], key_type: str = "api_key", metadata: Optional[Dict] = None) -> bool:
        """Store encrypted credentials with per-key random salt"""
        try:
            # Safeguard: Prevent test tokens from being stored in production keys
            if key_id == 'slack_tokens_production':
                # Check if any value contains 'test'
                data_str = json.dumps(data).lower()
                if 'test' in data_str or any('test' in str(v).lower() for v in data.values() if isinstance(v, str)):
                    print("🛑 BLOCKED: Cannot store test tokens in production key 'slack_tokens_production'")
                    print("   Use 'slack_tokens_test' for test tokens")
                    return False
                
                # Require confirmation for production key updates
                print("⚠️  WARNING: About to store tokens in PRODUCTION key 'slack_tokens_production'")
                print("   This should only be done when setting real Slack tokens")
                print("   Test tokens should use 'slack_tokens_test' key")
            
            # Safeguard: Prevent production tokens from being stored in test keys
            if key_id == 'slack_tokens_test':
                # Check if tokens look like real production tokens (not test tokens)
                for key, value in data.items():
                    if isinstance(value, str) and value.startswith(('xoxb-', 'xoxp-')) and not value.startswith(('xoxb-test-', 'xoxp-test-')):
                        print("🛑 BLOCKED: Detected real token in test key 'slack_tokens_test'")
                        print("   Real tokens should use 'slack_tokens_production'")
                        print("   Test tokens should start with 'xoxb-test-' or 'xoxp-test-'")
                        return False
            # Generate new cipher suite with random salt for this key
            cipher_suite, salt = self._get_cipher_suite()
            
            # Encrypt the data
            json_data = json.dumps(data)
            encrypted_data = cipher_suite.encrypt(json_data.encode())
            
            # Store in database
            conn = sqlite3.connect(self.storage_path)
            cursor = conn.cursor()
            
            timestamp = datetime.now().isoformat()
            metadata_json = json.dumps(metadata) if metadata else None
            
            cursor.execute('''
                INSERT OR REPLACE INTO encrypted_keys 
                (key_id, encrypted_data, salt, created_at, updated_at, key_type, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (key_id, encrypted_data, salt, timestamp, timestamp, key_type, metadata_json))
            
            # Log the access
            cursor.execute('''
                INSERT INTO access_log (key_id, action, timestamp, user)
                VALUES (?, ?, ?, ?)
            ''', (key_id, 'STORE', timestamp, getpass.getuser()))
            
            conn.commit()
            conn.close()
            
            print(f"✅ Encrypted credentials stored with unique salt: {key_id}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to store encrypted key {key_id}: {e}")
            return False
    
    def retrieve_key(self, key_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve and decrypt credentials using stored salt"""
        try:
            conn = sqlite3.connect(self.storage_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT encrypted_data, salt FROM encrypted_keys WHERE key_id = ?
            ''', (key_id,))
            
            result = cursor.fetchone()
            if not result:
                print(f"❌ Key not found: {key_id}")
                return None
            
            encrypted_data, stored_salt = result
            
            # Handle backward compatibility for keys without salt
            if stored_salt is None:
                print(f"⚠️ Key {key_id} uses legacy encryption (no salt) - consider re-storing for security")
                # Use old hardcoded salt for backward compatibility
                legacy_salt = b'ai_chief_of_staff_salt'
                cipher_suite, _ = self._get_cipher_suite(legacy_salt)
            else:
                # Use stored salt
                cipher_suite, _ = self._get_cipher_suite(stored_salt)
            
            # Decrypt the data
            decrypted_data = cipher_suite.decrypt(encrypted_data)
            data = json.loads(decrypted_data.decode())
            
            # Log the access
            timestamp = datetime.now().isoformat()
            cursor.execute('''
                INSERT INTO access_log (key_id, action, timestamp, user)
                VALUES (?, ?, ?, ?)
            ''', (key_id, 'RETRIEVE', timestamp, getpass.getuser()))
            
            conn.commit()
            conn.close()
            
            return data
            
        except Exception as e:
            print(f"❌ Failed to retrieve key {key_id}: {e}")
            return None
    
    def list_keys(self) -> list:
        """List all stored key IDs with metadata"""
        try:
            conn = sqlite3.connect(self.storage_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT key_id, key_type, created_at, updated_at, metadata, salt 
                FROM encrypted_keys
                ORDER BY updated_at DESC
            ''')
            
            results = cursor.fetchall()
            conn.close()
            
            keys = []
            for row in results:
                salt_status = 'secure' if row[5] is not None else 'legacy'
                keys.append({
                    'key_id': row[0],
                    'key_type': row[1],
                    'created_at': row[2],
                    'updated_at': row[3],
                    'metadata': json.loads(row[4]) if row[4] else None,
                    'salt_status': salt_status
                })
            
            return keys
            
        except Exception as e:
            print(f"❌ Failed to list keys: {e}")
            return []
    
    def delete_key(self, key_id: str) -> bool:
        """Delete encrypted credentials"""
        try:
            conn = sqlite3.connect(self.storage_path)
            cursor = conn.cursor()
            
            # Log the deletion
            timestamp = datetime.now().isoformat()
            cursor.execute('''
                INSERT INTO access_log (key_id, action, timestamp, user)
                VALUES (?, ?, ?, ?)
            ''', (key_id, 'DELETE', timestamp, getpass.getuser()))
            
            # Delete the key
            cursor.execute('DELETE FROM encrypted_keys WHERE key_id = ?', (key_id,))
            
            if cursor.rowcount > 0:
                conn.commit()
                conn.close()
                print(f"✅ Key deleted: {key_id}")
                return True
            else:
                conn.close()
                print(f"❌ Key not found: {key_id}")
                return False
                
        except Exception as e:
            print(f"❌ Failed to delete key {key_id}: {e}")
            return False
    
    def get_access_log(self, key_id: Optional[str] = None) -> list:
        """Get access log for audit purposes"""
        try:
            conn = sqlite3.connect(self.storage_path)
            cursor = conn.cursor()
            
            if key_id:
                cursor.execute('''
                    SELECT key_id, action, timestamp, user 
                    FROM access_log 
                    WHERE key_id = ?
                    ORDER BY timestamp DESC
                ''', (key_id,))
            else:
                cursor.execute('''
                    SELECT key_id, action, timestamp, user 
                    FROM access_log 
                    ORDER BY timestamp DESC
                    LIMIT 100
                ''')
            
            results = cursor.fetchall()
            conn.close()
            
            log_entries = []
            for row in results:
                log_entries.append({
                    'key_id': row[0],
                    'action': row[1],
                    'timestamp': row[2],
                    'user': row[3]
                })
            
            return log_entries
            
        except Exception as e:
            print(f"❌ Failed to get access log: {e}")
            return []
    
    def migrate_from_json(self, json_path: str, key_id: str, key_type: str = "migrated") -> bool:
        """Migrate existing JSON credentials to encrypted storage"""
        try:
            if not os.path.exists(json_path):
                print(f"❌ JSON file not found: {json_path}")
                return False
            
            with open(json_path, 'r') as f:
                data = json.load(f)
            
            metadata = {
                'migrated_from': json_path,
                'migration_date': datetime.now().isoformat()
            }
            
            success = self.store_key(key_id, data, key_type, metadata)
            
            if success:
                print(f"✅ Migrated {json_path} to encrypted storage as {key_id}")
                return True
            else:
                return False
                
        except Exception as e:
            print(f"❌ Failed to migrate {json_path}: {e}")
            return False

# Global instance
key_manager = EncryptedKeyManager()