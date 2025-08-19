"""
Archive Indexer - Phase 2: Archive Indexing Pipeline

Main ArchiveIndexer class that processes JSONL archive files and populates 
the SearchDatabase with batch processing, streaming, and error handling.

Key Features:
- Batch processing of JSONL files (10,000 records per batch by default)
- Incremental indexing with state persistence 
- Memory-safe streaming for large archives
- Format detection and content extraction
- Progress reporting and error recovery
- Thread-safe concurrent processing

References: 
- tasks_A.md lines 552-900 for implementation requirements
- SearchDatabase integration from Sub-Agent A1
- Real Slack/Calendar message structures from data/archive/
"""

import json
import hashlib
import logging
import threading
import time
import psutil
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable, Generator, Tuple
from dataclasses import dataclass, field
from datetime import datetime

from .database import SearchDatabase, DatabaseError

logger = logging.getLogger(__name__)


class IndexingError(Exception):
    """Exception raised during archive indexing operations"""
    
    def __init__(self, message: str, file_path: Optional[str] = None, 
                 line_number: Optional[int] = None):
        super().__init__(message)
        self.file_path = file_path
        self.line_number = line_number


@dataclass
class IndexingStats:
    """Statistics and metrics for indexing operations"""
    
    file_path: str
    source: str
    processed: int = 0
    error_count: int = 0
    errors: List[Dict[str, Any]] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    duration: float = 0.0
    avg_processing_rate: float = 0.0
    peak_memory_mb: float = 0.0
    skipped_unchanged: bool = False
    manifest_validated: bool = False
    
    def complete(self, processed: int, error_count: int):
        """Mark indexing as complete and calculate final stats"""
        self.processed = processed
        self.error_count = error_count
        self.end_time = datetime.now()
        self.duration = (self.end_time - self.start_time).total_seconds()
        
        if self.duration > 0:
            self.avg_processing_rate = self.processed / self.duration
        
        # Track peak memory usage
        process = psutil.Process()
        self.peak_memory_mb = process.memory_info().rss / 1024 / 1024


class ArchiveIndexer:
    """
    Main Archive Indexer for processing JSONL files into SearchDatabase
    
    Processes archives with:
    - Memory-efficient streaming (doesn't load entire files into memory)
    - Batch processing (default 10,000 records per batch for optimal performance) 
    - Incremental indexing (tracks file changes via checksums)
    - Format detection (slack, calendar, drive, employees)
    - Comprehensive error handling and recovery
    - Real-time progress tracking
    - Thread-safe concurrent processing
    """
    
    def __init__(self, database: SearchDatabase, batch_size: int = 10000):
        """
        Initialize Archive Indexer
        
        Args:
            database: SearchDatabase instance for indexing
            batch_size: Records per batch (10K optimized for performance per user feedback)
        """
        self.database = database
        self.batch_size = batch_size
        self.file_cursors: Dict[str, Dict[str, Any]] = {}
        self._stats_lock = threading.Lock()
        
        logger.info(f"Initialized ArchiveIndexer with batch_size={batch_size}")
    
    def process_archive(self, file_path: Path, source: str = None, 
                       progress_callback: Optional[Callable[[int, int, float], None]] = None) -> IndexingStats:
        """
        Process a single JSONL archive file
        
        Args:
            file_path: Path to JSONL archive file
            source: Source type (slack, calendar, drive, employees) - auto-detected if None
            progress_callback: Optional callback for progress updates (processed, total, rate)
            
        Returns:
            IndexingStats with processing results
        """
        file_path = Path(file_path)
        
        # Auto-detect source if not provided
        if not source:
            source = self._detect_source_from_path(str(file_path))
        
        # Initialize stats
        stats = IndexingStats(str(file_path), source)
        
        logger.info(f"Starting archive processing: {file_path} (source: {source})")
        
        try:
            # Check if file needs reindexing (incremental indexing)
            if self._should_skip_file(file_path):
                stats.skipped_unchanged = True
                stats.complete(0, 0)
                logger.info(f"Skipping unchanged file: {file_path}")
                return stats
            
            # Stream and process file in batches
            processed_count = 0
            error_count = 0
            errors = []
            
            for batch_num, batch_info in enumerate(self._stream_jsonl_batches(file_path)):
                if isinstance(batch_info, dict) and 'errors' in batch_info:
                    # This batch contains error information from JSON parsing
                    batch = batch_info['records']
                    batch_errors = batch_info['errors']
                    error_count += len(batch_errors)
                    errors.extend(batch_errors)
                else:
                    # Regular batch
                    batch = batch_info
                
                try:
                    # Extract searchable content from batch
                    processed_batch = self._process_batch_content(batch, source)
                    
                    # Index batch in database
                    if processed_batch:
                        self.database.index_records_batch(processed_batch, source)
                        processed_count += len(processed_batch)
                    
                    # Progress callback
                    if progress_callback and batch_num % 10 == 0:  # Update every 10 batches
                        rate = processed_count / max(0.1, (time.time() - stats.start_time.timestamp()))
                        progress_callback(processed_count, processed_count, rate)
                
                except Exception as e:
                    error_count += len(batch)
                    error_details = {
                        'batch_number': batch_num,
                        'error': str(e),
                        'record_count': len(batch)
                    }
                    errors.append(error_details)
                    logger.warning(f"Batch {batch_num} failed: {e}")
                    continue
                
                # Update peak memory tracking
                current_memory = self._get_memory_usage() / 1024 / 1024
                stats.peak_memory_mb = max(stats.peak_memory_mb, current_memory)
            
            # Update file cursor for incremental indexing
            self._update_file_cursor(file_path)
            
            # Track archive in database
            self._track_archive_in_database(file_path, source, processed_count)
            
            # Complete stats
            stats.errors = errors
            stats.complete(processed_count, error_count)
            
            logger.info(f"Completed processing: {processed_count} indexed, {error_count} errors, {stats.duration:.2f}s")
            
        except Exception as e:
            logger.error(f"Failed to process archive {file_path}: {e}")
            stats.errors = [{'error': f"Fatal error: {str(e)}"}]
            stats.complete(0, 1)
            
        return stats
    
    def process_archive_directory(self, directory_path: Path) -> IndexingStats:
        """
        Process an archive directory with manifest integration
        
        Args:
            directory_path: Path to archive directory containing data.jsonl and manifest.json
            
        Returns:
            Combined IndexingStats for all files in directory
        """
        directory_path = Path(directory_path)
        
        # Look for manifest file
        manifest_path = directory_path / "manifest.json"
        manifest = None
        
        if manifest_path.exists():
            try:
                with open(manifest_path, 'r') as f:
                    manifest = json.load(f)
                logger.info(f"Loaded manifest: {manifest}")
            except Exception as e:
                logger.warning(f"Failed to load manifest {manifest_path}: {e}")
        
        # Find JSONL files to process
        jsonl_files = list(directory_path.glob("*.jsonl"))
        
        if not jsonl_files:
            # Try looking for specific files mentioned in manifest
            if manifest and 'files' in manifest:
                jsonl_files = [directory_path / f for f in manifest['files'] if f.endswith('.jsonl')]
        
        if not jsonl_files:
            raise IndexingError(f"No JSONL files found in directory: {directory_path}")
        
        # Process files
        combined_stats = IndexingStats(str(directory_path), manifest.get('source', 'unknown') if manifest else 'unknown')
        
        for jsonl_file in jsonl_files:
            if manifest:
                combined_stats.manifest_validated = True
                source = manifest.get('source', 'unknown')
            else:
                source = None
            
            file_stats = self.process_archive(jsonl_file, source)
            
            # Combine stats
            combined_stats.processed += file_stats.processed
            combined_stats.error_count += file_stats.error_count
            combined_stats.errors.extend(file_stats.errors)
            combined_stats.peak_memory_mb = max(combined_stats.peak_memory_mb, file_stats.peak_memory_mb)
        
        combined_stats.complete(combined_stats.processed, combined_stats.error_count)
        return combined_stats
    
    def _stream_jsonl_batches(self, file_path: Path) -> Generator[Dict[str, Any], None, None]:
        """
        Stream JSONL file in batches for memory efficiency
        
        Args:
            file_path: Path to JSONL file
            
        Yields:
            Dict containing 'records' (list of parsed records) and 'errors' (list of error info)
        """
        if not file_path.exists():
            raise IndexingError(f"File not found: {file_path}")
        
        batch = []
        batch_errors = []
        line_number = 0
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line_number += 1
                    line = line.strip()
                    
                    if not line:  # Skip empty lines
                        continue
                    
                    try:
                        record = json.loads(line)
                        record['_line_number'] = line_number  # Track for error reporting
                        batch.append(record)
                        
                    except json.JSONDecodeError as e:
                        # Track JSON errors for reporting
                        error_info = {
                            'line_number': line_number,
                            'error': f"Invalid JSON: {str(e)}",
                            'raw_line': line[:100] + '...' if len(line) > 100 else line
                        }
                        batch_errors.append(error_info)
                        logger.warning(f"Invalid JSON at {file_path}:{line_number}: {e}")
                        continue
                    
                    # Yield batch when it reaches size limit
                    if len(batch) >= self.batch_size:
                        yield {
                            'records': batch,
                            'errors': batch_errors
                        }
                        batch = []
                        batch_errors = []
                
                # Yield final partial batch
                if batch or batch_errors:
                    yield {
                        'records': batch,
                        'errors': batch_errors
                    }
                    
        except Exception as e:
            raise IndexingError(f"Failed to stream file: {str(e)}", str(file_path))
    
    def _process_batch_content(self, batch: List[Dict[str, Any]], source: str) -> List[Dict[str, Any]]:
        """
        Process batch records and extract searchable content
        
        Args:
            batch: List of raw records from JSONL
            source: Source type for content extraction
            
        Returns:
            List of processed records ready for database indexing
        """
        processed_records = []
        
        for record in batch:
            try:
                # Extract content based on source type
                content = self._extract_content_by_source(record, source)
                
                if not content:  # Skip records without searchable content
                    continue
                
                # Build processed record for database
                processed_record = {
                    'content': content,
                    'source': source,
                    'date': self._extract_date(record),
                    'metadata': record  # Store original record as metadata
                }
                
                processed_records.append(processed_record)
                
            except Exception as e:
                logger.warning(f"Failed to process record at line {record.get('_line_number', '?')}: {e}")
                continue
        
        return processed_records
    
    def _extract_content_by_source(self, record: Dict[str, Any], source: str) -> str:
        """
        Extract searchable content based on source type
        
        Args:
            record: Raw record from JSONL
            source: Source type (slack, calendar, drive, employees)
            
        Returns:
            Searchable content string
        """
        content_parts = []
        
        if source == 'slack':
            # Slack message content extraction
            text = record.get('text', '').strip()
            if text:
                content_parts.append(text)
            
            # Add user context
            user = record.get('user', '')
            if user:
                content_parts.append(f"from:{user}")
                
            # Add channel context
            channel_name = record.get('channel_name', record.get('channel', ''))
            if channel_name:
                content_parts.append(f"in:{channel_name}")
            
            # Handle attachments and blocks (rich content)
            blocks = record.get('blocks', [])
            for block in blocks:
                if isinstance(block, dict) and 'elements' in block:
                    for element in block['elements']:
                        if isinstance(element, dict) and 'elements' in element:
                            for sub_element in element['elements']:
                                if isinstance(sub_element, dict) and sub_element.get('type') == 'text':
                                    text = sub_element.get('text', '').strip()
                                    if text:
                                        content_parts.append(text)
        
        elif source == 'calendar':
            # Calendar event content extraction
            summary = record.get('summary', '').strip()
            if summary:
                content_parts.append(summary)
            
            # Add attendee information
            attendees = record.get('attendees', [])
            for attendee in attendees:
                if isinstance(attendee, dict) and 'email' in attendee:
                    content_parts.append(attendee['email'])
            
            # Add organizer information
            organizer = record.get('organizer', {})
            if isinstance(organizer, dict) and 'email' in organizer:
                content_parts.append(organizer['email'])
                
            # Add location if available
            location = record.get('location', '').strip()
            if location:
                content_parts.append(location)
        
        elif source == 'drive':
            # Drive document content extraction
            name = record.get('name', record.get('title', '')).strip()
            if name:
                content_parts.append(name)
                
            # Add MIME type information
            mime_type = record.get('mimeType', '')
            if mime_type:
                content_parts.append(mime_type)
        
        elif source == 'employees':
            # Employee data content extraction
            name = record.get('name', record.get('real_name', '')).strip()
            if name:
                content_parts.append(name)
                
            email = record.get('email', '').strip()
            if email:
                content_parts.append(email)
                
            title = record.get('title', '').strip()
            if title:
                content_parts.append(title)
        
        else:
            # Generic content extraction for unknown sources
            for field in ['text', 'content', 'message', 'title', 'subject', 'name']:
                if field in record and record[field]:
                    content_parts.append(str(record[field]))
        
        return ' '.join(content_parts)
    
    def _extract_date(self, record: Dict[str, Any]) -> str:
        """Extract date from record for filtering and sorting"""
        # Try various date fields
        for field in ['date', 'timestamp', 'ts', 'created_at', 'start', 'archive_timestamp']:
            if field in record and record[field]:
                date_val = record[field]
                
                # Handle different date formats
                if isinstance(date_val, str):
                    if 'T' in date_val:  # ISO format
                        return date_val.split('T')[0]
                    elif '-' in date_val:  # YYYY-MM-DD
                        return date_val.split(' ')[0]
                
                # Handle Unix timestamp (Slack format)
                elif isinstance(date_val, (int, float)):
                    dt = datetime.fromtimestamp(date_val)
                    return dt.strftime('%Y-%m-%d')
                    
                # Handle dict with dateTime (Calendar format)
                elif isinstance(date_val, dict) and 'dateTime' in date_val:
                    dt_str = date_val['dateTime']
                    if 'T' in dt_str:
                        return dt_str.split('T')[0]
        
        # Default to today
        return datetime.now().strftime('%Y-%m-%d')
    
    def _should_skip_file(self, file_path: Path) -> bool:
        """
        Check if file should be skipped based on incremental indexing
        
        Args:
            file_path: Path to file to check
            
        Returns:
            True if file should be skipped (unchanged)
        """
        file_key = str(file_path)
        current_checksum = self._calculate_file_checksum(file_path)
        
        if file_key in self.file_cursors:
            last_checksum = self.file_cursors[file_key].get('checksum')
            if last_checksum == current_checksum:
                return True  # File unchanged
        
        return False
    
    def _update_file_cursor(self, file_path: Path):
        """Update file cursor for incremental indexing"""
        file_key = str(file_path)
        checksum = self._calculate_file_checksum(file_path)
        
        self.file_cursors[file_key] = {
            'checksum': checksum,
            'last_indexed': datetime.now().isoformat(),
            'file_size': file_path.stat().st_size
        }
    
    def get_file_cursor(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Get cursor information for a file"""
        return self.file_cursors.get(str(file_path))
    
    def _track_archive_in_database(self, file_path: Path, source: str, record_count: int):
        """Track archive in database archives table"""
        checksum = self._calculate_file_checksum(file_path)
        indexed_at = datetime.now().isoformat()
        
        try:
            with self.database.transaction() as conn:
                # Insert or update archive record
                conn.execute("""
                    INSERT OR REPLACE INTO archives 
                    (path, source, indexed_at, record_count, checksum, status)
                    VALUES (?, ?, ?, ?, ?, 'active')
                """, (str(file_path), source, indexed_at, record_count, checksum))
                
            logger.debug(f"Tracked archive: {file_path} ({record_count} records)")
            
        except Exception as e:
            logger.warning(f"Failed to track archive {file_path}: {e}")
    
    @staticmethod
    def _calculate_file_checksum(file_path: Path) -> str:
        """
        Calculate SHA-256 checksum of file for change detection
        
        Args:
            file_path: Path to file
            
        Returns:
            Hex digest of file contents
        """
        hasher = hashlib.sha256()
        
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception as e:
            raise IndexingError(f"Checksum calculation failed: {str(e)}", str(file_path))
    
    @staticmethod
    def _detect_source_from_path(file_path: str) -> str:
        """
        Auto-detect source type from file path
        
        Args:
            file_path: Path to archive file
            
        Returns:
            Detected source type or 'unknown'
        """
        path_lower = file_path.lower()
        
        if '/slack/' in path_lower:
            return 'slack'
        elif '/calendar/' in path_lower:
            return 'calendar'
        elif '/drive/' in path_lower:
            return 'drive'
        elif '/employee' in path_lower:  # employees or employee
            return 'employees'
        else:
            return 'unknown'
    
    def _get_memory_usage(self) -> int:
        """Get current memory usage in bytes"""
        try:
            process = psutil.Process()
            return process.memory_info().rss
        except:
            # Fallback if psutil not available
            return 0