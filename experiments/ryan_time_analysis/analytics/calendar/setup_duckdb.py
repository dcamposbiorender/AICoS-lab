#!/usr/bin/env python3
"""
Calendar Analytics - DuckDB Setup and Data Transformation
==========================================================

This script transforms Ryan's 6-month calendar data (2,358 events) from JSONL format
into a normalized DuckDB schema following the CoS Analytics framework.

The transformation creates three main tables:
- events: Core calendar events with normalized timestamps
- participants: Attendee data extracted from nested arrays
- org: Inferred organization structure from email domains

Data Source: /experiments/ryan_time_analysis/data/raw/calendar_full_6months/ryan_calendar_6months.jsonl
Output: /experiments/ryan_time_analysis/data/processed/duckdb/calendar_analytics.db
"""

import json
import duckdb
import pandas as pd
from datetime import datetime, timezone
import re
from typing import Dict, List, Any, Tuple
import hashlib
import os

class CalendarDuckDBTransformer:
    def __init__(self, data_path: str, output_db_path: str):
        """Initialize the transformer with input and output paths."""
        self.data_path = data_path
        self.output_db_path = output_db_path
        self.connection = None
        self.events_data = []
        self.participants_data = []
        self.org_data = []
        
    def connect_db(self):
        """Create and connect to DuckDB database."""
        os.makedirs(os.path.dirname(self.output_db_path), exist_ok=True)
        self.connection = duckdb.connect(self.output_db_path)
        print(f"Connected to DuckDB at: {self.output_db_path}")
        
    def load_calendar_data(self) -> List[Dict[str, Any]]:
        """Load calendar events from JSONL file."""
        events = []
        with open(self.data_path, 'r') as file:
            for line_num, line in enumerate(file, 1):
                try:
                    event = json.loads(line.strip())
                    events.append(event)
                except json.JSONDecodeError as e:
                    print(f"Error parsing line {line_num}: {e}")
                    continue
        print(f"Loaded {len(events)} calendar events")
        return events
        
    def parse_datetime(self, dt_obj: Dict[str, str]) -> Tuple[datetime, str]:
        """Parse Google Calendar datetime object into UTC datetime and timezone."""
        if 'dateTime' in dt_obj:
            # Parse with timezone
            dt_str = dt_obj['dateTime']
            # Handle various timezone formats
            try:
                dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
                tz = dt_obj.get('timeZone', 'UTC')
                return dt, tz
            except ValueError:
                # Fallback parsing
                dt = datetime.fromisoformat(dt_str)
                tz = dt_obj.get('timeZone', 'UTC')
                return dt, tz
        elif 'date' in dt_obj:
            # All-day event
            dt = datetime.fromisoformat(dt_obj['date'])
            return dt, dt_obj.get('timeZone', 'UTC')
        else:
            raise ValueError(f"Cannot parse datetime object: {dt_obj}")
            
    def extract_email_domain(self, email: str) -> str:
        """Extract domain from email address."""
        if '@' in email:
            return email.split('@')[1].lower()
        return 'unknown'
        
    def generate_series_id(self, event: Dict[str, Any]) -> str:
        """Generate consistent series ID for recurring events."""
        if event.get('recurring_event_id'):
            # Use recurring_event_id without instance suffix
            base_id = event['recurring_event_id']
            # Remove instance-specific suffix if present
            if '_' in base_id:
                parts = base_id.split('_')
                if len(parts) > 1 and parts[-1].startswith('R'):
                    return '_'.join(parts[:-1])
            return base_id
        else:
            # For non-recurring events, use event ID as series ID
            return event['id']
            
    def categorize_meeting_type(self, event: Dict[str, Any]) -> str:
        """Categorize meeting type based on summary and attendees."""
        summary = event.get('summary', '').lower()
        attendee_count = event.get('attendee_count', 0)
        
        # Personal/blocked time patterns
        personal_patterns = [
            'lunch', 'workout', 'heads down', 'hard work', 'travel', 'dinner',
            'personal', 'break', 'block', 'focus'
        ]
        
        if any(pattern in summary for pattern in personal_patterns):
            return 'personal'
        elif attendee_count == 0:
            return 'blocked_time'
        elif '1:1' in summary or 'one-on-one' in summary:
            return 'one_on_one'
        elif attendee_count >= 5:
            return 'large_meeting'
        elif attendee_count >= 2:
            return 'small_meeting'
        else:
            return 'other'
            
    def transform_events_data(self, events: List[Dict[str, Any]]):
        """Transform events into normalized schema."""
        for event in events:
            try:
                # Parse timestamps
                start_dt, start_tz = self.parse_datetime(event['start'])
                end_dt, end_tz = self.parse_datetime(event['end'])
                created_dt = datetime.fromisoformat(event['created'].replace('Z', '+00:00'))
                updated_dt = datetime.fromisoformat(event['updated'].replace('Z', '+00:00'))
                
                # Generate series ID
                series_id = self.generate_series_id(event)
                
                # Categorize meeting
                meeting_type = self.categorize_meeting_type(event)
                
                # Extract organizer info
                organizer = event.get('organizer', {})
                organizer_email = organizer.get('email', 'unknown')
                organizer_domain = self.extract_email_domain(organizer_email)
                
                # Build normalized event record
                event_record = {
                    'event_id': event['id'],
                    'series_id': series_id,
                    'calendar_id': event.get('calendar_id', ''),
                    'summary': event.get('summary', ''),
                    'description': event.get('description', ''),
                    'start_time': start_dt,
                    'end_time': end_dt,
                    'start_tz': start_tz,
                    'end_tz': end_tz,
                    'duration_minutes': event.get('meeting_duration_minutes', 0),
                    'is_all_day': event.get('is_all_day', False),
                    'status': event.get('status', 'confirmed'),
                    'visibility': event.get('visibility', 'default'),
                    'location': event.get('location', ''),
                    'organizer_email': organizer_email,
                    'organizer_domain': organizer_domain,
                    'organizer_self': organizer.get('self', False),
                    'attendee_count': event.get('attendee_count', 0),
                    'has_external_attendees': event.get('has_external_attendees', False),
                    'meeting_type': meeting_type,
                    'is_recurring': event.get('recurring_event_id') is not None,
                    'created_time': created_dt,
                    'updated_time': updated_dt,
                    'processed_at': datetime.fromisoformat(event['processed_at']),
                    'etag': event.get('etag', '')
                }
                
                self.events_data.append(event_record)
                
                # Process attendees
                attendees = event.get('attendees', [])
                for idx, attendee in enumerate(attendees):
                    attendee_record = {
                        'event_id': event['id'],
                        'attendee_index': idx,
                        'email': attendee.get('email', ''),
                        'display_name': attendee.get('displayName', ''),
                        'response_status': attendee.get('responseStatus', 'needsAction'),
                        'organizer': attendee.get('organizer', False),
                        'self': attendee.get('self', False),
                        'domain': self.extract_email_domain(attendee.get('email', ''))
                    }
                    self.participants_data.append(attendee_record)
                    
            except Exception as e:
                print(f"Error processing event {event.get('id', 'unknown')}: {e}")
                continue
                
    def build_org_data(self):
        """Build organization structure from email domains."""
        domain_stats = {}
        
        # Count emails by domain from events
        for event in self.events_data:
            domain = event['organizer_domain']
            if domain != 'unknown':
                if domain not in domain_stats:
                    domain_stats[domain] = {
                        'domain': domain,
                        'organizer_count': 0,
                        'participant_count': 0,
                        'is_internal': domain == 'biorender.com'
                    }
                domain_stats[domain]['organizer_count'] += 1
                
        # Count from participants
        for participant in self.participants_data:
            domain = participant['domain']
            if domain != 'unknown':
                if domain not in domain_stats:
                    domain_stats[domain] = {
                        'domain': domain,
                        'organizer_count': 0,
                        'participant_count': 0,
                        'is_internal': domain == 'biorender.com'
                    }
                domain_stats[domain]['participant_count'] += 1
                
        self.org_data = list(domain_stats.values())
        
    def create_tables(self):
        """Create DuckDB tables with proper schema."""
        
        # Events table
        self.connection.execute("""
            CREATE TABLE IF NOT EXISTS events (
                event_id VARCHAR PRIMARY KEY,
                series_id VARCHAR,
                calendar_id VARCHAR,
                summary VARCHAR,
                description TEXT,
                start_time TIMESTAMPTZ,
                end_time TIMESTAMPTZ,
                start_tz VARCHAR,
                end_tz VARCHAR,
                duration_minutes INTEGER,
                is_all_day BOOLEAN,
                status VARCHAR,
                visibility VARCHAR,
                location VARCHAR,
                organizer_email VARCHAR,
                organizer_domain VARCHAR,
                organizer_self BOOLEAN,
                attendee_count INTEGER,
                has_external_attendees BOOLEAN,
                meeting_type VARCHAR,
                is_recurring BOOLEAN,
                created_time TIMESTAMPTZ,
                updated_time TIMESTAMPTZ,
                processed_at TIMESTAMPTZ,
                etag VARCHAR
            )
        """)
        
        # Participants table
        self.connection.execute("""
            CREATE TABLE IF NOT EXISTS participants (
                event_id VARCHAR,
                attendee_index INTEGER,
                email VARCHAR,
                display_name VARCHAR,
                response_status VARCHAR,
                organizer BOOLEAN,
                self BOOLEAN,
                domain VARCHAR,
                PRIMARY KEY (event_id, attendee_index)
            )
        """)
        
        # Organization table
        self.connection.execute("""
            CREATE TABLE IF NOT EXISTS org (
                domain VARCHAR PRIMARY KEY,
                organizer_count INTEGER,
                participant_count INTEGER,
                is_internal BOOLEAN
            )
        """)
        
        print("Created DuckDB tables: events, participants, org")
        
    def insert_data(self):
        """Insert transformed data into DuckDB tables."""
        
        # Insert events
        if self.events_data:
            events_df = pd.DataFrame(self.events_data)
            self.connection.execute("DELETE FROM events")
            self.connection.register('events_df', events_df)
            self.connection.execute("INSERT INTO events SELECT * FROM events_df")
            print(f"Inserted {len(self.events_data)} events")
            
        # Insert participants
        if self.participants_data:
            participants_df = pd.DataFrame(self.participants_data)
            self.connection.execute("DELETE FROM participants")
            self.connection.register('participants_df', participants_df)
            self.connection.execute("INSERT INTO participants SELECT * FROM participants_df")
            print(f"Inserted {len(self.participants_data)} participant records")
            
        # Insert org data
        if self.org_data:
            org_df = pd.DataFrame(self.org_data)
            self.connection.execute("DELETE FROM org")
            self.connection.register('org_df', org_df)
            self.connection.execute("INSERT INTO org SELECT * FROM org_df")
            print(f"Inserted {len(self.org_data)} organization domains")
            
    def validate_data(self):
        """Validate the transformed data."""
        # Check event count
        event_count = self.connection.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        print(f"Total events in database: {event_count}")
        
        # Check date range
        date_range = self.connection.execute("""
            SELECT 
                MIN(start_time) as earliest,
                MAX(start_time) as latest
            FROM events
        """).fetchone()
        print(f"Date range: {date_range[0]} to {date_range[1]}")
        
        # Check meeting types
        meeting_types = self.connection.execute("""
            SELECT meeting_type, COUNT(*) as count
            FROM events 
            GROUP BY meeting_type 
            ORDER BY count DESC
        """).fetchall()
        print("Meeting types distribution:")
        for mt, count in meeting_types:
            print(f"  {mt}: {count}")
            
        # Check domains
        domains = self.connection.execute("""
            SELECT domain, organizer_count + participant_count as total
            FROM org 
            ORDER BY total DESC
            LIMIT 10
        """).fetchall()
        print("Top domains by activity:")
        for domain, total in domains:
            print(f"  {domain}: {total}")
            
    def run_transformation(self):
        """Run the complete transformation process."""
        print("Starting Calendar DuckDB Transformation")
        print("=" * 50)
        
        # Step 1: Connect to database
        self.connect_db()
        
        # Step 2: Load calendar data
        events = self.load_calendar_data()
        
        # Step 3: Transform data
        print("Transforming events data...")
        self.transform_events_data(events)
        
        print("Building organization data...")
        self.build_org_data()
        
        # Step 4: Create tables and insert data
        print("Creating database tables...")
        self.create_tables()
        
        print("Inserting data...")
        self.insert_data()
        
        # Step 5: Validate
        print("\nData validation:")
        self.validate_data()
        
        print("\nTransformation completed successfully!")
        print(f"Database saved at: {self.output_db_path}")
        
    def close(self):
        """Close database connection."""
        if self.connection:
            self.connection.close()

def main():
    """Main execution function."""
    
    # Define paths
    base_path = "/Users/david.campos/VibeCode/AICoS-Lab/experiments/ryan_time_analysis"
    data_path = f"{base_path}/data/raw/calendar_full_6months/ryan_calendar_6months.jsonl"
    output_db_path = f"{base_path}/data/processed/duckdb/calendar_analytics.db"
    
    # Run transformation
    transformer = CalendarDuckDBTransformer(data_path, output_db_path)
    
    try:
        transformer.run_transformation()
    finally:
        transformer.close()

if __name__ == "__main__":
    main()