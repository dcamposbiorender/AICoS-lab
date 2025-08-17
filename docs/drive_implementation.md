# Google Drive Implementation Guide

**Version**: 1.0  
**Date**: 2025-08-16  
**Target Audience**: Implementation Claude or Developer  
**Goal**: Complete Google Drive collector implementation for AI Chief of Staff system

## Overview

This document provides comprehensive guidance for implementing the Google Drive collector that integrates with the existing AI Chief of Staff architecture. The Drive collector will track file metadata and activity without storing content, maintaining privacy while enabling powerful organizational insights.

## 1. API Endpoints Required

### Google Drive API v3 Core Endpoints

```python
# Primary endpoints needed for implementation
REQUIRED_ENDPOINTS = {
    # File discovery and metadata
    'files.list': {
        'url': 'https://www.googleapis.com/drive/v3/files',
        'purpose': 'Discover files with metadata filtering',
        'key_params': ['q', 'fields', 'pageSize', 'pageToken'],
        'rate_limit': '1000 requests/100 seconds per user'
    },
    
    # Individual file metadata
    'files.get': {
        'url': 'https://www.googleapis.com/drive/v3/files/{fileId}',
        'purpose': 'Get detailed metadata for specific file',
        'key_params': ['fileId', 'fields'],
        'rate_limit': '1000 requests/100 seconds per user'
    },
    
    # File activity and changes
    'changes.list': {
        'url': 'https://www.googleapis.com/drive/v3/changes',
        'purpose': 'Track file modifications since last check',
        'key_params': ['pageToken', 'includeRemoved', 'fields'],
        'rate_limit': '1000 requests/100 seconds per user'
    },
    
    # Get starting change token
    'changes.getStartPageToken': {
        'url': 'https://www.googleapis.com/drive/v3/changes/startPageToken',
        'purpose': 'Get initial change token for incremental updates',
        'key_params': [],
        'rate_limit': '1000 requests/100 seconds per user'
    },
    
    # Permission tracking (optional but valuable)
    'permissions.list': {
        'url': 'https://www.googleapis.com/drive/v3/files/{fileId}/permissions',
        'purpose': 'Track file sharing and permission changes',
        'key_params': ['fileId'],
        'rate_limit': '1000 requests/100 seconds per user'
    }
}
```

### Essential Query Parameters

```python
# Query filters for files.list
RECOMMENDED_QUERIES = {
    'recent_activity': "modifiedTime > '2025-01-01T00:00:00Z'",
    'exclude_trash': "trashed = false",
    'documents_only': "mimeType contains 'application/vnd.google-apps'",
    'shared_files': "sharedWithMe = true",
    'owned_files': "'user@company.com' in owners"
}

# Fields to request for comprehensive metadata
METADATA_FIELDS = (
    "files("
    "id,name,mimeType,size,createdTime,modifiedTime,"
    "owners,lastModifyingUser,parents,webViewLink,"
    "shared,permissions,capabilities,exportLinks"
    ")"
)
```

## 2. Authentication Flow

### OAuth 2.0 Implementation

```python
# Complete authentication setup using existing patterns
def setup_drive_authentication(self):
    """
    Set up Google Drive API authentication using existing auth manager
    
    Leverages:
    - src/core/auth_manager.py - Existing credential management
    - data/auth/token.pickle - OAuth token storage
    - data/auth/credentials.json - OAuth app credentials
    """
    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        from google.auth.transport.requests import Request
        from google_auth_oauthlib.flow import InstalledAppFlow
        
        # Required scopes for Drive metadata collection
        SCOPES = [
            'https://www.googleapis.com/auth/drive.readonly',
            'https://www.googleapis.com/auth/drive.metadata.readonly'
        ]
        
        creds = None
        token_path = self.config.auth_dir / "token.pickle"
        credentials_path = self.config.auth_dir / "credentials.json"
        
        # Load existing token if available
        if token_path.exists():
            with open(token_path, 'rb') as token:
                creds = pickle.load(token)
        
        # Refresh or obtain new credentials
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not credentials_path.exists():
                    raise DriveAuthError(
                        "credentials.json not found. Run: python tools/setup_google_oauth.py"
                    )
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    credentials_path, SCOPES
                )
                creds = flow.run_local_server(port=0)
            
            # Save credentials for next run
            with open(token_path, 'wb') as token:
                pickle.dump(creds, token)
        
        # Build and return Drive service
        self.drive_service = build('drive', 'v3', credentials=creds)
        return True
        
    except Exception as e:
        self.log_error(f"Drive authentication failed: {e}")
        return False
```

### Integration with Existing Auth System

```python
# Use existing auth_manager.py patterns
from src.core.auth_manager import credential_vault

class DriveCollector:
    def __init__(self):
        # Leverage existing credential management
        self.auth_manager = credential_vault
        self.credentials = self.auth_manager.get_google_credentials()
```

## 3. Rate Limiting Strategy

### Google Drive API Quotas

```python
# Rate limiting configuration
DRIVE_RATE_LIMITS = {
    'requests_per_100_seconds_per_user': 1000,
    'requests_per_day': 1_000_000_000,  # Very high, unlikely to hit
    'recommended_delay_seconds': 0.1,    # Conservative 100ms between requests
    'backoff_multiplier': 2,             # Exponential backoff on 429 errors
    'max_backoff_seconds': 32,           # Maximum wait time
    'max_retries': 5
}

class DriveRateLimiter:
    """Rate limiter for Google Drive API following existing patterns"""
    
    def __init__(self, requests_per_100_seconds=1000):
        self.requests_per_100_seconds = requests_per_100_seconds
        self.min_delay = 100 / requests_per_100_seconds  # 0.1 seconds default
        self.request_times = []
        self.consecutive_rate_limits = 0
        
    def wait_for_api_limit(self):
        """Conservative rate limiting to prevent 429 errors"""
        current_time = time.time()
        
        # Remove requests older than 100 seconds
        cutoff_time = current_time - 100
        self.request_times = [t for t in self.request_times if t > cutoff_time]
        
        # If approaching limit, wait
        if len(self.request_times) >= self.requests_per_100_seconds * 0.9:
            sleep_time = self.request_times[0] - cutoff_time + 1
            time.sleep(sleep_time)
        else:
            time.sleep(self.min_delay)
        
        self.request_times.append(current_time)
    
    def handle_429_error(self, error):
        """Handle rate limit exceeded errors with exponential backoff"""
        self.consecutive_rate_limits += 1
        
        # Extract retry-after header if present
        retry_after = getattr(error, 'retry_after', None)
        if retry_after:
            wait_time = int(retry_after)
        else:
            wait_time = min(2 ** self.consecutive_rate_limits, 32)
        
        self.log_warning(f"Rate limit hit. Waiting {wait_time} seconds...")
        time.sleep(wait_time)
```

## 4. Data Structure and JSONL Output Format

### File Metadata Schema

```python
# Complete file metadata structure for JSONL output
DRIVE_FILE_SCHEMA = {
    "file_id": "string",                    # Google Drive file ID
    "name": "string",                       # File name
    "mime_type": "string",                  # MIME type (e.g., application/vnd.google-apps.document)
    "size": "integer",                      # File size in bytes (null for Google Docs)
    "created_time": "string",               # ISO 8601 timestamp (UTC)
    "modified_time": "string",              # ISO 8601 timestamp (UTC)
    "owners": "array",                      # List of owner objects with email, displayName
    "last_modifying_user": "object",        # User who last modified (email, displayName)
    "parents": "array",                     # Parent folder IDs
    "web_view_link": "string",              # Shareable link to file
    "shared": "boolean",                    # True if file is shared with others
    "permissions": "array",                 # Permission objects (type, role, email)
    "capabilities": "object",               # What actions user can perform
    "export_links": "object",               # Available export formats for Google Docs
    "collection_timestamp": "string",       # When this record was collected (UTC)
    "change_type": "string",                # "created", "modified", "deleted", "permission_changed"
    "activity_summary": "object"            # Activity metrics (views, comments, etc. if available)
}
```

### JSONL Output Example

```jsonl
{"file_id":"1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms","name":"Example Spreadsheet","mime_type":"application/vnd.google-apps.spreadsheet","size":null,"created_time":"2025-01-15T10:00:00Z","modified_time":"2025-08-16T14:30:00Z","owners":[{"email":"user@company.com","displayName":"John Doe"}],"last_modifying_user":{"email":"user@company.com","displayName":"John Doe"},"parents":["0BwwA4oUTeiV1TGRPeTVjaWRDY1E"],"web_view_link":"https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms","shared":true,"permissions":[{"type":"user","role":"owner","email":"user@company.com"}],"collection_timestamp":"2025-08-16T15:00:00Z","change_type":"modified"}
{"file_id":"1mGVIs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms","name":"Meeting Notes Q3","mime_type":"application/vnd.google-apps.document","size":null,"created_time":"2025-07-20T09:15:00Z","modified_time":"2025-08-16T11:45:00Z","owners":[{"email":"manager@company.com","displayName":"Jane Smith"}],"last_modifying_user":{"email":"team@company.com","displayName":"Team Member"},"parents":["0BwwA4oUTeiV1TGRPeTVjaWRDY1E"],"web_view_link":"https://docs.google.com/document/d/1mGVIs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms","shared":true,"collection_timestamp":"2025-08-16T15:00:00Z","change_type":"modified"}
```

### Daily Archive Structure

```
data/archive/drive/
├── 2025-08-16/
│   ├── drive_metadata.jsonl      # File metadata
│   ├── drive_changes.jsonl       # Change events
│   ├── drive_permissions.jsonl   # Permission changes
│   └── manifest.json            # Collection summary
├── 2025-08-17/
│   └── ...
```

## 5. Implementation Code Structure

### Complete Class Implementation

```python
#!/usr/bin/env python3
"""
Google Drive Collector - Metadata and Activity Tracking
Integrates with AI Chief of Staff archive system
"""

import json
import time
import pickle
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from ..core.config import get_config
from ..core.state import StateManager
from ..core.archive_writer import ArchiveWriter
from .base import BaseArchiveCollector, CollectorError

class DriveCollectorError(CollectorError):
    """Drive-specific collection errors"""
    pass

@dataclass
class DriveCollectionResult:
    """Results from Drive collection operation"""
    files_collected: int
    changes_tracked: int
    permissions_updated: int
    errors: List[str]
    collection_duration: float

class DriveCollector(BaseArchiveCollector):
    """
    Google Drive metadata collector
    
    Collects file metadata and tracks changes without storing content.
    Maintains privacy while providing organizational visibility.
    """
    
    def __init__(self, config_path: Optional[Path] = None):
        super().__init__("drive", config_path)
        
        # Drive-specific configuration
        self.drive_service = None
        self.rate_limiter = DriveRateLimiter()
        self.change_token = None
        
        # Archive writer for JSONL persistence
        self.archive_writer = ArchiveWriter(
            base_path=self.config.archive_path / "drive",
            source_type="drive"
        )
        
    def setup_authentication(self) -> bool:
        """Set up Google Drive API authentication"""
        # Implementation from authentication section above
        return self.setup_drive_authentication()
    
    def discover_files(self, max_files: int = 1000) -> Dict[str, Dict]:
        """
        Discover Drive files with metadata
        
        Args:
            max_files: Maximum number of files to discover
            
        Returns:
            Dictionary mapping file_id -> metadata
        """
        discovered_files = {}
        
        try:
            # Query for recent files
            query = "trashed = false and modifiedTime > '2024-01-01T00:00:00Z'"
            
            request = self.drive_service.files().list(
                q=query,
                fields="nextPageToken, files(id, name, mimeType, size, createdTime, "
                      "modifiedTime, owners, lastModifyingUser, parents, webViewLink, "
                      "shared, permissions)",
                pageSize=min(max_files, 1000)
            )
            
            while request is not None and len(discovered_files) < max_files:
                self.rate_limiter.wait_for_api_limit()
                
                response = request.execute()
                files = response.get('files', [])
                
                for file_metadata in files:
                    file_id = file_metadata['id']
                    discovered_files[file_id] = file_metadata
                
                request = self.drive_service.files().list_next(request, response)
                
            return discovered_files
            
        except Exception as e:
            self.log_error(f"Drive discovery failed: {e}")
            raise DriveCollectorError(f"Discovery failed: {e}")
    
    def collect_file_changes(self, since_token: Optional[str] = None) -> List[Dict]:
        """
        Collect file changes since last check
        
        Args:
            since_token: Change token from previous collection
            
        Returns:
            List of change events
        """
        changes = []
        
        try:
            if since_token is None:
                # Get starting token for first run
                response = self.drive_service.changes().getStartPageToken().execute()
                since_token = response['startPageToken']
                
            request = self.drive_service.changes().list(
                pageToken=since_token,
                includeRemoved=True,
                fields="nextPageToken, newStartPageToken, changes(fileId, removed, file)"
            )
            
            while request is not None:
                self.rate_limiter.wait_for_api_limit()
                
                response = request.execute()
                page_changes = response.get('changes', [])
                
                for change in page_changes:
                    change_data = {
                        'file_id': change['fileId'],
                        'removed': change.get('removed', False),
                        'change_timestamp': datetime.now(timezone.utc).isoformat(),
                        'file_metadata': change.get('file', {})
                    }
                    changes.append(change_data)
                
                # Update token for next collection
                if 'newStartPageToken' in response:
                    self.change_token = response['newStartPageToken']
                
                request = self.drive_service.changes().list_next(request, response)
                
            return changes
            
        except Exception as e:
            self.log_error(f"Change collection failed: {e}")
            raise DriveCollectorError(f"Change collection failed: {e}")
    
    def collect(self) -> DriveCollectionResult:
        """
        Main collection method - implements BaseArchiveCollector interface
        
        Returns:
            Collection results with counts and errors
        """
        start_time = time.time()
        errors = []
        
        try:
            # Phase 1: Authentication
            if not self.setup_authentication():
                raise DriveCollectorError("Authentication failed")
            
            # Phase 2: Load previous state
            previous_state = self.get_state()
            last_change_token = previous_state.get('last_change_token')
            
            # Phase 3: Collect file metadata
            self.log_info("Starting Drive file metadata collection...")
            discovered_files = self.discover_files(max_files=10000)
            
            # Phase 4: Collect changes since last run
            self.log_info("Collecting file changes...")
            changes = self.collect_file_changes(since_token=last_change_token)
            
            # Phase 5: Save to JSONL archives
            files_count = self.save_files_to_archive(list(discovered_files.values()))
            changes_count = self.save_changes_to_archive(changes)
            
            # Phase 6: Update state
            new_state = {
                'last_collection_time': datetime.now(timezone.utc).isoformat(),
                'last_change_token': self.change_token,
                'files_discovered': len(discovered_files),
                'changes_tracked': len(changes)
            }
            self.set_state(new_state)
            
            duration = time.time() - start_time
            
            return DriveCollectionResult(
                files_collected=files_count,
                changes_tracked=changes_count,
                permissions_updated=0,  # TODO: Implement permission tracking
                errors=errors,
                collection_duration=duration
            )
            
        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"Drive collection failed: {e}"
            errors.append(error_msg)
            self.log_error(error_msg)
            
            return DriveCollectionResult(
                files_collected=0,
                changes_tracked=0,
                permissions_updated=0,
                errors=errors,
                collection_duration=duration
            )
    
    def save_files_to_archive(self, files_metadata: List[Dict]) -> int:
        """Save file metadata to JSONL archive"""
        try:
            return self.archive_writer.write_batch(
                records=files_metadata,
                record_type="file_metadata",
                batch_id=f"files_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )
        except Exception as e:
            self.log_error(f"Failed to save files to archive: {e}")
            return 0
    
    def save_changes_to_archive(self, changes: List[Dict]) -> int:
        """Save change events to JSONL archive"""
        try:
            return self.archive_writer.write_batch(
                records=changes,
                record_type="changes",
                batch_id=f"changes_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )
        except Exception as e:
            self.log_error(f"Failed to save changes to archive: {e}")
            return 0

# Rate limiter implementation (from section 3)
class DriveRateLimiter:
    # Implementation from rate limiting section above
    pass
```

## 6. Error Handling and Resilience

### Common Error Scenarios

```python
# Error handling patterns
DRIVE_ERROR_HANDLING = {
    'HttpError 403': {
        'cause': 'Insufficient permissions or quota exceeded',
        'action': 'Check OAuth scopes and API quotas',
        'retry': False
    },
    'HttpError 404': {
        'cause': 'File not found or deleted',
        'action': 'Mark as deleted in change log',
        'retry': False
    },
    'HttpError 429': {
        'cause': 'Rate limit exceeded',
        'action': 'Exponential backoff retry',
        'retry': True
    },
    'HttpError 500': {
        'cause': 'Google API server error',
        'action': 'Retry with exponential backoff',
        'retry': True
    },
    'ConnectionError': {
        'cause': 'Network connectivity issues',
        'action': 'Retry with exponential backoff',
        'retry': True
    }
}

def handle_drive_error(self, error, context: str):
    """Comprehensive error handling for Drive API"""
    if hasattr(error, 'resp') and hasattr(error.resp, 'status'):
        status_code = error.resp.status
        
        if status_code == 429:
            self.rate_limiter.handle_429_error(error)
            return True  # Retry
        elif status_code in [500, 502, 503]:
            wait_time = min(2 ** self.consecutive_errors, 32)
            time.sleep(wait_time)
            return True  # Retry
        elif status_code == 403:
            self.log_error(f"Permission denied for {context}. Check OAuth scopes.")
            return False  # Don't retry
        else:
            self.log_error(f"Drive API error {status_code} in {context}: {error}")
            return False
    else:
        self.log_error(f"Unexpected error in {context}: {error}")
        return False
```

## 7. Testing Strategy

### Unit Tests

```python
# Example test structure
class TestDriveCollector(unittest.TestCase):
    def setUp(self):
        self.collector = DriveCollector()
        
    def test_authentication_setup(self):
        """Test Drive API authentication"""
        # Mock credentials and test auth flow
        pass
        
    def test_file_discovery(self):
        """Test file discovery with various filters"""
        # Test with mock Drive API responses
        pass
        
    def test_change_tracking(self):
        """Test incremental change collection"""
        # Test with mock change tokens
        pass
        
    def test_rate_limiting(self):
        """Test rate limiter prevents 429 errors"""
        # Test rate limiter behavior
        pass
        
    def test_error_handling(self):
        """Test error scenarios and recovery"""
        # Test various error conditions
        pass
```

### Integration Tests

```python
def test_drive_collection_integration(self):
    """Test full Drive collection pipeline"""
    collector = DriveCollector()
    
    # Test authentication
    assert collector.setup_authentication()
    
    # Test file discovery
    files = collector.discover_files(max_files=10)
    assert len(files) >= 0  # Allow for empty Drive
    
    # Test change tracking
    changes = collector.collect_file_changes()
    assert isinstance(changes, list)
    
    # Test JSONL archive creation
    result = collector.collect()
    assert result.files_collected >= 0
    assert len(result.errors) == 0
```

## 8. Privacy and Security Considerations

### Data Minimization

```python
# Only collect essential metadata - NO file content
COLLECTED_FIELDS = [
    'id', 'name', 'mimeType', 'size',
    'createdTime', 'modifiedTime',
    'owners', 'lastModifyingUser',
    'shared', 'webViewLink'
]

# EXPLICITLY EXCLUDE content and thumbnails
EXCLUDED_FIELDS = [
    'thumbnailLink',  # Visual previews
    'content',        # File content (not available via metadata API anyway)
    'exportLinks',    # Links to download content (optional)
]
```

### Access Control

```python
# Respect Drive permissions in collection
def should_collect_file(self, file_metadata: Dict) -> bool:
    """Check if file should be collected based on access"""
    
    # Skip files the user cannot access
    capabilities = file_metadata.get('capabilities', {})
    if not capabilities.get('canRead', False):
        return False
    
    # Skip highly sensitive file types (optional)
    sensitive_patterns = [
        'password', 'private', 'confidential', 'secret'
    ]
    file_name = file_metadata.get('name', '').lower()
    if any(pattern in file_name for pattern in sensitive_patterns):
        self.log_warning(f"Skipping sensitive file: {file_name}")
        return False
    
    return True
```

## 9. Performance Optimization

### Pagination and Batch Processing

```python
# Efficient pagination for large Drive collections
def collect_files_paginated(self, batch_size: int = 1000) -> Iterator[List[Dict]]:
    """Collect files in batches for memory efficiency"""
    
    page_token = None
    
    while True:
        request = self.drive_service.files().list(
            q="trashed = false",
            pageSize=batch_size,
            pageToken=page_token,
            fields="nextPageToken, files(...)"
        )
        
        self.rate_limiter.wait_for_api_limit()
        response = request.execute()
        
        files = response.get('files', [])
        if not files:
            break
            
        yield files
        
        page_token = response.get('nextPageToken')
        if not page_token:
            break
```

### Caching and State Management

```python
def get_cached_file_metadata(self, file_id: str) -> Optional[Dict]:
    """Get cached file metadata to avoid redundant API calls"""
    cache_file = self.config.state_path / "drive_cache.json"
    
    if cache_file.exists():
        with open(cache_file) as f:
            cache = json.load(f)
            return cache.get(file_id)
    
    return None

def cache_file_metadata(self, file_id: str, metadata: Dict):
    """Cache file metadata for future use"""
    cache_file = self.config.state_path / "drive_cache.json"
    
    # Load existing cache
    cache = {}
    if cache_file.exists():
        with open(cache_file) as f:
            cache = json.load(f)
    
    # Update with new metadata
    cache[file_id] = {
        **metadata,
        'cached_at': datetime.now(timezone.utc).isoformat()
    }
    
    # Save updated cache
    with open(cache_file, 'w') as f:
        json.dump(cache, f, indent=2)
```

## 10. Integration with Existing System

### Archive Writer Integration

```python
# Use existing ArchiveWriter from src/core/archive_writer.py
from ..core.archive_writer import ArchiveWriter

def integrate_with_archive_system(self):
    """Set up integration with existing archive infrastructure"""
    
    # Create archive writer using existing patterns
    self.archive_writer = ArchiveWriter(
        base_path=self.config.archive_path / "drive",
        source_type="drive",
        compression_enabled=True,
        daily_rotation=True
    )
    
    # Use existing state management
    self.state_manager = StateManager(
        state_file=self.config.state_path / "drive_state.json"
    )
```

### CLI Tool Integration

```python
# Integration with tools/collect_data.py
def add_drive_to_collection_tool():
    """Add Drive collector to main collection orchestrator"""
    
    # In tools/collect_data.py, add:
    
    from src.collectors.drive_collector import DriveCollector
    
    def collect_drive_data() -> Dict:
        """Collect Drive data using standardized interface"""
        collector = DriveCollector()
        result = collector.collect()
        
        return {
            'source': 'drive',
            'status': 'success' if not result.errors else 'error',
            'files_collected': result.files_collected,
            'changes_tracked': result.changes_tracked,
            'duration': result.collection_duration,
            'errors': result.errors
        }
```

## 11. Monitoring and Alerting

### Collection Metrics

```python
# Metrics to track for Drive collection
DRIVE_METRICS = {
    'files_discovered_per_day': 'Gauge',
    'changes_tracked_per_day': 'Gauge',
    'api_requests_per_collection': 'Histogram',
    'collection_duration_seconds': 'Histogram',
    'rate_limit_errors_per_day': 'Counter',
    'authentication_failures_per_day': 'Counter'
}

def emit_collection_metrics(self, result: DriveCollectionResult):
    """Emit metrics for monitoring"""
    metrics = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'files_collected': result.files_collected,
        'changes_tracked': result.changes_tracked,
        'duration': result.collection_duration,
        'api_requests': self.rate_limiter.request_count,
        'errors_count': len(result.errors),
        'errors': result.errors
    }
    
    # Log metrics to JSONL for analysis
    metrics_file = self.config.logs_path / "drive_metrics.jsonl"
    with open(metrics_file, 'a') as f:
        f.write(json.dumps(metrics) + '\n')
```

### Health Checks

```python
def health_check(self) -> Dict:
    """Health check for Drive collector"""
    health_status = {
        'service': 'drive_collector',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'status': 'healthy',
        'checks': {}
    }
    
    # Test authentication
    try:
        if self.setup_authentication():
            health_status['checks']['authentication'] = 'pass'
        else:
            health_status['checks']['authentication'] = 'fail'
            health_status['status'] = 'unhealthy'
    except Exception as e:
        health_status['checks']['authentication'] = f'error: {e}'
        health_status['status'] = 'unhealthy'
    
    # Test API connectivity
    try:
        self.drive_service.files().list(pageSize=1).execute()
        health_status['checks']['api_connectivity'] = 'pass'
    except Exception as e:
        health_status['checks']['api_connectivity'] = f'error: {e}'
        health_status['status'] = 'unhealthy'
    
    # Check recent collection success
    last_collection = self.get_state().get('last_collection_time')
    if last_collection:
        last_time = datetime.fromisoformat(last_collection)
        if datetime.now(timezone.utc) - last_time > timedelta(days=2):
            health_status['checks']['recent_collection'] = 'stale'
            health_status['status'] = 'degraded'
        else:
            health_status['checks']['recent_collection'] = 'pass'
    else:
        health_status['checks']['recent_collection'] = 'never_run'
        health_status['status'] = 'degraded'
    
    return health_status
```

## 12. Deployment Checklist

### Pre-Implementation Checklist

- [ ] OAuth 2.0 credentials configured in Google Cloud Console
- [ ] Required API scopes enabled (`drive.readonly`, `drive.metadata.readonly`)
- [ ] Google Drive API enabled in Google Cloud project
- [ ] Rate limiting quotas verified (1000 requests/100 seconds)
- [ ] Archive directory structure created
- [ ] State management files initialized
- [ ] Logging configuration verified

### Implementation Checklist

- [ ] `DriveCollector` class implemented with all methods
- [ ] `DriveRateLimiter` implemented with conservative limits
- [ ] Authentication flow working with existing auth system
- [ ] JSONL output format validated against schema
- [ ] Error handling implemented for all API scenarios
- [ ] Unit tests written with >80% coverage
- [ ] Integration tests passing
- [ ] Performance benchmarks met (<10 seconds for 1000 files)

### Post-Implementation Checklist

- [ ] Initial collection test successful
- [ ] Incremental change tracking verified
- [ ] Rate limiting prevents 429 errors
- [ ] Archive files created in correct format
- [ ] State persistence working correctly
- [ ] Error recovery tested
- [ ] Monitoring metrics being emitted
- [ ] Documentation updated

## 13. Future Enhancements

### Phase 2 Features (Not in Initial Implementation)

1. **Content Extraction** (Privacy-preserving)
   - Extract text from Google Docs for search indexing
   - OCR for image-based documents
   - Keyword extraction and tagging

2. **Advanced Analytics**
   - File activity patterns
   - Collaboration metrics
   - Document lifecycle tracking

3. **Smart Categorization**
   - Automatic folder classification
   - Project association based on naming patterns
   - Team ownership inference

4. **Real-time Change Notifications**
   - Webhook integration for instant change detection
   - Push notifications for important file changes
   - Real-time collaboration insights

## Conclusion

This comprehensive implementation guide provides everything needed to create a production-ready Google Drive collector for the AI Chief of Staff system. The implementation follows existing patterns, maintains privacy, and provides robust error handling and monitoring.

The key principles are:
- **Privacy First**: Only metadata, never content
- **Integration**: Works with existing architecture
- **Reliability**: Comprehensive error handling and rate limiting
- **Monitoring**: Full observability and health checks
- **Scalability**: Efficient pagination and state management

Follow this guide step-by-step, and the Drive collector will integrate seamlessly with the existing AI Chief of Staff data collection pipeline.