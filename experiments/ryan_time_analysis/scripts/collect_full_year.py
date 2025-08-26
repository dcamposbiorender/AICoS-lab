#!/usr/bin/env python3
"""
Full Year Calendar Collection for Ryan Marien Time Analysis Experiment

This script collects a full year of calendar data specifically for Ryan Marien
to support advanced time allocation analysis. Data is stored in the isolated
experiment directory to avoid contaminating the main AICoS system.

Usage:
    python experiments/ryan_time_analysis/scripts/collect_full_year.py

Expected Runtime: 2-4 hours due to Google API rate limiting
"""

import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any

# Add main project to path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Import from main AICoS system
from src.collectors.calendar_collector import CalendarCollector

# Experiment paths
EXPERIMENT_ROOT = Path(__file__).parent.parent
DATA_PATH = EXPERIMENT_ROOT / "data" / "raw"
LOG_PATH = EXPERIMENT_ROOT / "experiment_log.md"

# Ryan's identifiers
RYAN_EMAIL = "ryan@biorender.com"
RYAN_SLACK_ID = "UBL74SKU0"

def log_session_update(session_info: str):
    """Append session update to experiment log"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"\n### {timestamp}\n{session_info}\n"
    
    with open(LOG_PATH, 'a') as f:
        f.write(log_entry)
    print(f"📝 Logged: {session_info}")

def collect_ryan_full_year() -> Dict[str, Any]:
    """
    Collect full year of calendar data specifically for Ryan Marien
    
    Returns:
        Dictionary containing collection results and statistics
    """
    start_time = datetime.now()
    log_session_update(f"**Data Collection Started** for Ryan Marien ({RYAN_EMAIL})")
    
    try:
        # Initialize calendar collector
        collector = CalendarCollector()
        log_session_update("✅ CalendarCollector initialized")
        
        # Set up data path for this experiment
        collection_path = DATA_PATH / "calendar_full_year"
        collection_path.mkdir(parents=True, exist_ok=True)
        
        # Skip employee validation - we know Ryan exists from prior exploration
        log_session_update(f"✅ Skipping employee validation - using known Ryan email")
        print(f"🎯 Collecting full year data for: Ryan Marien ({RYAN_EMAIL})")
        
        # Collect full year (52 weeks backward + 4 weeks forward)
        print(f"📅 Collecting 52 weeks backward + 4 weeks forward")
        print(f"💾 Saving to: {collection_path}")
        print(f"⚠️  Expected runtime: 2-4 hours due to API rate limiting")
        print(f"🔄 Collection will show progress updates...\n")
        
        # Start collection with extended time window
        collection_results = collector.collect_all_employee_calendars(
            weeks_backward=52,  # Full year
            weeks_forward=4     # 1 month ahead
        )
        
        # Filter to just Ryan's data
        ryan_data = {}
        if RYAN_EMAIL in collection_results:
            ryan_data = collection_results[RYAN_EMAIL]
        else:
            # Try to find Ryan by calendar ID or other identifier
            for cal_id, data in collection_results.items():
                if RYAN_EMAIL in cal_id or 'ryan' in cal_id.lower():
                    ryan_data = data
                    break
        
        if not ryan_data:
            raise ValueError(f"No data collected for Ryan ({RYAN_EMAIL})")
        
        # Save Ryan's data to experiment directory
        output_file = collection_path / f"ryan_calendar_full_year_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(output_file, 'w') as f:
            json.dump(ryan_data, f, indent=2, default=str)
        
        # Calculate statistics
        events = ryan_data.get('events', [])
        event_count = len(events)
        
        if events:
            # Get date range from events
            dates = []
            for event in events:
                start_date = event.get('start', {}).get('dateTime') or event.get('start', {}).get('date')
                if start_date:
                    dates.append(start_date[:10])  # Just YYYY-MM-DD
            
            date_range = f"{min(dates)} to {max(dates)}" if dates else "Unknown"
        else:
            date_range = "No events found"
        
        duration = datetime.now() - start_time
        
        # Log completion
        completion_info = f"""**Data Collection Completed**
- **Events Collected**: {event_count:,}
- **Date Range**: {date_range}  
- **Duration**: {duration.total_seconds()/60:.1f} minutes
- **Output File**: {output_file.name}
- **API Calls**: {ryan_data.get('collection_stats', {}).get('total_api_calls', 'Unknown')}
- **Rate Limits Hit**: {ryan_data.get('collection_stats', {}).get('rate_limits_hit', 0)}"""
        
        log_session_update(completion_info)
        
        print(f"\n🎉 Collection Complete!")
        print(f"📊 Collected {event_count:,} events spanning {date_range}")
        print(f"⏱️  Total time: {duration.total_seconds()/60:.1f} minutes")
        print(f"💾 Saved to: {output_file}")
        
        return {
            'success': True,
            'events_collected': event_count,
            'date_range': date_range,
            'duration_minutes': duration.total_seconds()/60,
            'output_file': str(output_file),
            'ryan_data': ryan_data
        }
        
    except Exception as e:
        error_info = f"❌ **Collection Failed**: {str(e)}"
        log_session_update(error_info)
        print(f"\n❌ Error: {e}")
        return {
            'success': False,
            'error': str(e),
            'duration_minutes': (datetime.now() - start_time).total_seconds()/60
        }

def main():
    """Main execution function"""
    print("🚀 Starting Full Year Calendar Collection for Ryan Marien")
    print("=" * 60)
    print(f"Target: {RYAN_EMAIL}")
    print(f"Experiment: {EXPERIMENT_ROOT.name}")
    print(f"Expected runtime: 2-4 hours")
    print("=" * 60)
    
    # Run collection
    results = collect_ryan_full_year()
    
    if results['success']:
        print(f"\n✅ SUCCESS: Data collection completed successfully")
        print(f"📊 {results['events_collected']:,} events collected")
        print(f"⏱️  Runtime: {results['duration_minutes']:.1f} minutes")
        print(f"\n🎯 Next steps:")
        print("1. Run context switching analysis")
        print("2. Analyze deep work patterns") 
        print("3. Generate insights report")
    else:
        print(f"\n❌ FAILED: {results['error']}")
        print(f"⏱️  Runtime: {results['duration_minutes']:.1f} minutes")
        print("\n🔧 Troubleshooting:")
        print("1. Check Google Calendar API credentials")
        print("2. Verify network connectivity")
        print("3. Check API quota limits")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())