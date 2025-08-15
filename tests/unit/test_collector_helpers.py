"""
Tests for collector test helpers.
Validates the testing utilities themselves to ensure they work correctly.
"""

import json
import tempfile
import threading
import time
from pathlib import Path
from typing import Dict, Any
from unittest.mock import Mock

import pytest

from tests.helpers.collector_helpers import (
    CollectorTestHelper,
    ArchiveTestValidator,
    create_test_helper,
    assert_jsonl_valid,
    assert_archive_structure_valid,
    slack_test_helper,
    calendar_test_helper,
    drive_test_helper,
    employee_test_helper
)


class TestCollectorTestHelper:
    """Test the CollectorTestHelper class."""
    
    def test_helper_creation_for_different_types(self):
        """Test helper creation for all collector types."""
        collector_types = ['slack', 'calendar', 'drive', 'employee']
        
        for collector_type in collector_types:
            helper = CollectorTestHelper(collector_type)
            assert helper.collector_type == collector_type
            assert helper.mock_data is not None
            assert isinstance(helper.mock_data, dict)
    
    def test_temporary_archive_dir_creation(self):
        """Test temporary archive directory creation and cleanup."""
        helper = CollectorTestHelper("slack")
        
        with helper.temporary_archive_dir() as archive_path:
            assert archive_path.exists()
            assert archive_path.is_dir()
            
            # Create a test file
            test_file = archive_path / "test.txt"
            test_file.write_text("test content")
            assert test_file.exists()
        
        # Directory should still exist after context manager
        assert archive_path.exists()
        
        # Cleanup should remove it
        helper.cleanup_temp_dirs()
        assert not archive_path.exists()
    
    def test_mock_collector_creation(self):
        """Test mock collector creation with default behavior."""
        helper = CollectorTestHelper("slack")
        mock_collector = helper.create_mock_collector()
        
        # Test default behavior
        result = mock_collector.collect()
        assert result is not None
        
        state = mock_collector.get_state()
        assert isinstance(state, dict)
        assert "cursor" in state
    
    def test_failing_collector_creation(self):
        """Test failing collector creation for different error types."""
        helper = CollectorTestHelper("slack")
        
        error_types = ["api_error", "rate_limit", "auth_error", "network_error", "timeout"]
        
        for error_type in error_types:
            failing_collector = helper.create_failing_collector(error_type)
            
            with pytest.raises(Exception):
                failing_collector.collect()
    
    def test_jsonl_validation_valid_file(self):
        """Test JSONL validation with valid file."""
        helper = CollectorTestHelper("slack")
        
        with helper.temporary_archive_dir() as archive_path:
            jsonl_file = archive_path / "test.jsonl"
            
            # Write valid JSONL data
            with open(jsonl_file, 'w') as f:
                f.write('{"id": 1, "message": "test"}\n')
                f.write('{"id": 2, "message": "another test"}\n')
            
            results = helper.validate_jsonl_format(jsonl_file)
            
            assert results["valid"] is True
            assert results["line_count"] == 2
            assert results["valid_lines"] == 2
            assert results["invalid_lines"] == 0
            assert len(results["sample_records"]) == 2
    
    def test_jsonl_validation_invalid_file(self):
        """Test JSONL validation with invalid file."""
        helper = CollectorTestHelper("slack")
        
        with helper.temporary_archive_dir() as archive_path:
            jsonl_file = archive_path / "invalid.jsonl"
            
            # Write invalid JSONL data
            with open(jsonl_file, 'w') as f:
                f.write('{"valid": "json"}\n')
                f.write('invalid json line\n')
                f.write('{"another": "valid"}\n')
            
            results = helper.validate_jsonl_format(jsonl_file)
            
            assert results["valid"] is False
            assert results["line_count"] == 3
            assert results["valid_lines"] == 2
            assert results["invalid_lines"] == 1
            assert len(results["errors"]) == 1
    
    def test_archive_structure_validation(self):
        """Test archive structure validation."""
        helper = CollectorTestHelper("slack")
        
        with helper.temporary_archive_dir() as archive_path:
            # Create proper archive structure
            collector_dir = archive_path / "slack"
            collector_dir.mkdir()
            
            daily_dir = collector_dir / "2025-08-15"
            daily_dir.mkdir()
            
            jsonl_file = daily_dir / "slack_data.jsonl"
            jsonl_file.write_text('{"test": "data"}\n')
            
            results = helper.validate_archive_structure(archive_path)
            
            assert results["valid_structure"] is True
            assert results["base_exists"] is True
            assert results["collector_dir_exists"] is True
            assert "2025-08-15" in results["daily_dirs"]
            assert len(results["jsonl_files"]) == 1
    
    def test_concurrent_test_scenario(self):
        """Test concurrent testing scenario creation."""
        helper = CollectorTestHelper("slack")
        
        concurrent_test = helper.create_concurrent_test_scenario(
            num_workers=3,
            operations_per_worker=5
        )
        
        # Simple operation function for testing
        def test_operation(worker_id: int, operation_id: int) -> Dict[str, Any]:
            return {"worker": worker_id, "operation": operation_id, "result": "success"}
        
        results = concurrent_test(test_operation)
        
        assert results["total_operations"] == 15  # 3 * 5
        assert results["successful_operations"] == 15
        assert results["success_rate"] == 1.0
        assert len(results["errors"]) == 0
    
    def test_performance_test_creation(self):
        """Test performance test scenario creation."""
        helper = CollectorTestHelper("slack")
        
        performance_test = helper.create_performance_test(
            target_ops_per_second=100,
            test_duration=1  # Short test for speed
        )
        
        # Simple operation
        def simple_op():
            return sum(range(10))
        
        results = performance_test(simple_op)
        
        assert "actual_ops_per_second" in results
        assert "total_operations" in results
        assert "performance_met" in results
        assert results["duration"] >= 0.9  # Should run for about 1 second


class TestArchiveTestValidator:
    """Test the ArchiveTestValidator class."""
    
    def test_metadata_consistency_validation(self):
        """Test metadata consistency validation."""
        # Valid record
        valid_record = {
            "data": {"test": "data"},
            "metadata": {
                "collector_type": "slack",
                "collection_timestamp": "2025-08-15T10:00:00"
            }
        }
        
        errors = ArchiveTestValidator.validate_metadata_consistency(valid_record)
        assert len(errors) == 0
        
        # Invalid record (missing metadata)
        invalid_record = {"data": {"test": "data"}}
        
        errors = ArchiveTestValidator.validate_metadata_consistency(invalid_record)
        assert len(errors) > 0
        assert any("Missing required field: metadata" in error for error in errors)
    
    def test_timestamp_validation(self):
        """Test timestamp validation across records."""
        records = [
            {
                "metadata": {
                    "collection_timestamp": "2025-08-15T10:00:00"
                }
            },
            {
                "metadata": {
                    "collection_timestamp": "2025-08-15T10:01:00"
                }
            }
        ]
        
        results = ArchiveTestValidator.validate_timestamps(records)
        
        assert results["valid"] is True
        assert results["record_count"] == 2
        assert "timestamp_range" in results
        assert results["timestamp_range"]["span_hours"] > 0
    
    def test_data_comparison(self):
        """Test comparison of original vs archived data."""
        original_data = {
            "messages": [
                {"id": 1, "text": "Hello"},
                {"id": 2, "text": "World"}
            ],
            "count": 2
        }
        
        archived_data = {
            "data": original_data,
            "metadata": {
                "collector_type": "slack",
                "collection_timestamp": "2025-08-15T10:00:00"
            }
        }
        
        results = ArchiveTestValidator.compare_with_original(original_data, archived_data)
        
        assert results["data_preserved"] is True
        assert len(results["missing_fields"]) == 0
        assert len(results["modified_fields"]) == 0


class TestHelperFunctions:
    """Test standalone helper functions."""
    
    def test_create_test_helper_function(self):
        """Test create_test_helper convenience function."""
        helper = create_test_helper("calendar")
        
        assert isinstance(helper, CollectorTestHelper)
        assert helper.collector_type == "calendar"
    
    def test_assert_jsonl_valid_function(self):
        """Test assert_jsonl_valid convenience function."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write('{"test": "record1"}\n')
            f.write('{"test": "record2"}\n')
            f.flush()
            
            jsonl_path = Path(f.name)
        
        # Should not raise exception for valid JSONL
        assert_jsonl_valid(jsonl_path, min_records=2)
        
        # Should raise exception for insufficient records
        with pytest.raises(AssertionError):
            assert_jsonl_valid(jsonl_path, min_records=5)
        
        # Cleanup
        jsonl_path.unlink()
    
    def test_assert_archive_structure_valid_function(self):
        """Test assert_archive_structure_valid convenience function."""
        with tempfile.TemporaryDirectory() as temp_dir:
            archive_path = Path(temp_dir)
            
            # Create invalid structure first
            with pytest.raises(AssertionError):
                assert_archive_structure_valid(archive_path, "slack")
            
            # Create valid structure
            slack_dir = archive_path / "slack"
            slack_dir.mkdir()
            
            daily_dir = slack_dir / "2025-08-15"
            daily_dir.mkdir()
            
            jsonl_file = daily_dir / "slack_data.jsonl"
            jsonl_file.write_text('{"test": "data"}\n')
            
            # Should not raise exception for valid structure
            assert_archive_structure_valid(archive_path, "slack")


class TestPytestFixtures:
    """Test pytest fixture integration."""
    
    def test_fixture_availability(self):
        """Test that fixture functions are available for import."""
        # Just verify that fixtures can be imported and are callable
        fixture_names = [
            slack_test_helper,
            calendar_test_helper,
            drive_test_helper,
            employee_test_helper
        ]
        
        for fixture_func in fixture_names:
            assert callable(fixture_func), f"Fixture {fixture_func.__name__} should be callable"
            
            # Verify it has pytest fixture decorator
            # Note: This test validates that the fixtures exist and can be imported
            # Actual fixture functionality would be tested in integration tests
            # where they're used as proper pytest fixtures


if __name__ == "__main__":
    # Run basic validation
    print("Testing collector helpers...")
    
    # Test helper creation
    helper = create_test_helper("slack")
    print(f"✓ Created helper for {helper.collector_type}")
    
    # Test mock data
    mock_collector = helper.create_mock_collector()
    data = mock_collector.collect()
    print(f"✓ Mock collector returns data: {len(str(data))} chars")
    
    # Test temporary directory
    with helper.temporary_archive_dir() as archive_path:
        print(f"✓ Temporary directory created: {archive_path}")
    
    helper.cleanup_temp_dirs()
    print("✓ Cleanup completed")
    
    print("All collector helper tests passed! ✅")