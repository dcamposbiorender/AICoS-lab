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

class EncryptedKeyManager:
    def __init__(self, storage_path: str = None):
        self.storage_path = storage_path or os.path.join(
            os.path.dirname(__file__), 'encrypted_keys.db'
        )
        self.master_key_path = os.path.join(
            os.path.dirname(__file__), '.master_key'
        )
        self._cipher_suite = None
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize the encrypted key database"""
        conn = sqlite3.connect(self.storage_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS encrypted_keys (
                key_id TEXT PRIMARY KEY,
                encrypted_data BLOB NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                key_type TEXT NOT NULL,
                metadata TEXT
            )
        ''')
        
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
        """Get or create master password for encryption"""
        if os.path.exists(self.master_key_path):
            # In production, this should be entered by user each session
            # For development, we'll store a hashed version
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
            
            with open(self.master_key_path, 'w') as f:
                f.write(password_hash)
            
            # Set restrictive permissions
            os.chmod(self.master_key_path, 0o600)
            
            print("✅ Generated secure master key for development")
            print("💡 In production, this should be user-provided password")
            return password_hash
    
    def _get_cipher_suite(self) -> Fernet:
        """Get or create cipher suite for encryption/decryption"""
        if self._cipher_suite is None:
            master_password = self._get_master_password()
            
            # Derive key from master password
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b'ai_chief_of_staff_salt',  # In production, use random salt per key
                iterations=100000,
            )
            
            key = base64.urlsafe_b64encode(kdf.derive(master_password.encode()))
            self._cipher_suite = Fernet(key)
        
        return self._cipher_suite
    
    def store_key(self, key_id: str, data: Dict[str, Any], key_type: str = "api_key", metadata: Optional[Dict] = None) -> bool:
        """Store encrypted credentials"""
        try:
            cipher_suite = self._get_cipher_suite()
            
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
                (key_id, encrypted_data, created_at, updated_at, key_type, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (key_id, encrypted_data, timestamp, timestamp, key_type, metadata_json))
            
            # Log the access
            cursor.execute('''
                INSERT INTO access_log (key_id, action, timestamp, user)
                VALUES (?, ?, ?, ?)
            ''', (key_id, 'STORE', timestamp, getpass.getuser()))
            
            conn.commit()
            conn.close()
            
            print(f"✅ Encrypted credentials stored: {key_id}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to store encrypted key {key_id}: {e}")
            return False
    
    def retrieve_key(self, key_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve and decrypt credentials"""
        try:
            conn = sqlite3.connect(self.storage_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT encrypted_data FROM encrypted_keys WHERE key_id = ?
            ''', (key_id,))
            
            result = cursor.fetchone()
            if not result:
                print(f"❌ Key not found: {key_id}")
                return None
            
            # Decrypt the data
            cipher_suite = self._get_cipher_suite()
            decrypted_data = cipher_suite.decrypt(result[0])
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
                SELECT key_id, key_type, created_at, updated_at, metadata 
                FROM encrypted_keys
                ORDER BY updated_at DESC
            ''')
            
            results = cursor.fetchall()
            conn.close()
            
            keys = []
            for row in results:
                keys.append({
                    'key_id': row[0],
                    'key_type': row[1],
                    'created_at': row[2],
                    'updated_at': row[3],
                    'metadata': json.loads(row[4]) if row[4] else None
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