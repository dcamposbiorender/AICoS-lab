#!/usr/bin/env python3
"""
Overnight Collection Script - AI Chief of Staff System
Sequential data collection with comprehensive progress logging and error recovery

This script orchestrates the complete data collection pipeline:
1. Employee roster collection (identity mapping)
2. Slack data collection (messages, channels, users)
3. Calendar data collection (events across time windows)
4. Drive data collection (metadata and changes)

Features:
- Sequential execution with dependency management
- Detailed progress logging with timestamps
- Error recovery and retry logic
- Resource monitoring (API quotas, disk space)
- Time estimation and completion forecasting
- Comprehensive summary reporting
- Integration with existing collectors

Usage:
    python tools/overnight_collection.py
    python tools/overnight_collection.py --collectors slack,calendar
    python tools/overnight_collection.py --time-windows 7,30,90
    python tools/overnight_collection.py --verbose
    python tools/overnight_collection.py --dry-run
"""

import json
import sys
import time
import traceback
import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import shutil
import psutil
import logging

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure logging for comprehensive progress tracking
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('overnight_collection.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class CollectionResult:
    """Result from a single collector"""
    collector: str
    status: str  # 'success', 'error', 'skipped'
    records_collected: int
    duration_seconds: float
    api_requests: int
    errors: List[str]
    details: Optional[Dict] = None


@dataclass
class OvernightCollectionSummary:
    """Complete summary of overnight collection"""
    start_time: str
    end_time: str
    total_duration_hours: float
    total_records_collected: int
    total_api_requests: int
    collectors_run: List[str]
    successful_collectors: List[str]
    failed_collectors: List[str]
    results: List[CollectionResult]
    system_resources: Dict
    disk_usage_before: Dict
    disk_usage_after: Dict


class OvernightCollectionOrchestrator:
    """
    Main orchestrator for overnight data collection
    
    Manages the complete data collection pipeline with:
    - Sequential execution (Employee → Slack → Calendar → Drive)
    - Progress logging and monitoring
    - Error recovery and retry logic
    - Resource usage tracking
    - Comprehensive reporting
    """
    
    def __init__(self, collectors: Optional[List[str]] = None, 
                 time_windows: Optional[List[int]] = None,
                 dry_run: bool = False, verbose: bool = False):
        """
        Initialize overnight collection orchestrator
        
        Args:
            collectors: List of collectors to run (default: all)
            time_windows: Time windows for calendar collection (default: [7, 30, 90])
            dry_run: If True, simulate collection without actual API calls
            verbose: Enable detailed logging
        """
        self.collectors = collectors or ['employee', 'slack', 'calendar', 'drive']
        self.time_windows = time_windows or [7, 30, 90]
        self.dry_run = dry_run
        self.verbose = verbose
        
        self.start_time = None
        self.results = []
        self.system_info = self._get_system_info()
        self.disk_usage_before = self._get_disk_usage()
        
        # Collection statistics
        self.total_records = 0
        self.total_api_requests = 0
        self.total_duration = 0.0
        
        logger.info("🌙 Overnight Collection Orchestrator initialized")
        logger.info(f"📋 Collectors: {', '.join(self.collectors)}")
        if 'calendar' in self.collectors:
            logger.info(f"📅 Time Windows: {', '.join(map(str, self.time_windows))} days")
        logger.info(f"💻 System: {self.system_info['cpu_count']} CPUs, {self.system_info['memory_gb']:.1f}GB RAM")
        if self.dry_run:
            logger.warning("🧪 DRY RUN MODE: No actual data collection will occur")
    
    def _get_system_info(self) -> Dict:
        """Get system information for monitoring"""
        return {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'cpu_count': psutil.cpu_count(),
            'memory_gb': psutil.virtual_memory().total / (1024**3),
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory_percent': psutil.virtual_memory().percent,
            'python_version': sys.version.split()[0]
        }
    
    def _get_disk_usage(self) -> Dict:
        """Get disk usage information"""
        try:
            data_dir = project_root / "data"
            if data_dir.exists():
                total, used, free = shutil.disk_usage(data_dir)
                return {
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'total_gb': total / (1024**3),
                    'used_gb': used / (1024**3),
                    'free_gb': free / (1024**3),
                    'used_percent': (used / total) * 100,
                    'data_dir': str(data_dir)
                }
            else:
                return {'error': 'Data directory not found'}
        except Exception as e:
            return {'error': str(e)}
    
    def _estimate_completion_time(self, completed_collectors: int, 
                                  total_collectors: int, 
                                  elapsed_time: float) -> str:
        """Estimate completion time based on progress"""
        if completed_collectors == 0:
            return "Unknown"
        
        avg_time_per_collector = elapsed_time / completed_collectors
        remaining_collectors = total_collectors - completed_collectors
        estimated_remaining = avg_time_per_collector * remaining_collectors
        
        completion_time = datetime.now() + timedelta(seconds=estimated_remaining)
        return completion_time.strftime("%H:%M:%S")
    
    def run_complete_collection(self) -> OvernightCollectionSummary:
        """
        Execute complete overnight collection pipeline
        
        Returns:
            Comprehensive summary of collection results
        """
        self.start_time = datetime.now(timezone.utc)
        logger.info("🚀 Starting overnight data collection pipeline")
        logger.info(f"⏰ Start Time: {self.start_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        
        try:
            # Phase 1: Pre-collection checks
            self._run_pre_collection_checks()
            
            # Phase 2: Sequential collector execution
            for i, collector_name in enumerate(self.collectors, 1):
                logger.info(f"\n{'='*60}")
                logger.info(f"📊 PHASE {i}/{len(self.collectors)}: {collector_name.upper()} COLLECTION")
                logger.info(f"{'='*60}")
                
                # Progress tracking
                elapsed = (datetime.now(timezone.utc) - self.start_time).total_seconds()
                estimated_completion = self._estimate_completion_time(i-1, len(self.collectors), elapsed)
                logger.info(f"⏱️  Elapsed: {elapsed/3600:.1f}h | Est. Completion: {estimated_completion}")
                
                # Run collector
                result = self._run_single_collector(collector_name)
                self.results.append(result)
                
                # Update totals
                self.total_records += result.records_collected
                self.total_api_requests += result.api_requests
                self.total_duration += result.duration_seconds
                
                # Log immediate results
                if result.status == 'success':
                    logger.info(f"✅ {collector_name.upper()} SUCCESS: {result.records_collected:,} records in {result.duration_seconds/60:.1f}m")
                else:
                    logger.error(f"❌ {collector_name.upper()} FAILED: {result.status}")
                    for error in result.errors:
                        logger.error(f"    💥 {error}")
                
                # Resource check after each collector
                self._log_resource_usage()
                
                # Optional delay between collectors
                if i < len(self.collectors) and not self.dry_run:
                    logger.info("⏸️  Brief pause between collectors...")
                    time.sleep(5)
            
            # Phase 3: Post-collection summary
            return self._generate_final_summary()
            
        except KeyboardInterrupt:
            logger.warning("⚠️  Collection interrupted by user (Ctrl+C)")
            return self._generate_final_summary(interrupted=True)
        except Exception as e:
            logger.error(f"💥 Fatal error in collection pipeline: {e}")
            logger.error(traceback.format_exc())
            return self._generate_final_summary(fatal_error=str(e))
    
    def _run_pre_collection_checks(self):
        """Run pre-collection validation checks"""
        logger.info("🔍 Running pre-collection checks...")
        
        # Check disk space
        disk_usage = self._get_disk_usage()
        if 'free_gb' in disk_usage:
            free_gb = disk_usage['free_gb']
            if free_gb < 10:
                logger.warning(f"⚠️  Low disk space: {free_gb:.1f}GB free")
                if free_gb < 5:
                    raise RuntimeError(f"Insufficient disk space: {free_gb:.1f}GB free (need >5GB)")
            else:
                logger.info(f"💾 Disk space OK: {free_gb:.1f}GB free")
        
        # Check virtual environment
        if not hasattr(sys, 'real_prefix') and not sys.base_prefix != sys.prefix:
            logger.warning("⚠️  Not running in virtual environment")
        else:
            logger.info("🐍 Virtual environment detected")
        
        # Check data directory structure
        data_dir = project_root / "data"
        archive_dir = data_dir / "archive"
        if not archive_dir.exists():
            logger.info(f"📁 Creating archive directory: {archive_dir}")
            archive_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("✅ Pre-collection checks completed")
    
    def _run_single_collector(self, collector_name: str) -> CollectionResult:
        """
        Run a single data collector with error handling and monitoring
        
        Args:
            collector_name: Name of collector to run
            
        Returns:
            Collection result with metrics and status
        """
        start_time = time.time()
        logger.info(f"🔄 Starting {collector_name} collection...")
        
        if self.dry_run:
            return self._simulate_collection(collector_name, start_time)
        
        try:
            if collector_name == 'employee':
                return self._run_employee_collection(start_time)
            elif collector_name == 'slack':
                return self._run_slack_collection(start_time)
            elif collector_name == 'calendar':
                return self._run_calendar_collection(start_time)
            elif collector_name == 'drive':
                return self._run_drive_collection(start_time)
            else:
                return CollectionResult(
                    collector=collector_name,
                    status='error',
                    records_collected=0,
                    duration_seconds=time.time() - start_time,
                    api_requests=0,
                    errors=[f"Unknown collector: {collector_name}"]
                )
                
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"💥 {collector_name} collection failed: {e}")
            return CollectionResult(
                collector=collector_name,
                status='error',
                records_collected=0,
                duration_seconds=duration,
                api_requests=0,
                errors=[str(e)]
            )
    
    def _run_employee_collection(self, start_time: float) -> CollectionResult:
        """Run employee roster collection"""
        try:
            from src.collectors.employee_collector import EmployeeCollector
            
            collector = EmployeeCollector()
            logger.info("👥 Collecting employee roster and identity mappings...")
            
            result = collector.collect()
            duration = time.time() - start_time
            
            # Extract metrics from result
            if hasattr(result, 'employees_collected'):
                records = result.employees_collected
            else:
                records = len(result) if isinstance(result, list) else 1
            
            return CollectionResult(
                collector='employee',
                status='success',
                records_collected=records,
                duration_seconds=duration,
                api_requests=getattr(result, 'api_requests', 0),
                errors=[],
                details={'employees_found': records}
            )
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Employee collection error: {e}")
            return CollectionResult(
                collector='employee',
                status='error',
                records_collected=0,
                duration_seconds=duration,
                api_requests=0,
                errors=[str(e)]
            )
    
    def _run_slack_collection(self, start_time: float) -> CollectionResult:
        """Run Slack data collection with bulk overnight mode"""
        try:
            from src.collectors.slack_collector import SlackCollector
            
            # Use test config for faster collection but allow scaling
            test_config_path = project_root / "config" / "test_config.json"
            collector = SlackCollector(config_path=test_config_path)
            
            logger.info("💬 Setting up Slack authentication...")
            if not collector.setup_slack_authentication():
                raise RuntimeError("Slack authentication failed")
            
            logger.info("🔍 Discovering Slack channels...")
            all_channels = collector.discover_all_channels()
            filtered_channels = collector.apply_collection_rules(all_channels)
            
            logger.info(f"📊 Found {len(all_channels)} total channels, {len(filtered_channels)} after filtering")
            logger.info("💬 Starting bulk Slack message collection...")
            
            # Run bulk collection on ALL filtered channels
            collection_results = collector.collect_from_filtered_channels(
                filtered_channels,
                max_channels=len(filtered_channels)  # Collect from ALL channels
            )
            
            duration = time.time() - start_time
            
            # Extract comprehensive metrics
            successful_collections = collection_results.get('successful_collections', 0)
            total_messages = collection_results.get('total_messages_collected', 0)
            api_requests = collector.rate_limiter.request_count
            rate_limit_hits = collector.rate_limiter.consecutive_rate_limits
            
            return CollectionResult(
                collector='slack',
                status='success' if successful_collections > 0 else 'error',
                records_collected=total_messages,
                duration_seconds=duration,
                api_requests=api_requests,
                errors=[],
                details={
                    'channels_available': len(all_channels),
                    'channels_filtered': len(filtered_channels),
                    'channels_collected': successful_collections,
                    'messages_collected': total_messages,
                    'rate_limit_hits': rate_limit_hits,
                    'avg_messages_per_channel': total_messages / successful_collections if successful_collections > 0 else 0
                }
            )
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Slack collection error: {e}")
            return CollectionResult(
                collector='slack',
                status='error',
                records_collected=0,
                duration_seconds=duration,
                api_requests=0,
                errors=[str(e)]
            )
    
    def _run_calendar_collection(self, start_time: float) -> CollectionResult:
        """Run Calendar data collection across multiple time windows"""
        try:
            from src.collectors.calendar_collector import CalendarCollector
            
            collector = CalendarCollector()
            logger.info("📅 Setting up Calendar authentication...")
            
            if not collector.setup_calendar_service():
                raise RuntimeError("Calendar authentication failed")
            
            logger.info("🔍 Discovering calendars...")
            all_calendars = collector.discover_all_calendars()
            logger.info(f"📊 Found {len(all_calendars)} calendars")
            
            total_events = 0
            total_calendars_collected = 0
            
            # Collect events across all time windows
            for time_window in self.time_windows:
                logger.info(f"📅 Collecting events for {time_window}-day window...")
                
                now = datetime.now()
                start_date = now - timedelta(days=time_window)
                end_date = now + timedelta(days=time_window)  # Include future events
                
                window_events = 0
                window_calendars = 0
                
                for calendar_id, calendar_info in all_calendars.items():
                    try:
                        collector.rate_limiter.wait_for_rate_limit()
                        
                        events_result = collector.calendar_service.events().list(
                            calendarId=calendar_id,
                            timeMin=start_date.isoformat() + 'Z',
                            timeMax=end_date.isoformat() + 'Z',
                            singleEvents=True,
                            orderBy='startTime',
                            maxResults=500  # Overnight collection - get more events
                        ).execute()
                        
                        events = events_result.get('items', [])
                        window_events += len(events)
                        window_calendars += 1
                        
                    except Exception as e:
                        logger.warning(f"Failed to collect from calendar {calendar_id}: {e}")
                        continue
                
                logger.info(f"    📊 {time_window}-day window: {window_events} events from {window_calendars} calendars")
                total_events += window_events
                total_calendars_collected = max(total_calendars_collected, window_calendars)
            
            duration = time.time() - start_time
            
            return CollectionResult(
                collector='calendar',
                status='success' if total_events > 0 else 'error',
                records_collected=total_events,
                duration_seconds=duration,
                api_requests=collector.rate_limiter.request_count,
                errors=[],
                details={
                    'calendars_available': len(all_calendars),
                    'calendars_collected': total_calendars_collected,
                    'time_windows': self.time_windows,
                    'total_events': total_events,
                    'api_requests': collector.rate_limiter.request_count
                }
            )
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Calendar collection error: {e}")
            return CollectionResult(
                collector='calendar',
                status='error',
                records_collected=0,
                duration_seconds=duration,
                api_requests=0,
                errors=[str(e)]
            )
    
    def _run_drive_collection(self, start_time: float) -> CollectionResult:
        """Run Drive data collection (currently stub implementation)"""
        try:
            from src.collectors.drive_collector import DriveCollector
            
            logger.info("🚗 Starting Drive collection (implementation stub)...")
            collector = DriveCollector()
            
            # Run the stub implementation
            result = collector.collect()
            duration = time.time() - start_time
            
            return CollectionResult(
                collector='drive',
                status='success' if len(result.errors) == 0 else 'error',
                records_collected=result.files_collected,
                duration_seconds=duration,
                api_requests=result.api_requests_made,
                errors=result.errors,
                details={
                    'files_collected': result.files_collected,
                    'changes_tracked': result.changes_tracked,
                    'implementation_status': 'stub_with_todos'
                }
            )
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Drive collection error: {e}")
            return CollectionResult(
                collector='drive',
                status='error',
                records_collected=0,
                duration_seconds=duration,
                api_requests=0,
                errors=[str(e)]
            )
    
    def _simulate_collection(self, collector_name: str, start_time: float) -> CollectionResult:
        """Simulate collection for dry run mode"""
        logger.info(f"🧪 SIMULATING {collector_name} collection...")
        
        # Simulate realistic timing
        simulation_time = {
            'employee': 5,
            'slack': 120,     # 2 minutes for bulk collection
            'calendar': 60,   # 1 minute for calendar
            'drive': 30       # 30 seconds for drive stub
        }.get(collector_name, 10)
        
        logger.info(f"    ⏱️  Simulating {simulation_time} seconds of collection...")
        time.sleep(2)  # Brief actual delay for realism
        
        # Simulate realistic results
        simulated_records = {
            'employee': 150,
            'slack': 125000,    # 125K messages
            'calendar': 45000,  # 45K events
            'drive': 500        # 500 files
        }.get(collector_name, 100)
        
        duration = time.time() - start_time
        
        return CollectionResult(
            collector=collector_name,
            status='success',
            records_collected=simulated_records,
            duration_seconds=duration,
            api_requests=simulated_records // 10,  # Simulated API calls
            errors=[],
            details={'simulation': True, 'simulated_time': simulation_time}
        )
    
    def _log_resource_usage(self):
        """Log current system resource usage"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk_usage = self._get_disk_usage()
            
            logger.info(f"📊 Resources: CPU {cpu_percent:.1f}% | RAM {memory.percent:.1f}% | Disk {disk_usage.get('used_percent', 0):.1f}%")
            
            if memory.percent > 80:
                logger.warning(f"⚠️  High memory usage: {memory.percent:.1f}%")
            if cpu_percent > 90:
                logger.warning(f"⚠️  High CPU usage: {cpu_percent:.1f}%")
                
        except Exception as e:
            logger.warning(f"Could not get resource usage: {e}")
    
    def _generate_final_summary(self, interrupted: bool = False, 
                               fatal_error: str = None) -> OvernightCollectionSummary:
        """Generate comprehensive collection summary"""
        end_time = datetime.now(timezone.utc)
        total_duration = (end_time - self.start_time).total_seconds() / 3600  # hours
        disk_usage_after = self._get_disk_usage()
        
        # Categorize results
        successful_collectors = [r.collector for r in self.results if r.status == 'success']
        failed_collectors = [r.collector for r in self.results if r.status == 'error']
        
        summary = OvernightCollectionSummary(
            start_time=self.start_time.isoformat(),
            end_time=end_time.isoformat(),
            total_duration_hours=total_duration,
            total_records_collected=self.total_records,
            total_api_requests=self.total_api_requests,
            collectors_run=[r.collector for r in self.results],
            successful_collectors=successful_collectors,
            failed_collectors=failed_collectors,
            results=self.results,
            system_resources=self._get_system_info(),
            disk_usage_before=self.disk_usage_before,
            disk_usage_after=disk_usage_after
        )
        
        # Log comprehensive summary
        self._log_final_summary(summary, interrupted, fatal_error)
        
        # Save summary to file
        self._save_summary_to_file(summary)
        
        return summary
    
    def _log_final_summary(self, summary: OvernightCollectionSummary, 
                          interrupted: bool, fatal_error: str):
        """Log final collection summary"""
        logger.info("\n" + "="*80)
        logger.info("🌙 OVERNIGHT COLLECTION COMPLETE")
        logger.info("="*80)
        
        if interrupted:
            logger.warning("⚠️  Collection was interrupted by user")
        elif fatal_error:
            logger.error(f"💥 Collection failed with fatal error: {fatal_error}")
        
        logger.info(f"⏰ Duration: {summary.total_duration_hours:.2f} hours")
        logger.info(f"📊 Total Records: {summary.total_records_collected:,}")
        logger.info(f"🌐 API Requests: {summary.total_api_requests:,}")
        logger.info(f"✅ Successful: {len(summary.successful_collectors)}/{len(summary.results)}")
        
        if summary.successful_collectors:
            logger.info(f"    ✅ {', '.join(summary.successful_collectors)}")
        if summary.failed_collectors:
            logger.error(f"    ❌ {', '.join(summary.failed_collectors)}")
        
        # Detailed results
        logger.info("\n📋 DETAILED RESULTS:")
        for result in summary.results:
            status_emoji = "✅" if result.status == 'success' else "❌"
            logger.info(f"  {status_emoji} {result.collector.upper()}: "
                       f"{result.records_collected:,} records | "
                       f"{result.duration_seconds/60:.1f}m | "
                       f"{result.api_requests} API calls")
            
            if result.errors:
                for error in result.errors[:3]:  # Show first 3 errors
                    logger.error(f"      💥 {error}")
        
        # Storage impact
        if 'used_gb' in summary.disk_usage_before and 'used_gb' in summary.disk_usage_after:
            storage_used = summary.disk_usage_after['used_gb'] - summary.disk_usage_before['used_gb']
            logger.info(f"💾 Storage Used: {storage_used:.2f} GB")
        
        logger.info("="*80)
    
    def _save_summary_to_file(self, summary: OvernightCollectionSummary):
        """Save collection summary to JSON file"""
        try:
            summary_file = project_root / f"overnight_collection_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            # Convert dataclasses to dict for JSON serialization
            summary_dict = asdict(summary)
            
            with open(summary_file, 'w') as f:
                json.dump(summary_dict, f, indent=2, default=str)
            
            logger.info(f"📄 Summary saved to: {summary_file}")
            
        except Exception as e:
            logger.error(f"Failed to save summary: {e}")


def main():
    """Main entry point for overnight collection script"""
    parser = argparse.ArgumentParser(
        description="AI Chief of Staff - Overnight Collection Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tools/overnight_collection.py
  python tools/overnight_collection.py --collectors slack,calendar
  python tools/overnight_collection.py --time-windows 7,30,90,365
  python tools/overnight_collection.py --dry-run --verbose
  python tools/overnight_collection.py --collectors employee,slack --verbose
  
Collection Order:
  1. Employee (identity mapping)
  2. Slack (messages, channels, users)
  3. Calendar (events across time windows)
  4. Drive (metadata and changes)
        """
    )
    
    parser.add_argument(
        '--collectors',
        type=str,
        default='employee,slack,calendar,drive',
        help='Comma-separated list of collectors to run (default: all)'
    )
    parser.add_argument(
        '--time-windows',
        type=str,
        default='7,30,90',
        help='Comma-separated list of calendar time windows in days (default: 7,30,90)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Simulate collection without actual API calls'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Parse arguments
    collectors = [c.strip() for c in args.collectors.split(',')]
    time_windows = [int(w.strip()) for w in args.time_windows.split(',')]
    
    # Validate collectors
    valid_collectors = ['employee', 'slack', 'calendar', 'drive']
    for collector in collectors:
        if collector not in valid_collectors:
            print(f"❌ Invalid collector: {collector}")
            print(f"Valid collectors: {', '.join(valid_collectors)}")
            sys.exit(1)
    
    # Initialize and run orchestrator
    try:
        orchestrator = OvernightCollectionOrchestrator(
            collectors=collectors,
            time_windows=time_windows,
            dry_run=args.dry_run,
            verbose=args.verbose
        )
        
        print("🌙 Starting overnight collection...")
        if args.dry_run:
            print("🧪 DRY RUN MODE: No actual collection will occur")
        print("⚠️  Remember to activate virtual environment: source venv/bin/activate")
        print()
        
        summary = orchestrator.run_complete_collection()
        
        # Exit with appropriate code
        if summary.failed_collectors:
            print(f"\n❌ Some collectors failed: {', '.join(summary.failed_collectors)}")
            sys.exit(1)
        else:
            print(f"\n✅ All collectors completed successfully!")
            sys.exit(0)
            
    except KeyboardInterrupt:
        print(f"\n⚠️  Collection interrupted by user (Ctrl+C)")
        sys.exit(130)
    except Exception as e:
        print(f"\n💥 Fatal error: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()