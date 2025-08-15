"""
Test helper utilities for collector testing.

Provides reusable testing utilities for collector wrappers, including:
- Mock API response generation
- Test data validation
- Archive verification helpers
- Performance testing utilities
- Error injection helpers
"""

import json
import tempfile
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Generator, Callable
from unittest.mock import Mock, patch
import pytest

# Import our mock data
from tests.fixtures.mock_slack_data import get_mock_collection_result as get_slack_data
from tests.fixtures.mock_calendar_data import get_mock_collection_result as get_calendar_data
from tests.fixtures.mock_employee_data import get_mock_collection_result as get_employee_data
from tests.fixtures.mock_drive_data import get_mock_collection_result as get_drive_data


class CollectorTestHelper:
    """
    Comprehensive test helper for collector testing.
    
    Provides utilities for mocking APIs, validating data, and testing
    collector wrappers in various scenarios.
    """
    
    def __init__(self, collector_type: str):
        """
        Initialize test helper for specific collector type.
        
        Args:
            collector_type: Type of collector (slack, calendar, drive, employee)
        """
        self.collector_type = collector_type
        self.mock_data = self._get_mock_data()
        self.temp_dirs = []
        
    def _get_mock_data(self) -> Dict[str, Any]:
        """Get mock data for this collector type."""
        data_sources = {
            'slack': get_slack_data,
            'calendar': get_calendar_data,
            'drive': get_drive_data,
            'employee': get_employee_data
        }
        return data_sources.get(self.collector_type, get_slack_data)()
    
    @contextmanager
    def temporary_archive_dir(self) -> Generator[Path, None, None]:
        """
        Create temporary archive directory for testing.
        
        Yields:
            Path to temporary archive directory
        """
        temp_dir = tempfile.mkdtemp(prefix=f"test_archive_{self.collector_type}_")
        archive_path = Path(temp_dir)
        self.temp_dirs.append(archive_path)
        
        try:
            yield archive_path
        finally:
            # Cleanup handled by teardown
            pass
    
    def cleanup_temp_dirs(self):
        """Clean up all temporary directories created during testing."""
        import shutil
        for temp_dir in self.temp_dirs:
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
        self.temp_dirs.clear()
    
    def create_mock_collector(self, **kwargs) -> Mock:
        """
        Create a mock collector with realistic behavior.
        
        Args:
            **kwargs: Additional configuration for the mock
            
        Returns:
            Mock collector with configured behavior
        """
        mock_collector = Mock()
        
        # Configure default behavior
        mock_collector.collect.return_value = self.mock_data
        mock_collector.get_state.return_value = {"cursor": "test_cursor", "last_run": None}
        mock_collector.set_state.return_value = None
        
        # Apply any custom configuration
        for key, value in kwargs.items():
            setattr(mock_collector, key, value)
        
        return mock_collector
    
    def create_failing_collector(self, failure_type: str = "api_error") -> Mock:
        """
        Create a mock collector that simulates failures.
        
        Args:
            failure_type: Type of failure to simulate
            
        Returns:
            Mock collector that raises appropriate exceptions
        """
        mock_collector = Mock()
        
        failure_types = {
            "api_error": Exception("API request failed"),
            "rate_limit": Exception("Rate limit exceeded"),
            "auth_error": Exception("Authentication failed"),
            "network_error": Exception("Network connection failed"),
            "timeout": Exception("Request timed out")
        }
        
        error = failure_types.get(failure_type, Exception(f"Unknown error: {failure_type}"))
        mock_collector.collect.side_effect = error
        
        return mock_collector
    
    def validate_jsonl_format(self, file_path: Path) -> Dict[str, Any]:
        """
        Validate JSONL file format and return statistics.
        
        Args:
            file_path: Path to JSONL file to validate
            
        Returns:
            Dictionary with validation results and statistics
        """
        if not file_path.exists():
            return {"valid": False, "error": "File does not exist"}
        
        results = {
            "valid": True,
            "line_count": 0,
            "valid_lines": 0,
            "invalid_lines": 0,
            "errors": [],
            "sample_records": []
        }
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    results["line_count"] += 1
                    
                    if not line.strip():
                        continue  # Skip empty lines
                    
                    try:
                        record = json.loads(line.strip())
                        results["valid_lines"] += 1
                        
                        # Collect sample records
                        if len(results["sample_records"]) < 3:
                            results["sample_records"].append(record)
                            
                    except json.JSONDecodeError as e:
                        results["invalid_lines"] += 1
                        results["errors"].append(f"Line {line_num}: {str(e)}")
                        
        except Exception as e:
            results["valid"] = False
            results["error"] = f"Failed to read file: {str(e)}"
        
        # Overall validation
        results["valid"] = results["valid"] and results["invalid_lines"] == 0
        
        return results
    
    def validate_archive_structure(self, archive_path: Path) -> Dict[str, Any]:
        """
        Validate archive directory structure.
        
        Args:
            archive_path: Base archive path to validate
            
        Returns:
            Dictionary with validation results
        """
        expected_structure = {
            "base_exists": archive_path.exists(),
            "collector_dir_exists": False,
            "daily_dirs": [],
            "jsonl_files": [],
            "valid_structure": False
        }
        
        if not expected_structure["base_exists"]:
            return expected_structure
        
        collector_dir = archive_path / self.collector_type
        expected_structure["collector_dir_exists"] = collector_dir.exists()
        
        if not expected_structure["collector_dir_exists"]:
            return expected_structure
        
        # Check for daily directories (YYYY-MM-DD format)
        for item in collector_dir.iterdir():
            if item.is_dir() and self._is_valid_date_dir(item.name):
                expected_structure["daily_dirs"].append(item.name)
                
                # Check for JSONL files in daily directory
                jsonl_files = list(item.glob("*.jsonl"))
                expected_structure["jsonl_files"].extend([str(f) for f in jsonl_files])
        
        expected_structure["valid_structure"] = (
            expected_structure["base_exists"] and
            expected_structure["collector_dir_exists"] and
            len(expected_structure["daily_dirs"]) > 0 and
            len(expected_structure["jsonl_files"]) > 0
        )
        
        return expected_structure
    
    def _is_valid_date_dir(self, dirname: str) -> bool:
        """Check if directory name is valid YYYY-MM-DD format."""
        try:
            datetime.strptime(dirname, "%Y-%m-%d")
            return True
        except ValueError:
            return False
    
    def create_concurrent_test_scenario(self, 
                                        num_workers: int = 5,
                                        operations_per_worker: int = 10) -> Callable:
        """
        Create a concurrent testing scenario.
        
        Args:
            num_workers: Number of concurrent workers
            operations_per_worker: Operations each worker should perform
            
        Returns:
            Function that runs the concurrent scenario
        """
        def run_scenario(collector_func: Callable, 
                        validation_func: Optional[Callable] = None):
            """
            Run concurrent operations and validate results.
            
            Args:
                collector_func: Function to run concurrently
                validation_func: Optional validation function
            """
            results = []
            errors = []
            
            def worker_task(worker_id: int):
                """Task for each worker thread."""
                try:
                    for i in range(operations_per_worker):
                        result = collector_func(worker_id, i)
                        results.append(result)
                except Exception as e:
                    errors.append(f"Worker {worker_id}: {str(e)}")
            
            # Start all workers
            threads = []
            for worker_id in range(num_workers):
                thread = threading.Thread(target=worker_task, args=(worker_id,))
                threads.append(thread)
                thread.start()
            
            # Wait for all workers to complete
            for thread in threads:
                thread.join()
            
            scenario_results = {
                "total_operations": num_workers * operations_per_worker,
                "successful_operations": len(results),
                "errors": errors,
                "success_rate": len(results) / (num_workers * operations_per_worker),
                "results": results
            }
            
            # Run validation if provided
            if validation_func:
                validation_results = validation_func(results, errors)
                scenario_results["validation"] = validation_results
            
            return scenario_results
        
        return run_scenario
    
    @contextmanager
    def mock_api_responses(self, 
                          responses: Dict[str, Any],
                          delay: Optional[float] = None) -> Generator[Mock, None, None]:
        """
        Mock API responses for testing.
        
        Args:
            responses: Dictionary of method_name -> response mappings
            delay: Optional delay to simulate network latency
            
        Yields:
            Mock object configured with the responses
        """
        def create_response_func(response):
            def response_func(*args, **kwargs):
                if delay:
                    time.sleep(delay)
                return response
            return response_func
        
        with patch('src.collectors.base.BaseArchiveCollector') as mock_base:
            mock_instance = Mock()
            
            # Configure responses
            for method_name, response in responses.items():
                response_func = create_response_func(response)
                setattr(mock_instance, method_name, Mock(side_effect=response_func))
            
            mock_base.return_value = mock_instance
            yield mock_instance
    
    def create_performance_test(self, 
                               target_ops_per_second: int = 100,
                               test_duration: int = 10) -> Callable:
        """
        Create a performance test scenario.
        
        Args:
            target_ops_per_second: Target operations per second
            test_duration: Test duration in seconds
            
        Returns:
            Function that runs performance test
        """
        def run_performance_test(operation_func: Callable) -> Dict[str, Any]:
            """
            Run performance test and return metrics.
            
            Args:
                operation_func: Function to performance test
                
            Returns:
                Performance metrics dictionary
            """
            start_time = time.time()
            end_time = start_time + test_duration
            operations = 0
            errors = 0
            
            while time.time() < end_time:
                try:
                    operation_func()
                    operations += 1
                except Exception:
                    errors += 1
                
                # Brief pause to prevent overwhelming the system
                time.sleep(0.001)
            
            actual_duration = time.time() - start_time
            ops_per_second = operations / actual_duration
            
            return {
                "target_ops_per_second": target_ops_per_second,
                "actual_ops_per_second": ops_per_second,
                "total_operations": operations,
                "total_errors": errors,
                "error_rate": errors / (operations + errors) if (operations + errors) > 0 else 0,
                "duration": actual_duration,
                "performance_met": ops_per_second >= target_ops_per_second * 0.9  # 90% of target
            }
        
        return run_performance_test


class ArchiveTestValidator:
    """
    Specialized validator for archive testing.
    
    Provides utilities specifically for validating archive files,
    structure, and data integrity.
    """
    
    @staticmethod
    def validate_metadata_consistency(record: Dict[str, Any]) -> List[str]:
        """
        Validate metadata consistency in a record.
        
        Args:
            record: Record to validate
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Check required metadata fields
        required_fields = ['metadata']
        for field in required_fields:
            if field not in record:
                errors.append(f"Missing required field: {field}")
                continue
        
        if 'metadata' in record:
            metadata = record['metadata']
            required_metadata = ['collector_type', 'collection_timestamp']
            
            for field in required_metadata:
                if field not in metadata:
                    errors.append(f"Missing metadata field: {field}")
        
        return errors
    
    @staticmethod
    def validate_timestamps(records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate timestamp consistency across records.
        
        Args:
            records: List of records to validate
            
        Returns:
            Validation results dictionary
        """
        results = {
            "valid": True,
            "errors": [],
            "timestamp_range": None,
            "record_count": len(records)
        }
        
        timestamps = []
        
        for i, record in enumerate(records):
            if 'metadata' in record and 'collection_timestamp' in record['metadata']:
                try:
                    ts = datetime.fromisoformat(record['metadata']['collection_timestamp'])
                    timestamps.append(ts)
                except ValueError as e:
                    results["errors"].append(f"Record {i}: Invalid timestamp format - {str(e)}")
                    results["valid"] = False
        
        if timestamps:
            results["timestamp_range"] = {
                "earliest": min(timestamps).isoformat(),
                "latest": max(timestamps).isoformat(),
                "span_hours": (max(timestamps) - min(timestamps)).total_seconds() / 3600
            }
        
        return results
    
    @staticmethod
    def compare_with_original(original_data: Dict[str, Any], 
                            archived_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compare original data with archived data to verify preservation.
        
        Args:
            original_data: Original data from collector
            archived_data: Data read from archive
            
        Returns:
            Comparison results
        """
        results = {
            "data_preserved": True,
            "missing_fields": [],
            "extra_fields": [],
            "modified_fields": [],
            "field_count_original": 0,
            "field_count_archived": 0
        }
        
        # Extract data portion from archived record
        if 'data' in archived_data:
            archived_content = archived_data['data']
        else:
            archived_content = archived_data
        
        # Count fields
        def count_fields(obj, prefix=""):
            count = 0
            if isinstance(obj, dict):
                for key, value in obj.items():
                    count += 1
                    if isinstance(value, (dict, list)):
                        count += count_fields(value, f"{prefix}.{key}" if prefix else key)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    if isinstance(item, (dict, list)):
                        count += count_fields(item, f"{prefix}[{i}]" if prefix else f"[{i}]")
            return count
        
        results["field_count_original"] = count_fields(original_data)
        results["field_count_archived"] = count_fields(archived_content)
        
        # Deep comparison function
        def compare_objects(orig, arch, path=""):
            if type(orig) != type(arch):
                results["modified_fields"].append(f"{path}: type changed from {type(orig)} to {type(arch)}")
                results["data_preserved"] = False
                return
            
            if isinstance(orig, dict):
                orig_keys = set(orig.keys())
                arch_keys = set(arch.keys())
                
                missing = orig_keys - arch_keys
                extra = arch_keys - orig_keys
                
                for key in missing:
                    results["missing_fields"].append(f"{path}.{key}" if path else key)
                    results["data_preserved"] = False
                
                for key in extra:
                    results["extra_fields"].append(f"{path}.{key}" if path else key)
                
                for key in orig_keys & arch_keys:
                    new_path = f"{path}.{key}" if path else key
                    compare_objects(orig[key], arch[key], new_path)
            
            elif isinstance(orig, list):
                if len(orig) != len(arch):
                    results["modified_fields"].append(f"{path}: length changed from {len(orig)} to {len(arch)}")
                    results["data_preserved"] = False
                    return
                
                for i, (o_item, a_item) in enumerate(zip(orig, arch)):
                    new_path = f"{path}[{i}]" if path else f"[{i}]"
                    compare_objects(o_item, a_item, new_path)
            
            elif orig != arch:
                results["modified_fields"].append(f"{path}: value changed from {orig} to {arch}")
                results["data_preserved"] = False
        
        compare_objects(original_data, archived_content)
        
        return results


# Convenience functions for common testing patterns
def create_test_helper(collector_type: str) -> CollectorTestHelper:
    """Create a CollectorTestHelper for the specified type."""
    return CollectorTestHelper(collector_type)


def assert_jsonl_valid(file_path: Path, min_records: int = 1):
    """Assert that a JSONL file is valid and contains minimum records."""
    results = CollectorTestHelper("test").validate_jsonl_format(file_path)
    
    assert results["valid"], f"JSONL validation failed: {results.get('error', results.get('errors', []))}"
    assert results["valid_lines"] >= min_records, f"Expected at least {min_records} records, found {results['valid_lines']}"


def assert_archive_structure_valid(archive_path: Path, collector_type: str):
    """Assert that archive directory structure is valid."""
    helper = CollectorTestHelper(collector_type)
    results = helper.validate_archive_structure(archive_path)
    
    assert results["valid_structure"], f"Archive structure invalid: {results}"


@pytest.fixture
def slack_test_helper():
    """Pytest fixture for Slack collector testing."""
    helper = CollectorTestHelper("slack")
    yield helper
    helper.cleanup_temp_dirs()


@pytest.fixture  
def calendar_test_helper():
    """Pytest fixture for Calendar collector testing."""
    helper = CollectorTestHelper("calendar")
    yield helper
    helper.cleanup_temp_dirs()


@pytest.fixture
def drive_test_helper():
    """Pytest fixture for Drive collector testing."""
    helper = CollectorTestHelper("drive")
    yield helper
    helper.cleanup_temp_dirs()


@pytest.fixture
def employee_test_helper():
    """Pytest fixture for Employee collector testing."""
    helper = CollectorTestHelper("employee")
    yield helper
    helper.cleanup_temp_dirs()


if __name__ == "__main__":
    # Example usage
    print("Collector Test Helpers - Example Usage")
    
    # Create helper for Slack testing
    helper = CollectorTestHelper("slack")
    
    # Create mock collector
    mock_collector = helper.create_mock_collector()
    print(f"Mock collector created: {type(mock_collector)}")
    
    # Create temporary archive directory
    with helper.temporary_archive_dir() as archive_path:
        print(f"Temporary archive directory: {archive_path}")
        
        # Validate archive structure (will be invalid since empty)
        results = helper.validate_archive_structure(archive_path)
        print(f"Archive structure valid: {results['valid_structure']}")
    
    # Create performance test
    perf_test = helper.create_performance_test(target_ops_per_second=50)
    
    def simple_operation():
        """Simple operation for performance testing."""
        return sum(range(100))
    
    perf_results = perf_test(simple_operation)
    print(f"Performance test results: {perf_results['actual_ops_per_second']:.2f} ops/sec")
    
    helper.cleanup_temp_dirs()
    print("Cleanup completed")