#!/usr/bin/env python3
"""
pytest configuration for AI Chief of Staff tests
Reuses existing path setup patterns and mock configurations
"""

import sys
import os
import pytest
from pathlib import Path
from unittest.mock import patch, Mock

# REUSE pattern from test_collector_harness.py line 26-27
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set minimal test environment variables
os.environ.setdefault('AICOS_BASE_DIR', '/tmp/test_aicos_data')
os.environ.setdefault('ENVIRONMENT', 'testing')
os.environ.setdefault('LOG_LEVEL', 'DEBUG')

# REUSE mock patterns from tests/fixtures/mock_config.py
try:
    from tests.fixtures.mock_config import get_minimal_test_environment
    # Set mock environment variables for unit tests
    for key, value in get_minimal_test_environment().items():
        os.environ.setdefault(key, value)
except ImportError:
    # Fallback if mock_config not available
    pass

# Universal Slack API mock for all unit tests
@pytest.fixture(autouse=True)
def mock_slack_for_all_tests(request):
    """Auto-mock Slack API for ALL unit tests, skip for integration tests"""
    # Only apply mock to unit tests, not integration tests
    if "unit" in str(request.fspath) or "unit" in str(request.node.parent):
        # Mock the WebClient import inside the method where it's used
        with patch('slack_sdk.WebClient') as mock_webclient:
            # Mock successful Slack auth response
            mock_client = Mock()
            mock_client.auth_test.return_value = {"ok": True, "user": "testbot"}
            mock_webclient.return_value = mock_client
            yield mock_client
    else:
        # No mocking for integration tests - they use real credentials
        yield None