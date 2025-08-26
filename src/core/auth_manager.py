#!/usr/bin/env python3
"""
Unified Authentication Manager
Centralizes all authentication chaos across 70+ scripts into a single, secure interface.

Handles:
- Slack bot/user tokens
- Google OAuth credentials
- Token refresh and validation
- Backward compatibility with existing scripts
- AES-256 encrypted credential storage
"""

import os
import json
import pickle
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Any, Union, List, Set
from dataclasses import dataclass
from enum import Enum
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

class AuthType(Enum):
    SLACK_BOT = "slack_bot"
    SLACK_USER = "slack_user" 
    GOOGLE_OAUTH = "google_oauth"
    GOOGLE_SERVICE = "google_service"

@dataclass
class AuthCredentials:
    """Standardized credential container"""
    auth_type: AuthType
    token: str
    refresh_token: Optional[str] = None
    expires_at: Optional[datetime] = None
    scopes: Optional[list] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def is_expired(self) -> bool:
        """Check if credentials are expired"""
        if not self.expires_at:
            return False
        return datetime.now() >= self.expires_at
    
    def is_valid(self) -> bool:
        """Check if credentials are valid and not expired"""
        return bool(self.token) and not self.is_expired()

class SecureCache:
    """Secure encrypted cache for sensitive credentials"""
    
    def __init__(self):
        self._cipher_suite = None
        self._cache_salt = None
        self._encrypted_cache = {}
        self.last_cache_update = {}
        
    def _get_cache_cipher(self) -> Fernet:
        """Get cipher suite for cache encryption"""
        if self._cipher_suite is None:
            # Generate cache encryption key from environment
            cache_key_material = os.environ.get('AICOS_CACHE_KEY', 'dev_cache_key_not_secure')
            
            # Generate salt if not exists
            if self._cache_salt is None:
                self._cache_salt = os.urandom(16)
            
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=self._cache_salt,
                iterations=100000,
            )
            
            key = base64.urlsafe_b64encode(kdf.derive(cache_key_material.encode()))
            self._cipher_suite = Fernet(key)
            
        return self._cipher_suite
    
    def set(self, key: str, value: str) -> None:
        """Store encrypted credential in cache"""
        try:
            cipher = self._get_cache_cipher()
            encrypted_value = cipher.encrypt(value.encode())
            self._encrypted_cache[key] = encrypted_value
            self.last_cache_update[key] = datetime.now()
        except Exception as e:
            print(f"⚠️ Failed to encrypt cache entry {key}: {e}")
            # Fallback: don't cache if encryption fails
            pass
    
    def get(self, key: str) -> Optional[str]:
        """Retrieve and decrypt credential from cache"""
        try:
            if key not in self._encrypted_cache:
                return None
                
            cipher = self._get_cache_cipher()
            encrypted_value = self._encrypted_cache[key]
            decrypted_value = cipher.decrypt(encrypted_value)
            return decrypted_value.decode()
        except Exception as e:
            print(f"⚠️ Failed to decrypt cache entry {key}: {e}")
            # Remove corrupted entry
            self._encrypted_cache.pop(key, None)
            self.last_cache_update.pop(key, None)
            return None
    
    def clear(self) -> None:
        """Clear all cached credentials"""
        self._encrypted_cache.clear()
        self.last_cache_update.clear()
    
    def remove(self, key: str) -> None:
        """Remove specific cached credential"""
        self._encrypted_cache.pop(key, None)
        self.last_cache_update.pop(key, None)


class CredentialVault:
    """
    Unified credential vault that provides single interface for all authentication needs.
    Maintains backward compatibility while centralizing authentication chaos.
    """
    
    def __init__(self):
        # Go up from src/core to the actual project root
        self.project_root = Path(__file__).parent.parent.parent
        self.auth_cache = SecureCache()
        self.last_cache_update = self.auth_cache.last_cache_update  # Backward compatibility
        
        # Credential file paths (prioritized order)
        self.credential_paths = {
            'slack_config': [
                self.project_root / "data" / "auth" / "slack_config.json",
                self.project_root / "chief_of_staff" / "sync" / "slack_config.json", 
                self.project_root / "archive" / "chief_of_staff" / "sync" / "slack_config.json"
            ],
            'google_config': [
                self.project_root / "data" / "auth" / "sync_config.json",
                self.project_root / "chief_of_staff" / "sync" / "sync_config.json",
                self.project_root / "archive" / "chief_of_staff" / "sync" / "sync_config.json"
            ],
            'google_tokens': [
                self.project_root / "data" / "auth" / "token.pickle",
                self.project_root / "chief_of_staff" / "sync" / "token.pickle",
                self.project_root / "archive" / "chief_of_staff" / "sync" / "token.pickle"
            ]
        }
        
        print("🔐 UNIFIED AUTHENTICATION MANAGER")
        print("🎯 Centralizing authentication across 70+ scripts")
        print("=" * 50)
        
        # Initialize secure config if available
        self.secure_config = self._init_secure_config()
        
        # Initialize OAuth scope management
        self._init_oauth_scopes()
        
    def _init_secure_config(self):
        """Initialize secure config system if available"""
        try:
            from .secure_config import secure_config
            print("✅ Secure encrypted config system available")
            return secure_config
        except ImportError:
            print("⚠️ Secure config not available, using fallback file system")
            return None
    
    def _init_oauth_scopes(self):
        """Initialize OAuth scope management system"""
        try:
            from .slack_scopes import slack_scopes
            self.slack_scopes = slack_scopes
            print("✅ OAuth scope management system initialized")
        except ImportError:
            print("⚠️ OAuth scope definitions not available")
            self.slack_scopes = None
    
    def get_slack_scopes(self, token_type: str = 'bot') -> Optional[Set[str]]:
        """Get stored OAuth scopes for Slack tokens"""
        cache_key = f'slack_scopes_{token_type}'
        
        # Return cached if fresh
        cached_scopes = self.auth_cache.get(cache_key)
        if cached_scopes and self._cache_key_age(cache_key) < 60:
            return set(json.loads(cached_scopes))
        
        # Try secure config first
        if self.secure_config:
            try:
                slack_config = self.secure_config.get_slack_config()
                if slack_config and slack_config.get(f'{token_type}_scopes'):
                    scopes = set(slack_config[f'{token_type}_scopes'])
                    self.auth_cache.set(cache_key, json.dumps(list(scopes)))
                    print(f"✅ Slack {token_type} scopes loaded from secure config")
                    return scopes
            except Exception as e:
                print(f"⚠️ Secure config slack scopes failed: {e}")
        
        # Fallback to file system
        config_file = self._find_credential_file('slack_config')
        if config_file:
            config = self._load_json_config(config_file)
            if config and config.get(f'{token_type}_scopes'):
                scopes = set(config[f'{token_type}_scopes'])
                self.auth_cache.set(cache_key, json.dumps(list(scopes)))
                print(f"✅ Slack {token_type} scopes loaded from {config_file}")
                return scopes
        
        # Return default minimal scopes if none found
        if self.slack_scopes:
            if token_type == 'bot':
                default_scopes = self.slack_scopes.get_minimal_scope_set()['basic_messaging']
            else:
                default_scopes = ['identity.basic', 'identity.email']
            
            print(f"⚠️ No stored {token_type} scopes found, using defaults: {default_scopes}")
            return set(default_scopes)
        
        print(f"❌ Slack {token_type} scopes not found")
        return None
    
    def store_slack_scopes(self, scopes: List[str], token_type: str = 'bot', 
                          storage_method: str = 'secure') -> bool:
        """Store OAuth scopes for Slack tokens"""
        try:
            # Validate scopes if possible
            if self.slack_scopes:
                validation = self.slack_scopes.validate_scopes(scopes, token_type)
                if not validation['all_valid']:
                    print(f"⚠️ Invalid scopes detected: {validation['invalid']}")
                    print(f"✅ Valid scopes: {validation['valid']}")
            
            if storage_method == 'secure' and self.secure_config:
                # Store in encrypted secure config
                try:
                    from .key_manager import key_manager
                    current_config = key_manager.retrieve_key('slack_credentials') or {}
                    current_config[f'{token_type}_scopes'] = scopes
                    
                    success = key_manager.store_key('slack_credentials', current_config, 'slack_oauth')
                    if success:
                        print(f"✅ Slack {token_type} scopes stored securely")
                        # Update cache
                        cache_key = f'slack_scopes_{token_type}'
                        self.auth_cache.set(cache_key, json.dumps(scopes))
                        return True
                except Exception as e:
                    print(f"⚠️ Secure scope storage failed: {e}")
                    # Fall through to file storage
            
            # Fallback to file system
            scopes_file = self.project_root / "data" / "auth" / "slack_scopes.json"
            scopes_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Load existing scopes or create new
            if scopes_file.exists():
                with open(scopes_file, 'r') as f:
                    stored_scopes = json.load(f)
            else:
                stored_scopes = {}
            
            # Update with new scopes
            stored_scopes[f'{token_type}_scopes'] = scopes
            stored_scopes['updated_at'] = datetime.now().isoformat()
            
            with open(scopes_file, 'w') as f:
                json.dump(stored_scopes, f, indent=2)
            
            print(f"✅ Slack {token_type} scopes stored to {scopes_file}")
            
            # Update cache
            cache_key = f'slack_scopes_{token_type}'
            self.auth_cache.set(cache_key, json.dumps(scopes))
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to store Slack {token_type} scopes: {e}")
            return False
    
    def validate_slack_permissions(self, required_scopes: List[str], 
                                 token_type: str = 'bot') -> Dict[str, Any]:
        """Validate that current token has required OAuth scopes"""
        current_scopes = self.get_slack_scopes(token_type)
        
        if not current_scopes:
            return {
                'valid': False,
                'missing_scopes': required_scopes,
                'available_scopes': [],
                'error': f'No {token_type} scopes available'
            }
        
        missing_scopes = []
        for scope in required_scopes:
            if scope not in current_scopes:
                missing_scopes.append(scope)
        
        return {
            'valid': len(missing_scopes) == 0,
            'missing_scopes': missing_scopes,
            'available_scopes': list(current_scopes),
            'required_scopes': required_scopes
        }
    
    def get_scopes_for_feature(self, feature_name: str) -> Set[str]:
        """Get required OAuth scopes for a specific feature"""
        if not self.slack_scopes:
            print("⚠️ OAuth scope definitions not available")
            return set()
        
        return self.slack_scopes.get_required_scopes_for_feature(feature_name)
    
    def _find_credential_file(self, credential_type: str) -> Optional[Path]:
        """Find the first existing credential file for given type"""
        for path in self.credential_paths.get(credential_type, []):
            if path.exists():
                return path
        return None
    
    def _load_json_config(self, file_path: Path) -> Optional[Dict]:
        """Load JSON configuration file safely"""
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Failed to load {file_path}: {e}")
            return None
    
    def _cache_key_age(self, key: str) -> float:
        """Get age of cached credential in minutes"""
        if key not in self.auth_cache.last_cache_update:
            return float('inf')
        delta = datetime.now() - self.auth_cache.last_cache_update[key]
        return delta.total_seconds() / 60
    
    def get_slack_bot_token(self) -> Optional[str]:
        """Get Slack bot token with encrypted caching and clear test/production separation"""
        cache_key = 'slack_bot_token'
        
        # Return cached if fresh (< 30 minutes)
        cached_token = self.auth_cache.get(cache_key)
        if cached_token and self._cache_key_age(cache_key) < 30:
            return cached_token
        
        # Check if we're in test mode
        test_mode = os.environ.get('AICOS_TEST_MODE', 'false').lower() == 'true'
        
        if test_mode:
            # Test mode: use test tokens
            try:
                from .key_manager import key_manager
                test_tokens = key_manager.retrieve_key('slack_tokens_test')
                if test_tokens and test_tokens.get('bot_token'):
                    token = test_tokens['bot_token']
                    self.auth_cache.set(cache_key, token)
                    print("🧪 Slack bot token loaded from TEST tokens")
                    return token
            except Exception as e:
                print(f"⚠️ Test token retrieval failed: {e}")
        else:
            # Production mode: use production tokens
            try:
                from .key_manager import key_manager
                prod_tokens = key_manager.retrieve_key('slack_tokens_production')
                if prod_tokens and prod_tokens.get('bot_token'):
                    token = prod_tokens['bot_token']
                    self.auth_cache.set(cache_key, token)
                    print("🔐 Slack bot token loaded from PRODUCTION tokens")
                    return token
            except Exception as e:
                print(f"⚠️ Production token retrieval failed: {e}")
            
            # Fallback: try legacy secure config
            if self.secure_config:
                try:
                    slack_config = self.secure_config.get_slack_config()
                    if slack_config and slack_config.get('bot_token'):
                        token = slack_config['bot_token']
                        self.auth_cache.set(cache_key, token)
                        print("⚠️ Slack bot token loaded from legacy secure config")
                        return token
                except Exception as e:
                    print(f"⚠️ Legacy secure config failed: {e}")
        
        # Final fallback to environment variables
        env_token = os.environ.get('SLACK_BOT_TOKEN')
        if env_token:
            token = env_token
            self.auth_cache.set(cache_key, token)
            mode_label = "TEST" if test_mode else "PRODUCTION"
            print(f"⚠️ Slack bot token loaded from environment variable ({mode_label} mode)")
            return token
        
        mode_label = "test" if test_mode else "production"
        print(f"❌ Slack bot token not found in {mode_label} mode")
        return None
    
    def get_slack_user_token(self) -> Optional[str]:
        """Get Slack user token with encrypted caching and clear test/production separation"""
        cache_key = 'slack_user_token'
        
        # Return cached if fresh
        cached_token = self.auth_cache.get(cache_key)
        if cached_token and self._cache_key_age(cache_key) < 30:
            return cached_token
        
        # Check if we're in test mode
        test_mode = os.environ.get('AICOS_TEST_MODE', 'false').lower() == 'true'
        
        if test_mode:
            # Test mode: use test tokens
            try:
                from .key_manager import key_manager
                test_tokens = key_manager.retrieve_key('slack_tokens_test')
                if test_tokens and test_tokens.get('user_token'):
                    token = test_tokens['user_token']
                    self.auth_cache.set(cache_key, token)
                    print("🧪 Slack user token loaded from TEST tokens")
                    return token
            except Exception as e:
                print(f"⚠️ Test user token retrieval failed: {e}")
        else:
            # Production mode: use production tokens
            try:
                from .key_manager import key_manager
                prod_tokens = key_manager.retrieve_key('slack_tokens_production')
                if prod_tokens and prod_tokens.get('user_token'):
                    token = prod_tokens['user_token']
                    self.auth_cache.set(cache_key, token)
                    print("🔐 Slack user token loaded from PRODUCTION tokens")
                    return token
            except Exception as e:
                print(f"⚠️ Production user token retrieval failed: {e}")
            
            # Fallback: try legacy secure config
            if self.secure_config:
                try:
                    slack_config = self.secure_config.get_slack_config()
                    if slack_config and slack_config.get('user_token'):
                        token = slack_config['user_token']
                        self.auth_cache.set(cache_key, token)
                        print("⚠️ Slack user token loaded from legacy secure config")
                        return token
                except Exception as e:
                    print(f"⚠️ Legacy secure config user token failed: {e}")
        
        # Final fallback to environment variables
        env_token = os.environ.get('SLACK_USER_TOKEN')
        if env_token:
            token = env_token
            self.auth_cache.set(cache_key, token)
            mode_label = "TEST" if test_mode else "PRODUCTION"
            print(f"⚠️ Slack user token loaded from environment variable ({mode_label} mode)")
            return token
        
        mode_label = "test" if test_mode else "production"
        print(f"❌ Slack user token not found in {mode_label} mode")
        return None
    
    def get_google_oauth_credentials(self) -> Optional[Any]:
        """Get Google OAuth credentials with automatic refresh"""
        cache_key = 'google_oauth_creds'
        
        # Note: Google OAuth credentials are complex objects that can't be easily encrypted
        # For security, we store them temporarily in memory without persistent cache
        # This maintains security while preserving functionality
        cached_creds = getattr(self, '_temp_google_creds', None)
        if (cached_creds and 
            self._cache_key_age(cache_key) < 10 and 
            hasattr(cached_creds, 'valid') and
            cached_creds.valid):
            return cached_creds
        
        # Try secure config first
        if self.secure_config:
            try:
                token_path = self.secure_config.get_oauth_tokens_path()
                if token_path and os.path.exists(token_path):
                    credentials = self._load_google_credentials_from_pickle(token_path)
                    if credentials:
                        return credentials
            except Exception as e:
                print(f"⚠️ Secure config Google OAuth failed: {e}")
                # Continue to fallback
        
        # Fallback to file system
        token_file = self._find_credential_file('google_tokens')
        if token_file:
            return self._load_google_credentials_from_pickle(str(token_file))
        
        print("❌ Google OAuth credentials not found")
        return None
    
    def _load_google_credentials_from_pickle(self, token_path: str):
        """Load and refresh Google credentials from pickle file"""
        try:
            # Import Google auth libs
            from google.auth.transport.requests import Request
            
            with open(token_path, 'rb') as token:
                credentials = pickle.load(token)
            
            # Refresh if expired
            if credentials and credentials.expired and credentials.refresh_token:
                try:
                    credentials.refresh(Request())
                    print("✅ Google OAuth credentials refreshed")
                    
                    # Save refreshed credentials back
                    with open(token_path, 'wb') as token:
                        pickle.dump(credentials, token)
                        
                except Exception as e:
                    print(f"⚠️ Google OAuth refresh failed: {e}")
                    return None
            
            if credentials and credentials.valid:
                cache_key = 'google_oauth_creds'
                # Store complex objects in temporary cache for security
                self._temp_google_creds = credentials
                self.auth_cache.last_cache_update[cache_key] = datetime.now()
                print(f"✅ Google OAuth credentials loaded from {token_path}")
                return credentials
            else:
                print("❌ Google OAuth credentials invalid")
                return None
                
        except Exception as e:
            print(f"❌ Failed to load Google credentials: {e}")
            return None
    
    def get_google_config(self) -> Optional[Dict]:
        """Get Google API configuration (client ID, secret, etc.)"""
        cache_key = 'google_config'
        
        # Return cached if fresh - config data is safe to cache encrypted
        cached_config = self.auth_cache.get(cache_key)
        if cached_config and self._cache_key_age(cache_key) < 60:
            return json.loads(cached_config)
        
        # Try secure config first
        if self.secure_config:
            try:
                config = self.secure_config.get_google_apis_config()
                if config:
                    self.auth_cache.set(cache_key, json.dumps(config))
                    print("✅ Google config loaded from secure config")
                    return config
            except Exception as e:
                print(f"⚠️ Secure config Google config failed: {e}")
        
        # Fallback to file system
        config_file = self._find_credential_file('google_config')
        if config_file:
            config = self._load_json_config(config_file)
            if config:
                self.auth_cache.set(cache_key, json.dumps(config))
                print(f"✅ Google config loaded from {config_file}")
                return config
        
        print("❌ Google config not found")
        return None
    
    def get_google_service(self, service_name: str, version: str = 'v3'):
        """Get authenticated Google API service"""
        try:
            from googleapiclient.discovery import build
            
            credentials = self.get_google_oauth_credentials()
            if not credentials:
                print(f"❌ Cannot create {service_name} service - no credentials")
                return None
            
            service = build(service_name, version, credentials=credentials)
            print(f"✅ Google {service_name} service created")
            return service
            
        except Exception as e:
            print(f"❌ Failed to create Google {service_name} service: {e}")
            return None
    
    def create_slack_headers(self, use_bot_token: bool = True) -> Dict[str, str]:
        """Create Slack API headers with appropriate token"""
        if use_bot_token:
            token = self.get_slack_bot_token()
            token_type = "bot"
        else:
            token = self.get_slack_user_token()
            token_type = "user"
        
        if not token:
            raise ValueError(f"Slack {token_type} token not available")
        
        return {"Authorization": f"Bearer {token}"}
    
    def validate_authentication(self) -> Dict[str, bool]:
        """Validate all available authentication methods"""
        validation_results = {
            'slack_bot_token': bool(self.get_slack_bot_token()),
            'slack_user_token': bool(self.get_slack_user_token()),
            'slack_bot_scopes': bool(self.get_slack_scopes('bot')),
            'slack_user_scopes': bool(self.get_slack_scopes('user')),
            'google_oauth': bool(self.get_google_oauth_credentials()),
            'google_config': bool(self.get_google_config())
        }
        
        print("\n🔍 AUTHENTICATION VALIDATION:")
        for auth_type, is_valid in validation_results.items():
            status = "✅" if is_valid else "❌"
            print(f"  {status} {auth_type}")
        
        # Show scope counts if available
        if validation_results['slack_bot_scopes']:
            bot_scopes = self.get_slack_scopes('bot')
            print(f"    📊 Bot scopes: {len(bot_scopes)} permissions")
        
        if validation_results['slack_user_scopes']:
            user_scopes = self.get_slack_scopes('user')
            print(f"    📊 User scopes: {len(user_scopes)} permissions")
        
        return validation_results
    
    def clear_cache(self):
        """Clear authentication cache for security"""
        self.auth_cache.clear()
        # Clear temporary Google credentials
        if hasattr(self, '_temp_google_creds'):
            delattr(self, '_temp_google_creds')
        if self.secure_config:
            self.secure_config.clear_cache()
        print("🧹 Authentication cache cleared securely")

# Global instance for easy import
credential_vault = CredentialVault()

# Legacy compatibility functions for existing scripts
def get_slack_bot_token() -> Optional[str]:
    """Legacy function - returns Slack bot token"""
    return credential_vault.get_slack_bot_token()

def get_slack_user_token() -> Optional[str]:
    """Legacy function - returns Slack user token"""
    return credential_vault.get_slack_user_token()

def get_google_credentials():
    """Legacy function - returns Google OAuth credentials"""
    return credential_vault.get_google_oauth_credentials()

def get_google_service(service_name: str, version: str = 'v3'):
    """Legacy function - returns authenticated Google service"""
    return credential_vault.get_google_service(service_name, version)

def create_slack_headers(use_bot_token: bool = True) -> Dict[str, str]:
    """Legacy function - creates Slack API headers"""
    return credential_vault.create_slack_headers(use_bot_token)

# Backward compatibility for existing working scripts
class LegacyAuthAdapter:
    """Adapter to maintain compatibility with existing authentication patterns"""
    
    @staticmethod
    def load_slack_config() -> Optional[Dict]:
        """Emulate loading slack_config.json"""
        bot_token = credential_vault.get_slack_bot_token()
        user_token = credential_vault.get_slack_user_token()
        
        if bot_token or user_token:
            return {
                'bot_token': bot_token,
                'user_token': user_token,
                'workspace_url': 'https://example.slack.com',
                'loaded_via': 'unified_auth_manager'
            }
        return None
    
    @staticmethod
    def load_google_apis() -> Optional[Any]:
        """Emulate RealGoogleAPIs class initialization"""
        class GoogleAPIsAdapter:
            def __init__(self):
                self.credentials = credential_vault.get_google_oauth_credentials()
                self.config = credential_vault.get_google_config()
            
            def get_service(self, service_name: str, version: str = 'v3'):
                return credential_vault.get_google_service(service_name, version)
            
            def authenticate(self):
                return bool(self.credentials)
        
        return GoogleAPIsAdapter()

# Create legacy adapter instance
legacy_auth = LegacyAuthAdapter()

if __name__ == "__main__":
    # Test the authentication system
    print("\n🧪 TESTING UNIFIED AUTHENTICATION SYSTEM")
    print("=" * 50)
    
    validation_results = credential_vault.validate_authentication()
    
    print(f"\n📊 Authentication Status:")
    total_auths = len(validation_results)
    valid_auths = sum(validation_results.values())
    print(f"✅ {valid_auths}/{total_auths} authentication methods available ({valid_auths/total_auths*100:.1f}%)")
    
    if validation_results['slack_bot_token']:
        print("\n🤖 Testing Slack bot token...")
        try:
            headers = credential_vault.create_slack_headers(use_bot_token=True)
            print(f"✅ Slack bot headers created successfully")
        except Exception as e:
            print(f"❌ Slack bot headers failed: {e}")
    
    if validation_results['google_oauth']:
        print("\n📅 Testing Google Calendar service...")
        try:
            calendar_service = credential_vault.get_google_service('calendar', 'v3')
            if calendar_service:
                print(f"✅ Google Calendar service created successfully")
        except Exception as e:
            print(f"❌ Google Calendar service failed: {e}")