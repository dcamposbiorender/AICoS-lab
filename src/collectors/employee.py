"""
EmployeeArchiveWrapper - Wrapper for existing scavenge EmployeeCollector.

This wrapper integrates the existing scavenge/src/collectors/employees.py collector
with the new BaseArchiveCollector interface, adding comprehensive ID mapping
and cross-referencing capabilities while preserving all employee data.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging

# Import our base collector
from src.collectors.base import BaseArchiveCollector

# Import the EmployeeCollector from the new location
try:
    from .employee_collector import EmployeeCollector
except ImportError as e:
    logging.warning(f"Could not import EmployeeCollector: {e}")
    EmployeeCollector = None

# Lab-grade mock collector for when scavenge import fails
class MockEmployeeCollector:
    """Mock EmployeeCollector for lab-grade testing when scavenge import fails."""
    
    def __init__(self, config_path=None):
        self.collection_results = {
            'status': 'success',
            'discovered': {'employees': 5},
            'collected': {'employees': 5}
        }
    
    def to_json(self):
        """Return mock employee data for lab testing."""
        from tests.fixtures.mock_employee_data import get_mock_collection_result
        return get_mock_collection_result()

logger = logging.getLogger(__name__)


class EmployeeArchiveWrapper(BaseArchiveCollector):
    """
    Wrapper for scavenge EmployeeCollector that provides BaseArchiveCollector interface.
    
    Uses composition pattern to wrap the existing collector while adding:
    - Comprehensive ID mapping and cross-referencing
    - Employee deduplication and conflict resolution
    - BaseArchiveCollector interface compliance
    - Circuit breaker and retry logic from base class
    - State management integration
    - Enhanced employee metadata and organizational processing
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize EmployeeArchiveWrapper with configuration validation.
        
        Args:
            config: Configuration dictionary for both wrapper and scavenge collector
        """
        super().__init__("employee", config or {})
        
        # Validate configuration
        self._validate_wrapper_config(config or {})
        
        # Initialize the underlying scavenge collector (or mock for lab-grade)
        if EmployeeCollector is None:
            logger.warning("Using MockEmployeeCollector for lab-grade testing")
            self.scavenge_collector = MockEmployeeCollector(config_path=None)
            self.is_mock_mode = True
        else:
            self.scavenge_collector = EmployeeCollector(config_path=None)
            self.is_mock_mode = False
        
        # Validate scavenge collector has expected components
        self._validate_scavenge_collector()
        
        # Configuration options
        self.enable_cross_reference = self.config.get('enable_cross_reference', True)
        self.deduplicate_by_email = self.config.get('deduplicate_by_email', True)
        self.include_inactive = self.config.get('include_inactive', True)
        
        logger.info("EmployeeArchiveWrapper initialized with scavenge collector")
    
    def collect(self) -> Dict[str, Any]:
        """
        Collect employee data using the scavenge collector and transform to archive format.
        
        This method integrates with the existing scavenge collector's multi-source discovery
        and adds comprehensive ID mapping and deduplication capabilities.
        
        Returns:
            Dictionary containing transformed data and metadata in BaseArchiveCollector format:
            {
                'data': {...},      # Transformed scavenge collector output
                'metadata': {...}   # Collection metadata
            }
        """
        logger.info("Starting Employee collection via scavenge collector")
        
        try:
            # Validate rate limiter is available (rate limiting integration check)
            if hasattr(self.scavenge_collector, 'rate_limiter'):
                rate_limiter = self.scavenge_collector.rate_limiter
                logger.info(f"Rate limiting: {rate_limiter.requests_per_second} req/sec")
            else:
                logger.warning("Rate limiter not found in scavenge collector - proceeding without rate limit validation")
            
            # Call the existing scavenge collector (inherits its rate limiting)
            scavenge_results = self.scavenge_collector.to_json()
            
            # Validate the scavenge collector output
            if not self._validate_scavenge_output(scavenge_results):
                raise ValueError(f"Invalid output from scavenge collector: {type(scavenge_results)}")
            
            # Check if collection failed
            if isinstance(scavenge_results, dict) and scavenge_results.get('error'):
                raise Exception(f"Scavenge collector failed: {scavenge_results['error']}")
            
            # Transform the results to our expected format
            transformed_data = self._transform_to_archive_format(scavenge_results)
            
            # Final validation of transformed data
            if not self._validate_transformed_output(transformed_data):
                raise ValueError("Transformation produced invalid output format")
            
            # Return in BaseArchiveCollector format
            return {
                'data': transformed_data,
                'metadata': self.get_metadata()
            }
            
        except Exception as e:
            logger.error(f"Employee collection failed: {str(e)}")
            raise Exception(f"Employee collection failed: {str(e)}")
    
    def get_state(self) -> Dict[str, Any]:
        """
        Get current collection state.
        
        Returns:
            Dictionary containing cursor and state information
        """
        with self._state_lock:
            # Base state from parent class
            base_state = self._state.copy()
            
            # Add Employee-specific state if available
            if hasattr(self.scavenge_collector, 'collection_results'):
                try:
                    scavenge_state = getattr(self.scavenge_collector, 'collection_results', {})
                    if isinstance(scavenge_state, dict):
                        # Extract discovered counts
                        discovered = scavenge_state.get('discovered', {})
                        merged = scavenge_state.get('merged', {})
                        
                        base_state.update({
                            'scavenge_cursor': scavenge_state.get('next_cursor'),
                            'employees_discovered': merged.get('total_employees', 0),
                            'slack_users_found': discovered.get('slack_users', 0),
                            'calendar_users_found': discovered.get('calendar_users', 0),
                            'drive_users_found': discovered.get('drive_users', 0),
                            'duplicates_resolved': merged.get('duplicates_resolved', 0)
                        })
                except (AttributeError, TypeError):
                    # Handle case where scavenge collector is mocked or doesn't have expected structure
                    pass
            
            return base_state
    
    def set_state(self, state: Dict[str, Any]) -> None:
        """
        Update collection state.
        
        Args:
            state: New state dictionary to merge with current state
        """
        with self._state_lock:
            self._state.update(state)
            
            # Pass relevant state to scavenge collector if needed
            if hasattr(self.scavenge_collector, 'collection_results'):
                if 'scavenge_cursor' in state:
                    self.scavenge_collector.collection_results['next_cursor'] = state['scavenge_cursor']
    
    def _transform_to_archive_format(self, scavenge_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform scavenge collector output to archive-compatible format.
        
        This method preserves all data from the scavenge collector while ensuring
        it's compatible with JSONL storage and our archive structure. It handles:
        - ID mapping creation and cross-referencing
        - Employee deduplication and conflict resolution
        - Organizational data enhancement
        - All metadata fields from scavenge collector
        - Error cases and malformed data
        
        Args:
            scavenge_data: Output from scavenge collector
            
        Returns:
            Transformed data ready for archive storage
        """
        if not isinstance(scavenge_data, dict):
            logger.warning(f"Unexpected scavenge data type: {type(scavenge_data)}")
            return {'raw_data': scavenge_data}
        
        # Start with the original data structure
        transformed = {}
        
        # Handle different data structures that might come from scavenge collector
        if 'error' in scavenge_data:
            # Error case - preserve error information
            transformed = {
                'collection_status': 'error',
                'error_details': scavenge_data,
                'transformation_timestamp': datetime.now(timezone.utc).isoformat()
            }
        else:
            # Successful collection - preserve all fields
            transformed = scavenge_data.copy()
            
            # Ensure consistent structure for archive storage
            # Handle both 'employees' and 'roster' keys from scavenge data
            employees = transformed.get('employees') or transformed.get('roster', [])
            if employees is None:
                employees = []
            
            # Process employees if we have them
            if isinstance(employees, list) and employees:
                # Deduplicate if configured
                if self.deduplicate_by_email:
                    employees = self._deduplicate_employees(employees)
                
                transformed['employees'] = self._process_employees_for_archive(employees)
            else:
                # No employees found - set empty list
                transformed['employees'] = []
            
            # Create ID mappings for cross-referencing
            if self.enable_cross_reference:
                transformed['id_mappings'] = self._create_cross_reference_mapping(transformed['employees'])
            
            # Add transformation metadata
            transformed['archive_transformation'] = {
                'transformer': 'EmployeeArchiveWrapper',
                'version': '1.0',
                'original_format': 'scavenge_collector',
                'id_mapping_enabled': self.enable_cross_reference,
                'deduplication_enabled': self.deduplicate_by_email,
                'transformation_timestamp': datetime.now(timezone.utc).isoformat(),
                'data_integrity': {
                    'employees_processed': len(employees) if isinstance(employees, list) else 0,
                    'duplicates_resolved': self._count_duplicates_resolved(employees) if isinstance(employees, list) else 0,
                    'id_mappings_created': len(transformed.get('id_mappings', {})) if self.enable_cross_reference else 0,
                    'active_employees': sum(1 for e in employees if isinstance(e, dict) and not e.get('deleted', False)) if isinstance(employees, list) else 0,
                    'contractor_count': sum(1 for e in employees if isinstance(e, dict) and e.get('is_contractor', False)) if isinstance(employees, list) else 0
                }
            }
        
        logger.debug(f"Transformed {len(str(scavenge_data))} chars to {len(str(transformed))} chars")
        return transformed
    
    def _deduplicate_employees(self, employees: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Deduplicate employees by email address, merging data from multiple sources.
        
        Args:
            employees: List of employee dictionaries
            
        Returns:
            Deduplicated list of employee dictionaries with merged data
        """
        if not employees:
            return []
        
        # Group employees by email
        email_groups = {}
        
        for employee in employees:
            if not isinstance(employee, dict):
                continue
            
            email = employee.get('email', '').lower()
            if not email:
                # Handle employees without email - use a unique key
                unique_key = f"no_email_{id(employee)}"
                email_groups[unique_key] = [employee]
            elif email in email_groups:
                email_groups[email].append(employee)
            else:
                email_groups[email] = [employee]
        
        # Merge duplicates within each group
        deduplicated = []
        for email, employee_group in email_groups.items():
            if len(employee_group) == 1:
                # No duplicates
                deduplicated.append(employee_group[0])
            else:
                # Merge duplicates
                merged_employee = self._merge_employee_records(employee_group)
                deduplicated.append(merged_employee)
        
        return deduplicated
    
    def _merge_employee_records(self, employee_records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Merge multiple employee records into a single comprehensive record.
        
        Args:
            employee_records: List of employee dictionaries to merge
            
        Returns:
            Single merged employee dictionary
        """
        if not employee_records:
            return {}
        
        if len(employee_records) == 1:
            return employee_records[0]
        
        # Start with the first record as base
        merged = employee_records[0].copy()
        
        # Merge sources list
        all_sources = set()
        for record in employee_records:
            sources = record.get('sources', [])
            if isinstance(sources, list):
                all_sources.update(sources)
            elif isinstance(sources, str):
                all_sources.add(sources)
        
        merged['sources'] = list(all_sources)
        
        # Merge fields from subsequent records, preferring non-empty values
        for record in employee_records[1:]:
            for key, value in record.items():
                if key == 'sources':
                    continue  # Already handled above
                
                # Prefer non-empty values
                if key not in merged or not merged[key]:
                    merged[key] = value
                elif value and (not merged[key] or len(str(value)) > len(str(merged[key]))):
                    # Prefer longer/more complete values
                    merged[key] = value
        
        # Add merge metadata
        merged['merge_info'] = {
            'records_merged': len(employee_records),
            'merged_at': datetime.now(timezone.utc).isoformat(),
            'sources_count': len(all_sources)
        }
        
        return merged
    
    def _process_employees_for_archive(self, employees: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process employees for archive storage with enhanced metadata.
        
        Args:
            employees: List of employee dictionaries from scavenge collector
            
        Returns:
            Processed employees with enhanced metadata and ID mappings
        """
        processed_employees = []
        
        for employee in employees:
            if not isinstance(employee, dict):
                continue
            
            processed_employee = employee.copy()
            
            # Create ID mapping for this employee
            processed_employee['id_mapping'] = self._create_employee_id_mapping(employee)
            
            # Add employee classification
            processed_employee['employee_classification'] = {
                'is_active': not employee.get('deleted', False),
                'is_contractor': employee.get('is_contractor', False),
                'has_complete_profile': self._assess_profile_completeness(employee),
                'primary_source': self._determine_primary_source(employee),
                'data_quality_score': self._calculate_data_quality_score(employee)
            }
            
            # Process organizational information
            if 'department' in employee or 'title' in employee or 'manager' in employee:
                processed_employee['organizational_info'] = self._process_organizational_data(employee)
            
            # Add contact information summary
            processed_employee['contact_summary'] = self._summarize_contact_info(employee)
            
            processed_employees.append(processed_employee)
        
        return processed_employees
    
    def _create_employee_id_mapping(self, employee: Dict[str, Any]) -> Dict[str, str]:
        """
        Create comprehensive ID mapping for a single employee.
        
        Args:
            employee: Employee dictionary
            
        Returns:
            Dictionary mapping ID types to values
        """
        id_mapping = {}
        
        # Standard ID fields
        id_fields = ['email', 'slack_id', 'calendar_id', 'google_workspace_id', 'employee_id']
        
        for field in id_fields:
            if field in employee and employee[field]:
                id_mapping[field] = employee[field]
        
        # Add derived mappings
        if 'email' in id_mapping:
            # Email-based IDs often match
            email = id_mapping['email']
            if 'calendar_id' not in id_mapping:
                id_mapping['calendar_id'] = email  # Usually the same
            if 'google_workspace_id' not in id_mapping:
                id_mapping['google_workspace_id'] = email  # Usually the same
        
        return id_mapping
    
    def _create_cross_reference_mapping(self, employees: List[Dict[str, Any]]) -> Dict[str, Dict[str, str]]:
        """
        Create cross-reference mapping for efficient lookups.
        
        Args:
            employees: List of processed employee dictionaries
            
        Returns:
            Dictionary containing various ID cross-reference mappings
        """
        cross_ref = {
            'slack_to_email': {},
            'email_to_slack': {},
            'calendar_to_email': {},
            'email_to_calendar': {},
            'employee_id_to_email': {},
            'email_to_employee_id': {}
        }
        
        for employee in employees:
            if not isinstance(employee, dict):
                continue
            
            # Handle both processed employees (with id_mapping) and raw employees
            id_mapping = employee.get('id_mapping', {})
            if not id_mapping:
                # Create id_mapping from raw employee data
                id_mapping = self._create_employee_id_mapping(employee)
            
            email = id_mapping.get('email')
            
            if email:
                # Slack mappings
                slack_id = id_mapping.get('slack_id')
                if slack_id:
                    cross_ref['slack_to_email'][slack_id] = email
                    cross_ref['email_to_slack'][email] = slack_id
                
                # Calendar mappings
                calendar_id = id_mapping.get('calendar_id')
                if calendar_id:
                    cross_ref['calendar_to_email'][calendar_id] = email
                    cross_ref['email_to_calendar'][email] = calendar_id
                
                # Employee ID mappings
                employee_id = id_mapping.get('employee_id')
                if employee_id:
                    cross_ref['employee_id_to_email'][employee_id] = email
                    cross_ref['email_to_employee_id'][email] = employee_id
        
        return cross_ref
    
    def _assess_profile_completeness(self, employee: Dict[str, Any]) -> bool:
        """
        Assess whether an employee has a complete profile.
        
        Args:
            employee: Employee dictionary
            
        Returns:
            True if profile is considered complete, False otherwise
        """
        required_fields = ['email', 'first_name', 'last_name']
        recommended_fields = ['title', 'department', 'slack_id']
        
        # All required fields must be present and non-empty
        for field in required_fields:
            if not employee.get(field):
                return False
        
        # At least 2 recommended fields should be present
        present_recommended = sum(1 for field in recommended_fields if employee.get(field))
        return present_recommended >= 2
    
    def _determine_primary_source(self, employee: Dict[str, Any]) -> str:
        """
        Determine the primary data source for an employee.
        
        Args:
            employee: Employee dictionary
            
        Returns:
            Primary source name
        """
        sources = employee.get('sources', [])
        if not sources:
            return 'unknown'
        
        if isinstance(sources, str):
            return sources
        
        if isinstance(sources, list):
            if not sources:
                return 'unknown'
            
            # Prefer sources in this order: slack, calendar, drive
            source_priority = ['slack', 'calendar', 'drive']
            for preferred_source in source_priority:
                if preferred_source in sources:
                    return preferred_source
            
            return sources[0]
        
        return 'unknown'
    
    def _calculate_data_quality_score(self, employee: Dict[str, Any]) -> float:
        """
        Calculate a data quality score for an employee record.
        
        Args:
            employee: Employee dictionary
            
        Returns:
            Score between 0.0 and 1.0
        """
        score = 0.0
        max_score = 0.0
        
        # Core fields (weight: 0.4)
        core_fields = ['email', 'first_name', 'last_name']
        for field in core_fields:
            max_score += 0.4 / len(core_fields)
            if employee.get(field):
                score += 0.4 / len(core_fields)
        
        # Professional fields (weight: 0.3)
        professional_fields = ['title', 'department', 'manager']
        for field in professional_fields:
            max_score += 0.3 / len(professional_fields)
            if employee.get(field):
                score += 0.3 / len(professional_fields)
        
        # ID fields (weight: 0.3)
        id_fields = ['slack_id', 'calendar_id', 'employee_id']
        for field in id_fields:
            max_score += 0.3 / len(id_fields)
            if employee.get(field):
                score += 0.3 / len(id_fields)
        
        return score if max_score == 0 else score / max_score
    
    def _process_organizational_data(self, employee: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process organizational data for an employee.
        
        Args:
            employee: Employee dictionary
            
        Returns:
            Processed organizational information
        """
        org_info = {}
        
        # Normalize department
        department = employee.get('department', '')
        if department:
            org_info['department_normalized'] = self._normalize_department_name(department)
            org_info['department_original'] = department
        
        # Process reporting structure
        reporting_info = {}
        if 'manager' in employee:
            reporting_info['has_manager'] = bool(employee['manager'])
            if employee['manager']:
                reporting_info['manager_email'] = employee['manager']
        
        if 'title' in employee:
            reporting_info['title'] = employee['title']
            reporting_info['is_manager'] = self._is_management_title(employee['title'])
        
        org_info['reporting_structure'] = reporting_info
        
        return org_info
    
    def _summarize_contact_info(self, employee: Dict[str, Any]) -> Dict[str, Any]:
        """
        Summarize contact information for an employee.
        
        Args:
            employee: Employee dictionary
            
        Returns:
            Contact information summary
        """
        contact_info = {
            'has_email': bool(employee.get('email')),
            'has_slack': bool(employee.get('slack_id')),
            'has_calendar': bool(employee.get('calendar_id')),
            'contact_methods': []
        }
        
        if contact_info['has_email']:
            contact_info['contact_methods'].append('email')
        if contact_info['has_slack']:
            contact_info['contact_methods'].append('slack')
        if contact_info['has_calendar']:
            contact_info['contact_methods'].append('calendar')
        
        contact_info['contact_score'] = len(contact_info['contact_methods']) / 3.0
        
        return contact_info
    
    def _normalize_department_name(self, department: str) -> str:
        """Normalize department name for consistency."""
        if not department:
            return ''
        
        dept_lower = department.lower().strip()
        
        # Common normalizations
        if 'engineer' in dept_lower or 'dev' in dept_lower or 'tech' in dept_lower:
            return 'Engineering'
        elif 'product' in dept_lower or 'pm' in dept_lower:
            return 'Product'
        elif 'market' in dept_lower:
            return 'Marketing'
        elif 'sale' in dept_lower:
            return 'Sales'
        elif 'hr' in dept_lower or 'people' in dept_lower:
            return 'Human Resources'
        elif 'finance' in dept_lower or 'accounting' in dept_lower:
            return 'Finance'
        elif 'ops' in dept_lower or 'operation' in dept_lower:
            return 'Operations'
        else:
            return department.title()
    
    def _is_management_title(self, title: str) -> bool:
        """Check if a title indicates management role."""
        if not title:
            return False
        
        title_lower = title.lower()
        management_keywords = ['manager', 'director', 'vp', 'ceo', 'cto', 'cfo', 'chief', 'head', 'lead']
        
        return any(keyword in title_lower for keyword in management_keywords)
    
    def _count_duplicates_resolved(self, employees: List[Dict[str, Any]]) -> int:
        """Count how many duplicate records were resolved."""
        if not employees:
            return 0
        
        duplicate_count = 0
        for employee in employees:
            if isinstance(employee, dict) and 'merge_info' in employee:
                records_merged = employee['merge_info'].get('records_merged', 1)
                if records_merged > 1:
                    duplicate_count += records_merged - 1  # Count extra records that were merged
        
        return duplicate_count
    
    def _validate_scavenge_output(self, data: Dict[str, Any]) -> bool:
        """
        Validate that scavenge collector output contains expected structure.
        
        Args:
            data: Output from scavenge collector
            
        Returns:
            True if data structure is valid, False otherwise
        """
        if not isinstance(data, dict):
            logger.warning(f"Scavenge collector output is not a dict: {type(data)}")
            return False
        
        # If there's an error, it's still valid (error case)
        if 'error' in data:
            logger.info("Scavenge collector returned error - treating as valid error response")
            return True
        
        # For successful collection, be flexible about structure
        logger.debug(f"Validation found employee data with keys: {list(data.keys())}")
        return True  # Accept any dict structure - preserve everything
    
    def _validate_transformed_output(self, data: Dict[str, Any]) -> bool:
        """
        Validate that transformed output is in correct format for archiving.
        
        Args:
            data: Transformed data output
            
        Returns:
            True if transformed data is valid, False otherwise
        """
        if not isinstance(data, dict):
            logger.error(f"Transformed output is not a dict: {type(data)}")
            return False
        
        # Check for required structure
        if 'collection_status' in data and data['collection_status'] == 'error':
            # Error case - should have error_details
            if 'error_details' not in data:
                logger.error("Error case missing error_details")
                return False
            logger.debug("Validated error case transformation")
            return True
        
        # Success case - should have basic structure
        required_fields = ['employees', 'archive_transformation']
        missing_fields = []
        
        for field in required_fields:
            if field not in data:
                missing_fields.append(field)
        
        if missing_fields:
            logger.error(f"Transformed output missing required fields: {missing_fields}")
            return False
        
        # Validate archive transformation metadata
        archive_meta = data.get('archive_transformation', {})
        required_meta = ['transformer', 'version', 'transformation_timestamp']
        missing_meta = []
        
        for meta_field in required_meta:
            if meta_field not in archive_meta:
                missing_meta.append(meta_field)
        
        if missing_meta:
            logger.error(f"Archive transformation metadata missing fields: {missing_meta}")
            return False
        
        # Check JSON serializability (critical for JSONL storage)
        try:
            import json
            json.dumps(data)
            logger.debug("Transformed output is JSON serializable")
        except (TypeError, ValueError) as e:
            logger.error(f"Transformed output is not JSON serializable: {e}")
            return False
        
        logger.debug("Transformed output validation successful")
        return True
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get collection statistics from the underlying scavenge collector.
        
        Returns:
            Dictionary with collection statistics
        """
        if hasattr(self.scavenge_collector, 'collection_results'):
            return getattr(self.scavenge_collector, 'collection_results', {})
        
        return {
            'discovered': {'slack_users': 0, 'calendar_users': 0, 'drive_users': 0},
            'merged': {'total_employees': 0, 'duplicates_resolved': 0},
            'sources_active': []
        }
    
    def _validate_wrapper_config(self, config: Dict[str, Any]) -> None:
        """
        Validate wrapper configuration parameters.
        
        Args:
            config: Configuration dictionary to validate
            
        Raises:
            ValueError: If configuration is invalid
        """
        if not isinstance(config, dict):
            raise ValueError(f"Configuration must be a dictionary, got {type(config)}")
        
        # Validate numeric settings
        numeric_settings = ['max_employees']
        for setting in numeric_settings:
            if setting in config:
                value = config[setting]
                if not isinstance(value, (int, float)) or value < 0:
                    raise ValueError(f"Invalid configuration: {setting} must be a non-negative number")
        
        # Validate boolean settings
        boolean_settings = ['enable_cross_reference', 'deduplicate_by_email', 'include_inactive']
        for setting in boolean_settings:
            if setting in config:
                if not isinstance(config[setting], bool):
                    raise ValueError(f"Invalid configuration: {setting} must be boolean")
        
        logger.debug(f"Configuration validation passed for {len(config)} settings")
    
    def _validate_scavenge_collector(self) -> None:
        """
        Validate that the scavenge collector has expected components for integration.
        
        Raises:
            ValueError: If scavenge collector is missing expected components
        """
        if not hasattr(self.scavenge_collector, 'to_json'):
            raise ValueError("Scavenge collector missing to_json method")
        
        if not hasattr(self.scavenge_collector, 'rate_limiter'):
            logger.warning("Scavenge collector missing rate_limiter attribute - rate limiting validation may not work")
        else:
            # Validate rate limiter has expected methods
            rate_limiter = self.scavenge_collector.rate_limiter
            required_methods = ['wait_for_rate_limit']
            missing_methods = []
            
            for method in required_methods:
                if not hasattr(rate_limiter, method):
                    missing_methods.append(method)
            
            if missing_methods:
                logger.warning(f"Rate limiter missing methods: {missing_methods}")
        
        logger.debug("Scavenge collector validation completed")
    
    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"<EmployeeArchiveWrapper(scavenge_collector={self.scavenge_collector}, state={self.get_state()})>"


# Convenience function for creating wrapper instances
def create_employee_wrapper(config: Optional[Dict[str, Any]] = None) -> EmployeeArchiveWrapper:
    """
    Create an EmployeeArchiveWrapper instance with optional configuration.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Configured EmployeeArchiveWrapper instance
    """
    return EmployeeArchiveWrapper(config)