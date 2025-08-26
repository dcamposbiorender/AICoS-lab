#!/usr/bin/env python3
"""
Calendar Analytics - Summary Report Generation
==============================================

This script generates a comprehensive markdown summary report of Ryan's
calendar analysis, combining metrics, insights, and recommendations.

Output: calendar_analysis_summary.md with executive-ready insights.
"""

import json
import os
from datetime import datetime
from typing import Dict, Any

class CalendarSummaryReportGenerator:
    def __init__(self, metrics_file: str, output_dir: str):
        """Initialize with metrics file and output directory."""
        self.metrics_file = metrics_file
        self.output_dir = output_dir
        self.metrics = {}
        
        os.makedirs(output_dir, exist_ok=True)
        
    def load_metrics(self):
        """Load metrics from JSON file."""
        with open(self.metrics_file, 'r') as f:
            self.metrics = json.load(f)
        print(f"Loaded metrics from: {self.metrics_file}")
        
    def generate_report(self):
        """Generate comprehensive summary report."""
        print("Generating calendar analysis summary report...")
        
        output_path = os.path.join(self.output_dir, 'calendar_analysis_summary.md')
        
        with open(output_path, 'w') as f:
            f.write(self._generate_header())
            f.write(self._generate_executive_summary())
            f.write(self._generate_key_findings())
            f.write(self._generate_productivity_analysis())
            f.write(self._generate_collaboration_insights())
            f.write(self._generate_time_allocation())
            f.write(self._generate_efficiency_metrics())
            f.write(self._generate_recommendations())
            f.write(self._generate_technical_details())
            
        print(f"Summary report generated: {output_path}")
        return output_path
        
    def _generate_header(self) -> str:
        """Generate report header."""
        period_start = self.metrics['core_kpis']['analysis_period']['start_date'][:10]
        period_end = self.metrics['core_kpis']['analysis_period']['end_date'][:10]
        total_days = self.metrics['core_kpis']['analysis_period']['total_days']
        
        return f"""# Ryan Marien - Calendar Analytics Summary Report

**Analysis Period:** {period_start} to {period_end} ({total_days} days)  
**Generated:** {datetime.now().strftime('%B %d, %Y at %I:%M %p')}  
**Total Events Analyzed:** {self.metrics['metadata']['total_events_analyzed']:,}  
**Data Source:** 6-month calendar export (2,358 events → 2,280 processed)

---

"""
        
    def _generate_executive_summary(self) -> str:
        """Generate executive summary section."""
        kpis = self.metrics['core_kpis']
        busy_trap = self.metrics['busy_trap_analysis']
        
        return f"""## Executive Summary

### 🎯 Overall Assessment

**Productivity Score: {kpis['productivity_score']['overall_score']:.1f}/100** ({kpis['productivity_score']['performance_rating'].replace('_', ' ').title()})

Ryan's calendar exhibits **{busy_trap['score_interpretation'].split(' - ')[0].replace('_', ' ')}** busy trap characteristics with a score of **{busy_trap['overall_score']:.1f}/100**. {busy_trap['score_interpretation'].split(' - ')[1] if ' - ' in busy_trap['score_interpretation'] else ''}

### 📊 Key Metrics at a Glance

| Metric | Current | Target | Status |
|--------|---------|---------|---------|
| **Deep Work Ratio** | {kpis['deep_work_metrics']['deep_work_ratio_pct']:.1f}% | 40% | {'✅ MEETS' if kpis['deep_work_metrics']['meets_target'] else '❌ BELOW'} |
| **Buffer Coverage** | {kpis['buffer_management']['buffer_coverage_pct']:.1f}% | 80% | {'✅ MEETS' if kpis['buffer_management']['meets_target'] else '❌ BELOW'} |
| **Daily Meeting Hours** | {kpis['meeting_volume']['avg_hours_per_day']:.1f} hours | <6 hours | {'✅ GOOD' if kpis['meeting_volume']['avg_hours_per_day'] < 6 else '⚠️ HIGH'} |
| **Meetings per Day** | {kpis['meeting_volume']['meetings_per_day']:.1f} | <8 | {'✅ GOOD' if kpis['meeting_volume']['meetings_per_day'] < 8 else '⚠️ HIGH'} |

### 🚨 Critical Insights

1. **Deep Work Deficit:** Only {kpis['deep_work_metrics']['deep_work_ratio_pct']:.1f}% of time allocated to focused work (target: 40%)
2. **Meeting Density:** {kpis['meeting_volume']['avg_hours_per_day']:.1f} hours/day in meetings with {kpis['meeting_volume']['meetings_per_day']:.1f} meetings/day average
3. **Buffer Management:** {kpis['buffer_management']['buffer_coverage_pct']:.1f}% of meeting transitions have adequate buffers
4. **Collaboration Focus:** {self.metrics['collaboration_analysis']['concentration_metrics']['concentration_level'].replace('_', ' ').title()} collaboration pattern

---

"""
        
    def _generate_key_findings(self) -> str:
        """Generate key findings section."""
        collab = self.metrics['collaboration_analysis']
        topics = self.metrics['topic_analysis']
        
        top_collaborator = collab['top_collaborators'][0]['participant_email'].split('@')[0]
        top_topic = topics['top_3_topics'][0]['topic']
        
        return f"""## 🔍 Key Findings

### Meeting Volume & Distribution
- **{self.metrics['core_kpis']['meeting_volume']['total_meetings']} total meetings** over {self.metrics['core_kpis']['analysis_period']['total_days']} days
- **{self.metrics['core_kpis']['meeting_volume']['avg_hours_per_day']:.1f} hours/day** average meeting time
- **{self.metrics['core_kpis']['analysis_period']['active_days']} active days** with calendar events

### Collaboration Patterns
- **Top Partner:** {top_collaborator} ({collab['top_collaborators'][0]['total_minutes']/60:.1f} hours total)
- **Network Breadth:** {collab['network_insights']['collaboration_breadth']} significant collaborators (>1 hour each)
- **Internal vs External:** {collab['collaboration_distribution']['internal_collaboration_pct']:.1f}% internal, {collab['collaboration_distribution']['external_collaboration_pct']:.1f}% external

### Time Allocation
- **Primary Focus:** {top_topic.replace('_', ' ').title()} ({topics['top_3_topics'][0]['time_share_pct']:.1f}% of time)
- **Topic Diversity:** {topics['diversity_metrics']['diversity_level'].replace('_', ' ').title()} with {topics['diversity_metrics']['normalized_entropy']:.2f} entropy score
- **Strategic vs Operational:** {self.metrics['goal_attention_analysis']['strategic_focus']['strategic_time_pct']:.1f}% strategic, {self.metrics['goal_attention_analysis']['strategic_focus']['operational_time_pct']:.1f}% operational

### Meeting Efficiency
- **Back-to-Back Rate:** {self.metrics['efficiency_analysis']['back_to_back_meetings']['b2b_rate_pct']:.1f}% of transitions are back-to-back or overlapping
- **Average Buffer Time:** {self.metrics['efficiency_analysis']['back_to_back_meetings']['avg_buffer_minutes']:.1f} minutes between meetings
- **Context Switching:** {self.metrics['efficiency_analysis']['context_switching']['rapid_switch_rate_pct']:.1f}% rapid topic transitions

---

"""
        
    def _generate_productivity_analysis(self) -> str:
        """Generate productivity analysis section."""
        deep_work = self.metrics['core_kpis']['deep_work_metrics']
        busy_trap = self.metrics['busy_trap_analysis']
        
        components_text = ""
        for comp_name, comp_data in busy_trap['component_scores'].items():
            status = "✅" if comp_data['score'] >= 70 else "⚠️" if comp_data['score'] >= 50 else "❌"
            components_text += f"- **{comp_name.replace('_', ' ').title()}:** {comp_data['score']:.1f}/100 {status}\n"
            
        return f"""## 📈 Productivity Analysis

### Deep Work Assessment
- **Available Deep Work Blocks:** {deep_work['total_blocks']} blocks totaling {deep_work['deep_work_hours']:.1f} hours
- **Deep Work Ratio:** {deep_work['deep_work_ratio_pct']:.1f}% (Target: {deep_work['target_ratio_pct']}%)
- **Target Achievement:** {'✅ MEETS GOAL' if deep_work['meets_target'] else '❌ BELOW TARGET'}

### Busy Trap Analysis Score: {busy_trap['overall_score']:.1f}/100

**Component Breakdown:**
{components_text}

**Risk Level:** {busy_trap['score_interpretation'].split(' - ')[0].replace('_', ' ').title()}

### Buffer Management
- **Total Transitions:** {self.metrics['core_kpis']['buffer_management']['total_transitions']}
- **Adequately Buffered:** {self.metrics['core_kpis']['buffer_management']['adequately_buffered']} ({self.metrics['core_kpis']['buffer_management']['buffer_coverage_pct']:.1f}%)
- **Average Buffer Time:** {self.metrics['core_kpis']['buffer_management']['avg_buffer_minutes']:.1f} minutes

---

"""
        
    def _generate_collaboration_insights(self) -> str:
        """Generate collaboration insights section."""
        collab = self.metrics['collaboration_analysis']
        delegation = self.metrics['delegation_analysis']
        
        top_5_partners = ""
        for i, partner in enumerate(collab['top_collaborators'][:5], 1):
            email = partner['participant_email'].split('@')[0]
            hours = partner['total_minutes'] / 60
            partner_type = "Internal" if partner['is_internal'] else "External"
            top_5_partners += f"{i}. **{email}** - {hours:.1f} hours ({partner_type})\n"
            
        return f"""## 🤝 Collaboration Analysis

### Network Concentration
- **HHI Score:** {collab['concentration_metrics']['hhi_score']:.0f} ({collab['concentration_metrics']['concentration_level'].replace('_', ' ').title()})
- **Total Domains:** {collab['concentration_metrics']['total_domains']} different organizations
- **Collaboration Breadth:** {collab['network_insights']['collaboration_breadth']} significant partners

### Top Collaboration Partners
{top_5_partners}

### Meeting Organization
- **Self-Organized:** {delegation['delegation_insights']['self_organized_pct']:.1f}% of meetings
- **Delegated/Invited:** {delegation['overall_delegation_ratio']:.1f}% of meetings
- **Delegation Level:** {delegation['delegation_insights']['delegation_level'].replace('_', ' ').title()}
- **Control Balance:** {delegation['delegation_insights']['control_vs_delegation_balance'].replace('_', ' ').title()}

### Internal vs External Split
- **Internal Collaboration:** {collab['collaboration_distribution']['internal_collaboration_pct']:.1f}% of time
- **External Collaboration:** {collab['collaboration_distribution']['external_collaboration_pct']:.1f}% of time
- **Internal Partners:** {collab['collaboration_distribution']['internal_collaborators']} people
- **External Partners:** {collab['collaboration_distribution']['external_collaborators']} people

---

"""
        
    def _generate_time_allocation(self) -> str:
        """Generate time allocation section."""
        topics = self.metrics['topic_analysis']
        goals = self.metrics['goal_attention_analysis']
        
        top_topics_text = ""
        for i, topic in enumerate(topics['top_3_topics'], 1):
            top_topics_text += f"{i}. **{topic['topic'].replace('_', ' ').title()}** - {topic['total_hours']:.1f} hours ({topic['time_share_pct']:.1f}%)\n"
            
        top_goals_text = ""
        for i, goal in enumerate(goals['top_3_goals'], 1):
            goal_name = goal['business_goal'].replace('_', ' ').title()
            top_goals_text += f"{i}. **{goal_name}** - {goal['total_hours']:.1f} hours ({goal['weighted_share_pct']:.1f}%)\n"
            
        return f"""## 🎯 Time Allocation Analysis

### Topic Distribution
**Diversity Level:** {topics['diversity_metrics']['diversity_level'].replace('_', ' ').title()}  
**Entropy Score:** {topics['diversity_metrics']['normalized_entropy']:.3f} (0 = focused, 1 = distributed)

**Top 3 Meeting Topics:**
{top_topics_text}

### Business Goal Attention
**Focus Pattern:** {goals['attention_insights']['focus_concentration'].title()}  
**Primary Focus:** {goals['attention_insights']['primary_focus'].replace('_', ' ').title()} ({goals['attention_insights']['primary_focus_pct']:.1f}%)

**Top 3 Business Goals:**
{top_goals_text}

### Strategic vs Operational Balance
- **Strategic Focus:** {goals['strategic_focus']['strategic_time_pct']:.1f}% of time
- **Operational Focus:** {goals['strategic_focus']['operational_time_pct']:.1f}% of time
- **Strategic/Operational Ratio:** {goals['strategic_focus']['strategic_vs_operational_ratio']:.2f}:1

---

"""
        
    def _generate_efficiency_metrics(self) -> str:
        """Generate efficiency metrics section."""
        efficiency = self.metrics['efficiency_analysis']
        
        return f"""## ⚡ Meeting Efficiency Metrics

### Back-to-Back Meeting Stress
- **Total Transitions:** {efficiency['back_to_back_meetings']['total_transitions']}
- **Back-to-Back Rate:** {efficiency['back_to_back_meetings']['b2b_rate_pct']:.1f}% 
- **Overlapping Meetings:** {efficiency['back_to_back_meetings']['overlapping_count']} instances
- **Adequate Buffer Rate:** {efficiency['back_to_back_meetings']['adequate_buffer_rate']:.1f}%

### Meeting Duration Patterns
- **Total Meetings:** {efficiency['meeting_duration_efficiency']['total_meetings']}
- **Average Duration:** {efficiency['meeting_duration_efficiency']['avg_duration_minutes']:.1f} minutes
- **Short Meetings (<15 min):** {efficiency['meeting_duration_efficiency']['short_meeting_pct']:.1f}%
- **Extended Meetings (>60 min):** {efficiency['meeting_duration_efficiency']['extended_meeting_pct']:.1f}%
- **High-Cost Meetings:** {efficiency['meeting_duration_efficiency']['high_cost_meetings']} (>5 attendees, >60 min)

### Off-Hours Work Impact
- **Off-Hours Meetings:** {efficiency['off_hours_impact']['total_offhours_meetings']}
- **Off-Hours Time:** {efficiency['off_hours_impact']['total_offhours_hours']:.1f} hours
- **Average Off-Hours Duration:** {efficiency['off_hours_impact']['avg_offhours_duration']:.1f} minutes

### Context Switching Analysis
- **Topic Transitions:** {efficiency['context_switching']['total_topic_transitions']}
- **Average Switch Time:** {efficiency['context_switching']['avg_switch_time_minutes']:.1f} minutes
- **Rapid Switches:** {efficiency['context_switching']['rapid_switches']} instances
- **Rapid Switch Rate:** {efficiency['context_switching']['rapid_switch_rate_pct']:.1f}%

---

"""
        
    def _generate_recommendations(self) -> str:
        """Generate recommendations section."""
        busy_trap_recs = self.metrics['busy_trap_analysis']['recommendations']
        
        recommendations_text = ""
        for i, rec in enumerate(busy_trap_recs, 1):
            recommendations_text += f"{i}. {rec}\n"
            
        return f"""## 💡 Strategic Recommendations

### Immediate Actions (Next 30 Days)
{recommendations_text}

### Calendar Optimization Strategies

#### 🎯 Deep Work Enhancement
- **Block 2-3 hour focused work sessions** daily, especially mornings
- **Decline meetings** that don't require your specific expertise
- **Batch similar meetings** to reduce context switching

#### 🤝 Meeting Efficiency
- **Implement 5-minute buffers** between all meetings
- **Default to 25/50-minute meetings** instead of 30/60 minutes
- **Question recurring meetings** - audit ROI quarterly

#### 📊 Collaboration Optimization
- **Delegate more meeting ownership** to reduce personal calendar load
- **Limit external meetings** to 2-3 per week maximum
- **Group stakeholder communications** into weekly updates

#### ⚡ Productivity Systems
- **Theme days** - dedicate specific days to specific types of work
- **Communication windows** - batch email/Slack to specific times
- **Energy management** - schedule high-cognitive tasks during peak hours

### Long-term Strategic Shifts (90+ Days)

1. **Reduce total meeting load** from {self.metrics['core_kpis']['meeting_volume']['avg_hours_per_day']:.1f} to <5 hours/day
2. **Increase deep work ratio** from {self.metrics['core_kpis']['deep_work_metrics']['deep_work_ratio_pct']:.1f}% to 40%+
3. **Improve buffer coverage** from {self.metrics['core_kpis']['buffer_management']['buffer_coverage_pct']:.1f}% to 80%+
4. **Achieve productivity score** of 80+ (currently {self.metrics['core_kpis']['productivity_score']['overall_score']:.1f})

---

"""
        
    def _generate_technical_details(self) -> str:
        """Generate technical details section."""
        return f"""## 📊 Technical Implementation Details

### Data Processing Summary
- **Source Events:** 2,358 calendar events from 6-month export
- **Processed Events:** 2,280 events (96.7% success rate)
- **Analysis Period:** {self.metrics['core_kpis']['analysis_period']['total_days']} days
- **Active Days:** {self.metrics['core_kpis']['analysis_period']['active_days']} days with calendar activity

### Analytical Framework
- **Database:** DuckDB with 16 analytical views
- **Views Created:** 
  - Core normalization (v_events_norm, v_day_load)
  - Meeting patterns (v_b2b, v_short_meetings, v_deep_work_blocks)
  - Collaboration analysis (v_collab_minutes, v_collab_hhi)
  - Topic analysis (v_topic_minutes, v_topic_entropy)
  - Productivity metrics (v_transition_map, v_offhours, v_series_audit)
  - Strategic views (v_goal_attention_share, v_delegation_index, v_bypass_rate)

### Metrics Calculations
- **Productivity Score:** Weighted combination of deep work ratio (40%), buffer coverage (30%), and meeting load (30%)
- **Busy Trap Score:** Multi-component analysis including meeting overload, back-to-back stress, deep work deficit, context switching, and off-hours burden
- **HHI Score:** Collaboration concentration using Herfindahl-Hirschman Index
- **Topic Entropy:** Shannon entropy for meeting topic diversity analysis

### Generated Outputs
- **Visualizations:** 10+ executive-ready charts (PNG + interactive HTML)
- **Metrics Export:** Comprehensive JSON with all calculated KPIs
- **SQL Queries:** Reusable analytical queries for ongoing monitoring
- **Summary Report:** This executive summary document

---

**Report Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Analysis Framework:** CoS Analytics with DuckDB  
**Visualization Tools:** Matplotlib + Plotly for publication-ready outputs

"""
        
def main():
    """Main execution function."""
    metrics_file = "/Users/david.campos/VibeCode/AICoS-Lab/experiments/ryan_time_analysis/analytics/calendar/calendar_metrics.json"
    output_dir = "/Users/david.campos/VibeCode/AICoS-Lab/experiments/ryan_time_analysis/analytics/calendar"
    
    generator = CalendarSummaryReportGenerator(metrics_file, output_dir)
    generator.load_metrics()
    generator.generate_report()

if __name__ == "__main__":
    main()