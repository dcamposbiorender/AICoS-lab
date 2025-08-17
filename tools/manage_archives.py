#!/usr/bin/env python3
"""
Archive Management CLI Tool
Unified interface for compression, verification, and statistics

References: CLAUDE.md commandments about production quality tools
"""

import click
import json
import sys
from pathlib import Path
from typing import Dict, Any, List
import logging
from datetime import datetime

# Import our utilities
# Add src to path so we can import from src.core
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.compression import Compressor, CompressionError

# Import verify_archive from same directory
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))
from verify_archive import ArchiveVerifier, VerificationError

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class ArchiveManager:
    """
    Unified archive management tool
    
    Provides compression, verification, and statistics functionality
    for archive directories in a single convenient interface.
    """
    
    def __init__(self, archive_dir: Path, dry_run: bool = False, quiet: bool = False):
        """
        Initialize archive manager
        
        Args:
            archive_dir: Root archive directory to manage
            dry_run: If True, show what would be done without executing
            quiet: If True, minimize output
        """
        self.archive_dir = archive_dir
        self.dry_run = dry_run
        self.quiet = quiet
        
        if quiet:
            logging.getLogger().setLevel(logging.WARNING)
        
        # Initialize components
        self.compressor = Compressor()
        self.verifier = ArchiveVerifier()
    
    def compress_old_files(self, age_days: int = 30) -> Dict[str, Any]:
        """
        Compress files older than specified age
        
        Args:
            age_days: Compress files older than this many days
            
        Returns:
            Summary of compression operation
        """
        if not self.archive_dir.exists():
            raise CompressionError(f"Archive directory does not exist: {self.archive_dir}")
        
        # Find old files
        old_files = self.compressor.find_old_files(self.archive_dir, age_days=age_days)
        
        summary = {
            'files_found': len(old_files),
            'files_compressed': 0,
            'files_failed': 0,
            'total_size_before': 0,
            'total_size_after': 0,
            'errors': []
        }
        
        if not old_files:
            if not self.quiet:
                print(f"No files older than {age_days} days found")
            return summary
        
        # Calculate total size before compression
        for file_path in old_files:
            try:
                summary['total_size_before'] += file_path.stat().st_size
            except OSError:
                pass
        
        if not self.quiet:
            if self.dry_run:
                print(f"Would compress {len(old_files)} files older than {age_days} days")
            else:
                print(f"Compressing {len(old_files)} files older than {age_days} days...")
        
        # Compress each file
        for file_path in old_files:
            try:
                if self.dry_run:
                    if not self.quiet:
                        print(f"Would compress: {file_path}")
                else:
                    compressed_path = self.compressor.compress(file_path)
                    summary['files_compressed'] += 1
                    summary['total_size_after'] += compressed_path.stat().st_size
                    
                    if not self.quiet:
                        print(f"Compressed: {file_path} -> {compressed_path}")
            
            except CompressionError as e:
                summary['files_failed'] += 1
                summary['errors'].append(f"Failed to compress {file_path}: {e}")
                if not self.quiet:
                    logger.error(f"Failed to compress {file_path}: {e}")
        
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


@click.command()
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
def manage_archives(compress, verify, stats, archive_dir, age_days, output_json, dry_run, quiet):
    """
    Archive management CLI tool
    
    Provides compression, verification, and statistics for archive directories.
    
    Examples:
      manage_archives.py --compress --age-days 30
      manage_archives.py --verify --json  
      manage_archives.py --stats --archive-dir /path/to/archive
      manage_archives.py --compress --dry-run
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
    
    # Initialize manager
    manager = ArchiveManager(archive_dir, dry_run=dry_run, quiet=quiet)
    
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
    manage_archives()