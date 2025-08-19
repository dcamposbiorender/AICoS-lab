"""
Test suite for Archive Indexer - Phase 2: Archive Indexing Pipeline

This test file implements comprehensive tests for the ArchiveIndexer class
following Test-Driven Development (TDD) approach.

Tests cover:
- JSONL file processing with batch indexing
- Incremental indexing with cursor tracking  
- Memory-safe streaming for large files
- Error handling for malformed records
- Progress tracking and performance monitoring
- Format detection (slack, calendar, drive, employees)

References: tasks_A.md lines 400-550 for test requirements
"""

import pytest
import json
import tempfile
import time
import sqlite3
import threading
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from src.search.indexer import ArchiveIndexer, IndexingError, IndexingStats
from src.search.database import SearchDatabase, DatabaseError


class TestArchiveIndexer:
    """Test Archive Indexing Pipeline - Sub-Agent A2 Phase 2"""
    
    @pytest.fixture
    def temp_db(self, tmp_path):
        """Create temporary test database"""
        db_path = tmp_path / "test_indexer.db"
        return SearchDatabase(str(db_path))
    
    @pytest.fixture
    def indexer(self, temp_db):
        """Create ArchiveIndexer instance"""
        return ArchiveIndexer(temp_db, batch_size=100)  # Small batch for testing
    
    @pytest.fixture
    def sample_slack_jsonl(self, tmp_path):
        """Create sample Slack JSONL file"""
        file_path = tmp_path / "slack_sample.jsonl"
        
        # Based on actual Slack message structure from system
        records = [
            {
                "user": "U06MUFURG1H",
                "type": "message", 
                "ts": "1755265938.233749",
                "client_msg_id": "ad70a8ff-79e4-419a-89f2-4529d48c8a9c",
                "text": "Hey everyone! Engagement Survey Launch - We've officially launched our survey!",
                "team": "TAGAKP69W",
                "channel_id": "CAH5PR7V3",
                "channel_name": "announcements",
                "collection_timestamp": "2025-08-16T14:35:33.825234",
                "_collection_context": {
                    "channel_id": "CAH5PR7V3",
                    "service": "slack",
                    "collected_at": "2025-08-16T14:35:50.559209"
                },
                "archive_timestamp": "2025-08-16T14:35:50.565506"
            },
            {
                "user": "U088GR4JFQS",
                "type": "message",
                "ts": "1755264080.860289", 
                "text": "Happy Friday! Here's today's round-up with quantum computer news!",
                "channel_id": "CAH5PR7V3",
                "channel_name": "announcements",
                "collection_timestamp": "2025-08-16T14:35:33.825234"
            },
            {
                # Empty text message - should be filtered out
                "user": "U12345678",
                "type": "message",
                "ts": "1755264000.000000",
                "text": "",
                "channel_id": "CAH5PR7V3"
            },
            {
                # Missing text field - should be handled gracefully
                "user": "U87654321", 
                "type": "message",
                "ts": "1755264100.000000",
                "channel_id": "CAH5PR7V3"
            }
        ]
        
        with open(file_path, 'w') as f:
            for record in records:
                f.write(json.dumps(record) + '\n')
        
        return file_path
    
    @pytest.fixture
    def sample_calendar_jsonl(self, tmp_path):
        """Create sample Calendar JSONL file"""
        file_path = tmp_path / "calendar_sample.jsonl"
        
        # Based on actual calendar event structure from system
        records = [
            {
                "kind": "calendar#event",
                "id": "5ijq2jsm9mco9hr9o1ccrc7fje",
                "status": "confirmed", 
                "summary": "David / Anne 1:1 Meeting",
                "creator": {"email": "anne.granger@biorender.com"},
                "organizer": {"email": "anne.granger@biorender.com"},
                "start": {
                    "dateTime": "2025-08-11T08:30:00-07:00",
                    "timeZone": "America/New_York"
                },
                "end": {
                    "dateTime": "2025-08-11T09:30:00-07:00", 
                    "timeZone": "America/New_York"
                },
                "attendees": [
                    {"email": "anne.granger@biorender.com", "organizer": True},
                    {"email": "david.campos@biorender.com", "self": True}
                ],
                "calendar_id": "david.campos@biorender.com",
                "_collection_context": {
                    "service": "calendar",
                    "collected_at": "2025-08-16T16:01:30.684467"
                }
            },
            {
                "kind": "calendar#event", 
                "id": "7jtn3alas6pjlur29dbt8vq9pj",
                "summary": "Exec Onsite - Strategic Planning Session",
                "start": {"dateTime": "2025-08-11T11:30:00-07:00"},
                "end": {"dateTime": "2025-08-11T12:00:00-07:00"},
                "attendees": [
                    {"email": "kiran.rao@biorender.com", "organizer": True},
                    {"email": "david.campos@biorender.com", "self": True}
                ],
                "calendar_id": "david.campos@biorender.com"
            }
        ]
        
        with open(file_path, 'w') as f:
            for record in records:
                f.write(json.dumps(record) + '\n')
                
        return file_path
    
    @pytest.fixture
    def large_jsonl_file(self, tmp_path):
        """Create large JSONL file for memory testing"""
        file_path = tmp_path / "large_test.jsonl"
        
        with open(file_path, 'w') as f:
            for i in range(15000):  # 15k records to test batching
                record = {
                    "id": f"msg_{i:05d}",
                    "text": f"Test message number {i} with some content for indexing",
                    "user": f"user_{i % 100}",
                    "ts": str(1755264000 + i),
                    "channel_id": "C12345678",
                    "type": "message"
                }
                f.write(json.dumps(record) + '\n')
        
        return file_path
    
    @pytest.fixture
    def malformed_jsonl_file(self, tmp_path):
        """Create JSONL file with various malformed records"""
        file_path = tmp_path / "malformed_test.jsonl"
        
        with open(file_path, 'w') as f:
            # Valid record
            f.write(json.dumps({"text": "Valid message", "user": "U123", "ts": "1755264000"}) + '\n')
            
            # Invalid JSON
            f.write('{"invalid": json, missing quote}\n')
            
            # Another valid record
            f.write(json.dumps({"text": "Another valid message", "user": "U456", "ts": "1755264100"}) + '\n')
            
            # Empty line
            f.write('\n')
            
            # Incomplete JSON 
            f.write('{"incomplete":\n')
            
            # Final valid record
            f.write(json.dumps({"text": "Final message", "user": "U789", "ts": "1755264200"}) + '\n')
        
        return file_path

    # Test 1: Basic JSONL Processing with Batch Indexing
    def test_jsonl_processing_with_batching(self, indexer, sample_slack_jsonl):
        """Test basic JSONL file processing with batch indexing"""
        stats = indexer.process_archive(sample_slack_jsonl, source='slack')
        
        # Should process valid records, skip empty/invalid ones
        assert stats.processed > 0
        assert stats.source == 'slack'
        assert stats.file_path == str(sample_slack_jsonl)
        assert stats.duration > 0
        
        # Check records were actually indexed in database
        db_stats = indexer.database.get_stats()
        assert db_stats['total_records'] >= 2  # At least 2 valid messages
        assert 'slack' in db_stats['records_by_source']

    # Test 2: Format Detection and Content Extraction
    def test_format_detection_and_extraction(self, indexer, sample_calendar_jsonl):
        """Test format detection and content extraction for calendar events"""
        stats = indexer.process_archive(sample_calendar_jsonl, source='calendar')
        
        # Should detect calendar format and extract content
        assert stats.processed > 0
        assert stats.source == 'calendar'
        
        # Verify searchable content was extracted properly
        results = indexer.database.search("David Anne meeting")
        assert len(results) > 0
        assert "David / Anne" in results[0]['content']
        
        # Check attendee emails were indexed (avoid special characters in FTS5)
        results = indexer.database.search("anne granger biorender")
        assert len(results) > 0

    # Test 3: Memory-Safe Streaming for Large Files
    def test_memory_safe_large_file_processing(self, indexer, large_jsonl_file):
        """Test memory-safe processing of large files without loading into memory"""
        initial_memory = indexer._get_memory_usage()
        
        # Process large file
        stats = indexer.process_archive(large_jsonl_file, source='test')
        
        # Verify all records processed
        assert stats.processed == 15000
        assert stats.error_count == 0
        
        # Memory usage should not have grown excessively 
        final_memory = indexer._get_memory_usage()
        memory_growth_mb = (final_memory - initial_memory) / 1024 / 1024
        
        # Should not use more than 100MB regardless of file size
        assert memory_growth_mb < 100, f"Memory grew by {memory_growth_mb:.1f}MB - too much for streaming"

    # Test 4: Error Handling for Malformed Records
    def test_malformed_record_handling(self, indexer, malformed_jsonl_file):
        """Test graceful handling of malformed JSON records"""
        stats = indexer.process_archive(malformed_jsonl_file, source='test')
        
        # Should process valid records despite errors
        assert stats.processed == 3  # 3 valid records
        assert stats.error_count > 0  # Some errors occurred
        assert len(stats.errors) > 0  # Error details captured
        
        # Verify error details are informative
        error_found = False
        for error in stats.errors:
            if "Invalid JSON" in error['error']:
                error_found = True
                assert 'line_number' in error
                break
        assert error_found, "Should capture JSON parsing errors with line numbers"

    # Test 5: Progress Tracking and Performance Monitoring
    def test_progress_tracking(self, indexer, large_jsonl_file):
        """Test progress tracking and performance monitoring"""
        progress_updates = []
        
        def progress_callback(processed, total, rate):
            progress_updates.append((processed, total, rate))
        
        # Process with progress tracking
        stats = indexer.process_archive(
            large_jsonl_file, 
            source='test',
            progress_callback=progress_callback
        )
        
        # Should have received progress updates
        assert len(progress_updates) > 0
        
        # Progress should be realistic - callbacks are periodic, not final
        assert all(processed >= 0 for processed, _, _ in progress_updates)
        assert all(rate > 0 for _, _, rate in progress_updates)
        
        # At least one update should show substantial progress
        max_progress = max(processed for processed, _, _ in progress_updates)
        assert max_progress >= 1000  # Should have progressed significantly
        
        # Performance stats should be populated
        assert stats.avg_processing_rate > 0
        assert stats.duration > 0

    # Test 6: Incremental Indexing with Cursor Tracking
    def test_incremental_indexing(self, indexer, sample_slack_jsonl):
        """Test incremental indexing with cursor/state tracking"""
        # First indexing run
        stats1 = indexer.process_archive(sample_slack_jsonl, source='slack')
        
        # Should track file state
        assert indexer.get_file_cursor(sample_slack_jsonl) is not None
        
        # Second run on same file (should skip - no changes)
        stats2 = indexer.process_archive(sample_slack_jsonl, source='slack')
        assert stats2.processed == 0  # No new records processed
        assert stats2.skipped_unchanged == True
        
        # Modify file 
        with open(sample_slack_jsonl, 'a') as f:
            new_record = {
                "user": "U_NEW_USER",
                "text": "New message added after first indexing",
                "ts": "1755300000.000000",
                "channel_id": "CAH5PR7V3",
                "type": "message"
            }
            f.write(json.dumps(new_record) + '\n')
        
        # Third run should detect change and reindex
        stats3 = indexer.process_archive(sample_slack_jsonl, source='slack')
        assert stats3.processed > 0  # New records processed
        assert not stats3.skipped_unchanged

    # Test 7: Concurrent Processing Safety 
    def test_concurrent_processing_safety(self, temp_db, sample_slack_jsonl):
        """Test thread-safe concurrent archive processing"""
        errors = []
        results = []
        
        def process_worker(worker_id):
            try:
                worker_indexer = ArchiveIndexer(temp_db, batch_size=50)
                stats = worker_indexer.process_archive(sample_slack_jsonl, source=f'worker_{worker_id}')
                results.append(stats)
            except Exception as e:
                errors.append(f"Worker {worker_id}: {str(e)}")
        
        # Start multiple worker threads
        threads = []
        for i in range(3):
            thread = threading.Thread(target=process_worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Should not have threading errors
        assert len(errors) == 0, f"Concurrent processing errors: {errors}"
        assert len(results) == 3
        
        # At least one worker should have successfully processed records
        total_processed = sum(r.processed for r in results)
        assert total_processed > 0

    # Test 8: Archive Manifest Integration
    def test_archive_manifest_integration(self, indexer, tmp_path):
        """Test integration with archive manifest files"""
        # Create archive structure with manifest
        archive_dir = tmp_path / "test_archive"
        archive_dir.mkdir()
        
        data_file = archive_dir / "data.jsonl"
        manifest_file = archive_dir / "manifest.json"
        
        # Create data file
        with open(data_file, 'w') as f:
            f.write(json.dumps({"text": "Test message", "user": "U123", "ts": "1755264000"}) + '\n')
        
        # Create manifest
        manifest = {
            "source": "slack",
            "date": "2025-08-16",
            "record_count": 1,
            "checksum": "abc123",
            "files": ["data.jsonl"]
        }
        with open(manifest_file, 'w') as f:
            json.dump(manifest, f)
        
        # Process archive directory
        stats = indexer.process_archive_directory(archive_dir)
        
        # Should use manifest information
        assert stats.source == 'slack'
        assert stats.processed == 1
        assert stats.manifest_validated == True

    # Test 9: Resource Cleanup and Error Recovery
    def test_resource_cleanup_and_recovery(self, indexer, tmp_path):
        """Test proper resource cleanup and error recovery"""
        # Create file with mixed valid and problematic records
        error_file = tmp_path / "error_test.jsonl"
        with open(error_file, 'w') as f:
            f.write('{"text": "valid record 1"}\n')
            # Write invalid JSON that will cause parsing error
            f.write('{"text": "missing closing brace"\n')
            f.write('{"text": "valid record 2"}\n')
        
        # Should handle error gracefully
        stats = indexer.process_archive(error_file, source='test')
        
        # Should process valid records despite errors
        assert stats.processed >= 2  # At least 2 valid records processed
        assert stats.error_count >= 1  # At least 1 JSON parsing error
        
        # Database should still be functional after error
        db_stats = indexer.database.get_stats()
        assert isinstance(db_stats, dict)
        assert db_stats['total_records'] >= 2

    # Test 10: Performance Benchmarking
    def test_performance_benchmarking(self, indexer, large_jsonl_file):
        """Test processing performance meets requirements"""
        start_time = time.time()
        stats = indexer.process_archive(large_jsonl_file, source='test')
        duration = time.time() - start_time
        
        # Should process at least 1000 records per second
        processing_rate = stats.processed / duration
        assert processing_rate >= 1000, f"Processing rate {processing_rate:.1f} records/sec too slow"
        
        # Memory usage should be reasonable
        assert stats.peak_memory_mb < 200, f"Peak memory {stats.peak_memory_mb}MB too high"

    # Test 11: Content Extraction Accuracy
    def test_content_extraction_accuracy(self, indexer, sample_slack_jsonl, sample_calendar_jsonl):
        """Test accuracy of content extraction from different sources"""
        # Process Slack messages
        indexer.process_archive(sample_slack_jsonl, source='slack')
        
        # Process Calendar events  
        indexer.process_archive(sample_calendar_jsonl, source='calendar')
        
        # Test Slack content extraction
        slack_results = indexer.database.search("Engagement Survey", source='slack')
        assert len(slack_results) > 0
        assert "survey" in slack_results[0]['content'].lower()
        
        # Test Calendar content extraction
        cal_results = indexer.database.search("Strategic Planning", source='calendar')
        assert len(cal_results) > 0
        assert "strategic" in cal_results[0]['content'].lower()
        
        # Test attendee extraction from calendar (avoid special chars in FTS5)
        attendee_results = indexer.database.search("david campos biorender")
        assert len(attendee_results) > 0

    # Test 12: Database Integration Validation
    def test_database_integration_validation(self, indexer, sample_slack_jsonl):
        """Test proper integration with SearchDatabase"""
        # Process records
        stats = indexer.process_archive(sample_slack_jsonl, source='slack')
        
        # Verify records are properly indexed in FTS5
        results = indexer.database.search("engagement survey")
        assert len(results) > 0
        
        # Verify metadata is properly stored
        result = results[0]
        assert 'metadata' in result
        assert 'source' in result
        assert result['source'] == 'slack'
        
        # Verify archive tracking
        db_stats = indexer.database.get_stats()
        assert db_stats['archives_tracked'] > 0


class TestIndexingStats:
    """Test IndexingStats data class"""
    
    def test_stats_initialization(self):
        """Test IndexingStats initialization and methods"""
        stats = IndexingStats('test.jsonl', 'slack')
        
        assert stats.file_path == 'test.jsonl'
        assert stats.source == 'slack'
        assert stats.processed == 0
        assert stats.error_count == 0
        assert stats.start_time is not None
        
    def test_stats_completion(self):
        """Test stats completion and rate calculation"""
        stats = IndexingStats('test.jsonl', 'slack')
        
        # Simulate processing
        time.sleep(0.1)
        stats.complete(processed=1000, error_count=5)
        
        assert stats.processed == 1000
        assert stats.error_count == 5
        assert stats.duration > 0
        assert stats.avg_processing_rate > 0


class TestIndexingError:
    """Test IndexingError exception handling"""
    
    def test_indexing_error_creation(self):
        """Test IndexingError exception creation"""
        error = IndexingError("Test error", file_path="test.jsonl", line_number=42)
        
        assert str(error) == "Test error"
        assert error.file_path == "test.jsonl"
        assert error.line_number == 42

    def test_indexing_error_without_context(self):
        """Test IndexingError without file context"""
        error = IndexingError("Simple error")
        
        assert str(error) == "Simple error"
        assert error.file_path is None
        assert error.line_number is None


# Helper Test Utilities
class TestArchiveIndexerHelpers:
    """Test helper methods and utilities"""
    
    def test_checksum_calculation(self, tmp_path):
        """Test file checksum calculation for change detection"""
        test_file = tmp_path / "checksum_test.jsonl"
        
        # Create file
        with open(test_file, 'w') as f:
            f.write('{"test": "content"}\n')
        
        from src.search.indexer import ArchiveIndexer
        
        # Calculate checksum
        checksum1 = ArchiveIndexer._calculate_file_checksum(test_file)
        assert isinstance(checksum1, str)
        assert len(checksum1) > 0
        
        # Same file should have same checksum
        checksum2 = ArchiveIndexer._calculate_file_checksum(test_file)
        assert checksum1 == checksum2
        
        # Modified file should have different checksum
        with open(test_file, 'a') as f:
            f.write('{"more": "content"}\n')
        
        checksum3 = ArchiveIndexer._calculate_file_checksum(test_file)
        assert checksum1 != checksum3

    def test_source_detection(self):
        """Test automatic source type detection from file paths"""
        from src.search.indexer import ArchiveIndexer
        
        assert ArchiveIndexer._detect_source_from_path("/archive/slack/2025-08-16/data.jsonl") == "slack"
        assert ArchiveIndexer._detect_source_from_path("/archive/calendar/2025-08-16/data.jsonl") == "calendar"
        assert ArchiveIndexer._detect_source_from_path("/archive/drive/2025-08-16/data.jsonl") == "drive"
        assert ArchiveIndexer._detect_source_from_path("/archive/employees/roster.jsonl") == "employees"
        assert ArchiveIndexer._detect_source_from_path("/unknown/path/data.jsonl") == "unknown"