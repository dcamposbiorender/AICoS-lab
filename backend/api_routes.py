"""
REST API endpoints for Agent E Backend

References:
- Task specification: Task E4 in /Users/david.campos/VibeCode/AICoS-Lab/tasks/frontend_agent_e_backend.md
- Existing API patterns from Slack bot implementation in src/bot/
- FastAPI route patterns from existing codebase

Features:
- System status management endpoints
- Command processing with structured parsing
- Collection triggering with state updates
- Integration with existing SearchDatabase
- Performance monitoring for <100ms response times
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, field_validator
from typing import Dict, Any, Optional, List
import logging
import time
from datetime import datetime

# Import state management
from .state_manager import get_state_manager, StateManager

# Import existing infrastructure when available
try:
    from src.search.database import SearchDatabase
except ImportError:
    SearchDatabase = None

logger = logging.getLogger(__name__)

# Create API router
router = APIRouter(prefix="/api")

# Pydantic models for request validation
class CommandRequest(BaseModel):
    """Request model for command execution"""
    command: str
    
    @field_validator('command')
    @classmethod
    def validate_command(cls, v):
        if not v or not isinstance(v, str):
            raise ValueError("Command must be a non-empty string")
        return v.strip()

class SystemStatusUpdate(BaseModel):
    """Request model for system status updates"""
    status: Optional[str] = None
    progress: Optional[int] = None
    
    @field_validator('progress')
    @classmethod
    def validate_progress(cls, v):
        if v is not None and not 0 <= v <= 100:
            raise ValueError("Progress must be between 0 and 100")
        return v

class BriefRequest(BaseModel):
    """Request model for brief operations"""
    brief_type: str = "daily"
    filters: Optional[Dict[str, Any]] = None

# Performance monitoring decorator
def monitor_performance(func):
    """Decorator to monitor API endpoint performance"""
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            response_time = (time.time() - start_time) * 1000
            
            if response_time > 100:  # Log slow responses
                logger.warning(f"Slow API response: {func.__name__} took {response_time:.2f}ms")
            
            return result
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            logger.error(f"API error in {func.__name__} after {response_time:.2f}ms: {e}")
            raise
    return wrapper

# System Status Endpoints
@router.get("/system/status")
def get_system_status():
    """
    Get current system status
    
    Returns:
        Current system state with status, progress, and last_sync
    """
    state_manager = get_state_manager()
    return state_manager.get_system_state()

@router.post("/system/status")
async def update_system_status(update: SystemStatusUpdate):
    """
    Update system status and broadcast changes
    
    Args:
        update: Status update with optional status and progress fields
        
    Returns:
        Success confirmation
        
    Raises:
        HTTPException: If validation fails or state update fails
    """
    try:
        state_manager = get_state_manager()
        await state_manager.update_system_status(
            status=update.status,
            progress=update.progress
        )
        return {"success": True, "updated_at": datetime.now().isoformat()}
        
    except ValueError as e:
        logger.warning(f"Invalid system status update: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"System status update failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Command Processing Endpoints
@router.post("/command")
async def execute_command(request: CommandRequest):
    """
    Execute command and return structured result
    
    Args:
        request: Command execution request
        
    Returns:
        Structured command result with action and target
        
    Raises:
        HTTPException: For invalid or unknown commands
    """
    command = request.command.lower()
    
    try:
        # Parse command using simple command parser
        result = _parse_command(command)
        
        # Update state based on command if needed
        if result["action"] == "refresh":
            state_manager = get_state_manager()
            await state_manager.update_system_status(
                status="PROCESSING",
                progress=0
            )
        
        logger.info(f"Executed command: {command} -> {result}")
        return result
        
    except ValueError as e:
        logger.warning(f"Invalid command: {command} - {e}")
        raise HTTPException(status_code=400, detail={"error": str(e), "command": command})
    except Exception as e:
        logger.error(f"Command execution failed: {command} - {e}")
        raise HTTPException(status_code=500, detail="Command execution failed")

def _parse_command(command: str) -> Dict[str, Any]:
    """
    Parse command string into structured action and target
    
    Args:
        command: Command string to parse
        
    Returns:
        Dict with action and target fields
        
    Raises:
        ValueError: For unknown or invalid commands
    """
    parts = command.strip().split()
    
    if not parts:
        raise ValueError("Empty command")
    
    action = parts[0]
    
    # Approve command: "approve P7", "approve commitment 123"
    if action == "approve":
        if len(parts) < 2:
            raise ValueError("Approve command requires a target")
        target = parts[1]
        return {"action": "approve", "target": target}
    
    # Brief command: "brief daily", "brief weekly", "brief"
    elif action == "brief":
        target = parts[1] if len(parts) > 1 else "daily"
        return {"action": "brief", "target": target}
    
    # Refresh command: "refresh"
    elif action == "refresh":
        return {"action": "refresh", "target": None}
    
    # Search command: "search keyword", "search person:john"
    elif action == "search":
        if len(parts) < 2:
            raise ValueError("Search command requires a query")
        query = " ".join(parts[1:])
        return {"action": "search", "target": query}
    
    # Status command: "status", "status details"
    elif action == "status":
        target = parts[1] if len(parts) > 1 else "summary"
        return {"action": "status", "target": target}
    
    else:
        raise ValueError(f"Unknown command: {action}")

# Collection Management Endpoints
@router.get("/trigger_collection")
@router.options("/trigger_collection")  # Add OPTIONS support for CORS preflight
async def trigger_collection(type: str = "quick"):
    """
    Trigger data collection process
    
    Args:
        type: Collection type - "quick" (Slack only) or "full" (all sources)
    
    Returns:
        Collection start confirmation and results
    """
    try:
        state_manager = get_state_manager()
        await state_manager.update_system_status(
            status="COLLECTING",
            progress=0
        )
        
        logger.info(f"Starting {type} data collection via API")
        
        # Import collection system
        import sys
        from pathlib import Path
        project_root = Path(__file__).parent.parent
        sys.path.insert(0, str(project_root))
        
        collection_results = {}
        
        if type == "quick":
            # Quick collection - Slack only
            try:
                await state_manager.update_system_status(progress=25)
                from src.collectors.slack_collector import SlackCollector
                slack_collector = SlackCollector()
                result = slack_collector.collect()
                collection_results["slack"] = {
                    "success": True,
                    "records": result.get("message_count", 0) if result else 0
                }
                logger.info(f"Slack collection completed: {collection_results['slack']}")
                await state_manager.update_system_status(progress=100)
            except Exception as e:
                collection_results["slack"] = {"success": False, "error": str(e)}
                logger.error(f"Slack collection failed: {e}")
                
        elif type == "full":
            # Full collection - all sources
            collectors = {
                "slack": ("src.collectors.slack_collector", "SlackCollector"),
                "calendar": ("src.collectors.calendar_collector", "CalendarCollector"),
                "drive": ("src.collectors.drive_collector", "DriveCollector")
            }
            
            progress_step = 80 // len(collectors)
            current_progress = 10
            
            for source, (module_name, class_name) in collectors.items():
                try:
                    await state_manager.update_system_status(progress=current_progress)
                    module = __import__(module_name, fromlist=[class_name])
                    collector_class = getattr(module, class_name)
                    collector = collector_class()
                    result = collector.collect()
                    collection_results[source] = {
                        "success": True,
                        "records": result.get("message_count", 0) if result and "message_count" in result else len(result) if result else 0
                    }
                    logger.info(f"{source} collection completed: {collection_results[source]}")
                except Exception as e:
                    collection_results[source] = {"success": False, "error": str(e)}
                    logger.error(f"{source} collection failed: {e}")
                
                current_progress += progress_step
                await state_manager.update_system_status(progress=min(current_progress, 90))
            
            await state_manager.update_system_status(progress=100)
        
        # Reset status after brief delay
        import asyncio
        asyncio.create_task(reset_status_after_delay(state_manager))
        
        return {
            "success": True,
            "message": f"{type.capitalize()} collection completed",
            "type": type,
            "results": collection_results,
            "started_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to trigger collection: {e}")
        await state_manager.update_system_status(status="ERROR", progress=0)
        raise HTTPException(status_code=500, detail=f"Failed to start collection: {str(e)}")

async def reset_status_after_delay(state_manager, delay_seconds: int = 3):
    """Reset system status to IDLE after delay"""
    import asyncio
    await asyncio.sleep(delay_seconds)
    await state_manager.update_system_status(status="IDLE", progress=0)

@router.get("/collection/status")
def get_collection_status():
    """
    Get current collection status and progress
    
    Returns:
        Collection status with progress and timing information
    """
    state_manager = get_state_manager()
    system_state = state_manager.get_system_state()
    
    return {
        "status": system_state["status"],
        "progress": system_state["progress"],
        "last_sync": system_state["last_sync"],
        "is_collecting": system_state["status"] == "COLLECTING"
    }

# Data Update Endpoints for Dashboard Population
@router.post("/update_calendar")
async def update_calendar(calendar_events: List[Dict[str, Any]]):
    """
    Update calendar data in the state manager
    
    Args:
        calendar_events: List of calendar event objects
        
    Returns:
        Success confirmation with count
    """
    try:
        state_manager = get_state_manager()
        await state_manager.update_calendar_events(calendar_events)
        
        logger.info(f"Updated calendar with {len(calendar_events)} events")
        return {
            "success": True,
            "message": f"Updated {len(calendar_events)} calendar events",
            "count": len(calendar_events),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to update calendar: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update calendar: {str(e)}")

@router.post("/update_priorities")
async def update_priorities(priorities: List[Dict[str, Any]]):
    """
    Update priorities data in the state manager
    
    Args:
        priorities: List of priority objects
        
    Returns:
        Success confirmation with count
    """
    try:
        state_manager = get_state_manager()
        await state_manager.update_priorities(priorities)
        
        logger.info(f"Updated priorities with {len(priorities)} items")
        return {
            "success": True,
            "message": f"Updated {len(priorities)} priorities",
            "count": len(priorities),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to update priorities: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update priorities: {str(e)}")

@router.post("/update_commitments")
async def update_commitments(commitments: Dict[str, Any]):
    """
    Update commitments data in the state manager
    
    Args:
        commitments: Commitment structure with 'owe' and 'owed' lists
        
    Returns:
        Success confirmation with counts
    """
    try:
        state_manager = get_state_manager()
        await state_manager.update_commitments(commitments)
        
        owe_count = len(commitments.get('owe', []))
        owed_count = len(commitments.get('owed', []))
        
        logger.info(f"Updated commitments: {owe_count} owe, {owed_count} owed")
        return {
            "success": True,
            "message": f"Updated {owe_count} owe commitments and {owed_count} owed commitments",
            "owe_count": owe_count,
            "owed_count": owed_count,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to update commitments: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update commitments: {str(e)}")

# Search Integration Endpoints (when SearchDatabase available)
if SearchDatabase:
    _search_db_instance = None
    
    def get_search_database():
        """Get SearchDatabase instance (lazy initialization)"""
        global _search_db_instance
        if _search_db_instance is None:
            _search_db_instance = SearchDatabase()
        return _search_db_instance
    
    @router.get("/search/stats")
    def get_search_stats():
        """
        Get search database statistics
        
        Returns:
            Database statistics including record counts and sources
        """
        try:
            search_db = get_search_database()
            stats = search_db.get_stats()
            return stats
        except Exception as e:
            logger.error(f"Failed to get search stats: {e}")
            raise HTTPException(status_code=500, detail="Failed to retrieve search statistics")
    
    @router.post("/search/query")
    def search_records(
        query: str,
        source: Optional[str] = None,
        limit: int = 50
    ):
        """
        Search records in the database
        
        Args:
            query: Search query string
            source: Optional source filter
            limit: Maximum results to return
            
        Returns:
            Search results with relevance scores
        """
        try:
            search_db = get_search_database()
            results = search_db.search(
                query=query,
                source=source,
                limit=limit
            )
            
            return {
                "query": query,
                "results_count": len(results),
                "results": results
            }
            
        except Exception as e:
            logger.error(f"Search query failed: {e}")
            raise HTTPException(status_code=500, detail="Search query failed")

# Brief Management Endpoints
@router.post("/brief/generate")
async def generate_brief(request: BriefRequest):
    """
    Generate brief based on current data
    
    Args:
        request: Brief generation request
        
    Returns:
        Brief generation status
    """
    try:
        state_manager = get_state_manager()
        await state_manager.update_system_status(
            status="PROCESSING",
            progress=10
        )
        
        # TODO: Integrate with brief generation logic (Agent H implementation)
        
        brief_data = {
            "type": request.brief_type,
            "generated_at": datetime.now().isoformat(),
            "filters": request.filters,
            "status": "generating"
        }
        
        await state_manager.set_active_brief(brief_data)
        
        return {
            "success": True,
            "brief_type": request.brief_type,
            "message": "Brief generation started"
        }
        
    except Exception as e:
        logger.error(f"Brief generation failed: {e}")
        raise HTTPException(status_code=500, detail="Brief generation failed")

@router.get("/brief/current")
def get_current_brief():
    """
    Get currently active brief
    
    Returns:
        Current brief data or None if no active brief
    """
    state_manager = get_state_manager()
    state = state_manager.get_state()
    return {
        "active_brief": state.get("active_brief"),
        "has_active_brief": state.get("active_brief") is not None
    }

# Health and Statistics Endpoints
@router.get("/health")
def api_health_check():
    """
    API health check endpoint
    
    Returns:
        Health status and basic system information
    """
    return {
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "api_prefix": "/api"
    }

@router.get("/stats")
def get_api_stats():
    """
    Get API and system statistics
    
    Returns:
        Combined statistics from state manager and API usage
    """
    state_manager = get_state_manager()
    stats = {
        "state_manager": state_manager.get_stats(),
        "api_version": "1.0.0",
        "endpoints_available": len([rule for rule in router.routes])
    }
    
    # Add search database stats if available
    if SearchDatabase:
        try:
            search_db = get_search_database()
            stats["search_database"] = search_db.get_stats()
        except Exception as e:
            logger.warning(f"Could not get search database stats: {e}")
            stats["search_database"] = {"error": str(e)}
    
    return stats