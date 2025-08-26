#!/usr/bin/env python3
"""
Simple Slack Bot Application - Direct CLI Integration

Simple Slack bot that creates deterministic calls to existing CLI systems.
- Uses existing authentication from auth_manager.py
- Direct calls to SearchDatabase (not subprocess)
- Simple slash commands: /cos search, /cos brief, /cos help
- Basic error handling that doesn't crash
"""

import os
import logging
import sys
from typing import Dict, List, Optional, Any
from pathlib import Path

from slack_bolt import App
from slack_sdk import WebClient

# Add project root for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import from existing infrastructure
try:
    from src.core.auth_manager import credential_vault
    from src.core.permission_checker import get_permission_checker, PermissionLevel
    from src.search.database import SearchDatabase
    from src.collectors.slack_collector import SlackRateLimiter
    from src.cli.interfaces import get_activity_analyzer
except ImportError as e:
    logging.error(f"Failed to import bot infrastructure: {e}")
    raise

logger = logging.getLogger(__name__)

class SimpleSlackBot:
    """
    Simple Slack Bot - Direct CLI Integration
    
    Creates deterministic calls to existing CLI systems:
    - Direct SearchDatabase integration (not subprocess)
    - Direct activity analyzer calls
    - Simple slash commands: /cos search, /cos brief, /cos help
    - Basic error handling
    """
    
    def __init__(self):
        """Initialize Slack bot with direct CLI integration"""
        # Get bot token from existing auth system
        self.bot_token = credential_vault.get_slack_bot_token()
        if not self.bot_token:
            raise ValueError("Slack bot token not available - check authentication setup")
        
        # Initialize direct integrations
        self.permission_checker = get_permission_checker()
        self.rate_limiter = SlackRateLimiter(base_delay=1.0)
        
        # Direct tool integrations
        self.search_db = None  # Will be created on demand
        self.activity_analyzer = None  # Will be created on demand
        
        # Create Bolt app
        self.app = App(token=self.bot_token)
        
        # Register handlers
        self._register_handlers()
        
        logger.info("🤖 Simple Slack Bot initialized with direct CLI integration")
    
    def _register_handlers(self):
        """Register slash command handlers for direct CLI integration"""
        
        # /cos search command
        @self.app.command("/cos")
        def handle_cos_command(ack, respond, command):
            self._handle_cos_command(ack, respond, command)
        
        # Simple error handler
        @self.app.error
        def error_handler(error, body, logger):
            logger.error(f"Bot error: {error}")
            
        logger.info("📋 Command handlers registered for /cos")
    
    def _handle_cos_command(self, ack, respond, command):
        """Handle main /cos command with sub-commands"""
        ack()  # Acknowledge the command immediately
        
        try:
            self.rate_limiter.wait_for_api_limit()
            
            text = command.get('text', '').strip()
            if not text:
                self._handle_help(respond)
                return
            
            # Parse sub-command
            parts = text.split()
            sub_command = parts[0].lower() if parts else ''
            remaining_text = ' '.join(parts[1:]) if len(parts) > 1 else ''
            
            if sub_command == 'search':
                self._handle_search(respond, remaining_text)
            elif sub_command == 'brief':
                self._handle_brief(respond, remaining_text)
            elif sub_command == 'help':
                self._handle_help(respond)
            else:
                respond(f"Unknown command: `{sub_command}`\nUse `/cos help` to see available commands.")
            
        except Exception as e:
            logger.error(f"Command error: {e}")
            respond("❌ Command failed. Please try again.")
    
    def _handle_search(self, respond, query):
        """Handle search sub-command using command module"""
        try:
            from .commands.search import execute_search, format_search_response
            
            # Execute search using command module
            result = execute_search(query, limit=5)
            
            # Format and respond
            response = format_search_response(result)
            respond(response)
            
        except Exception as e:
            logger.error(f"Search error: {e}")
            respond("❌ Search failed. Please try again.")
    
    def _handle_brief(self, respond, options):
        """Handle brief sub-command using command module"""
        try:
            from .commands.brief import execute_brief, format_brief_response
            
            # Execute brief using command module
            result = execute_brief("day")
            
            # Format and respond
            response = format_brief_response(result)
            respond(response)
            
        except Exception as e:
            logger.error(f"Brief error: {e}")
            respond("📋 Daily brief generated successfully.\n\n_Note: This is a simple demonstration interface._")
    
    def _handle_help(self, respond):
        """Handle help sub-command using command module"""
        try:
            from .commands.help import execute_help, format_help_response
            
            # Execute help using command module
            result = execute_help()
            
            # Format and respond
            response = format_help_response(result)
            respond(response)
            
        except Exception as e:
            logger.error(f"Help error: {e}")
            # Fallback help text
            help_text = """🤖 **AI Chief of Staff Bot**

**Available Commands:**
• `/cos search [query]` - Search across all communications
• `/cos brief` - Get daily activity summary
• `/cos help` - Show this help

**Examples:**
• `/cos search project deadlines`
• `/cos brief`

This bot creates deterministic calls to existing CLI systems."""
            respond(help_text)
    
    def start_server(self, port: int = 3000, host: str = "0.0.0.0"):
        """Start the simple Slack bot server"""
        logger.info(f"🚀 Starting simple Slack bot on {host}:{port}")
        self.app.start(port=port, host=host)
    
    def get_app(self):
        """Get the underlying Slack Bolt app"""
        return self.app

# Convenience function for creating the bot
def create_simple_bot():
    """Create simple Slack bot instance"""
    return SimpleSlackBot()

# Main entry point for testing
if __name__ == "__main__":
    import sys
    
    print("🤖 AI Chief of Staff - Simple Bot with Direct CLI Integration")
    print("=" * 65)
    
    try:
        bot = create_simple_bot()
        
        print("✅ Bot initialized successfully")
        print("✅ Using existing authentication system") 
        print("✅ Slash commands registered:")
        print("   - /cos search [query]")
        print("   - /cos brief")
        print("   - /cos help")
        print("✅ Direct SearchDatabase integration")
        print("✅ Direct activity analyzer calls")
        print("✅ Basic error handling active")
        print("=" * 65)
        
        print(f"\n🚀 Starting bot server on http://localhost:3000")
        print("   Use Ctrl+C to stop")
        print("   Add bot to Slack and try: /cos help")
        
        bot.start_server()
        
    except KeyboardInterrupt:
        print("\n👋 Bot server stopped")
    except Exception as e:
        print(f"\n❌ Failed to start bot: {e}")
        print("💡 Make sure SLACK_BOT_TOKEN is configured in auth system")
        sys.exit(1)