#!/usr/bin/env python3
"""
Permission Validation Middleware for Slack Bot

Validates OAuth permissions before executing commands and API calls.
Integrates with the comprehensive permission checking system.
"""

import logging
import traceback
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime
import functools

from slack_bolt import BoltRequest, BoltResponse
from slack_bolt.middleware import Middleware

# Import from core authentication infrastructure
try:
    from ...core.permission_checker import get_permission_checker, PermissionLevel
    from ..auth.scope_validator import get_scope_validator, ValidationLevel, ValidationResult
except ImportError as e:
    logging.error(f"Failed to import permission checking modules: {e}")
    raise

logger = logging.getLogger(__name__)

class PermissionMiddleware(Middleware):
    """
    Slack Bolt middleware for permission validation
    
    Features:
    - Validates OAuth scopes before command execution
    - Provides graceful degradation on permission failures
    - Logs permission issues for security audit
    - Integrates with both permission checker and scope validator
    """
    
    def __init__(self, validation_level: ValidationLevel = ValidationLevel.STRICT,
                 enable_audit_logging: bool = True):
        """
        Initialize permission middleware
        
        Args:
            validation_level: How strictly to enforce permissions
            enable_audit_logging: Whether to log permission events
        """
        super().__init__()
        self.validation_level = validation_level
        self.enable_audit_logging = enable_audit_logging
        
        # Initialize validators
        self.permission_checker = get_permission_checker()
        self.scope_validator = get_scope_validator()
        
        # Set validation levels
        if validation_level == ValidationLevel.STRICT:
            self.permission_checker.set_permission_level(PermissionLevel.STRICT)
        elif validation_level == ValidationLevel.WARNING:
            self.permission_checker.set_permission_level(PermissionLevel.LENIENT)
        else:
            self.permission_checker.set_permission_level(PermissionLevel.DISABLED)
        
        self.scope_validator.set_validation_level(validation_level)
        
        logger.info(f"🔒 Permission middleware initialized with {validation_level.value} validation")
    
    def process(self, *, req: BoltRequest, resp: BoltResponse, next: Callable[[], BoltResponse]) -> BoltResponse:
        """
        Process incoming request with permission validation
        
        Args:
            req: Bolt request object
            resp: Bolt response object  
            next: Next middleware/handler in chain
            
        Returns:
            Bolt response (possibly with permission error)
        """
        try:
            # Skip validation for certain request types
            if self._should_skip_validation(req):
                return next()
            
            # Extract command/action information
            command_info = self._extract_command_info(req)
            
            if not command_info:
                # No specific command detected, allow through
                return next()
            
            # Validate permissions for the command
            validation_result = self._validate_command_permissions(command_info, req)
            
            # Log permission check for audit
            if self.enable_audit_logging:
                self._log_permission_check(req, command_info, validation_result)
            
            # Handle validation result
            if not validation_result.valid:
                return self._handle_permission_failure(req, resp, command_info, validation_result)
            
            # Permissions OK, continue to handler
            return next()
            
        except Exception as e:
            logger.error(f"Permission middleware error: {e}")
            logger.error(traceback.format_exc())
            
            # On middleware error, allow through but log
            if self.enable_audit_logging:
                self._log_permission_error(req, str(e))
            
            return next()
    
    def _should_skip_validation(self, req: BoltRequest) -> bool:
        """Check if validation should be skipped for this request"""
        # Skip for OAuth flow and health checks
        if req.body.get("type") == "url_verification":
            return True
        
        # Skip for challenge requests
        if req.body.get("challenge"):
            return True
        
        # Skip if validation disabled
        if self.validation_level == ValidationLevel.DISABLED:
            return True
        
        return False
    
    def _extract_command_info(self, req: BoltRequest) -> Optional[Dict[str, Any]]:
        """Extract command/action information from request"""
        command_info = {}
        
        # Handle slash commands
        if req.body.get("command"):
            command_info = {
                'type': 'slash_command',
                'command': req.body["command"],
                'text': req.body.get("text", ""),
                'user_id': req.body.get("user_id"),
                'channel_id': req.body.get("channel_id"),
                'team_id': req.body.get("team_id")
            }
        
        # Handle interactive components (buttons, modals)
        elif req.body.get("type") == "interactive_component" or "payload" in req.body:
            payload = req.body.get("payload", {})
            if isinstance(payload, str):
                import json
                try:
                    payload = json.loads(payload)
                except json.JSONDecodeError:
                    payload = {}
            
            command_info = {
                'type': 'interactive_component',
                'callback_id': payload.get("callback_id"),
                'action': payload.get("actions", [{}])[0].get("value") if payload.get("actions") else None,
                'user_id': payload.get("user", {}).get("id"),
                'channel_id': payload.get("channel", {}).get("id"),
                'team_id': payload.get("team", {}).get("id")
            }
        
        # Handle events (message events, etc.)
        elif req.body.get("type") == "event_callback":
            event = req.body.get("event", {})
            command_info = {
                'type': 'event',
                'event_type': event.get("type"),
                'user_id': event.get("user"),
                'channel_id': event.get("channel"),
                'team_id': req.body.get("team_id")
            }
        
        return command_info if command_info else None
    
    def _validate_command_permissions(self, command_info: Dict[str, Any], 
                                    req: BoltRequest) -> ValidationResult:
        """Validate permissions for specific command"""
        command_type = command_info.get('type')
        
        if command_type == 'slash_command':
            return self._validate_slash_command(command_info)
        elif command_type == 'interactive_component':
            return self._validate_interactive_component(command_info)
        elif command_type == 'event':
            return self._validate_event_handler(command_info)
        else:
            # Unknown command type - allow through with warning
            logger.warning(f"Unknown command type for validation: {command_type}")
            return ValidationResult(
                valid=True,
                missing_scopes=[],
                available_scopes=[],
                warnings=[f"Unknown command type: {command_type}"],
                errors=[],
                recommendations=[]
            )
    
    def _validate_slash_command(self, command_info: Dict[str, Any]) -> ValidationResult:
        """Validate slash command permissions"""
        command = command_info.get('command', '')
        text = command_info.get('text', '')
        
        # Map commands to required scopes
        command_scopes = self._get_command_scope_requirements(command, text)
        
        if not command_scopes:
            # No specific requirements
            return ValidationResult(
                valid=True,
                missing_scopes=[],
                available_scopes=[],
                warnings=[],
                errors=[],
                recommendations=[]
            )
        
        # Validate scopes
        return self.scope_validator.validate_command_permissions(
            command, 
            command_scopes['scopes'],
            command_scopes.get('token_type', 'bot')
        )
    
    def _validate_interactive_component(self, command_info: Dict[str, Any]) -> ValidationResult:
        """Validate interactive component permissions"""
        callback_id = command_info.get('callback_id', '')
        action = command_info.get('action', '')
        
        # Interactive components generally need basic messaging scopes
        required_scopes = ['chat:write']
        
        # Add specific scopes based on action
        if 'search' in callback_id or 'search' in action:
            required_scopes.append('search:read')
        elif 'file' in callback_id or 'file' in action:
            required_scopes.extend(['files:read', 'files:write'])
        elif 'channel' in callback_id or 'channel' in action:
            required_scopes.extend(['channels:read', 'channels:history'])
        
        return self.scope_validator.validate_command_permissions(
            f"interactive:{callback_id}",
            required_scopes,
            'bot'
        )
    
    def _validate_event_handler(self, command_info: Dict[str, Any]) -> ValidationResult:
        """Validate event handler permissions"""
        event_type = command_info.get('event_type', '')
        
        # Event handlers need appropriate read scopes
        if event_type == 'message':
            required_scopes = ['channels:history', 'groups:history', 'im:history']
        elif event_type == 'channel_created':
            required_scopes = ['channels:read']
        elif event_type == 'member_joined_channel':
            required_scopes = ['users:read', 'channels:read']
        else:
            required_scopes = ['channels:read']  # Basic fallback
        
        return self.scope_validator.validate_command_permissions(
            f"event:{event_type}",
            required_scopes,
            'bot'
        )
    
    def _get_command_scope_requirements(self, command: str, text: str) -> Optional[Dict[str, Any]]:
        """Get scope requirements for slash commands"""
        command_lower = command.lower()
        text_lower = text.lower()
        
        # AI Chief of Staff commands
        if '/cos' in command_lower:
            if 'search' in text_lower:
                return {
                    'scopes': ['search:read', 'channels:history', 'groups:history', 'im:history'],
                    'token_type': 'bot'
                }
            elif 'schedule' in text_lower:
                return {
                    'scopes': ['users:read', 'users:read.email', 'chat:write'],
                    'token_type': 'bot'
                }
            elif 'brief' in text_lower:
                return {
                    'scopes': ['channels:history', 'groups:history', 'chat:write'],
                    'token_type': 'bot'
                }
            elif 'goals' in text_lower:
                return {
                    'scopes': ['pins:write', 'chat:write', 'channels:read'],
                    'token_type': 'bot'
                }
            elif 'commitments' in text_lower:
                return {
                    'scopes': ['metadata.message:read', 'search:read', 'chat:write'],
                    'token_type': 'bot'
                }
            elif 'admin' in text_lower:
                return {
                    'scopes': ['admin', 'usergroups:write', 'channels:write'],
                    'token_type': 'user'
                }
            else:
                # Default /cos command scopes
                return {
                    'scopes': ['chat:write', 'users:read'],
                    'token_type': 'bot'
                }
        
        # Other common commands
        elif command_lower in ['/help', '/about']:
            return {
                'scopes': ['chat:write'],
                'token_type': 'bot'
            }
        
        # No specific requirements found
        return None
    
    def _handle_permission_failure(self, req: BoltRequest, resp: BoltResponse,
                                 command_info: Dict[str, Any], 
                                 validation_result: ValidationResult) -> BoltResponse:
        """Handle permission validation failure"""
        if self.validation_level == ValidationLevel.WARNING:
            # Log warnings but continue
            for warning in validation_result.warnings:
                logger.warning(warning)
            return resp  # Continue to next middleware
        
        # Strict mode - block with helpful error message
        command = command_info.get('command', 'unknown command')
        missing_scopes = validation_result.missing_scopes
        
        error_message = self._format_permission_error_message(command, missing_scopes, validation_result.recommendations)
        
        # Send ephemeral error message
        resp.status = 200
        resp.body = {
            "response_type": "ephemeral",
            "text": "🔒 Permission Required",
            "attachments": [
                {
                    "color": "danger",
                    "fields": [
                        {
                            "title": "Missing Permissions",
                            "value": error_message,
                            "short": False
                        }
                    ]
                }
            ]
        }
        
        return resp
    
    def _format_permission_error_message(self, command: str, missing_scopes: List[str],
                                       recommendations: List[str]) -> str:
        """Format user-friendly permission error message"""
        message = f"The command `{command}` requires additional permissions.\n\n"
        message += "**Missing OAuth Scopes:**\n"
        
        for scope in missing_scopes[:5]:  # Limit to first 5 for readability
            description = self.scope_validator._get_scope_description(scope)
            message += f"• `{scope}`: {description}\n"
        
        if len(missing_scopes) > 5:
            message += f"• ... and {len(missing_scopes) - 5} more\n"
        
        message += "\n**To resolve this:**\n"
        message += "1. Contact your Slack admin to reinstall the bot with updated permissions\n"
        message += "2. Or try using alternative commands that don't require these permissions\n"
        
        return message
    
    def _log_permission_check(self, req: BoltRequest, command_info: Dict[str, Any],
                            validation_result: ValidationResult):
        """Log permission check for security audit"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'event': 'permission_check',
            'command': command_info.get('command', command_info.get('type')),
            'user_id': command_info.get('user_id'),
            'team_id': command_info.get('team_id'),
            'channel_id': command_info.get('channel_id'),
            'validation_result': {
                'valid': validation_result.valid,
                'missing_scopes': validation_result.missing_scopes,
                'validation_level': self.validation_level.value
            },
            'request_headers': dict(req.headers),
            'success': validation_result.valid
        }
        
        if validation_result.valid:
            logger.info(f"Permission check passed: {log_entry}")
        else:
            logger.warning(f"Permission check failed: {log_entry}")
    
    def _log_permission_error(self, req: BoltRequest, error_msg: str):
        """Log permission middleware error"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'event': 'permission_middleware_error',
            'error': error_msg,
            'request_body': req.body,
            'request_headers': dict(req.headers)
        }
        
        logger.error(f"Permission middleware error: {log_entry}")

# Decorator for method-level permission checking
def require_permissions(scopes: List[str], token_type: str = 'bot', 
                       validation_level: ValidationLevel = ValidationLevel.STRICT):
    """
    Decorator to require specific OAuth scopes for a handler method
    
    Args:
        scopes: Required OAuth scopes
        token_type: 'bot' or 'user' token type
        validation_level: Validation strictness level
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Get scope validator
            validator = get_scope_validator()
            
            # Create synthetic command name from function
            command_name = getattr(func, '__name__', 'unknown_handler')
            
            # Validate permissions
            validation_result = validator.validate_command_permissions(
                command_name, scopes, token_type
            )
            
            # Handle validation result
            if not validation_result.valid:
                if validation_level == ValidationLevel.STRICT:
                    error_msg = f"Handler {command_name} missing required scopes: {validation_result.missing_scopes}"
                    logger.error(error_msg)
                    raise PermissionError(error_msg)
                elif validation_level == ValidationLevel.WARNING:
                    for warning in validation_result.warnings:
                        logger.warning(warning)
            
            # Permissions OK or lenient mode, continue
            return func(*args, **kwargs)
        
        # Store scope requirements on function for introspection
        wrapper._required_scopes = scopes
        wrapper._token_type = token_type
        wrapper._validation_level = validation_level
        
        return wrapper
    return decorator

# Global middleware instance
_global_permission_middleware = None

def get_permission_middleware(validation_level: ValidationLevel = ValidationLevel.STRICT) -> PermissionMiddleware:
    """Get global permission middleware instance"""
    global _global_permission_middleware
    if _global_permission_middleware is None:
        _global_permission_middleware = PermissionMiddleware(validation_level)
    return _global_permission_middleware