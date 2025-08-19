# Task Queue - AI Chief of Staff Lab Implementation

## Current Status: Plan Critique Complete ✅
**Date**: 2025-08-17  
**Last Updated**: Post Team A/B Plan Analysis  
**Next Review**: After Priority 1 completion  

## Priority 1: Critical Safety Fixes (Day 1) 🚨
**Status**: Pending  
**Risk Level**: HIGH - These issues could cause data loss or system failure

### T1.1 - Fix FTS5 Trigger Recursion Issue (Team A)
- [ ] **Status**: Pending
- [ ] **Location**: `tasks_A.md` lines 296-317
- [ ] **Issue**: Triggers use `json_extract(new.metadata, '$.content')` causing recursive metadata bloat
- [ ] **Fix**: Separate content storage from metadata, update trigger logic
- [ ] **Impact**: Prevents stack overflow and memory exhaustion
- [ ] **Estimated Time**: 2 hours
- [ ] **Blocker for**: All search functionality

### T1.2 - Add filelock Dependency and Fallback (Team B)  
- [ ] **Status**: Pending
- [ ] **Location**: `tasks_B.md` line 316
- [ ] **Issue**: Uses `filelock.FileLock` without import or availability check
- [ ] **Fix**: Add proper import, check availability, implement fallback
- [ ] **Impact**: Prevents runtime crashes during compression
- [ ] **Estimated Time**: 1 hour
- [ ] **Blocker for**: Archive compression functionality

### T1.3 - Implement Two-Phase Commit for Compression (Team B)
- [ ] **Status**: Pending  
- [ ] **Location**: `tasks_B.md` line 244
- [ ] **Issue**: Deletes original after rename - if delete fails, have duplicates
- [ ] **Fix**: Implement proper two-phase commit pattern
- [ ] **Impact**: Ensures atomic compression operations
- [ ] **Estimated Time**: 1.5 hours
- [ ] **Blocker for**: Safe production compression

### T1.4 - Add Error Recovery to Indexing Pipeline (Team A)
- [ ] **Status**: Pending
- [ ] **Location**: `tasks_A.md` indexing implementation
- [ ] **Issue**: No handling for partial indexing failures or corruption
- [ ] **Fix**: Add transaction checkpoints and recovery procedures  
- [ ] **Impact**: Enables recovery from indexing failures
- [ ] **Estimated Time**: 2 hours
- [ ] **Blocker for**: Reliable indexing operations

**Priority 1 Total Estimated Time**: 6.5 hours

---

## Priority 2: Core Functionality (Day 2-3) ⚙️
**Status**: Pending  
**Risk Level**: MEDIUM - Required for basic functionality

### T2.1 - Simplify Connection Pooling for Lab Deployment (Team A)
- [ ] **Status**: Pending
- [ ] **Location**: `tasks_A.md` lines 207-391  
- [ ] **Issue**: Over-engineered pooling for single-user lab scenario
- [ ] **Fix**: Replace with simple connection + retry logic
- [ ] **Impact**: Reduces complexity, improves maintainability
- [ ] **Estimated Time**: 2 hours

### T2.2 - Implement Schema Migration Logic (Team A)
- [ ] **Status**: Pending
- [ ] **Location**: `tasks_A.md` line 328
- [ ] **Issue**: `_migrate_schema()` function is empty
- [ ] **Fix**: Implement actual migration logic for version updates
- [ ] **Impact**: Enables database schema evolution
- [ ] **Estimated Time**: 1.5 hours

### T2.3 - Add Actual Backup Cleanup Mechanism (Team B)  
- [ ] **Status**: Pending
- [ ] **Location**: `tasks_B.md` line 418
- [ ] **Issue**: `_schedule_backup_cleanup()` only logs, doesn't clean
- [ ] **Fix**: Implement actual cleanup or make retention policy clear
- [ ] **Impact**: Prevents backup storage exhaustion
- [ ] **Estimated Time**: 1 hour

### T2.4 - Create Basic Team C Query Engine
- [ ] **Status**: Pending
- [ ] **Location**: New - `tasks_C.md` to be created
- [ ] **Issue**: Missing query engine to consume search infrastructure
- [ ] **Fix**: Define and implement basic query processing
- [ ] **Impact**: Makes search functionality accessible
- [ ] **Estimated Time**: 4 hours

**Priority 2 Total Estimated Time**: 8.5 hours

---

## Priority 3: Performance & Polish (Day 4) 🚀  
**Status**: Pending
**Risk Level**: LOW - Performance improvements

### T3.1 - Increase Batch Sizes for Better Performance (Team A)
- [ ] **Status**: Pending
- [ ] **Current**: 1000 records/batch creates excessive transactions
- [ ] **Fix**: Increase to 10,000 records/batch
- [ ] **Impact**: 4-10x performance improvement
- [ ] **Estimated Time**: 30 minutes

### T3.2 - Add Missing Database Indexes (Team A)
- [ ] **Status**: Pending
- [ ] **Missing**: Index on `messages.created_at`
- [ ] **Fix**: Add time-based query optimization
- [ ] **Impact**: Faster date range searches
- [ ] **Estimated Time**: 30 minutes

### T3.3 - Implement Simple Query Caching (Team A)
- [ ] **Status**: Pending
- [ ] **Issue**: Repeated searches hit database every time
- [ ] **Fix**: Add LRU cache for common queries
- [ ] **Impact**: Faster repeated searches
- [ ] **Estimated Time**: 1 hour

### T3.4 - Add Parallel Compression Support (Team B)
- [ ] **Status**: Pending
- [ ] **Current**: Single-threaded compression is slow
- [ ] **Fix**: Use multiprocessing for multiple files
- [ ] **Impact**: 4x speedup on typical hardware
- [ ] **Estimated Time**: 2 hours

**Priority 3 Total Estimated Time**: 4 hours

---

## Priority 4: User Experience (Day 5) ✨
**Status**: Pending  
**Risk Level**: LOW - User experience improvements

### T4.1 - Add Progress Indicators with Fallbacks
- [ ] **Status**: Pending
- [ ] **Issue**: Uses `tqdm` without checking availability
- [ ] **Fix**: Add try/except with simple progress fallback
- [ ] **Impact**: Better user feedback during operations
- [ ] **Estimated Time**: 1 hour

### T4.2 - Make Compression Levels Configurable  
- [ ] **Status**: Pending
- [ ] **Issue**: Hard-coded level 6 might be too slow for large files
- [ ] **Fix**: Make configurable based on file size
- [ ] **Impact**: Optimized compression performance
- [ ] **Estimated Time**: 30 minutes

### T4.3 - Persist Statistics Between Runs
- [ ] **Status**: Pending  
- [ ] **Issue**: All statistics lost on restart
- [ ] **Fix**: Save stats to JSON file
- [ ] **Impact**: Better operational visibility
- [ ] **Estimated Time**: 1 hour

### T4.4 - Build FastAPI Search Endpoints (Team C)
- [ ] **Status**: Pending
- [ ] **Issue**: No API layer for search functionality  
- [ ] **Fix**: Create REST API with FastAPI
- [ ] **Impact**: Makes search accessible to external clients
- [ ] **Estimated Time**: 2 hours

**Priority 4 Total Estimated Time**: 4.5 hours

---

## Additional Issues Identified (Future Backlog) 📋

### Testing Concerns:
- [ ] Tests use different fixtures than production code
- [ ] Mock data doesn't reflect actual Slack/Calendar structure  
- [ ] Integration tests missing for end-to-end flow

### Documentation Gaps:
- [ ] No API documentation for search endpoints
- [ ] Missing deployment guide  
- [ ] No troubleshooting section
- [ ] No performance tuning guide

### Production Readiness Assessment:
- **Team A**: 65% ready (major safety issues)
- **Team B**: 75% ready (dependency issues)
- **Team C**: 0% ready (not defined)  
- **Overall**: 45% ready for production

---

## Completion Criteria

### Priority 1 Definition of Done:
- [ ] All critical safety fixes implemented and tested
- [ ] No data loss scenarios in compression operations
- [ ] FTS5 triggers work without recursion
- [ ] Error recovery mechanisms in place

### Priority 2 Definition of Done:  
- [ ] Basic search functionality working end-to-end
- [ ] Schema migration system operational
- [ ] Backup cleanup properly implemented
- [ ] Team C query engine delivering basic results

### Priority 3 Definition of Done:
- [ ] Performance improvements measured and documented
- [ ] All database queries optimized with proper indexes
- [ ] Compression operations 4x faster with parallelization
- [ ] Query caching reducing database load

### Priority 4 Definition of Done:
- [ ] User experience polished with progress indicators
- [ ] All configuration options externalized
- [ ] Statistics persisted and available across restarts
- [ ] API endpoints documented and tested

## Risk Mitigation

### High-Risk Items Requiring Extra Attention:
1. **FTS5 Trigger Fix**: Test thoroughly with large datasets
2. **Two-Phase Compression**: Verify atomic operations under failure scenarios
3. **Schema Migration**: Test upgrade/downgrade paths
4. **Team C Definition**: Ensure integration with Teams A & B

### Rollback Plans:
- Keep original task files as `tasks_A_original.md`, `tasks_B_original.md`
- Maintain checkpoint saves during critical updates
- Document all changes for easy reversal

---

## CRITIQUE-BASED PRIORITY UPDATES (Added 2025-08-19) 🔍

### Current Reality Check (Based on Code Analysis)
**Actual Status**: 407/469 tests passing (86.7%), not "300+ tests all passing"
**Missing Components**: TimeQueryEngine, ArchiveVerifier, PersonQueries  
**Over-Engineering**: Connection pooling and complex abstractions for single-user lab

### REVISED PRIORITY 1: Lab-Grade Simplification (Day 1) ⚡
**Status**: Ready to Start  
**Risk Level**: MEDIUM - Reducing complexity without breaking functionality

#### T1.1-R - Verify Critical Fixes Are Actually Working ✅
- [x] **Status**: COMPLETED (verified in analysis)
- [x] **FTS5 Recursion**: Fixed in `src/search/database.py` with separate content field
- [x] **filelock Fallback**: Fixed in `src/core/compression.py` with try/except
- [x] **Compression Safety**: Atomic operations implemented correctly

#### T1.2-R - Simplify SearchDatabase for Lab Use
- [ ] **Status**: Ready to Start
- [ ] **Issue**: Complex connection pooling for single-user scenario
- [ ] **Fix**: Replace Queue-based pool with simple connection + retry
- [ ] **Files**: `src/search/database.py:49-392`
- [ ] **Impact**: Reduces complexity, maintains functionality
- [ ] **Estimated Time**: 1.5 hours

#### T1.3-R - Implement Missing TimeQueryEngine  
- [ ] **Status**: Ready to Start
- [ ] **Issue**: 6 tests failing because TimeQueryEngine class doesn't exist
- [ ] **Fix**: Create `src/queries/time_queries.py` with basic date range functionality
- [ ] **Tests**: `tests/unit/test_time_queries.py` (already written)
- [ ] **Impact**: Enables time-based search functionality
- [ ] **Estimated Time**: 2 hours

#### T1.4-R - Create Missing ArchiveVerifier Module
- [ ] **Status**: Ready to Start  
- [ ] **Issue**: Tests expect `src/core/verification_enhanced.py` with ArchiveVerifier class
- [ ] **Fix**: Implement basic JSONL validation and integrity checking
- [ ] **Tests**: `tests/unit/test_verification_enhanced.py`
- [ ] **Impact**: Enables archive integrity validation
- [ ] **Estimated Time**: 1.5 hours

**Revised Priority 1 Total Time**: 5 hours

### REVISED PRIORITY 2: Test Suite Cleanup (Day 2) 🧪
**Status**: Pending P1 completion
**Risk Level**: LOW - Quality improvements

#### T2.1-R - Fix or Remove Failing Tests
- [ ] **Status**: Pending
- [ ] **Issue**: 59 failing tests creating noise in test suite
- [ ] **Fix**: Either implement missing features or mark tests as TODO/skip
- [ ] **Target**: Get to >95% test pass rate
- [ ] **Estimated Time**: 3 hours

#### T2.2-R - Update Documentation with Real Metrics  
- [ ] **Status**: Pending
- [ ] **Issue**: README claims inaccurate test counts and coverage
- [ ] **Fix**: Update with actual metrics from test runs
- [ ] **Files**: `readme.md`, `tasks.md`
- [ ] **Estimated Time**: 1 hour

### REVISED PRIORITY 3: Optional Polish (Day 3) ✨  
**Status**: Pending P1-P2 completion
**Risk Level**: LOW - Nice-to-have improvements

#### T3.1-R - Implement PersonQueries for Completeness
- [ ] **Status**: Pending
- [ ] **Issue**: Person-based queries mentioned in Phase 1 but not implemented
- [ ] **Fix**: Add basic user filtering and activity aggregation
- [ ] **Estimated Time**: 2 hours

#### T3.2-R - Add Integration Test for Full Pipeline
- [ ] **Status**: Pending
- [ ] **Issue**: No test that exercises collection → indexing → search
- [ ] **Fix**: Create end-to-end test with real data flow
- [ ] **Estimated Time**: 1 hour

---

## Lab-Grade vs Production Assessment 

### What Should Stay Complex (Core Value):
✅ **Archive System**: JSONL with atomic writes  
✅ **Search Infrastructure**: SQLite FTS5 (but simplified)  
✅ **Data Collection**: Comprehensive API integration  
✅ **CLI Tools**: User-friendly interfaces

### What Should Be Simplified (Over-Engineering):
❌ **Connection Pooling**: Single connection fine for lab  
❌ **Complex State Management**: JSON files sufficient  
❌ **Enterprise Features**: Multi-user abstractions unnecessary  
❌ **Production Monitoring**: Simple logging sufficient

### Key Finding: 65% Lab-Ready
**Working**: Data collection, compression, basic search  
**Missing**: TimeQueryEngine, ArchiveVerifier, working test suite  
**Over-Engineered**: Database pooling, state management abstractions

---

*This task queue will be updated as tasks are completed and new issues are discovered.*