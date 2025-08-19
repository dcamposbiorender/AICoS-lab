"""
Comprehensive integration tests for the AI Chief of Staff data pipeline.

Tests complete data flow:
- Collection → Archive → Index → Search
- Multi-source coordination (Slack + Calendar + Drive)
- State persistence across components
- End-to-end query processing
"""

import pytest
import tempfile
import json
import time
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

# Import components under test
import sys
sys.path.insert(0, '/Users/david.campos/VibeCode/AICoS-Lab')

from src.core.config import Config
from src.core.state import StateManager
from src.core.archive_writer import ArchiveWriter
from src.collectors.base import BaseArchiveCollector
from src.search.database import SearchDatabase
from src.search.indexer import ArchiveIndexer
from src.intelligence.query_engine import QueryEngine


class TestDataPipelineIntegration:
    """Test complete data pipeline from collection to search."""
    
    def setup_method(self):
        """Set up integration test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_env = {
            "AICOS_BASE_DIR": self.temp_dir,
            "AICOS_TEST_MODE": "true"
        }
        
    def teardown_method(self):
        """Clean up integration tests."""
        import shutil
        if hasattr(self, 'temp_dir') and Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)
    
    @pytest.mark.integration
    @patch.dict('os.environ', {"AICOS_BASE_DIR": "/tmp/integration_test", "AICOS_TEST_MODE": "true"})
    def test_collection_to_archive_pipeline(self):
        """Collection → Archive pipeline works end-to-end."""
        # Create test collector
        collector = BaseArchiveCollector("integration_test")
        
        # Mock collected data
        collected_data = [
            {
                "id": "collect1",
                "type": "slack_message",
                "content": "alice: I'll finish the project by friday",
                "timestamp": "2025-08-18T10:00:00Z",
                "metadata": {"channel": "general", "user": "alice"}
            },
            {
                "id": "collect2", 
                "type": "calendar_event",
                "content": "Project review meeting",
                "timestamp": "2025-08-18T14:00:00Z",
                "metadata": {"attendees": ["alice", "bob"], "duration": 3600}
            }
        ]
        
        # Test collection to archive
        with patch.object(collector, 'archive_writer') as mock_writer:
            mock_writer.write_records = Mock()
            
            collector.write_to_archive(collected_data)
            
            # Verify archive writer called correctly
            mock_writer.write_records.assert_called_once_with(collected_data)
    
    @pytest.mark.integration
    def test_archive_to_search_pipeline(self):
        """Archive → Search indexing pipeline works."""
        # Create archive writer and search indexer
        archive_writer = ArchiveWriter("pipeline_test")
        search_indexer = ArchiveIndexer(str(Path(self.temp_dir) / "search_pipeline.db"))
        
        # Create test records
        test_records = [
            {
                "id": "archive1",
                "content": "project meeting with stakeholders",
                "source": "slack",
                "timestamp": "2025-08-18T10:00:00Z"
            },
            {
                "id": "archive2",
                "content": "budget discussion and planning session", 
                "source": "calendar",
                "timestamp": "2025-08-18T14:00:00Z"
            }
        ]
        
        # Write to archive
        with patch('src.core.archive_writer.get_config') as mock_config:
            mock_config.return_value.archive_dir = Path(self.temp_dir) / "archive"
            archive_writer.write_records(test_records)
        
        # Index from archive
        index_result = search_indexer.index_batch(test_records)
        
        assert index_result["indexed"] == 2
        assert index_result["errors"] == 0
        
        # Test search
        results = search_indexer.search("project meeting")
        assert len(results) >= 1
        assert any("project meeting" in r["content"] for r in results)
        
        search_indexer.close()
    
    @pytest.mark.integration
    def test_complete_query_processing_pipeline(self):
        """Complete pipeline: Query → Parse → Search → Aggregate → Results."""
        # Set up all components
        search_db = SearchDatabase(str(Path(self.temp_dir) / "complete_pipeline.db"))
        query_engine = QueryEngine()
        
        # Index test data
        test_data = [
            {"id": "q1", "content": "alice committed to finishing design by tuesday", "source": "slack"},
            {"id": "q2", "content": "project alpha budget meeting scheduled", "source": "calendar"},
            {"id": "q3", "content": "bob uploaded final specifications document", "source": "drive"},
            {"id": "q4", "content": "design review meeting with alice and charlie", "source": "calendar"}
        ]
        
        search_db.index_records_batch(test_data, source="test")
        
        # Test complete pipeline
        user_query = "what commitments did alice make about design"
        
        # 1. Parse query
        parsed = query_engine.parse_query(user_query)
        assert parsed.original_query == user_query
        
        # 2. Execute search
        search_results = search_db.search("alice design commitments")
        
        # 3. Verify results
        assert len(search_results) >= 1
        
        # Should find alice's design commitment
        alice_results = [r for r in search_results if "alice" in r["content"] and "design" in r["content"]]
        assert len(alice_results) >= 1
        
        search_db.close()


class TestMultiSourceIntegration:
    """Test integration across multiple data sources."""
    
    def setup_method(self):
        """Set up multi-source test environment."""
        self.temp_dir = tempfile.mkdtemp()
        
    @pytest.mark.integration
    def test_cross_source_data_correlation(self):
        """Data from different sources correlates correctly."""
        search_db = SearchDatabase(str(Path(self.temp_dir) / "multi_source.db"))
        
        # Index data from multiple sources
        multi_source_data = [
            {
                "id": "slack_msg_1",
                "content": "alice: I'll present the quarterly results at the board meeting",
                "source": "slack",
                "timestamp": "2025-08-15T09:00:00Z",
                "metadata": {"channel": "executives", "user": "alice"}
            },
            {
                "id": "cal_event_1", 
                "content": "Board Meeting Q3 Results Presentation",
                "source": "calendar",
                "timestamp": "2025-08-20T10:00:00Z",
                "metadata": {"attendees": ["alice", "board"], "location": "Conference Room A"}
            },
            {
                "id": "drive_doc_1",
                "content": "Q3_Results_Final.pptx uploaded by alice",
                "source": "drive",
                "timestamp": "2025-08-19T16:00:00Z", 
                "metadata": {"file_type": "presentation", "owner": "alice"}
            }
        ]
        
        search_db.index_records_batch(multi_source_data, source="multi_source")
        
        # Test cross-source search
        board_results = search_db.search("board meeting quarterly results alice")
        
        # Should find related content across all sources
        sources_found = set(r["source"] for r in board_results)
        assert len(sources_found) >= 2  # Should find content from multiple sources
        
        # Should identify the connection between commitment and event
        alice_content = [r for r in board_results if "alice" in r["content"]]
        assert len(alice_content) >= 2
        
        search_db.close()
    
    @pytest.mark.integration
    def test_state_coordination_across_collectors(self):
        """State management coordinates across multiple collectors."""
        # Create multiple collectors with shared state
        collectors = {}
        for source in ["slack", "calendar", "drive"]:
            collectors[source] = BaseArchiveCollector(source)
        
        # Test state isolation and sharing
        with patch('src.collectors.base.StateManager') as mock_state:
            mock_state_instance = Mock()
            mock_state.return_value = mock_state_instance
            
            # Each collector should manage its own state
            for source, collector in collectors.items():
                test_state = {"last_sync": f"2025-08-18T{source}:00:00Z", "cursor": f"{source}_cursor"}
                collector.save_state(test_state)
                
                # Verify state saved with source-specific key
                calls = mock_state_instance.set_state.call_args_list
                assert len(calls) >= 1
                
        # State should be isolated per collector
        assert len(mock_state_instance.set_state.call_args_list) == 3


class TestPerformanceIntegration:
    """Test integrated performance across the pipeline."""
    
    def setup_method(self):
        """Set up performance integration tests."""
        self.temp_dir = tempfile.mkdtemp()
        
    @pytest.mark.integration
    def test_end_to_end_performance(self):
        """Complete pipeline meets performance targets."""
        # Set up pipeline components
        search_db = SearchDatabase(str(Path(self.temp_dir) / "e2e_perf.db"))
        query_engine = QueryEngine()
        
        # Simulate realistic data volume
        documents = []
        for i in range(2000):  # Realistic daily volume
            documents.append({
                "id": f"e2e_doc_{i}",
                "content": f"Message {i} about project planning meeting discussion with team members analysis review",
                "source": ["slack", "calendar", "drive"][i % 3],
                "timestamp": f"2025-08-18T{i%24:02d}:{i%60:02d}:00Z",
                "metadata": {"user": ["alice", "bob", "charlie"][i % 3]}
            })
        
        # Test indexing performance
        start_time = time.time()
        result = search_db.index_records_batch(documents, source="performance_test")
        indexing_time = time.time() - start_time
        
        assert result["indexed"] == 2000
        indexing_rate = 2000 / indexing_time
        assert indexing_rate >= 1000, f"Indexing rate too slow: {indexing_rate:.1f} docs/sec"
        
        # Test query processing performance
        test_queries = [
            "find project planning discussions with alice",
            "show me meeting analysis from this week",
            "what team discussions happened about budget"
        ]
        
        for query in test_queries:
            # Parse query
            start_time = time.time()
            parsed = query_engine.parse_query(query)
            parse_time = time.time() - start_time
            
            # Search
            search_start = time.time()
            results = search_db.search(" ".join(parsed.keywords))
            search_time = time.time() - search_start
            
            total_time = parse_time + search_time
            
            # Performance targets
            assert parse_time < 0.1, f"Query parsing too slow: {parse_time:.3f}s"
            assert search_time < 1.0, f"Search too slow: {search_time:.3f}s"
            assert total_time < 1.1, f"Total query time too slow: {total_time:.3f}s"
            assert len(results) > 0
        
        search_db.close()


class TestErrorRecoveryIntegration:
    """Test error recovery across integrated components."""
    
    def setup_method(self):
        """Set up error recovery test environment."""
        self.temp_dir = tempfile.mkdtemp()
        
    @pytest.mark.integration
    def test_partial_failure_recovery(self):
        """Pipeline recovers from partial component failures."""
        # Set up components
        search_db = SearchDatabase(str(Path(self.temp_dir) / "recovery_test.db"))
        
        # Mix of valid and invalid documents
        mixed_documents = [
            {"id": "valid1", "content": "valid document one", "source": "test"},
            {"id": "invalid1", "content": None, "source": "test"},  # Invalid content
            {"id": "valid2", "content": "valid document two", "source": "test"},
            {"invalid_field": "missing_id", "content": "content without id", "source": "test"},  # Invalid structure
            {"id": "valid3", "content": "valid document three", "source": "test"}
        ]
        
        # Should handle partial failures gracefully
        result = search_db.index_records_batch(mixed_documents, source="recovery_test")
        
        # Should index valid documents, skip invalid ones
        assert result["indexed"] >= 3  # At least the valid ones
        assert result["errors"] >= 2   # At least the invalid ones
        
        # Valid documents should be searchable
        search_results = search_db.search("valid document")
        assert len(search_results) >= 3
        
        search_db.close()
    
    @pytest.mark.integration
    def test_state_recovery_after_interruption(self):
        """System recovers state after process interruption."""
        # Create initial state
        state_mgr = StateManager(Path(self.temp_dir) / "recovery_state.db")
        
        initial_state = {
            "collection_status": {
                "slack": {"last_cursor": "slack_123", "last_sync": "2025-08-18T10:00:00Z"},
                "calendar": {"sync_token": "cal_abc", "last_sync": "2025-08-18T10:00:00Z"}
            },
            "indexing_status": {
                "last_indexed": "2025-08-18T09:00:00Z", 
                "total_documents": 1500
            }
        }
        
        state_mgr.set_state("system_state", initial_state)
        state_mgr.close()
        
        # Simulate process restart
        new_state_mgr = StateManager(Path(self.temp_dir) / "recovery_state.db")
        recovered_state = new_state_mgr.get_state("system_state")
        
        # State should be fully recovered
        assert recovered_state == initial_state
        assert recovered_state["collection_status"]["slack"]["last_cursor"] == "slack_123"
        assert recovered_state["indexing_status"]["total_documents"] == 1500
        
        new_state_mgr.close()


class TestRealDataIntegration:
    """Test with realistic data volumes and patterns."""
    
    def setup_method(self):
        """Set up realistic data test environment."""
        self.temp_dir = tempfile.mkdtemp()
        
    @pytest.mark.integration
    def test_realistic_daily_data_volume(self):
        """Pipeline handles realistic daily data volumes."""
        search_db = SearchDatabase(str(Path(self.temp_dir) / "daily_volume.db"))
        
        # Simulate realistic daily volume
        daily_data = []
        
        # 200 Slack messages
        for i in range(200):
            daily_data.append({
                "id": f"slack_daily_{i}",
                "content": f"Daily slack message {i} about project work meeting discussion team collaboration",
                "source": "slack",
                "timestamp": f"2025-08-18T{i%24:02d}:{i%60:02d}:00Z",
                "metadata": {"channel": ["general", "project", "random"][i % 3], "user": ["alice", "bob", "charlie"][i % 3]}
            })
        
        # 50 Calendar events
        for i in range(50):
            daily_data.append({
                "id": f"calendar_daily_{i}",
                "content": f"Calendar event {i}: team meeting project review discussion",
                "source": "calendar", 
                "timestamp": f"2025-08-18T{(i%12)+8:02d}:00:00Z",
                "metadata": {"attendees": ["alice", "bob"], "duration": 3600}
            })
        
        # 30 Drive activities
        for i in range(30):
            daily_data.append({
                "id": f"drive_daily_{i}",
                "content": f"Document {i}: project_plan_v{i}.pdf updated",
                "source": "drive",
                "timestamp": f"2025-08-18T{(i%12)+8:02d}:30:00Z",
                "metadata": {"file_type": "pdf", "owner": ["alice", "bob"][i % 2]}
            })
        
        # Test complete processing
        start_time = time.time()
        result = search_db.index_records_batch(daily_data, source="daily_volume")
        processing_time = time.time() - start_time
        
        # Verify all data processed
        assert result["indexed"] == 280  # 200 + 50 + 30
        assert result["errors"] == 0
        
        # Performance: should process daily volume quickly
        docs_per_second = 280 / processing_time
        assert docs_per_second >= 500, f"Daily processing too slow: {docs_per_second:.1f} docs/sec"
        
        # Test search across all sources
        multi_source_results = search_db.search("project meeting")
        sources_found = set(r["source"] for r in multi_source_results)
        assert len(sources_found) >= 2  # Should find across multiple sources
        
        search_db.close()
    
    @pytest.mark.integration
    def test_weekly_data_accumulation(self):
        """System handles weekly data accumulation correctly."""
        search_db = SearchDatabase(str(Path(self.temp_dir) / "weekly_data.db"))
        
        # Simulate 7 days of data
        weekly_totals = {"indexed": 0, "errors": 0}
        
        for day in range(7):
            daily_data = []
            
            # Each day: 100 messages, 20 events, 10 files
            for i in range(130):
                daily_data.append({
                    "id": f"week_day{day}_item{i}",
                    "content": f"Day {day} item {i} content with project meeting discussion",
                    "source": ["slack", "calendar", "drive"][i % 3],
                    "timestamp": f"2025-08-{11+day:02d}T{i%24:02d}:00:00Z"
                })
            
            # Index daily batch
            result = search_db.index_records_batch(daily_data, source="weekly_data")
            weekly_totals["indexed"] += result["indexed"]
            weekly_totals["errors"] += result["errors"]
        
        # Verify weekly totals
        expected_total = 7 * 130  # 910 documents
        assert weekly_totals["indexed"] == expected_total
        assert weekly_totals["errors"] == 0
        
        # Test search performance with weekly data
        start_time = time.time()
        weekly_results = search_db.search("project meeting")
        search_time = time.time() - start_time
        
        assert search_time < 1.0, f"Weekly search too slow: {search_time:.3f}s"
        assert len(weekly_results) > 0
        
        # Test date range queries work with weekly data
        recent_results = search_db.search("project", date_range=("2025-08-15", "2025-08-25"))
        older_results = search_db.search("project", date_range=("2025-08-01", "2025-08-14"))
        
        assert len(recent_results) > len(older_results)  # More recent data
        
        search_db.close()


class TestDataConsistencyIntegration:
    """Test data consistency across pipeline stages."""
    
    def setup_method(self):
        """Set up consistency test environment."""
        self.temp_dir = tempfile.mkdtemp()
        
    @pytest.mark.integration
    def test_data_integrity_preservation(self):
        """Data integrity preserved through entire pipeline."""
        # Original data with specific structure
        original_data = [
            {
                "id": "integrity_test_1",
                "content": "Important meeting with precise timestamps and metadata",
                "source": "slack",
                "timestamp": "2025-08-18T14:30:45Z",
                "metadata": {
                    "channel": "project-alpha",
                    "user": "alice.smith",
                    "thread_ts": "1692364245.123456",
                    "reactions": [{"name": "thumbsup", "count": 3}]
                }
            }
        ]
        
        # Process through pipeline
        search_db = SearchDatabase(str(Path(self.temp_dir) / "integrity_test.db"))
        result = search_db.index_records_batch(original_data, source="integrity_test")
        
        assert result["indexed"] == 1
        assert result["errors"] == 0
        
        # Retrieve and verify data integrity
        search_results = search_db.search("important meeting")
        assert len(search_results) == 1
        
        retrieved = search_results[0]
        
        # Verify all original data preserved
        assert retrieved["id"] == "integrity_test_1"
        assert retrieved["content"] == "Important meeting with precise timestamps and metadata"
        assert retrieved["source"] == "slack"
        assert retrieved["timestamp"] == "2025-08-18T14:30:45Z"
        
        # Verify metadata preserved
        original_metadata = original_data[0]["metadata"]
        retrieved_metadata = json.loads(retrieved["metadata"]) if isinstance(retrieved["metadata"], str) else retrieved["metadata"]
        
        assert retrieved_metadata["channel"] == original_metadata["channel"]
        assert retrieved_metadata["user"] == original_metadata["user"]
        assert retrieved_metadata["thread_ts"] == original_metadata["thread_ts"]
        
        search_db.close()
    
    @pytest.mark.integration
    def test_timestamp_consistency(self):
        """Timestamps remain consistent across pipeline stages."""
        search_db = SearchDatabase(str(Path(self.temp_dir) / "timestamp_test.db"))
        
        # Create data with precise timestamps
        timestamp_data = []
        base_time = datetime.fromisoformat("2025-08-18T10:00:00")
        
        for i in range(100):
            event_time = base_time + timedelta(minutes=i)
            timestamp_data.append({
                "id": f"timestamp_{i}",
                "content": f"Event {i} at precise time",
                "source": "test",
                "timestamp": event_time.isoformat() + "Z"
            })
        
        # Index with timestamps
        search_db.index_records_batch(timestamp_data, source="timestamp_test")
        
        # Test timestamp-based queries
        recent_results = search_db.search("event", date_range=("2025-08-18", "2025-08-25"))
        early_results = search_db.search("event", date_range=("2025-08-01", "2025-08-17"))
        
        # Verify timestamp filtering works correctly
        assert len(recent_results) + len(early_results) <= 100  # Total shouldn't exceed input
        assert len(recent_results) > 0
        assert len(early_results) > 0
        
        # Verify timestamps preserved accurately
        for result in recent_results:
            result_time = datetime.fromisoformat(result["timestamp"].replace("Z", ""))
            cutoff_time = datetime.fromisoformat("2025-08-18T10:30:00")
            assert result_time >= cutoff_time
        
        search_db.close()


if __name__ == "__main__":
    # Run integration tests with coverage
    pytest.main([
        __file__,
        "-v",
        "--cov=../../src",
        "--cov-report=html:../reports/coverage/integration", 
        "--cov-report=term-missing"
    ])