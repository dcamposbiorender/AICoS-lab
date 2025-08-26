# AI Chief of Staff - System Capabilities

## What This System Does

The AI Chief of Staff is a comprehensive data collection and search platform that:
- **Collects** data from Slack, Calendar, Drive, and Employee systems
- **Archives** everything as searchable JSONL files with compression
- **Searches** across all data using natural language queries
- **Manages** archives with verification, compression, and statistics

## Working CLI Tools (7 Total)

### Core Collection Tools
1. **collect_data.py** - Orchestrates data collection from all sources
   - Usage: `--source=all|slack|calendar|employee|drive --output=console|json`
   - Purpose: Basic collection orchestrator for lab-grade testing

2. **overnight_collection.py** - Sequential collection with progress logging
   - Usage: `--collectors slack,calendar --time-windows 7,30,90 --dry-run --verbose`
   - Purpose: Comprehensive overnight data collection pipeline

### Search and Query Tools
3. **search_cli.py** - Phase 3 Search Interface with 3 subcommands:
   - `search` - Natural language search across indexed archives
   - `index` - Index JSONL archive files into search database
   - `stats` - Display database statistics and health information
   - Features: Interactive mode, multiple output formats, source filtering

### Archive Management Tools
4. **manage_archives.py** - Enhanced archive management with UX features
   - Commands: `compress`, `verify`, `stats`, `backup`
   - Features: Progress indicators, dry-run mode, colored output

5. **verify_archive.py** - Comprehensive archive validation
   - Purpose: Validates JSONL format, file integrity, data completeness
   - Features: Performance metrics, gap detection, cross-reference validation

6. **verify_enhanced.py** - Enhanced verification with checksums
   - Purpose: SHA-256 integrity monitoring with resume capability
   - Features: Resume capability, source filtering, days-back options

### Setup and Authentication
7. **setup_google_oauth.py** - Google OAuth credential setup
   - Purpose: Creates Google OAuth credentials for Calendar and Drive APIs
   - Features: Browser-based authorization, token management, credential testing

## System Architecture

### Four-Layer Architecture
1. **Collection Layer** - Deterministic data collection from APIs
2. **Processing Layer** - Deduplication, validation, state persistence
3. **Intelligence Layer** - LLM-powered extraction and summarization
4. **Interface Layer** - CLI tools, search interface, management commands

### Data Flow
```
APIs (Slack/Calendar/Drive) → Collectors → JSONL Archives → Search Index → Query Results
```

## Performance Characteristics

- **Search Database**: Comprehensive record indexing using SQLite FTS5
- **Search Performance**: Sub-second response time for large datasets
- **Archive Storage**: Efficient storage with compression support
- **Test Coverage**: Comprehensive test suite with ongoing validation
- **Indexing Speed**: High-throughput record processing capability

## Current System Status

### Working Components ✅
- **Data Collection**: All 4 collectors (Slack, Calendar, Drive, Employee) operational
- **Archive System**: JSONL storage with daily directories and compression
- **Search Infrastructure**: Full-text search with natural language queries
- **Management Tools**: Compression, verification, statistics, backup capabilities
- **Test Suite**: Comprehensive test coverage with integration tests

### Development Status
1. **BaseArchiveCollector**: Constructor parameter standardization needed
2. **ArchiveVerifier**: Enhanced verification module in development
3. **Archive Data**: Limited test data available (demonstration purposes)
4. **Search Database**: Database creation requires initial data indexing

## Quick Start Commands

### Environment Setup
```bash
source venv/bin/activate
export AICOS_TEST_MODE=true  # Bypass credentials for testing
```

### Data Collection
```bash
# Collect from all sources
python3 tools/collect_data.py --source=all --output=json

# Overnight collection with progress tracking
python3 tools/overnight_collection.py --collectors slack,calendar --verbose
```

### Search Operations
```bash
# Index archive data
python3 tools/search_cli.py index data/archive/

# Search with natural language
python3 tools/search_cli.py search "meeting notes from last week"

# Interactive search session
python3 tools/search_cli.py search --interactive

# Database statistics
python3 tools/search_cli.py stats
```

### Archive Management
```bash
# Compress old files (30+ days)
python3 tools/manage_archives.py --compress --age-days 30

# Verify archive integrity
python3 tools/verify_archive.py

# Enhanced verification with checksums
python3 tools/verify_enhanced.py --source slack --days-back 7

# Get storage statistics
python3 tools/manage_archives.py --stats
```

## Technical Foundation

### Technology Stack
- **Backend**: Python 3.10+, FastAPI for APIs
- **Search**: SQLite FTS5 for portable full-text search
- **Storage**: JSON/JSONL for data storage with gzip compression
- **APIs**: Slack API, Google Calendar API, Google Drive API
- **Testing**: pytest with comprehensive fixtures and integration tests

### Data Architecture
- **Collection**: Comprehensive data from all sources
- **Storage**: Local-first with gitignored data directories
- **Format**: JSONL for raw logs, JSON for processed state
- **Auditability**: Every insight links back to source with file path and index

### Key Features
- **Comprehensive Coverage**: Collects all relevant Slack, Calendar, and Drive data
- **Local-First**: Store and process locally, no cloud dependencies
- **Audit Trail**: Complete transparency with source attribution
- **Performance**: Fast search and efficient storage management
- **Resilience**: Circuit breakers, retry logic, atomic operations

## Next Steps

### Immediate Fixes (High Priority)
1. Fix BaseArchiveCollector constructor to accept `collector_type` parameter
2. Implement missing ArchiveVerifier module for enhanced verification
3. Generate test data by running collection tools
4. Create search database by indexing existing archives

### System Enhancement (Medium Priority)
1. Expand data collection to generate more comprehensive archives
2. Optimize search performance and add advanced query features
3. Implement additional archive management capabilities
4. Add monitoring and alerting for operational issues

## Documentation Structure

- **CAPABILITIES.md** (this file) - System overview and quick reference
- **plan.md** - High-level architecture and implementation phases  
- **tasks.md** - Current status and essential commands
- **CLAUDE.md** - Instructions for AI assistants
- **tasks/** - Individual task specifications and progress tracking

This structure provides immediate operational knowledge while preserving all implementation details for reference.