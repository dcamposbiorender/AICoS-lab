#!/usr/bin/env python3
"""
Test suite for atomic state management
Tests file locking, atomic operations, corruption recovery, and concurrent access
"""

import pytest
import os
import json
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import patch, mock_open, Mock
import fcntl
import multiprocessing

# Import will fail initially - expected in Red phase
try:
    from src.core.state import StateManager, StateError
    from src.core.config import Config
except ImportError:
    # Expected during Red phase
    StateManager = None
    StateError = None
    Config = None


class TestAtomicOperations:
    """Test atomic write operations"""
    
    def test_state_write_is_atomic(self):
        """State writes use temp file + rename for atomicity"""
        # ACCEPTANCE: Interrupted writes never leave partial files
        with tempfile.TemporaryDirectory() as temp_dir:
            state_file = Path(temp_dir) / "state.json"
            
            # Mock config to use our temp directory
            mock_config = Mock()
            mock_config.state_dir = Path(temp_dir)
            
            with patch('src.core.state.get_config', return_value=mock_config):
                state_manager = StateManager()
                
                # Test data to write
                test_data = {"test_key": "test_value", "timestamp": "2025-08-15T10:30:00"}
                
                # Mock an interruption during write by making rename fail once
                original_rename = os.rename
                rename_call_count = 0
                
                def mock_rename(src, dst):
                    nonlocal rename_call_count
                    rename_call_count += 1
                    if rename_call_count == 1:
                        # First call fails (simulating interruption)
                        raise OSError("Simulated interruption")
                    # Second call succeeds
                    return original_rename(src, dst)
                
                with patch('os.rename', side_effect=mock_rename):
                    # First write should fail
                    with pytest.raises(OSError):
                        state_manager.write_state("test_source", test_data)
                    
                    # Verify no partial file left behind
                    assert not state_file.exists(), "Partial file should not exist after failed atomic write"
                    
                    # Second write should succeed
                    state_manager.write_state("test_source", test_data)
                    
                    # Verify file exists and contains correct data
                    assert state_file.exists(), "State file should exist after successful write"
                    with open(state_file, 'r') as f:
                        data = json.load(f)
                        assert data["test_source"] == test_data

    def test_temp_file_creation_pattern(self):
        """Verify temp file + rename pattern is used"""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_config = Mock()
            mock_config.state_dir = Path(temp_dir)
            
            with patch('src.core.state.get_config', return_value=mock_config):
                state_manager = StateManager()
                
                # Track calls to NamedTemporaryFile and rename
                with patch('tempfile.NamedTemporaryFile') as mock_temp:
                    with patch('os.rename') as mock_rename:
                        with patch('fcntl.flock') as mock_flock:
                            # Configure mock temp file
                            temp_file_mock = Mock()
                            temp_file_mock.__enter__ = Mock(return_value=temp_file_mock)
                            temp_file_mock.__exit__ = Mock(return_value=None)
                            temp_file_mock.name = str(Path(temp_dir) / "temp_state.tmp")
                            temp_file_mock.fileno.return_value = 3  # Mock file descriptor
                            mock_temp.return_value = temp_file_mock
                            
                            # Perform write operation
                            state_manager.write_state("test", {"key": "value"})
                            
                            # Verify temp file was created in correct directory
                            mock_temp.assert_called_once()
                            call_kwargs = mock_temp.call_args[1]
                            assert call_kwargs['dir'] == str(Path(temp_dir))
                            assert call_kwargs['mode'] == 'w'
                            assert call_kwargs['delete'] == False
                            
                            # Verify rename was called (atomic move)
                            mock_rename.assert_called_once()

    def test_atomic_write_preserves_existing_on_failure(self):
        """Failed writes don't corrupt existing state files"""
        with tempfile.TemporaryDirectory() as temp_dir:
            state_file = Path(temp_dir) / "state.json"
            
            # Create initial state file
            initial_data = {"existing_source": {"important": "data"}}
            with open(state_file, 'w') as f:
                json.dump(initial_data, f)
            
            mock_config = Mock()
            mock_config.state_dir = Path(temp_dir)
            
            with patch('src.core.state.get_config', return_value=mock_config):
                state_manager = StateManager()
                
                # Mock JSON dump to fail
                with patch('json.dump', side_effect=ValueError("JSON encoding failed")):
                    with pytest.raises(ValueError):
                        state_manager.write_state("new_source", {"new": "data"})
                
                # Verify original file is unchanged
                assert state_file.exists(), "Original state file should still exist"
                with open(state_file, 'r') as f:
                    data = json.load(f)
                    assert data == initial_data, "Original data should be preserved"


class TestConcurrentAccess:
    """Test concurrent access safety with file locking"""
    
    def test_concurrent_state_access_safe(self):
        """Multiple processes can safely read/write state"""
        # ACCEPTANCE: 10 concurrent writers, zero corruption
        with tempfile.TemporaryDirectory() as temp_dir:
            state_file = Path(temp_dir) / "state.json"
            
            mock_config = Mock()
            mock_config.state_dir = Path(temp_dir)
            
            def write_worker(worker_id):
                """Worker function for concurrent writes"""
                try:
                    with patch('src.core.state.get_config', return_value=mock_config):
                        state_manager = StateManager()
                        # Each worker writes multiple times
                        for i in range(5):
                            data = {
                                "worker_id": worker_id,
                                "iteration": i,
                                "timestamp": time.time()
                            }
                            state_manager.write_state(f"worker_{worker_id}", data)
                            time.sleep(0.01)  # Small delay to increase contention
                except Exception as e:
                    # Print any errors that occur during testing
                    print(f"Worker {worker_id} failed: {e}")
                    raise
            
            # Start 10 concurrent workers
            threads = []
            for worker_id in range(10):
                thread = threading.Thread(target=write_worker, args=(worker_id,))
                threads.append(thread)
                thread.start()
            
            # Wait for all workers to complete
            for thread in threads:
                thread.join()
            
            # Verify final state is valid JSON and contains all workers
            assert state_file.exists(), "State file should exist after concurrent writes"
            with open(state_file, 'r') as f:
                final_state = json.load(f)
                
            # Should have entries from all 10 workers
            worker_keys = [key for key in final_state.keys() if key.startswith("worker_")]
            assert len(worker_keys) == 10, f"Expected 10 workers, found {len(worker_keys)}"

    def test_file_locking_prevents_conflicts(self):
        """File locking prevents concurrent access issues"""
        # ACCEPTANCE: Second process waits for lock, no data loss
        with tempfile.TemporaryDirectory() as temp_dir:
            state_file = Path(temp_dir) / "state.json"
            lock_acquired_order = []
            
            mock_config = Mock()
            mock_config.state_dir = Path(temp_dir)
            
            def locking_worker(worker_id, delay=0):
                """Worker that holds lock for specified delay"""
                with patch('src.core.state.get_config', return_value=mock_config):
                    state_manager = StateManager()
                    
                    # Patch fcntl.flock to track lock acquisition order
                    original_flock = fcntl.flock
                    def tracking_flock(fd, operation):
                        if operation == fcntl.LOCK_EX:
                            lock_acquired_order.append(worker_id)
                        if delay and worker_id == 0:
                            time.sleep(delay)  # First worker holds lock longer
                        return original_flock(fd, operation)
                    
                    with patch('fcntl.flock', side_effect=tracking_flock):
                        state_manager.write_state(f"worker_{worker_id}", {"id": worker_id})
            
            # Start two workers - first one holds lock longer
            thread1 = threading.Thread(target=locking_worker, args=(0, 0.05))  # 50ms delay
            thread2 = threading.Thread(target=locking_worker, args=(1, 0))     # No delay
            
            thread1.start()
            time.sleep(0.01)  # Ensure thread1 starts first
            thread2.start()
            
            thread1.join()
            thread2.join()
            
            # Verify locks were acquired in proper order (no race condition)
            assert len(lock_acquired_order) == 2, "Both workers should have acquired locks"
            # First worker should get lock first, even though second worker started after
            assert lock_acquired_order[0] == 0, "First worker should acquire lock first"


class TestCorruptionRecovery:
    """Test corruption detection and recovery mechanisms"""
    
    def test_state_corruption_recovery(self):
        """Corrupted state files are detected and recovered"""
        # ACCEPTANCE: Auto-restores from backup, logs warning
        with tempfile.TemporaryDirectory() as temp_dir:
            state_file = Path(temp_dir) / "state.json"
            backup_file = Path(temp_dir) / "state.json.backup"
            
            # Create a valid backup file
            backup_data = {"backed_up_source": {"important": "backup_data"}}
            with open(backup_file, 'w') as f:
                json.dump(backup_data, f)
            
            # Create corrupted main state file
            with open(state_file, 'w') as f:
                f.write('{"invalid": json content}')  # Invalid JSON
            
            mock_config = Mock()
            mock_config.state_dir = Path(temp_dir)
            
            with patch('src.core.state.get_config', return_value=mock_config):
                # Mock logging to capture warnings
                with patch('src.core.state.logger') as mock_logger:
                    state_manager = StateManager()
                    
                    # Try to read state - should trigger recovery
                    state = state_manager.read_state()
                    
                    # Verify recovery occurred
                    assert state == backup_data, "Should restore from backup"
                    # Check that at least one warning was logged about corruption
                    assert mock_logger.warning.called, "Should log warning about corruption"
                    warning_calls = [call[0][0] for call in mock_logger.warning.call_args_list]
                    corruption_warnings = [msg for msg in warning_calls if "corrupted" in msg.lower()]
                    assert len(corruption_warnings) > 0, "Should log corruption warning"

    def test_corruption_without_backup_creates_fresh_state(self):
        """Creates fresh state when no backup exists"""
        with tempfile.TemporaryDirectory() as temp_dir:
            state_file = Path(temp_dir) / "state.json"
            
            # Create corrupted main state file (no backup)
            with open(state_file, 'w') as f:
                f.write('invalid json')
            
            mock_config = Mock()
            mock_config.state_dir = Path(temp_dir)
            
            with patch('src.core.state.get_config', return_value=mock_config):
                with patch('src.core.state.logger') as mock_logger:
                    state_manager = StateManager()
                    state = state_manager.read_state()
                    
                    # Should create fresh empty state
                    assert state == {}, "Should create fresh empty state"
                    # Check that at least one warning was logged
                    assert mock_logger.warning.called, "Should log warning about corruption"


class TestBackupMechanism:
    """Test backup before modify functionality"""
    
    def test_state_backup_before_modify(self):
        """All modifications create backup first"""
        # ACCEPTANCE: .backup file exists before any write operation
        with tempfile.TemporaryDirectory() as temp_dir:
            state_file = Path(temp_dir) / "state.json"
            backup_file = Path(temp_dir) / "state.json.backup"
            
            # Create initial state
            initial_data = {"initial_source": {"data": "original"}}
            with open(state_file, 'w') as f:
                json.dump(initial_data, f)
            
            mock_config = Mock()
            mock_config.state_dir = Path(temp_dir)
            
            with patch('src.core.state.get_config', return_value=mock_config):
                state_manager = StateManager()
                
                # Modify state - should create backup first
                new_data = {"new_source": {"data": "modified"}}
                state_manager.write_state("new_source", new_data)
                
                # Verify backup was created
                assert backup_file.exists(), "Backup file should be created before modification"
                
                # Verify backup contains original data
                with open(backup_file, 'r') as f:
                    backup_data = json.load(f)
                    assert backup_data == initial_data, "Backup should contain original data"

    def test_backup_rotation(self):
        """Backup files are rotated to prevent excessive storage"""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_config = Mock()
            mock_config.state_dir = Path(temp_dir)
            
            with patch('src.core.state.get_config', return_value=mock_config):
                state_manager = StateManager()
                
                # Write multiple states to test backup rotation
                for i in range(5):
                    state_manager.write_state(f"source_{i}", {"iteration": i})
                
                # Should not accumulate too many backup files
                backup_files = list(Path(temp_dir).glob("*.backup*"))
                assert len(backup_files) <= 3, f"Should keep max 3 backups, found {len(backup_files)}"


class TestStateManagerAPI:
    """Test StateManager public API"""
    
    def test_state_manager_initialization(self):
        """StateManager initializes correctly with config"""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_config = Mock()
            mock_config.state_dir = Path(temp_dir)
            
            with patch('src.core.state.get_config', return_value=mock_config):
                state_manager = StateManager()
                
                assert state_manager.state_dir == Path(temp_dir)
                assert hasattr(state_manager, 'state_file')
                assert str(state_manager.state_file).endswith('state.json')

    def test_read_write_state_round_trip(self):
        """State can be written and read back correctly"""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_config = Mock()
            mock_config.state_dir = Path(temp_dir)
            
            with patch('src.core.state.get_config', return_value=mock_config):
                state_manager = StateManager()
                
                # Write test data
                test_data = {
                    "slack": {"cursor": "abc123", "last_run": "2025-08-15T10:00:00"},
                    "calendar": {"cursor": "xyz789", "last_run": "2025-08-15T10:05:00"}
                }
                
                for source, data in test_data.items():
                    state_manager.write_state(source, data)
                
                # Read back and verify
                state = state_manager.read_state()
                for source, expected_data in test_data.items():
                    assert state[source] == expected_data

    def test_get_source_state(self):
        """Can retrieve state for specific source"""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_config = Mock()
            mock_config.state_dir = Path(temp_dir)
            
            with patch('src.core.state.get_config', return_value=mock_config):
                state_manager = StateManager()
                
                # Write state for multiple sources
                state_manager.write_state("slack", {"cursor": "slack_123"})
                state_manager.write_state("calendar", {"cursor": "cal_456"})
                
                # Get specific source state
                slack_state = state_manager.get_source_state("slack")
                assert slack_state == {"cursor": "slack_123"}
                
                # Non-existent source should return None
                missing_state = state_manager.get_source_state("nonexistent")
                assert missing_state is None


class TestErrorHandling:
    """Test error handling and edge cases"""
    
    def test_state_error_exception(self):
        """StateError exception can be raised and caught"""
        try:
            raise StateError("Test state error")
        except StateError as e:
            assert str(e) == "Test state error"

    def test_permission_denied_handling(self):
        """Handles permission denied errors gracefully"""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_config = Mock()
            mock_config.state_dir = Path(temp_dir)
            
            with patch('src.core.state.get_config', return_value=mock_config):
                state_manager = StateManager()
                
                # Mock open to raise PermissionError
                with patch('builtins.open', mock_open()) as mock_file:
                    mock_file.side_effect = PermissionError("Permission denied")
                    
                    with pytest.raises(StateError) as exc_info:
                        state_manager.write_state("test", {"data": "value"})
                    
                    error_msg = str(exc_info.value)
                    assert "Permission denied" in error_msg or "permission" in error_msg.lower()

    def test_disk_full_handling(self):
        """Handles disk full errors gracefully"""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_config = Mock()
            mock_config.state_dir = Path(temp_dir)
            
            with patch('src.core.state.get_config', return_value=mock_config):
                state_manager = StateManager()
                
                # Mock write to raise disk full error
                with patch('builtins.open', mock_open()) as mock_file:
                    mock_file.side_effect = OSError("No space left on device")
                    
                    with pytest.raises(StateError) as exc_info:
                        state_manager.write_state("test", {"data": "value"})
                    
                    error_msg = str(exc_info.value)
                    assert "space" in error_msg.lower() or "disk" in error_msg.lower()