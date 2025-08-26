#!/usr/bin/env python3
"""
Runtime Permission Checker for Slack API Operations
Validates OAuth scopes before making API calls to prevent authorization errors
"""

import functools
import inspect
from typing import Dict, List, Optional, Set, Union, Any, Callable
from dataclasses import dataclass
from enum import Enum
import logging

try:
    from .auth_manager import credential_vault
    from .slack_scopes import slack_scopes, ScopeCategory
except ImportError:
    # Handle imports when running standalone
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    from auth_manager import credential_vault
    from slack_scopes import slack_scopes, ScopeCategory

logger = logging.getLogger(__name__)

class PermissionLevel(Enum):
    """Permission validation levels"""
    STRICT = "strict"      # Fail on any missing permission
    LENIENT = "lenient"    # Warn on missing permissions but continue
    DISABLED = "disabled"  # No permission checking

@dataclass
class APIEndpoint:
    """Slack API endpoint configuration"""
    name: str
    required_scopes: List[str]
    token_type: str = 'bot'  # 'bot' or 'user'
    optional_scopes: Optional[List[str]] = None
    description: str = ""

class SlackAPIRegistry:
    """Registry of Slack API endpoints and their required scopes"""
    
    # Common API endpoints and their scope requirements
    ENDPOINTS = {
        # Chat/Messaging APIs
        'chat.postMessage': APIEndpoint(
            name='chat.postMessage',
            required_scopes=['chat:write'],
            description='Post messages to channels'
        ),
        'chat.update': APIEndpoint(
            name='chat.update',
            required_scopes=['chat:write'],
            description='Update existing messages'
        ),
        'chat.delete': APIEndpoint(
            name='chat.delete',
            required_scopes=['chat:write'],
            description='Delete messages'
        ),
        'chat.postEphemeral': APIEndpoint(
            name='chat.postEphemeral',
            required_scopes=['chat:write'],
            description='Post ephemeral messages'
        ),
        
        # Channel APIs
        'channels.list': APIEndpoint(
            name='channels.list',
            required_scopes=['channels:read'],
            description='List public channels'
        ),
        'channels.info': APIEndpoint(
            name='channels.info',
            required_scopes=['channels:read'],
            description='Get channel information'
        ),
        'channels.history': APIEndpoint(
            name='channels.history',
            required_scopes=['channels:history'],
            description='Fetch channel message history'
        ),
        'channels.create': APIEndpoint(
            name='channels.create',
            required_scopes=['channels:write'],
            description='Create new channels'
        ),
        'channels.invite': APIEndpoint(
            name='channels.invite',
            required_scopes=['channels:write.invites'],
            description='Invite users to channels'
        ),
        'channels.setTopic': APIEndpoint(
            name='channels.setTopic',
            required_scopes=['channels:write.topic'],
            description='Set channel topics'
        ),
        
        # Group (Private Channel) APIs
        'groups.list': APIEndpoint(
            name='groups.list',
            required_scopes=['groups:read'],
            description='List private channels'
        ),
        'groups.info': APIEndpoint(
            name='groups.info',
            required_scopes=['groups:read'],
            description='Get private channel information'
        ),
        'groups.history': APIEndpoint(
            name='groups.history',
            required_scopes=['groups:history'],
            description='Fetch private channel history'
        ),
        
        # User APIs
        'users.list': APIEndpoint(
            name='users.list',
            required_scopes=['users:read'],
            description='List workspace users'
        ),
        'users.info': APIEndpoint(
            name='users.info',
            required_scopes=['users:read'],
            description='Get user information'
        ),
        'users.profile.get': APIEndpoint(
            name='users.profile.get',
            required_scopes=['users.profile:read'],
            description='Get user profiles'
        ),
        
        # File APIs
        'files.list': APIEndpoint(
            name='files.list',
            required_scopes=['files:read'],
            description='List files'
        ),
        'files.info': APIEndpoint(
            name='files.info',
            required_scopes=['files:read'],
            description='Get file information'
        ),
        'files.upload': APIEndpoint(
            name='files.upload',
            required_scopes=['files:write'],
            description='Upload files'
        ),
        
        # Conversation APIs (modern unified API)
        'conversations.list': APIEndpoint(
            name='conversations.list',
            required_scopes=['channels:read', 'groups:read', 'im:read', 'mpim:read'],
            description='List all conversation types'
        ),
        'conversations.history': APIEndpoint(
            name='conversations.history',
            required_scopes=['channels:history', 'groups:history', 'im:history', 'mpim:history'],
            description='Fetch conversation history'
        ),
        'conversations.info': APIEndpoint(
            name='conversations.info',
            required_scopes=['channels:read', 'groups:read', 'im:read', 'mpim:read'],
            description='Get conversation information'
        ),
        
        # Reactions APIs
        'reactions.add': APIEndpoint(
            name='reactions.add',
            required_scopes=['reactions:write'],
            description='Add emoji reactions'
        ),
        'reactions.get': APIEndpoint(
            name='reactions.get',
            required_scopes=['reactions:read'],
            description='Get message reactions'
        ),
        
        # Pins APIs
        'pins.add': APIEndpoint(
            name='pins.add',
            required_scopes=['pins:write'],
            description='Pin messages or files'
        ),
        'pins.list': APIEndpoint(
            name='pins.list',
            required_scopes=['pins:read'],
            description='List pinned items'
        ),
        
        # Search API
        'search.messages': APIEndpoint(
            name='search.messages',
            required_scopes=['search:read'],
            description='Search messages'
        ),
        'search.files': APIEndpoint(
            name='search.files',
            required_scopes=['search:read'],
            description='Search files'
        ),
        
        # Team API
        'team.info': APIEndpoint(
            name='team.info',
            required_scopes=['team:read'],
            description='Get team information'
        ),
        
        # Bookmarks APIs
        'bookmarks.list': APIEndpoint(
            name='bookmarks.list',
            required_scopes=['bookmarks:read'],
            description='List channel bookmarks'
        ),
        'bookmarks.add': APIEndpoint(
            name='bookmarks.add',
            required_scopes=['bookmarks:write'],
            description='Add bookmarks'
        ),
        
        # Calls APIs
        'calls.info': APIEndpoint(
            name='calls.info',
            required_scopes=['calls:read'],
            description='Get call information'
        ),
        'calls.add': APIEndpoint(
            name='calls.add',
            required_scopes=['calls:write'],
            description='Start calls'
        ),
        
        # Do Not Disturb APIs
        'dnd.info': APIEndpoint(
            name='dnd.info',
            required_scopes=['dnd:read'],
            description='Get DND status'
        ),
        
        # Emoji API
        'emoji.list': APIEndpoint(
            name='emoji.list',
            required_scopes=['emoji:read'],
            description='List custom emoji'
        ),
        
        # Reminders APIs
        'reminders.list': APIEndpoint(
            name='reminders.list',
            required_scopes=['reminders:read'],
            description='List reminders'
        ),
        'reminders.add': APIEndpoint(
            name='reminders.add',
            required_scopes=['reminders:write'],
            description='Create reminders'
        ),
        
        # Stars APIs
        'stars.list': APIEndpoint(
            name='stars.list',
            required_scopes=['stars:read'],
            description='List starred items'
        ),
        'stars.add': APIEndpoint(
            name='stars.add',
            required_scopes=['stars:write'],
            description='Star items'
        ),
        
        # User Groups APIs
        'usergroups.list': APIEndpoint(
            name='usergroups.list',
            required_scopes=['usergroups:read'],
            description='List user groups'
        ),
        'usergroups.create': APIEndpoint(
            name='usergroups.create',
            required_scopes=['usergroups:write'],
            description='Create user groups'
        ),
    }

class PermissionChecker:
    """Runtime permission checker for Slack API operations"""
    
    def __init__(self, permission_level: PermissionLevel = PermissionLevel.STRICT):
        self.permission_level = permission_level
        self.credential_vault = credential_vault
        self.api_registry = SlackAPIRegistry()
        self.slack_scopes = slack_scopes
        
        # Cache for performance
        self._scope_cache = {}
        self._validation_cache = {}
    
    def set_permission_level(self, level: PermissionLevel):
        """Set permission validation level"""
        self.permission_level = level
        self._validation_cache.clear()  # Clear cache when level changes
        logger.info(f"Permission checking level set to: {level.value}")
    
    def check_api_permissions(self, api_method: str, token_type: str = 'bot',
                            custom_scopes: Optional[List[str]] = None) -> Dict[str, Any]:
        """Check if current token has required permissions for API method"""
        
        if self.permission_level == PermissionLevel.DISABLED:
            return {'valid': True, 'disabled': True}
        
        # Use cache for performance
        cache_key = f"{api_method}:{token_type}"
        if cache_key in self._validation_cache:
            return self._validation_cache[cache_key]
        
        # Get API endpoint configuration
        endpoint = self.api_registry.ENDPOINTS.get(api_method)
        if not endpoint and not custom_scopes:
            logger.warning(f"Unknown API method: {api_method}")
            return {
                'valid': self.permission_level == PermissionLevel.LENIENT,
                'error': f'Unknown API method: {api_method}',
                'warning': True
            }
        
        # Determine required scopes
        required_scopes = custom_scopes or (endpoint.required_scopes if endpoint else [])
        
        if not required_scopes:
            result = {'valid': True, 'no_scopes_required': True}
            self._validation_cache[cache_key] = result
            return result
        
        # Get current token scopes
        current_scopes = self._get_current_scopes(token_type)
        
        if current_scopes is None:
            error_msg = f'No {token_type} scopes available'
            result = {
                'valid': False,
                'error': error_msg,
                'missing_scopes': required_scopes,
                'available_scopes': []
            }
            self._validation_cache[cache_key] = result
            return result
        
        # Check for missing scopes
        missing_scopes = []
        satisfied_scopes = []
        
        for scope in required_scopes:
            if scope in current_scopes:
                satisfied_scopes.append(scope)
            else:
                missing_scopes.append(scope)
        
        # Build validation result
        result = {
            'valid': len(missing_scopes) == 0,
            'api_method': api_method,
            'token_type': token_type,
            'required_scopes': required_scopes,
            'satisfied_scopes': satisfied_scopes,
            'missing_scopes': missing_scopes,
            'available_scopes': list(current_scopes)
        }
        
        # Add endpoint description if available
        if endpoint:
            result['description'] = endpoint.description
        
        # Cache the result
        self._validation_cache[cache_key] = result
        
        return result
    
    def _get_current_scopes(self, token_type: str) -> Optional[Set[str]]:
        """Get current scopes for token type with caching"""
        if token_type not in self._scope_cache:
            scopes = self.credential_vault.get_slack_scopes(token_type)
            self._scope_cache[token_type] = scopes
        
        return self._scope_cache[token_type]
    
    def validate_and_warn(self, api_method: str, token_type: str = 'bot',
                         custom_scopes: Optional[List[str]] = None) -> bool:
        """Validate permissions and log warnings/errors as appropriate"""
        
        if self.permission_level == PermissionLevel.DISABLED:
            return True
        
        result = self.check_api_permissions(api_method, token_type, custom_scopes)
        
        if result['valid']:
            return True
        
        # Handle permission failures based on level
        if self.permission_level == PermissionLevel.STRICT:
            error_msg = f"Permission denied for {api_method}: missing scopes {result.get('missing_scopes', [])}"
            logger.error(error_msg)
            return False
        
        elif self.permission_level == PermissionLevel.LENIENT:
            warning_msg = f"Missing permissions for {api_method}: {result.get('missing_scopes', [])} (continuing anyway)"
            logger.warning(warning_msg)
            return True
        
        return True
    
    def get_feature_requirements(self, feature_name: str) -> Dict[str, Any]:
        """Get all API permission requirements for a feature"""
        if not self.slack_scopes:
            return {'error': 'Slack scopes not available'}
        
        required_scopes = self.slack_scopes.get_required_scopes_for_feature(feature_name)
        
        if not required_scopes:
            return {'error': f'Feature not found: {feature_name}'}
        
        # Check current permissions
        bot_validation = self.credential_vault.validate_slack_permissions(list(required_scopes), 'bot')
        user_validation = self.credential_vault.validate_slack_permissions(list(required_scopes), 'user')
        
        return {
            'feature': feature_name,
            'required_scopes': list(required_scopes),
            'bot_validation': bot_validation,
            'user_validation': user_validation
        }
    
    def clear_cache(self):
        """Clear permission validation cache"""
        self._scope_cache.clear()
        self._validation_cache.clear()
        logger.info("Permission checker cache cleared")

# Decorator for automatic permission checking
def require_permissions(api_method: Optional[str] = None, 
                       scopes: Optional[List[str]] = None,
                       token_type: str = 'bot'):
    """Decorator to automatically check permissions before function execution"""
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Get the global permission checker
            checker = get_permission_checker()
            
            if checker.permission_level == PermissionLevel.DISABLED:
                return func(*args, **kwargs)
            
            # Determine API method name
            method_name = api_method or func.__name__
            if not method_name.startswith(('chat.', 'channels.', 'users.', 'files.')):
                # Try to infer from function name
                if hasattr(func, '__module__') and 'slack' in func.__module__.lower():
                    method_name = f"unknown.{method_name}"
            
            # Check permissions
            is_valid = checker.validate_and_warn(method_name, token_type, scopes)
            
            if not is_valid and checker.permission_level == PermissionLevel.STRICT:
                raise PermissionError(f"Insufficient permissions for {method_name}")
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator

# Global permission checker instance
_global_checker = None

def get_permission_checker() -> PermissionChecker:
    """Get global permission checker instance"""
    global _global_checker
    if _global_checker is None:
        _global_checker = PermissionChecker()
    return _global_checker

def set_permission_level(level: PermissionLevel):
    """Set global permission checking level"""
    checker = get_permission_checker()
    checker.set_permission_level(level)

# Convenience functions
def check_api_permissions(api_method: str, token_type: str = 'bot') -> Dict[str, Any]:
    """Check API permissions using global checker"""
    return get_permission_checker().check_api_permissions(api_method, token_type)

def validate_permissions(api_method: str, token_type: str = 'bot') -> bool:
    """Validate permissions using global checker"""
    return get_permission_checker().validate_and_warn(api_method, token_type)

# Example usage patterns
if __name__ == "__main__":
    # Test the permission checker
    checker = PermissionChecker()
    
    # Test various API methods
    test_methods = [
        'chat.postMessage',
        'channels.list',
        'channels.history',
        'users.list',
        'files.upload'
    ]
    
    print("🔍 Testing Permission Checker")
    print("=" * 40)
    
    for method in test_methods:
        result = checker.check_api_permissions(method)
        status = "✅" if result['valid'] else "❌"
        print(f"{status} {method}: {result.get('description', 'No description')}")
        
        if not result['valid'] and 'missing_scopes' in result:
            print(f"    Missing: {', '.join(result['missing_scopes'])}")
    
    # Test feature requirements
    print(f"\n📋 Feature Requirements Test")
    print("-" * 30)
    
    feature_result = checker.get_feature_requirements('message_collection')
    if 'error' not in feature_result:
        print(f"Feature: {feature_result['feature']}")
        print(f"Required scopes: {', '.join(feature_result['required_scopes'])}")
        print(f"Bot valid: {feature_result['bot_validation']['valid']}")
        print(f"User valid: {feature_result['user_validation']['valid']}")