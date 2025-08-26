#!/usr/bin/env python3
"""
Simple Collection Status Dashboard
Standalone dashboard that shows collection status without auth system dependencies

Usage:
    python tools/simple_dashboard.py
    python tools/simple_dashboard.py --compact
"""

import os
import json
from pathlib import Path
from datetime import datetime
import click


@click.command()
@click.option('--compact', '-c', is_flag=True, help='Show compact view')
def main(compact):
    """Simple Collection Status Dashboard"""
    
    base_dir = Path(os.environ.get('AICOS_BASE_DIR', '.'))
    
    if compact:
        _show_compact_status(base_dir)
    else:
        _show_full_status(base_dir)


def _show_compact_status(base_dir: Path):
    """Show compact status"""
    
    click.echo("🎯 " + click.style("AI CoS Quick Status", fg='cyan', bold=True))
    
    # Check authentication files
    keys_db = base_dir / 'src' / 'core' / 'encrypted_keys.db'
    oauth_file = base_dir / 'data' / 'auth' / 'token.pickle'
    
    slack_auth = "✅" if keys_db.exists() else "❌"
    google_auth = "✅" if oauth_file.exists() else "❌"
    click.echo(f"Auth: Slack {slack_auth} | Google {google_auth}")
    
    # Check recent collections
    data_dir = base_dir / 'data' / 'raw'
    collectors = ['slack', 'calendar', 'drive', 'employee']
    recent_count = 0
    
    for collector in collectors:
        if _has_recent_data(data_dir / collector):
            recent_count += 1
    
    click.echo(f"Collections: {recent_count}/{len(collectors)} recent")
    
    # Check storage
    total_size = _get_total_size(data_dir)
    click.echo(f"Storage: {total_size:.1f} MB")
    
    # Check summaries
    summaries_dir = base_dir / 'data' / 'processed' / 'digests'
    summary_files = list(summaries_dir.glob('daily-*.json')) if summaries_dir.exists() else []
    summary_status = "✅" if summary_files else "❌"
    click.echo(f"Summaries: {summary_status} ({len(summary_files)} total)")


def _show_full_status(base_dir: Path):
    """Show full status"""
    
    click.echo("🎯 " + click.style("AI Chief of Staff - Collection Status", fg='cyan', bold=True))
    click.echo("=" * 50)
    click.echo(f"Base directory: {base_dir}")
    click.echo(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Authentication
    click.echo(f"\n🔐 Authentication:")
    keys_db = base_dir / 'src' / 'core' / 'encrypted_keys.db'
    oauth_file = base_dir / 'data' / 'auth' / 'token.pickle'
    
    if keys_db.exists():
        size_kb = keys_db.stat().st_size / 1024
        click.echo(f"   ✅ Slack: Encrypted keys database ({size_kb:.1f} KB)")
    else:
        click.echo(f"   ❌ Slack: No encrypted keys database found")
    
    if oauth_file.exists():
        mtime = datetime.fromtimestamp(oauth_file.stat().st_mtime)
        click.echo(f"   ✅ Google: OAuth tokens ({mtime.strftime('%Y-%m-%d %H:%M')})")
    else:
        click.echo(f"   ❌ Google: No OAuth tokens found")
    
    # Collection Status
    click.echo(f"\n📊 Collection Status:")
    data_dir = base_dir / 'data' / 'raw'
    collectors = ['slack', 'calendar', 'drive', 'employee']
    
    for collector in collectors:
        collector_dir = data_dir / collector
        
        if collector == 'employee':
            roster_file = collector_dir / 'roster.json'
            if roster_file.exists():
                mtime = datetime.fromtimestamp(roster_file.stat().st_mtime)
                size_kb = roster_file.stat().st_size / 1024
                click.echo(f"   ✅ {collector.title()}: {mtime.strftime('%Y-%m-%d %H:%M')} ({size_kb:.1f} KB)")
                
                try:
                    with open(roster_file) as f:
                        data = json.load(f)
                        count = len(data.get('employees', []))
                        click.echo(f"       {count} employees in roster")
                except:
                    click.echo(f"       Error reading roster")
            else:
                click.echo(f"   ⚫ {collector.title()}: No data")
        else:
            # Date-based collections
            if collector_dir.exists():
                date_dirs = [d for d in collector_dir.iterdir() if d.is_dir() and d.name.count('-') == 2]
                if date_dirs:
                    latest_dir = max(date_dirs, key=lambda d: d.name)
                    files = list(latest_dir.glob('*.json')) + list(latest_dir.glob('*.jsonl'))
                    
                    if files:
                        total_size = sum(f.stat().st_size for f in files) / (1024 * 1024)
                        click.echo(f"   ✅ {collector.title()}: {latest_dir.name} ({len(files)} files, {total_size:.1f} MB)")
                    else:
                        click.echo(f"   🟡 {collector.title()}: {latest_dir.name} (no data files)")
                else:
                    click.echo(f"   ⚫ {collector.title()}: No collections")
            else:
                click.echo(f"   ⚫ {collector.title()}: Directory not found")
    
    # Storage Summary
    click.echo(f"\n💾 Storage Summary:")
    if data_dir.exists():
        total_size = _get_total_size(data_dir)
        file_count = _get_file_count(data_dir)
        click.echo(f"   Total: {total_size:.1f} MB ({file_count} files)")
        
        # Breakdown by type
        for subdir in ['slack', 'calendar', 'drive', 'employee']:
            subdir_path = data_dir / subdir
            if subdir_path.exists():
                size = _get_total_size(subdir_path)
                count = _get_file_count(subdir_path)
                if size > 0:
                    click.echo(f"   {subdir.title()}: {size:.1f} MB ({count} files)")
    else:
        click.echo(f"   No data directory found")
    
    # Daily Summaries
    click.echo(f"\n📄 Daily Summaries:")
    summaries_dir = base_dir / 'data' / 'processed' / 'digests'
    
    if summaries_dir.exists():
        summary_files = list(summaries_dir.glob('daily-*.json'))
        if summary_files:
            latest_file = max(summary_files, key=lambda f: f.stat().st_mtime)
            mtime = datetime.fromtimestamp(latest_file.stat().st_mtime)
            
            click.echo(f"   ✅ {len(summary_files)} summaries generated")
            click.echo(f"   Latest: {latest_file.name} ({mtime.strftime('%Y-%m-%d %H:%M')})")
        else:
            click.echo(f"   🟡 Directory exists but no summaries found")
    else:
        click.echo(f"   ⚫ No summaries directory")
    
    # Quick Actions
    click.echo(f"\n💡 Quick Actions:")
    
    if not keys_db.exists():
        click.echo(f"   • Set up Slack authentication (encrypted keys needed)")
    
    if not oauth_file.exists():
        click.echo(f"   • Set up Google OAuth: python tools/setup_google_oauth.py")
    
    recent_collections = sum(1 for collector in collectors if _has_recent_data(data_dir / collector))
    if recent_collections < len(collectors):
        click.echo(f"   • Run data collection: python tools/run_collectors.py all")
    
    if not summaries_dir.exists() or len(list(summaries_dir.glob('*.json'))) == 0:
        click.echo(f"   • Generate summary: python tools/daily_summary.py --save")


def _has_recent_data(collector_dir: Path) -> bool:
    """Check if collector has data from last 2 days"""
    if not collector_dir.exists():
        return False
    
    if collector_dir.name == 'employee':
        roster_file = collector_dir / 'roster.json'
        if not roster_file.exists():
            return False
        mtime = datetime.fromtimestamp(roster_file.stat().st_mtime)
        age_hours = (datetime.now() - mtime).total_seconds() / 3600
        return age_hours < 48
    
    # Date-based collections
    date_dirs = [d for d in collector_dir.iterdir() if d.is_dir() and d.name.count('-') == 2]
    if not date_dirs:
        return False
    
    latest_dir = max(date_dirs, key=lambda d: d.name)
    try:
        collection_date = datetime.strptime(latest_dir.name, '%Y-%m-%d')
        age_hours = (datetime.now() - collection_date).total_seconds() / 3600
        return age_hours < 48
    except:
        return False


def _get_total_size(directory: Path) -> float:
    """Get total size of directory in MB"""
    if not directory.exists():
        return 0.0
    
    total_size = 0
    for item in directory.rglob('*'):
        if item.is_file():
            total_size += item.stat().st_size
    
    return total_size / (1024 * 1024)


def _get_file_count(directory: Path) -> int:
    """Get total file count in directory"""
    if not directory.exists():
        return 0
    
    return sum(1 for item in directory.rglob('*') if item.is_file())


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        click.echo("\n⏹️ Dashboard cancelled")
        exit(130)
    except Exception as e:
        click.echo(f"\n❌ Error: {str(e)}")
        exit(1)