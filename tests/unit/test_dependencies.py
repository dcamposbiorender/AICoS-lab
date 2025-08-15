#!/usr/bin/env python3
"""
Test suite for dependency validation and environment setup
Tests that all required packages can be imported and no version conflicts exist
"""

import pytest
import importlib
import subprocess
import sys
from pathlib import Path


def test_all_base_requirements_importable():
    """All packages in requirements/base.txt can be imported successfully"""
    # ACCEPTANCE: Zero import errors for any base dependency
    base_requirements_file = Path(__file__).parent.parent.parent / 'requirements' / 'base.txt'
    
    # This test will fail initially since we haven't created base.txt yet
    assert base_requirements_file.exists(), "requirements/base.txt must exist"
    
    # Read and parse requirements
    with open(base_requirements_file, 'r') as f:
        lines = f.readlines()
    
    # Extract package names (ignore comments, empty lines, and version specifiers)
    packages = []
    # Package name mapping for packages with different import names
    import_name_mapping = {
        'python-dotenv': 'dotenv',
        'google-api-python-client': 'googleapiclient',
        'google-auth': 'google.auth',
        'google-auth-oauthlib': 'google_auth_oauthlib',
        'google-auth-httplib2': 'google_auth_httplib2',
        'slack-sdk': 'slack_sdk',
        'slack-bolt': 'slack_bolt',
        'pathlib-abc': 'pathlib_abc'
    }
    
    for line in lines:
        line = line.strip()
        if line and not line.startswith('#'):
            # Extract package name before any version specifiers
            package_name = line.split('==')[0].split('>=')[0].split('<=')[0].split('~=')[0]
            # Map to correct import name
            import_name = import_name_mapping.get(package_name, package_name.replace('-', '_'))
            packages.append(import_name)
    
    # Try to import each package
    import_errors = []
    for package in packages:
        try:
            importlib.import_module(package)
        except ImportError as e:
            import_errors.append(f"{package}: {e}")
    
    assert len(import_errors) == 0, f"Import errors found: {import_errors}"


def test_dev_requirements_importable():
    """All development tools can be imported"""
    # ACCEPTANCE: black, mypy, coverage, pytest all importable
    dev_requirements_file = Path(__file__).parent.parent.parent / 'requirements' / 'dev.txt'
    
    # This test will fail initially since we haven't created dev.txt yet
    assert dev_requirements_file.exists(), "requirements/dev.txt must exist"
    
    # Essential dev tools that must be importable
    essential_dev_tools = ['black', 'mypy', 'coverage', 'pytest']
    
    import_errors = []
    for tool in essential_dev_tools:
        try:
            importlib.import_module(tool)
        except ImportError as e:
            import_errors.append(f"{tool}: {e}")
    
    assert len(import_errors) == 0, f"Dev tool import errors: {import_errors}"


def test_env_example_completeness():
    """Template .env.example has all required variables"""
    # ACCEPTANCE: Every required variable present with example values
    env_example_file = Path(__file__).parent.parent.parent / '.env.example'
    
    # This test will fail initially since we haven't created .env.example yet
    assert env_example_file.exists(), ".env.example must exist"
    
    # Required environment variables based on project requirements
    required_vars = [
        'AICOS_BASE_DIR',
        'SLACK_BOT_TOKEN', 
        'SLACK_APP_TOKEN',
        'SLACK_SIGNING_SECRET',
        'GOOGLE_CLIENT_ID',
        'GOOGLE_CLIENT_SECRET', 
        'GOOGLE_REDIRECT_URI',
        'ANTHROPIC_API_KEY',
        'OPENAI_API_KEY',
        'ENVIRONMENT',
        'LOG_LEVEL',
        'DATA_RETENTION_DAYS',
        'BRIEFING_TIME',
        'TIMEZONE'
    ]
    
    # Read .env.example content
    with open(env_example_file, 'r') as f:
        content = f.read()
    
    # Check that all required variables are present
    missing_vars = []
    for var in required_vars:
        if f"{var}=" not in content:
            missing_vars.append(var)
    
    assert len(missing_vars) == 0, f"Missing required variables in .env.example: {missing_vars}"
    assert len(required_vars) >= 14, f"Must have at least 14 required variables, got {len(required_vars)}"


def test_requirements_no_version_conflicts():
    """No conflicting package versions"""
    # ACCEPTANCE: pip-compile runs without conflicts
    
    # Check that main requirements.txt includes both base and dev
    main_requirements = Path(__file__).parent.parent.parent / 'requirements.txt'
    assert main_requirements.exists(), "requirements.txt must exist"
    
    # Try to install requirements to check for conflicts
    # Note: This is a basic check - in production we'd use pip-tools
    result = subprocess.run([
        sys.executable, '-m', 'pip', 'check'
    ], capture_output=True, text=True)
    
    # pip check should pass (return code 0) if no conflicts
    assert result.returncode == 0, f"Package conflicts detected: {result.stdout}{result.stderr}"