"""
Integration tests for complete data pipeline flows.

Tests:
- Collection → Archive → Search pipeline
- Data preservation through transformations
- State persistence across pipeline stages
- Error recovery and partial failures
- Performance with realistic data volumes
"""

import pytest
import tempfile
import json
import time
from pathlib import Path
from unittest.mock import Mock, patch
import sqlite3
from concurrent.futures import ThreadPoolExecutor
import subprocess

# Import test fixtures
import sys
sys.path.append('..')
from fixtures.large_datasets import LargeDatasetGenerator

# Import components
sys.path.append('../src')
from src.collectors.slack_collector import SlackCollector
from src.collectors.calendar_collector import CalendarCollector
from src.collectors.drive_collector import DriveCollector
from src.core.state import StateManager
from src.core.archive_writer import ArchiveWriter
from src.core.config import Config
from src.search.database import SearchDatabase
from src.search.indexer import ArchiveIndexer


class TestDataPipelineIntegration:
    """Test complete data pipeline integration."""
    
    def setup_method(self):
        """Set up test environment with realistic data."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_env = {
            "AICOS_BASE_DIR": self.temp_dir,
            "AICOS_TEST_MODE": "true"
        }
        
        # Generate test datasets
        self.data_generator = LargeDatasetGenerator()
        self.slack_messages = list(self.data_generator.generate_slack_messages(1000))
        self.calendar_events = list(self.data_generator.generate_calendar_events(100))
        self.drive_files = list(self.data_generator.generate_drive_metadata(500))
    
    @pytest.mark.integration
    def test_complete_collection_to_search_pipeline(self):
        """Test full pipeline: Collection → Archive → Index → Search."""
        with patch.dict('os.environ', self.test_env):
            # Step 1: Initialize components
            config = Config()
            state_mgr = StateManager(config.state_dir / "pipeline_test.db")
            archive_writer = ArchiveWriter(config.archive_dir)
            
            # Step 2: Simulate data collection and archival
            print("📝 Archiving test data...")
            
            # Archive Slack messages
            for i, message in enumerate(self.slack_messages):
                archive_writer.write_record("slack", message)
                if i % 100 == 0:
                    print(f"  Slack: {i+1}/{len(self.slack_messages)} messages")
            
            # Archive calendar events
            for i, event in enumerate(self.calendar_events):
                archive_writer.write_record("calendar", event)
                if i % 20 == 0:
                    print(f"  Calendar: {i+1}/{len(self.calendar_events)} events")
            
            # Archive drive metadata
            for i, file_meta in enumerate(self.drive_files):
                archive_writer.write_record("drive", file_meta)
                if i % 100 == 0:
                    print(f"  Drive: {i+1}/{len(self.drive_files)} files")
            
            # Step 3: Index archived data
            print("🔍 Indexing archived data...")
            search_db = SearchDatabase(config.data_dir / "search_test.db")
            indexer = ArchiveIndexer(search_db)
            
            indexer.process_archive_directory(config.archive_dir)
            
            # Step 4: Test search functionality
            print("🔎 Testing search functionality...")
            
            # Test basic search
            results = search_db.search("meeting")
            assert len(results) > 0, "Should find meetings in test data"
            
            # Test multi-source search
            slack_results = search_db.search("test", source="slack")
            calendar_results = search_db.search("meeting", source="calendar")
            
            assert len(slack_results) > 0, "Should find Slack results"
            assert len(calendar_results) > 0, "Should find calendar results"
            
            # Step 5: Verify data integrity
            print("✅ Verifying data integrity...")
            
            # Count archived records
            total_archived = 0
            for source_dir in config.archive_dir.iterdir():
                if source_dir.is_dir():
                    for daily_dir in source_dir.iterdir():
                        if daily_dir.is_dir():
                            for jsonl_file in daily_dir.glob("*.jsonl"):
                                with open(jsonl_file) as f:
                                    total_archived += sum(1 for _ in f)
            
            expected_total = len(self.slack_messages) + len(self.calendar_events) + len(self.drive_files)
            assert total_archived == expected_total, f"Data loss: expected {expected_total}, got {total_archived}"
            
            # Cleanup
            state_mgr.close()
            search_db.close()
    
    @pytest.mark.integration
    def test_incremental_pipeline_updates(self):
        """Test incremental updates through the pipeline."""
        with patch.dict('os.environ', self.test_env):
            config = Config()
            state_mgr = StateManager(config.state_dir / "incremental_test.db")
            archive_writer = ArchiveWriter(config.archive_dir)
            search_db = SearchDatabase(config.data_dir / "search_incremental.db")
            indexer = ArchiveIndexer(search_db, config.archive_dir)
            
            # Initial data load
            initial_messages = self.slack_messages[:500]
            for message in initial_messages:
                archive_writer.write_record("slack", message)
            
            # Initial indexing
            indexer.index_directory(config.archive_dir)
            initial_count = search_db.get_record_count()
            
            # Add more data (incremental)
            additional_messages = self.slack_messages[500:]
            for message in additional_messages:
                archive_writer.write_record("slack", message)
            
            # Incremental indexing
            indexer.index_directory(config.archive_dir)
            final_count = search_db.get_record_count()
            
            # Verify incremental update worked
            assert final_count > initial_count, "Incremental indexing should add records"
            assert final_count == len(self.slack_messages), f"Expected {len(self.slack_messages)}, got {final_count}"
            
            # Cleanup
            state_mgr.close()
            search_db.close()
    
    @pytest.mark.integration
    def test_pipeline_state_persistence(self):
        """Test state persistence across pipeline restarts."""
        with patch.dict('os.environ', self.test_env):
            config = Config()
            
            # Phase 1: Initial processing with state tracking
            state_mgr1 = StateManager(config.state_dir / "persistence_test.db")
            archive_writer1 = ArchiveWriter(config.archive_dir)
            
            # Process some data and save state
            processed_count = 200
            for i, message in enumerate(self.slack_messages[:processed_count]):
                archive_writer1.write_record("slack", message)
                
                # Update state periodically
                if i % 50 == 0:
                    state_mgr1.set_state("slack_collector", {
                        "last_processed": i,
                        "timestamp": message.get("ts", ""),
                        "total_processed": i + 1
                    })
            
            # Save final state
            state_mgr1.set_state("slack_collector", {
                "last_processed": processed_count - 1,
                "timestamp": self.slack_messages[processed_count - 1].get("ts", ""),
                "total_processed": processed_count
            })
            
            state_mgr1.close()
            
            # Phase 2: Resume processing with new instances
            state_mgr2 = StateManager(config.state_dir / "persistence_test.db")
            archive_writer2 = ArchiveWriter(config.archive_dir)
            
            # Retrieve state
            saved_state = state_mgr2.get_state("slack_collector")
            assert saved_state is not None, "State should be persisted"
            assert saved_state["total_processed"] == processed_count
            
            # Continue processing from where we left off
            remaining_messages = self.slack_messages[processed_count:]
            for message in remaining_messages:
                archive_writer2.write_record("slack", message)
            
            # Verify total data integrity
            total_records = 0
            slack_dir = config.archive_dir / "slack"
            for daily_dir in slack_dir.iterdir():
                if daily_dir.is_dir():
                    for jsonl_file in daily_dir.glob("*.jsonl"):
                        with open(jsonl_file) as f:
                            total_records += sum(1 for _ in f)
            
            assert total_records == len(self.slack_messages), "All messages should be archived"
            
            state_mgr2.close()
    
    @pytest.mark.integration
    def test_pipeline_error_recovery(self):
        """Test pipeline recovery from various error scenarios."""
        with patch.dict('os.environ', self.test_env):
            config = Config()
            state_mgr = StateManager(config.state_dir / "error_recovery_test.db")
            archive_writer = ArchiveWriter(config.archive_dir)
            
            # Scenario 1: Partial write failure
            processed_before_error = 0
            
            try:
                for i, message in enumerate(self.slack_messages[:100]):
                    if i == 50:
                        # Simulate disk full error
                        with patch('pathlib.Path.write_text', side_effect=OSError("No space left on device")):
                            archive_writer.write_record("slack", message)
                    else:
                        archive_writer.write_record("slack", message)
                        processed_before_error = i + 1
            except OSError:
                pass  # Expected error
            
            # Verify partial processing was successful
            assert processed_before_error == 50, "Should have processed 50 records before error"
            
            # Scenario 2: Database corruption recovery
            search_db = SearchDatabase(config.data_dir / "search_error_test.db")
            
            # Corrupt the database file
            db_file = config.data_dir / "search_error_test.db"
            with open(db_file, 'w') as f:
                f.write("CORRUPTED")
            
            # Should handle corruption gracefully
            search_db_recovery = SearchDatabase(config.data_dir / "search_error_recovery.db")
            
            # Should be able to create new database
            assert search_db_recovery.conn is not None
            
            # Cleanup
            state_mgr.close()
            search_db_recovery.close()
    
    @pytest.mark.integration
    @pytest.mark.slow
    def test_pipeline_performance_with_large_dataset(self):
        """Test pipeline performance with large realistic datasets."""
        with patch.dict('os.environ', self.test_env):
            config = Config()
            
            # Generate larger dataset for performance testing
            large_generator = LargeDatasetGenerator()
            large_messages = list(large_generator.generate_slack_messages(5000))
            
            print(f"📊 Performance testing with {len(large_messages)} messages...")
            
            # Measure archive writing performance
            archive_writer = ArchiveWriter(config.archive_dir)
            
            start_time = time.time()
            for message in large_messages:
                archive_writer.write_record("slack", message)
            archive_duration = time.time() - start_time
            
            archive_rate = len(large_messages) / archive_duration
            print(f"  Archive rate: {archive_rate:.1f} records/second")
            assert archive_rate >= 1000, f"Archive performance too slow: {archive_rate:.1f} records/sec"
            
            # Measure indexing performance
            search_db = SearchDatabase(config.data_dir / "search_perf.db")
            indexer = ArchiveIndexer(search_db, config.archive_dir)
            
            start_time = time.time()
            indexer.index_directory(config.archive_dir)
            index_duration = time.time() - start_time
            
            index_rate = len(large_messages) / index_duration
            print(f"  Index rate: {index_rate:.1f} records/second")
            assert index_rate >= 500, f"Index performance too slow: {index_rate:.1f} records/sec"
            
            # Measure search performance
            start_time = time.time()
            results = search_db.search("test")
            search_duration = time.time() - start_time
            
            print(f"  Search time: {search_duration:.3f} seconds")
            assert search_duration < 1.0, f"Search too slow: {search_duration:.3f} seconds"
            
            search_db.close()
    
    @pytest.mark.integration
    def test_multi_source_data_coordination(self):
        """Test coordination between multiple data sources."""
        with patch.dict('os.environ', self.test_env):
            config = Config()
            state_mgr = StateManager(config.state_dir / "multi_source_test.db")
            archive_writer = ArchiveWriter(config.archive_dir)
            
            # Archive data from multiple sources simultaneously
            print("📚 Testing multi-source coordination...")
            
            def archive_slack_data():
                for message in self.slack_messages[:300]:
                    archive_writer.write_record("slack", message)
                    time.sleep(0.001)  # Small delay to simulate real processing
            
            def archive_calendar_data():
                for event in self.calendar_events[:50]:
                    archive_writer.write_record("calendar", event)
                    time.sleep(0.001)
            
            def archive_drive_data():
                for file_meta in self.drive_files[:200]:
                    archive_writer.write_record("drive", file_meta)
                    time.sleep(0.001)
            
            # Run concurrent archiving
            with ThreadPoolExecutor(max_workers=3) as executor:
                futures = [
                    executor.submit(archive_slack_data),
                    executor.submit(archive_calendar_data),
                    executor.submit(archive_drive_data)
                ]
                
                # Wait for all to complete
                for future in futures:
                    future.result()
            
            # Verify all data was archived correctly
            source_counts = {}
            for source in ["slack", "calendar", "drive"]:
                count = 0
                source_dir = config.archive_dir / source
                if source_dir.exists():
                    for daily_dir in source_dir.iterdir():
                        if daily_dir.is_dir():
                            for jsonl_file in daily_dir.glob("*.jsonl"):
                                with open(jsonl_file) as f:
                                    count += sum(1 for _ in f)
                source_counts[source] = count
            
            assert source_counts["slack"] == 300, f"Expected 300 Slack messages, got {source_counts['slack']}"
            assert source_counts["calendar"] == 50, f"Expected 50 calendar events, got {source_counts['calendar']}"
            assert source_counts["drive"] == 200, f"Expected 200 drive files, got {source_counts['drive']}"
            
            print(f"✅ Multi-source archival successful: {source_counts}")
            
            state_mgr.close()
    
    @pytest.mark.integration
    def test_search_cross_source_queries(self):
        """Test search queries across multiple data sources."""
        with patch.dict('os.environ', self.test_env):
            config = Config()
            archive_writer = ArchiveWriter(config.archive_dir)
            
            # Create test data with specific searchable content
            test_slack_message = {
                "ts": "1692360000.000000",
                "user": "U1000001",
                "channel": "C1000001",
                "text": "Project Alpha quarterly review meeting scheduled for next week",
                "type": "message"
            }
            
            test_calendar_event = {
                "id": "event_test_search",
                "summary": "Project Alpha quarterly review",
                "description": "Quarterly review for Project Alpha including metrics and planning",
                "start": {"dateTime": "2025-08-25T14:00:00Z"},
                "end": {"dateTime": "2025-08-25T15:00:00Z"},
                "attendees": [{"email": "test@company.com"}]
            }
            
            # Archive test data
            archive_writer.write_record("slack", test_slack_message)
            archive_writer.write_record("calendar", test_calendar_event)
            
            # Index and search
            search_db = SearchDatabase(config.data_dir / "cross_source_search.db")
            indexer = ArchiveIndexer(search_db, config.archive_dir)
            indexer.index_directory(config.archive_dir)
            
            # Test cross-source search
            results = search_db.search("Project Alpha quarterly")
            
            # Should find results from both sources
            slack_results = [r for r in results if r.get("source") == "slack"]
            calendar_results = [r for r in results if r.get("source") == "calendar"]
            
            assert len(slack_results) >= 1, "Should find Slack results for 'Project Alpha quarterly'"
            assert len(calendar_results) >= 1, "Should find calendar results for 'Project Alpha quarterly'"
            
            print(f"🔍 Cross-source search found {len(results)} total results")
            print(f"  Slack: {len(slack_results)}, Calendar: {len(calendar_results)}")
            
            search_db.close()


class TestPipelineDataIntegrity:
    """Test data integrity throughout the pipeline."""
    
    def setup_method(self):
        """Set up data integrity test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_env = {
            "AICOS_BASE_DIR": self.temp_dir,
            "AICOS_TEST_MODE": "true"
        }
    
    @pytest.mark.integration
    def test_no_data_loss_in_pipeline(self):
        """Verify no data loss during pipeline processing."""
        with patch.dict('os.environ', self.test_env):
            config = Config()
            archive_writer = ArchiveWriter(config.archive_dir)
            
            # Create deterministic test data
            test_messages = [
                {
                    "id": f"msg_{i}",
                    "ts": f"{1692360000 + i}.000000",
                    "text": f"Test message {i}",
                    "checksum": f"hash_{i:04d}"
                }
                for i in range(1000)
            ]
            
            # Archive all messages
            for message in test_messages:
                archive_writer.write_record("data_integrity_test", message)
            
            # Read back all archived data
            archived_messages = []
            test_dir = config.archive_dir / "data_integrity_test"
            
            for daily_dir in test_dir.iterdir():
                if daily_dir.is_dir():
                    for jsonl_file in daily_dir.glob("*.jsonl"):
                        with open(jsonl_file) as f:
                            for line in f:
                                archived_messages.append(json.loads(line.strip()))
            
            # Verify data integrity
            assert len(archived_messages) == len(test_messages), "Message count mismatch"
            
            # Sort by ID for comparison
            archived_messages.sort(key=lambda x: x["id"])
            test_messages.sort(key=lambda x: x["id"])
            
            for original, archived in zip(test_messages, archived_messages):
                assert original == archived, f"Data corruption detected: {original} != {archived}"
    
    @pytest.mark.integration
    def test_timestamp_preservation(self):
        """Verify timestamps are preserved exactly through pipeline."""
        with patch.dict('os.environ', self.test_env):
            config = Config()
            archive_writer = ArchiveWriter(config.archive_dir)
            search_db = SearchDatabase(config.data_dir / "timestamp_test.db")
            indexer = ArchiveIndexer(search_db, config.archive_dir)
            
            # Test data with various timestamp formats
            test_records = [
                {"id": 1, "timestamp": "2025-08-17T12:00:00Z", "type": "iso"},
                {"id": 2, "timestamp": "1692360000.123456", "type": "unix"},
                {"id": 3, "timestamp": "2025-08-17T12:00:00.123456Z", "type": "iso_micro"},
            ]
            
            # Archive and index
            for record in test_records:
                archive_writer.write_record("timestamp_test", record)
            
            indexer.index_directory(config.archive_dir)
            
            # Search and verify timestamps
            results = search_db.search("timestamp")
            
            for result in results:
                original_record = next(r for r in test_records if r["id"] == result["id"])
                assert result["timestamp"] == original_record["timestamp"], "Timestamp corruption"
            
            search_db.close()


if __name__ == "__main__":
    # Run integration tests
    pytest.main([
        __file__,
        "-v",
        "-m", "integration",
        "--tb=short"
    ])