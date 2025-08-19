"""
Natural Language Query Engine for AI Chief of Staff
Transforms natural language queries into structured search parameters
References: Team A search infrastructure for query execution

ENHANCED WITH DETERMINISTIC QUERY METHODS:
- Time-based queries with timezone awareness (Phase 1 requirement)
- Direct database access bypassing NLP parsing for deterministic results
- Integration with existing search infrastructure
"""

import re
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timedelta, date
from enum import Enum
from .query_parser import NLQueryParser
from ..queries.time_utils import TimeQueryEngine, parse_time_expression

logger = logging.getLogger(__name__)

class QueryIntent(Enum):
    """Types of user query intents - 9 supported intent types"""
    SEARCH_MESSAGES = "search_messages"
    FIND_COMMITMENTS = "find_commitments"
    BUILD_CONTEXT = "build_context"
    MULTI_SOURCE_SEARCH = "multi_source_search"
    CLARIFICATION_NEEDED = "clarification_needed"
    SHOW_STATISTICS = "show_statistics"
    TIME_RANGE_QUERY = "time_range_query"
    PERSON_ACTIVITY = "person_activity"
    TRENDING_TOPICS = "trending_topics"

@dataclass
class ParsedQuery:
    """Structured representation of a parsed natural language query"""
    original_query: str
    intent: QueryIntent
    keywords: List[str] = field(default_factory=list)
    sources: List[str] = field(default_factory=list)
    time_filter: Optional[str] = None
    person_filter: Optional[str] = None
    person_variants: List[str] = field(default_factory=list)
    response_type: str = "search_results"
    confidence: float = 0.0
    clarification_options: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

class QueryEngine:
    """
    Main query engine that orchestrates natural language processing
    
    Features:
    - Parses natural language queries into structured format
    - Supports 9 query intent types for comprehensive understanding
    - Query expansion with synonyms and related terms
    - Person name resolution to multiple identifiers  
    - Time filter parsing with natural language support
    - User context and query history tracking
    - Confidence scoring for query understanding
    """
    
    def __init__(self, db_path: str = "search.db"):
        """Initialize query engine with parser and context tracking"""
        self.parser = NLQueryParser()
        self.query_history = []
        self.user_context = {}
        self.intent_mapping = {
            'SEARCH_MESSAGES': QueryIntent.SEARCH_MESSAGES,
            'FIND_COMMITMENTS': QueryIntent.FIND_COMMITMENTS,
            'BUILD_CONTEXT': QueryIntent.BUILD_CONTEXT,
            'MULTI_SOURCE_SEARCH': QueryIntent.MULTI_SOURCE_SEARCH,
            'CLARIFICATION_NEEDED': QueryIntent.CLARIFICATION_NEEDED,
            'SHOW_STATISTICS': QueryIntent.SHOW_STATISTICS,
            'TIME_RANGE_QUERY': QueryIntent.TIME_RANGE_QUERY,
            'PERSON_ACTIVITY': QueryIntent.PERSON_ACTIVITY,
            'TRENDING_TOPICS': QueryIntent.TRENDING_TOPICS
        }
        
        # PHASE 1 ENHANCEMENT: Add deterministic query engine
        self.time_engine = TimeQueryEngine(db_path=db_path)
        self.db_path = db_path
    
    def parse_query(self, query: str, user_id: str = None) -> ParsedQuery:
        """
        Parse natural language query with user context
        
        Args:
            query: Natural language query string
            user_id: Optional user identifier for personalization
            
        Returns:
            ParsedQuery with structured query information
        """
        # Parse using NLQueryParser
        parsed_dict = self.parser.parse(query)
        
        # Convert to ParsedQuery dataclass
        parsed = ParsedQuery(
            original_query=parsed_dict['original_query'],
            intent=self.intent_mapping[parsed_dict['intent']],
            keywords=parsed_dict['keywords'],
            sources=parsed_dict['sources'],
            time_filter=parsed_dict['time_filter'],
            person_filter=parsed_dict['person_filter'],
            person_variants=parsed_dict['person_variants'],
            response_type=parsed_dict['response_type'],
            confidence=parsed_dict['confidence'],
            clarification_options=parsed_dict['clarification_options'],
            metadata=parsed_dict['metadata']
        )
        
        # Store in history for context learning
        self.query_history.append({
            'query': query,
            'parsed': parsed,
            'timestamp': datetime.now(),
            'user_id': user_id
        })
        
        # Enhance with user context if available
        if user_id and user_id in self.user_context:
            parsed = self._apply_user_context(parsed, user_id)
        
        return parsed
    
    def expand_query(self, query: str) -> ParsedQuery:
        """
        Expand query with additional context and synonyms
        
        Args:
            query: Original natural language query
            
        Returns:
            ParsedQuery with expanded keywords and context
        """
        parsed = self.parse_query(query)
        
        # Add context from recent queries
        recent_context = self._get_recent_context()
        if recent_context:
            parsed.keywords.extend(recent_context)
            parsed.keywords = list(set(parsed.keywords))  # Remove duplicates
        
        # Update confidence based on expansion
        if recent_context:
            parsed.confidence = min(1.0, parsed.confidence + 0.1)
            
        return parsed
    
    def update_user_context(self, user_id: str, context_updates: Dict[str, Any]):
        """
        Update user context for personalization
        
        Args:
            user_id: User identifier
            context_updates: Dictionary with context updates
        """
        if user_id not in self.user_context:
            self.user_context[user_id] = {}
        
        self.user_context[user_id].update(context_updates)
    
    def get_query_history(self, user_id: str = None, limit: int = 10) -> List[Dict]:
        """
        Get recent query history
        
        Args:
            user_id: Optional filter by user
            limit: Maximum number of queries to return
            
        Returns:
            List of recent query entries
        """
        history = self.query_history
        
        # Filter by user if specified
        if user_id:
            history = [entry for entry in history if entry.get('user_id') == user_id]
        
        # Return most recent entries
        return history[-limit:]
    
    def clear_history(self, user_id: str = None):
        """
        Clear query history
        
        Args:
            user_id: Optional - clear only for specific user
        """
        if user_id:
            self.query_history = [
                entry for entry in self.query_history 
                if entry.get('user_id') != user_id
            ]
        else:
            self.query_history = []
    
    def get_supported_intents(self) -> List[str]:
        """Get list of all supported query intents"""
        return [intent.value for intent in QueryIntent]
    
    def validate_query(self, query: str) -> Dict[str, Any]:
        """
        Validate a query without full parsing
        
        Args:
            query: Query to validate
            
        Returns:
            Validation result with suggestions
        """
        validation = {
            'is_valid': True,
            'issues': [],
            'suggestions': []
        }
        
        if not query or not query.strip():
            validation['is_valid'] = False
            validation['issues'].append('Query is empty')
            validation['suggestions'].append('Try asking a specific question')
            return validation
        
        query_clean = query.strip()
        
        # Check for minimum length
        if len(query_clean) < 3:
            validation['issues'].append('Query is very short')
            validation['suggestions'].append('Try providing more details')
        
        # Check for common issues
        if query_clean.count('?') > 3:
            validation['issues'].append('Too many question marks')
            validation['suggestions'].append('Use single question mark')
        
        if not any(char.isalpha() for char in query_clean):
            validation['is_valid'] = False
            validation['issues'].append('Query contains no letters')
            validation['suggestions'].append('Include descriptive words')
        
        return validation
    
    def _apply_user_context(self, parsed: ParsedQuery, user_id: str) -> ParsedQuery:
        """Apply user-specific context to enhance query"""
        user_ctx = self.user_context.get(user_id, {})
        
        # Add user's common search terms
        if 'common_terms' in user_ctx:
            parsed.keywords.extend(user_ctx['common_terms'])
            parsed.keywords = list(set(parsed.keywords))  # Remove duplicates
        
        # Prefer user's typical sources if not explicitly specified
        if 'preferred_sources' in user_ctx and len(parsed.sources) >= 3:
            # Only apply if user didn't specify sources explicitly
            parsed.sources = user_ctx['preferred_sources']
        
        # Apply user's common time preferences
        if 'default_time_range' in user_ctx and not parsed.time_filter:
            parsed.time_filter = user_ctx['default_time_range']
        
        return parsed
    
    def _get_recent_context(self) -> List[str]:
        """Get context keywords from recent queries"""
        if len(self.query_history) < 2:
            return []
        
        # Get keywords from last few queries
        recent_keywords = []
        for entry in self.query_history[-3:]:
            recent_keywords.extend(entry['parsed'].keywords)
        
        # Return most common recent keywords
        from collections import Counter
        keyword_counts = Counter(recent_keywords)
        return [kw for kw, count in keyword_counts.most_common(3)]
    
    def get_intent_statistics(self) -> Dict[str, int]:
        """Get statistics on query intent distribution"""
        intent_counts = Counter()
        
        for entry in self.query_history:
            intent_counts[entry['parsed'].intent.value] += 1
        
        return dict(intent_counts)
    
    def suggest_query_improvements(self, parsed: ParsedQuery) -> List[str]:
        """Suggest improvements for low-confidence queries"""
        suggestions = []
        
        if parsed.confidence < 0.5:
            if not parsed.keywords:
                suggestions.append("Try including more specific keywords")
            
            if not parsed.person_filter and 'from' not in parsed.original_query.lower():
                suggestions.append("Specify a person if looking for their content")
            
            if not parsed.time_filter:
                suggestions.append("Add a time range like 'last week' or 'yesterday'")
            
            if len(parsed.sources) >= 3:
                suggestions.append("Specify where to search: messages, calendar, or files")
        
        return suggestions
    
    def format_parsed_query(self, parsed: ParsedQuery) -> str:
        """Format parsed query for debugging or display"""
        lines = [
            f"Original: {parsed.original_query}",
            f"Intent: {parsed.intent.value}",
            f"Keywords: {', '.join(parsed.keywords)}",
            f"Sources: {', '.join(parsed.sources)}",
            f"Confidence: {parsed.confidence:.2f}"
        ]
        
        if parsed.person_filter:
            lines.append(f"Person: {parsed.person_filter}")
        
        if parsed.time_filter:
            lines.append(f"Time: {parsed.time_filter}")
        
        if parsed.clarification_options:
            lines.append(f"Clarifications: {', '.join(parsed.clarification_options)}")
        
        return '\n'.join(lines)
    
    # PHASE 1 ENHANCEMENT: Deterministic Query Methods
    # These methods bypass NLP parsing for guaranteed deterministic results
    
    def query_by_time_deterministic(self, time_expression: str, db_path: str = None) -> List[Dict[str, Any]]:
        """
        Execute deterministic time-based query without NLP parsing
        
        Args:
            time_expression: Natural language time expression (e.g., "yesterday", "past 7 days")
            db_path: Optional database path override
            
        Returns:
            List of matching records with source attribution
            
        Raises:
            TimeParsingError: If time expression cannot be parsed
        """
        db_path = db_path or self.db_path
        engine = TimeQueryEngine(db_path=db_path) if db_path != self.db_path else self.time_engine
        
        try:
            return engine.query_by_time(time_expression)
        except Exception as e:
            logger.error(f"Deterministic time query failed: {str(e)}")
            return []
    
    def query_date_range_deterministic(self, start: date, end: date, content_filter: str = None, db_path: str = None) -> List[Dict[str, Any]]:
        """
        Execute deterministic date range query
        
        Args:
            start: Start date (inclusive)
            end: End date (inclusive)
            content_filter: Optional content filter
            db_path: Optional database path override
            
        Returns:
            List of matching records
        """
        db_path = db_path or self.db_path
        engine = TimeQueryEngine(db_path=db_path) if db_path != self.db_path else self.time_engine
        
        try:
            return engine.query_date_range(start, end, content_filter)
        except Exception as e:
            logger.error(f"Deterministic date range query failed: {str(e)}")
            return []
    
    def query_by_time_and_source_deterministic(self, time_expression: str, source: str, db_path: str = None) -> List[Dict[str, Any]]:
        """
        Execute deterministic time and source filtered query
        
        Args:
            time_expression: Natural language time expression
            source: Source to filter by (e.g., 'slack', 'calendar', 'drive')
            db_path: Optional database path override
            
        Returns:
            List of matching records from specified source
        """
        db_path = db_path or self.db_path
        engine = TimeQueryEngine(db_path=db_path) if db_path != self.db_path else self.time_engine
        
        try:
            return engine.query_by_time_and_source(time_expression, source)
        except Exception as e:
            logger.error(f"Deterministic time/source query failed: {str(e)}")
            return []
    
    def validate_time_expression(self, expression: str) -> Dict[str, Any]:
        """
        Validate time expression without executing query
        
        Args:
            expression: Time expression to validate
            
        Returns:
            Validation result with parsed date range if valid
        """
        try:
            start, end = parse_time_expression(expression)
            return {
                'valid': True,
                'start_date': start,
                'end_date': end,
                'days_covered': (end.date() - start.date()).days,
                'timezone': str(start.tzinfo)
            }
        except Exception as e:
            return {
                'valid': False,
                'error': str(e),
                'suggestion': 'Try expressions like "yesterday", "past 7 days", "this week"'
            }
    
    def get_deterministic_query_stats(self) -> Dict[str, Any]:
        """Get statistics about deterministic query usage"""
        # Count deterministic vs NLP queries from history
        deterministic_count = 0
        nlp_count = 0
        
        for entry in self.query_history:
            if hasattr(entry, 'query_type'):
                if entry['query_type'] == 'deterministic':
                    deterministic_count += 1
                else:
                    nlp_count += 1
            else:
                nlp_count += 1  # Default to NLP for legacy entries
        
        return {
            'total_queries': len(self.query_history),
            'deterministic_queries': deterministic_count,
            'nlp_queries': nlp_count,
            'deterministic_percentage': (deterministic_count / max(1, len(self.query_history))) * 100
        }
    
    def close_connections(self):
        """Close database connections for cleanup"""
        if hasattr(self.time_engine, 'close'):
            self.time_engine.close()