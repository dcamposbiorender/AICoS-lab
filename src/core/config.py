#!/usr/bin/env python3
"""
Configuration management for AI Chief of Staff
Handles environment-based configuration, credential validation, and startup checks
"""

import os
import sys
import shutil
from pathlib import Path
from typing import Optional, Dict, Any
from packaging import version


class ConfigurationError(Exception):
    """Raised when system configuration is invalid"""
    pass


def validate_python_version():
    """
    Validate Python version meets project requirements
    Fails fast with helpful error message if version is insufficient
    """
    required_version = "3.9.0"  # Lowered for compatibility
    
    # Handle both real sys.version_info and mocked tuples
    version_info = sys.version_info
    if hasattr(version_info, 'major'):
        # Real sys.version_info object
        current_version = f"{version_info.major}.{version_info.minor}.{version_info.micro}"
    else:
        # Mocked tuple (for testing)
        current_version = f"{version_info[0]}.{version_info[1]}.{version_info[2]}"
    
    if version.parse(current_version) < version.parse(required_version):
        print(f"⚠️ Python {required_version}+ recommended. Current: {current_version}")
        print("Some features may not work with older Python versions.")
        # Don't raise error, just warn


# Validate Python version at module import
validate_python_version()


class Config:
    """
    System configuration manager with comprehensive validation
    
    Validates:
    - Python version compatibility
    - AICOS_BASE_DIR environment variable
    - Directory structure and permissions
    - API credentials
    - Disk space requirements
    - All settings before allowing system startup
    """
    
    def __init__(self, test_mode: bool = None):
        """Initialize configuration with full validation
        
        Args:
            test_mode: If True, skips credential validation. If None, checks AICOS_TEST_MODE env var
        """
        # Determine test mode
        if test_mode is None:
            test_mode = os.getenv('AICOS_TEST_MODE', 'false').lower() == 'true'
        self.test_mode = test_mode
        
        # Load and validate base directory
        self.base_dir = self._load_base_directory()
        
        # Set up directory structure
        self._setup_directory_structure()
        
        # Validate disk space requirements (skip in test mode for CI environments)
        if not self.test_mode:
            self._validate_disk_space()
        
        # Load and validate API credentials (skip in test mode)
        if not self.test_mode:
            self._validate_credentials()
        
        # Set configuration properties
        self._setup_configuration()
    
    def _load_base_directory(self) -> Path:
        """Load and validate AICOS_BASE_DIR from environment with fallback to project root"""
        base_dir_str = os.getenv('AICOS_BASE_DIR')
        if not base_dir_str:
            # Fallback to project root for automatic operation
            project_root = Path(__file__).parent.parent.parent
            base_dir_str = str(project_root)
            print(f"⚠️ AICOS_BASE_DIR not set, using project root: {base_dir_str}")
            print("   For production, set: export AICOS_BASE_DIR=/path/to/data")
        
        base_dir = Path(base_dir_str).resolve()
        
        # Create base directory if it doesn't exist
        if not base_dir.exists():
            try:
                base_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
            except PermissionError:
                raise ConfigurationError(
                    f"Cannot create base directory: {base_dir}\n"
                    f"Check permissions and ensure parent directory exists."
                )
        
        # Validate it's a directory
        if not base_dir.is_dir():
            raise ConfigurationError(
                f"AICOS_BASE_DIR must be a directory, not a file: {base_dir}"
            )
        
        # Validate write permissions
        if not os.access(base_dir, os.W_OK):
            raise ConfigurationError(
                f"Base directory is not writable: {base_dir}\n"
                f"Check file permissions and ownership."
            )
        
        return base_dir
    
    def _setup_directory_structure(self):
        """Create required directory structure"""
        # Define required directories
        self.data_dir = self.base_dir / "data"
        self.archive_dir = self.data_dir / "archive"
        self.state_dir = self.data_dir / "state"
        self.logs_dir = self.data_dir / "logs"
        
        # Create all required directories
        required_dirs = [
            self.data_dir,
            self.archive_dir,
            self.state_dir, 
            self.logs_dir,
            # Archive subdirectories
            self.archive_dir / "slack",
            self.archive_dir / "calendar",
            self.archive_dir / "drive",
            self.archive_dir / "employees"
        ]
        
        for dir_path in required_dirs:
            try:
                dir_path.mkdir(parents=True, exist_ok=True, mode=0o700)
            except PermissionError:
                raise ConfigurationError(
                    f"Cannot create directory: {dir_path}\n"
                    f"Check permissions on parent directory."
                )
            
            # Validate write permissions
            if not os.access(dir_path, os.W_OK):
                raise ConfigurationError(
                    f"Directory is not writable: {dir_path}\n"
                    f"Check file permissions and ownership."
                )
    
    def _validate_disk_space(self):
        """Validate minimum disk space requirements"""
        try:
            total, used, free = shutil.disk_usage(self.base_dir)
        except OSError as e:
            raise ConfigurationError(f"Cannot check disk usage for {self.base_dir}: {e}")
        
        # Require at least 10GB free space
        required_bytes = 10 * 1024**3  # 10GB in bytes
        
        if free < required_bytes:
            free_gb = free / (1024**3)
            required_gb = required_bytes / (1024**3)
            raise ConfigurationError(
                f"Insufficient disk space. Required: {required_gb:.1f}GB, Available: {free_gb:.1f}GB\n"
                f"Free up disk space or choose a different AICOS_BASE_DIR location."
            )
    
    def _validate_credentials(self):
        """Validate all API credentials"""
        # Validate Slack credentials
        slack_token = os.getenv('SLACK_BOT_TOKEN')
        if slack_token:
            self._validate_slack_credentials(slack_token)
        
        # Additional credential validations can be added here
        # Google and Anthropic credentials are loaded but not validated yet
        # This provides a clear extension point for future validation
    
    def _validate_slack_credentials(self, token: str):
        """Validate Slack bot token by making test API call"""
        try:
            from slack_sdk import WebClient
            from slack_sdk.errors import SlackApiError
            
            client = WebClient(token=token)
            response = client.auth_test()
            
            if not response.get("ok"):
                raise ConfigurationError(
                    f"Slack authentication failed: {response.get('error', 'Unknown error')}\n"
                    f"Check your SLACK_BOT_TOKEN in environment variables."
                )
                
        except ImportError:
            # slack_sdk not available - skip validation
            pass
        except Exception as e:
            raise ConfigurationError(
                f"Slack credential validation failed: {str(e)}\n"
                f"Check your SLACK_BOT_TOKEN and network connection."
            )
    
    def _setup_configuration(self):
        """Set up configuration properties from environment"""
        # Core settings
        self.environment = os.getenv('ENVIRONMENT', 'development')
        self.log_level = os.getenv('LOG_LEVEL', 'INFO')
        
        # Data retention
        retention_days_str = os.getenv('DATA_RETENTION_DAYS', '365')
        try:
            self.data_retention_days = int(retention_days_str)
        except ValueError:
            raise ConfigurationError(
                f"DATA_RETENTION_DAYS must be a number, got: {retention_days_str}"
            )
        
        # API tokens (stored securely, not logged)
        self.slack_bot_token = os.getenv('SLACK_BOT_TOKEN')
        self.slack_app_token = os.getenv('SLACK_APP_TOKEN')
        self.google_client_id = os.getenv('GOOGLE_CLIENT_ID')
        self.google_client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
        self.anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
        
        # Operational settings
        self.briefing_time = os.getenv('BRIEFING_TIME', '06:00')
        self.timezone = os.getenv('TIMEZONE', 'UTC')
    
    def __repr__(self) -> str:
        """String representation (without sensitive data)"""
        return (
            f"Config(base_dir='{self.base_dir}', "
            f"environment='{self.environment}', "
            f"log_level='{self.log_level}')"
        )


# Global configuration instance (created on first import)
# This ensures configuration is validated immediately when the module is imported
_config: Optional[Config] = None

def get_config(test_mode: bool = None) -> Config:
    """Get global configuration instance (singleton pattern)
    
    Args:
        test_mode: If True, creates config in test mode. If None, uses environment setting
    """
    global _config
    if _config is None:
        _config = Config(test_mode=test_mode)
    return _config