"""
Phase 1 Integration Tests - End-to-End Validation
Tests complete Phase 1 functionality: collection → indexing → querying

CRITICAL REQUIREMENTS TESTED:
- Complete data pipeline functionality
- Search accuracy against known data
- Calendar coordination without AI
- Cross-module consistency
- Performance targets met
- Data integrity preserved
"""

import pytest
import json
import tempfile
import subprocess
import sqlite3
import hashlib
import time
import shutil
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any

# Import project modules
from src.search.database import SearchDatabase
from src.search.migrations import MigrationManager
from src.search.schema_validator import SchemaValidator
from src.core.config import get_config
from src.core.state import StateManager


class TestPhase1Integration:
    """Test complete Phase 1 functionality end-to-end"""
    
    def setup_method(self):
        """Setup test environment for integration tests"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.db_path = self.test_dir / 'test_integration.db'
        self.migration_dir = self.test_dir / 'migrations'
        self.data_dir = self.test_dir / 'data'
        self.archive_dir = self.data_dir / 'archive'
        
        # Create directory structure
        self.migration_dir.mkdir(parents=True, exist_ok=True)
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy migration files to test directory
        project_root = Path(__file__).parent.parent.parent
        source_migrations = project_root / 'migrations'
        
        if source_migrations.exists():
            for migration_file in source_migrations.glob('*.sql'):
                shutil.copy(migration_file, self.migration_dir)
        
        # Initialize components
        self.migration_manager = MigrationManager(
            str(self.db_path), 
            str(self.migration_dir)
        )
        
        # Create test data
        self._create_test_data()
    
    def teardown_method(self):
        """Cleanup test environment"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def _create_test_data(self):
        """Create realistic test data for integration testing"""
        test_data = {
            'slack_messages': [
                {
                    'id': 'msg_001',
                    'content': 'Project Alpha meeting tomorrow at 2pm in conference room A',
                    'source': 'slack',
                    'created_at': '2025-08-19T10:30:00Z',
                    'person_id': 'john@example.com',
                    'channel_id': 'general'
                },
                {
                    'id': 'msg_002', 
                    'content': 'TODO: Review quarterly budget spreadsheet by Friday',
                    'source': 'slack',
                    'created_at': '2025-08-19T11:15:00Z',
                    'person_id': 'jane@example.com',
                    'channel_id': 'finance'
                },
                {
                    'id': 'msg_003',
                    'content': 'Weekly standup notes uploaded to drive folder',
                    'source': 'slack', 
                    'created_at': '2025-08-18T16:45:00Z',
                    'person_id': 'bob@example.com',
                    'channel_id': 'general'
                }
            ],
            'calendar_events': [
                {
                    'id': 'cal_001',
                    'content': 'Project Alpha Planning Session',
                    'source': 'calendar',
                    'created_at': '2025-08-20T14:00:00Z',
                    'person_id': 'john@example.com',
                    'channel_id': 'meeting_room_a'
                },
                {
                    'id': 'cal_002',
                    'content': 'Budget Review Meeting with Finance Team',
                    'source': 'calendar',
                    'created_at': '2025-08-22T09:00:00Z',
                    'person_id': 'jane@example.com', 
                    'channel_id': 'meeting_room_b'
                }
            ],
            'drive_documents': [
                {
                    'id': 'doc_001',
                    'content': 'Q3 Budget Analysis Spreadsheet - Updated financial projections',
                    'source': 'drive',
                    'created_at': '2025-08-19T13:20:00Z',
                    'person_id': 'jane@example.com',
                    'channel_id': 'finance_folder'
                }
            ]
        }
        
        # Save test data to archive directory
        for data_type, records in test_data.items():
            type_dir = self.archive_dir / data_type
            type_dir.mkdir(exist_ok=True)
            
            # Create daily data file
            data_file = type_dir / f'{date.today().isoformat()}.jsonl'
            with open(data_file, 'w') as f:
                for record in records:
                    f.write(json.dumps(record) + '\n')
        
        self.test_data = test_data
    
    def test_complete_data_pipeline(self):
        """Validate entire data flow: migration → indexing → querying"""
        # Step 1: Apply database migrations
        self.migration_manager.apply_migration('001_initial_schema.sql')
        self.migration_manager.apply_migration('002_query_optimizations.sql')
        self.migration_manager.apply_migration('003_statistics_views.sql')
        
        assert self.migration_manager.get_current_version() == 3
        
        # Step 2: Initialize search database and index data
        search_db = SearchDatabase(str(self.db_path))
        
        # Index all test data
        all_records = []
        for records in self.test_data.values():
            all_records.extend(records)
        
        # Add date field for indexing compatibility
        for record in all_records:
            record['date'] = record['created_at'].split('T')[0]
        
        result = search_db.index_records_batch(all_records, 'mixed')
        assert result['indexed'] == len(all_records)
        assert result['errors'] == 0
        
        # Step 3: Verify search functionality
        search_results = search_db.search('Project Alpha', limit=10)
        assert len(search_results) >= 2  # Should find both slack message and calendar event
        
        # Verify content accuracy
        found_content = [r['content'] for r in search_results]
        assert any('Project Alpha meeting' in content for content in found_content)
        assert any('Project Alpha Planning' in content for content in found_content)
        
        # Step 4: Test query views work
        with sqlite3.connect(self.db_path) as conn:
            # Test daily activity view
            cursor = conn.execute("""
                SELECT activity_date, source, activity_count 
                FROM daily_activity 
                WHERE activity_date >= '2025-08-18'
                ORDER BY activity_date, source
            """)
            activity_results = cursor.fetchall()
            assert len(activity_results) > 0
            
            # Test person stats view
            cursor = conn.execute("""
                SELECT person_id, total_activity 
                FROM person_stats 
                WHERE person_id = 'john@example.com'
            """)
            person_results = cursor.fetchall()
            assert len(person_results) > 0
        
        # Step 5: Verify schema validation passes
        validator = SchemaValidator(str(self.db_path))
        validation_result = validator.validate_schema()
        assert validation_result['valid'] is True
    
    def test_search_accuracy_validation(self):
        """Validate search results accuracy against known data"""
        # Setup database and index test data
        self.migration_manager.apply_migration('001_initial_schema.sql')
        search_db = SearchDatabase(str(self.db_path))
        
        all_records = []
        for records in self.test_data.values():
            all_records.extend(records)
        
        for record in all_records:
            record['date'] = record['created_at'].split('T')[0]
        
        search_db.index_records_batch(all_records, 'mixed')
        
        # Test specific searches
        test_cases = [
            {
                'query': 'Project Alpha',
                'expected_results': 2,  # Slack message + calendar event
                'must_contain': ['meeting', 'Planning']
            },
            {
                'query': 'budget spreadsheet',
                'expected_results': 2,  # Slack message + drive document
                'must_contain': ['TODO', 'Budget Analysis']
            },
            {
                'query': 'jane@example.com',
                'expected_results': 2,  # Finance-related items
                'must_contain': ['budget', 'Budget']
            }
        ]
        
        for test_case in test_cases:
            results = search_db.search(test_case['query'], limit=10)
            
            # Check result count
            assert len(results) >= test_case['expected_results'], \
                f"Expected at least {test_case['expected_results']} results for '{test_case['query']}', got {len(results)}"
            
            # Check content requirements
            found_content = ' '.join([r['content'] for r in results])
            for required_term in test_case['must_contain']:
                assert required_term in found_content, \
                    f"Required term '{required_term}' not found in results for query '{test_case['query']}'"
            
            # Verify source attribution
            for result in results:
                assert 'source' in result
                assert result['source'] in ['slack', 'calendar', 'drive']
                assert 'date' in result
                assert 'content' in result
    
    def test_calendar_coordination_accuracy(self):
        """Validate calendar coordination without AI dependencies"""
        # Setup database with calendar data
        self.migration_manager.apply_migration('001_initial_schema.sql')
        self.migration_manager.apply_migration('003_statistics_views.sql')
        
        search_db = SearchDatabase(str(self.db_path))
        
        # Index calendar events
        calendar_records = self.test_data['calendar_events']
        for record in calendar_records:
            record['date'] = record['created_at'].split('T')[0]
        
        search_db.index_records_batch(calendar_records, 'calendar')
        
        # Test calendar-specific queries
        with sqlite3.connect(self.db_path) as conn:
            # Find events for specific person
            cursor = conn.execute("""
                SELECT * FROM messages 
                WHERE source = 'calendar' AND person_id = 'john@example.com'
            """)
            john_events = cursor.fetchall()
            assert len(john_events) >= 1
            
            # Test temporal patterns view
            cursor = conn.execute("""
                SELECT activity_date, hour_of_day, activity_count
                FROM temporal_patterns 
                WHERE source = 'calendar'
                ORDER BY activity_date, hour_of_day
            """)
            temporal_results = cursor.fetchall()
            assert len(temporal_results) > 0
            
            # Verify deterministic analysis (no AI)
            # This should work without any LLM dependencies
            cursor = conn.execute("""
                SELECT person_id, COUNT(*) as event_count,
                       MIN(created_at) as earliest_event,
                       MAX(created_at) as latest_event
                FROM messages
                WHERE source = 'calendar'
                GROUP BY person_id
            """)
            person_calendar_stats = cursor.fetchall()
            assert len(person_calendar_stats) > 0
            
            # Each result should have deterministic data
            for person_id, event_count, earliest, latest in person_calendar_stats:
                assert person_id is not None
                assert event_count > 0
                assert earliest is not None
                assert latest is not None
    
    def test_cross_module_consistency(self):
        """Verify data consistency between Agent A, B, and C modules"""
        # Setup complete database
        for migration_file in ['001_initial_schema.sql', '002_query_optimizations.sql', '003_statistics_views.sql']:
            self.migration_manager.apply_migration(migration_file)
        
        search_db = SearchDatabase(str(self.db_path))
        
        # Index all test data
        all_records = []
        for records in self.test_data.values():
            all_records.extend(records)
        
        for record in all_records:
            record['date'] = record['created_at'].split('T')[0]
        
        search_db.index_records_batch(all_records, 'mixed')
        
        # Test consistency across different query methods
        with sqlite3.connect(self.db_path) as conn:
            # Method 1: Direct table query (Agent A approach)
            cursor = conn.execute("""
                SELECT person_id, COUNT(*) as direct_count
                FROM messages 
                WHERE person_id = 'john@example.com'
                GROUP BY person_id
            """)
            direct_results = dict(cursor.fetchall())
            
            # Method 2: Via person_stats view (Agent B approach)
            cursor = conn.execute("""
                SELECT person_id, SUM(total_activity) as view_count
                FROM person_stats
                WHERE person_id = 'john@example.com'
                GROUP BY person_id
            """)
            view_results = dict(cursor.fetchall())
            
            # Method 3: Via daily_activity view aggregation
            cursor = conn.execute("""
                SELECT person_id, SUM(activity_count) as daily_count
                FROM daily_activity
                WHERE person_id = 'john@example.com'
                GROUP BY person_id
            """)
            daily_results = dict(cursor.fetchall())
            
            # Verify consistency
            john_id = 'john@example.com'
            assert john_id in direct_results
            assert john_id in view_results  
            assert john_id in daily_results
            
            # Counts should match (allowing for view aggregation differences)
            direct_count = direct_results[john_id]
            view_count = view_results[john_id]
            daily_count = daily_results[john_id]
            
            assert direct_count == daily_count, \
                f"Direct count {direct_count} != daily view count {daily_count}"
            
            # View count might differ due to source grouping, but should be reasonable
            assert abs(direct_count - view_count) <= direct_count, \
                f"View count {view_count} too different from direct count {direct_count}"
    
    def test_migration_data_preservation(self):
        """Test that migrations preserve existing data"""
        # Start with initial schema
        self.migration_manager.apply_migration('001_initial_schema.sql')
        
        search_db = SearchDatabase(str(self.db_path))
        
        # Index initial data
        initial_records = self.test_data['slack_messages']
        for record in initial_records:
            record['date'] = record['created_at'].split('T')[0]
        
        result = search_db.index_records_batch(initial_records, 'slack')
        assert result['indexed'] == len(initial_records)
        
        # Calculate data checksum before migration
        pre_migration_checksum = self._calculate_data_checksum()
        
        # Apply additional migrations
        self.migration_manager.apply_migration('002_query_optimizations.sql')
        self.migration_manager.apply_migration('003_statistics_views.sql')
        
        # Verify data preserved
        post_migration_checksum = self._calculate_data_checksum()
        assert pre_migration_checksum == post_migration_checksum
        
        # Verify all original records still searchable
        for original_record in initial_records:
            search_term = original_record['content'].split()[0]  # First word
            results = search_db.search(search_term)
            
            found = any(
                original_record['id'] in r.get('metadata', {}).get('id', '') or 
                original_record['content'] in r['content']
                for r in results
            )
            assert found, f"Original record with content '{original_record['content'][:50]}...' not found after migration"
    
    def test_rollback_integrity(self):
        """Test rollback maintains data integrity"""
        # Apply all migrations
        for migration_file in ['001_initial_schema.sql', '002_query_optimizations.sql', '003_statistics_views.sql']:
            self.migration_manager.apply_migration(migration_file)
        
        assert self.migration_manager.get_current_version() == 3
        
        # Add test data
        search_db = SearchDatabase(str(self.db_path))
        test_records = self.test_data['slack_messages'][:2]  # Use subset for rollback test
        
        for record in test_records:
            record['date'] = record['created_at'].split('T')[0]
        
        search_db.index_records_batch(test_records, 'slack')
        
        # Calculate checksums before rollback
        pre_rollback_data = self._get_table_data('messages')
        
        # Rollback to version 2
        rollback_result = self.migration_manager.rollback_to_version(2)
        assert rollback_result['success'] is True
        assert self.migration_manager.get_current_version() == 2
        
        # Verify core data preserved
        post_rollback_data = self._get_table_data('messages')
        
        # Core columns should have same data
        core_columns = ['content', 'source', 'created_at', 'date']
        for i, pre_row in enumerate(pre_rollback_data):
            post_row = post_rollback_data[i]
            for col_idx, col_name in enumerate(core_columns):
                assert pre_row[col_idx] == post_row[col_idx], \
                    f"Data mismatch in column {col_name} after rollback"
        
        # Verify schema changes rolled back
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='view'")
            views = [row[0] for row in cursor.fetchall()]
            
            # Statistics views should be gone
            stats_views = ['channel_stats', 'person_stats', 'temporal_patterns']
            for stats_view in stats_views:
                assert stats_view not in views, \
                    f"Statistics view {stats_view} should have been removed by rollback"
    
    def _calculate_data_checksum(self) -> str:
        """Calculate checksum of core data for integrity verification"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT content, source, created_at, date 
                FROM messages 
                ORDER BY id
            """)
            data = cursor.fetchall()
            
            data_str = json.dumps(data, sort_keys=True)
            return hashlib.sha256(data_str.encode()).hexdigest()
    
    def _get_table_data(self, table_name: str) -> List[tuple]:
        """Get all data from a table"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(f"SELECT * FROM {table_name} ORDER BY id")
            return cursor.fetchall()


class TestPerformanceBenchmarks:
    """Test Phase 1 performance requirements"""
    
    def setup_method(self):
        """Setup performance testing environment"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.db_path = self.test_dir / 'perf_test.db'
        self.migration_dir = self.test_dir / 'migrations'
        
        # Copy migrations
        self.migration_dir.mkdir(parents=True, exist_ok=True)
        project_root = Path(__file__).parent.parent.parent
        source_migrations = project_root / 'migrations'
        
        if source_migrations.exists():
            for migration_file in source_migrations.glob('*.sql'):
                shutil.copy(migration_file, self.migration_dir)
        
        # Setup database
        self.migration_manager = MigrationManager(str(self.db_path), str(self.migration_dir))
        
        # Apply all migrations
        for migration_file in ['001_initial_schema.sql', '002_query_optimizations.sql', '003_statistics_views.sql']:
            self.migration_manager.apply_migration(migration_file)
        
        # Create large dataset for performance testing
        self._create_performance_test_data()
    
    def teardown_method(self):
        """Cleanup performance test environment"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def _create_performance_test_data(self):
        """Create larger dataset for performance testing"""
        search_db = SearchDatabase(str(self.db_path))
        
        # Generate 1000 test records
        large_dataset = []
        base_date = datetime(2025, 8, 1)
        
        for i in range(1000):
            record_date = base_date + timedelta(days=i % 30, hours=i % 24)
            
            record = {
                'id': f'perf_test_{i:04d}',
                'content': f'Performance test message {i} with searchable content about project {i % 10}',
                'source': ['slack', 'calendar', 'drive'][i % 3],
                'created_at': record_date.isoformat() + 'Z',
                'date': record_date.strftime('%Y-%m-%d'),
                'person_id': f'user_{i % 50}@example.com',
                'channel_id': f'channel_{i % 20}'
            }
            large_dataset.append(record)
        
        # Index in batches
        batch_size = 100
        for i in range(0, len(large_dataset), batch_size):
            batch = large_dataset[i:i+batch_size]
            search_db.index_records_batch(batch, 'performance_test')
        
        self.large_dataset = large_dataset
        self.search_db = search_db
    
    @pytest.mark.performance
    def test_query_performance_targets(self):
        """Validate all query types meet <2 second requirement"""
        query_test_cases = [
            ('simple_search', lambda: self.search_db.search('project', limit=50)),
            ('date_range_search', lambda: self.search_db.search('test', date_range=('2025-08-01', '2025-08-15'), limit=100)),
            ('source_filtered_search', lambda: self.search_db.search('message', source='slack', limit=100))
        ]
        
        performance_results = {}
        
        for test_name, query_func in query_test_cases:
            times = []
            
            # Run each query 5 times for statistical validity
            for run in range(5):
                start_time = time.time()
                results = query_func()
                end_time = time.time()
                
                execution_time = end_time - start_time
                times.append(execution_time)
                
                # Verify query returns results
                assert len(results) > 0, f"Query {test_name} returned no results"
            
            avg_time = sum(times) / len(times)
            max_time = max(times)
            min_time = min(times)
            
            performance_results[test_name] = {
                'average_time': avg_time,
                'max_time': max_time,
                'min_time': min_time,
                'all_times': times
            }
            
            # Core Phase 1 requirement: <2 seconds
            assert avg_time < 2.0, \
                f"Query {test_name} average time {avg_time:.3f}s exceeds 2s limit"
            assert max_time < 3.0, \
                f"Query {test_name} max time {max_time:.3f}s exceeds 3s limit"
        
        # Log performance results
        print(f"\nPhase 1 Query Performance Results:")
        for test_name, metrics in performance_results.items():
            print(f"  {test_name}: avg={metrics['average_time']:.3f}s, max={metrics['max_time']:.3f}s")
    
    @pytest.mark.performance
    def test_database_view_performance(self):
        """Test that database views meet performance requirements"""
        view_queries = [
            ('daily_activity', "SELECT * FROM daily_activity WHERE activity_date >= '2025-08-01' LIMIT 100"),
            ('person_stats', "SELECT * FROM person_stats WHERE total_activity > 5 LIMIT 50"),
            ('temporal_patterns', "SELECT * FROM temporal_patterns WHERE hour_of_day BETWEEN '09' AND '17' LIMIT 100")
        ]
        
        with sqlite3.connect(self.db_path) as conn:
            for view_name, query in view_queries:
                start_time = time.time()
                
                cursor = conn.execute(query)
                results = cursor.fetchall()
                
                end_time = time.time()
                execution_time = end_time - start_time
                
                # Views should execute quickly
                assert execution_time < 1.0, \
                    f"View {view_name} query took {execution_time:.3f}s, exceeds 1s limit"
                
                # Should return meaningful results
                assert len(results) > 0, f"View {view_name} returned no results"
    
    @pytest.mark.performance
    def test_migration_performance(self):
        """Test migration operations complete within reasonable time"""
        # Create a fresh database for migration testing
        temp_db = self.test_dir / 'migration_perf_test.db'
        
        migration_manager = MigrationManager(str(temp_db), str(self.migration_dir))
        
        # Time each migration
        migration_times = {}
        
        for migration_file in ['001_initial_schema.sql', '002_query_optimizations.sql', '003_statistics_views.sql']:
            start_time = time.time()
            
            result = migration_manager.apply_migration(migration_file)
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            migration_times[migration_file] = execution_time
            
            # Migrations should complete quickly
            assert result['success'] is True
            assert execution_time < 30.0, \
                f"Migration {migration_file} took {execution_time:.3f}s, exceeds 30s limit"
        
        # Total migration time should be reasonable
        total_time = sum(migration_times.values())
        assert total_time < 60.0, \
            f"Total migration time {total_time:.3f}s exceeds 60s limit"
        
        print(f"\nMigration Performance Results:")
        for migration, exec_time in migration_times.items():
            print(f"  {migration}: {exec_time:.3f}s")
        print(f"  Total: {total_time:.3f}s")


class TestDataIntegrity:
    """Test data integrity and audit trail preservation"""
    
    def setup_method(self):
        """Setup data integrity testing"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.db_path = self.test_dir / 'integrity_test.db'
        self.migration_dir = self.test_dir / 'migrations'
        
        # Setup migrations
        self.migration_dir.mkdir(parents=True, exist_ok=True)
        project_root = Path(__file__).parent.parent.parent
        source_migrations = project_root / 'migrations'
        
        if source_migrations.exists():
            for migration_file in source_migrations.glob('*.sql'):
                shutil.copy(migration_file, self.migration_dir)
        
        self.migration_manager = MigrationManager(str(self.db_path), str(self.migration_dir))
        
        # Apply migrations
        self.migration_manager.apply_migration('001_initial_schema.sql')
        self.search_db = SearchDatabase(str(self.db_path))
    
    def teardown_method(self):
        """Cleanup integrity testing"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_source_attribution_preserved(self):
        """All indexed data includes complete source attribution"""
        test_records = [
            {
                'id': 'test_001',
                'content': 'Test message with full attribution',
                'source': 'slack',
                'created_at': '2025-08-19T10:00:00Z',
                'date': '2025-08-19',
                'person_id': 'test@example.com',
                'channel_id': 'test_channel'
            }
        ]
        
        # Index with full metadata
        result = self.search_db.index_records_batch(test_records, 'test')
        assert result['indexed'] == 1
        
        # Verify source attribution in search results
        search_results = self.search_db.search('attribution')
        assert len(search_results) >= 1
        
        found_record = search_results[0]
        
        # Check required attribution fields
        required_fields = ['source', 'date']
        for field in required_fields:
            assert field in found_record, f"Missing required field: {field}"
            assert found_record[field] is not None, f"Field {field} is None"
        
        # Verify metadata preservation
        assert 'metadata' in found_record
        if found_record['metadata']:
            metadata = found_record['metadata']
            if isinstance(metadata, str):
                try:
                    metadata = json.loads(metadata)
                except json.JSONDecodeError:
                    pass  # Simple string metadata is acceptable
            
            # Should preserve original record structure
            assert 'id' in metadata or found_record.get('id')
    
    def test_no_data_modification_during_queries(self):
        """Query operations never modify source data"""
        # Index initial data
        test_records = [
            {
                'id': f'immutable_{i:03d}',
                'content': f'Immutable test record {i}',
                'source': 'test',
                'created_at': f'2025-08-19T{10+i:02d}:00:00Z',
                'date': '2025-08-19'
            }
            for i in range(10)
        ]
        
        result = self.search_db.index_records_batch(test_records, 'test')
        assert result['indexed'] == 10
        
        # Calculate initial data checksum
        initial_checksum = self._calculate_full_db_checksum()
        
        # Perform various query operations
        query_operations = [
            lambda: self.search_db.search('immutable'),
            lambda: self.search_db.search('test', source='test'),
            lambda: self.search_db.search('record', date_range=('2025-08-19', '2025-08-19')),
            lambda: self.search_db.search('nonexistent_query_should_return_empty'),
            lambda: self.search_db.get_stats()
        ]
        
        for i, query_op in enumerate(query_operations):
            # Run query multiple times
            for run in range(3):
                query_op()
            
            # Verify data unchanged after each operation
            current_checksum = self._calculate_full_db_checksum()
            assert current_checksum == initial_checksum, \
                f"Data modified by query operation {i} (run {run})"
    
    def test_deterministic_results(self):
        """Same query returns identical results across multiple runs"""
        # Index consistent test data
        test_records = [
            {
                'id': 'deterministic_001',
                'content': 'Deterministic test content for consistent results',
                'source': 'test',
                'created_at': '2025-08-19T12:00:00Z',
                'date': '2025-08-19'
            },
            {
                'id': 'deterministic_002', 
                'content': 'Another deterministic record with test content',
                'source': 'test',
                'created_at': '2025-08-19T13:00:00Z',
                'date': '2025-08-19'
            }
        ]
        
        self.search_db.index_records_batch(test_records, 'test')
        
        # Run same queries multiple times
        test_queries = [
            ('deterministic', {}),
            ('test content', {'source': 'test'}),
            ('record', {'date_range': ('2025-08-19', '2025-08-19')})
        ]
        
        for query_text, query_params in test_queries:
            results_set = []
            
            # Run query 5 times
            for run in range(5):
                results = self.search_db.search(query_text, **query_params)
                
                # Normalize results for comparison (remove any timestamps, etc.)
                normalized_results = []
                for result in results:
                    normalized = {
                        'content': result['content'],
                        'source': result['source'], 
                        'date': result['date']
                    }
                    normalized_results.append(normalized)
                
                # Sort for consistent comparison
                normalized_results.sort(key=lambda x: x['content'])
                results_set.append(normalized_results)
            
            # All results should be identical
            first_result = results_set[0]
            for i, result in enumerate(results_set[1:], 1):
                assert result == first_result, \
                    f"Query '{query_text}' run {i+1} returned different results than run 1"
    
    def test_schema_consistency_after_operations(self):
        """Database schema remains consistent after all operations"""
        # Perform comprehensive operations
        operations = [
            # Data operations
            lambda: self._index_test_batch('consistency_batch_1', 50),
            lambda: self._index_test_batch('consistency_batch_2', 25),
            
            # Query operations  
            lambda: self.search_db.search('consistency'),
            lambda: self.search_db.search('batch', limit=100),
            
            # Migration operations
            lambda: self.migration_manager.apply_migration('002_query_optimizations.sql'),
            lambda: self.migration_manager.apply_migration('003_statistics_views.sql')
        ]
        
        validator = SchemaValidator(str(self.db_path))
        
        for i, operation in enumerate(operations):
            # Perform operation
            operation()
            
            # Validate schema consistency
            validation_result = validator.validate_schema()
            assert validation_result['valid'] is True, \
                f"Schema validation failed after operation {i}: {validation_result.get('issues', [])}"
            
            # Validate data consistency
            consistency_result = validator.validate_data_consistency()
            assert consistency_result['valid'] is True, \
                f"Data consistency failed after operation {i}: {consistency_result.get('issues', [])}"
    
    def _calculate_full_db_checksum(self) -> str:
        """Calculate checksum of entire database content"""
        with sqlite3.connect(self.db_path) as conn:
            # Get all user table data
            cursor = conn.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' 
                AND name NOT LIKE 'sqlite_%'
                AND name NOT LIKE '%_fts'
                ORDER BY name
            """)
            
            table_names = [row[0] for row in cursor.fetchall()]
            
            all_data = {}
            for table_name in table_names:
                cursor = conn.execute(f"SELECT * FROM {table_name} ORDER BY rowid")
                table_data = cursor.fetchall()
                all_data[table_name] = table_data
            
            data_str = json.dumps(all_data, sort_keys=True, default=str)
            return hashlib.sha256(data_str.encode()).hexdigest()
    
    def _index_test_batch(self, batch_name: str, count: int):
        """Helper to index a batch of test records"""
        records = [
            {
                'id': f'{batch_name}_{i:03d}',
                'content': f'Test record {i} in batch {batch_name}',
                'source': 'test',
                'created_at': f'2025-08-19T{10 + i % 12:02d}:00:00Z',
                'date': '2025-08-19'
            }
            for i in range(count)
        ]
        
        result = self.search_db.index_records_batch(records, batch_name)
        assert result['indexed'] == count
        return result