#!/usr/bin/env python3
"""
Calendar Collection Only - with timeout protection and batch processing
"""

import sys
import time
import json
import signal
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def timeout_handler(signum, frame):
    """Handle timeout gracefully"""
    print("\n⏱️ Collection timeout reached - saving progress...")
    raise TimeoutError("Collection timeout")

def run_calendar_collection_batch():
    """Run calendar collection with batch processing and timeouts"""
    print("=" * 80)
    print("📅 CALENDAR COLLECTION - BATCH MODE")
    print("=" * 80)
    print(f"Start time: {datetime.now().isoformat()}")
    
    try:
        from src.collectors.calendar_collector import CalendarCollector
        from src.collectors.employee_collector import EmployeeCollector
        
        # Setup calendar collector
        config_path = project_root / "config" / "test_config.json"
        cal_collector = CalendarCollector(config_path)
        
        # Setup authentication
        print("\n🔐 Setting up calendar authentication...")
        if not cal_collector.setup_calendar_service():
            print("❌ Calendar authentication failed")
            return False
        
        # Get employee calendars
        print("\n👥 Discovering employee calendars...")
        emp_collector = EmployeeCollector()
        employee_calendar_ids = emp_collector.get_all_calendar_ids(include_inactive=True)
        
        print(f"✅ Found {len(employee_calendar_ids)} employee calendar IDs")
        
        # Process in smaller batches to avoid timeout
        batch_size = 10  # Process 10 calendars at a time
        total_events = 0
        processed_calendars = 0
        failed_calendars = []
        
        # Group calendars into batches
        calendar_items = list(employee_calendar_ids.items())
        batches = [calendar_items[i:i+batch_size] for i in range(0, len(calendar_items), batch_size)]
        
        print(f"\n📊 Processing {len(batches)} batches of {batch_size} calendars each")
        print("   • Time range: 2 weeks back + 1 week forward (testing)")
        print("   • Rate limiting: 3s base delay + jitter")
        
        for batch_idx, batch in enumerate(batches[:5], 1):  # Limit to first 5 batches for testing
            print(f"\n🔄 Batch {batch_idx}/{min(5, len(batches))}: Processing {len(batch)} calendars...")
            
            for email, calendar_id in batch:
                try:
                    # Set a timeout for each calendar
                    signal.signal(signal.SIGALRM, timeout_handler)
                    signal.alarm(60)  # 60 second timeout per calendar
                    
                    print(f"   • {email}: ", end="", flush=True)
                    
                    # Collect with reduced time range for testing
                    events = cal_collector.collect_calendar_events_weekly_chunks(
                        calendar_id=calendar_id,
                        calendar_info={'email': email, 'employee_context': {'display_name': email}},
                        weeks_backward=2,  # Just 2 weeks for testing
                        weeks_forward=1    # Just 1 week forward
                    )
                    
                    # Cancel timeout
                    signal.alarm(0)
                    
                    if events:
                        total_events += len(events)
                        processed_calendars += 1
                        print(f"{len(events)} events ✅")
                    else:
                        print("no access ⚠️")
                        
                except TimeoutError:
                    signal.alarm(0)  # Cancel timeout
                    print("timeout ⏱️")
                    failed_calendars.append(email)
                except Exception as e:
                    signal.alarm(0)  # Cancel timeout
                    print(f"error: {str(e)[:30]} ❌")
                    failed_calendars.append(email)
            
            print(f"   Batch complete: {total_events} total events from {processed_calendars} calendars")
            
            # Brief pause between batches
            if batch_idx < min(5, len(batches)):
                print("   Pausing 5 seconds before next batch...")
                time.sleep(5)
        
        # Final summary
        print("\n" + "=" * 60)
        print("📊 COLLECTION SUMMARY")
        print("=" * 60)
        print(f"✅ Calendars processed: {processed_calendars}/{len(employee_calendar_ids)}")
        print(f"📅 Total events collected: {total_events:,}")
        print(f"❌ Failed calendars: {len(failed_calendars)}")
        
        if failed_calendars:
            print(f"\nFailed calendars: {', '.join(failed_calendars[:5])}{'...' if len(failed_calendars) > 5 else ''}")
        
        # Save summary
        summary_file = project_root / "calendar_batch_results.json"
        with open(summary_file, 'w') as f:
            json.dump({
                'processed_calendars': processed_calendars,
                'total_events': total_events,
                'failed_calendars': failed_calendars,
                'timestamp': datetime.now().isoformat()
            }, f, indent=2)
        print(f"\n💾 Results saved to: {summary_file}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Calendar collection failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_calendar_collection_batch()
    sys.exit(0 if success else 1)