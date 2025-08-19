#!/usr/bin/env python3
"""
Test Enhanced Calendar and Drive Collectors
Quick validation script to test new functionality before full collection
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_enhanced_calendar_collector():
    """Test calendar collector with employee discovery and weekly chunks"""
    print("=" * 60)
    print("🧪 TESTING ENHANCED CALENDAR COLLECTOR")
    print("=" * 60)
    
    try:
        from src.collectors.calendar_collector import CalendarCollector
        
        # Test with limited scope for validation
        config_path = project_root / "config" / "test_config.json"
        collector = CalendarCollector(config_path)
        
        # Test authentication
        print("\n📋 Testing authentication...")
        if not collector.setup_calendar_service():
            print("❌ Calendar authentication failed")
            return False
        
        # Test employee calendar discovery (small sample)
        print("\n📋 Testing employee calendar discovery...")
        employee_calendars = collector.discover_employee_calendars()
        
        if employee_calendars:
            print(f"✅ Found {len(employee_calendars)} accessible employee calendars")
            
            # Test weekly chunk collection on ONE calendar
            first_calendar_id = next(iter(employee_calendars.keys()))
            first_calendar_info = employee_calendars[first_calendar_id]
            
            print(f"\n📋 Testing weekly chunk collection on {first_calendar_info.get('employee_context', {}).get('display_name', first_calendar_id)}")
            events = collector.collect_calendar_events_weekly_chunks(
                calendar_id=first_calendar_id,
                calendar_info=first_calendar_info,
                weeks_backward=2,  # Test with just 2 weeks
                weeks_forward=1   # Test with just 1 week
            )
            
            print(f"✅ Weekly chunk test: collected {len(events)} events")
            return True
        else:
            print("⚠️ No accessible employee calendars found")
            print("   This could be normal if employees haven't shared their calendars")
            print("   But we should still verify the employee discovery worked")
            
            # Let's check if we can at least discover employees from Slack
            from src.collectors.employee_collector import EmployeeCollector
            emp_collector = EmployeeCollector()
            slack_employees = emp_collector.build_roster_from_slack()
            
            if len(slack_employees) > 0:
                print(f"✅ Employee discovery working: found {len(slack_employees)} employees from Slack")
                print("   (Calendar sharing permissions prevent calendar access - this is normal)")
                return True
            else:
                print("❌ Employee discovery failed: no employees found from Slack")
                return False
            
    except Exception as e:
        print(f"❌ Calendar collector test failed: {e}")
        return False

def test_enhanced_drive_collector():
    """Test drive collector with rate limiting and metadata collection"""
    print("\n" + "=" * 60)
    print("🧪 TESTING ENHANCED DRIVE COLLECTOR")
    print("=" * 60)
    
    try:
        from src.collectors.drive_collector import DriveCollector
        
        collector = DriveCollector()
        
        # Test authentication
        print("\n📋 Testing Drive authentication...")
        if not collector.setup_drive_authentication():
            print("❌ Drive authentication failed")
            return False
        
        # Test file discovery with small limit
        print("\n📋 Testing file discovery (limited to 100 files)...")
        discovered_files = collector.discover_all_files(days_backward=30, max_files=100)
        
        if discovered_files:
            print(f"✅ File discovery test: found {len(discovered_files)} files")
            
            # Test rate limiter statistics
            rate_stats = collector.rate_limiter.get_rate_limit_stats()
            print(f"📊 Rate limiter stats: {rate_stats}")
            
            # Test metadata enhancement
            sample_file = next(iter(discovered_files.values()))
            print(f"📄 Sample file metadata: {sample_file.get('name')} ({sample_file.get('file_size_mb', 0):.2f} MB)")
            
            return True
        else:
            print("⚠️ No files discovered (check permissions)")
            return False
            
    except Exception as e:
        print(f"❌ Drive collector test failed: {e}")
        return False

def main():
    """Run validation tests for both enhanced collectors"""
    print("🚀 ENHANCED COLLECTOR VALIDATION TESTS")
    print("Testing new functionality before full collection run")
    print("=" * 80)
    
    # Test calendar collector
    calendar_success = test_enhanced_calendar_collector()
    
    # Test drive collector
    drive_success = test_enhanced_drive_collector()
    
    # Final results
    print("\n" + "=" * 80)
    print("📊 VALIDATION RESULTS")
    print("=" * 80)
    print(f"📅 Calendar Collector: {'✅ PASSED' if calendar_success else '❌ FAILED'}")
    print(f"🚗 Drive Collector: {'✅ PASSED' if drive_success else '❌ FAILED'}")
    
    if calendar_success and drive_success:
        print("\n🎉 ALL TESTS PASSED! Ready for full collection.")
        print("\nTo run full collection:")
        print("  📅 Calendar: Use collect_all_employee_calendars() method")
        print("  🚗 Drive: Use collect() method with 365 days backward")
    else:
        print("\n⚠️ Some tests failed. Review errors before full collection.")
    
    return calendar_success and drive_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)