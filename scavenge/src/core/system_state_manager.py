#!/usr/bin/env python3
"""
SIMPLE STATE MANAGER
Provides basic cursor tracking and state persistence for collectors
"""
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path

class SimpleStateManager:
    """
    Simple state manager for tracking collection cursors and basic statistics.
    Supports Slack, Calendar, and Employee collectors with atomic operations.
    """
    
    def __init__(self, state_dir=None):
        """Initialize state manager with configurable state directory"""
        # Auto-detect base path from current file location
        self.base_path = Path(__file__).parent.parent.parent
        
        # Use provided state directory or default to data/state/
        if state_dir:
            self.state_dir = Path(state_dir)
        else:
            self.state_dir = self.base_path / 'data' / 'state'
        
        # Ensure state directory exists
        self.state_dir.mkdir(parents=True, exist_ok=True)
        
        # State file location
        self.state_file = self.state_dir / 'cursors.json'
        
        # Supported collector sources
        self.supported_sources = {'slack', 'calendar', 'employees'}
        
        # Load or create initial state
        self.state = self._load_or_create_state()
    
    def _load_or_create_state(self):
        """Load existing state or create new empty state"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                # If state file is corrupted, create fresh state
                pass
        
        # Create fresh state structure
        return {
            'last_updated': datetime.now().isoformat(),
            'sources': {
                source: {
                    'cursor': None,
                    'last_run': None,
                    'last_stats': {}
                } for source in self.supported_sources
            }
        }
    
    def _atomic_write(self, data):
        """Atomically write state data to prevent corruption"""
        # Write to temporary file first
        with tempfile.NamedTemporaryFile(
            mode='w',
            dir=self.state_dir,
            prefix='cursors_',
            suffix='.tmp',
            delete=False
        ) as tmp_file:
            json.dump(data, tmp_file, indent=2)
            tmp_path = tmp_file.name
        
        # Atomic move to actual state file
        os.rename(tmp_path, self.state_file)
    
    def _validate_source(self, source):
        """Validate that source is supported"""
        if source not in self.supported_sources:
            raise ValueError(f"Unsupported source '{source}'. Must be one of: {self.supported_sources}")
    
    def get_cursor(self, source):
        """
        Get the last cursor/position for a source
        
        Args:
            source (str): Source name ('slack', 'calendar', 'employees')
            
        Returns:
            str or None: Last cursor value or None if never set
        """
        self._validate_source(source)
        return self.state['sources'][source]['cursor']
    
    def update_cursor(self, source, cursor):
        """
        Update cursor for a source after successful collection
        
        Args:
            source (str): Source name ('slack', 'calendar', 'employees')
            cursor (str): New cursor value (timestamp, token, etc.)
        """
        self._validate_source(source)
        
        # Update cursor and last_updated timestamp
        self.state['sources'][source]['cursor'] = cursor
        self.state['last_updated'] = datetime.now().isoformat()
        
        # Atomic write
        self._atomic_write(self.state)
    
    def get_last_run(self, source):
        """
        Get timestamp of last collection run for a source
        
        Args:
            source (str): Source name ('slack', 'calendar', 'employees')
            
        Returns:
            str or None: ISO timestamp of last run or None if never run
        """
        self._validate_source(source)
        return self.state['sources'][source]['last_run']
    
    def update_last_run(self, source, timestamp=None):
        """
        Update last run timestamp for a source
        
        Args:
            source (str): Source name ('slack', 'calendar', 'employees')
            timestamp (str, optional): ISO timestamp, defaults to current time
        """
        self._validate_source(source)
        
        if timestamp is None:
            timestamp = datetime.now().isoformat()
        
        # Update last run and global last_updated
        self.state['sources'][source]['last_run'] = timestamp
        self.state['last_updated'] = datetime.now().isoformat()
        
        # Atomic write
        self._atomic_write(self.state)
    
    def get_collection_stats(self, source):
        """
        Get collection statistics for a source
        
        Args:
            source (str): Source name ('slack', 'calendar', 'employees')
            
        Returns:
            dict: Statistics dictionary
        """
        self._validate_source(source)
        return self.state['sources'][source]['last_stats'].copy()
    
    def update_collection_stats(self, source, stats):
        """
        Update collection statistics for a source
        
        Args:
            source (str): Source name ('slack', 'calendar', 'employees')
            stats (dict): Statistics to store
        """
        self._validate_source(source)
        
        if not isinstance(stats, dict):
            raise ValueError("Stats must be a dictionary")
        
        # Update stats and timestamp
        self.state['sources'][source]['last_stats'] = stats.copy()
        self.state['last_updated'] = datetime.now().isoformat()
        
        # Atomic write
        self._atomic_write(self.state)
    
    def get_state_summary(self):
        """
        Get summary of all collector states
        
        Returns:
            dict: Summary with last runs, cursors, and basic stats
        """
        summary = {
            'last_updated': self.state['last_updated'],
            'sources': {}
        }
        
        for source in self.supported_sources:
            source_data = self.state['sources'][source]
            summary['sources'][source] = {
                'has_cursor': source_data['cursor'] is not None,
                'last_run': source_data['last_run'],
                'stats_count': len(source_data['last_stats'])
            }
        
        return summary
    
    def detect_changes(self, source, new_stats):
        """
        Simple change detection by comparing current stats with new stats
        
        Args:
            source (str): Source name ('slack', 'calendar', 'employees')  
            new_stats (dict): New statistics to compare
            
        Returns:
            dict: Changes detected with 'added', 'changed', 'removed' keys
        """
        self._validate_source(source)
        
        if not isinstance(new_stats, dict):
            raise ValueError("New stats must be a dictionary")
        
        old_stats = self.get_collection_stats(source)
        
        changes = {
            'added': {},
            'changed': {},
            'removed': {}
        }
        
        # Find added and changed keys
        for key, new_value in new_stats.items():
            if key not in old_stats:
                changes['added'][key] = new_value
            elif old_stats[key] != new_value:
                changes['changed'][key] = {
                    'old': old_stats[key],
                    'new': new_value
                }
        
        # Find removed keys
        for key in old_stats:
            if key not in new_stats:
                changes['removed'][key] = old_stats[key]
        
        return changes
    
    def reset_source(self, source):
        """
        Reset all state for a source (cursor, last_run, stats)
        
        Args:
            source (str): Source name to reset
        """
        self._validate_source(source)
        
        # Reset to initial state
        self.state['sources'][source] = {
            'cursor': None,
            'last_run': None,
            'last_stats': {}
        }
        self.state['last_updated'] = datetime.now().isoformat()
        
        # Atomic write
        self._atomic_write(self.state)


if __name__ == "__main__":
    # Example usage and testing
    print("🔄 Simple State Manager - Testing")
    print("=" * 40)
    
    # Initialize state manager
    state_manager = SimpleStateManager()
    print(f"✅ Initialized state manager at: {state_manager.state_file}")
    
    # Show initial state
    summary = state_manager.get_state_summary()
    print(f"\n📊 Initial State Summary:")
    print(f"  Last Updated: {summary['last_updated']}")
    for source, info in summary['sources'].items():
        print(f"  {source}: cursor={info['has_cursor']}, last_run={info['last_run']}")
    
    # Test cursor operations
    print(f"\n🔄 Testing Cursor Operations:")
    test_cursor = "2024-01-15T10:30:00Z"
    state_manager.update_cursor('slack', test_cursor)
    retrieved_cursor = state_manager.get_cursor('slack')
    print(f"  Set Slack cursor: {test_cursor}")
    print(f"  Retrieved cursor: {retrieved_cursor}")
    print(f"  ✅ Match: {test_cursor == retrieved_cursor}")
    
    # Test stats operations
    print(f"\n📈 Testing Stats Operations:")
    test_stats = {
        'channels_discovered': 45,
        'messages_collected': 1234,
        'users_discovered': 89
    }
    state_manager.update_collection_stats('slack', test_stats)
    retrieved_stats = state_manager.get_collection_stats('slack')
    print(f"  Stored stats: {test_stats}")
    print(f"  Retrieved stats: {retrieved_stats}")
    print(f"  ✅ Match: {test_stats == retrieved_stats}")
    
    # Test change detection
    print(f"\n🔍 Testing Change Detection:")
    new_stats = {
        'channels_discovered': 47,  # Changed
        'messages_collected': 1234,  # Same
        'users_discovered': 89,  # Same
        'new_field': 'test'  # Added
    }
    changes = state_manager.detect_changes('slack', new_stats)
    print(f"  Changes detected: {changes}")
    
    # Update last run
    state_manager.update_last_run('slack')
    print(f"  ✅ Updated last run timestamp")
    
    # Final summary
    final_summary = state_manager.get_state_summary()
    print(f"\n📊 Final State Summary:")
    print(f"  Last Updated: {final_summary['last_updated']}")
    for source, info in final_summary['sources'].items():
        print(f"  {source}: cursor={info['has_cursor']}, last_run={bool(info['last_run'])}, stats={info['stats_count']}")
    
    print(f"\n✅ All tests completed successfully!")