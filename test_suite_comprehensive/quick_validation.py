#!/usr/bin/env python3
"""
Quick validation script to test core functionality works correctly.
"""

import sys
import tempfile
from pathlib import Path

# Add project root to path
sys.path.insert(0, '/Users/david.campos/VibeCode/AICoS-Lab')

from src.search.database import SearchDatabase
from src.intelligence.query_engine import QueryEngine
from src.intelligence.result_aggregator import ResultAggregator

def test_core_functionality():
    """Test that core components work together"""
    print("🧪 Testing core functionality...")
    
    # Test 1: SearchDatabase basic operations
    print("  1. SearchDatabase initialization and indexing...")
    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "test.db"
    
    db = SearchDatabase(str(db_path))
    
    # Test indexing
    test_records = [
        {"id": "test1", "content": "alice committed to finishing the report", "source": "slack"},
        {"id": "test2", "content": "meeting scheduled for project review", "source": "calendar"}
    ]
    
    result = db.index_records_batch(test_records, source="test")
    print(f"    Indexed: {result['indexed']} records, {result['errors']} errors")
    assert result['indexed'] == 2
    assert result['errors'] == 0
    
    # Test search
    search_results = db.search("alice")
    print(f"    Search results: {len(search_results)} found")
    assert len(search_results) > 0
    
    print("    ✅ SearchDatabase works correctly")
    
    # Test 2: QueryEngine 
    print("  2. QueryEngine natural language processing...")
    query_engine = QueryEngine()
    
    parsed = query_engine.parse_query("find commitments from alice about project")
    print(f"    Parsed intent: {parsed.intent}")
    print(f"    Keywords: {parsed.keywords}")
    assert len(parsed.keywords) > 0
    
    print("    ✅ QueryEngine works correctly")
    
    # Test 3: ResultAggregator
    print("  3. ResultAggregator result processing...")
    aggregator = ResultAggregator()
    
    mock_results = {
        "test": [
            {"content": "alice committed to project", "source": "slack", "timestamp": "2025-08-18T10:00:00Z"},
            {"content": "project meeting scheduled", "source": "calendar", "timestamp": "2025-08-18T14:00:00Z"}
        ]
    }
    
    aggregated = aggregator.aggregate(mock_results, query="project")
    print(f"    Aggregated: {len(aggregated.results)} results")
    assert len(aggregated.results) == 2
    
    print("    ✅ ResultAggregator works correctly")
    
    # Clean up
    db.close()
    
    print("🎉 All core functionality validated successfully!")
    return True

if __name__ == "__main__":
    try:
        test_core_functionality()
        print("\n✅ VALIDATION PASSED: Core system functionality working correctly")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ VALIDATION FAILED: {str(e)}")
        sys.exit(1)