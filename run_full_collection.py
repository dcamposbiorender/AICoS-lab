#!/usr/bin/env python3
"""
Full Collection Script for Enhanced Calendar and Drive Collectors
Executes comprehensive data gathering for AI Chief of Staff system
"""

import sys
import time
import json
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def run_calendar_collection():
    """Execute full calendar collection for all employee calendars"""
    print("=" * 80)
    print("📅 STARTING FULL CALENDAR COLLECTION")
    print("=" * 80)
    print(f"Start time: {datetime.now().isoformat()}")
    print()
    
    try:
        from src.collectors.calendar_collector import CalendarCollector
        
        # Use production config
        config_path = project_root / "config" / "test_config.json"
        collector = CalendarCollector(config_path)
        
        # Setup authentication
        print("🔐 Setting up calendar authentication...")
        if not collector.setup_calendar_service():
            print("❌ Calendar authentication failed")
            return None
        
        # Run bulk collection for all employees
        print("\n🚀 Starting bulk employee calendar collection...")
        print("   • Time range: 6 months backward + 30 days forward")
        print("   • Collection strategy: Weekly chunks (7-day increments)")
        print("   • Expected calendars: ~206 employees")
        print("   • Estimated events: 20,000-40,000")
        print()
        
        results = collector.collect_all_employee_calendars()
        
        # Print results summary
        print("\n" + "=" * 60)
        print("📊 CALENDAR COLLECTION RESULTS")
        print("=" * 60)
        print(f"✅ Calendars processed: {results['calendars_processed']}")
        print(f"📅 Total events collected: {results['total_events']:,}")
        print(f"⏱️  Collection duration: {results['duration_minutes']:.1f} minutes")
        print(f"🌐 API requests made: {results['api_requests_made']:,}")
        print(f"⚠️  Rate limit hits: {results['rate_limit_hits']}")
        
        if results['errors']:
            print(f"\n❌ Errors encountered: {len(results['errors'])}")
            for error in results['errors'][:5]:  # Show first 5 errors
                print(f"   • {error}")
        
        # Save results summary
        summary_file = project_root / "calendar_collection_results.json"
        with open(summary_file, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n💾 Results saved to: {summary_file}")
        
        return results
        
    except Exception as e:
        print(f"❌ Calendar collection failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def run_drive_collection():
    """Execute full drive metadata collection for past year"""
    print("\n" + "=" * 80)
    print("🚗 STARTING FULL DRIVE COLLECTION")
    print("=" * 80)
    print(f"Start time: {datetime.now().isoformat()}")
    print()
    
    try:
        from src.collectors.drive_collector import DriveCollector
        
        collector = DriveCollector()
        
        # Run full collection
        print("🚀 Starting Drive metadata collection...")
        print("   • Time range: Past 365 days")
        print("   • Collection type: Metadata only (no content)")
        print("   • Expected files: 1,000-10,000")
        print("   • Rate limiting: 900 requests/100s with exponential backoff")
        print()
        
        result = collector.collect()
        
        # Print results summary
        print("\n" + "=" * 60)
        print("📊 DRIVE COLLECTION RESULTS")
        print("=" * 60)
        print(f"✅ Files collected: {result.files_collected:,}")
        print(f"🔄 Changes tracked: {result.changes_tracked}")
        print(f"⏱️  Collection duration: {result.collection_duration/60:.1f} minutes")
        print(f"🌐 API requests made: {result.api_requests_made:,}")
        print(f"⚠️  Rate limit hits: {result.rate_limit_hits}")
        
        if result.errors:
            print(f"\n❌ Errors encountered: {len(result.errors)}")
            for error in result.errors[:5]:  # Show first 5 errors
                print(f"   • {error}")
        
        # Save results summary
        summary_file = project_root / "drive_collection_results.json"
        with open(summary_file, 'w') as f:
            json.dump({
                'files_collected': result.files_collected,
                'changes_tracked': result.changes_tracked,
                'permissions_updated': result.permissions_updated,
                'errors': result.errors,
                'collection_duration': result.collection_duration,
                'api_requests_made': result.api_requests_made,
                'rate_limit_hits': result.rate_limit_hits
            }, f, indent=2)
        print(f"\n💾 Results saved to: {summary_file}")
        
        return result
        
    except Exception as e:
        print(f"❌ Drive collection failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """Execute both calendar and drive collections"""
    print("🎯 AI CHIEF OF STAFF - FULL DATA COLLECTION")
    print("=" * 80)
    print(f"Collection initiated: {datetime.now().isoformat()}")
    print(f"Project root: {project_root}")
    print()
    
    start_time = time.time()
    
    # Run calendar collection first
    calendar_results = run_calendar_collection()
    
    # Brief pause between collections
    print("\n⏸️  Pausing 10 seconds before Drive collection...")
    time.sleep(10)
    
    # Run drive collection
    drive_results = run_drive_collection()
    
    # Final summary
    total_duration = time.time() - start_time
    print("\n" + "=" * 80)
    print("🎉 FULL COLLECTION COMPLETE")
    print("=" * 80)
    print(f"⏱️  Total duration: {total_duration/60:.1f} minutes")
    
    if calendar_results:
        print(f"\n📅 Calendar:")
        print(f"   • Calendars: {calendar_results['calendars_processed']}")
        print(f"   • Events: {calendar_results['total_events']:,}")
        print(f"   • Duration: {calendar_results['duration_minutes']:.1f} min")
    else:
        print("\n📅 Calendar: ❌ Failed")
    
    if drive_results:
        print(f"\n🚗 Drive:")
        print(f"   • Files: {drive_results.files_collected:,}")
        print(f"   • Duration: {drive_results.collection_duration/60:.1f} min")
    else:
        print("\n🚗 Drive: ❌ Failed")
    
    # Data location summary
    print(f"\n📁 Data stored in:")
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"   • Calendar: data/raw/calendar/{today}/")
    print(f"   • Drive: data/raw/drive/{today}/")
    
    success = bool(calendar_results or drive_results)
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())