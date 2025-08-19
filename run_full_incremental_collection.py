#!/usr/bin/env python3
"""
Full Incremental Collection Script with Resume Support
Collects all calendars and drive data with configurable parameters
"""

import sys
import json
import time
import argparse
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def load_progress():
    """Load collection progress from previous runs"""
    progress_file = project_root / "data" / "collection_progress.json"
    if progress_file.exists():
        try:
            with open(progress_file, 'r') as f:
                return json.load(f)
        except:
            pass
    return {
        'calendars_completed': [],
        'last_calendar_index': 0,
        'total_events_collected': 0,
        'drive_completed': False
    }

def save_progress(progress):
    """Save collection progress for resume capability"""
    progress_file = project_root / "data" / "collection_progress.json"
    progress_file.parent.mkdir(exist_ok=True)
    with open(progress_file, 'w') as f:
        json.dump(progress, f, indent=2)

def collect_calendar_full(start_index=0, max_calendars=None, weeks_back=26, weeks_forward=4):
    """
    Collect calendar data with full control
    
    Args:
        start_index: Index to start from (for resuming)
        max_calendars: Maximum calendars to collect (None = all)
        weeks_back: Weeks to look backward (26 = 6 months)
        weeks_forward: Weeks to look forward (4 = 1 month)
    """
    print("=" * 80)
    print("📅 FULL CALENDAR COLLECTION")
    print("=" * 80)
    
    from src.collectors.calendar_collector import CalendarCollector
    from src.collectors.employee_collector import EmployeeCollector
    
    # Load progress
    progress = load_progress()
    
    # Setup
    config_path = project_root / "config" / "test_config.json"
    cal_collector = CalendarCollector(config_path)
    
    if not cal_collector.setup_calendar_service():
        print("❌ Calendar authentication failed")
        return False
    
    # Get employee calendars
    emp_collector = EmployeeCollector()
    all_calendars = emp_collector.get_all_calendar_ids(include_inactive=True)
    
    # Filter out already completed calendars
    calendars_to_process = {
        email: cal_id for email, cal_id in all_calendars.items()
        if email not in progress['calendars_completed']
    }
    
    print(f"✅ Total calendars: {len(all_calendars)}")
    print(f"✅ Already completed: {len(progress['calendars_completed'])}")
    print(f"✅ To process: {len(calendars_to_process)}")
    
    if not calendars_to_process:
        print("📊 All calendars already processed!")
        return True
    
    # Create output directory
    output_dir = project_root / "data" / "raw" / "calendar" / datetime.now().strftime("%Y-%m-%d")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Collection parameters
    print(f"\n📊 Collection parameters:")
    print(f"   • Time range: {weeks_back} weeks back, {weeks_forward} weeks forward")
    print(f"   • Starting from calendar #{start_index + 1}")
    if max_calendars:
        print(f"   • Will collect up to {max_calendars} calendars")
    print(f"   • Output directory: {output_dir}")
    print()
    
    # Process calendars
    calendar_list = list(calendars_to_process.items())
    if start_index > 0:
        calendar_list = calendar_list[start_index:]
    if max_calendars:
        calendar_list = calendar_list[:max_calendars]
    
    total_events = progress['total_events_collected']
    processed = len(progress['calendars_completed'])
    failed = []
    
    for idx, (email, calendar_id) in enumerate(calendar_list, start=start_index + 1):
        try:
            print(f"[{idx}/{len(all_calendars)}] {email}: ", end="", flush=True)
            
            # Check if file already exists (from previous partial run)
            output_file = output_dir / f"employee_{email.replace('@', '_at_').replace('.', '_')}.jsonl"
            if output_file.exists():
                # Count existing events
                with open(output_file, 'r') as f:
                    existing_events = sum(1 for _ in f)
                print(f"already saved ({existing_events} events) ✓")
                progress['calendars_completed'].append(email)
                processed += 1
                total_events += existing_events
                continue
            
            # Collect events
            events = cal_collector.collect_calendar_events_weekly_chunks(
                calendar_id=calendar_id,
                calendar_info={'email': email, 'employee_context': {'display_name': email}},
                weeks_backward=weeks_back,
                weeks_forward=weeks_forward
            )
            
            if events:
                # Save immediately to JSONL
                with open(output_file, 'w') as f:
                    for event in events:
                        # Add metadata
                        event['_collected_at'] = datetime.now().isoformat()
                        event['_employee_email'] = email
                        event['_calendar_id'] = calendar_id
                        f.write(json.dumps(event) + '\n')
                
                total_events += len(events)
                processed += 1
                progress['calendars_completed'].append(email)
                progress['total_events_collected'] = total_events
                progress['last_calendar_index'] = idx
                print(f"{len(events)} events saved ✅")
            else:
                print("no access ⚠️")
                progress['calendars_completed'].append(email)  # Mark as attempted
                
        except KeyboardInterrupt:
            print("\n\n⚠️ Collection interrupted by user")
            save_progress(progress)
            print(f"Progress saved. Resume from calendar #{idx}")
            break
        except Exception as e:
            print(f"error: {str(e)[:50]} ❌")
            failed.append(email)
        
        # Save progress every 10 calendars
        if idx % 10 == 0:
            save_progress(progress)
            print(f"\n   Progress saved: {processed} calendars, {total_events} events total\n")
        
        # Optional break after certain number
        if max_calendars and (idx - start_index) >= max_calendars:
            print(f"\n\n📊 Reached maximum of {max_calendars} calendars")
            break
    
    # Save final progress
    save_progress(progress)
    
    # Save summary
    summary = {
        'collection_date': datetime.now().isoformat(),
        'parameters': {
            'weeks_backward': weeks_back,
            'weeks_forward': weeks_forward,
            'start_index': start_index,
            'max_calendars': max_calendars
        },
        'results': {
            'total_calendars': len(all_calendars),
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
    print("📊 CALENDAR COLLECTION SUMMARY")
    print("=" * 60)
    print(f"✅ Calendars processed: {processed}/{len(all_calendars)}")
    print(f"📅 Total events: {total_events:,}")
    print(f"❌ Failed: {len(failed)}")
    print(f"💾 Data saved to: {output_dir}")
    print(f"📄 Summary: {summary_file}")
    
    return True

def collect_drive_full(days_back=365, max_files=100000):
    """
    Collect drive data with full parameters
    
    Args:
        days_back: Days to look backward (365 = 1 year)
        max_files: Maximum files to collect
    """
    print("\n" + "=" * 80)
    print("🚗 FULL DRIVE COLLECTION")
    print("=" * 80)
    
    # Check if already completed
    progress = load_progress()
    if progress.get('drive_completed'):
        print("✅ Drive collection already completed")
        return True
    
    from src.collectors.drive_collector import DriveCollector
    
    drive_collector = DriveCollector()
    
    if not drive_collector.setup_drive_authentication():
        print("❌ Drive authentication failed")
        return False
    
    # Create output directory
    output_dir = project_root / "data" / "raw" / "drive" / datetime.now().strftime("%Y-%m-%d")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n📊 Collection parameters:")
    print(f"   • Time range: Past {days_back} days")
    print(f"   • Max files: {max_files:,}")
    print(f"   • Output directory: {output_dir}")
    print()
    
    # Discover files
    discovered_files = drive_collector.discover_all_files(
        days_backward=days_back,
        max_files=max_files
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
        
        # Mark as completed
        progress['drive_completed'] = True
        progress['drive_files_collected'] = len(discovered_files)
        save_progress(progress)
        
        return True
    else:
        print("❌ No files discovered")
        return False

def main():
    """Run full incremental collection with command-line options"""
    parser = argparse.ArgumentParser(description='AI Chief of Staff - Full Data Collection')
    parser.add_argument('--calendars-only', action='store_true', 
                       help='Only collect calendar data')
    parser.add_argument('--drive-only', action='store_true',
                       help='Only collect drive data')
    parser.add_argument('--start-calendar', type=int, default=0,
                       help='Calendar index to start from (for resuming)')
    parser.add_argument('--max-calendars', type=int, default=None,
                       help='Maximum number of calendars to collect')
    parser.add_argument('--weeks-back', type=int, default=26,
                       help='Weeks to look backward for calendars (default: 26 = 6 months)')
    parser.add_argument('--weeks-forward', type=int, default=4,
                       help='Weeks to look forward for calendars (default: 4 = 1 month)')
    parser.add_argument('--days-back-drive', type=int, default=365,
                       help='Days to look backward for drive (default: 365 = 1 year)')
    parser.add_argument('--max-files', type=int, default=100000,
                       help='Maximum drive files to collect (default: 100000)')
    parser.add_argument('--resume', action='store_true',
                       help='Resume from last saved progress')
    
    args = parser.parse_args()
    
    print("🎯 AI CHIEF OF STAFF - FULL DATA COLLECTION")
    print("=" * 80)
    print(f"Collection initiated: {datetime.now().isoformat()}")
    print(f"Project root: {project_root}")
    
    # Load progress if resuming
    if args.resume:
        progress = load_progress()
        if progress['last_calendar_index'] > 0:
            args.start_calendar = progress['last_calendar_index']
            print(f"📊 Resuming from calendar #{args.start_calendar}")
            print(f"   Already collected: {progress['total_events_collected']:,} events")
    
    print()
    
    calendar_success = True
    drive_success = True
    
    # Calendar collection
    if not args.drive_only:
        calendar_success = collect_calendar_full(
            start_index=args.start_calendar,
            max_calendars=args.max_calendars,
            weeks_back=args.weeks_back,
            weeks_forward=args.weeks_forward
        )
        
        if not args.calendars_only:
            print("\n⏸️ Pausing 5 seconds before Drive collection...")
            time.sleep(5)
    
    # Drive collection
    if not args.calendars_only:
        drive_success = collect_drive_full(
            days_back=args.days_back_drive,
            max_files=args.max_files
        )
    
    # Final summary
    print("\n" + "=" * 80)
    print("🎉 COLLECTION COMPLETE")
    print("=" * 80)
    
    if not args.drive_only:
        print(f"📅 Calendar: {'✅ Success' if calendar_success else '❌ Failed'}")
    if not args.calendars_only:
        print(f"🚗 Drive: {'✅ Success' if drive_success else '❌ Failed'}")
    
    # Load final progress
    progress = load_progress()
    print(f"\n📊 Final Statistics:")
    print(f"   • Calendars completed: {len(progress.get('calendars_completed', []))}")
    print(f"   • Total events: {progress.get('total_events_collected', 0):,}")
    if progress.get('drive_completed'):
        print(f"   • Drive files: {progress.get('drive_files_collected', 0):,}")
    
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"\n📁 Data locations:")
    print(f"   • Calendar: data/raw/calendar/{today}/")
    print(f"   • Drive: data/raw/drive/{today}/")
    print(f"   • Progress: data/collection_progress.json")
    
    print("\n💡 Usage examples:")
    print("   • Resume collection: python3 run_full_incremental_collection.py --resume")
    print("   • Collect next 50 calendars: python3 run_full_incremental_collection.py --start-calendar 50 --max-calendars 50")
    print("   • Full 6-month calendar collection: python3 run_full_incremental_collection.py --calendars-only")
    print("   • Full drive collection: python3 run_full_incremental_collection.py --drive-only")
    
    return 0 if (calendar_success and drive_success) else 1

if __name__ == "__main__":
    sys.exit(main())