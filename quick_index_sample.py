#!/usr/bin/env python3
"""
Quick sample indexing for performance validation.

Indexes a sample of records to create a reasonably sized database
for performance testing without processing all 800K+ records.
"""

import json
import sqlite3
import time
from pathlib import Path

def index_sample_data():
    """Index a sample of data quickly."""
    print("🚀 Quick Sample Data Indexing")
    print("=" * 50)
    
    # Connect to existing database
    conn = sqlite3.connect('search.db')
    cursor = conn.cursor()
    
    # Count existing records
    cursor.execute("SELECT COUNT(*) FROM messages")
    initial_count = cursor.fetchone()[0]
    print(f"Starting with {initial_count:,} records")
    
    # Index sample from the large Slack file
    slack_file = Path("data/archive/slack/2025-08-16/data.jsonl")
    
    if not slack_file.exists():
        print("❌ Large Slack file not found!")
        return False
    
    print(f"📄 Sampling from {slack_file}")
    
    records_added = 0
    target_sample = 50000  # Sample 50K records for testing
    
    start_time = time.perf_counter()
    
    with open(slack_file, 'r') as f:
        for i, line in enumerate(f):
            if records_added >= target_sample:
                break
                
            if i % 7 != 0:  # Sample every 7th record for variety
                continue
                
            try:
                record = json.loads(line.strip())
                
                # Extract content
                content = record.get('text', '').strip()
                if not content:
                    continue
                
                # Generate simple ID
                record_id = abs(hash(f"slack_{record.get('ts', i)}"))
                
                # Insert record
                cursor.execute("""
                    INSERT OR REPLACE INTO messages 
                    (id, content, source, created_at, date, metadata, person_id, channel_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    record_id,
                    content[:1000],  # Limit content length
                    "slack",
                    record.get('ts', ''),
                    "2025-08-16",
                    json.dumps({"channel_name": record.get('channel_name', '')}),
                    record.get('user', ''),
                    record.get('channel_id', '')
                ))
                
                records_added += 1
                
                if records_added % 5000 == 0:
                    conn.commit()
                    elapsed = time.perf_counter() - start_time
                    rate = records_added / elapsed if elapsed > 0 else 0
                    print(f"   📊 Indexed {records_added:,} records ({rate:.0f} rec/sec)")
                    
            except Exception as e:
                continue
    
    # Add some calendar data too
    print("📅 Adding calendar sample...")
    
    calendar_files = list(Path("data/raw/calendar/2025-08-17").glob("*.jsonl"))[:10]  # First 10 files
    
    for cal_file in calendar_files:
        try:
            with open(cal_file, 'r') as f:
                for line_num, line in enumerate(f):
                    if line_num >= 50:  # Limit per file
                        break
                        
                    try:
                        record = json.loads(line.strip())
                        
                        # Extract calendar content
                        content_parts = []
                        content_parts.append(record.get('summary', ''))
                        content_parts.append(record.get('description', ''))
                        content_parts.append(record.get('location', ''))
                        
                        content = ' '.join(filter(None, content_parts)).strip()
                        if not content:
                            continue
                        
                        record_id = abs(hash(f"calendar_{cal_file.name}_{line_num}"))
                        
                        cursor.execute("""
                            INSERT OR REPLACE INTO messages 
                            (id, content, source, created_at, date, metadata, person_id, channel_id)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            record_id,
                            content[:1000],
                            "calendar",
                            record.get('start', {}).get('dateTime', ''),
                            "2025-08-17",
                            json.dumps({"file": cal_file.name}),
                            "",
                            ""
                        ))
                        
                        records_added += 1
                        
                    except Exception:
                        continue
                        
        except Exception:
            continue
    
    conn.commit()
    total_time = time.perf_counter() - start_time
    
    # Final count
    cursor.execute("SELECT COUNT(*) FROM messages")
    final_count = cursor.fetchone()[0]
    
    print("\n" + "=" * 50)
    print("📊 INDEXING SUMMARY")
    print("=" * 50)
    print(f"   Records added: {records_added:,}")
    print(f"   Final count: {final_count:,}")
    print(f"   Time taken: {total_time:.1f} seconds")
    
    if total_time > 0:
        rate = records_added / total_time
        print(f"   Indexing rate: {rate:.0f} records/second")
        print(f"   {'✅' if rate >= 1000 else '❌'} Indexing target (>1000 rec/sec)")
    
    conn.close()
    
    return final_count >= 50000

if __name__ == "__main__":
    success = index_sample_data()
    exit(0 if success else 1)