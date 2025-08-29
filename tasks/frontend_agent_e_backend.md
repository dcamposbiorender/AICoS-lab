# Agent E: Backend API & WebSocket Server - Phase 4.5 Frontend

**Date Created**: 2025-08-28  
**Owner**: Agent E (Backend Infrastructure Team)  
**Status**: PENDING  
**Estimated Time**: 8 hours (1 day)  
**Dependencies**: Existing SearchDatabase (340K+ records), working collectors

## Executive Summary

Build minimal FastAPI server with WebSocket support for real-time state synchronization. Focus on lab-grade simplicity - no external dependencies like Redis, just in-memory state management for single-user deployment.

**Core Philosophy**: Leverage existing infrastructure (SearchDatabase, collectors) through simple API layer. No over-engineering - just enough to connect dashboard and Slack bot with real-time updates.

## Test Acceptance Criteria (Write FIRST)

### File: `tests/test_backend_api.py`
```python
import pytest
import asyncio
import json
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocketDisconnect
from backend.server import app, system_state, get_state_manager

class TestWebSocketConnection:
    """Test WebSocket connectivity and initial state delivery"""
    
    def test_websocket_connects_successfully(self):
        """WebSocket connection establishes and receives initial state"""
        with TestClient(app) as client:
            with client.websocket_connect("/ws") as websocket:
                # Should receive initial state immediately
                data = websocket.receive_json()
                
                # Verify required state structure
                assert "system" in data
                assert "calendar" in data  
                assert "priorities" in data
                assert "commitments" in data
                
                # System state should have required fields
                assert "status" in data["system"]
                assert "progress" in data["system"]
                assert "last_sync" in data["system"]
    
    def test_multiple_websocket_clients(self):
        """Multiple WebSocket clients can connect simultaneously"""
        with TestClient(app) as client:
            with client.websocket_connect("/ws") as ws1:
                with client.websocket_connect("/ws") as ws2:
                    # Both should receive initial state
                    state1 = ws1.receive_json()
                    state2 = ws2.receive_json()
                    
                    assert state1 == state2
                    assert "system" in state1

class TestStateBroadcasting:
    """Test real-time state updates broadcast to all clients"""
    
    def test_state_update_broadcasts_to_all_clients(self):
        """State changes broadcast to all connected WebSocket clients"""
        with TestClient(app) as client:
            with client.websocket_connect("/ws") as ws1:
                with client.websocket_connect("/ws") as ws2:
                    # Skip initial state messages
                    ws1.receive_json()
                    ws2.receive_json()
                    
                    # Update state via API
                    response = client.post("/api/system/status", 
                                         json={"status": "COLLECTING", "progress": 25})
                    assert response.status_code == 200
                    
                    # Both clients should receive the update
                    update1 = ws1.receive_json()
                    update2 = ws2.receive_json()
                    
                    assert update1["system"]["status"] == "COLLECTING"
                    assert update1["system"]["progress"] == 25
                    assert update1 == update2
    
    def test_collection_progress_updates(self):
        """Collection progress updates broadcast in real-time"""
        with TestClient(app) as client:
            with client.websocket_connect("/ws") as websocket:
                websocket.receive_json()  # Skip initial state
                
                # Simulate collection progress
                for progress in [10, 25, 50, 75, 100]:
                    response = client.post("/api/system/status",
                                         json={"status": "COLLECTING", "progress": progress})
                    assert response.status_code == 200
                    
                    update = websocket.receive_json()
                    assert update["system"]["progress"] == progress

class TestRESTAPIEndpoints:
    """Test REST API functionality"""
    
    def test_system_status_endpoint(self):
        """GET /api/system/status returns current system state"""
        with TestClient(app) as client:
            response = client.get("/api/system/status")
            assert response.status_code == 200
            
            data = response.json()
            assert "status" in data
            assert "progress" in data
            assert "last_sync" in data
    
    def test_command_execution_endpoint(self):
        """POST /api/command processes commands and updates state"""
        with TestClient(app) as client:
            # Test simple approve command
            response = client.post("/api/command", 
                                 json={"command": "approve P7"})
            assert response.status_code == 200
            
            result = response.json()
            assert "action" in result
            assert "target" in result
            assert result["action"] == "approve"
            assert result["target"] == "P7"
    
    def test_trigger_collection_endpoint(self):
        """GET /api/trigger_collection starts data collection"""
        with TestClient(app) as client:
            response = client.get("/api/trigger_collection")
            assert response.status_code == 200
            
            # Should change system status
            status_response = client.get("/api/system/status")
            status_data = status_response.json()
            assert status_data["status"] in ["COLLECTING", "IDLE"]

class TestStateManagement:
    """Test in-memory state management"""
    
    def test_state_persistence_during_session(self):
        """State persists across API calls within session"""
        with TestClient(app) as client:
            # Update system status
            client.post("/api/system/status", json={"status": "COLLECTING"})
            
            # Verify persistence
            response = client.get("/api/system/status")
            data = response.json()
            assert data["status"] == "COLLECTING"
    
    def test_state_validation(self):
        """Invalid state updates are rejected"""
        with TestClient(app) as client:
            # Invalid status value
            response = client.post("/api/system/status", 
                                 json={"status": "INVALID_STATUS"})
            assert response.status_code == 400
            
            # Invalid progress value
            response = client.post("/api/system/status",
                                 json={"progress": 150})  # Over 100%
            assert response.status_code == 400

class TestErrorHandling:
    """Test error handling and recovery"""
    
    def test_websocket_disconnection_handling(self):
        """WebSocket disconnections handled gracefully"""
        with TestClient(app) as client:
            with client.websocket_connect("/ws") as websocket:
                websocket.receive_json()
                
                # Force disconnection by closing
                websocket.close()
                
                # Server should handle this gracefully - no crashes
                response = client.get("/api/system/status")
                assert response.status_code == 200
    
    def test_invalid_command_handling(self):
        """Invalid commands return appropriate errors"""
        with TestClient(app) as client:
            response = client.post("/api/command",
                                 json={"command": "invalid_command xyz"})
            assert response.status_code == 400
            
            result = response.json()
            assert "error" in result
```

## Implementation Tasks

### Task E1: FastAPI Foundation (2 hours)

**Objective**: Set up basic FastAPI application with CORS and health check

**File**: `backend/server.py`
```python
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import logging

app = FastAPI(title="AICoS Frontend API", version="1.0.0")

# CORS middleware for dashboard access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "version": "1.0.0"}
```

**Acceptance Criteria**:
- FastAPI app starts without errors
- CORS configured for dashboard access
- Health check endpoint responds
- Proper logging configured

### Task E2: In-Memory State Management (2 hours)

**Objective**: Create state management system with validation and atomic updates

**File**: `backend/state_manager.py`
```python
import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, validator

class SystemState(BaseModel):
    status: str = "IDLE"
    progress: int = 0
    last_sync: Optional[str] = None
    
    @validator('status')
    def validate_status(cls, v):
        valid_statuses = ["IDLE", "COLLECTING", "PROCESSING", "ERROR"]
        if v not in valid_statuses:
            raise ValueError(f"Status must be one of {valid_statuses}")
        return v
    
    @validator('progress')
    def validate_progress(cls, v):
        if not 0 <= v <= 100:
            raise ValueError("Progress must be between 0 and 100")
        return v

class StateManager:
    def __init__(self):
        self.state = {
            "system": SystemState().dict(),
            "calendar": [],
            "priorities": [],
            "commitments": {"owe": [], "owed": []},
            "active_brief": None
        }
        self.observers = []  # WebSocket connections
    
    async def update_state(self, path: str, value: Any):
        """Update state and broadcast to observers"""
        # Atomic update
        keys = path.split('/')
        current = self.state
        for key in keys[:-1]:
            current = current[key]
        current[keys[-1]] = value
        
        # Broadcast update
        await self.broadcast_update()
    
    async def broadcast_update(self):
        """Send state update to all connected WebSocket clients"""
        if not self.observers:
            return
            
        message = json.dumps(self.state)
        disconnected = []
        
        for websocket in self.observers:
            try:
                await websocket.send_text(message)
            except:
                disconnected.append(websocket)
        
        # Remove disconnected clients
        for ws in disconnected:
            self.observers.remove(ws)
```

**Acceptance Criteria**:
- State structure matches requirements
- Atomic state updates work correctly
- State validation prevents invalid data
- Observer pattern for WebSocket broadcasting

### Task E3: WebSocket Broadcasting System (2 hours)

**Objective**: Implement WebSocket endpoint with connection management and broadcasting

**File**: `backend/websocket_manager.py`
```python
from fastapi import WebSocket, WebSocketDisconnect
import json
import logging

logger = logging.getLogger(__name__)

class WebSocketManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket, state_manager):
        """Accept WebSocket connection and send initial state"""
        await websocket.accept()
        self.active_connections.append(websocket)
        
        # Send initial state
        try:
            await websocket.send_text(json.dumps(state_manager.state))
            logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")
        except Exception as e:
            logger.error(f"Error sending initial state: {e}")
            await self.disconnect(websocket)
    
    async def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Remaining connections: {len(self.active_connections)}")
    
    async def broadcast(self, message: str):
        """Send message to all connected clients"""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                disconnected.append(connection)
        
        # Clean up disconnected clients
        for connection in disconnected:
            await self.disconnect(connection)

# Add to server.py
from backend.websocket_manager import WebSocketManager
websocket_manager = WebSocketManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket_manager.connect(websocket, get_state_manager())
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        await websocket_manager.disconnect(websocket)
```

**Acceptance Criteria**:
- WebSocket connections accept and handle multiple clients
- Initial state sent on connection
- Broadcast system works reliably
- Disconnections handled gracefully

### Task E4: REST API Endpoints (2 hours)

**Objective**: Implement REST endpoints for commands and state management

**File**: `backend/api_routes.py`
```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any

router = APIRouter(prefix="/api")

class CommandRequest(BaseModel):
    command: str

class SystemStatusUpdate(BaseModel):
    status: str = None
    progress: int = None

@router.get("/system/status")
async def get_system_status():
    """Get current system status"""
    state_manager = get_state_manager()
    return state_manager.state["system"]

@router.post("/system/status")
async def update_system_status(update: SystemStatusUpdate):
    """Update system status and broadcast change"""
    state_manager = get_state_manager()
    
    try:
        if update.status:
            await state_manager.update_state("system/status", update.status)
        if update.progress is not None:
            await state_manager.update_state("system/progress", update.progress)
        
        return {"success": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/command")
async def execute_command(request: CommandRequest):
    """Execute command and return structured result"""
    command = request.command.strip().lower()
    
    # Simple command parser for now
    if command.startswith("approve "):
        target = command.split()[1]
        return {"action": "approve", "target": target}
    elif command.startswith("brief "):
        target = command.split()[1] if len(command.split()) > 1 else None
        return {"action": "brief", "target": target}
    elif command == "refresh":
        return {"action": "refresh", "target": None}
    else:
        raise HTTPException(status_code=400, detail=f"Unknown command: {command}")

@router.get("/trigger_collection")
async def trigger_collection():
    """Trigger data collection process"""
    state_manager = get_state_manager()
    await state_manager.update_state("system/status", "COLLECTING")
    await state_manager.update_state("system/progress", 0)
    
    # TODO: Actually trigger collection in Agent H
    return {"success": True, "message": "Collection started"}

# Add to server.py
from backend.api_routes import router
app.include_router(router)
```

**Acceptance Criteria**:
- All endpoints respond correctly
- Commands parse and return structured data
- System status updates work with validation
- Collection trigger changes state appropriately

## Integration Requirements

### SearchDatabase Integration
- Import and use existing `src.search.database.SearchDatabase`
- Query capabilities for dashboard data population
- No modifications to existing search infrastructure

### Collector Integration Points
- Hooks for Agent H to connect existing collectors
- Progress callback system for real-time updates
- State update integration for collection status

### Performance Requirements
- API response time <100ms for all endpoints
- WebSocket message delivery <50ms
- Memory usage <100MB for state management
- Concurrent WebSocket connections: 5-10 (lab use)

## Files to Create

### Core Backend Files
```
backend/
├── __init__.py
├── server.py              # Main FastAPI application
├── state_manager.py       # In-memory state management
├── websocket_manager.py   # WebSocket connection handling
└── api_routes.py         # REST API endpoints
```

### Test Files
```
tests/
├── test_backend_api.py    # Comprehensive API test suite
├── test_websocket.py      # WebSocket functionality tests
└── test_state_manager.py  # State management tests
```

## Dependencies Required

Add to `requirements.txt`:
```
fastapi==0.104.1
uvicorn[standard]==0.24.0
websockets==12.0
pydantic==2.4.2
```

## Success Criteria

### Functional Validation ✅
- [ ] FastAPI server starts and responds to health checks
- [ ] WebSocket connections establish and receive initial state
- [ ] Multiple WebSocket clients supported simultaneously
- [ ] State updates broadcast to all connected clients
- [ ] REST API endpoints return correct responses
- [ ] Command parsing works for basic commands
- [ ] State validation prevents invalid data

### Performance Validation ✅
- [ ] API response time <100ms
- [ ] WebSocket message delivery <50ms
- [ ] Memory usage remains stable under load
- [ ] No memory leaks with connection churn

### Integration Validation ✅
- [ ] Integrates with existing SearchDatabase
- [ ] Provides hooks for collector integration
- [ ] Compatible with existing authentication system
- [ ] No conflicts with existing infrastructure

## Delivery Checklist

Before marking Agent E complete:
- [ ] All test suites written and passing
- [ ] FastAPI server functional with all endpoints
- [ ] WebSocket broadcasting system operational
- [ ] State management validated with edge cases
- [ ] Performance benchmarks documented
- [ ] Integration points clearly defined for Agent H
- [ ] Code follows existing project patterns

---

**Contact Agent E Team Lead for questions or Agent F/G integration points**  
**Next**: Agent H depends on this backend API foundation