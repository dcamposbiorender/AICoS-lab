#!/usr/bin/env python3
"""
Slack Bot Module - Phase 4a Foundation

Comprehensive Slack bot implementation with OAuth 2.0 integration, 
permission validation, rate limiting, and security audit trails.

This module provides:
- OAuth 2.0 flow management with 84 comprehensive scope validation
- Runtime permission checking for all API calls
- Dual-mode rate limiting (interactive ≤1s, bulk ≥2s)
- Complete security audit logging
- @require_permissions decorator for command handlers
- Integration with existing authentication infrastructure

Architecture:
- slack_bot.py: Main Bolt application with OAuth integration
- auth/: OAuth flow and scope validation
- middleware/: Security, rate limiting, audit logging 
- commands/: Slash command handlers with permission decorators
- utils/: Slack-specific utilities and formatters
"""

from typing import Dict, Any, Optional
import logging

# Configure logging for bot module
logger = logging.getLogger(__name__)

# Module metadata
__version__ = "1.0.0"
__author__ = "AI Chief of Staff System"
__description__ = "Enterprise-grade Slack bot foundation with OAuth 2.0 and security"

# Export key classes for easy importing
__all__ = [
    'SlackBot',
    'OAuthHandler', 
    'ScopeValidator',
    'PermissionMiddleware',
    'RateLimiter',
    'AuditLogger',
    'BaseCommand',
    'require_permissions'
]

def get_bot_info() -> Dict[str, Any]:
    """Get bot module information"""
    return {
        "version": __version__,
        "description": __description__,
        "features": [
            "OAuth 2.0 integration with 84 scopes",
            "Runtime permission validation",
            "Dual-mode rate limiting",
            "Security audit trails", 
            "Command permission decorators",
            "Enterprise-grade security"
        ],
        "dependencies": [
            "slack-bolt==1.21.2",
            "slack-sdk==3.33.2",
            "src.core.slack_scopes",
            "src.core.permission_checker",
            "src.core.auth_manager"
        ]
    }

# Lazy import pattern for better startup performance
def _lazy_import():
    """Lazy import of bot components"""
    try:
        from .slack_bot import SlackBot
        from .auth.oauth_handler import OAuthHandler
        from .auth.scope_validator import ScopeValidator
        from .middleware.permission_check import PermissionMiddleware
        from .middleware.rate_limiter import RateLimiter
        from .middleware.audit_logger import AuditLogger
        from .commands.base_command import BaseCommand, require_permissions
        
        return {
            'SlackBot': SlackBot,
            'OAuthHandler': OAuthHandler,
            'ScopeValidator': ScopeValidator,
            'PermissionMiddleware': PermissionMiddleware,
            'RateLimiter': RateLimiter,
            'AuditLogger': AuditLogger,
            'BaseCommand': BaseCommand,
            'require_permissions': require_permissions
        }
    except ImportError as e:
        logger.error(f"Failed to import bot components: {e}")
        return {}

# Make components available at module level
def __getattr__(name: str):
    """Dynamic attribute access for lazy loading"""
    components = _lazy_import()
    if name in components:
        return components[name]
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

# Module initialization message
logger.info(f"🤖 AI Chief of Staff Slack Bot Module v{__version__} initialized")
logger.info("Features: OAuth 2.0, Permission Validation, Rate Limiting, Audit Logging")