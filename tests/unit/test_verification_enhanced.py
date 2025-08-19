#!/usr/bin/env python3
"""
Comprehensive tests for enhanced archive verification system
Tests the ArchiveVerifier class with all advanced features including
schema validation, compression support, and resume capability.

Based on tasks_B.md requirements and user feedback fixes.
"""

import gzip
import hashlib
import json
import tempfile
import pytest
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import Dict
from unittest.mock import MagicMock, patch, mock_open

from src.core.verification import (
    ArchiveVerifier, 
    VerificationError, 
    VerificationResult,
    RecordVerificationResult
)


class TestArchiveVerifierCore:
    """Test core ArchiveVerifier functionality"""
    
    @pytest.fixture
    def verifier(self):
        """Create fresh verifier instance"""
        return ArchiveVerifier()
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    def test_verifier_initialization(self, verifier):
        """Test verifier initializes with correct defaults"""
        assert verifier.checksum_algorithm == 'sha256'
        assert verifier.checkpoint_interval == 1000
        assert 'files_checked' in verifier.stats
        assert 'records_verified' in verifier.stats
        assert 'errors' in verifier.stats
        assert 'warnings' in verifier.stats
    
    def test_required_fields_schema(self, verifier):
        """Test schema definitions for different source types"""
        assert 'timestamp' in verifier.REQUIRED_FIELDS['slack']
        assert 'user' in verifier.REQUIRED_FIELDS['slack']
        assert 'text' in verifier.REQUIRED_FIELDS['slack']
        assert 'channel' in verifier.REQUIRED_FIELDS['slack']
        
        assert 'timestamp' in verifier.REQUIRED_FIELDS['calendar']
        assert 'summary' in verifier.REQUIRED_FIELDS['calendar']
        assert 'start' in verifier.REQUIRED_FIELDS['calendar']
        assert 'end' in verifier.REQUIRED_FIELDS['calendar']
        
        assert 'timestamp' in verifier.REQUIRED_FIELDS['drive']
        assert 'name' in verifier.REQUIRED_FIELDS['drive']
        assert 'id' in verifier.REQUIRED_FIELDS['drive']
        assert 'mimeType' in verifier.REQUIRED_FIELDS['drive']


class TestRecordVerification:
    """Test individual record verification with schema validation"""
    
    @pytest.fixture
    def verifier(self):
        return ArchiveVerifier()
    
    def test_valid_slack_record(self, verifier):
        """Test valid Slack record passes validation"""
        record = {
            "timestamp": "2025-08-17T10:00:00Z",
            "user": "U123USER",
            "text": "Hello world!",
            "channel": "C123GENERAL",
            "thread_ts": "1692259200.123456"
        }
        
        result = verifier.verify_record(record, 'slack')
        assert result.is_valid
        assert len(result.errors) == 0
        assert len(result.missing_fields) == 0
    
    def test_invalid_slack_record_missing_fields(self, verifier):
        """Test Slack record missing required fields"""
        record = {
            "timestamp": "2025-08-17T10:00:00Z",
            "user": "U123USER"
            # Missing 'text' and 'channel'
        }
        
        result = verifier.verify_record(record, 'slack')
        assert not result.is_valid
        assert 'text' in result.missing_fields
        assert 'channel' in result.missing_fields
        assert len(result.errors) > 0
    
    def test_invalid_slack_record_empty_user(self, verifier):
        """Test Slack record with empty user field"""
        record = {
            "timestamp": "2025-08-17T10:00:00Z",
            "user": "",  # Empty user
            "text": "Hello",
            "channel": "general"
        }
        
        result = verifier.verify_record(record, 'slack')
        assert not result.is_valid
        assert any("User field must be non-empty" in error for error in result.errors)
    
    def test_valid_calendar_record(self, verifier):
        """Test valid Calendar record passes validation"""
        record = {
            "timestamp": "2025-08-17T10:00:00Z",
            "summary": "Team Meeting",
            "start": "2025-08-17T14:00:00Z",
            "end": "2025-08-17T15:00:00Z",
            "attendees": ["alice@example.com", "bob@example.com"]
        }
        
        result = verifier.verify_record(record, 'calendar')
        assert result.is_valid
        assert len(result.errors) == 0
    
    def test_invalid_calendar_record_empty_summary(self, verifier):
        """Test Calendar record with empty summary"""
        record = {
            "timestamp": "2025-08-17T10:00:00Z",
            "summary": "",  # Empty summary
            "start": "2025-08-17T14:00:00Z",
            "end": "2025-08-17T15:00:00Z"
        }
        
        result = verifier.verify_record(record, 'calendar')
        assert not result.is_valid
        assert any("Summary field must be non-empty" in error for error in result.errors)
    
    def test_valid_drive_record(self, verifier):
        """Test valid Drive record passes validation"""
        record = {
            "timestamp": "2025-08-17T10:00:00Z",
            "name": "document.pdf",
            "id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
            "mimeType": "application/pdf",
            "size": 1024
        }
        
        result = verifier.verify_record(record, 'drive')
        assert result.is_valid
        assert len(result.errors) == 0
    
    def test_invalid_drive_record_missing_mime_type(self, verifier):
        """Test Drive record missing MIME type"""
        record = {
            "timestamp": "2025-08-17T10:00:00Z",
            "name": "document.pdf",
            "id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"
            # Missing 'mimeType'
        }
        
        result = verifier.verify_record(record, 'drive')
        assert not result.is_valid
        assert 'mimeType' in result.missing_fields
    
    def test_invalid_timestamp_format(self, verifier):
        """Test record with invalid timestamp format"""
        record = {
            "timestamp": "invalid-timestamp",
            "user": "U123USER",
            "text": "Hello",
            "channel": "general"
        }
        
        result = verifier.verify_record(record, 'slack')
        assert not result.is_valid
        assert any("Invalid timestamp format" in error for error in result.errors)
    
    def test_valid_timestamp_formats(self, verifier):
        """Test various valid timestamp formats"""
        valid_timestamps = [
            "2025-08-17T10:00:00Z",
            "2025-08-17T10:00:00+00:00",
            "2025-08-17T10:00:00.123456Z",
            "2025-08-17T10:00:00"
        ]
        
        for ts in valid_timestamps:
            record = {
                "timestamp": ts,
                "user": "U123USER", 
                "text": "Hello",
                "channel": "general"
            }
            result = verifier.verify_record(record, 'slack')
            assert result.is_valid, f"Timestamp {ts} should be valid"


class TestChecksumCalculation:
    """Test SHA-256 checksum calculation for different file types"""
    
    @pytest.fixture
    def verifier(self):
        return ArchiveVerifier()
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    def test_checksum_uncompressed_file(self, verifier, temp_dir):
        """Test checksum calculation for uncompressed JSONL file"""
        test_data = b'{"test": "data"}\n{"more": "data"}\n'
        test_file = temp_dir / "test.jsonl"
        test_file.write_bytes(test_data)
        
        # Calculate expected checksum
        expected = hashlib.sha256(test_data).hexdigest()
        
        # Test our calculation
        actual = verifier._calculate_checksum(test_file)
        assert actual == expected
    
    def test_checksum_compressed_file(self, verifier, temp_dir):
        """Test checksum calculation for gzipped file"""
        test_data = b'{"test": "data"}\n{"more": "data"}\n'
        
        # Create compressed file
        compressed_file = temp_dir / "test.jsonl.gz"
        with gzip.open(compressed_file, 'wb') as f:
            f.write(test_data)
        
        # Expected checksum of uncompressed content
        expected = hashlib.sha256(test_data).hexdigest()
        
        # Test our calculation (should decompress transparently)
        actual = verifier._calculate_checksum(compressed_file)
        assert actual == expected
    
    def test_checksum_empty_file(self, verifier, temp_dir):
        """Test checksum of empty file"""
        empty_file = temp_dir / "empty.jsonl"
        empty_file.write_bytes(b'')
        
        expected = hashlib.sha256(b'').hexdigest()
        actual = verifier._calculate_checksum(empty_file)
        assert actual == expected
    
    def test_checksum_nonexistent_file(self, verifier, temp_dir):
        """Test checksum calculation fails for nonexistent file"""
        nonexistent = temp_dir / "does_not_exist.jsonl"
        
        with pytest.raises(VerificationError):
            verifier._calculate_checksum(nonexistent)


class TestJSONLValidation:
    """Test JSONL format validation with line-by-line error reporting"""
    
    @pytest.fixture
    def verifier(self):
        return ArchiveVerifier()
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    def test_valid_jsonl_file(self, verifier, temp_dir):
        """Test validation of perfectly valid JSONL file"""
        records = [
            {"id": 1, "timestamp": "2025-08-17T10:00:00Z", "user": "alice", "text": "Hello", "channel": "general"},
            {"id": 2, "timestamp": "2025-08-17T10:01:00Z", "user": "bob", "text": "Hi there", "channel": "general"},
            {"id": 3, "timestamp": "2025-08-17T10:02:00Z", "user": "charlie", "text": "Good morning", "channel": "general"}
        ]
        
        test_file = temp_dir / "slack" / "2025-08-17" / "data.jsonl"
        test_file.parent.mkdir(parents=True)
        
        with open(test_file, 'w') as f:
            for record in records:
                f.write(json.dumps(record) + '\n')
        
        count, errors = verifier._validate_jsonl_format(test_file)
        
        assert count == 3
        assert len(errors) == 0
    
    def test_jsonl_file_with_invalid_json(self, verifier, temp_dir):
        """Test JSONL file with invalid JSON lines"""
        test_file = temp_dir / "test.jsonl"
        
        with open(test_file, 'w') as f:
            f.write('{"valid": true}\n')  # Line 1: valid
            f.write('{"also": "valid"}\n')  # Line 2: valid  
            f.write('{"invalid": missing_quotes}\n')  # Line 3: invalid JSON
            f.write('{"valid": "again"}\n')  # Line 4: valid
            f.write('incomplete json\n')  # Line 5: invalid JSON
            f.write('{"final": "valid"}\n')  # Line 6: valid
        
        count, errors = verifier._validate_jsonl_format(test_file)
        
        assert count == 4  # 4 valid records
        assert len(errors) == 2  # 2 invalid lines
        
        # Check specific line numbers are reported
        error_lines = [int(err.split('Line ')[1].split(':')[0]) for err in errors if 'Line ' in err]
        assert 3 in error_lines
        assert 5 in error_lines
    
    def test_jsonl_file_with_schema_errors(self, verifier, temp_dir):
        """Test JSONL file with valid JSON but schema violations"""
        test_file = temp_dir / "slack" / "data.jsonl"
        test_file.parent.mkdir(parents=True)
        
        with open(test_file, 'w') as f:
            # Valid record
            f.write('{"timestamp": "2025-08-17T10:00:00Z", "user": "alice", "text": "Hello", "channel": "general"}\n')
            # Missing required field
            f.write('{"timestamp": "2025-08-17T10:01:00Z", "user": "bob", "text": "Hi"}\n')  # Missing channel
            # Invalid timestamp
            f.write('{"timestamp": "invalid", "user": "charlie", "text": "Hey", "channel": "general"}\n')
        
        count, errors = verifier._validate_jsonl_format(test_file)
        
        assert count == 3  # All are valid JSON
        assert len(errors) > 0  # But have schema errors
        
        # Should report schema violations
        assert any("Missing required fields" in error for error in errors)
        assert any("Invalid timestamp format" in error for error in errors)
    
    def test_compressed_jsonl_validation(self, verifier, temp_dir):
        """Test validation of compressed JSONL file"""
        records = [
            {"timestamp": "2025-08-17T10:00:00Z", "user": "alice", "text": "Hello", "channel": "general"},
            {"timestamp": "2025-08-17T10:01:00Z", "user": "bob", "text": "Hi", "channel": "general"}
        ]
        
        # Create compressed file
        test_file = temp_dir / "test.jsonl.gz"
        with gzip.open(test_file, 'wt') as f:
            for record in records:
                f.write(json.dumps(record) + '\n')
        
        count, errors = verifier._validate_jsonl_format(test_file)
        
        assert count == 2
        assert len(errors) == 0  # Should handle compression transparently


class TestArchiveVerification:
    """Test complete archive directory verification"""
    
    @pytest.fixture  
    def verifier(self):
        return ArchiveVerifier()
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    def create_test_archive(self, base_path: Path, source: str, date_str: str, 
                           record_count: int = 10, include_manifest: bool = True,
                           compress: bool = False, add_errors: bool = False):
        """Helper to create test archive directory"""
        archive_dir = base_path / source / date_str
        archive_dir.mkdir(parents=True)
        
        # Create data file
        data_file = archive_dir / ("data.jsonl.gz" if compress else "data.jsonl")
        
        records = []
        for i in range(record_count):
            if source == 'slack':
                record = {
                    "timestamp": f"2025-08-17T{10 + i//60:02d}:{i%60:02d}:00Z",
                    "user": f"U{i:03d}USER",
                    "text": f"Message {i}" if not (add_errors and i == 5) else "",  # Empty text for error
                    "channel": "C123GENERAL"
                }
            elif source == 'calendar':
                record = {
                    "timestamp": f"2025-08-17T{10 + i//60:02d}:{i%60:02d}:00Z",
                    "summary": f"Meeting {i}",
                    "start": f"2025-08-17T{14 + i//60:02d}:{i%60:02d}:00Z",
                    "end": f"2025-08-17T{15 + i//60:02d}:{i%60:02d}:00Z"
                }
            elif source == 'drive':
                record = {
                    "timestamp": f"2025-08-17T{10 + i//60:02d}:{i%60:02d}:00Z",
                    "name": f"document_{i}.pdf",
                    "id": f"doc_id_{i:03d}",
                    "mimeType": "application/pdf"
                }
            else:
                record = {
                    "timestamp": f"2025-08-17T{10 + i//60:02d}:{i%60:02d}:00Z",
                    "source": source,
                    "data": {"value": i}
                }
            
            # Add invalid JSON for error testing
            if add_errors and i == 8:
                continue  # Skip this record to create count mismatch
                
            records.append(record)
        
        # Write data file
        if compress:
            with gzip.open(data_file, 'wt') as f:
                for record in records:
                    f.write(json.dumps(record) + '\n')
                # Add invalid JSON line if testing errors
                if add_errors:
                    f.write('{"invalid": json}\n')
        else:
            with open(data_file, 'w') as f:
                for record in records:
                    f.write(json.dumps(record) + '\n')
                if add_errors:
                    f.write('{"invalid": json}\n')
        
        # Create manifest
        if include_manifest:
            manifest = {
                "source": source,
                "record_count": record_count if not add_errors else record_count - 1,  # Account for skipped record
                "file_size": data_file.stat().st_size,
                "checksum": hashlib.sha256(data_file.read_bytes()).hexdigest() if not compress else "placeholder",
                "last_write": f"{date_str}T10:00:00Z",
                "format": "jsonl",
                "encoding": "utf-8"
            }
            
            manifest_file = archive_dir / "manifest.json"
            with open(manifest_file, 'w') as f:
                json.dump(manifest, f, indent=2)
        
        return archive_dir
    
    def test_verify_valid_archive(self, verifier, temp_dir):
        """Test verification of valid archive directory"""
        archive_dir = self.create_test_archive(temp_dir, "slack", "2025-08-17", record_count=5)
        
        result = verifier.verify_archive(archive_dir)
        
        assert result.status == 'valid'
        assert result.record_count == 5
        assert result.source_type == 'slack'
        assert result.compression_detected == False
        assert len(result.errors) == 0
        assert result.checksum is not None
    
    def test_verify_compressed_archive(self, verifier, temp_dir):
        """Test verification of compressed archive"""
        archive_dir = self.create_test_archive(temp_dir, "calendar", "2025-08-17", 
                                             record_count=3, compress=True)
        
        result = verifier.verify_archive(archive_dir)
        
        assert result.status == 'valid'
        assert result.record_count == 3
        assert result.source_type == 'calendar'
        assert result.compression_detected == True
        assert len(result.errors) == 0
    
    def test_verify_archive_with_errors(self, verifier, temp_dir):
        """Test verification of archive with data errors"""
        archive_dir = self.create_test_archive(temp_dir, "slack", "2025-08-17",
                                             record_count=5, add_errors=True)
        
        result = verifier.verify_archive(archive_dir)
        
        assert result.status == 'corrupted'
        assert len(result.errors) > 0
        # Should detect invalid JSON and schema violations
        assert any("Invalid JSON" in str(result.errors) for _ in result.errors)
    
    def test_verify_missing_archive(self, verifier, temp_dir):
        """Test verification of non-existent archive"""
        missing_dir = temp_dir / "slack" / "2025-01-01"
        
        result = verifier.verify_archive(missing_dir)
        
        assert result.status == 'missing'
        assert result.record_count == 0
        assert len(result.errors) > 0
        assert "not found" in result.errors[0]
    
    def test_verify_archive_without_manifest(self, verifier, temp_dir):
        """Test verification when manifest is missing"""
        archive_dir = self.create_test_archive(temp_dir, "drive", "2025-08-17",
                                             include_manifest=False)
        
        result = verifier.verify_archive(archive_dir)
        
        assert result.status == 'corrupted'  # Missing manifest is an error
        assert any("Manifest file missing" in error for error in result.errors)


class TestManifestVerification:
    """Test manifest.json verification against actual file contents"""
    
    @pytest.fixture
    def verifier(self):
        return ArchiveVerifier()
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    def test_manifest_matches_actual_data(self, verifier, temp_dir):
        """Test manifest verification when data matches"""
        # Create test data
        data_content = b'{"test": "data"}\n{"more": "data"}\n'
        data_file = temp_dir / "data.jsonl"
        data_file.write_bytes(data_content)
        
        # Create matching manifest
        manifest = {
            "source": "test",
            "record_count": 2,
            "file_size": len(data_content),
            "checksum": hashlib.sha256(data_content).hexdigest(),
            "last_write": "2025-08-17T10:00:00Z"
        }
        manifest_file = temp_dir / "manifest.json"
        with open(manifest_file, 'w') as f:
            json.dump(manifest, f)
        
        # Test verification
        errors = verifier._verify_manifest(manifest_file, 2, len(data_content), 
                                         hashlib.sha256(data_content).hexdigest())
        
        assert len(errors) == 0
    
    def test_manifest_count_mismatch(self, verifier, temp_dir):
        """Test manifest with incorrect record count"""
        manifest = {
            "source": "test", 
            "record_count": 5,  # Wrong count
            "file_size": 100,
            "last_write": "2025-08-17T10:00:00Z"
        }
        
        manifest_file = temp_dir / "manifest.json"
        with open(manifest_file, 'w') as f:
            json.dump(manifest, f)
        
        errors = verifier._verify_manifest(manifest_file, 3, 100, "dummy_checksum")
        
        assert len(errors) > 0
        assert any("Record count mismatch" in error for error in errors)
    
    def test_manifest_checksum_mismatch(self, verifier, temp_dir):
        """Test manifest with incorrect checksum"""
        manifest = {
            "source": "test",
            "record_count": 2,
            "file_size": 100,
            "checksum": "wrong_checksum",
            "last_write": "2025-08-17T10:00:00Z"
        }
        
        manifest_file = temp_dir / "manifest.json"
        with open(manifest_file, 'w') as f:
            json.dump(manifest, f)
        
        errors = verifier._verify_manifest(manifest_file, 2, 100, "correct_checksum")
        
        assert len(errors) > 0
        assert any("Checksum mismatch" in error for error in errors)
    
    def test_manifest_invalid_json(self, verifier, temp_dir):
        """Test manifest with invalid JSON"""
        manifest_file = temp_dir / "manifest.json"
        manifest_file.write_text('{"invalid": json}')  # Invalid JSON
        
        errors = verifier._verify_manifest(manifest_file, 2, 100, "checksum")
        
        assert len(errors) > 0
        assert any("invalid JSON" in error for error in errors)


class TestCheckpointSystem:
    """Test resume capability for interrupted verification operations"""
    
    @pytest.fixture
    def verifier(self):
        return ArchiveVerifier()
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    def test_save_and_load_checkpoint(self, verifier, temp_dir):
        """Test checkpoint save and load functionality"""
        test_file = temp_dir / "test.jsonl"
        test_file.write_text('{"test": "data"}\n')
        
        # Save checkpoint
        verifier._save_checkpoint(test_file, 100)
        
        # Load checkpoint
        checkpoint = verifier.load_checkpoint()
        
        assert checkpoint['last_file'] == str(test_file)
        assert checkpoint['line_number'] == 100
        assert 'timestamp' in checkpoint
        assert checkpoint['version'] == '1.0'
    
    def test_load_nonexistent_checkpoint(self, verifier):
        """Test loading checkpoint when none exists"""
        # Ensure no checkpoint file exists
        if verifier.checkpoint_file.exists():
            verifier.checkpoint_file.unlink()
        
        checkpoint = verifier.load_checkpoint()
        assert checkpoint == {}
    
    def test_checkpoint_updates_stats(self, verifier, temp_dir):
        """Test that loading checkpoint updates verifier stats"""
        # Create and save checkpoint with stats
        verifier.stats['records_verified'] = 500
        verifier.stats['files_checked'] = 5
        
        test_file = temp_dir / "test.jsonl"
        verifier._save_checkpoint(test_file, 100)
        
        # Create new verifier and load checkpoint
        new_verifier = ArchiveVerifier()
        checkpoint = new_verifier.load_checkpoint()
        
        assert new_verifier.stats['records_verified'] == 500
        assert new_verifier.stats['files_checked'] == 5


class TestSourceDetection:
    """Test automatic detection of data source types from file paths"""
    
    @pytest.fixture
    def verifier(self):
        return ArchiveVerifier()
    
    def test_detect_slack_source(self, verifier):
        """Test detection of Slack source from path"""
        slack_paths = [
            Path("/data/archive/slack/2025-08-17/data.jsonl"),
            Path("slack/messages.jsonl.gz"),
            Path("archives/slack_data.jsonl")
        ]
        
        for path in slack_paths:
            source = verifier._detect_source(path)
            assert source == 'slack'
    
    def test_detect_calendar_source(self, verifier):
        """Test detection of Calendar source from path"""
        calendar_paths = [
            Path("/data/archive/calendar/2025-08-17/data.jsonl"),
            Path("calendar/events.jsonl"),
            Path("cal_data/calendar_events.jsonl.gz")
        ]
        
        for path in calendar_paths:
            source = verifier._detect_source(path)
            assert source == 'calendar'
    
    def test_detect_drive_source(self, verifier):
        """Test detection of Drive source from path"""
        drive_paths = [
            Path("/data/archive/drive/2025-08-17/data.jsonl"),
            Path("google_drive/changes.jsonl"),
            Path("drive_metadata.jsonl.gz")
        ]
        
        for path in drive_paths:
            source = verifier._detect_source(path)
            assert source == 'drive'
    
    def test_detect_employee_source(self, verifier):
        """Test detection of Employee source from path"""
        employee_paths = [
            Path("/data/archive/employee/roster.jsonl"),
            Path("employees/data.jsonl")
        ]
        
        for path in employee_paths:
            source = verifier._detect_source(path)
            assert source == 'employees'
    
    def test_default_source_detection(self, verifier):
        """Test fallback to default source"""
        unknown_paths = [
            Path("/data/unknown/data.jsonl"),
            Path("random_file.jsonl"),
            Path("misc/data.txt")
        ]
        
        for path in unknown_paths:
            source = verifier._detect_source(path)
            assert source == 'default'


class TestDirectoryVerification:
    """Test batch verification of multiple files with progress tracking"""
    
    @pytest.fixture
    def verifier(self):
        return ArchiveVerifier()
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    def create_test_files(self, base_dir: Path, count: int = 5, with_errors: bool = False):
        """Create multiple test JSONL files"""
        files = []
        
        for i in range(count):
            file_path = base_dir / f"test_{i}.jsonl"
            
            records = [
                {"timestamp": f"2025-08-17T{10+j:02d}:00:00Z", "source": "test", "data": {"id": j}}
                for j in range(3)
            ]
            
            with open(file_path, 'w') as f:
                for record in records:
                    f.write(json.dumps(record) + '\n')
                
                # Add invalid JSON to some files for error testing
                if with_errors and i % 2 == 0:
                    f.write('{"invalid": json}\n')
            
            files.append(file_path)
        
        return files
    
    def test_verify_directory_all_valid(self, verifier, temp_dir):
        """Test directory verification with all valid files"""
        self.create_test_files(temp_dir, count=3)
        
        stats = verifier.verify_directory(temp_dir, resume=False)
        
        assert stats['files_checked'] == 3
        assert stats['records_verified'] > 0
        assert len(stats['errors']) == 0
    
    def test_verify_directory_with_errors(self, verifier, temp_dir):
        """Test directory verification with some invalid files"""
        self.create_test_files(temp_dir, count=4, with_errors=True)
        
        stats = verifier.verify_directory(temp_dir, resume=False)
        
        assert stats['files_checked'] == 4
        assert len(stats['errors']) > 0  # Should have detected invalid JSON
    
    @patch('src.core.verification.tqdm')
    def test_verify_directory_progress_tracking(self, mock_tqdm, verifier, temp_dir):
        """Test that progress tracking is used during directory verification"""
        self.create_test_files(temp_dir, count=2)
        
        # Mock tqdm to track calls
        mock_progress = MagicMock()
        mock_tqdm.return_value.__enter__.return_value = mock_progress
        
        verifier.verify_directory(temp_dir, resume=False)
        
        # Should have created progress bars for file verification
        assert mock_tqdm.called


class TestReportGeneration:
    """Test comprehensive verification report generation"""
    
    @pytest.fixture
    def verifier(self):
        return ArchiveVerifier()
    
    def create_sample_results(self) -> Dict[str, VerificationResult]:
        """Create sample verification results for testing"""
        results = {}
        
        # Valid result
        results['2025-08-15'] = VerificationResult(
            path="/archive/slack/2025-08-15",
            status='valid',
            record_count=150,
            file_size=45678,
            checksum="abc123def456",
            errors=[],
            timestamp="2025-08-17T10:00:00Z",
            source_type='slack'
        )
        
        # Corrupted result
        results['2025-08-16'] = VerificationResult(
            path="/archive/calendar/2025-08-16",
            status='corrupted',
            record_count=75,
            file_size=23456,
            checksum="def789ghi012",
            errors=["Invalid JSON at line 15", "Missing required field: summary"],
            timestamp="2025-08-17T10:05:00Z",
            source_type='calendar'
        )
        
        # Missing result
        results['2025-08-17'] = VerificationResult(
            path="/archive/drive/2025-08-17",
            status='missing',
            record_count=0,
            file_size=0,
            checksum=None,
            errors=["Archive directory not found"],
            timestamp="2025-08-17T10:10:00Z",
            source_type='drive'
        )
        
        return results
    
    def test_generate_verification_report(self, verifier):
        """Test comprehensive report generation"""
        results = self.create_sample_results()
        report = verifier.generate_verification_report(results)
        
        # Check report structure
        assert 'timestamp' in report
        assert 'verification_summary' in report
        assert 'data_statistics' in report
        assert 'source_breakdown' in report
        assert 'error_summary' in report
        assert 'recommendations' in report
        
        # Check summary counts
        summary = report['verification_summary']
        assert summary['total_archives'] == 3
        assert summary['valid'] == 1
        assert summary['corrupted'] == 1
        assert summary['missing'] == 1
        assert summary['success_rate'] == 1/3
    
    def test_report_source_breakdown(self, verifier):
        """Test source-specific statistics in report"""
        results = self.create_sample_results()
        report = verifier.generate_verification_report(results)
        
        source_breakdown = report['source_breakdown']
        
        # Should have entries for each source type
        assert 'slack' in source_breakdown
        assert 'calendar' in source_breakdown
        assert 'drive' in source_breakdown
        
        # Check slack stats
        slack_stats = source_breakdown['slack']
        assert slack_stats['archives'] == 1
        assert slack_stats['valid'] == 1
        assert slack_stats['total_records'] == 150
    
    def test_report_recommendations(self, verifier):
        """Test recommendation generation based on results"""
        results = self.create_sample_results()
        report = verifier.generate_verification_report(results)
        
        recommendations = report['recommendations']
        assert len(recommendations) > 0
        
        # Should recommend investigating corrupted archives
        assert any("corrupted" in rec.lower() for rec in recommendations)


class TestCompressionSupport:
    """Test support for compressed archive files"""
    
    @pytest.fixture
    def verifier(self):
        return ArchiveVerifier()
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    def test_get_file_opener_regular_file(self, verifier):
        """Test file opener selection for regular files"""
        opener = verifier._get_file_opener(Path("test.jsonl"))
        assert opener == open
    
    def test_get_file_opener_gzip_file(self, verifier):
        """Test file opener selection for gzip files"""
        opener = verifier._get_file_opener(Path("test.jsonl.gz"))
        assert opener == gzip.open
    
    @pytest.mark.skipif(True, reason="zstandard optional dependency")
    def test_get_file_opener_zstd_file(self, verifier):
        """Test file opener selection for zstd files"""
        # This test would run if zstandard is available
        pass
    
    def test_verify_compressed_jsonl_file(self, verifier, temp_dir):
        """Test end-to-end verification of compressed JSONL file"""
        # Create test data
        records = [
            {"timestamp": "2025-08-17T10:00:00Z", "source": "test", "data": {"id": i}}
            for i in range(5)
        ]
        
        # Create compressed file
        compressed_file = temp_dir / "test.jsonl.gz"
        with gzip.open(compressed_file, 'wt') as f:
            for record in records:
                f.write(json.dumps(record) + '\n')
        
        # Verify compressed file
        result = verifier.verify_jsonl_file(compressed_file)
        
        assert result['is_valid']
        assert result['lines_processed'] == 5
        assert result['compression_detected'] == True
        assert len(result['errors']) == 0


if __name__ == "__main__":
    pytest.main([__file__])