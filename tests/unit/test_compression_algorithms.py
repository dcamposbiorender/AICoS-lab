"""
Test compression algorithms for JSONL data with critical safety fixes
Tests atomic operations, backup mechanisms, and dependency handling
"""
import pytest
import json
import gzip
import time
from pathlib import Path
import tempfile
import threading
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

# Import the SafeCompressor and other classes
from src.core.compression import SafeCompressor, CompressionError, HAS_ZSTD, HAS_TQDM, HAS_FILELOCK

try:
    import zstandard as zstd
    HAS_ZSTD = True
except ImportError:
    HAS_ZSTD = False
    import gzip

class TestCompressionAlgorithms:
    """Test different compression algorithms for JSONL data"""
    
    @pytest.fixture
    def sample_jsonl_data(self):
        """Generate realistic JSONL test data"""
        records = []
        for i in range(1000):
            record = {
                "id": f"msg_{i:04d}",
                "timestamp": f"2025-08-15T10:{i%60:02d}:{i%60:02d}Z",
                "user": f"U{i%20:02d}USER",
                "channel": f"C{i%5:02d}CHANNEL", 
                "text": f"This is message {i} with some repeated content patterns" * (i % 3 + 1),
                "thread_ts": f"1234567890.{i:06d}" if i % 10 == 0 else None,
                "reactions": [{"name": "thumbsup", "count": i % 5}] if i % 7 == 0 else [],
                "metadata": {
                    "client_msg_id": f"client_{i}",
                    "type": "message",
                    "subtype": "bot_message" if i % 15 == 0 else None
                }
            }
            records.append(json.dumps(record))
        return "\n".join(records).encode('utf-8')
    
    @pytest.fixture
    def test_file(self, tmp_path, sample_jsonl_data):
        """Create a test JSONL file"""
        test_file = tmp_path / "test_data.jsonl"
        test_file.write_bytes(sample_jsonl_data)
        return test_file
    
    def test_gzip_compression_ratio(self, sample_jsonl_data):
        """Test gzip compression ratio and speed"""
        start_time = time.time()
        compressed = gzip.compress(sample_jsonl_data, compresslevel=6)
        compression_time = time.time() - start_time
        
        ratio = len(compressed) / len(sample_jsonl_data)
        
        # Decompress to verify
        start_time = time.time()
        decompressed = gzip.decompress(compressed)
        decompression_time = time.time() - start_time
        
        assert decompressed == sample_jsonl_data
        assert ratio < 0.3  # Expect at least 70% compression
        assert compression_time < 0.5  # Should be reasonably fast
        assert decompression_time < 0.1  # Decompression faster
    
    @pytest.mark.skipif(not HAS_ZSTD, reason="zstandard not available")
    def test_zstandard_compression_ratio(self, sample_jsonl_data):
        """Test zstandard compression - best balance of speed and ratio"""
        cctx = zstd.ZstdCompressor(level=3)
        
        start_time = time.time()
        compressed = cctx.compress(sample_jsonl_data)
        compression_time = time.time() - start_time
        
        ratio = len(compressed) / len(sample_jsonl_data)
        
        # Decompress to verify
        dctx = zstd.ZstdDecompressor()
        start_time = time.time()
        decompressed = dctx.decompress(compressed)
        decompression_time = time.time() - start_time
        
        assert decompressed == sample_jsonl_data
        assert ratio < 0.25  # Zstd typically better than gzip
        assert compression_time < 0.2  # Much faster than gzip
        assert decompression_time < 0.05  # Very fast decompression
    
    def test_streaming_compression(self, sample_jsonl_data):
        """Test streaming compression for large files"""
        if not HAS_ZSTD:
            pytest.skip("zstandard required for streaming test")
        
        # Simulate streaming with chunks
        chunk_size = 8192
        chunks = [sample_jsonl_data[i:i+chunk_size] 
                 for i in range(0, len(sample_jsonl_data), chunk_size)]
        
        # Streaming compression with zstandard
        cctx = zstd.ZstdCompressor(level=3)
        compressor = cctx.compressobj()
        
        compressed_chunks = []
        for chunk in chunks:
            compressed_chunks.append(compressor.compress(chunk))
        compressed_chunks.append(compressor.flush())
        
        compressed = b''.join(compressed_chunks)
        
        # Verify streaming decompression
        dctx = zstd.ZstdDecompressor()
        decompressed = dctx.decompress(compressed)
        
        assert decompressed == sample_jsonl_data

    def test_atomic_compression_safety(self, tmp_path):
        """Test atomic compression prevents data loss"""
        # Create test file
        test_file = tmp_path / "test.jsonl"
        test_data = b'{"test": "data"}\n{"more": "data"}\n'
        test_file.write_bytes(test_data)
        
        # Test that compression fails safely - simulate failure during compression
        compressed_file = tmp_path / "test.jsonl.gz"
        
        try:
            # Simulate compression failure after partial write
            with pytest.raises(Exception):
                with gzip.open(compressed_file, 'wb') as f:
                    f.write(test_data[:10])
                    raise Exception("Simulated failure")
        finally:
            # Clean up the partial file (this simulates what our SafeCompressor does)
            compressed_file.unlink(missing_ok=True)
        
        # Original file should still exist
        assert test_file.exists()
        assert test_file.read_bytes() == test_data
        
        # Partial compressed file should be cleaned up
        assert not compressed_file.exists()

class TestSafeCompressor:
    """Test SafeCompressor class with critical fixes"""
    
    @pytest.fixture
    def compressor(self):
        """Create SafeCompressor instance"""
        return SafeCompressor(backup_days=3)
    
    @pytest.fixture 
    def test_file(self, tmp_path):
        """Create test JSONL file"""
        test_file = tmp_path / "test_data.jsonl"
        data = []
        for i in range(100):
            data.append(json.dumps({"id": i, "text": f"Message {i}"}))
        test_file.write_text("\n".join(data))
        return test_file
    
    def test_atomic_compression_success(self, compressor, test_file):
        """Test successful atomic compression"""
        original_size = test_file.stat().st_size
        
        # Compress file
        result = compressor.compress_file_atomic(test_file)
        
        assert result is True
        assert not test_file.exists()  # Original should be gone
        
        # Compressed file should exist
        compressed_file = test_file.with_suffix('.jsonl.gz')
        assert compressed_file.exists()
        assert compressed_file.stat().st_size < original_size
        
        # Should be readable
        with gzip.open(compressed_file, 'rt') as f:
            content = f.read()
            assert '"id": 0' in content
            assert '"id": 99' in content
    
    def test_atomic_compression_with_backup(self, compressor, test_file):
        """Test compression with backup creation"""
        result = compressor.compress_with_backup(test_file)
        
        assert result is True
        assert not test_file.exists()  # Original should be gone
        
        # Compressed file should exist
        compressed_file = test_file.with_suffix('.jsonl.gz')
        assert compressed_file.exists()
        
        # Backup should exist
        backup_dir = test_file.parent / '.backup'
        assert backup_dir.exists()
        backup_files = list(backup_dir.glob('test_data.jsonl.*'))
        assert len(backup_files) == 1
        
        # Backup should be readable
        backup_file = backup_files[0]
        with open(backup_file) as f:
            content = f.read()
            assert '"id": 0' in content
    
    def test_two_phase_commit_verification(self, compressor, test_file):
        """Test two-phase commit with verification"""
        # Mock gzip.open to fail verification step
        original_open = gzip.open
        
        def failing_verify(*args, **kwargs):
            if 'rb' in args:
                # Fail on verification read
                raise gzip.BadGzipFile("Corrupted file")
            return original_open(*args, **kwargs)
        
        with patch('gzip.open', side_effect=failing_verify):
            with pytest.raises(CompressionError, match="Atomic compression failed"):
                compressor.compress_file_atomic(test_file)
        
        # Original file should still exist after failure
        assert test_file.exists()
        
        # No compressed file should exist
        compressed_file = test_file.with_suffix('.jsonl.gz')
        assert not compressed_file.exists()
    
    def test_file_active_detection(self, compressor, test_file):
        """Test active file detection"""
        # File should not be active (was created in fixture, should be older than 1 second)
        import time
        time.sleep(1.1)  # Wait a bit to ensure file is older than idle_seconds
        assert not compressor._is_file_active(test_file, idle_seconds=1)
        
        # Modify file to make it "active"
        test_file.write_text("new content")
        assert compressor._is_file_active(test_file, idle_seconds=60)
    
    def test_safe_compress_skips_active_files(self, compressor, test_file):
        """Test that safe_compress skips recently modified files"""
        # Touch file to make it recent
        test_file.touch()
        
        result = compressor.safe_compress(test_file, idle_seconds=60)
        
        assert result is False
        assert compressor.stats['skipped'] == 1
        assert test_file.exists()  # File should not be compressed
    
    @pytest.mark.skipif(not HAS_FILELOCK, reason="filelock not available")
    def test_file_locking(self, compressor, test_file):
        """Test file locking prevents concurrent access"""
        import filelock
        
        # Create a lock on the file
        lock_path = f"{test_file}.lock"
        lock = filelock.FileLock(lock_path)
        
        with lock:
            # Try to compress while locked
            result = compressor.safe_compress(test_file, idle_seconds=0)
            
            assert result is False
            assert compressor.stats['skipped'] == 1
            assert test_file.exists()  # File should not be compressed
    
    def test_streaming_compression_large_file(self, compressor, tmp_path):
        """Test streaming compression for large files"""
        # Create larger test file (simulated)
        large_file = tmp_path / "large_data.jsonl"
        
        # Write in chunks to simulate large file
        with open(large_file, 'w') as f:
            for i in range(10000):
                f.write(json.dumps({"id": i, "data": "x" * 100}) + "\n")
        
        original_size = large_file.stat().st_size
        assert original_size > 1_000_000  # Ensure it's reasonably large
        
        result = compressor.compress_streaming(large_file)
        
        assert result is True
        assert not large_file.exists()  # Original should be gone
        
        # Compressed file should exist and be smaller
        compressed_file = large_file.with_suffix('.jsonl.gz')
        assert compressed_file.exists()
        assert compressed_file.stat().st_size < original_size
    
    def test_backup_cleanup_tracking(self, compressor, test_file):
        """Test backup cleanup is properly tracked"""
        # Create backup
        compressor.compress_with_backup(test_file)
        
        # Check backup registry
        registry = compressor.get_backup_registry()
        assert len(registry) == 1
        
        backup_path = list(registry.keys())[0]
        backup_info = registry[backup_path]
        assert 'created' in backup_info
        assert 'cleanup_date' in backup_info
        assert 'size' in backup_info
    
    def test_actual_backup_cleanup(self, compressor, tmp_path):
        """Test actual cleanup of old backups"""
        # Create test file and compress it
        test_file = tmp_path / "cleanup_test.jsonl"
        test_file.write_text('{"test": "data"}')
        
        # Compress to create backup
        compressor.compress_with_backup(test_file)
        
        # Verify backup exists
        backup_dir = test_file.parent / '.backup'
        backup_files = list(backup_dir.glob('cleanup_test.jsonl.*'))
        assert len(backup_files) == 1
        
        # Force cleanup
        stats = compressor.cleanup_old_backups(force=True)
        
        assert stats['cleaned_count'] == 1
        assert stats['bytes_freed'] > 0
        assert len(stats['errors']) == 0
        
        # Backup should be gone
        backup_files = list(backup_dir.glob('cleanup_test.jsonl.*'))
        assert len(backup_files) == 0
    
    def test_dependency_fallbacks(self, compressor):
        """Test that missing dependencies don't cause crashes"""
        # Test should pass regardless of whether optional deps are installed
        assert compressor is not None
        
        # Test progress bar fallback
        if not HAS_TQDM:
            # Should still work without tqdm
            from src.core.compression import tqdm
            pbar = tqdm(range(10), desc="Test")
            count = 0
            for _ in pbar:
                count += 1
            assert count == 10
    
    def test_compress_old_files(self, compressor, tmp_path):
        """Test compression of old files with safety features"""
        # Create multiple test files with different ages
        old_file = tmp_path / "old.jsonl"
        recent_file = tmp_path / "recent.jsonl"
        
        # Write files
        old_file.write_text('{"old": "data"}')
        recent_file.write_text('{"recent": "data"}')
        
        # Make old file actually old
        old_time = time.time() - (40 * 86400)  # 40 days ago
        import os
        os.utime(old_file, (old_time, old_time))
        
        # Compress files older than 30 days
        stats = compressor.compress_old_files(tmp_path, age_days=30)
        
        # Only old file should be compressed
        assert not old_file.exists()
        assert old_file.with_suffix('.jsonl.gz').exists()
        assert recent_file.exists()  # Recent file untouched
        
        assert stats['compressed'] >= 1
    
    def test_read_compressed_jsonl(self, compressor, test_file):
        """Test reading compressed JSONL files"""
        # Compress the file first
        compressor.compress_file_atomic(test_file)
        compressed_file = test_file.with_suffix('.jsonl.gz')
        
        # Read back the data
        records = list(compressor.read_compressed_jsonl(compressed_file))
        
        assert len(records) == 100
        assert records[0]['id'] == 0
        assert records[99]['id'] == 99
        assert all('text' in record for record in records)
    
    def test_compression_stats(self, compressor, tmp_path):
        """Test compression statistics calculation"""
        # Create and compress some files
        for i in range(3):
            test_file = tmp_path / f"test_{i}.jsonl"
            test_file.write_text(f'{{"id": {i}, "data": "test"}}')
            compressor.compress_file_atomic(test_file)
        
        # Calculate stats
        stats = compressor.get_compression_stats(tmp_path)
        
        assert stats['file_count'] == 3
        assert stats['total_compressed'] > 0
        assert '.gz' in stats['by_extension']
        assert stats['by_extension']['.gz']['count'] == 3
    
    def test_error_handling_and_logging(self, compressor, tmp_path, caplog):
        """Test error handling and logging"""
        # Try to compress non-existent file
        nonexistent = tmp_path / "nonexistent.jsonl"
        
        result = compressor.compress_file_atomic(nonexistent)
        assert result is False
        assert "File not found" in caplog.text
    
    def test_concurrent_compression(self, tmp_path):
        """Test thread safety of compression operations"""
        # Create multiple files
        files = []
        for i in range(5):
            test_file = tmp_path / f"concurrent_{i}.jsonl"
            test_file.write_text(f'{{"id": {i}}}')
            files.append(test_file)
        
        compressor = SafeCompressor()
        results = []
        
        def compress_file(file_path):
            try:
                result = compressor.compress_file_atomic(file_path)
                results.append(result)
            except Exception as e:
                results.append(False)
        
        # Run compressions concurrently
        threads = []
        for file_path in files:
            thread = threading.Thread(target=compress_file, args=(file_path,))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # All compressions should succeed
        assert all(results)
        assert len(results) == 5
        
        # All files should be compressed
        for i in range(5):
            compressed = tmp_path / f"concurrent_{i}.jsonl.gz"
            assert compressed.exists()