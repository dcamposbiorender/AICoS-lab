#!/usr/bin/env python3
"""
Secure Configuration Loader
Provides encrypted credential access for existing applications
"""

import os
from typing import Dict, Optional
from .key_manager import key_manager

class SecureConfig:
    """Secure configuration loader that replaces plaintext JSON files"""
    
    def __init__(self):
        self.cache = {}
    
    def get_google_apis_config(self) -> Optional[Dict]:
        """Get Google APIs configuration with fallback to original location"""
        if 'google_apis' not in self.cache:
            # Try current location first
            self.cache['google_apis'] = key_manager.retrieve_key('google_apis')
            
            # If not found, try original location
            if not self.cache['google_apis']:
                try:
                    import sys
                    from pathlib import Path
                    
                    # Add original scavenge path
                    scavenge_path = Path(__file__).parent.parent.parent / "scavenge" / "src"
                    sys.path.insert(0, str(scavenge_path))
                    
                    from core.key_manager import EncryptedKeyManager as OriginalKeyManager
                    
                    # Use original database location
                    original_db_path = scavenge_path / "core" / "encrypted_keys.db"
                    original_km = OriginalKeyManager(storage_path=str(original_db_path))
                    
                    original_config = original_km.retrieve_key('google_apis')
                    if original_config:
                        print("✅ Google APIs configuration found in original location")
                        self.cache['google_apis'] = original_config
                    
                except Exception as e:
                    print(f"⚠️ Could not check original Google APIs config: {e}")
                    
        return self.cache['google_apis']
    
    def get_slack_config(self) -> Optional[Dict]:
        """Get Slack configuration with fallback to original location"""
        if 'slack_credentials' not in self.cache:
            # Try current location first
            self.cache['slack_credentials'] = key_manager.retrieve_key('slack_credentials')
            
            # If not found, try original location
            if not self.cache['slack_credentials']:
                try:
                    import sys
                    from pathlib import Path
                    
                    # Add original scavenge path
                    scavenge_path = Path(__file__).parent.parent.parent / "scavenge" / "src"
                    sys.path.insert(0, str(scavenge_path))
                    
                    from core.key_manager import EncryptedKeyManager as OriginalKeyManager
                    
                    # Use original database location
                    original_db_path = scavenge_path / "core" / "encrypted_keys.db"
                    original_km = OriginalKeyManager(storage_path=str(original_db_path))
                    
                    original_creds = original_km.retrieve_key('slack_credentials')
                    if original_creds:
                        print("✅ Slack credentials found in original location")
                        self.cache['slack_credentials'] = original_creds
                    
                except Exception as e:
                    print(f"⚠️ Could not check original Slack credentials: {e}")
                    
        return self.cache['slack_credentials']
    
    def get_oauth_tokens_path(self) -> Optional[str]:
        """Get path to OAuth tokens pickle file"""
        pickle_ref = key_manager.retrieve_key('google_oauth_tokens_pickle')
        if pickle_ref:
            return pickle_ref.get('original_path')
        return None
    
    def clear_cache(self):
        """Clear credential cache (for security)"""
        self.cache.clear()

# Global instance for easy import
secure_config = SecureConfig()

# Legacy compatibility functions
def load_sync_config():
    """Legacy function - returns encrypted Google APIs config"""
    return secure_config.get_google_apis_config()

def load_slack_config():
    """Legacy function - returns encrypted Slack config"""
    return secure_config.get_slack_config()