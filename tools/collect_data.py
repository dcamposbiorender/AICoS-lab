#!/usr/bin/env python3
"""
Collect Data - Basic collection orchestrator for lab-grade testing.

This script runs all available collectors and returns structured JSON output.
For lab-grade implementation, it focuses on basic functionality without
extensive error handling or recovery mechanisms.

Usage:
    python tools/collect_data.py --source=all
    python tools/collect_data.py --source=slack
    python tools/collect_data.py --source=calendar,drive
"""

import argparse
import json
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import all collectors
from src.collectors.slack_collector import SlackCollector
from src.collectors.calendar_collector import CalendarCollector  
from src.collectors.employee_collector import EmployeeCollector
from src.collectors.drive_collector import DriveCollector

# Available collectors mapping
COLLECTORS = {
    'slack': SlackCollector,
    'calendar': CalendarCollector,
    'employee': EmployeeCollector,
    'drive': DriveCollector
}


def run_collector(collector_name: str, collector_class, employees=None, lookback_weeks=26, lookahead_weeks=4) -> Dict[str, Any]:
    """
    Run a single collector and return results.
    
    Args:
        collector_name: Name of the collector
        collector_class: Collector class to instantiate
        employees: List of employee emails for calendar collection (optional)
        lookback_weeks: Number of weeks to look backward for calendar data
        lookahead_weeks: Number of weeks to look forward for calendar data
        
    Returns:
        Dictionary with collector results and status
    """
    print(f"Running {collector_name} collector...")
    
    try:
        # Create collector
        collector = collector_class()
        
        start_time = datetime.now()
        
        # Special handling for calendar collector with parameters
        if collector_name == 'calendar' and (employees or lookback_weeks != 26 or lookahead_weeks != 4):
            print(f"📅 Calendar collection - Employees: {employees or 'all'}, Lookback: {lookback_weeks}w, Lookahead: {lookahead_weeks}w")
            
            if employees:
                # Parse employee list and create email->calendar_id mapping
                employee_list = [e.strip() for e in employees.split(',')]
                employee_dict = {email: email for email in employee_list}
                
                print(f"🎯 Targeting specific employees: {employee_list}")
                result = collector.collect_from_employee_list(
                    employee_emails=employee_dict,
                    days_back=lookback_weeks * 7
                )
            else:
                print(f"📊 Collecting all employee calendars")
                result = collector.collect_all_employee_calendars(
                    weeks_backward=lookback_weeks,
                    weeks_forward=lookahead_weeks
                )
        else:
            # Handle different collector types with their specific methods
            if collector_name == 'slack':
                # SlackCollector uses collect_all_slack_data for comprehensive collection
                result = collector.collect_all_slack_data()
            elif collector_name == 'drive':
                # DriveCollector returns DriveCollectionResult object
                drive_result = collector.collect()
                # Convert to dictionary format expected by the rest of the code
                result = {
                    'data': {
                        'files': [],  # Files are saved to JSONL, not returned in memory
                        'metadata': {}  # Drive metadata stored in JSONL files
                    },
                    'success': len(drive_result.errors) == 0,
                    'message': 'Drive collection completed' if len(drive_result.errors) == 0 else f'Drive collection completed with {len(drive_result.errors)} errors',
                    'stats': {
                        'files_collected': drive_result.files_collected,
                        'changes_tracked': drive_result.changes_tracked,
                        'api_requests': drive_result.api_requests_made,
                        'duration': drive_result.collection_duration,
                        'rate_limit_hits': drive_result.rate_limit_hits
                    }
                }
            else:
                # Default behavior for other collectors (employee, calendar)
                result = collector.collect()
        
        end_time = datetime.now()
        
        duration = (end_time - start_time).total_seconds()
        
        # Extract basic stats
        if collector_name == 'drive':
            # Drive collector has custom stats format already processed
            drive_stats = result.get('stats', {})
            stats = {
                'files': drive_stats.get('files_collected', 0),
                'api_requests': drive_stats.get('api_requests', 0),
                'duration_mins': round(drive_stats.get('duration', 0) / 60, 1)
            }
        else:
            # Standard stats extraction for other collectors
            data = result.get('data', {})
            stats = {
                'messages': len(data.get('messages', [])),
                'channels': len(data.get('channels', [])),
                'users': len(data.get('users', [])),
                'files': len(data.get('files', [])),
                'changes': len(data.get('changes', [])),
                'employees': len(data.get('employees', [])),
            }
        
        # Remove zero counts for cleaner output
        stats = {k: v for k, v in stats.items() if v > 0}
        
        print(f"✅ {collector_name}: {duration:.2f}s - {stats}")
        
        return {
            'status': 'success',
            'collector': collector_name,
            'duration_seconds': duration,
            'collection_stats': stats,
            'data': result,  # Full data for further processing
            'timestamp': start_time.isoformat()
        }
        
    except Exception as e:
        error_msg = str(e)
        print(f"❌ {collector_name}: Failed - {error_msg}")
        
        # Provide actionable error messages
        suggestion = _get_error_suggestion(collector_name, error_msg)
        if suggestion:
            print(f"💡 Suggestion: {suggestion}")
        
        return {
            'status': 'error',
            'collector': collector_name,
            'error': error_msg,
            'suggestion': suggestion,
            'timestamp': datetime.now().isoformat()
        }


def _get_error_suggestion(collector_name: str, error_msg: str) -> str:
    """Get actionable suggestions for common collector errors"""
    
    error_lower = error_msg.lower()
    
    # Slack-specific errors
    if collector_name == 'slack':
        if 'token' in error_lower and ('not found' in error_lower or 'invalid' in error_lower):
            return "Run 'python tools/run_collectors.py check-auth' to verify Slack tokens are configured"
        elif 'invalid_auth' in error_lower or 'authentication' in error_lower:
            return "Slack tokens may be expired or invalid. Check token permissions in Slack app settings"
        elif 'rate_limit' in error_lower or 'too_many_requests' in error_lower:
            return "Slack API rate limit hit. Wait a few minutes and try again, or reduce collection scope"
        elif 'channel_not_found' in error_lower or 'not_in_channel' in error_lower:
            return "Bot may not be added to required channels. Invite the bot to channels you want to collect"
    
    # Google services errors (Drive/Calendar)
    elif collector_name in ['drive', 'calendar']:
        if 'credentials' in error_lower or 'oauth' in error_lower:
            return "Run 'python tools/setup_google_oauth.py' to configure Google authentication"
        elif 'quota' in error_lower or 'rate' in error_lower:
            return "Google API quota exceeded. Wait for quota reset or request quota increase"
        elif 'forbidden' in error_lower or '403' in error_lower:
            return "Permission denied. Ensure Calendar/Drive APIs are enabled in Google Cloud Console"
        elif 'expired' in error_lower:
            return "OAuth tokens expired. Run 'python tools/setup_google_oauth.py' to refresh"
        elif 'calendar_not_found' in error_lower:
            return "Calendar not accessible. Check calendar sharing permissions or specify different calendar"
    
    # Employee collector errors
    elif collector_name == 'employee':
        if 'no data' in error_lower or 'empty' in error_lower:
            return "Employee collector requires data from other collectors. Run Slack, Calendar, or Drive collectors first"
    
    # Generic authentication errors
    if 'authentication' in error_lower or 'unauthorized' in error_lower:
        return f"Authentication failed for {collector_name}. Run 'python tools/run_collectors.py check-auth'"
    
    # Network/connection errors
    if 'connection' in error_lower or 'network' in error_lower or 'timeout' in error_lower:
        return "Network connectivity issue. Check internet connection and try again"
    
    # Permission errors
    if 'permission' in error_lower or 'access' in error_lower:
        return f"File/directory permission issue. Check write permissions for data directory"
    
    # Import/module errors
    if 'import' in error_lower or 'module' in error_lower:
        return "Missing dependencies. Run 'pip install -r requirements.txt' to install required packages"
    
    # Generic fallback
    return f"For detailed troubleshooting, see docs/COLLECTORS_GUIDE.md or run with --verbose flag"


def main():
    """Main orchestrator function."""
    parser = argparse.ArgumentParser(description='AI Chief of Staff Data Collector')
    parser.add_argument(
        '--source',
        default='all',
        help='Data sources to collect: all, slack, calendar, employee, drive, or comma-separated list'
    )
    parser.add_argument(
        '--output',
        default='console',
        choices=['console', 'json'],
        help='Output format: console (human-readable) or json'
    )
    parser.add_argument(
        '--employees',
        help='Comma-separated list of employee emails for calendar collection (e.g., ryan@biorender.com,shiz@biorender.com)'
    )
    parser.add_argument(
        '--lookback-weeks',
        type=int,
        default=26,
        help='Number of weeks to look backward for calendar data (default: 26 = 6 months)'
    )
    parser.add_argument(
        '--lookahead-weeks',
        type=int,
        default=4,
        help='Number of weeks to look forward for calendar data (default: 4 = 1 month)'
    )
    
    args = parser.parse_args()
    
    # Determine which collectors to run
    if args.source == 'all':
        collectors_to_run = list(COLLECTORS.keys())
    else:
        collectors_to_run = [source.strip() for source in args.source.split(',')]
    
    # Validate collector names
    invalid_collectors = [c for c in collectors_to_run if c not in COLLECTORS]
    if invalid_collectors:
        print(f"❌ Invalid collectors: {invalid_collectors}")
        print(f"Available collectors: {list(COLLECTORS.keys())}")
        return 1
    
    print(f"🚀 Starting data collection for: {collectors_to_run}")
    print("=" * 60)
    
    # Run all collectors
    results = []
    for collector_name in collectors_to_run:
        collector_class = COLLECTORS[collector_name]
        result = run_collector(
            collector_name, 
            collector_class,
            employees=args.employees,
            lookback_weeks=args.lookback_weeks,
            lookahead_weeks=args.lookahead_weeks
        )
        results.append(result)
    
    print("=" * 60)
    
    # Generate summary
    successful = [r for r in results if r['status'] == 'success']
    failed = [r for r in results if r['status'] == 'error']
    
    total_duration = sum(r.get('duration_seconds', 0) for r in successful)
    
    summary = {
        'collection_summary': {
            'total_collectors': len(results),
            'successful': len(successful),
            'failed': len(failed),
            'total_duration_seconds': round(total_duration, 2),
            'timestamp': datetime.now().isoformat()
        },
        'results': results
    }
    
    # Output results
    if args.output == 'json':
        print(json.dumps(summary, indent=2))
    else:
        # Human-readable summary
        print(f"📊 Collection Summary:")
        print(f"   Total: {len(results)} collectors")
        print(f"   ✅ Success: {len(successful)}")
        print(f"   ❌ Failed: {len(failed)}")
        print(f"   ⏱️  Total time: {total_duration:.2f}s")
        
        if failed:
            print(f"\n🚨 Failed Collectors:")
            for result in failed:
                print(f"   - {result['collector']}: {result['error']}")
                if result.get('suggestion'):
                    print(f"     💡 {result['suggestion']}")
            
            print(f"\n📋 Quick Help:")
            print(f"   • Check authentication: python tools/run_collectors.py check-auth")
            print(f"   • View detailed guide: docs/COLLECTORS_GUIDE.md")
            print(f"   • Test with verbose output: add --output=console flag")
    
    return 0 if len(failed) == 0 else 1


if __name__ == '__main__':
    # Ensure AICOS_BASE_DIR is set for lab testing
    if not os.getenv('AICOS_BASE_DIR'):
        os.environ['AICOS_BASE_DIR'] = str(Path(__file__).parent.parent)
        print(f"🔧 Setting AICOS_BASE_DIR to: {os.environ['AICOS_BASE_DIR']}")
    
    exit_code = main()
    sys.exit(exit_code)