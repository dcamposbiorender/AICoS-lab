#!/usr/bin/env python3
"""
Secure Configuration Loader
Provides encrypted credential access for existing applications
"""

import os
from typing import Dict, Optional
from key_manager import key_manager

class SecureConfig:
    """Secure configuration loader that replaces plaintext JSON files"""
    
    def __init__(self):
        self.cache = {}
    
    def get_google_apis_config(self) -> Optional[Dict]:
        """Get Google APIs configuration (replaces sync_config.json)"""
        if 'google_apis' not in self.cache:
            self.cache['google_apis'] = key_manager.retrieve_key('google_apis')
        return self.cache['google_apis']
    
    def get_slack_config(self) -> Optional[Dict]:
        """Get Slack configuration (replaces slack_config.json)"""
        if 'slack_credentials' not in self.cache:
            self.cache['slack_credentials'] = key_manager.retrieve_key('slack_credentials')
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
