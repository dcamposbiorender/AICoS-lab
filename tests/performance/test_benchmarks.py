"""
Phase 1 Performance Benchmark Suite
Validates all Phase 1 performance commitments and targets

CRITICAL PERFORMANCE REQUIREMENTS:
- Search response time: <1 second for typical queries
- Migration performance: <30 seconds per migration
- Memory usage: <500MB for normal operations  
- Indexing throughput: >1000 records/second
- Concurrent operation support
- Large dataset handling efficiency
"""

import pytest
import time
import json
import sqlite3
import threading
import tempfile
import shutil
import psutil
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

# Import project modules
from src.search.database import SearchDatabase
from src.search.migrations import MigrationManager
from src.search.schema_validator import SchemaValidator


class TestPhase1Benchmarks:
    """Validate Phase 1 performance commitments against real targets"""
    
    def setup_method(self):
        """Setup performance testing environment"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.db_path = self.test_dir / 'benchmark.db'
        self.migration_dir = self.test_dir / 'migrations'
        
        # Copy migration files
        self.migration_dir.mkdir(parents=True, exist_ok=True)
        project_root = Path(__file__).parent.parent.parent
        source_migrations = project_root / 'migrations'
        
        if source_migrations.exists():
            for migration_file in source_migrations.glob('*.sql'):
                shutil.copy(migration_file, self.migration_dir)
        
        # Initialize performance monitoring
        self.performance_results = {}
        
        print(f"\nPerformance test environment: {self.test_dir}")
    
    def teardown_method(self):
        """Cleanup and report performance results"""
        # Log final performance summary
        if self.performance_results:
            print(f"\n=== PHASE 1 PERFORMANCE SUMMARY ===")
            for test_name, metrics in self.performance_results.items():
                print(f"{test_name}:")
                if isinstance(metrics, dict):
                    for metric_name, value in metrics.items():
                        if isinstance(value, float):
                            print(f"  {metric_name}: {value:.3f}")
                        else:
                            print(f"  {metric_name}: {value}")
                else:
                    print(f"  Result: {metrics}")
        
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    @pytest.mark.performance
    def test_search_response_time_target(self):
        """Core Phase 1 Promise: Search completes in <1 second"""
        # Setup database with realistic dataset
        migration_manager = MigrationManager(str(self.db_path), str(self.migration_dir))
        migration_manager.apply_migration('001_initial_schema.sql')
        migration_manager.apply_migration('002_query_optimizations.sql')
        
        search_db = SearchDatabase(str(self.db_path))
        
        # Create realistic dataset (5000 records)
        large_dataset = self._generate_realistic_dataset(5000)
        
        # Index dataset and measure indexing performance
        index_start = time.time()
        result = search_db.index_records_batch(large_dataset, 'benchmark')
        index_time = time.time() - index_start
        
        assert result['indexed'] == 5000
        
        # Test various query types with performance requirements
        query_types = [
            ('simple_text_search', lambda: search_db.search('project meeting', limit=50)),
            ('person_specific_search', lambda: search_db.search('user_025@example.com', limit=100)),
            ('date_range_search', lambda: search_db.search('status update', 
                                                          date_range=('2025-08-01', '2025-08-15'), limit=100)),
            ('source_filtered_search', lambda: search_db.search('document', source='drive', limit=50)),
            ('complex_multi_term', lambda: search_db.search('project status meeting update', limit=75))
        ]
        
        search_performance = {}
        
        for query_name, query_func in query_types:
            times = []
            result_counts = []
            
            # Run each query multiple times for statistical validity
            for run in range(10):  # Increased runs for more accurate benchmarking
                start_time = time.time()
                results = query_func()
                end_time = time.time()
                
                execution_time = end_time - start_time
                times.append(execution_time)
                result_counts.append(len(results))
                
                # Verify query returns meaningful results
                assert len(results) > 0, f"Query {query_name} run {run} returned no results"
            
            # Calculate statistics
            avg_time = sum(times) / len(times)
            max_time = max(times)
            min_time = min(times)
            avg_results = sum(result_counts) / len(result_counts)
            
            search_performance[query_name] = {
                'average_time_ms': avg_time * 1000,
                'max_time_ms': max_time * 1000,
                'min_time_ms': min_time * 1000,
                'avg_result_count': avg_results,
                'all_times': [t * 1000 for t in times]
            }
            
            # CORE PHASE 1 REQUIREMENT: <1 second average
            assert avg_time < 1.0, \
                f"Query {query_name} average time {avg_time:.3f}s exceeds 1s target"
            
            # No query should take more than 2 seconds
            assert max_time < 2.0, \
                f"Query {query_name} max time {max_time:.3f}s exceeds 2s limit"
        
        # Store results for summary
        self.performance_results['search_performance'] = search_performance
        self.performance_results['indexing_performance'] = {
            'records_indexed': 5000,
            'indexing_time_seconds': index_time,
            'records_per_second': 5000 / index_time,
            'meets_target': (5000 / index_time) > 1000  # Target: >1000 records/sec
        }
        
        # Verify indexing performance target
        assert (5000 / index_time) > 1000, \
            f"Indexing performance {5000/index_time:.1f} records/sec below 1000 target"
    
    @pytest.mark.performance
    def test_large_dataset_handling(self):
        """System handles large datasets efficiently (Phase 1 scalability)"""
        # Setup database
        migration_manager = MigrationManager(str(self.db_path), str(self.migration_dir))
        for migration in ['001_initial_schema.sql', '002_query_optimizations.sql', '003_statistics_views.sql']:
            migration_manager.apply_migration(migration)
        
        search_db = SearchDatabase(str(self.db_path))
        
        # Create large dataset (15,000 records - approaching realistic usage)
        large_dataset = self._generate_realistic_dataset(15000)
        
        # Monitor memory usage during indexing
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024**2  # MB
        
        # Index in batches and measure performance
        batch_size = 1000
        total_index_time = 0
        
        for i in range(0, len(large_dataset), batch_size):
            batch = large_dataset[i:i+batch_size]
            
            batch_start = time.time()
            result = search_db.index_records_batch(batch, 'large_dataset')
            batch_time = time.time() - batch_start
            
            total_index_time += batch_time
            
            assert result['indexed'] == len(batch)
            assert result['errors'] == 0
        
        peak_memory = process.memory_info().rss / 1024**2  # MB
        memory_growth = peak_memory - initial_memory
        
        # Test large dataset queries
        large_dataset_queries = [
            ('broad_search_large', lambda: search_db.search('project', limit=200)),
            ('specific_search_large', lambda: search_db.search('user_5000@example.com', limit=50)),
            ('date_range_large', lambda: search_db.search('update', 
                                                          date_range=('2025-07-01', '2025-08-31'), limit=500))
        ]
        
        large_query_performance = {}
        
        for query_name, query_func in large_dataset_queries:
            start_time = time.time()
            results = query_func()
            execution_time = time.time() - start_time
            
            large_query_performance[query_name] = {
                'execution_time_ms': execution_time * 1000,
                'result_count': len(results),
                'results_per_second': len(results) / execution_time if execution_time > 0 else 0
            }
            
            # Large dataset queries should still be fast
            assert execution_time < 3.0, \
                f"Large dataset query {query_name} took {execution_time:.3f}s, exceeds 3s limit"
            
            assert len(results) > 0, f"Large dataset query {query_name} returned no results"
        
        # Memory usage should be reasonable
        assert memory_growth < 500, \
            f"Memory growth {memory_growth:.1f}MB exceeds 500MB limit during large dataset handling"
        
        # Overall indexing performance should remain good
        overall_throughput = 15000 / total_index_time
        assert overall_throughput > 500, \
            f"Large dataset indexing throughput {overall_throughput:.1f} records/sec below 500 target"
        
        self.performance_results['large_dataset_performance'] = {
            'dataset_size': 15000,
            'total_index_time': total_index_time,
            'throughput_records_per_sec': overall_throughput,
            'memory_growth_mb': memory_growth,
            'query_performance': large_query_performance,
            'meets_memory_target': memory_growth < 500,
            'meets_throughput_target': overall_throughput > 500
        }
    
    @pytest.mark.performance  
    def test_concurrent_operations(self):
        """System handles concurrent operations without significant degradation"""
        # Setup database
        migration_manager = MigrationManager(str(self.db_path), str(self.migration_dir))
        migration_manager.apply_migration('001_initial_schema.sql')
        migration_manager.apply_migration('002_query_optimizations.sql')
        
        search_db = SearchDatabase(str(self.db_path))
        
        # Index initial dataset
        initial_data = self._generate_realistic_dataset(2000)
        search_db.index_records_batch(initial_data, 'concurrent_test')
        
        # Define concurrent operations
        def search_operation(query_id: int, search_term: str) -> Dict[str, Any]:
            start_time = time.time()
            results = search_db.search(f'{search_term} {query_id % 10}', limit=50)
            execution_time = time.time() - start_time
            
            return {
                'query_id': query_id,
                'search_term': search_term,
                'execution_time': execution_time,
                'result_count': len(results),
                'success': len(results) > 0
            }
        
        # Run concurrent searches
        concurrent_queries = [
            ('project', 20),  # 20 concurrent "project" searches
            ('meeting', 15),  # 15 concurrent "meeting" searches  
            ('update', 10),   # 10 concurrent "update" searches
            ('document', 5)   # 5 concurrent "document" searches
        ]
        
        all_operations = []
        for search_term, count in concurrent_queries:
            for i in range(count):
                all_operations.append((i, search_term))
        
        # Execute concurrent operations
        concurrent_start = time.time()
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_op = {
                executor.submit(search_operation, query_id, search_term): (query_id, search_term)
                for query_id, search_term in all_operations
            }
            
            concurrent_results = []
            for future in as_completed(future_to_op):
                query_id, search_term = future_to_op[future]
                try:
                    result = future.result(timeout=10)  # 10 second timeout per operation
                    concurrent_results.append(result)
                except Exception as e:
                    # Record failures
                    concurrent_results.append({
                        'query_id': query_id,
                        'search_term': search_term,
                        'execution_time': 10.0,
                        'result_count': 0,
                        'success': False,
                        'error': str(e)
                    })
        
        concurrent_total_time = time.time() - concurrent_start
        
        # Analyze concurrent performance
        successful_operations = [r for r in concurrent_results if r['success']]
        failed_operations = [r for r in concurrent_results if not r['success']]
        
        if successful_operations:
            avg_concurrent_time = sum(r['execution_time'] for r in successful_operations) / len(successful_operations)
            max_concurrent_time = max(r['execution_time'] for r in successful_operations)
            
            # Concurrent operations should not be significantly slower
            assert avg_concurrent_time < 2.0, \
                f"Average concurrent operation time {avg_concurrent_time:.3f}s exceeds 2s limit"
            
            assert max_concurrent_time < 5.0, \
                f"Max concurrent operation time {max_concurrent_time:.3f}s exceeds 5s limit"
        
        # Most operations should succeed
        success_rate = len(successful_operations) / len(concurrent_results)
        assert success_rate > 0.95, \
            f"Concurrent operation success rate {success_rate:.3f} below 95% target"
        
        self.performance_results['concurrent_performance'] = {
            'total_operations': len(all_operations),
            'successful_operations': len(successful_operations),
            'failed_operations': len(failed_operations),
            'success_rate': success_rate,
            'avg_operation_time': avg_concurrent_time if successful_operations else 0,
            'max_operation_time': max_concurrent_time if successful_operations else 0,
            'total_concurrent_time': concurrent_total_time,
            'operations_per_second': len(all_operations) / concurrent_total_time,
            'meets_targets': success_rate > 0.95 and (avg_concurrent_time < 2.0 if successful_operations else False)
        }
    
    @pytest.mark.performance
    def test_migration_performance(self):
        """Migration operations complete within acceptable timeframes"""
        # Create fresh database for migration testing
        migration_db_path = self.test_dir / 'migration_benchmark.db'
        migration_manager = MigrationManager(str(migration_db_path), str(self.migration_dir))
        
        # Pre-populate with some data to make migrations more realistic
        search_db = SearchDatabase(str(migration_db_path))
        
        # Apply initial schema first
        migration_start = time.time()
        result_001 = migration_manager.apply_migration('001_initial_schema.sql')
        migration_001_time = time.time() - migration_start
        
        assert result_001['success']
        assert migration_001_time < 30.0, \
            f"Initial schema migration took {migration_001_time:.3f}s, exceeds 30s limit"
        
        # Add some data before subsequent migrations
        test_data = self._generate_realistic_dataset(1000)
        search_db.index_records_batch(test_data, 'migration_test')
        
        # Apply optimization migrations
        migration_times = {'001_initial_schema.sql': migration_001_time}
        
        for migration_file in ['002_query_optimizations.sql', '003_statistics_views.sql']:
            migration_start = time.time()
            result = migration_manager.apply_migration(migration_file)
            migration_time = time.time() - migration_start
            
            assert result['success'], f"Migration {migration_file} failed: {result}"
            assert migration_time < 30.0, \
                f"Migration {migration_file} took {migration_time:.3f}s, exceeds 30s limit"
            
            migration_times[migration_file] = migration_time
        
        # Test rollback performance
        rollback_start = time.time()
        rollback_result = migration_manager.rollback_to_version(2)
        rollback_time = time.time() - rollback_start
        
        assert rollback_result['success']
        assert rollback_time < 60.0, \
            f"Rollback operation took {rollback_time:.3f}s, exceeds 60s limit"
        
        total_migration_time = sum(migration_times.values())
        
        self.performance_results['migration_performance'] = {
            'individual_migrations': migration_times,
            'total_migration_time': total_migration_time,
            'rollback_time': rollback_time,
            'meets_individual_target': all(t < 30.0 for t in migration_times.values()),
            'meets_total_target': total_migration_time < 90.0,  # 3 migrations * 30s
            'meets_rollback_target': rollback_time < 60.0
        }
        
        # All migration performance targets should be met
        assert total_migration_time < 90.0, \
            f"Total migration time {total_migration_time:.3f}s exceeds 90s target"
    
    @pytest.mark.performance
    def test_database_view_performance(self):
        """Database views (Agent B statistics) perform within targets"""
        # Setup full database with statistics views
        migration_manager = MigrationManager(str(self.db_path), str(self.migration_dir))
        for migration in ['001_initial_schema.sql', '002_query_optimizations.sql', '003_statistics_views.sql']:
            migration_manager.apply_migration(migration)
        
        search_db = SearchDatabase(str(self.db_path))
        
        # Create dataset that will populate views meaningfully
        view_test_data = self._generate_realistic_dataset(5000)
        search_db.index_records_batch(view_test_data, 'view_test')
        
        # Test all statistics views created by Agent B
        view_queries = [
            ('channel_stats', "SELECT * FROM channel_stats ORDER BY message_count DESC LIMIT 100"),
            ('person_stats', "SELECT * FROM person_stats WHERE total_activity > 10 ORDER BY total_activity DESC LIMIT 50"),
            ('temporal_patterns', "SELECT * FROM temporal_patterns WHERE hour_of_day BETWEEN '09' AND '17' LIMIT 200"),
            ('communication_patterns', "SELECT * FROM communication_patterns ORDER BY interaction_count DESC LIMIT 75"),
            ('weekly_activity', "SELECT * FROM weekly_activity WHERE week >= strftime('%Y-%W', 'now', '-30 days') LIMIT 100"),
            ('cross_source_activity', "SELECT * FROM cross_source_activity WHERE sources_used > 1 LIMIT 50"),
            ('activity_intensity', "SELECT * FROM activity_intensity WHERE intensity_level != 'none' LIMIT 100")
        ]
        
        view_performance = {}
        
        with sqlite3.connect(self.db_path) as conn:
            for view_name, query in view_queries:
                # Run each view query multiple times
                times = []
                result_counts = []
                
                for run in range(5):
                    start_time = time.time()
                    cursor = conn.execute(query)
                    results = cursor.fetchall()
                    execution_time = time.time() - start_time
                    
                    times.append(execution_time)
                    result_counts.append(len(results))
                
                avg_time = sum(times) / len(times)
                max_time = max(times)
                avg_results = sum(result_counts) / len(result_counts)
                
                view_performance[view_name] = {
                    'avg_execution_time_ms': avg_time * 1000,
                    'max_execution_time_ms': max_time * 1000,
                    'avg_result_count': avg_results,
                    'meets_target': avg_time < 1.0  # Views should execute in <1 second
                }
                
                # Views should be fast for Agent B statistics
                assert avg_time < 1.0, \
                    f"View {view_name} average time {avg_time:.3f}s exceeds 1s target"
                
                assert max_time < 2.0, \
                    f"View {view_name} max time {max_time:.3f}s exceeds 2s limit"
                
                # Views should return meaningful data
                assert avg_results > 0, f"View {view_name} returns no results"
        
        self.performance_results['view_performance'] = view_performance
    
    @pytest.mark.performance
    def test_memory_usage_constraints(self):
        """Validate memory usage stays within reasonable bounds"""
        # Setup database
        migration_manager = MigrationManager(str(self.db_path), str(self.migration_dir))
        migration_manager.apply_migration('001_initial_schema.sql')
        
        search_db = SearchDatabase(str(self.db_path))
        
        # Monitor memory throughout operations
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024**2  # MB
        memory_samples = [initial_memory]
        
        # Phase 1: Large indexing operation
        large_dataset = self._generate_realistic_dataset(10000)
        
        # Index in chunks while monitoring memory
        chunk_size = 1000
        for i in range(0, len(large_dataset), chunk_size):
            chunk = large_dataset[i:i+chunk_size]
            search_db.index_records_batch(chunk, 'memory_test')
            
            current_memory = process.memory_info().rss / 1024**2
            memory_samples.append(current_memory)
        
        # Phase 2: Intensive query operations
        intensive_queries = [
            lambda: search_db.search('project', limit=500),
            lambda: search_db.search('meeting status update document', limit=1000),
            lambda: search_db.search('user', date_range=('2025-07-01', '2025-08-31'), limit=750)
        ]
        
        for query_func in intensive_queries:
            for run in range(10):  # Multiple runs to stress memory
                query_func()
                current_memory = process.memory_info().rss / 1024**2
                memory_samples.append(current_memory)
        
        # Phase 3: Migration operations
        migration_manager.apply_migration('002_query_optimizations.sql')
        current_memory = process.memory_info().rss / 1024**2
        memory_samples.append(current_memory)
        
        migration_manager.apply_migration('003_statistics_views.sql')
        final_memory = process.memory_info().rss / 1024**2
        memory_samples.append(final_memory)
        
        # Analyze memory usage
        peak_memory = max(memory_samples)
        average_memory = sum(memory_samples) / len(memory_samples)
        memory_growth = peak_memory - initial_memory
        
        # Memory constraints for Phase 1
        assert memory_growth < 500, \
            f"Memory growth {memory_growth:.1f}MB exceeds 500MB limit"
        
        assert peak_memory < initial_memory + 500, \
            f"Peak memory {peak_memory:.1f}MB exceeds limit (initial: {initial_memory:.1f}MB)"
        
        self.performance_results['memory_performance'] = {
            'initial_memory_mb': initial_memory,
            'peak_memory_mb': peak_memory,
            'final_memory_mb': final_memory,
            'memory_growth_mb': memory_growth,
            'average_memory_mb': average_memory,
            'memory_samples': len(memory_samples),
            'meets_growth_target': memory_growth < 500,
            'meets_peak_target': peak_memory < initial_memory + 500
        }
    
    def _generate_realistic_dataset(self, count: int) -> List[Dict[str, Any]]:
        """Generate realistic test dataset for performance testing"""
        base_date = datetime(2025, 7, 1)
        
        # Realistic content templates
        content_templates = [
            "Project {project_id} status update: {status} - meeting scheduled for {date}",
            "Budget review for Q{quarter} shows {trend} - document in drive folder",
            "Team meeting notes: discussed {topic} and {topic2} - action items assigned",
            "Client feedback on {project_id}: {feedback_type} response required by {deadline}",
            "Weekly standup: completed {task_count} tasks, blocked on {blocker}",
            "Document review: {document_type} needs approval from {approver}",
            "System alert: {system} showing {metric} at {value} - investigation needed",
            "Training session on {topic} scheduled for {date} in {location}",
            "Performance metrics for {period}: {metric1} up {percent}%, {metric2} stable",
            "Vendor communication: {vendor} proposal for {service} - evaluation in progress"
        ]
        
        statuses = ["on track", "delayed", "ahead of schedule", "needs review", "completed"]
        trends = ["positive growth", "stable performance", "concerning decline", "significant improvement"]
        topics = ["budget allocation", "team structure", "process improvement", "technology upgrade", "client relations"]
        feedback_types = ["positive", "mixed", "critical", "enthusiastic", "constructive"]
        document_types = ["contract", "proposal", "specification", "report", "policy"]
        systems = ["database", "API", "frontend", "authentication", "monitoring"]
        metrics = ["response time", "error rate", "throughput", "availability", "performance"]
        
        dataset = []
        
        for i in range(count):
            record_date = base_date + timedelta(
                days=i % 60,  # Spread over 2 months
                hours=8 + (i % 12),  # Business hours
                minutes=i % 60
            )
            
            # Choose content template and fill in realistic values
            template = content_templates[i % len(content_templates)]
            
            content = template.format(
                project_id=f"PROJ-{(i % 100):03d}",
                status=statuses[i % len(statuses)],
                date=record_date.strftime("%Y-%m-%d"),
                quarter=((i % 4) + 1),
                trend=trends[i % len(trends)],
                topic=topics[i % len(topics)],
                topic2=topics[(i + 1) % len(topics)],
                feedback_type=feedback_types[i % len(feedback_types)],
                deadline=(record_date + timedelta(days=7 + (i % 14))).strftime("%Y-%m-%d"),
                task_count=3 + (i % 8),
                blocker=f"dependency on {topics[i % len(topics)]}",
                document_type=document_types[i % len(document_types)],
                approver=f"manager_{(i % 20):02d}",
                system=systems[i % len(systems)],
                metric=metrics[i % len(metrics)],
                value=f"{50 + (i % 50)}%",
                period=f"week {(i % 52) + 1}",
                metric1=metrics[i % len(metrics)],
                percent=5 + (i % 15),
                metric2=metrics[(i + 1) % len(metrics)],
                vendor=f"vendor_{(i % 30):02d}",
                service=f"service_{(i % 10):02d}",
                location=f"room_{chr(65 + (i % 26))}"
            )
            
            record = {
                'id': f'perf_test_{i:05d}',
                'content': content,
                'source': ['slack', 'calendar', 'drive'][i % 3],
                'created_at': record_date.isoformat() + 'Z',
                'date': record_date.strftime('%Y-%m-%d'),
                'person_id': f'user_{(i % 100):03d}@example.com',
                'channel_id': f'channel_{(i % 50):02d}'
            }
            
            dataset.append(record)
        
        return dataset