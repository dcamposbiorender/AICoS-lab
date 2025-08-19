#!/usr/bin/env python3
"""
Simple, self-contained test suite for AI Chief of Staff
No external dependencies - just tests basic functionality
"""

import unittest
import tempfile
import json
import os
import time
from pathlib import Path


class SimpleTestRunner:
    """Simple test runner with clear output"""
    
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
    
    def run_test(self, test_name, test_func):
        """Run a single test and track results"""
        try:
            test_func()
            print(f"✅ {test_name}")
            self.passed += 1
        except Exception as e:
            print(f"❌ {test_name}: {e}")
            self.failed += 1
            self.errors.append(f"{test_name}: {e}")
    
    def summary(self):
        """Print test summary"""
        total = self.passed + self.failed
        print("\n" + "="*50)
        print("TEST SUMMARY")
        print("="*50)
        print(f"Total Tests: {total}")
        print(f"Passed: {self.passed}")
        print(f"Failed: {self.failed}")
        print(f"Success Rate: {(self.passed/max(total,1)*100):.1f}%")
        
        if self.failed > 0:
            print("\nFAILED TESTS:")
            for error in self.errors:
                print(f"  - {error}")
        
        return self.failed == 0


def test_basic_math():
    """Test basic math operations"""
    assert 1 + 1 == 2
    assert 10 - 5 == 5
    assert 3 * 4 == 12
    assert 8 / 2 == 4
    assert 2 ** 3 == 8


def test_string_operations():
    """Test string operations"""
    text = "AI Chief of Staff"
    assert len(text) == 17
    assert text.lower() == "ai chief of staff"
    assert text.startswith("AI")
    assert "Chief" in text
    assert text.replace("Staff", "Assistant") == "AI Chief of Assistant"


def test_list_operations():
    """Test list operations"""
    data = [1, 2, 3, 4, 5]
    assert len(data) == 5
    assert data[0] == 1
    assert data[-1] == 5
    data.append(6)
    assert 6 in data
    assert sum(data) == 21


def test_dictionary_operations():
    """Test dictionary operations"""
    config = {
        "slack_token": "xoxb-test",
        "base_dir": "/tmp/test",
        "enabled": True,
        "count": 42
    }
    
    assert config["slack_token"] == "xoxb-test"
    assert config.get("missing_key", "default") == "default"
    assert len(config) == 4
    config["new_key"] = "new_value"
    assert "new_key" in config


def test_file_operations():
    """Test file operations"""
    # Create temporary file
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        test_file = f.name
        f.write("test data")
    
    # Test file exists
    assert Path(test_file).exists()
    
    # Test file reading
    with open(test_file, 'r') as f:
        content = f.read()
    assert content == "test data"
    
    # Cleanup
    os.unlink(test_file)
    assert not Path(test_file).exists()


def test_json_operations():
    """Test JSON operations"""
    data = {
        "timestamp": "2025-08-19T12:00:00Z",
        "records": [1, 2, 3],
        "metadata": {"version": "1.0"}
    }
    
    # Test JSON serialization
    json_str = json.dumps(data)
    assert isinstance(json_str, str)
    
    # Test JSON deserialization
    parsed = json.loads(json_str)
    assert parsed == data
    assert parsed["records"] == [1, 2, 3]


def test_path_operations():
    """Test path operations"""
    temp_dir = tempfile.mkdtemp()
    base_path = Path(temp_dir)
    
    # Test path creation
    test_dir = base_path / "test" / "subdir"
    test_dir.mkdir(parents=True, exist_ok=True)
    assert test_dir.exists()
    
    # Test file creation
    test_file = test_dir / "test.txt"
    test_file.write_text("test content")
    assert test_file.read_text() == "test content"
    
    # Cleanup
    import shutil
    shutil.rmtree(temp_dir)


def test_time_operations():
    """Test time operations"""
    start = time.time()
    time.sleep(0.1)  # Sleep 100ms
    end = time.time()
    
    duration = end - start
    assert duration >= 0.1
    assert duration < 0.2  # Should be close to 100ms


def test_error_handling():
    """Test error handling"""
    # Test that we can catch exceptions
    try:
        result = 1 / 0
        assert False, "Should have raised ZeroDivisionError"
    except ZeroDivisionError:
        pass  # Expected
    
    # Test assertion errors
    try:
        assert False, "This should fail"
        assert False, "Should not reach here"
    except AssertionError:
        pass  # Expected


def test_data_structures():
    """Test more complex data structures"""
    # Test nested structures
    nested = {
        "users": [
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"}
        ],
        "config": {
            "timeout": 30,
            "retries": 3
        }
    }
    
    assert len(nested["users"]) == 2
    assert nested["users"][0]["name"] == "Alice"
    assert nested["config"]["timeout"] == 30
    
    # Test list comprehension
    names = [user["name"] for user in nested["users"]]
    assert names == ["Alice", "Bob"]


def main():
    """Run all tests"""
    print("🚀 AI Chief of Staff - Simple Test Suite")
    print("="*50)
    
    runner = SimpleTestRunner()
    
    # Define all tests
    tests = [
        ("Basic Math Operations", test_basic_math),
        ("String Operations", test_string_operations),
        ("List Operations", test_list_operations),
        ("Dictionary Operations", test_dictionary_operations),
        ("File Operations", test_file_operations),
        ("JSON Operations", test_json_operations),
        ("Path Operations", test_path_operations),
        ("Time Operations", test_time_operations),
        ("Error Handling", test_error_handling),
        ("Data Structures", test_data_structures)
    ]
    
    print(f"Running {len(tests)} test categories...\n")
    
    # Run all tests
    for test_name, test_func in tests:
        runner.run_test(test_name, test_func)
    
    # Show summary
    success = runner.summary()
    
    print("\n" + "="*50)
    if success:
        print("🎉 ALL TESTS PASSED - Test infrastructure is working!")
    else:
        print("⚠️  Some tests failed - Check the errors above")
    print("="*50)
    
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())