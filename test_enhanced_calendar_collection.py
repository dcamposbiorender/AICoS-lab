#!/usr/bin/env python3
"""
Enhanced Calendar Collection Test Harness - Company-Wide Scale
Tests Tasks 3.1-3.3: Employee discovery, bulk collection, and progressive time windows
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add src to path for imports
src_path = str(Path(__file__).parent / "src")
sys.path.insert(0, src_path)

# Set PYTHONPATH to allow relative imports in the modules
import os
os.environ['PYTHONPATH'] = src_path

try:
    from src.collectors.employee_collector import EmployeeCollector
    from src.collectors.calendar_collector import CalendarCollector
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("⚠️ This test requires proper authentication setup and credentials.")
    print("💡 This is a demonstration of the enhanced calendar collection features.")
    sys.exit(1)

def test_task_3_1_employee_discovery():
    """Test Task 3.1: Enhanced employee discovery with calendar ID mapping"""
    print("🧪 TESTING TASK 3.1: EMPLOYEE DISCOVERY")
    print("=" * 50)
    
    # Initialize employee collector
    employee_collector = EmployeeCollector()
    
    try:
        # Test getting all calendar IDs (active only)
        print("\n📧 Testing active employee calendar ID mapping...")
        active_calendar_ids = employee_collector.get_active_calendar_ids()
        
        print(f"✅ Active calendar IDs discovered: {len(active_calendar_ids)}")
        
        # Show first few examples
        for i, (email, calendar_id) in enumerate(list(active_calendar_ids.items())[:5]):
            print(f"  {i+1}. {email} -> {calendar_id}")
        
        if len(active_calendar_ids) > 5:
            print(f"  ... and {len(active_calendar_ids) - 5} more employees")
        
        # Test getting all calendar IDs (including inactive)
        print("\n📧 Testing all employee calendar ID mapping (including inactive)...")
        all_calendar_ids = employee_collector.get_all_calendar_ids_including_inactive()
        
        print(f"✅ All calendar IDs discovered: {len(all_calendar_ids)}")
        print(f"📊 Active: {len(active_calendar_ids)}, Total: {len(all_calendar_ids)}")
        print(f"🟡 Inactive: {len(all_calendar_ids) - len(active_calendar_ids)}")
        
        return {
            "status": "success",
            "active_employees": len(active_calendar_ids),
            "total_employees": len(all_calendar_ids),
            "calendar_ids": active_calendar_ids  # Return active for further testing
        }
        
    except Exception as e:
        print(f"❌ Task 3.1 failed: {e}")
        return {
            "status": "failed",
            "error": str(e),
            "calendar_ids": {}
        }

def test_task_3_2_bulk_collection(calendar_ids, test_subset_size=10):
    """Test Task 3.2: Bulk calendar collection from employee list"""
    print(f"\n🧪 TESTING TASK 3.2: BULK CALENDAR COLLECTION")
    print("=" * 50)
    
    if not calendar_ids:
        print("⚠️ No calendar IDs available, skipping bulk collection test")
        return {"status": "skipped", "reason": "no_calendar_ids"}
    
    # Use subset for testing to avoid overwhelming APIs
    test_calendar_ids = dict(list(calendar_ids.items())[:test_subset_size])
    
    print(f"📊 Testing with {len(test_calendar_ids)} employees (subset for safe testing)")
    
    # Initialize calendar collector
    calendar_collector = CalendarCollector()
    
    # Setup calendar service
    if not calendar_collector.setup_calendar_service():
        print("❌ Failed to setup calendar service")
        return {"status": "failed", "error": "calendar_service_setup_failed"}
    
    try:
        # Test bulk collection with different time windows
        test_results = {}
        
        # Test 7-day lookback
        print("\n📅 Testing 7-day bulk collection...")
        results_7d = calendar_collector.collect_from_employee_list(test_calendar_ids, 7)
        test_results['7_days'] = results_7d
        
        summary_7d = results_7d.get('bulk_collection_summary', {})
        print(f"✅ 7-day results: {summary_7d.get('successful_collections', 0)}/{summary_7d.get('total_employees', 0)} success")
        print(f"📅 Events collected: {summary_7d.get('total_events_collected', 0)}")
        print(f"🚫 Permission denied: {summary_7d.get('permission_denied', 0)}")
        print(f"🎯 Success rate: {summary_7d.get('success_rate', 0):.1f}%")
        
        # Test 30-day lookback (if 7-day was successful)
        if summary_7d.get('successful_collections', 0) > 0:
            print("\n📅 Testing 30-day bulk collection...")
            results_30d = calendar_collector.collect_from_employee_list(test_calendar_ids, 30)
            test_results['30_days'] = results_30d
            
            summary_30d = results_30d.get('bulk_collection_summary', {})
            print(f"✅ 30-day results: {summary_30d.get('successful_collections', 0)}/{summary_30d.get('total_employees', 0)} success")
            print(f"📅 Events collected: {summary_30d.get('total_events_collected', 0)}")
            print(f"🎯 Success rate: {summary_30d.get('success_rate', 0):.1f}%")
        
        return {
            "status": "success",
            "test_subset_size": len(test_calendar_ids),
            "results": test_results
        }
        
    except Exception as e:
        print(f"❌ Task 3.2 failed: {e}")
        return {
            "status": "failed", 
            "error": str(e),
            "test_subset_size": len(test_calendar_ids)
        }

def test_task_3_3_progressive_collection(calendar_ids, test_subset_size=5):
    """Test Task 3.3: Progressive time window collection"""
    print(f"\n🧪 TESTING TASK 3.3: PROGRESSIVE TIME WINDOW COLLECTION")
    print("=" * 60)
    
    if not calendar_ids:
        print("⚠️ No calendar IDs available, skipping progressive collection test")
        return {"status": "skipped", "reason": "no_calendar_ids"}
    
    # Use small subset for testing progressive collection
    test_calendar_ids = dict(list(calendar_ids.items())[:test_subset_size])
    
    print(f"📊 Testing progressive collection with {len(test_calendar_ids)} employees")
    print(f"🔄 Time windows: [7, 30, 90, 365] days")
    
    # Initialize calendar collector with progressive collection config
    calendar_collector = CalendarCollector()
    
    # Override config for testing (shorter delays)
    calendar_collector.config.update({
        'time_windows': [7, 30],  # Test with shorter windows for speed
        'time_window_delay': 10,  # Shorter delay for testing
        'progressive_collection': {
            'enabled': True,
            'save_each_window': True,
            'continue_on_window_failure': True
        }
    })
    
    # Setup calendar service
    if not calendar_collector.setup_calendar_service():
        print("❌ Failed to setup calendar service")
        return {"status": "failed", "error": "calendar_service_setup_failed"}
    
    try:
        print(f"🎯 Starting progressive collection with time windows: {calendar_collector.config['time_windows']}")
        
        # Run progressive collection
        progressive_results = calendar_collector.collect_progressive_time_windows(test_calendar_ids)
        
        # Analyze results
        summary = progressive_results.get('progressive_summary', {})
        stats = progressive_results.get('aggregated_stats', {})
        window_results = progressive_results.get('window_results', {})
        
        print(f"\n📊 PROGRESSIVE COLLECTION ANALYSIS:")
        print(f"⏱️ Total duration: {summary.get('total_duration_minutes', 0):.1f} minutes")
        print(f"📊 Windows completed: {stats.get('windows_completed', 0)}/{len(calendar_collector.config['time_windows'])}")
        print(f"❌ Windows failed: {stats.get('windows_failed', 0)}")
        print(f"📅 Total events collected: {stats.get('total_events_collected', 0)}")
        print(f"✅ Total successful collections: {stats.get('total_successful_collections', 0)}")
        print(f"❌ Total failed collections: {stats.get('total_failed_collections', 0)}")
        
        # Window-by-window breakdown
        print(f"\n📋 WINDOW-BY-WINDOW BREAKDOWN:")
        for window_name, window_data in window_results.items():
            window_info = window_data.get('window_info', {})
            collection_summary = window_data.get('collection_results', {}).get('bulk_collection_summary', {})
            
            print(f"  {window_name}:")
            print(f"    📅 Days back: {window_info.get('days_back', 'unknown')}")
            print(f"    ⏱️ Duration: {window_info.get('duration_minutes', 0):.1f} minutes")
            print(f"    ✅ Success: {collection_summary.get('successful_collections', 0)}/{collection_summary.get('total_employees', 0)}")
            print(f"    📊 Events: {collection_summary.get('total_events_collected', 0)}")
            print(f"    🎯 Rate: {collection_summary.get('success_rate', 0):.1f}%")
        
        return {
            "status": "success",
            "test_subset_size": len(test_calendar_ids),
            "progressive_results": progressive_results
        }
        
    except Exception as e:
        print(f"❌ Task 3.3 failed: {e}")
        return {
            "status": "failed",
            "error": str(e),
            "test_subset_size": len(test_calendar_ids)
        }

def main():
    """Run all enhanced calendar collection tests"""
    print("🚀 ENHANCED CALENDAR COLLECTION TEST SUITE")
    print("Testing Tasks 3.1-3.3: Company-Wide Calendar Scale")
    print("=" * 70)
    
    test_results = {
        "test_suite": "enhanced_calendar_collection",
        "timestamp": datetime.now().isoformat(),
        "tasks": {}
    }
    
    # Test Task 3.1: Employee Discovery
    task_3_1_results = test_task_3_1_employee_discovery()
    test_results["tasks"]["task_3_1"] = task_3_1_results
    
    # Test Task 3.2: Bulk Collection (if Task 3.1 succeeded)
    if task_3_1_results["status"] == "success":
        calendar_ids = task_3_1_results.get("calendar_ids", {})
        task_3_2_results = test_task_3_2_bulk_collection(calendar_ids, test_subset_size=10)
        test_results["tasks"]["task_3_2"] = task_3_2_results
        
        # Test Task 3.3: Progressive Collection (if we have calendar IDs)
        if calendar_ids:
            task_3_3_results = test_task_3_3_progressive_collection(calendar_ids, test_subset_size=5)
            test_results["tasks"]["task_3_3"] = task_3_3_results
    else:
        print("⚠️ Skipping Tasks 3.2 and 3.3 due to Task 3.1 failure")
        test_results["tasks"]["task_3_2"] = {"status": "skipped", "reason": "task_3_1_failed"}
        test_results["tasks"]["task_3_3"] = {"status": "skipped", "reason": "task_3_1_failed"}
    
    # Save complete test results
    results_file = Path("enhanced_calendar_test_results.json")
    with open(results_file, 'w') as f:
        json.dump(test_results, f, indent=2)
    
    print(f"\n🎉 TEST SUITE COMPLETE!")
    print(f"📄 Complete results saved to: {results_file}")
    
    # Summary
    task_statuses = [task_data.get("status", "unknown") for task_data in test_results["tasks"].values()]
    successful_tasks = task_statuses.count("success")
    total_tasks = len(task_statuses)
    
    print(f"\n📊 FINAL SUMMARY:")
    print(f"✅ Successful tasks: {successful_tasks}/{total_tasks}")
    print(f"❌ Failed tasks: {task_statuses.count('failed')}")
    print(f"⏭️ Skipped tasks: {task_statuses.count('skipped')}")
    
    for task_name, task_data in test_results["tasks"].items():
        status = task_data.get("status", "unknown")
        status_emoji = "✅" if status == "success" else "❌" if status == "failed" else "⏭️"
        print(f"  {status_emoji} {task_name.upper()}: {status}")
    
    return test_results

if __name__ == "__main__":
    main()