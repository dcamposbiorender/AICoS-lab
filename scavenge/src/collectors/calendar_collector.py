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

# Add auth system to path
sys.path.insert(0, str(Path(__file__).parent.parent / "core"))
from auth_manager import credential_vault

class CalendarRateLimiter:
    """Rate limiting with exponential backoff for bulk calendar collection"""
    
    def __init__(self, base_delay: float = 3.0, jitter_seconds: float = 2):
        # Conservative settings for bulk collection
        self.base_delay = base_delay  # 3 seconds base delay for bulk collection
        self.jitter_seconds = jitter_seconds
        self.last_request_time = 0
        self.request_count = 0
        
        # Exponential backoff state for rate limiting
        self.consecutive_rate_limits = 0
        self.current_backoff_delay = 0
        self.backoff_levels = [60, 300, 600]  # 1min, 5min, 10min
        
    def wait_for_rate_limit(self):
        """Wait with exponential backoff and jitter for bulk collection"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
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
            "backoff_multiplier": 2.0
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
    
    def _save_calendar_data(self, calendar_data: Dict, user_data: Dict):
        """Save calendar data to dated directory structure"""
        
        # Save calendar data
        calendars_file = self.data_path / "calendars.json"
        with open(calendars_file, 'w') as f:
            json.dump(calendar_data, f, indent=2)
        
        # Save user data
        users_file = self.data_path / "users.json"
        with open(users_file, 'w') as f:
            json.dump(user_data, f, indent=2)
        
        # Save events as JSONL
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