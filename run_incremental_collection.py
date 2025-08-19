#!/usr/bin/env python3
"""
Incremental Collection Script with Data Persistence
Saves data immediately as collected to prevent loss on timeout
"""

import sys
import json
import time
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def collect_calendar_incrementally():
    """Collect calendar data with incremental saves"""
    print("=" * 80)
    print("📅 INCREMENTAL CALENDAR COLLECTION")
    print("=" * 80)
    
    from src.collectors.calendar_collector import CalendarCollector
    from src.collectors.employee_collector import EmployeeCollector
    
    # Setup
    config_path = project_root / "config" / "test_config.json"
    cal_collector = CalendarCollector(config_path)
    
    if not cal_collector.setup_calendar_service():
        print("❌ Calendar authentication failed")
        return False
    
    # Get employee calendars
    emp_collector = EmployeeCollector()
    employee_calendars = emp_collector.get_all_calendar_ids(include_inactive=False)
    print(f"✅ Found {len(employee_calendars)} active employee calendars")
    
    # Create output directory
    output_dir = project_root / "data" / "raw" / "calendar" / datetime.now().strftime("%Y-%m-%d")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Process each calendar and save immediately
    total_events = 0
    processed = 0
    failed = []
    
    # Collection parameters - reduced for initial run
    weeks_backward = 4  # 1 month back
    weeks_forward = 2   # 2 weeks forward
    
    print(f"\n📊 Collection parameters:")
    print(f"   • Time range: {weeks_backward} weeks back, {weeks_forward} weeks forward")
    print(f"   • Target calendars: {len(employee_calendars)}")
    print(f"   • Output directory: {output_dir}")
    print()
    
    for idx, (email, calendar_id) in enumerate(employee_calendars.items(), 1):
        try:
            print(f"[{idx}/{len(employee_calendars)}] {email}: ", end="", flush=True)
            
            # Collect events
            events = cal_collector.collect_calendar_events_weekly_chunks(
                calendar_id=calendar_id,
                calendar_info={'email': email, 'employee_context': {'display_name': email}},
                weeks_backward=weeks_backward,
                weeks_forward=weeks_forward
            )
            
            if events:
                # Save immediately to JSONL
                output_file = output_dir / f"employee_{email.replace('@', '_at_').replace('.', '_')}.jsonl"
                with open(output_file, 'w') as f:
                    for event in events:
                        # Add metadata
                        event['_collected_at'] = datetime.now().isoformat()
                        event['_employee_email'] = email
                        event['_calendar_id'] = calendar_id
                        f.write(json.dumps(event) + '\n')
                
                total_events += len(events)
                processed += 1
                print(f"{len(events)} events saved ✅")
            else:
                print("no access ⚠️")
                
        except KeyboardInterrupt:
            print("\n\n⚠️ Collection interrupted by user")
            break
        except Exception as e:
            print(f"error: {str(e)[:50]} ❌")
            failed.append(email)
        
        # Progress report every 10 calendars
        if idx % 10 == 0:
            print(f"\n   Progress: {processed} calendars, {total_events} events total\n")
        
        # Stop after 50 calendars for initial run
        if idx >= 50:
            print(f"\n\n📊 Stopping after {idx} calendars (initial run limit)")
            break
    
    # Save summary
    summary = {
        'collection_date': datetime.now().isoformat(),
        'parameters': {
            'weeks_backward': weeks_backward,
            'weeks_forward': weeks_forward
        },
        'results': {
            'total_calendars': len(employee_calendars),
            'processed_calendars': processed,
            'total_events': total_events,
            'failed_calendars': len(failed)
        },
        'failed_list': failed,
        'output_directory': str(output_dir)
    }
    
    summary_file = output_dir / "collection_summary.json"
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print("\n" + "=" * 60)
    print("📊 COLLECTION SUMMARY")
    print("=" * 60)
    print(f"✅ Calendars processed: {processed}/{len(employee_calendars)}")
    print(f"📅 Total events: {total_events:,}")
    print(f"❌ Failed: {len(failed)}")
    print(f"💾 Data saved to: {output_dir}")
    print(f"📄 Summary: {summary_file}")
    
    return True

def collect_drive_incrementally():
    """Collect drive data with incremental saves"""
    print("\n" + "=" * 80)
    print("🚗 INCREMENTAL DRIVE COLLECTION")
    print("=" * 80)
    
    from src.collectors.drive_collector import DriveCollector
    
    drive_collector = DriveCollector()
    
    if not drive_collector.setup_drive_authentication():
        print("❌ Drive authentication failed")
        return False
    
    # Create output directory
    output_dir = project_root / "data" / "raw" / "drive" / datetime.now().strftime("%Y-%m-%d")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n📊 Collection parameters:")
    print(f"   • Time range: Past 30 days (initial run)")
    print(f"   • Max files: 1000 (initial run)")
    print(f"   • Output directory: {output_dir}")
    print()
    
    # Discover files with reduced scope for initial run
    discovered_files = drive_collector.discover_all_files(
        days_backward=30,  # Just last month for initial run
        max_files=1000     # Limit to 1000 files
    )
    
    if discovered_files:
        # Save to JSONL immediately
        output_file = output_dir / "drive_metadata.jsonl"
        with open(output_file, 'w') as f:
            for file_id, metadata in discovered_files.items():
                metadata['_file_id'] = file_id
                metadata['_collected_at'] = datetime.now().isoformat()
                f.write(json.dumps(metadata) + '\n')
        
        print(f"\n✅ Saved {len(discovered_files)} file metadata records")
        print(f"💾 Data saved to: {output_file}")
        
        # Save summary
        drive_collector._save_drive_summary(discovered_files)
        
        return True
    else:
        print("❌ No files discovered")
        return False

def main():
    """Run incremental collection for both services"""
    print("🎯 AI CHIEF OF STAFF - INCREMENTAL DATA COLLECTION")
    print("=" * 80)
    print("This script saves data incrementally to prevent loss on timeout")
    print()
    
    # Calendar collection
    calendar_success = collect_calendar_incrementally()
    
    # Brief pause
    print("\n⏸️ Pausing 5 seconds before Drive collection...")
    time.sleep(5)
    
    # Drive collection
    drive_success = collect_drive_incrementally()
    
    # Final summary
    print("\n" + "=" * 80)
    print("🎉 INCREMENTAL COLLECTION COMPLETE")
    print("=" * 80)
    print(f"📅 Calendar: {'✅ Success' if calendar_success else '❌ Failed'}")
    print(f"🚗 Drive: {'✅ Success' if drive_success else '❌ Failed'}")
    
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"\n📁 Data locations:")
    print(f"   • Calendar: data/raw/calendar/{today}/")
    print(f"   • Drive: data/raw/drive/{today}/")
    
    return 0 if (calendar_success or drive_success) else 1

if __name__ == "__main__":
    sys.exit(main())