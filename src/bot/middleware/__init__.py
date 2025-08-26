#!/usr/bin/env python3
"""
Bot Middleware Module

Security, rate limiting, and audit logging middleware for Slack bot.
"""

__all__ = ['PermissionMiddleware', 'RateLimiter', 'AuditLogger']