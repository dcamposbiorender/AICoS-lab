#!/usr/bin/env python3
"""
Search CLI Tool - Phase 3: Search CLI Interface

Command-line interface for searching indexed archives using natural language queries.
Provides comprehensive search capabilities with multiple output formats and 
interactive mode for exploratory search.

Key Features:
- Natural language search with FTS5 integration
- Multiple output formats (table, JSON, CSV) 
- Source filtering and date range queries
- Interactive mode for exploratory search
- Archive indexing management
- Performance monitoring and statistics
- Query enhancement for better matching

Integration:
- Uses SearchDatabase from Sub-Agent A1 for database operations
- Uses ArchiveIndexer from Sub-Agent A2 for indexing operations
- Supports all data sources: slack, calendar, drive, employees

Usage:
    python tools/search_cli.py search "team meeting"
    python tools/search_cli.py search --source slack --format json "project deadline"  
    python tools/search_cli.py search --interactive
    python tools/search_cli.py index --source slack /path/to/archive.jsonl
    python tools/search_cli.py stats --format json

References:
- tasks_A.md lines 1334-1717 for implementation requirements
- Integration with SearchDatabase and ArchiveIndexer
- Test requirements from tests/integration/test_search_cli.py
"""

import json
import csv
import io
import sys
import time
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

import click

# Add project root to Python path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.search.database import SearchDatabase, DatabaseError
from src.search.indexer import ArchiveIndexer, IndexingError
from src.search.migrations import MigrationManager, MigrationError
from src.search.schema_validator import SchemaValidator


class SearchCLIError(Exception):
    """Exception raised by Search CLI operations"""
    pass


@click.group()
@click.version_option(version='1.0.0', prog_name='search-cli')
def search_cli():
    """
    AI Chief of Staff Search CLI
    
    Search indexed archives using natural language queries across
    Slack messages, Calendar events, Drive files, and Employee data.
    
    \b
    Examples:
        search "team meeting tomorrow"
        search --source slack "project deadline" 
        search --start-date 2025-08-01 --end-date 2025-08-31 "birthday"
        search --format json "important announcement" > results.json
        search --interactive
        index --source slack /path/to/slack_archive.jsonl
        stats --format json
        migrate apply 001_initial_schema.sql
        migrate status
    """
    pass


@search_cli.command()
@click.option('--db', 'db_path', default='search.db', 
              help='Path to search database (default: search.db)')
@click.option('--source', type=click.Choice(['slack', 'calendar', 'drive', 'employees']),
              help='Filter results by source type')
@click.option('--start-date', type=str,
              help='Start date filter (YYYY-MM-DD format)')
@click.option('--end-date', type=str,
              help='End date filter (YYYY-MM-DD format)')
@click.option('--limit', type=int, default=10,
              help='Maximum number of results to return (default: 10)')
@click.option('--format', 'output_format', 
              type=click.Choice(['table', 'json', 'csv']), default='table',
              help='Output format (default: table)')
@click.option('--interactive', is_flag=True,
              help='Start interactive search session')
@click.option('--verbose', is_flag=True,
              help='Show detailed metadata in results')
@click.argument('query', required=False)
def search(db_path: str, source: Optional[str], start_date: Optional[str], 
           end_date: Optional[str], limit: int, output_format: str,
           interactive: bool, verbose: bool, query: Optional[str]):
    """
    Search indexed archives using natural language queries
    
    \b
    Query Examples:
        "team meeting"               # Simple text search
        "project deadline friday"   # Multiple terms
        "from:alice important"       # User-specific search
        
    \b
    Filter Examples:
        --source slack "meeting"     # Search only Slack messages
        --start-date 2025-08-01      # Results after date
        --limit 5                    # Top 5 results only
    """
    try:
        # Initialize database
        db = SearchDatabase(db_path)
        
        if interactive:
            run_interactive_search(db, source, start_date, end_date, limit, output_format, verbose)
        elif query:
            results = perform_search(db, query, source, start_date, end_date, limit)
            display_results(results, output_format, verbose, query, db)
        else:
            click.echo("Error: Query required in non-interactive mode. Use --help for usage.", err=True)
            sys.exit(1)
            
    except DatabaseError as e:
        click.echo(f"Database error: {str(e)}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Search error: {str(e)}", err=True)
        sys.exit(1)


@search_cli.command()
@click.option('--db', 'db_path', default='search.db',
              help='Path to search database (default: search.db)')
@click.option('--source', type=click.Choice(['slack', 'calendar', 'drive', 'employees']),
              required=True, help='Source type of the archive')
@click.option('--progress', is_flag=True,
              help='Show indexing progress')
@click.option('--batch-size', type=int, default=10000,
              help='Records per batch for processing (default: 10000)')
@click.argument('archive_path', type=click.Path(exists=True))
def index(db_path: str, source: str, progress: bool, batch_size: int, archive_path: str):
    """
    Index JSONL archive files into the search database
    
    \b
    Examples:
        index --source slack /data/archive/slack/2025-08-17/data.jsonl
        index --source calendar --progress /data/archive/calendar/events.jsonl
    """
    try:
        # Initialize database and indexer
        db = SearchDatabase(db_path)
        indexer = ArchiveIndexer(db, batch_size=batch_size)
        
        archive_path = Path(archive_path)
        
        if progress:
            click.echo(f"Processing archive: {archive_path}")
            click.echo(f"Source: {source}")
            click.echo(f"Batch size: {batch_size}")
            click.echo()
        
        # Progress callback for updates
        def progress_callback(processed: int, total: int, rate: float):
            if progress:
                click.echo(f"Processed {processed:,} records at {rate:.1f} records/sec", nl=False)
                click.echo('\r', nl=False)  # Carriage return for same-line updates
        
        # Process the archive
        start_time = time.time()
        stats = indexer.process_archive(archive_path, source, progress_callback)
        duration = time.time() - start_time
        
        # Display results
        if progress:
            click.echo()  # New line after progress updates
        
        if stats.processed > 0:
            click.echo(f"✓ Indexing completed successfully")
            click.echo(f"  Records indexed: {stats.processed:,}")
            click.echo(f"  Errors: {stats.error_count}")
            click.echo(f"  Duration: {duration:.2f} seconds") 
            click.echo(f"  Rate: {stats.avg_processing_rate:.1f} records/sec")
            click.echo(f"  Peak memory: {stats.peak_memory_mb:.1f} MB")
        else:
            if stats.skipped_unchanged:
                click.echo("⚠ Archive unchanged - indexing skipped")
            else:
                click.echo("⚠ No records were indexed")
                if stats.errors:
                    click.echo("Errors encountered:")
                    for error in stats.errors[:5]:  # Show first 5 errors
                        click.echo(f"  • {error}")
        
    except (DatabaseError, IndexingError) as e:
        click.echo(f"Indexing error: {str(e)}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {str(e)}", err=True)
        sys.exit(1)


@search_cli.command()
@click.option('--db', 'db_path', default='search.db',
              help='Path to search database (default: search.db)')
@click.option('--format', 'output_format',
              type=click.Choice(['table', 'json']), default='table',
              help='Output format (default: table)')
def stats(db_path: str, output_format: str):
    """
    Display search database statistics and health information
    
    Shows total records, source breakdown, indexing performance,
    and database health metrics.
    """
    try:
        db = SearchDatabase(db_path)
        stats_data = db.get_stats()
        
        if output_format == 'json':
            click.echo(json.dumps(stats_data, indent=2))
        else:
            display_stats_table(stats_data)
            
    except DatabaseError as e:
        click.echo(f"Database error: {str(e)}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Stats error: {str(e)}", err=True) 
        sys.exit(1)


def run_interactive_search(db: SearchDatabase, source: Optional[str], 
                          start_date: Optional[str], end_date: Optional[str],
                          limit: int, output_format: str, verbose: bool):
    """Run interactive search session with special commands"""
    click.echo(click.style("AI Chief of Staff - Interactive Search Mode", fg='cyan', bold=True))
    click.echo(f"Database: {db.db_path}")
    
    if source:
        click.echo(f"Source filter: {click.style(source, fg='blue')}")
    if start_date and end_date:
        click.echo(f"Date range: {start_date} to {end_date}")
    
    click.echo()
    click.echo("Special commands:")
    click.echo("  /stats  - Show database statistics") 
    click.echo("  /help   - Show help information")
    click.echo("  q, quit, exit - Quit interactive mode")
    click.echo()
    
    while True:
        try:
            query = click.prompt(click.style("Search>", fg='green'), type=str)
            
            if query.lower() in ['q', 'quit', 'exit']:
                click.echo("Goodbye!")
                break
                
            if not query.strip():
                continue
            
            # Handle special commands
            if query.startswith('/'):
                handle_special_command(query, db)
                continue
            
            # Perform search
            click.echo()  # Blank line before results
            results = perform_search(db, query, source, start_date, end_date, limit)
            
            if results:
                click.echo(f"Found {click.style(str(len(results)), fg='cyan')} results:")
                display_results(results, output_format, verbose, query, db)
            else:
                click.echo(click.style("No results found.", fg='yellow'))
                suggest_alternatives(query, db)
            
            click.echo()  # Blank line after results
            
        except KeyboardInterrupt:
            click.echo("\nExiting interactive mode...")
            break
        except EOFError:
            break
        except Exception as e:
            click.echo(f"Search error: {str(e)}", err=True)


def perform_search(db: SearchDatabase, query: str, source: Optional[str],
                  start_date: Optional[str], end_date: Optional[str],
                  limit: int) -> List[Dict[str, Any]]:
    """Perform search with query enhancement and return results"""
    
    # Parse date range
    date_range = None
    if start_date and end_date:
        date_range = (start_date, end_date)
    
    # Enhanced query processing for better FTS5 matching
    processed_query = enhance_query(query)
    
    # Execute search
    results = db.search(
        query=processed_query,
        source=source,
        date_range=date_range,
        limit=limit
    )
    
    return results


def enhance_query(query: str) -> str:
    """
    Enhance query for better FTS5 searching
    
    Applies transformations to improve search effectiveness:
    - Add wildcards for partial matches on longer words
    - Handle special search operators
    - Clean up problematic characters
    """
    # Split query into words
    words = query.split()
    enhanced_words = []
    
    for word in words:
        # Skip special operators (from:, in:, etc.)
        if ':' in word:
            enhanced_words.append(word)
        # Add wildcards for longer words to enable partial matching
        elif len(word) > 3 and word.isalnum():
            enhanced_words.append(f"{word}*")
        else:
            enhanced_words.append(word)
    
    enhanced_query = ' '.join(enhanced_words)
    
    # Handle phrase queries (keep quoted phrases intact)
    if '"' in query:
        enhanced_query = query  # Preserve exact phrase queries
    
    return enhanced_query


def display_results(results: List[Dict[str, Any]], output_format: str, 
                   verbose: bool, query: Optional[str] = None, 
                   db: Optional['SearchDatabase'] = None):
    """Display search results in the specified format"""
    
    if not results:
        if output_format == 'json':
            click.echo("[]")  # Empty JSON array for no results
        elif output_format == 'csv':
            click.echo("")  # Empty CSV
        else:
            click.echo(click.style("No results found.", fg='yellow'))
            # Show suggestions in non-interactive mode too if we have database access
            if query and db:
                suggest_alternatives(query, db)
        return
    
    if output_format == 'json':
        click.echo(json.dumps(results, indent=2, ensure_ascii=False))
        
    elif output_format == 'csv':
        display_results_csv(results, verbose)
        
    else:  # table format (default)
        display_results_table(results, verbose, query)


def display_results_table(results: List[Dict[str, Any]], verbose: bool, 
                         query: Optional[str] = None):
    """Display results in human-readable table format"""
    
    for i, result in enumerate(results, 1):
        # Header with result number, source, date, and score
        source_styled = click.style(result['source'].upper(), fg='blue', bold=True)
        score_styled = click.style(f"{result['relevance_score']:.3f}", fg='cyan')
        
        click.echo(f"{i}. {source_styled} | {result['date']} | Score: {score_styled}")
        
        # Content with basic highlighting
        content = result['content']
        if query and len(query) > 2:
            content = highlight_query_terms(content, query)
        
        # Truncate long content
        if len(content) > 300:
            content = content[:297] + '...'
        
        click.echo(f"   {content}")
        
        # Show metadata if verbose mode
        if verbose and result.get('metadata'):
            metadata = result['metadata']
            if isinstance(metadata, dict):
                meta_items = []
                for key, value in metadata.items():
                    # Skip large or complex metadata fields
                    if key not in ['original_record', 'blocks', 'attachments'] and value:
                        if len(str(value)) < 50:  # Keep metadata concise
                            meta_items.append(f"{key}={value}")
                
                if meta_items:
                    meta_text = ', '.join(meta_items[:5])  # Max 5 metadata items
                    click.echo(f"   {click.style('Metadata:', dim=True)} {meta_text}")
        
        # Add spacing between results
        if i < len(results):
            click.echo()


def display_results_csv(results: List[Dict[str, Any]], verbose: bool):
    """Display results in CSV format"""
    output = io.StringIO()
    
    # Define CSV columns
    fieldnames = ['content', 'source', 'date', 'score']
    if verbose:
        fieldnames.append('metadata')
    
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    
    for result in results:
        row = {
            'content': result['content'][:200] + '...' if len(result['content']) > 200 else result['content'],
            'source': result['source'],
            'date': result['date'],
            'score': f"{result['relevance_score']:.3f}"
        }
        
        if verbose and result.get('metadata'):
            # Serialize metadata as JSON string for CSV
            row['metadata'] = json.dumps(result['metadata'])
        
        writer.writerow(row)
    
    click.echo(output.getvalue().strip())


def display_stats_table(stats_data: Dict[str, Any]):
    """Display database statistics in table format"""
    click.echo(click.style("Database Statistics:", fg='cyan', bold=True))
    click.echo(f"Total records: {stats_data.get('total_records', 0):,}")
    click.echo(f"Archives tracked: {stats_data.get('archives_tracked', 0)}")
    click.echo(f"Queries executed: {stats_data.get('queries_executed', 0)}")
    click.echo(f"Records indexed: {stats_data.get('records_indexed', 0)}")
    
    # Connection statistics
    click.echo(f"Connections created: {stats_data.get('connections_created', 0)}")
    click.echo(f"Connections reused: {stats_data.get('connections_reused', 0)}")
    
    # Records by source breakdown
    if 'records_by_source' in stats_data and stats_data['records_by_source']:
        click.echo()
        click.echo(click.style("Records by source:", fg='yellow'))
        for source, count in stats_data['records_by_source'].items():
            percentage = (count / stats_data['total_records'] * 100) if stats_data['total_records'] > 0 else 0
            click.echo(f"  {source}: {count:,} ({percentage:.1f}%)")


def suggest_alternatives(query: str, db: SearchDatabase):
    """Suggest alternative searches when no results found"""
    suggestions = []
    
    # Get database stats for source suggestions
    try:
        stats = db.get_stats()
        
        if 'records_by_source' in stats and stats['records_by_source']:
            available_sources = list(stats['records_by_source'].keys())
            if available_sources:
                sources_text = click.style(', '.join(available_sources), fg='blue')
                suggestions.append(f"Try filtering by source: {sources_text}")
        
        # Simple word-based suggestions
        words = query.lower().split()
        if len(words) > 1:
            word_suggestions = [click.style(word, fg='cyan') for word in words[:3]]
            suggestions.append(f"Try searching for individual terms: {', '.join(word_suggestions)}")
        
        # Query length suggestions
        if len(query) < 3:
            suggestions.append("Try a longer, more specific query")
        elif len(query.split()) > 5:
            suggestions.append("Try a shorter, more focused query")
        
    except Exception:
        # Fallback suggestions if stats unavailable
        suggestions.append("Try different keywords or check your spelling")
        suggestions.append("Use --source to filter by data type")
    
    if suggestions:
        click.echo()
        click.echo(click.style('Suggestions:', fg='yellow', bold=True))
        for suggestion in suggestions:
            click.echo(f"  • {suggestion}")


def handle_special_command(command: str, db: SearchDatabase):
    """Handle special commands in interactive mode"""
    
    if command == '/stats':
        try:
            stats_data = db.get_stats()
            display_stats_table(stats_data)
        except Exception as e:
            click.echo(f"Error getting stats: {str(e)}", err=True)
    
    elif command == '/help':
        click.echo()
        click.echo(click.style("Interactive Search Help", fg='cyan', bold=True))
        click.echo()
        click.echo("Search Queries:")
        click.echo("  team meeting              # Simple search")
        click.echo("  \"project deadline\"        # Phrase search")
        click.echo("  from:alice important      # User-specific search")
        click.echo("  meeting OR project        # Boolean OR")
        click.echo()
        click.echo("Special Commands:")
        click.echo("  /stats                    # Database statistics")
        click.echo("  /help                     # This help message")
        click.echo("  q, quit, exit            # Quit interactive mode")
        click.echo()
    
    else:
        click.echo(f"Unknown command: {click.style(command, fg='red')}")
        click.echo("Type '/help' for available commands")


def highlight_query_terms(content: str, query: str) -> str:
    """
    Highlight query terms in content for better readability
    
    Simple highlighting using ANSI color codes
    """
    try:
        # Extract meaningful terms from query (skip operators and short words)
        terms = []
        for word in query.split():
            if ':' not in word and len(word) > 2:
                # Remove wildcards and special characters for highlighting
                clean_word = word.rstrip('*').strip('"')
                if clean_word:
                    terms.append(clean_word)
        
        # Highlight each term (case-insensitive)
        highlighted = content
        for term in terms:
            pattern = re.compile(re.escape(term), re.IGNORECASE)
            highlighted = pattern.sub(lambda m: click.style(m.group(), bg='yellow', fg='black'), highlighted)
        
        return highlighted
        
    except Exception:
        # If highlighting fails, return original content
        return content


def validate_date_format(date_str: str) -> bool:
    """Validate date string is in YYYY-MM-DD format"""
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        return True
    except ValueError:
        return False


@search_cli.group()
def migrate():
    """
    Database schema migration commands
    
    Manage database schema versions, apply migrations, and validate schema integrity.
    
    \b
    Examples:
        migrate status                           # Show current migration status
        migrate apply 001_initial_schema.sql     # Apply specific migration
        migrate rollback 2                       # Rollback to version 2
        migrate validate                         # Validate schema integrity
    """
    pass


@migrate.command()
@click.option('--db', 'db_path', default='search.db',
              help='Path to search database (default: search.db)')
@click.option('--migrations-dir', default=None,
              help='Path to migrations directory (default: auto-detect)')
def status(db_path: str, migrations_dir: Optional[str]):
    """Show current migration status and available migrations"""
    try:
        migration_manager = MigrationManager(db_path, migrations_dir)
        status_info = migration_manager.get_migration_status()
        
        click.echo(click.style("Database Migration Status", fg='cyan', bold=True))
        click.echo(f"Database: {status_info['database_path']}")
        click.echo(f"Migration Directory: {status_info['migration_directory']}")
        click.echo(f"Current Version: {click.style(str(status_info['current_version']), fg='green', bold=True)}")
        click.echo()
        
        if status_info['applied_migrations'] > 0:
            click.echo(f"Applied Migrations: {status_info['applied_migrations']}")
            
            # Show applied migrations
            applied_migrations = migration_manager.get_applied_migrations()
            for migration in applied_migrations[-5:]:  # Show last 5
                version_str = click.style(f"v{migration['version']}", fg='green')
                click.echo(f"  ✓ {version_str} {migration['filename']} - {migration['description']}")
                click.echo(f"    Applied: {migration['applied_at']}")
        
        if status_info['pending_migrations'] > 0:
            click.echo()
            click.echo(f"Pending Migrations: {click.style(str(status_info['pending_migrations']), fg='yellow')}")
            for filename in status_info['pending_migration_files']:
                click.echo(f"  • {filename}")
        else:
            click.echo()
            click.echo(click.style("✓ All migrations applied", fg='green'))
        
        if status_info['failed_migrations']:
            click.echo()
            click.echo(click.style("Failed Migrations:", fg='red', bold=True))
            for failed in status_info['failed_migrations']:
                click.echo(f"  ✗ {failed['filename']}: {failed['error']}")
    
    except MigrationError as e:
        click.echo(f"Migration error: {str(e)}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {str(e)}", err=True)
        sys.exit(1)


@migrate.command()
@click.option('--db', 'db_path', default='search.db',
              help='Path to search database (default: search.db)')
@click.option('--migrations-dir', default=None,
              help='Path to migrations directory (default: auto-detect)')
@click.option('--dry-run', is_flag=True,
              help='Show what would be applied without executing')
@click.argument('migration_file')
def apply(db_path: str, migrations_dir: Optional[str], dry_run: bool, migration_file: str):
    """Apply a specific migration file"""
    try:
        migration_manager = MigrationManager(db_path, migrations_dir)
        
        if dry_run:
            # Show what would be applied
            migrations = migration_manager.discover_migrations()
            target_migration = None
            
            for migration in migrations:
                if migration.filename == migration_file:
                    target_migration = migration
                    break
            
            if not target_migration:
                click.echo(f"Migration file not found: {migration_file}", err=True)
                sys.exit(1)
            
            click.echo(click.style("Dry Run - Migration Preview", fg='yellow', bold=True))
            click.echo(f"File: {target_migration.filename}")
            click.echo(f"Description: {target_migration.description}")
            click.echo(f"Version: {target_migration.version}")
            click.echo(f"Checksum: {target_migration.checksum[:16]}...")
            click.echo()
            click.echo("SQL Content Preview:")
            click.echo("-" * 50)
            click.echo(target_migration.sql_content[:500])
            if len(target_migration.sql_content) > 500:
                click.echo("... (truncated)")
            click.echo("-" * 50)
            click.echo()
            click.echo(click.style("Use --apply without --dry-run to execute", fg='green'))
            return
        
        # Apply migration
        click.echo(f"Applying migration: {click.style(migration_file, fg='cyan')}")
        
        start_time = time.time()
        result = migration_manager.apply_migration(migration_file)
        duration = time.time() - start_time
        
        if result['success']:
            click.echo(click.style("✓ Migration applied successfully", fg='green'))
            click.echo(f"  Version: {result['version']}")
            click.echo(f"  Duration: {duration:.3f} seconds")
            
            if result.get('data_integrity_verified'):
                click.echo(f"  {click.style('✓ Data integrity verified', fg='green')}")
        else:
            click.echo(click.style("✗ Migration failed", fg='red'))
            if 'message' in result:
                click.echo(f"  Error: {result['message']}")
            sys.exit(1)
    
    except MigrationError as e:
        click.echo(f"Migration error: {str(e)}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {str(e)}", err=True)
        sys.exit(1)


@migrate.command()
@click.option('--db', 'db_path', default='search.db',
              help='Path to search database (default: search.db)')
@click.option('--migrations-dir', default=None,
              help='Path to migrations directory (default: auto-detect)')
@click.option('--confirm', is_flag=True,
              help='Confirm rollback operation')
@click.argument('target_version', type=int)
def rollback(db_path: str, migrations_dir: Optional[str], confirm: bool, target_version: int):
    """Rollback database to a specific version"""
    try:
        migration_manager = MigrationManager(db_path, migrations_dir)
        current_version = migration_manager.get_current_version()
        
        if target_version >= current_version:
            click.echo(f"Target version {target_version} is not less than current version {current_version}")
            return
        
        # Show rollback plan
        applied_migrations = migration_manager.get_applied_migrations()
        rollback_migrations = [m for m in applied_migrations if m['version'] > target_version]
        
        click.echo(click.style("Rollback Plan", fg='yellow', bold=True))
        click.echo(f"Current Version: {current_version}")
        click.echo(f"Target Version: {target_version}")
        click.echo(f"Migrations to rollback: {len(rollback_migrations)}")
        
        for migration in reversed(rollback_migrations):
            click.echo(f"  • v{migration['version']} {migration['filename']}")
        
        if not confirm:
            click.echo()
            click.echo(click.style("WARNING: This operation may result in data loss!", fg='red', bold=True))
            if not click.confirm("Are you sure you want to continue?"):
                click.echo("Rollback cancelled")
                return
        
        # Perform rollback
        click.echo()
        click.echo(f"Rolling back to version {target_version}...")
        
        start_time = time.time()
        result = migration_manager.rollback_to_version(target_version)
        duration = time.time() - start_time
        
        if result['success']:
            click.echo(click.style("✓ Rollback completed successfully", fg='green'))
            click.echo(f"  New Version: {result['version']}")
            click.echo(f"  Duration: {duration:.3f} seconds")
            click.echo(f"  Rolled Back: {', '.join(result['rolled_back_migrations'])}")
            
            if result.get('data_integrity_verified'):
                click.echo(f"  {click.style('✓ Data integrity verified', fg='green')}")
        else:
            click.echo(click.style("✗ Rollback failed", fg='red'))
            if 'message' in result:
                click.echo(f"  Error: {result['message']}")
            sys.exit(1)
    
    except MigrationError as e:
        click.echo(f"Migration error: {str(e)}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {str(e)}", err=True)
        sys.exit(1)


@migrate.command()
@click.option('--db', 'db_path', default='search.db',
              help='Path to search database (default: search.db)')
@click.option('--format', 'output_format',
              type=click.Choice(['table', 'json']), default='table',
              help='Output format (default: table)')
def validate(db_path: str, output_format: str):
    """Validate database schema integrity and consistency"""
    try:
        validator = SchemaValidator(db_path)
        
        click.echo("Validating database schema...")
        
        # Comprehensive validation
        schema_result = validator.validate_schema()
        fk_result = validator.validate_foreign_keys() 
        consistency_result = validator.validate_data_consistency()
        
        if output_format == 'json':
            validation_report = {
                'schema_validation': schema_result,
                'foreign_key_validation': fk_result,
                'data_consistency': consistency_result,
                'overall_valid': (schema_result['valid'] and 
                                 fk_result['valid'] and 
                                 consistency_result['valid'])
            }
            click.echo(json.dumps(validation_report, indent=2))
        else:
            # Table format
            overall_valid = (schema_result['valid'] and 
                           fk_result['valid'] and 
                           consistency_result['valid'])
            
            if overall_valid:
                click.echo(click.style("✓ Schema validation passed", fg='green', bold=True))
            else:
                click.echo(click.style("✗ Schema validation failed", fg='red', bold=True))
            
            click.echo()
            click.echo("Schema Structure:")
            if schema_result['valid']:
                click.echo(f"  ✓ Tables: {len(schema_result['tables'])}")
                click.echo(f"  ✓ Indexes: {len(schema_result['indexes'])}")  
                click.echo(f"  ✓ Views: {len(schema_result['views'])}")
                click.echo(f"  ✓ Triggers: {len(schema_result['triggers'])}")
            else:
                click.echo(f"  ✗ Issues found: {len(schema_result['issues'])}")
                for issue in schema_result['issues'][:5]:
                    click.echo(f"    • {issue}")
            
            click.echo()
            click.echo("Foreign Key Constraints:")
            if fk_result['valid']:
                click.echo("  ✓ All foreign key constraints valid")
            else:
                click.echo(f"  ✗ Violations found: {len(fk_result['violations'])}")
                for violation in fk_result['violations'][:3]:
                    click.echo(f"    • Table {violation['table']}, row {violation['rowid']}")
            
            click.echo()
            click.echo("Data Consistency:")
            if consistency_result['valid']:
                click.echo("  ✓ Data consistency checks passed")
                click.echo(f"  ✓ SQLite integrity: {consistency_result['integrity_check']}")
            else:
                click.echo(f"  ✗ Issues found: {len(consistency_result['issues'])}")
                for issue in consistency_result['issues'][:3]:
                    click.echo(f"    • {issue}")
            
            if not overall_valid:
                sys.exit(1)
    
    except Exception as e:
        click.echo(f"Validation error: {str(e)}", err=True)
        sys.exit(1)


@migrate.command()
@click.option('--db', 'db_path', default='search.db',
              help='Path to search database (default: search.db)')
@click.option('--migrations-dir', default=None,
              help='Path to migrations directory (default: auto-detect)')
def discover(db_path: str, migrations_dir: Optional[str]):
    """Discover and list all available migration files"""
    try:
        migration_manager = MigrationManager(db_path, migrations_dir)
        migrations = migration_manager.discover_migrations()
        applied_migrations = {m['version'] for m in migration_manager.get_applied_migrations()}
        
        click.echo(click.style("Available Migrations", fg='cyan', bold=True))
        click.echo(f"Migration Directory: {migration_manager.migration_dir}")
        click.echo(f"Found: {len(migrations)} migration files")
        click.echo()
        
        if not migrations:
            click.echo(click.style("No migration files found", fg='yellow'))
            return
        
        for migration in migrations:
            status_symbol = "✓" if migration.version in applied_migrations else "•"
            status_color = "green" if migration.version in applied_migrations else "yellow"
            version_str = click.style(f"v{migration.version}", fg='blue')
            
            click.echo(f"{click.style(status_symbol, fg=status_color)} {version_str} {migration.filename}")
            click.echo(f"  Description: {migration.description}")
            click.echo(f"  Checksum: {migration.checksum[:16]}...")
            
            if migration.version in applied_migrations:
                click.echo(f"  {click.style('Applied', fg='green')}")
            else:
                click.echo(f"  {click.style('Pending', fg='yellow')}")
            
            click.echo()
    
    except MigrationError as e:
        click.echo(f"Migration error: {str(e)}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {str(e)}", err=True)
        sys.exit(1)


if __name__ == '__main__':
    search_cli()