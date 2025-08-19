"""
Unified Error Handling Framework for CLI Tools

Provides consistent error classes and user-friendly error messages across
all CLI tools. Includes proper exit codes, remediation suggestions, and
graceful degradation when dependencies are unavailable.

Usage:
    from src.cli.errors import CLIError, QueryError, handle_cli_error
    
    try:
        # CLI operation
        pass
    except QueryError as e:
        handle_cli_error(e, quiet=False)
        sys.exit(e.exit_code)
"""

import sys
import traceback
from typing import Optional, Dict, Any
import click
from pathlib import Path


class CLIError(Exception):
    """Base class for all CLI errors with user-friendly messages"""
    
    exit_code = 1
    category = "General"
    
    def __init__(self, message: str, suggestion: Optional[str] = None, 
                 technical_details: Optional[str] = None):
        """
        Initialize CLI error
        
        Args:
            message: User-friendly error message
            suggestion: Optional remediation suggestion
            technical_details: Optional technical details for debugging
        """
        super().__init__(message)
        self.message = message
        self.suggestion = suggestion
        self.technical_details = technical_details


class ConfigurationError(CLIError):
    """Configuration or setup related errors"""
    exit_code = 2
    category = "Configuration"


class QueryError(CLIError):
    """Query execution errors"""
    exit_code = 3
    category = "Query"


class DatabaseError(CLIError):
    """Database connection or operation errors"""
    exit_code = 4
    category = "Database"


class DependencyError(CLIError):
    """Missing or unavailable dependency errors"""
    exit_code = 5
    category = "Dependency"


class AuthenticationError(CLIError):
    """Authentication or credential errors"""
    exit_code = 6
    category = "Authentication"


class ValidationError(CLIError):
    """Input validation errors"""
    exit_code = 7
    category = "Validation"


class PerformanceError(CLIError):
    """Performance threshold exceeded errors"""
    exit_code = 8
    category = "Performance"


def handle_cli_error(error: Exception, quiet: bool = False, verbose: bool = False) -> int:
    """
    Handle CLI errors with consistent formatting and exit codes
    
    Args:
        error: The exception that occurred
        quiet: If True, minimize output
        verbose: If True, show technical details
        
    Returns:
        Appropriate exit code
    """
    if quiet:
        return getattr(error, 'exit_code', 1)
    
    # Determine error styling
    if isinstance(error, CLIError):
        category = error.category
        exit_code = error.exit_code
        message = error.message
        suggestion = error.suggestion
        technical_details = error.technical_details
    else:
        category = "Unexpected"
        exit_code = 1
        message = str(error)
        suggestion = "Please check your input and try again"
        technical_details = traceback.format_exc() if verbose else None
    
    # Format error output with colors
    click.echo(f"❌ {click.style(category + ' Error:', fg='red', bold=True)} {message}", err=True)
    
    if suggestion:
        click.echo(f"💡 {click.style('Suggestion:', fg='yellow', bold=True)} {suggestion}", err=True)
    
    if verbose and technical_details:
        click.echo(f"\n🔍 {click.style('Technical Details:', fg='cyan', bold=True)}", err=True)
        click.echo(technical_details, err=True)
    elif not verbose and hasattr(error, 'technical_details') and error.technical_details:
        click.echo(f"📝 Use --verbose for technical details", err=True)
    
    return exit_code


def check_test_mode() -> bool:
    """
    Check if CLI is running in test mode (AICOS_TEST_MODE environment variable)
    
    Returns:
        True if in test mode, False otherwise
    """
    import os
    return os.getenv('AICOS_TEST_MODE', '').lower() in ('true', '1', 'yes', 'on')


def validate_file_path(path: str, must_exist: bool = True, must_be_readable: bool = True) -> Path:
    """
    Validate file path with user-friendly error messages
    
    Args:
        path: File path to validate
        must_exist: If True, path must exist
        must_be_readable: If True, path must be readable
        
    Returns:
        Validated Path object
        
    Raises:
        ValidationError: If validation fails
    """
    try:
        file_path = Path(path).expanduser().resolve()
    except Exception as e:
        raise ValidationError(
            f"Invalid file path: {path}",
            suggestion="Check that the path is properly formatted and accessible",
            technical_details=str(e)
        )
    
    if must_exist and not file_path.exists():
        raise ValidationError(
            f"File not found: {file_path}",
            suggestion=f"Ensure the file exists at {file_path.parent}/ or check the path"
        )
    
    if must_be_readable and file_path.exists() and not file_path.is_file():
        raise ValidationError(
            f"Path is not a file: {file_path}",
            suggestion="Provide a path to a file, not a directory"
        )
    
    if must_be_readable and file_path.exists() and not file_path.stat().st_mode & 0o400:
        raise ValidationError(
            f"File is not readable: {file_path}",
            suggestion="Check file permissions or run with appropriate user privileges"
        )
    
    return file_path


def validate_date_range(start_date: Optional[str], end_date: Optional[str]) -> tuple:
    """
    Validate date range parameters
    
    Args:
        start_date: Start date string (YYYY-MM-DD)
        end_date: End date string (YYYY-MM-DD)
        
    Returns:
        Tuple of validated date strings
        
    Raises:
        ValidationError: If dates are invalid
    """
    from datetime import datetime
    
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        except ValueError:
            raise ValidationError(
                f"Invalid start date format: {start_date}",
                suggestion="Use YYYY-MM-DD format (e.g., 2025-08-19)"
            )
    
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        except ValueError:
            raise ValidationError(
                f"Invalid end date format: {end_date}",
                suggestion="Use YYYY-MM-DD format (e.g., 2025-08-19)"
            )
    
    if start_date and end_date:
        if start_dt > end_dt:
            raise ValidationError(
                f"Start date {start_date} is after end date {end_date}",
                suggestion="Ensure start date is before or equal to end date"
            )
    
    return start_date, end_date


def safe_import(module_name: str, fallback_class: Optional[type] = None) -> Any:
    """
    Safely import a module with graceful fallback
    
    Args:
        module_name: Module to import
        fallback_class: Optional fallback class if module unavailable
        
    Returns:
        Imported module or fallback
        
    Raises:
        DependencyError: If module unavailable and no fallback provided
    """
    try:
        import importlib
        return importlib.import_module(module_name)
    except ImportError as e:
        if fallback_class:
            return fallback_class
        
        test_mode = check_test_mode()
        if test_mode:
            # In test mode, provide more helpful guidance
            raise DependencyError(
                f"Module {module_name} not available in test mode",
                suggestion=f"This is expected in AICOS_TEST_MODE. The CLI will use mock implementations.",
                technical_details=str(e)
            )
        else:
            raise DependencyError(
                f"Required module {module_name} not available",
                suggestion=f"Install missing dependencies or set AICOS_TEST_MODE=true for testing",
                technical_details=str(e)
            )


def get_common_error_suggestions() -> Dict[str, str]:
    """
    Get common error remediation suggestions
    
    Returns:
        Dictionary mapping error patterns to suggestions
    """
    return {
        'permission_denied': "Check file/directory permissions or run with appropriate privileges",
        'file_not_found': "Ensure the file path is correct and the file exists",
        'database_locked': "Another process may be using the database. Wait and retry.",
        'out_of_memory': "Try reducing the query scope or increase available memory",
        'timeout': "The operation took too long. Try a more specific query or check system resources",
        'invalid_config': "Check configuration file format and required fields",
        'network_error': "Check network connection and API endpoint availability",
        'api_rate_limit': "Too many API requests. Wait before retrying or check rate limits"
    }


class MockQueryEngine:
    """Mock query engine for use when Agent A modules unavailable"""
    
    def __init__(self):
        self.test_mode = check_test_mode()
    
    def time_query(self, time_expression: str, **kwargs):
        """Mock time-based query"""
        if not self.test_mode:
            raise DependencyError(
                "TimeQueryEngine not available",
                suggestion="Set AICOS_TEST_MODE=true or install Agent A modules"
            )
        
        return {
            'query_type': 'time',
            'time_expression': time_expression,
            'results': [
                {
                    'content': f'Mock result for time query: {time_expression}',
                    'source': 'mock',
                    'date': '2025-08-19',
                    'relevance_score': 0.85
                }
            ],
            'metadata': {'mock_mode': True}
        }
    
    def person_query(self, person_id: str, **kwargs):
        """Mock person-based query"""
        if not self.test_mode:
            raise DependencyError(
                "PersonQueryEngine not available",
                suggestion="Set AICOS_TEST_MODE=true or install Agent A modules"
            )
        
        return {
            'query_type': 'person',
            'person_id': person_id,
            'results': [
                {
                    'content': f'Mock result for person query: {person_id}',
                    'source': 'mock',
                    'date': '2025-08-19',
                    'relevance_score': 0.90
                }
            ],
            'metadata': {'mock_mode': True}
        }
    
    def pattern_query(self, pattern_type: str, **kwargs):
        """Mock pattern extraction query"""
        if not self.test_mode:
            raise DependencyError(
                "StructuredExtractor not available", 
                suggestion="Set AICOS_TEST_MODE=true or install Agent A modules"
            )
        
        return {
            'query_type': 'patterns',
            'pattern_type': pattern_type,
            'results': [
                {
                    'content': f'Mock {pattern_type} pattern found',
                    'source': 'mock',
                    'date': '2025-08-19',
                    'relevance_score': 0.75
                }
            ],
            'metadata': {'mock_mode': True}
        }


class MockCalendarEngine:
    """Mock calendar engine for use when Agent B modules unavailable"""
    
    def __init__(self):
        self.test_mode = check_test_mode()
    
    def find_slots(self, attendees: list, duration: int, **kwargs):
        """Mock free slot finding"""
        if not self.test_mode:
            raise DependencyError(
                "AvailabilityEngine not available",
                suggestion="Set AICOS_TEST_MODE=true or install Agent B modules"
            )
        
        return {
            'available_slots': [
                {'start': '2025-08-19T14:00:00', 'end': '2025-08-19T15:00:00'},
                {'start': '2025-08-19T16:00:00', 'end': '2025-08-19T17:00:00'}
            ],
            'attendees': attendees,
            'duration_minutes': duration,
            'metadata': {'mock_mode': True}
        }
    
    def check_conflicts(self, attendees: list, date: str, **kwargs):
        """Mock conflict checking"""
        if not self.test_mode:
            raise DependencyError(
                "ConflictDetector not available",
                suggestion="Set AICOS_TEST_MODE=true or install Agent B modules"
            )
        
        return {
            'conflicts_found': False,
            'attendees': attendees,
            'date': date,
            'details': 'No conflicts found (mock mode)',
            'metadata': {'mock_mode': True}
        }
    
    def analyze_activity(self, date: str, **kwargs):
        """Mock activity analysis"""
        if not self.test_mode:
            raise DependencyError(
                "ActivityAnalyzer not available",
                suggestion="Set AICOS_TEST_MODE=true or install Agent B modules"
            )
        
        return {
            'date': date,
            'slack_activity': {
                'message_count': 42,
                'channels': ['general', 'project-alpha'],
                'top_participants': ['alice@example.com', 'bob@example.com']
            },
            'calendar_activity': {
                'meeting_count': 3,
                'total_duration_minutes': 120,
                'meeting_types': ['standup', 'planning', 'review']
            },
            'key_highlights': ['Mock project milestone completed'],
            'metadata': {'mock_mode': True}
        }