# tasks.md - AI Chief of Staff System Tasks

## ACTIVE TASK QUEUE

**Current Task**: Stage 3: Search Infrastructure Integration  
**Status**: COMPLETE - ALL SYSTEMS OPERATIONAL
**Owner**: Agent Team

**Completed Tasks**:
- ✅ Stage 1a: Core Infrastructure Foundation - COMPLETE (see [completed_tasks.md](./completed_tasks.md))
- ✅ Stage 1b: Collector Wrappers Implementation - COMPLETE (see [completed_tasks.md](./completed_tasks.md))  
- ✅ Stage 1c: Management & Compression Tools - COMPLETE (see [completed_tasks.md](./completed_tasks.md))
- ✅ Stage 3: Search Infrastructure - COMPLETE (August 17, 2025)

**Stage 3 Completion Summary (August 17, 2025)**:
✅ **Test Mode Configuration**: Added AICOS_TEST_MODE support to bypass credential validation during development
✅ **Integration Validation**: All major components working together seamlessly
✅ **Search Database**: 340,071 records indexed and searchable via SQLite FTS5
✅ **Query Engine**: 36 test cases passing, natural language query processing functional
✅ **Data Collection**: Working collection orchestrator with JSON output format
✅ **Archive Management**: 677MB of real data across multiple sources, compression tools operational
✅ **CLI Tools**: search_cli.py and manage_archives.py fully functional

**Performance Metrics**:
- Search response time: <1 second for typical queries
- Database records: 340,071 across Slack (99.9%) and Calendar (0.1%)
- Archive storage: 677MB efficiently managed
- Test coverage: 10/11 integration tests passing, 1 skipped (credentials)

**In Progress**:
- None

**Active Development - Phase 1 Completion (Lab-Grade)**:

### Updated Timeline (Based on Architecture Review)
- **Agent A**: Query Engines - 2 days (extend existing intelligence module) 
- **Agent B**: Calendar & Statistics - 2 days (fix timezone handling, add validation)
- **Agent C**: CLI Tools - 3 days (create interfaces first, unified error handling)
- **Agent D**: Migration & Testing - 2 days (add safety enhancements)

**Total Estimated Time**: 9 days (was 7 days) - Additional time for architectural fixes

### Critical Fixes Applied to Plans
1. **Query Engine Consolidation** - Use existing `src/intelligence/` instead of duplicates
2. **Timezone Safety** - All datetime objects must be timezone-aware  
3. **Dependency Management** - Create interfaces first for parallel development
4. **Lab-Grade Simplifications** - Remove over-engineering for single-user environment

**Queued Tasks**:
- Stage 4: User Interfaces (Slack bot, HTML dashboard)
- Stage 5: Scale & Optimization

---

# Phase 1 Completion Plan - Test-Driven Development

## Executive Summary
Complete the final 15% of Phase 1 (Deterministic Foundation) by implementing query engines, calendar coordination, statistics, and enhanced CLI tools. All work follows test-driven development with acceptance criteria defined before implementation.

**Target Completion**: 5-7 days  
**Test Coverage Goal**: 90% for all new modules  
**Performance Targets**: <2s queries, <5s calendar ops, <10s statistics

## Active Sub-Agent Tasks

### Agent A: Query Engines Module
- **File**: [tasks/phase1_agent_a_queries.md](tasks/phase1_agent_a_queries.md)
- **Focus**: Time-based queries, person queries, structured extraction
- **Status**: PENDING
- **Estimated Time**: 2 days
- **Dependencies**: Search database from Stage 3 ✅

### Agent B: Calendar & Statistics Module  
- **File**: [tasks/phase1_agent_b_calendar.md](tasks/phase1_agent_b_calendar.md)
- **Focus**: Free slot finding, meeting coordination, activity statistics
- **Status**: PENDING
- **Estimated Time**: 2 days
- **Dependencies**: Calendar collector data ✅

### Agent C: CLI Tools & Integration
- **File**: [tasks/phase1_agent_c_cli.md](tasks/phase1_agent_c_cli.md)
- **Focus**: User-facing CLI tools integrating all modules
- **Status**: PENDING
- **Estimated Time**: 1.5 days
- **Dependencies**: Agent A & B deliverables

### Agent D: Schema Migration & Testing
- **File**: [tasks/phase1_agent_d_migration.md](tasks/phase1_agent_d_migration.md)
- **Focus**: Database evolution, migration system, comprehensive testing
- **Status**: PENDING
- **Estimated Time**: 1.5 days
- **Dependencies**: All other agents for integration testing

## Integration Matrix

| Component | Agent A | Agent B | Agent C | Agent D |
|-----------|---------|---------|---------|---------|
| Time Queries | ✓ Primary | - | ✓ Uses | ✓ Tests |
| Person Queries | ✓ Primary | - | ✓ Uses | ✓ Tests |
| Calendar Coordination | - | ✓ Primary | ✓ Uses | ✓ Tests |
| Statistics | - | ✓ Primary | ✓ Uses | ✓ Tests |
| CLI Tools | ✓ Feeds | ✓ Feeds | ✓ Primary | ✓ Tests |
| Schema Migration | ✓ Uses | ✓ Uses | - | ✓ Primary |

## Phase 1 Completion Criteria

### Technical Requirements ✅
- All operations run without LLM/AI
- Full-text search returns accurate results <2s
- Calendar coordination finds valid slots <5s
- State persists across restarts
- Configuration validates all paths and credentials
- Data collection maintains complete history

### Test Requirements
- Unit tests: 95% coverage per module
- Integration tests: 90% coverage overall
- Performance tests: All targets met
- Migration tests: Forward/backward compatibility

### Quality Gates
- Zero regression in existing functionality
- All new tests passing
- Documentation complete
- Code review approved

---

# Stage 3: Search Infrastructure

## Executive Summary
Build comprehensive search and indexing infrastructure to enable powerful queries across all collected data from Stages 1a-1c. This includes SQLite FTS5 database, indexing pipeline, and search CLI.

**Files to Modify:**
- `requirements.txt` - Add missing dependencies (Google APIs, Slack SDK, FastAPI)

**Reference Patterns:**
- `scavenge/src/core/system_state_manager.py:42-50` - Temp file + rename pattern
- `scavenge/src/core/system_state_manager.py:75-85` - File locking mechanism
- `scavenge/src/core/secure_config.py:20-35` - Path validation logic

**Test Files to Create:**
- `tests/unit/test_config.py` - Configuration validation tests
- `tests/unit/test_state.py` - Atomic operations tests  
- `tests/unit/test_archive_writer.py` - JSONL writer tests
- `tests/fixtures/mock_config.py` - Test configuration data

## Tasks for Stage 1a (Test-Driven Development)

### Summary of Completed Stages

**Stage 1a**: Core Infrastructure - COMPLETE
- Environment setup, configuration management, atomic state operations
- Archive writer with JSONL support and metadata tracking
- 90% test coverage achieved

**Stage 1b**: Collector Wrappers - COMPLETE  
- All 4 collectors (Slack, Calendar, Drive, Employee) wrapped successfully
- 100% feature parity with existing scavenge functionality maintained
- JSONL format with daily archive structure

**Stage 1c**: Management Tools - COMPLETE
- Compression utilities for archive management
- Verification tools with integrity checking
- Management CLI with stats and operational commands

---

## Stage 3: Search Infrastructure - COMPLETE (August 17, 2025)

**Search Database**: 340,071 records indexed using SQLite FTS5
**Performance**: <1 second search response time
**Archive Storage**: 677MB efficiently managed with compression tools
**Test Status**: 10/11 integration tests passing, 1 skipped (credentials)

## Implementation Details Reference

For detailed implementation specifications, test acceptance criteria, and TDD workflows, see:
**[archive_context/tasks_implementation_details.md](archive_context/tasks_implementation_details.md)**

This file contains 2,000+ lines of detailed test specifications, implementation tasks, and acceptance criteria that were moved to reduce context window usage.

---

## Current System Status

### Working Components ✅
- **7 CLI Tools** operational (see CAPABILITIES.md for details)
- **Data Collection**: All 4 collectors (Slack, Calendar, Drive, Employee) working
- **Archive Management**: Compression, verification, statistics tools
- **Search System**: Full-text search with natural language queries
- **Test Suite**: 262/322 tests passing (81% success rate)

### Known Issues 🔴
1. **BaseArchiveCollector**: Constructor missing `collector_type` parameter
   - **Fix Location**: `src/collectors/base.py` line ~50
   - **Impact**: Multiple collector test failures

2. **ArchiveVerifier Missing**: Module `src/core/verification_enhanced.py` doesn't exist
   - **Fix Location**: Create missing module with ArchiveVerifier class
   - **Impact**: 23 test errors related to verification

3. **Limited Data**: Only 3 JSONL files in archive currently
   - **Fix**: Run `python3 tools/collect_data.py --source=all` to generate more data

### Next Priority Actions
1. Fix BaseArchiveCollector constructor signature
2. Implement missing ArchiveVerifier module  
3. Generate test data and create search database
4. Run full system verification tests

## Quick Command Reference

### Data Collection
```bash
# Collect from all sources
python3 tools/collect_data.py --source=all --output=json

# Collect from specific source
python3 tools/collect_data.py --source=slack
```

### Search Operations
```bash
# Index archive data
python3 tools/search_cli.py index data/archive/

# Search with natural language
python3 tools/search_cli.py search "meeting notes from last week"

# Get database statistics
python3 tools/search_cli.py stats
```

### Archive Management
```bash
# Compress old files (30+ days)
python3 tools/manage_archives.py --compress --age-days 30

# Verify archive integrity
python3 tools/verify_archive.py

# Get storage statistics
python3 tools/manage_archives.py --stats
```

### Environment Setup
```bash
# Activate virtual environment
source venv/bin/activate

# Set test mode (bypasses credential validation)
export AICOS_TEST_MODE=true
```

---

*For detailed implementation specifications, see [archive_context/tasks_implementation_details.md](archive_context/tasks_implementation_details.md)*

