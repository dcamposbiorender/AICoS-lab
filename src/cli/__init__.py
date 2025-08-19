"""
CLI Module - User-facing command line interface tools

This module provides user-facing CLI tools that integrate all Phase 1 modules
into a cohesive interface with excellent user experience.

Components:
- errors: Unified error handling framework
- formatters: Output formatting utilities (JSON, CSV, table, markdown)
- interfaces: Abstract interfaces for Agent A & B modules
- interactive: Interactive mode utilities

Design Principles:
- Consistent error handling across all tools
- Multiple output formats for different use cases
- Graceful degradation when dependencies unavailable
- Cross-platform compatibility
- Performance: CLI responds in <3 seconds
"""

__version__ = "1.0.0"
__author__ = "Agent C - CLI Integration Team"