#!/usr/bin/env python3
"""
Employee Collector - Dynamic multi-source roster building
Discovers employees from Slack, Calendar, and Drive APIs with unified output
"""

import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
import requests

# Add auth system to path
sys.path.insert(0, str(Path(__file__).parent.parent / "core"))
from auth_manager import credential_vault
class EmployeeRateLimiter:
    """Rate limiting for employee discovery across multiple APIs"""
    
    def __init__(self, requests_per_second: float = 5):
        self.requests_per_second = requests_per_second
        self.last_request_time = 0
        self.request_count = 0
        
    def wait_for_rate_limit(self):
        """Wait appropriate time for rate limiting"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        min_interval = 1.0 / self.requests_per_second
        
        if time_since_last < min_interval:
            wait_time = min_interval - time_since_last
            time.sleep(wait_time)
        
        self.last_request_time = time.time()
        self.request_count += 1

class EmployeeCollector:
    """
    Dynamic multi-source employee roster builder
    Discovers employees from Slack, Calendar, and Drive with conflict resolution
    """
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or Path(__file__).parent.parent.parent / "config"
        self.data_path = Path(__file__).parent.parent.parent / "data"
        self.raw_data_path = self.data_path / "raw" / "employees"
        self.processed_data_path = self.data_path / "processed"
        
        # Create directories
        self.raw_data_path.mkdir(parents=True, exist_ok=True)
        self.processed_data_path.mkdir(parents=True, exist_ok=True)
        
        # Rate limiter
        self.rate_limiter = EmployeeRateLimiter()
        
        # Track collection stats
        self.stats = {
            "slack_users": 0,
            "calendar_users": 0, 
            "drive_users": 0,
            "unified_employees": 0,
            "new_employees": [],
            "removed_employees": [],
            "updated_profiles": 0
        }
        
        # Load previous roster for change detection
        self.previous_roster = self._load_previous_roster()
        
        print(f"👥 EMPLOYEE COLLECTOR - Multi-Source Roster Building")
        print(f"📁 Raw data: {self.raw_data_path}")
        print(f"📊 Processed data: {self.processed_data_path}")
        print("=" * 60)
    def _load_previous_roster(self) -> Dict:
        """Load previous roster for change detection"""
        roster_file = self.processed_data_path / "roster.json"
        if roster_file.exists():
            try:
                with open(roster_file, 'r') as f:
                    data = json.load(f)
                    return data.get('roster_data', {}).get('employees', {})
            except Exception as e:
                print(f"⚠️ Could not load previous roster: {e}")
        return {}
    
    def _log_operation(self, operation: str, details: Dict):
        """Log operations for audit trail"""
        timestamp = datetime.now().isoformat()
        log_entry = {
            "timestamp": timestamp,
            "operation": operation,
            "details": details
        }
        
        log_file = self.data_path / "logs" / "employee_collector.jsonl"
        log_file.parent.mkdir(exist_ok=True)
        
        with open(log_file, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
    
    def build_roster_from_slack(self) -> Dict[str, Dict]:
        """Build employee roster from Slack users"""
        print(f"\n🔍 DISCOVERING EMPLOYEES FROM SLACK")
        print("-" * 40)
        
        slack_employees = {}
        
        try:
            # Get Slack credentials
            slack_creds = credential_vault.get_slack_bot_credentials()
            if not slack_creds or not slack_creds.is_valid():
                print(f"❌ Invalid Slack credentials")
                return slack_employees
            
            headers = {"Authorization": f"Bearer {slack_creds.token}"}
            
            self.rate_limiter.wait_for_rate_limit()
            
            # Get all users
            response = requests.get(
                "https://slack.com/api/users.list",
                headers=headers,
                params={"limit": 1000}
            )
            
            if response.status_code != 200:
                print(f"❌ Slack API HTTP error: {response.status_code}")
                return slack_employees
            
            result = response.json()
            if not result.get('ok'):
                print(f"❌ Slack API error: {result.get('error')}")
                return slack_employees
            
            users = result.get('members', [])
            print(f"✅ Found {len(users)} Slack users")
            
            # Process users
            for user in users:
                if user.get('deleted') or user.get('is_bot'):
                    continue
                
                profile = user.get('profile', {})
                email = profile.get('email', '')
                
                if email:  # Only include users with email addresses
                    slack_employees[email] = {
                        "email": email,
                        "slack_id": user.get('id'),
                        "slack_name": user.get('real_name') or user.get('name', ''),
                        "slack_display_name": profile.get('display_name', ''),
                        "slack_title": profile.get('title', ''),
                        "sources": ["slack"],
                        "last_seen": datetime.now().isoformat()
                    }
            
            self.stats["slack_users"] = len(slack_employees)
            print(f"📧 Users with emails: {len(slack_employees)}")
            
            # Save raw Slack data
            slack_raw_file = self.raw_data_path / f"slack_users_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(slack_raw_file, 'w') as f:
                json.dump({"users": users, "processed_count": len(slack_employees)}, f, indent=2)
            
            self._log_operation("slack_discovery", {
                "total_users": len(users),
                "users_with_email": len(slack_employees),
                "raw_file": str(slack_raw_file)
            })
            
        except Exception as e:
            print(f"❌ Slack roster building error: {e}")
            self._log_operation("slack_discovery_error", {"error": str(e)})
        
        return slack_employees
    def build_roster_from_calendar(self) -> Dict[str, Dict]:
        """Build employee roster from Google Calendar attendees"""
        print(f"\n📅 DISCOVERING EMPLOYEES FROM CALENDAR")
        print("-" * 42)
        
        calendar_employees = {}
        
        try:
            # Get Google Calendar credentials
            google_creds = credential_vault.get_google_credentials()
            if not google_creds or not google_creds.is_valid():
                print(f"❌ Invalid Google credentials")
                return calendar_employees
            
            headers = {"Authorization": f"Bearer {google_creds.token}"}
            
            # Get calendar list
            self.rate_limiter.wait_for_rate_limit()
            response = requests.get(
                "https://www.googleapis.com/calendar/v3/users/me/calendarList",
                headers=headers
            )
            
            if response.status_code != 200:
                print(f"❌ Calendar API HTTP error: {response.status_code}")
                return calendar_employees
            
            calendar_list = response.json()
            calendars = calendar_list.get('items', [])
            print(f"✅ Found {len(calendars)} calendars")
            
            # Look at recent events to find attendees
            end_time = datetime.now()
            start_time = end_time - timedelta(days=30)  # Last 30 days
            
            unique_attendees = set()
            
            for calendar in calendars[:5]:  # Limit to first 5 calendars
                calendar_id = calendar.get('id')
                
                self.rate_limiter.wait_for_rate_limit()
                
                events_response = requests.get(
                    f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events",
                    headers=headers,
                    params={
                        'timeMin': start_time.isoformat() + 'Z',
                        'timeMax': end_time.isoformat() + 'Z',
                        'maxResults': 100
                    }
                )
                
                if events_response.status_code == 200:
                    events_data = events_response.json()
                    events = events_data.get('items', [])
                    
                    for event in events:
                        attendees = event.get('attendees', [])
                        for attendee in attendees:
                            email = attendee.get('email', '')
                            if email and '@' in email:
                                unique_attendees.add(email)
            
            # Process unique attendees
            for email in unique_attendees:
                calendar_employees[email] = {
                    "email": email,
                    "calendar_id": email,  # Typically the same
                    "sources": ["calendar"],
                    "last_seen": datetime.now().isoformat()
                }
            
            self.stats["calendar_users"] = len(calendar_employees)
            print(f"📧 Unique attendees found: {len(calendar_employees)}")
            
            # Save raw calendar data
            calendar_raw_file = self.raw_data_path / f"calendar_attendees_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(calendar_raw_file, 'w') as f:
                json.dump({"attendees": list(unique_attendees), "processed_count": len(calendar_employees)}, f, indent=2)
            
            self._log_operation("calendar_discovery", {
                "calendars_checked": len(calendars[:5]),
                "unique_attendees": len(calendar_employees),
                "raw_file": str(calendar_raw_file)
            })
            
        except Exception as e:
            print(f"❌ Calendar roster building error: {e}")
            self._log_operation("calendar_discovery_error", {"error": str(e)})
        
        return calendar_employees
    def build_roster_from_drive(self) -> Dict[str, Dict]:
        """Build employee roster from Google Drive collaborators"""
        print(f"\n📁 DISCOVERING EMPLOYEES FROM DRIVE")
        print("-" * 40)
        
        drive_employees = {}
        
        try:
            # Get Google Drive credentials
            google_creds = credential_vault.get_google_credentials()
            if not google_creds or not google_creds.is_valid():
                print(f"❌ Invalid Google credentials for Drive")
                return drive_employees
            
            headers = {"Authorization": f"Bearer {google_creds.token}"}
            
            # Get recent files to find collaborators
            self.rate_limiter.wait_for_rate_limit()
            
            response = requests.get(
                "https://www.googleapis.com/drive/v3/files",
                headers=headers,
                params={
                    'q': "trashed=false and (mimeType='application/vnd.google-apps.document' or mimeType='application/vnd.google-apps.spreadsheet' or mimeType='application/vnd.google-apps.presentation')",
                    'pageSize': 50,
                    'fields': 'files(id,name,owners,permissions)'
                }
            )
            
            if response.status_code != 200:
                print(f"❌ Drive API HTTP error: {response.status_code}")
                return drive_employees
            
            files_data = response.json()
            files = files_data.get('files', [])
            print(f"✅ Found {len(files)} Drive files")
            
            unique_collaborators = set()
            
            for file_item in files:
                # Get owners
                owners = file_item.get('owners', [])
                for owner in owners:
                    email = owner.get('emailAddress')
                    if email:
                        unique_collaborators.add(email)
                
                # Get permissions (shared with users)
                permissions = file_item.get('permissions', [])
                for permission in permissions:
                    email = permission.get('emailAddress')
                    if email:
                        unique_collaborators.add(email)
            
            # Process unique collaborators
            for email in unique_collaborators:
                if '@' in email:  # Basic email validation
                    drive_employees[email] = {
                        "email": email,
                        "has_drive_access": True,
                        "sources": ["drive"],
                        "last_seen": datetime.now().isoformat()
                    }
            
            self.stats["drive_users"] = len(drive_employees)
            print(f"📧 Unique collaborators found: {len(drive_employees)}")
            
            # Save raw drive data
            drive_raw_file = self.raw_data_path / f"drive_collaborators_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(drive_raw_file, 'w') as f:
                json.dump({"collaborators": list(unique_collaborators), "processed_count": len(drive_employees)}, f, indent=2)
            
            self._log_operation("drive_discovery", {
                "files_checked": len(files),
                "unique_collaborators": len(drive_employees),
                "raw_file": str(drive_raw_file)
            })
            
        except Exception as e:
            print(f"❌ Drive roster building error: {e}")
            self._log_operation("drive_discovery_error", {"error": str(e)})
        
        return drive_employees
    
    def merge_multi_source_roster(self, slack_users: Dict, calendar_users: Dict, drive_users: Dict) -> Dict[str, Dict]:
        """Merge employees from multiple sources with conflict resolution"""
        print(f"\n🔄 MERGING MULTI-SOURCE ROSTER DATA")
        print("-" * 38)
        
        unified_roster = {}
        
        # Start with Slack users (most complete data)
        for email, data in slack_users.items():
            unified_roster[email] = data.copy()
        
        # Merge Calendar users
        for email, data in calendar_users.items():
            if email in unified_roster:
                # Add calendar info to existing user
                unified_roster[email]["calendar_id"] = data["calendar_id"]
                if "calendar" not in unified_roster[email]["sources"]:
                    unified_roster[email]["sources"].append("calendar")
            else:
                # New user from calendar
                unified_roster[email] = data.copy()
        
        # Merge Drive users
        for email, data in drive_users.items():
            if email in unified_roster:
                # Add drive info to existing user
                unified_roster[email]["has_drive_access"] = True
                if "drive" not in unified_roster[email]["sources"]:
                    unified_roster[email]["sources"].append("drive")
            else:
                # New user from drive
                unified_roster[email] = data.copy()
        
        self.stats["unified_employees"] = len(unified_roster)
        
        print(f"✅ Unified roster: {len(unified_roster)} employees")
        print(f"  🔵 Slack only: {len([u for u in unified_roster.values() if u['sources'] == ['slack']])}")
        print(f"  📝 Calendar only: {len([u for u in unified_roster.values() if u['sources'] == ['calendar']])}")
        print(f"  📁 Drive only: {len([u for u in unified_roster.values() if u['sources'] == ['drive']])}")
        print(f"  🌈 Multi-source: {len([u for u in unified_roster.values() if len(u['sources']) > 1])}")
        
        return unified_roster
    
    def detect_roster_changes(self, current_roster: Dict[str, Dict]) -> Tuple[List[str], List[str], int]:
        """Detect changes since last roster update"""
        print(f"\n🔍 DETECTING ROSTER CHANGES")
        print("-" * 28)
        
        previous_emails = set(self.previous_roster.keys())
        current_emails = set(current_roster.keys())
        
        new_employees = list(current_emails - previous_emails)
        removed_employees = list(previous_emails - current_emails)
        
        # Detect profile updates
        updated_profiles = 0
        for email in current_emails.intersection(previous_emails):
            current_sources = set(current_roster[email].get('sources', []))
            previous_sources = set(self.previous_roster[email].get('sources', []))
            if current_sources != previous_sources:
                updated_profiles += 1
        
        self.stats["new_employees"] = new_employees
        self.stats["removed_employees"] = removed_employees
        self.stats["updated_profiles"] = updated_profiles
        
        print(f"➕ New employees: {len(new_employees)}")
        print(f"➖ Removed employees: {len(removed_employees)}")
        print(f"🔄 Updated profiles: {updated_profiles}")
        
        if new_employees:
            print(f"  New: {', '.join(new_employees[:5])}{'...' if len(new_employees) > 5 else ''}")
        if removed_employees:
            print(f"  Removed: {', '.join(removed_employees[:3])}{'...' if len(removed_employees) > 3 else ''}")
        
        return new_employees, removed_employees, updated_profiles
    
    def to_json(self) -> Dict:
        """Generate unified JSON output for tool pattern"""
        # Build roster from all sources
        slack_users = self.build_roster_from_slack()
        calendar_users = self.build_roster_from_calendar() 
        drive_users = self.build_roster_from_drive()
        
        # Merge with conflict resolution
        unified_roster = self.merge_multi_source_roster(slack_users, calendar_users, drive_users)
        
        # Detect changes
        new_employees, removed_employees, updated_profiles = self.detect_roster_changes(unified_roster)
        
        # Save processed roster
        roster_file = self.processed_data_path / "roster.json"
        roster_data = {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "discovered": {
                "slack_users": self.stats["slack_users"],
                "calendar_users": self.stats["calendar_users"],
                "drive_users": self.stats["drive_users"],
                "unified_employees": self.stats["unified_employees"]
            },
            "changes": {
                "new_employees": new_employees,
                "removed_employees": removed_employees,
                "updated_profiles": updated_profiles
            },
            "data_path": str(roster_file),
            "roster_data": {
                "employees": unified_roster
            }
        }
        
        with open(roster_file, 'w') as f:
            json.dump(roster_data, f, indent=2)
        
        print(f"\n✅ ROSTER COLLECTION COMPLETE")
        print(f"📄 Saved to: {roster_file}")
        
        self._log_operation("roster_complete", {
            "total_employees": len(unified_roster),
            "new_employees": len(new_employees),
            "removed_employees": len(removed_employees),
            "output_file": str(roster_file)
        })
        
        return roster_data

def main():
    """CLI entry point for employee roster building"""
    collector = EmployeeCollector()
    result = collector.to_json()
    
    # Print summary
    print(f"\n📊 SUMMARY:")
    print(f"  ✅ Total employees: {result['discovered']['unified_employees']}")
    print(f"  🔵 From Slack: {result['discovered']['slack_users']}")
    print(f"  📝 From Calendar: {result['discovered']['calendar_users']}")
    print(f"  📁 From Drive: {result['discovered']['drive_users']}")
    print(f"  ➕ New: {len(result['changes']['new_employees'])}")
    print(f"  ➖ Removed: {len(result['changes']['removed_employees'])}")
    
    return result

if __name__ == "__main__":
    main()