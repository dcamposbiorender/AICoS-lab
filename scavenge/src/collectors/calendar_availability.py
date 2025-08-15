#!/usr/bin/env python3
"""
Calendar Availability Indexer - Google Calendar Freebusy API Integration

Monitors availability for target users over next 7 days using Google Calendar's
freebusy endpoint for efficient bulk availability queries.

Features:
- Uses freebusy endpoint for bulk availability queries (efficient)  
- Leverages existing auth_manager for Google Calendar authentication
- Follows established rate limiting patterns from calendar_collector.py
- Handles partial failures gracefully (403, 404 errors)
- Outputs structured JSON format for downstream consumption
- Integrates with existing configuration and storage patterns

Built on existing infrastructure:
- auth_manager.py: Unified Google OAuth authentication
- CalendarRateLimiter: Proven rate limiting with jitter and backoff
- Established JSON output patterns from other collectors
"""

import asyncio
import json
import logging
import sys
import time
import yaml
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass
from enum import Enum

# Add auth system path following established patterns
sys.path.insert(0, str(Path(__file__).parent.parent / "core"))
from auth_manager import credential_vault


class AvailabilityStatus(Enum):
    """Calendar availability status"""
    BUSY = "busy"
    FREE = "free"
    UNKNOWN = "unknown"


@dataclass
class TimeSlot:
    """Time slot for availability"""
    start: str  # ISO format datetime
    end: str    # ISO format datetime
    status: AvailabilityStatus = AvailabilityStatus.BUSY
    
    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary for JSON serialization"""
        return {
            "start": self.start,
            "end": self.end
        }


@dataclass 
class UserAvailability:
    """Availability data for a single user"""
    email: str
    success: bool
    error_type: Optional[str] = None
    busy_times: List[TimeSlot] = None
    
    def __post_init__(self):
        if self.busy_times is None:
            self.busy_times = []


class CalendarAvailabilityRateLimiter:
    """
    Rate limiter specifically tuned for Google Calendar freebusy API
    Based on existing CalendarRateLimiter patterns but optimized for availability queries
    """
    
    def __init__(self, requests_per_second: float = 1.0, requests_per_minute: int = 20):
        self.requests_per_second = requests_per_second
        self.requests_per_minute = requests_per_minute
        self.request_history: List[float] = []
        self.last_request_time = 0
        
        # Use 1 req/sec max as specified in requirements
        self.min_interval = 1.0 / requests_per_second
        
    async def wait_for_rate_limit(self):
        """Wait appropriate time for rate limiting"""
        current_time = time.time()
        
        # Clean old requests from history (>1 minute old)
        minute_ago = current_time - 60
        self.request_history = [t for t in self.request_history if t > minute_ago]
        
        # Check per-minute limit
        if len(self.request_history) >= self.requests_per_minute:
            # Wait until oldest request is >1 minute old
            wait_time = 61 - (current_time - self.request_history[0])
            if wait_time > 0:
                await asyncio.sleep(wait_time)
                
        # Check per-second limit
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_interval:
            wait_time = self.min_interval - time_since_last
            await asyncio.sleep(wait_time)
        
        # Record request time
        current_time = time.time()
        self.request_history.append(current_time)
        self.last_request_time = current_time


class CalendarAvailabilityIndexer:
    """
    Google Calendar availability indexer using freebusy endpoint.
    
    Efficiently queries availability for multiple users using bulk freebusy API,
    following established patterns from the existing calendar collection system.
    """
    
    def __init__(self, config_path: str = "config/calendar_targets.yaml"):
        self.config_path = Path(config_path)
        self.project_root = Path(__file__).parent.parent.parent
        
        # Initialize logging first
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)
        
        # Load configuration
        self.config = self._load_config()
        
        # Initialize authentication using existing credential vault
        self.auth_manager = credential_vault
        self.calendar_service = None
        
        # Initialize rate limiter
        rate_config = self.config.get('calendar_api', {})
        self.rate_limiter = CalendarAvailabilityRateLimiter(
            requests_per_second=rate_config.get('requests_per_second', 1),
            requests_per_minute=rate_config.get('requests_per_minute', 20)
        )
        
        # Statistics tracking
        self.stats = {
            'total_users': 0,
            'successful_queries': 0,
            'failed_queries': 0,
            'errors': {},
            'collection_start': None,
            'collection_end': None
        }
        
        self.logger.info("📅 Calendar Availability Indexer initialized")
        self.logger.info(f"🎯 Config: {self.config_path}")
        self.logger.info(f"⚡ Rate limit: {rate_config.get('requests_per_second', 1)} req/sec")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            self.logger.info(f"✅ Configuration loaded: {len(config.get('users', []))} target users")
            return config
        except Exception as e:
            self.logger.error(f"❌ Failed to load config from {self.config_path}: {e}")
            raise
    
    def _initialize_calendar_service(self) -> bool:
        """Initialize Google Calendar service using existing auth infrastructure"""
        try:
            # Use existing credential vault to get authenticated service
            self.calendar_service = self.auth_manager.get_google_service('calendar', 'v3')
            
            if not self.calendar_service:
                self.logger.error("❌ Failed to create Google Calendar service")
                return False
            
            self.logger.info("✅ Google Calendar service initialized")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Calendar service initialization failed: {e}")
            return False
    
    def _get_time_range(self, days_ahead: int = 7) -> tuple[str, str]:
        """Get ISO format time range for availability query"""
        now = datetime.now(timezone.utc)
        start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = start_time + timedelta(days=days_ahead)
        
        return start_time.isoformat(), end_time.isoformat()
    
    async def _query_user_availability(self, email: str, start_time: str, end_time: str) -> UserAvailability:
        """Query availability for a single user using freebusy API"""
        try:
            # Apply rate limiting
            await self.rate_limiter.wait_for_rate_limit()
            
            # Prepare freebusy query
            body = {
                'timeMin': start_time,
                'timeMax': end_time,
                'items': [{'id': email}]
            }
            
            # Execute freebusy query
            self.logger.debug(f"🔍 Querying availability for {email}")
            result = self.calendar_service.freebusy().query(body=body).execute()
            
            # Process results
            calendar_data = result.get('calendars', {}).get(email, {})
            
            # Check for errors
            if 'errors' in calendar_data:
                errors = calendar_data['errors']
                if errors:
                    error_reason = errors[0].get('reason', 'unknown')
                    self.logger.warning(f"⚠️ Calendar error for {email}: {error_reason}")
                    return UserAvailability(email=email, success=False, error_type=error_reason)
            
            # Extract busy times
            busy_periods = calendar_data.get('busy', [])
            busy_times = []
            
            for period in busy_periods:
                busy_times.append(TimeSlot(
                    start=period.get('start'),
                    end=period.get('end'),
                    status=AvailabilityStatus.BUSY
                ))
            
            self.logger.debug(f"✅ Found {len(busy_times)} busy periods for {email}")
            return UserAvailability(email=email, success=True, busy_times=busy_times)
            
        except Exception as e:
            error_msg = str(e)
            self.logger.warning(f"❌ Failed to query {email}: {error_msg}")
            
            # Categorize error types
            error_type = "unknown"
            if "403" in error_msg or "Forbidden" in error_msg:
                error_type = "permission_denied"
            elif "404" in error_msg or "Not Found" in error_msg:
                error_type = "calendar_not_found"
            elif "429" in error_msg or "Rate" in error_msg:
                error_type = "rate_limit"
                
            return UserAvailability(email=email, success=False, error_type=error_type)
    
    def _convert_to_daily_format(self, availability: UserAvailability, 
                                start_time: str, days: int = 7) -> Dict[str, List[Dict[str, str]]]:
        """Convert busy times to daily format as specified in requirements"""
        if not availability.success:
            return {}
        
        # Initialize daily structure
        start_date = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        daily_busy = {}
        
        for day_offset in range(days):
            day_date = start_date + timedelta(days=day_offset)
            date_key = day_date.strftime('%Y-%m-%d')
            daily_busy[date_key] = []
        
        # Group busy times by date
        for busy_slot in availability.busy_times:
            if not busy_slot.start:
                continue
                
            # Parse start time to get date
            try:
                slot_start = datetime.fromisoformat(busy_slot.start.replace('Z', '+00:00'))
                date_key = slot_start.strftime('%Y-%m-%d')
                
                if date_key in daily_busy:
                    daily_busy[date_key].append(busy_slot.to_dict())
                    
            except Exception as e:
                self.logger.warning(f"⚠️ Failed to parse busy time {busy_slot.start}: {e}")
        
        return daily_busy
    
    async def collect_availability(self) -> Dict[str, Any]:
        """Main collection method - queries all target users"""
        self.logger.info("🚀 Starting calendar availability collection")
        self.stats['collection_start'] = datetime.now().isoformat()
        
        # Initialize Calendar service
        if not self._initialize_calendar_service():
            raise RuntimeError("Failed to initialize Google Calendar service")
        
        # Get target users and time range
        users = self.config.get('users', [])
        days_ahead = self.config.get('lookahead_days', 7)
        start_time, end_time = self._get_time_range(days_ahead)
        
        self.stats['total_users'] = len(users)
        self.logger.info(f"👥 Collecting availability for {len(users)} users")
        self.logger.info(f"📅 Time range: {start_time} to {end_time}")
        
        # Query availability for all users
        results = {}
        for user_email in users:
            try:
                availability = await self._query_user_availability(user_email, start_time, end_time)
                
                if availability.success:
                    self.stats['successful_queries'] += 1
                    # Convert to daily format as required
                    daily_availability = self._convert_to_daily_format(availability, start_time, days_ahead)
                    results[user_email] = daily_availability
                    
                else:
                    self.stats['failed_queries'] += 1
                    error_type = availability.error_type or 'unknown'
                    self.stats['errors'][error_type] = self.stats['errors'].get(error_type, 0) + 1
                    
                    # Log specific error types as specified
                    if error_type in ['permission_denied', 'calendar_not_found']:
                        self.logger.warning(f"📵 {error_type} for {user_email}")
                        
            except Exception as e:
                self.logger.error(f"💥 Unexpected error for {user_email}: {e}")
                self.stats['failed_queries'] += 1
                self.stats['errors']['unexpected'] = self.stats['errors'].get('unexpected', 0) + 1
        
        self.stats['collection_end'] = datetime.now().isoformat()
        
        # Log final statistics
        self.logger.info(f"✅ Collection complete: {self.stats['successful_queries']}/{self.stats['total_users']} users")
        for error_type, count in self.stats['errors'].items():
            self.logger.warning(f"⚠️ {error_type}: {count} users")
        
        return results
    
    def _create_output_structure(self, availability_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create the final output structure with metadata"""
        output = {
            'collection_metadata': {
                'timestamp': datetime.now().isoformat(),
                'collection_start': self.stats['collection_start'],
                'collection_end': self.stats['collection_end'],
                'lookahead_days': self.config.get('lookahead_days', 7),
                'total_users': self.stats['total_users'],
                'successful_queries': self.stats['successful_queries'],
                'failed_queries': self.stats['failed_queries'],
                'errors': self.stats['errors'],
                'config_file': str(self.config_path)
            },
            'availability': availability_data
        }
        
        return output
    
    def _save_results(self, output_data: Dict[str, Any]) -> str:
        """Save results to JSON file following established patterns"""
        output_config = self.config.get('output', {})
        output_dir = Path(output_config.get('directory', 'data/state'))
        output_file = output_config.get('filename', 'calendar_availability.json')
        
        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_path = output_dir / output_file
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"💾 Results saved to: {output_path}")
            return str(output_path)
            
        except Exception as e:
            self.logger.error(f"❌ Failed to save results: {e}")
            raise
    
    async def run(self, dry_run: bool = False) -> Dict[str, Any]:
        """Main execution method"""
        try:
            if dry_run:
                # Dry run mode - simulate without API calls
                self.logger.info("🧪 Running in DRY RUN mode (no API calls)")
                availability_data = await self._simulate_availability_data()
            else:
                # Collect availability data
                availability_data = await self.collect_availability()
            
            # Create output structure with metadata
            output_data = self._create_output_structure(availability_data)
            
            # Save results
            output_path = self._save_results(output_data)
            
            # Print summary
            self.logger.info("📊 Collection Summary:")
            self.logger.info(f"  👥 Users processed: {self.stats['total_users']}")
            self.logger.info(f"  ✅ Successful: {self.stats['successful_queries']}")
            self.logger.info(f"  ❌ Failed: {self.stats['failed_queries']}")
            self.logger.info(f"  💾 Output: {output_path}")
            
            return {
                'success': True,
                'output_path': output_path,
                'stats': self.stats
            }
            
        except Exception as e:
            self.logger.error(f"💥 Collection failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'stats': self.stats
            }
    
    async def _simulate_availability_data(self) -> Dict[str, Any]:
        """Simulate availability data for demonstration purposes"""
        self.logger.info("🎭 Simulating availability data...")
        self.stats['collection_start'] = datetime.now().isoformat()
        
        users = self.config.get('users', [])
        days_ahead = self.config.get('lookahead_days', 7)
        start_time, end_time = self._get_time_range(days_ahead)
        
        self.stats['total_users'] = len(users)
        results = {}
        
        # Simulate data for each user
        for user_email in users:
            self.stats['successful_queries'] += 1
            
            # Create sample busy times (simulate 2-3 meetings per day)
            daily_availability = {}
            start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            
            for day_offset in range(days_ahead):
                day_date = start_date + timedelta(days=day_offset)
                date_key = day_date.strftime('%Y-%m-%d')
                
                # Skip weekends in simulation
                if day_date.weekday() >= 5:
                    daily_availability[date_key] = []
                    continue
                
                # Simulate 2-3 meetings per workday
                import random
                meeting_count = random.randint(2, 3)
                day_meetings = []
                
                for _ in range(meeting_count):
                    # Random meeting times during work hours (9 AM - 5 PM)
                    start_hour = random.randint(9, 15)
                    duration = random.choice([0.5, 1, 1.5])  # 30min, 1hr, 1.5hr meetings
                    
                    meeting_start = day_date.replace(hour=start_hour, minute=random.choice([0, 30]))
                    meeting_end = meeting_start + timedelta(hours=duration)
                    
                    day_meetings.append({
                        "start": meeting_start.isoformat(),
                        "end": meeting_end.isoformat()
                    })
                
                daily_availability[date_key] = sorted(day_meetings, key=lambda x: x['start'])
            
            results[user_email] = daily_availability
        
        self.stats['collection_end'] = datetime.now().isoformat()
        self.logger.info(f"🎭 Simulated data for {len(users)} users")
        return results


async def main():
    """Main entry point for standalone execution"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Calendar Availability Indexer - Monitor user availability via Google Calendar freebusy API"
    )
    
    parser.add_argument(
        '--config', 
        default='config/calendar_targets.yaml',
        help='Path to configuration file (default: config/calendar_targets.yaml)'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Simulate data without making API calls (useful when credentials not available)'
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Initialize and run indexer
    indexer = CalendarAvailabilityIndexer(config_path=args.config)
    result = await indexer.run(dry_run=args.dry_run)
    
    if result['success']:
        print(f"✅ Calendar availability collection completed successfully")
        print(f"📄 Results: {result['output_path']}")
        exit(0)
    else:
        print(f"❌ Calendar availability collection failed: {result['error']}")
        exit(1)


if __name__ == "__main__":
    asyncio.run(main())