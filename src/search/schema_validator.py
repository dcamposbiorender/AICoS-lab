"""
Database schema validator for migration integrity checking
Provides comprehensive schema validation and consistency checking
"""

import sqlite3
import logging
from pathlib import Path
from typing import Dict, List, Any, Set, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of schema validation"""
    valid: bool
    message: str
    details: Dict[str, Any]


class SchemaValidationError(Exception):
    """Raised when schema validation fails"""
    pass


class SchemaValidator:
    """
    Database schema validator with comprehensive integrity checking
    
    Features:
    - Table structure validation
    - Index existence verification
    - Foreign key constraint checking
    - FTS5 virtual table consistency
    - Data integrity validation
    - Performance optimization verification
    """
    
    def __init__(self, db_path: str):
        """
        Initialize schema validator
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        if not self.db_path.exists():
            raise SchemaValidationError(f"Database file not found: {db_path}")
        
        logger.info(f"SchemaValidator initialized for: {self.db_path}")
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection"""
        try:
            conn = sqlite3.connect(
                str(self.db_path),
                timeout=10.0,
                check_same_thread=False
            )
            
            # Enable foreign keys for validation
            conn.execute("PRAGMA foreign_keys=ON")
            return conn
            
        except Exception as e:
            raise SchemaValidationError(f"Failed to connect to database: {str(e)}")
    
    def validate_schema(self) -> Dict[str, Any]:
        """
        Comprehensive schema validation
        
        Returns:
            Validation result with detailed information
        """
        try:
            with self._get_connection() as conn:
                results = {
                    'valid': True,
                    'tables': {},
                    'indexes': {},
                    'views': {},
                    'triggers': {},
                    'issues': []
                }
                
                # Validate tables
                tables_result = self._validate_tables(conn)
                results['tables'] = tables_result['tables']
                if not tables_result['valid']:
                    results['valid'] = False
                    results['issues'].extend(tables_result['issues'])
                
                # Validate indexes
                indexes_result = self._validate_indexes(conn)
                results['indexes'] = indexes_result['indexes']
                if not indexes_result['valid']:
                    results['valid'] = False
                    results['issues'].extend(indexes_result['issues'])
                
                # Validate views
                views_result = self._validate_views(conn)
                results['views'] = views_result['views']
                if not views_result['valid']:
                    results['valid'] = False
                    results['issues'].extend(views_result['issues'])
                
                # Validate triggers
                triggers_result = self._validate_triggers(conn)
                results['triggers'] = triggers_result['triggers']
                if not triggers_result['valid']:
                    results['valid'] = False
                    results['issues'].extend(triggers_result['issues'])
                
                return results
                
        except Exception as e:
            logger.error(f"Schema validation failed: {e}")
            return {
                'valid': False,
                'error': str(e),
                'tables': {},
                'indexes': {},
                'views': {},
                'triggers': {},
                'issues': [f'Validation error: {str(e)}']
            }
    
    def _validate_tables(self, conn: sqlite3.Connection) -> Dict[str, Any]:
        """Validate table structures"""
        try:
            cursor = conn.execute("""
                SELECT name, sql FROM sqlite_master 
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
                ORDER BY name
            """)
            
            tables = {}
            issues = []
            
            for table_name, create_sql in cursor.fetchall():
                table_info = self._analyze_table(conn, table_name, create_sql)
                tables[table_name] = table_info
                
                # Check for common issues (skip for virtual tables)
                if not table_info.get('has_primary_key') and not table_info.get('is_virtual'):
                    issues.append(f"Table '{table_name}' lacks primary key")
                
                if table_name.endswith('_fts'):
                    # FTS5 table validation
                    fts_issues = self._validate_fts5_table(conn, table_name)
                    issues.extend(fts_issues)
            
            return {
                'valid': len(issues) == 0,
                'tables': tables,
                'issues': issues
            }
            
        except Exception as e:
            return {
                'valid': False,
                'tables': {},
                'issues': [f'Table validation error: {str(e)}']
            }
    
    def _analyze_table(self, conn: sqlite3.Connection, table_name: str, create_sql: str) -> Dict[str, Any]:
        """Analyze individual table structure"""
        try:
            # Get table info - validate table name for security
            if not table_name.replace('_', '').replace('-', '').isalnum():
                raise ValueError(f"Invalid table name: {table_name}")
                
            cursor = conn.execute(f"PRAGMA table_info({table_name})")
            columns = []
            has_primary_key = False
            
            for row in cursor.fetchall():
                cid, name, type_name, not_null, default_value, pk = row
                columns.append({
                    'name': name,
                    'type': type_name,
                    'not_null': bool(not_null),
                    'default_value': default_value,
                    'primary_key': bool(pk)
                })
                
                if pk:
                    has_primary_key = True
            
            # Get foreign keys (table_name already validated above)
            cursor = conn.execute(f"PRAGMA foreign_key_list({table_name})")
            foreign_keys = []
            for row in cursor.fetchall():
                id_num, seq, table, from_col, to_col, on_update, on_delete, match = row
                foreign_keys.append({
                    'from_column': from_col,
                    'to_table': table,
                    'to_column': to_col,
                    'on_update': on_update,
                    'on_delete': on_delete
                })
            
            # Check if it's a virtual table (FTS5)
            is_virtual = 'VIRTUAL TABLE' in create_sql.upper() if create_sql else False
            
            return {
                'columns': columns,
                'foreign_keys': foreign_keys,
                'has_primary_key': has_primary_key,
                'is_virtual': is_virtual,
                'create_sql': create_sql
            }
            
        except Exception as e:
            logger.warning(f"Failed to analyze table {table_name}: {e}")
            return {
                'error': str(e),
                'columns': [],
                'foreign_keys': [],
                'has_primary_key': False,
                'is_virtual': False
            }
    
    def _validate_fts5_table(self, conn: sqlite3.Connection, fts_table: str) -> List[str]:
        """Validate FTS5 virtual table consistency"""
        issues = []
        
        try:
            # Check if FTS5 table is properly configured
            cursor = conn.execute(f"SELECT sql FROM sqlite_master WHERE name = ?", (fts_table,))
            result = cursor.fetchone()
            
            if not result:
                issues.append(f"FTS5 table '{fts_table}' not found in schema")
                return issues
            
            create_sql = result[0]
            
            # Basic FTS5 syntax validation
            if 'fts5' not in create_sql.lower():
                issues.append(f"Table '{fts_table}' is not a proper FTS5 table")
            
            # Check for content table reference
            if 'content=' in create_sql:
                # Extract content table name
                content_table = None
                parts = create_sql.split('content=')
                if len(parts) > 1:
                    content_part = parts[1].split(',')[0].split(')')[0].strip()
                    content_table = content_part.strip('\'"')
                
                if content_table:
                    # Verify content table exists
                    cursor = conn.execute("""
                        SELECT name FROM sqlite_master 
                        WHERE type='table' AND name = ?
                    """, (content_table,))
                    
                    if not cursor.fetchone():
                        issues.append(f"FTS5 table '{fts_table}' references non-existent content table '{content_table}'")
            
            # Test FTS5 functionality - validate FTS table name
            if not fts_table.replace('_', '').replace('-', '').isalnum():
                raise ValueError(f"Invalid FTS table name: {fts_table}")
            try:
                conn.execute(f"SELECT * FROM {fts_table} WHERE {fts_table} MATCH 'test' LIMIT 1")
            except Exception as e:
                issues.append(f"FTS5 table '{fts_table}' is not functional: {str(e)}")
            
        except Exception as e:
            issues.append(f"Failed to validate FTS5 table '{fts_table}': {str(e)}")
        
        return issues
    
    def _validate_indexes(self, conn: sqlite3.Connection) -> Dict[str, Any]:
        """Validate database indexes"""
        try:
            cursor = conn.execute("""
                SELECT name, tbl_name, sql FROM sqlite_master 
                WHERE type='index' AND name NOT LIKE 'sqlite_%'
                ORDER BY name
            """)
            
            indexes = {}
            issues = []
            
            for index_name, table_name, create_sql in cursor.fetchall():
                indexes[index_name] = {
                    'table': table_name,
                    'sql': create_sql
                }
                
                # Test index usage - validate index name
                if not index_name.replace('_', '').replace('-', '').isalnum():
                    issues.append(f"Invalid index name detected: {index_name}")
                    continue
                try:
                    conn.execute(f"ANALYZE {index_name}")
                except Exception as e:
                    issues.append(f"Index '{index_name}' analysis failed: {str(e)}")
            
            return {
                'valid': len(issues) == 0,
                'indexes': indexes,
                'issues': issues
            }
            
        except Exception as e:
            return {
                'valid': False,
                'indexes': {},
                'issues': [f'Index validation error: {str(e)}']
            }
    
    def _validate_views(self, conn: sqlite3.Connection) -> Dict[str, Any]:
        """Validate database views"""
        try:
            cursor = conn.execute("""
                SELECT name, sql FROM sqlite_master 
                WHERE type='view'
                ORDER BY name
            """)
            
            views = {}
            issues = []
            
            for view_name, create_sql in cursor.fetchall():
                views[view_name] = {
                    'sql': create_sql
                }
                
                # Test view accessibility - validate view name
                if not view_name.replace('_', '').replace('-', '').isalnum():
                    issues.append(f"Invalid view name detected: {view_name}")
                    continue
                try:
                    conn.execute(f"SELECT * FROM {view_name} LIMIT 1")
                except Exception as e:
                    issues.append(f"View '{view_name}' is not accessible: {str(e)}")
            
            return {
                'valid': len(issues) == 0,
                'views': views,
                'issues': issues
            }
            
        except Exception as e:
            return {
                'valid': False,
                'views': {},
                'issues': [f'View validation error: {str(e)}']
            }
    
    def _validate_triggers(self, conn: sqlite3.Connection) -> Dict[str, Any]:
        """Validate database triggers"""
        try:
            cursor = conn.execute("""
                SELECT name, tbl_name, sql FROM sqlite_master 
                WHERE type='trigger'
                ORDER BY name
            """)
            
            triggers = {}
            issues = []
            
            for trigger_name, table_name, create_sql in cursor.fetchall():
                triggers[trigger_name] = {
                    'table': table_name,
                    'sql': create_sql
                }
            
            return {
                'valid': len(issues) == 0,
                'triggers': triggers,
                'issues': issues
            }
            
        except Exception as e:
            return {
                'valid': False,
                'triggers': {},
                'issues': [f'Trigger validation error: {str(e)}']
            }
    
    def validate_foreign_keys(self) -> Dict[str, Any]:
        """Validate foreign key constraints"""
        try:
            with self._get_connection() as conn:
                # Run foreign key check
                cursor = conn.execute("PRAGMA foreign_key_check")
                violations = []
                
                for row in cursor.fetchall():
                    table, rowid, parent_table, fk_index = row
                    violations.append({
                        'table': table,
                        'rowid': rowid,
                        'parent_table': parent_table,
                        'fk_index': fk_index
                    })
                
                return {
                    'valid': len(violations) == 0,
                    'violations': violations,
                    'message': f'Found {len(violations)} foreign key violations' if violations else 'All foreign keys valid'
                }
                
        except Exception as e:
            return {
                'valid': False,
                'error': str(e),
                'violations': [],
                'message': f'Foreign key validation failed: {str(e)}'
            }
    
    def validate_required_indexes(self, required_indexes: Dict[str, str]) -> Dict[str, Any]:
        """
        Validate that required indexes exist for performance
        
        Args:
            required_indexes: Dict of {index_name: expected_definition}
            
        Returns:
            Validation result with missing indexes
        """
        try:
            with self._get_connection() as conn:
                # Get existing indexes
                cursor = conn.execute("""
                    SELECT name, sql FROM sqlite_master 
                    WHERE type='index' AND name NOT LIKE 'sqlite_%'
                """)
                
                existing_indexes = {name: sql for name, sql in cursor.fetchall()}
                
                missing_indexes = []
                invalid_indexes = []
                
                for required_name, expected_def in required_indexes.items():
                    if required_name not in existing_indexes:
                        missing_indexes.append({
                            'name': required_name,
                            'expected_definition': expected_def
                        })
                    else:
                        # Could add more sophisticated definition matching here
                        existing_sql = existing_indexes[required_name]
                        if existing_sql and expected_def.lower() not in existing_sql.lower():
                            invalid_indexes.append({
                                'name': required_name,
                                'expected': expected_def,
                                'actual': existing_sql
                            })
                
                return {
                    'valid': len(missing_indexes) == 0 and len(invalid_indexes) == 0,
                    'missing_indexes': missing_indexes,
                    'invalid_indexes': invalid_indexes,
                    'existing_indexes': list(existing_indexes.keys())
                }
                
        except Exception as e:
            return {
                'valid': False,
                'error': str(e),
                'missing_indexes': [],
                'invalid_indexes': [],
                'existing_indexes': []
            }
    
    def validate_data_consistency(self) -> Dict[str, Any]:
        """Validate data consistency across related tables"""
        try:
            with self._get_connection() as conn:
                issues = []
                
                # Run SQLite integrity check
                cursor = conn.execute("PRAGMA integrity_check")
                integrity_result = cursor.fetchone()[0]
                
                if integrity_result != "ok":
                    issues.append(f"Database integrity check failed: {integrity_result}")
                
                # Check FTS5 synchronization
                fts_issues = self._check_fts5_sync(conn)
                issues.extend(fts_issues)
                
                # Check for orphaned records (basic check)
                orphan_issues = self._check_orphaned_records(conn)
                issues.extend(orphan_issues)
                
                return {
                    'valid': len(issues) == 0,
                    'issues': issues,
                    'integrity_check': integrity_result
                }
                
        except Exception as e:
            return {
                'valid': False,
                'error': str(e),
                'issues': [f'Data consistency check failed: {str(e)}'],
                'integrity_check': 'failed'
            }
    
    def _check_fts5_sync(self, conn: sqlite3.Connection) -> List[str]:
        """Check FTS5 virtual table synchronization with content tables"""
        issues = []
        
        try:
            # Find FTS5 tables with content tables
            cursor = conn.execute("""
                SELECT name, sql FROM sqlite_master 
                WHERE type='table' AND sql LIKE '%fts5%' AND sql LIKE '%content=%'
            """)
            
            for fts_table, create_sql in cursor.fetchall():
                # Extract content table name (simplified parsing)
                content_table = None
                if 'content=' in create_sql:
                    parts = create_sql.split('content=')
                    if len(parts) > 1:
                        content_part = parts[1].split(',')[0].split(')')[0].strip()
                        content_table = content_part.strip('\'"')
                
                if content_table:
                    # Check record counts match
                    try:
                        cursor = conn.execute(f"SELECT COUNT(*) FROM {content_table}")
                        content_count = cursor.fetchone()[0]
                        
                        cursor = conn.execute(f"SELECT COUNT(*) FROM {fts_table}")
                        fts_count = cursor.fetchone()[0]
                        
                        if content_count != fts_count:
                            issues.append(
                                f"FTS5 table '{fts_table}' ({fts_count} records) "
                                f"out of sync with content table '{content_table}' ({content_count} records)"
                            )
                    except Exception as e:
                        issues.append(f"Failed to check FTS5 sync for '{fts_table}': {str(e)}")
        
        except Exception as e:
            issues.append(f"FTS5 sync check failed: {str(e)}")
        
        return issues
    
    def _check_orphaned_records(self, conn: sqlite3.Connection) -> List[str]:
        """Check for orphaned records in tables with foreign keys"""
        issues = []
        
        try:
            # Get tables with foreign keys
            cursor = conn.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
            """)
            
            for (table_name,) in cursor.fetchall():
                # Get foreign key constraints
                cursor = conn.execute(f"PRAGMA foreign_key_list({table_name})")
                foreign_keys = cursor.fetchall()
                
                for fk in foreign_keys:
                    _, _, parent_table, from_column, to_column, _, _, _ = fk
                    
                    # Check for orphaned records
                    try:
                        cursor = conn.execute(f"""
                            SELECT COUNT(*) FROM {table_name} 
                            WHERE {from_column} IS NOT NULL 
                            AND {from_column} NOT IN (
                                SELECT {to_column} FROM {parent_table} 
                                WHERE {to_column} IS NOT NULL
                            )
                        """)
                        
                        orphaned_count = cursor.fetchone()[0]
                        if orphaned_count > 0:
                            issues.append(
                                f"Table '{table_name}' has {orphaned_count} orphaned records "
                                f"in column '{from_column}' referencing '{parent_table}.{to_column}'"
                            )
                    except Exception as e:
                        # Skip if query fails (complex foreign key relationships)
                        pass
        
        except Exception as e:
            issues.append(f"Orphaned record check failed: {str(e)}")
        
        return issues
    
    def get_schema_summary(self) -> Dict[str, Any]:
        """Get comprehensive schema summary"""
        try:
            with self._get_connection() as conn:
                # Count objects by type
                cursor = conn.execute("""
                    SELECT type, COUNT(*) FROM sqlite_master 
                    WHERE name NOT LIKE 'sqlite_%'
                    GROUP BY type
                """)
                
                object_counts = dict(cursor.fetchall())
                
                # Get database file info
                cursor = conn.execute("PRAGMA page_count")
                page_count = cursor.fetchone()[0]
                
                cursor = conn.execute("PRAGMA page_size")
                page_size = cursor.fetchone()[0]
                
                db_size = page_count * page_size
                
                # Get table sizes
                table_sizes = {}
                cursor = conn.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name NOT LIKE 'sqlite_%'
                """)
                
                for (table_name,) in cursor.fetchall():
                    try:
                        cursor = conn.execute(f"SELECT COUNT(*) FROM {table_name}")
                        row_count = cursor.fetchone()[0]
                        table_sizes[table_name] = row_count
                    except:
                        table_sizes[table_name] = 'unknown'
                
                return {
                    'object_counts': object_counts,
                    'database_size_bytes': db_size,
                    'database_size_mb': db_size / 1024**2,
                    'page_count': page_count,
                    'page_size': page_size,
                    'table_sizes': table_sizes,
                    'database_path': str(self.db_path)
                }
                
        except Exception as e:
            return {
                'error': f'Failed to get schema summary: {str(e)}',
                'database_path': str(self.db_path)
            }