"""
Custom validators for comprehensive testing.

Provides validation utilities for test data and system behavior.
"""

from typing import Any, Dict, List, Optional

def validate_performance_metrics(metrics: Dict[str, Any], requirements: Dict[str, Any]) -> bool:
    """Validate performance metrics against requirements.
    
    Args:
        metrics: Actual performance metrics
        requirements: Required performance thresholds
        
    Returns:
        True if all requirements are met
    """
    for metric_name, required_value in requirements.items():
        if metric_name not in metrics:
            return False
            
        actual_value = metrics[metric_name]
        
        # Handle different comparison types
        if isinstance(required_value, dict):
            if "max" in required_value and actual_value > required_value["max"]:
                return False
            if "min" in required_value and actual_value < required_value["min"]:
                return False
        else:
            # Simple equality check
            if actual_value != required_value:
                return False
                
    return True

def validate_search_results(results: List[Dict[str, Any]], expected_count: Optional[int] = None) -> bool:
    """Validate search results format and content.
    
    Args:
        results: Search results to validate
        expected_count: Expected number of results (optional)
        
    Returns:
        True if results are valid
    """
    if expected_count is not None and len(results) != expected_count:
        return False
        
    required_fields = ["id", "content", "source"]
    
    for result in results:
        if not isinstance(result, dict):
            return False
            
        for field in required_fields:
            if field not in result:
                return False
                
    return True

def validate_database_integrity(db_connection) -> bool:
    """Validate database integrity and structure.
    
    Args:
        db_connection: Database connection to validate
        
    Returns:
        True if database is valid
    """
    try:
        cursor = db_connection.cursor()
        
        # Check required tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        required_tables = ["messages", "messages_fts"]
        for table in required_tables:
            if table not in tables:
                return False
                
        # Basic data consistency checks
        cursor.execute("SELECT COUNT(*) FROM messages")
        message_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM messages_fts")
        fts_count = cursor.fetchone()[0]
        
        # FTS table should have at least as many records as messages
        return fts_count >= message_count
        
    except Exception:
        return False