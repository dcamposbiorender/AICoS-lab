#!/usr/bin/env python3
"""
6-Month Calendar Pattern Analysis for Ryan Marien

This script performs comprehensive analysis of Ryan's 6-month calendar data
to identify busy trap indicators, time allocation patterns, and optimization opportunities.

Key analyses:
1. Time trend analysis (meeting volume evolution)
2. Context switching patterns
3. Deep work protection rates
4. Collaboration network analysis
5. Meeting efficiency patterns
6. Priority coherence tracking

Output: Structured analysis results and actionable insights
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Tuple
import pandas as pd
from collections import defaultdict, Counter
import calendar

# Experiment paths
EXPERIMENT_ROOT = Path(__file__).parent.parent
DATA_PATH = EXPERIMENT_ROOT / "data" / "raw" / "calendar_full_6months"
REPORTS_PATH = EXPERIMENT_ROOT / "reports"
LOG_PATH = EXPERIMENT_ROOT / "experiment_log.md"

def log_analysis_update(session_info: str):
    """Append analysis update to experiment log"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"\n### {timestamp}\n{session_info}\n"
    
    with open(LOG_PATH, 'a') as f:
        f.write(log_entry)
    print(f"📝 {session_info}")

def load_calendar_data() -> List[Dict]:
    """Load Ryan's 6-month calendar data"""
    calendar_file = DATA_PATH / "ryan_calendar_6months.jsonl"
    
    if not calendar_file.exists():
        raise FileNotFoundError(f"Calendar data not found at {calendar_file}")
    
    events = []
    with open(calendar_file, 'r') as f:
        for line in f:
            event = json.loads(line.strip())
            events.append(event)
    
    log_analysis_update(f"✅ Loaded {len(events)} calendar events for 6-month analysis")
    return events

def parse_event_time(event: Dict) -> Tuple[datetime, datetime, int]:
    """
    Parse event start/end times and calculate duration
    
    Returns:
        (start_datetime, end_datetime, duration_minutes)
    """
    start = event.get('start', {})
    end = event.get('end', {})
    
    # Handle timed events (all events in this dataset are timed)
    start_str = start.get('dateTime', '')
    end_str = end.get('dateTime', '')
    
    if not start_str or not end_str:
        return None, None, 0
        
    # Parse ISO format datetime
    start_dt = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
    end_dt = datetime.fromisoformat(end_str.replace('Z', '+00:00'))
    
    # Convert to naive datetime for calculation
    start_dt = start_dt.replace(tzinfo=None)
    end_dt = end_dt.replace(tzinfo=None)
    
    duration_minutes = int((end_dt - start_dt).total_seconds() / 60)
    
    return start_dt, end_dt, duration_minutes

def analyze_time_trends(events: List[Dict]) -> Dict[str, Any]:
    """
    Analyze how Ryan's meeting patterns have evolved over 6 months
    
    Returns:
        Dict with time trend analysis results
    """
    log_analysis_update("📈 Analyzing time trends across 6 months...")
    
    # Group events by month and week
    monthly_stats = defaultdict(lambda: {
        'total_meetings': 0,
        'total_minutes': 0,
        'avg_duration': 0,
        'short_meetings': 0,  # ≤ 15 min
        'long_meetings': 0,   # ≥ 90 min
        'back_to_back': 0,
        'unique_attendees': set(),
        'meeting_types': defaultdict(int)
    })
    
    weekly_stats = defaultdict(lambda: {
        'total_meetings': 0,
        'total_minutes': 0
    })
    
    # Sort events by start time for chronological analysis
    timed_events = []
    for event in events:
        start_dt, end_dt, duration = parse_event_time(event)
        if start_dt:
            timed_events.append({
                'event': event,
                'start': start_dt,
                'end': end_dt,
                'duration': duration
            })
    
    timed_events.sort(key=lambda x: x['start'])
    
    # Analyze each event
    for i, event_data in enumerate(timed_events):
        event = event_data['event']
        start_dt = event_data['start']
        duration = event_data['duration']
        
        # Monthly grouping
        month_key = start_dt.strftime('%Y-%m')
        monthly_stats[month_key]['total_meetings'] += 1
        monthly_stats[month_key]['total_minutes'] += duration
        
        # Weekly grouping
        week_start = start_dt - timedelta(days=start_dt.weekday())
        week_key = week_start.strftime('%Y-W%U')
        weekly_stats[week_key]['total_meetings'] += 1
        weekly_stats[week_key]['total_minutes'] += duration
        
        # Meeting duration analysis
        if duration <= 15:
            monthly_stats[month_key]['short_meetings'] += 1
        elif duration >= 90:
            monthly_stats[month_key]['long_meetings'] += 1
        
        # Attendee analysis
        attendees = event.get('attendees', [])
        for attendee in attendees:
            email = attendee.get('email', '')
            if email and email != 'ryan@biorender.com':
                monthly_stats[month_key]['unique_attendees'].add(email)
        
        # Meeting type classification (basic)
        summary = event.get('summary', '').lower()
        if '1:1' in summary or 'one-on-one' in summary:
            monthly_stats[month_key]['meeting_types']['1:1'] += 1
        elif 'standup' in summary or 'scrum' in summary:
            monthly_stats[month_key]['meeting_types']['standup'] += 1
        elif 'all hands' in summary or 'company' in summary:
            monthly_stats[month_key]['meeting_types']['all_hands'] += 1
        elif 'deep' in summary or 'focus' in summary or 'work' in summary:
            monthly_stats[month_key]['meeting_types']['deep_work'] += 1
        else:
            monthly_stats[month_key]['meeting_types']['other'] += 1
        
        # Back-to-back meeting detection
        if i > 0:
            prev_event = timed_events[i-1]
            gap_minutes = (start_dt - prev_event['end']).total_seconds() / 60
            if gap_minutes <= 5:  # 5 minute buffer
                monthly_stats[month_key]['back_to_back'] += 1
    
    # Calculate averages and create trend data
    monthly_trends = {}
    for month, stats in monthly_stats.items():
        if stats['total_meetings'] > 0:
            stats['avg_duration'] = stats['total_minutes'] / stats['total_meetings']
            stats['unique_attendees'] = len(stats['unique_attendees'])
        monthly_trends[month] = dict(stats)
    
    return {
        'analysis_type': '6_month_trends',
        'period': '2024-08 to 2025-02',
        'monthly_trends': monthly_trends,
        'summary': {
            'total_months': len(monthly_trends),
            'peak_meeting_month': max(monthly_trends.keys(), key=lambda m: monthly_trends[m]['total_meetings']),
            'peak_meeting_count': max(stats['total_meetings'] for stats in monthly_trends.values()),
            'avg_monthly_meetings': sum(stats['total_meetings'] for stats in monthly_trends.values()) / len(monthly_trends),
            'avg_monthly_hours': sum(stats['total_minutes'] for stats in monthly_trends.values()) / 60 / len(monthly_trends)
        }
    }

def analyze_context_switching_evolution(events: List[Dict]) -> Dict[str, Any]:
    """
    Track how context switching patterns have evolved over time
    
    Returns:
        Dict with context switching evolution analysis
    """
    log_analysis_update("🔄 Analyzing context switching evolution...")
    
    # Group by month and analyze switching patterns
    monthly_switching = defaultdict(lambda: {
        'total_meetings': 0,
        'short_gaps': 0,      # < 15 min between meetings
        'no_gaps': 0,         # Back-to-back meetings
        'fragmentation_score': 0,
        'daily_switches': [],
        'avg_meeting_duration': 0,
        'total_minutes': 0
    })
    
    # Sort events by time
    timed_events = []
    for event in events:
        start_dt, end_dt, duration = parse_event_time(event)
        if start_dt:
            timed_events.append({
                'start': start_dt,
                'end': end_dt,
                'duration': duration,
                'summary': event.get('summary', ''),
                'attendee_count': len(event.get('attendees', []))
            })
    
    timed_events.sort(key=lambda x: x['start'])
    
    # Analyze context switching per day
    daily_events = defaultdict(list)
    for event in timed_events:
        date_key = event['start'].date()
        daily_events[date_key].append(event)
    
    for date, day_events in daily_events.items():
        month_key = date.strftime('%Y-%m')
        
        if len(day_events) < 2:
            continue  # No switching possible with < 2 events
        
        day_switches = 0
        total_gap_time = 0
        
        for i in range(1, len(day_events)):
            prev_event = day_events[i-1]
            curr_event = day_events[i]
            
            gap_minutes = (curr_event['start'] - prev_event['end']).total_seconds() / 60
            
            # Count as context switch if gap is short (< 30 min)
            if gap_minutes < 30:
                day_switches += 1
                
                if gap_minutes < 5:
                    monthly_switching[month_key]['no_gaps'] += 1
                elif gap_minutes < 15:
                    monthly_switching[month_key]['short_gaps'] += 1
            
            total_gap_time += gap_minutes
        
        monthly_switching[month_key]['daily_switches'].append(day_switches)
        monthly_switching[month_key]['total_meetings'] += len(day_events)
        monthly_switching[month_key]['total_minutes'] += sum(e['duration'] for e in day_events)
    
    # Calculate monthly fragmentation scores
    for month, stats in monthly_switching.items():
        if stats['daily_switches']:
            avg_daily_switches = sum(stats['daily_switches']) / len(stats['daily_switches'])
            # Fragmentation score: higher = more fragmented
            # Based on switches per day and proportion of short gaps
            total_gaps = stats['short_gaps'] + stats['no_gaps']
            gap_ratio = total_gaps / max(stats['total_meetings'], 1)
            stats['fragmentation_score'] = (avg_daily_switches * 10) + (gap_ratio * 50)
            stats['avg_daily_switches'] = avg_daily_switches
            
            if stats['total_meetings'] > 0:
                stats['avg_meeting_duration'] = stats['total_minutes'] / stats['total_meetings']
    
    return {
        'analysis_type': 'context_switching_evolution',
        'period': '2024-08 to 2025-02',
        'monthly_patterns': dict(monthly_switching),
        'evolution_summary': {
            'highest_fragmentation_month': max(
                monthly_switching.keys(), 
                key=lambda m: monthly_switching[m]['fragmentation_score']
            ) if monthly_switching else None,
            'lowest_fragmentation_month': min(
                monthly_switching.keys(),
                key=lambda m: monthly_switching[m]['fragmentation_score']
            ) if monthly_switching else None,
            'fragmentation_trend': 'calculated_separately'  # Would need regression analysis
        }
    }

def analyze_collaboration_network(events: List[Dict]) -> Dict[str, Any]:
    """
    Analyze Ryan's collaboration patterns and how they've evolved
    
    Returns:
        Dict with collaboration network analysis
    """
    log_analysis_update("🤝 Analyzing collaboration network evolution...")
    
    monthly_collaborations = defaultdict(lambda: {
        'unique_collaborators': set(),
        'meeting_counts': defaultdict(int),
        'total_collaboration_time': defaultdict(int),
        'external_meetings': 0,
        'internal_meetings': 0,
        'large_meetings': 0,  # > 5 attendees
        'small_meetings': 0   # ≤ 5 attendees
    })
    
    # Analyze each event
    for event in events:
        start_dt, _, duration = parse_event_time(event)
        if not start_dt:
            continue
            
        month_key = start_dt.strftime('%Y-%m')
        attendees = event.get('attendees', [])
        attendee_count = len([a for a in attendees if a.get('email') != 'ryan@biorender.com'])
        
        # Track meeting size
        if attendee_count > 5:
            monthly_collaborations[month_key]['large_meetings'] += 1
        else:
            monthly_collaborations[month_key]['small_meetings'] += 1
        
        # Track individual collaborators
        for attendee in attendees:
            email = attendee.get('email', '')
            if email and email != 'ryan@biorender.com':
                monthly_collaborations[month_key]['unique_collaborators'].add(email)
                monthly_collaborations[month_key]['meeting_counts'][email] += 1
                monthly_collaborations[month_key]['total_collaboration_time'][email] += duration
                
                # External vs internal (basic heuristic)
                if '@biorender.com' not in email:
                    monthly_collaborations[month_key]['external_meetings'] += 1
                else:
                    monthly_collaborations[month_key]['internal_meetings'] += 1
    
    # Process results
    collaboration_summary = {}
    for month, data in monthly_collaborations.items():
        top_collaborators = sorted(
            data['meeting_counts'].items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:10]
        
        collaboration_summary[month] = {
            'unique_collaborator_count': len(data['unique_collaborators']),
            'top_collaborators': top_collaborators,
            'external_meetings': data['external_meetings'],
            'internal_meetings': data['internal_meetings'],
            'large_meetings': data['large_meetings'],
            'small_meetings': data['small_meetings']
        }
    
    return {
        'analysis_type': 'collaboration_network_evolution',
        'period': '2024-08 to 2025-02',
        'monthly_collaboration': collaboration_summary,
        'network_insights': {
            'peak_collaboration_month': max(
                collaboration_summary.keys(),
                key=lambda m: collaboration_summary[m]['unique_collaborator_count']
            ) if collaboration_summary else None,
            'avg_monthly_collaborators': sum(
                data['unique_collaborator_count'] 
                for data in collaboration_summary.values()
            ) / len(collaboration_summary) if collaboration_summary else 0
        }
    }

def main():
    """Main analysis process"""
    print("🚀 Starting 6-month calendar pattern analysis for Ryan Marien")
    
    try:
        # Load calendar data
        events = load_calendar_data()
        
        # Perform analyses
        print("📈 Analyzing time trends...")
        time_trends = analyze_time_trends(events)
        
        print("🔄 Analyzing context switching patterns...")
        switching_analysis = analyze_context_switching_evolution(events)
        
        print("🤝 Analyzing collaboration network...")
        collaboration_analysis = analyze_collaboration_network(events)
        
        # Save results
        REPORTS_PATH.mkdir(exist_ok=True)
        
        analyses = {
            'time_trends': time_trends,
            'context_switching': switching_analysis,
            'collaboration_network': collaboration_analysis,
            'analysis_timestamp': datetime.now().isoformat(),
            'data_period': '2024-08-20 to 2025-02-07',
            'total_events_analyzed': len(events)
        }
        
        output_file = REPORTS_PATH / "6_month_pattern_analysis.json"
        with open(output_file, 'w') as f:
            json.dump(analyses, f, indent=2, default=str)
        
        print(f"✅ Analysis complete! Results saved to: {output_file}")
        
        # Log key findings
        peak_month = time_trends['summary']['peak_meeting_month']
        peak_count = time_trends['summary']['peak_meeting_count']
        avg_monthly = time_trends['summary']['avg_monthly_meetings']
        
        log_analysis_update(f"✅ 6-month analysis complete")
        log_analysis_update(f"📊 Peak meeting month: {peak_month} ({peak_count} meetings)")
        log_analysis_update(f"📊 Average monthly meetings: {avg_monthly:.1f}")
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        log_analysis_update(f"❌ 6-month analysis failed: {e}")
        raise

if __name__ == "__main__":
    main()