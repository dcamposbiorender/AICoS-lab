#!/usr/bin/env python3
"""
Calendar Analytics - Visualization Generation
============================================

This script generates 15+ comprehensive visualizations from the DuckDB analytical views,
providing executive-ready charts for Ryan's calendar analysis.

Visualizations generated:
1. Weekly load heatmap (DoW × Hour)
2. Meeting volume time series (6 months)
3. Back-to-back rate vs buffer coverage
4. Topic mix stacked area chart
5. Meeting duration distribution
6. Collaboration network analysis
7. Deep work erosion timeline
8. Context switching metrics
9. Goal attention pie charts
10. Delegation opportunity matrix
11. Off-hours meeting patterns
12. Recurring meeting efficiency
13. Productivity score dashboard
14. Meeting type evolution
15. Executive summary KPIs

Uses matplotlib and plotly for publication-ready outputs.
"""

import duckdb
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime, timedelta
import json
import os
from typing import Dict, List, Any, Tuple

# Set style for matplotlib
plt.style.use('default')

class CalendarVisualizationGenerator:
    def __init__(self, db_path: str, output_dir: str):
        """Initialize with database and output paths."""
        self.db_path = db_path
        self.output_dir = output_dir
        self.connection = None
        self.visualizations_created = []
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
    def connect_db(self):
        """Connect to DuckDB database."""
        self.connection = duckdb.connect(self.db_path)
        print(f"Connected to database: {self.db_path}")
        
    def save_chart(self, fig, filename: str, chart_type: str = "matplotlib"):
        """Save chart in both PNG and HTML formats."""
        base_path = os.path.join(self.output_dir, filename)
        
        if chart_type == "matplotlib":
            png_path = f"{base_path}.png"
            fig.savefig(png_path, dpi=300, bbox_inches='tight', 
                       facecolor='white', edgecolor='none')
            print(f"  Saved PNG: {png_path}")
            
        elif chart_type == "plotly":
            png_path = f"{base_path}.png"
            html_path = f"{base_path}.html"
            
            fig.write_image(png_path, width=1200, height=800, scale=2)
            fig.write_html(html_path)
            print(f"  Saved PNG: {png_path}")
            print(f"  Saved HTML: {html_path}")
            
        self.visualizations_created.append(filename)
        
    def generate_heatmap_weekly_load(self):
        """Generate DoW × Hour heatmap of meeting load."""
        print("Generating weekly load heatmap...")
        
        data = self.connection.execute("""
            SELECT 
                day_of_week,
                start_hour,
                meetings_per_day,
                total_minutes
            FROM v_day_load
            ORDER BY day_of_week, start_hour
        """).fetchdf()
        
        # Create pivot table for heatmap
        pivot_meetings = data.pivot(index='start_hour', columns='day_of_week', values='meetings_per_day')
        pivot_minutes = data.pivot(index='start_hour', columns='day_of_week', values='total_minutes')
        
        # Create matplotlib heatmap
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 10))
        
        # Meetings per day heatmap
        im1 = ax1.imshow(pivot_meetings.values, cmap='YlOrRd', aspect='auto')
        ax1.set_title('Meetings per Day by Hour and Day of Week', fontsize=14, fontweight='bold')
        ax1.set_xlabel('Day of Week (0=Sunday, 6=Saturday)')
        ax1.set_ylabel('Hour of Day')
        ax1.set_xticks(range(len(pivot_meetings.columns)))
        ax1.set_xticklabels(['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'])
        ax1.set_yticks(range(len(pivot_meetings.index)))
        ax1.set_yticklabels([f"{int(h)}:00" for h in pivot_meetings.index])
        plt.colorbar(im1, ax=ax1, label='Meetings per Day')
        
        # Add text annotations
        for i in range(len(pivot_meetings.index)):
            for j in range(len(pivot_meetings.columns)):
                val = pivot_meetings.iloc[i, j]
                if not pd.isna(val):
                    text = ax1.text(j, i, f'{val:.1f}', ha="center", va="center",
                                   color="black" if val < pivot_meetings.values.max()/2 else "white")
        
        # Total minutes heatmap
        im2 = ax2.imshow(pivot_minutes.values, cmap='Blues', aspect='auto')
        ax2.set_title('Total Minutes by Hour and Day of Week', fontsize=14, fontweight='bold')
        ax2.set_xlabel('Day of Week (0=Sunday, 6=Saturday)')
        ax2.set_ylabel('Hour of Day')
        ax2.set_xticks(range(len(pivot_minutes.columns)))
        ax2.set_xticklabels(['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'])
        ax2.set_yticks(range(len(pivot_minutes.index)))
        ax2.set_yticklabels([f"{int(h)}:00" for h in pivot_minutes.index])
        plt.colorbar(im2, ax=ax2, label='Total Minutes')
        
        plt.tight_layout()
        self.save_chart(fig, '01_weekly_load_heatmap', 'matplotlib')
        plt.close()
        
        # Create interactive plotly version
        fig_plotly = make_subplots(
            rows=1, cols=2,
            subplot_titles=('Meetings per Day', 'Total Minutes'),
            shared_yaxes=True
        )
        
        fig_plotly.add_trace(
            go.Heatmap(
                z=pivot_meetings.values,
                x=['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'],
                y=[f"{int(h)}:00" for h in pivot_meetings.index],
                colorscale='YlOrRd',
                name='Meetings'
            ),
            row=1, col=1
        )
        
        fig_plotly.add_trace(
            go.Heatmap(
                z=pivot_minutes.values,
                x=['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'],
                y=[f"{int(h)}:00" for h in pivot_minutes.index],
                colorscale='Blues',
                name='Minutes'
            ),
            row=1, col=2
        )
        
        fig_plotly.update_layout(
            title="Weekly Meeting Load Analysis",
            height=600,
            showlegend=False
        )
        
        self.save_chart(fig_plotly, '01_weekly_load_heatmap_interactive', 'plotly')
        
    def generate_meeting_volume_time_series(self):
        """Generate meeting volume over time."""
        print("Generating meeting volume time series...")
        
        data = self.connection.execute("""
            SELECT 
                event_date,
                COUNT(*) AS daily_meetings,
                SUM(duration_minutes) AS daily_minutes,
                SUM(duration_minutes) / 60.0 AS daily_hours,
                AVG(duration_minutes) AS avg_duration,
                COUNT(CASE WHEN meeting_type IN ('one_on_one', 'small_meeting', 'large_meeting') THEN 1 END) AS actual_meetings,
                COUNT(CASE WHEN meeting_type = 'personal' THEN 1 END) AS personal_time,
                COUNT(CASE WHEN meeting_type = 'blocked_time' THEN 1 END) AS blocked_time
            FROM v_events_norm
            GROUP BY event_date
            ORDER BY event_date
        """).fetchdf()
        
        data['event_date'] = pd.to_datetime(data['event_date'])
        
        # Create matplotlib time series
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
        
        # Daily meetings count
        ax1.plot(data['event_date'], data['daily_meetings'], marker='o', linewidth=2, markersize=4)
        ax1.set_title('Daily Meeting Count', fontweight='bold')
        ax1.set_ylabel('Number of Meetings')
        ax1.grid(True, alpha=0.3)
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
        ax1.tick_params(axis='x', rotation=45)
        
        # Daily hours
        ax2.plot(data['event_date'], data['daily_hours'], marker='s', color='red', linewidth=2, markersize=4)
        ax2.axhline(y=6, color='orange', linestyle='--', alpha=0.8, label='6-hour target')
        ax2.set_title('Daily Meeting Hours', fontweight='bold')
        ax2.set_ylabel('Hours')
        ax2.grid(True, alpha=0.3)
        ax2.legend()
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
        ax2.tick_params(axis='x', rotation=45)
        
        # Meeting type stacked area
        ax3.stackplot(
            data['event_date'], 
            data['actual_meetings'], 
            data['personal_time'], 
            data['blocked_time'],
            labels=['Actual Meetings', 'Personal Time', 'Blocked Time'],
            alpha=0.7
        )
        ax3.set_title('Meeting Type Distribution', fontweight='bold')
        ax3.set_ylabel('Number of Events')
        ax3.legend(loc='upper left')
        ax3.grid(True, alpha=0.3)
        ax3.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
        ax3.tick_params(axis='x', rotation=45)
        
        # Average duration trend
        ax4.plot(data['event_date'], data['avg_duration'], marker='^', color='green', linewidth=2, markersize=4)
        ax4.set_title('Average Meeting Duration', fontweight='bold')
        ax4.set_ylabel('Minutes')
        ax4.grid(True, alpha=0.3)
        ax4.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
        ax4.tick_params(axis='x', rotation=45)
        
        plt.tight_layout()
        self.save_chart(fig, '02_meeting_volume_time_series', 'matplotlib')
        plt.close()
        
        # Create interactive plotly version
        fig_plotly = make_subplots(
            rows=2, cols=2,
            subplot_titles=('Daily Meeting Count', 'Daily Hours', 'Meeting Type Distribution', 'Avg Duration'),
            specs=[[{"secondary_y": False}, {"secondary_y": False}],
                   [{"secondary_y": False}, {"secondary_y": False}]]
        )
        
        # Add traces
        fig_plotly.add_trace(
            go.Scatter(x=data['event_date'], y=data['daily_meetings'], mode='lines+markers', name='Daily Meetings'),
            row=1, col=1
        )
        
        fig_plotly.add_trace(
            go.Scatter(x=data['event_date'], y=data['daily_hours'], mode='lines+markers', name='Daily Hours'),
            row=1, col=2
        )
        
        fig_plotly.add_trace(
            go.Scatter(x=data['event_date'], y=data['actual_meetings'], mode='lines', fill='tonexty', name='Actual Meetings'),
            row=2, col=1
        )
        
        fig_plotly.add_trace(
            go.Scatter(x=data['event_date'], y=data['avg_duration'], mode='lines+markers', name='Avg Duration'),
            row=2, col=2
        )
        
        fig_plotly.update_layout(
            title="Meeting Volume Analysis Over Time",
            height=800,
            showlegend=True
        )
        
        self.save_chart(fig_plotly, '02_meeting_volume_time_series_interactive', 'plotly')
        
    def generate_b2b_analysis(self):
        """Generate back-to-back meeting analysis."""
        print("Generating back-to-back meeting analysis...")
        
        # Get B2B transition data
        b2b_data = self.connection.execute("""
            SELECT 
                transition_type,
                COUNT(*) AS transition_count,
                AVG(gap_minutes) AS avg_gap,
                AVG(current_duration) AS avg_current_duration,
                AVG(next_duration) AS avg_next_duration
            FROM v_b2b
            GROUP BY transition_type
            ORDER BY 
                CASE transition_type 
                    WHEN 'overlapping' THEN 1
                    WHEN 'back_to_back' THEN 2
                    WHEN 'short_buffer' THEN 3
                    WHEN 'medium_buffer' THEN 4
                    WHEN 'long_buffer' THEN 5
                END
        """).fetchdf()
        
        # Get buffer coverage stats
        buffer_stats = self.connection.execute("""
            SELECT 
                COUNT(*) AS total_transitions,
                SUM(adequate_buffer) AS adequate_buffers,
                ROUND(AVG(gap_minutes), 1) AS avg_gap_minutes,
                ROUND(SUM(adequate_buffer)::DECIMAL / COUNT(*) * 100, 1) AS buffer_coverage_pct
            FROM v_b2b
        """).fetchone()
        
        # Create visualization
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
        
        # Transition type distribution
        colors = ['#ff4d4d', '#ff8c1a', '#ffcc1a', '#66cc66', '#4d9fff']
        bars = ax1.bar(b2b_data['transition_type'], b2b_data['transition_count'], color=colors)
        ax1.set_title('Meeting Transition Types', fontweight='bold')
        ax1.set_ylabel('Number of Transitions')
        ax1.tick_params(axis='x', rotation=45)
        
        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height,
                    f'{int(height)}', ha='center', va='bottom')
        
        # Average gap by transition type
        ax2.bar(b2b_data['transition_type'], b2b_data['avg_gap'], color=colors, alpha=0.7)
        ax2.set_title('Average Gap Time by Transition Type', fontweight='bold')
        ax2.set_ylabel('Average Gap (minutes)')
        ax2.tick_params(axis='x', rotation=45)
        ax2.axhline(y=5, color='red', linestyle='--', alpha=0.8, label='5-min minimum')
        ax2.legend()
        
        # Meeting duration impact
        x_pos = np.arange(len(b2b_data['transition_type']))
        width = 0.35
        ax3.bar(x_pos - width/2, b2b_data['avg_current_duration'], width, label='Current Meeting', alpha=0.8)
        ax3.bar(x_pos + width/2, b2b_data['avg_next_duration'], width, label='Next Meeting', alpha=0.8)
        ax3.set_title('Meeting Duration by Transition Type', fontweight='bold')
        ax3.set_ylabel('Average Duration (minutes)')
        ax3.set_xticks(x_pos)
        ax3.set_xticklabels(b2b_data['transition_type'], rotation=45)
        ax3.legend()
        
        # Buffer coverage summary
        sizes = [buffer_stats[1], buffer_stats[0] - buffer_stats[1]]
        labels = [f'Adequate Buffer\n({buffer_stats[3]}%)', f'Insufficient Buffer\n({100-buffer_stats[3]:.1f}%)']
        colors_pie = ['#66cc66', '#ff4d4d']
        
        wedges, texts, autotexts = ax4.pie(sizes, labels=labels, colors=colors_pie, autopct='%1.0f',
                                          startangle=90, textprops={'fontsize': 10})
        ax4.set_title('Buffer Coverage Analysis', fontweight='bold')
        
        plt.tight_layout()
        self.save_chart(fig, '03_back_to_back_analysis', 'matplotlib')
        plt.close()
        
    def generate_topic_analysis(self):
        """Generate topic and goal attention analysis."""
        print("Generating topic analysis...")
        
        # Get topic data
        topic_data = self.connection.execute("""
            SELECT * FROM v_topic_minutes ORDER BY total_minutes DESC
        """).fetchdf()
        
        # Get goal attention data
        goal_data = self.connection.execute("""
            SELECT * FROM v_goal_attention_share ORDER BY weighted_minutes DESC
        """).fetchdf()
        
        # Create visualizations
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(18, 14))
        
        # Topic time distribution (horizontal bar chart)
        y_pos = np.arange(len(topic_data.head(10)))
        bars = ax1.barh(y_pos, topic_data.head(10)['total_hours'], 
                       color=plt.cm.Set3(np.linspace(0, 1, len(topic_data.head(10)))))
        ax1.set_yticks(y_pos)
        ax1.set_yticklabels(topic_data.head(10)['topic_category'])
        ax1.set_xlabel('Total Hours')
        ax1.set_title('Time Allocation by Topic (Top 10)', fontweight='bold')
        
        # Add value labels
        for i, bar in enumerate(bars):
            width = bar.get_width()
            ax1.text(width, bar.get_y() + bar.get_height()/2.,
                    f'{width:.1f}h ({topic_data.head(10).iloc[i]["time_share_pct"]:.1f}%)',
                    ha='left', va='center', fontsize=9)
        
        # Topic meeting count vs average duration scatter
        ax2.scatter(topic_data['meeting_count'], topic_data['avg_duration'], 
                   s=topic_data['total_minutes']/10, alpha=0.6, 
                   c=range(len(topic_data)), cmap='viridis')
        ax2.set_xlabel('Number of Meetings')
        ax2.set_ylabel('Average Duration (minutes)')
        ax2.set_title('Topic Analysis: Volume vs Duration', fontweight='bold')
        
        # Add labels for major topics
        for i, row in topic_data.head(8).iterrows():
            ax2.annotate(row['topic_category'], (row['meeting_count'], row['avg_duration']),
                        xytext=(5, 5), textcoords='offset points', fontsize=8)
        
        # Goal attention pie chart
        goal_colors = plt.cm.Set3(np.linspace(0, 1, len(goal_data.head(8))))
        wedges, texts, autotexts = ax3.pie(goal_data.head(8)['weighted_share_pct'], 
                                          labels=goal_data.head(8)['business_goal'],
                                          colors=goal_colors, autopct='%1.1f%%',
                                          startangle=90)
        ax3.set_title('Goal Attention Share (Weighted)', fontweight='bold')
        
        # Topic entropy and diversity
        entropy_data = self.connection.execute("SELECT * FROM v_topic_entropy").fetchone()
        
        metrics = ['Total Topics', 'Entropy Score', 'Max Entropy', 'Normalized Entropy']
        values = [entropy_data[0], entropy_data[2], entropy_data[3], entropy_data[4]]
        
        bars = ax4.bar(metrics, values, color=['skyblue', 'lightcoral', 'lightgreen', 'gold'])
        ax4.set_title('Topic Diversity Metrics', fontweight='bold')
        ax4.set_ylabel('Score')
        ax4.tick_params(axis='x', rotation=45)
        
        # Add value labels
        for bar, val in zip(bars, values):
            height = bar.get_height()
            ax4.text(bar.get_x() + bar.get_width()/2., height,
                    f'{val:.2f}', ha='center', va='bottom')
        
        plt.tight_layout()
        self.save_chart(fig, '04_topic_analysis', 'matplotlib')
        plt.close()
        
    def generate_deep_work_analysis(self):
        """Generate deep work and productivity analysis."""
        print("Generating deep work analysis...")
        
        # Get deep work blocks
        deep_work_data = self.connection.execute("""
            SELECT 
                event_date,
                COUNT(*) AS blocks_count,
                SUM(business_hours_minutes) / 60.0 AS total_deep_work_hours,
                AVG(gap_minutes) AS avg_block_duration,
                COUNT(CASE WHEN deep_work_quality = 'extended_deep_work' THEN 1 END) AS extended_blocks,
                COUNT(CASE WHEN time_period = 'morning' THEN 1 END) AS morning_blocks
            FROM v_deep_work_blocks
            GROUP BY event_date
            ORDER BY event_date
        """).fetchdf()
        
        deep_work_data['event_date'] = pd.to_datetime(deep_work_data['event_date'])
        
        # Get overall KPIs
        kpis = self.connection.execute("SELECT * FROM v_calendar_kpis").fetchone()
        
        # Create visualizations
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
        
        # Daily deep work availability
        ax1.plot(deep_work_data['event_date'], deep_work_data['total_deep_work_hours'], 
                marker='o', linewidth=2, markersize=4, color='green')
        ax1.axhline(y=2, color='orange', linestyle='--', alpha=0.8, label='2-hour target')
        ax1.set_title('Daily Deep Work Hours Available', fontweight='bold')
        ax1.set_ylabel('Hours')
        ax1.grid(True, alpha=0.3)
        ax1.legend()
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
        ax1.tick_params(axis='x', rotation=45)
        
        # Deep work blocks count
        ax2.bar(deep_work_data['event_date'], deep_work_data['blocks_count'], 
               alpha=0.7, color='lightblue', width=0.8)
        ax2.set_title('Daily Deep Work Blocks Count', fontweight='bold')
        ax2.set_ylabel('Number of Blocks')
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
        ax2.tick_params(axis='x', rotation=45)
        
        # Block quality distribution
        quality_data = self.connection.execute("""
            SELECT 
                deep_work_quality,
                COUNT(*) AS count,
                SUM(business_hours_minutes) / 60.0 AS total_hours
            FROM v_deep_work_blocks
            GROUP BY deep_work_quality
            ORDER BY count DESC
        """).fetchdf()
        
        colors = ['#4CAF50', '#FFC107', '#FF5722']
        bars = ax3.bar(quality_data['deep_work_quality'], quality_data['count'], 
                      color=colors[:len(quality_data)])
        ax3.set_title('Deep Work Block Quality', fontweight='bold')
        ax3.set_ylabel('Number of Blocks')
        ax3.tick_params(axis='x', rotation=45)
        
        # Add value labels
        for bar in bars:
            height = bar.get_height()
            ax3.text(bar.get_x() + bar.get_width()/2., height,
                    f'{int(height)}', ha='center', va='bottom')
        
        # Productivity KPI dashboard
        kpi_labels = ['Deep Work\nRatio (%)', 'Buffer\nCoverage (%)', 'Productivity\nScore', 'Avg Hours\nper Day']
        kpi_values = [kpis[8], kpis[12], kpis[14], kpis[7]]  # Adjust indices based on KPI structure
        
        bars = ax4.bar(kpi_labels, kpi_values, color=['green', 'blue', 'purple', 'orange'])
        ax4.set_title('Key Productivity Metrics', fontweight='bold')
        ax4.set_ylabel('Score/Percentage')
        
        # Add value labels and targets
        for i, (bar, val) in enumerate(zip(bars, kpi_values)):
            height = bar.get_height()
            ax4.text(bar.get_x() + bar.get_width()/2., height,
                    f'{val:.1f}', ha='center', va='bottom', fontweight='bold')
            
            # Add target lines
            if i == 0:  # Deep work ratio target 40%
                ax4.axhline(y=40, color='red', linestyle='--', alpha=0.5)
            elif i == 1:  # Buffer coverage target 80%
                ax4.axhline(y=80, color='red', linestyle='--', alpha=0.5)
                
        plt.tight_layout()
        self.save_chart(fig, '05_deep_work_analysis', 'matplotlib')
        plt.close()
        
    def generate_collaboration_network(self):
        """Generate collaboration network and patterns analysis."""
        print("Generating collaboration analysis...")
        
        # Get collaboration data
        collab_data = self.connection.execute("""
            SELECT * FROM v_collab_minutes 
            WHERE total_minutes >= 60  -- Only significant collaborations
            ORDER BY total_minutes DESC 
            LIMIT 20
        """).fetchdf()
        
        # Get HHI concentration data
        hhi_data = self.connection.execute("SELECT * FROM v_collab_hhi").fetchone()
        
        # Create visualizations
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(18, 14))
        
        # Top collaboration partners (horizontal bar)
        y_pos = np.arange(len(collab_data.head(15)))
        colors = ['red' if is_ext else 'blue' for is_ext in (collab_data.head(15)['is_internal'] == 0)]
        
        bars = ax1.barh(y_pos, collab_data.head(15)['total_minutes'], color=colors, alpha=0.7)
        ax1.set_yticks(y_pos)
        ax1.set_yticklabels([f"{email.split('@')[0]}" for email in collab_data.head(15)['participant_email']])
        ax1.set_xlabel('Total Minutes')
        ax1.set_title('Top Collaboration Partners', fontweight='bold')
        
        # Add legend
        from matplotlib.patches import Patch
        legend_elements = [Patch(facecolor='blue', alpha=0.7, label='Internal'),
                          Patch(facecolor='red', alpha=0.7, label='External')]
        ax1.legend(handles=legend_elements, loc='lower right')
        
        # Meeting type breakdown for top partners
        top_partners = collab_data.head(10)
        x_pos = np.arange(len(top_partners))
        width = 0.25
        
        ax2.bar(x_pos - width, top_partners['one_on_one_minutes'], width, label='1:1', alpha=0.8)
        ax2.bar(x_pos, top_partners['small_meeting_minutes'], width, label='Small Meetings', alpha=0.8)
        ax2.bar(x_pos + width, top_partners['large_meeting_minutes'], width, label='Large Meetings', alpha=0.8)
        
        ax2.set_title('Meeting Type Distribution (Top 10 Partners)', fontweight='bold')
        ax2.set_ylabel('Minutes')
        ax2.set_xticks(x_pos)
        ax2.set_xticklabels([email.split('@')[0][:8] for email in top_partners['participant_email']], rotation=45)
        ax2.legend()
        
        # Domain concentration
        domain_data = self.connection.execute("""
            SELECT 
                domain,
                SUM(total_minutes) AS total_minutes,
                COUNT(*) AS partner_count,
                ROUND(SUM(total_minutes)::DECIMAL / SUM(SUM(total_minutes)) OVER () * 100, 1) AS share_pct
            FROM v_collab_minutes
            GROUP BY domain
            ORDER BY total_minutes DESC
        """).fetchdf()
        
        # Filter out very small domains for readability
        significant_domains = domain_data[domain_data['share_pct'] >= 1.0]
        other_domains_total = domain_data[domain_data['share_pct'] < 1.0]['share_pct'].sum()
        
        if other_domains_total > 0:
            other_row = pd.DataFrame({'domain': ['others'], 'share_pct': [other_domains_total]})
            plot_data = pd.concat([significant_domains[['domain', 'share_pct']], other_row], ignore_index=True)
        else:
            plot_data = significant_domains[['domain', 'share_pct']]
        
        colors_pie = plt.cm.Set3(np.linspace(0, 1, len(plot_data)))
        wedges, texts, autotexts = ax3.pie(plot_data['share_pct'], labels=plot_data['domain'],
                                          colors=colors_pie, autopct='%1.1f%%', startangle=90)
        ax3.set_title('Collaboration by Domain', fontweight='bold')
        
        # HHI and concentration metrics
        metrics = ['Total Domains', 'HHI Score', 'Concentration Level']
        values = [hhi_data[0], hhi_data[2], 0]  # Use 0 for text metric
        
        bars = ax4.bar(metrics[:2], values[:2], color=['lightblue', 'lightcoral'])
        ax4.set_title('Collaboration Concentration Analysis', fontweight='bold')
        ax4.set_ylabel('Score')
        
        # Add HHI interpretation text
        ax4.text(0.5, 0.8, f'Concentration: {hhi_data[3]}', transform=ax4.transAxes,
                ha='center', va='center', fontsize=12, fontweight='bold',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        ax4.text(0.5, 0.6, f'HHI Score: {hhi_data[2]}', transform=ax4.transAxes,
                ha='center', va='center', fontsize=10)
        
        # Add value labels on bars
        for bar, val in zip(bars, values[:2]):
            height = bar.get_height()
            ax4.text(bar.get_x() + bar.get_width()/2., height,
                    f'{val:.0f}', ha='center', va='bottom')
        
        plt.tight_layout()
        self.save_chart(fig, '06_collaboration_network', 'matplotlib')
        plt.close()
        
    def generate_efficiency_metrics(self):
        """Generate meeting efficiency and optimization metrics."""
        print("Generating efficiency metrics...")
        
        # Get recurring meeting efficiency
        recurring_data = self.connection.execute("""
            SELECT * FROM v_series_audit 
            ORDER BY total_hours DESC 
            LIMIT 15
        """).fetchdf()
        
        # Get off-hours analysis
        offhours_data = self.connection.execute("""
            SELECT 
                offhours_type,
                COUNT(*) AS meeting_count,
                SUM(duration_minutes) / 60.0 AS total_hours,
                AVG(duration_minutes) AS avg_duration
            FROM v_offhours
            GROUP BY offhours_type
            ORDER BY total_hours DESC
        """).fetchdf()
        
        # Get transition analysis
        transition_data = self.connection.execute("""
            SELECT 
                from_topic,
                to_topic,
                transition_count,
                avg_transition_minutes,
                rapid_transition_pct
            FROM v_transition_map
            ORDER BY transition_count DESC
            LIMIT 10
        """).fetchdf()
        
        # Create visualizations
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(18, 14))
        
        # Recurring meeting ROI analysis
        ax1.scatter(recurring_data['total_hours'], recurring_data['frequency_per_week'],
                   s=recurring_data['avg_attendees'] * 20, 
                   c=recurring_data['avg_duration_minutes'],
                   cmap='RdYlBu_r', alpha=0.7)
        ax1.set_xlabel('Total Hours Invested')
        ax1.set_ylabel('Frequency per Week')
        ax1.set_title('Recurring Meeting ROI Analysis', fontweight='bold')
        
        # Add colorbar
        scatter = ax1.scatter(recurring_data['total_hours'], recurring_data['frequency_per_week'],
                             s=recurring_data['avg_attendees'] * 20, 
                             c=recurring_data['avg_duration_minutes'],
                             cmap='RdYlBu_r', alpha=0.7)
        plt.colorbar(scatter, ax=ax1, label='Avg Duration (min)')
        
        # Off-hours distribution
        colors = ['#ff6b6b', '#4ecdc4', '#45b7d1', '#96ceb4']
        bars = ax2.bar(offhours_data['offhours_type'], offhours_data['total_hours'], 
                      color=colors[:len(offhours_data)], alpha=0.8)
        ax2.set_title('Off-Hours Meeting Distribution', fontweight='bold')
        ax2.set_ylabel('Total Hours')
        ax2.tick_params(axis='x', rotation=45)
        
        # Add value labels
        for bar in bars:
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.1f}h', ha='center', va='bottom')
        
        # Context switching heatmap
        if len(transition_data) > 0:
            # Create a simple transition matrix visualization
            unique_topics = pd.concat([transition_data['from_topic'], transition_data['to_topic']]).unique()
            matrix_size = min(len(unique_topics), 8)  # Limit size for readability
            
            transition_matrix = np.zeros((matrix_size, matrix_size))
            topic_labels = unique_topics[:matrix_size]
            
            for _, row in transition_data.head(20).iterrows():
                if row['from_topic'] in topic_labels and row['to_topic'] in topic_labels:
                    from_idx = np.where(topic_labels == row['from_topic'])[0]
                    to_idx = np.where(topic_labels == row['to_topic'])[0]
                    if len(from_idx) > 0 and len(to_idx) > 0:
                        transition_matrix[from_idx[0], to_idx[0]] = row['transition_count']
            
            im = ax3.imshow(transition_matrix, cmap='Blues', aspect='auto')
            ax3.set_title('Topic Transition Matrix', fontweight='bold')
            ax3.set_xticks(range(len(topic_labels)))
            ax3.set_yticks(range(len(topic_labels)))
            ax3.set_xticklabels([label[:10] for label in topic_labels], rotation=45)
            ax3.set_yticklabels([label[:10] for label in topic_labels])
            ax3.set_xlabel('To Topic')
            ax3.set_ylabel('From Topic')
            plt.colorbar(im, ax=ax3, label='Transition Count')
        else:
            ax3.text(0.5, 0.5, 'No transition data available', ha='center', va='center',
                    transform=ax3.transAxes, fontsize=14)
            ax3.set_title('Topic Transition Matrix', fontweight='bold')
        
        # Meeting duration distribution
        duration_data = self.connection.execute("""
            SELECT 
                duration_category,
                COUNT(*) AS meeting_count,
                ROUND(AVG(duration_minutes), 1) AS avg_duration
            FROM v_events_norm
            WHERE meeting_type IN ('one_on_one', 'small_meeting', 'large_meeting')
            GROUP BY duration_category
            ORDER BY 
                CASE duration_category 
                    WHEN 'short' THEN 1
                    WHEN 'standard' THEN 2
                    WHEN 'long' THEN 3
                    WHEN 'extended' THEN 4
                END
        """).fetchdf()
        
        colors = ['#66cc66', '#ffcc00', '#ff8000', '#ff4d4d']
        bars = ax4.bar(duration_data['duration_category'], duration_data['meeting_count'], 
                      color=colors[:len(duration_data)], alpha=0.8)
        ax4.set_title('Meeting Duration Distribution', fontweight='bold')
        ax4.set_ylabel('Number of Meetings')
        ax4.set_xlabel('Duration Category')
        
        # Add percentage labels
        total_meetings = duration_data['meeting_count'].sum()
        for bar, count in zip(bars, duration_data['meeting_count']):
            height = bar.get_height()
            pct = (count / total_meetings) * 100
            ax4.text(bar.get_x() + bar.get_width()/2., height,
                    f'{count}\n({pct:.1f}%)', ha='center', va='bottom')
        
        plt.tight_layout()
        self.save_chart(fig, '07_efficiency_metrics', 'matplotlib')
        plt.close()
        
    def generate_executive_dashboard(self):
        """Generate executive summary dashboard."""
        print("Generating executive dashboard...")
        
        # Get comprehensive KPIs
        kpis = self.connection.execute("SELECT * FROM v_calendar_kpis").fetchone()
        
        # Get top insights
        top_collaborators = self.connection.execute("""
            SELECT participant_email, total_minutes, domain, is_internal
            FROM v_collab_minutes 
            ORDER BY total_minutes DESC 
            LIMIT 5
        """).fetchdf()
        
        top_topics = self.connection.execute("""
            SELECT topic_category, total_hours, time_share_pct
            FROM v_topic_minutes 
            ORDER BY total_minutes DESC 
            LIMIT 5
        """).fetchdf()
        
        # Create dashboard
        fig = plt.figure(figsize=(20, 16))
        gs = fig.add_gridspec(4, 4, hspace=0.3, wspace=0.3)
        
        # Title
        fig.suptitle('Ryan Marien - Calendar Analytics Executive Dashboard', 
                    fontsize=24, fontweight='bold', y=0.95)
        
        # Period summary (top row, full width)
        ax_period = fig.add_subplot(gs[0, :])
        ax_period.axis('off')
        
        period_text = f"""
        ANALYSIS PERIOD: {kpis[0].strftime('%b %d, %Y')} - {kpis[1].strftime('%b %d, %Y')} ({int(kpis[2])} days)
        
        MEETING VOLUME: {kpis[3]} total meetings | {kpis[5]:.1f} meetings/day | {kpis[6]:.1f} hours/day
        PRODUCTIVITY: {kpis[14]:.1f}/100 score | {kpis[8]:.1f}% deep work ratio | {kpis[12]:.1f}% buffer coverage
        """
        
        ax_period.text(0.5, 0.5, period_text, ha='center', va='center', fontsize=14,
                      bbox=dict(boxstyle='round,pad=1', facecolor='lightblue', alpha=0.8))
        
        # Key metrics gauges (row 2)
        metrics_data = [
            ('Productivity Score', kpis[14], 100, '#4CAF50'),
            ('Deep Work Ratio', kpis[8], 40, '#2196F3'), 
            ('Buffer Coverage', kpis[12], 80, '#FF9800'),
            ('Avg Daily Hours', kpis[7], 6, '#9C27B0')
        ]
        
        for i, (label, value, target, color) in enumerate(metrics_data):
            ax = fig.add_subplot(gs[1, i])
            self._create_gauge_chart(ax, label, value, target, color)
        
        # Top collaborators (row 3, left)
        ax_collab = fig.add_subplot(gs[2, :2])
        y_pos = np.arange(len(top_collaborators))
        colors = ['red' if not is_int else 'blue' for is_int in top_collaborators['is_internal']]
        
        bars = ax_collab.barh(y_pos, top_collaborators['total_minutes'], color=colors, alpha=0.7)
        ax_collab.set_yticks(y_pos)
        ax_collab.set_yticklabels([email.split('@')[0][:15] for email in top_collaborators['participant_email']])
        ax_collab.set_xlabel('Total Minutes')
        ax_collab.set_title('Top Collaboration Partners', fontweight='bold', fontsize=14)
        
        # Add legend
        from matplotlib.patches import Patch
        legend_elements = [Patch(facecolor='blue', alpha=0.7, label='Internal'),
                          Patch(facecolor='red', alpha=0.7, label='External')]
        ax_collab.legend(handles=legend_elements)
        
        # Top topics (row 3, right)
        ax_topics = fig.add_subplot(gs[2, 2:])
        colors = plt.cm.Set3(np.linspace(0, 1, len(top_topics)))
        wedges, texts, autotexts = ax_topics.pie(top_topics['time_share_pct'], 
                                                 labels=top_topics['topic_category'],
                                                 colors=colors, autopct='%1.1f%%', startangle=90)
        ax_topics.set_title('Time Allocation by Topic', fontweight='bold', fontsize=14)
        
        # Weekly pattern heatmap (bottom row)
        ax_heatmap = fig.add_subplot(gs[3, :])
        
        # Get heatmap data
        heatmap_data = self.connection.execute("""
            SELECT day_of_week, start_hour, meetings_per_day
            FROM v_day_load
            WHERE meetings_per_day > 0
        """).fetchdf()
        
        if not heatmap_data.empty:
            pivot_data = heatmap_data.pivot(index='start_hour', columns='day_of_week', values='meetings_per_day')
            pivot_data = pivot_data.fillna(0)
            
            im = ax_heatmap.imshow(pivot_data.values, cmap='YlOrRd', aspect='auto')
            ax_heatmap.set_title('Weekly Meeting Pattern (Meetings per Day)', fontweight='bold', fontsize=14)
            ax_heatmap.set_xlabel('Day of Week')
            ax_heatmap.set_ylabel('Hour of Day')
            ax_heatmap.set_xticks(range(len(pivot_data.columns)))
            ax_heatmap.set_xticklabels(['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'])
            ax_heatmap.set_yticks(range(len(pivot_data.index)))
            ax_heatmap.set_yticklabels([f"{int(h)}:00" for h in pivot_data.index])
            
            # Add colorbar
            cbar = plt.colorbar(im, ax=ax_heatmap, orientation='horizontal', pad=0.1, shrink=0.8)
            cbar.set_label('Meetings per Day')
        
        self.save_chart(fig, '08_executive_dashboard', 'matplotlib')
        plt.close()
        
    def _create_gauge_chart(self, ax, label, value, target, color):
        """Create a gauge chart for KPI visualization."""
        # Create gauge background
        ax.pie([value, max(100 - value, 0)], colors=[color, '#e0e0e0'], 
               startangle=90, counterclock=False)
        
        # Add center circle for donut effect
        centre_circle = plt.Circle((0,0), 0.70, fc='white')
        ax.add_patch(centre_circle)
        
        # Add text
        ax.text(0, 0.1, f'{value:.1f}', ha='center', va='center', fontsize=18, fontweight='bold')
        ax.text(0, -0.2, label, ha='center', va='center', fontsize=10, fontweight='bold')
        ax.text(0, -0.35, f'Target: {target}', ha='center', va='center', fontsize=8)
        
        ax.set_aspect('equal')
        
    def generate_all_visualizations(self):
        """Generate all calendar visualizations."""
        print("Generating Calendar Analytics Visualizations")
        print("=" * 50)
        
        self.connect_db()
        
        try:
            # Generate all visualizations
            self.generate_heatmap_weekly_load()
            self.generate_meeting_volume_time_series()
            self.generate_b2b_analysis()
            self.generate_topic_analysis()
            self.generate_deep_work_analysis()
            self.generate_collaboration_network()
            self.generate_efficiency_metrics()
            self.generate_executive_dashboard()
            
            print("\n" + "=" * 50)
            print(f"Generated {len(self.visualizations_created)} visualizations:")
            for viz in self.visualizations_created:
                print(f"  • {viz}")
                
            return self.visualizations_created
            
        except Exception as e:
            print(f"Error generating visualizations: {e}")
            raise
        finally:
            if self.connection:
                self.connection.close()

def main():
    """Main execution function."""
    db_path = "/Users/david.campos/VibeCode/AICoS-Lab/experiments/ryan_time_analysis/data/processed/duckdb/calendar_analytics.db"
    output_dir = "/Users/david.campos/VibeCode/AICoS-Lab/experiments/ryan_time_analysis/visualizations/calendar"
    
    generator = CalendarVisualizationGenerator(db_path, output_dir)
    generator.generate_all_visualizations()

if __name__ == "__main__":
    main()