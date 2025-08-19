#!/usr/bin/env python3
"""
Calendar Free Slot Finder CLI Tool
CRITICAL: Timezone-aware calendar coordination with interactive interface

References:
- src/calendar/availability.py - AvailabilityEngine implementation
- src/calendar/conflicts.py - ConflictDetector for validation
- tools/collect_data.py - CLI argument patterns
"""

import argparse
import json
import pytz
import sys
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.scheduling.availability import AvailabilityEngine, FreeSlot
from src.scheduling.conflicts import ConflictDetector
from src.collectors.calendar_collector import CalendarCollector


class CalendarCLI:
    """
    Interactive CLI for calendar coordination
    CRITICAL: All operations are timezone-aware
    """
    
    def __init__(self):
        self.availability_engine = AvailabilityEngine()
        self.conflict_detector = ConflictDetector()
        self.calendar_collector = None
        
    def load_calendar_data(self, data_path: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Load calendar data from collected JSONL files
        
        Args:
            data_path: Path to calendar data directory
            
        Returns:
            List of calendar events
        """
        if data_path:
            calendar_dir = Path(data_path)
        else:
            # Use default data directory
            calendar_dir = project_root / "data" / "raw" / "calendar"
        
        events = []
        
        try:
            # Find most recent calendar data
            if calendar_dir.exists():
                date_dirs = [d for d in calendar_dir.iterdir() if d.is_dir()]
                if date_dirs:
                    latest_dir = max(date_dirs, key=lambda d: d.name)
                    
                    # Load events from JSONL files
                    for jsonl_file in latest_dir.glob("*.jsonl"):
                        try:
                            with open(jsonl_file, 'r') as f:
                                for line in f:
                                    if line.strip():
                                        record = json.loads(line)
                                        event = record.get('event', {})
                                        if event:
                                            events.append(event)
                        except Exception as e:
                            print(f"Warning: Error reading {jsonl_file}: {e}")
                    
                    print(f"Loaded {len(events)} calendar events from {latest_dir}")
                else:
                    print("No calendar data found. Run 'python tools/collect_data.py --source=calendar' first.")
            else:
                print(f"Calendar data directory not found: {calendar_dir}")
                
        except Exception as e:
            print(f"Error loading calendar data: {e}")
        
        return events
    
    def find_free_slots(self, args) -> List[FreeSlot]:
        """
        Find free slots based on CLI arguments
        
        Args:
            args: Parsed command line arguments
            
        Returns:
            List of available time slots
        """
        # Load calendar events
        events = self.load_calendar_data(args.data_path)
        
        if not events:
            print("No calendar events found. Cannot determine availability.")
            return []
        
        # Parse target date
        try:
            target_date = datetime.strptime(args.date, '%Y-%m-%d').date()
        except ValueError:
            print(f"Invalid date format: {args.date}. Use YYYY-MM-DD")
            return []
        
        # Validate timezone
        try:
            pytz.timezone(args.timezone)
        except pytz.exceptions.UnknownTimeZoneError:
            print(f"Invalid timezone: {args.timezone}")
            return []
        
        # Group events by calendar (simulate multi-calendar scenario)
        calendars = [events]  # For now, treat all events as one calendar
        
        # Parse working hours
        try:
            start_hour, end_hour = map(int, args.working_hours.split('-'))
            working_hours = (start_hour, end_hour)
        except ValueError:
            print(f"Invalid working hours format: {args.working_hours}. Use HH-HH (e.g., 9-17)")
            return []
        
        # Find free slots
        try:
            free_slots = self.availability_engine.find_free_slots(
                calendars=calendars,
                duration_minutes=args.duration,
                working_hours=working_hours,
                date=target_date,
                timezone=args.timezone,
                buffer_minutes=args.buffer
            )
            
            print(f"\nFound {len(free_slots)} available time slots:")
            return free_slots
            
        except Exception as e:
            print(f"Error finding free slots: {e}")
            return []
    
    def check_conflicts(self, args) -> List[Dict[str, Any]]:
        """
        Check for scheduling conflicts in calendar events
        
        Args:
            args: Parsed command line arguments
            
        Returns:
            List of detected conflicts
        """
        events = self.load_calendar_data(args.data_path)
        
        if len(events) < 2:
            print("Need at least 2 events to detect conflicts.")
            return []
        
        try:
            conflicts = self.conflict_detector.detect_all_conflicts(
                events=events,
                timezone=args.timezone,
                include_resource_conflicts=True
            )
            
            print(f"\nDetected {len(conflicts)} scheduling conflicts:")
            return [conflict.to_dict() for conflict in conflicts]
            
        except Exception as e:
            print(f"Error detecting conflicts: {e}")
            return []
    
    def display_slots(self, slots: List[FreeSlot], format_type: str = "table"):
        """
        Display free slots in requested format
        
        Args:
            slots: List of free slots
            format_type: Output format ("table", "json", "summary")
        """
        if not slots:
            print("No available time slots found.")
            return
        
        if format_type == "json":
            # JSON output
            slots_data = [slot.to_dict() for slot in slots]
            print(json.dumps(slots_data, indent=2))
            
        elif format_type == "summary":
            # Summary output
            total_hours = sum(slot.duration_hours for slot in slots)
            print(f"\nSummary: {len(slots)} slots totaling {total_hours:.1f} hours available")
            
            for i, slot in enumerate(slots, 1):
                print(f"  {i}. {slot.start.strftime('%H:%M')}-{slot.end.strftime('%H:%M')} "
                      f"({slot.duration_hours:.1f}h)")
                      
        else:
            # Table output (default)
            print("\n" + "="*80)
            print(f"{'#':<3} {'Start Time':<12} {'End Time':<12} {'Duration':<10} {'Timezone':<15}")
            print("="*80)
            
            for i, slot in enumerate(slots, 1):
                print(f"{i:<3} {slot.start.strftime('%H:%M'):<12} "
                      f"{slot.end.strftime('%H:%M'):<12} "
                      f"{slot.duration_hours:.1f}h{'':<6} {slot.timezone:<15}")
            
            print("="*80)
            total_hours = sum(slot.duration_hours for slot in slots)
            print(f"Total available time: {total_hours:.1f} hours")
    
    def display_conflicts(self, conflicts: List[Dict[str, Any]], format_type: str = "table"):
        """
        Display conflicts in requested format
        
        Args:
            conflicts: List of conflict dictionaries
            format_type: Output format ("table", "json", "summary")
        """
        if not conflicts:
            print("No scheduling conflicts detected.")
            return
        
        if format_type == "json":
            print(json.dumps(conflicts, indent=2))
            
        elif format_type == "summary":
            high_severity = [c for c in conflicts if c['severity'] > 0.7]
            medium_severity = [c for c in conflicts if 0.3 <= c['severity'] <= 0.7]
            low_severity = [c for c in conflicts if c['severity'] < 0.3]
            
            print(f"\nConflict Summary:")
            print(f"  High severity: {len(high_severity)} conflicts")
            print(f"  Medium severity: {len(medium_severity)} conflicts")
            print(f"  Low severity: {len(low_severity)} conflicts")
            
        else:
            # Table output (default)
            print("\n" + "="*100)
            print(f"{'#':<3} {'Event 1':<25} {'Event 2':<25} {'Overlap':<8} {'Type':<15} {'Severity':<8}")
            print("="*100)
            
            for i, conflict in enumerate(conflicts, 1):
                event1_summary = conflict['event1_summary'][:24]
                event2_summary = conflict['event2_summary'][:24]
                overlap_mins = conflict['overlap_minutes']
                conflict_type = conflict['conflict_type'][:14]
                severity = f"{conflict['severity']:.2f}"
                
                print(f"{i:<3} {event1_summary:<25} {event2_summary:<25} "
                      f"{overlap_mins}m{'':<4} {conflict_type:<15} {severity:<8}")
            
            print("="*100)
    
    def interactive_mode(self):
        """Run interactive calendar coordination session"""
        print("\n" + "="*60)
        print("INTERACTIVE CALENDAR COORDINATION")
        print("="*60)
        
        # Get user preferences
        try:
            target_date_str = input("\nEnter target date (YYYY-MM-DD) [today]: ").strip()
            if not target_date_str:
                target_date = date.today()
            else:
                target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
            
            duration_str = input("Enter minimum duration in minutes [60]: ").strip()
            duration = int(duration_str) if duration_str else 60
            
            timezone_str = input("Enter timezone [UTC]: ").strip()
            timezone = timezone_str if timezone_str else 'UTC'
            
            working_hours_str = input("Enter working hours (HH-HH) [9-17]: ").strip()
            working_hours = working_hours_str if working_hours_str else '9-17'
            
            # Create mock args object
            class Args:
                def __init__(self):
                    self.date = target_date.strftime('%Y-%m-%d')
                    self.duration = duration
                    self.timezone = timezone
                    self.working_hours = working_hours
                    self.buffer = 15  # Default buffer
                    self.data_path = None
                    self.format = 'table'
            
            args = Args()
            
            # Find and display free slots
            print(f"\nSearching for {duration}-minute slots on {target_date} ({timezone})...")
            free_slots = self.find_free_slots(args)
            self.display_slots(free_slots, 'table')
            
            # Check for conflicts
            print(f"\nChecking for scheduling conflicts...")
            conflicts = self.check_conflicts(args)
            self.display_conflicts(conflicts, 'summary')
            
            # Offer to save results
            save_results = input("\nSave results to file? (y/N): ").strip().lower()
            if save_results == 'y':
                output_file = f"calendar_analysis_{target_date.strftime('%Y%m%d')}.json"
                results = {
                    'search_parameters': {
                        'date': target_date.strftime('%Y-%m-%d'),
                        'duration_minutes': duration,
                        'timezone': timezone,
                        'working_hours': working_hours
                    },
                    'free_slots': [slot.to_dict() for slot in free_slots],
                    'conflicts': conflicts,
                    'generated_at': datetime.now().isoformat()
                }
                
                with open(output_file, 'w') as f:
                    json.dump(results, f, indent=2)
                
                print(f"Results saved to {output_file}")
            
        except KeyboardInterrupt:
            print("\nInteractive session cancelled.")
        except Exception as e:
            print(f"Error in interactive mode: {e}")


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Find free time slots and detect calendar conflicts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Find 60-minute slots for today in Eastern timezone
  python tools/find_slots.py find --duration 60 --timezone "America/New_York"
  
  # Find slots for specific date with custom working hours
  python tools/find_slots.py find --date 2025-08-25 --working-hours 10-18
  
  # Check for scheduling conflicts
  python tools/find_slots.py conflicts --timezone "America/Los_Angeles"
  
  # Run interactive mode
  python tools/find_slots.py interactive
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Find slots command
    find_parser = subparsers.add_parser('find', help='Find free time slots')
    find_parser.add_argument('--date', 
                           default=date.today().strftime('%Y-%m-%d'),
                           help='Target date (YYYY-MM-DD)')
    find_parser.add_argument('--duration', type=int, default=60,
                           help='Minimum slot duration in minutes (default: 60)')
    find_parser.add_argument('--timezone', default='UTC',
                           help='Timezone for results (default: UTC)')
    find_parser.add_argument('--working-hours', default='9-17',
                           help='Working hours range (default: 9-17)')
    find_parser.add_argument('--buffer', type=int, default=15,
                           help='Buffer time between meetings in minutes (default: 15)')
    find_parser.add_argument('--data-path',
                           help='Path to calendar data directory')
    find_parser.add_argument('--format', choices=['table', 'json', 'summary'], 
                           default='table',
                           help='Output format (default: table)')
    
    # Conflicts command
    conflict_parser = subparsers.add_parser('conflicts', help='Check for scheduling conflicts')
    conflict_parser.add_argument('--timezone', default='UTC',
                               help='Timezone for conflict detection (default: UTC)')
    conflict_parser.add_argument('--data-path',
                               help='Path to calendar data directory')
    conflict_parser.add_argument('--format', choices=['table', 'json', 'summary'], 
                               default='table',
                               help='Output format (default: table)')
    
    # Interactive command
    interactive_parser = subparsers.add_parser('interactive', help='Run interactive calendar coordination')
    
    # Parse arguments
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialize CLI
    cli = CalendarCLI()
    
    try:
        if args.command == 'find':
            free_slots = cli.find_free_slots(args)
            cli.display_slots(free_slots, args.format)
            
        elif args.command == 'conflicts':
            conflicts = cli.check_conflicts(args)
            cli.display_conflicts(conflicts, args.format)
            
        elif args.command == 'interactive':
            cli.interactive_mode()
        
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()