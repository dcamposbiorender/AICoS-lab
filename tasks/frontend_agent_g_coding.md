# Agent G: Coding System & State Management - Phase 4.5 Frontend

**Date Created**: 2025-08-28  
**Owner**: Agent G (Coding System Team)  
**Status**: PENDING  
**Estimated Time**: 8 hours (1 day)  
**Dependencies**: Agent E state management (`backend/state_manager.py`)

## Executive Summary

Implement the C1/P1/M1 coding system that enables rapid keyboard navigation and command execution. This system automatically assigns unique short codes to all items (Calendar=C1-Cn, Priority=P1-Pn, Commitments=M1-Mn) for efficient interaction.

**Core Philosophy**: Every item in the system gets a unique, memorable code that persists across updates. This enables commands like "approve P7" or "brief C3" to work reliably and provides rapid keyboard navigation.

## Relevant Files for Context

**Read for Context:**
- `backend/state_manager.py` - State structure and update patterns (from Agent E)
- `/Users/david.campos/VibeCode/AICoS-Lab/cos-paper-dense.html` - Coding examples from mockup
- `src/search/database.py` - Database patterns for persistence

**Files to Create:**
- `backend/coding_system.py` - Core coding logic and management
- `backend/code_parser.py` - Parse codes from natural language commands
- `tests/test_coding_system.py` - Comprehensive test suite

## Test Acceptance Criteria (Write FIRST)

### File: `tests/test_coding_system.py`
```python
import pytest
from datetime import datetime
from backend.coding_system import CodingManager, CodeType
from backend.code_parser import CodeParser

class TestCodeGeneration:
    """Test automatic code generation for different item types"""
    
    def test_calendar_code_generation(self):
        """Calendar items get sequential C codes"""
        manager = CodingManager()
        
        calendar_items = [
            {'time': '9:00', 'title': 'Product Sync', 'date': '2025-08-28'},
            {'time': '11:00', 'title': '1:1 w/ Sarah', 'date': '2025-08-28'},
            {'time': '2:00', 'title': 'Budget Review', 'date': '2025-08-28'},
        ]
        
        coded_items = manager.assign_codes(CodeType.CALENDAR, calendar_items)
        
        assert len(coded_items) == 3
        assert coded_items[0]['code'] == 'C1'
        assert coded_items[1]['code'] == 'C2' 
        assert coded_items[2]['code'] == 'C3'
        
        # Items should retain all original data
        assert coded_items[0]['title'] == 'Product Sync'
        assert coded_items[1]['time'] == '11:00'
    
    def test_priority_code_generation(self):
        """Priority items get sequential P codes"""
        manager = CodingManager()
        
        priorities = [
            {'text': 'Q1 Planning Doc', 'status': 'done'},
            {'text': 'Budget Review', 'status': 'pending'},
            {'text': 'Hire Approval', 'status': 'partial'},
            {'text': 'API v2 Spec', 'status': 'pending'},
        ]
        
        coded_items = manager.assign_codes(CodeType.PRIORITY, priorities)
        
        assert len(coded_items) == 4
        assert coded_items[0]['code'] == 'P1'
        assert coded_items[3]['code'] == 'P4'
        
        # Status should be preserved
        assert coded_items[0]['status'] == 'done'
        assert coded_items[2]['status'] == 'partial'
    
    def test_commitment_code_generation(self):
        """Commitments get sequential M codes across both directions"""
        manager = CodingManager()
        
        commitments = {
            'owe': [
                {'text': 'Budget slides → CFO (Fri)', 'due_date': '2025-08-29'},
                {'text': 'Hire decision → HR (Today)', 'due_date': '2025-08-28'},
            ],
            'owed': [
                {'text': 'Sales forecast ← Sarah (noon)', 'due_date': '2025-08-28'},
                {'text': 'Tech spec ← Eng (Thu)', 'due_date': '2025-08-29'},
                {'text': 'Market analysis ← PM (Fri)', 'due_date': '2025-08-29'},
            ]
        }
        
        coded_commitments = manager.assign_commitment_codes(commitments)
        
        # Should have sequential codes across both sections
        assert coded_commitments['owe'][0]['code'] == 'M1'
        assert coded_commitments['owe'][1]['code'] == 'M2'
        assert coded_commitments['owed'][0]['code'] == 'M3'
        assert coded_commitments['owed'][1]['code'] == 'M4'
        assert coded_commitments['owed'][2]['code'] == 'M5'
    
    def test_code_persistence_across_updates(self):
        """Codes persist when items are updated"""
        manager = CodingManager()
        
        # Initial assignment
        original_items = [
            {'text': 'Task 1', 'status': 'pending'},
            {'text': 'Task 2', 'status': 'pending'},
        ]
        
        coded_items = manager.assign_codes(CodeType.PRIORITY, original_items)
        assert coded_items[0]['code'] == 'P1'
        assert coded_items[1]['code'] == 'P2'
        
        # Update with status changes - codes should persist
        updated_items = [
            {'text': 'Task 1', 'status': 'done'},  # Status changed
            {'text': 'Task 2', 'status': 'pending'},
        ]
        
        # Re-assign codes with same manager
        re_coded_items = manager.assign_codes(CodeType.PRIORITY, updated_items)
        assert re_coded_items[0]['code'] == 'P1'  # Same code
        assert re_coded_items[1]['code'] == 'P2'  # Same code
        assert re_coded_items[0]['status'] == 'done'  # Updated status

class TestCodeLookup:
    """Test code-to-item lookup functionality"""
    
    def test_code_lookup_success(self):
        """Successfully find items by code"""
        manager = CodingManager()
        
        items = [
            {'text': 'First task'},
            {'text': 'Second task'},
            {'text': 'Third task'},
        ]
        
        coded_items = manager.assign_codes(CodeType.PRIORITY, items)
        
        # Test lookups
        found_item = manager.get_by_code('P1')
        assert found_item is not None
        assert found_item['text'] == 'First task'
        assert found_item['code'] == 'P1'
        
        found_item = manager.get_by_code('P3')
        assert found_item is not None
        assert found_item['text'] == 'Third task'
    
    def test_code_lookup_failure(self):
        """Handle non-existent codes gracefully"""
        manager = CodingManager()
        
        items = [{'text': 'Only task'}]
        coded_items = manager.assign_codes(CodeType.PRIORITY, items)
        
        # Lookup non-existent codes
        assert manager.get_by_code('P5') is None
        assert manager.get_by_code('C1') is None
        assert manager.get_by_code('INVALID') is None
    
    def test_code_type_validation(self):
        """Codes match expected patterns for each type"""
        manager = CodingManager()
        
        # Test calendar codes
        cal_items = [{'title': 'Meeting'}]
        coded_cal = manager.assign_codes(CodeType.CALENDAR, cal_items)
        assert coded_cal[0]['code'].startswith('C')
        assert coded_cal[0]['code'][1:].isdigit()
        
        # Test priority codes
        pri_items = [{'text': 'Task'}]
        coded_pri = manager.assign_codes(CodeType.PRIORITY, pri_items)
        assert coded_pri[0]['code'].startswith('P')
        assert coded_pri[0]['code'][1:].isdigit()

class TestCodePersistence:
    """Test code persistence across system restarts"""
    
    def test_code_persistence_to_storage(self):
        """Codes can be saved and restored"""
        manager = CodingManager()
        
        items = [
            {'text': 'Persistent task 1'},
            {'text': 'Persistent task 2'},
        ]
        
        # Assign codes and save
        coded_items = manager.assign_codes(CodeType.PRIORITY, items)
        manager.save_code_mappings()
        
        # Create new manager (simulating restart)
        new_manager = CodingManager()
        new_manager.load_code_mappings()
        
        # Verify codes restored
        found_item = new_manager.get_by_code('P1')
        assert found_item is not None
        assert found_item['text'] == 'Persistent task 1'
    
    def test_code_mapping_updates(self):
        """Code mappings update when items change"""
        manager = CodingManager()
        
        # Initial items
        original = [{'text': 'Original task'}]
        coded_original = manager.assign_codes(CodeType.PRIORITY, original)
        
        # Add new item
        updated = [
            {'text': 'Original task'},
            {'text': 'New task'},
        ]
        coded_updated = manager.assign_codes(CodeType.PRIORITY, updated)
        
        # Both items should be findable
        assert manager.get_by_code('P1')['text'] == 'Original task'
        assert manager.get_by_code('P2')['text'] == 'New task'
        
        # Remove first item
        reduced = [{'text': 'New task'}]
        coded_reduced = manager.assign_codes(CodeType.PRIORITY, reduced)
        
        # P1 should no longer exist, but P2 should still work
        assert manager.get_by_code('P1') is None
        assert manager.get_by_code('P2')['text'] == 'New task'

class TestCommandParsing:
    """Test parsing codes from natural language commands"""
    
    def test_approve_command_parsing(self):
        """Parse approve commands with codes"""
        parser = CodeParser()
        
        result = parser.parse('approve P7')
        assert result['action'] == 'approve'
        assert result['code'] == 'P7'
        assert result['type'] == 'priority'
        
        result = parser.parse('approve p3')  # Case insensitive
        assert result['action'] == 'approve'
        assert result['code'] == 'P3'
        assert result['type'] == 'priority'
    
    def test_brief_command_parsing(self):
        """Parse brief commands with calendar codes"""
        parser = CodeParser()
        
        result = parser.parse('brief C3')
        assert result['action'] == 'brief'
        assert result['code'] == 'C3'
        assert result['type'] == 'calendar'
        
        result = parser.parse('brief meeting C5')
        assert result['action'] == 'brief'
        assert result['code'] == 'C5'
    
    def test_complex_command_parsing(self):
        """Parse complex commands with multiple codes"""
        parser = CodeParser()
        
        result = parser.parse('approve P7 | refresh | brief C3')
        assert len(result['commands']) == 3
        assert result['commands'][0] == {'action': 'approve', 'code': 'P7', 'type': 'priority'}
        assert result['commands'][1] == {'action': 'refresh'}
        assert result['commands'][2] == {'action': 'brief', 'code': 'C3', 'type': 'calendar'}
    
    def test_invalid_command_handling(self):
        """Handle invalid commands gracefully"""
        parser = CodeParser()
        
        result = parser.parse('invalid command xyz')
        assert result['error'] is not None
        assert 'unknown' in result['error'].lower()
        
        result = parser.parse('approve P999')  # Code doesn't exist
        assert result['action'] == 'approve'
        assert result['code'] == 'P999'
        # Note: Existence validation happens in CodingManager, not parser

class TestIntegration:
    """Test integration with state management system"""
    
    def test_state_update_with_codes(self):
        """State updates include proper codes"""
        from backend.state_manager import StateManager
        
        manager = CodingManager()
        state_mgr = StateManager()
        
        # Test calendar integration
        calendar_data = [
            {'time': '9:00', 'title': 'Morning sync'},
            {'time': '2:00', 'title': 'Afternoon review'},
        ]
        
        coded_calendar = manager.assign_codes(CodeType.CALENDAR, calendar_data)
        
        # Should be able to update state with coded items
        # This tests the interface between coding system and state management
        assert coded_calendar[0]['code'] == 'C1'
        assert coded_calendar[1]['code'] == 'C2'
        
        # Items should be suitable for state management
        assert all('code' in item for item in coded_calendar)
        assert all('time' in item for item in coded_calendar)
        assert all('title' in item for item in coded_calendar)
```

## Implementation Tasks

### Task G1: Core Coding System (2 hours)

**Objective**: Implement CodingManager class with code generation and persistence

**File**: `backend/coding_system.py`
```python
import json
import logging
from enum import Enum
from typing import Dict, List, Any, Optional, Union
from pathlib import Path

logger = logging.getLogger(__name__)

class CodeType(Enum):
    CALENDAR = "calendar"
    PRIORITY = "priority"
    COMMITMENT = "commitment"

class CodingManager:
    """
    Manages the C1/P1/M1 coding system for rapid item identification
    
    Responsibilities:
    - Assign unique codes to items (C1-Cn, P1-Pn, M1-Mn)
    - Maintain bidirectional mapping (code ↔ item)
    - Persist code assignments across system restarts
    - Handle item additions, removals, and updates
    """
    
    def __init__(self, persistence_path: str = "data/code_mappings.json"):
        self.persistence_path = Path(persistence_path)
        self.code_mappings: Dict[str, Dict[str, Any]] = {}
        self.reverse_mappings: Dict[str, str] = {}
        self.counters = {
            CodeType.CALENDAR: 0,
            CodeType.PRIORITY: 0,
            CodeType.COMMITMENT: 0
        }
        
        # Load existing mappings if available
        self.load_code_mappings()
    
    def assign_codes(self, code_type: CodeType, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Assign codes to a list of items, preserving existing codes where possible
        
        Args:
            code_type: Type of code to assign (C, P, or M)
            items: List of items to code
            
        Returns:
            List of items with 'code' field added
        """
        coded_items = []
        existing_codes = set()
        
        # First pass: identify items that already have codes
        for item in items:
            if 'code' in item:
                # Validate existing code
                if self._is_valid_code(item['code'], code_type):
                    existing_codes.add(item['code'])
                    self._update_mapping(item['code'], item)
                    coded_items.append(item.copy())
                else:
                    # Invalid code, will be reassigned
                    coded_items.append(item.copy())
            else:
                coded_items.append(item.copy())
        
        # Second pass: assign codes to items without valid codes
        counter = 1
        prefix = self._get_code_prefix(code_type)
        
        for i, item in enumerate(coded_items):
            if 'code' not in item or not self._is_valid_code(item['code'], code_type):
                # Find next available code
                while f"{prefix}{counter}" in existing_codes:
                    counter += 1
                
                new_code = f"{prefix}{counter}"
                coded_items[i]['code'] = new_code
                existing_codes.add(new_code)
                
                self._update_mapping(new_code, coded_items[i])
                counter += 1
        
        # Update counter for this type
        if existing_codes:
            max_num = max(int(code[1:]) for code in existing_codes if code.startswith(prefix))
            self.counters[code_type] = max_num
        
        return coded_items
    
    def assign_commitment_codes(self, commitments: Dict[str, List[Dict[str, Any]]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Special handling for commitments which have 'owe' and 'owed' sections
        but share a single M code sequence
        """
        # Flatten commitments for coding
        all_commitments = []
        all_commitments.extend(commitments.get('owe', []))
        all_commitments.extend(commitments.get('owed', []))
        
        # Assign codes to flattened list
        coded_all = self.assign_codes(CodeType.COMMITMENT, all_commitments)
        
        # Rebuild structure
        result = {'owe': [], 'owed': []}
        owe_count = len(commitments.get('owe', []))
        
        result['owe'] = coded_all[:owe_count]
        result['owed'] = coded_all[owe_count:]
        
        return result
    
    def get_by_code(self, code: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve item by its code
        
        Args:
            code: The code to look up (e.g., 'P7', 'C3')
            
        Returns:
            The item with that code, or None if not found
        """
        return self.code_mappings.get(code.upper())
    
    def get_codes_by_type(self, code_type: CodeType) -> List[str]:
        """Get all codes of a specific type"""
        prefix = self._get_code_prefix(code_type)
        return [code for code in self.code_mappings.keys() if code.startswith(prefix)]
    
    def remove_code(self, code: str):
        """Remove a code from mappings"""
        code = code.upper()
        if code in self.code_mappings:
            del self.code_mappings[code]
        if code in self.reverse_mappings:
            del self.reverse_mappings[code]
    
    def clear_type(self, code_type: CodeType):
        """Clear all codes of a specific type"""
        prefix = self._get_code_prefix(code_type)
        codes_to_remove = [code for code in self.code_mappings.keys() 
                          if code.startswith(prefix)]
        
        for code in codes_to_remove:
            self.remove_code(code)
        
        self.counters[code_type] = 0
    
    def save_code_mappings(self):
        """Persist code mappings to disk"""
        try:
            # Ensure directory exists
            self.persistence_path.parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                'mappings': self.code_mappings,
                'counters': {k.value: v for k, v in self.counters.items()},
                'timestamp': datetime.now().isoformat()
            }
            
            with open(self.persistence_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
                
            logger.info(f"Saved {len(self.code_mappings)} code mappings to {self.persistence_path}")
            
        except Exception as e:
            logger.error(f"Failed to save code mappings: {e}")
    
    def load_code_mappings(self):
        """Load code mappings from disk"""
        if not self.persistence_path.exists():
            logger.info("No existing code mappings found")
            return
        
        try:
            with open(self.persistence_path, 'r') as f:
                data = json.load(f)
            
            self.code_mappings = data.get('mappings', {})
            
            # Restore counters
            saved_counters = data.get('counters', {})
            for code_type_str, count in saved_counters.items():
                code_type = CodeType(code_type_str)
                self.counters[code_type] = count
            
            logger.info(f"Loaded {len(self.code_mappings)} code mappings from {self.persistence_path}")
            
        except Exception as e:
            logger.error(f"Failed to load code mappings: {e}")
            self.code_mappings = {}
    
    def _update_mapping(self, code: str, item: Dict[str, Any]):
        """Update internal mappings for a code"""
        code = code.upper()
        self.code_mappings[code] = item.copy()
    
    def _get_code_prefix(self, code_type: CodeType) -> str:
        """Get the letter prefix for a code type"""
        prefixes = {
            CodeType.CALENDAR: 'C',
            CodeType.PRIORITY: 'P', 
            CodeType.COMMITMENT: 'M'
        }
        return prefixes[code_type]
    
    def _is_valid_code(self, code: str, code_type: CodeType) -> bool:
        """Check if a code is valid for the given type"""
        if not code:
            return False
        
        code = code.upper()
        prefix = self._get_code_prefix(code_type)
        
        if not code.startswith(prefix):
            return False
        
        try:
            int(code[1:])  # Check if numeric part is valid
            return True
        except ValueError:
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about current code assignments"""
        stats = {
            'total_codes': len(self.code_mappings),
            'by_type': {},
            'counters': {k.value: v for k, v in self.counters.items()}
        }
        
        for code_type in CodeType:
            prefix = self._get_code_prefix(code_type)
            count = len([c for c in self.code_mappings.keys() if c.startswith(prefix)])
            stats['by_type'][code_type.value] = count
        
        return stats
```

**Acceptance Criteria**:
- Sequential code generation for each type
- Code persistence across system restarts
- Efficient lookup by code
- Handle item updates without breaking codes

### Task G2: Command Parser Integration (2 hours)

**Objective**: Parse natural language commands to extract codes and actions

**File**: `backend/code_parser.py`
```python
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
        for pattern_name in self.patterns.keys():
            if pattern_name.startswith(partial_command.split()[0]):
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
```

**Acceptance Criteria**:
- Parse common command patterns accurately
- Extract codes and normalize to uppercase
- Handle multiple commands with pipe separator
- Provide helpful error messages and suggestions

### Task G3: State Integration (2 hours)

**Objective**: Integrate coding system with Agent E state management

**File**: `backend/state_integration.py`
```python
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
```

**Acceptance Criteria**:
- State updates include codes automatically
- Code-based commands execute correctly
- Integration doesn't break existing state management
- Performance remains acceptable with coding overhead

### Task G4: Testing & Validation (2 hours)

**Objective**: Comprehensive test suite and performance validation

**Implementation of test file already shown above in Test Acceptance Criteria**

**Additional Performance Tests**:
```python
class TestPerformance:
    """Test performance of coding system with large datasets"""
    
    def test_large_dataset_performance(self):
        """Code assignment should be fast even with many items"""
        import time
        
        manager = CodingManager()
        
        # Create 1000 priority items
        large_dataset = [
            {'text': f'Priority item {i}', 'status': 'pending'} 
            for i in range(1000)
        ]
        
        start_time = time.time()
        coded_items = manager.assign_codes(CodeType.PRIORITY, large_dataset)
        duration = time.time() - start_time
        
        assert len(coded_items) == 1000
        assert duration < 1.0  # Should complete in under 1 second
        assert all('code' in item for item in coded_items)
    
    def test_lookup_performance(self):
        """Code lookup should be O(1) fast"""
        import time
        
        manager = CodingManager()
        
        # Set up large dataset
        items = [{'text': f'Item {i}'} for i in range(10000)]
        coded_items = manager.assign_codes(CodeType.PRIORITY, items)
        
        # Test lookup performance
        start_time = time.time()
        for _ in range(1000):
            result = manager.get_by_code('P5000')
            assert result is not None
        duration = time.time() - start_time
        
        assert duration < 0.1  # 1000 lookups in under 0.1 seconds
```

**Acceptance Criteria**:
- All test suites pass completely
- Performance acceptable with 1000+ items
- Code persistence works correctly
- Integration tests validate end-to-end functionality

## Integration Requirements

### Agent E Backend Integration
- Integrate with `StateManager` class for state updates
- Use WebSocket broadcasting for code updates
- Maintain compatibility with existing API endpoints

### Agent F Dashboard Integration  
- Provide code information for display
- Enable code-based DOM targeting
- Support command execution with codes

### Performance Requirements
- Code assignment: <1 second for 1000 items
- Code lookup: O(1) performance
- Memory usage: <50MB for typical datasets
- Persistence operations: <100ms

## Files to Create

### Core Coding Files
```
backend/
├── coding_system.py        # Core CodingManager class
├── code_parser.py         # Command parsing logic
└── state_integration.py   # State management integration
```

### Test Files
```
tests/
├── test_coding_system.py   # Comprehensive test suite
├── test_code_parser.py    # Command parsing tests
└── test_performance.py    # Performance validation
```

### Data Files
```
data/
└── code_mappings.json     # Persistent code storage
```

## Success Criteria

### Core Functionality ✅
- [ ] Sequential code generation works for all types
- [ ] Code persistence survives system restarts
- [ ] Lookup by code is fast and accurate
- [ ] Command parsing handles all common patterns

### Performance Validation ✅
- [ ] Code assignment <1 second for 1000 items
- [ ] Code lookup in O(1) time
- [ ] Memory usage remains reasonable
- [ ] No performance degradation with large datasets

### Integration Validation ✅
- [ ] Integrates seamlessly with Agent E state management
- [ ] Provides clear interface for Agent F dashboard
- [ ] Supports Agent H command execution
- [ ] No conflicts with existing infrastructure

### Error Handling ✅
- [ ] Graceful handling of invalid codes
- [ ] Recovery from corrupted persistence files
- [ ] Clear error messages for invalid commands
- [ ] Robust handling of edge cases

## Delivery Checklist

Before marking Agent G complete:
- [ ] All test suites written and passing
- [ ] Coding system functional with persistence
- [ ] Command parser handles all required patterns
- [ ] Integration layer works with state management
- [ ] Performance benchmarks documented and met
- [ ] Code quality meets project standards
- [ ] Integration points clearly defined for Agent H

---

**Contact Agent G Team Lead for questions or Agent H integration requirements**  
**Dependencies**: Requires Agent E state management foundation