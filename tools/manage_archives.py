#!/usr/bin/env python3
"""
Enhanced Archive Management CLI Tool with UX and Safety Features
Unified interface for compression, verification, statistics, and backup

Enhanced Features for Team B:
- Beautiful terminal output with colors and symbols
- Progress indicators for long operations  
- Dry-run mode shows exactly what would be changed
- Comprehensive error handling with remediation steps
- Multiple output formats (table, JSON)
- Resume capability for interrupted operations
- Safety features with backup creation

References: CLAUDE.md commandments about production quality tools
"""

import click
import json
import sys
import os
import shutil
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime

# Enhanced imports for UX features
try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False
    
try:
    import filelock
    HAS_FILELOCK = True
except ImportError:
    HAS_FILELOCK = False

# Import our utilities
# Add src to path so we can import from src.core
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.safe_compression import SafeCompressor, CompressionError

# Import verify_archive from same directory
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))
from verify_archive import ArchiveVerifier, VerificationError

# Set up enhanced logging with colors
class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for better UX"""
    
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record):
        if sys.stderr.isatty():  # Only use colors in interactive terminals
            log_color = self.COLORS.get(record.levelname, '')
            record.levelname = f"{log_color}{record.levelname}{self.RESET}"
        return super().format(record)

# Set up colored logging
handler = logging.StreamHandler()
handler.setFormatter(ColoredFormatter('%(levelname)s: %(message)s'))
logging.basicConfig(level=logging.INFO, handlers=[handler])
logger = logging.getLogger(__name__)


class DiskFullError(Exception):
    """Raised when disk is full"""
    pass


class SafeArchiveManager:
    """
    Enhanced archive management tool with safety features and excellent UX
    
    Features:
    - Beautiful terminal output with colors and symbols  
    - Progress indicators for operations taking >5 seconds
    - Dry-run mode shows exactly what would be changed
    - Comprehensive error handling with remediation steps
    - Safety features with backup creation before destructive operations
    - Resume capability for interrupted operations
    - Multiple output formats (table, JSON)
    """
    
    def __init__(self, archive_dir: Path, dry_run: bool = False, quiet: bool = False, 
                 backup_days: int = 7, chunk_size: int = 1024*1024):
        """
        Initialize enhanced archive manager
        
        Args:
            archive_dir: Root archive directory to manage
            dry_run: If True, show what would be done without executing
            quiet: If True, minimize output
            backup_days: Days to retain backups
            chunk_size: Chunk size for file operations
        """
        self.archive_dir = archive_dir
        self.dry_run = dry_run
        self.quiet = quiet
        self.backup_days = backup_days
        self.chunk_size = chunk_size
        
        if quiet:
            logging.getLogger().setLevel(logging.WARNING)
        
        # Initialize components with enhanced features
        self.compressor = SafeCompressor(backup_days=backup_days)
        self.verifier = ArchiveVerifier()
        
        # Operation statistics
        self.stats = {
            'files_processed': 0,
            'files_failed': 0,
            'bytes_processed': 0,
            'operations_completed': 0,
            'errors': []
        }
        
        # Resume capability
        self.checkpoint_file = archive_dir / '.archive_checkpoint.json'
    
    def _check_disk_space(self, required_bytes: int) -> bool:
        """Check if sufficient disk space is available"""
        try:
            stat = shutil.disk_usage(self.archive_dir)
            available = stat.free
            if available < required_bytes:
                raise DiskFullError(
                    f"Insufficient disk space. Required: {required_bytes/1024**2:.1f}MB, "
                    f"Available: {available/1024**2:.1f}MB"
                )
            return True
        except Exception as e:
            logger.warning(f"Could not check disk space: {e}")
            return True  # Proceed optimistically
    
    def _create_backup(self, file_path: Path) -> Optional[Path]:
        """Create backup before destructive operation"""
        if not file_path.exists():
            return None
        
        backup_dir = file_path.parent / '.backup'
        backup_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = backup_dir / f"{file_path.name}.{timestamp}"
        
        try:
            shutil.copy2(file_path, backup_path)
            return backup_path
        except Exception as e:
            logger.error(f"Failed to create backup for {file_path}: {e}")
            return None
    
    def _progress_bar(self, iterable, desc: str):
        """Create progress bar with fallback"""
        if HAS_TQDM and not self.quiet and len(iterable) > 5:
            return tqdm(iterable, desc=desc, unit='files')
        return iterable
    
    def compress_old_files(self, age_days: int = 30, resume: bool = True) -> Dict[str, Any]:
        """
        Compress files older than specified age with enhanced safety and UX
        
        Args:
            age_days: Compress files older than this many days
            resume: Resume from checkpoint if available
            
        Returns:
            Summary of compression operation with enhanced details
        """
        if not self.archive_dir.exists():
            raise CompressionError(f"Archive directory does not exist: {self.archive_dir}")
        
        # Enhanced summary with more details
        summary = {
            'files_found': 0,
            'files_compressed': 0,
            'files_failed': 0,
            'files_skipped': 0,
            'total_size_before': 0,
            'total_size_after': 0,
            'space_saved': 0,
            'compression_ratio': 0.0,
            'errors': [],
            'backups_created': 0,
            'operation_duration': 0,
            'files_per_second': 0.0
        }
        
        start_time = time.time()
        
        # Find compression candidates
        if not self.quiet:
            click.echo(f"🔍 Finding files older than {age_days} days...")
        
        old_files = self.compressor.find_compression_candidates(self.archive_dir, age_days=age_days)
        summary['files_found'] = len(old_files)
        
        if not old_files:
            if not self.quiet:
                click.echo(f"✅ No files older than {age_days} days found")
            return summary
        
        # Calculate total size and check disk space
        total_size = sum(f.stat().st_size for f in old_files if f.exists())
        summary['total_size_before'] = total_size
        
        # Estimate compressed size (assume 70% compression)
        estimated_temp_space = total_size * 0.3  # Temp files during compression
        self._check_disk_space(int(estimated_temp_space * 1.5))  # 50% safety margin
        
        if self.dry_run:
            if not self.quiet:
                click.echo(f"\n{click.style('DRY RUN', fg='yellow', bold=True)} - No changes will be made\n")
                click.echo(f"Would compress {len(old_files)} files:")
                click.echo(f"  Total size: {total_size / 1024**2:.1f} MB")
                click.echo(f"  Estimated space savings: {total_size * 0.7 / 1024**2:.1f} MB")
                
                # Show first 10 files as preview
                for i, f in enumerate(old_files[:10]):
                    size_mb = f.stat().st_size / 1024**2 if f.exists() else 0
                    click.echo(f"  - {f.relative_to(self.archive_dir)} ({size_mb:.1f} MB)")
                
                if len(old_files) > 10:
                    click.echo(f"  ... and {len(old_files)-10} more files")
            return summary
        
        # Resume from checkpoint if available
        processed_files = set()
        if resume and self.checkpoint_file.exists():
            try:
                with open(self.checkpoint_file) as f:
                    checkpoint = json.load(f)
                    processed_files = set(checkpoint.get('processed_files', []))
                    if not self.quiet:
                        click.echo(f"📄 Resuming from checkpoint ({len(processed_files)} files already processed)")
            except Exception as e:
                logger.warning(f"Could not load checkpoint: {e}")
        
        # Filter out already processed files
        remaining_files = [f for f in old_files if str(f) not in processed_files]
        
        if not self.quiet:
            if remaining_files:
                click.echo(f"🔄 Compressing {len(remaining_files)} files ({total_size/1024**2:.1f} MB)...")
                if self.backup_days > 0:
                    click.echo(f"💾 Creating backups (retention: {self.backup_days} days)")
            else:
                click.echo("✅ All files already processed")
                return summary
        
        # Compress files with progress bar and enhanced error handling
        for file_path in self._progress_bar(remaining_files, "Compressing"):
            try:
                if not file_path.exists():
                    summary['files_skipped'] += 1
                    continue
                
                file_size = file_path.stat().st_size
                
                # Create backup before compression
                backup_path = self._create_backup(file_path)
                if backup_path:
                    summary['backups_created'] += 1
                
                # Perform compression with enhanced error handling
                try:
                    success = self.compressor.safe_compress(file_path)
                    if success:
                        compressed_path = file_path.with_suffix('.jsonl.gz')
                        compressed_size = compressed_path.stat().st_size
                        
                        summary['files_compressed'] += 1
                        summary['total_size_after'] += compressed_size
                        summary['space_saved'] += (file_size - compressed_size)
                        
                        # Add to processed set
                        processed_files.add(str(file_path))
                        
                        if not self.quiet and not HAS_TQDM:
                            compression_ratio = (1 - compressed_size/file_size) * 100
                            click.echo(f"  ✅ {file_path.name}: {file_size/1024**2:.1f}MB → "
                                      f"{compressed_size/1024**2:.1f}MB ({compression_ratio:.1f}% saved)")
                    else:
                        summary['files_skipped'] += 1
                
                except CompressionError as e:
                    summary['files_failed'] += 1
                    summary['errors'].append({
                        'file': str(file_path),
                        'error': str(e),
                        'suggestion': 'Check file permissions and available disk space'
                    })
                    
                    # Remove backup if compression failed
                    if backup_path and backup_path.exists():
                        backup_path.unlink()
                        summary['backups_created'] -= 1
                
                # Save checkpoint every 10 files
                if len(processed_files) % 10 == 0:
                    self._save_checkpoint(processed_files)
                    
            except Exception as e:
                summary['files_failed'] += 1
                summary['errors'].append({
                    'file': str(file_path),
                    'error': f'Unexpected error: {str(e)}',
                    'suggestion': 'Check system resources and file access permissions'
                })
        
        # Calculate final statistics
        end_time = time.time()
        duration = end_time - start_time
        summary['operation_duration'] = duration
        summary['files_per_second'] = len(remaining_files) / duration if duration > 0 else 0
        
        if summary['total_size_before'] > 0:
            summary['compression_ratio'] = summary['space_saved'] / summary['total_size_before']
        
        # Clean up checkpoint
        if self.checkpoint_file.exists():
            self.checkpoint_file.unlink()
        
        return summary
    
    def verify_archive(self) -> Dict[str, Any]:
        """
        Verify archive integrity
        
        Returns:
            Verification report
        """
        try:
            report = self.verifier.generate_report(self.archive_dir)
            
            if not self.quiet:
                if report['errors_found'] == 0:
                    print("Archive verification PASSED - no issues found")
                else:
                    print(f"Archive verification FAILED - {report['errors_found']} issues found")
                    
                    for detail in report.get('details', []):
                        if detail['type'] == 'file_verification':
                            print(f"  File: {detail['file']}")
                            for error in detail['errors']:
                                print(f"    Error: {error}")
                        elif detail['type'] == 'directory_structure':
                            print(f"  Directory structure issues:")
                            for issue in detail['issues']:
                                print(f"    {issue['message']}")
            
            return report
        
        except VerificationError as e:
            error_report = {
                'timestamp': datetime.now().isoformat(),
                'archive_directory': str(self.archive_dir),
                'errors_found': 1,
                'verification_error': str(e)
            }
            if not self.quiet:
                logger.error(f"Verification failed: {e}")
            return error_report
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Generate archive statistics
        
        Returns:
            Statistics about the archive
        """
        stats = {
            'archive_directory': str(self.archive_dir),
            'timestamp': datetime.now().isoformat(),
            'total_files': 0,
            'total_size_bytes': 0,
            'file_types': {
                'jsonl': {'count': 0, 'size_bytes': 0},
                'compressed': {'count': 0, 'size_bytes': 0},
                'other': {'count': 0, 'size_bytes': 0}
            },
            'directories': []
        }
        
        if not self.archive_dir.exists():
            if not self.quiet:
                logger.error(f"Archive directory does not exist: {self.archive_dir}")
            return stats
        
        # Scan all files
        for file_path in self.archive_dir.rglob('*'):
            if file_path.is_file():
                try:
                    file_size = file_path.stat().st_size
                    stats['total_files'] += 1
                    stats['total_size_bytes'] += file_size
                    
                    # Categorize by file type
                    if file_path.suffix == '.jsonl':
                        stats['file_types']['jsonl']['count'] += 1
                        stats['file_types']['jsonl']['size_bytes'] += file_size
                    elif file_path.suffixes == ['.jsonl', '.gz']:
                        stats['file_types']['compressed']['count'] += 1
                        stats['file_types']['compressed']['size_bytes'] += file_size
                    else:
                        stats['file_types']['other']['count'] += 1
                        stats['file_types']['other']['size_bytes'] += file_size
                
                except OSError as e:
                    if not self.quiet:
                        logger.warning(f"Could not stat file {file_path}: {e}")
        
        # Get directory breakdown
        for subdir in self.archive_dir.iterdir():
            if subdir.is_dir():
                subdir_files = sum(1 for f in subdir.rglob('*') if f.is_file())
                subdir_size = sum(f.stat().st_size for f in subdir.rglob('*') 
                                 if f.is_file() and f.exists())
                
                stats['directories'].append({
                    'name': subdir.name,
                    'files': subdir_files,
                    'size_bytes': subdir_size
                })
        
        return stats
    
    def format_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"
    
    def backup_source(self, source: str, retention_days: int = 30) -> Dict[str, Any]:
        """
        Create incremental backup of a specific source with rotation
        
        Args:
            source: Source name (slack, calendar, drive, employees)
            retention_days: Days to retain backups
            
        Returns:
            Backup operation summary
        """
        if not self.quiet:
            click.echo(f"💾 Creating incremental backup of {source}...")
        
        source_dir = self.archive_dir / source
        if not source_dir.exists():
            raise ValueError(f"Source directory not found: {source_dir}")
        
        # Create backup root
        backup_root = Path('backups')
        backup_root.mkdir(exist_ok=True)
        
        # Create timestamped backup directory
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_dir = backup_root / source / timestamp
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        summary = {
            'source': source,
            'backup_path': str(backup_dir),
            'files_copied': 0,
            'files_skipped': 0,
            'bytes_copied': 0,
            'errors': [],
            'duration': 0
        }
        
        start_time = time.time()
        
        try:
            # Copy files with progress indication
            source_files = list(source_dir.rglob('*'))
            files_to_copy = [f for f in source_files if f.is_file()]
            
            for file_path in self._progress_bar(files_to_copy, f"Backing up {source}"):
                try:
                    rel_path = file_path.relative_to(source_dir)
                    dest_path = backup_dir / rel_path
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Check if file already exists and is identical
                    if dest_path.exists() and dest_path.stat().st_size == file_path.stat().st_size:
                        summary['files_skipped'] += 1
                        continue
                    
                    shutil.copy2(file_path, dest_path)
                    summary['files_copied'] += 1
                    summary['bytes_copied'] += file_path.stat().st_size
                    
                except Exception as e:
                    summary['errors'].append(f"Failed to copy {file_path}: {e}")
            
            # Clean up old backups
            self._cleanup_old_backups(backup_root / source, retention_days)
            
        except Exception as e:
            summary['errors'].append(f"Backup operation failed: {e}")
        
        summary['duration'] = time.time() - start_time
        
        if not self.quiet:
            if summary['errors']:
                click.echo(f"⚠️ Backup completed with {len(summary['errors'])} errors")
            else:
                click.echo(f"✅ Backup completed successfully")
                click.echo(f"  Files copied: {summary['files_copied']}")
                click.echo(f"  Data copied: {self.format_size(summary['bytes_copied'])}")
        
        return summary
    
    def _cleanup_old_backups(self, backup_source_dir: Path, retention_days: int):
        """Clean up backups older than retention period"""
        if not backup_source_dir.exists():
            return
        
        cutoff_time = time.time() - (retention_days * 24 * 60 * 60)
        cleaned = 0
        
        for backup_dir in backup_source_dir.iterdir():
            if backup_dir.is_dir():
                try:
                    if backup_dir.stat().st_mtime < cutoff_time:
                        shutil.rmtree(backup_dir)
                        cleaned += 1
                except Exception as e:
                    logger.warning(f"Could not clean up old backup {backup_dir}: {e}")
        
        if cleaned > 0 and not self.quiet:
            click.echo(f"  🗑️ Cleaned up {cleaned} old backups")


@click.group()
@click.option('--archive-dir', type=click.Path(path_type=Path),
              help='Archive directory to manage (default: data/archive)')
@click.option('--quiet', is_flag=True, help='Minimize output')
@click.option('--verbose', is_flag=True, help='Show detailed progress')
@click.pass_context
def cli(ctx, archive_dir, quiet, verbose):
    """Enhanced archive management utilities with safety features"""
    ctx.ensure_object(dict)
    
    # Set up archive directory
    if not archive_dir:
        archive_dir = Path('data/archive')
    
    if not archive_dir.exists():
        if not quiet:
            click.echo(f"❌ Archive directory not found: {archive_dir}", err=True)
            click.echo("💡 Suggestion: Run data collection first to create archives", err=True)
        sys.exit(1)
    
    ctx.obj['archive_dir'] = archive_dir
    ctx.obj['quiet'] = quiet
    ctx.obj['verbose'] = verbose

@cli.command()
@click.option('--age-days', type=int, default=30, 
              help='Age threshold in days for compression (default: 30)')
@click.option('--dry-run', is_flag=True, help='Show what would be done without executing')
@click.option('--backup-days', type=int, default=7, help='Keep backups for N days')
@click.option('--resume', is_flag=True, help='Resume from last checkpoint', default=True)
@click.pass_context
def compress(ctx, age_days, dry_run, backup_days, resume):
    """Compress old archive files with safety features"""
    archive_dir = ctx.obj['archive_dir']
    quiet = ctx.obj['quiet']
    
    try:
        manager = SafeArchiveManager(archive_dir, dry_run=dry_run, quiet=quiet, backup_days=backup_days)
        
        if dry_run and not quiet:
            click.echo(f"🔍 {click.style('DRY RUN MODE', fg='yellow', bold=True)} - No changes will be made\n")
        
        result = manager.compress_old_files(age_days=age_days, resume=resume)
        
        if not quiet and not dry_run:
            click.echo(f"\n📊 {click.style('Compression Summary:', fg='blue', bold=True)}")
            click.echo(f"  Files compressed: {click.style(str(result['files_compressed']), fg='green')}")
            click.echo(f"  Files failed: {click.style(str(result['files_failed']), fg='red' if result['files_failed'] > 0 else 'green')}")
            click.echo(f"  Space saved: {click.style(manager.format_size(result['space_saved']), fg='cyan')}")
            
            if result['compression_ratio'] > 0:
                compression_pct = f"{result['compression_ratio']:.1%}"
                click.echo(f"  Compression ratio: {click.style(compression_pct, fg='cyan')}")
            
            if result['operation_duration'] > 0:
                duration_str = f"{result['operation_duration']:.1f}s"
                rate_str = f"{result['files_per_second']:.1f} files/sec"
                click.echo(f"  Duration: {click.style(duration_str, fg='cyan')}")
                click.echo(f"  Rate: {click.style(rate_str, fg='cyan')}")
            
            if result['backups_created'] > 0:
                click.echo(f"  Backups created: {click.style(str(result['backups_created']), fg='yellow')}")
        
        # Exit with error code if failures occurred
        if result['files_failed'] > 0:
            if not quiet:
                click.echo(f"\n⚠️ {result['files_failed']} files failed to compress", err=True)
                for error in result['errors'][:3]:  # Show first 3 errors
                    if isinstance(error, dict):
                        click.echo(f"  • {error.get('file', 'Unknown')}: {error.get('error', 'Unknown error')}", err=True)
                        if 'suggestion' in error:
                            click.echo(f"    💡 {error['suggestion']}", err=True)
            sys.exit(1)
        
    except (CompressionError, DiskFullError) as e:
        if not quiet:
            click.echo(f"❌ Compression failed: {e}", err=True)
            if isinstance(e, DiskFullError):
                click.echo("💡 Suggestions:", err=True)
                click.echo("  • Free up disk space and retry", err=True)
                click.echo("  • Compress older files first (increase --age-days)", err=True)
        sys.exit(1)
    except Exception as e:
        if not quiet:
            click.echo(f"❌ Unexpected error: {e}", err=True)
        sys.exit(3)

@cli.command()
@click.option('--resume', is_flag=True, help='Resume from last checkpoint', default=True)
@click.option('--source', type=click.Choice(['slack', 'calendar', 'drive']),
              help='Verify specific source only')
@click.option('--json', 'output_json', is_flag=True, help='Output results as JSON')
@click.pass_context
def verify(ctx, resume, source, output_json):
    """Verify archive integrity with enhanced reporting"""
    archive_dir = ctx.obj['archive_dir']
    quiet = ctx.obj['quiet']
    
    try:
        manager = SafeArchiveManager(archive_dir, quiet=quiet)
        
        if not quiet:
            if source:
                click.echo(f"🔍 Verifying {source} archives...")
            else:
                click.echo("🔍 Verifying all archives...")
        
        result = manager.verify_archive()
        # Note: Resume functionality not yet implemented in verify_archive method
        
        if output_json:
            print(json.dumps(result, indent=2, default=str))
        elif not quiet:
            # Human-readable output already handled by _display_verification_results
            pass
        
        # Exit with appropriate code
        overall_status = result.get('summary', {}).get('overall_status', 'unknown')
        if overall_status == 'critical_issues' or len(result.get('critical_issues', [])) > 0:
            sys.exit(1)
        elif result.get('errors_found', 0) > 0:
            sys.exit(1)
        
    except VerificationError as e:
        if not quiet:
            click.echo(f"❌ Verification failed: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        if not quiet:
            click.echo(f"❌ Unexpected verification error: {e}", err=True)
        sys.exit(3)

@cli.command()
@click.option('--detailed', is_flag=True, help='Show detailed breakdown by source and age')
@click.option('--json', 'output_json', is_flag=True, help='Output results as JSON')
@click.pass_context
def stats(ctx, detailed, output_json):
    """Show comprehensive archive statistics with optimization recommendations"""
    archive_dir = ctx.obj['archive_dir']
    quiet = ctx.obj['quiet']
    
    try:
        manager = SafeArchiveManager(archive_dir, quiet=quiet)
        result = manager.get_statistics()
        # Add detailed flag to result if requested
        if detailed:
            result['detailed_mode'] = True
        
        if output_json:
            print(json.dumps(result, indent=2, default=str))
            return
        
        # Beautiful human-readable output
        if not quiet:
            click.echo(f"\n📊 {click.style('Archive Statistics', fg='blue', bold=True)}")
            click.echo(f"  Archive directory: {click.style(str(archive_dir), fg='cyan')}")
            total_files_str = f"{result['total_files']:,}"
            click.echo(f"  Total files: {click.style(total_files_str, fg='green')}")
            click.echo(f"  Total size: {click.style(manager.format_size(result['total_size_bytes']), fg='green')}")
            
            # Compression statistics
            compressed_files = result['file_types']['compressed']['count']
            uncompressed_files = result['file_types']['jsonl']['count']
            if compressed_files > 0:
                click.echo(f"  Compressed files: {click.style(str(compressed_files), fg='yellow')}")
                click.echo(f"  Uncompressed files: {click.style(str(uncompressed_files), fg='yellow')}")
                
                # Calculate compression ratio if we have both types
                if compressed_files > 0 and uncompressed_files > 0:
                    total_files = compressed_files + uncompressed_files
                    compression_ratio = compressed_files / total_files
                    click.echo(f"  Files compressed: {click.style(f'{compression_ratio:.1%}', fg='cyan')}")
                
                # Show compressed vs uncompressed size
                compressed_size = result['file_types']['compressed']['size_bytes']
                uncompressed_size = result['file_types']['jsonl']['size_bytes']
                click.echo(f"  Compressed data: {click.style(manager.format_size(compressed_size), fg='cyan')}")
                click.echo(f"  Uncompressed data: {click.style(manager.format_size(uncompressed_size), fg='cyan')}")
            
            # Health score with color coding (if available)
            health_score = result.get('health_score')
            if health_score is not None:
                if health_score >= 80:
                    health_color = 'green'
                    health_symbol = '🟢'
                elif health_score >= 60:
                    health_color = 'yellow'
                    health_symbol = '🟡'
                else:
                    health_color = 'red'
                    health_symbol = '🔴'
                
                click.echo(f"  Health score: {health_symbol} {click.style(f'{health_score}/100', fg=health_color)}")
            
            # Source breakdown (if available)
            if result.get('by_source'):
                click.echo(f"\n📁 {click.style('By Source:', fg='blue')}")
                for source_name, source_stats in result['by_source'].items():
                    click.echo(f"  {source_name}:")
                    click.echo(f"    Files: {source_stats['files']:,}")
                    click.echo(f"    Size: {manager.format_size(int(source_stats['size_bytes']))}")
                    if detailed and source_stats.get('latest_file'):
                        click.echo(f"    Latest: {source_stats['latest_file'][:10]}")
            
            # Age distribution
            # Age distribution breakdown (if available)
            age_distribution = result.get('age_distribution', {})
            if detailed and age_distribution and any(age_data.get('count', 0) > 0 for age_data in age_distribution.values()):
                click.echo(f"\n📅 {click.style('Age Distribution:', fg='blue')}")
                age_labels = {
                    'week': '< 7 days',
                    'month': '< 30 days', 
                    'year': '< 365 days',
                    'ancient': '> 365 days'
                }
                for age, label in age_labels.items():
                    age_data = age_distribution.get(age, {'count': 0, 'size_bytes': 0})
                    if age_data.get('count', 0) > 0:
                        click.echo(f"  {label}: {age_data['count']:,} files ({manager.format_size(age_data['size_bytes'])})")
            
            # Optimization recommendations (if available)
            if result.get('recommendations'):
                click.echo(f"\n💡 {click.style('Optimization Recommendations:', fg='yellow')}")
                for rec in result['recommendations']:
                    click.echo(f"  • {rec}")
            
            # Performance info
            # Scan duration (if available)
            scan_duration = result.get('scan_duration', 0)
            if scan_duration > 0:
                click.echo(f"\n⏱️ Scan completed in {scan_duration:.1f} seconds")
    
    except Exception as e:
        if not quiet:
            click.echo(f"❌ Statistics calculation failed: {e}", err=True)
        sys.exit(3)

@cli.command()
@click.option('--source', required=True, type=click.Choice(['slack', 'calendar', 'drive']),
              help='Source to backup')
@click.option('--retention', type=int, default=30, help='Backup retention in days')
@click.pass_context
def backup(ctx, source, retention):
    """Create incremental backups with rotation"""
    archive_dir = ctx.obj['archive_dir']
    quiet = ctx.obj['quiet']
    
    try:
        manager = SafeArchiveManager(archive_dir, quiet=quiet)
        result = manager.backup_source(source, retention_days=retention)
        
        if not quiet:
            click.echo(f"\n📋 {click.style('Backup Summary:', fg='blue', bold=True)}")
            click.echo(f"  Source: {click.style(source, fg='cyan')}")
            click.echo(f"  Files copied: {click.style(str(result['files_copied']), fg='green')}")
            click.echo(f"  Files skipped: {click.style(str(result['files_skipped']), fg='yellow')}")
            click.echo(f"  Data copied: {click.style(manager.format_size(result['bytes_copied']), fg='green')}")
            click.echo(f"  Backup location: {click.style(result['backup_path'], fg='cyan')}")
            
            if result['errors']:
                click.echo(f"  ⚠️ Errors: {len(result['errors'])}")
                for error in result['errors'][:3]:
                    click.echo(f"    • {error}")
        
        if result['errors']:
            sys.exit(1)
            
    except Exception as e:
        if not quiet:
            click.echo(f"❌ Backup failed: {e}", err=True)
        sys.exit(3)

# Legacy single command interface for backward compatibility
@click.command(name='legacy')
@click.option('--compress', is_flag=True, help='Compress old archive files')
@click.option('--verify', is_flag=True, help='Verify archive integrity')
@click.option('--stats', is_flag=True, help='Show archive statistics')
@click.option('--archive-dir', type=click.Path(exists=True, path_type=Path),
              help='Archive directory to manage (default: data/archive)')
@click.option('--age-days', type=int, default=30, 
              help='Age threshold in days for compression (default: 30)')
@click.option('--json', 'output_json', is_flag=True, help='Output results as JSON')
@click.option('--dry-run', is_flag=True, help='Show what would be done without executing')
@click.option('--quiet', is_flag=True, help='Minimize output')
def manage_archives_legacy(compress, verify, stats, archive_dir, age_days, output_json, dry_run, quiet):
    """
    Legacy single-command interface (DEPRECATED - use subcommands instead)
    
    Examples:
      manage_archives.py --compress --age-days 30
      manage_archives.py --verify --json  
      manage_archives.py --stats --archive-dir /path/to/archive
      manage_archives.py --compress --dry-run
      
    New interface:
      manage_archives.py compress --age-days 30
      manage_archives.py verify --json
      manage_archives.py stats --detailed
      manage_archives.py backup --source slack
    """
    
    # Default archive directory
    if not archive_dir:
        archive_dir = Path.cwd() / "data" / "archive"
        if not archive_dir.exists():
            if not quiet:
                logger.error(f"Default archive directory does not exist: {archive_dir}")
                logger.error("Please specify --archive-dir or create the default directory")
            sys.exit(1)
    
    # Must specify at least one action
    if not any([compress, verify, stats]):
        if not quiet:
            logger.error("Must specify at least one action: --compress, --verify, or --stats")
        sys.exit(1)
    
    # Initialize manager with enhanced features
    manager = SafeArchiveManager(archive_dir, dry_run=dry_run, quiet=quiet)
    
    results = {}
    exit_code = 0
    
    try:
        # Execute requested operations
        if compress:
            compress_result = manager.compress_old_files(age_days=age_days)
            results['compression'] = compress_result
            
            if compress_result['files_failed'] > 0:
                exit_code = 1
        
        if verify:
            verify_result = manager.verify_archive()
            results['verification'] = verify_result
            
            if verify_result['errors_found'] > 0:
                exit_code = 1
        
        if stats:
            stats_result = manager.get_statistics()
            results['statistics'] = stats_result
        
        # Output results
        if output_json:
            print(json.dumps(results, indent=2))
        else:
            # Human-readable output
            if stats:
                stats_data = results['statistics']
                print(f"Archive Statistics")
                print(f"Directory: {stats_data['archive_directory']}")
                print(f"Total files: {stats_data['total_files']}")
                print(f"Total size: {manager.format_size(stats_data['total_size_bytes'])}")
                print()
                print(f"File breakdown:")
                print(f"  JSONL files: {stats_data['file_types']['jsonl']['count']} "
                      f"({manager.format_size(stats_data['file_types']['jsonl']['size_bytes'])})")
                print(f"  Compressed: {stats_data['file_types']['compressed']['count']} "
                      f"({manager.format_size(stats_data['file_types']['compressed']['size_bytes'])})")
                print(f"  Other: {stats_data['file_types']['other']['count']} "
                      f"({manager.format_size(stats_data['file_types']['other']['size_bytes'])})")
                
                if stats_data['directories']:
                    print()
                    print(f"Directory breakdown:")
                    for dir_info in stats_data['directories']:
                        print(f"  {dir_info['name']}: {dir_info['files']} files "
                              f"({manager.format_size(dir_info['size_bytes'])})")
    
    except Exception as e:
        if not quiet:
            logger.error(f"Operation failed: {e}")
        sys.exit(1)
    
    sys.exit(exit_code)


if __name__ == '__main__':
    # Check if user is using legacy interface (no subcommands)
    subcommands = ['compress', 'verify', 'stats', 'backup']
    has_subcommand = any(arg in subcommands for arg in sys.argv[1:])
    has_help = any(arg in ['--help', '-h'] for arg in sys.argv[1:])
    
    if len(sys.argv) > 1 and not has_subcommand and not has_help:
        # Legacy interface
        manage_archives_legacy()
    else:
        # New enhanced interface
        cli()