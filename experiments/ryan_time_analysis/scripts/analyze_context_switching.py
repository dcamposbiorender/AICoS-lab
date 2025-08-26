#!/usr/bin/env python3
"""
Context Switching Analysis for Ryan Marien

This script analyzes Ryan's calendar data to identify patterns that indicate
high context switching costs and schedule fragmentation. Key metrics include:

1. Meeting fragmentation score (15-minute meetings)
2. Back-to-back meeting patterns
3. Recovery time between context switches
4. Daily schedule density analysis

This is an experimental analysis to identify potential evergreen features
for the main AICoS system.
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Tuple
import pandas as pd
from collections import defaultdict

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
    
    log_analysis_update(f"✅ Loaded {len(events)} calendar events for analysis")
    return events

def parse_event_time(event: Dict) -> Tuple[datetime, datetime, int]:
    """
    Parse event start/end times and calculate duration
    
    Returns:
        (start_datetime, end_datetime, duration_minutes)
    """
    start = event.get('start', {})
    end = event.get('end', {})
    
    # Handle all-day events (date only) vs timed events (dateTime)
    if 'date' in start:
        # All-day event
        start_dt = datetime.fromisoformat(start['date']).replace(hour=0, minute=0)
        end_dt = datetime.fromisoformat(end['date']).replace(hour=0, minute=0)
        duration_minutes = 24 * 60  # All day
    else:
        # Timed event - parse datetime strings
        start_str = start.get('dateTime', '')
        end_str = end.get('dateTime', '')
        
        if not start_str or not end_str:
            return None, None, 0
            
        # Parse ISO format datetime (remove timezone for simplicity)
        start_dt = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(end_str.replace('Z', '+00:00'))
        
        # Convert to local time if needed (remove timezone info for calculation)
        start_dt = start_dt.replace(tzinfo=None)
        end_dt = end_dt.replace(tzinfo=None)
        
        duration_minutes = int((end_dt - start_dt).total_seconds() / 60)
    
    return start_dt, end_dt, duration_minutes

def calculate_context_switching_metrics(events: List[Dict]) -> Dict[str, Any]:
    """
    Calculate various context switching cost metrics
    
    Returns:
        Dictionary with context switching analysis results
    """
    log_analysis_update("🔄 Calculating context switching metrics...")
    
    # Parse and filter to timed meetings only
    meetings = []
    for event in events:
        start_dt, end_dt, duration = parse_event_time(event)
        if start_dt and end_dt and duration > 0 and duration < 24 * 60:  # Skip all-day events
            meetings.append({
                'summary': event.get('summary', 'Untitled'),
                'start': start_dt,
                'end': end_dt,
                'duration_minutes': duration,
                'attendees': len(event.get('attendees', [])),
                'event_type': classify_meeting_type(event.get('summary', ''))
            })
    
    # Sort meetings by start time
    meetings.sort(key=lambda m: m['start'])
    
    # Calculate metrics
    metrics = {
        'total_meetings': len(meetings),
        'meeting_duration_analysis': analyze_meeting_durations(meetings),
        'fragmentation_analysis': analyze_schedule_fragmentation(meetings),
        'back_to_back_analysis': analyze_back_to_back_meetings(meetings),
        'daily_patterns': analyze_daily_patterns(meetings),
        'context_switching_score': 0  # Will calculate after other metrics
    }
    
    # Calculate overall context switching score (0-100, higher = more fragmented)
    metrics['context_switching_score'] = calculate_fragmentation_score(metrics)
    
    return metrics

def classify_meeting_type(summary: str) -> str:
    """Classify meeting type based on summary text"""
    summary_lower = summary.lower()
    
    if any(keyword in summary_lower for keyword in ['1:1', 'one-on-one', '1-on-1', 'check in']):
        return 'one_on_one'
    elif any(keyword in summary_lower for keyword in ['heads down', 'focus', 'deep work', 'hard work']):
        return 'deep_work'
    elif any(keyword in summary_lower for keyword in ['sync', 'standup', 'daily', 'weekly']):
        return 'sync'
    elif any(keyword in summary_lower for keyword in ['office hours', 'oh']):
        return 'office_hours'
    elif any(keyword in summary_lower for keyword in ['lunch', 'coffee', 'dinner', 'breakfast']):
        return 'social'
    elif any(keyword in summary_lower for keyword in ['interview', 'candidate']):
        return 'interview'
    elif any(keyword in summary_lower for keyword in ['all hands', 'company', 'townhall']):
        return 'company_wide'
    else:
        return 'general_meeting'

def analyze_meeting_durations(meetings: List[Dict]) -> Dict[str, Any]:
    """Analyze distribution of meeting durations"""
    durations = [m['duration_minutes'] for m in meetings]
    
    # Count meetings by duration buckets
    duration_buckets = {
        '15_min': len([d for d in durations if d <= 15]),
        '30_min': len([d for d in durations if 15 < d <= 30]),
        '45_min': len([d for d in durations if 30 < d <= 45]),
        '60_min': len([d for d in durations if 45 < d <= 60]),
        '90_min': len([d for d in durations if 60 < d <= 90]),
        '120_min_plus': len([d for d in durations if d > 90])
    }
    
    # Calculate percentage of short meetings (high context switching cost)
    short_meetings = duration_buckets['15_min']
    short_meeting_percentage = (short_meetings / len(durations)) * 100 if durations else 0
    
    return {
        'duration_distribution': duration_buckets,
        'average_duration': sum(durations) / len(durations) if durations else 0,
        'short_meeting_count': short_meetings,
        'short_meeting_percentage': short_meeting_percentage,
        'total_meeting_time': sum(durations)
    }

def analyze_schedule_fragmentation(meetings: List[Dict]) -> Dict[str, Any]:
    """Analyze how fragmented the schedule is"""
    if len(meetings) < 2:
        return {'gap_analysis': {}, 'fragmentation_score': 0}
    
    # Calculate gaps between meetings
    gaps = []
    for i in range(len(meetings) - 1):
        gap_minutes = int((meetings[i + 1]['start'] - meetings[i]['end']).total_seconds() / 60)
        gaps.append(gap_minutes)
    
    # Categorize gaps
    gap_categories = {
        'no_gap': len([g for g in gaps if g <= 0]),           # Back-to-back or overlapping
        'short_gap': len([g for g in gaps if 0 < g <= 15]),   # 1-15 minutes (too short for context switch)
        'medium_gap': len([g for g in gaps if 15 < g <= 60]), # 15-60 minutes (minimal recovery)
        'long_gap': len([g for g in gaps if g > 60])          # 60+ minutes (good recovery time)
    }
    
    # Calculate fragmentation score (0-100, higher = more fragmented)
    total_gaps = len(gaps)
    if total_gaps == 0:
        fragmentation_score = 0
    else:
        # Weight: back-to-back = 100, short = 80, medium = 40, long = 0
        weighted_score = (
            gap_categories['no_gap'] * 100 +
            gap_categories['short_gap'] * 80 +
            gap_categories['medium_gap'] * 40 +
            gap_categories['long_gap'] * 0
        ) / total_gaps
        fragmentation_score = weighted_score
    
    return {
        'gap_analysis': gap_categories,
        'gap_distribution': gaps,
        'average_gap_minutes': sum(gaps) / len(gaps) if gaps else 0,
        'fragmentation_score': fragmentation_score
    }

def analyze_back_to_back_meetings(meetings: List[Dict]) -> Dict[str, Any]:
    """Analyze patterns of back-to-back meetings"""
    if len(meetings) < 2:
        return {'back_to_back_chains': [], 'longest_chain': 0}
    
    # Find chains of back-to-back meetings
    chains = []
    current_chain = 1
    
    for i in range(len(meetings) - 1):
        gap_minutes = int((meetings[i + 1]['start'] - meetings[i]['end']).total_seconds() / 60)
        
        if gap_minutes <= 0:  # Back-to-back or overlapping
            current_chain += 1
        else:
            if current_chain > 1:
                chains.append(current_chain)
            current_chain = 1
    
    # Don't forget the last chain
    if current_chain > 1:
        chains.append(current_chain)
    
    return {
        'back_to_back_chains': chains,
        'longest_chain': max(chains) if chains else 0,
        'total_chains': len(chains),
        'average_chain_length': sum(chains) / len(chains) if chains else 0
    }

def analyze_daily_patterns(meetings: List[Dict]) -> Dict[str, Any]:
    """Analyze daily meeting patterns"""
    daily_stats = defaultdict(lambda: {'meeting_count': 0, 'total_duration': 0, 'meetings': []})
    
    for meeting in meetings:
        date_key = meeting['start'].strftime('%Y-%m-%d')
        daily_stats[date_key]['meeting_count'] += 1
        daily_stats[date_key]['total_duration'] += meeting['duration_minutes']
        daily_stats[date_key]['meetings'].append(meeting)
    
    # Calculate daily metrics
    daily_metrics = {}
    for date, stats in daily_stats.items():
        daily_metrics[date] = {
            'meeting_count': stats['meeting_count'],
            'total_duration_hours': stats['total_duration'] / 60,
            'meeting_density': stats['meeting_count'] / 8,  # Meetings per 8-hour workday
            'meetings': stats['meetings']
        }
    
    # Calculate overall daily averages
    if daily_metrics:
        avg_meetings_per_day = sum(d['meeting_count'] for d in daily_metrics.values()) / len(daily_metrics)
        avg_hours_per_day = sum(d['total_duration_hours'] for d in daily_metrics.values()) / len(daily_metrics)
    else:
        avg_meetings_per_day = 0
        avg_hours_per_day = 0
    
    return {
        'daily_breakdown': daily_metrics,
        'average_meetings_per_day': avg_meetings_per_day,
        'average_hours_per_day': avg_hours_per_day,
        'total_days_analyzed': len(daily_metrics)
    }

def calculate_fragmentation_score(metrics: Dict[str, Any]) -> float:
    """Calculate overall context switching fragmentation score (0-100)"""
    
    # Component scores (0-100 each)
    duration_score = metrics['meeting_duration_analysis']['short_meeting_percentage']
    fragmentation_score = metrics['fragmentation_analysis']['fragmentation_score']
    
    # Back-to-back penalty
    btb_score = min(metrics['back_to_back_analysis']['longest_chain'] * 20, 100)
    
    # Daily density penalty (meetings per day)
    density_score = min(metrics['daily_patterns']['average_meetings_per_day'] * 10, 100)
    
    # Weighted average
    overall_score = (
        duration_score * 0.3 +      # 30% weight on short meetings
        fragmentation_score * 0.4 + # 40% weight on schedule gaps
        btb_score * 0.2 +           # 20% weight on back-to-back chains
        density_score * 0.1         # 10% weight on meeting density
    )
    
    return round(overall_score, 1)

def generate_insights(metrics: Dict[str, Any]) -> List[str]:
    """Generate actionable insights from the analysis"""
    insights = []
    
    # Short meeting insights
    short_pct = metrics['meeting_duration_analysis']['short_meeting_percentage']
    if short_pct > 20:
        insights.append(f"⚠️  High context switching cost: {short_pct:.1f}% of meetings are 15 minutes or less")
    
    # Fragmentation insights
    frag_score = metrics['fragmentation_analysis']['fragmentation_score']
    if frag_score > 60:
        insights.append(f"🔀 Schedule is highly fragmented (score: {frag_score:.1f}/100) - consider consolidating meetings")
    
    # Back-to-back insights
    longest_chain = metrics['back_to_back_analysis']['longest_chain']
    if longest_chain > 4:
        insights.append(f"⚡ Longest back-to-back meeting chain: {longest_chain} meetings - schedule recovery breaks")
    
    # Daily load insights
    avg_meetings = metrics['daily_patterns']['average_meetings_per_day']
    if avg_meetings > 8:
        insights.append(f"📅 High meeting load: {avg_meetings:.1f} meetings per day on average")
    
    # Overall fragmentation
    overall_score = metrics['context_switching_score']
    if overall_score > 70:
        insights.append(f"🚨 Critical: Overall fragmentation score is {overall_score}/100 - immediate optimization needed")
    elif overall_score > 50:
        insights.append(f"⚠️  Warning: Fragmentation score is {overall_score}/100 - optimization recommended")
    
    return insights

def main():
    """Main analysis function"""
    print("🔄 Starting Context Switching Analysis for Ryan Marien")
    print("=" * 60)
    
    try:
        # Load data
        events = load_calendar_data()
        
        # Run analysis
        metrics = calculate_context_switching_metrics(events)
        
        # Generate insights
        insights = generate_insights(metrics)
        
        # Create results
        results = {
            'analysis_type': 'context_switching',
            'subject': 'Ryan Marien',
            'analysis_date': datetime.now().isoformat(),
            'data_period': {
                'total_events': len(events),
                'meetings_analyzed': metrics['total_meetings']
            },
            'metrics': metrics,
            'insights': insights,
            'recommendations': [
                "Consider consolidating 15-minute check-ins into longer, more substantive meetings",
                "Block 60+ minute periods for deep work without interruptions",
                "Add 15-minute buffers between meetings to allow for context switching",
                "Batch similar meeting types together (e.g., all 1:1s on same day)",
                "Delegate routine meetings that don't require executive input"
            ]
        }
        
        # Save results
        REPORTS_PATH.mkdir(parents=True, exist_ok=True)
        results_file = REPORTS_PATH / "context_switching_analysis.json"
        
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        # Display key findings
        print(f"\n🎯 Analysis Complete!")
        print(f"📊 Meetings analyzed: {metrics['total_meetings']}")
        print(f"🔀 Context switching score: {metrics['context_switching_score']}/100")
        print(f"⚡ Short meetings (≤15min): {metrics['meeting_duration_analysis']['short_meeting_percentage']:.1f}%")
        print(f"📅 Average meetings/day: {metrics['daily_patterns']['average_meetings_per_day']:.1f}")
        print(f"⛓️  Longest meeting chain: {metrics['back_to_back_analysis']['longest_chain']} meetings")
        
        print(f"\n💡 Key Insights:")
        for insight in insights:
            print(f"   {insight}")
        
        print(f"\n💾 Full results saved to: {results_file}")
        
        log_analysis_update(f"✅ Context switching analysis completed - Score: {metrics['context_switching_score']}/100")
        
        return results
        
    except Exception as e:
        error_msg = f"❌ Context switching analysis failed: {str(e)}"
        log_analysis_update(error_msg)
        print(error_msg)
        return None

if __name__ == "__main__":
    results = main()
    if results:
        print(f"\n🎉 Success! Context switching analysis complete.")
    else:
        print(f"\n❌ Analysis failed. Check logs for details.")
        sys.exit(1)