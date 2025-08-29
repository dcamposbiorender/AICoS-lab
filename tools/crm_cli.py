#!/usr/bin/env python3
"""
CRM CLI - Personal relationship management tool

This CLI tool demonstrates the micro-CRM functionality by providing commands to:
- Generate comprehensive person dossiers
- View and manage action items/commitments
- Import existing roster and search for people
- Add notes and manage relationships

Built on top of existing SearchDatabase (340K+ records) and PersonResolver infrastructure.
"""

import click
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich.text import Text

# Add project root to Python path
sys.path.append(str(Path(__file__).parent.parent))

from src.people.dossier_generator import DossierGenerator
from src.people.crm_directory import CRMDirectory
from src.people.interaction_manager import InteractionManager
from src.people.models import Note, ActionItem, ActionDirection, ActionStatus

console = Console()


@click.group()
def cli():
    """🤖 AI Chief of Staff CRM - Personal relationship management"""
    pass


@cli.command()
@click.argument('name_or_email')
@click.option('--days', '-d', default=30, help='Days of interaction history')
@click.option('--format', '-f', type=click.Choice(['rich', 'json']), default='rich', help='Output format')
def dossier(name_or_email, days, format):
    """📋 Generate comprehensive dossier for a person"""
    try:
        generator = DossierGenerator()
        
        # Try to resolve name to email
        email = _resolve_person(name_or_email)
        if not email:
            console.print(f"[red]❌ Person not found: {name_or_email}[/red]")
            console.print("💡 Try searching first: [cyan]crm search {name_or_email}[/cyan]")
            return
        
        with console.status(f"Generating dossier for {email}..."):
            dossier_data = generator.generate_dossier(email, interaction_days=days)
        
        if format == 'json':
            click.echo(json.dumps(dossier_data, indent=2))
        else:
            _display_rich_dossier(dossier_data)
            
    except Exception as e:
        console.print(f"[red]❌ Error generating dossier: {e}[/red]")


def _display_rich_dossier(dossier: dict):
    """Display dossier in rich format"""
    profile = dossier['profile']
    quick_stats = dossier['quick_stats']
    
    # Header
    header_text = Text()
    header_text.append(f"{profile['name']}", style="bold blue")
    if profile['title']:
        header_text.append(f" • {profile['title']}", style="dim")
    if profile['company']:
        header_text.append(f" @ {profile['company']}", style="green")
    
    console.print(Panel(header_text, title="👤 Person Profile", expand=False))
    
    # Quick stats
    stats_table = Table.grid(padding=1)
    stats_table.add_column(style="cyan", min_width=20)
    stats_table.add_column()
    
    stats_table.add_row("📊 Interactions:", str(quick_stats['total_interactions']))
    if quick_stats['last_contact']:
        last_contact = datetime.fromisoformat(quick_stats['last_contact'])
        days_ago = (datetime.now() - last_contact).days
        stats_table.add_row("⏰ Last Contact:", f"{days_ago} days ago")
    stats_table.add_row("📝 Action Items:", str(quick_stats['total_action_items']))
    stats_table.add_row("🔥 Overdue Items:", str(quick_stats['overdue_items']))
    stats_table.add_row("📈 Profile Complete:", f"{quick_stats['profile_completeness']}%")
    
    console.print(stats_table)
    
    # Contact info
    if any([profile['email'], profile['phone'], profile['location']]):
        console.print("\n📞 Contact Information:")
        contact_table = Table.grid(padding=1)
        contact_table.add_column(style="dim", min_width=10)
        contact_table.add_column()
        
        contact_table.add_row("Email:", profile['email'])
        if profile['phone']:
            contact_table.add_row("Phone:", profile['phone'])
        if profile['location']:
            contact_table.add_row("Location:", profile['location'])
        if profile['linkedin']:
            contact_table.add_row("LinkedIn:", profile['linkedin'])
        
        console.print(contact_table)
    
    # Background & interests
    if profile['background'] or profile['interests'] or profile['expertise']:
        console.print("\n🎯 Background & Expertise:")
        if profile['background']:
            console.print(f"Background: {profile['background']}")
        if profile['interests']:
            console.print(f"Interests: {', '.join(profile['interests'])}")
        if profile['expertise']:
            console.print(f"Expertise: {', '.join(profile['expertise'])}")
    
    # Action items
    action_summary = dossier['action_items']['summary']
    if action_summary['total_i_owe'] > 0 or action_summary['total_they_owe'] > 0:
        console.print(f"\n⚡ Action Items:")
        
        actions_table = Table()
        actions_table.add_column("Direction", style="cyan")
        actions_table.add_column("Description", style="white")
        actions_table.add_column("Due Date", style="yellow")
        actions_table.add_column("Status", style="green")
        
        # Show I owe items
        for action in dossier['action_items']['i_owe'][:5]:
            due_date = action['due_date'] if action['due_date'] else "No deadline"
            status_style = "red" if action['is_overdue'] else "green"
            actions_table.add_row(
                "→ I owe",
                action['description'][:60] + "..." if len(action['description']) > 60 else action['description'],
                due_date,
                f"[{status_style}]{action['status']}[/{status_style}]"
            )
        
        # Show they owe items
        for action in dossier['action_items']['they_owe'][:5]:
            due_date = action['due_date'] if action['due_date'] else "No deadline"
            status_style = "red" if action['is_overdue'] else "green"
            actions_table.add_row(
                "← They owe",
                action['description'][:60] + "..." if len(action['description']) > 60 else action['description'],
                due_date,
                f"[{status_style}]{action['status']}[/{status_style}]"
            )
        
        console.print(actions_table)
    
    # Recent interactions
    if dossier['recent_interactions']['count'] > 0:
        console.print(f"\n💬 Recent Interactions ({dossier['recent_interactions']['count']} total):")
        
        for interaction in dossier['recent_interactions']['interactions'][:5]:
            timestamp = datetime.fromisoformat(interaction['timestamp'])
            days_ago = (datetime.now() - timestamp).days
            
            # Create interaction summary
            summary_text = Text()
            summary_text.append(f"{days_ago}d ago", style="dim")
            summary_text.append(f" • {interaction['type']}", style="cyan")
            if interaction['channel']:
                summary_text.append(f" in {interaction['channel']}", style="dim")
            summary_text.append(f": {interaction['summary'][:100]}", style="white")
            
            console.print(f"  {summary_text}")
    
    # Communication insights
    comm = dossier.get('communication_insights', {})
    if comm:
        console.print(f"\n📊 Communication Patterns:")
        console.print(f"  Activity Level: {dossier.get('activity_summary', {}).get('activity_level', 'unknown').title()}")
        if 'preferred_channels' in comm:
            channels = list(comm['preferred_channels'].keys())[:3]
            console.print(f"  Preferred Channels: {', '.join(channels)}")
        if 'avg_response_time_hours' in comm:
            console.print(f"  Avg Response Time: {comm['avg_response_time_hours']} hours")
    
    # Notes
    if dossier['notes']:
        console.print(f"\n📝 Notes ({len(dossier['notes'])}):")
        for note in dossier['notes'][:3]:
            timestamp = datetime.fromisoformat(note['timestamp'])
            console.print(f"  • {timestamp.strftime('%Y-%m-%d')}: {note['content'][:100]}")
    
    # Generation metadata
    metadata = dossier['metadata']
    console.print(f"\n[dim]Generated in {metadata['generation_time']:.1f}s at {metadata['generated_at']}[/dim]")


@cli.command()
@click.option('--person', '-p', help='Filter by person email')
@click.option('--status', '-s', default='pending', help='Filter by status (pending, completed, overdue)')
@click.option('--direction', '-dir', type=click.Choice(['i_owe', 'they_owe', 'all']), default='all', help='Direction filter')
def commitments(person, status, direction):
    """⚡ View and manage commitments/action items"""
    try:
        crm = CRMDirectory()
        
        # Build table
        table = Table(title="🎯 Commitments & Action Items")
        table.add_column("Direction", style="cyan", width=12)
        table.add_column("Person", style="magenta", width=25)
        table.add_column("Description", style="white", width=40)
        table.add_column("Due Date", style="yellow", width=12)
        table.add_column("Status", style="green", width=12)
        
        # Get commitments
        all_actions = []
        
        if direction in ['i_owe', 'all']:
            i_owe_actions = crm.get_actions_i_owe()
            for action in i_owe_actions:
                if person and person.lower() not in action.counterparty.lower():
                    continue
                if status != 'all' and action.status.value != status:
                    continue
                all_actions.append(('I owe', action))
        
        if direction in ['they_owe', 'all']:
            they_owe_actions = crm.get_actions_they_owe_me(counterparty=person)
            for action in they_owe_actions:
                if status != 'all' and action.status.value != status:
                    continue
                all_actions.append(('They owe', action))
        
        # Sort by due date
        all_actions.sort(key=lambda x: x[1].due_date if x[1].due_date else datetime.max)
        
        for direction_text, action in all_actions[:50]:  # Limit to 50
            # Format due date
            if action.due_date:
                due_str = action.due_date.strftime('%m/%d')
                if action.is_overdue():
                    due_str = f"[red]{due_str}[/red]"
            else:
                due_str = "No deadline"
            
            # Format status
            status_str = action.status.value
            if action.is_overdue():
                status_str = f"[red]{status_str}[/red]"
            
            # Truncate description
            desc = action.description
            if len(desc) > 40:
                desc = desc[:37] + "..."
            
            table.add_row(
                f"→ {direction_text}" if direction_text == 'I owe' else f"← {direction_text}",
                action.counterparty,
                desc,
                due_str,
                status_str
            )
        
        console.print(table)
        
        if not all_actions:
            console.print("[yellow]No commitments found matching the criteria[/yellow]")
        
    except Exception as e:
        console.print(f"[red]❌ Error retrieving commitments: {e}[/red]")


@cli.command()
@click.argument('query')
@click.option('--limit', '-l', default=10, help='Maximum results')
def search(query, limit):
    """🔍 Search for people in the CRM"""
    try:
        generator = DossierGenerator()
        results = generator.search_dossiers(query, limit=limit)
        
        if not results:
            console.print(f"[yellow]No people found matching: {query}[/yellow]")
            return
        
        table = Table(title=f"🔍 Search Results: '{query}'")
        table.add_column("Name", style="cyan", width=20)
        table.add_column("Email", style="white", width=30)
        table.add_column("Title", style="green", width=25)
        table.add_column("Company", style="magenta", width=20)
        table.add_column("Last Contact", style="yellow", width=15)
        table.add_column("Actions", style="red", width=10)
        
        for result in results:
            if 'error' in result:
                continue
                
            last_contact = "Never"
            if result['last_contact']:
                last_contact_dt = datetime.fromisoformat(result['last_contact'])
                days_ago = (datetime.now() - last_contact_dt).days
                last_contact = f"{days_ago}d ago"
            
            action_count = result['action_items']['i_owe'] + result['action_items']['they_owe']
            overdue_count = result['action_items']['overdue']
            
            actions_str = str(action_count)
            if overdue_count > 0:
                actions_str = f"[red]{action_count} ({overdue_count} overdue)[/red]"
            
            table.add_row(
                result['name'],
                result['email'],
                result['title'] or "Unknown",
                result['company'] or "Unknown",
                last_contact,
                actions_str
            )
        
        console.print(table)
        console.print(f"\n💡 Get detailed info: [cyan]crm dossier <email>[/cyan]")
        
    except Exception as e:
        console.print(f"[red]❌ Error searching: {e}[/red]")


@cli.command()
@click.argument('email')
@click.argument('note_content')
@click.option('--source', '-s', default='manual', help='Note source')
@click.option('--tags', '-t', help='Comma-separated tags')
def add_note(email, note_content, source, tags):
    """📝 Add a note to a person's profile"""
    try:
        crm = CRMDirectory()
        
        # Create note
        note = Note(
            author="cli_user",
            content=note_content,
            source=source,
            tags=tags.split(',') if tags else []
        )
        
        success = crm.add_note(email, note)
        
        if success:
            console.print(f"[green]✅ Note added to {email}[/green]")
        else:
            console.print(f"[red]❌ Failed to add note. Person not found: {email}[/red]")
            
    except Exception as e:
        console.print(f"[red]❌ Error adding note: {e}[/red]")


@cli.command()
def import_roster():
    """📥 Import existing employee roster from PersonResolver"""
    try:
        crm = CRMDirectory()
        
        with console.status("Importing employee roster..."):
            imported = crm.enrich_from_resolver()
        
        console.print(f"[green]✅ Imported {imported} people from existing roster[/green]")
        
        # Show stats
        stats = crm.get_stats()
        console.print(f"📊 Total people in CRM: {stats['total_people']}")
        console.print(f"📝 Total notes: {stats['total_notes']}")
        console.print(f"⚡ Total action items: {stats['total_actions']}")
        
    except Exception as e:
        console.print(f"[red]❌ Error importing roster: {e}[/red]")


@cli.command()
def stats():
    """📊 Show CRM statistics and health"""
    try:
        crm = CRMDirectory()
        stats = crm.get_stats()
        
        # Create stats display
        stats_table = Table(title="📊 CRM Statistics", show_header=False)
        stats_table.add_column("Metric", style="cyan", width=30)
        stats_table.add_column("Value", style="white", width=15)
        
        stats_table.add_row("👥 Total People", str(stats['total_people']))
        stats_table.add_row("📝 Total Notes", str(stats['total_notes']))
        stats_table.add_row("⚡ Total Action Items", str(stats['total_actions']))
        stats_table.add_row("→ Actions I Owe", str(stats['actions_i_owe']))
        stats_table.add_row("← Actions They Owe", str(stats['actions_they_owe']))
        stats_table.add_row("🔥 Overdue Actions", str(stats['overdue_actions']))
        stats_table.add_row("👥 People with Notes", str(stats['people_with_notes']))
        stats_table.add_row("🤝 People with Actions", str(stats['people_with_actions']))
        stats_table.add_row("💬 Total Interactions", str(stats['total_interactions']))
        stats_table.add_row("🔗 Total Relationships", str(stats['total_relationships']))
        
        console.print(stats_table)
        
        # Show health indicators
        console.print("\n🏥 System Health:")
        health_items = []
        
        if stats['total_people'] > 0:
            health_items.append("[green]✅ CRM populated with people[/green]")
        else:
            health_items.append("[red]❌ No people in CRM - run 'import-roster'[/red]")
        
        if stats['overdue_actions'] == 0:
            health_items.append("[green]✅ No overdue action items[/green]")
        else:
            health_items.append(f"[yellow]⚠️  {stats['overdue_actions']} overdue action items[/yellow]")
        
        engagement_ratio = stats['people_with_notes'] / max(stats['total_people'], 1)
        if engagement_ratio > 0.1:
            health_items.append("[green]✅ Good engagement with notes[/green]")
        else:
            health_items.append("[yellow]⚠️  Low engagement - consider adding more notes[/yellow]")
        
        for item in health_items:
            console.print(f"  {item}")
            
    except Exception as e:
        console.print(f"[red]❌ Error getting stats: {e}[/red]")


def _resolve_person(name_or_email: str) -> Optional[str]:
    """Resolve a name or email to an email address"""
    if '@' in name_or_email:
        return name_or_email
    
    # Search for person by name
    try:
        crm = CRMDirectory()
        results = crm.search_people(name_or_email)
        
        if results:
            return results[0].email
        
        return None
        
    except Exception:
        return None


if __name__ == "__main__":
    cli()