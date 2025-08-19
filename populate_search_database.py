#!/usr/bin/env python3
"""
Populate Search Database with Real Data

This script indexes all available JSONL data into the search database
to create a realistic dataset for performance testing.
"""

import sys
import os
import time
import json
import sqlite3
from pathlib import Path
from typing import Dict, Any, List, Tuple

# Add src to path
sys.path.append('src')

def setup_search_database(db_path: str = "search.db") -> sqlite3.Connection:
    """Connect to existing search database with proper schema."""
    conn = sqlite3.connect(db_path)
    return conn

def extract_content_from_record(record: Dict[str, Any], source: str) -> Tuple[str, str, str, str, str, str]:
    """Extract searchable content from various record types for existing schema."""
    
    # Generate unique ID (use integer for compatibility)  
    record_id = str(abs(hash(f"{source}_{json.dumps(record, sort_keys=True)}")))
    
    # Extract searchable content based on source type
    content_parts = []
    person_id = ""
    channel_id = ""
    created_at = ""
    date = ""
    
    if source == "slack" or "text" in record:
        # Slack message
        content_parts.append(record.get('text', ''))
        person_id = record.get('user', '')
        channel_id = record.get('channel', '')
        created_at = record.get('ts', '')
        date = created_at.split('.')[0] if created_at else ""  # Extract date part
        
    elif source == "calendar" or "summary" in record:
        # Calendar event
        content_parts.append(record.get('summary', ''))
        content_parts.append(record.get('description', ''))
        content_parts.append(record.get('location', ''))
        
        # Extract attendee information
        attendees = record.get('attendees', [])
        if attendees:
            attendee_names = [a.get('displayName', a.get('email', '')) for a in attendees]
            content_parts.extend(attendee_names)
        
        created_at = record.get('start', {}).get('dateTime', record.get('created', ''))
        if created_at:
            date = created_at.split('T')[0]  # Extract date part
        
    elif source == "drive" or "name" in record:
        # Drive file
        content_parts.append(record.get('name', ''))
        content_parts.append(record.get('description', ''))
        
        # Extract owner information
        owners = record.get('owners', [])
        if owners:
            owner_names = [o.get('displayName', o.get('emailAddress', '')) for o in owners]
            content_parts.extend(owner_names)
        
        created_at = record.get('modifiedTime', record.get('createdTime', ''))
        if created_at:
            date = created_at.split('T')[0]  # Extract date part
            
    elif source == "employee" or "email" in record:
        # Employee record
        content_parts.append(record.get('first_name', ''))
        content_parts.append(record.get('last_name', ''))
        content_parts.append(record.get('email', ''))
        content_parts.append(record.get('title', ''))
        content_parts.append(record.get('department', ''))
        
        person_id = record.get('slack_id', '')
        created_at = record.get('updated_at', record.get('created_at', ''))
        if created_at:
            date = created_at.split('T')[0]  # Extract date part
    
    # Combine all content
    content = ' '.join(filter(None, content_parts))
    
    # Create metadata JSON
    metadata = json.dumps({k: v for k, v in record.items() if k not in ['text', 'summary', 'name']})
    
    return record_id, content, source, created_at, date, metadata

def index_jsonl_file(conn: sqlite3.Connection, file_path: Path, source_hint: str = "") -> Tuple[int, int]:
    """Index a JSONL file into the search database."""
    
    # Determine source from file path or hint
    source = source_hint
    if not source:
        path_parts = str(file_path).lower()
        if "slack" in path_parts:
            source = "slack"
        elif "calendar" in path_parts:
            source = "calendar"
        elif "drive" in path_parts:
            source = "drive"
        elif "employee" in path_parts:
            source = "employee"
        else:
            source = "unknown"
    
    cursor = conn.cursor()
    records_processed = 0
    records_indexed = 0
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    record = json.loads(line.strip())
                    if not record:  # Skip empty records
                        continue
                    
                    records_processed += 1
                    
                    # Extract searchable content
                    record_id, content, source_type, created_at, date, metadata = extract_content_from_record(record, source)
                    
                    if not content.strip():  # Skip records with no searchable content
                        continue
                    
                    # Insert into database (matching existing schema)
                    cursor.execute("""
                        INSERT OR REPLACE INTO messages 
                        (id, content, source, created_at, date, metadata, person_id, channel_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (int(record_id) if record_id.isdigit() else abs(hash(record_id)), content, source_type, created_at, date, metadata, "", ""))
                    
                    records_indexed += 1
                    
                except json.JSONDecodeError:
                    print(f"   Warning: Invalid JSON on line {line_num} in {file_path}")
                    continue
                except Exception as e:
                    print(f"   Warning: Error processing line {line_num} in {file_path}: {e}")
                    continue
                    
                if records_processed % 1000 == 0:
                    conn.commit()  # Commit periodically
                    
    except Exception as e:
        print(f"   Error reading {file_path}: {e}")
        return 0, 0
    
    conn.commit()
    return records_processed, records_indexed

def find_jsonl_files() -> List[Tuple[Path, int]]:
    """Find all JSONL files and their sizes."""
    jsonl_files = []
    
    for jsonl_path in Path('.').rglob('*.jsonl'):
        if jsonl_path.is_file():
            try:
                # Count lines to estimate records
                with open(jsonl_path, 'r') as f:
                    line_count = sum(1 for _ in f)
                jsonl_files.append((jsonl_path, line_count))
            except Exception:
                jsonl_files.append((jsonl_path, 0))
    
    # Sort by line count (largest first)
    jsonl_files.sort(key=lambda x: x[1], reverse=True)
    return jsonl_files

def main():
    """Main indexing process."""
    print("🗂️  Populating Search Database with Real Data")
    print("=" * 60)
    
    # Find all JSONL files
    print("\n1. Discovering JSONL files...")
    jsonl_files = find_jsonl_files()
    
    total_estimated_records = sum(count for _, count in jsonl_files)
    print(f"   📊 Found {len(jsonl_files)} JSONL files")
    print(f"   📊 Estimated {total_estimated_records:,} total records")
    
    if not jsonl_files:
        print("   ❌ No JSONL files found!")
        return 1
    
    # Show top files
    print(f"\n   📁 Top 10 largest files:")
    for i, (file_path, count) in enumerate(jsonl_files[:10], 1):
        size_mb = file_path.stat().st_size / 1024 / 1024
        print(f"   {i:2d}. {file_path} ({count:,} records, {size_mb:.1f} MB)")
    
    # Set up database
    print("\n2. Setting up search database...")
    conn = setup_search_database()
    
    # Check current record count
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM messages")
    existing_count = cursor.fetchone()[0]
    print(f"   📊 Existing records: {existing_count:,}")
    
    # Index files
    print(f"\n3. Indexing {len(jsonl_files)} files...")
    start_time = time.perf_counter()
    
    total_processed = 0
    total_indexed = 0
    files_processed = 0
    
    for file_path, estimated_count in jsonl_files:
        print(f"   📄 Processing {file_path} ({estimated_count:,} estimated records)...")
        
        file_start_time = time.perf_counter()
        processed, indexed = index_jsonl_file(conn, file_path)
        file_time = time.perf_counter() - file_start_time
        
        total_processed += processed
        total_indexed += indexed
        files_processed += 1
        
        if indexed > 0:
            rate = indexed / file_time if file_time > 0 else 0
            print(f"      ✅ {indexed:,} records indexed ({rate:.0f} rec/sec)")
        else:
            print(f"      ⚠️  No records indexed")
        
        # Show progress
        if files_processed % 10 == 0:
            elapsed = time.perf_counter() - start_time
            overall_rate = total_indexed / elapsed if elapsed > 0 else 0
            print(f"   📊 Progress: {files_processed}/{len(jsonl_files)} files, {total_indexed:,} total records ({overall_rate:.0f} rec/sec)")
    
    total_time = time.perf_counter() - start_time
    
    # Final count
    cursor.execute("SELECT COUNT(*) FROM messages")
    final_count = cursor.fetchone()[0]
    
    # Summary
    print(f"\n" + "=" * 60)
    print("📋 INDEXING SUMMARY")
    print("=" * 60)
    print(f"   📁 Files processed: {files_processed:,}")
    print(f"   📊 Records processed: {total_processed:,}")
    print(f"   📊 Records indexed: {total_indexed:,}")
    print(f"   📊 Final database count: {final_count:,}")
    print(f"   ⏱️  Total time: {total_time:.1f} seconds")
    
    if total_time > 0:
        overall_rate = total_indexed / total_time
        print(f"   📈 Overall indexing rate: {overall_rate:.0f} records/second")
    
    # Indexing performance validation
    indexing_target_met = (total_indexed / total_time) >= 1000 if total_time > 0 else False
    print(f"   {'✅' if indexing_target_met else '❌'} Indexing performance target (>1000 rec/sec)")
    
    # Record count validation
    record_target_met = final_count >= 340000
    print(f"   {'✅' if record_target_met else '❌'} Record count target (340K+ records)")
    
    if final_count >= 340000:
        print("🎉 Successfully created 340K+ record database for realistic testing!")
    elif final_count >= 100000:
        print("🎯 Created substantial dataset for performance testing")
    else:
        print("⚠️  Dataset smaller than target, but sufficient for basic performance validation")
    
    conn.close()
    
    return 0 if indexing_target_met else 1

if __name__ == "__main__":
    sys.exit(main())