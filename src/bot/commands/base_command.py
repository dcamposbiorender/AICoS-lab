#!/usr/bin/env python3
"""
Base Command Class with Permission Decorators

Provides foundation for all Slack bot commands with:
- @require_permissions decorator for OAuth scope validation
- Standardized command structure and error handling
- Integration with audit logging and rate limiting
- Consistent response formatting
"""

import functools
import logging
import traceback
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Callable, Any, Union
from datetime import datetime

from slack_bolt import BoltContext, BoltRequest, BoltResponse
from slack_sdk import WebClient

# Import from authentication and middleware infrastructure
try:
    from ...core.permission_checker import get_permission_checker, PermissionLevel
    from ..auth.scope_validator import get_scope_validator, ValidationLevel, ValidationResult
    from ..middleware.audit_logger import get_audit_logger, AuditEventType, SecurityLevel
except ImportError as e:
    logging.error(f"Failed to import command infrastructure: {e}")
    raise

logger = logging.getLogger(__name__)

class CommandError(Exception):
    """Base exception for command errors"""
    def __init__(self, message: str, user_friendly: bool = True, 
                 show_help: bool = False):
        super().__init__(message)
        self.user_friendly = user_friendly
        self.show_help = show_help

class PermissionError(CommandError):
    """Permission-related command error"""
    def __init__(self, message: str, missing_scopes: List[str] = None):
        super().__init__(message, user_friendly=True)
        self.missing_scopes = missing_scopes or []

class BaseCommand(ABC):
    """
    Abstract base class for Slack bot commands
    
    Provides:
    - Standard command lifecycle management
    - Permission validation integration  
    - Error handling and user feedback
    - Audit logging hooks
    - Response formatting utilities
    """
    
    def __init__(self, command_name: str, description: str,
                 required_scopes: List[str] = None,
                 token_type: str = 'bot'):
        """
        Initialize base command
        
        Args:
            command_name: Command identifier (e.g., '/cos search')
            description: Human-readable command description
            required_scopes: OAuth scopes required for command
            token_type: Token type needed ('bot' or 'user')
        """
        self.command_name = command_name
        self.description = description
        self.required_scopes = required_scopes or []
        self.token_type = token_type
        
        # Initialize components
        self.permission_checker = get_permission_checker()
        self.scope_validator = get_scope_validator()
        self.audit_logger = get_audit_logger()
        
        logger.info(f"📋 Command '{command_name}' initialized with {len(self.required_scopes)} required scopes")
    
    @abstractmethod
    def execute(self, context: BoltContext, request: BoltRequest, 
                client: WebClient) -> Union[Dict[str, Any], str]:
        """
        Execute the command
        
        Args:
            context: Slack Bolt context
            request: Incoming request
            client: Slack WebClient
            
        Returns:
            Response dict or string message
        """
        pass
    
    def handle_command(self, context: BoltContext, request: BoltRequest, 
                      client: WebClient) -> Union[Dict[str, Any], str]:
        """
        Handle command with full lifecycle management
        
        Args:
            context: Slack Bolt context
            request: Incoming request  
            client: Slack WebClient
            
        Returns:
            Formatted response
        """
        start_time = datetime.now()
        user_id = self._extract_user_id(request)
        team_id = self._extract_team_id(request)
        channel_id = self._extract_channel_id(request)
        
        try:
            # Validate permissions
            if self.required_scopes:
                self._validate_permissions(user_id, team_id)
            
            # Execute command
            result = self.execute(context, request, client)
            
            # Log successful execution
            self._log_command_success(user_id, team_id, channel_id, start_time)
            
            return self._format_response(result)
            
        except PermissionError as e:
            self._log_command_error(user_id, team_id, channel_id, str(e), start_time)
            return self._format_permission_error(e)
            
        except CommandError as e:
            self._log_command_error(user_id, team_id, channel_id, str(e), start_time)
            return self._format_command_error(e)
            
        except Exception as e:
            error_msg = f"Unexpected error in {self.command_name}: {e}"
            logger.error(f"{error_msg}\n{traceback.format_exc()}")
            self._log_command_error(user_id, team_id, channel_id, error_msg, start_time)
            return self._format_unexpected_error(e)
    
    def _validate_permissions(self, user_id: Optional[str], team_id: Optional[str]):
        """Validate command permissions"""
        if not self.required_scopes:
            return
        
        # Validate using scope validator
        validation_result = self.scope_validator.validate_command_permissions(
            self.command_name,
            self.required_scopes,
            self.token_type
        )
        
        # Log permission check
        self.audit_logger.log_permission_check(
            user_id or "unknown",
            team_id or "unknown", 
            self.command_name,
            {
                'valid': validation_result.valid,
                'missing_scopes': validation_result.missing_scopes,
                'available_scopes': validation_result.available_scopes
            }
        )
        
        # Handle validation failure
        if not validation_result.valid:
            raise PermissionError(
                f"Command '{self.command_name}' requires additional permissions",
                validation_result.missing_scopes
            )
    
    def _extract_user_id(self, request: BoltRequest) -> Optional[str]:
        """Extract user ID from request"""
        if request.body.get("user_id"):
            return request.body["user_id"]
        elif request.body.get("user", {}).get("id"):
            return request.body["user"]["id"]
        return None
    
    def _extract_team_id(self, request: BoltRequest) -> Optional[str]:
        """Extract team ID from request"""
        if request.body.get("team_id"):
            return request.body["team_id"]
        elif request.body.get("team", {}).get("id"):
            return request.body["team"]["id"]
        return None
    
    def _extract_channel_id(self, request: BoltRequest) -> Optional[str]:
        """Extract channel ID from request"""
        if request.body.get("channel_id"):
            return request.body["channel_id"]
        elif request.body.get("channel", {}).get("id"):
            return request.body["channel"]["id"]
        return None
    
    def _log_command_success(self, user_id: Optional[str], team_id: Optional[str],
                           channel_id: Optional[str], start_time: datetime):
        """Log successful command execution"""
        duration = (datetime.now() - start_time).total_seconds()
        
        self.audit_logger.log_command_execution(
            user_id or "unknown",
            team_id or "unknown",
            channel_id or "unknown",
            self.command_name,
            True
        )
        
        logger.info(f"✅ Command '{self.command_name}' completed in {duration:.2f}s for user {user_id}")
    
    def _log_command_error(self, user_id: Optional[str], team_id: Optional[str],
                          channel_id: Optional[str], error_message: str, start_time: datetime):
        """Log command execution error"""
        duration = (datetime.now() - start_time).total_seconds()
        
        self.audit_logger.log_command_execution(
            user_id or "unknown",
            team_id or "unknown", 
            channel_id or "unknown",
            self.command_name,
            False,
            error_message
        )
        
        logger.warning(f"❌ Command '{self.command_name}' failed in {duration:.2f}s for user {user_id}: {error_message}")
    
    def _format_response(self, result: Union[Dict[str, Any], str]) -> Dict[str, Any]:
        """Format command response"""
        if isinstance(result, dict):
            # Already formatted
            return result
        elif isinstance(result, str):
            # Simple string response
            return {
                "response_type": "in_channel",
                "text": result
            }
        else:
            # Convert to string
            return {
                "response_type": "in_channel", 
                "text": str(result)
            }
    
    def _format_permission_error(self, error: PermissionError) -> Dict[str, Any]:
        """Format permission error response"""
        message = "🔒 **Permission Required**\n\n"
        message += f"{error}\n\n"
        
        if error.missing_scopes:
            message += "**Missing OAuth Scopes:**\n"
            for scope in error.missing_scopes[:5]:  # Limit to 5 for readability
                description = self.scope_validator._get_scope_description(scope)
                message += f"• `{scope}`: {description}\n"
            
            if len(error.missing_scopes) > 5:
                message += f"• ... and {len(error.missing_scopes) - 5} more\n"
        
        message += "\n**To resolve:**\n"
        message += "1. Contact your Slack admin to reinstall the bot with updated permissions\n"
        message += "2. Or try alternative commands that don't require these permissions\n"
        
        return {
            "response_type": "ephemeral",
            "text": message
        }
    
    def _format_command_error(self, error: CommandError) -> Dict[str, Any]:
        """Format command error response"""
        if error.user_friendly:
            message = f"❌ **Command Error**\n\n{error}"
            
            if error.show_help:
                message += f"\n\n**Help for `{self.command_name}`:**\n{self.description}"
        else:
            message = f"❌ **Error**\n\nSomething went wrong with the `{self.command_name}` command. Please try again or contact support."
        
        return {
            "response_type": "ephemeral",
            "text": message
        }
    
    def _format_unexpected_error(self, error: Exception) -> Dict[str, Any]:
        """Format unexpected error response"""
        return {
            "response_type": "ephemeral",
            "text": f"❌ **Unexpected Error**\n\nSomething unexpected happened while processing your `{self.command_name}` command. The error has been logged and will be investigated.\n\nPlease try again in a few moments."
        }
    
    def create_help_response(self, include_permissions: bool = False) -> Dict[str, Any]:
        """Create standardized help response"""
        message = f"**`{self.command_name}`**\n\n{self.description}\n"
        
        if include_permissions and self.required_scopes:
            message += f"\n**Required Permissions:** {len(self.required_scopes)} OAuth scopes\n"
            message += f"**Token Type:** {self.token_type}\n"
        
        return {
            "response_type": "ephemeral",
            "text": message
        }

def require_permissions(scopes: List[str], token_type: str = 'bot',
                       validation_level: ValidationLevel = ValidationLevel.STRICT):
    """
    Decorator to require specific OAuth scopes for command handlers
    
    Args:
        scopes: Required OAuth scopes
        token_type: 'bot' or 'user' token type
        validation_level: Validation strictness level
    
    Usage:
        @require_permissions(['chat:write', 'channels:read'])
        def handle_search_command(context, request, client):
            # Command implementation
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Extract context from function arguments
            context = None
            request = None
            
            for arg in args:
                if hasattr(arg, 'body') and hasattr(arg, 'headers'):
                    request = arg
                elif hasattr(arg, 'user_id') and hasattr(arg, 'team_id'):
                    context = arg
            
            if not request:
                # If no request found, proceed without validation
                logger.warning(f"No BoltRequest found in {func.__name__} args, skipping permission check")
                return func(*args, **kwargs)
            
            # Extract user/team info
            user_id = None
            team_id = None
            
            if request.body.get("user_id"):
                user_id = request.body["user_id"]
            elif request.body.get("user", {}).get("id"):
                user_id = request.body["user"]["id"]
            
            if request.body.get("team_id"):
                team_id = request.body["team_id"]
            elif request.body.get("team", {}).get("id"):
                team_id = request.body["team"]["id"]
            
            # Validate permissions
            scope_validator = get_scope_validator()
            validation_result = scope_validator.validate_command_permissions(
                func.__name__, scopes, token_type
            )
            
            # Log permission check
            audit_logger = get_audit_logger()
            audit_logger.log_permission_check(
                user_id or "unknown",
                team_id or "unknown",
                func.__name__,
                {
                    'valid': validation_result.valid,
                    'missing_scopes': validation_result.missing_scopes,
                    'available_scopes': validation_result.available_scopes
                }
            )
            
            # Handle validation result
            if not validation_result.valid:
                if validation_level == ValidationLevel.STRICT:
                    error_msg = f"Function {func.__name__} missing required scopes: {validation_result.missing_scopes}"
                    logger.error(error_msg)
                    
                    # Return permission error response
                    return {
                        "response_type": "ephemeral",
                        "text": f"🔒 **Permission Required**\n\nThis command requires additional OAuth scopes: {', '.join(validation_result.missing_scopes)}\n\nPlease contact your Slack admin to reinstall the bot with updated permissions."
                    }
                    
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

# Convenience decorators for common permission patterns
def require_basic_messaging(func: Callable) -> Callable:
    """Require basic messaging permissions"""
    return require_permissions(['chat:write', 'channels:read', 'users:read'])(func)

def require_search_access(func: Callable) -> Callable:
    """Require search and history access permissions"""
    return require_permissions(['search:read', 'channels:history', 'groups:history', 'im:history'])(func)

def require_admin_access(func: Callable) -> Callable:
    """Require admin permissions (user token)"""
    return require_permissions(['admin', 'usergroups:write', 'channels:write'], token_type='user')(func)

def require_file_access(func: Callable) -> Callable:
    """Require file read/write permissions"""
    return require_permissions(['files:read', 'files:write'])(func)

# Helper class for command registration
class CommandRegistry:
    """Registry for tracking available commands"""
    
    def __init__(self):
        self._commands = {}
    
    def register(self, command: BaseCommand):
        """Register a command"""
        self._commands[command.command_name] = command
        logger.info(f"📝 Registered command: {command.command_name}")
    
    def get_command(self, command_name: str) -> Optional[BaseCommand]:
        """Get registered command"""
        return self._commands.get(command_name)
    
    def list_commands(self) -> List[BaseCommand]:
        """List all registered commands"""
        return list(self._commands.values())
    
    def get_help_text(self) -> str:
        """Get help text for all commands"""
        if not self._commands:
            return "No commands registered."
        
        help_text = "**Available Commands:**\n\n"
        for command in self._commands.values():
            help_text += f"• **`{command.command_name}`**: {command.description}\n"
        
        return help_text

# Global command registry
command_registry = CommandRegistry()