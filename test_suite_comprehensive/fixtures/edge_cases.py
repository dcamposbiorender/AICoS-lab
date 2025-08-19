"""
Edge case test data for comprehensive testing.

Provides test cases for error conditions, boundary conditions, and edge cases.
"""

from typing import Dict, List, Any

def get_empty_data_cases() -> List[Dict[str, Any]]:
    """Test cases for empty data scenarios."""
    return [
        {"id": "empty_text", "text": "", "user": "U1000000", "channel": "C1000000"},
        {"id": "null_text", "text": None, "user": "U1000000", "channel": "C1000000"},
        {"id": "whitespace", "text": "   \n\t   ", "user": "U1000000", "channel": "C1000000"}
    ]

def get_large_data_cases() -> List[Dict[str, Any]]:
    """Test cases for large data scenarios."""
    return [
        {
            "id": "large_text", 
            "text": "A" * 10000,  # 10KB text
            "user": "U1000000", 
            "channel": "C1000000"
        },
        {
            "id": "unicode_text",
            "text": "Test with unicode: 🚀 ñáéíóú αβγδε 中文测试 العربية русский",
            "user": "U1000000",
            "channel": "C1000000"
        }
    ]

def get_malformed_data_cases() -> List[Dict[str, Any]]:
    """Test cases for malformed data."""
    return [
        {"text": "Missing required fields"},
        {"id": "no_text", "user": "U1000000", "channel": "C1000000"},
        {"id": "invalid_timestamp", "text": "Test", "ts": "invalid_timestamp"}
    ]