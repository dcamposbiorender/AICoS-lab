"""
Test suite for Result Aggregator module
Tests multi-source result processing, intelligence extraction, and context generation
References: Team A search results format, intelligence patterns from tasks_C.md
"""

import pytest
from datetime import datetime, timedelta
from typing import Dict, List, Any
import json
from src.intelligence.result_aggregator import ResultAggregator, AggregatedResult


class TestResultAggregator:
    """Test result aggregation and intelligence features"""
    
    @pytest.fixture
    def aggregator(self):
        """Create ResultAggregator instance for testing"""
        return ResultAggregator()
    
    @pytest.fixture
    def sample_results(self):
        """Sample results from different sources for testing"""
        return {
            'slack': [
                {
                    'content': 'Project Alpha deadline moved to Friday',
                    'source': 'slack',
                    'date': '2025-08-15',
                    'metadata': {'user': 'alice', 'channel': 'general'},
                    'relevance_score': 0.9
                },
                {
                    'content': 'Alpha project update: 80% complete',
                    'source': 'slack', 
                    'date': '2025-08-14',
                    'metadata': {'user': 'bob', 'channel': 'dev'},
                    'relevance_score': 0.7
                }
            ],
            'calendar': [
                {
                    'content': 'Project Alpha Review Meeting',
                    'source': 'calendar',
                    'date': '2025-08-16',
                    'metadata': {'attendees': ['alice', 'bob', 'charlie'], 'duration': 60},
                    'relevance_score': 0.8
                }
            ]
        }
    
    @pytest.fixture
    def commitment_results(self):
        """Sample results with various commitment patterns"""
        return {
            'slack': [
                {
                    'content': 'I will finish the report by tomorrow',
                    'source': 'slack',
                    'date': '2025-08-15',
                    'metadata': {'user': 'alice'},
                    'relevance_score': 0.8
                },
                {
                    'content': 'Bob agreed to review the code before Friday',
                    'source': 'slack',
                    'date': '2025-08-15', 
                    'metadata': {'user': 'charlie'},
                    'relevance_score': 0.9
                },
                {
                    'content': 'TODO: Update documentation for new API endpoints',
                    'source': 'slack',
                    'date': '2025-08-15',
                    'metadata': {'user': 'david'},
                    'relevance_score': 0.6
                },
                {
                    'content': 'Sarah is responsible for testing the deployment pipeline',
                    'source': 'slack',
                    'date': '2025-08-14',
                    'metadata': {'user': 'manager'},
                    'relevance_score': 0.7
                }
            ]
        }
    
    @pytest.fixture
    def duplicate_results(self):
        """Sample results with duplicates for testing deduplication"""
        return {
            'slack': [
                {
                    'content': 'Meeting at 2pm today',
                    'source': 'slack',
                    'date': '2025-08-15',
                    'metadata': {'user': 'alice'},
                    'relevance_score': 0.9
                },
                {
                    'content': 'Meeting today at 2pm',  # Very similar
                    'source': 'slack',
                    'date': '2025-08-15',
                    'metadata': {'user': 'bob'},
                    'relevance_score': 0.8
                },
                {
                    'content': 'Different topic entirely about budget planning',
                    'source': 'slack',
                    'date': '2025-08-15',
                    'metadata': {'user': 'charlie'},
                    'relevance_score': 0.5
                }
            ]
        }

    def test_basic_aggregation(self, aggregator, sample_results):
        """Test basic aggregation from multiple sources"""
        aggregated = aggregator.aggregate(sample_results, query="Project Alpha")
        
        assert len(aggregated.results) == 3
        assert aggregated.total_sources == 2
        assert 'slack' in aggregated.source_breakdown
        assert 'calendar' in aggregated.source_breakdown
        assert aggregated.source_breakdown['slack'] == 2
        assert aggregated.source_breakdown['calendar'] == 1
    
    def test_relevance_ranking(self, aggregator, sample_results):
        """Test results ranked by relevance score"""
        aggregated = aggregator.aggregate(sample_results, query="Project Alpha")
        
        scores = [r['relevance_score'] for r in aggregated.results]
        assert scores == sorted(scores, reverse=True)  # Descending order
        assert scores[0] > scores[1] > scores[2]  # Properly ranked highest to lowest
    
    def test_timeline_extraction(self, aggregator, sample_results):
        """Test timeline extraction from chronological results"""
        aggregated = aggregator.aggregate(sample_results, query="Project Alpha")
        timeline = aggregated.timeline
        
        assert len(timeline) == 3
        # Should be in chronological order
        dates = [event['date'] for event in timeline]
        assert dates == sorted(dates)
        
        # Verify timeline structure
        for event in timeline:
            assert 'date' in event
            assert 'content' in event
            assert 'source' in event
            assert 'metadata' in event
    
    def test_commitment_detection(self, aggregator, commitment_results):
        """Test detection of commitments and action items"""
        aggregated = aggregator.aggregate(commitment_results, query="commitments")
        
        assert len(aggregated.commitments) >= 3  # At least 3 different commitment patterns
        
        # Check for specific commitment patterns
        commitment_texts = [c['text'] for c in aggregated.commitments]
        
        # Should detect "I will" pattern
        assert any('I will finish' in text for text in commitment_texts)
        
        # Should detect "agreed to" pattern  
        assert any('agreed to review' in text for text in commitment_texts)
        
        # Should detect TODO pattern
        assert any('TODO:' in text for text in commitment_texts)
        
        # Verify commitment structure
        for commitment in aggregated.commitments:
            assert 'text' in commitment
            assert 'person' in commitment
            assert 'commitment' in commitment
            assert 'source' in commitment
            assert 'date' in commitment
            assert 'confidence' in commitment
            assert 0.0 <= commitment['confidence'] <= 1.0
    
    def test_context_summary_generation(self, aggregator, sample_results):
        """Test generation of context summary from aggregated results"""
        aggregated = aggregator.aggregate(sample_results, query="Project Alpha")
        summary = aggregated.context_summary
        
        assert isinstance(summary, str)
        assert 'Project Alpha' in summary
        assert 'deadline' in summary.lower()
        assert 'Friday' in summary
        assert len(summary.split('.')) >= 2  # Multiple sentences
        
        # Should mention result count
        assert '3 results' in summary
        
        # Should mention sources
        assert 'slack' in summary.lower() or 'calendar' in summary.lower()
    
    def test_duplicate_detection(self, aggregator, duplicate_results):
        """Test detection and removal of duplicate or similar results"""
        aggregated = aggregator.aggregate(duplicate_results, query="meeting")
        
        # Should deduplicate similar results
        assert len(aggregated.results) == 2  # One duplicate removed
        assert aggregated.duplicates_removed == 1
        
        # Should keep the higher relevance result
        meeting_results = [r for r in aggregated.results if 'Meeting' in r['content']]
        assert len(meeting_results) == 1
        assert meeting_results[0]['relevance_score'] == 0.9  # Higher score kept
    
    def test_key_people_extraction(self, aggregator, sample_results):
        """Test extraction of key people from results"""
        aggregated = aggregator.aggregate(sample_results, query="Project Alpha")
        
        assert len(aggregated.key_people) >= 3
        assert 'alice' in aggregated.key_people
        assert 'bob' in aggregated.key_people
        assert 'charlie' in aggregated.key_people
    
    def test_key_topics_extraction(self, aggregator, sample_results):
        """Test extraction of key topics from results"""
        aggregated = aggregator.aggregate(sample_results, query="Project Alpha")
        
        # Should extract meaningful topics, excluding query terms
        assert len(aggregated.key_topics) > 0
        
        # Should not include query terms
        assert 'Project' not in aggregated.key_topics
        assert 'Alpha' not in aggregated.key_topics
        
        # Should include relevant topics
        topic_str = ' '.join(aggregated.key_topics).lower()
        assert any(word in topic_str for word in ['deadline', 'complete', 'meeting', 'review'])
    
    def test_confidence_scoring(self, aggregator, sample_results):
        """Test confidence score calculation"""
        aggregated = aggregator.aggregate(sample_results, query="Project Alpha")
        
        assert 0.0 <= aggregated.confidence_score <= 1.0
        
        # Should have reasonable confidence with multiple sources and results
        assert aggregated.confidence_score >= 0.5
    
    def test_empty_results(self, aggregator):
        """Test handling of empty results"""
        aggregated = aggregator.aggregate({}, query="nothing")
        
        assert len(aggregated.results) == 0
        assert aggregated.total_sources == 0
        assert len(aggregated.timeline) == 0
        assert len(aggregated.commitments) == 0
        assert len(aggregated.key_people) == 0
        assert len(aggregated.key_topics) == 0
        assert "No results found" in aggregated.context_summary
        assert aggregated.confidence_score == 0.0
    
    def test_max_results_limiting(self, aggregator):
        """Test limiting of results when max_results is specified"""
        # Create many results
        large_results = {
            'slack': [
                {
                    'content': f'Message {i} content',
                    'source': 'slack',
                    'date': '2025-08-15',
                    'metadata': {'user': f'user{i}'},
                    'relevance_score': 0.5 + (i % 10) * 0.05  # Varying scores
                }
                for i in range(100)
            ]
        }
        
        aggregated = aggregator.aggregate(large_results, query="messages", max_results=10)
        
        assert len(aggregated.results) == 10
        # Should keep highest scoring results
        scores = [r['relevance_score'] for r in aggregated.results]
        assert all(score >= 0.9 for score in scores[:5])  # Top results have high scores
    
    def test_recency_boost_in_ranking(self, aggregator):
        """Test that recent results get ranking boost"""
        today = datetime.now().strftime('%Y-%m-%d')
        old_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        
        results = {
            'slack': [
                {
                    'content': 'Old message',
                    'source': 'slack',
                    'date': old_date,
                    'metadata': {'user': 'alice'},
                    'relevance_score': 0.8  # Higher base score
                },
                {
                    'content': 'Recent message',
                    'source': 'slack',
                    'date': today,
                    'metadata': {'user': 'bob'},
                    'relevance_score': 0.6  # Lower base score but recent
                }
            ]
        }
        
        aggregated = aggregator.aggregate(results, query="message")
        
        # Recent message should rank higher due to recency boost
        assert aggregated.results[0]['content'] == 'Recent message'
    
    def test_aggregation_strategies(self, aggregator, sample_results):
        """Test different aggregation strategies"""
        # Test chronological strategy
        aggregated_chrono = aggregator.aggregate(
            sample_results, 
            query="Project Alpha",
            strategy="chronological"
        )
        
        # Results should be in chronological order
        dates = [r['date'] for r in aggregated_chrono.results]
        assert dates == sorted(dates)
        
        # Test relevance strategy (default)
        aggregated_relevance = aggregator.aggregate(
            sample_results,
            query="Project Alpha",
            strategy="relevance"
        )
        
        # Should be different from chronological order
        relevance_dates = [r['date'] for r in aggregated_relevance.results]
        assert relevance_dates != dates
    
    def test_source_grouping_strategy(self, aggregator, sample_results):
        """Test source-grouped aggregation strategy"""
        aggregated = aggregator.aggregate(
            sample_results,
            query="Project Alpha", 
            strategy="source_grouped"
        )
        
        # Should group results by source
        sources_in_order = [r['source'] for r in aggregated.results]
        
        # All slack results should come before calendar results (or vice versa)
        slack_positions = [i for i, src in enumerate(sources_in_order) if src == 'slack']
        calendar_positions = [i for i, src in enumerate(sources_in_order) if src == 'calendar']
        
        # Should be grouped together
        assert max(slack_positions) < min(calendar_positions) or max(calendar_positions) < min(slack_positions)
    
    def test_commitment_confidence_levels(self, aggregator, commitment_results):
        """Test that different commitment patterns have different confidence levels"""
        aggregated = aggregator.aggregate(commitment_results, query="commitments")
        
        commitments = aggregated.commitments
        
        # "I will" commitments should have high confidence
        i_will_commitments = [c for c in commitments if 'I will' in c['text']]
        assert len(i_will_commitments) > 0
        assert all(c['confidence'] >= 0.8 for c in i_will_commitments)
        
        # TODO items should have medium confidence
        todo_commitments = [c for c in commitments if 'TODO' in c['text']]
        assert len(todo_commitments) > 0
        assert all(0.5 <= c['confidence'] <= 0.7 for c in todo_commitments)
    
    def test_metadata_preservation(self, aggregator, sample_results):
        """Test that metadata is preserved through aggregation"""
        aggregated = aggregator.aggregate(sample_results, query="Project Alpha")
        
        # Should preserve original metadata
        for result in aggregated.results:
            assert 'metadata' in result
            original_metadata = result['metadata']
            
            if result['source'] == 'slack':
                assert 'user' in original_metadata
                assert 'channel' in original_metadata
            elif result['source'] == 'calendar':
                assert 'attendees' in original_metadata
                assert 'duration' in original_metadata
    
    def test_query_boost_in_ranking(self, aggregator):
        """Test that results matching query terms get ranking boost"""
        results = {
            'slack': [
                {
                    'content': 'Random content about something else',
                    'source': 'slack',
                    'date': '2025-08-15',
                    'metadata': {'user': 'alice'},
                    'relevance_score': 0.9  # Higher base score
                },
                {
                    'content': 'Meeting discussion with project details',
                    'source': 'slack',
                    'date': '2025-08-15',
                    'metadata': {'user': 'bob'},
                    'relevance_score': 0.5  # Lower base score but matches query
                }
            ]
        }
        
        aggregated = aggregator.aggregate(results, query="meeting project")
        
        # Result with query matches should rank higher
        assert aggregated.results[0]['content'] == 'Meeting discussion with project details'
    
    def test_date_range_in_summary(self, aggregator, sample_results):
        """Test that context summary includes date range information"""
        aggregated = aggregator.aggregate(sample_results, query="Project Alpha")
        summary = aggregated.context_summary
        
        # Should mention date range
        assert any(month in summary for month in ['August', 'Aug'])
        assert '14' in summary or '15' in summary or '16' in summary
    
    def test_aggregated_result_serialization(self, aggregator, sample_results):
        """Test that AggregatedResult can be serialized to JSON"""
        aggregated = aggregator.aggregate(sample_results, query="Project Alpha")
        
        # Should be serializable
        serialized = {
            'results': aggregated.results,
            'total_sources': aggregated.total_sources,
            'source_breakdown': aggregated.source_breakdown,
            'timeline': aggregated.timeline,
            'commitments': aggregated.commitments,
            'context_summary': aggregated.context_summary,
            'key_people': aggregated.key_people,
            'key_topics': aggregated.key_topics,
            'confidence_score': aggregated.confidence_score,
            'duplicates_removed': aggregated.duplicates_removed,
            'metadata': aggregated.metadata
        }
        
        json_str = json.dumps(serialized)
        assert isinstance(json_str, str)
        assert len(json_str) > 100  # Should have substantial content
        
        # Should be deserializable
        deserialized = json.loads(json_str)
        assert deserialized['total_sources'] == aggregated.total_sources
        assert deserialized['confidence_score'] == aggregated.confidence_score