# Development Guide - AI Chief of Staff

This guide covers the development environment setup, common development tasks, debugging procedures, and architectural patterns for contributors to the AI Chief of Staff project.

## Development Environment Setup

### Prerequisites
- **Python 3.9+** with pip and venv
- **Git** for version control  
- **SQLite 3.35+** with FTS5 support
- **Text Editor/IDE** with Python support (VSCode, PyCharm, etc.)

### Quick Setup
```bash
# Clone and enter project
git clone https://github.com/your-org/ai-cos-lab.git
cd ai-cos-lab

# Setup Python environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements/dev.txt  # If exists

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Verify setup
python -c "import src.core.config; print('✅ Configuration loaded')"
```

### IDE Configuration

#### VSCode Settings
Create `.vscode/settings.json`:
```json
{
    "python.defaultInterpreterPath": "./venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "python.formatting.provider": "black",
    "python.formatting.blackArgs": ["--line-length", "100"],
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": ["tests/"]
}
```

#### PyCharm Configuration
- Set Python interpreter to `./venv/bin/python`
- Enable pytest as test runner
- Configure Black as code formatter
- Enable type checking with mypy

## Development Workflow

### Daily Development Tasks
```bash
# Activate environment (start of each session)
source venv/bin/activate

# Pull latest changes
git pull origin main

# Run tests before starting work
make test  # or python -m pytest tests/ -v

# Start development server (if applicable)
make dev   # or python tools/dev_server.py

# Run specific collector for testing
export AICOS_TEST_MODE=true
python tools/collect_data.py --source=slack --output=console
```

### Common Development Commands
```bash
# Code quality checks
make lint          # Run linting
make format        # Format code
make typecheck     # Type checking
make test          # Run test suite
make coverage      # Generate coverage report

# Database operations
make db-reset      # Reset search database
make db-migrate    # Run database migrations
make db-status     # Check database status

# Documentation
make docs          # Generate documentation
make docs-serve    # Serve docs locally

# Cleanup
make clean         # Remove generated files
make clean-all     # Full cleanup including venv
```

## Architecture Overview

### Core Components

#### 1. Data Collection Layer (`src/collectors/`)
```python
# BaseArchiveCollector provides common functionality
class MyCollector(BaseArchiveCollector):
    def __init__(self):
        super().__init__("my_collector")
    
    def collect(self) -> List[Dict]:
        # Implement collection logic
        pass
```

#### 2. Storage Layer (`src/core/`)
```python
# ArchiveWriter handles JSONL storage
writer = ArchiveWriter("my_source", date.today())
writer.write(data)

# StateManager handles persistent state
state_manager = StateManager()
state_manager.set_state("key", value)
```

#### 3. Search Layer (`src/search/`)
```python
# SearchDatabase provides full-text search
db = SearchDatabase()
db.index_archive("path/to/archive.jsonl")
results = db.search("query text")
```

### Data Flow Architecture
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Collectors    │    │  Archive Writer │    │ Search Database │
│                 │───▶│                 │───▶│                 │
│ - Slack         │    │ - JSONL files   │    │ - SQLite FTS5   │
│ - Calendar      │    │ - Compression   │    │ - Indexing      │
│ - Drive         │    │ - Validation    │    │ - Query engine  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  State Manager  │    │  Configuration  │    │   CLI Tools     │
│                 │    │                 │    │                 │
│ - SQLite DB     │    │ - Environment   │    │ - Search CLI    │
│ - Cursors       │    │ - Validation    │    │ - Management    │
│ - History       │    │ - Defaults      │    │ - Verification  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Testing Strategy

### Test Categories
1. **Unit Tests** (`tests/unit/`) - Individual component testing
2. **Integration Tests** (`tests/integration/`) - Component interaction testing  
3. **Performance Tests** (`tests/performance/`) - Speed and resource testing
4. **Security Tests** (`tests/security/`) - Security vulnerability testing

### Writing Tests
```python
# Unit test example
import pytest
from unittest.mock import Mock, patch
from src.collectors.slack_collector import SlackCollector

class TestSlackCollector:
    def test_initialization(self):
        """Test collector initializes correctly."""
        collector = SlackCollector()
        assert collector.collector_type == "slack"
        assert collector.rate_limiter is not None
    
    @patch('src.collectors.slack_collector.requests.get')
    def test_api_request_timeout(self, mock_get):
        """Test API requests include timeout."""
        collector = SlackCollector()
        collector._make_api_request("http://test.com")
        mock_get.assert_called_with(
            "http://test.com", 
            headers=None, 
            params=None, 
            timeout=30
        )

# Integration test example  
def test_full_collection_pipeline():
    """Test complete data flow from collection to search."""
    # Setup test environment
    with temp_directory() as tmp_dir:
        # Test collector → archive → search flow
        collector = SlackCollector()
        data = collector.collect()
        
        writer = ArchiveWriter("slack", date.today())
        writer.write(data)
        
        db = SearchDatabase()
        db.index_archive(writer.file_path)
        
        results = db.search("test query")
        assert len(results) > 0
```

### Test Configuration
```python
# tests/conftest.py
import pytest
import tempfile
from pathlib import Path

@pytest.fixture
def temp_directory():
    """Provide temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)

@pytest.fixture
def mock_config():
    """Provide test configuration."""
    return {
        'test_mode': True,
        'data_retention_days': 7,
        'log_level': 'DEBUG'
    }
```

## Debugging Guide

### Common Issues and Solutions

#### 1. Import Errors
```python
# Problem: ModuleNotFoundError
# Solution: Check PYTHONPATH and virtual environment
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
source venv/bin/activate
```

#### 2. Database Issues
```bash
# Check SQLite FTS5 support
python -c "import sqlite3; conn = sqlite3.connect(':memory:'); conn.execute('CREATE VIRTUAL TABLE test USING fts5(content)'); print('✅ FTS5 supported')"

# Reset database if corrupted
rm data/search.db*
python tools/search_cli.py index data/archive/
```

#### 3. Credential Issues
```bash
# Verify credentials are properly set
python -c "from src.core.auth_manager import credential_vault; vault = credential_vault(); print('✅ Credentials loaded' if vault else '❌ No credentials')"

# Reset OAuth credentials
rm -rf data/auth/
python tools/setup_google_oauth.py
```

#### 4. Performance Issues
```python
# Enable debug logging
export LOG_LEVEL=DEBUG
python tools/collect_data.py --source=slack --output=console

# Profile memory usage
pip install memory-profiler
python -m memory_profiler tools/collect_data.py
```

### Debugging Tools
```bash
# Interactive debugging with pdb
python -m pdb tools/collect_data.py --source=slack

# Memory profiling
pip install memory-profiler
@profile
def my_function():
    pass

# SQL query debugging
export SQLITE_DEBUG=1
python tools/search_cli.py search "test query"
```

## Performance Optimization

### Database Optimization
```sql
-- Add indexes for common queries
CREATE INDEX idx_archive_date ON archives(collection_date);
CREATE INDEX idx_search_timestamp ON search_results(timestamp);

-- Optimize FTS5 performance
INSERT INTO fts_table(fts_table, rank) VALUES('rank', 'bm25(10.0, 5.0)');
```

### Memory Management
```python
# Use generators for large datasets
def process_large_dataset(data_iterator):
    for item in data_iterator:
        yield process_item(item)

# Implement pagination
def collect_paginated(page_size=1000):
    cursor = None
    while True:
        page = fetch_page(cursor, page_size)
        if not page:
            break
        yield from page
        cursor = page[-1]['cursor']
```

### API Rate Limiting
```python
class RateLimiter:
    def __init__(self, calls_per_minute=60):
        self.calls_per_minute = calls_per_minute
        self.last_call_time = 0
    
    def wait_if_needed(self):
        now = time.time()
        time_since_last = now - self.last_call_time
        min_interval = 60.0 / self.calls_per_minute
        
        if time_since_last < min_interval:
            time.sleep(min_interval - time_since_last)
        
        self.last_call_time = time.time()
```

## Deployment Preparation

### Pre-deployment Checklist
- [ ] All tests pass
- [ ] Code coverage >80%
- [ ] No hardcoded credentials
- [ ] Environment variables documented
- [ ] Error handling comprehensive
- [ ] Logging appropriately configured
- [ ] Performance benchmarks meet requirements

### Build Process
```bash
# Create distribution package
python setup.py sdist bdist_wheel

# Verify package integrity
pip install dist/ai-cos-lab-*.whl
python -c "import src.core.config; print('✅ Package installed correctly')"

# Generate deployment documentation
make docs-deploy
```

## Contributing Guidelines

### Code Review Process
1. **Self-review** code before submitting
2. **Run full test suite** locally
3. **Update documentation** for any API changes
4. **Add tests** for new functionality
5. **Follow coding standards** consistently

### Git Workflow
```bash
# Feature development
git checkout -b feature/my-feature
# ... make changes ...
git add .
git commit -m "feat: add new feature with comprehensive tests"
git push origin feature/my-feature

# Create pull request with clear description
# Address code review feedback
# Merge after approval
```

This development guide provides the foundation for effective contribution to the AI Chief of Staff project. Follow these patterns and practices to maintain code quality and system reliability.