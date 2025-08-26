#!/usr/bin/env python3
"""
AI Chief of Staff - Collection Status Dashboard
Visual dashboard showing collection status, recent activity, and data health

This tool provides a comprehensive overview of the data collection system
including authentication status, recent collections, and data freshness.

Usage:
    python tools/collection_dashboard.py              # Show full dashboard
    python tools/collection_dashboard.py --compact    # Compact view
    python tools/collection_dashboard.py --json       # JSON output
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime, timedelta, date
from typing import Dict, List, Any, Optional, Tuple
import subprocess

import click

# Add project root to Python path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Auth manager import causes recursion issues, use direct file checking instead

__version__ = "1.0.0"
__author__ = "AI Chief of Staff Dashboard Team"


@click.command()
@click.option('--compact', '-c', is_flag=True, help='Show compact dashboard view')
@click.option('--json', '-j', 'output_json', is_flag=True, help='Output as JSON')
@click.option('--refresh', '-r', is_flag=True, help='Refresh data before showing dashboard')
@click.version_option(version=__version__)
def main(compact, output_json, refresh):
    """AI Chief of Staff - Collection Status Dashboard
    
    Shows comprehensive status of data collection system including:
    - Authentication status for all services
    - Recent collection activity and data freshness
    - Storage usage and system health
    - Actionable recommendations
    """
    
    if refresh:
        _refresh_status_data()
    
    dashboard_data = _collect_dashboard_data()
    
    if output_json:
        click.echo(json.dumps(dashboard_data, indent=2, default=str))
    elif compact:
        _show_compact_dashboard(dashboard_data)
    else:
        _show_full_dashboard(dashboard_data)


def _refresh_status_data():
    """Refresh status data by running quick checks"""
    click.echo("🔄 Refreshing status data...")
    
    try:
        # Run a quick drive collection to update status
        subprocess.run([
            sys.executable, 
            str(project_root / 'tools' / 'collect_data.py'),
            '--source=drive',
            '--output=archive'
        ], cwd=project_root, capture_output=True, timeout=60)
    except:
        pass  # Ignore errors during refresh


def _collect_dashboard_data() -> Dict[str, Any]:
    """Collect all data needed for the dashboard"""
    
    base_dir = Path(os.environ.get('AICOS_BASE_DIR', '.'))
    
    return {
        'timestamp': datetime.now(),
        'authentication': _get_auth_status(),
        'collections': _get_collection_status(base_dir),
        'storage': _get_storage_status(base_dir),
        'summaries': _get_summary_status(base_dir),
        'recommendations': _get_recommendations(),
        'system_health': _get_system_health(base_dir)
    }


def _get_auth_status() -> Dict[str, Any]:
    """Get authentication status for all services"""
    
    # Slack authentication - use safe file checking
    slack_auth = False
    slack_user = False
    try:
        # Check for encrypted keys database
        base_dir = Path(os.environ.get('AICOS_BASE_DIR', '.'))
        keys_db = base_dir / 'src' / 'core' / 'encrypted_keys.db'
        slack_auth = keys_db.exists()  # Assume Slack keys exist if DB exists
        slack_user = slack_auth
    except:
        pass
    
    # Google authentication
    google_auth = False
    google_expired = True
    try:
        # Check for Google OAuth token file
        token_file = Path(os.environ.get('AICOS_BASE_DIR', '.')) / 'data' / 'auth' / 'token.pickle'
        google_auth = token_file.exists()
        google_expired = False  # Assume valid if file exists
    except:
        pass
    
    return {
        'slack': {
            'bot_token': slack_auth,
            'user_token': slack_user,
            'status': 'ready' if slack_auth else 'missing_tokens'
        },
        'google': {
            'oauth_configured': google_auth,
            'expired': google_expired,
            'status': 'ready' if google_auth and not google_expired else 
                     'expired' if google_auth and google_expired else 'not_configured'
        },
        'overall_status': 'ready' if (slack_auth and google_auth and not google_expired) else 'partial'
    }


def _get_collection_status(base_dir: Path) -> Dict[str, Any]:
    """Get status of recent collections"""
    
    data_dir = base_dir / 'data' / 'raw'
    collectors = ['slack', 'calendar', 'drive', 'employee']
    status = {}
    
    for collector in collectors:
        collector_status = {
            'name': collector,
            'last_collection': None,
            'data_count': 0,
            'data_size_mb': 0,
            'freshness_hours': None,
            'status': 'no_data'
        }
        
        collector_dir = data_dir / collector
        
        if collector == 'employee':
            # Employee collector stores in roster.json
            roster_file = collector_dir / 'roster.json'
            if roster_file.exists():
                mtime = datetime.fromtimestamp(roster_file.stat().st_mtime)
                collector_status['last_collection'] = mtime
                collector_status['freshness_hours'] = (datetime.now() - mtime).total_seconds() / 3600
                collector_status['data_size_mb'] = roster_file.stat().st_size / (1024 * 1024)
                
                try:
                    with open(roster_file) as f:
                        data = json.load(f)
                        collector_status['data_count'] = len(data.get('employees', []))
                except:
                    collector_status['data_count'] = 0
                
                collector_status['status'] = 'recent' if collector_status['freshness_hours'] < 24 else 'stale'
        else:
            # Date-based collections
            if collector_dir.exists():
                date_dirs = [d for d in collector_dir.iterdir() if d.is_dir() and d.name.count('-') == 2]
                if date_dirs:
                    latest_dir = max(date_dirs, key=lambda d: d.name)
                    
                    try:
                        collection_date = datetime.strptime(latest_dir.name, '%Y-%m-%d')
                        collector_status['last_collection'] = collection_date
                        collector_status['freshness_hours'] = (datetime.now() - collection_date).total_seconds() / 3600
                    except:
                        pass
                    
                    # Count files and size
                    files = list(latest_dir.glob('*.json')) + list(latest_dir.glob('*.jsonl'))
                    collector_status['data_count'] = len(files)
                    if files:
                        total_size = sum(f.stat().st_size for f in files)
                        collector_status['data_size_mb'] = total_size / (1024 * 1024)
                        
                        # Determine freshness status
                        if collector_status['freshness_hours'] is not None:
                            if collector_status['freshness_hours'] < 24:
                                collector_status['status'] = 'recent'
                            elif collector_status['freshness_hours'] < 72:
                                collector_status['status'] = 'stale'
                            else:
                                collector_status['status'] = 'very_stale'
        
        status[collector] = collector_status
    
    return status


def _get_storage_status(base_dir: Path) -> Dict[str, Any]:
    """Get storage usage information"""
    
    data_dir = base_dir / 'data'
    
    def get_dir_size(directory: Path) -> Tuple[int, int]:
        """Get directory size and file count"""
        if not directory.exists():
            return 0, 0
        
        total_size = 0
        file_count = 0
        
        for item in directory.rglob('*'):
            if item.is_file():
                total_size += item.stat().st_size
                file_count += 1
        
        return total_size, file_count
    
    raw_size, raw_files = get_dir_size(data_dir / 'raw')
    processed_size, processed_files = get_dir_size(data_dir / 'processed')
    
    return {
        'raw_data': {
            'size_mb': raw_size / (1024 * 1024),
            'file_count': raw_files
        },
        'processed_data': {
            'size_mb': processed_size / (1024 * 1024),
            'file_count': processed_files
        },
        'total_size_mb': (raw_size + processed_size) / (1024 * 1024),
        'total_files': raw_files + processed_files
    }


def _get_summary_status(base_dir: Path) -> Dict[str, Any]:
    """Get daily summary generation status"""
    
    summaries_dir = base_dir / 'data' / 'processed' / 'digests'
    
    status = {
        'directory_exists': summaries_dir.exists(),
        'summary_count': 0,
        'latest_summary': None,
        'latest_summary_age_hours': None,
        'status': 'no_summaries'
    }
    
    if summaries_dir.exists():
        summary_files = list(summaries_dir.glob('daily-*.json'))
        status['summary_count'] = len(summary_files)
        
        if summary_files:
            latest_file = max(summary_files, key=lambda f: f.stat().st_mtime)
            mtime = datetime.fromtimestamp(latest_file.stat().st_mtime)
            
            status['latest_summary'] = latest_file.name
            status['latest_summary_age_hours'] = (datetime.now() - mtime).total_seconds() / 3600
            
            if status['latest_summary_age_hours'] < 24:
                status['status'] = 'current'
            elif status['latest_summary_age_hours'] < 72:
                status['status'] = 'stale'
            else:
                status['status'] = 'very_stale'
    
    return status


def _get_recommendations() -> List[Dict[str, str]]:
    """Get actionable recommendations based on current status"""
    
    recommendations = []
    dashboard_data = _collect_dashboard_data()
    
    # Authentication recommendations
    auth = dashboard_data['authentication']
    if not auth['slack']['bot_token']:
        recommendations.append({
            'priority': 'high',
            'category': 'authentication',
            'title': 'Configure Slack Authentication',
            'description': 'Slack bot token not found. Set up Slack tokens to enable message collection.',
            'action': 'Verify Slack tokens are stored in encrypted database'
        })
    
    if not auth['google']['oauth_configured']:
        recommendations.append({
            'priority': 'high', 
            'category': 'authentication',
            'title': 'Configure Google OAuth',
            'description': 'Google OAuth not configured. Set up to enable Drive and Calendar collection.',
            'action': 'Run: python tools/setup_google_oauth.py'
        })
    
    if auth['google']['expired']:
        recommendations.append({
            'priority': 'medium',
            'category': 'authentication', 
            'title': 'Refresh Google OAuth',
            'description': 'Google OAuth tokens have expired.',
            'action': 'Run: python tools/setup_google_oauth.py'
        })
    
    # Collection recommendations
    collections = dashboard_data['collections']
    stale_collectors = [name for name, data in collections.items() 
                       if data['status'] in ['stale', 'very_stale']]
    
    if stale_collectors:
        recommendations.append({
            'priority': 'medium',
            'category': 'collection',
            'title': 'Stale Data Detected',
            'description': f'Data is stale for: {", ".join(stale_collectors)}',
            'action': 'Run: python tools/run_collectors.py all'
        })
    
    no_data_collectors = [name for name, data in collections.items() 
                         if data['status'] == 'no_data']
    
    if no_data_collectors:
        recommendations.append({
            'priority': 'low',
            'category': 'collection',
            'title': 'No Data Collected',
            'description': f'No data found for: {", ".join(no_data_collectors)}',
            'action': 'Check authentication and run collectors'
        })
    
    # Summary recommendations
    summaries = dashboard_data['summaries']
    if summaries['status'] == 'no_summaries':
        recommendations.append({
            'priority': 'low',
            'category': 'summaries',
            'title': 'Generate Daily Summaries',
            'description': 'No daily summaries found. Generate summaries from collected data.',
            'action': 'Run: python tools/daily_summary.py --save'
        })
    
    return recommendations


def _get_system_health(base_dir: Path) -> Dict[str, Any]:
    """Get overall system health indicators"""
    
    dashboard_data = _collect_dashboard_data()
    
    # Count health indicators
    auth_ready = dashboard_data['authentication']['overall_status'] == 'ready'
    
    collections = dashboard_data['collections']
    recent_collections = sum(1 for data in collections.values() if data['status'] == 'recent')
    total_collections = len(collections)
    
    storage = dashboard_data['storage']
    has_data = storage['total_files'] > 0
    
    summaries = dashboard_data['summaries']
    summaries_current = summaries['status'] == 'current'
    
    # Calculate health score (0-100)
    health_score = 0
    if auth_ready:
        health_score += 30
    if recent_collections > 0:
        health_score += 30 * (recent_collections / total_collections)
    if has_data:
        health_score += 20
    if summaries_current:
        health_score += 20
    
    # Determine overall status
    if health_score >= 80:
        status = 'excellent'
    elif health_score >= 60:
        status = 'good'
    elif health_score >= 40:
        status = 'fair'
    else:
        status = 'poor'
    
    return {
        'health_score': int(health_score),
        'status': status,
        'indicators': {
            'authentication_ready': auth_ready,
            'recent_collections': recent_collections,
            'total_collections': total_collections,
            'has_data': has_data,
            'summaries_current': summaries_current
        }
    }


def _show_full_dashboard(data: Dict[str, Any]):
    """Show full dashboard view"""
    
    click.echo("🎯 " + click.style("AI Chief of Staff - Collection Dashboard", fg='cyan', bold=True))
    click.echo("=" * 60)
    click.echo(f"Last updated: {data['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
    
    # System Health Overview
    health = data['system_health']
    health_color = {'excellent': 'green', 'good': 'blue', 'fair': 'yellow', 'poor': 'red'}[health['status']]
    click.echo(f"\n💊 System Health: {click.style(health['status'].title(), fg=health_color, bold=True)} ({health['health_score']}/100)")
    
    # Authentication Status
    click.echo(f"\n🔐 Authentication Status:")
    auth = data['authentication']
    
    slack_status = "✅ Ready" if auth['slack']['status'] == 'ready' else "❌ Missing tokens"
    click.echo(f"   Slack: {slack_status}")
    if auth['slack']['user_token']:
        click.echo(f"          Bot + User tokens available")
    elif auth['slack']['bot_token']:
        click.echo(f"          Bot token only")
    
    google_status_map = {'ready': '✅ Ready', 'expired': '⚠️ Expired', 'not_configured': '❌ Not configured'}
    google_status = google_status_map.get(auth['google']['status'], '❓ Unknown')
    click.echo(f"   Google: {google_status}")
    
    # Collection Status
    click.echo(f"\n📊 Data Collections:")
    collections = data['collections']
    
    for name, cdata in collections.items():
        status_icon = {
            'recent': '🟢',
            'stale': '🟡', 
            'very_stale': '🔴',
            'no_data': '⚫'
        }.get(cdata['status'], '❓')
        
        click.echo(f"   {status_icon} {name.title()}:")
        
        if cdata['last_collection']:
            last_str = cdata['last_collection'].strftime('%Y-%m-%d %H:%M')
            click.echo(f"      Last collection: {last_str}")
            
            if cdata['freshness_hours'] is not None:
                hours = int(cdata['freshness_hours'])
                if hours < 1:
                    freshness = "< 1 hour ago"
                elif hours < 24:
                    freshness = f"{hours} hours ago"
                else:
                    days = hours // 24
                    freshness = f"{days} day{'s' if days != 1 else ''} ago"
                click.echo(f"      Freshness: {freshness}")
        else:
            click.echo(f"      Last collection: Never")
        
        if cdata['data_count'] > 0:
            click.echo(f"      Data: {cdata['data_count']} files, {cdata['data_size_mb']:.1f} MB")
    
    # Storage Status
    click.echo(f"\n💾 Storage Usage:")
    storage = data['storage']
    click.echo(f"   Total: {storage['total_size_mb']:.1f} MB ({storage['total_files']} files)")
    click.echo(f"   Raw data: {storage['raw_data']['size_mb']:.1f} MB")
    click.echo(f"   Processed: {storage['processed_data']['size_mb']:.1f} MB")
    
    # Summary Status
    click.echo(f"\n📄 Daily Summaries:")
    summaries = data['summaries']
    
    if summaries['summary_count'] > 0:
        status_icon = {'current': '🟢', 'stale': '🟡', 'very_stale': '🔴'}.get(summaries['status'], '❓')
        click.echo(f"   {status_icon} {summaries['summary_count']} summaries generated")
        click.echo(f"   Latest: {summaries['latest_summary']}")
        
        if summaries['latest_summary_age_hours']:
            hours = int(summaries['latest_summary_age_hours'])
            if hours < 24:
                age_str = f"{hours} hours old"
            else:
                age_str = f"{hours // 24} days old"
            click.echo(f"   Age: {age_str}")
    else:
        click.echo(f"   ⚫ No summaries generated yet")
    
    # Recommendations
    recommendations = data['recommendations']
    if recommendations:
        click.echo(f"\n💡 Recommendations:")
        
        high_priority = [r for r in recommendations if r['priority'] == 'high']
        medium_priority = [r for r in recommendations if r['priority'] == 'medium']
        low_priority = [r for r in recommendations if r['priority'] == 'low']
        
        for priority, recs in [('🔴 High Priority', high_priority), ('🟡 Medium Priority', medium_priority), ('🟢 Low Priority', low_priority)]:
            if recs:
                click.echo(f"   {priority}:")
                for rec in recs:
                    click.echo(f"   • {rec['title']}")
                    click.echo(f"     {rec['description']}")
                    click.echo(f"     Action: {rec['action']}")
    else:
        click.echo(f"\n💡 Recommendations: All systems running smoothly! 🎉")


def _show_compact_dashboard(data: Dict[str, Any]):
    """Show compact dashboard view"""
    
    click.echo("🎯 " + click.style("AI CoS Dashboard", fg='cyan', bold=True))
    
    # Health overview
    health = data['system_health']
    health_color = {'excellent': 'green', 'good': 'blue', 'fair': 'yellow', 'poor': 'red'}[health['status']]
    click.echo(f"Health: {click.style(health['status'].title(), fg=health_color)} ({health['health_score']}/100)")
    
    # Auth status
    auth = data['authentication']
    slack_icon = "✅" if auth['slack']['status'] == 'ready' else "❌"
    google_icon = "✅" if auth['google']['status'] == 'ready' else "❌"
    click.echo(f"Auth: Slack {slack_icon} | Google {google_icon}")
    
    # Collection overview
    collections = data['collections']
    recent = len([c for c in collections.values() if c['status'] == 'recent'])
    total = len(collections)
    click.echo(f"Collections: {recent}/{total} recent")
    
    # Storage
    storage = data['storage']
    click.echo(f"Storage: {storage['total_size_mb']:.1f} MB ({storage['total_files']} files)")
    
    # Summaries
    summaries = data['summaries']
    summary_status = "✅" if summaries['status'] == 'current' else "❌"
    click.echo(f"Summaries: {summary_status} ({summaries['summary_count']} total)")
    
    # Top recommendation
    recommendations = data['recommendations']
    if recommendations:
        top_rec = next((r for r in recommendations if r['priority'] == 'high'), recommendations[0])
        click.echo(f"💡 Next: {top_rec['action']}")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        click.echo("\n⏹️ Dashboard cancelled by user")
        sys.exit(130)
    except Exception as e:
        click.echo(f"\n❌ Dashboard error: {str(e)}")
        sys.exit(1)