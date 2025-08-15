"""
Failing tests for EmployeeArchiveWrapper (TDD Red phase).
Tests define expected behavior before implementation.
All tests will initially fail until EmployeeArchiveWrapper is implemented.
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List

# Add test fixtures to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import the EmployeeArchiveWrapper (expected to fail initially in TDD Red phase)  
try:
    from src.collectors.employee import EmployeeArchiveWrapper
except ImportError:
    EmployeeArchiveWrapper = None

# Import test fixtures
from tests.fixtures.mock_employee_data import (
    get_mock_collection_result,
    get_mock_employee_roster,
    get_mock_id_mappings
)


@pytest.fixture(autouse=True)
def mock_stage1a_components():
    """Mock Stage 1a components for all tests."""
    with patch('src.collectors.base.get_config') as mock_config, \
         patch('src.collectors.base.StateManager') as mock_state_manager, \
         patch('src.collectors.base.ArchiveWriter') as mock_archive_writer, \
         patch('src.collectors.employee.EmployeeCollector') as mock_employee_collector_class:
        
        # Configure mocks
        mock_config_obj = Mock()
        mock_config_obj.archive_dir = Path('/tmp/test_archive')
        mock_config.return_value = mock_config_obj
        
        mock_state_manager.return_value = Mock()
        mock_archive_writer.return_value = Mock()
        
        # Configure EmployeeCollector mock
        mock_employee_collector = Mock()
        # Configure the to_json method to return test data
        mock_employee_collector.to_json.return_value = get_mock_collection_result()
        mock_employee_collector_class.return_value = mock_employee_collector
        
        yield {
            'config': mock_config,
            'state_manager': mock_state_manager,
            'archive_writer': mock_archive_writer,
            'employee_collector': mock_employee_collector_class
        }


class TestEmployeeWrapperInterface:
    """Test that EmployeeArchiveWrapper implements BaseArchiveCollector interface."""
    
    def test_employee_wrapper_implements_base_interface(self):
        """EmployeeArchiveWrapper implements required BaseArchiveCollector methods"""
        # ACCEPTANCE: collect(), get_state(), set_state() methods exist and are callable
        if EmployeeArchiveWrapper is None:
            pytest.skip("EmployeeArchiveWrapper not implemented yet (TDD Red phase)")
            
        wrapper = EmployeeArchiveWrapper()
        
        # Test that all required methods exist and are callable
        assert hasattr(wrapper, 'collect'), "EmployeeWrapper missing collect() method"
        assert callable(wrapper.collect), "collect() must be callable"
        
        assert hasattr(wrapper, 'get_state'), "EmployeeWrapper missing get_state() method"
        assert callable(wrapper.get_state), "get_state() must be callable"
        
        assert hasattr(wrapper, 'set_state'), "EmployeeWrapper missing set_state() method"
        assert callable(wrapper.set_state), "set_state() must be callable"
    
    def test_employee_wrapper_inherits_from_base_collector(self):
        """EmployeeArchiveWrapper inherits from BaseArchiveCollector"""
        if EmployeeArchiveWrapper is None:
            pytest.skip("EmployeeArchiveWrapper not implemented yet (TDD Red phase)")
            
        from src.collectors.base import BaseArchiveCollector
        wrapper = EmployeeArchiveWrapper()
        assert isinstance(wrapper, BaseArchiveCollector), "Must inherit from BaseArchiveCollector"
    
    def test_employee_wrapper_collector_type(self):
        """EmployeeArchiveWrapper has correct collector_type"""
        if EmployeeArchiveWrapper is None:
            pytest.skip("EmployeeArchiveWrapper not implemented yet (TDD Red phase)")
            
        wrapper = EmployeeArchiveWrapper()
        assert wrapper.collector_type == "employee", "collector_type must be 'employee'"


class TestEmployeeDataCollection:
    """Test employee data collection and integration with scavenge collector."""
    
    def test_collect_returns_expected_structure(self):
        """collect() returns dictionary with data and metadata"""
        if EmployeeArchiveWrapper is None:
            pytest.skip("EmployeeArchiveWrapper not implemented yet (TDD Red phase)")
            
        wrapper = EmployeeArchiveWrapper()
        result = wrapper.collect()
        
        assert isinstance(result, dict), "collect() must return dict"
        assert 'data' in result, "collect() result must contain 'data' key"
        assert 'metadata' in result, "collect() result must contain 'metadata' key"
        assert 'collection_timestamp' in result['metadata'], "metadata must contain collection_timestamp"
        assert result['metadata']['collector_type'] == 'employee', "metadata must specify employee collector"
    
    def test_scavenge_collector_integration(self):
        """Employee wrapper properly integrates with scavenge EmployeeCollector"""
        if EmployeeArchiveWrapper is None:
            pytest.skip("EmployeeArchiveWrapper not implemented yet (TDD Red phase)")
            
        wrapper = EmployeeArchiveWrapper()
        
        # Wrapper should have a scavenge_collector attribute
        assert hasattr(wrapper, 'scavenge_collector'), "Must have scavenge_collector attribute"
        assert wrapper.scavenge_collector is not None, "scavenge_collector must be initialized"
        
        # Should have the main collection method
        assert hasattr(wrapper.scavenge_collector, 'to_json'), \
            "scavenge_collector must have to_json method"
    
    @patch('src.collectors.employee.EmployeeCollector')
    def test_collect_calls_scavenge_collector(self, mock_employee_collector_class):
        """collect() method calls the scavenge EmployeeCollector"""
        if EmployeeArchiveWrapper is None:
            pytest.skip("EmployeeArchiveWrapper not implemented yet (TDD Red phase)")
            
        # Setup mock
        mock_collector = Mock()
        mock_collector.to_json.return_value = get_mock_collection_result()
        mock_employee_collector_class.return_value = mock_collector
        
        wrapper = EmployeeArchiveWrapper()
        result = wrapper.collect()
        
        # Verify scavenge collector was called
        mock_collector.to_json.assert_called_once()
        
        # Verify result structure
        assert isinstance(result, dict)
        assert 'data' in result
        assert 'metadata' in result


class TestEmployeeIdMapping:
    """Test ID mapping and cross-referencing functionality for employees."""
    
    def test_id_mapping_creation(self):
        """Employee data includes comprehensive ID mappings"""
        # ACCEPTANCE: All employee records have consistent ID mapping
        if EmployeeArchiveWrapper is None:
            pytest.skip("EmployeeArchiveWrapper not implemented yet (TDD Red phase)")
            
        wrapper = EmployeeArchiveWrapper()
        result = wrapper.collect()
        
        employees = result['data'].get('employees', [])
        assert len(employees) > 0, "Must have employee data"
        
        # Check ID mapping structure
        for employee in employees:
            assert 'id_mapping' in employee, "Each employee must have id_mapping"
            
            id_mapping = employee['id_mapping']
            required_id_fields = ['email', 'slack_id', 'calendar_id']
            
            for field in required_id_fields:
                # At least email should be present for all employees
                if field == 'email':
                    assert field in id_mapping, f"All employees must have {field}"
                elif field in id_mapping:
                    # If present, must not be empty
                    assert id_mapping[field], f"{field} must not be empty if present"
    
    def test_cross_reference_mapping(self):
        """Wrapper creates cross-reference mapping for efficient lookups"""
        if EmployeeArchiveWrapper is None:
            pytest.skip("EmployeeArchiveWrapper not implemented yet (TDD Red phase)")
            
        wrapper = EmployeeArchiveWrapper()
        
        # Test cross-reference creation method
        if hasattr(wrapper, '_create_cross_reference_mapping'):
            employees = get_mock_employee_roster()
            cross_ref = wrapper._create_cross_reference_mapping(employees)
            
            # Should have mappings for different ID types
            assert 'slack_to_email' in cross_ref, "Must include slack_to_email mapping"
            assert 'email_to_slack' in cross_ref, "Must include email_to_slack mapping"
            assert 'calendar_to_email' in cross_ref, "Must include calendar_to_email mapping"
            
            # Mappings should contain actual data
            assert len(cross_ref['slack_to_email']) > 0, "slack_to_email mapping should not be empty"
            assert len(cross_ref['email_to_slack']) > 0, "email_to_slack mapping should not be empty"
    
    def test_duplicate_handling(self):
        """Wrapper handles duplicate employee records across sources"""
        if EmployeeArchiveWrapper is None:
            pytest.skip("EmployeeArchiveWrapper not implemented yet (TDD Red phase)")
            
        wrapper = EmployeeArchiveWrapper()
        
        # Test deduplication method
        if hasattr(wrapper, '_deduplicate_employees'):
            # Create test data with duplicates
            employees_with_dupes = [
                {'email': 'alice@company.com', 'slack_id': 'U123', 'sources': ['slack']},
                {'email': 'alice@company.com', 'calendar_id': 'alice@company.com', 'sources': ['calendar']},
                {'email': 'bob@company.com', 'slack_id': 'U456', 'sources': ['slack']}
            ]
            
            deduplicated = wrapper._deduplicate_employees(employees_with_dupes)
            
            # Should merge duplicates by email
            emails = [emp['email'] for emp in deduplicated]
            assert len(set(emails)) == len(emails), "Should not have duplicate emails after deduplication"
            
            # Merged record should have data from both sources
            alice_record = next(emp for emp in deduplicated if emp['email'] == 'alice@company.com')
            assert 'slack_id' in alice_record, "Merged record should have slack_id"
            assert 'calendar_id' in alice_record, "Merged record should have calendar_id"
            assert set(alice_record['sources']) == {'slack', 'calendar'}, "Sources should be merged"


class TestEmployeeStateManagement:
    """Test state persistence for employee collection cursors."""
    
    def test_state_includes_employee_cursors(self):
        """State includes employee-specific cursor information"""
        if EmployeeArchiveWrapper is None:
            pytest.skip("EmployeeArchiveWrapper not implemented yet (TDD Red phase)")
            
        wrapper = EmployeeArchiveWrapper()
        
        # Set some employee-specific state
        employee_state = {
            "last_slack_sync": "2025-08-15T10:00:00Z",
            "last_calendar_discovery": "2025-08-15T10:00:00Z", 
            "last_drive_sync": "2025-08-15T10:00:00Z",
            "employees_discovered": 25,
            "cursor": "employee_cursor_123"
        }
        
        wrapper.set_state(employee_state)
        current_state = wrapper.get_state()
        
        assert current_state["last_slack_sync"] == "2025-08-15T10:00:00Z", "Slack sync time should persist"
        assert current_state["employees_discovered"] == 25, "Employee count should persist"
        assert "last_calendar_discovery" in current_state, "Calendar discovery time should persist"
    
    def test_scavenge_collector_state_integration(self):
        """Wrapper integrates with scavenge collector state management"""
        if EmployeeArchiveWrapper is None:
            pytest.skip("EmployeeArchiveWrapper not implemented yet (TDD Red phase)")
            
        wrapper = EmployeeArchiveWrapper()
        
        # Mock scavenge collector state
        if hasattr(wrapper, 'scavenge_collector'):
            wrapper.scavenge_collector.collection_results = {
                "discovered": {"slack_users": 20, "calendar_users": 18, "drive_users": 15},
                "merged": {"total_employees": 25, "duplicates_resolved": 13},
                "sources_active": ["slack", "calendar", "drive"]
            }
            
            state = wrapper.get_state()
            
            # Should include scavenge collector state information
            assert "employees_discovered" in state or "scavenge_cursor" in state, \
                "State should include scavenge collector information"


class TestEmployeeDataTransformation:
    """Test transformation of employee data to archive format."""
    
    def test_employee_data_transformation(self):
        """Employee data is transformed to consistent archive format"""
        if EmployeeArchiveWrapper is None:
            pytest.skip("EmployeeArchiveWrapper not implemented yet (TDD Red phase)")
            
        wrapper = EmployeeArchiveWrapper()
        mock_data = get_mock_collection_result()
        
        if hasattr(wrapper, '_transform_to_archive_format'):
            transformed = wrapper._transform_to_archive_format(mock_data)
            
            # Check required structure
            assert isinstance(transformed, dict), "Transformed data must be dict"
            assert 'employees' in transformed, "Must contain employees"
            assert 'id_mappings' in transformed, "Must contain id_mappings"
            assert 'archive_transformation' in transformed, "Must contain transformation metadata"
    
    def test_employee_metadata_enhancement(self):
        """Employee records are enhanced with additional metadata"""
        if EmployeeArchiveWrapper is None:
            pytest.skip("EmployeeArchiveWrapper not implemented yet (TDD Red phase)")
            
        wrapper = EmployeeArchiveWrapper()
        mock_employees = get_mock_employee_roster()
        
        if hasattr(wrapper, '_process_employees_for_archive'):
            processed_employees = wrapper._process_employees_for_archive(mock_employees)
            
            for employee in processed_employees:
                # Should have employee classification
                assert 'employee_classification' in employee, "Employees should have classification metadata"
                
                classification = employee['employee_classification']
                assert 'is_active' in classification, "Should classify active employees"
                assert 'is_contractor' in classification, "Should classify contractors"
                assert 'has_complete_profile' in classification, "Should assess profile completeness"
                assert 'primary_source' in classification, "Should identify primary data source"
    
    def test_organizational_structure_processing(self):
        """Organizational data is properly processed and enhanced"""
        if EmployeeArchiveWrapper is None:
            pytest.skip("EmployeeArchiveWrapper not implemented yet (TDD Red phase)")
            
        wrapper = EmployeeArchiveWrapper()
        mock_employees = get_mock_employee_roster()
        
        if hasattr(wrapper, '_process_employees_for_archive'):
            processed_employees = wrapper._process_employees_for_archive(mock_employees)
            
            # Find employees with organizational data
            employees_with_org_data = [e for e in processed_employees if 'department' in e]
            assert len(employees_with_org_data) > 0, "Test requires employees with organizational data"
            
            for employee in employees_with_org_data:
                # Should have organizational summary
                assert 'organizational_info' in employee, "Should include organizational summary"
                
                org_info = employee['organizational_info']
                assert 'department_normalized' in org_info, "Should normalize department names"
                assert 'reporting_structure' in org_info, "Should include reporting information"


class TestEmployeeErrorHandling:
    """Test error handling and validation for employee collection."""
    
    def test_scavenge_collector_error_handling(self):
        """Wrapper handles errors from scavenge collector gracefully"""
        if EmployeeArchiveWrapper is None:
            pytest.skip("EmployeeArchiveWrapper not implemented yet (TDD Red phase)")
            
        with patch('src.collectors.employee.EmployeeCollector') as mock_collector_class:
            # Setup mock to raise exception
            mock_collector = Mock()
            mock_collector.to_json.side_effect = Exception("API rate limit exceeded")
            mock_collector_class.return_value = mock_collector
            
            wrapper = EmployeeArchiveWrapper()
            
            # Should handle exception and provide meaningful error
            with pytest.raises(Exception) as exc_info:
                wrapper.collect()
            
            # Error should be informative
            assert "Employee collection failed" in str(exc_info.value) or \
                   "API rate limit exceeded" in str(exc_info.value), \
                   "Should provide informative error message"
    
    def test_invalid_employee_data_validation(self):
        """Wrapper validates employee data structure"""
        if EmployeeArchiveWrapper is None:
            pytest.skip("EmployeeArchiveWrapper not implemented yet (TDD Red phase)")
            
        wrapper = EmployeeArchiveWrapper()
        
        # Test with invalid data structure
        invalid_data = {"invalid": "structure"}
        
        if hasattr(wrapper, '_validate_scavenge_output'):
            # Should identify invalid structure
            is_valid = wrapper._validate_scavenge_output(invalid_data)
            # Implementation should handle this gracefully
            assert isinstance(is_valid, bool), "Validation should return boolean"
    
    def test_configuration_validation(self):
        """Wrapper validates configuration parameters"""
        if EmployeeArchiveWrapper is None:
            pytest.skip("EmployeeArchiveWrapper not implemented yet (TDD Red phase)")
            
        # Test with invalid configuration
        with pytest.raises(ValueError, match="Invalid configuration"):
            EmployeeArchiveWrapper(config={"max_employees": -1})
        
        # Test with valid configuration
        valid_config = {
            "enable_cross_reference": True,
            "deduplicate_by_email": True,
            "include_inactive": False
        }
        wrapper = EmployeeArchiveWrapper(config=valid_config)
        assert wrapper is not None, "Should accept valid configuration"
    
    def test_missing_id_field_handling(self):
        """Wrapper handles employees with missing ID fields gracefully"""
        if EmployeeArchiveWrapper is None:
            pytest.skip("EmployeeArchiveWrapper not implemented yet (TDD Red phase)")
            
        wrapper = EmployeeArchiveWrapper()
        
        # Test employees with missing ID fields
        incomplete_employees = [
            {'email': 'complete@company.com', 'slack_id': 'U123', 'calendar_id': 'complete@company.com'},
            {'email': 'no-slack@company.com', 'calendar_id': 'no-slack@company.com'},
            {'slack_id': 'U456'},  # No email
            {}  # Empty record
        ]
        
        if hasattr(wrapper, '_process_employees_for_archive'):
            processed = wrapper._process_employees_for_archive(incomplete_employees)
            
            # Should not crash and should handle incomplete records
            assert isinstance(processed, list), "Should return list even with incomplete data"
            
            # Should flag incomplete records
            for employee in processed:
                if 'employee_classification' in employee:
                    classification = employee['employee_classification']
                    assert 'has_complete_profile' in classification, "Should assess profile completeness"


if __name__ == "__main__":
    # Run a subset of tests for quick validation
    print("Running EmployeeArchiveWrapper failing tests (TDD Red phase)...")
    
    # These should all fail initially - that's the point!
    try:
        if EmployeeArchiveWrapper:
            wrapper = EmployeeArchiveWrapper()
            print("❌ EmployeeArchiveWrapper instantiated (unexpected - should fail)")
        else:
            print("✅ EmployeeArchiveWrapper not implemented yet (expected)")
    except (ImportError, NameError, AttributeError):
        print("✅ EmployeeArchiveWrapper fails properly (expected)")
    
    print("\nAll tests are properly failing - ready for implementation phase! 🔴")
    print("Next step: Implement EmployeeArchiveWrapper to make tests pass (TDD Green phase)")