#!/usr/bin/env python3
"""
Sub-Agent 2: Topic×Segment×Week Heatmap Generator
Creates the specific visualization requested: "heatmap showing topic engagement week by week by segment"
"""

import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import warnings
warnings.filterwarnings('ignore')

class TopicSegmentHeatmapGenerator:
    """Generates topic engagement heatmaps by company segment"""
    
    def __init__(self, data_file: str):
        self.data_file = data_file
        self.weekly_matrix = pd.read_csv(data_file)
        self.prepare_data()
    
    def prepare_data(self):
        """Prepare and clean data for visualization"""
        # Ensure proper data types
        self.weekly_matrix['duration_hours'] = pd.to_numeric(self.weekly_matrix['duration_hours'])
        
        # Sort by chronological order
        self.weekly_matrix['week_sort'] = self.weekly_matrix['calendar_week'].apply(self._week_to_sortable)
        self.weekly_matrix = self.weekly_matrix.sort_values('week_sort')
        
        # Clean up topic names for display
        self.weekly_matrix['topic_display'] = self.weekly_matrix['topic'].str.replace('_', ' ').str.title()
        
        # Filter out personal life to focus on work topics (user can uncomment to include)
        work_matrix = self.weekly_matrix[
            ~self.weekly_matrix['topic'].isin(['Personal_Life', 'Uncategorized'])
        ].copy()
        
        self.work_matrix = work_matrix
        
        print(f"Data prepared: {len(self.weekly_matrix)} total combinations")
        print(f"Work-focused data: {len(self.work_matrix)} combinations")
    
    def _week_to_sortable(self, week_str: str) -> int:
        """Convert week string to sortable integer"""
        year, week = week_str.split('-W')
        return int(year) * 100 + int(week)
    
    def create_segment_focused_heatmaps(self):
        """Create separate heatmaps for each company segment"""
        
        segments = sorted(self.work_matrix['segment'].unique())
        
        fig, axes = plt.subplots(len(segments), 1, figsize=(16, 6*len(segments)))
        if len(segments) == 1:
            axes = [axes]
        
        plt.style.use('default')
        
        for i, segment in enumerate(segments):
            segment_data = self.work_matrix[self.work_matrix['segment'] == segment]
            
            # Create pivot table for this segment
            pivot = segment_data.pivot_table(
                values='duration_hours',
                index='topic_display',
                columns='calendar_week',
                aggfunc='sum',
                fill_value=0
            )
            
            # Sort rows by total hours (most engaged topics first)
            row_sums = pivot.sum(axis=1).sort_values(ascending=False)
            pivot = pivot.reindex(row_sums.index)
            
            # Sort columns chronologically
            pivot = pivot.reindex(columns=sorted(pivot.columns, key=self._week_to_sortable))
            
            # Create heatmap
            sns.heatmap(
                pivot,
                ax=axes[i],
                cmap='YlOrRd',
                cbar_kws={'label': 'Hours per Week'},
                linewidths=0.5,
                linecolor='white',
                fmt='.1f',
                annot=pivot > 0,  # Only annotate non-zero values
                annot_kws={'size': 8}
            )
            
            axes[i].set_title(f'Topic Engagement by Week - {segment} Meetings', 
                            fontsize=14, fontweight='bold', pad=20)
            axes[i].set_xlabel('Calendar Week', fontweight='bold')
            axes[i].set_ylabel('Meeting Topics', fontweight='bold')
            
            # Rotate x-axis labels for better readability
            axes[i].tick_params(axis='x', rotation=45)
            axes[i].tick_params(axis='y', rotation=0)
        
        plt.suptitle('Ryan Marien: Topic Engagement Heatmap by Company Segment\n(Aug 2024 - Feb 2025)', 
                     fontsize=16, fontweight='bold', y=0.98)
        plt.tight_layout()
        
        # Save static version
        output_file = "/Users/david.campos/VibeCode/AICoS-Lab/experiments/ryan_time_analysis/topic_segment_weekly_heatmap.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight', facecolor='white')
        print(f"Static heatmap saved: {output_file}")
        
        plt.show()
    
    def create_interactive_heatmap(self):
        """Create interactive Plotly heatmap"""
        
        # Focus on work topics for cleaner visualization
        data = self.work_matrix.copy()
        
        # Create pivot table
        pivot = data.pivot_table(
            values='duration_hours',
            index='topic_display',
            columns='calendar_week',
            aggfunc='sum',
            fill_value=0
        )
        
        # Sort by total engagement
        row_sums = pivot.sum(axis=1).sort_values(ascending=False)
        pivot = pivot.reindex(row_sums.index)
        
        # Sort columns chronologically
        pivot = pivot.reindex(columns=sorted(pivot.columns, key=self._week_to_sortable))
        
        # Create hover text with details
        hover_text = []
        for i, topic in enumerate(pivot.index):
            hover_row = []
            for j, week in enumerate(pivot.columns):
                hours = pivot.iloc[i, j]
                # Get segment breakdown for this topic-week combination
                segment_data = data[(data['topic_display'] == topic) & (data['calendar_week'] == week)]
                segment_info = ""
                if not segment_data.empty:
                    for _, row in segment_data.iterrows():
                        segment_info += f"<br>{row['segment']}: {row['duration_hours']:.1f}h ({row['event_count']} events)"
                
                hover_text_cell = f"<b>{topic}</b><br>Week: {week}<br>Total: {hours:.1f} hours{segment_info}"
                hover_row.append(hover_text_cell)
            hover_text.append(hover_row)
        
        # Create the interactive heatmap
        fig = go.Figure(data=go.Heatmap(
            z=pivot.values,
            x=list(pivot.columns),
            y=list(pivot.index),
            hovertemplate='%{text}<extra></extra>',
            text=hover_text,
            colorscale='YlOrRd',
            colorbar=dict(title="Hours per Week"),
            showscale=True
        ))
        
        fig.update_layout(
            title={
                'text': 'Ryan Marien: Topic Engagement Week by Week by Company Segment<br><sub>Aug 2024 - Feb 2025 • Hover for segment breakdown</sub>',
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 16}
            },
            xaxis_title="Calendar Week",
            yaxis_title="Meeting Topics",
            width=1400,
            height=800,
            xaxis=dict(tickangle=45),
            yaxis=dict(tickangle=0),
            font=dict(size=10)
        )
        
        # Save interactive version
        interactive_file = "/Users/david.campos/VibeCode/AICoS-Lab/experiments/ryan_time_analysis/topic_segment_weekly_heatmap_interactive.html"
        fig.write_html(interactive_file)
        print(f"Interactive heatmap saved: {interactive_file}")
        
        return fig
    
    def create_segment_comparison_view(self):
        """Create side-by-side comparison of segments"""
        
        # Get top topics across all segments
        top_topics = (self.work_matrix.groupby('topic_display')['duration_hours']
                     .sum().sort_values(ascending=False).head(8).index.tolist())
        
        # Filter data to top topics
        filtered_data = self.work_matrix[self.work_matrix['topic_display'].isin(top_topics)]
        
        # Create subplots for each segment
        segments = sorted(filtered_data['segment'].unique())
        fig = make_subplots(
            rows=1, cols=len(segments),
            subplot_titles=[f'{segment} Meetings' for segment in segments],
            shared_yaxis=True
        )
        
        for i, segment in enumerate(segments):
            segment_data = filtered_data[filtered_data['segment'] == segment]
            
            if segment_data.empty:
                continue
                
            pivot = segment_data.pivot_table(
                values='duration_hours',
                index='topic_display',
                columns='calendar_week',
                aggfunc='sum',
                fill_value=0
            )
            
            # Ensure consistent topic ordering
            pivot = pivot.reindex(top_topics, fill_value=0)
            pivot = pivot.reindex(columns=sorted(pivot.columns, key=self._week_to_sortable))
            
            # Add heatmap
            fig.add_trace(
                go.Heatmap(
                    z=pivot.values,
                    x=list(pivot.columns),
                    y=list(pivot.index),
                    colorscale='YlOrRd',
                    showscale=(i == len(segments) - 1),  # Only show scale for last subplot
                    hovertemplate=f'<b>{segment} - %{{y}}</b><br>Week: %{{x}}<br>Hours: %{{z:.1f}}<extra></extra>'
                ),
                row=1, col=i+1
            )
        
        fig.update_layout(
            title={
                'text': 'Topic Engagement by Company Segment - Side-by-Side Comparison',
                'x': 0.5,
                'xanchor': 'center'
            },
            width=1600,
            height=700
        )
        
        # Update x-axis labels
        for i in range(len(segments)):
            fig.update_xaxes(tickangle=45, row=1, col=i+1)
        
        comparison_file = "/Users/david.campos/VibeCode/AICoS-Lab/experiments/ryan_time_analysis/topic_segment_comparison_heatmap.html"
        fig.write_html(comparison_file)
        print(f"Comparison heatmap saved: {comparison_file}")
        
        return fig
    
    def generate_insights_report(self):
        """Generate insights about topic-segment patterns"""
        
        print("\n" + "="*80)
        print("TOPIC×SEGMENT×WEEK HEATMAP ANALYSIS INSIGHTS")
        print("="*80)
        
        # Weekly engagement patterns
        weekly_totals = self.weekly_matrix.groupby('calendar_week')['duration_hours'].sum().sort_index()
        peak_week = weekly_totals.idxmax()
        low_week = weekly_totals.idxmin()
        
        print(f"📅 WEEKLY PATTERNS:")
        print(f"   • Peak Engagement Week: {peak_week} ({weekly_totals[peak_week]:.1f} hours)")
        print(f"   • Lowest Engagement Week: {low_week} ({weekly_totals[low_week]:.1f} hours)")
        
        # Topic consistency across segments
        topic_segment_diversity = {}
        for topic in self.work_matrix['topic'].unique():
            topic_data = self.work_matrix[self.work_matrix['topic'] == topic]
            unique_segments = topic_data['segment'].nunique()
            total_hours = topic_data['duration_hours'].sum()
            topic_segment_diversity[topic] = {
                'segments': unique_segments,
                'hours': total_hours
            }
        
        print(f"\n🎯 TOPIC CROSS-SEGMENT ENGAGEMENT:")
        for topic, stats in sorted(topic_segment_diversity.items(), key=lambda x: x[1]['hours'], reverse=True)[:6]:
            topic_clean = topic.replace('_', ' ').title()
            print(f"   • {topic_clean:20}: {stats['segments']} segments, {stats['hours']:.1f} hours total")
        
        # Segment specialization
        print(f"\n🏢 SEGMENT SPECIALIZATION:")
        for segment in sorted(self.work_matrix['segment'].unique()):
            segment_data = self.work_matrix[self.work_matrix['segment'] == segment]
            top_topic = segment_data.groupby('topic_display')['duration_hours'].sum().idxmax()
            top_hours = segment_data.groupby('topic_display')['duration_hours'].sum().max()
            total_segment_hours = segment_data['duration_hours'].sum()
            
            print(f"   • {segment:10}: Most engaged in '{top_topic}' ({top_hours:.1f}h / {top_hours/total_segment_hours*100:.1f}%)")
        
        # Time distribution insights
        work_hours = self.work_matrix['duration_hours'].sum()
        total_hours = self.weekly_matrix['duration_hours'].sum()
        
        print(f"\n⏰ TIME ALLOCATION:")
        print(f"   • Work-focused meeting hours: {work_hours:.1f} ({work_hours/total_hours*100:.1f}%)")
        print(f"   • Average work hours per week: {work_hours/25:.1f}")
        print(f"   • Most active work topics account for {work_hours:.1f} hours across {len(self.work_matrix)} combinations")
        
        print("\n" + "="*80)

def main():
    """Main execution function"""
    print("Generating Topic×Segment×Week Heatmap Visualizations")
    print("=" * 60)
    
    # Initialize generator
    data_file = "/Users/david.campos/VibeCode/AICoS-Lab/experiments/ryan_time_analysis/weekly_topic_segment_matrix.csv"
    generator = TopicSegmentHeatmapGenerator(data_file)
    
    # Generate insights
    generator.generate_insights_report()
    
    # Create visualizations
    print("\n📊 Creating segment-focused static heatmaps...")
    generator.create_segment_focused_heatmaps()
    
    print("\n🎮 Creating interactive heatmap...")
    interactive_fig = generator.create_interactive_heatmap()
    
    print("\n📋 Creating segment comparison view...")
    comparison_fig = generator.create_segment_comparison_view()
    
    print("\n✅ HEATMAP GENERATION COMPLETE!")
    print("Files created:")
    print("• topic_segment_weekly_heatmap.png (static)")  
    print("• topic_segment_weekly_heatmap_interactive.html (interactive)")
    print("• topic_segment_comparison_heatmap.html (comparison view)")
    print("\n🎯 DELIVERABLE: User's requested 'heatmap showing topic engagement week by week by segment' is ready!")

if __name__ == "__main__":
    main()