"""
WebSocket connection manager for real-time state broadcasting

References:
- Task specification: Task E3 in /Users/david.campos/VibeCode/AICoS-Lab/tasks/frontend_agent_e_backend.md
- FastAPI WebSocket patterns from existing Slack bot implementation
- WebSocket connection management for concurrent clients

Features:
- Connection lifecycle management
- Automatic initial state delivery
- Graceful disconnection handling
- Performance monitoring for lab deployment
"""

from fastapi import WebSocket, WebSocketDisconnect
import json
import logging
import asyncio
from typing import List, Dict, Any
import time
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

class WebSocketManager:
    """
    Manages WebSocket connections for real-time state broadcasting
    
    Features:
    - Multi-client connection management
    - Automatic initial state delivery
    - Graceful disconnection handling
    - Performance monitoring for response times
    """
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.connection_metadata: Dict[WebSocket, Dict[str, Any]] = {}
        self._stats = {
            "connections_total": 0,
            "connections_active": 0,
            "messages_sent": 0,
            "disconnections_clean": 0,
            "disconnections_error": 0
        }
        
        logger.info("WebSocketManager initialized for real-time broadcasting")
    
    async def connect(self, websocket: WebSocket, state_manager) -> None:
        """
        Accept WebSocket connection and send initial state
        
        Args:
            websocket: FastAPI WebSocket connection
            state_manager: StateManager instance for initial state
        """
        try:
            await websocket.accept()
            self.active_connections.append(websocket)
            
            # Track connection metadata
            self.connection_metadata[websocket] = {
                "connected_at": time.time(),
                "messages_sent": 0,
                "last_message_at": None
            }
            
            # Update statistics
            self._stats["connections_total"] += 1
            self._stats["connections_active"] = len(self.active_connections)
            
            # Register with state manager for broadcasts
            state_manager.add_observer(websocket)
            
            # Send initial state immediately
            initial_state = state_manager.get_state()
            await self._send_to_connection(websocket, json.dumps(initial_state))
            
            logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")
            
        except Exception as e:
            logger.error(f"Error during WebSocket connection: {e}")
            await self.disconnect(websocket, state_manager, error=True)
            raise
    
    async def disconnect(self, websocket: WebSocket, state_manager, error: bool = False) -> None:
        """
        Remove WebSocket connection with cleanup
        
        Args:
            websocket: WebSocket connection to remove
            state_manager: StateManager to remove observer from
            error: Whether disconnection was due to an error
        """
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            
            # Remove from state manager observers
            state_manager.remove_observer(websocket)
            
            # Clean up metadata
            if websocket in self.connection_metadata:
                connection_info = self.connection_metadata.pop(websocket)
                duration = time.time() - connection_info["connected_at"]
                logger.debug(f"Connection lasted {duration:.2f}s, sent {connection_info['messages_sent']} messages")
            
            # Update statistics
            self._stats["connections_active"] = len(self.active_connections)
            if error:
                self._stats["disconnections_error"] += 1
            else:
                self._stats["disconnections_clean"] += 1
        
        logger.info(f"WebSocket disconnected. Remaining connections: {len(self.active_connections)}")
    
    async def broadcast(self, message: str) -> None:
        """
        Send message to all connected clients with error handling
        
        Args:
            message: JSON message to broadcast
        """
        if not self.active_connections:
            return
            
        disconnected = []
        sent_count = 0
        
        # Send to all active connections
        for connection in list(self.active_connections):  # Copy to avoid modification during iteration
            try:
                await self._send_to_connection(connection, message)
                sent_count += 1
            except Exception as e:
                logger.debug(f"Failed to send to connection: {e}")
                disconnected.append(connection)
        
        # Clean up failed connections
        for connection in disconnected:
            await self.disconnect(connection, None, error=True)  # Note: state_manager is None here
        
        # Update statistics
        self._stats["messages_sent"] += sent_count
        
        if disconnected:
            logger.warning(f"Removed {len(disconnected)} failed connections during broadcast")
    
    async def _send_to_connection(self, websocket: WebSocket, message: str) -> None:
        """
        Send message to specific WebSocket connection with timing
        
        Args:
            websocket: Target WebSocket connection
            message: Message to send
            
        Raises:
            Exception: If message sending fails
        """
        start_time = time.time()
        
        try:
            await websocket.send_text(message)
            
            # Update connection metadata
            if websocket in self.connection_metadata:
                metadata = self.connection_metadata[websocket]
                metadata["messages_sent"] += 1
                metadata["last_message_at"] = time.time()
            
            # Log slow sends for performance monitoring
            send_time = (time.time() - start_time) * 1000
            if send_time > 50:  # Log if over 50ms threshold
                logger.warning(f"Slow WebSocket send: {send_time:.2f}ms")
                
        except Exception as e:
            logger.debug(f"WebSocket send failed: {e}")
            raise
    
    def get_connection_count(self) -> int:
        """Get current number of active connections"""
        return len(self.active_connections)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get WebSocket manager statistics
        
        Returns:
            Dict with connection and performance statistics
        """
        return {
            **self._stats,
            "active_connections": len(self.active_connections),
            "average_messages_per_connection": (
                self._stats["messages_sent"] / max(self._stats["connections_total"], 1)
            )
        }
    
    def get_connection_info(self) -> List[Dict[str, Any]]:
        """
        Get information about all active connections (for debugging)
        
        Returns:
            List of connection metadata
        """
        info = []
        current_time = time.time()
        
        for websocket in self.active_connections:
            if websocket in self.connection_metadata:
                metadata = self.connection_metadata[websocket]
                info.append({
                    "duration_seconds": current_time - metadata["connected_at"],
                    "messages_sent": metadata["messages_sent"],
                    "last_message_ago": (
                        current_time - metadata["last_message_at"] 
                        if metadata["last_message_at"] else None
                    )
                })
        
        return info
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on all connections
        
        Returns:
            Health status of WebSocket manager
        """
        healthy_connections = 0
        
        # Test each connection with a ping
        for websocket in list(self.active_connections):
            try:
                await websocket.ping()
                healthy_connections += 1
            except Exception:
                # Connection is dead, will be cleaned up on next operation
                pass
        
        return {
            "healthy": healthy_connections == len(self.active_connections),
            "active_connections": len(self.active_connections),
            "healthy_connections": healthy_connections,
            "total_messages_sent": self._stats["messages_sent"]
        }

# Global WebSocket manager instance (singleton for lab deployment)
_websocket_manager_instance = None

def get_websocket_manager() -> WebSocketManager:
    """
    Get global WebSocket manager instance (singleton pattern)
    
    Returns:
        WebSocketManager: Global WebSocket manager instance
    """
    global _websocket_manager_instance
    
    if _websocket_manager_instance is None:
        _websocket_manager_instance = WebSocketManager()
        logger.info("Created global WebSocketManager instance")
    
    return _websocket_manager_instance