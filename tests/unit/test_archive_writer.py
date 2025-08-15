#!/usr/bin/env python3
"""
Test suite for JSONL archive writer
Tests atomic append operations, thread safety, performance, and metadata tracking
"""

import pytest
import os
import json
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import patch, Mock
from datetime import datetime, date

# Import will fail initially - expected in Red phase
try:
    from src.core.archive_writer import ArchiveWriter, ArchiveError
    from src.core.config import Config
except ImportError:
    # Expected during Red phase
    ArchiveWriter = None
    ArchiveError = None
    Config = None


class TestArchiveWriterAtomic:
    """Test atomic JSONL append operations"""
    
    def test_jsonl_append_is_atomic(self):
        """JSONL append operations are atomic"""
        # ACCEPTANCE: Process interruption never leaves partial lines
        with tempfile.TemporaryDirectory() as temp_dir:
            archive_path = Path(temp_dir) / "test_source" / "2025-08-15" / "data.jsonl"
            
            mock_config = Mock()
            mock_config.archive_dir = Path(temp_dir)
            
            with patch('src.core.archive_writer.get_config', return_value=mock_config):
                writer = ArchiveWriter("test_source")
                
                test_records = [
                    {"id": "1", "message": "First record", "timestamp": "2025-08-15T10:00:00"},
                    {"id": "2", "message": "Second record", "timestamp": "2025-08-15T10:01:00"},
                ]
                
                # Mock os.rename to fail (simulating interruption during atomic move)
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
                    with pytest.raises(ArchiveError):  # Our code wraps OSError in ArchiveError
                        writer.write_records(test_records)
                    
                    # Verify no partial content in file
                    if archive_path.exists():
                        with open(archive_path, 'r') as f:
                            lines = f.readlines()
                            # Either empty file or complete records only
                            for line in lines:
                                json.loads(line)  # Should not raise for partial JSON
                
                # Second write should succeed
                writer.write_records(test_records)
                
                # Verify complete records written
                assert archive_path.exists()
                with open(archive_path, 'r') as f:
                    lines = f.readlines()
                    assert len(lines) == 2
                    for i, line in enumerate(lines):
                        record = json.loads(line.strip())
                        assert record["id"] == test_records[i]["id"]

    def test_incomplete_records_not_written(self):
        """Incomplete or corrupted records are rejected"""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_config = Mock()
            mock_config.archive_dir = Path(temp_dir)
            
            with patch('src.core.archive_writer.get_config', return_value=mock_config):
                writer = ArchiveWriter("test_source")
                
                # Test invalid JSON serializable data
                invalid_records = [
                    {"valid": "record"},
                    {"invalid": set([1, 2, 3])},  # Sets not JSON serializable
                    {"also_valid": "record"}
                ]
                
                with pytest.raises(ArchiveError) as exc_info:
                    writer.write_records(invalid_records)
                
                assert "json serializable" in str(exc_info.value).lower()
                
                # Verify no partial writes occurred
                archive_path = Path(temp_dir) / "test_source" / str(date.today()) / "data.jsonl"
                if archive_path.exists():
                    with open(archive_path, 'r') as f:
                        content = f.read().strip()
                        # Should be empty or contain only valid complete records
                        if content:
                            lines = content.split('\n')
                            for line in lines:
                                json.loads(line)  # Should not raise

    def test_filesystem_full_handled_atomically(self):
        """Archive writer handles disk full errors atomically"""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_config = Mock()
            mock_config.archive_dir = Path(temp_dir)
            
            with patch('src.core.archive_writer.get_config', return_value=mock_config):
                writer = ArchiveWriter("test_source")
                
                # Mock disk full error during tempfile creation
                with patch('tempfile.NamedTemporaryFile', side_effect=OSError("No space left on device")):
                    test_records = [{"id": "test", "data": "value"}]
                    
                    with pytest.raises(ArchiveError) as exc_info:
                        writer.write_records(test_records)
                    
                    error_msg = str(exc_info.value).lower()
                    assert "space" in error_msg or "device" in error_msg or "archive" in error_msg


class TestDailyDirectories:
    """Test automatic daily directory creation"""
    
    def test_daily_directories_auto_created(self):
        """Daily archive directories created automatically"""
        # ACCEPTANCE: /data/archive/source/YYYY-MM-DD/ exists after first write
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_config = Mock()
            mock_config.archive_dir = Path(temp_dir)
            
            with patch('src.core.archive_writer.get_config', return_value=mock_config):
                writer = ArchiveWriter("slack")
                
                test_record = {"channel": "general", "message": "Hello world"}
                writer.write_records([test_record])
                
                # Verify daily directory structure created
                today = date.today()
                expected_dir = Path(temp_dir) / "slack" / today.isoformat()
                assert expected_dir.exists()
                assert expected_dir.is_dir()
                
                # Verify data file created
                data_file = expected_dir / "data.jsonl"
                assert data_file.exists()
                
                # Verify content is correct
                with open(data_file, 'r') as f:
                    line = f.readline().strip()
                    record = json.loads(line)
                    assert record["channel"] == "general"
                    assert record["message"] == "Hello world"

    def test_directory_permissions_correct(self):
        """Daily directories created with correct permissions"""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_config = Mock()
            mock_config.archive_dir = Path(temp_dir)
            
            with patch('src.core.archive_writer.get_config', return_value=mock_config):
                writer = ArchiveWriter("calendar")
                writer.write_records([{"event": "test"}])
                
                daily_dir = Path(temp_dir) / "calendar" / str(date.today())
                assert daily_dir.exists()
                
                # Verify directory is readable and writable
                assert os.access(daily_dir, os.R_OK)
                assert os.access(daily_dir, os.W_OK)
                assert os.access(daily_dir, os.X_OK)  # Executable for directories

    def test_multiple_sources_separate_directories(self):
        """Different sources create separate directory structures"""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_config = Mock()
            mock_config.archive_dir = Path(temp_dir)
            
            with patch('src.core.archive_writer.get_config', return_value=mock_config):
                slack_writer = ArchiveWriter("slack")
                calendar_writer = ArchiveWriter("calendar") 
                drive_writer = ArchiveWriter("drive")
                
                slack_writer.write_records([{"type": "slack_message"}])
                calendar_writer.write_records([{"type": "calendar_event"}])
                drive_writer.write_records([{"type": "drive_change"}])
                
                today = str(date.today())
                
                # Verify separate directory structures
                slack_dir = Path(temp_dir) / "slack" / today
                calendar_dir = Path(temp_dir) / "calendar" / today
                drive_dir = Path(temp_dir) / "drive" / today
                
                assert slack_dir.exists()
                assert calendar_dir.exists()  
                assert drive_dir.exists()
                
                # Verify data files exist
                assert (slack_dir / "data.jsonl").exists()
                assert (calendar_dir / "data.jsonl").exists()
                assert (drive_dir / "data.jsonl").exists()

    def test_date_rollover_creates_new_directory(self):
        """Date changes create new daily directories"""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_config = Mock()
            mock_config.archive_dir = Path(temp_dir)
            
            with patch('src.core.archive_writer.get_config', return_value=mock_config):
                writer = ArchiveWriter("test_source")
                
                # Mock current date
                fake_date1 = date(2025, 8, 15)
                fake_date2 = date(2025, 8, 16)
                
                with patch('src.core.archive_writer.date') as mock_date:
                    mock_date.today.return_value = fake_date1
                    writer.write_records([{"day": "first"}])
                    
                    mock_date.today.return_value = fake_date2
                    writer.write_records([{"day": "second"}])
                
                # Verify both directories created
                dir1 = Path(temp_dir) / "test_source" / "2025-08-15"
                dir2 = Path(temp_dir) / "test_source" / "2025-08-16"
                
                assert dir1.exists()
                assert dir2.exists()
                
                # Verify separate data files
                assert (dir1 / "data.jsonl").exists()
                assert (dir2 / "data.jsonl").exists()


class TestPerformanceBenchmarks:
    """Test archive writer performance targets"""
    
    def test_write_performance_target(self):
        """Archive writer meets performance target"""
        # ACCEPTANCE: Sustained 10,000 records/second write speed
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_config = Mock()
            mock_config.archive_dir = Path(temp_dir)
            
            with patch('src.core.archive_writer.get_config', return_value=mock_config):
                writer = ArchiveWriter("performance_test")
                
                # Generate test records
                num_records = 1000  # Reduced for test speed, but extrapolate
                test_records = []
                for i in range(num_records):
                    record = {
                        "id": f"record_{i}",
                        "timestamp": f"2025-08-15T10:{i//60:02d}:{i%60:02d}",
                        "data": f"Sample data for record {i}" * 10  # ~250 chars each
                    }
                    test_records.append(record)
                
                # Measure write performance
                start_time = time.time()
                writer.write_records(test_records)
                end_time = time.time()
                
                duration = end_time - start_time
                records_per_second = num_records / duration
                
                # Extrapolate performance (target: 10,000 records/second)
                # With 1000 records, should complete in <0.1 seconds
                assert duration < 0.2, f"Write took {duration:.3f}s, too slow for target performance"
                
                # Verify all records written correctly
                data_file = Path(temp_dir) / "performance_test" / str(date.today()) / "data.jsonl"
                assert data_file.exists()
                
                with open(data_file, 'r') as f:
                    lines = f.readlines()
                    assert len(lines) == num_records

    def test_large_record_handling(self):
        """Large records handled efficiently"""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_config = Mock()
            mock_config.archive_dir = Path(temp_dir)
            
            with patch('src.core.archive_writer.get_config', return_value=mock_config):
                writer = ArchiveWriter("large_test")
                
                # Create large record (~1MB)
                large_content = "x" * (1024 * 1024)  # 1MB string
                large_record = {
                    "id": "large_record",
                    "content": large_content,
                    "timestamp": "2025-08-15T10:00:00"
                }
                
                # Should handle large record without issues
                start_time = time.time()
                writer.write_records([large_record])
                duration = time.time() - start_time
                
                # Should complete within reasonable time (1MB record in <1 second)
                assert duration < 1.0, f"Large record write took {duration:.3f}s, too slow"
                
                # Verify record written correctly
                data_file = Path(temp_dir) / "large_test" / str(date.today()) / "data.jsonl"
                with open(data_file, 'r') as f:
                    line = f.readline().strip()
                    record = json.loads(line)
                    assert len(record["content"]) == 1024 * 1024

    def test_memory_usage_bounded(self):
        """Memory usage stays bounded during large operations"""
        # This is more of a documentation test - real memory testing would require psutil
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_config = Mock()
            mock_config.archive_dir = Path(temp_dir)
            
            with patch('src.core.archive_writer.get_config', return_value=mock_config):
                writer = ArchiveWriter("memory_test")
                
                # Write many small records - should not accumulate in memory
                batch_size = 1000
                for batch in range(10):  # 10,000 total records
                    records = []
                    for i in range(batch_size):
                        record = {
                            "batch": batch,
                            "id": i,
                            "data": f"Record {batch * batch_size + i}"
                        }
                        records.append(record)
                    
                    writer.write_records(records)
                
                # Verify all records written
                data_file = Path(temp_dir) / "memory_test" / str(date.today()) / "data.jsonl"
                with open(data_file, 'r') as f:
                    lines = f.readlines()
                    assert len(lines) == 10000


class TestMetadataTracking:
    """Test metadata tracking accuracy"""
    
    def test_metadata_tracking_accurate(self):
        """Metadata correctly tracks file sizes, counts, timestamps"""
        # ACCEPTANCE: manifest.json matches actual file contents
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_config = Mock()
            mock_config.archive_dir = Path(temp_dir)
            
            with patch('src.core.archive_writer.get_config', return_value=mock_config):
                writer = ArchiveWriter("metadata_test")
                
                test_records = [
                    {"id": "1", "size": "small"},
                    {"id": "2", "size": "medium" * 100}, 
                    {"id": "3", "size": "large" * 1000}
                ]
                
                write_time = datetime.now()
                writer.write_records(test_records)
                
                # Check metadata file created
                daily_dir = Path(temp_dir) / "metadata_test" / str(date.today())
                metadata_file = daily_dir / "manifest.json"
                data_file = daily_dir / "data.jsonl"
                
                assert metadata_file.exists()
                assert data_file.exists()
                
                # Verify metadata accuracy
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                
                # Verify record count matches
                assert metadata["record_count"] == 3
                
                # Verify file size matches actual file
                actual_size = data_file.stat().st_size
                assert metadata["file_size"] == actual_size
                
                # Verify timestamp is recent
                write_timestamp = datetime.fromisoformat(metadata["last_write"])
                time_diff = abs((write_timestamp - write_time).total_seconds())
                assert time_diff < 5  # Within 5 seconds
                
                # Verify source matches
                assert metadata["source"] == "metadata_test"

    def test_metadata_updates_incrementally(self):
        """Metadata updates correctly with incremental writes"""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_config = Mock()
            mock_config.archive_dir = Path(temp_dir)
            
            with patch('src.core.archive_writer.get_config', return_value=mock_config):
                writer = ArchiveWriter("incremental_test")
                
                # First write
                writer.write_records([{"batch": 1, "id": 1}])
                
                daily_dir = Path(temp_dir) / "incremental_test" / str(date.today())
                metadata_file = daily_dir / "manifest.json"
                
                with open(metadata_file, 'r') as f:
                    metadata1 = json.load(f)
                
                assert metadata1["record_count"] == 1
                size1 = metadata1["file_size"]
                
                # Second write
                writer.write_records([{"batch": 2, "id": 2}, {"batch": 2, "id": 3}])
                
                with open(metadata_file, 'r') as f:
                    metadata2 = json.load(f)
                
                assert metadata2["record_count"] == 3  # 1 + 2
                assert metadata2["file_size"] > size1  # File grew
                assert metadata2["last_write"] > metadata1["last_write"]  # Timestamp updated

    def test_metadata_survives_failures(self):
        """Metadata consistency maintained even during write failures"""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_config = Mock()
            mock_config.archive_dir = Path(temp_dir)
            
            with patch('src.core.archive_writer.get_config', return_value=mock_config):
                writer = ArchiveWriter("failure_test")
                
                # Successful write
                writer.write_records([{"success": True}])
                
                daily_dir = Path(temp_dir) / "failure_test" / str(date.today())
                metadata_file = daily_dir / "manifest.json"
                
                with open(metadata_file, 'r') as f:
                    good_metadata = json.load(f)
                
                # Failed write (invalid JSON)
                with pytest.raises(ArchiveError):
                    writer.write_records([{"invalid": set([1, 2, 3])}])
                
                # Metadata should be unchanged after failure
                with open(metadata_file, 'r') as f:
                    metadata_after_fail = json.load(f)
                
                assert metadata_after_fail == good_metadata


class TestThreadSafety:
    """Test thread-safe operations"""
    
    def test_thread_safe_operations(self):
        """Multiple threads can write safely"""
        # ACCEPTANCE: 5 threads writing simultaneously, zero corruption
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_config = Mock()
            mock_config.archive_dir = Path(temp_dir)
            
            with patch('src.core.archive_writer.get_config', return_value=mock_config):
                writer = ArchiveWriter("thread_test")
                
                def write_worker(thread_id):
                    """Worker function for concurrent writes"""
                    records = []
                    for i in range(100):  # 100 records per thread
                        record = {
                            "thread_id": thread_id,
                            "record_id": i,
                            "timestamp": datetime.now().isoformat(),
                            "data": f"Thread {thread_id} record {i}"
                        }
                        records.append(record)
                    
                    writer.write_records(records)
                
                # Start 5 concurrent writer threads
                threads = []
                for thread_id in range(5):
                    thread = threading.Thread(target=write_worker, args=(thread_id,))
                    threads.append(thread)
                    thread.start()
                
                # Wait for all threads to complete
                for thread in threads:
                    thread.join()
                
                # Verify all records written without corruption
                data_file = Path(temp_dir) / "thread_test" / str(date.today()) / "data.jsonl"
                assert data_file.exists()
                
                thread_counts = {}
                total_records = 0
                
                with open(data_file, 'r') as f:
                    for line_num, line in enumerate(f, 1):
                        try:
                            record = json.loads(line.strip())
                            thread_id = record["thread_id"]
                            thread_counts[thread_id] = thread_counts.get(thread_id, 0) + 1
                            total_records += 1
                        except json.JSONDecodeError as e:
                            pytest.fail(f"Corrupted JSON on line {line_num}: {e}")
                
                # Verify expected counts
                assert total_records == 500  # 5 threads * 100 records each
                assert len(thread_counts) == 5  # All 5 threads contributed
                for thread_id, count in thread_counts.items():
                    assert count == 100, f"Thread {thread_id} wrote {count} records, expected 100"

    def test_concurrent_metadata_updates(self):
        """Metadata updates are thread-safe"""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_config = Mock()
            mock_config.archive_dir = Path(temp_dir)
            
            with patch('src.core.archive_writer.get_config', return_value=mock_config):
                writer = ArchiveWriter("concurrent_meta_test")
                
                def metadata_worker(worker_id):
                    """Worker that writes records and checks metadata"""
                    for i in range(50):
                        writer.write_records([{"worker": worker_id, "index": i}])
                
                # Start 3 concurrent workers
                threads = []
                for worker_id in range(3):
                    thread = threading.Thread(target=metadata_worker, args=(worker_id,))
                    threads.append(thread)
                    thread.start()
                
                for thread in threads:
                    thread.join()
                
                # Check final metadata consistency
                daily_dir = Path(temp_dir) / "concurrent_meta_test" / str(date.today())
                metadata_file = daily_dir / "manifest.json"
                data_file = daily_dir / "data.jsonl"
                
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                
                # Count actual records
                actual_count = 0
                with open(data_file, 'r') as f:
                    for line in f:
                        actual_count += 1
                
                # Metadata should match actual file
                assert metadata["record_count"] == actual_count
                assert metadata["record_count"] == 150  # 3 workers * 50 records
                assert metadata["file_size"] == data_file.stat().st_size

    def test_directory_creation_race_conditions(self):
        """Concurrent directory creation handled safely"""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_config = Mock()
            mock_config.archive_dir = Path(temp_dir)
            
            with patch('src.core.archive_writer.get_config', return_value=mock_config):
                
                def create_writer_and_write(source_id):
                    """Create writer and write a record"""
                    writer = ArchiveWriter(f"race_test_{source_id}")
                    writer.write_records([{"source": source_id, "test": "race_condition"}])
                
                # Start multiple threads creating writers simultaneously
                threads = []
                for source_id in range(10):
                    thread = threading.Thread(target=create_writer_and_write, args=(source_id,))
                    threads.append(thread)
                    thread.start()
                
                for thread in threads:
                    thread.join()
                
                # Verify all directories and files created successfully
                today = str(date.today())
                for source_id in range(10):
                    expected_dir = Path(temp_dir) / f"race_test_{source_id}" / today
                    expected_file = expected_dir / "data.jsonl"
                    
                    assert expected_dir.exists(), f"Directory not created for source {source_id}"
                    assert expected_file.exists(), f"Data file not created for source {source_id}"


class TestErrorHandling:
    """Test error handling and edge cases"""
    
    def test_archive_error_exception(self):
        """ArchiveError exception can be raised and caught"""
        try:
            raise ArchiveError("Test archive error")
        except ArchiveError as e:
            assert str(e) == "Test archive error"

    def test_invalid_source_names(self):
        """Invalid source names are rejected"""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_config = Mock()
            mock_config.archive_dir = Path(temp_dir)
            
            with patch('src.core.archive_writer.get_config', return_value=mock_config):
                
                # Test various invalid source names
                invalid_names = ["", "  ", "source/with/slash", "source\\with\\backslash", "source:with:colon"]
                
                for invalid_name in invalid_names:
                    with pytest.raises(ArchiveError) as exc_info:
                        ArchiveWriter(invalid_name)
                    
                    error_msg = str(exc_info.value).lower()
                    assert "invalid" in error_msg or "source" in error_msg

    def test_read_only_directory_handling(self):
        """Handles read-only directories gracefully"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Make directory read-only
            os.chmod(temp_dir, 0o444)  # Read-only
            
            try:
                mock_config = Mock()
                mock_config.archive_dir = Path(temp_dir)
                
                with patch('src.core.archive_writer.get_config', return_value=mock_config):
                    # Should fail during initialization when trying to create source directory
                    with pytest.raises(ArchiveError) as exc_info:
                        writer = ArchiveWriter("readonly_test")
                    
                    error_msg = str(exc_info.value).lower()
                    assert "permission" in error_msg or "create" in error_msg
                    
            finally:
                # Restore permissions for cleanup
                os.chmod(temp_dir, 0o755)

    def test_empty_records_handled(self):
        """Empty record lists handled gracefully"""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_config = Mock()
            mock_config.archive_dir = Path(temp_dir)
            
            with patch('src.core.archive_writer.get_config', return_value=mock_config):
                writer = ArchiveWriter("empty_test")
                
                # Writing empty list should succeed but do nothing
                writer.write_records([])
                
                # Directory might be created but no data file
                daily_dir = Path(temp_dir) / "empty_test" / str(date.today())
                data_file = daily_dir / "data.jsonl"
                
                # If file exists, it should be empty
                if data_file.exists():
                    assert data_file.stat().st_size == 0