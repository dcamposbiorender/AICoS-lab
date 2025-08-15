# ARCHITECTURE.md - AI Chief of Staff System Architecture

## System Design Overview

The AI Chief of Staff is built on a four-layer architecture with deterministic processing, LLM assistance, and complete transparency. The system follows a strict separation of concerns where Claude Code acts as orchestrator, calling deterministic tools that produce structured JSON outputs.

## Core Design Principles

### 1. Claude Code as Orchestrator Only
- The LLM orchestrates by invoking tools via safe subprocess calls
- It never reads or writes data stores directly
- All tool outputs are structured JSON; the orchestrator reasons over these outputs and decides next steps
- No direct mutations by the LLM; all state persisted in append-only JSONL

### 2. Tool Pattern (Deterministic, Composable)
- **Inputs**: flags or environment variables; no hidden state
- **Execution**: tool runs to completion; prints a single JSON object to stdout; uses exit codes for success/failure
- **Outputs**: status, counters (e.g., slack_messages, calendar_events), paths to artifacts, and any warnings
- **Example behavior**: a collect_data tool returns status=success and counts of items collected across sources; orchestrator logs the result and schedules processing

### 3. Module Independence
- Each module (collector, processor, interface) can run standalone
- Modules communicate via files (JSON/JSONL) under data/; no shared memory
- Contracts: clearly defined input and output schemas; versioned if needed
- Fail-open for non-critical paths: partial results are accepted and marked; system remains operable

### 4. Deterministic-First, LLM-Assist
- Collection and processing are deterministic and reproducible
- LLMs are used for text understanding (e.g., commitment extraction, summarization), never for direct state mutation
- Human approval required for any action with external effects

### 5. Explainability & Traceability
- Every surfaced item links to raw_reference (file path and record index) and lists the processing steps taken
- Complete audit trail from raw data to user-facing insights

## Four-Layer Architecture

### Layer 1: Collection (Deterministic)
**Purpose**: Complete, continuous, append-only data capture from all sources

**Components**:
- **SlackCollector**: All channels, DMs, threads with metadata and users
- **CalendarCollector**: Internal calendars with attendees and event metadata  
- **DriveCollector**: Document activity and changes (metadata-only in MVP)
- **EmployeeCollector**: Roster mapping Slack IDs, emails, and calendar IDs

**Guarantees**:
- Never overwrite existing data
- Complete capture within defined lag times
- Structured storage with timestamps
- Rate limit compliance with backoff

### Layer 2: Processing (Deterministic)
**Purpose**: Transform raw data into structured, queryable formats

**Components**:
- **Change Detection**: Identify meaningful updates across all data sources
- **Deduplication**: Eliminate redundant information and normalize formats
- **Relevance Scoring**: Prioritize information for briefing inclusion
- **State Management**: Maintain cursors, timestamps, and processing status
- **Anomaly Detection**: Flag unusual patterns requiring attention

**Operations**:
- Incremental processing with cursor management
- Conflict resolution and data validation
- Performance metrics and quality scoring
- Error tracking and recovery

### Layer 3: Intelligence (LLM)
**Purpose**: Extract semantic meaning and generate insights from processed data

**Components**:
- **Commitment Extraction**: Identify promises and deadlines from conversations
- **Goal Status Inference**: Determine progress from activity patterns
- **Context Synthesis**: Generate actionable briefings from raw activity
- **Intent Recognition**: Parse scheduling requests and preferences
- **Summarization**: Create concise overviews of complex information

**Constraints**:
- Read-only access to processed data
- Outputs structured JSON only
- Human confirmation for ambiguous extractions
- Source attribution for all insights

### Layer 4: Interface
**Purpose**: Surface insights and enable user interaction

**Components**:
- **Slack Bot**: Interactive commands and rich message formatting
- **CLI Tools**: Administrative commands and data management
- **Dashboard**: Simple HTML views for transparency and audit
- **Briefing Engine**: Automated digest generation and delivery

**Features**:
- Real-time command processing
- Interactive approval workflows
- Comprehensive error handling
- Accessibility and mobile support

## Project Structure

```
ai-cos-lab/
├── .git/
├── .gitignore                    # Excludes data/, logs/, .env, caches
├── README.md                     # Project overview & setup
├── DEVELOPMENT_LOG.md            # Daily progress tracking
├── ARCHITECTURE.md               # System design decisions (this file)
├── requirements.txt              # Python dependencies
├── .env.example                  # Template for credentials
├── Makefile                      # Common commands
├── pyproject.toml               # Python project configuration
├── pytest.ini                  # Test configuration
├── .pre-commit-config.yaml      # Git hooks configuration
│
├── src/                         # Core application code
│   ├── __init__.py
│   ├── core/                    # Shared infrastructure
│   │   ├── __init__.py
│   │   ├── config.py            # Configuration management
│   │   ├── state.py             # State persistence utilities
│   │   ├── logging.py           # Structured logging setup
│   │   └── exceptions.py        # Custom exception classes
│   │
│   ├── collectors/              # Data collection modules
│   │   ├── __init__.py
│   │   ├── base.py              # Base collector class
│   │   ├── slack.py             # Slack API collector
│   │   ├── calendar.py          # Google Calendar collector
│   │   ├── drive.py             # Google Drive collector
│   │   └── employees.py         # Employee roster builder
│   │
│   ├── processors/              # Data processing modules
│   │   ├── __init__.py
│   │   ├── base.py              # Base processor class
│   │   ├── goals.py             # Goal state management
│   │   ├── commitments.py       # Commitment extraction
│   │   ├── changes.py           # Change detection
│   │   ├── profiles.py          # Person profile building
│   │   └── relevance.py         # Content relevance scoring
│   │
│   ├── orchestrators/           # Workflow coordination
│   │   ├── __init__.py
│   │   ├── base.py              # Base orchestrator class
│   │   ├── scheduler.py         # Meeting scheduler
│   │   ├── briefing.py          # Digest generator
│   │   └── feedback.py          # Feedback processor
│   │
│   └── interfaces/              # User interaction layers
│       ├── __init__.py
│       ├── cli.py               # Command-line interface
│       ├── slack_bot.py         # Slack bot implementation
│       ├── dashboard.py         # Web dashboard (simple HTML)
│       └── webhooks.py          # Webhook handlers
│
├── tools/                       # Claude Code callable tools
│   ├── collect_data.py          # Run data collection
│   ├── update_goals.py          # Modify goal states
│   ├── find_slots.py            # Find meeting availability
│   ├── generate_digest.py       # Create briefing
│   ├── process_feedback.py      # Handle user feedback
│   └── health_check.py          # System health validation
│
├── tests/                       # Test suite
│   ├── __init__.py
│   ├── conftest.py              # Pytest configuration and fixtures
│   ├── test_collectors.py       # Collector module tests
│   ├── test_processors.py       # Processor module tests
│   ├── test_orchestrators.py    # Orchestrator module tests
│   ├── test_interfaces.py       # Interface module tests
│   ├── test_tools.py            # Tool integration tests
│   ├── test_e2e.py              # End-to-end workflow tests
│   └── fixtures/                # Test data and mocks
│       ├── slack_data.json
│       ├── calendar_events.json
│       └── sample_goals.json
│
├── scripts/                     # Automation and deployment
│   ├── setup.sh                 # Initial environment setup
│   ├── run_collection.sh        # Manual data collection
│   ├── clean_data.sh            # Data cleanup utilities
│   ├── backup_data.sh           # Data backup procedures
│   └── deploy.sh                # Production deployment
│
├── docs/                        # Additional documentation
│   ├── api.md                   # API reference
│   ├── deployment.md            # Deployment guide
│   ├── troubleshooting.md       # Common issues and solutions
│   └── examples/                # Usage examples
│       ├── slack_commands.md
│       └── briefing_samples.md
│
└── data/                        # Runtime data (gitignored)
    ├── raw/                     # Immutable source data
    ├── processed/               # Derived data and state
    ├── state/                   # System state and cursors
    └── logs/                    # Execution and audit logs
```

## Data Directory Structure

### Data Storage Philosophy
- **Comprehensive**: Collect all relevant Slack, Calendar, and Drive data required for context, commitments, and scheduling coverage
- **Immutable**: Never overwrite. Use append-only logs to ensure complete auditability and reproducible processing
- **Local-First**: Store and process on a secure local system by default; no cloud usage until explicitly enabled
- **Structured**: Use JSONL for raw, time-ordered logs and structured JSON for state and processed views
- **Explainable**: Every derived insight links back to its raw source with file path and record index

### Directory Layout

```
data/ (gitignored)
├── raw/                         # Immutable source data
│   ├── slack/                   # Slack workspace data
│   │   ├── YYYY-MM-DD/          # Daily collection batches
│   │   │   ├── channels.json    # Channel list with metadata
│   │   │   ├── messages_*.jsonl # Messages by channel/thread
│   │   │   ├── users.json       # User directory snapshot
│   │   │   ├── reactions.json   # Message reactions
│   │   │   └── files.json       # File metadata and links
│   │   └── cursors.json         # Collection state tracking
│   │
│   ├── calendar/                # Google Calendar data
│   │   ├── YYYY-MM-DD/          # Daily event collections
│   │   │   ├── events_*.json    # Events by person or scope
│   │   │   ├── attendees.json   # Meeting participant data
│   │   │   └── changes.json     # Event modifications
│   │   └── calendars.json       # Calendar metadata
│   │
│   ├── drive/                   # Google Drive activity
│   │   ├── YYYY-MM-DD/          # Daily change batches
│   │   │   ├── changes_*.json   # File activity (metadata only)
│   │   │   ├── permissions.json # Sharing and access changes
│   │   │   └── comments.json    # Document comments
│   │   └── drive_state.json     # Drive collection state
│   │
│   └── employees/               # Team roster and mappings
│       ├── roster.json          # Master employee list
│       ├── mappings.json        # ID correlations across systems
│       └── org_chart.json       # Organizational structure
│
├── processed/                   # Derived intelligence
│   ├── goals.json               # Active objectives and status
│   ├── commitments.jsonl        # Extracted promises and deadlines
│   ├── profiles/                # Person profiles and patterns
│   │   ├── david.json           # Individual profile data
│   │   └── team_dynamics.json   # Team interaction patterns
│   ├── digests/                 # Generated briefings
│   │   ├── daily/               # Daily digest archive
│   │   └── weekly/              # Weekly summary archive
│   ├── meetings/                # Meeting coordination data
│   │   ├── proposals.json       # Scheduling proposals
│   │   ├── bookings.json        # Confirmed meetings
│   │   └── conflicts.json       # Scheduling conflicts
│   ├── insights/                # AI-generated insights
│   │   ├── trends.json          # Pattern analysis
│   │   ├── risks.json           # Risk identification
│   │   └── opportunities.json   # Opportunity detection
│   ├── feedback.jsonl           # User feedback with context
│   └── coverage_stats.json      # Data collection metrics
│
├── state/                       # System state management
│   ├── cursors.json             # Data collection positions
│   ├── last_run.json            # Execution timestamps
│   ├── ids.json                 # Entity ID mappings
│   ├── config.json              # Runtime configuration
│   └── health.json              # System health status
│
└── logs/                        # System audit trail
    ├── collector_runs.jsonl     # Collection execution logs
    ├── orchestrator.jsonl       # Processing workflow logs
    ├── slack_bot.jsonl          # Bot interaction logs
    ├── errors.jsonl             # Error tracking and resolution
    ├── performance.jsonl        # Performance metrics
    └── audit.jsonl              # Security and access logs
```

## Core Module Architecture

### Collectors Module (`src/collectors/`)

**Base Collector** (`base.py`):
```python
class BaseCollector:
    def __init__(self, config: CollectorConfig):
        self.config = config
        self.state = StateManager(config.state_file)
    
    def collect(self) -> CollectionResult:
        """Main collection method - override in subclasses"""
        raise NotImplementedError
    
    def get_cursor(self) -> Optional[str]:
        """Get last collection position"""
        return self.state.get_cursor()
    
    def update_cursor(self, cursor: str):
        """Update collection position"""
        self.state.update_cursor(cursor)
```

**Slack Collector** (`slack.py`):
```python
class SlackCollector(BaseCollector):
    def __init__(self, config: SlackConfig):
        super().__init__(config)
        self.client = WebClient(token=config.bot_token)
    
    def collect_channels(self) -> List[Channel]:
        """Collect all workspace channels"""
        
    def collect_messages(self, channel_id: str, since: datetime) -> List[Message]:
        """Collect messages since last cursor"""
        
    def collect_users(self) -> List[User]:
        """Collect user directory"""
        
    def handle_rate_limits(self, retry_after: int):
        """Exponential backoff for rate limits"""
```

**Calendar Collector** (`calendar.py`):
```python
class CalendarCollector(BaseCollector):
    def __init__(self, config: CalendarConfig):
        super().__init__(config)
        self.service = build('calendar', 'v3', credentials=config.credentials)
    
    def collect_events(self, calendar_id: str, since: datetime) -> List[Event]:
        """Collect calendar events with attendees"""
        
    def collect_calendars(self) -> List[Calendar]:
        """Collect available calendars"""
        
    def handle_timezone_conversion(self, event: Event) -> Event:
        """Normalize timezones to UTC"""
```

### Processors Module (`src/processors/`)

**Goals Processor** (`goals.py`):
```python
class GoalProcessor(BaseProcessor):
    def __init__(self, config: ProcessorConfig):
        super().__init__(config)
        self.state_machine = GoalStateMachine()
    
    def extract_goals_from_messages(self, messages: List[Message]) -> List[Goal]:
        """Extract goal mentions from conversations"""
        
    def update_goal_status(self, goal_id: str, status: GoalStatus) -> Goal:
        """Update goal with validation"""
        
    def detect_blocked_goals(self, goals: List[Goal]) -> List[Goal]:
        """Identify goals needing attention"""
```

**Commitments Processor** (`commitments.py`):
```python
class CommitmentProcessor(BaseProcessor):
    def __init__(self, config: ProcessorConfig):
        super().__init__(config)
        self.llm_client = AnthropicClient(config.api_key)
    
    def extract_commitments(self, messages: List[Message]) -> List[Commitment]:
        """LLM-powered commitment extraction"""
        
    def validate_commitment(self, commitment: Commitment) -> bool:
        """Validate extracted commitment"""
        
    def link_to_source(self, commitment: Commitment, message: Message):
        """Create audit trail to source"""
```

### Orchestrators Module (`src/orchestrators/`)

**Briefing Orchestrator** (`briefing.py`):
```python
class BriefingOrchestrator(BaseOrchestrator):
    def __init__(self, config: BriefingConfig):
        super().__init__(config)
        self.processors = self._load_processors()
    
    def generate_daily_digest(self, date: datetime) -> Digest:
        """Orchestrate daily briefing generation"""
        
    def generate_weekly_summary(self, week_start: datetime) -> Summary:
        """Orchestrate weekly summary"""
        
    def personalize_content(self, content: List[Item], user: User) -> List[Item]:
        """Customize content for user preferences"""
```

**Scheduler Orchestrator** (`scheduler.py`):
```python
class SchedulerOrchestrator(BaseOrchestrator):
    def __init__(self, config: SchedulerConfig):
        super().__init__(config)
        self.calendar_service = CalendarService(config)
    
    def find_meeting_slots(self, request: SchedulingRequest) -> List[TimeSlot]:
        """Find optimal meeting times"""
        
    def propose_slots(self, slots: List[TimeSlot], channel: str):
        """Send proposals to Slack"""
        
    def book_meeting(self, slot: TimeSlot, approved_by: str) -> Event:
        """Create calendar event after approval"""
```

### Interfaces Module (`src/interfaces/`)

**Slack Bot** (`slack_bot.py`):
```python
class SlackBot:
    def __init__(self, config: SlackBotConfig):
        self.app = App(token=config.bot_token)
        self.orchestrators = self._load_orchestrators()
        self._register_commands()
    
    def handle_goals_command(self, ack, respond, command):
        """Handle /cos goals command"""
        
    def handle_schedule_command(self, ack, respond, command):
        """Handle /cos schedule command"""
        
    def handle_update_command(self, ack, respond, command):
        """Handle /cos update command"""
        
    def send_daily_digest(self, user_id: str, digest: Digest):
        """Deliver daily briefing"""
```

**CLI Interface** (`cli.py`):
```python
@click.group()
def cli():
    """AI Chief of Staff CLI"""
    pass

@cli.command()
@click.option('--source', multiple=True, help='Data sources to collect')
def collect(source):
    """Run data collection"""
    
@cli.command()
@click.option('--goal-id', help='Goal ID to update')
@click.option('--status', help='New status')
def update_goal(goal_id, status):
    """Update goal status"""
    
@cli.command()
def generate_digest():
    """Generate and display current digest"""
```

## Tool Architecture

### Tool Interface Pattern

All tools follow a consistent interface for Claude Code orchestration:

```python
#!/usr/bin/env python3
"""
Tool: collect_data.py
Purpose: Run data collection across specified sources
"""

import json
import sys
import argparse
from typing import Dict, Any

def main() -> Dict[str, Any]:
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', choices=['slack', 'calendar', 'drive', 'all'])
    parser.add_argument('--since', help='Collect since timestamp (ISO format)')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    
    try:
        result = {
            "status": "success",
            "sources_processed": [],
            "items_collected": {},
            "errors": [],
            "warnings": [],
            "execution_time_seconds": 0,
            "next_cursor": None
        }
        
        # Execute collection logic
        if args.source in ['slack', 'all']:
            slack_result = collect_slack_data(args.since, args.dry_run)
            result["sources_processed"].append("slack")
            result["items_collected"]["slack"] = slack_result["count"]
            
        # Return structured JSON result
        return result
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "error_type": type(e).__name__
        }

if __name__ == "__main__":
    result = main()
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["status"] == "success" else 1)
```

### Available Tools

1. **collect_data.py** - Run data collection
2. **update_goals.py** - Modify goal states  
3. **find_slots.py** - Find meeting availability
4. **generate_digest.py** - Create briefing
5. **process_feedback.py** - Handle user feedback
6. **health_check.py** - System health validation

## Integration Architecture

### API Integration Patterns

**Slack Integration**:
```python
class SlackIntegration:
    def __init__(self, config: SlackConfig):
        self.client = WebClient(token=config.bot_token)
        self.app = App(token=config.bot_token, signing_secret=config.signing_secret)
        
    def setup_event_subscriptions(self):
        """Configure real-time event handling"""
        
    def handle_rate_limits(self, retry_after: int):
        """Exponential backoff with jitter"""
        
    def validate_signatures(self, request):
        """Verify request authenticity"""
```

**Google API Integration**:
```python
class GoogleIntegration:
    def __init__(self, config: GoogleConfig):
        self.credentials = self._load_credentials(config)
        self.calendar_service = build('calendar', 'v3', credentials=self.credentials)
        self.drive_service = build('drive', 'v3', credentials=self.credentials)
        
    def refresh_credentials(self):
        """Handle OAuth token refresh"""
        
    def batch_requests(self, requests: List[Request]) -> List[Response]:
        """Optimize API calls with batching"""
```

### State Management Architecture

**State Persistence**:
```python
class StateManager:
    def __init__(self, state_file: str):
        self.state_file = state_file
        self.state = self._load_state()
        
    def get_cursor(self, source: str) -> Optional[str]:
        """Get collection cursor for source"""
        
    def update_cursor(self, source: str, cursor: str):
        """Update cursor with atomic write"""
        
    def atomic_update(self, updates: Dict[str, Any]):
        """Thread-safe state updates"""
```

## Error Handling & Resilience

### Error Categories and Handling

**Collection Errors**:
- API rate limits: Exponential backoff with jitter
- Network timeouts: Retry with circuit breaker
- Authentication failures: Alert and pause collection
- Partial data: Mark incomplete and continue

**Processing Errors**:
- Data validation failures: Skip invalid records, log for review
- LLM API errors: Fallback to cached results
- State corruption: Rebuild from raw data
- Disk space issues: Cleanup old data, alert operator

**Interface Errors**:
- Slack delivery failures: Retry with different format
- Command parsing errors: Helpful error messages
- Permission errors: Clear instructions for resolution

### Monitoring and Alerting

**Health Checks**:
```python
class HealthChecker:
    def check_data_freshness(self) -> HealthStatus:
        """Verify recent data collection"""
        
    def check_api_connectivity(self) -> HealthStatus:
        """Test all external API connections"""
        
    def check_disk_space(self) -> HealthStatus:
        """Monitor storage capacity"""
        
    def check_processing_lag(self) -> HealthStatus:
        """Verify processing keeps up with collection"""
```

## Performance and Scalability

### Performance Targets
- **Collection Lag**: Slack ≤5min, Calendar ≤60min, Drive ≤120min
- **Processing Speed**: Digest generation ≤30s, scheduling proposals ≤10s
- **Reliability**: <1% error rate with automatic retry mechanisms
- **Storage Efficiency**: Compress old data, maintain 1-year retention

### Optimization Strategies

**Data Collection**:
- Incremental collection with cursors
- Parallel collection across sources
- Smart rate limit handling
- Compression for long-term storage

**Processing**:
- Lazy loading of large datasets
- Efficient change detection algorithms
- Caching of expensive computations
- Batch processing for bulk operations

**Storage**:
- JSONL for append-only operations
- Periodic compaction of old data
- Index files for fast queries
- Automatic cleanup of temporary files

## Security Architecture

### Data Protection
- **Local Storage**: All sensitive data processed locally by default
- **Encryption**: At-rest encryption for credentials and sensitive data
- **Access Logging**: Complete audit trail of all data access
- **Retention Controls**: Configurable data retention with automatic cleanup

### Authentication & Authorization
- **OAuth2**: Secure token management for Google APIs
- **Slack App**: Proper scope management and token rotation
- **Local Credentials**: Encrypted storage of API keys
- **Access Revocation**: Complete data purging on revocation

### Privacy Controls
- **Minimal Collection**: Only collect necessary data
- **Consent Management**: Clear user consent for data collection
- **Data Deletion**: Comprehensive purging on request
- **Audit Trails**: Complete logging of all data operations

This architecture supports the system's goals of providing persistent organizational memory while maintaining complete transparency, security, and user control over their data.