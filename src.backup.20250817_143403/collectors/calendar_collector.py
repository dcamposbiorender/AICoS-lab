#!/usr/bin/env python3
"""
Calendar Collector - Dynamic discovery-based Google Calendar collection
Handles rate limiting, dynamic calendar discovery, and rule-based filtering
"""

import json
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set
import time

from ..core.auth_manager import credential_vault
from ..core.jsonl_writer import create_calendar_writer
from .employee_collector import EmployeeCollector

class CalendarRateLimiter:
    """Rate limiting with exponential backoff for bulk calendar collection"""
    
    def __init__(self, base_delay: float = 3.0, jitter_seconds: float = 2, daily_quota: int = 10000):
        # Conservative settings for bulk collection
        self.base_delay = base_delay  # 3 seconds base delay for bulk collection
        self.jitter_seconds = jitter_seconds
        self.last_request_time = 0
        self.request_count = 0
        
        # Daily quota tracking (Google Calendar API: 1M requests/day default)
        self.daily_quota = daily_quota
        self.daily_requests_made = 0
        self.quota_reset_time = datetime.now().replace(hour=0, minute=0, second=0) + timedelta(days=1)
        
        # Exponential backoff state for rate limiting
        self.consecutive_rate_limits = 0
        self.current_backoff_delay = 0
        self.backoff_levels = [60, 300, 600, 1800]  # 1min, 5min, 10min, 30min
        
    def wait_for_rate_limit(self):
        """Wait with exponential backoff, jitter, and daily quota management"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        # Check if we need to reset daily quota
        now = datetime.now()
        if now >= self.quota_reset_time:
            self.daily_requests_made = 0
            self.quota_reset_time = now.replace(hour=0, minute=0, second=0) + timedelta(days=1)
            print(f"    🔄 Daily quota reset: {self.daily_requests_made}/{self.daily_quota} requests used")
        
        # Check daily quota (leave 10% buffer for safety)
        quota_threshold = self.daily_quota * 0.9
        if self.daily_requests_made >= quota_threshold:
            time_until_reset = (self.quota_reset_time - now).total_seconds()
            if time_until_reset > 0:
                print(f"    🛑 Daily quota threshold reached ({self.daily_requests_made}/{self.daily_quota})")
                print(f"    ⏳ Waiting {time_until_reset/3600:.1f} hours until quota reset...")
                time.sleep(min(time_until_reset, 3600))  # Wait max 1 hour, then re-check
                return
        
        # Calculate total delay with backoff
        total_delay = self.base_delay + self.current_backoff_delay
        
        if time_since_last < total_delay:
            wait_time = total_delay - time_since_last
            
            # Add jitter to prevent thundering herd
            jitter = random.uniform(-self.jitter_seconds/2, self.jitter_seconds/2)
            wait_time = max(0, wait_time + jitter)
            
            if wait_time > 60:  # Inform user of long waits
                print(f"    ⏳ Calendar rate limit backoff: waiting {wait_time/60:.1f} minutes...")
            
            time.sleep(wait_time)
        
        self.last_request_time = time.time()
        self.request_count += 1
        self.daily_requests_made += 1
        
    def handle_rate_limit_error(self, error):
        """Handle Google API rate limit errors with exponential backoff"""
        if "quota" in str(error).lower() or "rate" in str(error).lower():
            self.consecutive_rate_limits += 1
            
            # Apply exponential backoff
            if self.consecutive_rate_limits <= len(self.backoff_levels):
                self.current_backoff_delay = self.backoff_levels[self.consecutive_rate_limits - 1]
            else:
                self.current_backoff_delay = self.backoff_levels[-1]  # Max 10min
            
            print(f"    🚫 Calendar API rate limited! Backing off for {self.current_backoff_delay/60:.1f} minutes")
            time.sleep(self.current_backoff_delay)
        else:
            # Success or other error - reset backoff
            if self.consecutive_rate_limits > 0:
                print(f"    ✅ Calendar rate limit recovered")
                self.consecutive_rate_limits = 0
                self.current_backoff_delay = 0

class CalendarCollector:
    """
    Dynamic discovery-based Google Calendar collector with rule-based filtering
    Discovers all calendars and users, then applies collection rules
    """
    
    def __init__(self, config_path: Optional[Path] = None):
        self.project_root = Path(__file__).parent.parent.parent
        
        # Load configuration
        self.config = self._load_config(config_path)
        
        # Initialize storage paths
        today = datetime.now().strftime("%Y-%m-%d")
        self.data_path = self.project_root / "data" / "raw" / "calendar" / today
        self.data_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize rate limiter with bulk collection settings
        self.rate_limiter = CalendarRateLimiter(
            base_delay=self.config.get('base_delay_seconds', 3.0),  # Conservative 3s for bulk collection
            jitter_seconds=self.config.get('jitter_seconds', 2.0)
        )
        
        # Initialize Google Calendar service
        self.calendar_service = None
        
        # Discovery caches
        self.calendar_cache = {}
        self.user_cache = {}
        
        # Collection results
        self.collection_results = {
            "status": "initialized",
            "discovered": {"calendars": 0, "users": 0},
            "collected": {"calendars": 0, "events": 0},
            "data_path": str(self.data_path),
            "next_cursor": None
        }
        
        # Initialize JSONL writer for persistence
        self.jsonl_writer = create_calendar_writer()
        
        print(f"📅 CALENDAR COLLECTOR INITIALIZED")
        print(f"💾 Storage: {self.data_path}")
        print(f"⚡ Rate limit: {self.config.get('requests_per_second', 10.0)} req/sec")
    
    def _load_config(self, config_path: Optional[Path] = None) -> Dict:
        """Load collection configuration with rule-based filtering"""
        default_config = {
            "base_delay_seconds": 3.0,  # 3 seconds between requests for bulk collection
            "jitter_seconds": 2.0,      # 2 seconds jitter for predictable timing
            "lookback_days": 90,        # 90-day lookback for bulk collection
            "lookahead_days": 90,       # 90-day lookahead for future events
            "collection_rules": {
                "collect_all_accessible": True,
                "exclude_patterns": ["test-*", "archive-*"],
                "must_include": ["leadership", "executive"],
                "include_shared": True,
                "primary_only": False
            },
            "max_retries": 3,
            "backoff_multiplier": 2.0,
            # Progressive time window collection settings
            "time_windows": [7, 30, 90, 365],  # Days to collect for each window
            "time_window_delay": 60,    # Seconds to wait between time windows
            "progressive_collection": {
                "enabled": True,
                "save_each_window": True,  # Save data after each window completes
                "continue_on_window_failure": True  # Continue to next window if one fails
            }
        }
        
        if config_path and config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    user_config = json.load(f)
                default_config.update(user_config)
                print(f"✅ Config loaded from {config_path}")
            except Exception as e:
                print(f"⚠️ Failed to load config from {config_path}: {e}")
        
        return default_config
    
    def _save_events_to_jsonl(self, calendar_data: Dict) -> Dict[str, int]:
        """
        Save calendar events to JSONL format organized by calendar
        
        Args:
            calendar_data: Dictionary mapping calendar_id -> calendar data with events
            
        Returns:
            Dictionary mapping calendar_id -> number of events saved
        """
        try:
            # Extract events from calendar data
            events_by_calendar = {}
            
            for calendar_id, calendar_info in calendar_data.items():
                events = calendar_info.get('events', [])
                
                if events:
                    # Add calendar context to each event
                    enriched_events = []
                    for event in events:
                        enriched_event = dict(event)  # Don't modify original
                        enriched_event['calendar_id'] = calendar_id
                        enriched_event['calendar_name'] = calendar_info.get('calendar', {}).get('summary', 'unknown')
                        enriched_event['collection_metadata'] = calendar_info.get('collection_metadata', {})
                        enriched_events.append(enriched_event)
                    
                    events_by_calendar[calendar_id] = enriched_events
            
            # Write events to JSONL using the centralized writer
            if events_by_calendar:
                results = self.jsonl_writer.write_events_by_calendar(events_by_calendar)
                total_events = sum(results.values())
                print(f"💾 JSONL: Saved {total_events} events across {len(results)} calendars to archive")
                return results
            else:
                print(f"💾 JSONL: No events to save")
                return {}
                
        except Exception as e:
            print(f"❌ JSONL persistence failed: {e}")
            # Don't fail the entire collection if JSONL persistence fails
            return {}

    def _save_calendar_data(self, calendar_data: Dict, user_data: Dict):
        """Save calendar data to dated directory structure and JSONL archive"""
        
        # FIRST: Save events to JSONL archive for persistent storage
        jsonl_results = self._save_events_to_jsonl(calendar_data)
        
        # THEN: Save calendar data to JSON (for immediate access)
        calendars_file = self.data_path / "calendars.json"
        with open(calendars_file, 'w') as f:
            json.dump(calendar_data, f, indent=2)
        
        # Save user data
        users_file = self.data_path / "users.json"
        with open(users_file, 'w') as f:
            json.dump(user_data, f, indent=2)
        
        # Save events as JSONL (legacy format for compatibility)
        events_file = self.data_path / "events.jsonl"
        with open(events_file, 'w') as f:
            for calendar_id, calendar_info in calendar_data.items():
                for event in calendar_info.get('events', []):
                    event_record = {
                        'calendar_id': calendar_id,
                        'event': event,
                        'collected_at': datetime.now().isoformat()
                    }
                    f.write(json.dumps(event_record) + '\n')
        
        print(f"💾 Data saved to {self.data_path}")
        if jsonl_results:
            total_jsonl_events = sum(jsonl_results.values())
            print(f"💾 JSONL archive: {total_jsonl_events} events persisted permanently")

    def setup_calendar_service(self) -> bool:
        """Setup Google Calendar service"""
        try:
            auth_status = credential_vault.validate_authentication()
            if not auth_status.get('google_oauth'):
                print("❌ Google OAuth credentials not available")
                return False
            
            self.calendar_service = credential_vault.get_google_service('calendar', 'v3')
            if not self.calendar_service:
                print("❌ Failed to create Google Calendar service")
                return False
            
            print("✅ Google Calendar service ready")
            return True
            
        except Exception as e:
            print(f"❌ Calendar service setup failed: {e}")
            return False

    def discover_all_calendars(self) -> Dict[str, Dict]:
        """Discover all accessible calendars in Google account"""
        
        discovered_calendars = {}
        start_time = time.time()
        
        try:
            # Rate limiting
            self.rate_limiter.wait_for_rate_limit()
            
            calendar_list = self.calendar_service.calendarList().list().execute()
            calendars = calendar_list.get('items', [])
            
            elapsed = time.time() - start_time
            print(f"🔍 Discovered {len(calendars)} total calendars ({elapsed:.1f}s elapsed)")
            
            for calendar in calendars:
                calendar_id = calendar['id']
                calendar_info = {
                    'id': calendar_id,
                    'summary': calendar.get('summary', 'Unnamed Calendar'),
                    'description': calendar.get('description', ''),
                    'primary': calendar.get('primary', False),
                    'access_role': calendar.get('accessRole', 'unknown'),
                    'selected': calendar.get('selected', False),
                    'color_id': calendar.get('colorId'),
                    'background_color': calendar.get('backgroundColor'),
                    'foreground_color': calendar.get('foregroundColor'),
                    'time_zone': calendar.get('timeZone'),
                    'discovered_at': datetime.now().isoformat()
                }
                
                discovered_calendars[calendar_id] = calendar_info
            
            self.calendar_cache = discovered_calendars
            self.collection_results["discovered"]["calendars"] = len(discovered_calendars)
            
            print(f"✅ Calendar discovery complete: {len(discovered_calendars)} calendars")
            return discovered_calendars
            
        except Exception as e:
            print(f"❌ Calendar discovery failed: {e}")
            return {}

    def discover_employee_calendars(self) -> Dict[str, Dict]:
        """
        Discover calendars for ALL employees by attempting calendar access for each email
        Returns accessible calendars with employee context
        """
        print(f"\n🔍 DISCOVERING EMPLOYEE CALENDARS")
        print("-" * 40)
        
        employee_calendars = {}
        successful_calendars = 0
        access_denied_count = 0
        
        try:
            # Get employee roster from Slack (contains email addresses)
            employee_collector = EmployeeCollector()
            slack_employees = employee_collector.build_roster_from_slack()
            
            total_employees = len(slack_employees)
            print(f"📋 Found {total_employees} employees from Slack roster")
            
            if not slack_employees:
                print("❌ No employees found in roster")
                return {}
            
            # Process each employee email
            for idx, (email, employee_data) in enumerate(slack_employees.items(), 1):
                self.rate_limiter.wait_for_rate_limit()
                
                try:
                    # Attempt to access the employee's primary calendar
                    # Google Calendar uses email as calendar ID for primary calendars
                    calendar_info = self.calendar_service.calendars().get(calendarId=email).execute()
                    
                    # Success! This employee's calendar is accessible
                    employee_calendars[email] = {
                        'calendar_id': email,
                        'summary': calendar_info.get('summary', f"{employee_data.get('display_name', email)}'s Calendar"),
                        'description': calendar_info.get('description', ''),
                        'primary': True,  # Employee primary calendars
                        'access_role': 'reader',  # We have at least read access
                        'time_zone': calendar_info.get('timeZone', 'UTC'),
                        'employee_context': {
                            'slack_id': employee_data.get('slack_id'),
                            'display_name': employee_data.get('display_name'),
                            'title': employee_data.get('title', ''),
                            'team': employee_data.get('team', ''),
                            'department': employee_data.get('department', '')
                        },
                        'discovered_at': datetime.now().isoformat(),
                        'discovery_method': 'employee_email_lookup'
                    }
                    
                    successful_calendars += 1
                    if idx % 10 == 0:  # Progress every 10 employees
                        print(f"    📊 Progress: {idx}/{total_employees} employees checked, {successful_calendars} calendars accessible")
                    
                except Exception as e:
                    # Expected for many employees - calendar not shared or accessible
                    access_denied_count += 1
                    if "403" in str(e) or "Forbidden" in str(e):
                        # Normal - employee hasn't shared calendar
                        pass
                    elif "404" in str(e) or "Not Found" in str(e):
                        # Normal - calendar doesn't exist or not accessible
                        pass
                    else:
                        # Unexpected error - log it
                        print(f"    ⚠️ Unexpected error for {email}: {str(e)[:80]}")
            
            print(f"✅ Employee calendar discovery complete:")
            print(f"    📧 Total employees checked: {total_employees}")
            print(f"    ✅ Accessible calendars: {successful_calendars}")
            print(f"    🔒 Access denied/not found: {access_denied_count}")
            print(f"    📊 Success rate: {successful_calendars/total_employees*100:.1f}%")
            
            return employee_calendars
            
        except Exception as e:
            print(f"❌ Employee calendar discovery failed: {e}")
            return {}

    def collect_calendar_events_weekly_chunks(self, calendar_id: str, calendar_info: Dict, weeks_backward: int = 26, weeks_forward: int = 4) -> List[Dict]:
        """
        Collect calendar events in weekly chunks for efficient processing
        
        Args:
            calendar_id: Google Calendar ID
            calendar_info: Calendar metadata
            weeks_backward: Number of weeks to collect backwards (default 26 = 6 months)
            weeks_forward: Number of weeks to collect forward (default 4 = 30 days)
            
        Returns:
            List of all events collected across all weekly chunks
        """
        all_events = []
        total_chunks = weeks_backward + weeks_forward
        successful_chunks = 0
        
        calendar_name = calendar_info.get('summary', calendar_id)
        print(f"    📅 Collecting {calendar_name} in {total_chunks} weekly chunks...")
        
        # Start from weeks_backward weeks ago
        current_date = datetime.now() - timedelta(weeks=weeks_backward)
        
        for chunk_idx in range(total_chunks):
            chunk_start = current_date + timedelta(weeks=chunk_idx)
            chunk_end = chunk_start + timedelta(days=7)  # 7-day chunks
            
            try:
                self.rate_limiter.wait_for_rate_limit()
                
                # Collect events for this week
                chunk_events = self._collect_events_with_retry(
                    calendar_id=calendar_id,
                    start_date=chunk_start,
                    end_date=chunk_end
                )
                
                # Add chunk context to events
                for event in chunk_events:
                    event['collection_chunk'] = {
                        'chunk_number': chunk_idx + 1,
                        'total_chunks': total_chunks,
                        'chunk_start': chunk_start.isoformat(),
                        'chunk_end': chunk_end.isoformat(),
                        'collection_method': 'weekly_chunks'
                    }
                
                all_events.extend(chunk_events)
                successful_chunks += 1
                
                # Progress reporting every 4 weeks (monthly)
                if (chunk_idx + 1) % 4 == 0:
                    events_so_far = len(all_events)
                    print(f"        📊 Week {chunk_idx + 1}/{total_chunks}: {events_so_far} events collected")
                
            except Exception as e:
                error_str = str(e)
                if "403" in error_str or "Forbidden" in error_str:
                    print(f"        🔒 Access denied for week {chunk_idx + 1} - skipping")
                elif "429" in error_str or "quota" in error_str.lower():
                    print(f"        ⚠️ Rate limit hit on week {chunk_idx + 1} - backing off")
                    self.rate_limiter.handle_rate_limit_error(e)
                    # Retry this chunk once after backoff
                    try:
                        chunk_events = self._collect_events_with_retry(calendar_id, chunk_start, chunk_end)
                        all_events.extend(chunk_events)
                        successful_chunks += 1
                    except:
                        print(f"        ❌ Failed to collect week {chunk_idx + 1} after retry")
                else:
                    print(f"        ⚠️ Error collecting week {chunk_idx + 1}: {error_str[:60]}")
        
        print(f"    ✅ {calendar_name}: {len(all_events)} events from {successful_chunks}/{total_chunks} weeks")
        return all_events

    def collect_all_employee_calendars(self, weeks_backward: int = 26, weeks_forward: int = 4) -> Dict[str, Dict]:
        """
        Collect ALL accessible employee calendars in weekly chunks
        
        Args:
            weeks_backward: Number of weeks to collect backwards (default 26 = 6 months)
            weeks_forward: Number of weeks to collect forward (default 4 = 30 days)
            
        Returns:
            Dictionary of calendar_id -> {calendar_info, events, collection_stats}
        """
        print(f"\n📅 BULK EMPLOYEE CALENDAR COLLECTION")
        print(f"📊 Target: {weeks_backward} weeks backward + {weeks_forward} weeks forward")
        print(f"📊 Collection period: {weeks_backward + weeks_forward} weeks per calendar")
        print("=" * 60)
        
        collection_start_time = time.time()
        all_calendar_data = {}
        total_events_collected = 0
        total_api_requests = 0
        
        try:
            # Step 1: Discover all employee calendars
            employee_calendars = self.discover_employee_calendars()
            
            if not employee_calendars:
                print("❌ No accessible employee calendars found")
                return {}
            
            total_calendars = len(employee_calendars)
            print(f"\n🚀 Starting bulk collection from {total_calendars} employee calendars")
            
            # Step 2: Collect from each accessible calendar in weekly chunks
            for calendar_idx, (calendar_id, calendar_info) in enumerate(employee_calendars.items(), 1):
                calendar_start_time = time.time()
                
                print(f"\n[{calendar_idx}/{total_calendars}] Processing {calendar_info.get('employee_context', {}).get('display_name', calendar_id)}")
                
                try:
                    # Collect events in weekly chunks
                    events = self.collect_calendar_events_weekly_chunks(
                        calendar_id=calendar_id,
                        calendar_info=calendar_info,
                        weeks_backward=weeks_backward,
                        weeks_forward=weeks_forward
                    )
                    
                    # Store calendar data with events
                    calendar_duration = time.time() - calendar_start_time
                    all_calendar_data[calendar_id] = {
                        'calendar': calendar_info,
                        'events': events,
                        'collection_metadata': {
                            'events_collected': len(events),
                            'collection_duration_seconds': calendar_duration,
                            'weeks_backward': weeks_backward,
                            'weeks_forward': weeks_forward,
                            'total_weeks': weeks_backward + weeks_forward,
                            'collected_at': datetime.now().isoformat(),
                            'collection_method': 'employee_bulk_weekly_chunks'
                        }
                    }
                    
                    total_events_collected += len(events)
                    total_api_requests += (weeks_backward + weeks_forward)  # Approximate API calls
                    
                    # Progress report every 10 calendars
                    if calendar_idx % 10 == 0:
                        elapsed_hours = (time.time() - collection_start_time) / 3600
                        avg_events_per_calendar = total_events_collected / calendar_idx if calendar_idx > 0 else 0
                        print(f"    📊 PROGRESS: {calendar_idx}/{total_calendars} calendars, {total_events_collected} events, {elapsed_hours:.1f}h elapsed")
                        print(f"    📊 Average: {avg_events_per_calendar:.1f} events/calendar")
                    
                except Exception as e:
                    print(f"    ❌ Failed to collect {calendar_id}: {str(e)[:80]}")
                    # Continue with next calendar
            
            # Final statistics
            collection_duration = time.time() - collection_start_time
            successful_calendars = len(all_calendar_data)
            
            print(f"\n🎉 BULK EMPLOYEE CALENDAR COLLECTION COMPLETE!")
            print(f"    ✅ Calendars processed: {successful_calendars}/{total_calendars}")
            print(f"    📊 Total events collected: {total_events_collected:,}")
            print(f"    🕒 Total duration: {collection_duration/3600:.2f} hours")
            print(f"    ⚡ API requests made: ~{total_api_requests:,}")
            print(f"    📊 Average events per calendar: {total_events_collected/successful_calendars:.1f}")
            
            # Save to JSONL archive
            if all_calendar_data:
                self._save_calendar_data(all_calendar_data, {})
            
            return all_calendar_data
            
        except Exception as e:
            print(f"❌ Bulk employee calendar collection failed: {e}")
            return {}
    
    def apply_collection_rules(self, calendars: Dict[str, Dict]) -> Dict[str, Dict]:
        """Apply collection rules to filter calendars"""
        rules = self.config.get('collection_rules', {})
        filtered_calendars = {}
        
        for calendar_id, calendar in calendars.items():
            calendar_name = calendar.get('summary', '').lower()
            
            # Check access role - must be at least reader
            access_role = calendar.get('access_role', '')
            if access_role not in ['owner', 'reader', 'writer']:
                continue
            
            # Skip if primary_only is True and this isn't primary
            if rules.get('primary_only', False) and not calendar.get('primary', False):
                continue
            
            # Check must_include patterns first
            must_include = rules.get('must_include', [])
            if must_include and any(pattern.lower() in calendar_name for pattern in must_include):
                filtered_calendars[calendar_id] = calendar
                continue
            
            # Check exclude patterns
            exclude_patterns = rules.get('exclude_patterns', [])
            if any(self._matches_pattern(calendar_name, pattern.lower()) for pattern in exclude_patterns):
                continue
            
            # Include if collect_all_accessible is True
            if rules.get('collect_all_accessible', True):
                filtered_calendars[calendar_id] = calendar
        
        print(f"📋 Filtered calendars: {len(filtered_calendars)}/{len(calendars)} calendars selected")
        return filtered_calendars
    
    def _matches_pattern(self, name: str, pattern: str) -> bool:
        """Simple pattern matching for calendar names"""
        if pattern.endswith('*'):
            return name.startswith(pattern[:-1])
        elif pattern.startswith('*'):
            return name.endswith(pattern[1:])
        else:
            return pattern in name

    def _collect_events_with_retry(self, calendar_id: str, start_date: datetime, end_date: datetime, max_retries: int = 3, backoff_multiplier: float = 2.0) -> List[Dict]:
        """Collect events with exponential backoff retry"""
        
        for attempt in range(max_retries):
            try:
                events_result = self.calendar_service.events().list(
                    calendarId=calendar_id,
                    timeMin=start_date.isoformat() + 'Z',
                    timeMax=end_date.isoformat() + 'Z',
                    maxResults=2500,
                    singleEvents=True,
                    orderBy='startTime'
                ).execute()
                
                return events_result.get('items', [])
                
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                
                # Exponential backoff
                wait_time = (backoff_multiplier ** attempt) + random.uniform(0, 2)
                print(f"    ⏳ Retry {attempt + 1}/{max_retries} in {wait_time:.1f}s: {str(e)[:50]}")
                time.sleep(wait_time)
        
        return []

    def discover_calendar_users(self, calendar_data: Dict[str, Dict]) -> Dict[str, Dict]:
        """Discover users from calendar attendees across all calendars"""
        
        discovered_users = {}
        
        for calendar_id, calendar_info in calendar_data.items():
            for event in calendar_info.get('events', []):
                # Process organizer
                organizer = event.get('organizer', {})
                if organizer.get('email'):
                    email = organizer['email'].lower()
                    if email not in discovered_users:
                        discovered_users[email] = {
                            'email': email,
                            'display_name': organizer.get('displayName', email.split('@')[0]),
                            'first_seen': datetime.now().isoformat(),
                            'role': 'organizer',
                            'meeting_count': 0
                        }
                    discovered_users[email]['meeting_count'] += 1
                
                # Process attendees
                for attendee in event.get('attendees', []):
                    if attendee.get('email'):
                        email = attendee['email'].lower()
                        if email not in discovered_users:
                            discovered_users[email] = {
                                'email': email,
                                'display_name': attendee.get('displayName', email.split('@')[0]),
                                'first_seen': datetime.now().isoformat(),
                                'role': 'attendee',
                                'meeting_count': 0
                            }
                        discovered_users[email]['meeting_count'] += 1
        
        self.user_cache = discovered_users
        self.collection_results["discovered"]["users"] = len(discovered_users)
        
        print(f"👥 Discovered {len(discovered_users)} users from calendar events")
        return discovered_users
    
    def _process_events(self, events: List[Dict], calendar_info: Dict) -> List[Dict]:
        """Process and enrich calendar events"""
        processed_events = []
        
        for event in events:
            # Extract key information
            processed_event = {
                'id': event.get('id'),
                'summary': event.get('summary', 'No Title'),
                'description': event.get('description', ''),
                'start': event.get('start', {}),
                'end': event.get('end', {}),
                'attendees': event.get('attendees', []),
                'organizer': event.get('organizer', {}),
                'created': event.get('created'),
                'updated': event.get('updated'),
                'status': event.get('status'),
                'visibility': event.get('visibility', 'default'),
                'location': event.get('location', ''),
                'recurring_event_id': event.get('recurringEventId'),
                'etag': event.get('etag'),
                
                # Add processing metadata
                'processed_at': datetime.now().isoformat(),
                'calendar_id': calendar_info.get('id'),
                'calendar_name': calendar_info.get('summary'),
                'is_all_day': bool(event.get('start', {}).get('date')),
                'attendee_count': len(event.get('attendees', [])),
                'has_external_attendees': self._has_external_attendees(event.get('attendees', [])),
                'meeting_duration_minutes': self._calculate_duration(event.get('start', {}), event.get('end', {}))
            }
            
            processed_events.append(processed_event)
        
        return processed_events
    
    def _has_external_attendees(self, attendees: List[Dict]) -> bool:
        """Check if meeting has external attendees (non-internal domain)"""
        # Get primary domain from config or use heuristic
        internal_domain = self.config.get('internal_domain', self._detect_internal_domain())
        
        for attendee in attendees:
            email = attendee.get('email', '')
            if email and internal_domain not in email.lower():
                return True
        return False
    
    def _detect_internal_domain(self) -> str:
        """Detect internal domain from primary calendar"""
        if hasattr(self, 'calendar_service') and self.calendar_service:
            try:
                profile = self.calendar_service.calendarList().get(calendarId='primary').execute()
                primary_email = profile.get('id', '')
                if '@' in primary_email:
                    return '@' + primary_email.split('@')[1]
            except:
                pass
        return '@company.com'  # fallback
    
    def _calculate_duration(self, start: Dict, end: Dict) -> Optional[int]:
        """Calculate meeting duration in minutes"""
        try:
            if start.get('dateTime') and end.get('dateTime'):
                start_dt = datetime.fromisoformat(start['dateTime'].replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(end['dateTime'].replace('Z', '+00:00'))
                return int((end_dt - start_dt).total_seconds() / 60)
        except:
            pass
        return None
    
    def _calculate_calendar_analytics(self, events: List[Dict], calendar_info: Dict) -> Dict:
        """Calculate calendar analytics for calendar"""
        if not events:
            return {}
        
        total_events = len(events)
        timed_events = [e for e in events if not e['is_all_day']]
        meetings_with_attendees = [e for e in events if e['attendee_count'] > 1]
        external_meetings = [e for e in events if e['has_external_attendees']]
        
        # Calculate total meeting time
        total_meeting_minutes = sum(
            e['meeting_duration_minutes'] for e in timed_events 
            if e['meeting_duration_minutes'] is not None
        )
        
        analytics = {
            'summary': {
                'calendar_name': calendar_info.get('summary', 'Unknown'),
                'total_events': total_events,
                'timed_events': len(timed_events),
                'all_day_events': total_events - len(timed_events),
                'meetings_with_attendees': len(meetings_with_attendees),
                'external_meetings': len(external_meetings),
                'total_meeting_hours': round(total_meeting_minutes / 60, 1),
                'average_meeting_duration': round(total_meeting_minutes / len(timed_events), 1) if timed_events else 0
            },
            'collaboration': {
                'internal_collaborators': len(self._extract_internal_collaborators(events)),
                'external_collaborators': len(self._extract_external_collaborators(events)),
                'most_frequent_collaborators': self._get_frequent_collaborators(events)[:10]
            },
            'patterns': {
                'busiest_day_of_week': self._get_busiest_day(timed_events),
                'peak_meeting_hour': self._get_peak_hour(timed_events),
                'date_range_days': (self.config.get('lookback_days', 30) + self.config.get('lookahead_days', 30)),
                'recurring_meetings': len([e for e in events if e['recurring_event_id']])
            }
        }
        
        return analytics
    
    def _extract_internal_collaborators(self, events: List[Dict]) -> Set[str]:
        """Extract unique internal collaborators"""
        internal_domain = self.config.get('internal_domain', self._detect_internal_domain())
        collaborators = set()
        for event in events:
            for attendee in event['attendees']:
                email = attendee.get('email', '').lower()
                if email and internal_domain in email:
                    collaborators.add(email)
        return collaborators
    
    def _extract_external_collaborators(self, events: List[Dict]) -> Set[str]:
        """Extract unique external collaborators"""
        internal_domain = self.config.get('internal_domain', self._detect_internal_domain())
        collaborators = set()
        for event in events:
            for attendee in event['attendees']:
                email = attendee.get('email', '').lower()
                if email and internal_domain not in email:
                    collaborators.add(email)
        return collaborators
    
    def _get_frequent_collaborators(self, events: List[Dict]) -> List[Dict]:
        """Get most frequent collaborators"""
        internal_domain = self.config.get('internal_domain', self._detect_internal_domain())
        collaborator_counts = {}
        for event in events:
            for attendee in event['attendees']:
                email = attendee.get('email', '').lower()
                if email and internal_domain in email:
                    collaborator_counts[email] = collaborator_counts.get(email, 0) + 1
        
        return [
            {'email': email, 'meeting_count': count}
            for email, count in sorted(collaborator_counts.items(), key=lambda x: x[1], reverse=True)
        ]
    
    def _get_busiest_day(self, events: List[Dict]) -> Optional[str]:
        """Get busiest day of week"""
        day_counts = {}
        for event in events:
            start_time = event.get('start', {}).get('dateTime')
            if start_time:
                try:
                    dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    day = dt.strftime('%A')
                    day_counts[day] = day_counts.get(day, 0) + 1
                except:
                    continue
        
        return max(day_counts, key=day_counts.get) if day_counts else None
    
    def _get_peak_hour(self, events: List[Dict]) -> Optional[int]:
        """Get peak meeting hour"""
        hour_counts = {}
        for event in events:
            start_time = event.get('start', {}).get('dateTime')
            if start_time:
                try:
                    dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    hour = dt.hour
                    hour_counts[hour] = hour_counts.get(hour, 0) + 1
                except:
                    continue
        
        return max(hour_counts, key=hour_counts.get) if hour_counts else None

    def collect_from_employee_list(self, employee_emails: Dict[str, str], days_back: int = 30) -> Dict:
        """
        Collect calendar events from a list of employee email addresses for bulk collection
        
        Args:
            employee_emails: Dictionary mapping email -> calendar_id 
            days_back: Number of days to look back for events
            
        Returns:
            Dictionary with collection results and statistics
        """
        print(f"\n🏢 BULK CALENDAR COLLECTION FROM {len(employee_emails)} EMPLOYEES")
        print(f"📅 Looking back {days_back} days from today")
        print("-" * 60)
        
        collected_data = {}
        successful_collections = 0
        failed_collections = 0
        permission_denied = 0
        total_events = 0
        
        # Calculate date range
        start_date = datetime.now() - timedelta(days=days_back)
        end_date = datetime.now()
        
        # Convert to list for progress tracking
        employee_list = list(employee_emails.items())
        
        for i, (email, calendar_id) in enumerate(employee_list, 1):
            # Progress update every 10 employees
            if i % 10 == 0 or i == len(employee_list):
                progress = (i / len(employee_list)) * 100
                print(f"📊 Progress: {i}/{len(employee_list)} ({progress:.1f}%) calendars processed")
            
            print(f"  [{i}/{len(employee_list)}] {email[:30]}{'...' if len(email) > 30 else ''}")
            
            try:
                # Rate limiting - critical for bulk collection
                self.rate_limiter.wait_for_rate_limit()
                
                # Create calendar info structure for this employee
                calendar_info = {
                    'id': calendar_id,
                    'summary': f"{email.split('@')[0]}'s Calendar",
                    'description': f"Personal calendar for {email}",
                    'primary': email == calendar_id,  # Usually true in Google Workspace
                    'access_role': 'reader',  # Assume read access
                    'employee_email': email,
                    'discovered_at': datetime.now().isoformat()
                }
                
                # Collect events with retry logic
                events = self._collect_events_with_retry(
                    calendar_id,
                    start_date,
                    end_date,
                    self.config.get('max_retries', 2),  # Fewer retries for bulk
                    self.config.get('backoff_multiplier', 2.0)
                )
                
                # Process events
                processed_events = self._process_events(events, calendar_info)
                
                # Calculate analytics
                analytics = self._calculate_calendar_analytics(processed_events, calendar_info)
                
                calendar_data = {
                    'calendar': calendar_info,
                    'collection_metadata': {
                        'last_collected': datetime.now().isoformat(),
                        'date_range': {
                            'start_date': start_date.isoformat(),
                            'end_date': end_date.isoformat()
                        },
                        'days_back': days_back,
                        'events_count': len(processed_events),
                        'collection_method': 'bulk_employee_collection',
                        'employee_email': email
                    },
                    'events': processed_events,
                    'analytics': analytics
                }
                
                collected_data[calendar_id] = calendar_data
                successful_collections += 1
                total_events += len(processed_events)
                
                print(f"    ✅ {len(processed_events)} events collected")
                
            except Exception as e:
                error_message = str(e).lower()
                
                # Categorize different types of failures
                if 'forbidden' in error_message or 'permission' in error_message or 'access' in error_message:
                    permission_denied += 1
                    failure_type = 'permission_denied'
                    print(f"    🚫 Access denied (private calendar)")
                else:
                    failure_type = 'collection_error'
                    print(f"    ❌ Collection failed: {str(e)[:50]}")
                
                error_data = {
                    'calendar': calendar_info,
                    'collection_metadata': {
                        'last_attempted': datetime.now().isoformat(),
                        'error': str(e),
                        'error_type': failure_type,
                        'collection_status': 'failed',
                        'employee_email': email
                    },
                    'events': [],
                    'analytics': {}
                }
                
                collected_data[calendar_id] = error_data
                failed_collections += 1
            
            # Brief pause between employee calendars for bulk collection
            time.sleep(0.2)
        
        # Calculate final statistics
        total_attempted = len(employee_list)
        success_rate = (successful_collections / total_attempted) * 100 if total_attempted else 0
        
        collection_results = {
            'bulk_collection_summary': {
                'total_employees': total_attempted,
                'successful_collections': successful_collections,
                'failed_collections': failed_collections,
                'permission_denied': permission_denied,
                'total_events_collected': total_events,
                'success_rate': round(success_rate, 1),
                'days_back': days_back,
                'date_range': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat()
                }
            },
            'collected_data': collected_data
        }
        
        print(f"\n📊 BULK COLLECTION COMPLETE:")
        print(f"  ✅ Successful: {successful_collections}/{total_attempted} ({success_rate:.1f}%)")
        print(f"  🚫 Permission denied: {permission_denied}")
        print(f"  ❌ Other failures: {failed_collections - permission_denied}")
        print(f"  📅 Total events: {total_events}")
        print(f"  📈 Requests made: {self.rate_limiter.request_count}")
        
        return collection_results

    def collect_from_filtered_calendars(self, calendars: Dict[str, Dict], max_calendars: int = 50) -> Dict:
        """Collect events from filtered calendars with rate limiting"""
        
        collected_data = {}
        successful_collections = 0
        failed_collections = 0
        total_events = 0
        
        # Limit calendars to process
        calendar_list = list(calendars.items())[:max_calendars]
        
        print(f"\n📅 COLLECTING FROM {len(calendar_list)} FILTERED CALENDARS")
        
        # Calculate date range
        start_date = datetime.now() - timedelta(days=self.config.get('lookback_days', 30))
        end_date = datetime.now() + timedelta(days=self.config.get('lookahead_days', 30))
        
        for i, (calendar_id, calendar_info) in enumerate(calendar_list, 1):
            print(f"  [{i}/{len(calendar_list)}] Collecting: {calendar_info.get('summary', calendar_id)}")
            
            try:
                # Rate limiting
                self.rate_limiter.wait_for_rate_limit()
                
                # Collect events with retry logic
                events = self._collect_events_with_retry(
                    calendar_id,
                    start_date,
                    end_date,
                    self.config.get('max_retries', 3),
                    self.config.get('backoff_multiplier', 2.0)
                )
                
                # Process events
                processed_events = self._process_events(events, calendar_info)
                
                # Calculate analytics
                analytics = self._calculate_calendar_analytics(processed_events, calendar_info)
                
                calendar_data = {
                    'calendar': calendar_info,
                    'collection_metadata': {
                        'last_collected': datetime.now().isoformat(),
                        'date_range': {
                            'start_date': start_date.isoformat(),
                            'end_date': end_date.isoformat()
                        },
                        'events_count': len(processed_events),
                        'collection_method': 'dynamic_discovery'
                    },
                    'events': processed_events,
                    'analytics': analytics
                }
                
                collected_data[calendar_id] = calendar_data
                successful_collections += 1
                total_events += len(processed_events)
                
                print(f"    ✅ {len(processed_events)} events collected from {calendar_info.get('summary', 'Unknown')}")
                
            except Exception as e:
                error_data = {
                    'calendar': calendar_info,
                    'collection_metadata': {
                        'last_attempted': datetime.now().isoformat(),
                        'error': str(e),
                        'collection_status': 'failed'
                    },
                    'events': [],
                    'analytics': {}
                }
                
                collected_data[calendar_id] = error_data
                failed_collections += 1
                print(f"    ❌ Failed to collect from {calendar_info.get('summary', 'Unknown')}: {e}")
            
            # Brief pause between calendars
            time.sleep(0.5)
        
        collection_results = {
            'collected_data': collected_data,
            'successful_collections': successful_collections,
            'failed_collections': failed_collections,
            'total_events_collected': total_events,
            'success_rate': (successful_collections / len(calendar_list)) * 100 if calendar_list else 0
        }
        
        print(f"✅ Calendar collection complete: {successful_collections}/{len(calendar_list)} success")
        return collection_results
    
    def collect_progressive_time_windows(self, employee_emails: Dict[str, str]) -> Dict:
        """
        Collect calendar data across multiple time windows with rate limiting between windows
        
        Args:
            employee_emails: Dictionary mapping email -> calendar_id
            
        Returns:
            Dictionary with results from all time windows
        """
        if not self.config.get('progressive_collection', {}).get('enabled', True):
            print("⚠️ Progressive collection is disabled, using standard collection")
            return self.collect_from_employee_list(employee_emails, self.config.get('lookback_days', 30))
        
        time_windows = self.config.get('time_windows', [7, 30, 90, 365])
        time_window_delay = self.config.get('time_window_delay', 60)
        
        print(f"\n🔄 PROGRESSIVE TIME WINDOW COLLECTION")
        print(f"📊 Time windows: {time_windows} days")
        print(f"👥 Target employees: {len(employee_emails)}")
        print(f"⏱️ Delay between windows: {time_window_delay}s")
        print("=" * 70)
        
        all_results = {
            'progressive_summary': {
                'time_windows': time_windows,
                'total_employees': len(employee_emails),
                'window_delay_seconds': time_window_delay,
                'collection_start': datetime.now().isoformat()
            },
            'window_results': {},
            'aggregated_stats': {
                'total_successful_collections': 0,
                'total_failed_collections': 0,
                'total_events_collected': 0,
                'windows_completed': 0,
                'windows_failed': 0
            }
        }
        
        for window_index, days_back in enumerate(time_windows, 1):
            window_name = f"window_{window_index}_{days_back}d"
            
            print(f"\n📅 WINDOW {window_index}/{len(time_windows)}: {days_back} DAYS LOOKBACK")
            print(f"🎯 Starting collection for {days_back}-day window...")
            
            window_start_time = datetime.now()
            
            try:
                # Collect from employee list for this time window
                window_results = self.collect_from_employee_list(employee_emails, days_back)
                
                # Calculate window statistics
                window_summary = window_results.get('bulk_collection_summary', {})
                window_end_time = datetime.now()
                window_duration = (window_end_time - window_start_time).total_seconds() / 60
                
                # Store results for this window
                all_results['window_results'][window_name] = {
                    'window_info': {
                        'days_back': days_back,
                        'window_number': window_index,
                        'start_time': window_start_time.isoformat(),
                        'end_time': window_end_time.isoformat(),
                        'duration_minutes': round(window_duration, 1)
                    },
                    'collection_results': window_results
                }
                
                # Update aggregated statistics
                all_results['aggregated_stats']['total_successful_collections'] += window_summary.get('successful_collections', 0)
                all_results['aggregated_stats']['total_failed_collections'] += window_summary.get('failed_collections', 0)
                all_results['aggregated_stats']['total_events_collected'] += window_summary.get('total_events_collected', 0)
                all_results['aggregated_stats']['windows_completed'] += 1
                
                print(f"✅ Window {window_index} completed successfully")
                print(f"  📊 Duration: {window_duration:.1f} minutes")
                print(f"  📅 Events collected: {window_summary.get('total_events_collected', 0)}")
                print(f"  🎯 Success rate: {window_summary.get('success_rate', 0):.1f}%")
                
                # Save data for this window if configured
                if self.config.get('progressive_collection', {}).get('save_each_window', True):
                    window_data_path = self.data_path / f"time_window_{days_back}d"
                    window_data_path.mkdir(exist_ok=True)
                    
                    window_file = window_data_path / f"collection_results_{days_back}d.json"
                    with open(window_file, 'w') as f:
                        json.dump(window_results, f, indent=2)
                    
                    print(f"  💾 Window data saved to: {window_file}")
                
            except Exception as e:
                print(f"❌ Window {window_index} failed: {e}")
                
                # Record failure
                all_results['window_results'][window_name] = {
                    'window_info': {
                        'days_back': days_back,
                        'window_number': window_index,
                        'start_time': window_start_time.isoformat(),
                        'error': str(e),
                        'status': 'failed'
                    },
                    'collection_results': None
                }
                
                all_results['aggregated_stats']['windows_failed'] += 1
                
                # Check if we should continue
                if not self.config.get('progressive_collection', {}).get('continue_on_window_failure', True):
                    print(f"🛑 Stopping progressive collection due to window failure")
                    break
                else:
                    print(f"⚠️ Continuing to next window despite failure")
            
            # Rate limiting delay between windows (except for last window)
            if window_index < len(time_windows):
                print(f"⏳ Waiting {time_window_delay}s before next time window...")
                time.sleep(time_window_delay)
        
        # Final summary
        collection_end_time = datetime.now()
        total_duration = (collection_end_time - datetime.fromisoformat(all_results['progressive_summary']['collection_start'])).total_seconds() / 60
        
        all_results['progressive_summary']['collection_end'] = collection_end_time.isoformat()
        all_results['progressive_summary']['total_duration_minutes'] = round(total_duration, 1)
        
        print(f"\n🎉 PROGRESSIVE COLLECTION COMPLETE!")
        print(f"⏱️ Total duration: {total_duration:.1f} minutes")
        print(f"📊 Windows completed: {all_results['aggregated_stats']['windows_completed']}/{len(time_windows)}")
        print(f"❌ Windows failed: {all_results['aggregated_stats']['windows_failed']}")
        print(f"📅 Total events collected: {all_results['aggregated_stats']['total_events_collected']}")
        print(f"🎯 Overall collections: {all_results['aggregated_stats']['total_successful_collections']} successful")
        
        # Save complete progressive results
        progressive_results_file = self.data_path / "progressive_collection_complete.json"
        with open(progressive_results_file, 'w') as f:
            json.dump(all_results, f, indent=2)
        
        print(f"💾 Complete results saved to: {progressive_results_file}")
        
        return all_results

    def to_json(self) -> str:
        """Output collection results as JSON string"""
        return json.dumps(self.collection_results, indent=2)
    
    def collect_all_calendar_data(self, force_refresh: bool = False, max_calendars: int = 50) -> Dict:
        """Collect comprehensive calendar data using dynamic discovery"""
        
        if not self.setup_calendar_service():
            self.collection_results["status"] = "error"
            return {'error': 'Failed to setup Google Calendar service'}
        
        print(f"\n🚀 STARTING DYNAMIC CALENDAR COLLECTION")
        collection_start = datetime.now()
        
        try:
            # 1. Discover all calendars
            all_calendars = self.discover_all_calendars()
            
            # 2. Apply collection rules to filter calendars
            filtered_calendars = self.apply_collection_rules(all_calendars)
            
            # 3. Collect from filtered calendars
            calendar_results = self.collect_from_filtered_calendars(filtered_calendars, max_calendars)
            
            # 4. Discover users from collected calendar data
            all_users = self.discover_calendar_users(calendar_results["collected_data"])
            
            collection_end = datetime.now()
            duration = (collection_end - collection_start).total_seconds() / 60
            
            # Update collection results
            self.collection_results.update({
                "status": "success",
                "collected": {
                    "calendars": calendar_results["successful_collections"],
                    "events": calendar_results["total_events_collected"]
                },
                "next_cursor": collection_end.timestamp()
            })
            
            # Save collected data
            self._save_calendar_data(calendar_results["collected_data"], all_users)
            
            final_results = {
                'collection_summary': {
                    'start_time': collection_start.isoformat(),
                    'end_time': collection_end.isoformat(),
                    'duration_minutes': round(duration, 1),
                    'total_calendars_discovered': len(all_calendars),
                    'total_calendars_collected': calendar_results["successful_collections"],
                    'total_events': calendar_results["total_events_collected"],
                    'total_users_discovered': len(all_users),
                    'total_requests': self.rate_limiter.request_count
                },
                'calendar_results': calendar_results,
                'data_path': str(self.data_path)
            }
            
            print(f"\n🎉 CALENDAR COLLECTION COMPLETE!")
            print(f"⏱️  Duration: {duration:.1f} minutes")
            print(f"📋 Calendars: {calendar_results['successful_collections']} collected")
            print(f"📅 Events: {calendar_results['total_events_collected']} collected")
            print(f"👥 Users: {len(all_users)} discovered")
            print(f"📈 Total requests: {self.rate_limiter.request_count}")
            print(f"💾 Stored: {self.data_path}")
            
            return final_results
            
        except Exception as e:
            self.collection_results["status"] = "error"
            print(f"❌ Collection failed: {e}")
            return {'error': str(e)}

def main():
    """Test calendar collector"""
    from pathlib import Path
    
    # Initialize calendar collector
    collector = CalendarCollector()
    
    # Run collection
    results = collector.collect_all_calendar_data(force_refresh=True, max_calendars=20)
    
    print(f"\n📊 Final Results:")
    print(json.dumps(results, indent=2))
    
    print(f"\n📊 Collection JSON:")
    print(collector.to_json())
    
    return results

if __name__ == "__main__":
    main()