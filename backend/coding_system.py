"""
Coding System for Agent G Frontend Integration

References:
- Task specification: /Users/david.campos/VibeCode/AICoS-Lab/tasks/frontend_agent_g_coding.md
- Coding examples from /Users/david.campos/VibeCode/AICoS-Lab/cos-paper-dense.html
- State management patterns from backend/state_manager.py

Features:
- Automatic C1/P1/M1 code generation for rapid keyboard navigation
- Bidirectional mapping for fast code-to-item lookup (O(1) performance)
- Persistence across system restarts
- Support for item updates without breaking code assignments
"""

import json
import logging
from enum import Enum
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
from datetime import datetime

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
        if not items:
            return []
            
        coded_items = []
        existing_codes = set()
        prefix = self._get_code_prefix(code_type)
        
        # Clear existing codes of this type from mappings
        self.clear_type(code_type)
        
        # First pass: identify items that might already have codes 
        # and collect items that need new codes
        items_needing_codes = []
        for item in items:
            item_copy = item.copy()
            if 'code' in item and self._is_valid_code(item['code'], code_type):
                # Validate existing code is not already taken
                if item['code'] not in existing_codes:
                    existing_codes.add(item['code'])
                    self._update_mapping(item['code'], item_copy)
                    coded_items.append(item_copy)
                else:
                    # Code conflict, needs new code
                    if 'code' in item_copy:
                        del item_copy['code']
                    items_needing_codes.append(item_copy)
            else:
                # Remove invalid code
                if 'code' in item_copy:
                    del item_copy['code']
                items_needing_codes.append(item_copy)
        
        # Second pass: assign codes to items without valid codes
        counter = 1
        for item in items_needing_codes:
            # Find next available code
            while f"{prefix}{counter}" in existing_codes:
                counter += 1
            
            new_code = f"{prefix}{counter}"
            item['code'] = new_code
            existing_codes.add(new_code)
            
            self._update_mapping(new_code, item)
            coded_items.append(item)
            counter += 1
        
        # Update counter for this type
        if existing_codes:
            max_num = max(int(code[1:]) for code in existing_codes if code.startswith(prefix))
            self.counters[code_type] = max_num
        
        # Sort coded_items to maintain consistent order (by code number)
        coded_items.sort(key=lambda x: int(x['code'][1:]))
        
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