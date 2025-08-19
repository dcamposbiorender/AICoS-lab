"""
Performance benchmarking tests for AI Chief of Staff system.

Validates performance targets:
- Search response time: <1 second for 340K records
- Indexing throughput: >1000 records/second  
- Compression ratio: 70% size reduction
- Memory usage: <500MB for normal operations
"""

import pytest
import time
import tempfile
import json
import psutil
import threading
from pathlib import Path
from unittest.mock import patch
import gzip
import sqlite3
from concurrent.futures import ThreadPoolExecutor
import memory_profiler

# Import test fixtures and utilities
import sys
sys.path.append('..')
from fixtures.large_datasets import LargeDatasetGenerator
from utilities.performance_monitors import PerformanceMonitor, MemoryTracker

# Import system components
sys.path.append('../src')
from src.core.config import Config
from src.core.archive_writer import ArchiveWriter
from src.search.database import SearchDatabase
from src.search.indexer import ArchiveIndexer
from src.core.compression import Compressor
from src.core.state import StateManager


class TestSearchPerformance:
    """Test search performance with realistic data volumes."""
    
    def setup_method(self):
        """Set up performance test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_env = {
            "AICOS_BASE_DIR": self.temp_dir,
            "AICOS_TEST_MODE": "true"
        }
        
        # Generate large realistic dataset
        self.data_generator = LargeDatasetGenerator()
        print("🏗️  Generating performance test dataset...")
        
        # Generate 10K messages for realistic testing
        self.test_messages = list(self.data_generator.generate_slack_messages(10000))
        print(f"✅ Generated {len(self.test_messages)} test messages")
    
    @pytest.mark.performance
    @pytest.mark.slow
    def test_search_performance_340k_records(self):
        """Test search performance with 340K+ records (matches production)."""
        with patch.dict('os.environ', self.test_env):
            config = Config()
            search_db = SearchDatabase(config.data_dir / "perf_search.db")
            
            print("📊 Performance test: Search with 340K+ records")
            
            # Simulate 340K records by inserting directly to database
            # (generating 340K realistic records would take too long)
            print("  Populating database with 340K test records...")
            
            start_time = time.time()
            
            # Insert test records in batches for efficiency
            batch_size = 1000
            total_records = 340000
            
            for batch_start in range(0, total_records, batch_size):
                batch_records = []
                for i in range(batch_start, min(batch_start + batch_size, total_records)):
                    record = {
                        "id": f"perf_record_{i}",
                        "content": f"This is test record {i} with searchable content about projects, meetings, and discussions",
                        "timestamp": f"2025-08-{(i % 30) + 1:02d}T{(i % 24):02d}:00:00Z",
                        "source": "slack",
                        "user": f"user_{i % 100}",
                        "channel": f"channel_{i % 50}"
                    }
                    batch_records.append(record)
                
                search_db.insert_batch(batch_records)
                
                if batch_start % 10000 == 0:
                    elapsed = time.time() - start_time
                    rate = (batch_start + batch_size) / elapsed if elapsed > 0 else 0
                    print(f"    Inserted {batch_start + batch_size:,} records ({rate:.1f} records/sec)")
            
            insertion_time = time.time() - start_time
            print(f"  ✅ Database populated in {insertion_time:.1f} seconds")
            
            # Test search performance with various query types
            search_queries = [
                "project",
                "meeting discussion",
                "user_50 channel_25", 
                "test record searchable",
                "projects meetings discussions"
            ]
            
            print("  🔍 Testing search performance...")
            search_times = []
            
            for query in search_queries:
                start_time = time.time()
                results = search_db.search(query, limit=50)
                search_time = time.time() - start_time
                search_times.append(search_time)
                
                print(f"    Query '{query}': {search_time:.3f}s ({len(results)} results)")
                
                # Performance requirement: <1 second per search
                assert search_time < 1.0, f"Search too slow: {search_time:.3f}s for query '{query}'"
            
            avg_search_time = sum(search_times) / len(search_times)
            print(f"  📈 Average search time: {avg_search_time:.3f} seconds")
            
            # Verify result quality
            detailed_results = search_db.search("test record", limit=10)
            assert len(detailed_results) > 0, "Should find relevant results"
            
            search_db.close()
    
    @pytest.mark.performance
    def test_concurrent_search_performance(self):
        """Test search performance under concurrent load."""
        with patch.dict('os.environ', self.test_env):
            config = Config()
            search_db = SearchDatabase(config.data_dir / "concurrent_search.db")
            
            # Insert test data
            test_records = []
            for i in range(5000):
                test_records.append({
                    "id": f"concurrent_record_{i}",
                    "content": f"Concurrent test record {i} with various keywords like project, meeting, discussion",
                    "timestamp": f"2025-08-18T{i % 24:02d}:{i % 60:02d}:00Z",
                    "source": "slack"
                })
            
            search_db.insert_batch(test_records)
            
            # Test concurrent searches
            def search_worker(worker_id):
                search_times = []
                queries = ["project", "meeting", "discussion", f"record_{worker_id}"]
                
                for query in queries:
                    start_time = time.time()
                    results = search_db.search(query)
                    search_time = time.time() - start_time
                    search_times.append(search_time)
                
                return search_times
            
            print("🔄 Testing concurrent search performance...")
            
            # Run 20 concurrent search workers
            with ThreadPoolExecutor(max_workers=20) as executor:
                start_time = time.time()
                futures = [executor.submit(search_worker, i) for i in range(20)]
                
                all_search_times = []
                for future in futures:
                    worker_times = future.result()
                    all_search_times.extend(worker_times)
                
                total_time = time.time() - start_time
            
            # Analyze results
            avg_search_time = sum(all_search_times) / len(all_search_times)
            max_search_time = max(all_search_times)
            total_searches = len(all_search_times)
            
            print(f"  ✅ {total_searches} concurrent searches completed in {total_time:.2f}s")
            print(f"  📊 Average search time: {avg_search_time:.3f}s")
            print(f"  📊 Maximum search time: {max_search_time:.3f}s")
            
            # Performance requirements
            assert avg_search_time < 1.0, f"Average search time too slow: {avg_search_time:.3f}s"
            assert max_search_time < 2.0, f"Maximum search time too slow: {max_search_time:.3f}s"
            
            search_db.close()


class TestIndexingPerformance:
    """Test indexing performance and throughput."""
    
    def setup_method(self):
        """Set up indexing performance test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_env = {
            "AICOS_BASE_DIR": self.temp_dir,
            "AICOS_TEST_MODE": "true"
        }
    
    @pytest.mark.performance
    def test_indexing_throughput_target(self):
        """Test indexing achieves >1000 records/second target."""
        with patch.dict('os.environ', self.test_env):
            config = Config()
            archive_writer = ArchiveWriter(config.archive_dir)
            search_db = SearchDatabase(config.data_dir / "indexing_perf.db")
            indexer = ArchiveIndexer(search_db, config.archive_dir)
            
            # Generate test data
            data_generator = LargeDatasetGenerator()
            test_records = list(data_generator.generate_slack_messages(5000))
            
            print(f"📝 Archiving {len(test_records)} records for indexing test...")
            
            # Archive test data
            for record in test_records:
                archive_writer.write_record("indexing_perf", record)
            
            print("🚀 Testing indexing performance...")
            
            # Measure indexing performance
            start_time = time.time()
            indexer.index_directory(config.archive_dir)
            indexing_time = time.time() - start_time
            
            indexing_rate = len(test_records) / indexing_time
            
            print(f"  ✅ Indexed {len(test_records)} records in {indexing_time:.2f} seconds")
            print(f"  📊 Indexing rate: {indexing_rate:.1f} records/second")
            
            # Performance requirement: >1000 records/second
            assert indexing_rate >= 1000, f"Indexing too slow: {indexing_rate:.1f} records/sec"
            
            # Verify indexed data
            record_count = search_db.get_record_count()
            assert record_count == len(test_records), f"Expected {len(test_records)}, indexed {record_count}"
            
            search_db.close()
    
    @pytest.mark.performance  
    def test_incremental_indexing_performance(self):
        """Test incremental indexing performance."""
        with patch.dict('os.environ', self.test_env):
            config = Config()
            archive_writer = ArchiveWriter(config.archive_dir)
            search_db = SearchDatabase(config.data_dir / "incremental_perf.db")
            indexer = ArchiveIndexer(search_db, config.archive_dir)
            
            data_generator = LargeDatasetGenerator()
            
            # Initial batch
            initial_records = list(data_generator.generate_slack_messages(2000))
            print(f"📝 Initial batch: {len(initial_records)} records")
            
            for record in initial_records:
                archive_writer.write_record("incremental_perf", record)
            
            # Initial indexing
            start_time = time.time()
            indexer.index_directory(config.archive_dir)
            initial_time = time.time() - start_time
            initial_rate = len(initial_records) / initial_time
            
            print(f"  Initial indexing: {initial_rate:.1f} records/sec")
            
            # Incremental batch
            incremental_records = list(data_generator.generate_slack_messages(1000))
            print(f"📝 Incremental batch: {len(incremental_records)} records")
            
            for record in incremental_records:
                archive_writer.write_record("incremental_perf", record)
            
            # Incremental indexing
            start_time = time.time()
            indexer.index_directory(config.archive_dir)
            incremental_time = time.time() - start_time
            incremental_rate = len(incremental_records) / incremental_time if incremental_time > 0 else float('inf')
            
            print(f"  Incremental indexing: {incremental_rate:.1f} records/sec")
            
            # Incremental should be faster (only processing new records)
            assert incremental_rate >= initial_rate * 0.8, "Incremental indexing should be efficient"
            
            # Verify total records
            total_expected = len(initial_records) + len(incremental_records)
            total_indexed = search_db.get_record_count()
            assert total_indexed == total_expected, f"Expected {total_expected}, got {total_indexed}"
            
            search_db.close()


class TestCompressionPerformance:
    """Test compression performance and ratios."""
    
    def setup_method(self):
        """Set up compression performance tests."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_env = {
            "AICOS_BASE_DIR": self.temp_dir,
            "AICOS_TEST_MODE": "true"
        }
    
    @pytest.mark.performance
    def test_compression_ratio_target(self):
        """Test compression achieves 70% size reduction target."""
        with patch.dict('os.environ', self.test_env):
            config = Config()
            archive_writer = ArchiveWriter(config.archive_dir)
            compressor = Compressor()
            
            # Generate test data
            data_generator = LargeDatasetGenerator()
            test_records = list(data_generator.generate_slack_messages(2000))
            
            # Archive test data
            for record in test_records:
                archive_writer.write_record("compression_test", record)
            
            # Find JSONL files to compress
            test_dir = config.archive_dir / "compression_test"
            jsonl_files = []
            for daily_dir in test_dir.iterdir():
                if daily_dir.is_dir():
                    jsonl_files.extend(daily_dir.glob("*.jsonl"))
            
            assert len(jsonl_files) > 0, "Should have JSONL files to compress"
            
            print(f"🗜️  Testing compression on {len(jsonl_files)} files...")
            
            total_original_size = 0
            total_compressed_size = 0
            compression_times = []
            
            for jsonl_file in jsonl_files:
                original_size = jsonl_file.stat().st_size
                total_original_size += original_size
                
                # Compress file
                start_time = time.time()
                compressed_file = compressor.compress_file(jsonl_file)
                compression_time = time.time() - start_time
                compression_times.append(compression_time)
                
                compressed_size = compressed_file.stat().st_size
                total_compressed_size += compressed_size
                
                file_ratio = (original_size - compressed_size) / original_size * 100
                print(f"  {jsonl_file.name}: {original_size:,} → {compressed_size:,} bytes ({file_ratio:.1f}% reduction)")
            
            # Calculate overall compression ratio
            overall_ratio = (total_original_size - total_compressed_size) / total_original_size * 100
            avg_compression_time = sum(compression_times) / len(compression_times)
            
            print(f"  📊 Overall compression: {total_original_size:,} → {total_compressed_size:,} bytes")
            print(f"  📊 Compression ratio: {overall_ratio:.1f}% reduction")
            print(f"  📊 Average compression time: {avg_compression_time:.3f} seconds/file")
            
            # Performance requirements
            assert overall_ratio >= 70.0, f"Compression ratio too low: {overall_ratio:.1f}%"
            assert avg_compression_time < 5.0, f"Compression too slow: {avg_compression_time:.3f}s/file"
    
    @pytest.mark.performance
    def test_decompression_performance(self):
        """Test decompression performance for search operations."""
        with patch.dict('os.environ', self.test_env):
            config = Config()
            archive_writer = ArchiveWriter(config.archive_dir)
            compressor = Compressor()
            
            # Create and compress test data
            test_data = [{"id": i, "content": f"Test content {i} " * 50} for i in range(1000)]
            
            test_file = Path(self.temp_dir) / "test_data.jsonl"
            with open(test_file, 'w') as f:
                for record in test_data:
                    f.write(json.dumps(record) + '\n')
            
            # Compress file
            compressed_file = compressor.compress_file(test_file)
            
            # Test decompression performance
            print("📖 Testing decompression performance...")
            
            decompression_times = []
            for _ in range(10):  # Multiple runs for average
                start_time = time.time()
                
                # Decompress and read data
                with gzip.open(compressed_file, 'rt') as f:
                    decompressed_records = [json.loads(line) for line in f]
                
                decompression_time = time.time() - start_time
                decompression_times.append(decompression_time)
            
            avg_decompression_time = sum(decompression_times) / len(decompression_times)
            decompression_rate = len(test_data) / avg_decompression_time
            
            print(f"  📊 Average decompression time: {avg_decompression_time:.3f} seconds")
            print(f"  📊 Decompression rate: {decompression_rate:.1f} records/second")
            
            # Verify data integrity
            assert len(decompressed_records) == len(test_data), "Data loss during decompression"
            assert decompressed_records == test_data, "Data corruption during decompression"
            
            # Performance requirement: fast enough for search
            assert avg_decompression_time < 1.0, f"Decompression too slow: {avg_decompression_time:.3f}s"


class TestMemoryPerformance:
    """Test memory usage and leak detection."""
    
    def setup_method(self):
        """Set up memory performance tests."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_env = {
            "AICOS_BASE_DIR": self.temp_dir,
            "AICOS_TEST_MODE": "true"
        }
    
    @pytest.mark.performance
    def test_memory_usage_under_load(self):
        """Test memory usage stays under 500MB during normal operations."""
        with patch.dict('os.environ', self.test_env):
            config = Config()
            
            # Monitor memory usage
            memory_tracker = MemoryTracker()
            memory_tracker.start()
            
            print("🧠 Testing memory usage under load...")
            
            # Simulate realistic workload
            archive_writer = ArchiveWriter(config.archive_dir)
            search_db = SearchDatabase(config.data_dir / "memory_test.db")
            indexer = ArchiveIndexer(search_db, config.archive_dir)
            
            # Generate and process data
            data_generator = LargeDatasetGenerator()
            
            for batch in range(5):  # Process in batches
                print(f"  Processing batch {batch + 1}/5...")
                
                # Generate batch data
                batch_records = list(data_generator.generate_slack_messages(1000))
                
                # Archive batch
                for record in batch_records:
                    archive_writer.write_record("memory_test", record)
                
                # Index batch
                indexer.index_directory(config.archive_dir)
                
                # Perform searches
                for _ in range(10):
                    results = search_db.search("test")
                
                # Check memory usage
                current_memory = memory_tracker.get_current_usage_mb()
                print(f"    Memory usage: {current_memory:.1f} MB")
                
                # Memory requirement: <500MB
                assert current_memory < 500, f"Memory usage too high: {current_memory:.1f} MB"
            
            peak_memory = memory_tracker.get_peak_usage_mb()
            print(f"  📊 Peak memory usage: {peak_memory:.1f} MB")
            
            memory_tracker.stop()
            search_db.close()
    
    @pytest.mark.performance
    @pytest.mark.slow
    def test_memory_leak_detection(self):
        """Test for memory leaks during long-running operations."""
        with patch.dict('os.environ', self.test_env):
            config = Config()
            
            print("🔍 Testing for memory leaks...")
            
            initial_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
            print(f"  Initial memory: {initial_memory:.1f} MB")
            
            # Perform repetitive operations
            for cycle in range(20):
                # Create and close components repeatedly
                search_db = SearchDatabase(config.data_dir / f"leak_test_{cycle}.db")
                archive_writer = ArchiveWriter(config.archive_dir)
                state_mgr = StateManager(config.state_dir / f"leak_test_{cycle}.db")
                
                # Perform operations
                test_record = {"id": cycle, "data": f"cycle_{cycle}"}
                archive_writer.write_record("leak_test", test_record)
                state_mgr.set_state(f"test_{cycle}", {"cycle": cycle})
                
                # Cleanup
                search_db.close()
                state_mgr.close()
                del search_db, archive_writer, state_mgr
                
                if cycle % 5 == 0:
                    current_memory = psutil.Process().memory_info().rss / 1024 / 1024
                    memory_growth = current_memory - initial_memory
                    print(f"    Cycle {cycle}: {current_memory:.1f} MB (growth: {memory_growth:.1f} MB)")
                    
                    # Memory leak threshold: <50MB growth over 20 cycles
                    assert memory_growth < 50, f"Potential memory leak: {memory_growth:.1f} MB growth"
            
            final_memory = psutil.Process().memory_info().rss / 1024 / 1024
            total_growth = final_memory - initial_memory
            
            print(f"  📊 Final memory: {final_memory:.1f} MB")
            print(f"  📊 Total growth: {total_growth:.1f} MB")
            
            assert total_growth < 50, f"Memory leak detected: {total_growth:.1f} MB growth"


if __name__ == "__main__":
    # Run performance tests
    pytest.main([
        __file__,
        "-v",
        "-m", "performance",
        "--tb=short",
        "--benchmark-columns=min,max,mean,median,stddev",
        "--benchmark-sort=name"
    ])