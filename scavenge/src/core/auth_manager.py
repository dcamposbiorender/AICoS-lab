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
from typing import Dict, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum

# Add credential paths
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "data" / "credentials"))

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

class CredentialVault:
    """
    Unified credential vault that provides single interface for all authentication needs.
    Maintains backward compatibility while centralizing authentication chaos.
    """
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        self.auth_cache = {}
        self.last_cache_update = {}
        
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
        
    def _init_secure_config(self):
        """Initialize secure config system if available"""
        try:
            from secure_config import secure_config
            print("✅ Secure encrypted config system available")
            return secure_config
        except ImportError:
            print("⚠️ Secure config not available, using fallback file system")
            return None
    
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
        if key not in self.last_cache_update:
            return float('inf')
        delta = datetime.now() - self.last_cache_update[key]
        return delta.total_seconds() / 60
    
    def get_slack_bot_token(self) -> Optional[str]:
        """Get Slack bot token with caching and fallback"""
        cache_key = 'slack_bot_token'
        
        # Return cached if fresh (< 30 minutes)
        if cache_key in self.auth_cache and self._cache_key_age(cache_key) < 30:
            return self.auth_cache[cache_key]
        
        # Try secure config first
        if self.secure_config:
            try:
                slack_config = self.secure_config.get_slack_config()
                if slack_config and slack_config.get('bot_token'):
                    token = slack_config['bot_token']
                    self.auth_cache[cache_key] = token
                    self.last_cache_update[cache_key] = datetime.now()
                    print("✅ Slack bot token loaded from secure config")
                    return token
            except Exception as e:
                print(f"⚠️ Secure config slack token failed: {e}")
        
        # Fallback to file system
        config_file = self._find_credential_file('slack_config')
        if config_file:
            config = self._load_json_config(config_file)
            if config and config.get('bot_token'):
                token = config['bot_token']
                self.auth_cache[cache_key] = token
                self.last_cache_update[cache_key] = datetime.now()
                print(f"✅ Slack bot token loaded from {config_file}")
                return token
        
        print("❌ Slack bot token not found")
        return None
    
    def get_slack_user_token(self) -> Optional[str]:
        """Get Slack user token with caching and fallback"""
        cache_key = 'slack_user_token'
        
        # Return cached if fresh
        if cache_key in self.auth_cache and self._cache_key_age(cache_key) < 30:
            return self.auth_cache[cache_key]
        
        # Try secure config first
        if self.secure_config:
            try:
                slack_config = self.secure_config.get_slack_config()
                if slack_config and slack_config.get('user_token'):
                    token = slack_config['user_token']
                    self.auth_cache[cache_key] = token
                    self.last_cache_update[cache_key] = datetime.now()
                    print("✅ Slack user token loaded from secure config")
                    return token
            except Exception as e:
                print(f"⚠️ Secure config slack user token failed: {e}")
        
        # Fallback to file system
        config_file = self._find_credential_file('slack_config')
        if config_file:
            config = self._load_json_config(config_file)
            if config and config.get('user_token'):
                token = config['user_token']
                self.auth_cache[cache_key] = token
                self.last_cache_update[cache_key] = datetime.now()
                print(f"✅ Slack user token loaded from {config_file}")
                return token
        
        print("❌ Slack user token not found")
        return None
    
    def get_google_oauth_credentials(self) -> Optional[Any]:
        """Get Google OAuth credentials with automatic refresh"""
        cache_key = 'google_oauth_creds'
        
        # Return cached if fresh and valid
        if (cache_key in self.auth_cache and 
            self._cache_key_age(cache_key) < 10 and 
            hasattr(self.auth_cache[cache_key], 'valid') and
            self.auth_cache[cache_key].valid):
            return self.auth_cache[cache_key]
        
        # Try secure config first
        if self.secure_config:
            try:
                token_path = self.secure_config.get_oauth_tokens_path()
                if token_path and os.path.exists(token_path):
                    return self._load_google_credentials_from_pickle(token_path)
            except Exception as e:
                print(f"⚠️ Secure config Google OAuth failed: {e}")
        
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
                self.auth_cache[cache_key] = credentials
                self.last_cache_update[cache_key] = datetime.now()
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
        
        # Return cached if fresh
        if cache_key in self.auth_cache and self._cache_key_age(cache_key) < 60:
            return self.auth_cache[cache_key]
        
        # Try secure config first
        if self.secure_config:
            try:
                config = self.secure_config.get_google_apis_config()
                if config:
                    self.auth_cache[cache_key] = config
                    self.last_cache_update[cache_key] = datetime.now()
                    print("✅ Google config loaded from secure config")
                    return config
            except Exception as e:
                print(f"⚠️ Secure config Google config failed: {e}")
        
        # Fallback to file system
        config_file = self._find_credential_file('google_config')
        if config_file:
            config = self._load_json_config(config_file)
            if config:
                self.auth_cache[cache_key] = config
                self.last_cache_update[cache_key] = datetime.now()
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
            'google_oauth': bool(self.get_google_oauth_credentials()),
            'google_config': bool(self.get_google_config())
        }
        
        print("\n🔍 AUTHENTICATION VALIDATION:")
        for auth_type, is_valid in validation_results.items():
            status = "✅" if is_valid else "❌"
            print(f"  {status} {auth_type}")
        
        return validation_results
    
    def clear_cache(self):
        """Clear authentication cache for security"""
        self.auth_cache.clear()
        self.last_cache_update.clear()
        if self.secure_config:
            self.secure_config.clear_cache()
        print("🧹 Authentication cache cleared")

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
                'workspace_url': 'https://biorender.slack.com',
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