"""
Main FastAPI server for Agent E Backend API

References:
- Task specification: Task E1 in /Users/david.campos/VibeCode/AICoS-Lab/tasks/frontend_agent_e_backend.md
- Existing FastAPI patterns from codebase
- WebSocket implementation patterns from Slack bot

Features:
- FastAPI application with CORS middleware
- WebSocket endpoint for real-time state updates
- REST API integration with state management
- Health check and monitoring endpoints
- Integration with existing infrastructure
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import logging
import json
from contextlib import asynccontextmanager
from typing import Dict, Any

# Import our backend components
from .state_manager import get_state_manager, StateManager
from .websocket_manager import get_websocket_manager, WebSocketManager
from .api_routes import router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Application lifecycle management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager for startup and shutdown
    
    Handles:
    - State manager initialization
    - WebSocket manager setup
    - Graceful shutdown cleanup
    """
    # Startup
    logger.info("Starting Agent E Backend API...")
    
    # Initialize global components
    state_manager = get_state_manager()
    websocket_manager = get_websocket_manager()
    
    # Log startup information
    logger.info(f"State manager initialized: {type(state_manager).__name__}")
    logger.info(f"WebSocket manager initialized: {type(websocket_manager).__name__}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Agent E Backend API...")
    
    # Clean up connections
    if websocket_manager:
        connections = websocket_manager.get_connection_count()
        if connections > 0:
            logger.info(f"Cleaning up {connections} WebSocket connections...")
    
    logger.info("Backend API shutdown complete")

# Create FastAPI application
app = FastAPI(
    title="AICoS Frontend API",
    version="1.0.0",
    description="Backend API for AI Chief of Staff frontend dashboard",
    lifespan=lifespan
)

# CORS middleware for dashboard access
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",    # React development server
        "http://127.0.0.1:3000",   # Alternative localhost
        "http://localhost:8080",    # Alternative frontend port
        "http://127.0.0.1:8080",   # Alternative frontend port
        "http://localhost:8501",    # Streamlit dashboard
        "http://127.0.0.1:8501"    # Streamlit dashboard alternative
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router)

# Health check endpoint (separate from API routes for direct access)
@app.get("/health")
async def health_check():
    """
    Health check endpoint for service monitoring
    
    Returns:
        Basic health status and version information
    """
    return {
        "status": "healthy",
        "version": "1.0.0",
        "service": "Agent E Backend API",
        "components": {
            "state_manager": "operational",
            "websocket_manager": "operational",
            "api_routes": "operational"
        }
    }

# WebSocket endpoint for real-time updates
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time state synchronization
    
    Features:
    - Automatic initial state delivery
    - Real-time state update broadcasting
    - Graceful disconnection handling
    - Connection lifecycle management
    
    Args:
        websocket: FastAPI WebSocket connection
    """
    state_manager = get_state_manager()
    websocket_manager = get_websocket_manager()
    
    # Connect and send initial state
    await websocket_manager.connect(websocket, state_manager)
    
    try:
        # Keep connection alive and handle incoming messages
        while True:
            # WebSocket connections are primarily for receiving updates,
            # but we can handle ping/pong and client messages here if needed
            try:
                message = await websocket.receive_text()
                
                # Handle client messages (currently just log them)
                if message:
                    try:
                        client_data = json.loads(message)
                        logger.debug(f"Received client message: {client_data}")
                        
                        # Could handle client-specific requests here
                        # For now, just acknowledge receipt
                        await websocket.send_text(json.dumps({
                            "type": "ack",
                            "received": True,
                            "timestamp": state_manager.get_system_state().get("last_sync")
                        }))
                        
                    except json.JSONDecodeError:
                        # Non-JSON message, treat as ping
                        await websocket.send_text("pong")
                        
            except WebSocketDisconnect:
                # Client disconnected normally
                break
            except Exception as e:
                logger.warning(f"WebSocket message handling error: {e}")
                # Continue listening for other messages
                
    except WebSocketDisconnect:
        # Normal disconnection
        logger.debug("WebSocket client disconnected normally")
    except Exception as e:
        # Unexpected error
        logger.error(f"WebSocket connection error: {e}")
    finally:
        # Clean up connection
        await websocket_manager.disconnect(websocket, state_manager)

# Additional monitoring endpoints
@app.get("/ws/stats")
async def websocket_stats():
    """
    Get WebSocket connection statistics
    
    Returns:
        WebSocket manager statistics and connection info
    """
    websocket_manager = get_websocket_manager()
    return {
        "websocket_stats": websocket_manager.get_stats(),
        "connection_info": websocket_manager.get_connection_info(),
        "health": await websocket_manager.health_check()
    }

@app.get("/state")
async def get_complete_state():
    """
    Get complete application state (for debugging)
    
    Returns:
        Complete state manager state
    """
    state_manager = get_state_manager()
    return state_manager.get_state()

@app.get("/system/info")
async def get_system_info():
    """
    Get system information and statistics
    
    Returns:
        Combined system information from all components
    """
    state_manager = get_state_manager()
    websocket_manager = get_websocket_manager()
    
    return {
        "application": {
            "name": "Agent E Backend API",
            "version": "1.0.0",
            "fastapi_version": "0.115.4"
        },
        "state_manager": state_manager.get_stats(),
        "websocket_manager": websocket_manager.get_stats(),
        "endpoints": {
            "websocket": "/ws",
            "api_prefix": "/api",
            "health_check": "/health"
        }
    }

# Error handlers for better error reporting
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Custom HTTP exception handler with enhanced logging"""
    logger.warning(f"HTTP {exc.status_code}: {exc.detail}")
    return {
        "error": exc.detail,
        "status_code": exc.status_code,
        "timestamp": state_manager.get_system_state().get("last_sync") if 'state_manager' in locals() else None
    }

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    """Handle internal server errors"""
    logger.error(f"Internal server error: {exc}")
    return {
        "error": "Internal server error",
        "status_code": 500,
        "message": "An unexpected error occurred"
    }

# Startup message
@app.on_event("startup")
async def startup_message():
    """Log startup completion"""
    logger.info("Agent E Backend API is ready for connections")
    logger.info("WebSocket endpoint: /ws")
    logger.info("API endpoints: /api/*")
    logger.info("Health check: /health")

# Export the app instance for external access
__all__ = ["app", "get_state_manager"]