#!/usr/bin/env python3
"""
Comprehensive Workstream Insights Generator

Combines analysis from Slack, Calendar, and Drive to generate actionable insights
about where David should focus his time based on actual vs intended workstream allocation.

Key Features:
- Cross-platform workstream analysis
- Goal alignment assessment
- Priority recommendations based on data
- Action item extraction and prioritization
- Weekly focus recommendations

Usage:
    python generate_comprehensive_insights.py
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any
from collections import defaultdict, Counter
import re

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# David's stated workstream goals and priorities
WORKSTREAM_GOALS = {
    "gtm_efficiency": {
        "90_day_goals": [
            "Increase productivity per BDR by 40%", 
            "Increase productivity per AE by 30%",
            "Increase productivity per CSM by 30%",
            "Double pipeline per quarter"
        ],
        "12_month_goals": [
            "Increase productivity per BDR by 40%, AE by 30%, CSM by 30%",
            "Double pipeline per quarter, reduce churn"
        ],
        "priority": "HIGH",
        "thesis": "Productivity per GTM role is subpar for assisted sales"
    },
    "data_platform": {
        "90_day_goals": [
            "Understand and organize data for AI tooling use",
            "Scope end-user / customer data clarity project - build MVP"
        ],
        "12_month_goals": [
            "End-user / customer data clarity project yields 6 tests and increase in MAU by X, ARR by Y"
        ],
        "priority": "MEDIUM",
        "thesis": "Data is underleveraged; goal is to make it self-serve, signal-rich, and AI-ready"
    },
    "icp_expansion": {
        "90_day_goals": [
            "Outline GTM expansion opportunities - run 3 tests"
        ],
        "12_month_goals": [
            "Expand buyer ICPs to increase SAM (1-2 proven personas with $1M ARR)"
        ],
        "priority": "MEDIUM", 
        "thesis": "TAM constrained by existing ICPs; new personas must be discovered"
    },
    "ai_transformation": {
        "90_day_goals": [
            "With Katya and Jon, build out AI governance and 'citizen developer approach'"
        ],
        "12_month_goals": [
            "Test new org systems, ways to run company"
        ],
        "priority": "MEDIUM",
        "thesis": "BioRender should operate like a modern, agentic company"
    },
    "ai_bizops_team": {
        "90_day_goals": [
            "Build plan to reduce cost base by $2M+"
        ],
        "12_month_goals": [
            "Built 'ai biz-ops team'"
        ],
        "priority": "MEDIUM",
        "thesis": "Cross-functional 'GTM engineers' as automation architects"
    },
    "cost_optimization": {
        "90_day_goals": [
            "Build plan to reduce cost base by $2M+"
        ],
        "12_month_goals": [
            "Reduce cost base by $2M compared to plan"
        ],
        "priority": "HIGH",
        "thesis": "Reduce cost base by $2M+ across GTM, product, and SG&A"
    }
}

def load_analysis_data(data_extraction_path: Path) -> Dict[str, Any]:
    """Load all analysis data from previous steps"""
    data = {}
    
    files_to_load = [
        ("slack", "slack_dms_analysis.json"),
        ("calendar", "calendar_analysis.json"), 
        ("drive", "drive_activity_analysis.json")
    ]
    
    for key, filename in files_to_load:
        file_path = data_extraction_path / filename
        if file_path.exists():
            with open(file_path, 'r') as f:
                data[key] = json.load(f)
        else:
            print(f"Warning: {filename} not found")
            data[key] = {}
    
    return data

def calculate_workstream_allocation(data: Dict[str, Any]) -> Dict[str, Dict[str, float]]:
    """Calculate time/attention allocation across workstreams from all data sources"""
    
    allocation = {}
    
    # Calendar time allocation (most reliable for time spent)
    calendar_data = data.get('calendar', {}).get('insights', {})
    if calendar_data:
        allocation['calendar_time_percent'] = calendar_data.get('time_allocation_percentage', {})
    
    # Slack message allocation
    slack_data = data.get('slack', {}).get('workstream_mapping', {})
    if slack_data:
        total_messages = sum(ws_data.get('messages', 0) for ws_data in slack_data.values())
        if total_messages > 0:
            allocation['slack_messages_percent'] = {
                ws: (ws_data.get('messages', 0) / total_messages * 100)
                for ws, ws_data in slack_data.items()
            }
    
    # Drive document allocation
    drive_data = data.get('drive', {}).get('insights', {})
    if drive_data:
        doc_distribution = drive_data.get('workstream_document_distribution', {})
        total_docs = sum(doc_distribution.values())
        if total_docs > 0:
            allocation['drive_documents_percent'] = {
                ws: (count / total_docs * 100)
                for ws, count in doc_distribution.items()
            }
    
    return allocation

def identify_key_stakeholders(data: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    """Identify key stakeholders by workstream across all platforms"""
    
    stakeholders_by_workstream = defaultdict(lambda: defaultdict(int))
    
    # From Slack conversations
    slack_data = data.get('slack', {}).get('workstream_mapping', {})
    for workstream, ws_data in slack_data.items():
        for participant in ws_data.get('participants', []):
            stakeholders_by_workstream[workstream][participant] += ws_data.get('messages', 0)
    
    # From Calendar meetings
    calendar_data = data.get('calendar', {}).get('insights', {})
    if calendar_data:
        for stakeholder, meeting_count in calendar_data.get('most_frequent_stakeholders', []):
            # Distribute based on workstream time allocation
            time_allocation = calendar_data.get('time_allocation_percentage', {})
            for workstream, time_percent in time_allocation.items():
                weighted_meetings = meeting_count * (time_percent / 100)
                stakeholders_by_workstream[workstream][stakeholder] += weighted_meetings
    
    # Convert to ranked lists
    ranked_stakeholders = {}
    for workstream, stakeholder_scores in stakeholders_by_workstream.items():
        ranked_stakeholders[workstream] = [
            {'email': stakeholder, 'interaction_score': score}
            for stakeholder, score in sorted(stakeholder_scores.items(), 
                                           key=lambda x: x[1], reverse=True)[:5]
        ]
    
    return ranked_stakeholders

def assess_goal_alignment(allocation: Dict[str, Dict[str, float]]) -> Dict[str, Any]:
    """Assess how actual time allocation aligns with stated goals"""
    
    # Get calendar allocation as primary time measure
    actual_allocation = allocation.get('calendar_time_percent', {})
    
    alignment_assessment = {}
    
    for workstream, goals in WORKSTREAM_GOALS.items():
        actual_percent = actual_allocation.get(workstream, 0)
        priority = goals['priority']
        
        # Expected allocation based on priority
        expected_ranges = {
            'HIGH': (25, 40),  # High priority should get 25-40% of time
            'MEDIUM': (10, 25),  # Medium priority should get 10-25% of time  
            'LOW': (0, 10)     # Low priority should get 0-10% of time
        }
        
        expected_min, expected_max = expected_ranges.get(priority, (0, 100))
        
        # Assess alignment
        if actual_percent < expected_min:
            alignment = "UNDER_ALLOCATED"
            gap = expected_min - actual_percent
        elif actual_percent > expected_max:
            alignment = "OVER_ALLOCATED" 
            gap = actual_percent - expected_max
        else:
            alignment = "WELL_ALIGNED"
            gap = 0
        
        alignment_assessment[workstream] = {
            'actual_percent': actual_percent,
            'expected_range': f"{expected_min}-{expected_max}%",
            'priority': priority,
            'alignment': alignment,
            'gap_percent': gap,
            'goals': goals['90_day_goals']
        }
    
    return alignment_assessment

def identify_high_priority_actions(data: Dict[str, Any], alignment: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Identify high priority actions based on analysis"""
    
    actions = []
    
    # 1. Address under-allocated high priority workstreams
    for workstream, assessment in alignment.items():
        if assessment['alignment'] == 'UNDER_ALLOCATED' and assessment['priority'] == 'HIGH':
            actions.append({
                'type': 'INCREASE_FOCUS',
                'workstream': workstream,
                'priority': 'HIGH',
                'description': f"Increase focus on {workstream} - currently {assessment['actual_percent']:.1f}% vs expected {assessment['expected_range']}",
                'suggested_actions': [
                    f"Schedule more meetings with {workstream} stakeholders",
                    f"Review active documents in {workstream}",
                    f"Block calendar time for {workstream} deep work"
                ]
            })
    
    # 2. Identify missing stakeholder engagement
    stakeholders = identify_key_stakeholders(data)
    
    for workstream, workstream_stakeholders in stakeholders.items():
        if len(workstream_stakeholders) < 2 and workstream != 'unclassified':
            actions.append({
                'type': 'INCREASE_STAKEHOLDER_ENGAGEMENT',
                'workstream': workstream,
                'priority': 'MEDIUM',
                'description': f"Limited stakeholder engagement in {workstream}",
                'suggested_actions': [
                    f"Schedule 1:1s with {workstream} team members",
                    f"Join relevant {workstream} meetings",
                    f"Review {workstream} documentation and provide input"
                ]
            })
    
    # 3. Identify recent document activity requiring attention
    drive_data = data.get('drive', {}).get('insights', {})
    if drive_data:
        top_active_docs = drive_data.get('top_active_documents', [])[:5]
        for doc in top_active_docs:
            if doc['activity']['activity_score'] > 6:  # High activity threshold
                actions.append({
                    'type': 'REVIEW_DOCUMENT',
                    'workstream': doc['primary_workstream'],
                    'priority': 'MEDIUM',
                    'description': f"Review high-activity document: {doc['name'][:50]}...",
                    'document_url': doc.get('web_view_link', ''),
                    'suggested_actions': [
                        "Review recent changes",
                        "Provide input or feedback", 
                        "Ensure alignment with workstream goals"
                    ]
                })
    
    return sorted(actions, key=lambda x: {'HIGH': 3, 'MEDIUM': 2, 'LOW': 1}[x['priority']], reverse=True)

def generate_weekly_recommendations(data: Dict[str, Any], alignment: Dict[str, Any], actions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate specific weekly focus recommendations"""
    
    stakeholders = identify_key_stakeholders(data)
    
    recommendations = {
        'focus_areas': [],
        'key_meetings_to_schedule': [],
        'documents_to_review': [],
        'people_to_connect_with': [],
        'time_allocation_adjustments': []
    }
    
    # Focus areas based on under-allocation
    for workstream, assessment in alignment.items():
        if assessment['alignment'] == 'UNDER_ALLOCATED':
            recommendations['focus_areas'].append({
                'workstream': workstream,
                'current_percent': assessment['actual_percent'],
                'target_increase': f"+{assessment['gap_percent']:.1f}%",
                'specific_goals': assessment['goals'][:2]  # Top 2 goals
            })
    
    # Key people to connect with
    for workstream in recommendations['focus_areas']:
        workstream_name = workstream['workstream']
        if workstream_name in stakeholders:
            top_stakeholders = stakeholders[workstream_name][:3]
            for stakeholder in top_stakeholders:
                recommendations['people_to_connect_with'].append({
                    'email': stakeholder['email'],
                    'workstream': workstream_name,
                    'reason': 'Key stakeholder for under-allocated workstream',
                    'suggested_frequency': 'Weekly 1:1' if stakeholder['interaction_score'] > 10 else 'Bi-weekly check-in'
                })
    
    # Documents to review from recent activity
    drive_data = data.get('drive', {}).get('insights', {})
    if drive_data:
        recent_by_workstream = drive_data.get('recent_activity_by_workstream', {})
        for focus_area in recommendations['focus_areas']:
            workstream_name = focus_area['workstream']
            if workstream_name in recent_by_workstream:
                docs = recent_by_workstream[workstream_name][:3]  # Top 3 recent docs
                for doc in docs:
                    recommendations['documents_to_review'].append({
                        'name': doc['name'],
                        'workstream': workstream_name,
                        'url': doc.get('web_view_link', ''),
                        'days_since_modified': doc['activity']['days_since_modified'],
                        'priority': 'High' if doc['activity']['activity_score'] > 6 else 'Medium'
                    })
    
    return recommendations

def main():
    """Main execution function"""
    print("Generating comprehensive workstream insights...")
    
    # Setup paths
    base_path = Path(__file__).parent.parent.parent.parent
    data_extraction_path = Path(__file__).parent.parent / "data_extraction"
    output_path = Path(__file__).parent.parent / "reports"
    
    # Load analysis data
    print("Loading analysis data...")
    data = load_analysis_data(data_extraction_path)
    
    # Calculate workstream allocation
    print("Calculating workstream allocation...")
    allocation = calculate_workstream_allocation(data)
    
    # Assess goal alignment
    print("Assessing goal alignment...")
    alignment = assess_goal_alignment(allocation)
    
    # Identify stakeholders
    print("Identifying key stakeholders...")
    stakeholders = identify_key_stakeholders(data)
    
    # Identify high priority actions
    print("Identifying high priority actions...")
    actions = identify_high_priority_actions(data, alignment)
    
    # Generate weekly recommendations
    print("Generating weekly recommendations...")
    weekly_recs = generate_weekly_recommendations(data, alignment, actions)
    
    # Compile comprehensive insights
    comprehensive_insights = {
        'analysis_metadata': {
            'generated_at': datetime.now().isoformat(),
            'data_sources': list(data.keys()),
            'target_user': 'david.campos@biorender.com'
        },
        'workstream_allocation': allocation,
        'goal_alignment_assessment': alignment,
        'key_stakeholders_by_workstream': stakeholders,
        'high_priority_actions': actions,
        'weekly_recommendations': weekly_recs,
        'executive_summary': {
            'top_insights': [],
            'critical_gaps': [],
            'recommended_focus_shifts': []
        }
    }
    
    # Generate executive summary insights
    calendar_allocation = allocation.get('calendar_time_percent', {})
    top_workstream = max(calendar_allocation, key=calendar_allocation.get) if calendar_allocation else None
    top_percentage = calendar_allocation.get(top_workstream, 0) if top_workstream else 0
    
    comprehensive_insights['executive_summary']['top_insights'] = [
        f"Currently spending {top_percentage:.1f}% of calendar time on {top_workstream}",
        f"Found {sum(len(ws_stakeholders) for ws_stakeholders in stakeholders.values())} key stakeholder relationships across workstreams",
        f"Identified {len([a for a in actions if a['priority'] == 'HIGH'])} high-priority action items",
        f"Active on {len(data.get('drive', {}).get('analysis', {}).get('recent_activity', []))} recently modified documents"
    ]
    
    under_allocated = [ws for ws, assessment in alignment.items() if assessment['alignment'] == 'UNDER_ALLOCATED']
    comprehensive_insights['executive_summary']['critical_gaps'] = [
        f"{ws} is under-allocated (current: {alignment[ws]['actual_percent']:.1f}%, expected: {alignment[ws]['expected_range']})"
        for ws in under_allocated
    ]
    
    comprehensive_insights['executive_summary']['recommended_focus_shifts'] = [
        f"Increase {rec['workstream']} by {rec['target_increase']}"
        for rec in weekly_recs['focus_areas'][:3]
    ]
    
    # Save comprehensive insights
    output_path.mkdir(exist_ok=True)
    output_file = output_path / "comprehensive_workstream_insights.json"
    
    with open(output_file, 'w') as f:
        json.dump(comprehensive_insights, f, indent=2, default=str)
    
    # Generate markdown summary
    markdown_summary = generate_markdown_summary(comprehensive_insights)
    markdown_file = output_path / "executive_summary.md"
    
    with open(markdown_file, 'w') as f:
        f.write(markdown_summary)
    
    # Print key insights
    print(f"\n=== EXECUTIVE SUMMARY ===")
    for insight in comprehensive_insights['executive_summary']['top_insights']:
        print(f"• {insight}")
    
    if comprehensive_insights['executive_summary']['critical_gaps']:
        print(f"\n=== CRITICAL GAPS ===")
        for gap in comprehensive_insights['executive_summary']['critical_gaps']:
            print(f"⚠️  {gap}")
    
    print(f"\n=== THIS WEEK'S FOCUS ===")
    for rec in weekly_recs['focus_areas'][:3]:
        print(f"🎯 {rec['workstream']}: {rec['target_increase']} (currently {rec['current_percent']:.1f}%)")
    
    print(f"\n=== KEY PEOPLE TO CONNECT WITH ===")
    for person in weekly_recs['people_to_connect_with'][:5]:
        print(f"👥 {person['email']} ({person['workstream']}) - {person['suggested_frequency']}")
    
    print(f"\nFull analysis saved to: {output_file}")
    print(f"Executive summary saved to: {markdown_file}")

def generate_markdown_summary(insights: Dict[str, Any]) -> str:
    """Generate a markdown executive summary"""
    
    markdown = f"""# Workstream Analysis Executive Summary
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}

## Key Insights
"""
    
    for insight in insights['executive_summary']['top_insights']:
        markdown += f"- {insight}\n"
    
    if insights['executive_summary']['critical_gaps']:
        markdown += f"\n## Critical Gaps\n"
        for gap in insights['executive_summary']['critical_gaps']:
            markdown += f"- ⚠️ {gap}\n"
    
    markdown += f"\n## Current Time Allocation\n"
    calendar_allocation = insights['workstream_allocation'].get('calendar_time_percent', {})
    for workstream, percentage in sorted(calendar_allocation.items(), key=lambda x: x[1], reverse=True):
        markdown += f"- **{workstream}**: {percentage:.1f}%\n"
    
    markdown += f"\n## This Week's Priorities\n"
    for i, rec in enumerate(insights['weekly_recommendations']['focus_areas'][:3], 1):
        markdown += f"{i}. **{rec['workstream']}** - Increase by {rec['target_increase']} (currently {rec['current_percent']:.1f}%)\n"
        for goal in rec['specific_goals']:
            markdown += f"   - {goal}\n"
    
    markdown += f"\n## Key People to Connect With\n"
    for person in insights['weekly_recommendations']['people_to_connect_with'][:5]:
        markdown += f"- **{person['email']}** ({person['workstream']}) - {person['suggested_frequency']}\n"
    
    markdown += f"\n## High Priority Actions\n"
    high_priority_actions = [a for a in insights['high_priority_actions'] if a['priority'] == 'HIGH']
    for i, action in enumerate(high_priority_actions[:5], 1):
        markdown += f"{i}. {action['description']}\n"
        for suggested in action['suggested_actions'][:2]:
            markdown += f"   - {suggested}\n"
    
    return markdown

if __name__ == "__main__":
    main()