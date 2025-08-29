# tasks.md - AI Chief of Staff System Tasks

## ACTIVE TASK QUEUE

**Current Status**: Phase 1 Complete - Moving to Phase 4.5 Frontend Dashboard  
**Active Development**: Lab-Grade Frontend Dashboard Implementation
**Owner**: Frontend Agent Team

**Phase 1 Completion Status** ✅:
- ✅ Stage 1a: Core Infrastructure Foundation - COMPLETE 
- ✅ Stage 1b: Collector Wrappers Implementation - COMPLETE 
- ✅ Stage 1c: Management & Compression Tools - COMPLETE 
- ✅ Stage 3: Search Infrastructure - COMPLETE (340,071 records indexed)
- ✅ **Agent A: Query Engines** - COMPLETE (21+23+33 tests passing)
- ✅ **Agent B: Calendar & Statistics** - COMPLETE (14+19 tests passing) 
- ✅ **Agent C: CLI Tools & Integration** - COMPLETE (all tools operational)
- ✅ **Agent D: Schema Migration & Testing** - COMPLETE (16/16 integration tests passing)

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
- **Phase 6: User-Centric Architecture** (Lab-Grade) - Transform system to recognize PRIMARY USER

---

# Phase 1 Completion Summary ✅

**Status**: COMPLETE (All 4 agents finished successfully)  
**Date Completed**: August 19, 2025  
**Total Development Time**: 4 days (vs 5-7 day estimate)

**Final Results**:
- All 907 system tests collected successfully
- Performance targets met: <2s queries, <5s calendar, <10s statistics  
- Zero regressions in existing functionality
- Complete audit trail maintained

**Detailed implementation specifications moved to**: [old/plan_archive.md](old/plan_archive.md)

---

# Phase 4.5: Frontend Dashboard Implementation (Lab-Grade)

## Executive Summary
Implement a real-time dashboard based on cos-paper-dense.html mockup with WebSocket synchronization between dashboard and Slack bot. Focus on core functionality without over-engineering for lab-grade deployment.

**Target Completion**: 5 days  
**Architecture**: FastAPI + WebSocket backend, dynamic HTML/JS frontend  
**Key Feature**: C1/P1/M1 coding system for rapid keyboard navigation  

## Sub-Agent Task Breakdown

### Agent E: Backend API & WebSocket Server ⏳ PENDING
- **File**: [tasks/frontend_agent_e_backend.md](tasks/frontend_agent_e_backend.md)
- **Focus**: FastAPI server with WebSocket broadcasting, in-memory state management
- **Estimated Time**: 8 hours (1 day)
- **Dependencies**: Existing SearchDatabase, collectors
- **Key Deliverables**:
  - FastAPI application with WebSocket endpoint `/ws`
  - REST API for commands and state management
  - Real-time broadcasting to connected clients
  - Integration with existing SearchDatabase (340K+ records)

### Agent F: Dashboard Frontend Implementation ⏳ PENDING
- **File**: [tasks/frontend_agent_f_dashboard.md](tasks/frontend_agent_f_dashboard.md)
- **Focus**: Convert cos-paper-dense.html mockup to dynamic dashboard
- **Estimated Time**: 8 hours (1 day)
- **Dependencies**: Agent E API endpoints
- **Key Deliverables**:
  - WebSocket client with auto-reconnection
  - Real-time DOM updates preserving paper-dense aesthetic
  - Command input with keyboard navigation
  - Visual feedback for state changes

### Agent G: Coding System & State Management ⏳ PENDING
- **File**: [tasks/frontend_agent_g_coding.md](tasks/frontend_agent_g_coding.md)
- **Focus**: Implement C1/P1/M1 coding system for rapid navigation
- **Estimated Time**: 8 hours (1 day)  
- **Dependencies**: Agent E state management
- **Key Deliverables**:
  - Automatic code generation (Calendar=C1-Cn, Priority=P1-Pn, Commitments=M1-Mn)
  - Bidirectional code mapping for fast lookups
  - Integration with command parser
  - Persistence across state updates

### Agent H: Integration & Command Processing ⏳ PENDING
- **File**: [tasks/frontend_agent_h_integration.md](tasks/frontend_agent_h_integration.md)
- **Focus**: Connect collectors, implement unified command parser, sync Slack bot
- **Estimated Time**: 8 hours (1 day)
- **Dependencies**: Agents E, F, G must be complete
- **Key Deliverables**:
  - Collector integration with real-time progress updates
  - Unified command parser for "approve P7" style commands
  - Updated Slack bot using shared backend API
  - Brief generation system

### Agent I: Testing & Polish ⏳ PENDING
- **File**: [tasks/frontend_agent_i_testing.md](tasks/frontend_agent_i_testing.md)
- **Focus**: End-to-end testing, performance validation, bug fixes
- **Estimated Time**: 8 hours (1 day)
- **Dependencies**: All other frontend agents complete
- **Key Deliverables**:
  - Comprehensive integration test suite
  - Performance benchmarks (<200ms command execution)
  - Error handling and recovery testing
  - Documentation and deployment guide

## Parallel Work Strategy

### Days 1-2: Core Infrastructure (Parallel Development)
- **Agent E, F, G can work simultaneously** (no interdependencies)
- Agent E builds backend API foundation
- Agent F converts mockup to dynamic interface
- Agent G implements coding system logic

### Day 3: System Integration  
- **Agent H integrates all components** (depends on E+F+G)
- Connects existing collectors to new API
- Implements unified command parser
- Updates Slack bot for shared backend

### Days 4-5: Testing & Deployment
- **Agent I validates entire system** (depends on A+B+C+D)
- End-to-end workflow testing
- Performance optimization
- Bug fixes and polish

## Integration Matrix

| Component | Agent E | Agent F | Agent G | Agent H | Agent I |
|-----------|---------|---------|---------|---------|---------|
| WebSocket | Creates | Uses | - | Updates | Tests |
| State Management | Creates | Reads | Updates | Updates | Tests |
| Coding System | - | Displays | Creates | Uses | Tests |
| Commands | Endpoint | Sends | Parses | Executes | Tests |
| Collectors | - | - | - | Integrates | Tests |
| Slack Bot | - | - | - | Updates | Tests |

## Success Criteria

### Technical Requirements ✅
- Dashboard loads in <3 seconds
- Command execution responds in <200ms  
- State updates propagate in <100ms
- WebSocket maintains stable connection

### Functional Requirements ✅
- Commands work identically in dashboard and Slack
- State remains synchronized across all interfaces
- Preserves exact paper-dense aesthetic from mockup
- Leverages existing SearchDatabase and collectors

### Integration Requirements ✅
- No regression in existing functionality
- All existing CLI tools continue working
- Slack bot maintains backward compatibility
- Search performance unaffected by new API layer

## Delivery Checklist

Before marking Phase 4.5 complete:
- [ ] All 5 agent task files created with test-driven specifications
- [ ] Backend API functional with WebSocket broadcasting
- [ ] Dashboard matches mockup aesthetics exactly
- [ ] C1/P1/M1 coding system operational
- [ ] Commands work from both dashboard and Slack
- [ ] Real-time state synchronization verified
- [ ] Performance targets met across all operations
- [ ] End-to-end test suite passing
- [ ] Documentation complete for lab deployment

---

# Phase 6: User-Centric Architecture Implementation (Lab-Grade)

## Executive Summary
Transform the AI Chief of Staff from treating all employees equally to recognizing the PRIMARY USER as central. Includes comprehensive setup wizard covering all system components and simple personalization for dashboard and briefs.

**Target Completion**: 3-4 days  
**Architecture**: Simple PRIMARY_USER configuration with comprehensive onboarding  
**Key Feature**: System awareness of who the user is, with personalized data presentation  

## Sub-Agent Task Breakdown

### Agent J: User Identity Configuration ⏳ PENDING
- **File**: [tasks/phase6_agent_j_user_identity.md](tasks/phase6_agent_j_user_identity.md)
- **Focus**: PRIMARY_USER configuration and identity mapping across systems
- **Estimated Time**: 4 hours (0.5 day)
- **Dependencies**: None (foundation module)
- **Key Deliverables**:
  - User identity module with PRIMARY_USER configuration
  - Cross-system identity mapping (email ↔ Slack ID ↔ Calendar ID)  
  - Integration with existing config.py system
  - Backwards compatibility for unconfigured systems
  - Validation that user exists in all connected systems

### Agent K: Comprehensive Setup Wizard ⏳ PENDING
- **File**: [tasks/phase6_agent_k_setup_wizard.md](tasks/phase6_agent_k_setup_wizard.md)
- **Focus**: Interactive wizard for complete system setup from scratch
- **Estimated Time**: 8-12 hours (1-1.5 days)
- **Dependencies**: Agent J for user identity structure
- **Key Deliverables**:
  - Interactive CLI setup wizard covering all components
  - Environment setup (directories, database, AICOS_BASE_DIR)
  - Slack API token configuration and validation
  - Google Calendar OAuth setup and credential storage
  - Google Drive API authentication and validation
  - User identity configuration and cross-system verification
  - Initial data collection run and search index building
  - Complete validation that all components work correctly

### Agent L: Personalization Integration ⏳ PENDING  
- **File**: [tasks/phase6_agent_l_personalization.md](tasks/phase6_agent_l_personalization.md)
- **Focus**: Integrate PRIMARY_USER throughout existing components
- **Estimated Time**: 8 hours (1 day)
- **Dependencies**: Agent J and K must be complete
- **Key Deliverables**:
  - Dashboard loads user's actual calendar data (not demo data)
  - Briefs prioritize user's activities, meetings, and mentions
  - Search results boost user-relevant content by 50%
  - Simple filtering for user-centric data presentation
  - Integration across all existing components (dashboard, brief, search)

## Parallel Work Strategy

### Day 1: Foundation (Agent J - 4 hours)
- Create user identity configuration system
- Can work independently without dependencies

### Days 2-3: Setup Wizard (Agent K - 8-12 hours)  
- Build comprehensive onboarding flow (depends on Agent J)
- Covers environment, APIs, credentials, user identity, validation

### Day 4: Integration (Agent L - 8 hours)
- Personalize all existing components (depends on J+K)
- Dashboard, briefs, search integration

## Integration Matrix

| Component | Agent J | Agent K | Agent L |
|-----------|---------|---------|---------|
| User Identity | ✓ Creates | ✓ Sets Up | ✓ Uses |
| Configuration | ✓ Extends | ✓ Initializes | ✓ Uses |
| API Setup | - | ✓ Configures | - |
| Dashboard | - | ✓ Validates | ✓ Personalizes |
| Briefs | - | ✓ Tests | ✓ Personalizes |
| Search | - | ✓ Indexes | ✓ Boosts |

## Success Criteria

### Technical Requirements ✅
- Setup wizard completes in <5 minutes with clear progress
- All API credentials validated and working during setup
- User identity correctly mapped across all systems
- Dashboard shows user's actual calendar (not sample data)
- Briefs focus on user's activities and commitments
- Search prioritizes user-relevant results

### Functional Requirements ✅  
- System recognizes who the PRIMARY USER is
- All data presentation revolves around user's perspective
- Complete setup from fresh installation to working system
- Backwards compatible with non-personalized mode
- Simple, maintainable lab-grade implementation

### Integration Requirements ✅
- All existing Phase 1-5 components continue working
- No regression in performance or functionality
- Setup wizard handles all authentication and configuration
- User identity propagates through entire system

## Delivery Checklist

Before marking Phase 6 complete:
- [ ] Agent J task file created with user identity specifications
- [ ] Agent K task file created with comprehensive setup wizard plan
- [ ] Agent L task file created with personalization integration details
- [ ] PRIMARY_USER configuration system implemented
- [ ] Setup wizard completes full system configuration
- [ ] Dashboard shows user's actual calendar data
- [ ] Briefs prioritize user's activities
- [ ] Search boosts user-relevant results
- [ ] All components backwards compatible
- [ ] Complete test coverage for personalization features
- [ ] Documentation updated for new user-centric features

---

# Stage 3: Search Infrastructure

## Executive Summary
Build comprehensive search and indexing infrastructure to enable powerful queries across all collected data from Stages 1a-1c. This includes SQLite FTS5 database, indexing pipeline, and search CLI.

**Files to Modify:**
- `requirements.txt` - Add missing dependencies (Google APIs, Slack SDK, FastAPI)

**Reference Patterns:**
- `src/core/state.py` - Temp file + rename pattern and file locking
- `src/core/secure_config.py` - Path validation logic

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
- 100% feature parity with existing collector functionality maintained
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

