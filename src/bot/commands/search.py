#!/usr/bin/env python3
"""
Search Command - Simple Direct Integration

Simple search functionality that creates deterministic calls to SearchDatabase.
No complex features, just working search functionality.
"""

import sys
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

# Add project root for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.search.database import SearchDatabase, DatabaseError
from src.core.permission_checker import get_permission_checker, validate_permissions

logger = logging.getLogger(__name__)

def execute_search(query: str, source: Optional[str] = None, limit: int = 5) -> Dict[str, Any]:
    """
    Execute search command with direct SearchDatabase integration
    
    Args:
        query: Search query string
        source: Optional source filter (slack, calendar, drive, employees)
        limit: Maximum results to return
        
    Returns:
        Dict containing search results or error information
    """
    try:
        # Basic permission check
        permission_checker = get_permission_checker()
        if not validate_permissions('search.messages'):
            logger.warning("Search permissions not validated, continuing anyway")
        
        # Get database path
        db_path = project_root / "search.db"
        if not db_path.exists():
            return {
                "error": "Search database not found",
                "suggestion": "Run data collection first"
            }
        
        # Create database connection and perform search
        search_db = SearchDatabase(str(db_path))
        results = search_db.search(query=query, source=source, limit=limit)
        
        return {
            "query": query,
            "source_filter": source,
            "results": results,
            "total": len(results),
            "error": None
        }
        
    except DatabaseError as e:
        logger.error(f"Database error during search: {e}")
        return {
            "error": f"Database error: {str(e)}",
            "query": query,
            "results": []
        }
    except Exception as e:
        logger.error(f"Unexpected search error: {e}")
        return {
            "error": f"Search failed: {str(e)}",
            "query": query,
            "results": []
        }

def format_search_response(search_result: Dict[str, Any]) -> str:
    """
    Format search results for Slack response
    
    Args:
        search_result: Result from execute_search()
        
    Returns:
        Formatted string for Slack
    """
    if search_result.get("error"):
        return f"❌ Search Error: {search_result['error']}"
    
    query = search_result.get("query", "")
    results = search_result.get("results", [])
    total = search_result.get("total", 0)
    
    if total == 0:
        return f"🔍 No results found for: `{query}`"
    
    # Format results
    response = f"🔍 **Search Results for:** `{query}`\n"
    response += f"Found {total} results\n\n"
    
    for i, result in enumerate(results[:3], 1):  # Show top 3
        content = result.get('content', 'No content')
        if len(content) > 200:
            content = content[:200] + '...'
        
        source = result.get('source', 'unknown')
        response += f"**{i}.** {source.title()}\n"
        response += f"{content}\n\n"
    
    if len(results) > 3:
        response += f"_...and {len(results) - 3} more results_"
    
    return response

# Simple test function
if __name__ == "__main__":
    # Test search functionality
    result = execute_search("test")
    print(f"Search test result: {result}")
    
    formatted = format_search_response(result)
    print(f"Formatted response:\n{formatted}")