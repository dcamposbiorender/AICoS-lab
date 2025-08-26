#!/usr/bin/env python3
"""
Extract comprehensive Slack metrics for Ryan's communication patterns
Generates detailed metrics JSON for executive analysis
"""

import duckdb
import json
from pathlib import Path
from datetime import datetime
import pandas as pd

# Database path
DB_PATH = Path(__file__).parent.parent.parent / "data" / "processed" / "duckdb" / "slack_analytics.db"

def extract_slack_metrics():
    """Extract comprehensive Slack metrics"""
    
    conn = duckdb.connect(str(DB_PATH))
    
    metrics = {
        'extraction_timestamp': datetime.now().isoformat(),
        'database_path': str(DB_PATH),
        'ryan_slack_id': 'UBL74SKU0',
        'analysis_summary': {}
    }
    
    print("📊 Extracting comprehensive Slack metrics...")
    
    # === BASIC STATISTICS ===
    print("   • Basic statistics...")
    basic_stats = {}
    
    # Total messages and Ryan's share
    total_result = conn.execute("""
        SELECT 
            COUNT(*) as total_messages,
            COUNT(CASE WHEN is_ryan_message THEN 1 END) as ryan_messages,
            COUNT(DISTINCT channel_id) as total_channels,
            COUNT(DISTINCT user_id) as total_users,
            COUNT(DISTINCT date) as total_days
        FROM slack_messages
    """).fetchone()
    
    basic_stats['total_messages'] = total_result[0]
    basic_stats['ryan_messages'] = total_result[1] 
    basic_stats['ryan_message_percentage'] = round(total_result[1] / total_result[0] * 100, 1)
    basic_stats['total_channels'] = total_result[2]
    basic_stats['total_users'] = total_result[3]
    basic_stats['total_days_analyzed'] = total_result[4]
    basic_stats['ryan_avg_messages_per_day'] = round(total_result[1] / total_result[4], 1)
    
    # === CHANNEL DISTRIBUTION ===
    print("   • Channel distribution...")
    channel_stats = conn.execute("""
        SELECT 
            channel_name,
            actual_total_messages,
            actual_ryan_messages,
            ryan_participation_pct,
            unique_participants,
            thread_messages,
            avg_message_length
        FROM v_channel_activity
        ORDER BY actual_total_messages DESC
    """).fetchall()
    
    basic_stats['channel_breakdown'] = [
        {
            'channel': row[0],
            'total_messages': row[1],
            'ryan_messages': row[2],
            'ryan_participation_pct': row[3],
            'participants': row[4],
            'thread_messages': row[5],
            'avg_message_length': round(row[6], 1) if row[6] else 0
        }
        for row in channel_stats
    ]
    
    # === TEMPORAL PATTERNS ===
    print("   • Temporal patterns...")
    temporal_stats = {}
    
    # Business hours vs after hours
    hours_breakdown = conn.execute("""
        SELECT 
            SUM(CASE WHEN is_business_hours AND is_ryan_message THEN 1 END) as business_hours,
            SUM(CASE WHEN is_after_hours AND is_ryan_message THEN 1 END) as after_hours,
            ROUND(SUM(CASE WHEN is_after_hours AND is_ryan_message THEN 1 END) * 100.0 / 
                  SUM(CASE WHEN is_ryan_message THEN 1 END), 1) as after_hours_pct
        FROM slack_messages
    """).fetchone()
    
    temporal_stats['business_hours_messages'] = hours_breakdown[0]
    temporal_stats['after_hours_messages'] = hours_breakdown[1] 
    temporal_stats['after_hours_percentage'] = hours_breakdown[2]
    
    # Peak hours analysis
    peak_hours = conn.execute("""
        SELECT hour, SUM(ryan_messages) as messages
        FROM v_peak_communication_hours
        WHERE activity_level = 'Peak Hour'
        GROUP BY hour
        ORDER BY messages DESC
        LIMIT 5
    """).fetchall()
    
    temporal_stats['peak_hours'] = [
        {'hour': row[0], 'messages': row[1]} for row in peak_hours
    ]
    
    # Day of week patterns
    daily_patterns = conn.execute("""
        SELECT 
            day_of_week,
            AVG(ryan_daily_messages) as avg_messages,
            SUM(ryan_daily_messages) as total_messages
        FROM v_communication_intensity
        GROUP BY day_of_week
        ORDER BY total_messages DESC
    """).fetchall()
    
    temporal_stats['daily_patterns'] = [
        {
            'day': row[0],
            'avg_messages': round(row[1], 1),
            'total_messages': row[2]
        }
        for row in daily_patterns
    ]
    
    # === COMMUNICATION BEHAVIOR ===
    print("   • Communication behavior...")
    behavior_stats = {}
    
    # DM vs Channel preference
    dm_preference = conn.execute("""
        SELECT 
            SUM(CASE WHEN is_dm AND is_ryan_message THEN 1 END) as dm_messages,
            SUM(CASE WHEN NOT is_dm AND is_ryan_message THEN 1 END) as channel_messages,
            ROUND(SUM(CASE WHEN is_dm AND is_ryan_message THEN 1 END) * 100.0 / 
                  SUM(CASE WHEN is_ryan_message THEN 1 END), 1) as dm_percentage
        FROM slack_messages
    """).fetchone()
    
    behavior_stats['dm_messages'] = dm_preference[0]
    behavior_stats['channel_messages'] = dm_preference[1]
    behavior_stats['dm_preference_percentage'] = dm_preference[2]
    
    # Thread participation
    thread_stats = conn.execute("""
        SELECT 
            SUM(ryan_thread_messages) as thread_replies,
            SUM(ryan_initial_messages) as initial_messages,
            AVG(thread_usage_pct) as avg_thread_usage_pct
        FROM v_thread_participation
    """).fetchone()
    
    behavior_stats['thread_replies'] = thread_stats[0] if thread_stats[0] else 0
    behavior_stats['initial_messages'] = thread_stats[1] if thread_stats[1] else 0
    behavior_stats['avg_thread_usage_pct'] = round(thread_stats[2], 1) if thread_stats[2] else 0
    
    # Message length analysis
    length_stats = conn.execute("""
        SELECT 
            AVG(CASE WHEN is_ryan_message THEN message_length END) as avg_ryan_length,
            AVG(CASE WHEN NOT is_ryan_message THEN message_length END) as avg_others_length,
            MAX(CASE WHEN is_ryan_message THEN message_length END) as max_ryan_length,
            MIN(CASE WHEN is_ryan_message AND message_length > 0 THEN message_length END) as min_ryan_length
        FROM slack_messages
    """).fetchone()
    
    behavior_stats['avg_message_length'] = round(length_stats[0], 1) if length_stats[0] else 0
    behavior_stats['others_avg_message_length'] = round(length_stats[1], 1) if length_stats[1] else 0
    behavior_stats['max_message_length'] = length_stats[2] if length_stats[2] else 0
    behavior_stats['min_message_length'] = length_stats[3] if length_stats[3] else 0
    
    # === COLLABORATION PATTERNS ===
    print("   • Collaboration patterns...")
    collaboration_stats = {}
    
    # Top collaborators
    top_collaborators = conn.execute("""
        SELECT 
            collaborator,
            interaction_type,
            SUM(total_messages) as messages,
            AVG(avg_messages_per_day) as avg_daily
        FROM v_collaboration_frequency
        GROUP BY collaborator, interaction_type
        ORDER BY messages DESC
        LIMIT 10
    """).fetchall()
    
    collaboration_stats['top_collaborators'] = [
        {
            'name': row[0],
            'type': row[1],
            'total_messages': row[2],
            'avg_daily': round(row[3], 1)
        }
        for row in top_collaborators
    ]
    
    # Context switching analysis
    context_switching = conn.execute("""
        SELECT 
            AVG(ryan_channels_active) as avg_channels_per_day,
            MAX(ryan_channels_active) as max_channels_per_day,
            COUNT(CASE WHEN ryan_channels_active >= 4 THEN 1 END) as high_switching_days,
            COUNT(*) as total_days
        FROM v_communication_intensity
        WHERE ryan_daily_messages > 0
    """).fetchone()
    
    collaboration_stats['avg_channels_per_day'] = round(context_switching[0], 1)
    collaboration_stats['max_channels_per_day'] = context_switching[1]
    collaboration_stats['high_context_switching_days'] = context_switching[2]
    collaboration_stats['high_switching_percentage'] = round(context_switching[2] / context_switching[3] * 100, 1)
    
    # === STRATEGIC COMMUNICATION ANALYSIS ===
    print("   • Strategic communication...")
    strategic_stats = {}
    
    strategic_breakdown = conn.execute("""
        SELECT 
            communication_category,
            SUM(ryan_messages) as messages,
            AVG(ryan_avg_message_length) as avg_length
        FROM v_strategic_vs_operational
        GROUP BY communication_category
        ORDER BY messages DESC
    """).fetchall()
    
    strategic_stats['category_breakdown'] = [
        {
            'category': row[0],
            'messages': row[1],
            'avg_message_length': round(row[2], 1) if row[2] else 0,
            'percentage': round(row[1] / basic_stats['ryan_messages'] * 100, 1)
        }
        for row in strategic_breakdown
    ]
    
    # Calculate strategic vs operational ratio
    strategic_messages = sum(row[1] for row in strategic_breakdown 
                           if 'Strategic' in row[0])
    operational_messages = sum(row[1] for row in strategic_breakdown 
                             if row[0] == 'Operational')
    
    strategic_stats['strategic_messages'] = strategic_messages
    strategic_stats['operational_messages'] = operational_messages
    strategic_stats['strategic_percentage'] = round(strategic_messages / basic_stats['ryan_messages'] * 100, 1)
    
    # === EFFICIENCY METRICS ===
    print("   • Efficiency metrics...")
    efficiency_stats = {}
    
    # Communication efficiency indicators
    efficiency_data = conn.execute("""
        SELECT 
            AVG(dm_count * 1.0 / (ryan_daily_messages + 0.001)) as dm_efficiency,
            AVG(ryan_channels_active) as avg_channel_switching,
            AVG(after_hours_pct) as avg_after_hours_pct,
            COUNT(CASE WHEN after_hours_pct > 25 THEN 1 END) as high_after_hours_days,
            COUNT(*) as total_days_with_activity
        FROM v_communication_intensity
        WHERE ryan_daily_messages > 0
    """).fetchone()
    
    efficiency_stats['dm_efficiency_ratio'] = round(efficiency_data[0], 2)
    efficiency_stats['avg_channel_switching'] = round(efficiency_data[1], 1)
    efficiency_stats['avg_after_hours_pct'] = round(efficiency_data[2], 1)
    efficiency_stats['high_after_hours_days'] = efficiency_data[3]
    efficiency_stats['high_after_hours_percentage'] = round(efficiency_data[3] / efficiency_data[4] * 100, 1)
    
    # Calculate overall communication efficiency score (0-100)
    # Based on: DM preference (higher=better), low after-hours (higher=better), 
    # focused channels (lower switching=better)
    dm_score = min(100, behavior_stats['dm_preference_percentage'] * 2)  # Max 100 if 50% DMs
    time_score = max(0, 100 - efficiency_stats['avg_after_hours_pct'] * 2)  # Lower after-hours = better
    focus_score = max(0, 100 - (efficiency_stats['avg_channel_switching'] - 1) * 20)  # Fewer channels = better focus
    
    efficiency_stats['communication_efficiency_score'] = round((dm_score + time_score + focus_score) / 3, 1)
    efficiency_stats['score_breakdown'] = {
        'dm_preference_score': round(dm_score, 1),
        'time_management_score': round(time_score, 1),
        'focus_score': round(focus_score, 1)
    }
    
    # === COMPILE FINAL METRICS ===
    metrics['analysis_summary'] = {
        'basic_statistics': basic_stats,
        'temporal_patterns': temporal_stats,
        'communication_behavior': behavior_stats,
        'collaboration_patterns': collaboration_stats,
        'strategic_communication': strategic_stats,
        'efficiency_metrics': efficiency_stats
    }
    
    # === EXECUTIVE INSIGHTS ===
    print("   • Executive insights...")
    insights = []
    
    # Key insights based on data
    if basic_stats['ryan_message_percentage'] > 50:
        insights.append(f"High communication volume: Ryan generates {basic_stats['ryan_message_percentage']}% of all messages")
    
    if temporal_stats['after_hours_percentage'] > 20:
        insights.append(f"After-hours communication concern: {temporal_stats['after_hours_percentage']}% of messages sent outside business hours")
    
    if behavior_stats['dm_preference_percentage'] > 40:
        insights.append(f"Strong DM preference: {behavior_stats['dm_preference_percentage']}% of messages are direct messages")
    
    if strategic_stats['strategic_percentage'] > 60:
        insights.append(f"Strategic focus: {strategic_stats['strategic_percentage']}% of communication is strategic")
    
    if collaboration_stats['avg_channels_per_day'] > 3:
        insights.append(f"High context switching: Active in {collaboration_stats['avg_channels_per_day']} channels daily on average")
    
    metrics['executive_insights'] = insights
    
    # === RECOMMENDATIONS ===
    recommendations = []
    
    if temporal_stats['after_hours_percentage'] > 15:
        recommendations.append("Consider implementing communication boundaries to reduce after-hours messaging")
    
    if collaboration_stats['avg_channels_per_day'] > 3:
        recommendations.append("Consolidate communication channels to reduce context switching")
    
    if behavior_stats['dm_preference_percentage'] < 30:
        recommendations.append("Increase use of direct messages for focused 1:1 conversations")
    
    if basic_stats['ryan_avg_messages_per_day'] > 15:
        recommendations.append("Consider batch processing messages to improve focus time")
    
    metrics['recommendations'] = recommendations
    
    conn.close()
    
    print(f"   ✅ Extracted {len(metrics['analysis_summary'])} metric categories")
    return metrics

def main():
    """Main execution"""
    print("🔍 Extracting comprehensive Slack metrics...")
    
    metrics = extract_slack_metrics()
    
    # Save metrics
    metrics_path = Path(__file__).parent / "slack_metrics.json"
    with open(metrics_path, 'w') as f:
        json.dump(metrics, f, indent=2)
    
    print(f"\n📊 Slack metrics extracted successfully!")
    print(f"📄 Saved to: {metrics_path}")
    
    # Print key findings
    basic = metrics['analysis_summary']['basic_statistics']
    temporal = metrics['analysis_summary']['temporal_patterns']
    behavior = metrics['analysis_summary']['communication_behavior']
    efficiency = metrics['analysis_summary']['efficiency_metrics']
    
    print(f"\n🎯 KEY FINDINGS:")
    print(f"   • Total messages analyzed: {basic['total_messages']:,}")
    print(f"   • Ryan's messages: {basic['ryan_messages']:,} ({basic['ryan_message_percentage']}%)")
    print(f"   • Average daily messages: {basic['ryan_avg_messages_per_day']}")
    print(f"   • After-hours communication: {temporal['after_hours_percentage']}%")
    print(f"   • DM preference: {behavior['dm_preference_percentage']}%")
    print(f"   • Strategic communication: {metrics['analysis_summary']['strategic_communication']['strategic_percentage']}%")
    print(f"   • Communication efficiency score: {efficiency['communication_efficiency_score']}/100")
    
    if metrics['executive_insights']:
        print(f"\n💡 EXECUTIVE INSIGHTS:")
        for insight in metrics['executive_insights']:
            print(f"   • {insight}")
    
    if metrics['recommendations']:
        print(f"\n📋 RECOMMENDATIONS:")
        for rec in metrics['recommendations']:
            print(f"   • {rec}")

if __name__ == "__main__":
    main()