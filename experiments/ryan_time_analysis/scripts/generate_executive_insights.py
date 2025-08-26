#!/usr/bin/env python3
"""
Executive Insights Generator for Ryan Marien Time Analysis

This script processes the 6-month calendar analysis to generate:
1. Executive summary of key findings
2. Quantified "busy trap" indicators
3. Specific time optimization opportunities 
4. Actionable delegation recommendations
5. Schedule restructuring strategy

Output: Executive report with data-driven recommendations
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
import math

# Experiment paths
EXPERIMENT_ROOT = Path(__file__).parent.parent
REPORTS_PATH = EXPERIMENT_ROOT / "reports"
OUTPUT_PATH = EXPERIMENT_ROOT / "insights"
LOG_PATH = EXPERIMENT_ROOT / "experiment_log.md"

def log_insight_update(session_info: str):
    """Append insight update to experiment log"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"\n### {timestamp}\n{session_info}\n"
    
    with open(LOG_PATH, 'a') as f:
        f.write(log_entry)
    print(f"📝 {session_info}")

def load_analysis_results() -> Dict[str, Any]:
    """Load the 6-month pattern analysis results"""
    analysis_file = REPORTS_PATH / "6_month_pattern_analysis.json"
    
    if not analysis_file.exists():
        raise FileNotFoundError(f"Analysis results not found: {analysis_file}")
    
    with open(analysis_file, 'r') as f:
        return json.load(f)

def calculate_busy_trap_score(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate a comprehensive "Busy Trap" score based on multiple indicators
    
    Returns:
        Dict with busy trap metrics and score breakdown
    """
    time_trends = analysis['time_trends']['monthly_trends']
    switching_data = analysis.get('context_switching', {}).get('monthly_patterns', {})
    
    # Indicators of "busy trap":
    # 1. High meeting volume (meetings per day)
    # 2. High back-to-back meeting ratio
    # 3. Short meeting prevalence
    # 4. High context switching
    # 5. Increasing trend over time
    
    indicators = {}
    
    # 1. Meeting volume analysis
    total_meetings = sum(month['total_meetings'] for month in time_trends.values())
    total_months = len(time_trends)
    avg_meetings_per_month = total_meetings / total_months
    avg_meetings_per_day = avg_meetings_per_month / 22  # ~22 work days per month
    
    # 2. Back-to-back meeting ratio
    total_back_to_back = sum(month['back_to_back'] for month in time_trends.values())
    back_to_back_ratio = (total_back_to_back / total_meetings) * 100
    
    # 3. Short meeting analysis (≤15 minutes)
    total_short = sum(month['short_meetings'] for month in time_trends.values())
    short_meeting_ratio = (total_short / total_meetings) * 100
    
    # 4. Average meeting duration trend
    monthly_durations = [month['avg_duration'] for month in time_trends.values()]
    avg_duration = sum(monthly_durations) / len(monthly_durations)
    
    # 5. Meeting volume trend (comparing first 3 vs last 3 months)
    months_sorted = sorted(time_trends.keys())
    early_months = months_sorted[:3]
    late_months = months_sorted[-3:]
    
    early_avg = sum(time_trends[m]['total_meetings'] for m in early_months) / 3
    late_avg = sum(time_trends[m]['total_meetings'] for m in late_months) / 3
    volume_increase = ((late_avg - early_avg) / early_avg) * 100
    
    # Calculate component scores (0-100, higher = more problematic)
    scores = {}
    
    # Meeting volume score (>6 meetings/day = high, >8 = extreme)
    if avg_meetings_per_day <= 4:
        scores['volume'] = 10
    elif avg_meetings_per_day <= 6:
        scores['volume'] = 40
    elif avg_meetings_per_day <= 8:
        scores['volume'] = 70
    else:
        scores['volume'] = 90
    
    # Back-to-back ratio score
    if back_to_back_ratio <= 20:
        scores['back_to_back'] = 10
    elif back_to_back_ratio <= 40:
        scores['back_to_back'] = 30
    elif back_to_back_ratio <= 60:
        scores['back_to_back'] = 60
    else:
        scores['back_to_back'] = 90
    
    # Short meeting score (high fragmentation indicator)
    if short_meeting_ratio <= 5:
        scores['fragmentation'] = 10
    elif short_meeting_ratio <= 10:
        scores['fragmentation'] = 30
    elif short_meeting_ratio <= 15:
        scores['fragmentation'] = 60
    else:
        scores['fragmentation'] = 85
    
    # Duration efficiency (very short or very long both problematic)
    if 45 <= avg_duration <= 60:  # Sweet spot
        scores['duration_efficiency'] = 20
    elif 30 <= avg_duration <= 75:
        scores['duration_efficiency'] = 40
    else:
        scores['duration_efficiency'] = 70
    
    # Trend score (increasing volume is problematic)
    if volume_increase <= 0:
        scores['trend'] = 20
    elif volume_increase <= 20:
        scores['trend'] = 50
    else:
        scores['trend'] = 80
    
    # Overall busy trap score (weighted average)
    weights = {
        'volume': 0.3,
        'back_to_back': 0.25,
        'fragmentation': 0.2,
        'duration_efficiency': 0.15,
        'trend': 0.1
    }
    
    overall_score = sum(scores[component] * weights[component] for component in scores)
    
    return {
        'overall_busy_trap_score': round(overall_score, 1),
        'component_scores': scores,
        'raw_metrics': {
            'avg_meetings_per_day': round(avg_meetings_per_day, 1),
            'back_to_back_ratio': round(back_to_back_ratio, 1),
            'short_meeting_ratio': round(short_meeting_ratio, 1),
            'avg_meeting_duration': round(avg_duration, 1),
            'volume_increase_6months': round(volume_increase, 1)
        },
        'interpretation': {
            'score_range': '0-100',
            'severity': 'CRITICAL' if overall_score >= 70 else 'HIGH' if overall_score >= 50 else 'MODERATE' if overall_score >= 30 else 'LOW'
        }
    }

def identify_optimization_opportunities(analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Identify specific time optimization opportunities with quantified impact
    
    Returns:
        List of optimization opportunities with time savings estimates
    """
    time_trends = analysis['time_trends']['monthly_trends']
    collaboration = analysis.get('collaboration_network', {}).get('monthly_collaboration', {})
    
    opportunities = []
    
    # 1. Back-to-back meeting optimization
    total_back_to_back = sum(month['back_to_back'] for month in time_trends.values())
    if total_back_to_back > 0:
        # Assume 10 minutes buffer per back-to-back meeting could be recovered
        weekly_savings = (total_back_to_back / 24) * 10  # 24 weeks of data, 10 min per meeting
        opportunities.append({
            'opportunity': 'Add 15-minute buffers between meetings',
            'current_issue': f'{total_back_to_back} back-to-back meetings in 6 months',
            'weekly_time_savings': f'{weekly_savings:.0f} minutes',
            'implementation': 'Block 15-minute buffers in calendar, decline overlapping meetings',
            'priority': 'HIGH',
            'effort': 'LOW'
        })
    
    # 2. Short meeting consolidation
    total_short = sum(month['short_meetings'] for month in time_trends.values())
    if total_short > 50:
        # Assume 30% of short meetings could be consolidated or handled async
        consolidatable = total_short * 0.3
        # Each short meeting + context switch costs ~25 minutes (15 min meeting + 10 min switching)
        weekly_savings = (consolidatable / 24) * 25
        opportunities.append({
            'opportunity': 'Consolidate or eliminate short meetings',
            'current_issue': f'{total_short} meetings ≤15 minutes in 6 months',
            'weekly_time_savings': f'{weekly_savings:.0f} minutes',
            'implementation': 'Batch similar topics, use async communication for quick updates',
            'priority': 'MEDIUM',
            'effort': 'MEDIUM'
        })
    
    # 3. Deep work protection
    total_deep_work = sum(month['meeting_types'].get('deep_work', 0) for month in time_trends.values())
    total_meetings = sum(month['total_meetings'] for month in time_trends.values())
    deep_work_ratio = (total_deep_work / total_meetings) * 100
    
    if deep_work_ratio < 20:  # Less than 20% deep work blocks
        opportunities.append({
            'opportunity': 'Increase protected deep work blocks',
            'current_issue': f'Only {deep_work_ratio:.1f}% of calendar is protected deep work',
            'weekly_time_savings': 'N/A - Quality improvement',
            'implementation': 'Block 2-4 hour chunks daily, decline meetings during these times',
            'priority': 'CRITICAL',
            'effort': 'HIGH'
        })
    
    # 4. Recurring meeting audit
    # Look for patterns in collaboration data to identify over-meeting relationships
    if collaboration:
        # Find people Ryan meets with most frequently
        frequent_collaborators = []
        for month_data in collaboration.values():
            for collab, count in month_data.get('top_collaborators', [])[:5]:
                frequent_collaborators.append((collab, count))
        
        # Aggregate by person
        collab_totals = {}
        for collab, count in frequent_collaborators:
            collab_totals[collab] = collab_totals.get(collab, 0) + count
        
        top_collabs = sorted(collab_totals.items(), key=lambda x: x[1], reverse=True)[:3]
        
        if top_collabs:
            top_name = top_collabs[0][0].split('@')[0]
            top_count = top_collabs[0][1]
            weekly_meetings = top_count / 24  # 24 weeks
            
            opportunities.append({
                'opportunity': 'Optimize recurring meetings with top collaborators',
                'current_issue': f'~{weekly_meetings:.1f} weekly meetings with {top_name}',
                'weekly_time_savings': f'{weekly_meetings * 15:.0f} minutes (reducing frequency/duration)',
                'implementation': 'Shift to biweekly, reduce duration, or combine meetings',
                'priority': 'MEDIUM',
                'effort': 'LOW'
            })
    
    # 5. Large meeting delegation
    total_large = sum(collab.get('large_meetings', 0) for collab in collaboration.values())
    if total_large > 50:
        # Assume Ryan could delegate 30% of large meetings
        delegatable = total_large * 0.3
        # Large meetings average ~90 minutes
        weekly_savings = (delegatable / 24) * 90
        
        opportunities.append({
            'opportunity': 'Delegate attendance at large meetings',
            'current_issue': f'{total_large} meetings with >5 attendees in 6 months',
            'weekly_time_savings': f'{weekly_savings:.0f} minutes',
            'implementation': 'Send team members as representatives, get summary reports',
            'priority': 'MEDIUM',
            'effort': 'LOW'
        })
    
    return opportunities

def generate_executive_summary(analysis: Dict[str, Any], busy_trap_score: Dict[str, Any], opportunities: List[Dict[str, Any]]) -> str:
    """
    Generate executive summary with key findings and recommendations
    
    Returns:
        Markdown formatted executive summary
    """
    time_trends = analysis['time_trends']
    total_events = analysis['total_events_analyzed']
    period = analysis['data_period']
    
    # Calculate total time savings potential
    total_weekly_savings = 0
    for opp in opportunities:
        savings_str = opp.get('weekly_time_savings', '0')
        if savings_str != 'N/A - Quality improvement' and 'minutes' in savings_str:
            minutes = int(savings_str.split(' ')[0])
            total_weekly_savings += minutes
    
    total_hours_savings = total_weekly_savings / 60
    
    summary = f"""# Ryan Marien Time Analysis - Executive Summary

## Analysis Overview
**Period**: {period}  
**Total Events Analyzed**: {total_events:,}  
**Analysis Date**: {datetime.now().strftime('%B %d, %Y')}

## Key Findings

### 🚨 Busy Trap Assessment
**Overall Score**: {busy_trap_score['overall_busy_trap_score']}/100 ({busy_trap_score['interpretation']['severity']} severity)

**Critical Indicators:**
- **{busy_trap_score['raw_metrics']['avg_meetings_per_day']} meetings per day** (sustainable threshold: 4-6)
- **{busy_trap_score['raw_metrics']['back_to_back_ratio']:.1f}% back-to-back meetings** (healthy: <30%)
- **{busy_trap_score['raw_metrics']['short_meeting_ratio']:.1f}% meetings ≤15 minutes** (fragmentation indicator)
- **{busy_trap_score['raw_metrics']['volume_increase_6months']:.1f}% meeting volume increase** over 6 months

### 📈 Time Allocation Trends
- **Peak month**: {time_trends['summary']['peak_meeting_month']} ({time_trends['summary']['peak_meeting_count']} meetings)
- **Average**: {time_trends['summary']['avg_monthly_meetings']:.0f} meetings per month
- **Weekly average**: ~{time_trends['summary']['avg_monthly_meetings']/4:.0f} meetings per week

## Optimization Opportunities

**Total Weekly Time Savings Potential: {total_hours_savings:.1f} hours**

"""
    
    # Add detailed opportunities
    for i, opp in enumerate(opportunities, 1):
        priority_emoji = "🔴" if opp['priority'] == 'CRITICAL' else "🟡" if opp['priority'] == 'HIGH' else "🟢"
        
        summary += f"""### {priority_emoji} {i}. {opp['opportunity']}
**Issue**: {opp['current_issue']}  
**Time Savings**: {opp['weekly_time_savings']}  
**Implementation**: {opp['implementation']}  
**Priority**: {opp['priority']} | **Effort**: {opp['effort']}

"""
    
    summary += f"""## Strategic Recommendations

### Immediate Actions (Next 2 weeks)
1. **Block calendar buffers**: Add 15-minute buffers between all meetings
2. **Audit recurring meetings**: Review top 10 recurring meetings for necessity
3. **Establish "No Meeting" blocks**: Protect 2-hour deep work chunks daily

### Medium-term Changes (Next month)
1. **Delegation strategy**: Identify meetings where team members can represent Ryan
2. **Communication protocols**: Shift routine updates to async channels
3. **Meeting efficiency**: Implement 25/50-minute default durations

### Long-term Transformation (Next quarter)
1. **Calendar architecture**: Redesign weekly template with protected time
2. **Team capacity building**: Train team members to handle routine decisions
3. **Executive presence optimization**: Focus Ryan's time on high-impact strategic work

## Expected Impact
- **Immediate**: {total_hours_savings:.1f} hours/week returned for strategic work
- **3-month**: Reduced context switching, improved decision quality
- **6-month**: Sustainable executive schedule, better team autonomy

*This analysis provides objective, data-driven insights into Ryan's calendar patterns from {period}. All recommendations are based on actual meeting data and proven optimization strategies.*
"""
    
    return summary

def main():
    """Generate executive insights and recommendations"""
    print("🎯 Generating executive insights for Ryan Marien time analysis")
    
    try:
        # Load analysis results
        log_insight_update("📊 Loading 6-month pattern analysis results")
        analysis = load_analysis_results()
        
        # Calculate busy trap score
        log_insight_update("🚨 Calculating busy trap indicators")
        busy_trap_score = calculate_busy_trap_score(analysis)
        
        # Identify optimization opportunities
        log_insight_update("💡 Identifying optimization opportunities")
        opportunities = identify_optimization_opportunities(analysis)
        
        # Generate executive summary
        log_insight_update("📝 Generating executive summary")
        executive_summary = generate_executive_summary(analysis, busy_trap_score, opportunities)
        
        # Save results
        OUTPUT_PATH.mkdir(exist_ok=True)
        
        # Save detailed insights
        insights = {
            'busy_trap_assessment': busy_trap_score,
            'optimization_opportunities': opportunities,
            'analysis_metadata': {
                'generated_at': datetime.now().isoformat(),
                'source_analysis': '6_month_pattern_analysis.json',
                'total_events': analysis['total_events_analyzed'],
                'period': analysis['data_period']
            }
        }
        
        insights_file = OUTPUT_PATH / "executive_insights.json"
        with open(insights_file, 'w') as f:
            json.dump(insights, f, indent=2)
        
        # Save executive summary
        summary_file = OUTPUT_PATH / "executive_summary.md"
        with open(summary_file, 'w') as f:
            f.write(executive_summary)
        
        print(f"✅ Executive insights generated!")
        print(f"   Busy Trap Score: {busy_trap_score['overall_busy_trap_score']}/100 ({busy_trap_score['interpretation']['severity']})")
        print(f"   Optimization Opportunities: {len(opportunities)}")
        print(f"   Executive Summary: {summary_file}")
        print(f"   Detailed Insights: {insights_file}")
        
        # Calculate and report total potential savings
        total_weekly_minutes = sum(
            int(opp['weekly_time_savings'].split()[0]) 
            for opp in opportunities 
            if opp['weekly_time_savings'] != 'N/A - Quality improvement' and 'minutes' in opp['weekly_time_savings']
        )
        
        log_insight_update(f"✅ Executive insights complete")
        log_insight_update(f"🚨 Busy Trap Score: {busy_trap_score['overall_busy_trap_score']}/100")
        log_insight_update(f"⏰ Weekly time savings potential: {total_weekly_minutes/60:.1f} hours")
        
    except Exception as e:
        print(f"❌ Insight generation failed: {e}")
        log_insight_update(f"❌ Executive insight generation failed: {e}")
        raise

if __name__ == "__main__":
    main()