#!/usr/bin/env python3
"""
RTF Calendar Data Extractor for Ryan Marien Analysis

This script extracts calendar event data from the RTF terminal output file
and converts it to structured JSONL format for analysis.

The RTF file contains terminal output with JSON data embedded in RTF formatting.
We need to:
1. Convert RTF to plain text
2. Extract valid JSON events
3. Clean and validate the data
4. Save to structured format
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
import re

# Experiment paths
EXPERIMENT_ROOT = Path(__file__).parent.parent
RTF_FILE = EXPERIMENT_ROOT / "export calendar mapper aug 19.rtf"
OUTPUT_DIR = EXPERIMENT_ROOT / "data" / "raw" / "calendar_full_6months"
LOG_PATH = EXPERIMENT_ROOT / "experiment_log.md"

def log_extraction_update(session_info: str):
    """Append extraction update to experiment log"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"\n### {timestamp}\n{session_info}\n"
    
    with open(LOG_PATH, 'a') as f:
        f.write(log_entry)
    print(f"📝 Logged: {session_info}")

def extract_text_from_rtf(rtf_file: Path) -> str:
    """
    Convert RTF file to plain text using textutil
    
    Returns:
        str: Plain text content of RTF file
    """
    try:
        result = subprocess.run([
            'textutil', '-convert', 'txt', '-stdout', str(rtf_file)
        ], capture_output=True, text=True, check=True)
        
        log_extraction_update(f"✅ RTF converted to text ({len(result.stdout)} characters)")
        return result.stdout
        
    except subprocess.CalledProcessError as e:
        log_extraction_update(f"❌ RTF conversion failed: {e}")
        raise

def find_json_events(text_content: str) -> List[Dict]:
    """
    Extract calendar events from the text content
    
    The text contains JSON-like structures for calendar events.
    We need to identify and parse these carefully.
    
    Returns:
        List[Dict]: List of calendar event dictionaries
    """
    events = []
    
    # The events in this RTF have "summary" and "start"/"end" fields
    # Look for JSON objects that contain both summary and dateTime
    event_pattern = r'"summary"\s*:\s*"[^"]*"[^}]*"dateTime"\s*:'
    
    event_matches = re.finditer(event_pattern, text_content)
    
    for match in event_matches:
        # Find the start of the JSON object containing this event
        start_pos = match.start()
        brace_count = 0
        json_start = None
        
        # Look backwards for the opening brace of this event object
        for i in range(start_pos, max(0, start_pos - 1000), -1):  # Limit search to 1000 chars back
            if text_content[i] == '{':
                if json_start is None:
                    json_start = i
                brace_count += 1
            elif text_content[i] == '}':
                brace_count -= 1
                if brace_count < 0:
                    break
        
        if json_start is None:
            continue
            
        # Look forwards for the matching closing brace
        brace_count = 0
        json_end = None
        for i in range(json_start, min(len(text_content), json_start + 10000)):  # Limit to 10k chars forward
            if text_content[i] == '{':
                brace_count += 1
            elif text_content[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    json_end = i + 1
                    break
        
        if json_end is None:
            continue
        
        # Extract the JSON string and try to parse it
        json_str = text_content[json_start:json_end]
        
        try:
            event_obj = json.loads(json_str)
            if validate_event(event_obj):
                events.append(event_obj)
        except json.JSONDecodeError:
            # If direct parsing fails, try to fix common issues
            try:
                # Fix trailing commas and other issues
                cleaned_json = fix_json_format(json_str)
                event_obj = json.loads(cleaned_json)
                if validate_event(event_obj):
                    events.append(event_obj)
            except (json.JSONDecodeError, ValueError):
                # Skip malformed events
                continue
    
    # Remove duplicates based on id if present, or summary + start time
    unique_events = []
    seen_signatures = set()
    
    for event in events:
        # Create a signature for deduplication
        if 'id' in event:
            signature = event['id']
        else:
            start_time = event.get('start', {}).get('dateTime', '')
            signature = f"{event.get('summary', '')}-{start_time}"
        
        if signature not in seen_signatures:
            seen_signatures.add(signature)
            unique_events.append(event)
    
    log_extraction_update(f"🎯 Extracted {len(unique_events)} unique calendar events from RTF")
    return unique_events

def fix_json_format(json_str: str) -> str:
    """
    Fix common JSON formatting issues from RTF extraction
    
    Args:
        json_str: Potentially malformed JSON string
        
    Returns:
        str: Fixed JSON string
    """
    # Remove trailing commas before closing brackets/braces
    json_str = re.sub(r',\s*([}\]])', r'\1', json_str)
    
    # Fix unescaped quotes in strings (basic attempt)
    # This is tricky and might need more sophisticated handling
    
    return json_str

def validate_event(event: Dict) -> bool:
    """
    Validate that an event has the required fields for analysis
    
    Args:
        event: Calendar event dictionary
        
    Returns:
        bool: True if event is valid for analysis
    """
    # Check for summary (event title)
    if 'summary' not in event:
        return False
    
    # Should have start time
    if 'start' not in event:
        return False
    
    start = event.get('start', {})
    # Should have either dateTime or date
    if 'dateTime' not in start and 'date' not in start:
        return False
    
    # Should have end time
    if 'end' not in event:
        return False
    
    # Skip events with empty or very short summaries
    summary = event.get('summary', '').strip()
    if len(summary) < 2:
        return False
    
    return True

def save_events_to_jsonl(events: List[Dict], output_file: Path):
    """
    Save calendar events to JSONL format
    
    Args:
        events: List of calendar event dictionaries
        output_file: Path to output JSONL file
    """
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w') as f:
        for event in events:
            json.dump(event, f, separators=(',', ':'))
            f.write('\n')
    
    log_extraction_update(f"💾 Saved {len(events)} events to {output_file}")

def generate_extraction_summary(events: List[Dict]) -> Dict[str, Any]:
    """
    Generate summary statistics about the extracted events
    
    Args:
        events: List of calendar event dictionaries
        
    Returns:
        Dict containing summary statistics
    """
    if not events:
        return {"total_events": 0, "error": "No events extracted"}
    
    # Extract dates for range analysis
    dates = []
    for event in events:
        start = event.get('start', {})
        if 'dateTime' in start:
            try:
                date_str = start['dateTime'][:10]  # Extract date part
                dates.append(date_str)
            except (KeyError, IndexError):
                continue
        elif 'date' in start:
            dates.append(start['date'])
    
    dates.sort()
    
    summary = {
        "extraction_timestamp": datetime.now().isoformat(),
        "total_events": len(events),
        "date_range": {
            "start": dates[0] if dates else None,
            "end": dates[-1] if dates else None
        },
        "events_with_datetime": len([e for e in events if 'dateTime' in e.get('start', {})]),
        "all_day_events": len([e for e in events if 'date' in e.get('start', {})]),
        "events_by_month": {}
    }
    
    # Count events by month
    for date in dates:
        month = date[:7]  # YYYY-MM
        summary["events_by_month"][month] = summary["events_by_month"].get(month, 0) + 1
    
    return summary

def main():
    """Main extraction process"""
    print("🚀 Starting RTF calendar data extraction for Ryan Marien")
    
    # Verify RTF file exists
    if not RTF_FILE.exists():
        print(f"❌ RTF file not found: {RTF_FILE}")
        sys.exit(1)
    
    log_extraction_update("🚀 Starting RTF calendar extraction")
    
    try:
        # Step 1: Convert RTF to text
        print("📄 Converting RTF to plain text...")
        text_content = extract_text_from_rtf(RTF_FILE)
        
        # Step 2: Extract calendar events
        print("🎯 Extracting calendar events...")
        events = find_json_events(text_content)
        
        if not events:
            print("❌ No calendar events found in RTF file")
            log_extraction_update("❌ No calendar events extracted - check RTF format")
            return
        
        # Step 3: Save events to JSONL
        output_file = OUTPUT_DIR / "ryan_calendar_6months.jsonl"
        print(f"💾 Saving {len(events)} events to JSONL...")
        save_events_to_jsonl(events, output_file)
        
        # Step 4: Generate summary
        summary = generate_extraction_summary(events)
        summary_file = OUTPUT_DIR / "extraction_summary.json"
        
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"📊 Extraction complete!")
        print(f"   Events: {summary['total_events']}")
        print(f"   Date range: {summary['date_range']['start']} to {summary['date_range']['end']}")
        print(f"   Output: {output_file}")
        
        log_extraction_update(f"✅ Extraction complete: {len(events)} events from {summary['date_range']['start']} to {summary['date_range']['end']}")
        
    except Exception as e:
        print(f"❌ Extraction failed: {e}")
        log_extraction_update(f"❌ Extraction failed: {e}")
        raise

if __name__ == "__main__":
    main()