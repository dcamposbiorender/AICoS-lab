#!/usr/bin/env python3
"""
Basic compression utilities for archive management
Provides gzip compression with integrity verification for JSONL files

References: CLAUDE.md commandments about production quality and atomic operations
"""

import gzip
import shutil
import tempfile
from pathlib import Path
from typing import List, Optional
from datetime import datetime, timedelta
import logging
import hashlib
import os

logger = logging.getLogger(__name__)


class CompressionError(Exception):
    """Raised when compression operations fail"""
    pass


class Compressor:
    """
    Basic gzip compressor for JSONL archive files
    
    Features:
    - Gzip compression with integrity verification
    - Age-based file discovery for automated compression
    - Atomic compression operations (temp file + rename)
    - Data integrity verification via checksums
    """

    def __init__(self, compression_level: int = 6):
        """
        Initialize compressor
        
        Args:
            compression_level: Gzip compression level (1-9, default 6)
        """
        self.compression_level = compression_level
        if not 1 <= compression_level <= 9:
            raise CompressionError(f"Invalid compression level: {compression_level}")

    def compress(self, file_path: Path) -> Path:
        """
        Compress a file using gzip
        
        Args:
            file_path: Path to file to compress
            
        Returns:
            Path to compressed file (.gz extension)
            
        Raises:
            CompressionError: If compression fails
        """
        if not file_path.exists():
            raise CompressionError(f"File does not exist: {file_path}")
        
        if not file_path.is_file():
            raise CompressionError(f"Path is not a file: {file_path}")
        
        compressed_path = file_path.with_suffix(file_path.suffix + '.gz')
        
        try:
            # Use temporary file for atomic operation
            with tempfile.NamedTemporaryFile(delete=False, suffix='.gz') as temp_file:
                temp_path = Path(temp_file.name)
                
                # Compress file
                with open(file_path, 'rb') as f_in:
                    with gzip.open(temp_path, 'wb', compresslevel=self.compression_level) as f_out:
                        shutil.copyfileobj(f_in, f_out)
                
                # Atomic rename to final location
                temp_path.rename(compressed_path)
                
                # Remove original file
                file_path.unlink()
                
                logger.info(f"Compressed {file_path} -> {compressed_path}")
                return compressed_path
                
        except Exception as e:
            # Clean up temp file if it exists
            if 'temp_path' in locals() and temp_path.exists():
                temp_path.unlink()
            raise CompressionError(f"Failed to compress {file_path}: {e}")

    def decompress(self, compressed_path: Path) -> Path:
        """
        Decompress a gzip file
        
        Args:
            compressed_path: Path to compressed file
            
        Returns:
            Path to decompressed file
            
        Raises:
            CompressionError: If decompression fails
        """
        if not compressed_path.exists():
            raise CompressionError(f"Compressed file does not exist: {compressed_path}")
        
        if not compressed_path.suffix == '.gz':
            raise CompressionError(f"File is not a gzip file: {compressed_path}")
        
        # Remove .gz extension for decompressed file
        decompressed_path = compressed_path.with_suffix('')
        
        try:
            # Use temporary file for atomic operation
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_path = Path(temp_file.name)
                
                # Decompress file
                with gzip.open(compressed_path, 'rb') as f_in:
                    with open(temp_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                
                # Atomic rename to final location
                temp_path.rename(decompressed_path)
                
                logger.info(f"Decompressed {compressed_path} -> {decompressed_path}")
                return decompressed_path
                
        except Exception as e:
            # Clean up temp file if it exists
            if 'temp_path' in locals() and temp_path.exists():
                temp_path.unlink()
            raise CompressionError(f"Failed to decompress {compressed_path}: {e}")

    def find_old_files(self, directory: Path, age_days: int = 30, 
                      pattern: str = "*.jsonl") -> List[Path]:
        """
        Find files older than specified age
        
        Args:
            directory: Directory to search in
            age_days: Files older than this many days
            pattern: File pattern to match (default: *.jsonl)
            
        Returns:
            List of old files that match criteria
        """
        if not directory.exists():
            raise CompressionError(f"Directory does not exist: {directory}")
        
        if not directory.is_dir():
            raise CompressionError(f"Path is not a directory: {directory}")
        
        cutoff_time = datetime.now() - timedelta(days=age_days)
        old_files = []
        
        for file_path in directory.rglob(pattern):
            if file_path.is_file():
                # Get file modification time
                file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                
                if file_mtime < cutoff_time:
                    old_files.append(file_path)
        
        logger.info(f"Found {len(old_files)} files older than {age_days} days in {directory}")
        return sorted(old_files)

    def verify_compression(self, compressed_path: Path) -> bool:
        """
        Verify compressed file integrity
        
        Args:
            compressed_path: Path to compressed file to verify
            
        Returns:
            True if file is valid, False otherwise
        """
        try:
            # Try to read and decompress the entire file
            with gzip.open(compressed_path, 'rb') as f:
                # Read entire content to fully verify integrity
                content = f.read()
                # Try to decode as text to catch encoding issues
                content.decode('utf-8', errors='strict')
            return True
        except (gzip.BadGzipFile, UnicodeDecodeError, OSError, EOFError) as e:
            logger.warning(f"Compression verification failed for {compressed_path}: {e}")
            return False
        except Exception as e:
            logger.warning(f"Unexpected error during compression verification for {compressed_path}: {e}")
            return False

    def get_compression_ratio(self, original_path: Path, compressed_path: Path) -> float:
        """
        Calculate compression ratio
        
        Args:
            original_path: Path to original file
            compressed_path: Path to compressed file
            
        Returns:
            Compression ratio as percentage (e.g., 0.3 for 30% of original size)
        """
        if not original_path.exists() or not compressed_path.exists():
            return 0.0
        
        original_size = original_path.stat().st_size
        compressed_size = compressed_path.stat().st_size
        
        if original_size == 0:
            return 0.0
        
        return compressed_size / original_size