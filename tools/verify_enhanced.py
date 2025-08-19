#!/usr/bin/env python3
"""
Enhanced Archive Verification CLI
Uses the new ArchiveVerifier with comprehensive schema validation and integrity monitoring.

Based on tasks_B.md requirements and addressing all critical fixes from user feedback.
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime

# Add the project directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.verification import ArchiveVerifier, VerificationError


def main():
    """Enhanced archive verification CLI"""
    parser = argparse.ArgumentParser(
        description="Enhanced Archive Verification with SHA-256 checksums and schema validation",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        'archive_path',
        type=Path,
        help='Path to archive directory or file to verify'
    )
    
    parser.add_argument(
        '--source',
        choices=['slack', 'calendar', 'drive', 'employees'],
        help='Verify archives for specific source only'
    )
    
    parser.add_argument(
        '--days-back',
        type=int,
        default=7,
        help='Number of days back to verify (default: 7)'
    )
    
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output results as JSON'
    )
    
    parser.add_argument(
        '--resume',
        action='store_true',
        help='Resume from last checkpoint if interrupted'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Show detailed progress and error information'
    )
    
    args = parser.parse_args()
    
    # Initialize verifier
    verifier = ArchiveVerifier()
    
    try:
        if args.verbose:
            print(f"🔍 Enhanced Archive Verification Starting...")
            print(f"📁 Archive Path: {args.archive_path}")
            print(f"🔧 Source Filter: {args.source or 'All sources'}")
            print(f"📅 Days Back: {args.days_back}")
            print()
        
        if args.archive_path.is_file():
            # Single file verification
            if args.verbose:
                print(f"📄 Verifying single file: {args.archive_path}")
            
            result = verifier.verify_jsonl_file(args.archive_path)
            
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                print(f"✅ File: {args.archive_path}")
                print(f"   Valid: {result['is_valid']}")
                print(f"   Records: {result['lines_processed']}")
                print(f"   Source: {result['source_type']}")
                print(f"   Compressed: {result['compression_detected']}")
                if result['errors']:
                    print(f"   Errors: {len(result['errors'])}")
                    if args.verbose:
                        for error in result['errors'][:5]:
                            print(f"     - {error}")
        
        elif args.source:
            # Source-specific verification
            if args.verbose:
                print(f"🔍 Verifying {args.source} archives...")
            
            results = verifier.verify_source_archives(args.source, args.archive_path, args.days_back)
            
            if args.json:
                # Convert results to serializable format
                json_results = {}
                for date_str, result in results.items():
                    json_results[date_str] = result.to_dict()
                print(json.dumps(json_results, indent=2))
            else:
                print(f"📊 {args.source.title()} Verification Results:")
                print(f"   Archives found: {len(results)}")
                
                valid_count = sum(1 for r in results.values() if r.status == 'valid')
                corrupted_count = sum(1 for r in results.values() if r.status == 'corrupted')
                missing_count = sum(1 for r in results.values() if r.status == 'missing')
                
                print(f"   ✅ Valid: {valid_count}")
                print(f"   ⚠️  Corrupted: {corrupted_count}")
                print(f"   ❌ Missing: {missing_count}")
                
                if args.verbose:
                    print("\n📋 Detailed Results:")
                    for date_str, result in sorted(results.items()):
                        status_icon = {'valid': '✅', 'corrupted': '⚠️', 'missing': '❌'}[result.status]
                        print(f"   {status_icon} {date_str}: {result.record_count} records, {result.file_size} bytes")
                        if result.errors:
                            for error in result.errors[:2]:
                                print(f"      - {error}")
        
        else:
            # Directory verification
            if args.verbose:
                print(f"📂 Verifying entire archive directory...")
            
            stats = verifier.verify_directory(args.archive_path, resume=args.resume)
            
            if args.json:
                print(json.dumps(stats, indent=2))
            else:
                print(f"📊 Directory Verification Complete:")
                print(f"   Files checked: {stats['files_checked']}")
                print(f"   Records verified: {stats['records_verified']:,}")
                print(f"   Errors found: {len(stats['errors'])}")
                
                if stats['sources_detected']:
                    print(f"\n🔍 Sources detected:")
                    for source, count in stats['sources_detected'].items():
                        print(f"   {source}: {count} archives")
                
                compression_stats = stats['compression_stats']
                total_files = compression_stats['compressed_files'] + compression_stats['uncompressed_files']
                if total_files > 0:
                    compression_rate = compression_stats['compressed_files'] / total_files * 100
                    print(f"\n📦 Compression:")
                    print(f"   Compressed files: {compression_stats['compressed_files']}")
                    print(f"   Uncompressed files: {compression_stats['uncompressed_files']}")
                    print(f"   Compression rate: {compression_rate:.1f}%")
                
                if stats['errors']:
                    print(f"\n⚠️  Errors found ({len(stats['errors'])}):")
                    for error in stats['errors'][:10]:
                        if isinstance(error, dict):
                            print(f"   - {error.get('file', 'Unknown')}: {error.get('error', 'Unknown error')}")
                        else:
                            print(f"   - {error}")
                    
                    if len(stats['errors']) > 10:
                        print(f"   ... and {len(stats['errors']) - 10} more errors")
                else:
                    print(f"\n✅ All files verified successfully!")
        
        # Generate comprehensive report if requested
        if args.source and not args.json:
            results_list = list(results.values())
            if results_list:
                report = verifier.generate_verification_report({
                    f"{args.source}_{i}": result for i, result in enumerate(results_list)
                })
                
                print(f"\n📋 Summary Report:")
                print(f"   Success rate: {report['verification_summary']['success_rate']:.1%}")
                print(f"   Total records: {report['data_statistics']['total_records']:,}")
                print(f"   Total size: {report['data_statistics']['total_size_bytes'] / 1024**2:.1f} MB")
                
                if report['recommendations']:
                    print(f"\n💡 Recommendations:")
                    for rec in report['recommendations'][:3]:
                        print(f"   • {rec}")
        
        # Exit with appropriate code
        if args.archive_path.is_file():
            sys.exit(0 if result['is_valid'] else 1)
        elif args.source:
            error_count = sum(1 for r in results.values() if r.status != 'valid')
            sys.exit(0 if error_count == 0 else 1)
        else:
            sys.exit(0 if len(stats['errors']) == 0 else 1)
    
    except VerificationError as e:
        print(f"❌ Verification Error: {e}", file=sys.stderr)
        sys.exit(2)
    except KeyboardInterrupt:
        print(f"\n⚠️  Verification interrupted by user", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()