#!/usr/bin/env python3
"""
Tests for basic compression utilities
Following TDD approach - tests written first before implementation
"""

import gzip
import json
import tempfile
import pytest
from pathlib import Path
from datetime import datetime, timedelta
import hashlib
import os

from src.core.compression import Compressor, CompressionError


class TestBasicCompression:
    """Test basic gzip compression functionality"""

    def test_gzip_compression_basic(self):
        """Files can be compressed with gzip"""
        # ACCEPTANCE: .jsonl files become .jsonl.gz
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            test_file = temp_path / "test.jsonl"
            
            # Create test JSONL file
            test_data = [
                {"message": "Hello World", "timestamp": "2025-08-15T10:00:00"},
                {"message": "Test Message", "timestamp": "2025-08-15T10:01:00"}
            ]
            
            with open(test_file, 'w') as f:
                for item in test_data:
                    f.write(json.dumps(item) + '\n')
            
            compressor = Compressor()
            compressed_file = compressor.compress(test_file)
            
            assert compressed_file.exists()
            assert compressed_file.suffix == '.gz'
            assert not test_file.exists()  # Original should be removed

    def test_compression_preserves_data_integrity(self):
        """Compressed files decompress to identical original"""
        # ACCEPTANCE: File contents identical before/after compression
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            test_file = temp_path / "integrity_test.jsonl"
            
            # Create test data
            original_data = [
                {"id": i, "data": f"test_{i}", "nested": {"value": i * 2}}
                for i in range(100)
            ]
            
            # Write original file
            with open(test_file, 'w') as f:
                for item in original_data:
                    f.write(json.dumps(item) + '\n')
            
            # Calculate original hash
            original_hash = hashlib.sha256(test_file.read_bytes()).hexdigest()
            
            # Compress and decompress
            compressor = Compressor()
            compressed_file = compressor.compress(test_file)
            decompressed_file = compressor.decompress(compressed_file)
            
            # Calculate decompressed hash
            decompressed_hash = hashlib.sha256(decompressed_file.read_bytes()).hexdigest()
            
            assert original_hash == decompressed_hash

    def test_finds_old_files(self):
        """Can identify files older than specified age"""
        # ACCEPTANCE: Correctly identifies files older than 30 days
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create files with different ages
            old_file = temp_path / "old.jsonl"
            recent_file = temp_path / "recent.jsonl"
            
            old_file.write_text('{"old": true}\n')
            recent_file.write_text('{"recent": true}\n')
            
            # Modify timestamps (31 days ago vs 1 day ago)
            old_time = datetime.now().timestamp() - (31 * 24 * 60 * 60)
            recent_time = datetime.now().timestamp() - (1 * 24 * 60 * 60)
            
            os.utime(old_file, (old_time, old_time))
            os.utime(recent_file, (recent_time, recent_time))
            
            compressor = Compressor()
            old_files = compressor.find_old_files(temp_path, age_days=30)
            
            assert old_file in old_files
            assert recent_file not in old_files

    def test_compression_error_handling(self):
        """Handles compression errors gracefully"""
        # ACCEPTANCE: Raises CompressionError for invalid inputs
        compressor = Compressor()
        
        with pytest.raises(CompressionError):
            compressor.compress(Path("nonexistent_file.jsonl"))

    def test_compression_verification(self):
        """Can verify compression integrity"""
        # ACCEPTANCE: Detects corrupted compressed files
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            test_file = temp_path / "verify_test.jsonl"
            
            test_file.write_text('{"test": "data"}\n')
            
            compressor = Compressor()
            compressed_file = compressor.compress(test_file)
            
            # Test valid file
            assert compressor.verify_compression(compressed_file) == True
            
            # Corrupt the file by damaging the gzip header
            with open(compressed_file, 'rb') as f:
                data = bytearray(f.read())
            # Corrupt the gzip magic number (first 2 bytes should be 0x1f, 0x8b)
            data[0] = 0xFF  # Corrupt magic number
            data[1] = 0xFF  # Corrupt magic number
            with open(compressed_file, 'wb') as f:
                f.write(data)
            
            # Test corrupted file
            assert compressor.verify_compression(compressed_file) == False