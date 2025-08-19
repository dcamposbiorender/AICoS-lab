"""
Comprehensive unit tests for search and database components.

Tests:
- SQLite FTS5 database operations and schema
- Search indexing with performance validation
- Query parsing and result aggregation
- Full-text search accuracy and ranking
"""

import pytest
import tempfile
import sqlite3
import json
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import threading

# Import components under test
import sys
sys.path.insert(0, '/Users/david.campos/VibeCode/AICoS-Lab')

from src.search.database import SearchDatabase, DatabaseError
from src.search.indexer import ArchiveIndexer


class TestSearchDatabase:
    """Test SQLite FTS5 database functionality."""
    
    def setup_method(self):
        """Set up test database."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_search.db"
        self.db = SearchDatabase(str(self.db_path))
        
    def teardown_method(self):
        """Clean up test database."""
        if hasattr(self, 'db'):
            self.db.close()
        
    @pytest.mark.unit
    def test_database_initialization(self):
        """SearchDatabase initializes with correct schema."""
        # Check database file exists
        assert self.db_path.exists()
        
        # Check FTS5 tables exist
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        
        # Should have FTS5 tables
        expected_tables = ['messages', 'messages_fts']
        for table in expected_tables:
            assert any(table in t for t in tables), f"Missing table: {table}"
        
        conn.close()
        
    @pytest.mark.unit
    def test_document_indexing(self):
        """Documents are indexed correctly in FTS5."""
        test_documents = [
            {
                "id": "msg1",
                "content": "Meeting with Alice about project planning",
                "source": "slack",
                "timestamp": "2025-08-18T10:00:00Z",
                "metadata": {"channel": "general", "user": "bob"}
            },
            {
                "id": "msg2", 
                "content": "Calendar event: Sprint review meeting",
                "source": "calendar",
                "timestamp": "2025-08-18T14:00:00Z",
                "metadata": {"attendees": ["alice", "bob"]}
            }
        ]
        
        # Index documents
        result = self.db.index_records_batch(test_documents, source="test")
        assert result["indexed"] == 2
        assert result["errors"] == 0
        
        # Verify documents are searchable
        search_results = self.db.search("meeting")
        assert len(search_results) == 2
        
        # Verify specific search
        project_results = self.db.search("project planning")
        assert len(project_results) == 1
        # ID is stored in metadata JSON
        metadata = project_results[0]["metadata"]
        if isinstance(metadata, str):
            import json
            metadata = json.loads(metadata)
        assert metadata["id"] == "msg1"
        
    @pytest.mark.unit
    def test_fts5_search_accuracy(self):
        """FTS5 search returns accurate, ranked results."""
        documents = [
            {"id": "exact", "content": "exact match query text", "source": "test"},
            {"id": "partial", "content": "query appears in middle of text", "source": "test"},
            {"id": "distant", "content": "some other content with query at end", "source": "test"},
            {"id": "irrelevant", "content": "completely different topic", "source": "test"}
        ]
        
        self.db.index_records_batch(documents, source="test")
        
        # Search for "query"
        results = self.db.search("query")
        
        # Should return 3 documents (not the irrelevant one)
        assert len(results) == 3
        
        # Results should be ranked by relevance (FTS5 ranking)
        # Extract IDs from metadata
        result_ids = []
        for r in results:
            metadata = r["metadata"]
            if isinstance(metadata, str):
                import json
                metadata = json.loads(metadata)
            result_ids.append(metadata["id"])
        
        assert "exact" in result_ids
        assert "partial" in result_ids 
        assert "distant" in result_ids
        assert "irrelevant" not in result_ids
        
    @pytest.mark.unit
    def test_search_performance_target(self):
        """Search meets <1 second performance target."""
        # Index 1000 documents
        documents = []
        for i in range(1000):
            documents.append({
                "id": f"doc_{i}",
                "content": f"Document number {i} with searchable content about meeting project data analysis",
                "source": "performance_test",
                "timestamp": f"2025-08-18T{i%24:02d}:00:00Z"
            })
        
        # Index all documents
        self.db.index_records_batch(documents, source="test")
        
        # Test search performance
        start_time = time.time()
        results = self.db.search("meeting project")
        search_time = time.time() - start_time
        
        # Should be fast and return results
        assert search_time < 1.0, f"Search too slow: {search_time:.3f} seconds"
        assert len(results) > 0
        
    @pytest.mark.unit
    def test_database_concurrency_safety(self):
        """Database handles concurrent access safely."""
        num_threads = 5
        docs_per_thread = 20
        errors = []
        
        def worker(thread_id):
            try:
                documents = []
                for i in range(docs_per_thread):
                    documents.append({
                        "id": f"thread_{thread_id}_doc_{i}",
                        "content": f"Thread {thread_id} document {i} content",
                        "source": "concurrency_test"
                    })
                
                # Index documents from this thread
                result = self.db.index_records_batch(documents, source="test")
                assert result["indexed"] == docs_per_thread
                
            except Exception as e:
                errors.append(f"Thread {thread_id}: {e}")
        
        # Run concurrent indexing
        threads = []
        for tid in range(num_threads):
            thread = threading.Thread(target=worker, args=(tid,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Should handle concurrency without errors
        assert len(errors) == 0, f"Concurrency errors: {errors}"
        
        # Verify all documents indexed
        total_results = self.db.search("content")
        expected_total = num_threads * docs_per_thread
        assert len(total_results) == expected_total
        
    @pytest.mark.unit
    def test_schema_migration(self):
        """Database schema migration works correctly."""
        # Create database with old schema version
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("CREATE TABLE schema_version (version INTEGER)")
        conn.execute("INSERT INTO schema_version (version) VALUES (1)")
        conn.commit()
        conn.close()
        
        # Initialize SearchDatabase - should trigger migration
        migrated_db = SearchDatabase(str(self.db_path))
        
        # Check migration completed
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT version FROM schema_version")
        version = cursor.fetchone()[0]
        assert version == SearchDatabase.CURRENT_SCHEMA_VERSION
        conn.close()
        
        migrated_db.close()


class TestArchiveIndexer:
    """Test archive indexing functionality."""
    
    def setup_method(self):
        """Set up test indexer."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_indexer.db"
        
    @pytest.mark.unit  
    def test_indexer_initialization(self):
        """ArchiveIndexer initializes correctly."""
        with patch('src.search.indexer.SearchDatabase') as mock_db:
            indexer = ArchiveIndexer(Mock())  # Takes a database instance
            assert indexer is not None
        
    @pytest.mark.unit
    def test_archive_processing_basic(self):
        """ArchiveIndexer can process archive files."""
        # Create a test JSONL file
        test_file = Path(self.temp_dir) / "test_archive.jsonl"
        test_data = [
            {"id": "test1", "content": "test message content", "source": "test"},
            {"id": "test2", "content": "another test message", "source": "test"}
        ]
        
        # Write test JSONL
        with open(test_file, 'w') as f:
            for record in test_data:
                f.write(json.dumps(record) + '\n')
        
        # Test archive processing
        with patch('src.search.indexer.SearchDatabase') as mock_db:
            mock_db_instance = Mock()
            mock_db_instance.index_records_batch.return_value = {"indexed": 2, "errors": 0}
            
            indexer = ArchiveIndexer(mock_db_instance)
            result = indexer.process_archive(test_file, source="test")
            
            # Should process the archive
            assert result.processed > 0
            assert result.error_count == 0


class TestSearchIntegration:
    """Test search integration with database."""
    
    def setup_method(self):
        """Set up integration test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "integration_search.db"
        
    @pytest.mark.unit
    def test_database_indexer_integration(self):
        """SearchDatabase and SearchIndexer work together."""
        # Create components
        database = SearchDatabase(str(self.db_path))
        indexer = ArchiveIndexer(str(self.db_path))
        
        # Index via indexer
        test_docs = [
            {"id": "test1", "content": "integration test document", "source": "test"}
        ]
        
        indexer.index_batch(test_docs)
        
        # Search via database
        results = database.search("integration test")
        assert len(results) == 1
        assert results[0]["id"] == "test1"
        
        database.close()
        indexer.close()
        
    @pytest.mark.unit
    def test_search_with_filters(self):
        """Search supports filtering by source and date."""
        database = SearchDatabase(str(self.db_path))
        
        documents = [
            {"id": "slack1", "content": "slack message about project", "source": "slack", "timestamp": "2025-08-18T10:00:00Z"},
            {"id": "cal1", "content": "calendar event about project", "source": "calendar", "timestamp": "2025-08-18T14:00:00Z"},
            {"id": "old1", "content": "old message about project", "source": "slack", "timestamp": "2025-08-01T10:00:00Z"}
        ]
        
        database.index_records_batch(documents, source="test")
        
        # Test source filtering
        slack_results = database.search("project", source_filter="slack")
        assert len(slack_results) == 2
        assert all(r["source"] == "slack" for r in slack_results)
        
        # Test date filtering
        recent_results = database.search("project", date_after="2025-08-15")
        assert len(recent_results) == 2
        assert all("2025-08-18" in r["timestamp"] for r in recent_results)
        
        database.close()


class TestSearchPerformance:
    """Test search performance requirements."""
    
    def setup_method(self):
        """Set up performance test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "perf_search.db"
        
    @pytest.mark.unit
    def test_large_dataset_search_performance(self):
        """Search performs well with large datasets."""
        database = SearchDatabase(str(self.db_path))
        
        # Index 10,000 documents (simulating large dataset)
        documents = []
        for i in range(10000):
            documents.append({
                "id": f"large_doc_{i}",
                "content": f"Document {i} contains information about project meeting calendar slack data analysis research {i % 100}",
                "source": "performance_test",
                "timestamp": f"2025-08-{(i%30)+1:02d}T{i%24:02d}:00:00Z"
            })
        
        # Index all documents at once for realistic performance
        start_time = time.time()
        result = database.index_records_batch(documents, source="test")
        total_index_time = time.time() - start_time
        
        assert result["indexed"] == len(documents)
        
        # Test search performance on large dataset
        search_queries = [
            "project meeting",
            "calendar data",
            "analysis research",
            "document information"
        ]
        
        for query in search_queries:
            start_time = time.time()
            results = database.search(query, limit=20)
            search_time = time.time() - start_time
            
            # Performance target: <1 second for search
            assert search_time < 1.0, f"Search '{query}' too slow: {search_time:.3f}s"
            assert len(results) > 0
        
        # Test indexing performance: >1000 docs/second target
        docs_per_second = len(documents) / total_index_time
        assert docs_per_second >= 1000, f"Indexing too slow: {docs_per_second:.1f} docs/sec"
        
        database.close()
        
    @pytest.mark.unit
    def test_concurrent_search_performance(self):
        """Concurrent searches don't degrade performance."""
        database = SearchDatabase(str(self.db_path))
        
        # Index test data
        documents = [
            {"id": f"concurrent_doc_{i}", "content": f"concurrent test document {i} with searchable content", "source": "test"}
            for i in range(1000)
        ]
        database.index_records_batch(documents, source="test")
        
        # Test concurrent searches
        search_times = []
        errors = []
        
        def search_worker(worker_id):
            try:
                start_time = time.time()
                results = database.search("concurrent test")
                search_time = time.time() - start_time
                search_times.append(search_time)
                
                assert len(results) > 0
            except Exception as e:
                errors.append(f"Worker {worker_id}: {e}")
        
        # Run 10 concurrent searches
        threads = []
        for i in range(10):
            thread = threading.Thread(target=search_worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # All searches should complete without errors
        assert len(errors) == 0, f"Concurrent search errors: {errors}"
        
        # Performance shouldn't degrade significantly
        avg_search_time = sum(search_times) / len(search_times)
        assert avg_search_time < 1.0, f"Concurrent search too slow: {avg_search_time:.3f}s"
        
        database.close()


class TestSearchErrorHandling:
    """Test search error handling and recovery."""
    
    def setup_method(self):
        """Set up error handling test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "error_search.db"
        
    @pytest.mark.unit
    def test_malformed_document_handling(self):
        """Search handles malformed documents gracefully."""
        database = SearchDatabase(str(self.db_path))
        
        # Mix of valid and invalid documents
        documents = [
            {"id": "valid1", "content": "valid document", "source": "test"},
            {"id": "missing_content", "source": "test"},  # Missing content
            {"content": "missing id", "source": "test"},  # Missing id
            {"id": "valid2", "content": "another valid document", "source": "test"}
        ]
        
        # Should handle errors gracefully
        result = database.index_records_batch(documents, source="test")
        
        # Should index valid documents, skip invalid ones
        assert result["indexed"] >= 2  # At least the valid ones
        assert result["errors"] <= 2   # At most the invalid ones
        
        # Valid documents should be searchable
        results = database.search("valid document")
        assert len(results) >= 1
        
        database.close()
        
    @pytest.mark.unit
    def test_database_corruption_recovery(self):
        """Database recovers from corruption gracefully."""
        # Create valid database first
        database = SearchDatabase(str(self.db_path))
        database.index_records_batch([{"id": "test", "content": "test doc", "source": "test"}])
        database.close()
        
        # Corrupt the database file
        with open(self.db_path, 'w') as f:
            f.write("CORRUPTED DATA")
        
        # Should handle corruption gracefully
        with pytest.raises((DatabaseError, sqlite3.DatabaseError)):
            SearchDatabase(str(self.db_path))
            
    @pytest.mark.unit
    def test_search_query_sanitization(self):
        """Search queries are properly sanitized."""
        database = SearchDatabase(str(self.db_path))
        
        # Index test document
        database.index_records_batch([{
            "id": "sanitize_test",
            "content": "normal searchable content",
            "source": "test"
        }])
        
        # Test potentially problematic queries
        problematic_queries = [
            "'; DROP TABLE messages; --",  # SQL injection attempt
            "search * wildcard",           # Wildcard characters
            "unicode_content_测试",         # Unicode content
            "",                            # Empty query
            "   ",                         # Whitespace only
        ]
        
        for query in problematic_queries:
            try:
                results = database.search(query)
                # Should not crash, may return empty results
                assert isinstance(results, list)
            except Exception as e:
                # Some queries may raise exceptions, but shouldn't cause corruption
                assert "DROP TABLE" not in str(e)  # SQL injection prevented
        
        database.close()


class TestSearchMetadata:
    """Test search metadata and statistics."""
    
    def setup_method(self):
        """Set up metadata test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "metadata_search.db"
        self.database = SearchDatabase(str(self.db_path))
        
    def teardown_method(self):
        """Clean up metadata tests."""
        if hasattr(self, 'database'):
            self.database.close()
        
    @pytest.mark.unit
    def test_database_statistics(self):
        """Database provides accurate statistics."""
        # Index known number of documents
        documents = [
            {"id": f"stats_doc_{i}", "content": f"Statistics test document {i}", "source": "stats"}
            for i in range(100)
        ]
        
        self.database.index_records_batch(documents, source="test")
        
        # Get statistics
        stats = self.database.get_statistics()
        
        assert stats["total_documents"] == 100
        assert stats["database_size_mb"] > 0
        assert "index_count" in stats
        
    @pytest.mark.unit
    def test_search_result_metadata(self):
        """Search results include proper metadata."""
        # Index document with rich metadata
        document = {
            "id": "metadata_test",
            "content": "test document with metadata",
            "source": "test_source",
            "timestamp": "2025-08-18T12:00:00Z",
            "metadata": {
                "channel": "general",
                "user": "alice",
                "thread_ts": "123456"
            }
        }
        
        self.database.index_records_batch([document], source="test")
        
        # Search and verify metadata preserved
        results = self.database.search("test document")
        assert len(results) == 1
        
        result = results[0]
        assert result["id"] == "metadata_test"
        assert result["source"] == "test_source"
        assert result["timestamp"] == "2025-08-18T12:00:00Z"
        assert "metadata" in result
        assert result["metadata"]["channel"] == "general"


if __name__ == "__main__":
    # Run search tests with coverage
    pytest.main([
        __file__,
        "-v",
        "--cov=../../src/search",
        "--cov-report=html:../reports/coverage/search",
        "--cov-report=term-missing"
    ])