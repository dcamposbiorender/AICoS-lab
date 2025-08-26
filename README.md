# AI Chief of Staff - Contextual Coordination System

[![Python](https://img.shields.io/badge/Python-3.10+-blue?style=for-the-badge&logo=python)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Tests](https://img.shields.io/badge/Tests-Comprehensive-brightgreen?style=for-the-badge&logo=pytest)](./tests/)
[![License](https://img.shields.io/badge/License-Proprietary-red?style=for-the-badge)](LICENSE)

## Overview

AI Chief of Staff is a deterministic personal assistant that maintains organizational context, tracks informal commitments, and coordinates action for remote leadership teams. The system collects Slack, Calendar, and Drive activity into transparent JSON, extracts goals and commitments, generates briefings, and assists with scheduling—delivering persistent memory and gentle accountability for executives.

## Quick Start

```bash
# Clone and setup
git clone https://github.com/your-org/ai-cos-lab.git
cd ai-cos-lab

# Setup environment
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure APIs using encrypted key manager (see INSTALLATION.md for details)
python tools/setup_google_oauth.py  # Set up Google authentication
# Note: API tokens are stored encrypted, not in .env files

# Run first collection
python tools/collect_data.py --source=slack
python tools/collect_data.py --source=calendar

# Generate briefing
python tools/generate_digest.py
```

## Testing

This project includes a comprehensive test suite across multiple categories:

### Test Suite Overview
- **📍 Location**: [`tests/`](./tests/)
- **Coverage**: Comprehensive tests validating all system components
- **⚡ Performance**: Includes load testing and benchmark validation
- **🔧 Categories**: Unit, Integration, Performance, Security

### Running Tests

```bash
# Run all tests
make test

# Run specific test categories
make test-unit
make test-integration

# Run with coverage
make coverage

# Individual test commands
python -m pytest tests/unit/ -v
python -m pytest tests/integration/ -v
```

### Test Architecture

**Unit Tests**
- Configuration management and validation
- SQLite state management with concurrency
- Archive writer with atomic operations
- Authentication and credential security

**Integration Tests**
- Collection → Archive → Search pipeline
- Multi-collector coordination
- State persistence across components
- Cross-source data correlation

**End-to-End Tests**
- Fresh system setup and initialization
- Complete data collection cycles
- CLI tool operations
- Disaster recovery procedures

**Performance Tests**
- Search response time validation
- Indexing throughput measurement
- Compression ratio testing
- Memory usage monitoring

### Test Reports

Generate comprehensive test reports and coverage:

```bash
# Generate coverage report
make coverage

# View HTML coverage report
open htmlcov/index.html  # macOS
# or browse to htmlcov/index.html in your browser
```

## 🏗️ System Architecture

### Four-Layer Design
1. **Collection Layer**: Slack, Calendar, Drive data gathering
2. **Processing Layer**: Deduplication, change detection, state management
3. **Intelligence Layer**: LLM-powered commitment extraction and briefing generation
4. **Interface Layer**: Slack bot, CLI tools, HTML dashboard

### Current Implementation Status
- ✅ Search database with FTS5 full-text search
- ✅ Fast search response times for large datasets
- ✅ Compressed archive storage system
- ✅ Data collection from Slack, Calendar, Drive (metadata)
- ✅ Comprehensive testing infrastructure

## Key Features

### Intelligence System (Planned)
- **Commitment Extraction**: AI-powered identification of promises and deadlines
- **Goal Tracking**: Intelligent monitoring of objectives and progress
- **Proactive Briefings**: Daily summaries with actionable insights
- **Smart Scheduling**: Natural language meeting coordination

### Security Features
- **Local-First Storage**: Sensitive data never leaves your infrastructure
- **Complete Audit Trails**: Every insight links to source with timestamps
- **Encrypted Credentials**: AES-256 encryption for API tokens in secure database
- **Privacy Controls**: Configurable retention and data deletion

### 🔐 Authentication System

**All API tokens are stored encrypted in `src/core/encrypted_keys.db` with AES-256 encryption.**

#### Slack Token Storage
- **Production tokens**: `slack_tokens_production` key (real Slack tokens for production use)
- **Test tokens**: `slack_tokens_test` key (test tokens for unit tests only)
- **⚠️ CRITICAL**: NEVER overwrite `slack_tokens_production` key
- **Environment control**: 
  - `AICOS_TEST_MODE=true` → uses test tokens
  - `AICOS_TEST_MODE=false` or unset → uses production tokens

#### Token Verification
```bash
# Verify which tokens are available
python -c "from src.core.auth_manager import credential_vault; credential_vault.validate_authentication()"

# List all encrypted keys
python -c "from src.core.key_manager import key_manager; import json; print(json.dumps(key_manager.list_keys(), indent=2))"
```

#### Additional Features
- **Master Key Security**: Encryption keys stored separately from data with secure permissions
- **Automatic Token Refresh**: Google OAuth tokens refreshed automatically when expired
- **Setup Tools**: Use `python tools/setup_google_oauth.py` instead of manual token configuration
- **Safeguards**: Built-in protection prevents test tokens from overwriting production tokens

### Performance & Scale
- **Incremental Collection**: Configurable collection intervals
- **Fast Search**: Sub-second response times for large datasets
- **Efficient Indexing**: High-throughput record processing
- **Memory Efficient**: Optimized for reasonable memory usage

## 🛠️ Technology Stack

- **Backend**: Python 3.10+, FastAPI, SQLite FTS5
- **AI/ML**: Anthropic Claude, OpenAI GPT
- **APIs**: Slack API, Google Calendar/Drive APIs
- **Storage**: JSONL archives, local-first approach
- **Testing**: pytest with comprehensive test coverage

## Documentation

- **[Installation Guide](./INSTALLATION.md)** - Complete setup instructions
- **[System Capabilities](./CAPABILITIES.md)** - Features and CLI tools overview
- **[Contributing Guide](./CONTRIBUTING.md)** - Development and contribution guidelines
- **[Security Guide](./docs/SECURITY.md)** - Security best practices and considerations
- **[Development Guide](./docs/DEVELOPMENT.md)** - Development environment and workflow
- **[Architecture Guide](./documentation/architecture.md)** - Technical deep-dive

## Performance Characteristics

System performance is validated through comprehensive testing:

| Metric | Target | Status |
|--------|--------|---------|
| Search Response | Sub-second | Validated |
| Indexing Rate | High throughput | Validated |
| Memory Usage | Reasonable | Monitored |
| Compression | Effective | Implemented |
| Test Coverage | Comprehensive | Ongoing |

## Development

```bash
# Install development dependencies
make install-dev

# Run the test suite
make test

# Run code quality checks
make lint format typecheck

# View test coverage
make coverage

# See all available commands
make help
```

### Testing Philosophy
- **Test-Driven Development**: Write tests before implementation
- **Production Parity**: Tests validate real system behavior
- **Performance Validation**: Benchmarks ensure scale requirements
- **Chaos Engineering**: Failure scenario testing
- **Regression Protection**: Prevent architectural changes from breaking features

## Project Goals

### Technical Objectives
- **Search Performance**: Fast response times for large datasets
- **Data Integrity**: Reliable data collection and storage
- **System Reliability**: Robust error handling and recovery
- **Processing Efficiency**: Scalable data processing architecture

### User Experience Objectives
- **Ease of Use**: Simple setup and daily operation
- **Context Preservation**: Comprehensive data collection and search
- **Transparency**: Clear audit trails and source attribution
- **Privacy**: Local-first data storage and processing

## Future Development

- **Enhanced Context**: Email integration and document content analysis
- **Predictive Intelligence**: Proactive conflict identification
- **Team Scaling**: Multi-executive deployment
- **Mobile Interface**: Native mobile app for executives

## License

© 2025 AI Chief of Staff. All rights reserved. Proprietary and confidential.

---

**Built for executives who need persistent memory and gentle accountability in remote work environments.**

**Experimental lab project with comprehensive testing for reliability validation.**