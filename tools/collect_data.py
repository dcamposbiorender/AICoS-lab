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
from src.collectors.slack_wrapper import SlackArchiveWrapper
from src.collectors.calendar import CalendarArchiveWrapper  
from src.collectors.employee import EmployeeArchiveWrapper
from src.collectors.drive import DriveArchiveWrapper

# Available collectors mapping
COLLECTORS = {
    'slack': SlackArchiveWrapper,
    'calendar': CalendarArchiveWrapper,
    'employee': EmployeeArchiveWrapper,
    'drive': DriveArchiveWrapper
}


def run_collector(collector_name: str, collector_class) -> Dict[str, Any]:
    """
    Run a single collector and return results.
    
    Args:
        collector_name: Name of the collector
        collector_class: Collector class to instantiate
        
    Returns:
        Dictionary with collector results and status
    """
    print(f"Running {collector_name} collector...")
    
    try:
        # Create and run collector
        collector = collector_class()
        
        start_time = datetime.now()
        result = collector.collect()
        end_time = datetime.now()
        
        duration = (end_time - start_time).total_seconds()
        
        # Extract basic stats
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
        print(f"❌ {collector_name}: Failed - {str(e)}")
        return {
            'status': 'error',
            'collector': collector_name,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }


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
        result = run_collector(collector_name, collector_class)
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
    
    return 0 if len(failed) == 0 else 1


if __name__ == '__main__':
    # Ensure AICOS_BASE_DIR is set for lab testing
    if not os.getenv('AICOS_BASE_DIR'):
        os.environ['AICOS_BASE_DIR'] = str(Path(__file__).parent.parent)
        print(f"🔧 Setting AICOS_BASE_DIR to: {os.environ['AICOS_BASE_DIR']}")
    
    exit_code = main()
    sys.exit(exit_code)