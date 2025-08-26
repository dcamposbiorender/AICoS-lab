#!/usr/bin/env python3
"""
Bot Utilities Package - Phase 4b

Provides utilities for Slack bot functionality including:
- Block Kit formatting for rich messages
- Async/sync bridges for CLI tool integration
- Message formatting and user experience helpers
"""

from .formatters import (
    format_search_results_blocks,
    format_brief_blocks,
    format_error_blocks,
    format_loading_blocks
)

from .async_bridge import run_sync_in_thread, AsyncBridge

__all__ = [
    'format_search_results_blocks',
    'format_brief_blocks', 
    'format_error_blocks',
    'format_loading_blocks',
    'run_sync_in_thread',
    'AsyncBridge'
]