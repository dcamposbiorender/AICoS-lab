#!/usr/bin/env python3
"""
Enhanced data verification and integrity monitoring system
Ensures archive data integrity through comprehensive SHA-256 checksums and validation

CRITICAL FIXES APPLIED (based on user feedback):
- All dependencies properly imported with fallbacks
- Schema validation for different source types
- Resume capability with checkpoint system
- Compressed file support with transparent decompression
- Progress tracking with real checkpoint saving
- Comprehensive error reporting with line numbers
- Multi-source validation rules

References:
- tasks_B.md: Enhanced verification requirements
- User feedback: Critical dependency and safety fixes
"""

import gzip
import hashlib
import json
import logging
import os
import time
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Iterator
from dataclasses import dataclass, asdict

# Critical fix #3: Proper tqdm import with fallback
try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False
    # Fallback progress bar implementation
    class tqdm:
        def __init__(self, iterable=None, desc=None, total=None, **kwargs):
            self.iterable = iterable or []
            self.desc = desc or ""
            self.total = total or len(self.iterable) if hasattr(self.iterable, '__len__') else 0
            self.current = 0
            if desc:
                print(f"Starting: {desc}")
        
        def __iter__(self):
            for item in self.iterable:
                yield item
                self.current += 1
                if self.current % 100 == 0:
                    print(f"  Progress: {self.current}/{self.total}")
        
        def update(self, n=1):
            self.current += n
            if self.current % 100 == 0:
                print(f"  Progress: {self.current}/{self.total}")
        
        def __enter__(self):
            return self
        
        def __exit__(self, *args):
            print(f"Completed: {self.desc} ({self.current} items)")

logger = logging.getLogger(__name__)


class VerificationError(Exception):
    """Raised when verification operations fail"""
    pass


@dataclass
class RecordVerificationResult:
    """Result of individual record verification"""
    is_valid: bool
    errors: List[str]
    missing_fields: List[str] = None
    line_number: Optional[int] = None
    
    def __post_init__(self):
        if self.missing_fields is None:
            self.missing_fields = []


@dataclass
class VerificationResult:
    """Result of archive verification"""
    path: str
    status: str  # 'valid', 'corrupted', 'missing'
    record_count: int
    file_size: int
    checksum: Optional[str]
    errors: List[str]
    timestamp: str
    source_type: Optional[str] = None
    compression_detected: bool = False
    
    def to_dict(self) -> dict:
        return asdict(self)


class ArchiveVerifier:
    """
    Enhanced verifier for JSONL archives with comprehensive integrity monitoring
    
    Features:
    - SHA-256 checksum calculation and verification
    - Schema validation for different source types (slack, calendar, drive, default)
    - JSONL format validation with line-by-line error reporting  
    - Manifest consistency checking against actual file contents
    - Corruption detection with detailed error reporting
    - Resume capability for interrupted verification operations
    - Compressed file support (.gz, .zst) with transparent decompression
    - Progress tracking with checkpoint saving every 1000 records
    - Record count validation and size verification
    - Multi-source verification with source-specific validation rules
    """
    
    # Data schema requirements for different source types
    REQUIRED_FIELDS = {
        'slack': {'timestamp', 'user', 'text', 'channel'},
        'calendar': {'timestamp', 'summary', 'start', 'end'},
        'drive': {'timestamp', 'name', 'id', 'mimeType'},
        'default': {'timestamp', 'source', 'data'}
    }
    
    # Optional fields that are commonly present
    OPTIONAL_FIELDS = {
        'slack': {'thread_ts', 'reactions', 'files', 'type', 'subtype'},
        'calendar': {'description', 'location', 'attendees', 'organizer'},
        'drive': {'size', 'modifiedTime', 'parents', 'shared'},
        'default': {'metadata', 'context'}
    }
    
    def __init__(self):
        """Initialize verifier with checkpoint and progress tracking"""
        self.checksum_algorithm = 'sha256'
        self._verification_cache = {}
        self.checkpoint_file = Path('.verification_checkpoint.json')
        self.checkpoint_interval = 1000  # Save checkpoint every 1000 records
        self.stats = {
            'files_checked': 0,
            'records_verified': 0,
            'errors': [],
            'warnings': [],
            'sources_detected': {},
            'compression_stats': {
                'compressed_files': 0,
                'uncompressed_files': 0
            }
        }
    
    def verify_record(self, record: Dict, source: str = 'default', line_number: Optional[int] = None) -> RecordVerificationResult:
        """
        Enhanced record validation with comprehensive schema checking
        
        Args:
            record: JSON record to validate
            source: Source type (slack, calendar, drive, default)
            line_number: Line number for error reporting
            
        Returns:
            RecordVerificationResult with validation details
        """
        required = self.REQUIRED_FIELDS.get(source, self.REQUIRED_FIELDS['default'])
        missing = required - set(record.keys())
        errors = []
        
        # Check required fields
        if missing:
            errors.append(f"Missing required fields: {', '.join(missing)}")
        
        # Additional validation based on source type
        if source == 'slack':
            errors.extend(self._validate_slack_record(record))
        elif source == 'calendar':
            errors.extend(self._validate_calendar_record(record))
        elif source == 'drive':
            errors.extend(self._validate_drive_record(record))
        else:
            errors.extend(self._validate_default_record(record))
        
        # Common validations for all sources
        errors.extend(self._validate_common_fields(record))
        
        return RecordVerificationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            missing_fields=list(missing),
            line_number=line_number
        )
    
    def _validate_slack_record(self, record: Dict) -> List[str]:
        """Validate Slack-specific record fields"""
        errors = []
        
        # Validate user field
        if 'user' in record:
            if not record['user'] or not isinstance(record['user'], str):
                errors.append("User field must be non-empty string")
        
        # Validate channel field
        if 'channel' in record:
            if not record['channel'] or not isinstance(record['channel'], str):
                errors.append("Channel field must be non-empty string")
        
        # Validate text field (can be empty for some message types)
        if 'text' in record:
            if not isinstance(record['text'], str):
                errors.append("Text field must be string")
        
        # Validate thread_ts if present
        if 'thread_ts' in record and record['thread_ts']:
            if not isinstance(record['thread_ts'], str):
                errors.append("Thread timestamp must be string")
        
        return errors
    
    def _validate_calendar_record(self, record: Dict) -> List[str]:
        """Validate Calendar-specific record fields"""
        errors = []
        
        # Validate summary
        if 'summary' in record:
            if not record['summary'] or not isinstance(record['summary'], str):
                errors.append("Summary field must be non-empty string")
        
        # Validate start/end times
        for field in ['start', 'end']:
            if field in record:
                if not record[field]:
                    errors.append(f"{field.title()} time cannot be empty")
                elif not isinstance(record[field], str):
                    errors.append(f"{field.title()} time must be string")
        
        # Validate attendees if present
        if 'attendees' in record and record['attendees']:
            if not isinstance(record['attendees'], list):
                errors.append("Attendees must be list")
        
        return errors
    
    def _validate_drive_record(self, record: Dict) -> List[str]:
        """Validate Drive-specific record fields"""
        errors = []
        
        # Validate name
        if 'name' in record:
            if not record['name'] or not isinstance(record['name'], str):
                errors.append("Name field must be non-empty string")
        
        # Validate id
        if 'id' in record:
            if not record['id'] or not isinstance(record['id'], str):
                errors.append("ID field must be non-empty string")
        
        # Validate mimeType
        if 'mimeType' in record:
            if not record['mimeType'] or not isinstance(record['mimeType'], str):
                errors.append("MIME type must be non-empty string")
        
        return errors
    
    def _validate_default_record(self, record: Dict) -> List[str]:
        """Validate default record fields"""
        errors = []
        
        # Validate source
        if 'source' in record:
            if not record['source'] or not isinstance(record['source'], str):
                errors.append("Source field must be non-empty string")
        
        # Validate data field
        if 'data' in record:
            if record['data'] is None:
                errors.append("Data field cannot be null")
        
        return errors
    
    def _validate_common_fields(self, record: Dict) -> List[str]:
        """Validate fields common to all record types"""
        errors = []
        
        # Validate timestamp format
        if 'timestamp' in record:
            if not record['timestamp']:
                errors.append("Timestamp cannot be empty")
            else:
                try:
                    # Try various timestamp formats
                    timestamp_str = record['timestamp']
                    if timestamp_str.endswith('Z'):
                        datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                    else:
                        datetime.fromisoformat(timestamp_str)
                except (ValueError, TypeError):
                    errors.append("Invalid timestamp format - must be ISO format")
        
        # Validate record is not empty
        if not record:
            errors.append("Record cannot be empty")
        
        # Check for null values in required fields
        for key, value in record.items():
            if value is None and key in ['timestamp', 'source']:
                errors.append(f"Critical field '{key}' cannot be null")
        
        return errors
    
    def verify_archive(self, archive_path: Path) -> VerificationResult:
        """
        Verify a single archive directory with enhanced checks
        
        Args:
            archive_path: Path to daily archive directory
            
        Returns:
            VerificationResult with comprehensive status and details
        """
        errors = []
        
        # Check directory exists
        if not archive_path.exists():
            return VerificationResult(
                path=str(archive_path),
                status='missing',
                record_count=0,
                file_size=0,
                checksum=None,
                errors=[f"Archive directory not found: {archive_path}"],
                timestamp=datetime.now().isoformat()
            )
        
        # Look for data files with multiple possible extensions
        data_file_candidates = [
            archive_path / 'data.jsonl',
            archive_path / 'data.jsonl.gz',
            archive_path / 'data.jsonl.zst'
        ]
        
        actual_data_file = None
        compression_detected = False
        
        # Find the actual data file
        for candidate in data_file_candidates:
            if candidate.exists():
                actual_data_file = candidate
                compression_detected = candidate.suffix in ['.gz', '.zst']
                break
        
        if actual_data_file is None:
            errors.append(f"No data file found. Looked for: {[str(f) for f in data_file_candidates]}")
            return VerificationResult(
                path=str(archive_path),
                status='missing',
                record_count=0,
                file_size=0,
                checksum=None,
                errors=errors,
                timestamp=datetime.now().isoformat()
            )
        
        # Calculate actual values
        try:
            file_size = actual_data_file.stat().st_size
            checksum = self._calculate_checksum(actual_data_file)
            record_count, format_errors = self._validate_jsonl_format(actual_data_file)
            errors.extend(format_errors)
            
            # Detect source type from path
            source_type = self._detect_source(actual_data_file)
            
        except Exception as e:
            errors.append(f"Verification failed: {str(e)}")
            return VerificationResult(
                path=str(archive_path),
                status='corrupted',
                record_count=0,
                file_size=0,
                checksum=None,
                errors=errors,
                timestamp=datetime.now().isoformat()
            )
        
        # Verify against manifest if it exists
        manifest_file = archive_path / 'manifest.json'
        if manifest_file.exists():
            manifest_errors = self._verify_manifest(
                manifest_file, record_count, file_size, checksum
            )
            errors.extend(manifest_errors)
        else:
            errors.append("Manifest file missing - consider regenerating")
        
        # Determine final status
        status = 'valid' if not errors else 'corrupted'
        
        # Update stats
        self.stats['sources_detected'][source_type] = self.stats['sources_detected'].get(source_type, 0) + 1
        if compression_detected:
            self.stats['compression_stats']['compressed_files'] += 1
        else:
            self.stats['compression_stats']['uncompressed_files'] += 1
        
        return VerificationResult(
            path=str(archive_path),
            status=status,
            record_count=record_count,
            file_size=file_size,
            checksum=checksum,
            errors=errors,
            timestamp=datetime.now().isoformat(),
            source_type=source_type,
            compression_detected=compression_detected
        )
    
    def verify_jsonl_file(self, file_path: Path, resume_from_line: int = 0) -> Dict:
        """
        Verify JSONL file with progress tracking and schema validation
        
        Args:
            file_path: Path to JSONL file (compressed or uncompressed)
            resume_from_line: Line number to resume from (for checkpoint recovery)
            
        Returns:
            Dict with verification results and statistics
        """
        errors = []
        line_count = 0
        valid_records = 0
        
        # Determine source from path
        source = self._detect_source(file_path)
        
        try:
            # Handle both compressed and uncompressed files
            opener = self._get_file_opener(file_path)
            
            with opener(file_path, 'rt', encoding='utf-8') as f:
                # Skip lines if resuming
                if resume_from_line > 0:
                    for _ in range(resume_from_line):
                        next(f, None)
                    line_count = resume_from_line
                
                # Get total lines for progress (expensive but informative)
                if HAS_TQDM and resume_from_line == 0:
                    total_lines = sum(1 for _ in opener(file_path, 'rt', encoding='utf-8'))
                    progress_bar = tqdm(total=total_lines, desc=f"Verifying {file_path.name}")
                else:
                    progress_bar = tqdm([], desc=f"Verifying {file_path.name}")
                
                with progress_bar:
                    for line in f:
                        line_count += 1
                        
                        line = line.strip()
                        if not line:
                            continue
                        
                        try:
                            record = json.loads(line)
                            result = self.verify_record(record, source, line_count)
                            
                            if result.is_valid:
                                valid_records += 1
                            else:
                                for error in result.errors:
                                    errors.append({
                                        'line': line_count,
                                        'error': error,
                                        'source_type': source
                                    })
                            
                        except json.JSONDecodeError as e:
                            errors.append({
                                'line': line_count,
                                'error': f"Invalid JSON: {e}",
                                'source_type': source
                            })
                        
                        # Update progress
                        if HAS_TQDM:
                            progress_bar.update(1)
                        
                        # Save checkpoint periodically  
                        if line_count % self.checkpoint_interval == 0:
                            self._save_checkpoint(file_path, line_count)
                            logger.debug(f"Checkpoint saved at line {line_count}")
        
        except Exception as e:
            errors.append({'file': str(file_path), 'error': str(e), 'source_type': source})
        
        # Update global stats
        self.stats['records_verified'] += line_count
        
        return {
            'file': str(file_path),
            'source_type': source,
            'lines_processed': line_count,
            'valid_records': valid_records,
            'errors': errors,
            'error_count': len(errors),
            'is_valid': len(errors) == 0,
            'compression_detected': file_path.suffix in ['.gz', '.zst']
        }
    
    def verify_directory(self, directory: Path, resume: bool = True) -> Dict:
        """
        Verify all archive files in directory with resume capability
        
        Args:
            directory: Directory containing archive files
            resume: Whether to resume from checkpoint
            
        Returns:
            Dict with comprehensive verification statistics
        """
        start_time = time.time()
        
        # Load checkpoint if resuming
        start_from_file = None
        start_from_line = 0
        
        if resume and self.checkpoint_file.exists():
            checkpoint = self.load_checkpoint()
            start_from_file = checkpoint.get('last_file')
            start_from_line = checkpoint.get('line_number', 0)
            logger.info(f"Resuming verification from {start_from_file}:{start_from_line}")
        
        # Find all archive files (both compressed and uncompressed)
        patterns = ['*.jsonl', '*.jsonl.gz', '*.jsonl.zst']
        files = []
        for pattern in patterns:
            files.extend(directory.rglob(pattern))
        
        # Sort for consistent ordering
        files.sort()
        
        if not files:
            logger.warning(f"No archive files found in {directory}")
            return self.stats
        
        # Skip to checkpoint file if resuming
        if start_from_file:
            try:
                start_idx = next(i for i, f in enumerate(files) if str(f) == start_from_file)
                files = files[start_idx:]
                logger.info(f"Found checkpoint file at index {start_idx}")
            except StopIteration:
                logger.warning(f"Checkpoint file {start_from_file} not found, starting from beginning")
                start_from_line = 0
        
        # Verify each file with progress tracking
        total_files = len(files)
        
        for i, file_path in enumerate(files, 1):
            resume_line = start_from_line if i == 1 and start_from_file else 0
            
            logger.info(f"Verifying file {i}/{total_files}: {file_path.name}")
            
            try:
                result = self.verify_jsonl_file(file_path, resume_from_line=resume_line)
                
                self.stats['files_checked'] += 1
                
                if result['errors']:
                    self.stats['errors'].extend(result['errors'])
                    logger.warning(f"Found {len(result['errors'])} errors in {file_path}")
                else:
                    logger.info(f"✓ File verified successfully: {result['valid_records']} valid records")
                
            except Exception as e:
                error_info = {
                    'file': str(file_path),
                    'error': f"Verification failed: {str(e)}",
                    'source_type': 'unknown'
                }
                self.stats['errors'].append(error_info)
                logger.error(f"Failed to verify {file_path}: {e}")
            
            # Reset line counter after first file
            start_from_line = 0
        
        # Calculate final statistics
        elapsed_time = time.time() - start_time
        self.stats['verification_time'] = elapsed_time
        self.stats['files_per_second'] = self.stats['files_checked'] / elapsed_time if elapsed_time > 0 else 0
        
        # Clean up checkpoint on successful completion
        if self.stats['errors']:
            logger.info(f"Verification completed with {len(self.stats['errors'])} errors")
        else:
            logger.info("✓ All files verified successfully")
            self.checkpoint_file.unlink(missing_ok=True)
        
        return self.stats
    
    def _calculate_checksum(self, file_path: Path) -> str:
        """
        Calculate SHA-256 checksum of file (handles compressed files)
        
        Args:
            file_path: Path to file
            
        Returns:
            SHA-256 checksum as hex string
        """
        hasher = hashlib.sha256()
        
        # Handle compressed files transparently
        opener = self._get_file_opener(file_path)
        
        try:
            with opener(file_path, 'rb') as f:
                # Read in chunks to handle large files
                while chunk := f.read(65536):
                    hasher.update(chunk)
        except Exception as e:
            logger.error(f"Failed to calculate checksum for {file_path}: {e}")
            raise VerificationError(f"Checksum calculation failed: {e}")
        
        return hasher.hexdigest()
    
    def _get_file_opener(self, file_path: Path):
        """Get appropriate file opener based on file extension"""
        if file_path.suffix == '.gz':
            return gzip.open
        elif file_path.suffix == '.zst':
            try:
                import zstandard as zstd
                # Create a wrapper that matches gzip.open interface
                class ZstdOpen:
                    def __init__(self):
                        self.dctx = zstd.ZstdDecompressor()
                    
                    def __call__(self, file_path, mode='rb', **kwargs):
                        if 'r' in mode:
                            return self.dctx.stream_reader(open(file_path, 'rb'))
                        else:
                            raise ValueError("Only read mode supported for zstd")
                
                return ZstdOpen()
            except ImportError:
                logger.warning("zstandard library not available, cannot read .zst files")
                raise VerificationError("Cannot read .zst files: zstandard library not installed")
        else:
            return open
    
    def _validate_jsonl_format(self, file_path: Path) -> Tuple[int, List[str]]:
        """
        Validate JSONL format and count records with comprehensive schema checking
        
        Args:
            file_path: Path to JSONL file
            
        Returns:
            Tuple of (record_count, list_of_errors)
        """
        errors = []
        record_count = 0
        source = self._detect_source(file_path)
        
        try:
            opener = self._get_file_opener(file_path)
            
            with opener(file_path, 'rt', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        record = json.loads(line)
                        record_count += 1
                        
                        # Basic validation
                        if not isinstance(record, dict):
                            errors.append(f"Line {line_num}: Not a JSON object")
                        else:
                            # Schema validation
                            result = self.verify_record(record, source, line_num)
                            if not result.is_valid:
                                for error in result.errors:
                                    errors.append(f"Line {line_num}: {error}")
                        
                    except json.JSONDecodeError as e:
                        errors.append(f"Line {line_num}: Invalid JSON - {str(e)}")
                    
                    # Limit errors reported to avoid overwhelming output
                    if len(errors) > 1000:
                        errors.append(f"Error limit reached - stopping validation (1000+ errors found)")
                        break
        
        except Exception as e:
            errors.append(f"Failed to read file: {str(e)}")
        
        return record_count, errors
    
    def _verify_manifest(self, manifest_file: Path, actual_count: int,
                        actual_size: int, actual_checksum: str) -> List[str]:
        """
        Verify manifest against actual values
        
        Args:
            manifest_file: Path to manifest.json file
            actual_count: Actual record count from verification
            actual_size: Actual file size
            actual_checksum: Actual file checksum
            
        Returns:
            List of manifest verification errors
        """
        errors = []
        
        try:
            with open(manifest_file, 'r', encoding='utf-8') as f:
                manifest = json.load(f)
            
            # Check required fields
            required = ['source', 'record_count', 'file_size', 'last_write']
            for field in required:
                if field not in manifest:
                    errors.append(f"Manifest missing required field: {field}")
            
            # Verify record count matches
            if 'record_count' in manifest:
                manifest_count = manifest['record_count']
                if manifest_count != actual_count:
                    errors.append(
                        f"Record count mismatch: manifest={manifest_count}, "
                        f"actual={actual_count} (difference: {actual_count - manifest_count})"
                    )
            
            # Verify file size (allow some tolerance for line ending differences)
            if 'file_size' in manifest:
                manifest_size = manifest['file_size']
                size_diff = abs(manifest_size - actual_size)
                # Allow up to 1% difference or 1KB, whichever is larger
                tolerance = max(manifest_size * 0.01, 1024)
                if size_diff > tolerance:
                    errors.append(
                        f"File size mismatch: manifest={manifest_size}, "
                        f"actual={actual_size} (difference: {size_diff} bytes)"
                    )
            
            # Verify checksum if present
            if 'checksum' in manifest:
                if manifest['checksum'] != actual_checksum:
                    errors.append(
                        f"Checksum mismatch - data may be corrupted. "
                        f"Expected: {manifest['checksum'][:16]}..., "
                        f"Got: {actual_checksum[:16]}..."
                    )
            
            # Check timestamp format
            if 'last_write' in manifest:
                try:
                    datetime.fromisoformat(manifest['last_write'].replace('Z', '+00:00'))
                except (ValueError, TypeError):
                    errors.append("Manifest last_write timestamp is invalid format")
        
        except json.JSONDecodeError:
            errors.append("Manifest file contains invalid JSON")
        except Exception as e:
            errors.append(f"Failed to read manifest: {str(e)}")
        
        return errors
    
    def _detect_source(self, file_path: Path) -> str:
        """
        Detect data source from file path
        
        Args:
            file_path: Path to data file
            
        Returns:
            Detected source type (slack, calendar, drive, default)
        """
        path_str = str(file_path).lower()
        
        # Check path components for source indicators
        for source in ['slack', 'calendar', 'drive', 'employee']:
            if source in path_str:
                return source if source != 'employee' else 'employees'
        
        return 'default'
    
    def _save_checkpoint(self, file_path: Path, line_num: int):
        """
        Save verification checkpoint for resume capability
        
        Args:
            file_path: Current file being verified
            line_num: Current line number
        """
        checkpoint = {
            'last_file': str(file_path),
            'line_number': line_num,
            'records_verified': self.stats['records_verified'],
            'files_checked': self.stats['files_checked'],
            'timestamp': datetime.now().isoformat(),
            'version': '1.0'
        }
        
        try:
            # Atomic write using temp file
            temp_checkpoint = self.checkpoint_file.with_suffix('.tmp')
            with open(temp_checkpoint, 'w') as f:
                json.dump(checkpoint, f, indent=2)
            temp_checkpoint.rename(self.checkpoint_file)
        except Exception as e:
            logger.warning(f"Failed to save checkpoint: {e}")
    
    def load_checkpoint(self) -> Dict:
        """
        Load verification checkpoint
        
        Returns:
            Checkpoint data or empty dict if no checkpoint exists
        """
        if not self.checkpoint_file.exists():
            return {}
        
        try:
            with open(self.checkpoint_file) as f:
                checkpoint = json.load(f)
            
            # Update stats from checkpoint
            if 'records_verified' in checkpoint:
                self.stats['records_verified'] = checkpoint['records_verified']
            if 'files_checked' in checkpoint:
                self.stats['files_checked'] = checkpoint['files_checked']
            
            return checkpoint
        except Exception as e:
            logger.warning(f"Failed to load checkpoint: {e}")
            return {}
    
    def verify_source_archives(self, source_name: str, base_dir: Path,
                              days_back: int = 7) -> Dict[str, VerificationResult]:
        """
        Verify all archives for a specific source over multiple days
        
        Args:
            source_name: Name of source (slack, calendar, drive, employees)
            base_dir: Base archive directory
            days_back: Number of days to check
            
        Returns:
            Dict mapping date strings to verification results
        """
        results = {}
        source_dir = base_dir / source_name
        
        if not source_dir.exists():
            logger.warning(f"Source directory not found: {source_dir}")
            return results
        
        # Check last N days
        today = date.today()
        
        for days_ago in range(days_back):
            check_date = today - timedelta(days=days_ago)
            date_str = check_date.isoformat()
            archive_path = source_dir / date_str
            
            if archive_path.exists():
                logger.info(f"Verifying {source_name} archive for {date_str}")
                result = self.verify_archive(archive_path)
                results[date_str] = result
                
                if result.status != 'valid':
                    logger.warning(
                        f"Issues found in {source_name}/{date_str}: "
                        f"{len(result.errors)} errors"
                    )
                else:
                    logger.info(f"✓ {source_name}/{date_str} verified successfully")
            else:
                logger.info(f"No archive found for {source_name}/{date_str}")
        
        return results
    
    def generate_verification_report(self, results: Dict[str, VerificationResult]) -> Dict:
        """
        Generate comprehensive verification report from results
        
        Args:
            results: Dict of verification results
            
        Returns:
            Summary report with statistics and recommendations
        """
        report = {
            'timestamp': datetime.now().isoformat(),
            'verification_summary': {
                'total_archives': len(results),
                'valid': 0,
                'corrupted': 0,
                'missing': 0
            },
            'data_statistics': {
                'total_records': 0,
                'total_size_bytes': 0,
                'compression_stats': self.stats['compression_stats'].copy()
            },
            'source_breakdown': {},
            'error_summary': [],
            'recommendations': []
        }
        
        # Process each result
        for date_str, result in results.items():
            # Update summary counts
            report['verification_summary'][result.status] += 1
            report['data_statistics']['total_records'] += result.record_count
            report['data_statistics']['total_size_bytes'] += result.file_size
            
            # Track by source type
            source = result.source_type or 'unknown'
            if source not in report['source_breakdown']:
                report['source_breakdown'][source] = {
                    'archives': 0,
                    'valid': 0,
                    'corrupted': 0,
                    'missing': 0,
                    'total_records': 0,
                    'total_size': 0
                }
            
            source_stats = report['source_breakdown'][source]
            source_stats['archives'] += 1
            source_stats[result.status] += 1
            source_stats['total_records'] += result.record_count
            source_stats['total_size'] += result.file_size
            
            # Collect error details
            if result.errors:
                report['error_summary'].append({
                    'date': date_str,
                    'source': source,
                    'error_count': len(result.errors),
                    'errors': result.errors[:5]  # Limit to first 5 errors
                })
        
        # Calculate success rates
        total = report['verification_summary']['total_archives']
        if total > 0:
            report['verification_summary']['success_rate'] = (
                report['verification_summary']['valid'] / total
            )
        else:
            report['verification_summary']['success_rate'] = 0.0
        
        # Generate recommendations
        report['recommendations'] = self._generate_recommendations(report)
        
        return report
    
    def _generate_recommendations(self, report: Dict) -> List[str]:
        """Generate recommendations based on verification results"""
        recommendations = []
        
        success_rate = report['verification_summary']['success_rate']
        total_archives = report['verification_summary']['total_archives']
        corrupted_count = report['verification_summary']['corrupted']
        
        if success_rate < 0.95 and total_archives > 0:
            recommendations.append(
                f"Success rate is {success_rate:.1%}. Consider investigating "
                f"{corrupted_count} corrupted archives."
            )
        
        if report['verification_summary']['missing'] > 0:
            recommendations.append(
                "Missing archives detected. Check data collection process."
            )
        
        # Check compression stats
        comp_stats = report['data_statistics']['compression_stats']
        total_files = comp_stats['compressed_files'] + comp_stats['uncompressed_files']
        if total_files > 0:
            compression_rate = comp_stats['compressed_files'] / total_files
            if compression_rate < 0.7:
                recommendations.append(
                    f"Only {compression_rate:.1%} of files are compressed. "
                    "Consider enabling automatic compression for older files."
                )
        
        # Check for source-specific issues
        for source, stats in report['source_breakdown'].items():
            if stats['corrupted'] > 0:
                recommendations.append(
                    f"Source '{source}' has {stats['corrupted']} corrupted archives. "
                    f"Check collection process for this source."
                )
        
        if not recommendations:
            recommendations.append("All archives verified successfully. No issues detected.")
        
        return recommendations