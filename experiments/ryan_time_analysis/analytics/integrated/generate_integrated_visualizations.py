#!/usr/bin/env python3
"""
Integrated Visualizations Generator
Sub-Agent 4: Cross-Platform Correlation Analysis

Generates 10+ integrated visualizations showing cross-platform correlations
between calendar and Slack activity patterns.
"""

import duckdb
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import numpy as np
import json
from pathlib import Path
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Configure matplotlib and seaborn
plt.rcParams['figure.dpi'] = 300
plt.rcParams['savefig.dpi'] = 300
plt.rcParams['font.size'] = 10
plt.style.use('default')

# Configure seaborn
sns.set_palette("husl")

class IntegratedVisualizationGenerator:
    def __init__(self, base_path="/Users/david.campos/VibeCode/AICoS-Lab/experiments/ryan_time_analysis"):
        self.base_path = Path(base_path)
        self.calendar_db_path = self.base_path / "data/processed/duckdb/calendar_analytics.db"
        self.slack_db_path = self.base_path / "data/processed/duckdb/slack_analytics.db"
        self.integrated_db_path = self.base_path / "analytics/integrated/unified_analytics.db"
        self.output_dir = self.base_path / "visualizations/integrated"
        
        # Create output directory
        self.output_dir.mkdir(exist_ok=True)
        
        # Initialize database connection
        self.conn = duckdb.connect(str(self.integrated_db_path))
        self.conn.execute(f"ATTACH '{self.calendar_db_path}' AS calendar_db")
        self.conn.execute(f"ATTACH '{self.slack_db_path}' AS slack_db")
        
        print("🎨 Integrated Visualizations Generator")
        print(f"📊 Database: {self.integrated_db_path}")
        print(f"📁 Output: {self.output_dir}")
        
        # Color schemes for consistency
        self.colors = {
            'calendar': '#1f77b4',
            'slack': '#ff7f0e', 
            'combined': '#2ca02c',
            'correlation': '#d62728',
            'high': '#e74c3c',
            'moderate': '#f39c12',
            'low': '#2ecc71'
        }
        
        self.visualizations_created = []
        
    def create_combined_workload_heatmap(self):
        """Create a heatmap showing combined workload across meetings + Slack."""
        print("\n📊 Creating combined workload heatmap...")
        
        try:
            # Get hourly workload data
            data = self.conn.execute("""
                SELECT 
                    day_of_week,
                    hour,
                    AVG(meeting_minutes) as avg_meeting_minutes,
                    AVG(message_count * 2) as avg_slack_minutes,
                    AVG(combined_workload_score) as avg_combined_score,
                    COUNT(*) as sample_size,
                    MAX(combined_workload_score) as max_combined_score
                FROM v_hourly_correlation
                WHERE meeting_count > 0 OR message_count > 0
                GROUP BY day_of_week, hour
                ORDER BY day_of_week, hour
            """).fetchdf()
            
            if data.empty:
                print("⚠️ No data available for combined workload heatmap")
                return False
            
            # Create pivot table for heatmap
            workload_matrix = data.pivot(index='hour', columns='day_of_week', values='avg_combined_score')
            meeting_matrix = data.pivot(index='hour', columns='day_of_week', values='avg_meeting_minutes')
            slack_matrix = data.pivot(index='hour', columns='day_of_week', values='avg_slack_minutes')
            
            # Create subplots
            fig, axes = plt.subplots(1, 3, figsize=(24, 8))
            
            # Combined workload heatmap
            sns.heatmap(workload_matrix, annot=True, fmt='.0f', cmap='YlOrRd', 
                       ax=axes[0], cbar_kws={'label': 'Combined Workload Score'})
            axes[0].set_title('Combined Workload (Meetings + Slack)\nHeatmap by Hour and Day', fontsize=14, fontweight='bold')
            axes[0].set_xlabel('Day of Week (0=Sunday)')
            axes[0].set_ylabel('Hour of Day')
            
            # Meeting workload heatmap
            sns.heatmap(meeting_matrix, annot=True, fmt='.0f', cmap='Blues',
                       ax=axes[1], cbar_kws={'label': 'Meeting Minutes'})
            axes[1].set_title('Meeting Workload Only', fontsize=14, fontweight='bold')
            axes[1].set_xlabel('Day of Week (0=Sunday)')
            axes[1].set_ylabel('Hour of Day')
            
            # Slack workload heatmap  
            sns.heatmap(slack_matrix, annot=True, fmt='.0f', cmap='Oranges',
                       ax=axes[2], cbar_kws={'label': 'Estimated Slack Minutes'})
            axes[2].set_title('Slack Communication Workload', fontsize=14, fontweight='bold')
            axes[2].set_xlabel('Day of Week (0=Sunday)')
            axes[2].set_ylabel('Hour of Day')
            
            plt.tight_layout()
            
            # Save static version
            static_path = self.output_dir / '01_combined_workload_heatmap.png'
            plt.savefig(static_path, bbox_inches='tight', facecolor='white')
            plt.close()
            
            # Create interactive version with Plotly
            fig_interactive = make_subplots(
                rows=1, cols=3,
                subplot_titles=['Combined Workload', 'Meeting Workload', 'Slack Workload'],
                horizontal_spacing=0.08
            )
            
            # Add heatmaps
            fig_interactive.add_trace(
                go.Heatmap(z=workload_matrix.values, 
                          x=workload_matrix.columns, 
                          y=workload_matrix.index,
                          colorscale='YlOrRd',
                          name='Combined'),
                row=1, col=1
            )
            
            fig_interactive.add_trace(
                go.Heatmap(z=meeting_matrix.values,
                          x=meeting_matrix.columns,
                          y=meeting_matrix.index, 
                          colorscale='Blues',
                          name='Meetings'),
                row=1, col=2
            )
            
            fig_interactive.add_trace(
                go.Heatmap(z=slack_matrix.values,
                          x=slack_matrix.columns,
                          y=slack_matrix.index,
                          colorscale='Oranges', 
                          name='Slack'),
                row=1, col=3
            )
            
            fig_interactive.update_layout(
                title='Combined Workload Analysis: Calendar + Slack Integration',
                height=500,
                showlegend=False
            )
            
            # Save interactive version
            interactive_path = self.output_dir / '01_combined_workload_heatmap_interactive.html'
            fig_interactive.write_html(str(interactive_path))
            
            self.visualizations_created.append({
                'name': 'Combined Workload Heatmap',
                'static_path': str(static_path),
                'interactive_path': str(interactive_path),
                'description': 'Hourly workload patterns combining meetings and Slack activity'
            })
            
            print("✅ Combined workload heatmap created")
            return True
            
        except Exception as e:
            print(f"❌ Error creating combined workload heatmap: {e}")
            return False
    
    def create_total_engagement_timeline(self):
        """Create timeline showing total engagement across platforms."""
        print("\n📈 Creating total engagement timeline...")
        
        try:
            data = self.conn.execute("""
                SELECT 
                    date,
                    day_of_week,
                    total_collaboration_hours,
                    meeting_collaboration_pct,
                    slack_collaboration_pct,
                    business_hours_collaboration_minutes / 60.0 as business_hours,
                    after_hours_collaboration_minutes / 60.0 as after_hours,
                    collaboration_intensity
                FROM v_total_collaboration_time
                ORDER BY date
            """).fetchdf()
            
            if data.empty:
                print("⚠️ No data available for engagement timeline")
                return False
            
            # Convert date column
            data['date'] = pd.to_datetime(data['date'])
            
            # Create figure with multiple subplots
            fig, axes = plt.subplots(3, 1, figsize=(16, 12))
            
            # 1. Total engagement timeline
            axes[0].plot(data['date'], data['total_collaboration_hours'], 
                        color=self.colors['combined'], linewidth=2, label='Total Collaboration')
            axes[0].fill_between(data['date'], 0, data['total_collaboration_hours'], 
                               alpha=0.3, color=self.colors['combined'])
            
            # Add intensity color coding
            intensity_colors = {'very_high': 'red', 'high': 'orange', 'moderate': 'yellow', 'low': 'green'}
            for intensity, color in intensity_colors.items():
                mask = data['collaboration_intensity'] == intensity
                if mask.any():
                    axes[0].scatter(data[mask]['date'], data[mask]['total_collaboration_hours'], 
                                  c=color, alpha=0.7, s=50, label=f'{intensity.title()} Intensity', zorder=5)
            
            axes[0].set_title('Total Daily Engagement (Calendar + Slack)', fontsize=14, fontweight='bold')
            axes[0].set_ylabel('Hours per Day')
            axes[0].legend(bbox_to_anchor=(1.05, 1), loc='upper left')
            axes[0].grid(True, alpha=0.3)
            
            # 2. Business vs after hours breakdown
            axes[1].stackplot(data['date'], 
                             data['business_hours'], data['after_hours'],
                             labels=['Business Hours', 'After Hours'],
                             colors=[self.colors['calendar'], self.colors['slack']],
                             alpha=0.7)
            axes[1].set_title('Business Hours vs After Hours Engagement', fontsize=14, fontweight='bold')
            axes[1].set_ylabel('Hours per Day')
            axes[1].legend(bbox_to_anchor=(1.05, 1), loc='upper left')
            axes[1].grid(True, alpha=0.3)
            
            # 3. Platform distribution
            meeting_hours = data['total_collaboration_hours'] * data['meeting_collaboration_pct'] / 100
            slack_hours = data['total_collaboration_hours'] * data['slack_collaboration_pct'] / 100
            
            axes[2].stackplot(data['date'],
                             meeting_hours, slack_hours,
                             labels=['Meeting Hours', 'Slack Hours'],
                             colors=[self.colors['calendar'], self.colors['slack']],
                             alpha=0.7)
            axes[2].set_title('Platform Distribution: Meetings vs Slack', fontsize=14, fontweight='bold')
            axes[2].set_ylabel('Hours per Day')
            axes[2].set_xlabel('Date')
            axes[2].legend(bbox_to_anchor=(1.05, 1), loc='upper left')
            axes[2].grid(True, alpha=0.3)
            
            # Format x-axis
            for ax in axes:
                ax.tick_params(axis='x', rotation=45)
            
            plt.tight_layout()
            
            # Save static version
            static_path = self.output_dir / '02_total_engagement_timeline.png'
            plt.savefig(static_path, bbox_inches='tight', facecolor='white')
            plt.close()
            
            # Create interactive version
            fig_interactive = make_subplots(
                rows=3, cols=1,
                subplot_titles=['Total Engagement', 'Business vs After Hours', 'Platform Distribution'],
                vertical_spacing=0.08
            )
            
            # Total engagement with intensity markers
            fig_interactive.add_trace(
                go.Scatter(x=data['date'], y=data['total_collaboration_hours'],
                          mode='lines+markers', name='Total Collaboration',
                          line=dict(color=self.colors['combined'], width=3),
                          marker=dict(size=6)),
                row=1, col=1
            )
            
            # Business vs after hours
            fig_interactive.add_trace(
                go.Scatter(x=data['date'], y=data['business_hours'],
                          mode='lines', name='Business Hours',
                          stackgroup='one', line=dict(color=self.colors['calendar'])),
                row=2, col=1
            )
            
            fig_interactive.add_trace(
                go.Scatter(x=data['date'], y=data['after_hours'],
                          mode='lines', name='After Hours',
                          stackgroup='one', line=dict(color=self.colors['slack'])),
                row=2, col=1
            )
            
            # Platform distribution
            fig_interactive.add_trace(
                go.Scatter(x=data['date'], y=meeting_hours,
                          mode='lines', name='Meeting Hours',
                          stackgroup='two', line=dict(color=self.colors['calendar'])),
                row=3, col=1
            )
            
            fig_interactive.add_trace(
                go.Scatter(x=data['date'], y=slack_hours,
                          mode='lines', name='Slack Hours',
                          stackgroup='two', line=dict(color=self.colors['slack'])),
                row=3, col=1
            )
            
            fig_interactive.update_layout(
                title='Total Engagement Timeline: Cross-Platform Analysis',
                height=800,
                showlegend=True
            )
            
            # Save interactive version
            interactive_path = self.output_dir / '02_total_engagement_timeline_interactive.html'
            fig_interactive.write_html(str(interactive_path))
            
            self.visualizations_created.append({
                'name': 'Total Engagement Timeline',
                'static_path': str(static_path),
                'interactive_path': str(interactive_path),
                'description': 'Daily engagement patterns across calendar and Slack platforms'
            })
            
            print("✅ Total engagement timeline created")
            return True
            
        except Exception as e:
            print(f"❌ Error creating engagement timeline: {e}")
            return False
    
    def create_pre_post_meeting_patterns(self):
        """Create visualization of pre/post-meeting communication patterns."""
        print("\n🔄 Creating pre/post-meeting patterns visualization...")
        
        try:
            # Get pre-meeting data
            pre_data = self.conn.execute("""
                SELECT 
                    preparation_level,
                    COUNT(*) as meeting_count,
                    AVG(messages_1hr_before) as avg_messages_1hr,
                    AVG(messages_30min_before) as avg_messages_30min,
                    AVG(messages_15min_before) as avg_messages_15min,
                    AVG(duration_minutes) as avg_meeting_duration,
                    AVG(attendee_count) as avg_attendees
                FROM v_pre_meeting_activity
                WHERE preparation_level IS NOT NULL
                GROUP BY preparation_level
            """).fetchdf()
            
            # Get post-meeting data
            post_data = self.conn.execute("""
                SELECT 
                    followup_level,
                    COUNT(*) as meeting_count,
                    AVG(messages_1hr_after) as avg_messages_1hr,
                    AVG(messages_30min_after) as avg_messages_30min,
                    AVG(messages_15min_after) as avg_messages_15min,
                    AVG(duration_minutes) as avg_meeting_duration,
                    AVG(attendee_count) as avg_attendees
                FROM v_post_meeting_followup
                WHERE followup_level IS NOT NULL
                GROUP BY followup_level
            """).fetchdf()
            
            if pre_data.empty and post_data.empty:
                print("⚠️ No data available for pre/post-meeting patterns")
                return False
            
            # Create figure
            fig, axes = plt.subplots(2, 2, figsize=(16, 12))
            
            # 1. Pre-meeting preparation levels
            if not pre_data.empty:
                prep_order = ['no_prep', 'light_prep', 'moderate_prep', 'high_prep']
                pre_data = pre_data.set_index('preparation_level').reindex(prep_order).fillna(0)
                
                bars1 = axes[0,0].bar(range(len(pre_data)), pre_data['meeting_count'], 
                                     color=self.colors['calendar'], alpha=0.7)
                axes[0,0].set_title('Meeting Distribution by Preparation Level', fontsize=14, fontweight='bold')
                axes[0,0].set_xlabel('Preparation Level')
                axes[0,0].set_ylabel('Number of Meetings')
                axes[0,0].set_xticks(range(len(pre_data)))
                axes[0,0].set_xticklabels([p.replace('_', ' ').title() for p in prep_order], rotation=45)
                
                # Add value labels on bars
                for bar, count in zip(bars1, pre_data['meeting_count']):
                    if count > 0:
                        axes[0,0].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                                     f'{int(count)}', ha='center', va='bottom')
            
            # 2. Pre-meeting activity intensity
            if not pre_data.empty:
                time_periods = ['15min', '30min', '1hr']
                prep_colors = ['#e74c3c', '#f39c12', '#2ecc71', '#3498db']
                
                x = np.arange(len(time_periods))
                width = 0.2
                
                for i, (prep_level, color) in enumerate(zip(prep_order, prep_colors)):
                    if prep_level in pre_data.index:
                        values = [
                            pre_data.loc[prep_level, 'avg_messages_15min'],
                            pre_data.loc[prep_level, 'avg_messages_30min'], 
                            pre_data.loc[prep_level, 'avg_messages_1hr']
                        ]
                        axes[0,1].bar(x + i*width, values, width, label=prep_level.replace('_', ' ').title(), 
                                    color=color, alpha=0.7)
                
                axes[0,1].set_title('Pre-Meeting Slack Activity by Time Window', fontsize=14, fontweight='bold')
                axes[0,1].set_xlabel('Time Before Meeting')
                axes[0,1].set_ylabel('Average Messages')
                axes[0,1].set_xticks(x + width * 1.5)
                axes[0,1].set_xticklabels(time_periods)
                axes[0,1].legend(bbox_to_anchor=(1.05, 1), loc='upper left')
            
            # 3. Post-meeting followup levels  
            if not post_data.empty:
                followup_order = ['no_followup', 'light_followup', 'moderate_followup', 'high_followup']
                post_data = post_data.set_index('followup_level').reindex(followup_order).fillna(0)
                
                bars2 = axes[1,0].bar(range(len(post_data)), post_data['meeting_count'],
                                     color=self.colors['slack'], alpha=0.7)
                axes[1,0].set_title('Meeting Distribution by Followup Level', fontsize=14, fontweight='bold')
                axes[1,0].set_xlabel('Followup Level') 
                axes[1,0].set_ylabel('Number of Meetings')
                axes[1,0].set_xticks(range(len(post_data)))
                axes[1,0].set_xticklabels([f.replace('_', ' ').title() for f in followup_order], rotation=45)
                
                # Add value labels on bars
                for bar, count in zip(bars2, post_data['meeting_count']):
                    if count > 0:
                        axes[1,0].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                                     f'{int(count)}', ha='center', va='bottom')
            
            # 4. Post-meeting activity intensity
            if not post_data.empty:
                followup_colors = ['#95a5a6', '#f39c12', '#e67e22', '#e74c3c']
                
                x = np.arange(len(time_periods))
                width = 0.2
                
                for i, (followup_level, color) in enumerate(zip(followup_order, followup_colors)):
                    if followup_level in post_data.index:
                        values = [
                            post_data.loc[followup_level, 'avg_messages_15min'],
                            post_data.loc[followup_level, 'avg_messages_30min'],
                            post_data.loc[followup_level, 'avg_messages_1hr']
                        ]
                        axes[1,1].bar(x + i*width, values, width, label=followup_level.replace('_', ' ').title(),
                                    color=color, alpha=0.7)
                
                axes[1,1].set_title('Post-Meeting Slack Activity by Time Window', fontsize=14, fontweight='bold')
                axes[1,1].set_xlabel('Time After Meeting')
                axes[1,1].set_ylabel('Average Messages')
                axes[1,1].set_xticks(x + width * 1.5)
                axes[1,1].set_xticklabels(time_periods)
                axes[1,1].legend(bbox_to_anchor=(1.05, 1), loc='upper left')
            
            plt.tight_layout()
            
            # Save static version
            static_path = self.output_dir / '03_pre_post_meeting_patterns.png'
            plt.savefig(static_path, bbox_inches='tight', facecolor='white')
            plt.close()
            
            self.visualizations_created.append({
                'name': 'Pre/Post-Meeting Patterns',
                'static_path': str(static_path),
                'interactive_path': None,
                'description': 'Slack communication patterns before and after meetings'
            })
            
            print("✅ Pre/post-meeting patterns created")
            return True
            
        except Exception as e:
            print(f"❌ Error creating pre/post-meeting patterns: {e}")
            return False
    
    def create_context_switching_analysis(self):
        """Create visualization of context switching patterns."""
        print("\n🔄 Creating context switching analysis...")
        
        try:
            # Get context switching data
            data = self.conn.execute("""
                SELECT 
                    date,
                    total_context_switches,
                    total_channel_switches,
                    total_meeting_context_switches,
                    switching_intensity,
                    avg_channels_per_hour,
                    max_channels_per_hour,
                    active_hours
                FROM v_context_switching_combined
                ORDER BY date
            """).fetchdf()
            
            if data.empty:
                print("⚠️ No data available for context switching analysis")
                return False
            
            # Convert date column
            data['date'] = pd.to_datetime(data['date'])
            
            # Create figure
            fig, axes = plt.subplots(2, 2, figsize=(16, 12))
            
            # 1. Context switching timeline
            axes[0,0].plot(data['date'], data['total_context_switches'], 
                          color=self.colors['correlation'], linewidth=2, marker='o', markersize=4)
            
            # Color code by intensity
            intensity_colors = {'very_high': 'red', 'high': 'orange', 'moderate': 'yellow', 'low': 'green'}
            for intensity, color in intensity_colors.items():
                mask = data['switching_intensity'] == intensity
                if mask.any():
                    axes[0,0].scatter(data[mask]['date'], data[mask]['total_context_switches'], 
                                    c=color, alpha=0.8, s=60, zorder=5)
            
            axes[0,0].set_title('Daily Context Switching Frequency', fontsize=14, fontweight='bold')
            axes[0,0].set_ylabel('Total Context Switches')
            axes[0,0].grid(True, alpha=0.3)
            axes[0,0].tick_params(axis='x', rotation=45)
            
            # 2. Switching intensity distribution
            intensity_counts = data['switching_intensity'].value_counts()
            colors = [intensity_colors.get(level, 'gray') for level in intensity_counts.index]
            
            wedges, texts, autotexts = axes[0,1].pie(intensity_counts.values, labels=intensity_counts.index, 
                                                   colors=colors, autopct='%1.1f%%', startangle=90)
            axes[0,1].set_title('Context Switching Intensity Distribution', fontsize=14, fontweight='bold')
            
            # 3. Channel vs meeting switches breakdown
            axes[1,0].bar(data['date'], data['total_channel_switches'], 
                         label='Channel Switches', color=self.colors['slack'], alpha=0.7)
            axes[1,0].bar(data['date'], data['total_meeting_context_switches'], 
                         bottom=data['total_channel_switches'], label='Meeting Switches', 
                         color=self.colors['calendar'], alpha=0.7)
            
            axes[1,0].set_title('Context Switching Breakdown: Channels vs Meetings', fontsize=14, fontweight='bold')
            axes[1,0].set_ylabel('Number of Switches')
            axes[1,0].set_xlabel('Date')
            axes[1,0].legend()
            axes[1,0].tick_params(axis='x', rotation=45)
            axes[1,0].grid(True, alpha=0.3)
            
            # 4. Average vs max channels correlation
            axes[1,1].scatter(data['avg_channels_per_hour'], data['total_context_switches'], 
                            c=data['active_hours'], cmap='viridis', alpha=0.7, s=50)
            
            # Add trend line
            z = np.polyfit(data['avg_channels_per_hour'], data['total_context_switches'], 1)
            p = np.poly1d(z)
            axes[1,1].plot(data['avg_channels_per_hour'], p(data['avg_channels_per_hour']), 
                          "r--", alpha=0.8, linewidth=2)
            
            # Calculate correlation
            correlation = data['avg_channels_per_hour'].corr(data['total_context_switches'])
            
            axes[1,1].set_title(f'Channels vs Context Switches\n(Correlation: r={correlation:.3f})', 
                               fontsize=14, fontweight='bold')
            axes[1,1].set_xlabel('Average Channels per Hour')
            axes[1,1].set_ylabel('Total Context Switches')
            
            # Add colorbar
            cbar = plt.colorbar(axes[1,1].collections[0], ax=axes[1,1])
            cbar.set_label('Active Hours per Day')
            
            plt.tight_layout()
            
            # Save static version
            static_path = self.output_dir / '04_context_switching_analysis.png'
            plt.savefig(static_path, bbox_inches='tight', facecolor='white')
            plt.close()
            
            self.visualizations_created.append({
                'name': 'Context Switching Analysis',
                'static_path': str(static_path),
                'interactive_path': None,
                'description': 'Analysis of context switching patterns across meetings and Slack channels'
            })
            
            print("✅ Context switching analysis created")
            return True
            
        except Exception as e:
            print(f"❌ Error creating context switching analysis: {e}")
            return False
    
    def create_strategic_operational_allocation(self):
        """Create visualization of strategic vs operational time allocation."""
        print("\n🎯 Creating strategic vs operational allocation visualization...")
        
        try:
            data = self.conn.execute("""
                SELECT 
                    date,
                    total_strategic_minutes / 60.0 as strategic_hours,
                    total_coaching_minutes / 60.0 as coaching_hours, 
                    total_operational_minutes / 60.0 as operational_hours,
                    total_engagement_minutes / 60.0 as total_hours,
                    strategic_allocation_pct
                FROM v_strategic_time_allocation
                WHERE total_engagement_minutes > 0
                ORDER BY date
            """).fetchdf()
            
            if data.empty:
                print("⚠️ No data available for strategic allocation")
                return False
            
            # Convert date column
            data['date'] = pd.to_datetime(data['date'])
            
            # Create figure
            fig, axes = plt.subplots(2, 2, figsize=(16, 12))
            
            # 1. Stacked time allocation timeline
            axes[0,0].stackplot(data['date'], 
                               data['strategic_hours'], data['coaching_hours'], data['operational_hours'],
                               labels=['Strategic', 'Coaching', 'Operational'],
                               colors=['#e74c3c', '#f39c12', '#3498db'],
                               alpha=0.7)
            
            axes[0,0].set_title('Daily Time Allocation: Strategic vs Operational', fontsize=14, fontweight='bold')
            axes[0,0].set_ylabel('Hours per Day')
            axes[0,0].legend(bbox_to_anchor=(1.05, 1), loc='upper left')
            axes[0,0].grid(True, alpha=0.3)
            axes[0,0].tick_params(axis='x', rotation=45)
            
            # 2. Strategic allocation percentage trend
            axes[0,1].plot(data['date'], data['strategic_allocation_pct'], 
                          color=self.colors['correlation'], linewidth=2, marker='o', markersize=4)
            axes[0,1].axhline(y=60, color='green', linestyle='--', alpha=0.7, label='Target: 60%')
            axes[0,1].fill_between(data['date'], data['strategic_allocation_pct'], 
                                  alpha=0.3, color=self.colors['correlation'])
            
            axes[0,1].set_title('Strategic Allocation Percentage Over Time', fontsize=14, fontweight='bold')
            axes[0,1].set_ylabel('Strategic Allocation %')
            axes[0,1].legend()
            axes[0,1].grid(True, alpha=0.3)
            axes[0,1].tick_params(axis='x', rotation=45)
            
            # 3. Distribution of allocation percentages
            bins = np.arange(0, 101, 10)
            axes[1,0].hist(data['strategic_allocation_pct'], bins=bins, 
                          color=self.colors['high'], alpha=0.7, edgecolor='black')
            axes[1,0].axvline(x=data['strategic_allocation_pct'].mean(), 
                            color='red', linestyle='-', linewidth=2, label=f'Mean: {data["strategic_allocation_pct"].mean():.1f}%')
            axes[1,0].axvline(x=60, color='green', linestyle='--', linewidth=2, label='Target: 60%')
            
            axes[1,0].set_title('Strategic Allocation Distribution', fontsize=14, fontweight='bold')
            axes[1,0].set_xlabel('Strategic Allocation %')
            axes[1,0].set_ylabel('Number of Days')
            axes[1,0].legend()
            axes[1,0].grid(True, alpha=0.3)
            
            # 4. Correlation: Total hours vs strategic percentage
            axes[1,1].scatter(data['total_hours'], data['strategic_allocation_pct'], 
                            alpha=0.6, s=60, color=self.colors['combined'])
            
            # Add trend line
            z = np.polyfit(data['total_hours'], data['strategic_allocation_pct'], 1)
            p = np.poly1d(z)
            axes[1,1].plot(data['total_hours'], p(data['total_hours']), 
                          "r--", alpha=0.8, linewidth=2)
            
            # Calculate correlation
            correlation = data['total_hours'].corr(data['strategic_allocation_pct'])
            
            axes[1,1].set_title(f'Total Engagement vs Strategic Focus\n(Correlation: r={correlation:.3f})', 
                               fontsize=14, fontweight='bold')
            axes[1,1].set_xlabel('Total Engagement Hours')
            axes[1,1].set_ylabel('Strategic Allocation %')
            axes[1,1].grid(True, alpha=0.3)
            
            plt.tight_layout()
            
            # Save static version
            static_path = self.output_dir / '05_strategic_operational_allocation.png'
            plt.savefig(static_path, bbox_inches='tight', facecolor='white')
            plt.close()
            
            self.visualizations_created.append({
                'name': 'Strategic vs Operational Allocation',
                'static_path': str(static_path),
                'interactive_path': None,
                'description': 'Time allocation analysis across strategic, coaching, and operational activities'
            })
            
            print("✅ Strategic vs operational allocation created")
            return True
            
        except Exception as e:
            print(f"❌ Error creating strategic allocation visualization: {e}")
            return False
    
    def create_collaboration_network_unified(self):
        """Create unified collaboration network visualization."""
        print("\n🤝 Creating collaboration network visualization...")
        
        try:
            data = self.conn.execute("""
                SELECT 
                    partner_name,
                    domain,
                    total_collaboration_hours,
                    meeting_count,
                    slack_interactions,
                    relationship_strength,
                    communication_preference
                FROM v_collaboration_network_unified
                WHERE total_collaboration_hours >= 1  -- Focus on meaningful collaborations
                ORDER BY total_collaboration_hours DESC
                LIMIT 20
            """).fetchdf()
            
            if data.empty:
                print("⚠️ No data available for collaboration network")
                return False
            
            # Create figure
            fig, axes = plt.subplots(2, 2, figsize=(16, 12))
            
            # 1. Top collaborators by total hours
            top_partners = data.head(10)
            
            bars = axes[0,0].barh(range(len(top_partners)), top_partners['total_collaboration_hours'])
            
            # Color bars by communication preference
            pref_colors = {'meeting_focused': self.colors['calendar'], 
                          'slack_focused': self.colors['slack'],
                          'balanced_communication': self.colors['combined']}
            
            for i, (bar, pref) in enumerate(zip(bars, top_partners['communication_preference'])):
                bar.set_color(pref_colors.get(pref, 'gray'))
            
            axes[0,0].set_title('Top Collaboration Partners', fontsize=14, fontweight='bold')
            axes[0,0].set_xlabel('Total Collaboration Hours')
            axes[0,0].set_yticks(range(len(top_partners)))
            axes[0,0].set_yticklabels(top_partners['partner_name'], fontsize=9)
            
            # Add value labels
            for i, (bar, hours) in enumerate(zip(bars, top_partners['total_collaboration_hours'])):
                axes[0,0].text(bar.get_width() + 0.1, bar.get_y() + bar.get_height()/2,
                              f'{hours:.1f}h', ha='left', va='center', fontsize=8)
            
            # 2. Relationship strength distribution
            strength_counts = data['relationship_strength'].value_counts()
            strength_colors = {'primary_collaborator': '#e74c3c', 'frequent_collaborator': '#f39c12',
                             'regular_collaborator': '#2ecc71', 'occasional_collaborator': '#95a5a6'}
            
            colors = [strength_colors.get(level, 'gray') for level in strength_counts.index]
            
            wedges, texts, autotexts = axes[0,1].pie(strength_counts.values, labels=strength_counts.index,
                                                   colors=colors, autopct='%1.1f%%', startangle=90)
            axes[0,1].set_title('Relationship Strength Distribution', fontsize=14, fontweight='bold')
            
            # 3. Communication preference analysis
            pref_counts = data['communication_preference'].value_counts()
            pref_bar_colors = [pref_colors.get(pref, 'gray') for pref in pref_counts.index]
            
            axes[1,0].bar(range(len(pref_counts)), pref_counts.values, color=pref_bar_colors)
            axes[1,0].set_title('Communication Preference Distribution', fontsize=14, fontweight='bold')
            axes[1,0].set_ylabel('Number of Partners')
            axes[1,0].set_xticks(range(len(pref_counts)))
            axes[1,0].set_xticklabels([pref.replace('_', ' ').title() for pref in pref_counts.index], 
                                    rotation=45)
            
            # Add value labels
            for i, (bar, count) in enumerate(zip(axes[1,0].patches, pref_counts.values)):
                axes[1,0].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
                              f'{count}', ha='center', va='bottom')
            
            # 4. Meeting vs Slack correlation
            # Only include partners with both meeting and slack data
            correlation_data = data[(data['meeting_count'] > 0) & (data['slack_interactions'] > 0)]
            
            if not correlation_data.empty:
                scatter = axes[1,1].scatter(correlation_data['meeting_count'], 
                                          correlation_data['slack_interactions'],
                                          c=correlation_data['total_collaboration_hours'],
                                          cmap='viridis', alpha=0.7, s=80)
                
                # Add trend line if we have enough data points
                if len(correlation_data) >= 3:
                    z = np.polyfit(correlation_data['meeting_count'], correlation_data['slack_interactions'], 1)
                    p = np.poly1d(z)
                    x_trend = np.linspace(correlation_data['meeting_count'].min(), 
                                        correlation_data['meeting_count'].max(), 100)
                    axes[1,1].plot(x_trend, p(x_trend), "r--", alpha=0.8, linewidth=2)
                    
                    # Calculate correlation
                    correlation = correlation_data['meeting_count'].corr(correlation_data['slack_interactions'])
                    title_suffix = f'\n(Correlation: r={correlation:.3f})'
                else:
                    title_suffix = ''
                
                axes[1,1].set_title(f'Meeting vs Slack Activity{title_suffix}', fontsize=14, fontweight='bold')
                axes[1,1].set_xlabel('Meeting Count')
                axes[1,1].set_ylabel('Slack Interactions')
                
                # Add colorbar
                cbar = plt.colorbar(scatter, ax=axes[1,1])
                cbar.set_label('Total Collaboration Hours')
            else:
                axes[1,1].text(0.5, 0.5, 'Insufficient data for correlation analysis', 
                              ha='center', va='center', transform=axes[1,1].transAxes)
                axes[1,1].set_title('Meeting vs Slack Activity', fontsize=14, fontweight='bold')
            
            plt.tight_layout()
            
            # Save static version
            static_path = self.output_dir / '06_collaboration_network.png'
            plt.savefig(static_path, bbox_inches='tight', facecolor='white')
            plt.close()
            
            self.visualizations_created.append({
                'name': 'Collaboration Network Unified',
                'static_path': str(static_path),
                'interactive_path': None,
                'description': 'Unified view of collaboration patterns across meetings and Slack'
            })
            
            print("✅ Collaboration network visualization created")
            return True
            
        except Exception as e:
            print(f"❌ Error creating collaboration network: {e}")
            return False
    
    def create_correlation_matrix(self):
        """Create correlation matrix showing relationships between key metrics."""
        print("\n📊 Creating correlation matrix...")
        
        try:
            # Get correlation data
            data = self.conn.execute("""
                SELECT 
                    tct.total_collaboration_hours,
                    tct.meeting_collaboration_pct,
                    tct.after_hours_collaboration_pct,
                    csc.total_context_switches,
                    wi.busy_trap_score,
                    ec.daily_meetings,
                    ec.daily_messages,
                    ec.channels_used,
                    sta.strategic_allocation_pct
                FROM v_total_collaboration_time tct
                LEFT JOIN v_context_switching_combined csc ON tct.date = csc.date
                LEFT JOIN v_workload_intensity wi ON tct.date = wi.date  
                LEFT JOIN v_efficiency_correlation ec ON tct.date = ec.date
                LEFT JOIN v_strategic_time_allocation sta ON tct.date = sta.date
                WHERE tct.total_collaboration_hours > 0
            """).fetchdf()
            
            if data.empty:
                print("⚠️ No data available for correlation matrix")
                return False
            
            # Select numeric columns and remove nulls
            data = data.select_dtypes(include=[np.number]).dropna()
            
            if data.shape[1] < 2:
                print("⚠️ Insufficient numeric data for correlation matrix")
                return False
            
            # Calculate correlation matrix
            correlation_matrix = data.corr()
            
            # Create figure
            fig, axes = plt.subplots(1, 2, figsize=(20, 8))
            
            # 1. Full correlation heatmap
            mask = np.triu(np.ones_like(correlation_matrix))
            im1 = axes[0].imshow(correlation_matrix.values, cmap='RdBu_r', vmin=-1, vmax=1)
            
            # Add text annotations
            for i in range(len(correlation_matrix)):
                for j in range(len(correlation_matrix.columns)):
                    if not mask[i, j]:  # Only show lower triangle
                        text = axes[0].text(j, i, f'{correlation_matrix.iloc[i, j]:.2f}',
                                          ha="center", va="center", color="white" if abs(correlation_matrix.iloc[i, j]) > 0.5 else "black")
            
            axes[0].set_title('Cross-Platform Metrics Correlation Matrix', fontsize=14, fontweight='bold')
            axes[0].set_xticks(range(len(correlation_matrix.columns)))
            axes[0].set_yticks(range(len(correlation_matrix.index)))
            axes[0].set_xticklabels([col.replace('_', ' ').title() for col in correlation_matrix.columns], rotation=45, ha='right')
            axes[0].set_yticklabels([col.replace('_', ' ').title() for col in correlation_matrix.index])
            
            # Add colorbar
            cbar1 = plt.colorbar(im1, ax=axes[0])
            cbar1.set_label('Correlation Coefficient')
            
            # 2. Strong correlations only (|r| > 0.5)
            strong_correlations = []
            for i in range(len(correlation_matrix)):
                for j in range(i+1, len(correlation_matrix.columns)):
                    corr_val = correlation_matrix.iloc[i, j]
                    if abs(corr_val) > 0.5:
                        strong_correlations.append({
                            'var1': correlation_matrix.index[i],
                            'var2': correlation_matrix.columns[j], 
                            'correlation': corr_val
                        })
            
            if strong_correlations:
                strong_df = pd.DataFrame(strong_correlations)
                
                # Create bar plot of strong correlations
                colors = ['red' if x < 0 else 'blue' for x in strong_df['correlation']]
                bars = axes[1].barh(range(len(strong_df)), strong_df['correlation'], color=colors, alpha=0.7)
                
                axes[1].set_title('Strong Correlations (|r| > 0.5)', fontsize=14, fontweight='bold')
                axes[1].set_xlabel('Correlation Coefficient')
                axes[1].set_yticks(range(len(strong_df)))
                
                # Create labels combining both variables
                labels = [f"{row['var1'].replace('_', ' ').title()[:15]}\nvs\n{row['var2'].replace('_', ' ').title()[:15]}" 
                         for _, row in strong_df.iterrows()]
                axes[1].set_yticklabels(labels, fontsize=9)
                
                # Add value labels
                for i, (bar, corr) in enumerate(zip(bars, strong_df['correlation'])):
                    axes[1].text(bar.get_width() + (0.05 if corr > 0 else -0.05), bar.get_y() + bar.get_height()/2,
                               f'{corr:.3f}', ha='left' if corr > 0 else 'right', va='center', fontsize=10, fontweight='bold')
                
                axes[1].axvline(x=0, color='black', linestyle='-', alpha=0.3)
                axes[1].set_xlim(-1, 1)
                axes[1].grid(True, alpha=0.3, axis='x')
            else:
                axes[1].text(0.5, 0.5, 'No strong correlations found\n(|r| > 0.5)', 
                           ha='center', va='center', transform=axes[1].transAxes, fontsize=14)
                axes[1].set_title('Strong Correlations (|r| > 0.5)', fontsize=14, fontweight='bold')
            
            plt.tight_layout()
            
            # Save static version
            static_path = self.output_dir / '07_correlation_matrix.png'
            plt.savefig(static_path, bbox_inches='tight', facecolor='white')
            plt.close()
            
            self.visualizations_created.append({
                'name': 'Correlation Matrix',
                'static_path': str(static_path),
                'interactive_path': None,
                'description': 'Correlation analysis between key calendar and Slack metrics'
            })
            
            print("✅ Correlation matrix created")
            return True
            
        except Exception as e:
            print(f"❌ Error creating correlation matrix: {e}")
            return False
    
    def create_workload_intensity_dashboard(self):
        """Create comprehensive workload intensity dashboard."""
        print("\n⚡ Creating workload intensity dashboard...")
        
        try:
            data = self.conn.execute("""
                SELECT 
                    date,
                    day_of_week,
                    total_collaboration_hours,
                    busy_trap_score,
                    workload_assessment,
                    meeting_overload_indicator,
                    multitasking_indicator,
                    switching_overload_indicator,
                    after_hours_indicator
                FROM v_workload_intensity
                ORDER BY date
            """).fetchdf()
            
            if data.empty:
                print("⚠️ No data available for workload intensity")
                return False
            
            # Convert date column
            data['date'] = pd.to_datetime(data['date'])
            
            # Create figure
            fig, axes = plt.subplots(2, 2, figsize=(16, 12))
            
            # 1. Workload intensity timeline
            colors_by_assessment = {
                'sustainable': 'green',
                'mild_overload': 'yellow', 
                'moderate_overload': 'orange',
                'severe_overload': 'red'
            }
            
            # Plot base timeline
            axes[0,0].plot(data['date'], data['total_collaboration_hours'], 
                          color='gray', alpha=0.5, linewidth=1)
            
            # Color points by assessment
            for assessment, color in colors_by_assessment.items():
                mask = data['workload_assessment'] == assessment
                if mask.any():
                    axes[0,0].scatter(data[mask]['date'], data[mask]['total_collaboration_hours'], 
                                    c=color, alpha=0.8, s=60, label=assessment.replace('_', ' ').title(), zorder=5)
            
            axes[0,0].set_title('Daily Workload Intensity Assessment', fontsize=14, fontweight='bold')
            axes[0,0].set_ylabel('Total Collaboration Hours')
            axes[0,0].legend(bbox_to_anchor=(1.05, 1), loc='upper left')
            axes[0,0].grid(True, alpha=0.3)
            axes[0,0].tick_params(axis='x', rotation=45)
            
            # 2. Busy trap score distribution
            axes[0,1].hist(data['busy_trap_score'], bins=range(6), align='left', rwidth=0.8, 
                          color=self.colors['high'], alpha=0.7, edgecolor='black')
            axes[0,1].set_title('Busy Trap Score Distribution', fontsize=14, fontweight='bold')
            axes[0,1].set_xlabel('Busy Trap Score (0-4)')
            axes[0,1].set_ylabel('Number of Days')
            axes[0,1].set_xticks(range(5))
            
            # Add score interpretation
            score_labels = ['Sustainable', 'Mild Risk', 'Moderate Risk', 'High Risk', 'Severe Risk']
            for i, label in enumerate(score_labels):
                count = (data['busy_trap_score'] == i).sum()
                if count > 0:
                    axes[0,1].text(i, count + 0.5, f'{count}\n({label})', ha='center', va='bottom', fontsize=9)
            
            axes[0,1].grid(True, alpha=0.3, axis='y')
            
            # 3. Busy trap indicators breakdown
            indicators = ['meeting_overload_indicator', 'multitasking_indicator', 
                         'switching_overload_indicator', 'after_hours_indicator']
            indicator_labels = ['Meeting\nOverload', 'Multi-\ntasking', 'Context\nSwitching', 'After Hours\nWork']
            indicator_counts = [data[ind].sum() for ind in indicators]
            
            bars = axes[1,0].bar(range(len(indicators)), indicator_counts, 
                               color=[self.colors['high'], self.colors['moderate'], self.colors['correlation'], self.colors['slack']],
                               alpha=0.7)
            
            axes[1,0].set_title('Busy Trap Indicators Frequency', fontsize=14, fontweight='bold')
            axes[1,0].set_ylabel('Days with Indicator Active')
            axes[1,0].set_xticks(range(len(indicators)))
            axes[1,0].set_xticklabels(indicator_labels)
            
            # Add value labels
            for bar, count in zip(bars, indicator_counts):
                if count > 0:
                    axes[1,0].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                                  f'{count}', ha='center', va='bottom', fontweight='bold')
            
            axes[1,0].grid(True, alpha=0.3, axis='y')
            
            # 4. Workload assessment by day of week
            day_names = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
            
            # Create a pivot table for day of week analysis
            dow_data = data.groupby(['day_of_week', 'workload_assessment']).size().unstack(fill_value=0)
            
            # Reorder columns by severity
            severity_order = ['sustainable', 'mild_overload', 'moderate_overload', 'severe_overload']
            dow_data = dow_data.reindex(columns=[col for col in severity_order if col in dow_data.columns], fill_value=0)
            
            # Create stacked bar chart
            bottom = np.zeros(7)
            for i, assessment in enumerate(dow_data.columns):
                if assessment in colors_by_assessment:
                    color = colors_by_assessment[assessment]
                    bars = axes[1,1].bar(range(7), dow_data[assessment], bottom=bottom, 
                                       label=assessment.replace('_', ' ').title(), 
                                       color=color, alpha=0.7)
                    bottom += dow_data[assessment]
            
            axes[1,1].set_title('Workload Assessment by Day of Week', fontsize=14, fontweight='bold')
            axes[1,1].set_ylabel('Number of Days')
            axes[1,1].set_xlabel('Day of Week')
            axes[1,1].set_xticks(range(7))
            axes[1,1].set_xticklabels([day[:3] for day in day_names])
            axes[1,1].legend(bbox_to_anchor=(1.05, 1), loc='upper left')
            axes[1,1].grid(True, alpha=0.3, axis='y')
            
            plt.tight_layout()
            
            # Save static version
            static_path = self.output_dir / '08_workload_intensity_dashboard.png'
            plt.savefig(static_path, bbox_inches='tight', facecolor='white')
            plt.close()
            
            self.visualizations_created.append({
                'name': 'Workload Intensity Dashboard',
                'static_path': str(static_path),
                'interactive_path': None,
                'description': 'Comprehensive analysis of workload intensity and busy trap indicators'
            })
            
            print("✅ Workload intensity dashboard created")
            return True
            
        except Exception as e:
            print(f"❌ Error creating workload intensity dashboard: {e}")
            return False
    
    def create_efficiency_comparison(self):
        """Create efficiency comparison between calendar and Slack."""
        print("\n⚖️ Creating efficiency comparison visualization...")
        
        try:
            data = self.conn.execute("""
                SELECT 
                    date,
                    calendar_efficiency,
                    slack_efficiency, 
                    overall_efficiency,
                    volume_correlation,
                    daily_meetings,
                    daily_messages,
                    avg_meeting_duration,
                    channels_used
                FROM v_efficiency_correlation
                WHERE daily_meetings > 0 OR daily_messages > 0
                ORDER BY date
            """).fetchdf()
            
            if data.empty:
                print("⚠️ No data available for efficiency comparison")
                return False
            
            # Convert date column
            data['date'] = pd.to_datetime(data['date'])
            
            # Create figure
            fig, axes = plt.subplots(2, 2, figsize=(16, 12))
            
            # 1. Calendar vs Slack efficiency distribution
            efficiency_levels = ['high_calendar_efficiency', 'moderate_calendar_efficiency', 'low_calendar_efficiency']
            slack_efficiency_levels = ['high_slack_efficiency', 'moderate_slack_efficiency', 'low_slack_efficiency']
            
            cal_counts = data['calendar_efficiency'].value_counts().reindex(efficiency_levels, fill_value=0)
            slack_counts = data['slack_efficiency'].value_counts().reindex(slack_efficiency_levels, fill_value=0)
            
            x = np.arange(len(efficiency_levels))
            width = 0.35
            
            bars1 = axes[0,0].bar(x - width/2, cal_counts.values, width, 
                                 label='Calendar Efficiency', color=self.colors['calendar'], alpha=0.7)
            bars2 = axes[0,0].bar(x + width/2, slack_counts.values, width,
                                 label='Slack Efficiency', color=self.colors['slack'], alpha=0.7)
            
            axes[0,0].set_title('Calendar vs Slack Efficiency Distribution', fontsize=14, fontweight='bold')
            axes[0,0].set_ylabel('Number of Days')
            axes[0,0].set_xticks(x)
            axes[0,0].set_xticklabels(['High', 'Moderate', 'Low'])
            axes[0,0].legend()
            axes[0,0].grid(True, alpha=0.3, axis='y')
            
            # Add value labels
            for bars in [bars1, bars2]:
                for bar in bars:
                    if bar.get_height() > 0:
                        axes[0,0].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                                      f'{int(bar.get_height())}', ha='center', va='bottom', fontsize=9)
            
            # 2. Overall efficiency over time
            efficiency_colors = {
                'high_overall_efficiency': 'green',
                'moderate_overall_efficiency': 'orange', 
                'low_overall_efficiency': 'red'
            }
            
            for efficiency, color in efficiency_colors.items():
                mask = data['overall_efficiency'] == efficiency
                if mask.any():
                    axes[0,1].scatter(data[mask]['date'], range(mask.sum()), 
                                    c=color, alpha=0.7, s=60, label=efficiency.replace('_', ' ').title())
            
            axes[0,1].set_title('Overall Efficiency Over Time', fontsize=14, fontweight='bold')
            axes[0,1].set_xlabel('Date')
            axes[0,1].set_ylabel('Efficiency Level')
            axes[0,1].legend(bbox_to_anchor=(1.05, 1), loc='upper left')
            axes[0,1].tick_params(axis='x', rotation=45)
            
            # 3. Volume correlation patterns
            volume_counts = data['volume_correlation'].value_counts()
            volume_colors = {
                'high_volume_both': '#e74c3c',
                'low_volume_both': '#2ecc71',
                'meeting_heavy': '#3498db',
                'slack_heavy': '#f39c12',
                'balanced': '#9b59b6'
            }
            
            colors = [volume_colors.get(pattern, 'gray') for pattern in volume_counts.index]
            
            wedges, texts, autotexts = axes[1,0].pie(volume_counts.values, labels=volume_counts.index,
                                                   colors=colors, autopct='%1.1f%%', startangle=90)
            axes[1,0].set_title('Volume Correlation Patterns', fontsize=14, fontweight='bold')
            
            # 4. Meetings vs messages correlation with efficiency
            # Create scatter plot with efficiency coloring
            efficiency_numeric = data['overall_efficiency'].map({
                'high_overall_efficiency': 3,
                'moderate_overall_efficiency': 2,
                'low_overall_efficiency': 1
            })
            
            scatter = axes[1,1].scatter(data['daily_meetings'], data['daily_messages'], 
                                      c=efficiency_numeric, cmap='RdYlGn', alpha=0.7, s=60)
            
            # Add trend line
            valid_data = data.dropna(subset=['daily_meetings', 'daily_messages'])
            if len(valid_data) >= 3:
                z = np.polyfit(valid_data['daily_meetings'], valid_data['daily_messages'], 1)
                p = np.poly1d(z)
                x_trend = np.linspace(valid_data['daily_meetings'].min(), 
                                    valid_data['daily_meetings'].max(), 100)
                axes[1,1].plot(x_trend, p(x_trend), "r--", alpha=0.8, linewidth=2)
                
                # Calculate correlation
                correlation = valid_data['daily_meetings'].corr(valid_data['daily_messages'])
                title_suffix = f'\n(Correlation: r={correlation:.3f})'
            else:
                title_suffix = ''
            
            axes[1,1].set_title(f'Daily Meetings vs Messages{title_suffix}', fontsize=14, fontweight='bold')
            axes[1,1].set_xlabel('Daily Meetings')
            axes[1,1].set_ylabel('Daily Messages')
            
            # Add colorbar
            cbar = plt.colorbar(scatter, ax=axes[1,1])
            cbar.set_label('Efficiency Level')
            cbar.set_ticks([1, 2, 3])
            cbar.set_ticklabels(['Low', 'Moderate', 'High'])
            
            plt.tight_layout()
            
            # Save static version
            static_path = self.output_dir / '09_efficiency_comparison.png'
            plt.savefig(static_path, bbox_inches='tight', facecolor='white')
            plt.close()
            
            self.visualizations_created.append({
                'name': 'Efficiency Comparison',
                'static_path': str(static_path),
                'interactive_path': None,
                'description': 'Comparative analysis of calendar vs Slack efficiency patterns'
            })
            
            print("✅ Efficiency comparison created")
            return True
            
        except Exception as e:
            print(f"❌ Error creating efficiency comparison: {e}")
            return False
    
    def create_executive_optimization_dashboard(self):
        """Create final executive dashboard with optimization opportunities."""
        print("\n🎯 Creating executive optimization dashboard...")
        
        try:
            # Get summary statistics for the dashboard
            summary_data = self.conn.execute("""
                SELECT 
                    AVG(tct.total_collaboration_hours) as avg_daily_collaboration,
                    AVG(wi.busy_trap_score) as avg_busy_trap_score,
                    AVG(sta.strategic_allocation_pct) as avg_strategic_allocation,
                    AVG(csc.total_context_switches) as avg_context_switches,
                    COUNT(CASE WHEN wi.workload_assessment IN ('moderate_overload', 'severe_overload') THEN 1 END) as overload_days,
                    COUNT(*) as total_days,
                    AVG(tct.after_hours_collaboration_pct) as avg_after_hours_pct
                FROM v_workload_intensity wi
                LEFT JOIN v_context_switching_combined csc ON wi.date = csc.date
                LEFT JOIN v_total_collaboration_time tct ON wi.date = tct.date
                LEFT JOIN v_strategic_time_allocation sta ON wi.date = sta.date
            """).fetchone()
            
            if not summary_data or summary_data[0] is None:
                print("⚠️ No data available for executive dashboard")
                return False
            
            # Create figure with custom layout
            fig = plt.figure(figsize=(20, 14))
            gs = fig.add_gridspec(3, 4, height_ratios=[1, 1, 1.2])
            
            # Key metrics overview (top row)
            ax1 = fig.add_subplot(gs[0, 0])
            ax2 = fig.add_subplot(gs[0, 1])
            ax3 = fig.add_subplot(gs[0, 2])
            ax4 = fig.add_subplot(gs[0, 3])
            
            # Trends (middle row)
            ax5 = fig.add_subplot(gs[1, :2])
            ax6 = fig.add_subplot(gs[1, 2:])
            
            # Optimization opportunities (bottom row)
            ax7 = fig.add_subplot(gs[2, :])
            
            # 1. Average daily collaboration hours
            avg_collab = summary_data[0] or 0
            target_collab = 8  # Target: 8 hours max
            
            colors = ['red' if avg_collab > 10 else 'orange' if avg_collab > 8 else 'green']
            bars = ax1.bar(['Current'], [avg_collab], color=colors, alpha=0.7)
            ax1.axhline(y=target_collab, color='green', linestyle='--', label=f'Target: {target_collab}h')
            ax1.set_title('Avg Daily\nCollaboration', fontsize=12, fontweight='bold')
            ax1.set_ylabel('Hours')
            ax1.text(0, avg_collab + 0.2, f'{avg_collab:.1f}h', ha='center', va='bottom', fontweight='bold')
            ax1.legend(fontsize=9)
            
            # 2. Busy trap score
            avg_busy_trap = summary_data[1] or 0
            
            colors = ['red' if avg_busy_trap >= 3 else 'orange' if avg_busy_trap >= 2 else 'green']
            bars = ax2.bar(['Current'], [avg_busy_trap], color=colors, alpha=0.7)
            ax2.axhline(y=1, color='green', linestyle='--', label='Target: ≤1')
            ax2.set_title('Avg Busy Trap\nScore', fontsize=12, fontweight='bold')
            ax2.set_ylabel('Score (0-4)')
            ax2.text(0, avg_busy_trap + 0.1, f'{avg_busy_trap:.1f}', ha='center', va='bottom', fontweight='bold')
            ax2.set_ylim(0, 4)
            ax2.legend(fontsize=9)
            
            # 3. Strategic allocation percentage
            avg_strategic = summary_data[2] or 0
            target_strategic = 60
            
            colors = ['red' if avg_strategic < 40 else 'orange' if avg_strategic < 60 else 'green']
            bars = ax3.bar(['Current'], [avg_strategic], color=colors, alpha=0.7)
            ax3.axhline(y=target_strategic, color='green', linestyle='--', label=f'Target: {target_strategic}%')
            ax3.set_title('Avg Strategic\nAllocation', fontsize=12, fontweight='bold')
            ax3.set_ylabel('Percentage')
            ax3.text(0, avg_strategic + 1, f'{avg_strategic:.1f}%', ha='center', va='bottom', fontweight='bold')
            ax3.legend(fontsize=9)
            
            # 4. Overload frequency
            overload_days = summary_data[4] or 0
            total_days = summary_data[5] or 1
            overload_pct = (overload_days / total_days) * 100
            
            colors = ['red' if overload_pct > 50 else 'orange' if overload_pct > 25 else 'green']
            bars = ax4.bar(['Current'], [overload_pct], color=colors, alpha=0.7)
            ax4.axhline(y=20, color='green', linestyle='--', label='Target: <20%')
            ax4.set_title('Overload Days\nFrequency', fontsize=12, fontweight='bold')
            ax4.set_ylabel('Percentage')
            ax4.text(0, overload_pct + 1, f'{overload_pct:.1f}%', ha='center', va='bottom', fontweight='bold')
            ax4.legend(fontsize=9)
            
            # 5. Collaboration trends
            trend_data = self.conn.execute("""
                SELECT 
                    date,
                    total_collaboration_hours,
                    busy_trap_score,
                    strategic_allocation_pct
                FROM v_workload_intensity wi
                LEFT JOIN v_total_collaboration_time tct ON wi.date = tct.date
                LEFT JOIN v_strategic_time_allocation sta ON wi.date = sta.date
                WHERE total_collaboration_hours > 0
                ORDER BY date
                LIMIT 30  -- Last 30 days
            """).fetchdf()
            
            if not trend_data.empty:
                trend_data['date'] = pd.to_datetime(trend_data['date'])
                
                ax5_twin = ax5.twinx()
                
                line1 = ax5.plot(trend_data['date'], trend_data['total_collaboration_hours'], 
                               color=self.colors['combined'], linewidth=2, label='Collaboration Hours')
                line2 = ax5_twin.plot(trend_data['date'], trend_data['busy_trap_score'], 
                                    color=self.colors['high'], linewidth=2, linestyle='--', label='Busy Trap Score')
                
                ax5.set_title('Recent Trends: Collaboration & Busy Trap Score', fontsize=14, fontweight='bold')
                ax5.set_ylabel('Collaboration Hours', color=self.colors['combined'])
                ax5_twin.set_ylabel('Busy Trap Score', color=self.colors['high'])
                ax5.tick_params(axis='x', rotation=45)
                
                # Combine legends
                lines1, labels1 = ax5.get_legend_handles_labels()
                lines2, labels2 = ax5_twin.get_legend_handles_labels()
                ax5.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
            
            # 6. Context switching and efficiency
            context_data = self.conn.execute("""
                SELECT 
                    date,
                    total_context_switches,
                    CASE 
                        WHEN overall_efficiency = 'high_overall_efficiency' THEN 3
                        WHEN overall_efficiency = 'moderate_overall_efficiency' THEN 2
                        ELSE 1
                    END as efficiency_score
                FROM v_context_switching_combined csc
                LEFT JOIN v_efficiency_correlation ec ON csc.date = ec.date
                WHERE total_context_switches > 0
                ORDER BY date
                LIMIT 30
            """).fetchdf()
            
            if not context_data.empty:
                context_data['date'] = pd.to_datetime(context_data['date'])
                
                ax6_twin = ax6.twinx()
                
                bars = ax6.bar(context_data['date'], context_data['total_context_switches'], 
                             alpha=0.7, color=self.colors['correlation'], label='Context Switches')
                line = ax6_twin.plot(context_data['date'], context_data['efficiency_score'],
                                   color=self.colors['moderate'], linewidth=3, marker='o', 
                                   markersize=4, label='Efficiency Score')
                
                ax6.set_title('Context Switching vs Efficiency', fontsize=14, fontweight='bold')
                ax6.set_ylabel('Context Switches', color=self.colors['correlation'])
                ax6_twin.set_ylabel('Efficiency Score', color=self.colors['moderate'])
                ax6.tick_params(axis='x', rotation=45)
                ax6_twin.set_ylim(0.5, 3.5)
                ax6_twin.set_yticks([1, 2, 3])
                ax6_twin.set_yticklabels(['Low', 'Moderate', 'High'])
                
                # Combine legends
                lines1, labels1 = ax6.get_legend_handles_labels()
                lines2, labels2 = ax6_twin.get_legend_handles_labels()
                ax6.legend(lines1 + lines2, labels1 + labels2, loc='upper right')
            
            # 7. Optimization opportunities matrix
            ax7.text(0.02, 0.95, 'KEY OPTIMIZATION OPPORTUNITIES', transform=ax7.transAxes,
                    fontsize=16, fontweight='bold', va='top')
            
            opportunities = []
            
            # Based on the metrics, identify opportunities
            if avg_collab > 8:
                opportunities.append(f"• REDUCE total collaboration time from {avg_collab:.1f}h to <8h/day")
            
            if avg_busy_trap >= 2:
                opportunities.append(f"• LOWER busy trap score from {avg_busy_trap:.1f} to <2.0")
            
            if avg_strategic < 60:
                opportunities.append(f"• INCREASE strategic allocation from {avg_strategic:.1f}% to >60%")
            
            if summary_data[3] and summary_data[3] > 6:
                opportunities.append(f"• REDUCE context switching from {summary_data[3]:.1f} to <6 switches/day")
            
            if summary_data[6] and summary_data[6] > 20:
                opportunities.append(f"• LIMIT after-hours work from {summary_data[6]:.1f}% to <20%")
            
            # General optimization recommendations
            opportunities.extend([
                "• IMPLEMENT 25/50-minute meeting defaults instead of 30/60",
                "• BATCH similar communication into focused time blocks", 
                "• DELEGATE more meeting ownership to reduce calendar load",
                "• ESTABLISH 'deep work' blocks with minimal Slack interruptions",
                "• CREATE communication boundaries for after-hours messaging"
            ])
            
            # Display opportunities
            y_pos = 0.85
            for opp in opportunities[:8]:  # Show top 8 opportunities
                color = 'red' if opp.startswith('• REDUCE') or opp.startswith('• LOWER') else 'blue'
                ax7.text(0.02, y_pos, opp, transform=ax7.transAxes, fontsize=12, 
                        va='top', color=color, fontweight='bold' if opp.startswith('•') else 'normal')
                y_pos -= 0.1
            
            ax7.set_xlim(0, 1)
            ax7.set_ylim(0, 1)
            ax7.axis('off')
            
            # Add overall title
            fig.suptitle('Executive Productivity Dashboard: Cross-Platform Analysis\nCalendar + Slack Integration', 
                        fontsize=18, fontweight='bold', y=0.98)
            
            plt.tight_layout()
            plt.subplots_adjust(top=0.93)
            
            # Save static version
            static_path = self.output_dir / '10_executive_optimization_dashboard.png'
            plt.savefig(static_path, bbox_inches='tight', facecolor='white', dpi=300)
            plt.close()
            
            self.visualizations_created.append({
                'name': 'Executive Optimization Dashboard',
                'static_path': str(static_path),
                'interactive_path': None,
                'description': 'Comprehensive executive dashboard with key metrics and optimization opportunities'
            })
            
            print("✅ Executive optimization dashboard created")
            return True
            
        except Exception as e:
            print(f"❌ Error creating executive dashboard: {e}")
            return False
    
    def create_visualizations_summary(self):
        """Create summary of all visualizations created."""
        print("\n📋 Creating visualizations summary...")
        
        summary = {
            "generation_timestamp": datetime.now().isoformat(),
            "total_visualizations": len(self.visualizations_created),
            "output_directory": str(self.output_dir),
            "visualizations": self.visualizations_created,
            "visualization_categories": {
                "temporal_correlations": 3,
                "behavioral_patterns": 3,
                "efficiency_analysis": 2,
                "executive_insights": 2
            },
            "files_created": [viz['static_path'] for viz in self.visualizations_created]
        }
        
        # Save summary
        summary_file = self.output_dir / 'visualization_summary.json'
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        
        print(f"✅ Visualizations summary saved to {summary_file}")
        return summary
    
    def run_generation(self):
        """Run the complete visualization generation process."""
        print("🚀 Starting Integrated Visualizations Generation...")
        
        visualizations_functions = [
            self.create_combined_workload_heatmap,
            self.create_total_engagement_timeline,
            self.create_pre_post_meeting_patterns,
            self.create_context_switching_analysis,
            self.create_strategic_operational_allocation,
            self.create_collaboration_network_unified,
            self.create_correlation_matrix,
            self.create_workload_intensity_dashboard,
            self.create_efficiency_comparison,
            self.create_executive_optimization_dashboard
        ]
        
        successful_visualizations = 0
        
        for viz_func in visualizations_functions:
            try:
                if viz_func():
                    successful_visualizations += 1
            except Exception as e:
                print(f"❌ Error in {viz_func.__name__}: {e}")
        
        # Create summary
        summary = self.create_visualizations_summary()
        
        print(f"\n✅ Integrated Visualizations Generation Completed!")
        print(f"📊 Successful visualizations: {successful_visualizations}/{len(visualizations_functions)}")
        print(f"📁 Output directory: {self.output_dir}")
        print(f"🎯 Target achieved: {successful_visualizations >= 10}")
        
        return successful_visualizations >= 10

if __name__ == "__main__":
    generator = IntegratedVisualizationGenerator()
    generator.run_generation()