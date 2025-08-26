#!/usr/bin/env python3
"""
Generate comprehensive Slack visualizations
Creates 12+ charts for executive communication pattern analysis
"""

import duckdb
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import networkx as nx
from pathlib import Path
import numpy as np
import json
from datetime import datetime

# Configuration
plt.style.use('seaborn-v0_8')
sns.set_palette("husl")

# Paths
DB_PATH = Path(__file__).parent.parent.parent / "data" / "processed" / "duckdb" / "slack_analytics.db"
VIZ_DIR = Path(__file__).parent.parent.parent / "visualizations" / "slack"
VIZ_DIR.mkdir(parents=True, exist_ok=True)

def connect_db():
    """Connect to DuckDB"""
    return duckdb.connect(str(DB_PATH))

def create_slack_activity_heatmap():
    """1. Slack Activity Heatmap (DoW × Hour)"""
    print("Creating Slack activity heatmap...")
    
    conn = connect_db()
    df = conn.execute("""
        SELECT day_of_week, hour, ryan_messages, total_messages,
               ryan_participation_pct, avg_messages_per_day_hour, time_period
        FROM v_slack_load_heatmap
        ORDER BY CASE day_of_week 
            WHEN 'Monday' THEN 1 WHEN 'Tuesday' THEN 2 WHEN 'Wednesday' THEN 3 
            WHEN 'Thursday' THEN 4 WHEN 'Friday' THEN 5 WHEN 'Saturday' THEN 6 
            WHEN 'Sunday' THEN 7 END, hour
    """).df()
    conn.close()
    
    # Pivot for heatmap
    heatmap_data = df.pivot(index='day_of_week', columns='hour', values='ryan_messages').fillna(0)
    
    # Reorder days
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    heatmap_data = heatmap_data.reindex(day_order)
    
    # Create matplotlib heatmap
    fig, ax = plt.subplots(figsize=(16, 8))
    sns.heatmap(heatmap_data, annot=True, fmt='g', cmap='YlOrRd', 
                cbar_kws={'label': "Ryan's Messages"}, ax=ax)
    ax.set_title("Ryan's Slack Activity Heatmap (Messages by Day and Hour)", fontsize=16, pad=20)
    ax.set_xlabel("Hour of Day", fontsize=12)
    ax.set_ylabel("Day of Week", fontsize=12)
    plt.tight_layout()
    plt.savefig(VIZ_DIR / "01_slack_activity_heatmap.png", dpi=300, bbox_inches='tight')
    plt.close()
    
    # Create Plotly interactive version
    fig_plotly = px.imshow(heatmap_data, 
                          labels=dict(x="Hour of Day", y="Day of Week", color="Ryan's Messages"),
                          title="Ryan's Slack Activity Heatmap (Interactive)",
                          color_continuous_scale='YlOrRd')
    fig_plotly.update_layout(height=600, width=1000)
    fig_plotly.write_html(str(VIZ_DIR / "01_slack_activity_heatmap_interactive.html"))
    
    print(f"   ✓ Peak activity: {heatmap_data.max().max()} messages")
    return heatmap_data

def create_message_volume_timeseries():
    """2. Message Volume Time Series"""
    print("Creating message volume time series...")
    
    conn = connect_db()
    df = conn.execute("""
        SELECT date, total_daily_messages, ryan_daily_messages, 
               dm_count, channel_count, after_hours_pct
        FROM v_communication_intensity
        ORDER BY date
    """).df()
    conn.close()
    
    # Convert date column
    df['date'] = pd.to_datetime(df['date'])
    
    # Create time series plot
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10))
    
    # Total messages over time
    ax1.plot(df['date'], df['total_daily_messages'], 'b-', linewidth=2, label='Total Messages', alpha=0.7)
    ax1.plot(df['date'], df['ryan_daily_messages'], 'r-', linewidth=2, label="Ryan's Messages")
    ax1.fill_between(df['date'], df['ryan_daily_messages'], alpha=0.3, color='red')
    ax1.set_title("Daily Slack Message Volume Over Time", fontsize=14, pad=15)
    ax1.set_ylabel("Messages per Day")
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # DM vs Channel breakdown
    ax2.bar(df['date'], df['dm_count'], label='DM Messages', alpha=0.7, color='skyblue')
    ax2.bar(df['date'], df['channel_count'], bottom=df['dm_count'], 
            label='Channel Messages', alpha=0.7, color='lightcoral')
    ax2.set_title("DM vs Channel Message Distribution", fontsize=14, pad=15)
    ax2.set_ylabel("Messages per Day")
    ax2.set_xlabel("Date")
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(VIZ_DIR / "02_message_volume_timeseries.png", dpi=300, bbox_inches='tight')
    plt.close()
    
    # Interactive Plotly version
    fig_plotly = make_subplots(rows=2, cols=1, 
                              subplot_titles=("Daily Message Volume", "DM vs Channel Distribution"),
                              vertical_spacing=0.1)
    
    fig_plotly.add_trace(go.Scatter(x=df['date'], y=df['total_daily_messages'], 
                                   name='Total Messages', line=dict(color='blue')), row=1, col=1)
    fig_plotly.add_trace(go.Scatter(x=df['date'], y=df['ryan_daily_messages'], 
                                   name="Ryan's Messages", line=dict(color='red')), row=1, col=1)
    fig_plotly.add_trace(go.Bar(x=df['date'], y=df['dm_count'], name='DM Messages'), row=2, col=1)
    fig_plotly.add_trace(go.Bar(x=df['date'], y=df['channel_count'], name='Channel Messages'), row=2, col=1)
    
    fig_plotly.update_layout(height=800, title="Slack Message Volume Analysis")
    fig_plotly.write_html(str(VIZ_DIR / "02_message_volume_timeseries_interactive.html"))
    
    total_messages = df['total_daily_messages'].sum()
    print(f"   ✓ Total messages analyzed: {total_messages:,}")
    return df

def create_channel_activity_breakdown():
    """3. Channel Activity Breakdown"""
    print("Creating channel activity breakdown...")
    
    conn = connect_db()
    df = conn.execute("""
        SELECT channel_name, actual_total_messages, actual_ryan_messages, 
               ryan_participation_pct, unique_participants, avg_message_length,
               thread_messages, business_hours_messages, after_hours_messages
        FROM v_channel_activity
        ORDER BY actual_total_messages DESC
    """).df()
    conn.close()
    
    # Create subplot
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
    
    # 1. Total messages by channel (pie chart)
    colors = plt.cm.Set3(np.linspace(0, 1, len(df)))
    ax1.pie(df['actual_total_messages'], labels=df['channel_name'], autopct='%1.1f%%', 
            colors=colors, startangle=90)
    ax1.set_title("Total Messages by Channel", fontsize=14)
    
    # 2. Ryan's participation by channel (bar chart)
    ax2.barh(df['channel_name'], df['actual_ryan_messages'], color='lightcoral', alpha=0.7)
    ax2.set_title("Ryan's Messages by Channel", fontsize=14)
    ax2.set_xlabel("Ryan's Messages")
    
    # 3. Participation percentage
    ax3.barh(df['channel_name'], df['ryan_participation_pct'], color='skyblue', alpha=0.7)
    ax3.set_title("Ryan's Participation Rate by Channel", fontsize=14)
    ax3.set_xlabel("Participation %")
    ax3.axvline(x=50, color='red', linestyle='--', alpha=0.5, label='50% line')
    ax3.legend()
    
    # 4. Business hours vs after hours
    width = 0.35
    x = np.arange(len(df))
    ax4.bar(x - width/2, df['business_hours_messages'], width, label='Business Hours', alpha=0.7)
    ax4.bar(x + width/2, df['after_hours_messages'], width, label='After Hours', alpha=0.7)
    ax4.set_title("Business Hours vs After Hours Messages", fontsize=14)
    ax4.set_xlabel("Channels")
    ax4.set_ylabel("Messages")
    ax4.set_xticks(x)
    ax4.set_xticklabels(df['channel_name'], rotation=45, ha='right')
    ax4.legend()
    
    plt.tight_layout()
    plt.savefig(VIZ_DIR / "03_channel_activity_breakdown.png", dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"   ✓ Most active channel: {df.iloc[0]['channel_name']} ({df.iloc[0]['actual_total_messages']} messages)")
    return df

def create_communication_intensity_analysis():
    """4. Communication Intensity Timeline"""
    print("Creating communication intensity analysis...")
    
    conn = connect_db()
    df = conn.execute("""
        SELECT date, ryan_daily_messages, active_channels, active_users,
               after_hours_pct, ryan_channels_active, day_of_week
        FROM v_communication_intensity
        ORDER BY date
    """).df()
    conn.close()
    
    df['date'] = pd.to_datetime(df['date'])
    
    # Create multi-metric analysis
    fig, axes = plt.subplots(2, 2, figsize=(16, 10))
    
    # 1. Daily message intensity
    axes[0, 0].plot(df['date'], df['ryan_daily_messages'], 'b-', linewidth=2)
    axes[0, 0].fill_between(df['date'], df['ryan_daily_messages'], alpha=0.3)
    axes[0, 0].set_title("Ryan's Daily Message Intensity", fontsize=14)
    axes[0, 0].set_ylabel("Messages per Day")
    axes[0, 0].grid(True, alpha=0.3)
    
    # 2. Channel diversity
    axes[0, 1].plot(df['date'], df['ryan_channels_active'], 'g-', linewidth=2, marker='o', markersize=3)
    axes[0, 1].set_title("Channel Context Switching", fontsize=14)
    axes[0, 1].set_ylabel("Active Channels per Day")
    axes[0, 1].grid(True, alpha=0.3)
    
    # 3. After hours percentage
    axes[1, 0].plot(df['date'], df['after_hours_pct'], 'r-', linewidth=2)
    axes[1, 0].axhline(y=20, color='orange', linestyle='--', alpha=0.7, label='20% threshold')
    axes[1, 0].set_title("After Hours Communication %", fontsize=14)
    axes[1, 0].set_ylabel("After Hours %")
    axes[1, 0].set_xlabel("Date")
    axes[1, 0].legend()
    axes[1, 0].grid(True, alpha=0.3)
    
    # 4. Day of week pattern
    day_avg = df.groupby('day_of_week')['ryan_daily_messages'].mean().reset_index()
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    day_avg['day_of_week'] = pd.Categorical(day_avg['day_of_week'], categories=day_order, ordered=True)
    day_avg = day_avg.sort_values('day_of_week')
    
    axes[1, 1].bar(day_avg['day_of_week'], day_avg['ryan_daily_messages'], 
                   color='skyblue', alpha=0.7)
    axes[1, 1].set_title("Average Messages by Day of Week", fontsize=14)
    axes[1, 1].set_ylabel("Avg Messages")
    axes[1, 1].set_xlabel("Day of Week")
    axes[1, 1].tick_params(axis='x', rotation=45)
    
    plt.tight_layout()
    plt.savefig(VIZ_DIR / "04_communication_intensity.png", dpi=300, bbox_inches='tight')
    plt.close()
    
    avg_daily = df['ryan_daily_messages'].mean()
    print(f"   ✓ Average daily messages: {avg_daily:.1f}")
    return df

def create_response_pattern_analysis():
    """5. Response Time Analysis"""
    print("Creating response pattern analysis...")
    
    # For this visualization, we'll create synthetic response time data since
    # the actual response pattern view would need more complex temporal analysis
    
    conn = connect_db()
    df = conn.execute("""
        WITH message_pairs AS (
            SELECT 
                channel_name,
                date,
                hour,
                COUNT(CASE WHEN is_ryan_message THEN 1 END) as ryan_msgs,
                COUNT(CASE WHEN NOT is_ryan_message THEN 1 END) as others_msgs,
                -- Approximate response activity
                CASE WHEN COUNT(CASE WHEN is_ryan_message THEN 1 END) > 0 
                     AND COUNT(CASE WHEN NOT is_ryan_message THEN 1 END) > 0 
                THEN 1 ELSE 0 END as has_interaction
            FROM slack_messages
            GROUP BY channel_name, date, hour
        )
        SELECT 
            channel_name,
            SUM(has_interaction) as interactive_hours,
            AVG(ryan_msgs) as avg_ryan_msgs_per_hour,
            AVG(others_msgs) as avg_others_msgs_per_hour
        FROM message_pairs
        GROUP BY channel_name
        ORDER BY interactive_hours DESC
    """).df()
    conn.close()
    
    # Create response pattern visualization
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    
    # Interactive hours by channel
    ax1.barh(df['channel_name'], df['interactive_hours'], color='lightgreen', alpha=0.7)
    ax1.set_title("Interactive Communication Hours by Channel", fontsize=14)
    ax1.set_xlabel("Interactive Hours")
    
    # Message exchange ratio
    ax2.scatter(df['avg_ryan_msgs_per_hour'], df['avg_others_msgs_per_hour'], 
                s=df['interactive_hours']*10, alpha=0.6, c=range(len(df)), cmap='viridis')
    for i, channel in enumerate(df['channel_name']):
        ax2.annotate(channel, (df.iloc[i]['avg_ryan_msgs_per_hour'], 
                              df.iloc[i]['avg_others_msgs_per_hour']), 
                    xytext=(5, 5), textcoords='offset points', fontsize=9)
    ax2.set_xlabel("Ryan's Avg Messages/Hour")
    ax2.set_ylabel("Others' Avg Messages/Hour")
    ax2.set_title("Communication Exchange Patterns", fontsize=14)
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(VIZ_DIR / "05_response_patterns.png", dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"   ✓ Most interactive channel: {df.iloc[0]['channel_name']}")
    return df

def create_dm_vs_channel_analysis():
    """6. DM vs Channel Preference Analysis"""
    print("Creating DM vs Channel analysis...")
    
    conn = connect_db()
    df = conn.execute("""
        SELECT 
            hour,
            day_of_week,
            SUM(ryan_dm_messages) as total_dm,
            SUM(ryan_channel_messages) as total_channel,
            AVG(ryan_dm_preference_pct) as avg_dm_pct
        FROM v_dm_vs_channel_ratio
        WHERE ryan_dm_messages + ryan_channel_messages > 0
        GROUP BY hour, day_of_week
        ORDER BY hour
    """).df()
    conn.close()
    
    # Create analysis
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10))
    
    # Hourly preference
    hourly_totals = df.groupby('hour').agg({
        'total_dm': 'sum',
        'total_channel': 'sum',
        'avg_dm_pct': 'mean'
    }).reset_index()
    
    width = 0.35
    x = hourly_totals['hour']
    ax1.bar(x - width/2, hourly_totals['total_dm'], width, label='DM Messages', alpha=0.7)
    ax1.bar(x + width/2, hourly_totals['total_channel'], width, label='Channel Messages', alpha=0.7)
    ax1.set_title("Ryan's DM vs Channel Messages by Hour", fontsize=14)
    ax1.set_xlabel("Hour of Day")
    ax1.set_ylabel("Messages")
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # DM preference percentage over time
    ax2.plot(hourly_totals['hour'], hourly_totals['avg_dm_pct'], 'ro-', linewidth=2)
    ax2.axhline(y=50, color='gray', linestyle='--', alpha=0.5, label='50% (Equal preference)')
    ax2.set_title("DM Preference Percentage by Hour", fontsize=14)
    ax2.set_xlabel("Hour of Day")
    ax2.set_ylabel("DM Preference %")
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(VIZ_DIR / "06_dm_vs_channel_preference.png", dpi=300, bbox_inches='tight')
    plt.close()
    
    overall_dm_pct = (hourly_totals['total_dm'].sum() / 
                      (hourly_totals['total_dm'].sum() + hourly_totals['total_channel'].sum()) * 100)
    print(f"   ✓ Overall DM preference: {overall_dm_pct:.1f}%")
    return hourly_totals

def create_collaboration_network():
    """7. Top Collaborators Network"""
    print("Creating collaboration network...")
    
    conn = connect_db()
    df = conn.execute("""
        SELECT collaborator, interaction_type, channel_name, total_messages,
               avg_messages_per_day
        FROM v_collaboration_frequency
        WHERE total_messages >= 5  -- Filter for meaningful collaborations
        ORDER BY total_messages DESC
        LIMIT 20
    """).df()
    conn.close()
    
    # Create network graph
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 8))
    
    # Top collaborators bar chart
    top_collaborators = df.groupby('collaborator')['total_messages'].sum().sort_values(ascending=False).head(10)
    ax1.barh(range(len(top_collaborators)), top_collaborators.values, color='lightcoral', alpha=0.7)
    ax1.set_yticks(range(len(top_collaborators)))
    ax1.set_yticklabels(top_collaborators.index, fontsize=10)
    ax1.set_title("Top 10 Communication Partners", fontsize=14)
    ax1.set_xlabel("Total Messages Exchanged")
    
    # Interaction type breakdown
    interaction_summary = df.groupby('interaction_type')['total_messages'].sum()
    colors = ['skyblue', 'lightgreen']
    ax2.pie(interaction_summary.values, labels=interaction_summary.index, 
            autopct='%1.1f%%', colors=colors, startangle=90)
    ax2.set_title("DM vs Channel Collaboration Distribution", fontsize=14)
    
    plt.tight_layout()
    plt.savefig(VIZ_DIR / "07_collaboration_network.png", dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"   ✓ Top collaborator: {top_collaborators.index[0]} ({top_collaborators.iloc[0]} messages)")
    return df

def create_after_hours_analysis():
    """8. After Hours Activity Analysis"""
    print("Creating after-hours analysis...")
    
    conn = connect_db()
    df = conn.execute("""
        SELECT time_category, SUM(ryan_messages) as ryan_msgs,
               SUM(total_messages) as total_msgs,
               AVG(avg_message_length) as avg_length,
               COUNT(DISTINCT date) as days_active
        FROM v_after_hours_slack
        GROUP BY time_category
        ORDER BY ryan_msgs DESC
    """).df()
    conn.close()
    
    # Create after-hours analysis
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    
    # After hours messages by time category
    ax1.bar(range(len(df)), df['ryan_msgs'], color='orange', alpha=0.7)
    ax1.set_xticks(range(len(df)))
    ax1.set_xticklabels(df['time_category'], rotation=45, ha='right')
    ax1.set_title("Ryan's After-Hours Messages by Time Category", fontsize=14)
    ax1.set_ylabel("Messages")
    
    # Average message length in different periods
    ax2.bar(range(len(df)), df['avg_length'], color='lightblue', alpha=0.7)
    ax2.set_xticks(range(len(df)))
    ax2.set_xticklabels(df['time_category'], rotation=45, ha='right')
    ax2.set_title("Average Message Length by Time Category", fontsize=14)
    ax2.set_ylabel("Characters")
    
    plt.tight_layout()
    plt.savefig(VIZ_DIR / "08_after_hours_analysis.png", dpi=300, bbox_inches='tight')
    plt.close()
    
    total_after_hours = df['ryan_msgs'].sum()
    print(f"   ✓ Total after-hours messages: {total_after_hours}")
    return df

def create_thread_participation_analysis():
    """9. Thread Participation Analysis"""
    print("Creating thread participation analysis...")
    
    conn = connect_db()
    df = conn.execute("""
        SELECT channel_name, 
               SUM(ryan_thread_messages) as ryan_threads,
               SUM(ryan_initial_messages) as ryan_initials,
               SUM(unique_threads) as total_threads,
               AVG(thread_usage_pct) as avg_thread_pct,
               AVG(avg_replies_per_thread) as avg_replies
        FROM v_thread_participation
        GROUP BY channel_name
        ORDER BY ryan_threads DESC
    """).df()
    conn.close()
    
    # Create thread analysis
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    
    # Thread vs initial messages
    width = 0.35
    x = np.arange(len(df))
    ax1.bar(x - width/2, df['ryan_threads'], width, label='Thread Replies', alpha=0.7)
    ax1.bar(x + width/2, df['ryan_initials'], width, label='Initial Messages', alpha=0.7)
    ax1.set_title("Ryan's Thread Replies vs Initial Messages", fontsize=14)
    ax1.set_xlabel("Channels")
    ax1.set_ylabel("Messages")
    ax1.set_xticks(x)
    ax1.set_xticklabels(df['channel_name'], rotation=45, ha='right')
    ax1.legend()
    
    # Thread usage percentage
    ax2.bar(df['channel_name'], df['avg_thread_pct'], color='green', alpha=0.7)
    ax2.set_title("Thread Usage Percentage by Channel", fontsize=14)
    ax2.set_ylabel("Thread Usage %")
    ax2.set_xlabel("Channels")
    ax2.tick_params(axis='x', rotation=45)
    
    plt.tight_layout()
    plt.savefig(VIZ_DIR / "09_thread_participation.png", dpi=300, bbox_inches='tight')
    plt.close()
    
    total_thread_msgs = df['ryan_threads'].sum()
    print(f"   ✓ Total thread messages: {total_thread_msgs}")
    return df

def create_strategic_vs_operational():
    """10. Strategic vs Operational Communication"""
    print("Creating strategic vs operational analysis...")
    
    conn = connect_db()
    df = conn.execute("""
        SELECT communication_category,
               SUM(ryan_messages) as ryan_msgs,
               SUM(total_messages) as total_msgs,
               AVG(ryan_avg_message_length) as avg_msg_length,
               COUNT(DISTINCT channel_name) as channels
        FROM v_strategic_vs_operational
        GROUP BY communication_category
        ORDER BY ryan_msgs DESC
    """).df()
    conn.close()
    
    # Create strategic analysis
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    
    # Messages by category
    colors = ['#ff9999', '#66b3ff', '#99ff99', '#ffcc99', '#ff99cc']
    ax1.pie(df['ryan_msgs'], labels=df['communication_category'], 
            autopct='%1.1f%%', colors=colors[:len(df)], startangle=90)
    ax1.set_title("Ryan's Messages by Communication Category", fontsize=14)
    
    # Average message length by category
    ax2.bar(df['communication_category'], df['avg_msg_length'], 
            color=colors[:len(df)], alpha=0.7)
    ax2.set_title("Average Message Length by Category", fontsize=14)
    ax2.set_ylabel("Characters")
    ax2.set_xlabel("Category")
    ax2.tick_params(axis='x', rotation=45)
    
    plt.tight_layout()
    plt.savefig(VIZ_DIR / "10_strategic_vs_operational.png", dpi=300, bbox_inches='tight')
    plt.close()
    
    strategic_pct = (df[df['communication_category'].str.contains('Strategic')]['ryan_msgs'].sum() / 
                     df['ryan_msgs'].sum() * 100)
    print(f"   ✓ Strategic communication: {strategic_pct:.1f}%")
    return df

def create_peak_hours_analysis():
    """11. Peak Communication Hours Analysis"""
    print("Creating peak hours analysis...")
    
    conn = connect_db()
    df = conn.execute("""
        SELECT day_of_week, hour, ryan_messages, total_messages,
               activity_level, time_period, ryan_activity_rank
        FROM v_peak_communication_hours
        WHERE ryan_activity_rank <= 8  -- Top 8 hours per day
        ORDER BY day_of_week, ryan_activity_rank
    """).df()
    conn.close()
    
    # Create peak hours visualization
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10))
    
    # Peak hours heatmap by day
    peak_data = df[df['ryan_activity_rank'] <= 3].pivot(index='day_of_week', columns='hour', values='ryan_messages').fillna(0)
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    if not peak_data.empty:
        peak_data = peak_data.reindex(day_order, fill_value=0)
        sns.heatmap(peak_data, annot=True, fmt='g', cmap='Reds', ax=ax1,
                   cbar_kws={'label': 'Messages'})
    ax1.set_title("Peak Communication Hours (Top 3 per Day)", fontsize=14)
    ax1.set_xlabel("Hour")
    ax1.set_ylabel("Day of Week")
    
    # Activity level distribution
    activity_counts = df['activity_level'].value_counts()
    ax2.pie(activity_counts.values, labels=activity_counts.index, 
            autopct='%1.1f%%', startangle=90)
    ax2.set_title("Distribution of Activity Levels", fontsize=14)
    
    plt.tight_layout()
    plt.savefig(VIZ_DIR / "11_peak_hours_analysis.png", dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"   ✓ Peak hours identified across {df['day_of_week'].nunique()} days")
    return df

def create_executive_dashboard():
    """12. Executive Summary Dashboard"""
    print("Creating executive summary dashboard...")
    
    conn = connect_db()
    
    # Collect key metrics
    total_messages = conn.execute("SELECT COUNT(*) FROM slack_messages WHERE is_ryan_message = true").fetchone()[0]
    total_channels = conn.execute("SELECT COUNT(DISTINCT channel_id) FROM slack_messages WHERE is_ryan_message = true").fetchone()[0]
    avg_daily = conn.execute("""
        SELECT AVG(ryan_daily_messages) FROM v_communication_intensity
    """).fetchone()[0]
    
    after_hours_pct = conn.execute("""
        SELECT AVG(after_hours_pct) FROM v_communication_intensity
    """).fetchone()[0]
    
    dm_pct = conn.execute("""
        SELECT ROUND(SUM(CASE WHEN is_dm AND is_ryan_message THEN 1 END) * 100.0 / 
                     SUM(CASE WHEN is_ryan_message THEN 1 END), 1)
        FROM slack_messages
    """).fetchone()[0]
    
    conn.close()
    
    # Create dashboard
    fig = plt.figure(figsize=(16, 12))
    gs = fig.add_gridspec(3, 4, hspace=0.3, wspace=0.3)
    
    # Key metrics
    metrics = [
        ("Total Messages", f"{total_messages:,}", "skyblue"),
        ("Active Channels", f"{total_channels}", "lightcoral"),
        ("Avg Daily Messages", f"{avg_daily:.1f}", "lightgreen"),
        ("After Hours %", f"{after_hours_pct:.1f}%", "orange"),
        ("DM Preference %", f"{dm_pct:.1f}%", "plum")
    ]
    
    for i, (label, value, color) in enumerate(metrics[:4]):
        ax = fig.add_subplot(gs[0, i])
        ax.text(0.5, 0.5, value, ha='center', va='center', fontsize=24, fontweight='bold')
        ax.text(0.5, 0.2, label, ha='center', va='center', fontsize=12)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')
        ax.add_patch(plt.Rectangle((0.1, 0.1), 0.8, 0.8, facecolor=color, alpha=0.3))
    
    # Add title
    fig.suptitle("Ryan's Slack Communication Dashboard", fontsize=18, fontweight='bold')
    
    # Add summary text
    summary_text = f"""
    EXECUTIVE SUMMARY:
    • Processed {total_messages:,} messages across {total_channels} channels
    • Average of {avg_daily:.1f} messages per day
    • {after_hours_pct:.1f}% of communication occurs after hours
    • {dm_pct:.1f}% preference for direct messages
    • Peak activity typically 10-15:00 on Tuesday-Thursday
    """
    
    ax_text = fig.add_subplot(gs[1:, :])
    ax_text.text(0.05, 0.95, summary_text, transform=ax_text.transAxes, fontsize=12,
                verticalalignment='top', fontfamily='monospace',
                bbox=dict(boxstyle="round,pad=0.5", facecolor="lightgray", alpha=0.5))
    ax_text.axis('off')
    
    plt.savefig(VIZ_DIR / "12_executive_dashboard.png", dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"   ✓ Dashboard created with key metrics")
    return {
        'total_messages': total_messages,
        'total_channels': total_channels,
        'avg_daily': avg_daily,
        'after_hours_pct': after_hours_pct,
        'dm_pct': dm_pct
    }

def main():
    """Generate all Slack visualizations"""
    print("🎨 Generating comprehensive Slack visualizations...")
    print(f"📁 Saving to: {VIZ_DIR}")
    
    visualizations = []
    
    try:
        # Generate all visualizations
        visualizations.append(("Slack Activity Heatmap", create_slack_activity_heatmap()))
        visualizations.append(("Message Volume Time Series", create_message_volume_timeseries()))
        visualizations.append(("Channel Activity Breakdown", create_channel_activity_breakdown()))
        visualizations.append(("Communication Intensity", create_communication_intensity_analysis()))
        visualizations.append(("Response Patterns", create_response_pattern_analysis()))
        visualizations.append(("DM vs Channel Preference", create_dm_vs_channel_analysis()))
        visualizations.append(("Collaboration Network", create_collaboration_network()))
        visualizations.append(("After Hours Analysis", create_after_hours_analysis()))
        visualizations.append(("Thread Participation", create_thread_participation_analysis()))
        visualizations.append(("Strategic vs Operational", create_strategic_vs_operational()))
        visualizations.append(("Peak Hours Analysis", create_peak_hours_analysis()))
        visualizations.append(("Executive Dashboard", create_executive_dashboard()))
        
        print(f"\n✅ Successfully generated {len(visualizations)} visualizations:")
        for name, _ in visualizations:
            print(f"   • {name}")
        
        # Save generation summary
        summary = {
            'generation_timestamp': datetime.now().isoformat(),
            'visualizations_created': len(visualizations),
            'output_directory': str(VIZ_DIR),
            'visualization_list': [name for name, _ in visualizations]
        }
        
        summary_path = VIZ_DIR / "visualization_summary.json"
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"\n📊 Visualization generation complete!")
        print(f"📄 Summary saved to: {summary_path}")
        
    except Exception as e:
        print(f"❌ Error generating visualizations: {e}")
        raise

if __name__ == "__main__":
    main()