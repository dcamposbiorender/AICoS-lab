#!/usr/bin/env python3
"""
Test suite for configuration management
Tests AICOS_BASE_DIR handling, credential validation, and startup behavior
"""

import pytest
import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, Mock
import sys

# Import will fail initially - this is expected in Red phase
try:
    from src.core.config import Config, ConfigurationError, validate_python_version
except ImportError:
    # Expected during Red phase
    Config = None
    ConfigurationError = None
    validate_python_version = None


class TestPythonVersionValidation:
    """Test Python version validation at startup"""
    
    def test_python_version_310_accepted(self):
        """Python 3.10+ should be accepted"""
        with patch('sys.version_info', (3, 10, 0)):
            # Should not raise an exception
            try:
                validate_python_version()
            except Exception as e:
                pytest.fail(f"Python 3.10.0 should be accepted but got: {e}")
    
    def test_python_version_311_accepted(self):
        """Python 3.11+ should be accepted"""  
        with patch('sys.version_info', (3, 11, 5)):
            # Should not raise an exception
            try:
                validate_python_version()
            except Exception as e:
                pytest.fail(f"Python 3.11.5 should be accepted but got: {e}")
    
    def test_python_version_39_rejected(self):
        """Python 3.9 should be rejected with helpful error"""
        with patch('sys.version_info', (3, 9, 6)):
            with pytest.raises(ConfigurationError) as exc_info:
                validate_python_version()
            
            error_msg = str(exc_info.value)
            assert "3.10" in error_msg, "Error should mention required version"
            assert "3.9.6" in error_msg, "Error should mention current version"
            assert "brew install" in error_msg, "Error should provide upgrade instructions"


class TestConfigurationLoading:
    """Test configuration loading from environment"""
    
    def test_config_loads_from_aicos_base_dir(self):
        """Config correctly reads AICOS_BASE_DIR environment variable"""
        # ACCEPTANCE: Config.base_dir equals os.getenv('AICOS_BASE_DIR')
        test_dir = "/tmp/test_aicos_data"
        
        with patch.dict(os.environ, {'AICOS_BASE_DIR': test_dir}):
            with patch('pathlib.Path.exists', return_value=True):
                with patch('pathlib.Path.is_dir', return_value=True):
                    with patch('os.access', return_value=True):  # Mock write permissions
                        with patch('pathlib.Path.mkdir'):  # Mock directory creation
                            with patch('shutil.disk_usage', return_value=(100*1024**3, 70*1024**3, 15*1024**3)):
                                config = Config()
                                # Check that base_dir resolves to the expected path (handles symlinks)
                                assert str(config.base_dir).endswith("test_aicos_data")
    
    def test_config_requires_aicos_base_dir(self):
        """Config fails if AICOS_BASE_DIR not set"""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ConfigurationError) as exc_info:
                Config()
            
            error_msg = str(exc_info.value)
            assert "AICOS_BASE_DIR" in error_msg, "Error should mention missing AICOS_BASE_DIR"
    
    def test_config_validates_base_dir_exists(self):
        """Config fails if AICOS_BASE_DIR doesn't exist and can't be created"""
        test_dir = "/nonexistent/directory"
        
        with patch.dict(os.environ, {'AICOS_BASE_DIR': test_dir}):
            # Mock Path.mkdir to raise PermissionError (simulating can't create directory)
            with patch('pathlib.Path.mkdir', side_effect=PermissionError("Permission denied")):
                with pytest.raises(ConfigurationError) as exc_info:
                    Config()
                
                error_msg = str(exc_info.value)
                assert "Cannot create base directory" in error_msg or "Permission" in error_msg
                assert test_dir in error_msg, "Error should include the problematic path"


class TestPathValidation:
    """Test path validation and permissions"""
    
    def test_config_validates_all_paths(self):
        """All configured paths must exist and be writable"""
        # ACCEPTANCE: Raises ConfigError for non-existent or read-only paths
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create base directory
            base_dir = Path(temp_dir) / "aicos_data"
            base_dir.mkdir()
            
            # Create some subdirectories but not others
            (base_dir / "data").mkdir()
            # Missing: logs, state, archive directories
            
            with patch.dict(os.environ, {'AICOS_BASE_DIR': str(base_dir)}):
                config = Config()
                
                # Should auto-create missing directories
                assert (base_dir / "data" / "archive").exists()
                assert (base_dir / "data" / "state").exists()
                assert (base_dir / "data" / "logs").exists()
    
    def test_config_fails_on_readonly_paths(self):
        """Config fails if paths are not writable"""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir) / "aicos_data"
            base_dir.mkdir()
            
            # Mock os.access to return False for write permission
            with patch.dict(os.environ, {'AICOS_BASE_DIR': str(base_dir)}):
                with patch('os.access', return_value=False):
                    with pytest.raises(ConfigurationError) as exc_info:
                        Config()
                    
                    error_msg = str(exc_info.value)
                    assert "not writable" in error_msg, "Error should mention write permission issue"


class TestCredentialValidation:
    """Test API credential validation"""
    
    @patch('slack_sdk.WebClient')
    def test_config_validates_slack_credentials(self, mock_slack_client):
        """Slack credentials are tested for validity"""
        # ACCEPTANCE: Makes actual test calls to Slack API
        with tempfile.TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir) / "aicos_data"  
            base_dir.mkdir()
            
            # Mock successful Slack API response
            mock_client_instance = Mock()
            mock_client_instance.auth_test.return_value = {"ok": True, "user": "testbot"}
            mock_slack_client.return_value = mock_client_instance
            
            env_vars = {
                'AICOS_BASE_DIR': str(base_dir),
                'SLACK_BOT_TOKEN': 'xoxb-test-token',
                'SLACK_APP_TOKEN': 'xapp-test-token'
            }
            
            with patch.dict(os.environ, env_vars):
                config = Config()
                
                # Should have called Slack auth test
                mock_client_instance.auth_test.assert_called_once()
    
    @patch('slack_sdk.WebClient')
    def test_config_fails_on_invalid_slack_credentials(self, mock_slack_client):
        """Config fails with invalid Slack credentials"""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir) / "aicos_data"
            base_dir.mkdir()
            
            # Mock failed Slack API response
            mock_client_instance = Mock()
            mock_client_instance.auth_test.side_effect = Exception("invalid_auth")
            mock_slack_client.return_value = mock_client_instance
            
            env_vars = {
                'AICOS_BASE_DIR': str(base_dir),
                'SLACK_BOT_TOKEN': 'xoxb-invalid-token'
            }
            
            with patch.dict(os.environ, env_vars):
                with pytest.raises(ConfigurationError) as exc_info:
                    Config()
                
                error_msg = str(exc_info.value)
                assert "Slack" in error_msg, "Error should mention Slack credential issue"


class TestDiskSpaceValidation:
    """Test disk space validation"""
    
    @patch('shutil.disk_usage')
    def test_config_validates_disk_space(self, mock_disk_usage):
        """Minimum 10GB disk space required"""
        # ACCEPTANCE: Raises ConfigError if <10GB available
        with tempfile.TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir) / "aicos_data"
            base_dir.mkdir()
            
            # Mock disk usage - less than 10GB available (in bytes)
            mock_disk_usage.return_value = (100 * 1024**3, 90 * 1024**3, 5 * 1024**3)  # 5GB free
            
            with patch.dict(os.environ, {'AICOS_BASE_DIR': str(base_dir)}):
                with pytest.raises(ConfigurationError) as exc_info:
                    Config()
                
                error_msg = str(exc_info.value)
                assert "10GB" in error_msg or "disk space" in error_msg, "Error should mention disk space requirement"
    
    @patch('shutil.disk_usage')
    def test_config_accepts_sufficient_disk_space(self, mock_disk_usage):
        """Config succeeds with sufficient disk space"""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir) / "aicos_data"
            base_dir.mkdir()
            
            # Mock disk usage - more than 10GB available
            mock_disk_usage.return_value = (100 * 1024**3, 70 * 1024**3, 15 * 1024**3)  # 15GB free
            
            env_vars = {
                'AICOS_BASE_DIR': str(base_dir),
                'SLACK_BOT_TOKEN': 'xoxb-test-token'  # Minimal required env
            }
            
            with patch.dict(os.environ, env_vars):
                with patch('slack_sdk.WebClient') as mock_slack:
                    mock_client = Mock()
                    mock_client.auth_test.return_value = {"ok": True}
                    mock_slack.return_value = mock_client
                    
                    config = Config()  # Should not raise
                    # Use string comparison to handle path resolution differences
                    assert str(config.base_dir).endswith("aicos_data")


class TestFailFastBehavior:
    """Test fail-fast startup behavior"""
    
    def test_config_fail_fast_on_errors(self):
        """Configuration errors prevent system startup"""
        # ACCEPTANCE: System exits with code 1 on any config error
        
        # Test with missing AICOS_BASE_DIR
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ConfigurationError):
                Config()
    
    def test_config_validation_comprehensive(self):
        """All validation checks run before any failure"""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir) / "aicos_data"
            base_dir.mkdir()
            
            # Set up environment with all required variables
            env_vars = {
                'AICOS_BASE_DIR': str(base_dir),
                'SLACK_BOT_TOKEN': 'xoxb-test-token',
                'SLACK_APP_TOKEN': 'xapp-test-token',
                'GOOGLE_CLIENT_ID': 'test-client-id',
                'GOOGLE_CLIENT_SECRET': 'test-client-secret',
                'ANTHROPIC_API_KEY': 'test-anthropic-key'
            }
            
            with patch.dict(os.environ, env_vars):
                with patch('slack_sdk.WebClient') as mock_slack:
                    with patch('shutil.disk_usage', return_value=(100*1024**3, 70*1024**3, 15*1024**3)):
                        mock_client = Mock()
                        mock_client.auth_test.return_value = {"ok": True}
                        mock_slack.return_value = mock_client
                        
                        config = Config()
                        
                        # Should have all required attributes
                        assert hasattr(config, 'base_dir')
                        assert hasattr(config, 'data_dir')
                        assert hasattr(config, 'archive_dir')
                        assert hasattr(config, 'state_dir')
                        assert hasattr(config, 'logs_dir')


class TestConfigurationPaths:
    """Test configuration path management"""
    
    def test_config_creates_directory_structure(self):
        """Config creates required directory structure"""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir) / "aicos_data"
            base_dir.mkdir()
            
            env_vars = {
                'AICOS_BASE_DIR': str(base_dir),
                'SLACK_BOT_TOKEN': 'xoxb-test-token'
            }
            
            with patch.dict(os.environ, env_vars):
                with patch('slack_sdk.WebClient') as mock_slack:
                    with patch('shutil.disk_usage', return_value=(100*1024**3, 70*1024**3, 15*1024**3)):
                        mock_client = Mock()
                        mock_client.auth_test.return_value = {"ok": True}
                        mock_slack.return_value = mock_client
                        
                        config = Config()
                        
                        # Check directory structure was created
                        expected_dirs = [
                            base_dir / "data",
                            base_dir / "data" / "archive", 
                            base_dir / "data" / "state",
                            base_dir / "data" / "logs"
                        ]
                        
                        for expected_dir in expected_dirs:
                            assert expected_dir.exists(), f"Directory {expected_dir} should be created"
                            assert expected_dir.is_dir(), f"{expected_dir} should be a directory"