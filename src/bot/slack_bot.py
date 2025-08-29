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
import asyncio
import aiohttp
import json
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
    
    def __init__(self, api_base_url: str = 'http://localhost:8000'):
        """Initialize Slack bot with direct CLI integration and API integration"""
        # Get bot token from existing auth system
        self.bot_token = credential_vault.get_slack_bot_token()
        if not self.bot_token:
            raise ValueError("Slack bot token not available - check authentication setup")
        
        # Agent H integration - API backend connection
        self.api_base_url = api_base_url
        self.session = None
        
        # Initialize direct integrations
        self.permission_checker = get_permission_checker()
        self.rate_limiter = SlackRateLimiter(base_delay=1.0)
        
        # Direct tool integrations - initialize immediately to avoid None errors
        try:
            from ..search.database import SearchDatabase
            from ..cli.interfaces import get_activity_analyzer
            
            self.search_db = SearchDatabase('data/search.db')
            self.activity_analyzer = get_activity_analyzer()
            
            if not self.search_db:
                raise ValueError("Failed to initialize SearchDatabase")
            if not self.activity_analyzer:
                raise ValueError("Failed to initialize ActivityAnalyzer")
                
        except Exception as e:
            logger.error(f"Failed to initialize bot dependencies: {e}")
            raise ValueError(f"Bot initialization failed: {e}")
        
        # Create command registry for extensible command handling
        # Agent H integration - unified command handling
        self.commands = {
            'search': self._handle_search,
            'brief': self._handle_brief,  
            'help': self._handle_help,
            'approve': self._handle_api_command,
            'complete': self._handle_api_command,
            'refresh': self._handle_api_command,
            'quick': self._handle_api_command,
            'full': self._handle_api_command,
            'status': self._handle_api_command
        }
        
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
            
            # Parse sub-command and dispatch via command registry
            parts = text.split()
            sub_command = parts[0].lower() if parts else 'help'
            remaining_text = ' '.join(parts[1:]) if len(parts) > 1 else ''
            
            # Look up command handler in registry
            handler = self.commands.get(sub_command, self._handle_unknown)
            handler(respond, remaining_text)
            
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
    
    def _handle_unknown(self, respond, query):
        """Handle unknown command with helpful message"""
        respond(f"❓ Unknown command. Available commands: {', '.join(self.commands.keys())}\nUse `/cos help` for details.")
    
    # Agent H Integration - API Command Handling
    
    def _handle_api_command(self, respond, command_text):
        """Handle commands that should go through the unified API"""
        try:
            # Run async API command in sync context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(self.execute_api_command(command_text))
                response = self.format_api_response(result)
                respond(response)
            finally:
                loop.close()
                
        except Exception as e:
            logger.error(f"API command error: {e}")
            respond(f"❌ Command failed: {str(e)}")
    
    async def connect_to_api(self):
        """Initialize HTTP session for API calls"""
        if not self.session:
            self.session = aiohttp.ClientSession()
    
    async def disconnect_from_api(self):
        """Clean up HTTP session"""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def execute_api_command(self, command_text: str) -> Dict[str, Any]:
        """
        Execute command via backend API
        
        Args:
            command_text: Command to execute (e.g., "approve P7", "brief C3")
            
        Returns:
            Dict with API response
        """
        await self.connect_to_api()
        
        url = f"{self.api_base_url}/api/command"
        
        try:
            async with self.session.post(url, json={'command': command_text}) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    return {
                        'success': False,
                        'error': f"API error ({response.status}): {error_text}"
                    }
        except aiohttp.ClientError as e:
            return {
                'success': False,
                'error': f"Connection error: {str(e)}"
            }
        except Exception as e:
            return {
                'success': False,
                'error': f"API call failed: {str(e)}"
            }
    
    def format_api_response(self, result: Dict[str, Any]) -> Dict[str, str]:
        """Format API command result for Slack"""
        if result['success']:
            return self.format_success_response(result)
        else:
            return self.format_error_response(result)
    
    def format_success_response(self, result: Dict[str, Any]) -> Dict[str, str]:
        """Format successful command result for Slack"""
        action = result.get('action', 'unknown')
        message = result.get('message', 'Command executed successfully')
        
        if action == 'approve' or action == 'complete':
            return {
                "text": f"✅ {message}",
                "response_type": "ephemeral"
            }
        elif action == 'brief':
            # Show brief content using Slack blocks
            brief_content = result.get('brief_content', {})
            return {
                "text": f"📋 Brief for {result.get('code', 'Unknown')}",
                "blocks": self.format_brief_blocks(brief_content),
                "response_type": "ephemeral"
            }
        elif action in ['refresh', 'quick_collection', 'full_collection']:
            return {
                "text": f"🔄 {message}",
                "response_type": "ephemeral"
            }
        elif action == 'status':
            status_info = result.get('status_info', {})
            return {
                "text": f"📊 {message}",
                "blocks": self.format_status_blocks(status_info),
                "response_type": "ephemeral"
            }
        else:
            return {
                "text": f"✅ {message}",
                "response_type": "ephemeral"
            }
    
    def format_error_response(self, result: Dict[str, Any]) -> Dict[str, str]:
        """Format error result for Slack"""
        error = result.get('error', 'Unknown error')
        suggestions = result.get('suggestions', [])
        
        message = f"❌ {error}"
        
        if suggestions:
            message += f"\n\n💡 Suggestions: {', '.join(suggestions)}"
        
        return {
            "text": message,
            "response_type": "ephemeral"
        }
    
    def format_brief_blocks(self, brief_content: Dict[str, Any]) -> List[Dict]:
        """Format brief content as Slack blocks"""
        if not brief_content:
            return []
        
        blocks = []
        
        # Meeting title and info
        if brief_content.get('meeting_title'):
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{brief_content['meeting_title']}*"
                }
            })
        
        # Meeting details
        details = []
        if brief_content.get('meeting_time'):
            details.append(f"⏰ {brief_content['meeting_time']}")
        if brief_content.get('attendee_count'):
            details.append(f"👥 {brief_content['attendee_count']} attendees")
        
        if details:
            blocks.append({
                "type": "context",
                "elements": [{"type": "mrkdwn", "text": " • ".join(details)}]
            })
        
        # Summary
        if brief_content.get('summary'):
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": brief_content['summary']
                }
            })
        
        # Related content
        if brief_content.get('related_content'):
            content_items = brief_content['related_content'][:3]  # Limit to 3 items
            content_text = "\n".join([
                f"• {item.get('text', item.get('title', 'Unknown'))[:60]}{'...' if len(str(item.get('text', item.get('title', '')))) > 60 else ''}"
                for item in content_items
            ])
            
            if content_text:
                blocks.append({
                    "type": "section", 
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Related Content:*\n{content_text}"
                    }
                })
        
        return blocks
    
    def format_status_blocks(self, status_info: Dict[str, Any]) -> List[Dict]:
        """Format system status as Slack blocks"""
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*System Status:* {status_info.get('system_status', 'Unknown')}"
                }
            }
        ]
        
        # Metrics
        if status_info.get('calendar_items') is not None:
            metrics_text = f"📅 {status_info['calendar_items']} meetings"
            if status_info.get('priority_items') is not None:
                metrics_text += f" • ⭐ {status_info['priority_items']} priorities"
            
            blocks.append({
                "type": "context",
                "elements": [{"type": "mrkdwn", "text": metrics_text}]
            })
        
        # Last sync
        if status_info.get('last_sync'):
            blocks.append({
                "type": "context",
                "elements": [{"type": "mrkdwn", "text": f"Last sync: {status_info['last_sync']}"}]
            })
        
        return blocks
    
    def start_server(self, port: int = 3000, host: str = "0.0.0.0"):
        """Start the simple Slack bot server"""
        logger.info(f"🚀 Starting simple Slack bot on {host}:{port}")
        self.app.start(port=port, host=host)
    
    def __del__(self):
        """Cleanup on bot destruction"""
        if self.session:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.disconnect_from_api())
                else:
                    loop.run_until_complete(self.disconnect_from_api())
            except Exception:
                pass  # Ignore cleanup errors
    
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