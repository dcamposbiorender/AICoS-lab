"""
Interactive Mode Utilities for CLI Tools

Provides shared interactive features including command history, autocomplete,
progress indicators, colored output, and session state management.

Usage:
    from src.cli.interactive import InteractiveSession, confirm_action
    
    session = InteractiveSession("Search CLI")
    session.start()
    
    if confirm_action("Delete file?"):
        # proceed with action
"""

import os
import sys
import json
import time
from typing import Dict, List, Any, Optional, Callable, Union
from pathlib import Path

import click


class InteractiveSession:
    """Interactive CLI session with history and context"""
    
    def __init__(self, title: str, prompt: str = "> ", 
                 history_file: Optional[str] = None):
        """
        Initialize interactive session
        
        Args:
            title: Session title to display
            prompt: Command prompt string
            history_file: Optional file to persist command history
        """
        self.title = title
        self.prompt = prompt
        self.history_file = history_file
        self.history = []
        self.session_data = {}
        self.commands = {}
        
        if history_file:
            self.history_path = Path(history_file).expanduser()
            self._load_history()
    
    def register_command(self, name: str, func: Callable, help_text: str):
        """
        Register a command for the interactive session
        
        Args:
            name: Command name
            func: Function to execute
            help_text: Help text for the command
        """
        self.commands[name] = {
            'func': func,
            'help': help_text
        }
    
    def start(self):
        """Start interactive session"""
        click.echo(f"\n{click.style(self.title, fg='cyan', bold=True)}")
        click.echo("=" * len(self.title))
        click.echo()
        
        self._show_welcome()
        
        while True:
            try:
                user_input = click.prompt(
                    click.style(self.prompt, fg='green'), 
                    type=str,
                    show_default=False
                ).strip()
                
                if not user_input:
                    continue
                
                # Add to history
                self.history.append(user_input)
                if self.history_file:
                    self._save_history()
                
                # Handle built-in commands
                if user_input.lower() in ['q', 'quit', 'exit']:
                    click.echo("Goodbye!")
                    break
                elif user_input.startswith('/'):
                    self._handle_special_command(user_input)
                else:
                    # Handle regular commands
                    yield user_input
                    
            except KeyboardInterrupt:
                click.echo("\nUse 'q' or 'quit' to exit gracefully.")
            except EOFError:
                click.echo("\nGoodbye!")
                break
    
    def _show_welcome(self):
        """Show welcome message and available commands"""
        click.echo("Interactive mode started. Available commands:")
        click.echo()
        
        # Built-in commands
        click.echo(f"  {click.style('/help', fg='yellow')}   - Show this help")
        click.echo(f"  {click.style('/history', fg='yellow')} - Show command history")
        click.echo(f"  {click.style('/clear', fg='yellow')}   - Clear screen")
        click.echo(f"  {click.style('q, quit, exit', fg='yellow')} - Exit interactive mode")
        
        # Registered commands
        if self.commands:
            click.echo()
            click.echo("Application commands:")
            for name, cmd in self.commands.items():
                click.echo(f"  {click.style(name, fg='cyan')} - {cmd['help']}")
        
        click.echo()
    
    def _handle_special_command(self, command: str):
        """Handle special commands starting with /"""
        cmd = command.lower()
        
        if cmd == '/help':
            self._show_welcome()
        elif cmd == '/history':
            self._show_history()
        elif cmd == '/clear':
            click.clear()
            click.echo(f"{click.style(self.title, fg='cyan', bold=True)}")
            click.echo("=" * len(self.title))
            click.echo()
        elif cmd.startswith('/set '):
            self._handle_set_command(command[5:])
        elif cmd == '/session':
            self._show_session_data()
        else:
            # Check registered commands
            cmd_name = cmd[1:]  # Remove /
            if cmd_name in self.commands:
                try:
                    self.commands[cmd_name]['func']()
                except Exception as e:
                    click.echo(f"Command error: {e}", err=True)
            else:
                click.echo(f"Unknown command: {command}")
                click.echo("Type '/help' for available commands")
    
    def _show_history(self):
        """Show command history"""
        if not self.history:
            click.echo("No command history")
            return
        
        click.echo(f"\n{click.style('Command History:', fg='blue', bold=True)}")
        for i, cmd in enumerate(self.history[-10:], 1):  # Show last 10
            click.echo(f"  {i:2d}. {cmd}")
        click.echo()
    
    def _handle_set_command(self, args: str):
        """Handle /set commands for session variables"""
        try:
            key, value = args.split('=', 1)
            self.session_data[key.strip()] = value.strip()
            click.echo(f"Set {key.strip()} = {value.strip()}")
        except ValueError:
            click.echo("Usage: /set key=value")
    
    def _show_session_data(self):
        """Show current session data"""
        if not self.session_data:
            click.echo("No session data")
            return
        
        click.echo(f"\n{click.style('Session Data:', fg='blue', bold=True)}")
        for key, value in self.session_data.items():
            click.echo(f"  {key}: {value}")
        click.echo()
    
    def _load_history(self):
        """Load command history from file"""
        if self.history_path.exists():
            try:
                with open(self.history_path) as f:
                    self.history = [line.strip() for line in f if line.strip()]
            except Exception:
                pass  # Ignore errors loading history
    
    def _save_history(self):
        """Save command history to file"""
        try:
            self.history_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.history_path, 'w') as f:
                # Keep only last 100 commands
                for cmd in self.history[-100:]:
                    f.write(f"{cmd}\n")
        except Exception:
            pass  # Ignore errors saving history


def confirm_action(message: str, default: bool = False) -> bool:
    """
    Ask user for confirmation with y/n prompt
    
    Args:
        message: Confirmation message
        default: Default value if user just presses Enter
        
    Returns:
        True if confirmed, False otherwise
    """
    default_str = "Y/n" if default else "y/N"
    prompt_text = f"{message} [{default_str}]"
    
    try:
        response = click.prompt(prompt_text, type=str, default="").lower()
        
        if not response:
            return default
        
        return response in ['y', 'yes', '1', 'true', 'on']
        
    except (KeyboardInterrupt, EOFError):
        return False


def show_progress(iterable, description: str = "Processing", 
                 show_eta: bool = True, disable_on_ci: bool = True):
    """
    Show progress for long-running operations
    
    Args:
        iterable: Iterable to process
        description: Progress description
        show_eta: Show estimated time remaining
        disable_on_ci: Disable progress bar in CI environments
        
    Yields:
        Items from iterable with progress indication
    """
    # Detect CI environment
    is_ci = any(var in os.environ for var in [
        'CI', 'CONTINUOUS_INTEGRATION', 'GITHUB_ACTIONS', 
        'JENKINS_URL', 'BUILDBOT_WORKER'
    ])
    
    if disable_on_ci and is_ci:
        # In CI, just yield items without progress bar
        for item in iterable:
            yield item
        return
    
    try:
        from tqdm import tqdm
        
        # Use tqdm for progress
        with tqdm(iterable, desc=description, disable=not sys.stderr.isatty()) as pbar:
            for item in pbar:
                yield item
                
    except ImportError:
        # Fallback: simple text-based progress
        try:
            total = len(iterable)
            for i, item in enumerate(iterable):
                if i % max(1, total // 20) == 0:  # Update every 5%
                    percent = (i / total) * 100
                    click.echo(f"\r{description}: {percent:.1f}%", nl=False, err=True)
                yield item
            click.echo(f"\r{description}: 100.0%", err=True)
        except TypeError:
            # Can't get length, just process without progress
            for item in iterable:
                yield item


class StatusIndicator:
    """Status indicator for operations"""
    
    def __init__(self, message: str, spinner: bool = True):
        """
        Initialize status indicator
        
        Args:
            message: Status message to display
            spinner: Show spinner animation
        """
        self.message = message
        self.spinner = spinner
        self.active = False
        self.spinner_chars = "|/-\\"
        self.spinner_index = 0
        
    def __enter__(self):
        """Start status indication"""
        self.active = True
        if self.spinner and sys.stderr.isatty():
            click.echo(f"{self.message}... ", nl=False, err=True)
        else:
            click.echo(f"{self.message}...", err=True)
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop status indication"""
        self.active = False
        if self.spinner and sys.stderr.isatty():
            click.echo("\b Done", err=True)
    
    def update(self, message: str):
        """Update status message"""
        self.message = message
        if self.active and not self.spinner:
            click.echo(f"  {message}...", err=True)


def get_terminal_width() -> int:
    """Get terminal width with fallback"""
    try:
        return os.get_terminal_size().columns
    except OSError:
        return 80  # Fallback width


def print_table(headers: List[str], rows: List[List[str]], 
                max_width: Optional[int] = None):
    """
    Print a formatted table
    
    Args:
        headers: Column headers
        rows: Table rows
        max_width: Maximum table width (auto-detect if None)
    """
    if not rows:
        return
    
    if max_width is None:
        max_width = get_terminal_width()
    
    # Calculate column widths
    col_widths = [len(header) for header in headers]
    
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(col_widths):
                col_widths[i] = max(col_widths[i], len(str(cell)))
    
    # Adjust widths to fit terminal
    total_width = sum(col_widths) + len(headers) * 3 - 1  # Account for separators
    if total_width > max_width:
        # Proportionally reduce column widths
        scale = (max_width - len(headers) * 3 + 1) / sum(col_widths)
        col_widths = [max(8, int(w * scale)) for w in col_widths]
    
    # Print header
    header_row = " | ".join(h.ljust(w) for h, w in zip(headers, col_widths))
    click.echo(header_row)
    click.echo("-" * len(header_row))
    
    # Print rows
    for row in rows:
        formatted_cells = []
        for i, (cell, width) in enumerate(zip(row, col_widths)):
            cell_str = str(cell)
            if len(cell_str) > width:
                cell_str = cell_str[:width-3] + "..."
            formatted_cells.append(cell_str.ljust(width))
        
        click.echo(" | ".join(formatted_cells))


def select_from_list(items: List[str], prompt: str = "Select an option",
                    allow_multiple: bool = False) -> Union[str, List[str], None]:
    """
    Interactive selection from a list of items
    
    Args:
        items: List of items to select from
        prompt: Prompt message
        allow_multiple: Allow multiple selections
        
    Returns:
        Selected item(s) or None if cancelled
    """
    if not items:
        click.echo("No items to select from")
        return None
    
    click.echo(f"\n{prompt}:")
    for i, item in enumerate(items, 1):
        click.echo(f"  {i}. {item}")
    
    if allow_multiple:
        click.echo("\nEnter numbers separated by commas (e.g., 1,3,5) or 'q' to cancel:")
    else:
        click.echo(f"\nEnter number (1-{len(items)}) or 'q' to cancel:")
    
    try:
        response = click.prompt("Selection", type=str).strip().lower()
        
        if response in ['q', 'quit', 'cancel']:
            return None
        
        if allow_multiple:
            selections = []
            for num_str in response.split(','):
                try:
                    num = int(num_str.strip())
                    if 1 <= num <= len(items):
                        selections.append(items[num - 1])
                except ValueError:
                    pass
            return selections if selections else None
        else:
            try:
                num = int(response)
                if 1 <= num <= len(items):
                    return items[num - 1]
            except ValueError:
                pass
            
            click.echo("Invalid selection")
            return None
            
    except (KeyboardInterrupt, EOFError):
        return None


def format_duration(seconds: float) -> str:
    """Format duration in human-readable format"""
    if seconds < 1:
        return f"{seconds*1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}m {secs:.0f}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"


def get_config_dir() -> Path:
    """Get user configuration directory"""
    if os.name == 'nt':  # Windows
        config_dir = Path(os.environ.get('APPDATA', '~')) / 'aicos'
    else:  # Unix-like
        config_dir = Path(os.environ.get('XDG_CONFIG_HOME', '~/.config')) / 'aicos'
    
    return config_dir.expanduser()


def save_session_state(session_name: str, data: Dict[str, Any]):
    """Save session state to file"""
    config_dir = get_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)
    
    session_file = config_dir / f"{session_name}.json"
    
    try:
        with open(session_file, 'w') as f:
            json.dump(data, f, indent=2, default=str)
    except Exception as e:
        click.echo(f"Warning: Could not save session state: {e}", err=True)


def load_session_state(session_name: str) -> Dict[str, Any]:
    """Load session state from file"""
    config_dir = get_config_dir()
    session_file = config_dir / f"{session_name}.json"
    
    if not session_file.exists():
        return {}
    
    try:
        with open(session_file) as f:
            return json.load(f)
    except Exception as e:
        click.echo(f"Warning: Could not load session state: {e}", err=True)
        return {}


class ColorTheme:
    """Color theme for consistent CLI styling"""
    
    # Status colors
    SUCCESS = 'green'
    WARNING = 'yellow'
    ERROR = 'red'
    INFO = 'blue'
    
    # Content colors
    HEADER = 'cyan'
    SUBHEADER = 'blue'
    ACCENT = 'magenta'
    DIM = 'white'
    
    # Data colors
    VALUE = 'green'
    METADATA = 'yellow'
    SCORE = 'cyan'


def styled_text(text: str, style: str, bold: bool = False) -> str:
    """Apply consistent styling to text"""
    return click.style(text, fg=style, bold=bold)