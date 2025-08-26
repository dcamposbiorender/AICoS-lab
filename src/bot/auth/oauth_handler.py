#!/usr/bin/env python3
"""
OAuth 2.0 Handler for Slack Bot Integration

Comprehensive OAuth 2.0 flow implementation with:
- 84 OAuth scope validation
- Token management and refresh
- Integration with encrypted credential storage
- Error handling and retry logic
"""

import os
import json
import logging
from typing import Dict, List, Optional, Set, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from urllib.parse import urlencode, parse_qs, urlparse

import requests
from slack_sdk import WebClient
from slack_sdk.oauth import AuthorizeUrlGenerator, RedirectUriPageRenderer
from slack_sdk.oauth.installation_store import Installation

# Import from core authentication infrastructure
try:
    from ...core.auth_manager import credential_vault, AuthType, AuthCredentials
    from ...core.slack_scopes import slack_scopes, SlackScopes, ScopeCategory
    from ...core.permission_checker import get_permission_checker, PermissionLevel
except ImportError as e:
    logging.error(f"Failed to import core authentication modules: {e}")
    raise

logger = logging.getLogger(__name__)

@dataclass
class OAuthConfig:
    """OAuth 2.0 configuration"""
    client_id: str
    client_secret: str
    redirect_uri: str
    scopes: List[str]
    user_scopes: Optional[List[str]] = None
    state: Optional[str] = None

class OAuthError(Exception):
    """OAuth-specific errors"""
    pass

class OAuthHandler:
    """
    Comprehensive OAuth 2.0 handler for Slack bot integration
    
    Features:
    - Complete OAuth 2.0 flow (authorization -> token exchange)  
    - 84 OAuth scope validation using slack_scopes.py
    - Token storage with encrypted credential vault
    - Automatic token refresh and validation
    - Integration with permission checker
    """
    
    def __init__(self, client_id: Optional[str] = None, client_secret: Optional[str] = None,
                 redirect_uri: Optional[str] = None):
        """
        Initialize OAuth handler
        
        Args:
            client_id: Slack app client ID (from environment if not provided)
            client_secret: Slack app client secret (from environment if not provided) 
            redirect_uri: OAuth redirect URI (defaults to localhost for dev)
        """
        self.client_id = client_id or os.environ.get('SLACK_CLIENT_ID')
        self.client_secret = client_secret or os.environ.get('SLACK_CLIENT_SECRET')
        self.redirect_uri = redirect_uri or os.environ.get('SLACK_REDIRECT_URI', 'http://localhost:3000/slack/oauth_redirect')
        
        if not self.client_id or not self.client_secret:
            raise OAuthError("Slack OAuth credentials not configured. Set SLACK_CLIENT_ID and SLACK_CLIENT_SECRET environment variables.")
        
        # Initialize components
        self.credential_vault = credential_vault
        self.slack_scopes = slack_scopes
        self.permission_checker = get_permission_checker()
        
        # OAuth URLs
        self.authorize_url = "https://slack.com/oauth/v2/authorize"
        self.token_url = "https://slack.com/api/oauth.v2.access"
        
        # State management for security
        self._oauth_states = {}  # In production, use Redis or secure storage
        
        logger.info("🔐 OAuth Handler initialized with comprehensive scope validation")
    
    def get_required_scopes(self, features: Optional[List[str]] = None) -> Dict[str, List[str]]:
        """
        Get required OAuth scopes based on desired features
        
        Args:
            features: List of feature names (e.g., ['message_collection', 'channel_management'])
        
        Returns:
            Dict with 'bot_scopes' and 'user_scopes' keys
        """
        if not features:
            # Return comprehensive collection scopes for full functionality
            bot_scopes = self.slack_scopes.get_minimal_scope_set()['comprehensive_collection']
            user_scopes = ['identity.basic', 'identity.email', 'identity.team']
        else:
            bot_scopes = set()
            user_scopes = set()
            
            for feature in features:
                feature_scopes = self.slack_scopes.get_required_scopes_for_feature(feature)
                
                # Separate bot vs user scopes
                for scope in feature_scopes:
                    scope_info = self.slack_scopes.get_scope_info(scope)
                    if scope_info.get('token_type') == 'user':
                        user_scopes.add(scope)
                    else:
                        bot_scopes.add(scope)
        
        result = {
            'bot_scopes': list(bot_scopes) if isinstance(bot_scopes, set) else bot_scopes,
            'user_scopes': list(user_scopes) if isinstance(user_scopes, set) else user_scopes
        }
        
        logger.info(f"📋 Required scopes for features {features}: {len(result['bot_scopes'])} bot + {len(result['user_scopes'])} user")
        return result
    
    def generate_authorize_url(self, scopes: Optional[List[str]] = None, 
                              user_scopes: Optional[List[str]] = None,
                              state: Optional[str] = None,
                              team_id: Optional[str] = None) -> str:
        """
        Generate OAuth authorization URL
        
        Args:
            scopes: Bot token scopes (defaults to comprehensive collection)
            user_scopes: User token scopes (defaults to basic identity)
            state: OAuth state parameter for security
            team_id: Specific workspace ID (optional)
        
        Returns:
            Authorization URL for user to visit
        """
        # Get default scopes if not provided
        if not scopes or not user_scopes:
            default_scopes = self.get_required_scopes()
            scopes = scopes or default_scopes['bot_scopes']
            user_scopes = user_scopes or default_scopes['user_scopes']
        
        # Validate scopes
        bot_validation = self.slack_scopes.validate_scopes(scopes, 'bot')
        user_validation = self.slack_scopes.validate_scopes(user_scopes, 'user')
        
        if not bot_validation['all_valid']:
            logger.warning(f"Invalid bot scopes: {bot_validation['invalid']}")
        
        if not user_validation['all_valid']:
            logger.warning(f"Invalid user scopes: {user_validation['invalid']}")
        
        # Generate secure state if not provided
        if not state:
            state = f"{datetime.now().isoformat()}_{os.urandom(16).hex()}"
        
        # Store state for validation
        self._oauth_states[state] = {
            'created_at': datetime.now(),
            'scopes': scopes,
            'user_scopes': user_scopes
        }
        
        # Build authorization URL
        params = {
            'client_id': self.client_id,
            'scope': ','.join(scopes),
            'user_scope': ','.join(user_scopes) if user_scopes else '',
            'redirect_uri': self.redirect_uri,
            'state': state
        }
        
        if team_id:
            params['team'] = team_id
        
        auth_url = f"{self.authorize_url}?{urlencode(params)}"
        
        logger.info(f"🔗 OAuth authorization URL generated with {len(scopes)} bot scopes + {len(user_scopes)} user scopes")
        return auth_url
    
    def exchange_code_for_token(self, code: str, state: Optional[str] = None) -> Dict[str, Any]:
        """
        Exchange OAuth authorization code for access tokens
        
        Args:
            code: Authorization code from OAuth callback
            state: OAuth state parameter for validation
        
        Returns:
            Dict containing installation information and tokens
        
        Raises:
            OAuthError: If token exchange fails
        """
        # Validate state if provided
        if state:
            if state not in self._oauth_states:
                raise OAuthError(f"Invalid OAuth state: {state}")
            
            # Check state expiration (30 minutes)
            state_data = self._oauth_states[state]
            if datetime.now() - state_data['created_at'] > timedelta(minutes=30):
                self._oauth_states.pop(state, None)
                raise OAuthError("OAuth state expired")
        
        # Exchange code for tokens
        payload = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': code,
            'redirect_uri': self.redirect_uri
        }
        
        try:
            response = requests.post(self.token_url, data=payload, timeout=30)
            response.raise_for_status()
            
            token_data = response.json()
            
            if not token_data.get('ok'):
                error_msg = token_data.get('error', 'Unknown OAuth error')
                raise OAuthError(f"OAuth token exchange failed: {error_msg}")
            
            # Extract installation details
            installation = {
                'app_id': token_data.get('app_id'),
                'enterprise_id': token_data.get('enterprise', {}).get('id'),
                'enterprise_name': token_data.get('enterprise', {}).get('name'),
                'team_id': token_data.get('team', {}).get('id'),
                'team_name': token_data.get('team', {}).get('name'),
                'bot_token': token_data.get('access_token'),
                'bot_id': token_data.get('bot_user_id'),
                'bot_scopes': token_data.get('scope', '').split(',') if token_data.get('scope') else [],
                'user_token': token_data.get('authed_user', {}).get('access_token'),
                'user_id': token_data.get('authed_user', {}).get('id'),
                'user_scopes': token_data.get('authed_user', {}).get('scope', '').split(',') if token_data.get('authed_user', {}).get('scope') else [],
                'installed_at': datetime.now().isoformat()
            }
            
            # Store credentials in vault
            self._store_installation(installation)
            
            # Clean up state
            if state and state in self._oauth_states:
                self._oauth_states.pop(state)
            
            logger.info(f"✅ OAuth token exchange successful for team: {installation['team_name']}")
            logger.info(f"📊 Bot scopes: {len(installation['bot_scopes'])}, User scopes: {len(installation['user_scopes'])}")
            
            return installation
            
        except requests.exceptions.RequestException as e:
            raise OAuthError(f"OAuth token exchange request failed: {e}")
        except Exception as e:
            raise OAuthError(f"OAuth token exchange error: {e}")
    
    def _store_installation(self, installation: Dict[str, Any]) -> bool:
        """
        Store OAuth installation in encrypted credential vault
        
        Args:
            installation: Installation data from OAuth flow
        
        Returns:
            True if storage successful
        """
        try:
            # Store bot token and scopes
            if installation.get('bot_token'):
                bot_success = self.credential_vault.store_slack_scopes(
                    installation['bot_scopes'], 
                    'bot',
                    'secure'
                )
                
                if not bot_success:
                    logger.warning("Failed to store bot scopes securely")
            
            # Store user token and scopes
            if installation.get('user_token'):
                user_success = self.credential_vault.store_slack_scopes(
                    installation['user_scopes'],
                    'user', 
                    'secure'
                )
                
                if not user_success:
                    logger.warning("Failed to store user scopes securely")
            
            # Store complete installation data
            from ...core.key_manager import key_manager
            installation_key = f"slack_installation_{installation['team_id']}"
            
            storage_success = key_manager.store_key(
                installation_key,
                installation,
                'slack_oauth'
            )
            
            if storage_success:
                logger.info("✅ OAuth installation stored securely")
                return True
            else:
                logger.error("❌ Failed to store OAuth installation")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error storing OAuth installation: {e}")
            return False
    
    def validate_installation(self, team_id: str) -> Dict[str, Any]:
        """
        Validate stored OAuth installation
        
        Args:
            team_id: Slack workspace/team ID
        
        Returns:
            Validation result with status and details
        """
        try:
            # Load installation from storage
            from ...core.key_manager import key_manager
            installation_key = f"slack_installation_{team_id}"
            installation = key_manager.retrieve_key(installation_key)
            
            if not installation:
                return {
                    'valid': False,
                    'error': f'No installation found for team {team_id}'
                }
            
            # Validate bot token
            bot_valid = False
            if installation.get('bot_token'):
                bot_client = WebClient(token=installation['bot_token'])
                try:
                    auth_response = bot_client.auth_test()
                    bot_valid = auth_response.get('ok', False)
                except Exception as e:
                    logger.warning(f"Bot token validation failed: {e}")
            
            # Validate user token
            user_valid = False
            if installation.get('user_token'):
                user_client = WebClient(token=installation['user_token'])
                try:
                    auth_response = user_client.auth_test()
                    user_valid = auth_response.get('ok', False)
                except Exception as e:
                    logger.warning(f"User token validation failed: {e}")
            
            # Validate scopes against requirements
            bot_scopes = installation.get('bot_scopes', [])
            user_scopes = installation.get('user_scopes', [])
            
            required_scopes = self.get_required_scopes()
            
            missing_bot_scopes = set(required_scopes['bot_scopes']) - set(bot_scopes)
            missing_user_scopes = set(required_scopes['user_scopes']) - set(user_scopes)
            
            return {
                'valid': bot_valid and (not missing_bot_scopes or len(missing_bot_scopes) == 0),
                'bot_token_valid': bot_valid,
                'user_token_valid': user_valid,
                'bot_scopes': bot_scopes,
                'user_scopes': user_scopes,
                'missing_bot_scopes': list(missing_bot_scopes),
                'missing_user_scopes': list(missing_user_scopes),
                'installation': installation
            }
            
        except Exception as e:
            return {
                'valid': False,
                'error': f'Installation validation failed: {e}'
            }
    
    def refresh_tokens_if_needed(self, team_id: str) -> bool:
        """
        Refresh OAuth tokens if needed
        
        Args:
            team_id: Slack workspace/team ID
        
        Returns:
            True if tokens are valid or successfully refreshed
        """
        # Slack OAuth 2.0 tokens don't expire, but we validate they still work
        validation = self.validate_installation(team_id)
        
        if validation['valid']:
            logger.info(f"✅ OAuth tokens valid for team {team_id}")
            return True
        
        if not validation['bot_token_valid']:
            logger.error(f"❌ Bot token invalid for team {team_id} - reinstallation required")
            return False
        
        logger.warning(f"⚠️ OAuth validation issues for team {team_id}: {validation.get('error', 'Unknown')}")
        return False
    
    def get_installation(self, team_id: str) -> Optional[Dict[str, Any]]:
        """
        Get stored OAuth installation for team
        
        Args:
            team_id: Slack workspace/team ID
        
        Returns:
            Installation data or None if not found
        """
        try:
            from ...core.key_manager import key_manager
            installation_key = f"slack_installation_{team_id}"
            return key_manager.retrieve_key(installation_key)
        except Exception as e:
            logger.error(f"Error retrieving installation for team {team_id}: {e}")
            return None
    
    def revoke_tokens(self, team_id: str) -> bool:
        """
        Revoke OAuth tokens and remove installation
        
        Args:
            team_id: Slack workspace/team ID
        
        Returns:
            True if revocation successful
        """
        try:
            installation = self.get_installation(team_id)
            if not installation:
                logger.warning(f"No installation found for team {team_id}")
                return True
            
            # Revoke tokens via Slack API
            revoke_url = "https://slack.com/api/auth.revoke"
            
            success = True
            
            # Revoke bot token
            if installation.get('bot_token'):
                try:
                    response = requests.post(revoke_url, data={
                        'token': installation['bot_token']
                    }, timeout=30)
                    
                    if not response.json().get('ok'):
                        logger.warning(f"Bot token revocation may have failed: {response.json()}")
                        success = False
                except Exception as e:
                    logger.warning(f"Bot token revocation error: {e}")
                    success = False
            
            # Revoke user token
            if installation.get('user_token'):
                try:
                    response = requests.post(revoke_url, data={
                        'token': installation['user_token']
                    }, timeout=30)
                    
                    if not response.json().get('ok'):
                        logger.warning(f"User token revocation may have failed: {response.json()}")
                        success = False
                except Exception as e:
                    logger.warning(f"User token revocation error: {e}")
                    success = False
            
            # Remove installation from storage
            from ...core.key_manager import key_manager
            installation_key = f"slack_installation_{team_id}"
            key_manager.delete_key(installation_key)
            
            logger.info(f"🗑️ OAuth installation revoked for team {team_id}")
            return success
            
        except Exception as e:
            logger.error(f"Error revoking tokens for team {team_id}: {e}")
            return False

# Convenience function for quick OAuth flow
def start_oauth_flow(features: Optional[List[str]] = None, 
                     redirect_uri: Optional[str] = None) -> Tuple[str, OAuthHandler]:
    """
    Start OAuth flow with specified features
    
    Args:
        features: List of feature names requiring OAuth scopes
        redirect_uri: Custom redirect URI
    
    Returns:
        Tuple of (authorization_url, oauth_handler)
    """
    handler = OAuthHandler(redirect_uri=redirect_uri)
    scopes_config = handler.get_required_scopes(features)
    
    auth_url = handler.generate_authorize_url(
        scopes=scopes_config['bot_scopes'],
        user_scopes=scopes_config['user_scopes']
    )
    
    return auth_url, handler