"""
In-memory state management for Agent E Backend API

References:
- Task specification: Task E2 in /Users/david.campos/VibeCode/AICoS-Lab/tasks/frontend_agent_e_backend.md
- Existing state management patterns in src/core/state.py
- Pydantic validation patterns from existing codebase

Features:
- Atomic state updates with validation
- Observer pattern for WebSocket broadcasting  
- Thread-safe operations for concurrent access
- Lab-grade simplicity - no external dependencies like Redis
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable
from pydantic import BaseModel, field_validator
import threading
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

class SystemState(BaseModel):
    """System state with validation"""
    status: str = "IDLE"
    progress: int = 0
    last_sync: Optional[str] = None
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        valid_statuses = ["IDLE", "COLLECTING", "PROCESSING", "ERROR"]
        if v not in valid_statuses:
            raise ValueError(f"Status must be one of {valid_statuses}")
        return v
    
    @field_validator('progress')
    @classmethod
    def validate_progress(cls, v):
        if not 0 <= v <= 100:
            raise ValueError("Progress must be between 0 and 100")
        return v

class CalendarEvent(BaseModel):
    """Calendar event representation"""
    id: str
    title: str
    start: str
    end: str
    attendees: Optional[List[str]] = []

class Priority(BaseModel):
    """Priority item representation"""
    id: str
    title: str
    urgency: str = "medium"  # low, medium, high
    due_date: Optional[str] = None

class Commitment(BaseModel):
    """Commitment representation"""
    id: str
    description: str
    assignee: str
    due_date: Optional[str] = None
    status: str = "pending"  # pending, completed, overdue

class StateManager:
    """
    Thread-safe in-memory state manager with WebSocket broadcasting
    
    Features:
    - Atomic state updates with validation
    - Observer pattern for real-time updates
    - Thread-safe operations
    - Memory efficient for lab deployment
    """
    
    def __init__(self):
        self._lock = threading.RLock()  # Reentrant lock for nested operations
        self._state = {
            "system": SystemState().dict(),
            "calendar": [],  # List of CalendarEvent objects
            "priorities": [],  # List of Priority objects
            "commitments": {"owe": [], "owed": []},  # Commitments owed/by user
            "active_brief": None  # Current brief being displayed
        }
        self._observers = set()  # WebSocket connections for broadcasting
        self._update_callbacks = []  # Additional update callbacks
        
        # Performance monitoring
        self._stats = {
            "state_updates": 0,
            "broadcast_count": 0,
            "observer_connections": 0,
            "validation_errors": 0
        }
        
        logger.info("StateManager initialized with lab-grade configuration")
    
    def get_state(self) -> Dict[str, Any]:
        """Get current complete state (thread-safe)"""
        with self._lock:
            return json.loads(json.dumps(self._state))  # Deep copy
    
    def get_system_state(self) -> Dict[str, Any]:
        """Get just the system state portion"""
        with self._lock:
            return json.loads(json.dumps(self._state["system"]))
    
    async def update_system_status(self, status: Optional[str] = None, 
                                 progress: Optional[int] = None) -> None:
        """
        Update system status with validation and broadcasting
        
        Args:
            status: New system status (optional)
            progress: New progress value (optional)
        """
        with self._lock:
            current_system = self._state["system"].copy()
            
            # Update fields if provided
            if status is not None:
                current_system["status"] = status
            if progress is not None:
                current_system["progress"] = progress
            
            # Update last sync time
            current_system["last_sync"] = datetime.now().isoformat()
            
            # Validate the updated state
            try:
                validated_state = SystemState(**current_system)
                self._state["system"] = validated_state.model_dump()
                self._stats["state_updates"] += 1
                
                logger.debug(f"Updated system state: status={status}, progress={progress}")
                
            except ValueError as e:
                self._stats["validation_errors"] += 1
                logger.error(f"State validation failed: {e}")
                raise ValueError(f"Invalid state update: {e}")
        
        # Broadcast update (outside lock to prevent deadlock)
        await self._broadcast_state_update()
    
    async def update_calendar_events(self, events: List[Dict[str, Any]]) -> None:
        """Update calendar events with validation"""
        validated_events = []
        
        for event_data in events:
            try:
                event = CalendarEvent(**event_data)
                validated_events.append(event.model_dump())
            except ValueError as e:
                logger.warning(f"Invalid calendar event skipped: {e}")
                self._stats["validation_errors"] += 1
                continue
        
        with self._lock:
            self._state["calendar"] = validated_events
            self._stats["state_updates"] += 1
        
        await self._broadcast_state_update()
    
    async def update_priorities(self, priorities: List[Dict[str, Any]]) -> None:
        """Update priority list with validation"""
        validated_priorities = []
        
        for priority_data in priorities:
            try:
                priority = Priority(**priority_data)
                validated_priorities.append(priority.model_dump())
            except ValueError as e:
                logger.warning(f"Invalid priority skipped: {e}")
                self._stats["validation_errors"] += 1
                continue
        
        with self._lock:
            self._state["priorities"] = validated_priorities
            self._stats["state_updates"] += 1
        
        await self._broadcast_state_update()
    
    async def update_commitments(self, commitments: Dict[str, List[Dict[str, Any]]]) -> None:
        """Update commitments (owe/owed) with validation"""
        validated_commitments = {"owe": [], "owed": []}
        
        for category in ["owe", "owed"]:
            if category in commitments:
                for commitment_data in commitments[category]:
                    try:
                        commitment = Commitment(**commitment_data)
                        validated_commitments[category].append(commitment.model_dump())
                    except ValueError as e:
                        logger.warning(f"Invalid {category} commitment skipped: {e}")
                        self._stats["validation_errors"] += 1
                        continue
        
        with self._lock:
            self._state["commitments"] = validated_commitments
            self._stats["state_updates"] += 1
        
        await self._broadcast_state_update()
    
    async def set_active_brief(self, brief_data: Optional[Dict[str, Any]]) -> None:
        """Set the currently active brief"""
        with self._lock:
            self._state["active_brief"] = brief_data
            self._stats["state_updates"] += 1
        
        await self._broadcast_state_update()
    
    async def update_state(self, key: str, value: Any) -> None:
        """
        Generic state update method for Agent H integration
        
        Args:
            key: State key to update (supports nested keys with '/' separator)
            value: New value for the state key
        """
        with self._lock:
            # Handle nested keys like 'system/status' or 'system/progress'
            if '/' in key:
                parts = key.split('/')
                if len(parts) == 2 and parts[0] == 'system':
                    # System state updates
                    system_key = parts[1]
                    current_system = self._state["system"].copy()
                    current_system[system_key] = value
                    
                    # Validate system state
                    try:
                        validated_state = SystemState(**current_system)
                        self._state["system"] = validated_state.model_dump()
                    except ValueError as e:
                        logger.error(f"System state validation failed: {e}")
                        raise ValueError(f"Invalid system state update: {e}")
                else:
                    # Other nested keys - just update directly (careful with validation)
                    current = self._state
                    for part in parts[:-1]:
                        if part not in current:
                            current[part] = {}
                        current = current[part]
                    current[parts[-1]] = value
            else:
                # Direct state key update
                if key in ['calendar', 'priorities', 'commitments', 'active_brief']:
                    self._state[key] = value
                elif key.endswith('_stats'):
                    # Allow stats updates
                    self._state[key] = value
                else:
                    # Other direct keys
                    self._state[key] = value
            
            self._stats["state_updates"] += 1
        
        await self._broadcast_state_update()
    
    def add_observer(self, observer) -> None:
        """
        Add WebSocket observer for state updates
        
        Args:
            observer: WebSocket connection object
        """
        with self._lock:
            self._observers.add(observer)
            self._stats["observer_connections"] = len(self._observers)
            
        logger.debug(f"Added observer, total: {len(self._observers)}")
    
    def remove_observer(self, observer) -> None:
        """
        Remove WebSocket observer
        
        Args:
            observer: WebSocket connection object to remove
        """
        with self._lock:
            self._observers.discard(observer)
            self._stats["observer_connections"] = len(self._observers)
            
        logger.debug(f"Removed observer, remaining: {len(self._observers)}")
    
    async def _broadcast_state_update(self) -> None:
        """
        Broadcast state update to all connected WebSocket clients
        
        Uses observer pattern to notify all registered WebSocket connections
        Handles disconnected clients gracefully
        """
        if not self._observers:
            return
        
        # Get current state (thread-safe)
        current_state = self.get_state()
        message = json.dumps(current_state)
        
        # Track disconnected observers for cleanup
        disconnected = set()
        
        # Broadcast to all observers
        for observer in list(self._observers):  # Create copy to avoid modification during iteration
            try:
                await observer.send_text(message)
            except Exception as e:
                logger.debug(f"Observer disconnected during broadcast: {e}")
                disconnected.add(observer)
        
        # Clean up disconnected observers
        if disconnected:
            with self._lock:
                self._observers -= disconnected
                self._stats["observer_connections"] = len(self._observers)
            
            logger.debug(f"Cleaned up {len(disconnected)} disconnected observers")
        
        self._stats["broadcast_count"] += 1
    
    def add_update_callback(self, callback: Callable) -> None:
        """Add callback to be called on state updates"""
        self._update_callbacks.append(callback)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        with self._lock:
            return {
                **self._stats,
                "current_observers": len(self._observers),
                "state_size_bytes": len(json.dumps(self._state)),
                "last_update": self._state["system"].get("last_sync")
            }
    
    async def reset_state(self) -> None:
        """Reset state to initial values (for testing)"""
        with self._lock:
            self._state = {
                "system": SystemState().model_dump(),
                "calendar": [],
                "priorities": [],
                "commitments": {"owe": [], "owed": []},
                "active_brief": None
            }
            self._stats["state_updates"] += 1
        
        await self._broadcast_state_update()
        logger.info("State reset to initial values")

# Global state manager instance (singleton pattern for lab deployment)
_state_manager_instance = None
_state_manager_lock = threading.Lock()

def get_state_manager() -> StateManager:
    """
    Get global state manager instance (singleton pattern)
    
    Returns:
        StateManager: Global state manager instance
    """
    global _state_manager_instance
    
    if _state_manager_instance is None:
        with _state_manager_lock:
            if _state_manager_instance is None:
                _state_manager_instance = StateManager()
                logger.info("Created global StateManager instance")
    
    return _state_manager_instance

def reset_state_manager() -> None:
    """Reset global state manager (for testing)"""
    global _state_manager_instance
    
    with _state_manager_lock:
        _state_manager_instance = None
        logger.info("Reset global StateManager instance")