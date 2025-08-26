#!/usr/bin/env python3
"""
Phase 1 Performance Benchmark Suite - Agent D Implementation

Comprehensive performance benchmarking for Phase 1 delivery validation.
Measures query performance, data throughput, and system responsiveness
against Phase 1 requirements.

Benchmark Categories:
- Query Engine Performance (Agent A) - <3s requirement
- Calendar Operations (Agent B) - <5s requirement  
- Statistics Generation (Agent B) - <10s requirement
- Database Operations - Migration and FTS performance
- CLI Tool Responsiveness - End-to-end user experience

Usage:
  python3 tools/benchmark_performance.py --full
  python3 tools/benchmark_performance.py --queries-only
  python3 tools/benchmark_performance.py --format json

References:
- tasks/phase1_agent_d_migration.md lines 350-400 for benchmark specifications
- tests/integration/test_phase1_complete.py for performance test patterns
"""

import argparse
import json
import logging
import os
import subprocess
import sqlite3
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from contextlib import contextmanager

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from search.migrations import create_migration_manager
from search.schema_validator import create_schema_validator

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkResult:
    """Individual benchmark test result"""
    name: str
    category: str
    duration_seconds: float
    status: str  # 'pass', 'warn', 'fail'
    requirement_seconds: float
    details: Dict[str, Any]
    error: Optional[str] = None


@dataclass 
class BenchmarkReport:
    """Complete benchmark report"""
    timestamp: str
    environment: Dict[str, str]
    summary: Dict[str, Any]
    results: List[BenchmarkResult]
    overall_status: str  # 'pass', 'degraded', 'fail'


class PerformanceBenchmark:
    """Phase 1 performance benchmark suite"""
    
    def __init__(self, db_path: str = "data/search.db"):
        self.db_path = Path(db_path)
        self.project_root = project_root
        self.test_mode = os.getenv('AICOS_TEST_MODE', '').lower() == 'true'
        
        # Performance requirements from Phase 1 specifications
        self.requirements = {
            'query_time': 3.0,      # <3s for query operations
            'calendar_time': 5.0,    # <5s for calendar operations 
            'statistics_time': 10.0, # <10s for statistics generation
            'migration_time': 30.0,  # <30s for schema migrations
            'cli_response_time': 2.0 # <2s for CLI tool startup
        }
    
    def run_full_benchmark(self) -> BenchmarkReport:
        """Run complete performance benchmark suite"""
        logger.info("Starting Phase 1 performance benchmark suite")
        start_time = datetime.now()
        results = []
        
        try:
            # Query engine benchmarks (Agent A)
            results.extend(self._benchmark_query_operations())
            
            # Calendar operations benchmarks (Agent B)
            results.extend(self._benchmark_calendar_operations())
            
            # Statistics generation benchmarks (Agent B)
            results.extend(self._benchmark_statistics_generation())
            
            # Database operations benchmarks
            results.extend(self._benchmark_database_operations())
            
            # CLI responsiveness benchmarks (Agent C)
            results.extend(self._benchmark_cli_responsiveness())
            
        except Exception as e:
            logger.error(f"Benchmark suite failed: {e}")
            results.append(BenchmarkResult(
                name="benchmark_execution",
                category="system",
                duration_seconds=0.0,
                status="fail",
                requirement_seconds=0.0,
                details={},
                error=str(e)
            ))
        
        # Generate summary and overall status
        summary = self._generate_summary(results)
        overall_status = self._determine_overall_status(results)
        
        return BenchmarkReport(
            timestamp=start_time.isoformat(),
            environment=self._get_environment_info(),
            summary=summary,
            results=results,
            overall_status=overall_status
        )
    
    def _benchmark_query_operations(self) -> List[BenchmarkResult]:
        """Benchmark Agent A query engine operations"""
        results = []
        
        query_tests = [
            {
                'name': 'time_query_recent',
                'args': ['time', 'yesterday'],
                'description': 'Recent time-based query'
            },
            {
                'name': 'time_query_range',
                'args': ['time', 'last week'],
                'description': 'Time range query'
            },
            {
                'name': 'person_query_activity',
                'args': ['person', 'alice@example.com', '--activity-summary'],
                'description': 'Person activity query'
            },
            {
                'name': 'pattern_query_todos',
                'args': ['patterns', '--pattern-type', 'todos'],
                'description': 'Pattern recognition query'
            }
        ]
        
        for test in query_tests:
            try:
                start_time = time.time()
                
                cmd = ['python3', 'tools/query_facts.py'] + test['args'] + ['--format', 'json']
                env = os.environ.copy()
                if self.test_mode:
                    env['AICOS_TEST_MODE'] = 'true'
                
                result = subprocess.run(
                    cmd, 
                    capture_output=True, 
                    text=True, 
                    cwd=self.project_root,
                    env=env,
                    timeout=self.requirements['query_time'] * 2  # Generous timeout
                )
                
                duration = time.time() - start_time
                
                # Determine status based on performance requirement
                if result.returncode != 0:
                    status = 'fail'
                    error = f"Command failed: {result.stderr}"
                elif duration > self.requirements['query_time']:
                    status = 'fail'
                    error = f"Exceeded {self.requirements['query_time']}s requirement"
                elif duration > self.requirements['query_time'] * 0.8:
                    status = 'warn'
                    error = None
                else:
                    status = 'pass'
                    error = None
                
                results.append(BenchmarkResult(
                    name=test['name'],
                    category='query_engine',
                    duration_seconds=duration,
                    status=status,
                    requirement_seconds=self.requirements['query_time'],
                    details={
                        'description': test['description'],
                        'command': ' '.join(cmd),
                        'return_code': result.returncode,
                        'test_mode': self.test_mode
                    },
                    error=error
                ))
                
            except subprocess.TimeoutExpired:
                results.append(BenchmarkResult(
                    name=test['name'],
                    category='query_engine',
                    duration_seconds=self.requirements['query_time'] * 2,
                    status='fail',
                    requirement_seconds=self.requirements['query_time'],
                    details={'description': test['description']},
                    error='Query timed out'
                ))
            except Exception as e:
                results.append(BenchmarkResult(
                    name=test['name'],
                    category='query_engine',
                    duration_seconds=0.0,
                    status='fail',
                    requirement_seconds=self.requirements['query_time'],
                    details={'description': test['description']},
                    error=str(e)
                ))
        
        return results
    
    def _benchmark_calendar_operations(self) -> List[BenchmarkResult]:
        """Benchmark Agent B calendar operations"""
        results = []
        
        calendar_tests = [
            {
                'name': 'calendar_find_slots_single',
                'args': ['calendar', 'find-slots', '--attendees', 'alice@example.com', '--duration', '60'],
                'description': 'Find meeting slots for single attendee'
            },
            {
                'name': 'calendar_find_slots_multiple',
                'args': ['calendar', 'find-slots', '--attendees', 'alice@example.com,bob@example.com', '--duration', '60'],
                'description': 'Find meeting slots for multiple attendees'
            },
            {
                'name': 'calendar_availability_check',
                'args': ['calendar', 'availability', '--person', 'alice@example.com', '--date', 'tomorrow'],
                'description': 'Check calendar availability'
            }
        ]
        
        for test in calendar_tests:
            try:
                start_time = time.time()
                
                cmd = ['python3', 'tools/query_facts.py'] + test['args'] + ['--format', 'json']
                env = os.environ.copy()
                if self.test_mode:
                    env['AICOS_TEST_MODE'] = 'true'
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    cwd=self.project_root,
                    env=env,
                    timeout=self.requirements['calendar_time'] * 2
                )
                
                duration = time.time() - start_time
                
                # Determine status
                if result.returncode != 0:
                    status = 'fail'
                    error = f"Command failed: {result.stderr}"
                elif duration > self.requirements['calendar_time']:
                    status = 'fail'
                    error = f"Exceeded {self.requirements['calendar_time']}s requirement"
                elif duration > self.requirements['calendar_time'] * 0.8:
                    status = 'warn' 
                    error = None
                else:
                    status = 'pass'
                    error = None
                
                results.append(BenchmarkResult(
                    name=test['name'],
                    category='calendar_operations',
                    duration_seconds=duration,
                    status=status,
                    requirement_seconds=self.requirements['calendar_time'],
                    details={
                        'description': test['description'],
                        'command': ' '.join(cmd),
                        'return_code': result.returncode,
                        'test_mode': self.test_mode
                    },
                    error=error
                ))
                
            except subprocess.TimeoutExpired:
                results.append(BenchmarkResult(
                    name=test['name'],
                    category='calendar_operations',
                    duration_seconds=self.requirements['calendar_time'] * 2,
                    status='fail',
                    requirement_seconds=self.requirements['calendar_time'],
                    details={'description': test['description']},
                    error='Calendar operation timed out'
                ))
            except Exception as e:
                results.append(BenchmarkResult(
                    name=test['name'],
                    category='calendar_operations',
                    duration_seconds=0.0,
                    status='fail',
                    requirement_seconds=self.requirements['calendar_time'],
                    details={'description': test['description']},
                    error=str(e)
                ))
        
        return results
    
    def _benchmark_statistics_generation(self) -> List[BenchmarkResult]:
        """Benchmark Agent B statistics generation"""
        results = []
        
        stats_tests = [
            {
                'name': 'daily_summary_simple',
                'args': ['--date', '2025-08-19'],
                'description': 'Generate daily summary'
            },
            {
                'name': 'daily_summary_person_focus',
                'args': ['--person', 'alice@example.com', '--date', '2025-08-19'],
                'description': 'Generate person-focused daily summary'
            },
            {
                'name': 'weekly_summary',
                'args': ['--period', 'week'],
                'description': 'Generate weekly summary'
            },
            {
                'name': 'statistics_detailed',
                'args': ['--date', '2025-08-19', '--detailed'],
                'description': 'Generate detailed statistics'
            }
        ]
        
        for test in stats_tests:
            try:
                start_time = time.time()
                
                cmd = ['python3', 'tools/daily_summary.py'] + test['args'] + ['--format', 'json']
                env = os.environ.copy()
                if self.test_mode:
                    env['AICOS_TEST_MODE'] = 'true'
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    cwd=self.project_root,
                    env=env,
                    timeout=self.requirements['statistics_time'] * 2
                )
                
                duration = time.time() - start_time
                
                # Determine status
                if result.returncode != 0:
                    status = 'fail'
                    error = f"Command failed: {result.stderr}"
                elif duration > self.requirements['statistics_time']:
                    status = 'fail'
                    error = f"Exceeded {self.requirements['statistics_time']}s requirement"
                elif duration > self.requirements['statistics_time'] * 0.8:
                    status = 'warn'
                    error = None
                else:
                    status = 'pass'
                    error = None
                
                results.append(BenchmarkResult(
                    name=test['name'],
                    category='statistics_generation',
                    duration_seconds=duration,
                    status=status,
                    requirement_seconds=self.requirements['statistics_time'],
                    details={
                        'description': test['description'],
                        'command': ' '.join(cmd),
                        'return_code': result.returncode,
                        'test_mode': self.test_mode
                    },
                    error=error
                ))
                
            except subprocess.TimeoutExpired:
                results.append(BenchmarkResult(
                    name=test['name'],
                    category='statistics_generation',
                    duration_seconds=self.requirements['statistics_time'] * 2,
                    status='fail',
                    requirement_seconds=self.requirements['statistics_time'],
                    details={'description': test['description']},
                    error='Statistics generation timed out'
                ))
            except Exception as e:
                results.append(BenchmarkResult(
                    name=test['name'],
                    category='statistics_generation',
                    duration_seconds=0.0,
                    status='fail',
                    requirement_seconds=self.requirements['statistics_time'],
                    details={'description': test['description']},
                    error=str(e)
                ))
        
        return results
    
    def _benchmark_database_operations(self) -> List[BenchmarkResult]:
        """Benchmark database and migration operations"""
        results = []
        
        try:
            # Test migration system performance
            if self.db_path.exists():
                # Backup original database
                backup_path = self.db_path.with_suffix('.benchmark_backup')
                if backup_path.exists():
                    backup_path.unlink()
                
                import shutil
                shutil.copy2(self.db_path, backup_path)
                
                try:
                    # Test migration discovery
                    start_time = time.time()
                    manager = create_migration_manager(str(self.db_path))
                    migrations = manager.discover_migrations()
                    discovery_duration = time.time() - start_time
                    
                    results.append(BenchmarkResult(
                        name='migration_discovery',
                        category='database_operations',
                        duration_seconds=discovery_duration,
                        status='pass' if discovery_duration < 1.0 else 'warn',
                        requirement_seconds=1.0,
                        details={
                            'description': 'Migration file discovery',
                            'migrations_found': len(migrations)
                        }
                    ))
                    
                    # Test schema validation
                    start_time = time.time()
                    validator = create_schema_validator(str(self.db_path))
                    validation_report = validator.validate_complete_schema()
                    validation_duration = time.time() - start_time
                    
                    results.append(BenchmarkResult(
                        name='schema_validation',
                        category='database_operations',
                        duration_seconds=validation_duration,
                        status='pass' if validation_duration < 5.0 else 'warn',
                        requirement_seconds=5.0,
                        details={
                            'description': 'Complete schema validation',
                            'validation_checks': validation_report.performance_metrics.get('total_checks', 0),
                            'overall_schema_status': validation_report.overall_status
                        }
                    ))
                    
                finally:
                    # Restore original database
                    if backup_path.exists():
                        shutil.copy2(backup_path, self.db_path)
                        backup_path.unlink()
            
            # Test basic database query performance
            if self.db_path.exists():
                start_time = time.time()
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    # Test basic queries
                    cursor.execute("SELECT COUNT(*) FROM sqlite_master")
                    cursor.execute("SELECT COUNT(*) FROM messages LIMIT 1000")
                    cursor.execute("SELECT source, COUNT(*) FROM messages GROUP BY source LIMIT 10")
                
                query_duration = time.time() - start_time
                
                results.append(BenchmarkResult(
                    name='basic_database_queries',
                    category='database_operations',
                    duration_seconds=query_duration,
                    status='pass' if query_duration < 0.5 else 'warn',
                    requirement_seconds=0.5,
                    details={
                        'description': 'Basic database query performance'
                    }
                ))
        
        except Exception as e:
            results.append(BenchmarkResult(
                name='database_operations_error',
                category='database_operations',
                duration_seconds=0.0,
                status='fail',
                requirement_seconds=0.0,
                details={'description': 'Database operations benchmark'},
                error=str(e)
            ))
        
        return results
    
    def _benchmark_cli_responsiveness(self) -> List[BenchmarkResult]:
        """Benchmark CLI tool responsiveness"""
        results = []
        
        cli_tests = [
            {
                'name': 'query_facts_help',
                'cmd': ['python3', 'tools/query_facts.py', '--help'],
                'description': 'Query facts tool help response'
            },
            {
                'name': 'daily_summary_help',
                'cmd': ['python3', 'tools/daily_summary.py', '--help'],
                'description': 'Daily summary tool help response'
            },
            {
                'name': 'query_facts_startup',
                'cmd': ['python3', 'tools/query_facts.py', 'time', 'today', '--format', 'json'],
                'description': 'Query facts tool startup and execution'
            }
        ]
        
        for test in cli_tests:
            try:
                start_time = time.time()
                
                env = os.environ.copy()
                if self.test_mode:
                    env['AICOS_TEST_MODE'] = 'true'
                
                result = subprocess.run(
                    test['cmd'],
                    capture_output=True,
                    text=True,
                    cwd=self.project_root,
                    env=env,
                    timeout=self.requirements['cli_response_time'] * 2
                )
                
                duration = time.time() - start_time
                
                # Determine status
                if result.returncode != 0:
                    status = 'fail'
                    error = f"Command failed: {result.stderr}"
                elif duration > self.requirements['cli_response_time']:
                    status = 'warn'  # CLI responsiveness is less critical
                    error = f"Slower than {self.requirements['cli_response_time']}s preference"
                else:
                    status = 'pass'
                    error = None
                
                results.append(BenchmarkResult(
                    name=test['name'],
                    category='cli_responsiveness',
                    duration_seconds=duration,
                    status=status,
                    requirement_seconds=self.requirements['cli_response_time'],
                    details={
                        'description': test['description'],
                        'command': ' '.join(test['cmd']),
                        'return_code': result.returncode,
                        'test_mode': self.test_mode
                    },
                    error=error
                ))
                
            except subprocess.TimeoutExpired:
                results.append(BenchmarkResult(
                    name=test['name'],
                    category='cli_responsiveness',
                    duration_seconds=self.requirements['cli_response_time'] * 2,
                    status='warn',
                    requirement_seconds=self.requirements['cli_response_time'],
                    details={'description': test['description']},
                    error='CLI response timed out'
                ))
            except Exception as e:
                results.append(BenchmarkResult(
                    name=test['name'],
                    category='cli_responsiveness',
                    duration_seconds=0.0,
                    status='fail',
                    requirement_seconds=self.requirements['cli_response_time'],
                    details={'description': test['description']},
                    error=str(e)
                ))
        
        return results
    
    def _generate_summary(self, results: List[BenchmarkResult]) -> Dict[str, Any]:
        """Generate benchmark summary statistics"""
        total_tests = len(results)
        passed_tests = len([r for r in results if r.status == 'pass'])
        warned_tests = len([r for r in results if r.status == 'warn'])
        failed_tests = len([r for r in results if r.status == 'fail'])
        
        # Calculate average performance by category
        category_performance = {}
        for result in results:
            if result.category not in category_performance:
                category_performance[result.category] = []
            if result.duration_seconds > 0:
                category_performance[result.category].append(result.duration_seconds)
        
        category_averages = {}
        for category, durations in category_performance.items():
            if durations:
                category_averages[category] = {
                    'average_seconds': sum(durations) / len(durations),
                    'max_seconds': max(durations),
                    'min_seconds': min(durations),
                    'test_count': len(durations)
                }
        
        return {
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'warned_tests': warned_tests,
            'failed_tests': failed_tests,
            'success_rate': (passed_tests / total_tests * 100) if total_tests > 0 else 0,
            'category_performance': category_averages,
            'requirements': self.requirements
        }
    
    def _determine_overall_status(self, results: List[BenchmarkResult]) -> str:
        """Determine overall benchmark status"""
        failed_critical = any(
            r.status == 'fail' and r.category in ['query_engine', 'database_operations']
            for r in results
        )
        
        if failed_critical:
            return 'fail'
        
        failed_any = any(r.status == 'fail' for r in results)
        warned_any = any(r.status == 'warn' for r in results)
        
        if failed_any:
            return 'degraded'
        elif warned_any:
            return 'degraded'
        else:
            return 'pass'
    
    def _get_environment_info(self) -> Dict[str, str]:
        """Get environment information"""
        return {
            'python_version': sys.version,
            'platform': sys.platform,
            'test_mode': str(self.test_mode),
            'database_path': str(self.db_path),
            'database_exists': str(self.db_path.exists())
        }


def format_benchmark_report(report: BenchmarkReport, verbose: bool = False) -> str:
    """Format benchmark report for CLI display"""
    lines = []
    
    lines.append("Phase 1 Performance Benchmark Report")
    lines.append(f"Timestamp: {report.timestamp}")
    lines.append(f"Overall Status: {report.overall_status.upper()}")
    lines.append("")
    
    # Summary statistics
    summary = report.summary
    lines.append(f"Test Results: {summary['passed_tests']} passed, {summary['warned_tests']} warned, {summary['failed_tests']} failed")
    lines.append(f"Success Rate: {summary['success_rate']:.1f}%")
    lines.append("")
    
    # Category performance
    if 'category_performance' in summary:
        lines.append("Performance by Category:")
        for category, perf in summary['category_performance'].items():
            lines.append(f"  {category}: avg {perf['average_seconds']:.3f}s, max {perf['max_seconds']:.3f}s ({perf['test_count']} tests)")
        lines.append("")
    
    # Group results by status
    passed = [r for r in report.results if r.status == 'pass']
    warned = [r for r in report.results if r.status == 'warn']
    failed = [r for r in report.results if r.status == 'fail']
    
    if passed and verbose:
        lines.append(f"✅ PASSED ({len(passed)} tests)")
        for result in passed:
            lines.append(f"  • {result.name}: {result.duration_seconds:.3f}s (req: <{result.requirement_seconds}s)")
        lines.append("")
    
    if warned:
        lines.append(f"⚠️  WARNINGS ({len(warned)} tests)")
        for result in warned:
            lines.append(f"  • {result.name}: {result.duration_seconds:.3f}s (req: <{result.requirement_seconds}s)")
            if result.error:
                lines.append(f"    {result.error}")
        lines.append("")
    
    if failed:
        lines.append(f"❌ FAILED ({len(failed)} tests)")
        for result in failed:
            lines.append(f"  • {result.name}: {result.duration_seconds:.3f}s (req: <{result.requirement_seconds}s)")
            if result.error:
                lines.append(f"    {result.error}")
        lines.append("")
    
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='Phase 1 Performance Benchmark Suite')
    parser.add_argument('--format', choices=['text', 'json'], default='text',
                      help='Output format')
    parser.add_argument('--verbose', '-v', action='store_true',
                      help='Show detailed results including passed tests')
    parser.add_argument('--queries-only', action='store_true',
                      help='Run only query engine benchmarks')
    parser.add_argument('--db-path', default='data/search.db',
                      help='Database path for benchmarking')
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format='%(levelname)s: %(message)s'
    )
    
    # Create benchmark suite
    benchmark = PerformanceBenchmark(args.db_path)
    
    # Run benchmarks
    if args.queries_only:
        # Run limited benchmark set
        results = []
        results.extend(benchmark._benchmark_query_operations())
        
        report = BenchmarkReport(
            timestamp=datetime.now().isoformat(),
            environment=benchmark._get_environment_info(),
            summary=benchmark._generate_summary(results),
            results=results,
            overall_status=benchmark._determine_overall_status(results)
        )
    else:
        # Run full benchmark suite
        report = benchmark.run_full_benchmark()
    
    # Output results
    if args.format == 'json':
        print(json.dumps(asdict(report), indent=2))
    else:
        print(format_benchmark_report(report, args.verbose))
    
    # Exit with appropriate code
    if report.overall_status == 'fail':
        sys.exit(1)
    elif report.overall_status == 'degraded':
        sys.exit(2)
    else:
        sys.exit(0)


if __name__ == '__main__':
    main()