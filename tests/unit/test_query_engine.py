"""
Unit tests for Natural Language Query Engine
Tests query parsing, intent recognition, and query expansion
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime
from src.intelligence.query_engine import QueryEngine, QueryIntent, ParsedQuery
from src.intelligence.query_parser import NLQueryParser


class TestNLQueryParser:
    """Test the natural language query parser"""
    
    @pytest.fixture
    def parser(self):
        """Initialize parser for testing"""
        return NLQueryParser()
    
    def test_search_messages_intent(self, parser):
        """Detect intent for message search queries"""
        queries = [
            "Find all messages about project deadline",
            "What did Alice say about the meeting?",
            "Show me slack discussions about Q4",
            "Any messages from Bob yesterday?"
        ]
        
        for query in queries:
            parsed_dict = parser.parse(query)
            assert parsed_dict['intent'] == 'SEARCH_MESSAGES'
    
    def test_find_commitments_intent(self, parser):
        """Detect intent for commitment finding queries"""
        queries = [
            "What did Alice promise to deliver by Friday?",
            "Show me all action items from last week",
            "Who committed to fixing the bug?",
            "What deadlines do we have this week?"
        ]
        
        for query in queries:
            parsed_dict = parser.parse(query)
            assert parsed_dict['intent'] == 'FIND_COMMITMENTS'
    
    def test_build_context_intent(self, parser):
        """Detect intent for context building queries"""
        queries = [
            "Give me context on the billing system project",
            "What's the background on the client issue?",
            "Explain the history of this feature request",
            "Provide an overview of Q4 planning"
        ]
        
        for query in queries:
            parsed_dict = parser.parse(query)
            assert parsed_dict['intent'] == 'BUILD_CONTEXT'
    
    def test_multi_source_search_intent(self, parser):
        """Detect intent for multi-source queries"""
        queries = [
            "Show me calendar events and slack discussions about Q4 planning",
            "Find all files and messages related to the project",
            "Search meetings and documents about client feedback"
        ]
        
        for query in queries:
            parsed_dict = parser.parse(query)
            assert parsed_dict['intent'] == 'MULTI_SOURCE_SEARCH'
    
    def test_clarification_needed_intent(self, parser):
        """Detect when clarification is needed"""
        queries = [
            "What's going on?",
            "Help me",
            "I need information",
            "Show me stuff"
        ]
        
        for query in queries:
            parsed_dict = parser.parse(query)
            assert parsed_dict['intent'] == 'CLARIFICATION_NEEDED'
            assert len(parsed_dict['clarification_options']) > 0
    
    def test_time_filter_extraction(self, parser):
        """Extract time filters from queries"""
        test_cases = [
            ("messages from last week", "last_week"),
            ("events from yesterday", "yesterday"),
            ("files shared today", "today"),
            ("commitments due by Friday", "by_friday"),
            ("updates from this month", "this_month")
        ]
        
        for query, expected_filter in test_cases:
            parsed_dict = parser.parse(query)
            assert parsed_dict['time_filter'] == expected_filter
    
    def test_person_filter_extraction(self, parser):
        """Extract person names from queries"""
        test_cases = [
            ("Messages from Alice about deployment", "Alice"),
            ("What did Bob promise?", "Bob"), 
            ("Files shared by Charlie", "Charlie"),
            ("Events with Dave", "Dave")
        ]
        
        for query, expected_person in test_cases:
            parsed_dict = parser.parse(query)
            assert parsed_dict['person_filter'] == expected_person
    
    def test_source_detection(self, parser):
        """Detect data sources to search"""
        test_cases = [
            ("slack messages about project", ["slack"]),
            ("calendar events next week", ["calendar"]),
            ("files in drive", ["drive"]),
            ("meeting and chat about Q4", ["calendar", "slack"]),
            ("all information about project", ["slack", "calendar", "drive"])  # default all
        ]
        
        for query, expected_sources in test_cases:
            parsed_dict = parser.parse(query)
            for source in expected_sources:
                assert source in parsed_dict['sources']
    
    def test_keyword_extraction(self, parser):
        """Extract meaningful keywords from queries"""
        query = "Find all messages about project deadline from last week"
        parsed_dict = parser.parse(query)
        
        # Should extract meaningful keywords, excluding stop words
        expected_keywords = {"project", "deadline", "messages"}
        actual_keywords = set(parsed_dict['keywords'])
        assert expected_keywords.issubset(actual_keywords)
        
        # Should not include stop words
        stop_words = {"find", "all", "about", "from"}
        assert not stop_words.intersection(actual_keywords)
    
    def test_person_name_variants(self, parser):
        """Generate name variants for better matching"""
        query = "Messages from John about deployment"
        parsed_dict = parser.parse(query)
        
        assert parsed_dict['person_filter'] == "John"
        # Should include common variations
        variants_lower = [v.lower() for v in parsed_dict['person_variants']]
        expected_variants = ["john", "johnny", "jon"]
        for variant in expected_variants:
            assert variant in variants_lower
    
    def test_query_expansion(self, parser):
        """Expand keywords with synonyms and related terms"""
        query = "Find bug reports"
        parsed_dict = parser.parse(query)
        
        # Should expand "bug" to include related terms
        expanded_terms = set(kw.lower() for kw in parsed_dict['keywords'])
        expected_terms = {"bug", "issue", "defect", "problem"}
        assert len(expanded_terms.intersection(expected_terms)) >= 2
    
    def test_confidence_scoring(self, parser):
        """Calculate confidence scores for parsed queries"""
        # High confidence query
        clear_query = "Find slack messages from Alice about project deadline yesterday"
        parsed_clear = parser.parse(clear_query)
        
        # Low confidence query  
        vague_query = "What's happening?"
        parsed_vague = parser.parse(vague_query)
        
        assert parsed_clear['confidence'] > parsed_vague['confidence']
        assert parsed_clear['confidence'] > 0.5
        assert parsed_vague['confidence'] < 0.5
    
    def test_response_type_mapping(self, parser):
        """Map intent to appropriate response type"""
        test_cases = [
            ("SEARCH_MESSAGES", "search_results"),
            ("FIND_COMMITMENTS", "commitment_summary"),
            ("BUILD_CONTEXT", "context_summary"),
            ("CLARIFICATION_NEEDED", "clarification")
        ]
        
        # Test response type mapping directly
        for intent_name, expected_type in test_cases:
            response_type = parser._determine_response_type(intent_name)
            assert response_type == expected_type


class TestQueryEngine:
    """Test the main query engine orchestrator"""
    
    @pytest.fixture
    def query_engine(self):
        """Initialize query engine for testing"""
        return QueryEngine()
    
    def test_parse_query_basic(self, query_engine):
        """Test basic query parsing functionality"""
        query = "Find all messages about project deadline from last week"
        parsed = query_engine.parse_query(query)
        
        assert isinstance(parsed, ParsedQuery)
        assert parsed.original_query == query
        assert parsed.intent == QueryIntent.SEARCH_MESSAGES
        assert "project" in parsed.keywords
        assert "deadline" in parsed.keywords
        assert parsed.time_filter == "last_week"
        assert "slack" in parsed.sources
    
    def test_parse_query_with_user_context(self, query_engine):
        """Test query parsing with user context"""
        user_id = "user123"
        
        # Set up user context
        query_engine.user_context[user_id] = {
            "common_terms": ["billing", "system"],
            "preferred_sources": ["slack"]
        }
        
        query = "Find project updates"
        parsed = query_engine.parse_query(query, user_id)
        
        # Should include user's common terms
        assert "billing" in parsed.keywords
        assert "system" in parsed.keywords
        # Should use user's preferred sources
        assert parsed.sources == ["slack"]
    
    def test_query_history_tracking(self, query_engine):
        """Test that query history is maintained"""
        queries = [
            "Find messages about project",
            "Show calendar events",
            "Search documents"
        ]
        
        for query in queries:
            query_engine.parse_query(query)
        
        assert len(query_engine.query_history) == 3
        assert query_engine.query_history[0]['query'] == queries[0]
        assert 'timestamp' in query_engine.query_history[0]
        assert 'parsed' in query_engine.query_history[0]
    
    def test_expand_query(self, query_engine):
        """Test query expansion with context"""
        # First, establish some context
        query_engine.parse_query("Find messages about billing project")
        query_engine.parse_query("Show billing system updates")
        
        # Now expand a related query
        expanded = query_engine.expand_query("project status")
        
        # Should include context from recent queries
        assert "billing" in expanded.keywords or "system" in expanded.keywords
    
    def test_multi_source_query_parsing(self, query_engine):
        """Test parsing of multi-source queries"""
        query = "Show me calendar events and slack discussions about Q4 planning"
        parsed = query_engine.parse_query(query)
        
        assert parsed.intent == QueryIntent.MULTI_SOURCE_SEARCH
        # Check for Q4 (case insensitive)
        keywords_lower = [k.lower() for k in parsed.keywords]
        assert any('q4' in k for k in keywords_lower)
        assert "planning" in parsed.keywords
        assert set(parsed.sources) == {"calendar", "slack"}
    
    def test_commitment_query_parsing(self, query_engine):
        """Test parsing of commitment-finding queries"""
        query = "What did Alice promise to deliver by Friday?"
        parsed = query_engine.parse_query(query)
        
        assert parsed.intent == QueryIntent.FIND_COMMITMENTS
        assert parsed.person_filter == "Alice"
        assert "deliver" in parsed.keywords
        assert parsed.time_filter == "by_friday"
        assert parsed.response_type == "commitment_summary"
    
    def test_context_building_query_parsing(self, query_engine):
        """Test parsing of context-building queries"""
        query = "Give me context on the billing system project"
        parsed = query_engine.parse_query(query)
        
        assert parsed.intent == QueryIntent.BUILD_CONTEXT
        # Check that keywords include the components of the phrase
        keywords_lower = [k.lower() for k in parsed.keywords] 
        assert "billing" in keywords_lower or any("billing" in k for k in keywords_lower)
        assert "system" in keywords_lower
        assert "project" in keywords_lower
        assert parsed.response_type == "context_summary"
    
    def test_ambiguous_query_handling(self, query_engine):
        """Test handling of ambiguous queries"""
        query = "What's going on?"
        parsed = query_engine.parse_query(query)
        
        assert parsed.intent == QueryIntent.CLARIFICATION_NEEDED
        assert len(parsed.clarification_options) > 0
        assert parsed.response_type == "clarification"
    
    def test_time_range_queries(self, query_engine):
        """Test various time range queries"""
        test_cases = [
            ("messages from today", "today"),
            ("events yesterday", "yesterday"), 
            ("files from last week", "last_week"),
            ("updates this month", "this_month"),
            ("deadlines by Friday", "by_friday")
        ]
        
        for query, expected_time in test_cases:
            parsed = query_engine.parse_query(query)
            assert parsed.time_filter == expected_time
    
    def test_person_activity_queries(self, query_engine):
        """Test person-specific activity queries"""
        query = "What has Alice been working on this week?"
        parsed = query_engine.parse_query(query)
        
        assert parsed.person_filter == "Alice"
        assert parsed.time_filter == "this_week"
        # Should include name variations
        assert len(parsed.person_variants) > 1
    
    def test_trending_topics_detection(self, query_engine):
        """Test detection of trending topics queries"""
        queries = [
            "What's trending in our discussions?",
            "Show me hot topics this week",
            "What are people talking about?"
        ]
        
        for query in queries:
            parsed = query_engine.parse_query(query)
            # Should detect as trending topics intent
            assert parsed.intent == QueryIntent.TRENDING_TOPICS
    
    def test_statistics_queries(self, query_engine):
        """Test detection of statistics queries"""
        queries = [
            "How many messages were sent today?",
            "Show me meeting statistics",
            "What's our activity level this week?"
        ]
        
        for query in queries:
            parsed = query_engine.parse_query(query)
            assert parsed.intent == QueryIntent.SHOW_STATISTICS
    
    def test_empty_query_handling(self, query_engine):
        """Test handling of empty or invalid queries"""
        empty_queries = ["", "   ", "\n\t", None]
        
        for query in empty_queries[:3]:  # Skip None for now
            parsed = query_engine.parse_query(query)
            assert parsed.intent == QueryIntent.CLARIFICATION_NEEDED
    
    def test_complex_multi_intent_query(self, query_engine):
        """Test handling of complex queries with multiple intents"""
        query = "Find Alice's commitments from last week and upcoming meetings about the project"
        parsed = query_engine.parse_query(query)
        
        # Should detect the primary intent
        assert parsed.intent in [QueryIntent.FIND_COMMITMENTS, QueryIntent.MULTI_SOURCE_SEARCH]
        assert parsed.person_filter == "Alice"
        assert "project" in parsed.keywords
        # Should detect some time-related filter
        assert parsed.time_filter is not None


class TestQueryIntentTypes:
    """Test all 9 query intent types"""
    
    @pytest.fixture
    def parser(self):
        return NLQueryParser()
    
    def test_search_messages_intent_type(self, parser):
        """Test SEARCH_MESSAGES intent detection"""
        query = "Find messages about the project"
        parsed_dict = parser.parse(query)
        assert parsed_dict['intent'] == 'SEARCH_MESSAGES'
    
    def test_find_commitments_intent_type(self, parser):
        """Test FIND_COMMITMENTS intent detection"""
        query = "What did Alice commit to deliver?"
        parsed_dict = parser.parse(query)
        assert parsed_dict['intent'] == 'FIND_COMMITMENTS'
    
    def test_build_context_intent_type(self, parser):
        """Test BUILD_CONTEXT intent detection"""
        query = "Give me background on the client project"
        parsed_dict = parser.parse(query)
        assert parsed_dict['intent'] == 'BUILD_CONTEXT'
    
    def test_multi_source_search_intent_type(self, parser):
        """Test MULTI_SOURCE_SEARCH intent detection"""
        query = "Search calendar and slack for Q4 planning"
        parsed_dict = parser.parse(query)
        assert parsed_dict['intent'] == 'MULTI_SOURCE_SEARCH'
    
    def test_clarification_needed_intent_type(self, parser):
        """Test CLARIFICATION_NEEDED intent detection"""
        query = "Help me find something"
        parsed_dict = parser.parse(query)
        assert parsed_dict['intent'] == 'CLARIFICATION_NEEDED'
    
    def test_show_statistics_intent_type(self, parser):
        """Test SHOW_STATISTICS intent detection"""
        query = "How many meetings did we have this week?"
        parsed_dict = parser.parse(query)
        assert parsed_dict['intent'] == 'SHOW_STATISTICS'
    
    def test_time_range_query_intent_type(self, parser):
        """Test TIME_RANGE_QUERY intent detection""" 
        query = "Show me everything from last month"
        parsed_dict = parser.parse(query)
        assert parsed_dict['intent'] == 'TIME_RANGE_QUERY'
    
    def test_person_activity_intent_type(self, parser):
        """Test PERSON_ACTIVITY intent detection"""
        query = "What has Bob been up to lately?"
        parsed_dict = parser.parse(query)
        assert parsed_dict['intent'] == 'PERSON_ACTIVITY'
    
    def test_trending_topics_intent_type(self, parser):
        """Test TRENDING_TOPICS intent detection"""
        query = "What topics are trending in our discussions?"
        parsed_dict = parser.parse(query)
        assert parsed_dict['intent'] == 'TRENDING_TOPICS'