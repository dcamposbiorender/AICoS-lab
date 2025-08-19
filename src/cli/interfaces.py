"""
Abstract Interfaces for Agent A & B Modules

Provides abstract base classes and interface definitions for Agent A (Query Engines)
and Agent B (Calendar & Statistics) modules. This allows parallel development of
CLI tools while other agents complete their implementations.

The interfaces define the expected method signatures and return formats that
CLI tools will use, with mock implementations available for testing.

Usage:
    from src.cli.interfaces import get_query_engine, get_calendar_engine
    
    query_engine = get_query_engine()
    results = query_engine.time_query("yesterday")
"""

import os
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from datetime import datetime


@dataclass
class QueryResult:
    """Standard query result format"""
    content: str
    source: str
    date: str
    relevance_score: float
    metadata: Dict[str, Any]


@dataclass
class QueryResponse:
    """Standard query response format"""
    query_type: str
    query_params: Dict[str, Any]
    results: List[QueryResult]
    metadata: Dict[str, Any]
    performance: Dict[str, Any]


class TimeQueryEngine(ABC):
    """Abstract interface for time-based query engine (Agent A)"""
    
    @abstractmethod
    def query(self, time_expression: str, source: Optional[str] = None,
              limit: int = 10, **kwargs) -> QueryResponse:
        """
        Execute time-based query
        
        Args:
            time_expression: Natural language time expression (e.g., "yesterday", "last week")
            source: Optional source filter (slack, calendar, drive, employees)
            limit: Maximum number of results
            **kwargs: Additional query parameters
            
        Returns:
            QueryResponse with time-filtered results
        """
        pass
    
    @abstractmethod
    def validate_time_expression(self, expression: str) -> bool:
        """
        Validate time expression format
        
        Args:
            expression: Time expression to validate
            
        Returns:
            True if valid, False otherwise
        """
        pass


class PersonQueryEngine(ABC):
    """Abstract interface for person-based query engine (Agent A)"""
    
    @abstractmethod
    def query(self, person_id: str, time_range: Optional[str] = None,
              include_activity_summary: bool = False, **kwargs) -> QueryResponse:
        """
        Execute person-based query
        
        Args:
            person_id: Person identifier (email, slack ID, etc.)
            time_range: Optional time range filter
            include_activity_summary: Include aggregated activity summary
            **kwargs: Additional query parameters
            
        Returns:
            QueryResponse with person-filtered results
        """
        pass
    
    @abstractmethod
    def get_activity_summary(self, person_id: str, time_range: str) -> Dict[str, Any]:
        """
        Get activity summary for a person
        
        Args:
            person_id: Person identifier
            time_range: Time range for activity summary
            
        Returns:
            Activity summary dictionary
        """
        pass


class StructuredExtractor(ABC):
    """Abstract interface for structured pattern extraction (Agent A)"""
    
    @abstractmethod
    def extract_patterns(self, pattern_type: str, time_range: Optional[str] = None,
                        person: Optional[str] = None, **kwargs) -> QueryResponse:
        """
        Extract structured patterns from data
        
        Args:
            pattern_type: Type of pattern to extract (todos, mentions, deadlines, etc.)
            time_range: Optional time range filter
            person: Optional person filter
            **kwargs: Additional extraction parameters
            
        Returns:
            QueryResponse with extracted patterns
        """
        pass
    
    @abstractmethod
    def get_supported_patterns(self) -> List[str]:
        """
        Get list of supported pattern types
        
        Returns:
            List of supported pattern type strings
        """
        pass


class AvailabilityEngine(ABC):
    """Abstract interface for calendar availability engine (Agent B)"""
    
    @abstractmethod
    def find_free_slots(self, attendees: List[str], duration: int,
                       date_range: Optional[tuple] = None, **kwargs) -> Dict[str, Any]:
        """
        Find free time slots for given attendees
        
        Args:
            attendees: List of attendee email addresses
            duration: Meeting duration in minutes
            date_range: Optional (start_date, end_date) tuple
            **kwargs: Additional constraints
            
        Returns:
            Dictionary with available slots and metadata
        """
        pass
    
    @abstractmethod
    def check_conflicts(self, attendees: List[str], start_time: str,
                       duration: int, **kwargs) -> Dict[str, Any]:
        """
        Check for scheduling conflicts
        
        Args:
            attendees: List of attendee email addresses
            start_time: Proposed start time (ISO format)
            duration: Duration in minutes
            **kwargs: Additional parameters
            
        Returns:
            Dictionary with conflict analysis
        """
        pass


class ActivityAnalyzer(ABC):
    """Abstract interface for activity analysis engine (Agent B)"""
    
    @abstractmethod
    def generate_daily_summary(self, date: str, person: Optional[str] = None,
                              **kwargs) -> Dict[str, Any]:
        """
        Generate daily activity summary
        
        Args:
            date: Date in YYYY-MM-DD format
            person: Optional person filter
            **kwargs: Additional parameters
            
        Returns:
            Daily summary dictionary
        """
        pass
    
    @abstractmethod
    def generate_weekly_summary(self, week_start: str, person: Optional[str] = None,
                               **kwargs) -> Dict[str, Any]:
        """
        Generate weekly activity summary
        
        Args:
            week_start: Week start date in YYYY-MM-DD format
            person: Optional person filter
            **kwargs: Additional parameters
            
        Returns:
            Weekly summary dictionary
        """
        pass
    
    @abstractmethod
    def get_statistics(self, time_range: str, breakdown: Optional[str] = None,
                      **kwargs) -> Dict[str, Any]:
        """
        Get activity statistics
        
        Args:
            time_range: Time range for statistics
            breakdown: Optional breakdown type (channel, person, etc.)
            **kwargs: Additional parameters
            
        Returns:
            Statistics dictionary
        """
        pass


# Factory functions to get appropriate implementations
def get_query_engine() -> Union[TimeQueryEngine, 'MockTimeQueryEngine']:
    """
    Get time query engine implementation
    
    Returns:
        TimeQueryEngine implementation (real or mock)
    """
    # Check if we're in test mode
    test_mode = os.getenv('AICOS_TEST_MODE', '').lower() in ('true', '1', 'yes', 'on')
    
    if test_mode:
        return MockTimeQueryEngine()
    
    # Try to import real implementation
    try:
        from src.queries.time_queries import TimeQueryEngineImpl
        return TimeQueryEngineImpl()
    except ImportError:
        # Fall back to mock if not available
        return MockTimeQueryEngine()


def get_person_engine() -> Union[PersonQueryEngine, 'MockPersonQueryEngine']:
    """
    Get person query engine implementation
    
    Returns:
        PersonQueryEngine implementation (real or mock)
    """
    test_mode = os.getenv('AICOS_TEST_MODE', '').lower() in ('true', '1', 'yes', 'on')
    
    if test_mode:
        return MockPersonQueryEngine()
    
    try:
        from src.queries.person_queries import PersonQueryEngineImpl
        return PersonQueryEngineImpl()
    except ImportError:
        return MockPersonQueryEngine()


def get_pattern_extractor() -> Union[StructuredExtractor, 'MockStructuredExtractor']:
    """
    Get structured pattern extractor implementation
    
    Returns:
        StructuredExtractor implementation (real or mock)
    """
    test_mode = os.getenv('AICOS_TEST_MODE', '').lower() in ('true', '1', 'yes', 'on')
    
    if test_mode:
        return MockStructuredExtractor()
    
    try:
        from src.extractors.structured import StructuredExtractorImpl
        return StructuredExtractorImpl()
    except ImportError:
        return MockStructuredExtractor()


def get_availability_engine() -> Union[AvailabilityEngine, 'MockAvailabilityEngine']:
    """
    Get availability engine implementation
    
    Returns:
        AvailabilityEngine implementation (real or mock)
    """
    test_mode = os.getenv('AICOS_TEST_MODE', '').lower() in ('true', '1', 'yes', 'on')
    
    if test_mode:
        return MockAvailabilityEngine()
    
    try:
        from src.scheduling.availability import AvailabilityEngineImpl
        return AvailabilityEngineImpl()
    except ImportError:
        return MockAvailabilityEngine()


def get_activity_analyzer() -> Union[ActivityAnalyzer, 'MockActivityAnalyzer']:
    """
    Get activity analyzer implementation
    
    Returns:
        ActivityAnalyzer implementation (real or mock)
    """
    test_mode = os.getenv('AICOS_TEST_MODE', '').lower() in ('true', '1', 'yes', 'on')
    
    if test_mode:
        return MockActivityAnalyzer()
    
    try:
        from src.aggregators.basic_stats import ActivityAnalyzerImpl
        return ActivityAnalyzerImpl()
    except ImportError:
        return MockActivityAnalyzer()


# Mock implementations for testing and development
class MockTimeQueryEngine(TimeQueryEngine):
    """Mock implementation of TimeQueryEngine for testing"""
    
    def query(self, time_expression: str, source: Optional[str] = None,
              limit: int = 10, **kwargs) -> QueryResponse:
        """Mock time-based query"""
        import time
        start_time = time.time()
        
        # Simulate query processing time
        time.sleep(0.1)
        
        results = []
        for i in range(min(limit, 3)):  # Return up to 3 mock results
            results.append(QueryResult(
                content=f'Mock result {i+1} for time query: {time_expression}',
                source=source or 'slack',
                date='2025-08-19',
                relevance_score=0.9 - (i * 0.1),
                metadata={'mock_result': True, 'index': i}
            ))
        
        return QueryResponse(
            query_type='time',
            query_params={'time_expression': time_expression, 'source': source, 'limit': limit},
            results=results,
            metadata={'mock_mode': True, 'engine': 'MockTimeQueryEngine'},
            performance={
                'execution_time_ms': int((time.time() - start_time) * 1000),
                'result_count': len(results)
            }
        )
    
    def validate_time_expression(self, expression: str) -> bool:
        """Mock time expression validation"""
        valid_expressions = [
            'today', 'yesterday', 'last week', 'this week', 'last month', 'this month'
        ]
        return any(expr in expression.lower() for expr in valid_expressions)


class MockPersonQueryEngine(PersonQueryEngine):
    """Mock implementation of PersonQueryEngine for testing"""
    
    def query(self, person_id: str, time_range: Optional[str] = None,
              include_activity_summary: bool = False, **kwargs) -> QueryResponse:
        """Mock person-based query"""
        import time
        start_time = time.time()
        
        results = []
        for i in range(2):  # Return 2 mock results
            results.append(QueryResult(
                content=f'Mock interaction {i+1} with {person_id}',
                source='slack',
                date='2025-08-19',
                relevance_score=0.85,
                metadata={'person': person_id, 'mock_result': True}
            ))
        
        response = QueryResponse(
            query_type='person',
            query_params={
                'person_id': person_id, 
                'time_range': time_range,
                'include_activity_summary': include_activity_summary
            },
            results=results,
            metadata={'mock_mode': True, 'engine': 'MockPersonQueryEngine'},
            performance={
                'execution_time_ms': int((time.time() - start_time) * 1000),
                'result_count': len(results)
            }
        )
        
        if include_activity_summary:
            response.metadata['activity_summary'] = self.get_activity_summary(person_id, time_range or 'last week')
        
        return response
    
    def get_activity_summary(self, person_id: str, time_range: str) -> Dict[str, Any]:
        """Mock activity summary"""
        return {
            'person_id': person_id,
            'time_range': time_range,
            'message_count': 42,
            'meeting_count': 5,
            'channels': ['general', 'project-alpha'],
            'top_topics': ['project updates', 'planning'],
            'mock_mode': True
        }


class MockStructuredExtractor(StructuredExtractor):
    """Mock implementation of StructuredExtractor for testing"""
    
    def extract_patterns(self, pattern_type: str, time_range: Optional[str] = None,
                        person: Optional[str] = None, **kwargs) -> QueryResponse:
        """Mock pattern extraction"""
        import time
        start_time = time.time()
        
        results = []
        if pattern_type == 'todos':
            results.append(QueryResult(
                content='TODO: Complete quarterly review',
                source='slack',
                date='2025-08-19',
                relevance_score=0.9,
                metadata={'pattern_type': 'todo', 'status': 'open', 'mock_result': True}
            ))
        elif pattern_type == 'mentions':
            results.append(QueryResult(
                content=f'@{person or "user"} mentioned in project discussion',
                source='slack', 
                date='2025-08-19',
                relevance_score=0.85,
                metadata={'pattern_type': 'mention', 'mock_result': True}
            ))
        elif pattern_type == 'deadlines':
            results.append(QueryResult(
                content='Project deadline: Friday Aug 23rd',
                source='slack',
                date='2025-08-19',
                relevance_score=0.95,
                metadata={'pattern_type': 'deadline', 'due_date': '2025-08-23', 'mock_result': True}
            ))
        
        return QueryResponse(
            query_type='patterns',
            query_params={'pattern_type': pattern_type, 'time_range': time_range, 'person': person},
            results=results,
            metadata={'mock_mode': True, 'engine': 'MockStructuredExtractor'},
            performance={
                'execution_time_ms': int((time.time() - start_time) * 1000),
                'result_count': len(results)
            }
        )
    
    def get_supported_patterns(self) -> List[str]:
        """Mock supported patterns"""
        return ['todos', 'mentions', 'deadlines', 'decisions', 'action_items']


class MockAvailabilityEngine(AvailabilityEngine):
    """Mock implementation of AvailabilityEngine for testing"""
    
    def find_free_slots(self, attendees: List[str], duration: int,
                       date_range: Optional[tuple] = None, **kwargs) -> Dict[str, Any]:
        """Mock free slot finding"""
        return {
            'available_slots': [
                {
                    'start': '2025-08-19T14:00:00',
                    'end': f'2025-08-19T{14 + duration//60}:{duration%60:02d}:00',
                    'confidence': 0.9
                },
                {
                    'start': '2025-08-19T16:00:00',
                    'end': f'2025-08-19T{16 + duration//60}:{duration%60:02d}:00',
                    'confidence': 0.8
                }
            ],
            'attendees': attendees,
            'duration_minutes': duration,
            'search_range': date_range,
            'metadata': {'mock_mode': True, 'engine': 'MockAvailabilityEngine'}
        }
    
    def check_conflicts(self, attendees: List[str], start_time: str,
                       duration: int, **kwargs) -> Dict[str, Any]:
        """Mock conflict checking"""
        return {
            'conflicts_found': False,
            'attendees': attendees,
            'proposed_time': start_time,
            'duration_minutes': duration,
            'details': 'No conflicts detected (mock mode)',
            'metadata': {'mock_mode': True}
        }


class MockActivityAnalyzer(ActivityAnalyzer):
    """Mock implementation of ActivityAnalyzer for testing"""
    
    def generate_daily_summary(self, date: str, person: Optional[str] = None,
                              **kwargs) -> Dict[str, Any]:
        """Mock daily summary generation"""
        return {
            'date': date,
            'person': person,
            'slack_activity': {
                'message_count': 42,
                'channels_active': ['general', 'project-alpha', 'random'],
                'top_participants': ['alice@example.com', 'bob@example.com'],
                'peak_activity_hour': 14
            },
            'calendar_activity': {
                'meeting_count': 3,
                'total_duration_minutes': 120,
                'meeting_types': ['standup', 'planning', 'review'],
                'busiest_hour': 10
            },
            'drive_activity': {
                'files_modified': 5,
                'files_created': 2,
                'collaborations': 3
            },
            'key_highlights': [
                'Project milestone completed',
                'New team member onboarded',
                'Quarterly planning session scheduled'
            ],
            'statistics': {
                'total_interactions': 67,
                'productivity_score': 85,
                'collaboration_index': 7.2
            },
            'metadata': {'mock_mode': True, 'engine': 'MockActivityAnalyzer'}
        }
    
    def generate_weekly_summary(self, week_start: str, person: Optional[str] = None,
                               **kwargs) -> Dict[str, Any]:
        """Mock weekly summary generation"""
        return {
            'week_start': week_start,
            'person': person,
            'summary_stats': {
                'total_messages': 210,
                'total_meetings': 15,
                'total_meeting_hours': 10,
                'active_days': 5
            },
            'trends': {
                'message_volume': 'increasing',
                'meeting_load': 'stable',
                'collaboration_trend': 'improving'
            },
            'top_achievements': [
                'Released feature X',
                'Completed code review backlog',
                'Onboarded 2 new team members'
            ],
            'metadata': {'mock_mode': True, 'engine': 'MockActivityAnalyzer'}
        }
    
    def get_statistics(self, time_range: str, breakdown: Optional[str] = None,
                      **kwargs) -> Dict[str, Any]:
        """Mock statistics generation"""
        stats = {
            'time_range': time_range,
            'breakdown': breakdown,
            'total_messages': 1337,
            'total_meetings': 42,
            'unique_participants': 15,
            'metadata': {'mock_mode': True}
        }
        
        if breakdown == 'channel':
            stats['by_channel'] = {
                'general': {'messages': 500, 'participants': 12},
                'project-alpha': {'messages': 300, 'participants': 8},
                'random': {'messages': 200, 'participants': 10}
            }
        elif breakdown == 'person':
            stats['by_person'] = {
                'alice@example.com': {'messages': 200, 'meetings': 10},
                'bob@example.com': {'messages': 150, 'meetings': 8},
                'charlie@example.com': {'messages': 100, 'meetings': 5}
            }
        
        return stats