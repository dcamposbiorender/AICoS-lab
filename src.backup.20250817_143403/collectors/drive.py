"""
DriveArchiveWrapper - Minimal lab-grade Drive collector.

For lab-grade implementation, this provides basic metadata collection
without file content storage. Returns mock data for testing purposes.
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
import logging
import hashlib

# Import our base collector
from src.collectors.base import BaseArchiveCollector

logger = logging.getLogger(__name__)


class DriveArchiveWrapper(BaseArchiveCollector):
    """
    Enhanced Drive collector for lab-grade testing with DriveToRag patterns.
    
    Returns mock Drive metadata with file type categorization, change detection,
    and content hashing patterns inspired by DriveToRag workflow analysis.
    This provides a foundation for future content extraction capabilities.
    """
    
    # MIME type categories inspired by DriveToRag workflow
    MIME_TYPE_CATEGORIES = {
        'docs': [
            'application/vnd.google-apps.document',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/msword'
        ],
        'pdf': ['application/pdf'],
        'html': ['text/html'],
        'spreadsheets': [
            'application/vnd.google-apps.spreadsheet',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'application/vnd.ms-excel',
            'text/csv'
        ],
        'images': [
            'image/png',
            'image/jpeg', 
            'image/jpg',
            'image/gif',
            'image/bmp'
        ],
        'presentations': [
            'application/vnd.google-apps.presentation',
            'application/vnd.openxmlformats-officedocument.presentationml.presentation'
        ]
    }
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize DriveArchiveWrapper with minimal configuration.
        
        Args:
            config: Configuration dictionary (not used in lab-grade version)
        """
        super().__init__("drive", config or {})
        logger.info("DriveArchiveWrapper initialized in lab-grade mode (mock data only)")
    
    def collect(self) -> Dict[str, Any]:
        """
        Collect Drive metadata with DriveToRag-inspired patterns.
        
        Enhanced lab-grade implementation with:
        - File type categorization using MIME types
        - Content hashing (mock) for change detection
        - File lifecycle tracking
        - Comprehensive metadata collection
        
        Returns:
            Dictionary containing enhanced mock drive data and metadata
        """
        logger.info("Starting Drive metadata collection (lab-grade mock)")
        
        # Enhanced lab-grade mock data with DriveToRag patterns
        mock_files = [
            {
                'id': 'file_001',
                'name': 'Project Plan.docx',
                'mimeType': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'size': '245760',
                'modifiedTime': '2025-08-15T08:30:00.000Z',
                'createdTime': '2025-08-14T14:20:00.000Z',
                'owners': [{'emailAddress': 'user@company.com', 'displayName': 'Project Lead'}],
                'shared': False,
                'mock_content': 'Q3 2025 Project Plan - Executive Summary and roadmap for AI Chief of Staff implementation...'
            },
            {
                'id': 'file_002',
                'name': 'Meeting Notes',
                'mimeType': 'application/vnd.google-apps.document',
                'size': '12800',
                'modifiedTime': '2025-08-15T10:15:00.000Z',
                'createdTime': '2025-08-15T09:45:00.000Z',
                'owners': [{'emailAddress': 'user@company.com', 'displayName': 'Meeting Host'}],
                'shared': True,
                'mock_content': 'Meeting with development team. Discussed Phase 1a completion and next steps for Phase 1b...'
            },
            {
                'id': 'file_003',
                'name': 'Budget Analysis Q3.xlsx',
                'mimeType': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'size': '98304',
                'modifiedTime': '2025-08-15T12:00:00.000Z',
                'createdTime': '2025-08-12T09:00:00.000Z',
                'owners': [{'emailAddress': 'finance@company.com', 'displayName': 'Finance Team'}],
                'shared': True,
                'mock_content': 'Q3 Budget Analysis - Development costs, infrastructure expenses, projected ROI...'
            },
            {
                'id': 'file_004',
                'name': 'Architecture Diagram.png',
                'mimeType': 'image/png',
                'size': '512000',
                'modifiedTime': '2025-08-14T16:45:00.000Z',
                'createdTime': '2025-08-14T16:45:00.000Z',
                'owners': [{'emailAddress': 'architect@company.com', 'displayName': 'System Architect'}],
                'shared': False,
                'mock_content': 'System architecture diagram showing data flow from collectors to search indices...'
            }
        ]

        # Add file categorization and hashing inspired by DriveToRag
        enhanced_files = []
        for file_data in mock_files:
            # Categorize file type
            file_category = self._categorize_file(file_data['mimeType'])
            
            # Generate mock content hash (SHA256)
            mock_content = file_data.pop('mock_content', '')
            content_hash = self._generate_content_hash(mock_content)
            
            # Enhance file data
            enhanced_file = {
                **file_data,
                'category': file_category,
                'content_hash': content_hash,
                'extractable': file_category in ['docs', 'pdf', 'spreadsheets'],
                'processing_priority': self._get_processing_priority(file_category),
                'estimated_extraction_time': self._estimate_extraction_time(file_data['size'], file_category)
            }
            enhanced_files.append(enhanced_file)

        mock_drive_data = {
            'files': enhanced_files,
            'changes': [
                {
                    'changeId': 'change_001',
                    'time': '2025-08-15T10:15:00.000Z',
                    'type': 'file',
                    'operation': 'updated',
                    'fileId': 'file_002',
                    'content_hash_changed': True,
                    'previous_hash': '8b2f5e1a...',  # Mock previous hash
                    'new_hash': enhanced_files[1]['content_hash'] if len(enhanced_files) > 1 else 'mock_hash'
                },
                {
                    'changeId': 'change_002',
                    'time': '2025-08-15T12:00:00.000Z',
                    'type': 'file',
                    'operation': 'created',
                    'fileId': 'file_003',
                    'content_hash_changed': True,
                    'new_hash': enhanced_files[2]['content_hash'] if len(enhanced_files) > 2 else 'mock_hash'
                }
            ],
            'collection_metadata': {
                'total_files_scanned': len(enhanced_files),
                'private_files_excluded': 0,
                'shared_files_included': sum(1 for f in enhanced_files if f['shared']),
                'changes_tracked': 2,
                'file_type_breakdown': self._get_file_type_breakdown(enhanced_files),
                'extractable_files': sum(1 for f in enhanced_files if f['extractable']),
                'total_estimated_extraction_time': sum(f['estimated_extraction_time'] for f in enhanced_files)
            }
        }
        
        # Add archive transformation metadata
        transformed_data = {
            **mock_drive_data,
            'archive_transformation': {
                'transformer': 'DriveArchiveWrapper',
                'version': '1.0-lab',
                'mode': 'mock_data_only',
                'transformation_timestamp': datetime.now(timezone.utc).isoformat(),
                'data_integrity': {
                    'files_processed': len(mock_drive_data['files']),
                    'changes_processed': len(mock_drive_data['changes']),
                    'content_excluded': True,  # Lab-grade: no file content
                    'privacy_filtering': False  # Lab-grade: simplified
                }
            }
        }
        
        logger.info(f"Drive collection complete: {len(mock_drive_data['files'])} files, {len(mock_drive_data['changes'])} changes")
        
        return {
            'data': transformed_data,
            'metadata': self.get_metadata()
        }
    
    def _categorize_file(self, mime_type: str) -> str:
        """Categorize file based on MIME type (inspired by DriveToRag)."""
        for category, mime_types in self.MIME_TYPE_CATEGORIES.items():
            if mime_type in mime_types:
                return category
        return 'other'
    
    def _generate_content_hash(self, content: str) -> str:
        """Generate SHA256 hash of content (mock implementation)."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()[:16] + "..."
    
    def _get_processing_priority(self, category: str) -> int:
        """Get processing priority based on file category."""
        priority_map = {
            'docs': 1,      # Highest priority
            'pdf': 1,       # Highest priority  
            'spreadsheets': 2,  # Medium priority
            'images': 3,    # Lower priority (requires OCR)
            'presentations': 2,
            'other': 4      # Lowest priority
        }
        return priority_map.get(category, 4)
    
    def _estimate_extraction_time(self, size: str, category: str) -> float:
        """Estimate content extraction time in seconds."""
        size_bytes = int(size) if size.isdigit() else 1000
        size_mb = size_bytes / (1024 * 1024)
        
        time_per_mb = {
            'docs': 0.5,      # Fast - direct API access
            'pdf': 2.0,       # Moderate - text extraction
            'spreadsheets': 1.0,  # Moderate - structured data
            'images': 5.0,    # Slow - OCR required
            'presentations': 1.5,
            'other': 1.0
        }
        
        return max(1.0, size_mb * time_per_mb.get(category, 1.0))
    
    def _get_file_type_breakdown(self, files: List[Dict[str, Any]]) -> Dict[str, int]:
        """Get breakdown of files by category."""
        breakdown = {}
        for file_data in files:
            category = file_data.get('category', 'other')
            breakdown[category] = breakdown.get(category, 0) + 1
        return breakdown
    
    def get_state(self) -> Dict[str, Any]:
        """Get current collection state with enhanced DriveToRag patterns."""
        with self._state_lock:
            base_state = self._state.copy()
            # Add enhanced drive-specific state
            base_state.update({
                'last_change_id': 'change_002',
                'files_tracked': 4,
                'content_hashes_tracked': True,
                'file_categories_supported': list(self.MIME_TYPE_CATEGORIES.keys()),
                'extraction_ready_files': 3,  # docs + pdf + spreadsheets
                'last_categorization_update': datetime.now(timezone.utc).isoformat()
            })
            return base_state
    
    def set_state(self, state: Dict[str, Any]) -> None:
        """Update collection state (minimal for lab-grade)."""
        with self._state_lock:
            self._state.update(state)
            logger.debug(f"Drive state updated with {len(state)} fields")


# Convenience function for creating wrapper instances
def create_drive_wrapper(config: Optional[Dict[str, Any]] = None) -> DriveArchiveWrapper:
    """
    Create a DriveArchiveWrapper instance with optional configuration.
    
    Args:
        config: Configuration dictionary (not used in lab-grade)
        
    Returns:
        Configured DriveArchiveWrapper instance
    """
    return DriveArchiveWrapper(config)