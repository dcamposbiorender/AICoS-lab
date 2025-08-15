"""
Test helpers package for AI Chief of Staff collector testing.

This package provides reusable testing utilities for collector wrappers
and other components of the AI Chief of Staff system.

Available modules:
- collector_helpers: Comprehensive testing utilities for collector wrappers

Key classes:
- CollectorTestHelper: Main helper class for collector testing
- ArchiveTestValidator: Specialized validator for archive testing

Key functions:
- create_test_helper(collector_type): Create a test helper for specific collector
- assert_jsonl_valid(file_path, min_records): Assert JSONL file validity
- assert_archive_structure_valid(archive_path, collector_type): Assert archive structure

Pytest fixtures:
- slack_test_helper: Slack collector test helper
- calendar_test_helper: Calendar collector test helper  
- drive_test_helper: Drive collector test helper
- employee_test_helper: Employee collector test helper
"""

from .collector_helpers import (
    CollectorTestHelper,
    ArchiveTestValidator,
    create_test_helper,
    assert_jsonl_valid,
    assert_archive_structure_valid
)

__all__ = [
    'CollectorTestHelper',
    'ArchiveTestValidator', 
    'create_test_helper',
    'assert_jsonl_valid',
    'assert_archive_structure_valid'
]