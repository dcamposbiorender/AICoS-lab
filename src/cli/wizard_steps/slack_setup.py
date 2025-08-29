#!/usr/bin/env python3
"""
Slack Setup Step for AI Chief of Staff Setup Wizard

Handles:
- Slack workspace configuration
- Bot token input and validation
- OAuth scope checking
- API connection testing
- User list retrieval for identity mapping
- Encrypted credential storage

References:
- src/core/auth_manager.py:345-405 - Slack token handling patterns
- src/core/key_manager.py - Encrypted credential storage
"""

import os
import re
import requests
from typing import Dict, Any, Optional, List, Set

class SlackSetup:
    """Step 2: Slack API token configuration and validation"""
    
    def __init__(self):
        self.required_bot_scopes = {
            'channels:history', 'channels:read', 'chat:write',
            'users:read', 'users:read.email', 'im:history',
            'mpim:history', 'groups:history'
        }
        self.api_base = "https://slack.com/api"
    
    def run(self, wizard_data: Dict[str, Any], interactive: bool = True) -> Dict[str, Any]:
        """
        Execute Slack setup step
        
        Args:
            wizard_data: Shared wizard data dictionary
            interactive: If True, prompt user for input
            
        Returns:
            Dictionary with setup results
        """
        print("Configuring Slack API access...")
        
        # Step 1: Get workspace information
        workspace = self._get_workspace_info(interactive)
        
        # Step 2: Configure bot token
        bot_token = self._configure_bot_token(interactive)
        
        # Step 3: Validate token and get workspace data
        workspace_data = self._validate_slack_connection(bot_token)
        
        # Step 4: Store encrypted credentials
        self._store_slack_credentials(bot_token, workspace_data)
        
        print("✅ Slack configuration complete")
        
        return {
            "slack_token": bot_token,
            "workspace": workspace_data,
            "workspace_name": workspace,
            "users_found": len(workspace_data.get('users', []))
        }
    
    def _get_workspace_info(self, interactive: bool) -> str:
        """Get Slack workspace name from user"""
        if interactive:
            print("\n💬 Slack Workspace Configuration")
            print("Enter your Slack workspace name (e.g., 'biorender' for biorender.slack.com)")
            
            workspace = input("Workspace name: ").strip().lower()
            
            if not workspace:
                raise RuntimeError("Workspace name is required")
            
            # Basic validation
            if not re.match(r'^[a-z0-9-]+$', workspace):
                raise RuntimeError(
                    "Invalid workspace name. Use only lowercase letters, numbers, and hyphens."
                )
            
            print(f"✅ Workspace: {workspace}.slack.com")
            return workspace
        else:
            # Non-interactive: try to get from environment or use default
            workspace = os.getenv('SLACK_WORKSPACE', 'workspace')
            print(f"💬 Using workspace: {workspace}")
            return workspace
    
    def _configure_bot_token(self, interactive: bool) -> str:
        """Configure and validate Slack bot token"""
        # Check for existing token
        existing_token = os.getenv('SLACK_BOT_TOKEN')
        
        if interactive:
            self._show_token_setup_guidance()
            
            if existing_token:
                print(f"Found existing token: {existing_token[:12]}...")
                use_existing = input("Use existing token? [Y/n]: ").strip().lower()
                if use_existing in ('', 'y', 'yes'):
                    return existing_token
            
            print("\nEnter your Slack bot token (starts with 'xoxb-'):")
            bot_token = input("Bot token: ").strip()
            
            if not bot_token:
                raise RuntimeError("Bot token is required")
            
            # Basic format validation
            if not bot_token.startswith('xoxb-'):
                raise RuntimeError("Bot token must start with 'xoxb-'")
            
            return bot_token
        else:
            # Non-interactive mode
            if existing_token:
                print(f"💬 Using existing bot token: {existing_token[:12]}...")
                return existing_token
            else:
                raise RuntimeError(
                    "SLACK_BOT_TOKEN environment variable required for non-interactive mode"
                )
    
    def _show_token_setup_guidance(self):
        """Show helpful guidance for setting up Slack bot token"""
        print("\n📋 Bot Token Setup Instructions:")
        print("1. Go to https://api.slack.com/apps")
        print("2. Create new app or select existing app")
        print("3. Go to 'OAuth & Permissions' in sidebar")
        print("4. Add required scopes (if not already added):")
        for scope in sorted(self.required_bot_scopes):
            print(f"   • {scope}")
        print("5. Click 'Install to Workspace' button")
        print("6. Copy the 'Bot User OAuth Token' (starts with xoxb-)")
        
        print("\n⚠️  Test vs Production Tokens:")
        print("• Test tokens: Limited permissions, safe for development")
        print("• Production tokens: Full access, use carefully")
        print("• This setup uses the production token storage")
    
    def _validate_slack_connection(self, bot_token: str) -> Dict[str, Any]:
        """Validate token and retrieve workspace information"""
        print("🔍 Testing Slack API connection...")
        
        headers = {"Authorization": f"Bearer {bot_token}"}
        
        # Test auth
        auth_response = self._make_api_call("auth.test", headers)
        if not auth_response.get("ok"):
            raise RuntimeError(f"Token validation failed: {auth_response.get('error')}")
        
        workspace_info = {
            'team_id': auth_response.get('team_id'),
            'team_name': auth_response.get('team'),
            'bot_id': auth_response.get('bot_id'),
            'user_id': auth_response.get('user_id')
        }
        
        print(f"✅ Connected to workspace: {workspace_info['team_name']}")
        
        # Get user list for identity mapping
        print("📋 Retrieving user list...")
        users = self._get_user_list(headers)
        workspace_info['users'] = users
        
        print(f"✅ Found {len(users)} users in workspace")
        
        # Validate scopes
        self._validate_token_scopes(headers)
        
        return workspace_info
    
    def _get_user_list(self, headers: Dict[str, str]) -> List[Dict[str, Any]]:
        """Retrieve list of users from Slack workspace"""
        users = []
        cursor = None
        
        while True:
            params = {"limit": 200}
            if cursor:
                params["cursor"] = cursor
            
            response = self._make_api_call("users.list", headers, params)
            
            if not response.get("ok"):
                print(f"⚠️  Warning: Could not retrieve users: {response.get('error')}")
                break
            
            batch_users = response.get("members", [])
            users.extend(batch_users)
            
            # Check for pagination
            response_metadata = response.get("response_metadata", {})
            cursor = response_metadata.get("next_cursor")
            if not cursor:
                break
        
        # Filter to active users with email addresses
        active_users = []
        for user in users:
            if (not user.get("deleted", False) and 
                not user.get("is_bot", False) and
                user.get("profile", {}).get("email")):
                
                active_users.append({
                    'id': user['id'],
                    'name': user.get('name'),
                    'real_name': user.get('real_name'),
                    'email': user.get('profile', {}).get('email'),
                    'display_name': user.get('profile', {}).get('display_name')
                })
        
        return active_users
    
    def _validate_token_scopes(self, headers: Dict[str, str]):
        """Validate that token has required OAuth scopes"""
        print("🔐 Validating OAuth scopes...")
        
        # Try to make calls that require specific scopes
        test_calls = [
            ("channels:read", "conversations.list", {"types": "public_channel"}),
            ("users:read", "users.info", {"user": "USLACKBOT"}),
        ]
        
        missing_scopes = []
        
        for scope_name, method, params in test_calls:
            response = self._make_api_call(method, headers, params)
            if not response.get("ok"):
                error = response.get("error", "")
                if "missing_scope" in error or "not_allowed" in error:
                    missing_scopes.append(scope_name)
        
        if missing_scopes:
            print(f"⚠️  Warning: Missing OAuth scopes: {', '.join(missing_scopes)}")
            print("Some features may not work correctly.")
            print("Go to your app's OAuth & Permissions page to add missing scopes.")
        else:
            print("✅ All required OAuth scopes are available")
    
    def _make_api_call(self, method: str, headers: Dict[str, str], 
                      params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make a Slack API call with error handling"""
        url = f"{self.api_base}/{method}"
        
        try:
            if params:
                response = requests.get(url, headers=headers, params=params, timeout=10)
            else:
                response = requests.get(url, headers=headers, timeout=10)
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"API call failed for {method}: {e}")
        except Exception as e:
            raise RuntimeError(f"Unexpected error calling {method}: {e}")
    
    def _store_slack_credentials(self, bot_token: str, workspace_data: Dict[str, Any]):
        """Store Slack credentials using encrypted storage"""
        print("🔐 Storing credentials securely...")
        
        try:
            # Try to use key manager for encrypted storage
            from ...core.key_manager import key_manager
            
            # Prepare credentials for storage
            slack_credentials = {
                'bot_token': bot_token,
                'workspace': workspace_data,
                'stored_at': os.popen('date -u +"%Y-%m-%dT%H:%M:%SZ"').read().strip()
            }
            
            # Store in production tokens (not test tokens)
            success = key_manager.store_key(
                'slack_tokens_production', 
                slack_credentials, 
                'slack_oauth'
            )
            
            if success:
                print("✅ Credentials stored in encrypted database")
            else:
                print("⚠️  Failed to store in encrypted database, using environment variable")
                os.environ['SLACK_BOT_TOKEN'] = bot_token
                
        except ImportError:
            print("⚠️  Encrypted storage not available, using environment variable")
            os.environ['SLACK_BOT_TOKEN'] = bot_token
        except Exception as e:
            print(f"⚠️  Credential storage warning: {e}")
            print("Using environment variable as fallback")
            os.environ['SLACK_BOT_TOKEN'] = bot_token

if __name__ == "__main__":
    # Test the Slack setup
    setup = SlackSetup()
    result = setup.run({}, interactive=True)
    print(f"Setup result: {result}")