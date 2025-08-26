#!/usr/bin/env python3
"""
Generate comprehensive Slack analysis summary report
Creates executive-focused markdown report of all findings
"""

import json
from pathlib import Path
from datetime import datetime

def generate_summary_report():
    """Generate comprehensive Slack analysis summary"""
    
    # Load metrics
    metrics_path = Path(__file__).parent / "slack_metrics.json"
    with open(metrics_path, 'r') as f:
        metrics = json.load(f)
    
    # Load visualization summary
    viz_summary_path = Path(__file__).parent.parent.parent / "visualizations" / "slack" / "visualization_summary.json"
    with open(viz_summary_path, 'r') as f:
        viz_summary = json.load(f)
    
    # Extract key data
    basic = metrics['analysis_summary']['basic_statistics']
    temporal = metrics['analysis_summary']['temporal_patterns']
    behavior = metrics['analysis_summary']['communication_behavior']
    collaboration = metrics['analysis_summary']['collaboration_patterns']
    strategic = metrics['analysis_summary']['strategic_communication']
    efficiency = metrics['analysis_summary']['efficiency_metrics']
    
    # Generate report
    report = f"""# Slack Communication Analysis Summary
## Ryan Marien Time Analysis Experiment

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Analysis Period:** {basic['total_days_analyzed']} days  
**Data Source:** Slack messages, channels, and user data  

---

## Executive Summary

Ryan's Slack communication patterns reveal a highly engaged executive with strong strategic focus but potential efficiency concerns around context switching and after-hours communication.

### Key Findings

- **High Communication Volume:** {basic['ryan_messages']:,} messages ({basic['ryan_message_percentage']}% of all activity)
- **Strategic Focus:** {strategic['strategic_percentage']}% of communication is strategic-level
- **Moderate After-Hours Activity:** {temporal['after_hours_percentage']}% of messages sent outside business hours
- **DM Preference:** {behavior['dm_preference_percentage']}% of messages are direct messages
- **Communication Efficiency Score:** {efficiency['communication_efficiency_score']}/100

---

## Detailed Analysis

### 1. Communication Volume & Distribution

**Total Messages Analyzed:** {basic['total_messages']:,}  
**Ryan's Messages:** {basic['ryan_messages']:,} ({basic['ryan_message_percentage']}%)  
**Daily Average:** {basic['ryan_avg_messages_per_day']} messages per day  
**Active Channels:** {basic['total_channels']} channels  

#### Channel Breakdown:
"""
    
    # Add channel breakdown
    for channel in basic['channel_breakdown']:
        report += f"- **{channel['channel']}:** {channel['ryan_messages']} messages ({channel['ryan_participation_pct']}% participation)\n"
    
    report += f"""

### 2. Temporal Communication Patterns

**Business Hours Messages:** {temporal['business_hours_messages']:,} ({100 - temporal['after_hours_percentage']:.1f}%)  
**After-Hours Messages:** {temporal['after_hours_messages']} ({temporal['after_hours_percentage']}%)  

#### Peak Activity Hours:
"""
    
    for peak in temporal['peak_hours']:
        report += f"- **{peak['hour']}:00:** {peak['messages']} messages\n"
    
    report += f"""
#### Daily Activity Patterns:
"""
    
    for day in temporal['daily_patterns']:
        report += f"- **{day['day']}:** {day['total_messages']} messages (avg: {day['avg_messages']})\n"
    
    report += f"""

### 3. Communication Behavior Analysis

**Message Preferences:**
- Direct Messages: {behavior['dm_messages']} ({behavior['dm_preference_percentage']}%)
- Channel Messages: {behavior['channel_messages']} ({100 - behavior['dm_preference_percentage']:.1f}%)

**Message Characteristics:**
- Average Message Length: {behavior['avg_message_length']} characters
- Thread Replies: {behavior['thread_replies']} messages
- Initial Messages: {behavior['initial_messages']} messages
- Thread Usage: {behavior['avg_thread_usage_pct']}%

### 4. Collaboration Patterns

**Context Switching:**
- Average Channels per Day: {collaboration['avg_channels_per_day']}
- Maximum Channels in One Day: {collaboration['max_channels_per_day']}
- High Context Switching Days: {collaboration.get('high_context_switching_days', 'N/A')} ({collaboration.get('high_switching_percentage', 'N/A')}%)

#### Top Communication Partners:
"""
    
    for collab in collaboration['top_collaborators'][:5]:
        report += f"- **{collab['name']}** ({collab['type']}): {collab['total_messages']} messages\n"
    
    report += f"""

### 5. Strategic vs Operational Communication

**Communication Category Breakdown:**
"""
    
    for category in strategic['category_breakdown']:
        report += f"- **{category['category']}:** {category['messages']} messages ({category['percentage']}%)\n"
    
    report += f"""

**Strategic Focus:**
- Strategic Messages: {strategic['strategic_messages']} ({strategic['strategic_percentage']}%)
- Operational Messages: {strategic['operational_messages']}
- Strategic-to-Operational Ratio: {strategic['strategic_messages']/max(strategic['operational_messages'], 1):.1f}:1

### 6. Communication Efficiency Analysis

**Overall Efficiency Score:** {efficiency['communication_efficiency_score']}/100

**Score Components:**
- DM Preference Score: {efficiency['score_breakdown']['dm_preference_score']}/100
- Time Management Score: {efficiency['score_breakdown']['time_management_score']}/100  
- Focus Score: {efficiency['score_breakdown']['focus_score']}/100

**Key Efficiency Metrics:**
- DM Efficiency Ratio: {efficiency['dm_efficiency_ratio']}
- Average Channel Switching: {efficiency['avg_channel_switching']} channels/day
- Average After-Hours %: {efficiency['avg_after_hours_pct']}%
- High After-Hours Days: {efficiency['high_after_hours_days']} ({efficiency['high_after_hours_percentage']}%)

---

## Executive Insights

"""
    
    for insight in metrics['executive_insights']:
        report += f"- {insight}\n"
    
    report += f"""

---

## Recommendations

"""
    
    for rec in metrics['recommendations']:
        report += f"- {rec}\n"
    
    report += f"""

---

## Visualization Assets

**Generated Visualizations:** {viz_summary['visualizations_created']} charts  
**Location:** `{Path(viz_summary['output_directory']).relative_to(Path(__file__).parent.parent.parent)}`

### Available Charts:
"""
    
    for viz in viz_summary['visualization_list']:
        report += f"- {viz}\n"
    
    report += f"""

---

## Technical Details

**Database:** DuckDB analytical database  
**Analytical Views:** 10 specialized views for communication pattern analysis  
**SQL Queries:** 18 queries across 4 categories (setup, views, metrics, performance)  
**Data Processing:** Python with pandas, matplotlib, plotly, and seaborn  

**Analysis Scripts:**
- `setup_duckdb.py` - Database initialization
- `create_views_fixed.py` - Analytical view creation  
- `generate_visualizations.py` - Chart generation
- `extract_metrics.py` - Comprehensive metrics extraction
- `export_sql_queries.py` - Query documentation

---

## Cross-Platform Correlation Opportunities

**Temporal Correlation Points:**
- Peak Slack activity hours: {', '.join([f"{peak['hour']}:00" for peak in temporal['peak_hours'][:3]])}
- Business hours activity: {100 - temporal['after_hours_percentage']:.1f}% alignment
- Daily patterns available for correlation with calendar meeting density

**Activity Level Correlation:**
- High-intensity communication days can be correlated with meeting volume
- After-hours Slack activity ({temporal['after_hours_percentage']}%) vs after-hours calendar events
- Context switching patterns can be mapped to meeting fragmentation

**Strategic Focus Correlation:**
- Strategic communication channels ({strategic['strategic_percentage']}%) vs strategic meeting topics
- Executive-level interactions vs leadership meeting patterns
- DM preference ({behavior['dm_preference_percentage']}%) vs 1:1 meeting frequency

---

*This analysis provides a comprehensive view of Ryan's Slack communication patterns as part of the broader time allocation analysis experiment. The findings should be considered alongside calendar and other productivity data for a complete executive efficiency assessment.*
"""
    
    # Save report
    report_path = Path(__file__).parent / "slack_analysis_summary.md"
    with open(report_path, 'w') as f:
        f.write(report)
    
    return report_path, len(report.split('\n'))

def main():
    """Generate the summary report"""
    print("📝 Generating comprehensive Slack analysis summary...")
    
    report_path, line_count = generate_summary_report()
    
    print(f"✅ Summary report generated successfully!")
    print(f"📄 File: {report_path}")
    print(f"📊 Lines: {line_count:,}")
    print(f"📁 Location: {report_path.relative_to(Path(__file__).parent.parent.parent)}")
    
    # Print file structure summary
    print(f"\n📋 Complete Slack Analytics Package:")
    analytics_dir = Path(__file__).parent
    files = list(analytics_dir.glob("*.py")) + list(analytics_dir.glob("*.json")) + list(analytics_dir.glob("*.sql")) + list(analytics_dir.glob("*.md"))
    
    for file in sorted(files):
        size_kb = file.stat().st_size / 1024
        print(f"   • {file.name} ({size_kb:.1f} KB)")
    
    print(f"\n🎯 Package Summary:")
    print(f"   • Database setup and 10 analytical views")
    print(f"   • 12 comprehensive visualizations")  
    print(f"   • 6 metric categories with executive insights")
    print(f"   • 18 documented SQL queries")
    print(f"   • Executive summary with recommendations")

if __name__ == "__main__":
    main()