"""
Intelligence Layer for AI Chief of Staff
Transforms natural language queries into structured search parameters
"""

from .query_engine import QueryEngine, QueryIntent, ParsedQuery
from .query_parser import NLQueryParser

__all__ = [
    'QueryEngine',
    'QueryIntent', 
    'ParsedQuery',
    'NLQueryParser'
]