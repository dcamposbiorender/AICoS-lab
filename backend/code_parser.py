"""
Code Parser for Agent G Frontend Integration

References:
- Task specification: /Users/david.campos/VibeCode/AICoS-Lab/tasks/frontend_agent_g_coding.md
- Command examples from /Users/david.campos/VibeCode/AICoS-Lab/cos-paper-dense.html
- Pattern matching approach for natural language command processing

Features:
- Parse natural language commands to extract codes and actions
- Support for piped commands like "approve P7 | refresh | brief C3"
- Robust error handling with helpful suggestions
- Case-insensitive command parsing
"""

import re
import logging
from typing import Dict, List, Any, Optional, Union

logger = logging.getLogger(__name__)

class CodeParser:
    """
    Parse natural language commands to extract codes and actions
    
    Supported patterns:
    - "approve P7" → {'action': 'approve', 'code': 'P7', 'type': 'priority'}
    - "brief C3" → {'action': 'brief', 'code': 'C3', 'type': 'calendar'}
    - "approve P7 | refresh | brief C3" → Multiple commands
    """
    
    def __init__(self):
        # Define command patterns
        self.patterns = {
            'approve': {
                'pattern': r'approve\s+([PpCcMm]\d+)',
                'action': 'approve',
                'captures': ['code']
            },
            'complete': {
                'pattern': r'(complete|done|finish)\s+([PpCcMm]\d+)',
                'action': 'complete',
                'captures': ['action_synonym', 'code']
            },
            'brief': {
                'pattern': r'brief\s+(?:meeting\s+)?([CcMm]\d+)',
                'action': 'brief',
                'captures': ['code']
            },
            'update': {
                'pattern': r'update\s+([PpCcMm]\d+)\s+(.+)',
                'action': 'update',
                'captures': ['code', 'new_value']
            },
            'schedule': {
                'pattern': r'schedule\s+(.+?)\s+with\s+(.+)',
                'action': 'schedule',
                'captures': ['description', 'attendees']
            },
            'refresh': {
                'pattern': r'refresh|reload|sync',
                'action': 'refresh',
                'captures': []
            },
            'quick': {
                'pattern': r'quick\s*(?:pull|sync|collection)?',
                'action': 'quick_collection',
                'captures': []
            },
            'full': {
                'pattern': r'full\s*(?:pull|sync|collection)?',
                'action': 'full_collection', 
                'captures': []
            }
        }
    
    def parse(self, command: str) -> Dict[str, Any]:
        """
        Parse a command string into structured actions
        
        Args:
            command: Natural language command string
            
        Returns:
            Dict with action, codes, and any parameters
        """
        command = command.strip()
        
        if '|' in command:
            # Handle pipe-separated multiple commands
            return self._parse_piped_commands(command)
        else:
            # Single command
            return self._parse_single_command(command)
    
    def _parse_piped_commands(self, command: str) -> Dict[str, Any]:
        """Parse command with pipe separators"""
        commands = [cmd.strip() for cmd in command.split('|')]
        parsed_commands = []
        
        for cmd in commands:
            if cmd:
                parsed = self._parse_single_command(cmd)
                if 'error' not in parsed:
                    parsed_commands.append(parsed)
                else:
                    # Return error from first failed command
                    return parsed
        
        return {
            'type': 'multiple',
            'commands': parsed_commands,
            'original': command
        }
    
    def _parse_single_command(self, command: str) -> Dict[str, Any]:
        """Parse a single command"""
        command_lower = command.lower().strip()
        
        for pattern_name, pattern_info in self.patterns.items():
            match = re.match(pattern_info['pattern'], command_lower)
            if match:
                result = {
                    'action': pattern_info['action'],
                    'original': command
                }
                
                # Extract captured groups
                groups = match.groups()
                for i, capture_name in enumerate(pattern_info['captures']):
                    if i < len(groups) and groups[i]:
                        if capture_name == 'code':
                            # Normalize code (uppercase)
                            code = groups[i].upper()
                            result['code'] = code
                            result['type'] = self._get_code_type(code)
                        else:
                            result[capture_name] = groups[i]
                
                return result
        
        # No pattern matched
        return {
            'error': f"Unknown command: {command}",
            'original': command,
            'suggestions': self._get_suggestions(command_lower)
        }
    
    def _get_code_type(self, code: str) -> str:
        """Determine the type of a code"""
        if code.startswith('C'):
            return 'calendar'
        elif code.startswith('P'):
            return 'priority'
        elif code.startswith('M'):
            return 'commitment'
        else:
            return 'unknown'
    
    def _get_suggestions(self, partial_command: str) -> List[str]:
        """Get suggestions for partial or invalid commands"""
        suggestions = []
        
        # Check if it's a partial match for any pattern
        first_word = partial_command.split()[0] if partial_command.split() else ""
        for pattern_name in self.patterns.keys():
            if pattern_name.startswith(first_word):
                suggestions.append(pattern_name)
        
        # Common command examples
        if not suggestions:
            suggestions = [
                'approve P1', 'approve P2', 'brief C1', 'refresh', 'quick', 'full'
            ]
        
        return suggestions[:5]  # Limit suggestions
    
    def validate_code_format(self, code: str) -> bool:
        """Validate that a code has the correct format"""
        pattern = r'^[CPM]\d+$'
        return bool(re.match(pattern, code.upper()))
    
    def extract_codes_from_text(self, text: str) -> List[str]:
        """Extract all codes from a text string"""
        pattern = r'\b([CPMcpm]\d+)\b'
        matches = re.findall(pattern, text)
        return [match.upper() for match in matches]
    
    def get_help(self) -> Dict[str, List[str]]:
        """Get help information for available commands"""
        return {
            'basic_commands': [
                'approve P7 - Approve priority P7',
                'brief C3 - Show brief for calendar item C3',
                'refresh - Refresh all data',
                'quick - Quick data collection',
                'full - Full data collection'
            ],
            'advanced_commands': [
                'update P5 new text - Update priority P5',
                'complete M2 - Mark commitment M2 complete',
                'schedule meeting with john - Schedule new meeting'
            ],
            'multiple_commands': [
                'approve P7 | refresh - Execute multiple commands',
                'brief C1 | approve P3 | refresh - Chain commands'
            ],
            'code_types': [
                'C1, C2... - Calendar items',
                'P1, P2... - Priority items', 
                'M1, M2... - Commitment items'
            ]
        }