#!/usr/bin/env python3
"""
Test suite for .env.example template validation
Tests that environment template is complete and well-formed
"""

import pytest
from pathlib import Path
import re


def test_env_example_format_valid():
    """Environment template follows proper .env format"""
    env_example_file = Path(__file__).parent.parent.parent / '.env.example'
    
    # This test will fail initially since we haven't created .env.example yet
    assert env_example_file.exists(), ".env.example must exist"
    
    with open(env_example_file, 'r') as f:
        lines = f.readlines()
    
    # Check each non-comment, non-empty line follows VAR=value format
    format_errors = []
    for i, line in enumerate(lines, 1):
        line = line.strip()
        if line and not line.startswith('#'):
            if '=' not in line:
                format_errors.append(f"Line {i}: Missing '=' in '{line}'")
            elif not re.match(r'^[A-Z_][A-Z0-9_]*=.*$', line):
                format_errors.append(f"Line {i}: Invalid format '{line}'")
    
    assert len(format_errors) == 0, f"Format errors in .env.example: {format_errors}"


def test_env_example_has_comments():
    """Environment template includes helpful comments"""
    env_example_file = Path(__file__).parent.parent.parent / '.env.example'
    
    assert env_example_file.exists(), ".env.example must exist"
    
    with open(env_example_file, 'r') as f:
        content = f.read()
    
    # Should have comment lines explaining sections
    assert '# Slack Configuration' in content or '# SLACK' in content, "Should have Slack section comments"
    assert '# Google' in content or '# GOOGLE' in content, "Should have Google section comments"
    assert '# AI Services' in content or '# ANTHROPIC' in content, "Should have AI services comments"


def test_env_example_no_real_secrets():
    """Environment template doesn't contain real credentials"""
    env_example_file = Path(__file__).parent.parent.parent / '.env.example'
    
    assert env_example_file.exists(), ".env.example must exist"
    
    with open(env_example_file, 'r') as f:
        content = f.read().lower()
    
    # Should not contain patterns that look like real credentials
    forbidden_patterns = [
        'xoxb-',  # Real Slack bot tokens
        'xapp-',  # Real Slack app tokens  
        'sk-',    # Real OpenAI API keys
        'claude-' # Real Anthropic keys might start with this
    ]
    
    found_patterns = []
    for pattern in forbidden_patterns:
        if pattern in content:
            found_patterns.append(pattern)
    
    assert len(found_patterns) == 0, f"Found real credential patterns: {found_patterns}"


def test_env_example_has_placeholder_values():
    """Environment template has meaningful placeholder values"""
    env_example_file = Path(__file__).parent.parent.parent / '.env.example'
    
    assert env_example_file.exists(), ".env.example must exist"
    
    with open(env_example_file, 'r') as f:
        lines = f.readlines()
    
    # Check for placeholder patterns
    placeholder_count = 0
    for line in lines:
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            value = line.split('=', 1)[1]
            # Count lines with placeholder-style values
            if any(placeholder in value for placeholder in ['your-', 'YOUR_', 'example', 'EXAMPLE', '/path/to/']):
                placeholder_count += 1
    
    # Should have several placeholder values
    assert placeholder_count >= 5, f"Should have at least 5 placeholder values, got {placeholder_count}"