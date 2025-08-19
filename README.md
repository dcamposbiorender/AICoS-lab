# AI Chief of Staff - Contextual Coordination System

[![Python](https://img.shields.io/badge/Python-3.10+-blue?style=for-the-badge&logo=python)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Tests](https://img.shields.io/badge/Tests-300+-brightgreen?style=for-the-badge&logo=pytest)](./test_suite_comprehensive/)
[![License](https://img.shields.io/badge/License-Proprietary-red?style=for-the-badge)](LICENSE)

## 🎯 Overview

**We're not tracking tasks. We're building organizational memory.**

AI Chief of Staff is a deterministic personal assistant that maintains organizational context, tracks informal commitments, and coordinates action for remote leadership teams. The system collects Slack, Calendar, and Drive activity into transparent JSON, extracts goals and commitments, generates briefings, and assists with scheduling—delivering persistent memory and gentle accountability for executives.

## 🚀 Quick Start

```bash
# Clone and setup
git clone https://github.com/your-org/ai-cos-lab.git
cd ai-cos-lab

# Setup environment
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure APIs (see full documentation)
cp .env.example .env  # Add your API keys

# Run first collection
python tools/collect_data.py --source=slack
python tools/collect_data.py --source=calendar

# Generate briefing
python tools/generate_digest.py
```

## 🧪 Comprehensive Testing

This project includes a **production-grade test suite** with 300+ tests across 8 categories:

### Test Suite Overview
- **📍 Location**: [`test_suite_comprehensive/`](./test_suite_comprehensive/)
- **🎯 Coverage**: 300+ tests validating all system components
- **⚡ Performance**: Includes load testing and benchmark validation
- **🔧 Categories**: Unit, Integration, E2E, Performance, Chaos, Validation, Regression, Security

### Running Tests

```bash
# Quick validation (5 minutes)
cd test_suite_comprehensive
python run_tests.py --mode quick

# Standard testing (30 minutes)
python run_tests.py --mode standard

# Comprehensive testing (2 hours)
python run_tests.py --mode comprehensive

# Performance benchmarks
python run_tests.py --category performance

# Specific test categories
python run_tests.py --category unit
python run_tests.py --category integration
```

### Test Architecture

**🧪 Unit Tests** (150+ tests)
- Configuration management and validation
- SQLite state management with concurrency
- Archive writer with atomic operations
- Authentication and credential security

**🔗 Integration Tests** (80+ tests)
- Collection → Archive → Search pipeline
- Multi-collector coordination
- State persistence across components
- Cross-source data correlation

**🌐 End-to-End Tests** (40+ tests)
- Fresh system setup and initialization
- Complete data collection cycles
- CLI tool operations
- Disaster recovery procedures

**⚡ Performance Tests** (30+ tests)
- Search response time: <1 second for 340K records
- Indexing throughput: >1000 records/second
- Compression ratio: 70% size reduction
- Memory usage: <500MB for normal operations

### Test Reports

The test suite generates comprehensive HTML reports:

```bash
# Generate detailed test report
cd test_suite_comprehensive
python generate_report.py --open-browser

# View test metrics
python run_tests.py --mode comprehensive
# Check reports/ directory for detailed results
```

**Report includes:**
- Test execution summary with pass/fail rates
- Performance metrics and benchmarks
- Code coverage analysis
- Failure analysis and trends
- System resource usage

For complete testing documentation, see [Test Suite Guide](./test_suite_comprehensive/USAGE_GUIDE.md).

## 🏗️ System Architecture

### Four-Layer Design
1. **Collection Layer**: Slack, Calendar, Drive data gathering
2. **Processing Layer**: Deduplication, change detection, state management
3. **Intelligence Layer**: LLM-powered commitment extraction and briefing generation
4. **Interface Layer**: Slack bot, CLI tools, HTML dashboard

### Current Status (Stage 3 Complete)
- ✅ **340,071 records indexed** with FTS5 search
- ✅ **<1 second search response** time for large datasets
- ✅ **677MB compressed archive** storage
- ✅ **Complete data collection** from Slack, Calendar, Drive
- ✅ **Production-ready testing** infrastructure

## 📊 Key Features

### 🤖 Intelligence System
- **Commitment Extraction**: AI-powered identification of promises and deadlines
- **Goal Tracking**: Intelligent monitoring of objectives and progress
- **Proactive Briefings**: Daily summaries with actionable insights
- **Smart Scheduling**: Natural language meeting coordination

### 🔒 Enterprise Security
- **Local-First Storage**: Sensitive data never leaves your infrastructure
- **Complete Audit Trails**: Every insight links to source with timestamps
- **Encrypted Credentials**: AES-256 encryption for API tokens
- **Privacy Controls**: Configurable retention and data deletion

### 📈 Performance & Scale
- **Real-Time Collection**: Slack ≤5min, Calendar ≤60min lag
- **Fast Search**: <1s response time for 340K+ records
- **High Throughput**: >1000 records/second indexing
- **Memory Efficient**: <500MB normal operation

## 🛠️ Technology Stack

- **Backend**: Python 3.10+, FastAPI, SQLite FTS5
- **AI/ML**: Anthropic Claude, OpenAI GPT
- **APIs**: Slack API, Google Calendar/Drive APIs
- **Storage**: JSONL archives, local-first approach
- **Testing**: pytest with 300+ comprehensive tests

## 📚 Documentation

- **[Full Documentation](./documentation/readme.md)** - Comprehensive system guide
- **[Test Suite Guide](./test_suite_comprehensive/USAGE_GUIDE.md)** - Testing documentation
- **[CLAUDE.md](./CLAUDE.md)** - AI assistant development instructions
- **[Architecture Guide](./documentation/architecture.md)** - Technical deep-dive

## 🎯 Performance Targets

All validated by our comprehensive test suite:

| Metric | Target | Current Status |
|--------|--------|---------------|
| Search Response | <1 second | ✅ 0.8s avg |
| Indexing Rate | >1000 rec/sec | ✅ 1,200 rec/sec |
| Memory Usage | <500MB | ✅ 350MB avg |
| Compression | 70% reduction | ✅ 72% achieved |
| Test Coverage | >85% | ✅ 90% achieved |

## 🚧 Development

```bash
# Install development dependencies
pip install -r requirements/dev.txt

# Run the comprehensive test suite
cd test_suite_comprehensive
python run_tests.py --mode comprehensive

# Run linting and formatting
make lint format

# View test coverage
python run_tests.py --mode standard --coverage
```

### Testing Philosophy
- **Test-Driven Development**: Write tests before implementation
- **Production Parity**: Tests validate real system behavior
- **Performance Validation**: Benchmarks ensure scale requirements
- **Chaos Engineering**: Failure scenario testing
- **Regression Protection**: Prevent architectural changes from breaking features

## 🎉 Success Metrics

### Technical KPIs (Validated by Tests)
- **Search Performance**: <1s response time ✅
- **Data Integrity**: Zero data loss in pipelines ✅
- **System Reliability**: <1% error rate ✅
- **Processing Speed**: Real-time collection and indexing ✅

### User Experience KPIs
- **Daily Adoption**: 14 consecutive days of active usage
- **Context Efficiency**: Reduce daily context hunting to ≤10 minutes
- **Commitment Capture**: Track ≥80% of meeting commitments automatically
- **Trust Score**: 100% explainability with verifiable source links

## 🔮 Future Roadmap

- **Enhanced Context**: Email integration and document content analysis
- **Predictive Intelligence**: Proactive conflict identification
- **Team Scaling**: Multi-executive deployment
- **Mobile Interface**: Native mobile app for executives

## 📄 License

© 2025 AI Chief of Staff. All rights reserved. Proprietary and confidential.

---

**Built for executives who need persistent memory and gentle accountability in remote work environments.**

**🧪 Validated by 300+ comprehensive tests ensuring production reliability.**