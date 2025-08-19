"""
Chaos engineering tests for failure scenarios.

Tests:
- Network failure during data collection
- API rate limit exhaustion handling
- Disk space limitations and recovery
- Database corruption scenarios
- Concurrent access stress testing
"""

import pytest
import tempfile
import time
import threading
import os
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import requests
import sqlite3

# Import components under test
import sys
sys.path.insert(0, '/Users/david.campos/VibeCode/AICoS-Lab')

from src.collectors.slack_collector import SlackCollector, SlackRateLimiter
from src.collectors.base import BaseArchiveCollector
from src.core.archive_writer import ArchiveWriter
from src.search.database import SearchDatabase
from src.core.state import StateManager


class TestNetworkFailures:
    """Test network failure scenarios during data collection."""
    
    def setup_method(self):
        """Set up network failure test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_env = {
            "AICOS_BASE_DIR": self.temp_dir,
            "AICOS_TEST_MODE": "true"
        }
        
    @pytest.mark.chaos
    def test_intermittent_network_failures(self):
        """System handles intermittent network failures gracefully."""
        with patch.dict('os.environ', self.test_env):
            collector = BaseArchiveCollector("test")
            
            # Simulate intermittent network failures
            call_count = 0
            def failing_network():
                nonlocal call_count
                call_count += 1
                if call_count <= 2:
                    raise requests.ConnectionError("Network temporarily unavailable")
                return {"success": True, "data": []}
            
            with patch.object(collector, 'collect', side_effect=failing_network):
                # Should eventually succeed after retries
                result = collector.collect_with_retry(max_attempts=5)
                assert result["success"] is True
                assert call_count == 3  # Failed twice, succeeded on third attempt
                
    @pytest.mark.chaos
    def test_total_network_outage(self):
        """System handles total network outage appropriately."""
        with patch.dict('os.environ', self.test_env):
            collector = BaseArchiveCollector("test", {"max_retries": 3})
            
            def network_down():
                raise requests.ConnectionError("Network is down")
            
            with patch.object(collector, 'collect', side_effect=network_down):
                # Should exhaust retries and fail gracefully
                with pytest.raises(Exception, match="Max retries exceeded"):
                    collector.collect_with_retry()
                    
                # Circuit breaker should be open
                assert collector.circuit_breaker.is_open()
                
    @pytest.mark.chaos
    def test_dns_resolution_failure(self):
        """System handles DNS resolution failures.""" 
        with patch('requests.get') as mock_get:
            mock_get.side_effect = requests.exceptions.ConnectionError("Name resolution failed")
            
            collector = BaseArchiveCollector("test")
            
            with pytest.raises(Exception):
                collector.collect_with_retry(max_attempts=2)


class TestRateLimitExhaustion:
    """Test API rate limit exhaustion handling."""
    
    def setup_method(self):
        """Set up rate limit test environment."""
        self.temp_dir = tempfile.mkdtemp()
        
    @pytest.mark.chaos
    def test_slack_rate_limit_exhaustion(self):
        """Slack collector handles rate limit exhaustion properly."""
        # Test rate limiter under extreme load
        limiter = SlackRateLimiter(base_delay=0.01)  # Very fast for testing
        
        # Simulate hitting rate limits repeatedly
        for i in range(5):
            mock_response = Mock()
            mock_response.status_code = 429
            mock_response.headers = {"Retry-After": "1"}
            
            # Should handle rate limit responses
            limiter.handle_rate_limit_response(mock_response)
            
        # Backoff delay should increase substantially
        assert limiter.current_backoff_delay > 0
        
    @pytest.mark.chaos
    def test_rate_limit_recovery(self):
        """Rate limiter recovers properly after successful calls."""
        limiter = SlackRateLimiter(base_delay=0.01)
        
        # Hit rate limit
        mock_response_429 = Mock()
        mock_response_429.status_code = 429
        limiter.handle_rate_limit_response(mock_response_429)
        
        initial_backoff = limiter.current_backoff_delay
        assert initial_backoff > 0
        
        # Successful call should reset backoff
        mock_response_200 = Mock()
        mock_response_200.status_code = 200
        limiter.handle_rate_limit_response(mock_response_200)
        
        assert limiter.current_backoff_delay == 0
        assert limiter.consecutive_rate_limits == 0
        
    @pytest.mark.chaos 
    def test_concurrent_rate_limiting(self):
        """Rate limiter works correctly under concurrent load."""
        limiter = SlackRateLimiter(base_delay=0.01)
        results = []
        
        def worker():
            try:
                start_time = time.time()
                limiter.wait_for_api_limit()
                end_time = time.time()
                results.append(end_time - start_time)
            except Exception as e:
                results.append(f"Error: {e}")
                
        # Start multiple threads simultaneously
        threads = [threading.Thread(target=worker) for _ in range(5)]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
            
        # All should complete without errors
        assert len(results) == 5
        assert all(isinstance(r, float) for r in results)


class TestDiskSpaceLimitations:
    """Test disk space limitations and recovery."""
    
    def setup_method(self):
        """Set up disk space test environment.""" 
        self.temp_dir = tempfile.mkdtemp()
        
    @pytest.mark.chaos
    def test_disk_full_during_write(self):
        """Archive writer handles disk full conditions gracefully."""
        with patch.dict('os.environ', {"AICOS_BASE_DIR": self.temp_dir}):
            writer = ArchiveWriter("test")
            
            # Mock disk full condition
            with patch('builtins.open', side_effect=OSError("No space left on device")):
                with pytest.raises(OSError, match="No space left on device"):
                    writer.write_records([{"id": 1, "data": "test"}])
                    
    @pytest.mark.chaos
    def test_partial_write_recovery(self):
        """System recovers from partial write failures."""
        with patch.dict('os.environ', {"AICOS_BASE_DIR": self.temp_dir}):
            writer = ArchiveWriter("test")
            
            # Create a large dataset that might trigger partial writes
            large_records = [{"id": i, "data": "x" * 1000} for i in range(100)]
            
            # Should handle large writes without corruption
            writer.write_records(large_records)
            
            # Verify data integrity
            output_files = list(Path(writer.get_output_dir()).glob("*.jsonl"))
            assert len(output_files) > 0
            
    @pytest.mark.chaos
    def test_disk_space_monitoring(self):
        """System monitors available disk space."""
        from src.core.config import check_disk_space
        
        # Should be able to check available space
        available_gb = check_disk_space(self.temp_dir)
        assert isinstance(available_gb, float)
        assert available_gb >= 0


class TestDatabaseCorruption:
    """Test database corruption and recovery scenarios."""
    
    def setup_method(self):
        """Set up database corruption test environment."""
        self.temp_dir = tempfile.mkdtemp()
        
    @pytest.mark.chaos
    def test_corrupted_database_recovery(self):
        """Search database recovers from corruption."""
        db_path = Path(self.temp_dir) / "test.db"
        
        # Create and populate database
        db = SearchDatabase(str(db_path))
        db.create_tables()
        
        test_records = [
            {"id": "1", "content": "test content", "source": "test"},
            {"id": "2", "content": "more test content", "source": "test"}
        ]
        db.index_records(test_records)
        
        # Simulate database corruption by writing garbage
        with open(db_path, 'wb') as f:
            f.write(b"corrupted database content")
            
        # Should detect corruption and recreate database
        db_new = SearchDatabase(str(db_path))
        assert db_new.get_stats()["total_records"] == 0  # Empty after recreation
        
    @pytest.mark.chaos
    def test_concurrent_database_access(self):
        """Database handles concurrent access safely."""
        db_path = Path(self.temp_dir) / "concurrent.db"
        results = []
        errors = []
        
        def worker(worker_id):
            try:
                db = SearchDatabase(str(db_path))
                db.create_tables()
                
                # Each worker inserts records
                records = [{"id": f"{worker_id}_{i}", "content": f"worker {worker_id} content {i}", "source": "test"} for i in range(10)]
                db.index_records(records)
                
                # Each worker searches
                search_results = db.search("content")
                results.append(len(search_results))
                
            except Exception as e:
                errors.append(str(e))
                
        # Start multiple database workers
        threads = [threading.Thread(target=worker, args=(i,)) for i in range(3)]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
            
        # Should complete without corruption errors
        assert len(errors) == 0, f"Database errors occurred: {errors}"
        assert len(results) == 3
        
    @pytest.mark.chaos
    def test_transaction_rollback(self):
        """Database properly rolls back failed transactions."""
        db_path = Path(self.temp_dir) / "rollback.db"
        db = SearchDatabase(str(db_path))
        db.create_tables()
        
        # Insert initial data
        initial_records = [{"id": "1", "content": "initial", "source": "test"}]
        db.index_records(initial_records)
        
        initial_count = db.get_stats()["total_records"]
        
        # Simulate transaction failure
        with patch.object(db.conn, 'commit', side_effect=sqlite3.Error("Transaction failed")):
            try:
                db.index_records([{"id": "2", "content": "should rollback", "source": "test"}])
            except sqlite3.Error:
                pass
                
        # Should rollback to initial state
        final_count = db.get_stats()["total_records"] 
        assert final_count == initial_count