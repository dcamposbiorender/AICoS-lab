"""
Unified Command Processor for Agent H Frontend Integration

References:
- Task specification: /Users/david.campos/VibeCode/AICoS-Lab/tasks/frontend_agent_h_integration.md
- Agent E StateManager: backend/state_manager.py
- Agent G CodingManager: backend/coding_system.py
- Agent G CodeParser: backend/code_parser.py

Features:
- Unified command processing for dashboard and Slack interfaces
- Handles all commands consistently regardless of source
- Support for approve, brief, refresh, multi-commands with pipes
- Real-time state updates with WebSocket broadcasting
- Performance optimized for <100ms command response time
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

# Add project root for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.state_manager import StateManager
from backend.coding_system import CodingManager
from backend.code_parser import CodeParser

logger = logging.getLogger(__name__)

class UnifiedCommandProcessor:
    """
    Unified command processing for dashboard and Slack interfaces
    
    Handles all commands consistently regardless of source:
    - approve P7 / complete P7 - Mark priority/commitment as done
    - brief C3 - Generate meeting brief for calendar item
    - refresh / quick / full - Trigger data collection
    - Multi-commands with pipes: "approve P7 | refresh | brief C3"
    
    Design Philosophy:
    - Single source of truth for command execution logic
    - Consistent behavior across all interfaces (dashboard, Slack, CLI)
    - Performance optimized for <100ms response time
    - Lab-grade implementation - reliable and simple
    """
    
    def __init__(self, state_manager: StateManager, coding_manager: CodingManager, 
                 parser: CodeParser, brief_generator=None):
        self.state_manager = state_manager
        self.coding_manager = coding_manager
        self.parser = parser
        self.brief_generator = brief_generator  # Will import lazily if needed
        
        # Command handlers mapping
        self.handlers = {
            'approve': self.handle_approve,
            'complete': self.handle_complete,
            'brief': self.handle_brief,
            'refresh': self.handle_refresh,
            'quick_collection': self.handle_quick_collection,
            'full_collection': self.handle_full_collection,
            'update': self.handle_update,
            'status': self.handle_status,
            'help': self.handle_help
        }
        
        # Performance monitoring
        self._command_count = 0
        self._total_execution_time = 0
        
        logger.info("UnifiedCommandProcessor initialized")
    
    async def execute_command(self, command: str) -> Dict[str, Any]:
        """
        Execute a command and return structured result
        
        Args:
            command: Natural language command string (e.g., "approve P7", "brief C3")
            
        Returns:
            Dict with success status, action taken, and result data
        """
        start_time = datetime.now()
        self._command_count += 1
        
        try:
            logger.info(f"Executing command: {command}")
            
            # Parse command using Agent G's parser
            parsed = self.parser.parse(command)
            
            if 'error' in parsed:
                return {
                    'success': False,
                    'error': parsed['error'],
                    'suggestions': parsed.get('suggestions', []),
                    'command': command,
                    'execution_time_ms': self._get_execution_time_ms(start_time)
                }
            
            # Handle multiple commands (pipe-separated)
            if parsed.get('type') == 'multiple':
                return await self.execute_multiple_commands(parsed, command, start_time)
            
            # Single command execution
            result = await self.execute_single_command(parsed)
            result['command'] = command
            result['execution_time_ms'] = self._get_execution_time_ms(start_time)
            
            logger.info(f"Command executed successfully: {result.get('action', 'unknown')}")
            return result
            
        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            return {
                'success': False,
                'error': f"Command execution failed: {str(e)}",
                'command': command,
                'execution_time_ms': self._get_execution_time_ms(start_time)
            }
    
    async def execute_multiple_commands(self, parsed: Dict[str, Any], original_command: str, start_time) -> Dict[str, Any]:
        """
        Execute multiple pipe-separated commands in sequence
        
        Args:
            parsed: Parsed command structure with multiple commands
            original_command: Original command string for reference
            start_time: Execution start time for performance tracking
            
        Returns:
            Dict with results from all commands
        """
        commands = parsed.get('commands', [])
        results = []
        
        logger.info(f"Executing {len(commands)} pipe-separated commands")
        
        for i, cmd in enumerate(commands):
            try:
                result = await self.execute_single_command(cmd)
                results.append(result)
                
                # Stop on first failure unless command is non-critical
                if not result.get('success', False) and not self._is_non_critical_command(cmd):
                    logger.warning(f"Stopping multi-command execution at step {i+1} due to failure")
                    break
                    
            except Exception as e:
                error_result = {
                    'success': False,
                    'error': str(e),
                    'command_index': i
                }
                results.append(error_result)
                break
        
        overall_success = all(r.get('success', False) for r in results)
        
        return {
            'success': overall_success,
            'type': 'multiple',
            'results': results,
            'message': f"Executed {len(results)} of {len(commands)} commands",
            'command': original_command,
            'execution_time_ms': self._get_execution_time_ms(start_time)
        }
    
    async def execute_single_command(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a single parsed command
        
        Args:
            parsed: Parsed command structure
            
        Returns:
            Dict with command execution result
        """
        action = parsed.get('action')
        
        if action in self.handlers:
            return await self.handlers[action](parsed)
        else:
            return {
                'success': False,
                'error': f"Unknown action: {action}",
                'available_actions': list(self.handlers.keys()),
                'suggestion': f"Try one of: {', '.join(list(self.handlers.keys())[:5])}"
            }
    
    async def handle_approve(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        """Handle approve command (mark item as approved/done)"""
        code = parsed.get('code')
        if not code:
            return {'success': False, 'error': 'No code specified for approve command'}
        
        # Find the item using Agent G's coding system
        item = self.coding_manager.get_by_code(code)
        if not item:
            return {'success': False, 'error': f'Item {code} not found'}
        
        # Update item status
        code_type = parsed.get('type', 'priority')
        
        if code_type == 'priority':
            item['status'] = 'done'
            await self.update_item_in_state('priorities', code, item)
            
            return {
                'success': True,
                'action': 'approve',
                'code': code,
                'item_text': item.get('text', item.get('title', 'Unknown')),
                'message': f"✅ Approved {code}: {item.get('text', item.get('title', 'Unknown'))}"
            }
        elif code_type == 'commitment':
            item['status'] = 'done'
            await self.update_commitment_in_state(code, item)
            
            return {
                'success': True,
                'action': 'approve',
                'code': code,
                'item_text': item.get('text', item.get('description', 'Unknown')),
                'message': f"✅ Approved commitment {code}"
            }
        else:
            return {
                'success': False,
                'error': f"Cannot approve {code_type} item {code}. Only priorities and commitments can be approved."
            }
    
    async def handle_complete(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        """Handle complete/done command (alias for approve)"""
        return await self.handle_approve(parsed)
    
    async def handle_brief(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        """Handle brief command (generate meeting brief)"""
        code = parsed.get('code')
        if not code:
            return {'success': False, 'error': 'No code specified for brief command'}
        
        # Find the item using Agent G's coding system
        item = self.coding_manager.get_by_code(code)
        if not item:
            return {'success': False, 'error': f'Item {code} not found'}
        
        code_type = parsed.get('type', 'calendar')
        
        if code_type == 'calendar':
            # Generate meeting brief
            brief = await self.generate_meeting_brief(item)
            
            # Update state to show active brief on dashboard
            await self.state_manager.update_state('active_brief', brief)
            
            return {
                'success': True,
                'action': 'brief',
                'code': code,
                'brief_content': brief,
                'message': f"📋 Generated brief for {code}: {item.get('title', 'Meeting')}"
            }
        else:
            return {
                'success': False,
                'error': f"Cannot generate brief for {code_type} item {code}. Only calendar items support briefs."
            }
    
    async def handle_refresh(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        """Handle refresh command (trigger quick collection)"""
        # Import collector integration lazily to avoid circular imports
        from backend.collector_integration import CollectorIntegrator
        
        integrator = CollectorIntegrator(self.state_manager, self.coding_manager)
        result = await integrator.trigger_quick_collection()
        
        return {
            'success': result['success'],
            'action': 'refresh',
            'message': result.get('message', '🔄 Refresh completed'),
            'details': result
        }
    
    async def handle_quick_collection(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        """Handle quick collection command (alias for refresh)"""
        return await self.handle_refresh(parsed)
    
    async def handle_full_collection(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        """Handle full collection command"""
        from backend.collector_integration import CollectorIntegrator
        
        integrator = CollectorIntegrator(self.state_manager, self.coding_manager)
        result = await integrator.trigger_full_collection()
        
        return {
            'success': result['success'],
            'action': 'full_collection',
            'message': result.get('message', '🔄 Full collection completed'),
            'details': result
        }
    
    async def handle_update(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        """Handle update command (modify item text/title)"""
        code = parsed.get('code')
        new_value = parsed.get('new_value')
        
        if not code or not new_value:
            return {'success': False, 'error': 'Update requires code and new value'}
        
        item = self.coding_manager.get_by_code(code)
        if not item:
            return {'success': False, 'error': f'Item {code} not found'}
        
        # Update appropriate field
        if 'text' in item:
            old_value = item['text']
            item['text'] = new_value
        elif 'title' in item:
            old_value = item['title']
            item['title'] = new_value
        else:
            return {'success': False, 'error': f'Cannot update {code} - no editable text field found'}
        
        # Update in state
        code_type = parsed.get('type', 'priority')
        if code_type == 'priority':
            await self.update_item_in_state('priorities', code, item)
        elif code_type == 'calendar':
            await self.update_item_in_state('calendar', code, item)
        elif code_type == 'commitment':
            await self.update_commitment_in_state(code, item)
        
        return {
            'success': True,
            'action': 'update',
            'code': code,
            'old_value': old_value,
            'new_value': new_value,
            'message': f"📝 Updated {code}: {old_value} → {new_value}"
        }
    
    async def handle_status(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        """Handle status command (show system status)"""
        system_state = self.state_manager.state.get('system', {})
        calendar_items = len(self.state_manager.state.get('calendar', []))
        priority_items = len(self.state_manager.state.get('priorities', []))
        
        status_info = {
            'system_status': system_state.get('status', 'UNKNOWN'),
            'last_sync': system_state.get('last_sync', 'Never'),
            'calendar_items': calendar_items,
            'priority_items': priority_items,
            'command_processor_stats': {
                'commands_processed': self._command_count,
                'average_execution_time_ms': self._total_execution_time / max(self._command_count, 1)
            }
        }
        
        return {
            'success': True,
            'action': 'status',
            'status_info': status_info,
            'message': f"📊 System Status: {status_info['system_status']}, {calendar_items} meetings, {priority_items} priorities"
        }
    
    async def handle_help(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        """Handle help command (show available commands)"""
        help_text = """Available commands:
• approve/complete <code> - Mark item as done (e.g., "approve P7")
• brief <code> - Generate meeting brief (e.g., "brief C3")
• refresh/quick - Quick data collection 
• full - Full data collection
• update <code> <new_text> - Update item text
• status - Show system status
• help - Show this help

Multi-commands: Use | to chain commands (e.g., "approve P7 | refresh")
"""
        
        return {
            'success': True,
            'action': 'help',
            'help_text': help_text,
            'available_commands': list(self.handlers.keys()),
            'message': "📚 Command help displayed"
        }
    
    async def update_item_in_state(self, section: str, code: str, updated_item: Dict[str, Any]):
        """
        Update a specific item in state by code with real-time broadcasting
        
        Args:
            section: State section ('priorities', 'calendar', etc.)
            code: Item code to update
            updated_item: Updated item data
        """
        current_state = self.state_manager.state.get(section, [])
        
        for i, item in enumerate(current_state):
            if item.get('code') == code:
                current_state[i] = updated_item
                break
        else:
            # Item not found, add it
            current_state.append(updated_item)
        
        # Update state with real-time WebSocket broadcasting
        await self.state_manager.update_state(section, current_state)
    
    async def update_commitment_in_state(self, code: str, updated_item: Dict[str, Any]):
        """
        Update commitment item (special handling for nested structure)
        
        Args:
            code: Commitment code
            updated_item: Updated commitment data
        """
        commitments = self.state_manager.state.get('commitments', {'owe': [], 'owed': []})
        
        # Check both owe and owed sections
        for section in ['owe', 'owed']:
            for i, item in enumerate(commitments[section]):
                if item.get('code') == code:
                    commitments[section][i] = updated_item
                    await self.state_manager.update_state('commitments', commitments)
                    return
        
        # Item not found, add to owe section by default
        commitments['owe'].append(updated_item)
        await self.state_manager.update_state('commitments', commitments)
    
    async def generate_meeting_brief(self, meeting_item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate meeting brief using brief generator
        
        Args:
            meeting_item: Calendar meeting data
            
        Returns:
            Dict with brief content
        """
        # Import brief generator lazily
        if not self.brief_generator:
            try:
                from backend.brief_generator import BriefGenerator
                self.brief_generator = BriefGenerator()
            except ImportError:
                logger.warning("BriefGenerator not available, using simple brief")
                return {
                    'meeting_code': meeting_item.get('code', 'Unknown'),
                    'meeting_title': meeting_item.get('title', 'Meeting'),
                    'summary': 'Brief generation not available - using simple format',
                    'formatted_text': f"Meeting: {meeting_item.get('title', 'Unknown')} at {meeting_item.get('time', 'Unknown time')}"
                }
        
        return await self.brief_generator.generate_meeting_brief(meeting_item)
    
    def _is_non_critical_command(self, cmd: Dict[str, Any]) -> bool:
        """Check if command is non-critical and shouldn't stop multi-command execution"""
        non_critical_actions = ['status', 'help']
        return cmd.get('action') in non_critical_actions
    
    def _get_execution_time_ms(self, start_time: datetime) -> float:
        """Calculate command execution time in milliseconds"""
        execution_time = (datetime.now() - start_time).total_seconds() * 1000
        self._total_execution_time += execution_time
        return round(execution_time, 2)
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get command processor performance statistics"""
        return {
            'commands_processed': self._command_count,
            'total_execution_time_ms': self._total_execution_time,
            'average_execution_time_ms': self._total_execution_time / max(self._command_count, 1),
            'handlers_available': len(self.handlers)
        }