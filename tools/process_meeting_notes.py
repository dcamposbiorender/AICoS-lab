#!/usr/bin/env python3
"""
Meeting Notes Processor CLI Tool - Enhanced with Full Pipeline Orchestration
Command-line interface for complete meeting notes processing workflow

This tool provides both legacy email-only processing and new 4-phase pipeline
orchestration combining email processing, Google Docs extraction, correlation, and output generation.

Usage:
    # NEW: Full 4-phase pipeline orchestration (RECOMMENDED)
    python3 tools/process_meeting_notes.py --directory "/Users/user/Downloads" --orchestrate
    
    # Legacy: Process single email file
    python3 tools/process_meeting_notes.py --file "path/to/Notes_Meeting.eml"
    
    # Legacy: Process all email files in directory  
    python3 tools/process_meeting_notes.py --directory "/Users/user/Downloads"
    
    # Pipeline with custom correlation strategy
    python3 tools/process_meeting_notes.py --directory "/path" --orchestrate --strategy composite
    
    # Dry run to preview what would be processed
    python3 tools/process_meeting_notes.py --directory "/path" --dry-run
    
    # Interactive mode with detailed output
    python3 tools/process_meeting_notes.py --interactive
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

try:
    from collectors.email_collector import EmailCollector, ParsedEmail
    from queries.structured import StructuredExtractor, PatternType
    from core.config import get_config
    
    # NEW: Import orchestration pipeline components
    from orchestrators.meeting_pipeline import MeetingPipeline, PipelineStatus
    from correlators.meeting_correlator import CorrelationStrategy
    ORCHESTRATION_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Some modules not available: {e}")
    print("Running in legacy mode (email processing only)")
    ORCHESTRATION_AVAILABLE = False


class MeetingNotesProcessor:
    """
    Main processor for meeting notes workflow
    Orchestrates email parsing, content extraction, and reporting
    """
    
    def __init__(self, verbose: bool = False):
        """
        Initialize processor
        
        Args:
            verbose: Enable verbose logging
        """
        self.verbose = verbose
        self.setup_logging()
        
        # Initialize components
        self.email_collector = EmailCollector()
        self.structured_extractor = StructuredExtractor()
        
        # Processing statistics
        self.stats = {
            'files_processed': 0,
            'emails_parsed': 0,
            'action_items_found': 0,
            'todos_found': 0,
            'deadlines_found': 0,
            'participants_identified': 0,
            'start_time': None,
            'end_time': None
        }
        
        self.logger = logging.getLogger(__name__)
    
    def setup_logging(self):
        """Setup logging configuration"""
        log_level = logging.DEBUG if self.verbose else logging.INFO
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout)
            ]
        )
    
    def process_single_file(self, file_path: str, dry_run: bool = False) -> Dict[str, Any]:
        """
        Process a single .eml file
        
        Args:
            file_path: Path to .eml file
            dry_run: If True, only analyze without saving
            
        Returns:
            Processing results dictionary
        """
        self.logger.info(f"Processing file: {file_path}")
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if not file_path.lower().endswith('.eml'):
            raise ValueError(f"File must be .eml format: {file_path}")
        
        try:
            # Parse email
            parsed_email = self.email_collector.parse_eml_file(file_path)
            if not parsed_email:
                return {'success': False, 'error': 'Failed to parse email'}
            
            # Extract structured content
            extracted_data = self._extract_meeting_content(parsed_email)
            
            # Create result
            result = {
                'success': True,
                'file_path': file_path,
                'meeting_title': parsed_email.meeting_title,
                'meeting_date': parsed_email.meeting_date.isoformat() if parsed_email.meeting_date else None,
                'participants': parsed_email.participants,
                'confidence_score': parsed_email.confidence_score,
                'extracted_content': extracted_data,
                'dry_run': dry_run
            }
            
            # Update statistics
            self.stats['files_processed'] += 1
            self.stats['emails_parsed'] += 1
            self.stats['action_items_found'] += len(extracted_data.get('action_items', []))
            self.stats['todos_found'] += len(extracted_data.get('todos', []))
            self.stats['deadlines_found'] += len(extracted_data.get('deadlines', []))
            self.stats['participants_identified'] += len(parsed_email.participants)
            
            if not dry_run:
                self.logger.info(f"Successfully processed: {parsed_email.meeting_title}")
            else:
                self.logger.info(f"DRY RUN - Would process: {parsed_email.meeting_title}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error processing {file_path}: {e}")
            return {'success': False, 'error': str(e), 'file_path': file_path}
    
    def process_directory(self, directory: str, dry_run: bool = False) -> Dict[str, Any]:
        """
        Process all meeting notes .eml files in directory
        
        Args:
            directory: Directory path to scan
            dry_run: If True, only analyze without saving
            
        Returns:
            Batch processing results
        """
        self.logger.info(f"Scanning directory: {directory}")
        
        if not os.path.exists(directory):
            raise FileNotFoundError(f"Directory not found: {directory}")
        
        # Find meeting notes files
        email_files = self.email_collector.detect_meeting_notes_emails(directory)
        
        if not email_files:
            self.logger.warning(f"No meeting notes files found in {directory}")
            return {'success': True, 'files_processed': 0, 'results': []}
        
        self.logger.info(f"Found {len(email_files)} meeting notes files")
        
        # Process each file
        results = []
        for file_path in email_files:
            try:
                result = self.process_single_file(file_path, dry_run=dry_run)
                results.append(result)
            except Exception as e:
                self.logger.error(f"Failed to process {file_path}: {e}")
                results.append({
                    'success': False, 
                    'error': str(e), 
                    'file_path': file_path
                })
        
        # Create summary
        successful_results = [r for r in results if r.get('success')]
        failed_results = [r for r in results if not r.get('success')]
        
        summary = {
            'success': True,
            'directory': directory,
            'files_found': len(email_files),
            'files_processed': len(results),
            'successful_parses': len(successful_results),
            'failed_parses': len(failed_results),
            'results': results,
            'statistics': self.stats.copy(),
            'dry_run': dry_run
        }
        
        self.logger.info(f"Directory processing complete: {len(successful_results)}/{len(results)} successful")
        
        return summary
    
    def _extract_meeting_content(self, parsed_email: ParsedEmail) -> Dict[str, Any]:
        """
        Extract structured content from parsed email using StructuredExtractor
        
        Args:
            parsed_email: ParsedEmail object
            
        Returns:
            Dictionary with extracted structured content
        """
        content = parsed_email.content
        
        # Extract all patterns
        all_patterns = self.structured_extractor.extract_all_patterns(content)
        
        # Extract specific actionable items
        actionable_items = []
        
        # Get TODOs
        todos = self.structured_extractor.extract_todos(content)
        for todo in todos:
            actionable_items.append({
                'type': 'todo',
                'text': todo['text'],
                'position': todo['position'],
                'assignee': None
            })
        
        # Get deadlines  
        deadlines = self.structured_extractor.extract_deadlines(content)
        for deadline in deadlines:
            actionable_items.append({
                'type': 'deadline',
                'text': deadline['deadline'],
                'position': deadline['position'],
                'assignee': None
            })
        
        # Get action items
        actions = self.structured_extractor.extract_action_items(content)
        for action in actions:
            actionable_items.append({
                'type': 'action',
                'text': action['action'],
                'position': action['position'],
                'assignee': action['assignee'],
                'due': action.get('due')
            })
        
        # Extract mentions and participants
        mentions = self.structured_extractor.extract_mentions(content)
        
        # Extract URLs for document references
        urls = self.structured_extractor.extract_urls(content)
        
        return {
            'action_items': actions,
            'todos': todos,
            'deadlines': deadlines,
            'mentions': mentions,
            'urls': urls,
            'actionable_items': actionable_items,
            'all_patterns': {k.value: v for k, v in all_patterns.items()}
        }
    
    def interactive_mode(self):
        """Run in interactive mode for step-by-step processing"""
        print("🎯 Meeting Notes Processor - Interactive Mode")
        print("=" * 60)
        
        while True:
            print("\nOptions:")
            print("1. Process single file")
            print("2. Process directory")
            print("3. View statistics")
            print("4. Exit")
            
            try:
                choice = input("\nSelect option (1-4): ").strip()
                
                if choice == '1':
                    self._interactive_single_file()
                elif choice == '2':
                    self._interactive_directory()
                elif choice == '3':
                    self._display_statistics()
                elif choice == '4':
                    print("Goodbye!")
                    break
                else:
                    print("Invalid option. Please select 1-4.")
                    
            except KeyboardInterrupt:
                print("\n\nExiting...")
                break
            except Exception as e:
                print(f"Error: {e}")
    
    def _interactive_single_file(self):
        """Interactive single file processing"""
        file_path = input("Enter path to .eml file: ").strip()
        if not file_path:
            print("No file path provided")
            return
        
        dry_run = input("Dry run? (y/N): ").strip().lower() == 'y'
        
        try:
            result = self.process_single_file(file_path, dry_run=dry_run)
            self._display_result(result)
        except Exception as e:
            print(f"Error: {e}")
    
    def _interactive_directory(self):
        """Interactive directory processing"""
        directory = input("Enter directory path (or Enter for ~/Downloads): ").strip()
        if not directory:
            directory = os.path.expanduser("~/Downloads")
        
        dry_run = input("Dry run? (y/N): ").strip().lower() == 'y'
        
        try:
            results = self.process_directory(directory, dry_run=dry_run)
            self._display_batch_results(results)
        except Exception as e:
            print(f"Error: {e}")
    
    def _display_result(self, result: Dict[str, Any]):
        """Display single file processing result"""
        print("\n" + "="*60)
        if result.get('success'):
            print(f"✅ Successfully processed: {os.path.basename(result['file_path'])}")
            print(f"📝 Meeting: {result['meeting_title']}")
            print(f"📅 Date: {result['meeting_date'] or 'Not detected'}")
            print(f"👥 Participants: {', '.join(result['participants'])}")
            print(f"🎯 Confidence: {result['confidence_score']:.2f}")
            
            extracted = result['extracted_content']
            print(f"\n📋 Extracted Content:")
            print(f"  • Action Items: {len(extracted['action_items'])}")
            print(f"  • TODOs: {len(extracted['todos'])}")
            print(f"  • Deadlines: {len(extracted['deadlines'])}")
            print(f"  • Mentions: {len(extracted['mentions'])}")
            
            # Show action items
            if extracted['action_items']:
                print(f"\n🎯 Action Items Found:")
                for i, action in enumerate(extracted['action_items'][:3], 1):
                    assignee = action['assignee']
                    action_text = action['action']
                    print(f"  {i}. {assignee} will {action_text}")
                    
                if len(extracted['action_items']) > 3:
                    print(f"  ... and {len(extracted['action_items']) - 3} more")
        else:
            print(f"❌ Failed to process: {result['file_path']}")
            print(f"Error: {result['error']}")
    
    def _display_batch_results(self, results: Dict[str, Any]):
        """Display batch processing results"""
        print("\n" + "="*60)
        print(f"📁 Directory: {results['directory']}")
        print(f"📊 Results: {results['successful_parses']}/{results['files_processed']} successful")
        
        if results['successful_parses'] > 0:
            print(f"\n✅ Successfully processed files:")
            for result in results['results']:
                if result.get('success'):
                    filename = os.path.basename(result['file_path'])
                    title = result['meeting_title']
                    actions = len(result['extracted_content']['action_items'])
                    print(f"  • {filename}: '{title}' ({actions} action items)")
        
        if results['failed_parses'] > 0:
            print(f"\n❌ Failed files:")
            for result in results['results']:
                if not result.get('success'):
                    filename = os.path.basename(result['file_path'])
                    error = result['error']
                    print(f"  • {filename}: {error}")
    
    def _display_statistics(self):
        """Display processing statistics"""
        print("\n📊 Processing Statistics")
        print("="*40)
        for key, value in self.stats.items():
            if key.endswith('_time') and value:
                if isinstance(value, datetime):
                    print(f"{key.replace('_', ' ').title()}: {value.strftime('%Y-%m-%d %H:%M:%S')}")
            else:
                print(f"{key.replace('_', ' ').title()}: {value}")
    
    def run_orchestration_pipeline(self, directory: str, strategy: str = "composite", 
                                 min_confidence: float = 0.6, output_dir: Optional[str] = None) -> Dict[str, Any]:
        """
        Run the full 4-phase orchestration pipeline (NEW)
        
        Args:
            directory: Directory containing meeting notes files
            strategy: Correlation strategy (temporal_first, participant_first, content_first, composite, adaptive)  
            min_confidence: Minimum correlation confidence threshold
            output_dir: Output directory for results
            
        Returns:
            Pipeline results dictionary
        """
        if not ORCHESTRATION_AVAILABLE:
            raise RuntimeError("Orchestration pipeline not available. Please ensure all dependencies are installed.")
        
        print("🚀 Starting Meeting Notes Orchestration Pipeline")
        print("=" * 60)
        
        # Map string to enum
        strategy_map = {
            'temporal_first': CorrelationStrategy.TEMPORAL_FIRST,
            'participant_first': CorrelationStrategy.PARTICIPANT_FIRST,
            'content_first': CorrelationStrategy.CONTENT_FIRST,
            'composite': CorrelationStrategy.COMPOSITE,
            'adaptive': CorrelationStrategy.ADAPTIVE
        }
        
        correlation_strategy = strategy_map.get(strategy.lower(), CorrelationStrategy.COMPOSITE)
        
        # Initialize pipeline
        pipeline = MeetingPipeline(
            correlation_strategy=correlation_strategy,
            min_correlation_confidence=min_confidence,
            output_directory=output_dir
        )
        
        # Execute pipeline
        start_time = datetime.now()
        self.stats['start_time'] = start_time
        
        try:
            results = pipeline.process_directory(directory)
            
            self.stats['end_time'] = datetime.now()
            
            # Display results
            self._display_pipeline_results(results)
            
            return {
                'success': True,
                'pipeline_results': results,
                'output_files': results.output_files,
                'summary': results.get_summary(),
                'processing_time': results.total_duration
            }
            
        except Exception as e:
            self.stats['end_time'] = datetime.now()
            error_msg = f"Pipeline execution failed: {e}"
            self.logger.error(error_msg)
            
            return {
                'success': False,
                'error': error_msg,
                'pipeline_results': None
            }
    
    def _display_pipeline_results(self, results):
        """Display orchestration pipeline results"""
        print("\n" + "="*80)
        print("🎯 PIPELINE EXECUTION COMPLETE")
        print("="*80)
        
        # Overall summary
        summary = results.get_summary()
        status_emoji = {
            'completed_success': '✅',
            'completed_with_errors': '⚠️',
            'failed': '❌',
            'in_progress': '🔄'
        }.get(summary['status'], '❓')
        
        print(f"\n📊 Overall Results:")
        print(f"  {status_emoji} Status: {summary['status'].replace('_', ' ').title()}")
        print(f"  ⏱️  Duration: {summary['duration']:.1f}s")
        print(f"  📧 Emails Found: {summary['files_processed']['emails']}")
        print(f"  📄 Google Docs Found: {summary['files_processed']['docs']}")
        print(f"  🔗 Successful Correlations: {summary['files_processed']['correlations']}")
        print(f"  🏷️  Orphaned Records: {summary['files_processed']['orphaned']}")
        print(f"  🎯 Action Items Extracted: {summary['action_items']}")
        
        # Phase breakdown
        print(f"\n📋 Phase Results:")
        for phase_result in results.phase_results:
            phase_name = phase_result.phase.value.replace('_', ' ').title()
            status_emoji = '✅' if phase_result.status.value.startswith('completed') else '❌'
            
            print(f"  {status_emoji} {phase_name}: {phase_result.records_processed} records "
                  f"({phase_result.duration:.1f}s)")
            
            if phase_result.errors:
                for error in phase_result.errors[:2]:  # Show first 2 errors
                    print(f"      ⚠️ {error}")
        
        # Output files
        if results.output_files:
            print(f"\n📁 Generated Output Files:")
            for output_file in results.output_files:
                file_name = os.path.basename(output_file)
                print(f"  📄 {file_name}")
                print(f"      {output_file}")
        
        # Correlation details
        if hasattr(results, 'phase_results') and len(results.phase_results) > 2:
            correlation_phase = results.phase_results[2]  # Phase 3 is correlation
            if correlation_phase.data and hasattr(correlation_phase.data, 'correlated_meetings'):
                meetings = correlation_phase.data.correlated_meetings
                
                if meetings:
                    print(f"\n🤝 Sample Correlations:")
                    for i, meeting in enumerate(meetings[:3], 1):  # Show first 3
                        match_type = meeting.correlation_match.match_type.value
                        confidence = meeting.correlation_match.confidence_score
                        
                        print(f"  {i}. {meeting.meeting_title}")
                        print(f"     🎯 Confidence: {confidence:.2f} ({match_type})")
                        print(f"     👥 Participants: {', '.join(meeting.participants[:3])}")
                        print(f"     📝 Action Items: {len(meeting.action_items)}")
        
        print(f"\n🎉 Pipeline execution completed successfully!")
        print("="*80)


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Process meeting notes .eml files and extract action items",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # NEW: Full 4-phase orchestration pipeline (RECOMMENDED)
  %(prog)s --directory "/Users/user/Downloads" --orchestrate
  
  # Pipeline with specific correlation strategy  
  %(prog)s --directory "/Users/user/Downloads" --orchestrate --strategy composite
  
  # Legacy: Process single email file
  %(prog)s --file "/Users/user/Downloads/Notes_Meeting.eml"
  
  # Legacy: Process all email files in Downloads directory
  %(prog)s --directory "/Users/user/Downloads"
  
  # Dry run to preview processing
  %(prog)s --directory "/Users/user/Downloads" --dry-run
  
  # Interactive mode
  %(prog)s --interactive
  
  # Verbose output for debugging
  %(prog)s --file "meeting.eml" --verbose
        """
    )
    
    parser.add_argument('--file', '-f', 
                       help='Process single .eml file')
    parser.add_argument('--directory', '-d', 
                       help='Process all .eml files in directory (legacy) or directory for orchestration pipeline')
    parser.add_argument('--interactive', '-i', action='store_true',
                       help='Run in interactive mode')
    parser.add_argument('--dry-run', action='store_true',
                       help='Preview processing without saving')
    parser.add_argument('--output', '-o',
                       help='Output file for results (JSON format)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    
    # NEW: Orchestration pipeline arguments
    parser.add_argument('--orchestrate', action='store_true',
                       help='Run full 4-phase orchestration pipeline (email + docs + correlation + output)')
    parser.add_argument('--strategy', choices=['temporal_first', 'participant_first', 'content_first', 'composite', 'adaptive'],
                       default='composite', help='Correlation strategy for orchestration pipeline (default: composite)')
    parser.add_argument('--min-confidence', type=float, default=0.6,
                       help='Minimum correlation confidence threshold (default: 0.6)')
    parser.add_argument('--output-dir', 
                       help='Output directory for orchestration pipeline results')
    
    args = parser.parse_args()
    
    # Validate arguments
    if not any([args.file, args.directory, args.interactive]):
        parser.error("Must specify --file, --directory, or --interactive")
    
    if args.file and args.directory:
        parser.error("Cannot specify both --file and --directory")
    
    if args.orchestrate and not args.directory:
        parser.error("--orchestrate requires --directory")
    
    if args.orchestrate and not ORCHESTRATION_AVAILABLE:
        parser.error("Orchestration pipeline not available. Please install dependencies.")
    
    try:
        # Initialize processor
        processor = MeetingNotesProcessor(verbose=args.verbose)
        processor.stats['start_time'] = datetime.now()
        
        results = None
        
        if args.interactive:
            processor.interactive_mode()
        elif args.file:
            results = processor.process_single_file(args.file, dry_run=args.dry_run)
            processor._display_result(results)
        elif args.directory and args.orchestrate:
            # NEW: Run full orchestration pipeline
            results = processor.run_orchestration_pipeline(
                directory=args.directory,
                strategy=args.strategy,
                min_confidence=args.min_confidence,
                output_dir=args.output_dir
            )
        elif args.directory:
            # Legacy: Email-only processing
            results = processor.process_directory(args.directory, dry_run=args.dry_run)
            processor._display_batch_results(results)
        
        processor.stats['end_time'] = datetime.now()
        
        # Save output file if requested
        if args.output and results:
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            print(f"\n💾 Results saved to: {args.output}")
        
        # Display final statistics
        if not args.interactive and not args.orchestrate:
            processor._display_statistics()
        
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()