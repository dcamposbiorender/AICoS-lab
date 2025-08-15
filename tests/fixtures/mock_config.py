#!/usr/bin/env python3
"""
Mock configuration data for testing
Provides consistent test data for configuration tests
"""

import tempfile
from pathlib import Path
from typing import Dict, Any


def get_valid_test_environment() -> Dict[str, str]:
    """Get a complete valid test environment configuration"""
    return {
        'AICOS_BASE_DIR': '/tmp/test_aicos_data',
        'SLACK_BOT_TOKEN': 'xoxb-test-bot-token-12345',
        'SLACK_APP_TOKEN': 'xapp-test-app-token-67890', 
        'SLACK_SIGNING_SECRET': 'test-signing-secret-abcdef',
        'GOOGLE_CLIENT_ID': 'test-client-id.apps.googleusercontent.com',
        'GOOGLE_CLIENT_SECRET': 'test-client-secret-xyz123',
        'GOOGLE_REDIRECT_URI': 'http://localhost:8000/auth/callback',
        'ANTHROPIC_API_KEY': 'test-anthropic-key-claude123',
        'OPENAI_API_KEY': 'test-openai-key-sk123',
        'ENVIRONMENT': 'testing',
        'LOG_LEVEL': 'DEBUG',
        'DATA_RETENTION_DAYS': '90',
        'BRIEFING_TIME': '06:00',
        'TIMEZONE': 'America/New_York'
    }


def get_minimal_test_environment() -> Dict[str, str]:
    """Get minimal environment for basic config tests"""
    return {
        'AICOS_BASE_DIR': '/tmp/test_aicos_minimal',
        'SLACK_BOT_TOKEN': 'xoxb-minimal-token'
    }


def get_invalid_test_environment() -> Dict[str, str]:
    """Get environment with invalid values for error testing"""
    return {
        'AICOS_BASE_DIR': '/nonexistent/invalid/path',
        'SLACK_BOT_TOKEN': 'invalid-token-format',
        'GOOGLE_CLIENT_ID': 'invalid-client-id',
        'LOG_LEVEL': 'INVALID_LEVEL',
        'DATA_RETENTION_DAYS': 'not-a-number'
    }


class MockSlackClient:
    """Mock Slack client for testing credential validation"""
    
    def __init__(self, token: str, should_succeed: bool = True):
        self.token = token
        self.should_succeed = should_succeed
    
    def auth_test(self):
        """Mock auth test response"""
        if self.should_succeed:
            return {
                "ok": True,
                "url": "https://test-workspace.slack.com/",
                "team": "Test Workspace", 
                "user": "testbot",
                "team_id": "T1234567890",
                "user_id": "U0987654321",
                "bot_id": "B1122334455"
            }
        else:
            raise Exception("invalid_auth")


class MockGoogleCredentials:
    """Mock Google credentials for testing"""
    
    @staticmethod
    def from_client_config(config, scopes):
        """Mock Google credentials creation"""
        return MockGoogleCredentials()
    
    def to_json(self):
        """Mock credentials serialization"""
        return '{"type": "test", "client_id": "mock-client-id"}'


def create_temp_config_dir() -> Path:
    """Create temporary directory structure for testing"""
    temp_dir = Path(tempfile.mkdtemp(prefix="aicos_test_"))
    
    # Create expected subdirectories
    (temp_dir / "data").mkdir()
    (temp_dir / "data" / "archive").mkdir()
    (temp_dir / "data" / "state").mkdir() 
    (temp_dir / "data" / "logs").mkdir()
    
    return temp_dir


def get_mock_disk_usage(free_gb: int = 15) -> tuple:
    """Get mock disk usage with specified free space in GB"""
    total_bytes = 100 * 1024**3  # 100GB total
    used_bytes = (100 - free_gb) * 1024**3
    free_bytes = free_gb * 1024**3
    
    return (total_bytes, used_bytes, free_bytes)


# Test configuration validation scenarios
CONFIG_TEST_SCENARIOS = {
    'valid_complete': {
        'description': 'Complete valid configuration',
        'environment': get_valid_test_environment(),
        'should_pass': True,
        'disk_free_gb': 20
    },
    'valid_minimal': {
        'description': 'Minimal valid configuration',
        'environment': get_minimal_test_environment(), 
        'should_pass': True,
        'disk_free_gb': 15
    },
    'missing_base_dir': {
        'description': 'Missing AICOS_BASE_DIR',
        'environment': {},
        'should_pass': False,
        'expected_error': 'AICOS_BASE_DIR'
    },
    'insufficient_disk': {
        'description': 'Insufficient disk space',
        'environment': get_minimal_test_environment(),
        'should_pass': False,
        'disk_free_gb': 5,
        'expected_error': 'disk space'
    },
    'invalid_slack_token': {
        'description': 'Invalid Slack credentials',
        'environment': {**get_minimal_test_environment(), 'SLACK_BOT_TOKEN': 'invalid-token'},
        'should_pass': False,
        'expected_error': 'Slack',
        'mock_slack_success': False
    }
}