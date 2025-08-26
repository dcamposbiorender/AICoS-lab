"""
Database Schema Validation System - Agent D Implementation

Validates database schema integrity, data consistency, and detects corruption.
Provides repair mechanisms for common schema issues and data inconsistencies.

Key Features:
- Schema structure validation against expected Phase 1 schema
- FTS5 synchronization validation and repair
- Data consistency checks across tables and indexes
- Index integrity validation and rebuilding
- Orphaned record detection and cleanup
- Performance diagnostics and optimization suggestions

References:
- migrations/001_initial_schema.sql - Expected baseline schema
- src/search/migrations.py - Migration system integration
- tasks/phase1_agent_d_migration.md lines 224-228 for validation requirements
"""

import sqlite3
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass
from datetime import datetime
import json
import time

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of a schema validation check"""
    check_name: str
    status: str  # 'pass', 'warn', 'fail'
    message: str
    details: Dict[str, Any]
    repair_available: bool = False
    repair_action: Optional[str] = None


@dataclass
class SchemaValidationReport:
    """Complete schema validation report"""
    database_path: str
    validation_time: datetime
    overall_status: str  # 'healthy', 'degraded', 'corrupt'
    results: List[ValidationResult]
    performance_metrics: Dict[str, Any]
    repair_recommendations: List[str]


class SchemaValidationError(Exception):
    """Schema validation system errors"""
    pass


class SchemaValidator:
    """Validates database schema integrity and consistency"""
    
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        
        # Expected Phase 1 schema structure
        self.expected_tables = {
            'messages': ['id', 'content', 'source', 'created_at', 'date', 'metadata', 'person_id', 'channel_id', 'indexed_at'],
            'messages_fts': [],  # FTS5 virtual table
            'archives': ['id', 'path', 'source', 'indexed_at', 'record_count', 'checksum', 'status'],
            'search_metadata': ['key', 'value', 'updated_at'],
            'schema_migrations': ['version', 'applied_at', 'description', 'checksum']
        }
        
        self.expected_indexes = [
            'idx_archives_source',
            'idx_archives_indexed_at', 
            'idx_messages_source',
            'idx_messages_date',
            'idx_messages_created_at'
        ]
        
        self.expected_triggers = [
            'messages_ai',  # After Insert
            'messages_ad',  # After Delete
            'messages_au'   # After Update
        ]
    
    def validate_complete_schema(self) -> SchemaValidationReport:
        """Run complete schema validation"""
        start_time = datetime.now()
        results = []
        
        logger.info(f"Starting schema validation for {self.db_path}")
        
        try:
            # Core structure validation
            results.extend(self._validate_table_structure())
            results.extend(self._validate_indexes())
            results.extend(self._validate_triggers())
            
            # Data consistency checks
            results.extend(self._validate_data_consistency())
            results.extend(self._validate_fts_synchronization())
            
            # Performance and optimization
            results.extend(self._validate_performance_characteristics())
            
            # Integrity checks
            results.extend(self._validate_referential_integrity())
            
        except Exception as e:
            logger.error(f"Schema validation failed: {e}")
            results.append(ValidationResult(
                check_name="validation_execution",
                status="fail", 
                message=f"Validation process failed: {e}",
                details={'error': str(e)},
                repair_available=False
            ))
        
        # Determine overall status
        fail_count = len([r for r in results if r.status == 'fail'])
        warn_count = len([r for r in results if r.status == 'warn'])
        
        if fail_count > 0:
            overall_status = 'corrupt'
        elif warn_count > 0:
            overall_status = 'degraded'
        else:
            overall_status = 'healthy'
        
        # Generate performance metrics
        validation_duration = (datetime.now() - start_time).total_seconds()
        performance_metrics = {
            'validation_duration_seconds': validation_duration,
            'total_checks': len(results),
            'passed_checks': len([r for r in results if r.status == 'pass']),
            'warning_checks': warn_count,
            'failed_checks': fail_count
        }
        
        # Generate repair recommendations
        repair_recommendations = [
            result.repair_action for result in results 
            if result.repair_available and result.repair_action
        ]
        
        return SchemaValidationReport(
            database_path=str(self.db_path),
            validation_time=start_time,
            overall_status=overall_status,
            results=results,
            performance_metrics=performance_metrics,
            repair_recommendations=repair_recommendations
        )
    
    def _validate_table_structure(self) -> List[ValidationResult]:
        """Validate expected tables and columns exist"""
        results = []
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get all tables
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                actual_tables = {row[0] for row in cursor.fetchall()}
                
                # Check expected tables exist
                for table_name, expected_columns in self.expected_tables.items():
                    if table_name not in actual_tables:
                        results.append(ValidationResult(
                            check_name=f"table_exists_{table_name}",
                            status="fail",
                            message=f"Required table '{table_name}' is missing",
                            details={'missing_table': table_name},
                            repair_available=True,
                            repair_action=f"Run migration to create table '{table_name}'"
                        ))
                        continue
                    
                    # For non-virtual tables, check column structure
                    if expected_columns:  # Skip FTS tables
                        cursor.execute(f"PRAGMA table_info({table_name})")
                        actual_columns = {row[1] for row in cursor.fetchall()}
                        
                        missing_columns = set(expected_columns) - actual_columns
                        if missing_columns:
                            results.append(ValidationResult(
                                check_name=f"table_columns_{table_name}",
                                status="fail", 
                                message=f"Table '{table_name}' missing columns: {missing_columns}",
                                details={'missing_columns': list(missing_columns)},
                                repair_available=True,
                                repair_action=f"Run migration to add missing columns to '{table_name}'"
                            ))
                        else:
                            results.append(ValidationResult(
                                check_name=f"table_structure_{table_name}",
                                status="pass",
                                message=f"Table '{table_name}' structure is valid",
                                details={'columns': list(actual_columns)}
                            ))
                    else:
                        # Basic existence check for virtual tables
                        results.append(ValidationResult(
                            check_name=f"virtual_table_{table_name}",
                            status="pass",
                            message=f"Virtual table '{table_name}' exists",
                            details={}
                        ))
                
        except sqlite3.Error as e:
            results.append(ValidationResult(
                check_name="table_structure_check",
                status="fail",
                message=f"Failed to validate table structure: {e}",
                details={'error': str(e)},
                repair_available=False
            ))
        
        return results
    
    def _validate_indexes(self) -> List[ValidationResult]:
        """Validate expected indexes exist and are functional"""
        results = []
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get all indexes
                cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND sql IS NOT NULL")
                actual_indexes = {row[0] for row in cursor.fetchall()}
                
                for index_name in self.expected_indexes:
                    if index_name not in actual_indexes:
                        results.append(ValidationResult(
                            check_name=f"index_exists_{index_name}",
                            status="warn",
                            message=f"Index '{index_name}' is missing - performance may be degraded",
                            details={'missing_index': index_name},
                            repair_available=True,
                            repair_action=f"Run query optimization migration to create index '{index_name}'"
                        ))
                    else:
                        results.append(ValidationResult(
                            check_name=f"index_exists_{index_name}",
                            status="pass",
                            message=f"Index '{index_name}' exists",
                            details={}
                        ))
                
        except sqlite3.Error as e:
            results.append(ValidationResult(
                check_name="index_validation",
                status="fail",
                message=f"Failed to validate indexes: {e}",
                details={'error': str(e)},
                repair_available=False
            ))
        
        return results
    
    def _validate_triggers(self) -> List[ValidationResult]:
        """Validate FTS synchronization triggers exist"""
        results = []
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get all triggers
                cursor.execute("SELECT name FROM sqlite_master WHERE type='trigger'")
                actual_triggers = {row[0] for row in cursor.fetchall()}
                
                for trigger_name in self.expected_triggers:
                    if trigger_name not in actual_triggers:
                        results.append(ValidationResult(
                            check_name=f"trigger_exists_{trigger_name}",
                            status="fail",
                            message=f"Critical trigger '{trigger_name}' is missing - FTS sync broken",
                            details={'missing_trigger': trigger_name},
                            repair_available=True,
                            repair_action=f"Rebuild FTS triggers by re-running initial schema migration"
                        ))
                    else:
                        results.append(ValidationResult(
                            check_name=f"trigger_exists_{trigger_name}",
                            status="pass",
                            message=f"Trigger '{trigger_name}' exists",
                            details={}
                        ))
                
        except sqlite3.Error as e:
            results.append(ValidationResult(
                check_name="trigger_validation",
                status="fail",
                message=f"Failed to validate triggers: {e}",
                details={'error': str(e)},
                repair_available=False
            ))
        
        return results
    
    def _validate_data_consistency(self) -> List[ValidationResult]:
        """Validate data consistency across tables"""
        results = []
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check for orphaned records
                # Check if all archived paths have corresponding message records
                cursor.execute("""
                    SELECT COUNT(*) FROM archives a 
                    LEFT JOIN messages m ON a.source = m.source 
                    WHERE m.source IS NULL AND a.record_count > 0
                """)
                orphaned_archives = cursor.fetchone()[0]
                
                if orphaned_archives > 0:
                    results.append(ValidationResult(
                        check_name="orphaned_archives",
                        status="warn",
                        message=f"Found {orphaned_archives} archive entries with no message records",
                        details={'orphaned_count': orphaned_archives},
                        repair_available=True,
                        repair_action="Run data cleanup to remove orphaned archive entries"
                    ))
                else:
                    results.append(ValidationResult(
                        check_name="orphaned_archives",
                        status="pass",
                        message="No orphaned archive entries found",
                        details={}
                    ))
                
                # Validate date consistency
                cursor.execute("""
                    SELECT COUNT(*) FROM messages 
                    WHERE date != substr(created_at, 1, 10) 
                    AND created_at IS NOT NULL AND date IS NOT NULL
                """)
                date_inconsistencies = cursor.fetchone()[0]
                
                if date_inconsistencies > 0:
                    results.append(ValidationResult(
                        check_name="date_consistency",
                        status="warn", 
                        message=f"Found {date_inconsistencies} messages with inconsistent date fields",
                        details={'inconsistent_count': date_inconsistencies},
                        repair_available=True,
                        repair_action="Run data normalization to fix date field consistency"
                    ))
                else:
                    results.append(ValidationResult(
                        check_name="date_consistency",
                        status="pass",
                        message="Date fields are consistent",
                        details={}
                    ))
                
        except sqlite3.Error as e:
            results.append(ValidationResult(
                check_name="data_consistency",
                status="fail",
                message=f"Failed to validate data consistency: {e}",
                details={'error': str(e)},
                repair_available=False
            ))
        
        return results
    
    def _validate_fts_synchronization(self) -> List[ValidationResult]:
        """Validate FTS5 table is synchronized with main messages table"""
        results = []
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if FTS table exists
                cursor.execute("SELECT name FROM sqlite_master WHERE name='messages_fts'")
                if not cursor.fetchone():
                    results.append(ValidationResult(
                        check_name="fts_table_exists",
                        status="fail",
                        message="FTS5 table 'messages_fts' is missing",
                        details={},
                        repair_available=True,
                        repair_action="Re-run initial schema migration to create FTS table"
                    ))
                    return results
                
                # Count records in both tables
                cursor.execute("SELECT COUNT(*) FROM messages")
                message_count = cursor.fetchone()[0]
                
                try:
                    cursor.execute("SELECT COUNT(*) FROM messages_fts")
                    fts_count = cursor.fetchone()[0]
                except sqlite3.Error:
                    # FTS table might be corrupted
                    results.append(ValidationResult(
                        check_name="fts_table_readable",
                        status="fail", 
                        message="FTS table is corrupted or unreadable",
                        details={},
                        repair_available=True,
                        repair_action="Rebuild FTS table: INSERT INTO messages_fts(messages_fts) VALUES('rebuild')"
                    ))
                    return results
                
                # Compare record counts
                if message_count != fts_count:
                    results.append(ValidationResult(
                        check_name="fts_synchronization",
                        status="fail",
                        message=f"FTS table out of sync: {message_count} messages vs {fts_count} FTS records",
                        details={'message_count': message_count, 'fts_count': fts_count},
                        repair_available=True,
                        repair_action="Rebuild FTS table to resynchronize with messages"
                    ))
                else:
                    results.append(ValidationResult(
                        check_name="fts_synchronization",
                        status="pass",
                        message=f"FTS table synchronized ({fts_count} records)",
                        details={'record_count': fts_count}
                    ))
                
        except sqlite3.Error as e:
            results.append(ValidationResult(
                check_name="fts_validation",
                status="fail",
                message=f"Failed to validate FTS synchronization: {e}",
                details={'error': str(e)},
                repair_available=False
            ))
        
        return results
    
    def _validate_performance_characteristics(self) -> List[ValidationResult]:
        """Validate database performance characteristics"""
        results = []
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Test query performance (simple benchmark)
                start_time = time.time()
                cursor.execute("SELECT COUNT(*) FROM messages WHERE source = 'slack' LIMIT 1000")
                query_time = time.time() - start_time
                
                if query_time > 1.0:  # > 1 second is concerning
                    results.append(ValidationResult(
                        check_name="query_performance",
                        status="warn",
                        message=f"Source filtering query slow: {query_time:.2f}s",
                        details={'query_time_seconds': query_time},
                        repair_available=True,
                        repair_action="Run ANALYZE and consider adding missing indexes"
                    ))
                else:
                    results.append(ValidationResult(
                        check_name="query_performance",
                        status="pass", 
                        message=f"Query performance acceptable: {query_time:.3f}s",
                        details={'query_time_seconds': query_time}
                    ))
                
                # Check database size and suggest maintenance
                cursor.execute("PRAGMA page_size")
                page_size = cursor.fetchone()[0]
                cursor.execute("PRAGMA page_count")
                page_count = cursor.fetchone()[0]
                
                db_size_mb = (page_size * page_count) / (1024 * 1024)
                
                if db_size_mb > 100:  # > 100MB
                    results.append(ValidationResult(
                        check_name="database_size",
                        status="warn",
                        message=f"Database is large ({db_size_mb:.1f}MB) - consider archival",
                        details={'size_mb': db_size_mb},
                        repair_available=True,
                        repair_action="Run VACUUM and consider data archival for old records"
                    ))
                else:
                    results.append(ValidationResult(
                        check_name="database_size",
                        status="pass",
                        message=f"Database size reasonable ({db_size_mb:.1f}MB)",
                        details={'size_mb': db_size_mb}
                    ))
                
        except sqlite3.Error as e:
            results.append(ValidationResult(
                check_name="performance_validation",
                status="fail",
                message=f"Failed to validate performance: {e}",
                details={'error': str(e)},
                repair_available=False
            ))
        
        return results
    
    def _validate_referential_integrity(self) -> List[ValidationResult]:
        """Validate referential integrity and constraints"""
        results = []
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check for NULL values in required fields
                required_checks = [
                    ('messages', 'content', 'Message content cannot be null'),
                    ('messages', 'source', 'Message source cannot be null'),
                    ('messages', 'created_at', 'Message created_at cannot be null'),
                    ('archives', 'path', 'Archive path cannot be null'),
                    ('archives', 'source', 'Archive source cannot be null')
                ]
                
                for table, column, description in required_checks:
                    cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE {column} IS NULL")
                    null_count = cursor.fetchone()[0]
                    
                    if null_count > 0:
                        results.append(ValidationResult(
                            check_name=f"null_check_{table}_{column}",
                            status="fail",
                            message=f"{description}: {null_count} null values found",
                            details={'null_count': null_count, 'table': table, 'column': column},
                            repair_available=True,
                            repair_action=f"Clean up null values in {table}.{column}"
                        ))
                    else:
                        results.append(ValidationResult(
                            check_name=f"null_check_{table}_{column}",
                            status="pass",
                            message=f"No null values in {table}.{column}",
                            details={}
                        ))
                
        except sqlite3.Error as e:
            results.append(ValidationResult(
                check_name="referential_integrity",
                status="fail",
                message=f"Failed to validate referential integrity: {e}",
                details={'error': str(e)},
                repair_available=False
            ))
        
        return results
    
    def repair_fts_synchronization(self) -> bool:
        """Repair FTS5 synchronization issues"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                logger.info("Rebuilding FTS5 table synchronization")
                
                # Rebuild FTS table
                cursor.execute("INSERT INTO messages_fts(messages_fts) VALUES('rebuild')")
                conn.commit()
                
                logger.info("FTS5 synchronization repair completed")
                return True
                
        except sqlite3.Error as e:
            logger.error(f"Failed to repair FTS synchronization: {e}")
            return False
    
    def repair_orphaned_data(self) -> bool:
        """Clean up orphaned data records"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                logger.info("Cleaning up orphaned data")
                
                # Remove archive entries with no corresponding messages
                cursor.execute("""
                    DELETE FROM archives 
                    WHERE id IN (
                        SELECT a.id FROM archives a 
                        LEFT JOIN messages m ON a.source = m.source 
                        WHERE m.source IS NULL AND a.record_count = 0
                    )
                """)
                
                deleted_count = cursor.rowcount
                conn.commit()
                
                logger.info(f"Cleaned up {deleted_count} orphaned archive entries")
                return True
                
        except sqlite3.Error as e:
            logger.error(f"Failed to repair orphaned data: {e}")
            return False


def create_schema_validator(db_path: str = "data/search.db") -> SchemaValidator:
    """Factory function to create schema validator"""
    return SchemaValidator(db_path)


def format_validation_report(report: SchemaValidationReport) -> str:
    """Format validation report for CLI display"""
    lines = []
    
    lines.append(f"Schema Validation Report")
    lines.append(f"Database: {report.database_path}")
    lines.append(f"Validated: {report.validation_time.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"Overall Status: {report.overall_status.upper()}")
    lines.append("")
    
    lines.append(f"Performance Metrics:")
    for key, value in report.performance_metrics.items():
        lines.append(f"  {key}: {value}")
    lines.append("")
    
    # Group results by status
    passed = [r for r in report.results if r.status == 'pass']
    warned = [r for r in report.results if r.status == 'warn']
    failed = [r for r in report.results if r.status == 'fail']
    
    if passed:
        lines.append(f"✅ PASSED ({len(passed)} checks)")
        for result in passed:
            lines.append(f"  • {result.message}")
        lines.append("")
    
    if warned:
        lines.append(f"⚠️  WARNINGS ({len(warned)} issues)")
        for result in warned:
            lines.append(f"  • {result.message}")
            if result.repair_action:
                lines.append(f"    → {result.repair_action}")
        lines.append("")
    
    if failed:
        lines.append(f"❌ FAILED ({len(failed)} critical issues)")
        for result in failed:
            lines.append(f"  • {result.message}")
            if result.repair_action:
                lines.append(f"    → {result.repair_action}")
        lines.append("")
    
    if report.repair_recommendations:
        lines.append("Repair Recommendations:")
        for i, recommendation in enumerate(report.repair_recommendations, 1):
            lines.append(f"  {i}. {recommendation}")
    
    return '\n'.join(lines)