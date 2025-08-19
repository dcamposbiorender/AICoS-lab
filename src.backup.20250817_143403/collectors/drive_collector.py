#!/usr/bin/env python3
"""
Google Drive Collector - Production Implementation Stub
Integrates with AI Chief of Staff archive system for metadata collection

This file provides a complete implementation stub with detailed TODO comments
for another Claude or developer to complete the Drive collector.

Architecture:
- Follows BaseArchiveCollector interface from base.py
- Integrates with existing auth_manager.py and archive_writer.py
- Uses JSONL format for persistent storage
- Implements rate limiting and error handling
- Tracks file metadata and changes without storing content

Implementation Status: STUB WITH DETAILED TODOS
Ready for completion by another Claude following /docs/drive_implementation.md

Usage:
    from src.collectors.drive_collector import DriveCollector
    collector = DriveCollector()
    result = collector.collect()
"""

import json
import sys
import io
import time
import pickle
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Iterator
from dataclasses import dataclass

# Import existing system components
try:
    from ..core.config import get_config
    from ..core.state import StateManager
    from ..core.archive_writer import ArchiveWriter
    from .base import BaseArchiveCollector, CollectorError
    from .circuit_breaker import CircuitBreaker
except ImportError:
    # Fallback for direct execution
    print("Warning: Could not import core components. Running in standalone mode.")
    
    class BaseArchiveCollector:
        def __init__(self, collector_type, config_path=None):
            self.collector_type = collector_type
            
    class CollectorError(Exception):
        pass


# =============================================================================
# ERROR CLASSES
# =============================================================================

class DriveCollectorError(CollectorError):
    """Drive-specific collection errors"""
    pass

class DriveAuthError(DriveCollectorError):
    """Drive authentication failures"""
    pass

class DriveRateLimitError(DriveCollectorError):
    """Drive API rate limit exceeded"""
    pass


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class DriveCollectionResult:
    """Results from Drive collection operation"""
    files_collected: int
    changes_tracked: int
    permissions_updated: int
    errors: List[str]
    collection_duration: float
    api_requests_made: int
    rate_limit_hits: int


# =============================================================================
# DRIVE RATE LIMITER
# =============================================================================

class DriveRateLimiter:
    """
    Rate limiter for Google Drive API
    
    Google Drive API Limits (as of 2025):
    - 1000 requests per 100 seconds per user
    - Conservative approach: 0.1 seconds between requests
    
    TODO: Implement the following methods:
    1. __init__(self, requests_per_100_seconds=1000)
    2. wait_for_api_limit(self) - enforces delays between requests
    3. handle_429_error(self, error) - handles rate limit responses
    4. record_request(self) - tracks request timing
    5. get_wait_time(self) - calculates required wait time
    
    Reference implementation: /docs/drive_implementation.md section 3
    """
    
    def __init__(self, requests_per_100_seconds: int = 900):  # Conservative: 900/1000 limit
        """
        Initialize rate limiter with conservative settings for bulk Drive collection
        
        Google Drive API limits: 1000 requests per 100 seconds per user
        We use 900 to leave safety buffer and add exponential backoff
        """
        self.requests_per_100_seconds = requests_per_100_seconds
        self.min_delay = 100.0 / requests_per_100_seconds  # ~0.11 seconds default
        self.request_times = []  # Track request timestamps in sliding window
        self.consecutive_rate_limits = 0
        self.request_count = 0
        self.total_rate_limit_hits = 0
        self.last_request_time = 0  # Initialize to 0 for first request
        
        # Exponential backoff levels for 429 responses
        self.backoff_levels = [1, 2, 4, 8, 16, 32, 64]  # seconds
        self.current_backoff_delay = 0
        
        print(f"🚗 Drive Rate Limiter initialized: {requests_per_100_seconds} requests/100s")
        print(f"⏱️  Minimum delay between requests: {self.min_delay:.3f}s")
    
    def wait_for_api_limit(self):
        """
        Enforce rate limiting with sliding window to prevent 429 errors
        
        Implements sliding window rate limiting:
        1. Maintains 100-second sliding window of request timestamps
        2. Enforces quota limits before making requests
        3. Adds minimum delay + any backoff delay
        4. Records request timing for next calculation
        """
        current_time = time.time()
        
        # Remove request times older than 100 seconds (sliding window)
        cutoff_time = current_time - 100
        self.request_times = [t for t in self.request_times if t > cutoff_time]
        
        # Check if approaching rate limit (90% threshold for safety)
        quota_threshold = int(self.requests_per_100_seconds * 0.9)
        if len(self.request_times) >= quota_threshold:
            # Calculate how long to wait for oldest request to age out
            oldest_in_window = self.request_times[0] if self.request_times else cutoff_time
            wait_time = (oldest_in_window + 100) - current_time + 1  # +1 second buffer
            
            if wait_time > 0:
                print(f"    ⏳ Drive quota threshold ({len(self.request_times)}/{self.requests_per_100_seconds}): waiting {wait_time:.1f}s")
                time.sleep(wait_time)
                current_time = time.time()  # Update after wait
        
        # Apply minimum delay between requests
        time_since_last = current_time - self.last_request_time if self.last_request_time else self.min_delay
        if time_since_last < self.min_delay:
            additional_wait = self.min_delay - time_since_last
            time.sleep(additional_wait)
            current_time = time.time()
        
        # Apply any backoff delay from previous rate limit hits
        if self.current_backoff_delay > 0:
            print(f"    ⚠️ Drive backoff delay: {self.current_backoff_delay}s")
            time.sleep(self.current_backoff_delay)
            current_time = time.time()
        
        # Record this request in sliding window
        self.request_times.append(current_time)
        self.last_request_time = current_time
        self.request_count += 1
    
    def handle_429_error(self, error):
        """
        Handle rate limit exceeded (429) responses with exponential backoff
        
        Implements sophisticated backoff strategy:
        1. Extracts retry-after header when available
        2. Falls back to exponential backoff progression
        3. Tracks consecutive rate limit hits
        4. Provides detailed logging for debugging
        """
        self.consecutive_rate_limits += 1
        self.total_rate_limit_hits += 1
        
        # Extract retry-after header from Google API error if available
        retry_after = None
        try:
            # Google API errors may include retry-after in error details
            if hasattr(error, 'resp') and hasattr(error.resp, 'get'):
                retry_after = error.resp.get('retry-after')
            elif hasattr(error, 'response') and hasattr(error.response, 'headers'):
                retry_after = error.response.headers.get('retry-after')
        except:
            pass
        
        if retry_after:
            try:
                wait_time = int(retry_after)
                print(f"    🚫 Drive API 429: Server requested {wait_time}s delay")
            except ValueError:
                wait_time = 60  # Default if retry-after header is malformed
        else:
            # Exponential backoff based on consecutive hits
            backoff_index = min(self.consecutive_rate_limits - 1, len(self.backoff_levels) - 1)
            wait_time = self.backoff_levels[backoff_index]
            print(f"    🚫 Drive API 429: Exponential backoff #{self.consecutive_rate_limits}, waiting {wait_time}s")
        
        # Add jitter to prevent thundering herd (±25% of wait time)
        jitter = random.uniform(-0.25 * wait_time, 0.25 * wait_time)
        actual_wait = max(1, wait_time + jitter)
        
        print(f"    ⏳ Drive rate limit backoff: {actual_wait:.1f}s (consecutive: {self.consecutive_rate_limits})")
        
        # Set backoff delay for next request
        self.current_backoff_delay = actual_wait
        time.sleep(actual_wait)
    
    def reset_backoff(self):
        """Reset backoff state after successful request"""
        if self.consecutive_rate_limits > 0:
            print(f"    ✅ Drive rate limit recovered after {self.consecutive_rate_limits} consecutive hits")
            self.consecutive_rate_limits = 0
            self.current_backoff_delay = 0
    
    def get_rate_limit_stats(self) -> Dict:
        """Get rate limiting statistics for monitoring"""
        return {
            'total_requests': self.request_count,
            'total_rate_limit_hits': self.total_rate_limit_hits,
            'consecutive_rate_limits': self.consecutive_rate_limits,
            'current_backoff_delay': self.current_backoff_delay,
            'requests_in_window': len(self.request_times),
            'rate_limit_hit_rate': self.total_rate_limit_hits / max(self.request_count, 1)
        }


# =============================================================================
# MAIN DRIVE COLLECTOR CLASS
# =============================================================================

class DriveCollector(BaseArchiveCollector):
    """
    Google Drive metadata collector following AI Chief of Staff patterns
    
    This collector:
    1. Discovers Drive files using Drive API v3
    2. Tracks file changes using Changes API
    3. Collects metadata ONLY (no file content)
    4. Saves data in JSONL format via ArchiveWriter
    5. Integrates with existing auth and state management
    
    TODO: Complete implementation of all methods below
    Reference: /docs/drive_implementation.md for complete implementation guide
    """
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize Drive collector with AI Chief of Staff integration"""
        # ALWAYS set project_root first
        self.project_root = Path(__file__).parent.parent.parent
        
        try:
            super().__init__("drive", config_path)
        except:
            # Fallback for standalone mode
            self.collector_type = "drive"
        
        # Initialize Drive-specific components
        self.drive_service = None
        self.rate_limiter = DriveRateLimiter()
        self.change_token = None
        
        # Collection statistics
        self.collection_stats = {
            'files_discovered': 0,
            'files_collected': 0,
            'shared_drives_found': 0,
            'api_requests_made': 0,
            'rate_limit_hits': 0,
            'errors_encountered': 0
        }
        
        # Data paths
        today = datetime.now().strftime("%Y-%m-%d")
        self.data_path = self.project_root / "data" / "raw" / "drive" / today
        self.data_path.mkdir(parents=True, exist_ok=True)
        
        print("🚗 Drive Collector initialized")
        print(f"💾 Storage: {self.data_path}")
    
    def setup_drive_authentication(self) -> bool:
        """Setup Google Drive API authentication using existing auth_manager"""
        try:
            # Import auth_manager if not already available
            from ..core.auth_manager import credential_vault
            
            # Validate authentication
            auth_status = credential_vault.validate_authentication()
            if not auth_status.get('google_oauth'):
                print("❌ Google OAuth credentials not available for Drive")
                return False
            
            # Create Drive service using existing auth system
            self.drive_service = credential_vault.get_google_service('drive', 'v3')
            if not self.drive_service:
                print("❌ Failed to create Google Drive service")
                return False
            
            print("✅ Google Drive service ready")
            return True
            
        except Exception as e:
            print(f"❌ Drive authentication failed: {e}")
            return False
    
    def discover_all_files(self, days_backward: int = 365, max_files: int = 100000) -> Dict[str, Dict]:
        """
        Discover Drive files with comprehensive metadata for the last year
        
        Args:
            days_backward: Number of days to look back for file activity (default 365 = 1 year)
            max_files: Maximum files to discover (default 100k for large workspace)
            
        Returns:
            Dictionary mapping file_id -> comprehensive metadata
        """
        discovered_files = {}
        
        try:
            print(f"🔍 Discovering Drive files from last {days_backward} days (max: {max_files:,})...")
            
            # Build query for file discovery with date filter
            since_date = (datetime.now() - timedelta(days=days_backward)).isoformat() + 'Z'
            query = f"trashed = false and modifiedTime > '{since_date}'"
            
            # Define comprehensive metadata fields
            fields = (
                "nextPageToken, files("
                "id, name, mimeType, size, "
                "createdTime, modifiedTime, "
                "owners, lastModifyingUser, "
                "parents, webViewLink, shared, "
                "version, originalFilename, "
                "fileExtension, fullFileExtension, "
                "teamDriveId, driveId, "
                "permissions, sharingUser, "
                "viewedByMe, viewedByMeTime, "
                "quotaBytesUsed, headRevisionId, "
                "isAppAuthorized, exportLinks"
                ")"
            )
            
            # Create initial request with pagination
            request = self.drive_service.files().list(
                q=query,
                fields=fields,
                pageSize=min(1000, max_files)  # API max is 1000 per request
            )
            
            page_count = 0
            total_processed = 0
            
            # Handle pagination loop
            while request is not None and len(discovered_files) < max_files:
                try:
                    self.rate_limiter.wait_for_api_limit()
                    
                    response = request.execute()
                    files = response.get('files', [])
                    
                    # Process each file
                    for file_metadata in files:
                        file_id = file_metadata['id']
                        
                        # Enhance metadata with collection context
                        enhanced_metadata = dict(file_metadata)
                        enhanced_metadata.update({
                            'collected_at': datetime.now().isoformat(),
                            'collection_method': 'bulk_metadata_discovery',
                            'file_size_mb': int(file_metadata.get('size', 0)) / (1024 * 1024) if file_metadata.get('size') else 0,
                            'age_days': self._calculate_file_age_days(file_metadata.get('createdTime')),
                            'is_google_doc': file_metadata.get('mimeType', '').startswith('application/vnd.google-apps'),
                            'has_external_sharing': self._has_external_sharing(file_metadata.get('permissions', [])),
                            'last_activity_days': self._calculate_last_activity_days(file_metadata.get('modifiedTime'))
                        })
                        
                        discovered_files[file_id] = enhanced_metadata
                    
                    page_count += 1
                    total_processed += len(files)
                    self.collection_stats['api_requests_made'] += 1
                    
                    # Progress reporting every 10 pages
                    if page_count % 10 == 0:
                        print(f"    📄 Page {page_count}: {total_processed:,} files discovered")
                    
                    # Get next page
                    request = self.drive_service.files().list_next(request, response)
                    
                except Exception as e:
                    if "429" in str(e) or "quota" in str(e).lower():
                        self.rate_limiter.handle_429_error(e)
                        self.collection_stats['rate_limit_hits'] += 1
                        # Retry the same request after backoff
                        continue
                    else:
                        print(f"    ❌ Error on page {page_count + 1}: {str(e)[:80]}")
                        self.collection_stats['errors_encountered'] += 1
                        break
            
            self.collection_stats['files_discovered'] = len(discovered_files)
            print(f"✅ Drive discovery complete: {len(discovered_files):,} files found from {page_count} pages")
            return discovered_files
            
        except Exception as e:
            print(f"❌ Drive discovery failed: {e}")
            self.collection_stats['errors_encountered'] += 1
            raise DriveCollectorError(f"File discovery failed: {e}")

    def _calculate_file_age_days(self, created_time: Optional[str]) -> int:
        """Calculate file age in days from creation timestamp"""
        if not created_time:
            return 0
        try:
            created_dt = datetime.fromisoformat(created_time.replace('Z', '+00:00'))
            age = datetime.now(timezone.utc) - created_dt
            return age.days
        except:
            return 0

    def _calculate_last_activity_days(self, modified_time: Optional[str]) -> int:
        """Calculate days since last activity from modified timestamp"""
        if not modified_time:
            return 0
        try:
            modified_dt = datetime.fromisoformat(modified_time.replace('Z', '+00:00'))
            age = datetime.now(timezone.utc) - modified_dt
            return age.days
        except:
            return 0

    def _has_external_sharing(self, permissions: List[Dict]) -> bool:
        """Check if file has external sharing (outside organization)"""
        # This is a simplified check - in practice you'd want to check against
        # your organization's domain
        for permission in permissions:
            if permission.get('type') == 'anyone':
                return True
            email = permission.get('emailAddress', '')
            if email and '@gmail.com' in email:  # Common external domain
                return True
        return False

    def _save_drive_metadata_to_jsonl(self, files_metadata: List[Dict]) -> int:
        """Save Drive file metadata to JSONL format"""
        try:
            if not files_metadata:
                print("    💾 No file metadata to save")
                return 0
            
            # Save to JSONL file
            jsonl_file = self.data_path / "drive_metadata.jsonl"
            with open(jsonl_file, 'w') as f:
                for file_metadata in files_metadata:
                    f.write(json.dumps(file_metadata) + '\n')
            
            file_size_mb = jsonl_file.stat().st_size / (1024 * 1024)
            print(f"    💾 Saved {len(files_metadata):,} file metadata records ({file_size_mb:.2f} MB)")
            
            self.collection_stats['files_collected'] = len(files_metadata)
            return len(files_metadata)
            
        except Exception as e:
            print(f"    ❌ Failed to save files to JSONL: {e}")
            return 0

    def _save_drive_summary(self, discovered_files: Dict[str, Dict]):
        """Save Drive collection summary with statistics"""
        try:
            summary = {
                'collection_metadata': {
                    'collected_at': datetime.now().isoformat(),
                    'total_files': len(discovered_files),
                    'collection_method': 'bulk_metadata_discovery',
                    'days_backward': 365,
                    'rate_limit_stats': self.rate_limiter.get_rate_limit_stats(),
                    'collection_stats': self.collection_stats
                },
                'file_statistics': self._calculate_drive_statistics(discovered_files),
                'files_by_type': self._group_files_by_type(discovered_files)
            }
            
            summary_file = self.data_path / "drive_summary.json"
            with open(summary_file, 'w') as f:
                json.dump(summary, f, indent=2)
            
            print(f"    📊 Summary saved to {summary_file}")
            
        except Exception as e:
            print(f"    ⚠️ Failed to save summary: {e}")

    def _calculate_drive_statistics(self, files: Dict[str, Dict]) -> Dict:
        """Calculate statistics about the Drive collection"""
        if not files:
            return {}
        
        total_size = 0
        google_docs = 0
        external_sharing = 0
        recent_files = 0  # Modified in last 30 days
        
        cutoff_date = datetime.now() - timedelta(days=30)
        
        for file_data in files.values():
            # Size calculation
            if file_data.get('size'):
                total_size += int(file_data['size'])
            
            # Google Docs count
            if file_data.get('is_google_doc'):
                google_docs += 1
            
            # External sharing
            if file_data.get('has_external_sharing'):
                external_sharing += 1
            
            # Recent activity
            if file_data.get('last_activity_days', 999) <= 30:
                recent_files += 1
        
        return {
            'total_files': len(files),
            'total_size_gb': total_size / (1024**3),
            'google_docs_count': google_docs,
            'externally_shared_files': external_sharing,
            'recently_active_files': recent_files,
            'avg_file_age_days': sum(f.get('age_days', 0) for f in files.values()) / len(files)
        }

    def _group_files_by_type(self, files: Dict[str, Dict]) -> Dict[str, int]:
        """Group files by MIME type for analysis"""
        type_counts = {}
        for file_data in files.values():
            mime_type = file_data.get('mimeType', 'unknown')
            type_counts[mime_type] = type_counts.get(mime_type, 0) + 1
        
        # Sort by count
        return dict(sorted(type_counts.items(), key=lambda x: x[1], reverse=True))
    
    def collect_file_changes(self, since_token: Optional[str] = None) -> List[Dict]:
        """
        Collect file changes since last collection using Changes API
        
        TODO: Implement change tracking
        1. Get starting change token if since_token is None
        2. Use changes().list() API with pagination
        3. Apply rate limiting between requests
        4. Process each change event
        5. Update self.change_token for next collection
        6. Return list of change events
        
        Change Event Fields:
        - fileId: ID of changed file
        - removed: True if file was deleted
        - file: File metadata (if not removed)
        - changeType: Type of change (for logging)
        
        Reference: /docs/drive_implementation.md section 5 (collect_file_changes method)
        """
        changes = []
        
        try:
            print(f"🔄 Collecting file changes...")
            
            # TODO: Get starting token if none provided
            if since_token is None:
                # response = self.drive_service.changes().getStartPageToken().execute()
                # since_token = response['startPageToken']
                print("    📍 Getting initial change token...")
                pass
            
            # TODO: Create changes request with pagination
            # request = self.drive_service.changes().list(
            #     pageToken=since_token,
            #     includeRemoved=True,
            #     fields="nextPageToken, newStartPageToken, changes(fileId, removed, file)"
            # )
            
            # TODO: Handle pagination loop
            # while request is not None:
            #     self.rate_limiter.wait_for_api_limit()
            #     
            #     response = request.execute()
            #     page_changes = response.get('changes', [])
            #     
            #     for change in page_changes:
            #         change_data = {
            #             'file_id': change['fileId'],
            #             'removed': change.get('removed', False),
            #             'change_timestamp': datetime.now(timezone.utc).isoformat(),
            #             'file_metadata': change.get('file', {})
            #         }
            #         changes.append(change_data)
            #     
            #     # Update token for next collection
            #     if 'newStartPageToken' in response:
            #         self.change_token = response['newStartPageToken']
            #     
            #     request = self.drive_service.changes().list_next(request, response)
            
            print(f"✅ Change tracking complete: {len(changes)} changes found")
            return changes
            
        except Exception as e:
            print(f"❌ Change tracking failed: {e}")
            raise DriveCollectorError(f"Change collection failed: {e}")
    
    def save_files_to_archive(self, files_metadata: List[Dict]) -> int:
        """
        Save file metadata to JSONL archive using ArchiveWriter
        
        TODO: Implement JSONL persistence
        1. Use self.archive_writer to save metadata
        2. Create batch with timestamp and batch_id
        3. Handle any persistence errors gracefully
        4. Return number of records saved
        5. Log success/failure with counts
        
        JSONL Format:
        Each line is a complete JSON object with file metadata
        Files saved to: data/archive/drive/YYYY-MM-DD/drive_metadata.jsonl
        
        Reference: /docs/drive_implementation.md section 4 (JSONL Output Format)
        """
        try:
            if not files_metadata:
                print("    💾 No file metadata to save")
                return 0
            
            # TODO: Use ArchiveWriter to save metadata
            # count = self.archive_writer.write_batch(
            #     records=files_metadata,
            #     record_type="file_metadata",
            #     batch_id=f"files_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            # )
            count = 0  # Placeholder
            
            print(f"    💾 Saved {count} file metadata records to archive")
            return count
            
        except Exception as e:
            print(f"    ❌ Failed to save files to archive: {e}")
            return 0
    
    def save_changes_to_archive(self, changes: List[Dict]) -> int:
        """
        Save change events to JSONL archive using ArchiveWriter
        
        TODO: Implement change persistence
        1. Use self.archive_writer to save changes
        2. Create batch with timestamp and batch_id  
        3. Handle any persistence errors gracefully
        4. Return number of records saved
        5. Log success/failure with counts
        
        JSONL Format:
        Each line is a complete JSON object with change event data
        Changes saved to: data/archive/drive/YYYY-MM-DD/drive_changes.jsonl
        """
        try:
            if not changes:
                print("    💾 No changes to save")
                return 0
            
            # TODO: Use ArchiveWriter to save changes
            # count = self.archive_writer.write_batch(
            #     records=changes,
            #     record_type="changes",
            #     batch_id=f"changes_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            # )
            count = 0  # Placeholder
            
            print(f"    💾 Saved {count} change records to archive")
            return count
            
        except Exception as e:
            print(f"    ❌ Failed to save changes to archive: {e}")
            return 0
    
    def collect(self) -> DriveCollectionResult:
        """
        Main collection method - implements BaseArchiveCollector interface
        
        This is the primary entry point called by tools/collect_data.py
        Must return standardized result object for integration with system
        
        TODO: Implement complete collection workflow
        1. Setup authentication
        2. Load previous collection state
        3. Discover files with metadata
        4. Collect changes since last run
        5. Save data to JSONL archives
        6. Update collection state
        7. Return comprehensive results
        
        Collection Phases:
        Phase 1: Authentication and setup
        Phase 2: File discovery (metadata only)
        Phase 3: Change tracking (incremental)
        Phase 4: Data persistence (JSONL)
        Phase 5: State management
        Phase 6: Results and metrics
        
        Reference: /docs/drive_implementation.md section 5 (collect method)
        """
        start_time = time.time()
        errors = []
        
        print("🚗 Starting Drive collection...")
        
        try:
            # Phase 1 - Authentication
            print("    🔐 Phase 1: Setting up authentication...")
            if not self.setup_drive_authentication():
                raise DriveCollectorError("Authentication failed")
            
            # Phase 2 - File discovery for entire workspace (last year)
            print("    🔍 Phase 2: Discovering Drive files for last year...")
            discovered_files = self.discover_all_files(days_backward=365, max_files=100000)
            
            # Phase 3 - Data persistence
            print("    💾 Phase 3: Saving metadata to JSONL archives...")
            files_count = self._save_drive_metadata_to_jsonl(list(discovered_files.values()))
            
            # Phase 4 - Save summary data
            print("    📊 Phase 4: Saving summary data...")
            self._save_drive_summary(discovered_files)
            
            # Phase 5 - Final results
            duration = time.time() - start_time
            
            result = DriveCollectionResult(
                files_collected=files_count,
                changes_tracked=0,  # Changes API not implemented in MVP
                permissions_updated=0,  # Permission tracking not implemented in MVP
                errors=errors,
                collection_duration=duration,
                api_requests_made=self.collection_stats['api_requests_made'],
                rate_limit_hits=self.collection_stats['rate_limit_hits']
            )
            
            print(f"✅ Drive collection complete!")
            print(f"    📊 Files collected: {result.files_collected:,}")
            print(f"    ⏱️  Duration: {result.collection_duration/60:.1f} minutes")
            print(f"    🌐 API Requests: {result.api_requests_made:,}")
            print(f"    ⚠️ Rate limit hits: {result.rate_limit_hits}")
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"Drive collection failed: {e}"
            errors.append(error_msg)
            print(f"❌ {error_msg}")
            
            return DriveCollectionResult(
                files_collected=0,
                changes_tracked=0,
                permissions_updated=0,
                errors=errors,
                collection_duration=duration,
                api_requests_made=self.rate_limiter.request_count,
                rate_limit_hits=self.rate_limiter.consecutive_rate_limits
            )


# =============================================================================
# LEGACY COMPATIBILITY
# =============================================================================

class DriveIngestor(DriveCollector):
    """
    Legacy alias for DriveCollector to maintain backward compatibility
    
    TODO: Remove this alias once all references are updated to DriveCollector
    """
    
    def __init__(self):
        print("⚠️  DriveIngestor is deprecated. Use DriveCollector instead.")
        super().__init__()
    
    async def ingest_drive_files(self):
        """
        Legacy method for backward compatibility
        
        TODO: Remove this method once references are updated
        """
        print("⚠️  ingest_drive_files() is deprecated. Use collect() instead.")
        result = self.collect()
        return len(result.errors) == 0


# =============================================================================
# IMPLEMENTATION REFERENCE AND NEXT STEPS
# =============================================================================

"""
IMPLEMENTATION COMPLETION CHECKLIST:

## Authentication (High Priority)
[ ] Import Google API libraries (google-auth, google-auth-oauthlib, google-api-python-client)
[ ] Implement OAuth 2.0 flow in setup_drive_authentication()
[ ] Test authentication with existing credentials.json and token.pickle
[ ] Handle token refresh and expired credentials

## File Discovery (High Priority)  
[ ] Implement files().list() API calls with proper pagination
[ ] Add query filters for trashed files and date ranges
[ ] Handle API errors and rate limiting
[ ] Test with various file types and large datasets

## Change Tracking (Medium Priority)
[ ] Implement changes().list() API for incremental updates
[ ] Handle change tokens and pagination
[ ] Store and retrieve change tokens in state management
[ ] Test incremental collection workflow

## Data Persistence (High Priority)
[ ] Integrate with ArchiveWriter for JSONL output
[ ] Ensure proper daily directory structure
[ ] Validate JSONL format and schema
[ ] Test archive persistence and retrieval

## State Management (Medium Priority)
[ ] Integrate with StateManager for cursor tracking
[ ] Store collection metadata and timestamps
[ ] Handle state corruption and recovery
[ ] Test state persistence across collection runs

## Error Handling (Medium Priority)
[ ] Implement comprehensive error handling for all API scenarios
[ ] Add circuit breaker integration
[ ] Handle network failures and API outages
[ ] Test error recovery and retry logic

## Integration Testing (High Priority)
[ ] Test with tools/collect_data.py orchestrator
[ ] Verify JSONL output format compatibility
[ ] Test integration with test_collector_harness.py
[ ] Validate against existing system architecture

## Performance & Rate Limiting (Medium Priority)
[ ] Tune rate limiting parameters for production use
[ ] Implement efficient pagination for large datasets
[ ] Add progress reporting for long-running collections
[ ] Test with realistic data volumes

## Monitoring & Metrics (Low Priority)
[ ] Add comprehensive logging and metrics
[ ] Implement health check functionality
[ ] Add performance monitoring
[ ] Create alerting for collection failures

REFERENCE DOCUMENTS:
- /docs/drive_implementation.md - Complete implementation guide
- /src/collectors/base.py - BaseArchiveCollector interface
- /src/core/archive_writer.py - JSONL persistence patterns
- /src/core/auth_manager.py - Authentication patterns
- /tests/integration/test_collector_harness.py - Testing integration

GOOGLE DRIVE API DOCUMENTATION:
- Files API: https://developers.google.com/drive/api/v3/reference/files
- Changes API: https://developers.google.com/drive/api/v3/reference/changes
- OAuth Scopes: https://developers.google.com/identity/protocols/oauth2/scopes#drive

IMPLEMENTATION PRIORITY:
1. Authentication (setup_drive_authentication)
2. File Discovery (discover_all_files)  
3. Data Persistence (save_files_to_archive, save_changes_to_archive)
4. Change Tracking (collect_file_changes)
5. Integration Testing
6. Error Handling & Rate Limiting
"""

if __name__ == "__main__":
    print("🚗 Drive Collector Implementation Stub")
    print("📖 See implementation guide: /docs/drive_implementation.md")
    print("✅ Ready for completion by another Claude")
    
    # Basic initialization test
    try:
        collector = DriveCollector()
        print("✅ Collector initialized successfully")
        
        # Run stub collection (will show all TODO items)
        result = collector.collect()
        print(f"📊 Stub collection result: {result}")
        
    except Exception as e:
        print(f"❌ Error during stub test: {e}")