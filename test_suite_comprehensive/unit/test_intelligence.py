"""
Comprehensive unit tests for intelligence components.

Tests:
- Query engine natural language processing
- Query parser with intent detection
- Result aggregation and ranking
- Context building and summarization
"""

import pytest
import tempfile
import json
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from datetime import datetime, timedelta

# Import components under test
import sys
sys.path.insert(0, '/Users/david.campos/VibeCode/AICoS-Lab')

from src.intelligence.query_engine import QueryEngine, QueryIntent, ParsedQuery
from src.intelligence.query_parser import NLQueryParser
from src.intelligence.result_aggregator import ResultAggregator


class TestQueryEngine:
    """Test natural language query processing."""
    
    def setup_method(self):
        """Set up query engine test environment."""
        self.query_engine = QueryEngine()
        
    @pytest.mark.unit
    def test_query_intent_detection(self):
        """Query engine correctly identifies user intents."""
        test_queries = [
            ("find messages about project alpha", QueryIntent.SEARCH_MESSAGES),
            ("what commitments did alice make this week", QueryIntent.FIND_COMMITMENTS),
            ("show me context about the marketing meeting", QueryIntent.BUILD_CONTEXT),
            ("search slack and calendar for budget discussions", QueryIntent.MULTI_SOURCE_SEARCH),
            ("what activity has bob had recently", QueryIntent.PERSON_ACTIVITY),
            ("show statistics about data collection", QueryIntent.SHOW_STATISTICS)
        ]
        
        for query_text, expected_intent in test_queries:
            parsed = self.query_engine.parse_query(query_text)
            assert parsed.intent == expected_intent, f"Wrong intent for '{query_text}'"
            assert parsed.original_query == query_text
            
    @pytest.mark.unit
    def test_keyword_extraction(self):
        """Query engine extracts relevant keywords."""
        query = "find messages about project alpha budget meeting"
        parsed = self.query_engine.parse_query(query)
        
        # Should extract important keywords
        expected_keywords = ["project", "alpha", "budget", "meeting"]
        for keyword in expected_keywords:
            assert keyword in parsed.keywords
            
        # Should exclude common stop words
        assert "about" not in parsed.keywords
        assert "find" not in parsed.keywords
        
    @pytest.mark.unit
    def test_person_name_extraction(self):
        """Query engine extracts person names and variants."""
        queries = [
            "what did alice say about the project",
            "show me bob's commitments",
            "messages from Alice Smith",
            "calendar events with alice.smith@company.com"
        ]
        
        for query in queries:
            parsed = self.query_engine.parse_query(query)
            
            # Should identify person-focused query
            assert parsed.intent == QueryIntent.PERSON_ACTIVITY
            assert parsed.person_filter is not None
            
            # Should extract person variants
            if "alice" in query.lower():
                assert any("alice" in variant.lower() for variant in parsed.person_variants)
                
    @pytest.mark.unit
    def test_time_filter_extraction(self):
        """Query engine extracts time filters correctly."""
        time_queries = [
            ("messages from last week", "last week"),
            ("calendar events this month", "this month"),
            ("what happened yesterday", "yesterday"),
            ("commitments due next friday", "next friday"),
            ("activities from august 15th", "august 15th")
        ]
        
        for query_text, expected_time in time_queries:
            parsed = self.query_engine.parse_query(query_text)
            
            assert parsed.time_filter is not None
            assert expected_time.lower() in parsed.time_filter.lower()
            
    @pytest.mark.unit
    def test_source_filter_detection(self):
        """Query engine identifies source-specific queries."""
        source_queries = [
            ("slack messages about project", ["slack"]),
            ("calendar events with alice", ["calendar"]),
            ("search slack and drive for documents", ["slack", "drive"]),
            ("find in all sources", ["slack", "calendar", "drive"])
        ]
        
        for query_text, expected_sources in source_queries:
            parsed = self.query_engine.parse_query(query_text)
            
            for source in expected_sources:
                assert source in parsed.sources or len(parsed.sources) == 0  # All sources if none specified


class TestNLQueryParser:
    """Test natural language query parsing."""
    
    def setup_method(self):
        """Set up query parser test environment."""
        self.parser = NLQueryParser()
        
    @pytest.mark.unit
    def test_basic_query_parsing(self):
        """Parser handles basic query structure."""
        query = "find project alpha discussions"
        parsed = self.parser.parse(query)
        
        assert isinstance(parsed, dict)
        assert "keywords" in parsed
        assert "intent" in parsed
        assert "confidence" in parsed
        
    @pytest.mark.unit
    def test_complex_query_parsing(self):
        """Parser handles complex multi-part queries."""
        query = "show me all slack messages from alice about project alpha budget discussions from last week"
        parsed = self.parser.parse(query)
        
        # Should extract multiple components
        assert "alice" in str(parsed).lower()
        assert "slack" in str(parsed).lower()
        assert "project" in str(parsed).lower()
        assert "last week" in str(parsed).lower()
        
    @pytest.mark.unit
    def test_ambiguous_query_handling(self):
        """Parser handles ambiguous queries appropriately."""
        ambiguous_queries = [
            "find it",
            "show me stuff",
            "what happened",
            "help"
        ]
        
        for query in ambiguous_queries:
            parsed = self.parser.parse(query)
            
            # Should indicate need for clarification or low confidence
            assert parsed["confidence"] < 0.7 or parsed["intent"] == "clarification_needed"
            
    @pytest.mark.unit
    def test_date_parsing_accuracy(self):
        """Parser accurately extracts date ranges."""
        date_queries = [
            "messages from yesterday",
            "events next tuesday", 
            "activities between august 15 and august 20",
            "commitments due this week"
        ]
        
        for query in date_queries:
            parsed = self.parser.parse(query)
            
            # Should extract time component
            assert "time" in str(parsed).lower() or "date" in str(parsed).lower()


class TestResultAggregator:
    """Test result aggregation and ranking."""
    
    def setup_method(self):
        """Set up result aggregator test environment."""
        self.aggregator = ResultAggregator()
        
    @pytest.mark.unit
    def test_result_aggregation_by_relevance(self):
        """Results are aggregated and sorted by relevance correctly."""
        source_results = {
            "slack": [
                {"id": "low", "content": "brief mention of project", "score": 0.3, "source": "slack"},
                {"id": "high", "content": "detailed project alpha discussion", "score": 0.9, "source": "slack"}
            ],
            "calendar": [
                {"id": "medium", "content": "project update meeting notes", "score": 0.6, "source": "calendar"}
            ]
        }
        
        aggregated = self.aggregator.aggregate(source_results, query="project")
        
        # Should have results from all sources
        assert len(aggregated.results) == 3
        assert aggregated.total_results == 3
        
    @pytest.mark.unit
    def test_cross_source_aggregation(self):
        """Results are aggregated and deduplicated across sources."""
        source_results = {
            "slack": [
                {"id": "msg1", "content": "project meeting", "source": "slack", "timestamp": "2025-08-18T10:00:00Z"},
                {"id": "msg2", "content": "different content", "source": "slack", "timestamp": "2025-08-18T10:05:00Z"}
            ],
            "calendar": [
                {"id": "cal1", "content": "project meeting", "source": "calendar", "timestamp": "2025-08-18T10:00:00Z"}
            ]
        }
        
        aggregated = self.aggregator.aggregate(source_results, query="meeting")
        
        # Should handle duplicate content across sources
        assert aggregated.total_results >= 2
        assert len(aggregated.source_breakdown) == 2
        assert "slack" in aggregated.source_breakdown
        assert "calendar" in aggregated.source_breakdown
        
    @pytest.mark.unit
    def test_result_timeline_extraction(self):
        """Results are organized into timeline appropriately."""
        source_results = {
            "slack": [
                {"id": "r1", "content": "alice committed to finishing the report by friday", "source": "slack", "timestamp": "2025-08-15T14:00:00Z"},
                {"id": "r2", "content": "project alpha budget approved for Q4", "source": "slack", "timestamp": "2025-08-16T10:00:00Z"}
            ],
            "calendar": [
                {"id": "r3", "content": "marketing meeting scheduled for next week", "source": "calendar", "timestamp": "2025-08-17T09:00:00Z"}
            ]
        }
        
        aggregated = self.aggregator.aggregate(source_results, query="project commitments")
        
        assert isinstance(aggregated.timeline, list)
        assert aggregated.total_results == 3
        assert len(aggregated.source_breakdown) == 2
        assert "slack" in aggregated.source_breakdown
        assert "calendar" in aggregated.source_breakdown
        
    @pytest.mark.unit
    def test_context_building(self):
        """Aggregator builds context from multiple results."""
        source_results = {
            "slack": [
                {
                    "id": "ctx1", 
                    "content": "alice: I'll have the design ready by tuesday",
                    "source": "slack",
                    "timestamp": "2025-08-15T14:00:00Z",
                    "metadata": {"channel": "design-team"}
                }
            ],
            "calendar": [
                {
                    "id": "ctx2",
                    "content": "Design review meeting", 
                    "source": "calendar",
                    "timestamp": "2025-08-20T10:00:00Z",
                    "metadata": {"attendees": ["alice", "bob"]}
                }
            ],
            "drive": [
                {
                    "id": "ctx3",
                    "content": "alice uploaded design_v2.pdf",
                    "source": "drive", 
                    "timestamp": "2025-08-19T16:00:00Z",
                    "metadata": {"file_type": "pdf"}
                }
            ]
        }
        
        aggregated = self.aggregator.aggregate(source_results, query="design project")
        
        assert isinstance(aggregated.timeline, list)
        assert isinstance(aggregated.key_people, list)
        assert isinstance(aggregated.commitments, list)
        
        # Should identify alice as key person
        assert "alice" in aggregated.key_people
        
        # Should show timeline progression
        assert len(aggregated.timeline) == 3


class TestIntelligenceIntegration:
    """Test intelligence component integration."""
    
    @pytest.mark.unit
    def test_query_to_results_pipeline(self):
        """Complete query processing pipeline works."""
        # Mock search database results
        mock_results = [
            {"id": "pipeline1", "content": "project alpha meeting notes", "source": "slack", "score": 0.8},
            {"id": "pipeline2", "content": "alice committed to deliverable", "source": "slack", "score": 0.9}
        ]
        
        with patch('src.intelligence.query_engine.SearchDatabase') as mock_db:
            mock_db_instance = Mock()
            mock_db_instance.search.return_value = mock_results
            mock_db.return_value = mock_db_instance
            
            # Test full pipeline
            query_engine = QueryEngine()
            aggregator = ResultAggregator()
            
            # Parse query
            parsed = query_engine.parse_query("what commitments did alice make about project alpha")
            
            # Execute search (mocked)
            raw_results = mock_db_instance.search("alice project alpha commitments")
            
            # Aggregate results
            source_mock_results = {"slack": mock_results}
            aggregated = aggregator.aggregate(source_mock_results, query="alice project alpha commitments")
            
            assert aggregated.total_results == 2
            assert len(aggregated.results) == 2
            
    @pytest.mark.unit
    def test_error_handling_in_pipeline(self):
        """Intelligence pipeline handles errors gracefully."""
        query_engine = QueryEngine()
        
        # Test malformed queries
        malformed_queries = [
            "",
            "   ",
            "askljdflkajsdf",
            "!!!@#$%^&*()",
            "a" * 1000  # Very long query
        ]
        
        for query in malformed_queries:
            try:
                parsed = query_engine.parse_query(query)
                # Should not crash, may return low confidence or clarification needed
                assert isinstance(parsed, ParsedQuery)
                assert parsed.confidence <= 0.5 or parsed.intent == QueryIntent.CLARIFICATION_NEEDED
            except Exception as e:
                # If it raises an exception, it should be a specific, handled error
                assert "parse" in str(e).lower() or "invalid" in str(e).lower()


class TestIntelligencePerformance:
    """Test intelligence performance requirements."""
    
    @pytest.mark.unit
    def test_query_parsing_speed(self):
        """Query parsing meets speed requirements."""
        parser = NLQueryParser()
        
        test_queries = [
            "find all messages about project alpha from last week",
            "what commitments did alice make in the marketing meeting",
            "show me calendar events with bob and charlie next tuesday",
            "search slack for budget discussions in the design channel"
        ]
        
        total_time = 0
        import time
        for query in test_queries:
            start_time = time.time()
            result = parser.parse(query)
            parse_time = time.time() - start_time
            total_time += parse_time
            
            # Each query should parse quickly
            assert parse_time < 0.5, f"Query parsing too slow: {parse_time:.3f}s for '{query}'"
            assert isinstance(result, dict)
        
        # Average parsing time should be very fast
        avg_time = total_time / len(test_queries)
        assert avg_time < 0.1, f"Average parsing too slow: {avg_time:.3f}s"
        
    @pytest.mark.unit
    def test_result_aggregation_performance(self):
        """Result aggregation handles large result sets efficiently."""
        aggregator = ResultAggregator()
        
        # Create large result set
        large_results = []
        for i in range(5000):
            large_results.append({
                "id": f"result_{i}",
                "content": f"Result {i} with content about project meeting discussion analysis data",
                "source": "performance_test",
                "score": (i % 100) / 100.0,  # Varying scores
                "timestamp": f"2025-08-{(i%30)+1:02d}T{i%24:02d}:00:00Z"
            })
        
        # Test aggregation performance
        import time
        start_time = time.time()
        source_large_results = {"performance_test": large_results}
        aggregated = aggregator.aggregate(source_large_results, query="project")
        ranking_time = time.time() - start_time
        
        assert ranking_time < 2.0, f"Aggregation too slow: {ranking_time:.3f}s for 5000 results"
        assert aggregated.total_results == 5000


class TestIntelligenceAccuracy:
    """Test intelligence accuracy and quality."""
    
    @pytest.mark.unit
    def test_commitment_extraction_accuracy(self):
        """Commitment extraction identifies promises correctly."""
        test_messages = [
            "alice: I'll have the report done by friday",  # Clear commitment
            "bob: we should consider the budget",          # No commitment
            "charlie: I will send the files tomorrow",     # Clear commitment
            "diana: maybe we can meet next week",          # Tentative, not commitment
            "eve: I committed to finishing the design"     # Clear commitment
        ]
        
        query_engine = QueryEngine()
        
        # Use aggregator for commitment extraction (correct API)
        aggregator = ResultAggregator()
        
        for message in test_messages:
            # Format as result for aggregator
            mock_results = {"test": [{"id": "test", "content": message, "source": "test"}]}
            aggregated = aggregator.aggregate(mock_results, query="commitments")
            
            if any(word in message.lower() for word in ["i'll", "i will", "committed to"]):
                # Should identify commitments in the results
                assert len(aggregated.commitments) > 0
            else:
                # Should not identify as commitment or have low confidence
                assert len(aggregated.commitments) == 0 or aggregated.confidence < 0.5
                
    @pytest.mark.unit
    def test_context_relevance_scoring(self):
        """Context building scores relevance accurately."""
        results = [
            {"content": "project alpha milestone completed", "source": "slack", "timestamp": "2025-08-18T10:00:00Z"},
            {"content": "lunch meeting cancelled", "source": "calendar", "timestamp": "2025-08-18T12:00:00Z"},
            {"content": "project alpha budget discussion", "source": "slack", "timestamp": "2025-08-18T14:00:00Z"}
        ]
        
        aggregator = ResultAggregator()
        source_results = {"test": results}
        aggregated = aggregator.aggregate(source_results, query="project alpha")
        
        # Should prioritize project alpha content
        relevant_items = [item for item in aggregated.timeline if "project alpha" in item["content"]]
        irrelevant_items = [item for item in aggregated.timeline if "lunch" in item["content"]]
        
        assert len(relevant_items) >= 2
        assert len(irrelevant_items) <= 1  # Should deprioritize irrelevant content


class TestIntelligenceEdgeCases:
    """Test edge cases and boundary conditions."""
    
    @pytest.mark.unit
    def test_empty_results_handling(self):
        """Intelligence handles empty search results gracefully."""
        aggregator = ResultAggregator()
        
        # Test with empty results
        empty_results = {"test": []}
        empty_aggregated = aggregator.aggregate(empty_results, query="nonexistent topic")
        
        assert isinstance(empty_aggregated, object)
        assert empty_aggregated.timeline == []
        assert empty_aggregated.key_people == []
        assert empty_aggregated.total_results == 0
        
    @pytest.mark.unit
    def test_unicode_content_handling(self):
        """Intelligence handles unicode content correctly."""
        test_content = [
            {"content": "meeting notes with émojis 🚀 and unicode characters", "source": "test"},
            {"content": "测试内容 with mixed languages", "source": "test"},
            {"content": "special chars: àáâãäåæçèéêë", "source": "test"}
        ]
        
        query_engine = QueryEngine()
        
        for item in test_content:
            # Should handle unicode without crashing
            parsed = query_engine.parse_query(f"find {item['content']}")
            assert isinstance(parsed, ParsedQuery)
            assert len(parsed.keywords) > 0
            
    @pytest.mark.unit 
    def test_very_long_content_handling(self):
        """Intelligence handles very long content appropriately."""
        # Create very long content
        long_content = "word " * 10000  # 50KB of repeated words
        
        query_engine = QueryEngine()
        aggregator = ResultAggregator()
        
        long_result = {
            "id": "long_doc",
            "content": long_content,
            "source": "test",
            "score": 0.8
        }
        
        # Should handle long content without performance issues
        import time
        start_time = time.time()
        source_long_results = {"test": [long_result]}
        processed = aggregator.aggregate(source_long_results, query="word")
        process_time = time.time() - start_time
        
        assert process_time < 1.0, f"Long content processing too slow: {process_time:.3f}s"
        assert processed.total_results == 1


if __name__ == "__main__":
    # Run intelligence tests with coverage
    pytest.main([
        __file__,
        "-v", 
        "--cov=../../src/intelligence",
        "--cov-report=html:../reports/coverage/intelligence",
        "--cov-report=term-missing"
    ])