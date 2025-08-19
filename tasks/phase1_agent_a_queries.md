# Agent A: Query Engines Module - Phase 1 Completion

**Date Created**: 2025-08-19  
**Owner**: Agent A (Query Engine Team)  
**Status**: PENDING  
**Estimated Time**: 2 days (16 hours)  
**Dependencies**: Search database from Stage 3 ✅

## Executive Summary

Implement deterministic query engines for time-based, person-based, and structured data retrieval. These modules provide the foundation for Phase 1's promise of unified search and immediate value without AI dependencies.

**Core Philosophy**: Pure deterministic queries with no LLM involvement - every result must be traceable to source data with perfect reproducibility.

## Module Architecture

### Relevant Files for Query Engines

**Read for Context:**
- `src/search/database.py` - SQLite FTS5 search infrastructure (lines 34-200)
- `src/core/config.py` - Configuration management patterns  
- `src/collectors/employee_collector.py` - Employee roster for ID mapping
- `tests/fixtures/mock_slack_data.py` - Data structure patterns

**ARCHITECTURAL CHANGE - Use Existing Infrastructure:**
- Extend `src/intelligence/query_engine.py` instead of creating duplicates
- Add deterministic methods to existing QueryEngine class
- Create query result processors for structured output

**Files to Enhance:**
- `src/intelligence/query_engine.py` - Add deterministic time/person query methods
- `src/queries/structured.py` - Pattern extraction (@mentions, TODOs, hashtags)
- `src/queries/time_utils.py` - Timezone-aware time parsing utilities
- `tests/unit/test_time_queries.py` - Time query test suite
- `tests/unit/test_person_queries.py` - Person query test suite  
- `tests/unit/test_structured.py` - Structured extraction test suite

**Reference Patterns:**
- `src/search/database.py:458-500` - FTS5 query patterns and performance
- `src/core/auth_manager.py:45-65` - Error handling and validation patterns
- `src/collectors/base.py:180-220` - Retry logic and circuit breaker patterns

## CRITICAL FIXES REQUIRED (From Architecture Review)

### Fix 1: Query Engine Duplication Issue
- **Problem**: Existing `src/intelligence/query_engine.py` has overlapping functionality
- **Solution**: Extend existing class with deterministic methods instead of creating duplicates
- **Files Affected**: All query implementations

### Fix 2: Person Data Limitation  
- **Problem**: Employee collector returns mock data only
- **Solution**: Design graceful fallbacks when person mapping unavailable
- **Impact**: Person queries work with or without real employee data

### Fix 3: Memory Usage Realism
- **Problem**: Plan underestimates memory requirements (340K records = 350MB)
- **Solution**: Implement streaming result processing, cursor-based pagination
- **Target**: Keep memory usage realistic for lab environment

## Test-Driven Development Plan

### Phase A1: Time Queries Module (6 hours)

#### Test Acceptance Criteria (Write FIRST)

**File**: `tests/unit/test_time_queries.py`
```python
import pytest
from datetime import datetime, date, timedelta
from src.queries.time_queries import TimeQueryEngine, parse_time_expression

class TestTimeQueryEngine:
    """Test natural language time parsing and filtering"""
    
    def test_natural_language_parsing(self):
        """Parse human-friendly time expressions accurately"""
        today = date.today()
        
        # Basic relative dates
        assert parse_time_expression("today") == (today, today)
        assert parse_time_expression("yesterday") == (today - timedelta(days=1), today - timedelta(days=1))
        assert parse_time_expression("last week") == (today - timedelta(days=7), today - timedelta(days=1))
        
        # Specific periods
        start, end = parse_time_expression("past 30 days")
        assert start == today - timedelta(days=30)
        assert end == today
        
        # Month references
        start, end = parse_time_expression("this month")
        assert start.month == today.month
        assert end.month == today.month
    
    def test_timezone_handling(self):
        """Handle timezone conversions properly"""
        # PST/EST timezone support
        pst_time = parse_time_expression("yesterday PST")
        est_time = parse_time_expression("yesterday EST")
        assert pst_time != est_time  # Different timezone offsets
        
        # UTC normalization
        utc_time = parse_time_expression("yesterday UTC")
        assert utc_time[0].tzinfo is not None
    
    def test_invalid_input_handling(self):
        """Gracefully handle invalid time expressions"""
        with pytest.raises(ValueError, match="Invalid time expression"):
            parse_time_expression("gibberish")
        
        assert parse_time_expression("") is None
        assert parse_time_expression(None) is None
    
    def test_database_integration(self):
        """Query search database with time filters"""
        engine = TimeQueryEngine(db_path="test.db")
        
        # Time-filtered queries
        results = engine.query_by_time("messages from yesterday")
        assert isinstance(results, list)
        assert all('timestamp' in r for r in results)
        
        # Date range queries
        results = engine.query_date_range(
            start=date.today() - timedelta(days=7),
            end=date.today(),
            content_filter="meeting"
        )
        assert len(results) >= 0
    
    def test_performance_requirements(self):
        """Query performance meets Phase 1 targets"""
        engine = TimeQueryEngine(db_path="test.db")
        
        start_time = time.time()
        results = engine.query_by_time("messages from last week")
        end_time = time.time()
        
        assert (end_time - start_time) < 2.0  # <2 second requirement
        assert len(results) >= 0
```

#### Implementation Tasks

**Task A1.1: Module Structure Setup (30 minutes)**
- Create `src/queries/__init__.py` with module exports
- Set up logging and configuration integration
- Define base query interfaces and error classes

**Task A1.2: Time Expression Parser (2 hours)**
- Implement `parse_time_expression()` function
- Support relative dates (yesterday, last week, past N days)
- Add timezone handling with pytz
- Handle month/year references (this month, last year)

**Task A1.3: Database Time Filtering (2 hours)**
- Create `TimeQueryEngine` class with search database integration
- Implement time-range filtering for FTS5 queries
- Add date normalization and timezone conversion
- Optimize with proper SQL indexes

**Task A1.4: Integration Testing (1.5 hours)**
- Test with real archive data
- Verify timezone conversions work correctly
- Benchmark query performance against targets
- Test error handling with malformed dates

### Phase A2: Person Queries Module (5 hours)

#### Test Acceptance Criteria (Write FIRST)

**File**: `tests/unit/test_person_queries.py`
```python
import pytest
from src.queries.person_queries import PersonQueryEngine, PersonResolver

class TestPersonResolver:
    """Test person identification and cross-referencing"""
    
    def test_person_lookup_by_email(self):
        """Find person by email address"""
        resolver = PersonResolver()
        person = resolver.find_person("john.doe@company.com")
        
        assert person is not None
        assert person['email'] == "john.doe@company.com"
        assert 'slack_id' in person
        assert 'calendar_id' in person
    
    def test_person_lookup_by_slack_id(self):
        """Find person by Slack user ID"""
        resolver = PersonResolver()
        person = resolver.find_person("U12345ABC")
        
        assert person is not None
        assert person['slack_id'] == "U12345ABC"
        assert person['email'] is not None
    
    def test_cross_system_mapping(self):
        """Cross-reference IDs between systems"""
        resolver = PersonResolver()
        person = resolver.find_person("john.doe@company.com")
        
        # Verify all system IDs mapped correctly
        assert person['slack_id'].startswith('U')
        assert '@' in person['email']
        assert person['calendar_id'] == person['email']  # Google workspace pattern
    
    def test_fuzzy_name_matching(self):
        """Handle name variations and fuzzy matching"""
        resolver = PersonResolver()
        
        person1 = resolver.find_person("John Doe")
        person2 = resolver.find_person("john doe")
        person3 = resolver.find_person("J. Doe")
        
        assert person1['email'] == person2['email']  # Case insensitive
        # Fuzzy matching optional for Phase 1

class TestPersonQueryEngine:
    """Test person-based data retrieval and aggregation"""
    
    def test_person_activity_aggregation(self):
        """Aggregate activity per person over time"""
        engine = PersonQueryEngine(db_path="test.db")
        
        stats = engine.get_person_activity("john.doe@company.com", "last week")
        
        required_fields = ['message_count', 'meetings_attended', 'files_modified', 'channels_active']
        assert all(field in stats for field in required_fields)
        assert all(isinstance(stats[field], int) for field in required_fields)
    
    def test_person_message_history(self):
        """Retrieve message history for specific person"""
        engine = PersonQueryEngine(db_path="test.db")
        
        messages = engine.get_messages_by_person("john.doe@company.com", limit=50)
        
        assert isinstance(messages, list)
        assert len(messages) <= 50
        assert all('author' in msg for msg in messages)
        assert all('timestamp' in msg for msg in messages)
    
    def test_person_meeting_participation(self):
        """Track meeting participation patterns"""
        engine = PersonQueryEngine(db_path="test.db")
        
        meetings = engine.get_meetings_for_person("john.doe@company.com", "past 30 days")
        
        assert isinstance(meetings, list)
        assert all('title' in meeting for meeting in meetings)
        assert all('attendees' in meeting for meeting in meetings)
        assert all('start_time' in meeting for meeting in meetings)
    
    def test_cross_source_correlation(self):
        """Correlate activity across Slack, Calendar, Drive"""
        engine = PersonQueryEngine(db_path="test.db")
        
        correlation = engine.get_cross_source_activity("john.doe@company.com", "yesterday")
        
        assert 'slack_activity' in correlation
        assert 'calendar_activity' in correlation  
        assert 'drive_activity' in correlation
        assert correlation['total_interactions'] >= 0
```

#### Implementation Tasks

**Task A2.1: Person Resolver (1.5 hours)**
- Create PersonResolver class for ID mapping
- Implement email/Slack ID/name lookups
- Add cross-system ID correlation
- Handle missing or invalid persons

**Task A2.2: Activity Aggregation (2 hours)**
- Create PersonQueryEngine with database integration
- Implement message count aggregation by person
- Add meeting participation tracking
- Calculate cross-source activity metrics

**Task A2.3: Message History Retrieval (1 hour)**
- Implement paginated message retrieval by person
- Add filtering by date range and content
- Optimize queries with proper indexes
- Handle deleted users and archived data

**Task A2.4: Integration & Performance (30 minutes)**
- Test with real employee roster data
- Verify cross-system ID mapping accuracy
- Benchmark aggregation performance
- Add caching for frequently accessed persons

### Phase A3: Structured Extraction Module (5 hours)

#### Test Acceptance Criteria (Write FIRST)

**File**: `tests/unit/test_structured.py`
```python
import pytest
from src.queries.structured import StructuredExtractor

class TestMentionExtraction:
    """Test @mention parsing from Slack messages"""
    
    def test_basic_mentions(self):
        """Extract @mentions from message text"""
        extractor = StructuredExtractor()
        
        text = "Hey @john and @jane, can you review this?"
        mentions = extractor.extract_mentions(text)
        
        assert mentions == ["john", "jane"]
    
    def test_channel_mentions(self):
        """Extract #channel mentions"""
        extractor = StructuredExtractor()
        
        text = "Discussed in #general and #product-team"
        channels = extractor.extract_channel_mentions(text)
        
        assert channels == ["general", "product-team"]
    
    def test_here_everyone_mentions(self):
        """Handle special mentions (@here, @everyone)"""
        extractor = StructuredExtractor()
        
        text = "@here urgent update, cc @everyone"
        mentions = extractor.extract_mentions(text)
        
        assert "here" in mentions
        assert "everyone" in mentions

class TestPatternExtraction:
    """Test TODO, DEADLINE, and action item extraction"""
    
    def test_todo_patterns(self):
        """Find TODO items in messages"""
        extractor = StructuredExtractor()
        
        text = "TODO: Review PR #123. Also TODO: Update docs"
        todos = extractor.extract_todos(text)
        
        assert len(todos) == 2
        assert todos[0]['text'] == "Review PR #123"
        assert todos[1]['text'] == "Update docs"
    
    def test_deadline_patterns(self):
        """Find DEADLINE and due date patterns"""
        extractor = StructuredExtractor()
        
        text = "Report due DEADLINE: Friday EOD. Submit by DEADLINE: 2025-08-20"
        deadlines = extractor.extract_deadlines(text)
        
        assert len(deadlines) == 2
        assert deadlines[0]['deadline'] == "Friday EOD"
        assert deadlines[1]['deadline'] == "2025-08-20"
    
    def test_action_item_extraction(self):
        """Find action items and assignments"""
        extractor = StructuredExtractor()
        
        text = "ACTION: @john to follow up with client by Tuesday"
        actions = extractor.extract_action_items(text)
        
        assert len(actions) == 1
        assert actions[0]['assignee'] == "john"
        assert actions[0]['action'] == "follow up with client"
        assert actions[0]['due'] == "Tuesday"

class TestContentExtraction:
    """Test URL, hashtag, and document reference extraction"""
    
    def test_url_extraction(self):
        """Extract URLs and links from messages"""
        extractor = StructuredExtractor()
        
        text = "Check https://github.com/repo and https://docs.google.com/doc123"
        urls = extractor.extract_urls(text)
        
        assert len(urls) == 2
        assert urls[0]['url'] == "https://github.com/repo"
        assert urls[1]['url'] == "https://docs.google.com/doc123"
    
    def test_hashtag_extraction(self):
        """Extract hashtags and project tags"""
        extractor = StructuredExtractor()
        
        text = "Working on #project-alpha #urgent #Q3-goals"
        hashtags = extractor.extract_hashtags(text)
        
        assert hashtags == ["project-alpha", "urgent", "Q3-goals"]
    
    def test_document_references(self):
        """Find document and file references"""
        extractor = StructuredExtractor()
        
        text = "See spreadsheet Q3-Budget.xlsx and proposal.pdf in shared folder"
        docs = extractor.extract_document_refs(text)
        
        assert len(docs) == 2
        assert any(doc['name'] == "Q3-Budget.xlsx" for doc in docs)
        assert any(doc['name'] == "proposal.pdf" for doc in docs)
```

#### Implementation Tasks

**Task A3.1: Mention Extraction Engine (2 hours)**
- Create StructuredExtractor class
- Implement regex patterns for @mentions and #channels
- Handle special mentions (@here, @everyone, @channel)
- Add validation and edge case handling

**Task A3.2: Pattern Extraction (2 hours)**
- Implement TODO/DEADLINE pattern recognition
- Add action item extraction with assignee detection
- Create configurable pattern system
- Handle multi-line and formatted text

**Task A3.3: Content Reference Extraction (1 hour)**
- Implement URL extraction and validation
- Add hashtag and project tag recognition
- Create document reference detection
- Handle various URL formats and domains

## Integration Requirements

### Database Integration
- All queries must use existing SQLite FTS5 database
- Results must include source attribution (file path, line number)
- Queries must support filtering by date range and source type

### Employee Roster Integration
- Person queries must use existing employee collector data
- ID mapping must work across Slack, Calendar, Drive systems
- Handle missing or incomplete roster data gracefully

### Performance Requirements
- All queries complete in <2 seconds
- Memory usage <100MB for typical queries
- Caching for frequently accessed data
- Efficient SQL generation

## Implementation Strategy

### Development Order
1. **Write all tests first** - Complete test suites before any implementation
2. **Time queries** - Foundation for all time-based filtering
3. **Person queries** - Enable person-centric analysis
4. **Structured extraction** - Add semantic structure to raw text

### Quality Standards
- Zero hardcoded values or estimates
- All results traceable to source data
- Comprehensive error handling with clear messages
- Production-ready code with proper logging

### Integration Points
- **Agent C Dependency**: CLI tools will consume these query engines
- **Agent D Dependency**: Migration system must support query engine tables
- **Stage 3 Integration**: Use existing search database and indexes

## Success Criteria

### Technical Validation ✅
- [ ] All unit tests passing (95% coverage minimum)
- [ ] Performance targets met (<2s response time)
- [ ] Integration with search database working
- [ ] Employee roster cross-referencing accurate

### Functional Validation ✅
- [ ] Time expressions parse correctly (20+ test cases)
- [ ] Person queries return accurate activity data
- [ ] Structured extraction finds patterns reliably
- [ ] All queries return properly formatted results

### Integration Validation ✅
- [ ] Agent C can consume query engine APIs
- [ ] Agent D migration system supports query tables
- [ ] No regression in existing search functionality
- [ ] Error handling prevents system crashes

## Delivery Checklist

Before marking complete:
- [ ] All tests written and passing
- [ ] Performance benchmarks documented
- [ ] Integration APIs clearly defined
- [ ] Error scenarios handled gracefully
- [ ] Documentation updated
- [ ] Code reviewed for production readiness

---

**Contact Agent A Team Lead for questions or clarification**
**Next Agent**: Agent B (Calendar & Statistics) depends on completion