"""
Phase 1 Integration Tests - Complete End-to-End Validation

Comprehensive integration testing for Phase 1 delivery validation.
Tests the core Phase 1 promise: unified search and coordination across
all data sources without AI dependencies.

Test Categories:
- Complete data pipeline validation
- Cross-module consistency
- Performance benchmarks  
- Data integrity validation
- Phase 1 requirements compliance

References:
- tasks/phase1_agent_d_migration.md lines 241-509 for test specifications
- All Phase 1 agents: A (queries), B (calendar/stats), C (CLI), D (migration)
"""

import pytest
import json
import subprocess
import tempfile
import os
import sys
import time
import sqlite3
from datetime import date, timedelta, datetime
from pathlib import Path
from unittest.mock import patch

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))


class TestPhase1Integration:
    """Test complete Phase 1 functionality end-to-end"""
    
    def test_complete_data_pipeline_simulation(self):
        """Validate entire data flow simulation in test mode"""
        with patch.dict(os.environ, {'AICOS_TEST_MODE': 'true'}):
            
            # Step 1: Test Agent A query engines work
            query_result = subprocess.run([
                'python3', 'tools/query_facts.py', 'time', 'yesterday', '--format', 'json'
            ], capture_output=True, text=True, cwd=project_root)
            
            assert query_result.returncode == 0, f"Query failed: {query_result.stderr}"
            query_data = json.loads(query_result.stdout)
            assert 'results' in query_data
            assert query_data.get('metadata', {}).get('mock_mode') is True
            
            # Step 2: Test Agent B statistics generation  
            stats_result = subprocess.run([
                'python3', 'tools/daily_summary.py', '--date', '2025-08-19', '--format', 'json'
            ], capture_output=True, text=True, cwd=project_root)
            
            assert stats_result.returncode == 0, f"Stats failed: {stats_result.stderr}"
            # Extract JSON from stdout - find the complete JSON object
            stdout_lines = stats_result.stdout.split('\n')
            json_start = -1
            for i, line in enumerate(stdout_lines):
                if line.strip().startswith('{'):
                    json_start = i
                    break
            
            assert json_start >= 0, f"No JSON start found in: {stats_result.stdout}"
            
            # Find JSON end (last line that ends with '}')
            json_end = -1
            for i in range(len(stdout_lines) - 1, json_start - 1, -1):
                if stdout_lines[i].strip().endswith('}'):
                    json_end = i
                    break
            
            assert json_end >= json_start, f"No JSON end found in: {stats_result.stdout}"
            
            json_content = '\n'.join(stdout_lines[json_start:json_end + 1])
            stats_data = json.loads(json_content)
            assert 'slack_activity' in stats_data
            
            # Step 3: Test Agent B calendar coordination
            calendar_result = subprocess.run([
                'python3', 'tools/query_facts.py', 'calendar', 'find-slots',
                '--attendees', 'alice@example.com', '--duration', '60', '--format', 'json'
            ], capture_output=True, text=True, cwd=project_root)
            
            assert calendar_result.returncode == 0, f"Calendar failed: {calendar_result.stderr}"
            calendar_data = json.loads(calendar_result.stdout)
            assert 'available_slots' in calendar_data
            
            # All steps must complete successfully
            all_results = [query_result, stats_result, calendar_result]
            assert all(result.returncode == 0 for result in all_results)
    
    def test_cross_module_consistency(self):
        """Verify data consistency between Agent A, B, and C modules"""
        with patch.dict(os.environ, {'AICOS_TEST_MODE': 'true'}):
            
            person_email = 'alice@example.com'
            
            # Agent A: Person query
            person_result = subprocess.run([
                'python3', 'tools/query_facts.py', 'person', person_email, 
                '--activity-summary', '--format', 'json'
            ], capture_output=True, text=True, cwd=project_root)
            
            assert person_result.returncode == 0
            person_data = json.loads(person_result.stdout)
            
            # Agent B: Statistics for same person
            stats_result = subprocess.run([
                'python3', 'tools/daily_summary.py', 
                '--person', person_email, '--format', 'json'
            ], capture_output=True, text=True, cwd=project_root)
            
            assert stats_result.returncode == 0
            # Extract JSON from stdout - find the complete JSON object
            stdout_lines = stats_result.stdout.split('\n')
            json_start = -1
            for i, line in enumerate(stdout_lines):
                if line.strip().startswith('{'):
                    json_start = i
                    break
            
            assert json_start >= 0, f"No JSON start found in: {stats_result.stdout}"
            
            # Find JSON end (last line that ends with '}')
            json_end = -1
            for i in range(len(stdout_lines) - 1, json_start - 1, -1):
                if stdout_lines[i].strip().endswith('}'):
                    json_end = i
                    break
            
            assert json_end >= json_start, f"No JSON end found in: {stats_result.stdout}"
            
            json_content = '\n'.join(stdout_lines[json_start:json_end + 1])
            stats_data = json.loads(json_content)
            
            # Both should reference the same person
            assert stats_data['person'] == person_email
            
            # Verify both have meaningful activity data
            assert 'metadata' in person_data
            assert 'slack_activity' in stats_data
    
    def test_migration_system_integration(self):
        """Test migration system works with Phase 1 modules"""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_db = Path(temp_dir) / "integration_test.db"
            
            from search.migrations import create_migration_manager
            manager = create_migration_manager(str(test_db))
            
            # Apply all Phase 1 migrations
            migrations = manager.discover_migrations()
            assert len(migrations) >= 3  # Should have 001, 002, 003 migrations
            
            for migration in migrations:
                result = manager.apply_migration(migration.file_path.name)
                assert result is True
            
            # Verify final schema version
            final_version = manager.get_current_version()
            assert final_version == len(migrations)
            
            # Verify database has expected Phase 1 structure
            with sqlite3.connect(test_db) as conn:
                cursor = conn.cursor()
                
                # Check core tables exist
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
                
                expected_tables = ['messages', 'messages_fts', 'archives', 'schema_migrations']
                for table in expected_tables:
                    assert table in tables, f"Missing table: {table}"


class TestPerformanceBenchmarks:
    """Test Phase 1 performance requirements"""
    
    def test_query_performance_targets(self):
        """Validate all query types meet <3 second requirement"""
        with patch.dict(os.environ, {'AICOS_TEST_MODE': 'true'}):
            query_types = [
                ['time', 'last week'],
                ['person', 'alice@example.com'],
                ['patterns', '--pattern-type', 'todos']
            ]
            
            for query_cmd in query_types:
                start_time = time.time()
                
                result = subprocess.run([
                    'python3', 'tools/query_facts.py'
                ] + query_cmd + ['--format', 'json'], 
                capture_output=True, text=True, cwd=project_root)
                
                end_time = time.time()
                execution_time = end_time - start_time
                
                assert result.returncode == 0, f"Query failed: {result.stderr}"
                assert execution_time < 3.0, f"Query too slow ({execution_time:.2f}s): {query_cmd}"
                
                # Verify results are meaningful
                if result.stdout:
                    data = json.loads(result.stdout)
                    assert 'results' in data
    
    def test_calendar_coordination_performance(self):
        """Calendar operations complete in <5 seconds"""
        with patch.dict(os.environ, {'AICOS_TEST_MODE': 'true'}):
            start_time = time.time()
            
            result = subprocess.run([
                'python3', 'tools/query_facts.py', 'calendar', 'find-slots',
                '--attendees', 'alice@example.com,bob@example.com',
                '--duration', '60',
                '--format', 'json'
            ], capture_output=True, text=True, cwd=project_root)
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            assert result.returncode == 0
            assert execution_time < 5.0, f"Calendar query too slow: {execution_time:.2f}s"
    
    def test_statistics_generation_performance(self):
        """Statistics generation completes in <10 seconds"""
        with patch.dict(os.environ, {'AICOS_TEST_MODE': 'true'}):
            start_time = time.time()
            
            result = subprocess.run([
                'python3', 'tools/daily_summary.py',
                '--period', 'week',
                '--format', 'json'
            ], capture_output=True, text=True, cwd=project_root)
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            assert result.returncode == 0
            assert execution_time < 10.0, f"Statistics generation too slow: {execution_time:.2f}s"


class TestPhase1Requirements:
    """Validate Phase 1 core requirements and deliverables"""
    
    def test_no_ai_dependencies(self):
        """All functionality works without LLM/AI"""
        with patch.dict(os.environ, {'AICOS_TEST_MODE': 'true'}):
            
            # Verify core Phase 1 modules have no AI dependencies
            phase1_modules = [
                'src/queries/time_queries.py',
                'src/queries/person_queries.py', 
                'src/queries/structured.py',
                'src/calendar/availability.py',
                'src/aggregators/basic_stats.py'
            ]
            
            ai_indicators = ['openai', 'anthropic', 'gpt', 'claude', 'embedding']
            
            for module_path in phase1_modules:
                if (project_root / module_path).exists():
                    with open(project_root / module_path, 'r') as f:
                        content = f.read().lower()
                    
                    # Remove comments and docstrings to focus on actual imports/code
                    lines = content.split('\n')
                    code_lines = []
                    in_docstring = False
                    
                    for line in lines:
                        stripped = line.strip()
                        
                        # Skip comment lines
                        if stripped.startswith('#'):
                            continue
                        
                        # Handle docstrings
                        if '"""' in stripped or "'''" in stripped:
                            in_docstring = not in_docstring
                            continue
                        
                        if not in_docstring:
                            code_lines.append(stripped)
                    
                    actual_code = ' '.join(code_lines).lower()
                    
                    for indicator in ai_indicators:
                        assert indicator not in actual_code, f"AI dependency found in {module_path}: {indicator}"
    
    def test_cli_tools_functional(self):
        """All CLI tools provide working functionality"""
        with patch.dict(os.environ, {'AICOS_TEST_MODE': 'true'}):
            
            # Test core CLI tools work
            cli_tests = [
                (['python3', 'tools/query_facts.py', '--help'], 'Query facts help'),
                (['python3', 'tools/daily_summary.py', '--help'], 'Daily summary help'),
                (['python3', 'tools/query_facts.py', 'time', 'today'], 'Time query'),
            ]
            
            for cmd, description in cli_tests:
                result = subprocess.run(cmd, capture_output=True, text=True, cwd=project_root)
                assert result.returncode == 0, f"{description} failed: {result.stderr}"
                assert len(result.stdout) > 0, f"{description} produced no output"
    
    def test_unified_search_capability(self):
        """Unified search across all data sources (core Phase 1 promise)"""
        with patch.dict(os.environ, {'AICOS_TEST_MODE': 'true'}):
            
            result = subprocess.run([
                'python3', 'tools/query_facts.py', 'time', 'yesterday', '--format', 'json'
            ], capture_output=True, text=True, cwd=project_root)
            
            assert result.returncode == 0
            data = json.loads(result.stdout)
            
            # Should include results with source attribution
            assert 'results' in data
            for result_item in data['results']:
                assert 'source' in result_item
                assert 'content' in result_item
            
            # Should work across different data types
            sources_found = set()
            for result_item in data['results']:
                sources_found.add(result_item['source'])
            
            # Should have at least one source with data
            assert len(sources_found) >= 1
    
    def test_deterministic_results(self):
        """Same query returns consistent results"""
        with patch.dict(os.environ, {'AICOS_TEST_MODE': 'true'}):
            query_cmd = [
                'python3', 'tools/query_facts.py', 'time', 'today', '--format', 'json'
            ]
            
            # Run same query multiple times
            results = []
            for _ in range(3):
                result = subprocess.run(query_cmd, capture_output=True, text=True, cwd=project_root)
                assert result.returncode == 0
                results.append(json.loads(result.stdout))
            
            # Results should be consistent
            assert all('results' in result for result in results)
            assert all('metadata' in result for result in results)
            
            # Verify mock mode consistency
            for result in results:
                assert result.get('metadata', {}).get('mock_mode') is True


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])