#!/usr/bin/env python3
"""
Mock user data for testing user identity functionality
Provides realistic test data for PRIMARY_USER configuration and identity mapping
"""

from datetime import datetime

# Primary user mock data for testing
MOCK_PRIMARY_USER = {
    "email": "david.campos@biorender.com",
    "slack_id": "U123456789",
    "calendar_id": "david.campos@biorender.com", 
    "name": "David Campos"
}

# Alternative primary user for testing different configurations
MOCK_PRIMARY_USER_ALT = {
    "email": "alice.johnson@company.com",
    "slack_id": "U987654321",
    "calendar_id": "alice.johnson@company.com",
    "name": "Alice Johnson"
}

# Mock employee data for identity mapping tests
MOCK_EMPLOYEE_DATA = [
    {
        "email": "david.campos@biorender.com",
        "slack_id": "U123456789",
        "slack_name": "David Campos",
        "calendar_id": "david.campos@biorender.com",
        "sources": ["slack", "calendar"],
        "last_seen": "2025-08-28T10:00:00Z"
    },
    {
        "email": "alice.johnson@company.com", 
        "slack_id": "U987654321",
        "slack_name": "Alice Johnson",
        "calendar_id": "alice.johnson@company.com",
        "sources": ["slack", "calendar", "drive"],
        "last_seen": "2025-08-28T09:30:00Z"
    },
    {
        "email": "bob.smith@company.com",
        "slack_id": "U555666777",
        "slack_name": "Bob Smith",
        "calendar_id": "bob.smith@company.com",
        "sources": ["slack"],
        "last_seen": "2025-08-28T08:45:00Z"
    },
    {
        "email": "charlie.brown@company.com",
        "slack_id": "U444333222",
        "slack_name": "Charlie Brown",
        "calendar_id": "charlie.brown@company.com",
        "sources": ["calendar"],
        "last_seen": "2025-08-27T16:20:00Z"
    }
]

# Mock Slack user data for cross-system mapping
MOCK_SLACK_USERS = {
    "U123456789": {
        "id": "U123456789",
        "name": "david.campos",
        "real_name": "David Campos",
        "profile": {
            "email": "david.campos@biorender.com",
            "display_name": "David",
            "title": "CTO"
        }
    },
    "U987654321": {
        "id": "U987654321", 
        "name": "alice.johnson",
        "real_name": "Alice Johnson",
        "profile": {
            "email": "alice.johnson@company.com",
            "display_name": "Alice",
            "title": "Product Manager"
        }
    },
    "U555666777": {
        "id": "U555666777",
        "name": "bob.smith", 
        "real_name": "Bob Smith",
        "profile": {
            "email": "bob.smith@company.com",
            "display_name": "Bob",
            "title": "Designer"
        }
    }
}

# Environment variable configurations for testing
MOCK_ENV_CONFIGS = {
    "complete_config": {
        "AICOS_PRIMARY_USER_EMAIL": "david.campos@biorender.com",
        "AICOS_PRIMARY_USER_SLACK_ID": "U123456789",
        "AICOS_PRIMARY_USER_CALENDAR_ID": "david.campos@biorender.com",
        "AICOS_PRIMARY_USER_NAME": "David Campos"
    },
    "minimal_config": {
        "AICOS_PRIMARY_USER_EMAIL": "alice.johnson@company.com"
    },
    "invalid_email_config": {
        "AICOS_PRIMARY_USER_EMAIL": "invalid-email",
        "AICOS_PRIMARY_USER_NAME": "Invalid User"
    },
    "empty_config": {}
}

# Mock configuration objects for testing
class MockConfig:
    """Mock configuration object for testing UserIdentity"""
    
    def __init__(self, env_vars=None):
        self.env_vars = env_vars or {}
        self.test_mode = True
    
    def get_env_var(self, key, default=None):
        """Simulate environment variable access"""
        return self.env_vars.get(key, default)

# Test scenarios for different configuration states
TEST_SCENARIOS = {
    "valid_primary_user": {
        "description": "Valid PRIMARY_USER configuration with all fields",
        "config": MOCK_ENV_CONFIGS["complete_config"],
        "expected_user": MOCK_PRIMARY_USER,
        "should_succeed": True
    },
    "minimal_primary_user": {
        "description": "Valid PRIMARY_USER with only email",
        "config": MOCK_ENV_CONFIGS["minimal_config"],
        "expected_user": {
            "email": "alice.johnson@company.com",
            "slack_id": None,
            "calendar_id": "alice.johnson@company.com",  # Default to email
            "name": None
        },
        "should_succeed": True
    },
    "no_primary_user": {
        "description": "No PRIMARY_USER configured (backwards compatibility)",
        "config": MOCK_ENV_CONFIGS["empty_config"],
        "expected_user": None,
        "should_succeed": True
    },
    "invalid_email": {
        "description": "Invalid email format",
        "config": MOCK_ENV_CONFIGS["invalid_email_config"],
        "expected_user": None,
        "should_succeed": False
    }
}

# Mock identity mapping scenarios
IDENTITY_MAPPING_SCENARIOS = {
    "email_to_slack_id": {
        "input": "david.campos@biorender.com",
        "expected_slack_id": "U123456789",
        "should_find": True
    },
    "email_to_calendar_id": {
        "input": "alice.johnson@company.com", 
        "expected_calendar_id": "alice.johnson@company.com",
        "should_find": True
    },
    "unknown_user": {
        "input": "unknown@example.com",
        "expected_slack_id": None,
        "expected_calendar_id": None,
        "should_find": False
    }
}

def get_mock_primary_user():
    """Get the default mock primary user"""
    return MOCK_PRIMARY_USER.copy()

def get_mock_employee_data():
    """Get copy of mock employee data"""
    return [employee.copy() for employee in MOCK_EMPLOYEE_DATA]

def get_mock_slack_users():
    """Get copy of mock Slack users"""
    return {k: v.copy() for k, v in MOCK_SLACK_USERS.items()}

def create_mock_config(scenario="complete_config"):
    """Create a mock configuration for testing"""
    return MockConfig(MOCK_ENV_CONFIGS.get(scenario, {}))