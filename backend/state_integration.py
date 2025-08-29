"""
State Integration for Agent G Coding System

References:
- Task specification: /Users/david.campos/VibeCode/AICoS-Lab/tasks/frontend_agent_g_coding.md
- State management patterns from backend/state_manager.py
- Integration approach with Agent E backend foundation

Features:
- Apply codes to state data before broadcasting
- Handle code-based state updates and command execution
- Maintain code consistency across state changes
- Bridge between coding system and Agent E StateManager
"""

import logging
from typing import Dict, List, Any
from backend.coding_system import CodingManager, CodeType
from backend.code_parser import CodeParser

logger = logging.getLogger(__name__)

class StateCodingIntegration:
    """
    Integration layer between coding system and state management
    
    Responsibilities:
    - Apply codes to state data before broadcasting
    - Handle code-based state updates
    - Maintain code consistency across state changes
    """
    
    def __init__(self, coding_manager: CodingManager, code_parser: CodeParser):
        self.coding_manager = coding_manager
        self.code_parser = code_parser
    
    def apply_codes_to_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply codes to all relevant items in state
        
        Args:
            state: Current system state
            
        Returns:
            State with codes applied to all items
        """
        coded_state = state.copy()
        
        # Apply codes to calendar items
        if 'calendar' in coded_state and coded_state['calendar']:
            coded_state['calendar'] = self.coding_manager.assign_codes(
                CodeType.CALENDAR, coded_state['calendar']
            )
        
        # Apply codes to priorities
        if 'priorities' in coded_state and coded_state['priorities']:
            coded_state['priorities'] = self.coding_manager.assign_codes(
                CodeType.PRIORITY, coded_state['priorities']
            )
        
        # Apply codes to commitments (special handling for nested structure)
        if 'commitments' in coded_state and coded_state['commitments']:
            coded_state['commitments'] = self.coding_manager.assign_commitment_codes(
                coded_state['commitments']
            )
        
        return coded_state
    
    def execute_coded_command(self, command_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a command that involves codes
        
        Args:
            command_result: Parsed command from CodeParser
            
        Returns:
            Execution result with success/failure info
        """
        try:
            if command_result.get('type') == 'multiple':
                # Handle multiple commands
                results = []
                for cmd in command_result.get('commands', []):
                    result = self._execute_single_coded_command(cmd)
                    results.append(result)
                
                return {
                    'success': all(r['success'] for r in results),
                    'results': results,
                    'message': f"Executed {len(results)} commands"
                }
            else:
                # Single command
                return self._execute_single_coded_command(command_result)
                
        except Exception as e:
            logger.error(f"Error executing coded command: {e}")
            return {
                'success': False,
                'error': str(e),
                'command': command_result.get('original', 'unknown')
            }
    
    def _execute_single_coded_command(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single coded command"""
        action = command.get('action')
        code = command.get('code')
        
        if action == 'approve' and code:
            return self._handle_approve_command(code)
        elif action == 'brief' and code:
            return self._handle_brief_command(code)
        elif action == 'complete' and code:
            return self._handle_complete_command(code)
        elif action == 'update' and code:
            return self._handle_update_command(code, command.get('new_value'))
        elif action in ['refresh', 'quick_collection', 'full_collection']:
            return self._handle_system_command(action)
        else:
            return {
                'success': False,
                'error': f"Unknown action: {action}",
                'command': command.get('original')
            }
    
    def _handle_approve_command(self, code: str) -> Dict[str, Any]:
        """Handle approve command for a coded item"""
        item = self.coding_manager.get_by_code(code)
        
        if not item:
            return {
                'success': False,
                'error': f"Item with code {code} not found",
                'code': code
            }
        
        # Update item status based on type
        code_type = self.code_parser._get_code_type(code)
        
        if code_type == 'priority':
            # Mark priority as done
            item['status'] = 'done'
            # Note: In real implementation, this would trigger state update
            return {
                'success': True,
                'message': f"Approved priority {code}: {item.get('text', 'Unknown')}",
                'code': code,
                'item': item
            }
        else:
            return {
                'success': False,
                'error': f"Cannot approve {code_type} item {code}",
                'code': code
            }
    
    def _handle_brief_command(self, code: str) -> Dict[str, Any]:
        """Handle brief command for a calendar item"""
        item = self.coding_manager.get_by_code(code)
        
        if not item:
            return {
                'success': False,
                'error': f"Item with code {code} not found",
                'code': code
            }
        
        code_type = self.code_parser._get_code_type(code)
        
        if code_type == 'calendar':
            return {
                'success': True,
                'message': f"Generating brief for {code}: {item.get('title', 'Unknown')}",
                'code': code,
                'item': item,
                'action_needed': 'generate_brief'  # Signal to Agent H
            }
        else:
            return {
                'success': False,
                'error': f"Cannot generate brief for {code_type} item {code}",
                'code': code
            }
    
    def _handle_complete_command(self, code: str) -> Dict[str, Any]:
        """Handle complete command for any item type"""
        item = self.coding_manager.get_by_code(code)
        
        if not item:
            return {
                'success': False,
                'error': f"Item with code {code} not found",
                'code': code
            }
        
        # Mark as complete regardless of type
        item['status'] = 'done'
        
        return {
            'success': True,
            'message': f"Completed {code}: {item.get('text') or item.get('title', 'Unknown')}",
            'code': code,
            'item': item
        }
    
    def _handle_update_command(self, code: str, new_value: str) -> Dict[str, Any]:
        """Handle update command for an item"""
        item = self.coding_manager.get_by_code(code)
        
        if not item:
            return {
                'success': False,
                'error': f"Item with code {code} not found",
                'code': code
            }
        
        # Update the text/title field
        if 'text' in item:
            item['text'] = new_value
        elif 'title' in item:
            item['title'] = new_value
        else:
            return {
                'success': False,
                'error': f"Don't know how to update {code}",
                'code': code
            }
        
        return {
            'success': True,
            'message': f"Updated {code} to: {new_value}",
            'code': code,
            'item': item
        }
    
    def _handle_system_command(self, action: str) -> Dict[str, Any]:
        """Handle system-level commands"""
        return {
            'success': True,
            'message': f"Executing {action}",
            'action': action,
            'system_command': True
        }
    
    def get_coded_item_summary(self) -> Dict[str, Any]:
        """Get summary of all coded items for display"""
        stats = self.coding_manager.get_stats()
        
        summary = {
            'total_items': stats['total_codes'],
            'by_type': stats['by_type'],
            'recent_codes': []
        }
        
        # Get recent codes for each type
        for code_type in CodeType:
            codes = self.coding_manager.get_codes_by_type(code_type)
            if codes:
                # Sort codes numerically
                sorted_codes = sorted(codes, key=lambda x: int(x[1:]))
                recent = sorted_codes[-3:]  # Last 3 codes
                summary['recent_codes'].extend(recent)
        
        return summary