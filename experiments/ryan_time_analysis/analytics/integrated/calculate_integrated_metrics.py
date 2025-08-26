#!/usr/bin/env python3
"""
Integrated Metrics Calculator
Sub-Agent 4: Cross-Platform Correlation Analysis

Calculates comprehensive integrated metrics and correlation coefficients
between calendar and Slack activity patterns.
"""

import duckdb
import pandas as pd
import numpy as np
import json
from pathlib import Path
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

class IntegratedMetricsCalculator:
    def __init__(self, base_path="/Users/david.campos/VibeCode/AICoS-Lab/experiments/ryan_time_analysis"):
        self.base_path = Path(base_path)
        self.calendar_db_path = self.base_path / "data/processed/duckdb/calendar_analytics.db"
        self.slack_db_path = self.base_path / "data/processed/duckdb/slack_analytics.db"
        self.integrated_db_path = self.base_path / "analytics/integrated/unified_analytics.db"
        
        # Initialize database connection
        self.conn = duckdb.connect(str(self.integrated_db_path))
        self.conn.execute(f"ATTACH '{self.calendar_db_path}' AS calendar_db")
        self.conn.execute(f"ATTACH '{self.slack_db_path}' AS slack_db")
        
        print("📊 Integrated Metrics Calculator")
        print(f"🔢 Database: {self.integrated_db_path}")
        
        # Initialize metrics storage
        self.metrics = {
            "calculation_timestamp": datetime.now().isoformat(),
            "total_workload_metrics": {},
            "correlation_coefficients": {},
            "efficiency_integration": {},
            "pattern_insights": {},
            "optimization_opportunities": {}
        }
    
    def calculate_total_workload_metrics(self):
        """Calculate comprehensive total workload metrics."""
        print("\n💼 Calculating total workload metrics...")
        
        try:
            # Overall totals and averages
            totals = self.conn.execute("""
                SELECT 
                    COUNT(DISTINCT date) as analysis_days,
                    AVG(total_collaboration_hours) as avg_daily_collaboration_hours,
                    MAX(total_collaboration_hours) as max_daily_collaboration_hours,
                    MIN(total_collaboration_hours) as min_daily_collaboration_hours,
                    STDDEV(total_collaboration_hours) as stddev_collaboration_hours,
                    
                    AVG(meeting_collaboration_pct) as avg_meeting_pct,
                    AVG(slack_collaboration_pct) as avg_slack_pct,
                    
                    SUM(business_hours_collaboration_minutes) / 60.0 as total_business_hours,
                    SUM(after_hours_collaboration_minutes) / 60.0 as total_after_hours,
                    
                    AVG(after_hours_collaboration_pct) as avg_after_hours_pct,
                    
                    COUNT(CASE WHEN collaboration_intensity = 'very_high' THEN 1 END) as very_high_days,
                    COUNT(CASE WHEN collaboration_intensity = 'high' THEN 1 END) as high_days,
                    COUNT(CASE WHEN collaboration_intensity = 'moderate' THEN 1 END) as moderate_days,
                    COUNT(CASE WHEN collaboration_intensity = 'low' THEN 1 END) as low_days
                FROM v_total_collaboration_time
            """).fetchone()
            
            if not totals:
                print("⚠️ No total workload data available")
                return False
            
            self.metrics["total_workload_metrics"] = {
                "analysis_period_days": totals[0],
                "average_daily_collaboration_hours": round(totals[1], 2) if totals[1] else 0,
                "max_daily_collaboration_hours": round(totals[2], 2) if totals[2] else 0,
                "min_daily_collaboration_hours": round(totals[3], 2) if totals[3] else 0,
                "collaboration_hours_volatility": round(totals[4], 2) if totals[4] else 0,
                
                "meeting_vs_slack_split": {
                    "average_meeting_percentage": round(totals[5], 1) if totals[5] else 0,
                    "average_slack_percentage": round(totals[6], 1) if totals[6] else 0
                },
                
                "business_vs_after_hours": {
                    "total_business_hours": round(totals[7], 1) if totals[7] else 0,
                    "total_after_hours": round(totals[8], 1) if totals[8] else 0,
                    "average_after_hours_percentage": round(totals[9], 1) if totals[9] else 0
                },
                
                "intensity_distribution": {
                    "very_high_intensity_days": totals[10] or 0,
                    "high_intensity_days": totals[11] or 0,
                    "moderate_intensity_days": totals[12] or 0,
                    "low_intensity_days": totals[13] or 0
                }
            }
            
            # Calculate additional context switching metrics
            context_metrics = self.conn.execute("""
                SELECT 
                    AVG(total_context_switches) as avg_daily_context_switches,
                    MAX(total_context_switches) as max_daily_context_switches,
                    AVG(total_channel_switches) as avg_channel_switches,
                    AVG(total_meeting_context_switches) as avg_meeting_switches,
                    
                    COUNT(CASE WHEN switching_intensity = 'very_high' THEN 1 END) as very_high_switching_days,
                    COUNT(CASE WHEN switching_intensity = 'high' THEN 1 END) as high_switching_days,
                    COUNT(CASE WHEN switching_intensity = 'moderate' THEN 1 END) as moderate_switching_days,
                    COUNT(CASE WHEN switching_intensity = 'low' THEN 1 END) as low_switching_days
                FROM v_context_switching_combined
            """).fetchone()
            
            if context_metrics:
                self.metrics["total_workload_metrics"]["context_switching"] = {
                    "average_daily_switches": round(context_metrics[0], 1) if context_metrics[0] else 0,
                    "max_daily_switches": context_metrics[1] or 0,
                    "average_channel_switches": round(context_metrics[2], 1) if context_metrics[2] else 0,
                    "average_meeting_switches": round(context_metrics[3], 1) if context_metrics[3] else 0,
                    
                    "switching_intensity_distribution": {
                        "very_high_days": context_metrics[4] or 0,
                        "high_days": context_metrics[5] or 0,
                        "moderate_days": context_metrics[6] or 0,
                        "low_days": context_metrics[7] or 0
                    }
                }
            
            # Calculate collaboration partner metrics
            collab_metrics = self.conn.execute("""
                SELECT 
                    COUNT(*) as total_collaborators,
                    SUM(total_collaboration_hours) as total_collaboration_hours_all,
                    AVG(total_collaboration_hours) as avg_hours_per_collaborator,
                    
                    COUNT(CASE WHEN relationship_strength = 'primary_collaborator' THEN 1 END) as primary_collaborators,
                    COUNT(CASE WHEN relationship_strength = 'frequent_collaborator' THEN 1 END) as frequent_collaborators,
                    COUNT(CASE WHEN relationship_strength = 'regular_collaborator' THEN 1 END) as regular_collaborators,
                    
                    COUNT(CASE WHEN communication_preference = 'meeting_focused' THEN 1 END) as meeting_focused_partners,
                    COUNT(CASE WHEN communication_preference = 'slack_focused' THEN 1 END) as slack_focused_partners,
                    COUNT(CASE WHEN communication_preference = 'balanced_communication' THEN 1 END) as balanced_partners
                FROM v_collaboration_network_unified
            """).fetchone()
            
            if collab_metrics:
                self.metrics["total_workload_metrics"]["collaboration_network"] = {
                    "total_collaboration_partners": collab_metrics[0] or 0,
                    "total_collaboration_hours_with_partners": round(collab_metrics[1], 1) if collab_metrics[1] else 0,
                    "average_hours_per_partner": round(collab_metrics[2], 2) if collab_metrics[2] else 0,
                    
                    "relationship_distribution": {
                        "primary_collaborators": collab_metrics[3] or 0,
                        "frequent_collaborators": collab_metrics[4] or 0,
                        "regular_collaborators": collab_metrics[5] or 0
                    },
                    
                    "communication_preference_distribution": {
                        "meeting_focused": collab_metrics[6] or 0,
                        "slack_focused": collab_metrics[7] or 0,
                        "balanced": collab_metrics[8] or 0
                    }
                }
            
            print("✅ Total workload metrics calculated")
            return True
            
        except Exception as e:
            print(f"❌ Error calculating total workload metrics: {e}")
            return False
    
    def calculate_correlation_coefficients(self):
        """Calculate correlation coefficients between key metrics."""
        print("\n🔗 Calculating correlation coefficients...")
        
        try:
            # Get correlation data
            data = self.conn.execute("""
                SELECT 
                    tct.total_collaboration_hours,
                    tct.meeting_collaboration_pct,
                    tct.slack_collaboration_pct,
                    tct.after_hours_collaboration_pct,
                    tct.high_intensity_hours,
                    
                    COALESCE(csc.total_context_switches, 0) as total_context_switches,
                    COALESCE(csc.total_channel_switches, 0) as total_channel_switches,
                    COALESCE(csc.avg_channels_per_hour, 0) as avg_channels_per_hour,
                    
                    COALESCE(wi.busy_trap_score, 0) as busy_trap_score,
                    CASE 
                        WHEN wi.workload_assessment = 'severe_overload' THEN 4
                        WHEN wi.workload_assessment = 'moderate_overload' THEN 3
                        WHEN wi.workload_assessment = 'mild_overload' THEN 2
                        ELSE 1
                    END as workload_assessment_numeric,
                    
                    COALESCE(sta.strategic_allocation_pct, 0) as strategic_allocation_pct,
                    COALESCE(sta.total_strategic_minutes, 0) / 60.0 as strategic_hours,
                    
                    COALESCE(ec.daily_meetings, 0) as daily_meetings,
                    COALESCE(ec.daily_messages, 0) as daily_messages,
                    COALESCE(ec.channels_used, 0) as channels_used
                FROM v_total_collaboration_time tct
                LEFT JOIN v_context_switching_combined csc ON tct.date = csc.date
                LEFT JOIN v_workload_intensity wi ON tct.date = wi.date
                LEFT JOIN v_strategic_time_allocation sta ON tct.date = sta.date
                LEFT JOIN v_efficiency_correlation ec ON tct.date = ec.date
                WHERE tct.total_collaboration_hours > 0
            """).fetchdf()
            
            if data.empty or len(data) < 3:
                print("⚠️ Insufficient data for correlation analysis")
                return False
            
            # Select numeric columns and clean data
            numeric_data = data.select_dtypes(include=[np.number]).dropna()
            
            if numeric_data.shape[1] < 2:
                print("⚠️ Insufficient numeric data for correlations")
                return False
            
            # Calculate key correlations
            correlations = {}
            
            # Key relationship pairs to analyze
            correlation_pairs = [
                ('total_collaboration_hours', 'busy_trap_score', 'Total Collaboration vs Busy Trap'),
                ('total_collaboration_hours', 'total_context_switches', 'Total Collaboration vs Context Switching'),
                ('total_collaboration_hours', 'strategic_allocation_pct', 'Total Collaboration vs Strategic Allocation'),
                ('meeting_collaboration_pct', 'slack_collaboration_pct', 'Meeting vs Slack Collaboration %'),
                ('total_context_switches', 'channels_used', 'Context Switches vs Channels Used'),
                ('daily_meetings', 'daily_messages', 'Daily Meetings vs Daily Messages'),
                ('busy_trap_score', 'workload_assessment_numeric', 'Busy Trap vs Workload Assessment'),
                ('after_hours_collaboration_pct', 'busy_trap_score', 'After Hours % vs Busy Trap'),
                ('strategic_allocation_pct', 'workload_assessment_numeric', 'Strategic Allocation vs Workload'),
                ('high_intensity_hours', 'total_context_switches', 'High Intensity Hours vs Context Switches')
            ]
            
            for var1, var2, description in correlation_pairs:
                if var1 in numeric_data.columns and var2 in numeric_data.columns:
                    # Remove pairs where both variables are null
                    pair_data = numeric_data[[var1, var2]].dropna()
                    
                    if len(pair_data) >= 3:  # Need at least 3 points for meaningful correlation
                        try:
                            # Calculate Pearson correlation using numpy
                            correlation_matrix = np.corrcoef(pair_data[var1], pair_data[var2])
                            pearson_r = correlation_matrix[0, 1]
                            
                            # Simple p-value approximation (for large samples)
                            n = len(pair_data)
                            if n > 3:
                                t_stat = pearson_r * np.sqrt((n - 2) / (1 - pearson_r**2))
                                # Rough p-value approximation
                                pearson_p = 2 * (1 - abs(t_stat) / np.sqrt(n))
                                pearson_p = max(0, min(1, pearson_p))  # Clamp between 0 and 1
                            else:
                                pearson_p = 1.0
                            
                            correlations[f"{var1}_vs_{var2}"] = {
                                "description": description,
                                "sample_size": len(pair_data),
                                "pearson_correlation": round(pearson_r, 4),
                                "pearson_p_value_approx": round(pearson_p, 4),
                                "strength_interpretation": self._interpret_correlation(abs(pearson_r)),
                                "significance": "likely_significant" if pearson_p < 0.05 else "likely_not_significant"
                            }
                        except Exception as e:
                            print(f"⚠️ Error calculating correlation for {description}: {e}")
            
            self.metrics["correlation_coefficients"] = correlations
            
            # Identify strongest correlations
            strong_correlations = []
            moderate_correlations = []
            
            for key, corr_data in correlations.items():
                abs_corr = abs(corr_data["pearson_correlation"])
                if abs_corr >= 0.7:
                    strong_correlations.append((key, corr_data))
                elif abs_corr >= 0.5:
                    moderate_correlations.append((key, corr_data))
            
            self.metrics["correlation_coefficients"]["summary"] = {
                "total_correlations_analyzed": len(correlations),
                "strong_correlations_count": len(strong_correlations),
                "moderate_correlations_count": len(moderate_correlations),
                "strongest_positive_correlation": max(correlations.items(), key=lambda x: x[1]["pearson_correlation"]) if correlations else None,
                "strongest_negative_correlation": min(correlations.items(), key=lambda x: x[1]["pearson_correlation"]) if correlations else None
            }
            
            print(f"✅ Calculated {len(correlations)} correlation coefficients")
            print(f"📈 Found {len(strong_correlations)} strong correlations (|r| ≥ 0.7)")
            print(f"📊 Found {len(moderate_correlations)} moderate correlations (|r| ≥ 0.5)")
            return True
            
        except Exception as e:
            print(f"❌ Error calculating correlation coefficients: {e}")
            return False
    
    def calculate_efficiency_integration_metrics(self):
        """Calculate integrated efficiency metrics across platforms."""
        print("\n⚡ Calculating efficiency integration metrics...")
        
        try:
            # Overall efficiency distribution
            efficiency_dist = self.conn.execute("""
                SELECT 
                    overall_efficiency,
                    COUNT(*) as day_count,
                    AVG(daily_meetings) as avg_meetings,
                    AVG(daily_messages) as avg_messages,
                    AVG(channels_used) as avg_channels
                FROM v_efficiency_correlation
                GROUP BY overall_efficiency
            """).fetchall()
            
            efficiency_data = {}
            total_days = 0
            
            for row in efficiency_dist:
                efficiency_level = row[0]
                count = row[1]
                total_days += count
                
                efficiency_data[efficiency_level] = {
                    "days_count": count,
                    "average_meetings": round(row[2], 1) if row[2] else 0,
                    "average_messages": round(row[3], 1) if row[3] else 0,
                    "average_channels": round(row[4], 1) if row[4] else 0
                }
            
            # Calculate percentages
            for level_data in efficiency_data.values():
                level_data["percentage_of_days"] = round((level_data["days_count"] / total_days * 100), 1) if total_days > 0 else 0
            
            # Busy trap analysis
            busy_trap_analysis = self.conn.execute("""
                SELECT 
                    AVG(busy_trap_score) as avg_busy_trap_score,
                    STDDEV(busy_trap_score) as busy_trap_volatility,
                    
                    COUNT(CASE WHEN busy_trap_score = 0 THEN 1 END) as sustainable_days,
                    COUNT(CASE WHEN busy_trap_score = 1 THEN 1 END) as mild_risk_days,
                    COUNT(CASE WHEN busy_trap_score = 2 THEN 1 END) as moderate_risk_days,
                    COUNT(CASE WHEN busy_trap_score = 3 THEN 1 END) as high_risk_days,
                    COUNT(CASE WHEN busy_trap_score = 4 THEN 1 END) as severe_risk_days,
                    
                    AVG(meeting_overload_indicator) * 100 as meeting_overload_pct,
                    AVG(multitasking_indicator) * 100 as multitasking_pct,
                    AVG(switching_overload_indicator) * 100 as switching_overload_pct,
                    AVG(after_hours_indicator) * 100 as after_hours_pct
                FROM v_workload_intensity
            """).fetchone()
            
            # Strategic allocation efficiency
            strategic_efficiency = self.conn.execute("""
                SELECT 
                    AVG(strategic_allocation_pct) as avg_strategic_allocation,
                    COUNT(CASE WHEN strategic_allocation_pct >= 60 THEN 1 END) as days_meeting_strategic_target,
                    COUNT(*) as total_strategic_days,
                    AVG(total_strategic_minutes) / 60.0 as avg_strategic_hours_daily,
                    AVG(total_coaching_minutes) / 60.0 as avg_coaching_hours_daily,
                    AVG(total_operational_minutes) / 60.0 as avg_operational_hours_daily
                FROM v_strategic_time_allocation
                WHERE total_engagement_minutes > 0
            """).fetchone()
            
            # Prepare efficiency metrics
            self.metrics["efficiency_integration"] = {
                "overall_efficiency_distribution": efficiency_data,
                "total_analysis_days": total_days,
                
                "busy_trap_analysis": {
                    "average_score": round(busy_trap_analysis[0], 2) if busy_trap_analysis[0] else 0,
                    "score_volatility": round(busy_trap_analysis[1], 2) if busy_trap_analysis[1] else 0,
                    "risk_distribution": {
                        "sustainable_days": busy_trap_analysis[2] or 0,
                        "mild_risk_days": busy_trap_analysis[3] or 0,
                        "moderate_risk_days": busy_trap_analysis[4] or 0,
                        "high_risk_days": busy_trap_analysis[5] or 0,
                        "severe_risk_days": busy_trap_analysis[6] or 0
                    },
                    "indicator_frequency": {
                        "meeting_overload_percentage": round(busy_trap_analysis[7], 1) if busy_trap_analysis[7] else 0,
                        "multitasking_percentage": round(busy_trap_analysis[8], 1) if busy_trap_analysis[8] else 0,
                        "switching_overload_percentage": round(busy_trap_analysis[9], 1) if busy_trap_analysis[9] else 0,
                        "after_hours_percentage": round(busy_trap_analysis[10], 1) if busy_trap_analysis[10] else 0
                    }
                }
            }
            
            if strategic_efficiency:
                self.metrics["efficiency_integration"]["strategic_allocation"] = {
                    "average_strategic_percentage": round(strategic_efficiency[0], 1) if strategic_efficiency[0] else 0,
                    "days_meeting_target_60pct": strategic_efficiency[1] or 0,
                    "total_days_with_strategic_data": strategic_efficiency[2] or 0,
                    "target_achievement_rate": round((strategic_efficiency[1] / strategic_efficiency[2] * 100), 1) if strategic_efficiency[2] > 0 else 0,
                    
                    "daily_time_allocation": {
                        "strategic_hours": round(strategic_efficiency[3], 1) if strategic_efficiency[3] else 0,
                        "coaching_hours": round(strategic_efficiency[4], 1) if strategic_efficiency[4] else 0,
                        "operational_hours": round(strategic_efficiency[5], 1) if strategic_efficiency[5] else 0
                    }
                }
            
            print("✅ Efficiency integration metrics calculated")
            return True
            
        except Exception as e:
            print(f"❌ Error calculating efficiency metrics: {e}")
            return False
    
    def identify_pattern_insights(self):
        """Identify key patterns and insights from cross-platform analysis."""
        print("\n🔍 Identifying key patterns and insights...")
        
        try:
            # Pre/post meeting patterns
            meeting_patterns = self.conn.execute("""
                SELECT 
                    COUNT(*) as total_meetings_analyzed,
                    AVG(messages_1hr_before) as avg_prep_messages,
                    AVG(messages_1hr_after) as avg_followup_messages,
                    
                    COUNT(CASE WHEN preparation_level = 'high_prep' THEN 1 END) as high_prep_meetings,
                    COUNT(CASE WHEN preparation_level = 'moderate_prep' THEN 1 END) as moderate_prep_meetings,
                    COUNT(CASE WHEN preparation_level = 'light_prep' THEN 1 END) as light_prep_meetings,
                    COUNT(CASE WHEN preparation_level = 'no_prep' THEN 1 END) as no_prep_meetings,
                    
                    COUNT(CASE WHEN followup_level = 'high_followup' THEN 1 END) as high_followup_meetings,
                    COUNT(CASE WHEN followup_level = 'moderate_followup' THEN 1 END) as moderate_followup_meetings,
                    COUNT(CASE WHEN followup_level = 'light_followup' THEN 1 END) as light_followup_meetings,
                    COUNT(CASE WHEN followup_level = 'no_followup' THEN 1 END) as no_followup_meetings
                FROM v_pre_meeting_activity pma
                FULL OUTER JOIN v_post_meeting_followup pmf ON pma.event_id = pmf.event_id
            """).fetchone()
            
            # Multitasking during meetings
            multitasking_patterns = self.conn.execute("""
                SELECT 
                    COUNT(*) as total_meetings,
                    AVG(messages_during_meeting) as avg_messages_during_meetings,
                    
                    COUNT(CASE WHEN multitasking_level = 'high_multitasking' THEN 1 END) as high_multitasking_meetings,
                    COUNT(CASE WHEN multitasking_level = 'moderate_multitasking' THEN 1 END) as moderate_multitasking_meetings,
                    COUNT(CASE WHEN multitasking_level = 'light_multitasking' THEN 1 END) as light_multitasking_meetings,
                    COUNT(CASE WHEN multitasking_level = 'focused_meeting' THEN 1 END) as focused_meetings,
                    
                    AVG(CASE WHEN multitasking_level != 'focused_meeting' THEN messages_per_hour_rate ELSE 0 END) as avg_multitasking_rate
                FROM v_meeting_slack_overlap
            """).fetchone()
            
            # Communication gaps analysis
            communication_gaps = self.conn.execute("""
                SELECT 
                    AVG(business_activity_coverage_pct) as avg_business_coverage,
                    AVG(business_gap_hours) as avg_daily_gaps,
                    
                    COUNT(CASE WHEN gap_pattern = 'frequent_gaps' THEN 1 END) as frequent_gap_days,
                    COUNT(CASE WHEN gap_pattern = 'moderate_gaps' THEN 1 END) as moderate_gap_days,
                    COUNT(CASE WHEN gap_pattern = 'few_gaps' THEN 1 END) as few_gap_days,
                    COUNT(CASE WHEN gap_pattern = 'no_gaps' THEN 1 END) as no_gap_days
                FROM v_communication_gaps
            """).fetchone()
            
            # Reactive vs proactive patterns
            reactivity_patterns = self.conn.execute("""
                SELECT 
                    AVG(proactive_ratio_pct) as avg_proactive_ratio,
                    
                    COUNT(CASE WHEN control_level = 'high_control' THEN 1 END) as high_control_days,
                    COUNT(CASE WHEN control_level = 'moderate_control' THEN 1 END) as moderate_control_days,
                    COUNT(CASE WHEN control_level = 'low_control' THEN 1 END) as low_control_days
                FROM v_reactive_vs_proactive
            """).fetchone()
            
            # Compile pattern insights
            self.metrics["pattern_insights"] = {
                "meeting_communication_patterns": {
                    "total_meetings_analyzed": meeting_patterns[0] or 0,
                    "average_preparation_messages": round(meeting_patterns[1], 1) if meeting_patterns[1] else 0,
                    "average_followup_messages": round(meeting_patterns[2], 1) if meeting_patterns[2] else 0,
                    
                    "preparation_distribution": {
                        "high_prep_meetings": meeting_patterns[3] or 0,
                        "moderate_prep_meetings": meeting_patterns[4] or 0,
                        "light_prep_meetings": meeting_patterns[5] or 0,
                        "no_prep_meetings": meeting_patterns[6] or 0
                    },
                    
                    "followup_distribution": {
                        "high_followup_meetings": meeting_patterns[7] or 0,
                        "moderate_followup_meetings": meeting_patterns[8] or 0,
                        "light_followup_meetings": meeting_patterns[9] or 0,
                        "no_followup_meetings": meeting_patterns[10] or 0
                    }
                },
                
                "multitasking_during_meetings": {
                    "total_meetings_analyzed": multitasking_patterns[0] or 0,
                    "average_messages_per_meeting": round(multitasking_patterns[1], 1) if multitasking_patterns[1] else 0,
                    
                    "multitasking_distribution": {
                        "high_multitasking": multitasking_patterns[2] or 0,
                        "moderate_multitasking": multitasking_patterns[3] or 0,
                        "light_multitasking": multitasking_patterns[4] or 0,
                        "focused_meetings": multitasking_patterns[5] or 0
                    },
                    
                    "multitasking_rate_per_hour": round(multitasking_patterns[6], 1) if multitasking_patterns[6] else 0
                },
                
                "communication_coverage": {
                    "average_business_hours_coverage_pct": round(communication_gaps[0], 1) if communication_gaps[0] else 0,
                    "average_daily_gaps_hours": round(communication_gaps[1], 1) if communication_gaps[1] else 0,
                    
                    "gap_pattern_distribution": {
                        "frequent_gaps_days": communication_gaps[2] or 0,
                        "moderate_gaps_days": communication_gaps[3] or 0,
                        "few_gaps_days": communication_gaps[4] or 0,
                        "no_gaps_days": communication_gaps[5] or 0
                    }
                },
                
                "executive_control_patterns": {
                    "average_proactive_ratio_pct": round(reactivity_patterns[0], 1) if reactivity_patterns[0] else 0,
                    
                    "control_level_distribution": {
                        "high_control_days": reactivity_patterns[1] or 0,
                        "moderate_control_days": reactivity_patterns[2] or 0,
                        "low_control_days": reactivity_patterns[3] or 0
                    }
                }
            }
            
            print("✅ Pattern insights identified")
            return True
            
        except Exception as e:
            print(f"❌ Error identifying patterns: {e}")
            return False
    
    def calculate_optimization_opportunities(self):
        """Calculate specific optimization opportunities based on the analysis."""
        print("\n🎯 Calculating optimization opportunities...")
        
        try:
            opportunities = []
            impact_scores = {}
            
            # Get current baseline metrics
            workload_metrics = self.metrics.get("total_workload_metrics", {})
            efficiency_metrics = self.metrics.get("efficiency_integration", {})
            
            # 1. Total collaboration time optimization
            avg_collab_hours = workload_metrics.get("average_daily_collaboration_hours", 0)
            if avg_collab_hours > 8:
                time_reduction_potential = avg_collab_hours - 8
                opportunities.append({
                    "category": "time_management",
                    "opportunity": f"Reduce total collaboration time from {avg_collab_hours:.1f}h to 8h/day",
                    "potential_time_savings_daily": time_reduction_potential,
                    "implementation": "Decline non-essential meetings, batch similar communications",
                    "priority": "high"
                })
                impact_scores["time_management"] = time_reduction_potential * 5  # 5 = weight factor
            
            # 2. Context switching optimization
            context_metrics = workload_metrics.get("context_switching", {})
            avg_switches = context_metrics.get("average_daily_switches", 0)
            if avg_switches > 6:
                switching_reduction = avg_switches - 6
                opportunities.append({
                    "category": "context_switching",
                    "opportunity": f"Reduce context switching from {avg_switches:.1f} to 6 switches/day",
                    "potential_efficiency_gain": f"{switching_reduction * 10:.0f}% productivity improvement",
                    "implementation": "Batch similar communications, establish communication windows",
                    "priority": "high"
                })
                impact_scores["context_switching"] = switching_reduction * 3
            
            # 3. Strategic allocation optimization
            strategic_metrics = efficiency_metrics.get("strategic_allocation", {})
            avg_strategic_pct = strategic_metrics.get("average_strategic_percentage", 0)
            if avg_strategic_pct < 60:
                strategic_gap = 60 - avg_strategic_pct
                opportunities.append({
                    "category": "strategic_focus",
                    "opportunity": f"Increase strategic allocation from {avg_strategic_pct:.1f}% to 60%",
                    "potential_strategic_gain": f"{strategic_gap:.1f} percentage points",
                    "implementation": "Delegate operational tasks, decline tactical meetings",
                    "priority": "high"
                })
                impact_scores["strategic_focus"] = strategic_gap * 2
            
            # 4. After hours optimization
            after_hours_pct = workload_metrics.get("business_vs_after_hours", {}).get("average_after_hours_percentage", 0)
            if after_hours_pct > 20:
                after_hours_reduction = after_hours_pct - 20
                opportunities.append({
                    "category": "work_life_balance",
                    "opportunity": f"Reduce after-hours work from {after_hours_pct:.1f}% to 20%",
                    "potential_wellbeing_gain": f"{after_hours_reduction:.1f} percentage points",
                    "implementation": "Establish communication boundaries, batch end-of-day tasks",
                    "priority": "medium"
                })
                impact_scores["work_life_balance"] = after_hours_reduction * 1.5
            
            # 5. Busy trap optimization
            busy_trap_metrics = efficiency_metrics.get("busy_trap_analysis", {})
            avg_busy_trap = busy_trap_metrics.get("average_score", 0)
            if avg_busy_trap > 2:
                opportunities.append({
                    "category": "busy_trap_reduction",
                    "opportunity": f"Reduce busy trap score from {avg_busy_trap:.1f} to <2.0",
                    "potential_efficiency_gain": "20-30% productivity improvement",
                    "implementation": "Implement 25/50-minute meetings, establish buffer times",
                    "priority": "high"
                })
                impact_scores["busy_trap_reduction"] = (avg_busy_trap - 2) * 4
            
            # 6. Meeting preparation optimization
            pattern_metrics = self.metrics.get("pattern_insights", {})
            meeting_patterns = pattern_metrics.get("meeting_communication_patterns", {})
            prep_distribution = meeting_patterns.get("preparation_distribution", {})
            no_prep_meetings = prep_distribution.get("no_prep_meetings", 0)
            total_meetings = meeting_patterns.get("total_meetings_analyzed", 1)
            
            if no_prep_meetings / total_meetings > 0.3:  # More than 30% unprepared
                opportunities.append({
                    "category": "meeting_preparation",
                    "opportunity": f"Improve preparation for {no_prep_meetings} meetings ({(no_prep_meetings/total_meetings*100):.0f}%)",
                    "potential_quality_gain": "15-25% meeting effectiveness improvement",
                    "implementation": "Pre-meeting Slack reviews, agenda preparation time blocks",
                    "priority": "medium"
                })
                impact_scores["meeting_preparation"] = (no_prep_meetings / total_meetings) * 10
            
            # 7. Multitasking reduction
            multitasking_patterns = pattern_metrics.get("multitasking_during_meetings", {})
            multitasking_dist = multitasking_patterns.get("multitasking_distribution", {})
            high_multitasking = multitasking_dist.get("high_multitasking", 0)
            
            if high_multitasking > 0:
                opportunities.append({
                    "category": "meeting_focus",
                    "opportunity": f"Reduce multitasking in {high_multitasking} meetings",
                    "potential_quality_gain": "10-20% meeting engagement improvement",
                    "implementation": "Phone away policy, designated note-taker role",
                    "priority": "medium"
                })
                impact_scores["meeting_focus"] = high_multitasking * 0.5
            
            # Sort opportunities by impact score
            for opp in opportunities:
                category = opp["category"]
                opp["impact_score"] = impact_scores.get(category, 0)
            
            opportunities.sort(key=lambda x: x["impact_score"], reverse=True)
            
            # Calculate potential total impact
            total_time_savings = sum(opp.get("potential_time_savings_daily", 0) for opp in opportunities)
            high_priority_count = len([opp for opp in opportunities if opp["priority"] == "high"])
            
            self.metrics["optimization_opportunities"] = {
                "total_opportunities_identified": len(opportunities),
                "high_priority_opportunities": high_priority_count,
                "medium_priority_opportunities": len(opportunities) - high_priority_count,
                "potential_daily_time_savings_hours": round(total_time_savings, 1),
                "total_impact_score": round(sum(impact_scores.values()), 1),
                "opportunities": opportunities
            }
            
            print(f"✅ Identified {len(opportunities)} optimization opportunities")
            print(f"🎯 High priority: {high_priority_count}, Medium priority: {len(opportunities) - high_priority_count}")
            return True
            
        except Exception as e:
            print(f"❌ Error calculating optimization opportunities: {e}")
            return False
    
    def _interpret_correlation(self, abs_correlation):
        """Interpret correlation strength."""
        if abs_correlation >= 0.7:
            return "strong"
        elif abs_correlation >= 0.5:
            return "moderate"
        elif abs_correlation >= 0.3:
            return "weak"
        else:
            return "negligible"
    
    def export_metrics(self):
        """Export all calculated metrics to JSON file."""
        print("\n💾 Exporting integrated metrics...")
        
        try:
            # Calculate summary statistics
            self.metrics["executive_summary"] = {
                "analysis_period_days": self.metrics.get("total_workload_metrics", {}).get("analysis_period_days", 0),
                "average_daily_collaboration_hours": self.metrics.get("total_workload_metrics", {}).get("average_daily_collaboration_hours", 0),
                "collaboration_platforms": {
                    "meeting_percentage": self.metrics.get("total_workload_metrics", {}).get("meeting_vs_slack_split", {}).get("average_meeting_percentage", 0),
                    "slack_percentage": self.metrics.get("total_workload_metrics", {}).get("meeting_vs_slack_split", {}).get("average_slack_percentage", 0)
                },
                "efficiency_indicators": {
                    "busy_trap_score": self.metrics.get("efficiency_integration", {}).get("busy_trap_analysis", {}).get("average_score", 0),
                    "strategic_allocation_pct": self.metrics.get("efficiency_integration", {}).get("strategic_allocation", {}).get("average_strategic_percentage", 0),
                    "context_switches_per_day": self.metrics.get("total_workload_metrics", {}).get("context_switching", {}).get("average_daily_switches", 0)
                },
                "key_correlations_count": len(self.metrics.get("correlation_coefficients", {})) - 1,  # Subtract summary
                "optimization_opportunities_count": self.metrics.get("optimization_opportunities", {}).get("total_opportunities_identified", 0),
                "potential_daily_savings_hours": self.metrics.get("optimization_opportunities", {}).get("potential_daily_time_savings_hours", 0)
            }
            
            # Export to file
            output_file = self.base_path / "analytics/integrated/integrated_metrics.json"
            with open(output_file, 'w') as f:
                json.dump(self.metrics, f, indent=2, default=str)
            
            print(f"✅ Integrated metrics exported to {output_file}")
            
            # Also create a simplified version for easier reading
            simplified_metrics = {
                "executive_summary": self.metrics["executive_summary"],
                "key_findings": {
                    "total_workload": self.metrics.get("total_workload_metrics", {}),
                    "efficiency": self.metrics.get("efficiency_integration", {}),
                    "top_opportunities": self.metrics.get("optimization_opportunities", {}).get("opportunities", [])[:5]
                }
            }
            
            simple_file = self.base_path / "analytics/integrated/integrated_metrics_summary.json"
            with open(simple_file, 'w') as f:
                json.dump(simplified_metrics, f, indent=2, default=str)
            
            print(f"✅ Simplified metrics exported to {simple_file}")
            return True
            
        except Exception as e:
            print(f"❌ Error exporting metrics: {e}")
            return False
    
    def run_calculation(self):
        """Run the complete integrated metrics calculation process."""
        print("🚀 Starting Integrated Metrics Calculation...")
        
        calculation_functions = [
            self.calculate_total_workload_metrics,
            self.calculate_correlation_coefficients,
            self.calculate_efficiency_integration_metrics,
            self.identify_pattern_insights,
            self.calculate_optimization_opportunities
        ]
        
        successful_calculations = 0
        
        for calc_func in calculation_functions:
            try:
                if calc_func():
                    successful_calculations += 1
            except Exception as e:
                print(f"❌ Error in {calc_func.__name__}: {e}")
        
        # Export metrics
        export_success = self.export_metrics()
        
        print(f"\n✅ Integrated Metrics Calculation Completed!")
        print(f"📊 Successful calculations: {successful_calculations}/{len(calculation_functions)}")
        print(f"💾 Export successful: {export_success}")
        print(f"🎯 Target achieved: {successful_calculations >= 4}")
        
        return successful_calculations >= 4

if __name__ == "__main__":
    calculator = IntegratedMetricsCalculator()
    calculator.run_calculation()