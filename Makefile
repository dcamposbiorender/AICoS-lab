# AI Chief of Staff - Development Makefile
# Common development tasks and shortcuts

.PHONY: help install test lint format clean dev docs

# Default target
help:
	@echo "AI Chief of Staff - Development Commands"
	@echo ""
	@echo "Setup commands:"
	@echo "  install     Install all dependencies"
	@echo "  install-dev Install development dependencies"
	@echo "  setup       Complete development environment setup"
	@echo ""
	@echo "Development commands:"
	@echo "  test        Run all tests"
	@echo "  test-unit   Run unit tests only"  
	@echo "  test-integration Run integration tests only"
	@echo "  coverage    Generate test coverage report"
	@echo ""
	@echo "Code quality commands:"
	@echo "  lint        Run linting checks"
	@echo "  format      Format code with black (if available)"
	@echo "  typecheck   Run type checking with mypy (if available)"
	@echo "  quality     Run all quality checks"
	@echo ""
	@echo "Database commands:"
	@echo "  db-reset    Reset search database"
	@echo "  db-status   Check database status"
	@echo "  db-index    Index existing archives"
	@echo ""
	@echo "Data collection commands:"
	@echo "  collect-test    Run test data collection"
	@echo "  collect-slack   Collect Slack data"
	@echo "  collect-calendar Collect Calendar data"
	@echo "  collect-all     Collect all data sources"
	@echo ""
	@echo "Utility commands:"
	@echo "  clean       Clean generated files"
	@echo "  clean-all   Complete cleanup including cache"
	@echo "  docs        Generate documentation (if available)"
	@echo "  archive-stats Show archive statistics"

# Installation and setup
install:
	@echo "Installing dependencies..."
	pip install --upgrade pip
	pip install -r requirements.txt

install-dev:
	@echo "Installing development dependencies..."
	pip install --upgrade pip
	pip install -r requirements.txt
	@if [ -f requirements/dev.txt ]; then pip install -r requirements/dev.txt; fi

setup: install-dev
	@echo "Setting up development environment..."
	@if [ ! -f .env ]; then cp .env.example .env; echo "Created .env from template - please configure it"; fi
	@echo "Development environment setup complete!"
	@echo "Next steps:"
	@echo "1. Edit .env with your API credentials"
	@echo "2. Run 'make test' to verify installation"
	@echo "3. Run 'make collect-test' to test data collection"

# Testing
test:
	@echo "Running all tests..."
	python -m pytest tests/ -v

test-unit:
	@echo "Running unit tests..."
	python -m pytest tests/unit/ -v

test-integration:
	@echo "Running integration tests..."
	python -m pytest tests/integration/ -v

test-performance:
	@echo "Running performance tests..."
	@if [ -d tests/performance ]; then python -m pytest tests/performance/ -v; else echo "No performance tests found"; fi

coverage:
	@echo "Generating test coverage report..."
	python -m pytest tests/ --cov=src --cov-report=html --cov-report=term
	@echo "Coverage report generated in htmlcov/"

# Code quality
lint:
	@echo "Running linting checks..."
	@if command -v flake8 >/dev/null 2>&1; then \
		echo "Running flake8..."; \
		flake8 src/ tests/ tools/ --max-line-length=100; \
	else \
		echo "flake8 not available, skipping lint check"; \
	fi

format:
	@echo "Formatting code..."
	@if command -v black >/dev/null 2>&1; then \
		echo "Running black..."; \
		black src/ tests/ tools/ --line-length=100; \
	else \
		echo "black not available, skipping code formatting"; \
	fi

typecheck:
	@echo "Running type checks..."
	@if command -v mypy >/dev/null 2>&1; then \
		echo "Running mypy..."; \
		mypy src/; \
	else \
		echo "mypy not available, skipping type checking"; \
	fi

quality: lint format typecheck
	@echo "All quality checks completed"

# Database operations
db-reset:
	@echo "Resetting search database..."
	@if [ -f data/search.db ]; then rm -f data/search.db*; fi
	@echo "Search database reset complete"

db-status:
	@echo "Checking database status..."
	python tools/search_cli.py stats

db-index:
	@echo "Indexing existing archives..."
	python tools/search_cli.py index data/archive/

# Data collection
collect-test:
	@echo "Running test data collection..."
	export AICOS_TEST_MODE=true && python tools/collect_data.py --source=employee --output=console

collect-slack:
	@echo "Collecting Slack data..."
	python tools/collect_data.py --source=slack --output=json

collect-calendar:
	@echo "Collecting Calendar data..."
	python tools/collect_data.py --source=calendar --output=json

collect-all:
	@echo "Collecting all data sources..."
	python tools/collect_data.py --source=all --output=json

# Archive management
archive-stats:
	@echo "Archive statistics..."
	python tools/manage_archives.py --stats

archive-compress:
	@echo "Compressing old archives (30+ days)..."
	python tools/manage_archives.py --compress --age-days 30

archive-verify:
	@echo "Verifying archive integrity..."
	python tools/verify_archive.py

# Utility commands
clean:
	@echo "Cleaning generated files..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf dist
	rm -rf build

clean-all: clean
	@echo "Complete cleanup..."
	rm -f *.log
	rm -f test_*.json
	rm -f *_results.json
	rm -f *.db *.db-*
	@echo "Complete cleanup finished"

docs:
	@echo "Generating documentation..."
	@if command -v sphinx-build >/dev/null 2>&1; then \
		sphinx-build -b html docs/ docs/_build/html; \
		echo "Documentation generated in docs/_build/html"; \
	else \
		echo "Sphinx not available, skipping documentation generation"; \
		echo "Documentation available in README.md, CAPABILITIES.md, and docs/"; \
	fi

# Development server (if applicable)
dev:
	@echo "Starting development environment..."
	@echo "Available CLI tools:"
	@echo "  python tools/search_cli.py search 'query'"
	@echo "  python tools/collect_data.py --source=slack --output=console"
	@echo "  python tools/manage_archives.py --stats"

# Security checks (if tools available)
security:
	@echo "Running security checks..."
	@if command -v bandit >/dev/null 2>&1; then \
		echo "Running bandit..."; \
		bandit -r src/; \
	else \
		echo "bandit not available, skipping security scan"; \
	fi
	@if command -v safety >/dev/null 2>&1; then \
		echo "Running safety..."; \
		safety check; \
	else \
		echo "safety not available, skipping dependency security check"; \
	fi

# Performance profiling
profile:
	@echo "Running performance profiling..."
	@echo "Profiling data collection..."
	python -m cProfile -s tottime tools/collect_data.py --source=employee --output=console

# Full development workflow
dev-workflow: clean install-dev test lint
	@echo ""
	@echo "✅ Development workflow completed successfully!"
	@echo "Ready for development. Try: make collect-test"

# CI/CD simulation
ci: clean install test lint
	@echo ""
	@echo "✅ CI pipeline simulation completed!"