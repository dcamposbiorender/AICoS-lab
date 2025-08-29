# Plan Archive - Detailed Implementation Specifications

This file contains the detailed implementation specifications that were moved from plan.md to reduce context consumption. All information is preserved but archived to keep the main plan.md focused on current status and high-level direction.

---

## Implementation Phases

### Phase 1: Deterministic Foundation

**Objectives**: Establish core deterministic infrastructure for immediate value delivery

**Modules to Implement**:
- Data collectors built new using learned patterns from scavenge/
- SQLite FTS5 for full-text search with incremental indexing
- Time-based and person-based queries
- Basic calendar coordination (free slot finding)
- Structured extraction (dates, @mentions, TODO/DEADLINE tags)
- Simple statistical aggregations
- Archive storage with JSONL + daily gzip compression, 90-day hot storage
- Environment-based configuration with startup validation
- Atomic state operations with proper file locking
- Circuit breaker pattern for API resilience
- Checkpoint/resume capabilities for long operations

**Patterns to Extract from scavenge/**:
- SlackRateLimiter's sophisticated rate limiting logic with jitter
- Atomic file write pattern using temp files + rename
- Collection rules system (include/exclude patterns, must_include overrides)
- Multi-location credential fallback concept (simplified to single source)
- Error handling and retry patterns with exponential backoff

**Deliverables**:
- Unified search across all data sources
- Basic calendar scheduling without AI
- Time-range queries ("yesterday", "last week")
- Person-based data retrieval
- CLI tools for all operations
- Complete data collection and archival

**Test Success Criteria**:
- All operations run without LLM
- Full-text search returns accurate results
- Calendar coordination finds valid slots
- State persists across restarts
- Configuration validates all paths and credentials
- Data collection maintains complete history

**Completion**: When entire data pipeline provides immediate value through unified search and basic coordination

### Phase 1.5: Content Extraction Layer

**Objectives**: Bridge deterministic foundation with intelligent features through local content extraction

**Drive Content Extraction Strategy** (Inspired by DriveToRag analysis):
- **Priority 1**: Google Docs & PDFs (most executive content)
  - Google Docs API for native text extraction
  - PyPDF2/pdfplumber for local PDF processing
  - OCR fallback for image-based PDFs (local processing only)
- **Priority 2**: Spreadsheets (data and reports)  
  - gspread for Google Sheets
  - openpyxl for Excel files
  - CSV parsing for exported data
- **Priority 3**: Images with OCR (screenshots, diagrams)
  - Local OCR libraries (pytesseract) 
  - No external API dependencies

**File Type Handling** (From DriveToRag patterns):
- MIME type routing: `application/vnd.google-apps.document` → DocsExtractor
- Content hashing: SHA256 for change detection and deduplication
- Incremental processing: Only extract when content hash changes
- Format normalization: All content → clean text for Phase 1 FTS5 indexing

**Architecture Integration**:
- Maintains local-first approach (no external APIs)
- Content stored alongside JSONL metadata for complete audit trail
- FTS5 indexing enhanced with extracted content
- Preserves Phase 1 deterministic principles

**Deliverables**:
- `src/extractors/drive_content.py` - Content extraction engine
- Enhanced Drive collector with content extraction capability
- Content-aware search across document text
- Change detection prevents redundant processing
- Complete local processing pipeline

**Success Criteria**:
- Extract readable text from 95% of document files
- Change detection prevents duplicate processing
- Search finds content within documents ("quarterly goals mentioned in docs")
- No external service dependencies
- Content extraction completes in <30 seconds per document

**Completion**: When Drive files are searchable by content while maintaining audit trail and local-first principles

### Phase 2: Intelligence Layer

**Objectives**: Add LLM-powered semantic understanding while maintaining deterministic foundation

**Modules to Implement**:
- LLM-based commitment extraction with confidence scoring
- Goal detection and status inference
- Intelligent briefing generation
- Sentiment analysis and urgency detection
- Semantic search capabilities (including Drive document content from Phase 1.5)
- Vector embeddings for document similarity and retrieval
- Pattern recognition and anomaly detection
- Cascading memory system for context preservation
- Human validation workflows for low-confidence extractions

**Approach**:
- All LLM outputs include confidence scores
- Human review for items below threshold
- Every extraction links to source data
- Fallback to Phase 1 functionality if LLM unavailable
- Pattern learning from validated examples

**Deliverables**:
- Natural language commitment extraction
- Goal tracking with automatic status updates
- AI-generated daily and weekly briefings
- Predictive nudging for deadlines
- Semantic search ("discussions about Q3")
- Sentiment-based urgency detection

**Test Success Criteria**:
- Commitment extraction accuracy ≥80% (with validation)
- Goal status inference matches user expectations
- Briefings provide actionable insights
- All AI outputs traceable to sources
- Graceful degradation to Phase 1 features

**Completion**: When AI features demonstrate clear value over Phase 1 baseline

### Phase 3: Memory Architecture [EVALUATED - NOT RECOMMENDED]

**Decision Date**: August 21, 2025  
**Decision**: After evaluating sophisticated memory systems (Memori, M3, Knowledge Graphs), we've decided NOT to implement complex memory layers.

**Rationale**: See [docs/architecture_decisions/memory_systems_analysis.md](docs/architecture_decisions/memory_systems_analysis.md)
- Current system already achieves <1 second queries with 340K+ records
- Memory layers would add 50-100% latency without proportional value  
- 3x maintenance burden for theoretical problems, not actual user pain points
- Architecture anti-pattern: Simple → Complex → Broken → Simple

**Alternative Approach**: Focus on high-value, low-complexity improvements:

#### Recommended Enhancements (Instead of Memory Layers)

**Query Result Caching** (1 day effort, 80% benefit):
```python
class QueryCache:
    def __init__(self, ttl=3600):
        self.cache = {}  # query_hash -> (result, timestamp)
```
- Instant responses for repeated queries
- Minimal complexity, maximum impact

**User Preference Learning** (2 days effort):
```python  
class UserPreferences:
    def track_patterns(self):
        # Track query sources, time ranges, common terms
        # Personalize without complex memory systems
```
- Actual personalization without architectural complexity
- Learn from usage patterns to improve relevance

**Smart Importance Scoring** (2 days effort):
- Better RAG prioritization using existing signals
- Time decay factors, interaction tracking
- Cross-reference bonuses for connected documents

**Daily/Weekly Summaries** (3 days effort):
- Proactive information delivery without AI memory
- Activity pattern recognition using deterministic aggregation
- No complex memory cascade needed

### Phase 4: Slack Bot Integration

**Objectives**: Build comprehensive Slack bot interface that exposes all Phase 1 functionality through natural slash commands with enterprise-grade security and permission management

**Architecture Philosophy**: Slack bot as thin orchestration layer over existing deterministic tools with comprehensive OAuth scope validation, encrypted credential management, and proactive permission checking. No new business logic - only secure user interface and workflow coordination.

#### Core Integration Strategy

**Leverage Existing Infrastructure**:
- Direct integration with existing CLI tools (search_cli.py, find_slots.py, query_facts.py)
- Use SearchDatabase directly for <1s search responses
- Wrap AvailabilityEngine for calendar coordination
- Reuse all authentication and rate limiting logic
- **NEW**: Integrate OAuth scope management system (84 comprehensive permissions)
- **NEW**: Use permission_checker.py for proactive API validation
- **NEW**: Leverage encrypted credential storage for secure token management

**Slash Commands → CLI Tool Mapping**:
- `/cos search [query]` → SearchDatabase (340K+ records, <1s response)
- `/cos schedule @person [duration]` → AvailabilityEngine + ConflictDetector
- `/cos goals` → StructuredExtractor patterns for goal tracking
- `/cos brief` → daily_summary.py wrapper with Slack formatting
- `/cos commitments` → query_facts.py pattern extraction
- `/cos help` → Interactive help with command buttons

#### Technical Foundation

**Dependencies (Already Available)**:
- slack-sdk==3.33.2 and slack-bolt==1.21.2 ✅
- Search infrastructure with FTS5 (340K+ records) ✅
- Query engines (time, person, structured) ✅
- Calendar coordination (AvailabilityEngine, ConflictDetector) ✅
- Authentication system (credential_vault) ✅
- **NEW**: OAuth scope management (slack_scopes.py) with 84 permissions ✅
- **NEW**: Runtime permission checker (permission_checker.py) with 40+ API endpoints ✅
- **NEW**: Encrypted credential storage with AES-256 encryption ✅
- **NEW**: Comprehensive scope validation and CLI management tools ✅

**Simplified Bot Architecture**:
```
src/bot/
├── __init__.py
├── slack_bot.py              # Simple Slack Bolt application
├── commands/                 # Basic command handlers
│   ├── search.py             # /cos search
│   ├── brief.py              # /cos brief  
│   └── help.py               # /cos help
└── utils/                    # Basic utilities
    ├── formatters.py         # Simple message formatting
    └── cli_wrapper.py        # Basic CLI integration
```

#### Implementation Phases

**Phase 4a: Basic Bot Foundation (2-3 hours)**
- Simple Slack Bolt application setup using existing oauth tokens
- Basic integration with auth_manager.py and permission_checker.py
- Essential error handling without complex middleware
- Use existing SlackRateLimiter from collectors

**Phase 4b: Core Commands (3-4 hours)**
- `/cos search` - Direct integration with SearchDatabase, basic permission checking
- `/cos brief` - Simple wrapper around existing daily_summary.py
- `/cos help` - Basic command documentation
- Simple Slack message formatting (plain text + basic formatting)
- Basic error messages with permission guidance

**Phase 4c: Testing & Deployment (1-2 hours)**
- Basic smoke tests to ensure commands work
- Simple deployment script using existing tools/run_slack_bot.py
- Documentation for installation and usage
- Validate OAuth scope integration works correctly

#### Success Metrics

**Performance Targets**:
- Command responses within 3 seconds ✅
- Search operations complete in <1 second ✅
- Basic permission checking functional ✅
- 95% command success rate with simple error handling

**User Experience Goals**:
- Commands work reliably without crashing
- Basic error messages are helpful
- Zero learning curve for executives

**Integration Validation**:
- Basic CLI functionality accessible via bot
- OAuth scope system integration works
- Simple deployment and setup process

#### Deliverables

**Core Bot Implementation**:
- Working Slack app using existing OAuth tokens
- 3 basic slash commands (/cos search, /cos brief, /cos help)
- Simple message responses with basic formatting
- Basic error handling that doesn't crash

**Integration Components**:
- Simple CLI tool wrapper for search and briefing
- Basic Slack message formatting
- Use existing rate limiting from collectors
- Integration with existing auth_manager.py

**Testing & Validation**:
- Basic smoke tests to ensure commands respond
- Simple integration tests with existing CLI tools
- Manual testing in real Slack workspace

**Documentation**:
- Simple Slack app setup guide using existing tokens
- Basic command reference with examples
- Installation and usage instructions

**Completion Criteria**: When executives can perform basic system functions (search, briefing) through simple Slack commands that work reliably without crashing.

---

**Detailed Implementation Plan**: See [slackbot_tasks.md](slackbot_tasks.md) for complete test-driven development specifications, acceptance criteria, and implementation tasks.

### Phase 4.5: Lab-Grade Frontend Dashboard

**Objectives**: Build a real-time, keyboard-driven dashboard with paper-dense aesthetic that synchronizes with existing backend infrastructure and Slack bot

**Architecture Philosophy**: Minimal complexity, maximum functionality - leverage existing collectors and search infrastructure through simple API and WebSocket connections. No over-engineering for lab-grade deployment.

#### Core Components

**Backend API Server** (`backend/server.py`)
- FastAPI with WebSocket support for real-time state broadcasting
- In-memory state management (no Redis needed for single-user lab)
- Direct integration with existing SearchDatabase (340K+ records)
- Simple command parser for "approve P7" style natural language commands

**Dashboard Frontend** (`dashboard/index.html`)
- Enhanced cos-paper-dense.html mockup with WebSocket client
- Real-time updates from backend state changes via WebSocket
- Command input with keyboard navigation and history
- Preserves exact paper-dense terminal aesthetic from mockup

**Coding System Implementation** (C1, P1, M1)
- Automatic ID generation for all items (Calendar=C1-Cn, Priority=P1-Pn, Commitments=M1-Mn)
- Consistent coding across dashboard and Slack interfaces
- Enables rapid keyboard navigation and command execution

**State Synchronization**
- WebSocket broadcasting keeps all connected clients synchronized
- Dashboard and Slack bot share same backend API
- Real-time progress updates during data collection
- Atomic state updates with optimistic UI updates

#### Implementation Timeline (5 days)

**Day 1-2**: Parallel Core Development
- **Agent E**: Backend API Foundation - FastAPI + WebSocket broadcasting system
- **Agent F**: Dashboard Frontend - Convert static mockup to dynamic interface  
- **Agent G**: Coding System - Implement C1/P1/M1 identification and management

**Day 3**: System Integration
- **Agent H**: Integration & Commands - Connect collectors, implement command parser, sync Slack bot

**Day 4-5**: Testing & Deployment
- **Agent I**: Testing & Polish - End-to-end testing, performance validation, bug fixes

#### Technical Architecture

**Dependencies Leveraged**:
- Existing SearchDatabase with 340K+ indexed records
- Working collectors (Slack, Calendar, Drive, Employee)
- Established authentication system (credential_vault)
- Proven Slack bot infrastructure

**New Infrastructure**:
- FastAPI backend with WebSocket endpoints
- Browser-based dashboard with WebSocket client
- Unified command parser for both interfaces
- Real-time state management and broadcasting

#### Key Features Delivered

**Real-Time Dashboard**:
- System status with collection progress bars
- Today's calendar with conflict detection
- Priority list with completion tracking  
- Commitment tracking (owed/owing)
- Live command execution with immediate feedback

**Command System**:
- Natural language commands: "approve P7", "brief C3", "refresh"
- Keyboard shortcuts and navigation
- Command history with up/down arrows
- Pipe operator support for chained commands

**State Synchronization**:
- Dashboard updates instantly reflect in Slack
- Slack commands update dashboard in real-time
- Collection progress visible across all interfaces
- No state conflicts with single-user lab deployment

#### Success Metrics

**Performance Targets**:
- Dashboard loads in <3 seconds
- Command execution responds in <200ms
- State updates propagate in <100ms
- WebSocket reconnection in <1 second

**Functional Requirements**:
- Commands work identically in dashboard and Slack
- State remains synchronized across all interfaces  
- Preserves exact paper-dense aesthetic from mockup
- Leverages all existing backend infrastructure

**Lab-Grade Simplifications**:
- In-memory state (no database persistence needed)
- Single-user deployment (no authentication)
- Modern browser support only (Chrome/Firefox)
- Local deployment (no production hosting)

#### Risk Mitigation

**WebSocket Reliability**:
- Automatic reconnection with exponential backoff
- State resync on reconnection
- Graceful degradation to polling if needed

**State Consistency**:
- Last-write-wins conflict resolution (acceptable for single user)
- Atomic updates where possible
- State validation on API boundaries

**Performance Optimization**:
- Debounced updates for rapid changes
- Efficient DOM updates using targeted selectors
- Lazy loading for large datasets

#### Deliverables

**Working Dashboard**:
- Real-time synchronized interface matching mockup exactly
- Full keyboard navigation and command execution
- WebSocket connection with auto-reconnection

**Enhanced Slack Bot**:
- Updated to use shared backend API
- Commands trigger real-time dashboard updates
- Consistent command parser across interfaces

**Integration Components**:
- Backend API connecting existing collectors to frontend
- WebSocket broadcasting system for real-time updates
- Command parsing system supporting natural language

**Testing & Documentation**:
- End-to-end test suite validating all workflows
- Performance benchmarks documenting response times
- Setup guide for lab deployment

**Completion Criteria**: When dashboard provides real-time view of system state, commands execute identically across interfaces, and aesthetics match mockup exactly while leveraging existing backend infrastructure.

---

**Detailed Implementation Plan**: See individual agent task files:
- [frontend_agent_e_backend.md](tasks/frontend_agent_e_backend.md) - Backend API & WebSocket
- [frontend_agent_f_dashboard.md](tasks/frontend_agent_f_dashboard.md) - Dashboard Frontend
- [frontend_agent_g_coding.md](tasks/frontend_agent_g_coding.md) - Coding System (C1/P1/M1)
- [frontend_agent_h_integration.md](tasks/frontend_agent_h_integration.md) - Integration & Commands
- [frontend_agent_i_testing.md](tasks/frontend_agent_i_testing.md) - Testing & Polish

### Phase 5: Scale & Optimization

**Objectives**: Optimize for production performance and multi-team deployment

**Modules to Implement**:
- Query optimization and caching layers
- Background processing pipelines
- Storage compression for archives
- Advanced pattern recognition
- Cross-source correlation
- Team dynamics analysis

**Optimization Targets**:
- Support 3-10 executives per instance
- Briefing generation <30 seconds
- Search response <2 seconds
- Collection lag: Slack ≤5min, Calendar ≤60min
- Storage growth sustainable for 1+ year retention

**Advanced Features**:
- Email integration preparation
- Document content analysis (beyond metadata)
- External calendar support
- Third-party tool webhooks
- Multi-team isolation and permissions

**Test Success Criteria**:
- Performance meets all targets under load
- Multi-user scenarios work correctly
- Storage efficiently compressed
- Cross-source insights accurate
- System scales to team size

**Completion**: When system ready for enterprise deployment

### Phase 6: User-Centric Architecture (Lab-Grade)

**Objectives**: Transform the system from treating all employees equally to recognizing the PRIMARY USER as central, with simple personalization and comprehensive setup wizard for lab-grade deployment.

**Core Philosophy**: Keep it simple and practical for lab-grade deployment. No enterprise features or over-engineering. Focus on making David Campos (or any primary user) the center of all data and interactions.

**Problem Being Solved**:
- Current system treats all employees equally - no awareness of who THE USER is
- Dashboard shows demo data instead of user's actual calendar
- Briefs don't prioritize user's activities and commitments
- Complex setup process requires manual configuration of tokens, APIs, and credentials
- No concept of relevance based on relationship to user

**Solution Architecture**:
```
src/
├── core/
│   └── user_identity.py      # Simple PRIMARY_USER configuration
├── cli/
│   └── setup_wizard.py       # Interactive setup for all components
└── personalization/
    └── simple_filter.py      # Basic filtering for user data
```

**Modules to Implement**:
- User identity configuration with PRIMARY_USER setting
- Comprehensive setup wizard for first-time installation covering:
  - Environment configuration (directories, database, paths)
  - Slack API tokens and workspace authentication
  - Google Calendar OAuth and credentials setup
  - Google Drive API authentication
  - User identity configuration and verification
  - Initial data collection and search indexing
- Simple personalization for dashboard and briefs
- Basic relevance boosting for user-related content in search results

**Key Features Delivered**:

**Comprehensive Setup Wizard**:
- Interactive CLI that guides through complete system configuration
- Validates all API credentials during setup process
- Creates required directories and initializes database
- Configures user identity with cross-system mapping
- Runs initial data collection to verify everything works
- Completes in <5 minutes with clear progress indicators

**User-Centric Data Presentation**:
- Dashboard loads user's actual calendar (not sample data)
- Briefs prioritize user's meetings, commitments, and mentions
- Search results boost user-relevant content by 50%
- All data filtered and organized around user's perspective

**Simple Configuration Management**:
- PRIMARY_USER setting stored in configuration
- Identity mapping across Slack, Calendar, and Drive
- Backwards compatible with non-personalized mode
- Environment-based configuration with validation

**Architecture Components**:

**User Identity System** (`src/core/user_identity.py`):
- Simple PRIMARY_USER configuration class (~50 lines)
- Cross-system identity mapping (email ↔ Slack ID ↔ Calendar ID)
- Validation that user exists in all connected systems
- Backwards compatibility when no PRIMARY_USER configured

**Setup Wizard** (`src/cli/setup_wizard.py`):
- Interactive CLI for complete system setup (~200 lines)
- Environment setup (directories, database, paths)
- API credential configuration and validation
- User identity setup and verification
- Initial data collection and indexing
- Clear error handling and progress indication

**Personalization Layer** (`src/personalization/simple_filter.py`):
- Simple filtering for user-centric data presentation (~100 lines)
- Relevance boosting for user-related search results
- Calendar filtering to show user's events prominently
- Brief personalization focusing on user activities

**Implementation Timeline** (3-4 days):

**Day 1: User Identity Foundation** (Agent J - 4 hours)
- Create user identity configuration module
- Integrate PRIMARY_USER into config system
- Implement cross-system identity mapping
- Add comprehensive test coverage

**Day 2-3: Comprehensive Setup Wizard** (Agent K - 8-12 hours)
- Build interactive CLI setup wizard
- Implement environment and directory setup
- Add API credential configuration flows
- Create user identity setup process
- Add validation and initial data collection

**Day 4: Personalization Integration** (Agent L - 8 hours)
- Update dashboard to use user's actual data
- Modify briefs to prioritize user activities
- Implement simple search relevance boosting
- Integrate personalization across all components

**Success Metrics**:
- Setup wizard completes without errors in <5 minutes
- Dashboard shows user's actual calendar data (not demo data)
- Briefs focus primarily on user's activities and mentions
- Search results prioritize user-relevant content
- All API credentials configured and validated
- System works immediately after setup completion

**Test Success Criteria**:
- All API connections validated during setup
- User identity correctly mapped across all systems
- Dashboard loads user-specific calendar data
- Brief generation prioritizes user's meetings and commitments
- Search relevance boosting increases user-related results
- Backwards compatibility maintained for unconfigured systems

**Risk Mitigation**:
- Graceful fallback when PRIMARY_USER not configured
- Clear error messages for setup failures
- Re-runnable wizard for configuration updates
- Validation of all credentials before storage
- Simple, maintainable code without over-engineering

**Lab-Grade Simplifications**:
- Single-user focus (no multi-user complexity)
- Simple relevance boosting (no complex algorithms)
- Basic personalization (no machine learning)
- Interactive setup (no web-based configuration)
- Local credential storage (no enterprise key management)

**Integration Points**:
- Collectors add PRIMARY_USER context to all data collection
- Dashboard filters calendar data for user's events
- Brief generation prioritizes user's activities and mentions
- Search engine boosts user-relevant results
- All authentication flows use setup wizard credentials

**Deliverables**:
- Working setup wizard configuring entire system from scratch
- PRIMARY_USER configuration integrated throughout codebase
- Dashboard displaying user's actual calendar data
- Personalized briefs focusing on user activities
- Search results with user relevance boosting
- Complete test coverage for all personalization features
- Simple, maintainable lab-grade implementation

**Files Created** (~500 lines total):
- `src/core/user_identity.py` - User identity configuration
- `src/cli/setup_wizard.py` - Interactive setup wizard
- `src/personalization/simple_filter.py` - Basic personalization
- `tools/setup.py` - Wizard entry point
- Corresponding test files

**Files Modified**:
- `src/core/config.py` - Add PRIMARY_USER configuration
- `tools/load_dashboard_data.py` - Load user-specific data
- `src/bot/commands/brief.py` - Personalize brief generation
- Search components for relevance boosting

**Completion Criteria**: When system recognizes the primary user, provides comprehensive setup wizard covering all components, and delivers personalized experiences through simple, maintainable lab-grade code.

---

**Detailed Implementation Plan**: See individual agent task files:
- [phase6_agent_j_user_identity.md](tasks/phase6_agent_j_user_identity.md) - User Identity Configuration
- [phase6_agent_k_setup_wizard.md](tasks/phase6_agent_k_setup_wizard.md) - Comprehensive Setup Wizard
- [phase6_agent_l_personalization.md](tasks/phase6_agent_l_personalization.md) - Personalization Integration

## Module Specifications

### Phase 1: Deterministic Modules

**Data Collectors**
- Return JSON-serializable facts only
- No LLM involvement whatsoever
- Include source, timestamp, cursor information
- Handle rate limiting and retries
- Leverage existing scavenge/ implementations

**Search & Indexing**
- Full-text search across all sources
- Time-based retrieval and filtering
- Person-based queries and aggregations
- Keyword and phrase matching
- No semantic understanding required

**Calendar Coordination**
- Find free slots across calendars
- Handle timezone conversions
- Detect conflicts and overlaps
- No intelligence, just availability math

**Structured Extractors**
- Use regex for TODO, DEADLINE patterns
- Extract @mentions and hashtags
- Parse dates and times
- Identify meeting titles and attendees
- Never attempt natural language understanding

### Phase 2+: Intelligence Modules

**LLM Extractors**
- Commitment extraction with confidence scores
- Goal identification and ownership
- Sentiment analysis for urgency
- Meeting outcome detection
- All extractions include source references

**Pattern Analyzers**
- Identify communication patterns
- Detect anomalies and changes
- Recognize recurring themes
- Track relationship dynamics
- Generate trend insights

**Memory System**
- AI-powered summarization for cascades
- Maintain context across time periods
- Generate statistical and semantic summaries
- Enable historical pattern queries
- Preserve full audit trail

**Intent Router**
- Parse user input to tool sequences
- Understand natural language commands
- Route to appropriate handlers
- Never generate facts, only orchestrate
- Handle ambiguous requests with clarification

**Output Formatter**
- Convert JSON to readable text
- Maintain source attribution in output
- Format for target medium (Slack, CLI, etc.)
- Never add information not in source data
- Preserve confidence scores in presentation

## Testing Strategy

### Testing Philosophy

**Test Boundaries, Not Implementation**

Focus testing on:
- Data contracts (JSON schemas)
- Tool input/output validation
- State transitions
- Integration points
- Critical business logic

Skip testing:
- LLM outputs directly (non-deterministic)
- Simple getters/setters
- Third-party library internals
- Display formatting details

### Test Categories by Phase

**Phase 1 Tests (Deterministic)**
- Collection completeness
- Search accuracy
- Calendar math correctness
- Data integrity
- State persistence

**Phase 2+ Tests (Intelligence)**
- Extraction accuracy against golden dataset
- Confidence threshold validation
- Source attribution presence
- Fallback to Phase 1 features
- Human validation workflow

### Coverage Strategy

- Contract Tests: 100% coverage required (all phases)
- Phase 1 Integration Tests: 90% coverage
- Phase 2+ Integration Tests: 80% coverage
- Unit Tests: 60% for complex logic
- LLM Tests: 50% using golden datasets
- Smoke Tests: 100% coverage
- Overall Target: 70-80% coverage

## Implementation Strategy

### Evolutionary Approach

**Start Clean with Pattern Reuse**
- Build new implementations using learned patterns from scavenge/
- Extract valuable logic patterns, not code directly
- Establish clean architecture boundaries from day one
- Create new collectors following consistent interfaces
- Implement proper separation of concerns throughout

**Progressive Enhancement Pattern**
- Phase 1 delivers immediate value
- Each phase builds on previous
- Graceful degradation if higher phases fail
- Users can stay on Phase 1 if preferred
- Clear boundaries between phase features

**Incremental Migration**
- Wrap existing collectors first
- Add search and indexing
- Implement basic coordination
- Layer intelligence carefully
- Never break working features

### Configuration Management

Phase 1:
- Environment variable AICOS_BASE_DIR for portable base path
- Single Config class with comprehensive validation
- Test all credentials actually work (not just exist)
- Verify all paths are writable at startup
- Check disk space requirements before operations
- Fail fast on configuration issues

Phase 2+:
- Add LLM API configurations
- Confidence thresholds
- Human validation settings
- Memory cascade parameters

### State Management

All Phases:
- Atomic file operations using temp files and rename
- File locking for concurrent access
- State migration capabilities
- Backup before modifications
- Recovery procedures for corruption

Phase 2+ additions:
- Validation state for extractions
- Confidence history tracking
- Pattern learning storage
- Memory cascade state

## Risk Mitigation

### Phase 1 Risks (Low)

**Data Collection**
- Use proven scavenge/ implementation
- Sophisticated rate limiting already built
- Error handling thoroughly tested

**Search & Storage**
- Simple append-only operations
- Standard full-text indexing
- No complex transformations

### Phase 2+ Risks (Medium)

**LLM Integration**
- Confidence scoring reduces bad extractions
- Human validation catches errors
- Fallback to Phase 1 features
- Source attribution prevents hallucination

**Memory System**
- Cascading can fall back to simple storage
- AI summaries validated against sources
- Statistical summaries as backup

### Cross-Phase Risks

**Authentication Failures**
- Reuse proven scavenge/ auth system
- Credential validation before execution
- Graceful fallbacks

**Data Loss**
- Append-only fact storage
- Complete historical archive
- Immutable data preservation
- Regular backup procedures

**Performance Degradation**
- Phase 1 features always fast
- AI features can be disabled
- Caching for expensive operations
- Background processing for non-critical

## Success Metrics

### Phase 1 Metrics
- Context hunting time: ≤10 minutes/day
- Search response time: <2 seconds
- Calendar coordination: 3+ meetings/week
- Data collection completeness: 100%
- Zero data loss incidents

### Phase 2 Metrics
- Commitment extraction accuracy: ≥80%
- Goal tracking agreement: ≥90%
- Briefing usefulness rating: >4/5
- AI insight accuracy: ≥85%
- Source attribution: 100%

### Phase 3 Metrics
- Memory cascade reliability: >99%
- Historical query accuracy: ≥95%
- Context preservation: 100%
- Summary quality rating: >4/5

### Phase 4 Metrics
- Bot uptime: >99%
- Command success rate: >95%
- Dashboard load time: <3 seconds
- User adoption: 100% of team

### Phase 5 Metrics
- Multi-user support: 3-10 executives
- Performance under load: meets all targets
- Storage efficiency: <20% monthly growth
- Cross-source insights: ≥80% valuable

### Overall Success Criteria
- 14 consecutive days of usage
- Zero hallucinated facts
- Complete audit trail maintained
- User trust score: >4.5/5
- All Phase 1 features rock-solid