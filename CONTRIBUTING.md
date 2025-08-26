# Contributing to AI Chief of Staff

Thank you for your interest in contributing to the AI Chief of Staff project! This guide will help you get started with development, testing, and submitting changes.

## Development Philosophy

This is an experimental lab project focused on:
- **Clean, maintainable code** with comprehensive testing
- **Local-first privacy** with no cloud dependencies
- **Incremental development** with working software at each stage
- **Comprehensive documentation** for reproducibility

## Getting Started

### Prerequisites
- Python 3.9 or higher
- Git for version control
- Virtual environment management
- SQLite with FTS5 support

### Initial Setup
```bash
# Fork and clone the repository
git clone https://github.com/your-username/ai-cos-lab.git
cd ai-cos-lab

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install development dependencies
pip install -r requirements.txt
pip install -r requirements/dev.txt

# Set up pre-commit hooks (if available)
pre-commit install

# Copy environment template
cp .env.example .env
```

## Code Standards

### Python Style Guide
We follow Python best practices with some specific requirements:

#### Code Formatting
- **Line length**: 100 characters maximum
- **Indentation**: 4 spaces (no tabs)
- **Imports**: Organized by standard library, third-party, then local imports
- **Docstrings**: Google-style docstrings for all public functions and classes

#### Type Hints
All code should include type hints:
```python
from typing import Dict, List, Optional, Any

def process_data(data: List[Dict[str, Any]], limit: Optional[int] = None) -> Dict[str, Any]:
    \"\"\"Process data with optional limit.\"\"\"
    pass
```

#### Error Handling
- Use specific exception types rather than bare `except` clauses
- Always handle expected errors gracefully
- Log errors with appropriate context
- Never swallow exceptions without logging

```python
try:
    result = risky_operation()
except SpecificError as e:
    logger.error(f"Operation failed: {e}", extra={'context': context})
    raise ProcessingError(f"Failed to process data: {e}")
```

### File Organization
- **Modules**: One class per file when possible
- **Tests**: Mirror source structure in `tests/` directory
- **Documentation**: Keep inline documentation current
- **Configuration**: Use environment variables, not hardcoded values

## Development Workflow

### 1. Feature Development
```bash
# Create feature branch
git checkout -b feature/your-feature-name

# Make your changes
# ... development work ...

# Run tests
python -m pytest tests/ -v

# Run linting and formatting
make lint format  # (if Makefile available)

# Commit changes
git add .
git commit -m "feat: add new feature with comprehensive tests"
```

### 2. Testing Requirements

#### Unit Tests
Every module should have comprehensive unit tests:
```python
import pytest
from unittest.mock import Mock, patch

from src.collectors.slack_collector import SlackCollector

class TestSlackCollector:
    def test_initialization(self):
        collector = SlackCollector()
        assert collector.collector_type == "slack"
    
    @patch('src.collectors.slack_collector.requests.get')
    def test_api_request_with_timeout(self, mock_get):
        # Test that API calls include timeout
        pass
```

#### Integration Tests
Test component interactions:
```python
def test_collector_archive_integration():
    \"\"\"Test that collectors properly integrate with archive system.\"\"\"
    # Test collector -> archive writer -> search database flow
    pass
```

#### Test Coverage
- Aim for >80% test coverage
- All new code must include tests
- Tests should cover both success and failure scenarios

### 3. Running Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test category
python -m pytest tests/unit/ -v          # Unit tests only
python -m pytest tests/integration/ -v   # Integration tests only

# Run with coverage report
python -m pytest tests/ --cov=src --cov-report=html

# Run specific test file
python -m pytest tests/unit/test_slack_collector.py -v
```

### 4. Code Quality Checks

```bash
# Type checking (if mypy is available)
mypy src/

# Linting (if flake8 is available)
flake8 src/ tests/

# Import sorting (if isort is available)
isort src/ tests/

# Code formatting (if black is available)
black src/ tests/
```

## Architecture Guidelines

### Module Structure
```
src/
├── collectors/         # Data collection modules
├── core/              # Core infrastructure
├── search/            # Search and indexing
├── intelligence/      # AI/LLM processing (Phase 2+)
├── cli/              # Command-line interfaces
└── utilities/        # Shared utilities
```

### Design Principles
1. **Single Responsibility**: Each module has one clear purpose
2. **Dependency Injection**: Accept dependencies as constructor parameters
3. **Interface Consistency**: Similar operations have similar interfaces
4. **Error Transparency**: Errors should be informative and actionable
5. **Local-First**: No cloud dependencies in core functionality

### Data Flow Patterns
```
Collection → Validation → Archive → Indexing → Search
```

Each stage should be:
- **Testable** in isolation
- **Resilient** to upstream failures
- **Observable** through logging
- **Configurable** through environment variables

## Submitting Changes

### Pull Request Process
1. **Fork the repository** and create your feature branch
2. **Make your changes** following the coding standards
3. **Add comprehensive tests** for new functionality
4. **Update documentation** if needed
5. **Run the full test suite** and ensure it passes
6. **Submit a pull request** with clear description

### Pull Request Description Template
```markdown
## Description
Brief description of changes and motivation.

## Type of Change
- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)  
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## Testing
- [ ] All existing tests pass
- [ ] New tests added for new functionality
- [ ] Integration tests updated if needed
- [ ] Manual testing completed

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review of code completed
- [ ] Documentation updated if needed
- [ ] No sensitive information included
```

### Code Review Guidelines
Reviews will focus on:
- **Correctness**: Does the code do what it's supposed to do?
- **Safety**: Are there security or reliability concerns?
- **Maintainability**: Is the code readable and well-structured?
- **Testing**: Is the code adequately tested?
- **Documentation**: Are changes properly documented?

## Security Considerations

### Data Privacy
- **Never commit sensitive data** (API keys, personal information, etc.)
- **Use test mode** for development to avoid collecting real data
- **Follow principle of least privilege** for API access
- **Document security implications** of changes

### Credential Management
- Store credentials in environment variables only
- Use encrypted storage for persistent credentials
- Rotate credentials regularly
- Never log credential values

## Documentation

### Code Documentation
- **Module docstrings**: Explain purpose and usage
- **Function docstrings**: Include parameters, returns, and examples
- **Inline comments**: Explain complex logic or business rules
- **Type hints**: Provide clear type information

### User Documentation
- Update relevant documentation for user-facing changes
- Include examples for new features
- Update installation instructions if dependencies change
- Keep README.md and CAPABILITIES.md current

## Getting Help

### Development Questions
- Check existing documentation first
- Search issue tracker for similar questions
- Ask specific, detailed questions with context

### Reporting Issues
When reporting bugs, include:
- Steps to reproduce the issue
- Expected vs. actual behavior
- Error messages or logs
- Environment details (OS, Python version, etc.)
- Configuration details (without sensitive information)

### Communication
- Be respectful and constructive in all interactions
- Focus on technical merits of proposals
- Ask for clarification when needed
- Provide helpful feedback during code reviews

## Release Process

### Version Management
- Follow semantic versioning (MAJOR.MINOR.PATCH)
- Update version numbers in relevant files
- Tag releases in Git with version numbers
- Maintain CHANGELOG.md with release notes

### Testing Before Release
- All tests must pass
- Manual testing of critical workflows
- Documentation review and updates
- Security review of changes

Thank you for contributing to the AI Chief of Staff project! Your contributions help make this system more reliable, maintainable, and useful for organizational coordination.