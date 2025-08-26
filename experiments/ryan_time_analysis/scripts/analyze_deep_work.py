#!/usr/bin/env python3
"""
Deep Work Analysis for Ryan Marien

This script analyzes Ryan's calendar data to identify:
1. Scheduled deep work blocks and their protection success rate
2. Patterns of interruptions to focused work time
3. Optimal time blocks for uninterrupted work
4. Analysis of who/what interrupts deep work sessions

This analysis identifies specific opportunities for better protecting
Ryan's strategic thinking and execution time.
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Tuple
from collections import defaultdict
import re

# Experiment paths
EXPERIMENT_ROOT = Path(__file__).parent.parent
DATA_PATH = EXPERIMENT_ROOT / "data" / "raw"
REPORTS_PATH = EXPERIMENT_ROOT / "reports"
LOG_PATH = EXPERIMENT_ROOT / "experiment_log.md"

def log_analysis_update(session_info: str):
    """Append analysis update to experiment log"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"\n### {timestamp}\n{session_info}\n"
    
    with open(LOG_PATH, 'a') as f:
        f.write(log_entry)
    print(f"📝 Logged: {session_info}")

def load_calendar_data() -> List[Dict]:
    """Load Ryan's calendar data from the experiment directory"""
    calendar_file = DATA_PATH / "employee_ryan_at_biorender_com.jsonl"
    
    if not calendar_file.exists():
        raise FileNotFoundError(f"Calendar data not found at {calendar_file}")
    
    events = []
    with open(calendar_file, 'r') as f:
        for line in f:
            event = json.loads(line.strip())
            events.append(event)
    
    return events

def parse_event_time(event: Dict) -> Tuple[datetime, datetime, int]:
    """Parse event start/end times and calculate duration"""
    start = event.get('start', {})
    end = event.get('end', {})
    
    # Handle all-day events vs timed events
    if 'date' in start:
        return None, None, 0  # Skip all-day events for deep work analysis
        
    start_str = start.get('dateTime', '')
    end_str = end.get('dateTime', '')
    
    if not start_str or not end_str:
        return None, None, 0
        
    # Parse ISO format datetime
    start_dt = datetime.fromisoformat(start_str.replace('Z', '+00:00')).replace(tzinfo=None)
    end_dt = datetime.fromisoformat(end_str.replace('Z', '+00:00')).replace(tzinfo=None)
    duration_minutes = int((end_dt - start_dt).total_seconds() / 60)
    
    return start_dt, end_dt, duration_minutes

def identify_deep_work_blocks(events: List[Dict]) -> List[Dict]:
    """
    Identify scheduled deep work blocks based on meeting titles and descriptions
    """
    deep_work_keywords = [
        'heads down', 'focus', 'deep work', 'hard work', 'focus time',
        'thinking', 'strategy', 'planning', 'writing', 'analysis',
        'preparation', 'prep', 'review', 'research'
    ]
    
    deep_work_blocks = []
    
    for event in events:
        start_dt, end_dt, duration = parse_event_time(event)
        if not start_dt:
            continue
            
        summary = event.get('summary', '').lower()
        description = event.get('description', '').lower()
        
        # Check if this looks like a deep work block
        is_deep_work = False
        
        # Direct keyword match
        if any(keyword in summary for keyword in deep_work_keywords):
            is_deep_work = True
        elif any(keyword in description for keyword in deep_work_keywords):
            is_deep_work = True
        # Single-person blocks (no attendees or just Ryan)
        elif len(event.get('attendees', [])) <= 1 and duration >= 30:
            # Check if it's a generic block that could be deep work
            if any(word in summary for word in ['block', 'time', 'work', 'hour']):
                is_deep_work = True
        
        if is_deep_work:
            deep_work_blocks.append({
                'event': event,
                'start': start_dt,
                'end': end_dt,
                'duration_minutes': duration,
                'summary': event.get('summary', ''),
                'protection_status': 'unknown'  # Will analyze later
            })
    
    return deep_work_blocks

def analyze_deep_work_protection(deep_work_blocks: List[Dict], all_events: List[Dict]) -> Dict[str, Any]:
    """
    Analyze how well deep work blocks are protected from interruptions
    """
    log_analysis_update("🧠 Analyzing deep work block protection...")
    
    # Parse all meetings for interference analysis
    all_meetings = []
    for event in all_events:
        start_dt, end_dt, duration = parse_event_time(event)
        if start_dt and duration > 0:
            all_meetings.append({
                'start': start_dt,
                'end': end_dt,
                'duration_minutes': duration,
                'summary': event.get('summary', ''),
                'attendees': event.get('attendees', []),
                'organizer': event.get('organizer', {}).get('email', ''),
                'event': event
            })
    
    # Sort meetings by time
    all_meetings.sort(key=lambda m: m['start'])
    
    protected_blocks = 0
    interrupted_blocks = 0
    interruption_details = []
    
    for block in deep_work_blocks:
        # Check for overlapping or adjacent meetings
        interruptions = []
        
        for meeting in all_meetings:
            # Skip the deep work block itself
            if meeting['summary'] == block['summary'] and meeting['start'] == block['start']:
                continue
            
            # Check for overlaps or very close adjacency (within 15 minutes)
            time_gap_start = (block['start'] - meeting['end']).total_seconds() / 60
            time_gap_end = (meeting['start'] - block['end']).total_seconds() / 60
            
            # Meeting overlaps with or is very close to deep work block
            if (meeting['start'] < block['end'] and meeting['end'] > block['start']) or \
               (-15 <= time_gap_start <= 15) or (-15 <= time_gap_end <= 15):
                
                interruptions.append({
                    'meeting_summary': meeting['summary'],
                    'meeting_start': meeting['start'],
                    'meeting_duration': meeting['duration_minutes'],
                    'organizer': meeting['organizer'],
                    'attendee_count': len(meeting['attendees']),
                    'interference_type': 'overlap' if (meeting['start'] < block['end'] and meeting['end'] > block['start']) else 'adjacent'
                })
        
        if interruptions:
            interrupted_blocks += 1
            block['protection_status'] = 'interrupted'
            interruption_details.append({
                'deep_work_block': block,
                'interruptions': interruptions
            })
        else:
            protected_blocks += 1
            block['protection_status'] = 'protected'
    
    protection_rate = (protected_blocks / len(deep_work_blocks)) * 100 if deep_work_blocks else 0
    
    return {
        'total_deep_work_blocks': len(deep_work_blocks),
        'protected_blocks': protected_blocks,
        'interrupted_blocks': interrupted_blocks,
        'protection_rate': protection_rate,
        'interruption_details': interruption_details,
        'deep_work_blocks': deep_work_blocks
    }

def identify_optimal_deep_work_times(all_events: List[Dict]) -> Dict[str, Any]:
    """
    Identify time periods that are typically free and could be good for deep work
    """
    # Create a time grid for analysis (15-minute slots over a week)
    time_slots = defaultdict(int)  # day_hour_minute -> meeting_count
    
    for event in all_events:
        start_dt, end_dt, duration = parse_event_time(event)
        if not start_dt:
            continue
            
        # Count meetings in each time slot
        current = start_dt
        while current < end_dt:
            day_of_week = current.weekday()  # 0=Monday, 6=Sunday
            hour = current.hour
            minute_slot = (current.minute // 15) * 15  # Round to 15-min slots
            
            slot_key = f"{day_of_week}_{hour:02d}_{minute_slot:02d}"
            time_slots[slot_key] += 1
            
            current += timedelta(minutes=15)
    
    # Find consistently free time slots (less than 20% occupied)
    total_weeks = 6  # Approximate weeks in data
    optimal_slots = []
    
    for slot_key, meeting_count in time_slots.items():
        occupation_rate = meeting_count / total_weeks
        if occupation_rate < 0.2:  # Less than 20% occupied
            day, hour, minute = slot_key.split('_')
            optimal_slots.append({
                'day_of_week': int(day),
                'hour': int(hour),
                'minute': int(minute),
                'occupation_rate': occupation_rate,
                'avg_meetings_per_week': meeting_count / total_weeks
            })
    
    # Group optimal slots into larger blocks
    optimal_blocks = group_time_slots_into_blocks(optimal_slots)
    
    return {
        'optimal_time_slots': optimal_slots,
        'optimal_blocks': optimal_blocks,
        'total_slots_analyzed': len(time_slots),
        'free_slots': len(optimal_slots)
    }

def group_time_slots_into_blocks(slots: List[Dict]) -> List[Dict]:
    """Group adjacent time slots into larger deep work blocks"""
    if not slots:
        return []
    
    # Sort slots by day, hour, minute
    slots.sort(key=lambda s: (s['day_of_week'], s['hour'], s['minute']))
    
    blocks = []
    current_block = [slots[0]]
    
    for i in range(1, len(slots)):
        prev_slot = slots[i-1]
        current_slot = slots[i]
        
        # Check if slots are adjacent (same day, consecutive 15-min slots)
        if (current_slot['day_of_week'] == prev_slot['day_of_week'] and
            current_slot['hour'] == prev_slot['hour'] and
            current_slot['minute'] == prev_slot['minute'] + 15) or \
           (current_slot['day_of_week'] == prev_slot['day_of_week'] and
            current_slot['hour'] == prev_slot['hour'] + 1 and
            current_slot['minute'] == 0 and prev_slot['minute'] == 45):
            current_block.append(current_slot)
        else:
            # End current block, start new one
            if len(current_block) >= 4:  # At least 1 hour block
                blocks.append({
                    'day_of_week': current_block[0]['day_of_week'],
                    'start_hour': current_block[0]['hour'],
                    'start_minute': current_block[0]['minute'],
                    'end_hour': current_block[-1]['hour'],
                    'end_minute': current_block[-1]['minute'] + 15,
                    'duration_minutes': len(current_block) * 15,
                    'avg_occupation_rate': sum(s['occupation_rate'] for s in current_block) / len(current_block)
                })
            current_block = [current_slot]
    
    # Don't forget the last block
    if len(current_block) >= 4:
        blocks.append({
            'day_of_week': current_block[0]['day_of_week'],
            'start_hour': current_block[0]['hour'],
            'start_minute': current_block[0]['minute'],
            'end_hour': current_block[-1]['hour'],
            'end_minute': current_block[-1]['minute'] + 15,
            'duration_minutes': len(current_block) * 15,
            'avg_occupation_rate': sum(s['occupation_rate'] for s in current_block) / len(current_block)
        })
    
    return blocks

def analyze_interruption_patterns(interruption_details: List[Dict]) -> Dict[str, Any]:
    """Analyze who and what interrupts deep work blocks"""
    
    interrupter_stats = defaultdict(int)
    interruption_types = defaultdict(int)
    time_patterns = defaultdict(int)
    
    for detail in interruption_details:
        for interruption in detail['interruptions']:
            # Who interrupts?
            organizer = interruption.get('organizer', 'unknown')
            if organizer:
                interrupter_stats[organizer] += 1
            
            # What type of meeting interrupts?
            meeting_summary = interruption['meeting_summary'].lower()
            if '1:1' in meeting_summary or 'check in' in meeting_summary:
                interruption_types['one_on_one'] += 1
            elif 'sync' in meeting_summary or 'standup' in meeting_summary:
                interruption_types['sync_meeting'] += 1
            elif 'urgent' in meeting_summary or 'emergency' in meeting_summary:
                interruption_types['urgent'] += 1
            else:
                interruption_types['other'] += 1
            
            # When do interruptions happen?
            start_time = interruption['meeting_start']
            time_bucket = f"{start_time.hour:02d}:00"
            time_patterns[time_bucket] += 1
    
    return {
        'top_interrupters': dict(sorted(interrupter_stats.items(), key=lambda x: x[1], reverse=True)[:10]),
        'interruption_types': dict(interruption_types),
        'time_patterns': dict(sorted(time_patterns.items())),
        'total_interruptions': sum(interrupter_stats.values())
    }

def generate_deep_work_insights(analysis_results: Dict[str, Any]) -> List[str]:
    """Generate actionable insights for protecting deep work time"""
    insights = []
    
    protection_data = analysis_results['protection_analysis']
    optimal_times = analysis_results['optimal_times']
    patterns = analysis_results['interruption_patterns']
    
    # Protection rate insights
    protection_rate = protection_data['protection_rate']
    if protection_rate < 50:
        insights.append(f"🚨 Critical: Only {protection_rate:.1f}% of deep work blocks are protected from interruptions")
    elif protection_rate < 80:
        insights.append(f"⚠️  {protection_rate:.1f}% deep work protection rate - improvement needed")
    
    # Interruption insights
    total_interruptions = patterns['total_interruptions']
    if total_interruptions > 10:
        insights.append(f"🔀 {total_interruptions} interruptions to deep work blocks detected")
    
    # Top interrupters
    if patterns['top_interrupters']:
        top_interrupter = list(patterns['top_interrupters'].items())[0]
        insights.append(f"👤 Top interrupter: {top_interrupter[0]} ({top_interrupter[1]} interruptions)")
    
    # Optimal time recommendations
    if optimal_times['optimal_blocks']:
        best_block = max(optimal_times['optimal_blocks'], key=lambda b: b['duration_minutes'])
        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        day_name = day_names[best_block['day_of_week']]
        insights.append(f"💡 Best deep work opportunity: {day_name} {best_block['start_hour']:02d}:{best_block['start_minute']:02d}-{best_block['end_hour']:02d}:{best_block['end_minute']:02d} ({best_block['duration_minutes']} min)")
    
    return insights

def main():
    """Main deep work analysis function"""
    print("🧠 Starting Deep Work Analysis for Ryan Marien")
    print("=" * 60)
    
    try:
        # Load data
        events = load_calendar_data()
        log_analysis_update(f"✅ Loaded {len(events)} calendar events for deep work analysis")
        
        # Identify deep work blocks
        deep_work_blocks = identify_deep_work_blocks(events)
        log_analysis_update(f"🎯 Identified {len(deep_work_blocks)} deep work blocks")
        
        # Analyze protection of deep work blocks
        protection_analysis = analyze_deep_work_protection(deep_work_blocks, events)
        
        # Find optimal times for deep work
        optimal_times = identify_optimal_deep_work_times(events)
        
        # Analyze interruption patterns
        interruption_patterns = analyze_interruption_patterns(protection_analysis['interruption_details'])
        
        # Compile results
        analysis_results = {
            'protection_analysis': protection_analysis,
            'optimal_times': optimal_times,
            'interruption_patterns': interruption_patterns
        }
        
        # Generate insights
        insights = generate_deep_work_insights(analysis_results)
        
        # Create comprehensive results
        results = {
            'analysis_type': 'deep_work_protection',
            'subject': 'Ryan Marien',
            'analysis_date': datetime.now().isoformat(),
            'data_period': {
                'total_events': len(events),
                'deep_work_blocks_identified': len(deep_work_blocks)
            },
            'analysis': analysis_results,
            'insights': insights,
            'recommendations': [
                "Block 2+ hour periods for deep work and mark as 'Do Not Disturb'",
                "Schedule deep work during identified optimal times",
                "Set clear boundaries with top interrupters about protected time",
                "Use automatic meeting decline for non-essential requests during deep work blocks",
                "Create 'office hours' to contain routine interruptions",
                "Delegate meetings that interrupt strategic thinking time"
            ]
        }
        
        # Save results
        REPORTS_PATH.mkdir(parents=True, exist_ok=True)
        results_file = REPORTS_PATH / "deep_work_analysis.json"
        
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        # Display key findings
        print(f"\n🎯 Deep Work Analysis Complete!")
        print(f"🧠 Deep work blocks found: {len(deep_work_blocks)}")
        print(f"🛡️  Protection rate: {protection_analysis['protection_rate']:.1f}%")
        print(f"🔀 Total interruptions: {interruption_patterns['total_interruptions']}")
        print(f"⏰ Optimal time blocks found: {len(optimal_times['optimal_blocks'])}")
        
        print(f"\n💡 Key Insights:")
        for insight in insights:
            print(f"   {insight}")
        
        print(f"\n💾 Full results saved to: {results_file}")
        
        log_analysis_update(f"✅ Deep work analysis completed - {protection_analysis['protection_rate']:.1f}% protection rate")
        
        return results
        
    except Exception as e:
        error_msg = f"❌ Deep work analysis failed: {str(e)}"
        log_analysis_update(error_msg)
        print(error_msg)
        return None

if __name__ == "__main__":
    results = main()
    if results:
        print(f"\n🎉 Success! Deep work analysis complete.")
    else:
        print(f"\n❌ Analysis failed. Check logs for details.")
        sys.exit(1)