# AI Chief of Staff - Contextual Coordination System

[![Python](https://img.shields.io/badge/Python-3.10+-blue?style=for-the-badge&logo=python)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Slack](https://img.shields.io/badge/Slack-API-purple?style=for-the-badge&logo=slack)](https://api.slack.com/)
[![License](https://img.shields.io/badge/License-Proprietary-red?style=for-the-badge)](LICENSE)

## 🎯 Overview

**We're not tracking tasks. We're building organizational memory.**

AI Chief of Staff is a deterministic personal assistant that maintains organizational context, tracks informal commitments, and coordinates action for remote leadership teams. The system collects Slack, Calendar, and Drive activity into transparent JSON, extracts goals and commitments, generates briefings, and assists with scheduling—delivering persistent memory and gentle accountability for executives.

### 🚀 The Problem We're Solving

- **Context Hunting**: Executives waste 30-60 minutes daily reconstructing context from scattered communications
- **Lost Commitments**: 80% of meeting commitments are forgotten due to lack of systematic tracking
- **Coordination Overhead**: Remote teams struggle with informal commitment tracking and follow-through
- **Information Silos**: Critical context scattered across Slack, Calendar, and Drive with no unified view
- **Memory Loss**: No persistent organizational memory of who promised what, when, and where

### Our Solution

- **Comprehensive Collection**: Continuous capture from Slack, Calendar, and Drive into structured JSON
- **Intelligent Processing**: AI-powered commitment extraction and goal tracking with human oversight
- **Proactive Briefings**: Daily/weekly summaries that surface changes, deadlines, and required actions
- **Seamless Coordination**: Lightweight scheduling via Slack with approval workflows
- **Complete Transparency**: Every insight links to source with full audit trail

## 🤖 AI-Powered Intelligence System

Advanced contextual understanding that transforms scattered communications into actionable intelligence:

### Intelligence Features
- **Commitment Extraction**: LLM-powered identification of promises and deadlines from conversations
- **Goal State Management**: Intelligent tracking of objectives with ownership and progress monitoring
- **Context Synthesis**: AI-generated briefings that highlight what matters most
- **Intent Recognition**: Natural language scheduling requests with smart attendee detection
- **Change Detection**: Automatic identification of important updates across all sources
- **Predictive Nudging**: Proactive reminders based on deadline proximity and importance
- **Sentiment Analysis**: Detection of blocked goals and escalation needs from conversation tone

## 🏗️ Four-Layer Architecture

AI Chief of Staff features a clean separation of concerns with deterministic processing and AI assistance:

### Layer 1: Collection (Deterministic)
- **Slack Collector**: Complete message history, channels, DMs, reactions, and user metadata
- **Calendar Collector**: Events, attendees, recurring patterns with timezone normalization
- **Drive Collector**: Document activity and metadata changes (content-agnostic in MVP)
- **Employee Roster**: Unified mapping of Slack IDs, emails, and calendar identities

### Layer 2: Processing (Deterministic)
- **Change Detection**: Identify meaningful updates across all data sources
- **Deduplication**: Eliminate redundant information and normalize formats
- **Relevance Scoring**: Prioritize information for briefing inclusion
- **State Management**: Maintain cursors, timestamps, and processing status

### Layer 3: Intelligence (LLM)
- **Text Understanding**: Extract commitments, goals, and scheduling intents
- **Summarization**: Generate concise briefings from raw activity
- **Context Generation**: Create actionable insights from scattered information
- **Anomaly Detection**: Identify unusual patterns requiring attention

### Layer 4: Interface
- **Slack Bot**: Interactive commands and rich message formatting
- **Daily Briefings**: Structured summaries delivered via Slack
- **CLI Tools**: Administrative commands and data management
- **Dashboard**: Simple HTML views for transparency and audit

## 📊 Comprehensive Data Management

Enterprise-grade data handling with complete auditability and privacy controls:

### Data Collection Philosophy
- **Immutable Logs**: Append-only storage ensuring complete audit trails
- **Local-First**: Secure local processing with optional cloud deployment
- **Structured Storage**: JSONL for raw data, JSON for processed state
- **Source Linking**: Every insight traces back to original source
- **Privacy by Design**: Minimal data collection with configurable retention

### Storage Architecture
```
data/ (gitignored)
├── raw/                      # Immutable source data
│   ├── slack/YYYY-MM-DD/     # Daily Slack exports
│   ├── calendar/YYYY-MM-DD/  # Calendar events and changes
│   ├── drive/YYYY-MM-DD/     # Document activity logs
│   └── employees/            # Team roster and mappings
├── processed/                # Derived intelligence
│   ├── goals.json           # Active objectives and status
│   ├── commitments.jsonl    # Extracted promises and deadlines
│   ├── digests/             # Generated briefings
│   └── coverage_stats.json  # Data collection metrics
├── state/                   # System state
│   ├── cursors.json         # Processing positions
│   ├── last_run.json        # Execution timestamps
│   └── ids.json             # Entity mappings
└── logs/                    # System audit trail
    ├── collector_runs.jsonl # Collection execution logs
    ├── orchestrator.jsonl   # Processing workflow logs
    └── errors.jsonl         # Error tracking and resolution
```

## 🎛️ Slack Bot Interface

Production-ready Slack integration with rich interactive capabilities:

### Core Commands
- **Goal Management**: `/cos goals` - View, create, and update objectives
- **Status Updates**: `/cos update status:goal123 completed` - Modify goal states
- **Smart Scheduling**: `/cos schedule @alice @bob 30min` - Coordinate meetings
- **Instant Briefings**: `/cos digest` - Generate current status summary
- **Feedback Loop**: `/cos feedback` - Submit improvements with context

### Interactive Features
- **Rich Message Blocks**: Buttons, selects, and forms for complex interactions
- **Approval Workflows**: Human confirmation for all external actions
- **Context Menus**: Quick actions from message threads and user profiles
- **Notification Management**: Configurable nudges and reminder preferences

## ⚙️ Technology Stack

### Core Architecture
- **Python 3.10+**: Modern async/await patterns with type hints
- **FastAPI**: High-performance API framework with automatic documentation
- **Local Storage**: JSON/JSONL files with git-ignored data directories
- **Claude Code**: LLM orchestration calling deterministic tools
- **Subprocess Pattern**: Isolated tool execution with structured outputs

### API Integrations
- **Slack API**: Comprehensive workspace access with rate limit handling
- **Google Calendar**: OAuth2 integration with read/write permissions
- **Google Drive**: Metadata collection with privacy-first approach
- **Anthropic Claude**: Advanced language understanding and generation
- **OpenAI GPT**: Supplementary text processing capabilities

### Development Tools
- **Pytest**: Comprehensive testing with fixtures and mocks
- **Black**: Code formatting with consistent style
- **MyPy**: Static type checking for reliability
- **Pre-commit**: Automated quality checks and linting

## 🚀 Key Features & Workflows

### Intelligent Morning Briefing
- **Automated Generation**: Daily 6 AM digest with overnight changes
- **Structured Sections**: Changes, goals, commitments, meetings, nudges
- **Interactive Elements**: Quick action buttons for common tasks
- **Source Attribution**: "Why?" links to verify every insight
- **Personalization**: Customizable content and delivery preferences

### Smart Meeting Coordination
- **Natural Language**: Parse scheduling requests from conversational text
- **Availability Analysis**: Calculate optimal slots across internal calendars
- **Conflict Resolution**: Handle timezone, working hours, and preference constraints
- **Approval Workflows**: Human confirmation before booking any meetings
- **Follow-up Tracking**: Monitor meeting outcomes and action items

### Goal & Commitment Tracking
- **Lifecycle Management**: Complete state machine from creation to completion
- **Automatic Extraction**: AI identification of commitments from conversations
- **Progress Monitoring**: Status inference from Slack activity and updates
- **Accountability Nudges**: Gentle reminders for approaching deadlines
- **Historical Analysis**: Trends and patterns in goal completion rates

### Comprehensive Audit System
- **Source Linking**: Every briefing item traces to original message/event
- **Processing Logs**: Complete record of data collection and transformation
- **Change History**: Full audit trail of goal and commitment modifications
- **Error Tracking**: Systematic logging and resolution of system issues
- **Privacy Controls**: Data deletion and access revocation workflows

## Getting Started

### Prerequisites

- Python 3.10 or higher
- Slack workspace admin access
- Google Cloud Console project with Calendar/Drive APIs
- 10GB free disk space for local data storage

### Installation

```bash
# Clone repository
git clone https://github.com/your-org/ai-cos-lab.git
cd ai-cos-lab

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Run setup script
./scripts/setup.sh
```

### API Configuration

Create Slack app and configure OAuth scopes:
```bash
# Required Slack scopes
channels:history, groups:history, im:history, mpim:history
users:read, channels:read, chat:write, commands
app_mentions:read, reactions:read
```

Enable Google APIs:
```bash
# Google Calendar API
calendar.readonly, calendar.events.write

# Google Drive API (MVP)
drive.metadata.readonly
```

### Environment Variables

```env
# Slack Configuration
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_APP_TOKEN=xapp-your-app-token
SLACK_SIGNING_SECRET=your-signing-secret

# Google API Configuration
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/callback

# AI Services
ANTHROPIC_API_KEY=your-anthropic-key
OPENAI_API_KEY=your-openai-key

# System Configuration
ENVIRONMENT=development
LOG_LEVEL=INFO
DATA_RETENTION_DAYS=365
BRIEFING_TIME=06:00
TIMEZONE=America/New_York
```

### First Run

```bash
# Initialize data directories
make setup

# Run collectors manually
python tools/collect_data.py --source=slack
python tools/collect_data.py --source=calendar

# Create test goals
python tools/update_goals.py --add "Complete MVP development" --owner=david --due="2025-08-21"

# Generate first briefing
python tools/generate_digest.py

# Start Slack bot
python src/interfaces/slack_bot.py
```

## Development Commands

```bash
make setup          # Initialize project and data directories
make collect         # Run all data collectors
make test           # Execute full test suite
make test-watch     # Run tests in watch mode
make lint           # Run code quality checks
make format         # Apply code formatting
make clean          # Clean temporary files and caches
make docs           # Generate documentation
```

## Testing

The project includes comprehensive testing across all system components:

### Test Categories
- **Unit Tests**: Individual module validation (`tests/test_collectors.py`)
- **Integration Tests**: API workflow testing (`tests/test_integrations.py`)
- **End-to-End Tests**: Complete user journey validation (`tests/test_e2e.py`)
- **Performance Tests**: Load and timing validation (`tests/test_performance.py`)

### Test Data
- **Fixtures**: Realistic mock data for repeatable testing
- **Factories**: Dynamic test data generation
- **Snapshots**: Golden file testing for output validation

Run tests with:
```bash
make test                    # Full test suite
make test-unit              # Unit tests only
make test-integration       # Integration tests only
make test-coverage          # Generate coverage report
pytest tests/test_goals.py  # Specific test file
pytest -k "test_slack"      # Pattern-based test selection
```

## Production Deployment

### Performance Specifications
- **Collection Lag**: Slack ≤5min, Calendar ≤60min, Drive ≤120min
- **Processing Speed**: Digest generation ≤30s, scheduling proposals ≤10s
- **Reliability**: <1% error rate with automatic retry mechanisms
- **Scalability**: Support 3-10 executives per deployment instance

### Security Features
- **Local-First Storage**: Sensitive data never leaves your infrastructure
- **Audit Trails**: Complete logging of all data access and modifications
- **Access Controls**: Fine-grained permissions with revocation workflows
- **Privacy Controls**: Configurable retention and selective data deletion
- **Secure Credentials**: Encrypted storage of API tokens and certificates

### Monitoring & Alerting
- **Health Checks**: Automated monitoring of all system components
- **Error Alerting**: Slack notifications for system issues
- **Performance Metrics**: Collection lag, processing time, success rates
- **Usage Analytics**: Command frequency, user engagement, goal completion

### Deployment Options
```bash
# Local Development
make dev

# Production with Docker
docker-compose up -d

# Systemd Service
sudo systemctl enable ai-cos
sudo systemctl start ai-cos

# Cron Job Configuration
# Add to crontab for scheduled collection
*/15 * * * * /path/to/ai-cos-lab/scripts/collect_slack.sh
0 */1 * * * /path/to/ai-cos-lab/scripts/collect_calendar.sh
0 6 * * * /path/to/ai-cos-lab/scripts/generate_digest.sh
```

## Architecture Documentation

- **System Design**: [ARCHITECTURE.md](./ARCHITECTURE.md) - Comprehensive system design and module structure
- **Development Guide**: [CLAUDE.md](./CLAUDE.md) - Complete system documentation for AI assistants
- **API Reference**: [docs/api.md](./docs/api.md) - Detailed API endpoint documentation
- **Deployment Guide**: [docs/deployment.md](./docs/deployment.md) - Production deployment instructions

## Success Metrics

### Primary KPIs
- **Daily Adoption**: 14 consecutive days of active goal system usage
- **Context Efficiency**: Reduce daily context hunting to ≤10 minutes
- **Commitment Capture**: Track ≥80% of meeting commitments automatically
- **Scheduling Success**: ≥3 meetings/week coordinated via bot
- **Trust Score**: 100% explainability with verifiable source links

### User Experience Metrics
- Daily active usage of briefings and commands
- Goal completion rates and update frequency
- Nudge response rates and preference adjustments
- User satisfaction via Slack feedback mechanism
- Feature adoption and retention rates

### Technical Performance
- Data collection completeness and lag times
- Processing accuracy and error rates
- API rate limit compliance and efficiency
- System uptime during business hours
- Storage efficiency and cleanup performance

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Run tests and linting (`make test lint`)
4. Commit changes (`git commit -m 'Add amazing feature'`)
5. Push to branch (`git push origin feature/amazing-feature`)
6. Open a Pull Request

### Development Guidelines
- Follow PEP 8 style guidelines with Black formatting
- Maintain 90%+ test coverage for new features
- Update documentation for API changes
- Use type hints for all function signatures
- Write descriptive commit messages

## Future Roadmap

Building towards comprehensive organizational intelligence:
- **Enhanced Context**: Email integration and document content analysis
- **Predictive Intelligence**: Proactive conflict identification and opportunity surfacing
- **Team Scaling**: Multi-executive deployment with shared organizational context
- **External Coordination**: Client scheduling and cross-organization workflows
- **Mobile Interface**: Native mobile app for on-the-go executive assistance

## Security & Privacy

### Data Protection
- **Local Storage**: All sensitive data processed and stored locally by default
- **Encryption**: At-rest encryption for stored credentials and sensitive information
- **Access Logging**: Complete audit trail of all data access and modifications
- **Retention Controls**: Configurable data retention with automatic cleanup
- **Deletion Workflows**: Comprehensive data purging and revocation capabilities

### Compliance Features
- **Privacy by Design**: Minimal data collection with explicit consent
- **Audit Readiness**: Complete paper trail for compliance reviews
- **Data Portability**: Export capabilities for data migration
- **Access Controls**: Role-based permissions with approval workflows

## License

© 2025 AI Chief of Staff. All rights reserved. Proprietary and confidential.

---

**Built for executives who need persistent memory and gentle accountability in remote work environments.**