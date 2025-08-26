#!/usr/bin/env python3
"""
Calendar Analytics - Key Metrics Extraction
===========================================

This script extracts and calculates comprehensive calendar analytics metrics
from the DuckDB views, providing executive-level insights and KPIs.

Metrics calculated:
- Deep work ratio vs 40% target
- Back-to-back rate and buffer coverage  
- Topic entropy and KL divergence
- Collaboration HHI concentration
- Meeting efficiency scores
- Busy trap component scores
- Goal attention distribution
- Productivity benchmarks

Output: calendar_metrics.json with structured metrics for executive reporting.
"""

import duckdb
import json
import pandas as pd
from datetime import datetime
from typing import Dict, List, Any
import os

class CalendarMetricsExtractor:
    def __init__(self, db_path: str, output_dir: str):
        """Initialize with database and output paths."""
        self.db_path = db_path
        self.output_dir = output_dir
        self.connection = None
        self.metrics = {}
        
        os.makedirs(output_dir, exist_ok=True)
        
    def connect_db(self):
        """Connect to DuckDB database."""
        self.connection = duckdb.connect(self.db_path)
        print(f"Connected to database: {self.db_path}")
        
    def extract_core_kpis(self):
        """Extract core productivity KPIs."""
        print("Extracting core KPIs...")
        
        kpis = self.connection.execute("SELECT * FROM v_calendar_kpis").fetchone()
        
        self.metrics['core_kpis'] = {
            'analysis_period': {
                'start_date': kpis[0].isoformat(),
                'end_date': kpis[1].isoformat(),
                'total_days': int(kpis[2]),
                'active_days': int(kpis[4])
            },
            'meeting_volume': {
                'total_meetings': int(kpis[3]),
                'meetings_per_day': float(kpis[5]),
                'total_hours': float(kpis[6]),
                'avg_hours_per_day': float(kpis[7])
            },
            'deep_work_metrics': {
                'total_blocks': int(kpis[8]),
                'deep_work_hours': float(kpis[9]),
                'deep_work_ratio_pct': float(kpis[10]),
                'target_ratio_pct': 40.0,
                'meets_target': float(kpis[10]) >= 40.0
            },
            'buffer_management': {
                'total_transitions': int(kpis[11]),
                'adequately_buffered': int(kpis[12]),
                'buffer_coverage_pct': float(kpis[13]),
                'avg_buffer_minutes': float(kpis[14]),
                'target_coverage_pct': 80.0,
                'meets_target': float(kpis[13]) >= 80.0
            },
            'productivity_score': {
                'overall_score': float(kpis[15]),
                'score_out_of_100': float(kpis[15]),
                'performance_rating': self._rate_productivity_score(float(kpis[15]))
            }
        }
        
    def extract_topic_metrics(self):
        """Extract topic analysis and entropy metrics."""
        print("Extracting topic metrics...")
        
        # Topic distribution
        topic_data = self.connection.execute("""
            SELECT * FROM v_topic_minutes ORDER BY total_minutes DESC
        """).fetchdf().to_dict('records')
        
        # Topic entropy
        entropy_data = self.connection.execute("SELECT * FROM v_topic_entropy").fetchone()
        
        self.metrics['topic_analysis'] = {
            'topic_distribution': topic_data,
            'diversity_metrics': {
                'total_topics': int(entropy_data[0]),
                'total_minutes': float(entropy_data[1]),
                'shannon_entropy': float(entropy_data[2]),
                'max_possible_entropy': float(entropy_data[3]),
                'normalized_entropy': float(entropy_data[4]),
                'diversity_level': entropy_data[5]
            },
            'top_3_topics': [
                {
                    'topic': topic_data[0]['topic_category'],
                    'time_share_pct': topic_data[0]['time_share_pct'],
                    'total_hours': topic_data[0]['total_hours']
                },
                {
                    'topic': topic_data[1]['topic_category'],
                    'time_share_pct': topic_data[1]['time_share_pct'],
                    'total_hours': topic_data[1]['total_hours']
                },
                {
                    'topic': topic_data[2]['topic_category'],
                    'time_share_pct': topic_data[2]['time_share_pct'],
                    'total_hours': topic_data[2]['total_hours']
                }
            ]
        }
        
    def extract_collaboration_metrics(self):
        """Extract collaboration and network analysis metrics."""
        print("Extracting collaboration metrics...")
        
        # HHI concentration
        hhi_data = self.connection.execute("SELECT * FROM v_collab_hhi").fetchone()
        
        # Top collaborators
        top_collabs = self.connection.execute("""
            SELECT participant_email, domain, total_minutes, meetings_count, is_internal
            FROM v_collab_minutes 
            ORDER BY total_minutes DESC 
            LIMIT 10
        """).fetchdf().to_dict('records')
        
        # Collaboration distribution
        collab_summary = self.connection.execute("""
            SELECT 
                COUNT(*) AS total_collaborators,
                COUNT(CASE WHEN is_internal = 1 THEN 1 END) AS internal_collaborators,
                COUNT(CASE WHEN is_internal = 0 THEN 1 END) AS external_collaborators,
                SUM(total_minutes) AS total_collaboration_minutes,
                SUM(CASE WHEN is_internal = 1 THEN total_minutes ELSE 0 END) AS internal_minutes,
                SUM(CASE WHEN is_internal = 0 THEN total_minutes ELSE 0 END) AS external_minutes
            FROM v_collab_minutes
        """).fetchone()
        
        self.metrics['collaboration_analysis'] = {
            'concentration_metrics': {
                'total_domains': int(hhi_data[0]),
                'total_collaboration_minutes': float(hhi_data[1]),
                'hhi_score': float(hhi_data[2]),
                'concentration_level': hhi_data[3],
                'interpretation': self._interpret_hhi_score(float(hhi_data[2]))
            },
            'collaboration_distribution': {
                'total_collaborators': int(collab_summary[0]),
                'internal_collaborators': int(collab_summary[1]),
                'external_collaborators': int(collab_summary[2]),
                'internal_collaboration_pct': round((collab_summary[4] / collab_summary[3]) * 100, 1),
                'external_collaboration_pct': round((collab_summary[5] / collab_summary[3]) * 100, 1)
            },
            'top_collaborators': top_collabs[:5],
            'network_insights': {
                'most_frequent_collaborator': top_collabs[0]['participant_email'],
                'highest_time_investment_hours': round(top_collabs[0]['total_minutes'] / 60, 1),
                'collaboration_breadth': len([c for c in top_collabs if c['total_minutes'] >= 60])
            }
        }
        
    def extract_efficiency_metrics(self):
        """Extract meeting efficiency and optimization metrics."""
        print("Extracting efficiency metrics...")
        
        # Back-to-back analysis
        b2b_summary = self.connection.execute("""
            SELECT 
                COUNT(*) AS total_transitions,
                COUNT(CASE WHEN transition_type = 'back_to_back' THEN 1 END) AS b2b_count,
                COUNT(CASE WHEN transition_type = 'overlapping' THEN 1 END) AS overlapping_count,
                AVG(gap_minutes) AS avg_gap_minutes,
                SUM(adequate_buffer) AS adequate_buffers,
                ROUND(AVG(CASE WHEN transition_type IN ('back_to_back', 'overlapping') THEN 1 ELSE 0 END) * 100, 1) AS b2b_rate_pct
            FROM v_b2b
        """).fetchone()
        
        # Meeting duration efficiency
        duration_summary = self.connection.execute("""
            SELECT 
                COUNT(*) AS total_meetings,
                COUNT(CASE WHEN duration_category = 'short' THEN 1 END) AS short_meetings,
                COUNT(CASE WHEN duration_category = 'extended' THEN 1 END) AS extended_meetings,
                AVG(duration_minutes) AS avg_duration,
                COUNT(CASE WHEN attendee_count > 5 AND duration_minutes > 60 THEN 1 END) AS high_cost_meetings
            FROM v_events_norm
            WHERE meeting_type IN ('one_on_one', 'small_meeting', 'large_meeting')
        """).fetchone()
        
        # Off-hours meetings
        offhours_summary = self.connection.execute("""
            SELECT 
                COUNT(*) AS total_offhours_meetings,
                SUM(duration_minutes) AS total_offhours_minutes,
                ROUND(AVG(duration_minutes), 1) AS avg_offhours_duration
            FROM v_offhours
        """).fetchone()
        
        # Context switching
        context_switching = self.connection.execute("""
            SELECT 
                COUNT(*) AS total_transitions,
                AVG(avg_transition_minutes) AS avg_context_switch_time,
                SUM(rapid_transitions) AS rapid_switches,
                ROUND(AVG(rapid_transition_pct), 1) AS avg_rapid_transition_pct
            FROM v_transition_map
        """).fetchone()
        
        self.metrics['efficiency_analysis'] = {
            'back_to_back_meetings': {
                'total_transitions': int(b2b_summary[0]),
                'b2b_count': int(b2b_summary[1]),
                'overlapping_count': int(b2b_summary[2]),
                'b2b_rate_pct': float(b2b_summary[5]),
                'avg_buffer_minutes': round(float(b2b_summary[3]), 1),
                'adequate_buffer_rate': round((b2b_summary[4] / b2b_summary[0]) * 100, 1) if b2b_summary[0] > 0 else 0
            },
            'meeting_duration_efficiency': {
                'total_meetings': int(duration_summary[0]),
                'avg_duration_minutes': round(float(duration_summary[3]), 1),
                'short_meeting_pct': round((duration_summary[1] / duration_summary[0]) * 100, 1),
                'extended_meeting_pct': round((duration_summary[2] / duration_summary[0]) * 100, 1),
                'high_cost_meetings': int(duration_summary[4])
            },
            'off_hours_impact': {
                'total_offhours_meetings': int(offhours_summary[0]),
                'total_offhours_hours': round(float(offhours_summary[1]) / 60, 1),
                'avg_offhours_duration': float(offhours_summary[2])
            },
            'context_switching': {
                'total_topic_transitions': int(context_switching[0]) if context_switching[0] else 0,
                'avg_switch_time_minutes': round(float(context_switching[1]), 1) if context_switching[1] else 0,
                'rapid_switches': int(context_switching[2]) if context_switching[2] else 0,
                'rapid_switch_rate_pct': float(context_switching[3]) if context_switching[3] else 0
            }
        }
        
    def extract_goal_metrics(self):
        """Extract goal attention and strategic focus metrics."""
        print("Extracting goal attention metrics...")
        
        goal_data = self.connection.execute("""
            SELECT * FROM v_goal_attention_share ORDER BY weighted_minutes DESC
        """).fetchdf().to_dict('records')
        
        # Calculate strategic vs operational split
        strategic_goals = ['strategic_planning', 'partnerships', 'product_development']
        operational_goals = ['operational_excellence', 'team_development']
        
        strategic_time = sum([g['weighted_minutes'] for g in goal_data if g['business_goal'] in strategic_goals])
        operational_time = sum([g['weighted_minutes'] for g in goal_data if g['business_goal'] in operational_goals])
        total_time = sum([g['weighted_minutes'] for g in goal_data])
        
        self.metrics['goal_attention_analysis'] = {
            'goal_distribution': goal_data,
            'strategic_focus': {
                'strategic_time_pct': round((strategic_time / total_time) * 100, 1) if total_time > 0 else 0,
                'operational_time_pct': round((operational_time / total_time) * 100, 1) if total_time > 0 else 0,
                'strategic_vs_operational_ratio': round(strategic_time / operational_time, 2) if operational_time > 0 else float('inf')
            },
            'top_3_goals': goal_data[:3],
            'attention_insights': {
                'primary_focus': goal_data[0]['business_goal'],
                'primary_focus_pct': goal_data[0]['weighted_share_pct'],
                'focus_concentration': 'high' if goal_data[0]['weighted_share_pct'] > 30 else 'moderate' if goal_data[0]['weighted_share_pct'] > 20 else 'distributed'
            }
        }
        
    def extract_delegation_metrics(self):
        """Extract delegation and control metrics."""
        print("Extracting delegation metrics...")
        
        delegation_data = self.connection.execute("""
            SELECT * FROM v_delegation_index
        """).fetchdf().to_dict('records')
        
        # Calculate overall delegation ratio
        total_minutes = sum([d['total_minutes'] for d in delegation_data])
        delegated_minutes = sum([d['total_minutes'] for d in delegation_data if not d['organizer_self']])
        delegation_ratio = (delegated_minutes / total_minutes * 100) if total_minutes > 0 else 0
        
        self.metrics['delegation_analysis'] = {
            'overall_delegation_ratio': round(delegation_ratio, 1),
            'delegation_breakdown': delegation_data,
            'delegation_insights': {
                'self_organized_pct': round(100 - delegation_ratio, 1),
                'delegation_level': self._assess_delegation_level(delegation_ratio),
                'control_vs_delegation_balance': self._assess_control_balance(delegation_ratio)
            }
        }
        
    def calculate_busy_trap_score(self):
        """Calculate comprehensive busy trap score (0-100 scale)."""
        print("Calculating busy trap score...")
        
        # Component scores based on productivity research
        components = {
            'meeting_overload': {
                'weight': 0.25,
                'score': max(0, 100 - (self.metrics['core_kpis']['meeting_volume']['avg_hours_per_day'] / 8 * 100))
            },
            'back_to_back_stress': {
                'weight': 0.20,
                'score': max(0, 100 - self.metrics['efficiency_analysis']['back_to_back_meetings']['b2b_rate_pct'])
            },
            'deep_work_deficit': {
                'weight': 0.25,
                'score': min(100, (self.metrics['core_kpis']['deep_work_metrics']['deep_work_ratio_pct'] / 40) * 100)
            },
            'context_switching': {
                'weight': 0.15,
                'score': max(0, 100 - self.metrics['efficiency_analysis']['context_switching']['rapid_switch_rate_pct'])
            },
            'off_hours_burden': {
                'weight': 0.15,
                'score': max(0, 100 - min(50, (self.metrics['efficiency_analysis']['off_hours_impact']['total_offhours_hours'] / 10) * 100))
            }
        }
        
        # Calculate weighted score
        weighted_score = sum(comp['score'] * comp['weight'] for comp in components.values())
        
        self.metrics['busy_trap_analysis'] = {
            'overall_score': round(weighted_score, 1),
            'score_interpretation': self._interpret_busy_trap_score(weighted_score),
            'component_scores': components,
            'recommendations': self._generate_busy_trap_recommendations(components)
        }
        
    def _rate_productivity_score(self, score: float) -> str:
        """Rate productivity score."""
        if score >= 80:
            return 'excellent'
        elif score >= 70:
            return 'good'
        elif score >= 60:
            return 'fair'
        else:
            return 'needs_improvement'
            
    def _interpret_hhi_score(self, hhi: float) -> str:
        """Interpret HHI concentration score."""
        if hhi > 2500:
            return 'Highly concentrated collaboration - may indicate over-dependence on few partners'
        elif hhi > 1500:
            return 'Moderately concentrated - balanced collaboration network'
        else:
            return 'Unconcentrated - diverse collaboration portfolio'
            
    def _assess_delegation_level(self, ratio: float) -> str:
        """Assess delegation level."""
        if ratio > 70:
            return 'high_delegation'
        elif ratio > 50:
            return 'moderate_delegation'
        else:
            return 'low_delegation'
            
    def _assess_control_balance(self, ratio: float) -> str:
        """Assess control vs delegation balance."""
        if ratio > 80:
            return 'may_lack_control'
        elif ratio > 60:
            return 'healthy_balance'
        elif ratio > 40:
            return 'moderate_control'
        else:
            return 'high_control'
            
    def _interpret_busy_trap_score(self, score: float) -> str:
        """Interpret busy trap score."""
        if score >= 80:
            return 'low_risk - well-managed calendar with good productivity practices'
        elif score >= 60:
            return 'moderate_risk - some areas for improvement in calendar management'
        elif score >= 40:
            return 'high_risk - significant busy trap indicators present'
        else:
            return 'very_high_risk - calendar management needs immediate attention'
            
    def _generate_busy_trap_recommendations(self, components: Dict) -> List[str]:
        """Generate recommendations based on component scores."""
        recommendations = []
        
        if components['meeting_overload']['score'] < 60:
            recommendations.append("Reduce total meeting hours - aim for <6 hours/day")
            
        if components['back_to_back_stress']['score'] < 60:
            recommendations.append("Implement 5-minute buffers between meetings")
            
        if components['deep_work_deficit']['score'] < 60:
            recommendations.append("Block larger time slots for deep work - target 40% of time")
            
        if components['context_switching']['score'] < 60:
            recommendations.append("Group similar meetings together to reduce context switching")
            
        if components['off_hours_burden']['score'] < 60:
            recommendations.append("Limit off-hours meetings to reduce work-life balance impact")
            
        return recommendations
        
    def extract_all_metrics(self):
        """Extract all calendar metrics."""
        print("Extracting Calendar Analytics Metrics")
        print("=" * 40)
        
        self.connect_db()
        
        try:
            self.extract_core_kpis()
            self.extract_topic_metrics()
            self.extract_collaboration_metrics()
            self.extract_efficiency_metrics()
            self.extract_goal_metrics()
            self.extract_delegation_metrics()
            self.calculate_busy_trap_score()
            
            # Add metadata
            self.metrics['metadata'] = {
                'extraction_timestamp': datetime.now().isoformat(),
                'database_path': self.db_path,
                'total_events_analyzed': self.metrics['core_kpis']['meeting_volume']['total_meetings'],
                'analysis_period_days': self.metrics['core_kpis']['analysis_period']['total_days']
            }
            
            print(f"\nExtracted {len(self.metrics)} metric categories")
            return self.metrics
            
        finally:
            if self.connection:
                self.connection.close()
                
    def save_metrics(self):
        """Save metrics to JSON file."""
        output_path = os.path.join(self.output_dir, 'calendar_metrics.json')
        
        with open(output_path, 'w') as f:
            json.dump(self.metrics, f, indent=2, default=str)
            
        print(f"Metrics saved to: {output_path}")
        return output_path

def main():
    """Main execution function."""
    db_path = "/Users/david.campos/VibeCode/AICoS-Lab/experiments/ryan_time_analysis/data/processed/duckdb/calendar_analytics.db"
    output_dir = "/Users/david.campos/VibeCode/AICoS-Lab/experiments/ryan_time_analysis/analytics/calendar"
    
    extractor = CalendarMetricsExtractor(db_path, output_dir)
    extractor.extract_all_metrics()
    extractor.save_metrics()

if __name__ == "__main__":
    main()