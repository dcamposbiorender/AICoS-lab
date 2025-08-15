#!/usr/bin/env python3
"""
AI CHIEF OF STAFF - TOOL PATTERN CLI
Outputs JSON for Claude Code orchestration with adapted collectors
"""

import sys
import os
import json
import argparse
import traceback
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

# Add src to path for clean imports  
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from core.system_state_manager import SimpleStateManager
from core.auth_manager import credential_vault
from collectors.slack import SlackCollector
from collectors.calendar import CalendarCollector  
from collectors.employees import EmployeeCollector

def output_json(data: Dict[str, Any], exit_code: int = 0):
    """Output JSON to stdout and exit with specified code"""
    print(json.dumps(data, indent=2))
    sys.exit(exit_code)

def handle_error(command: str, error: Exception, source: Optional[str] = None):
    """Handle errors with structured JSON output"""
    error_data = {
        "status": "error",
        "command": command,
        "error": {
            "type": type(error).__name__,
            "message": str(error),
            "traceback": traceback.format_exc()
        },
        "timestamp": datetime.now().isoformat()
    }
    
    if source:
        error_data["source"] = source
        
    output_json(error_data, exit_code=1)

def collect_data(source: str) -> Dict[str, Any]:
    """Run data collection for specified source"""
    start_time = datetime.now()
    
    try:
        # Initialize state manager
        state_manager = SimpleStateManager()
        
        if source == "all":
            # Collect from all sources
            results = {}
            for src in ["slack", "calendar", "employees"]:
                src_result = _collect_single_source(src, state_manager)
                results[src] = src_result
            
            return {
                "status": "success", 
                "command": "collect",
                "source": "all",
                "execution_time": (datetime.now() - start_time).total_seconds(),
                "results": results,
                "timestamp": datetime.now().isoformat()
            }
        else:
            # Collect from single source
            result = _collect_single_source(source, state_manager)
            
            return {
                "status": "success",
                "command": "collect", 
                "source": source,
                "execution_time": (datetime.now() - start_time).total_seconds(),
                "results": result,
                "timestamp": datetime.now().isoformat()
            }
            
    except Exception as e:
        handle_error("collect", e, source)

def _collect_single_source(source: str, state_manager: SimpleStateManager) -> Dict[str, Any]:
    """Collect data from a single source"""
    
    if source == "slack":
        # Get Slack credentials
        slack_token = credential_vault.get_slack_bot_token()
        if not slack_token:
            raise Exception("Invalid or missing Slack bot token")
            
        # Initialize Slack collector
        config_path = Path(__file__).parent / "config"
        collector = SlackCollector(config_path=config_path)
        
        # Get last cursor
        cursor = state_manager.get_cursor("slack")
        
        # Run collection
        collection_results = collector.collect_all_slack_data(max_channels=50)
        
        # Update state
        new_cursor = datetime.now().isoformat()  
        state_manager.update_cursor("slack", new_cursor)
        state_manager.update_last_run("slack")
        state_manager.update_collection_stats("slack", {
            "channels_discovered": collection_results.get("discovered", {}).get("channels", 0),
            "users_discovered": collection_results.get("discovered", {}).get("users", 0),
            "messages_collected": collection_results.get("collected", {}).get("messages", 0),
            "conversations_collected": collection_results.get("collected", {}).get("conversations", 0)
        })
        
        return {
            "discovered": collection_results.get("discovered", {}),
            "collected": collection_results.get("collected", {}),
            "data_path": f"data/raw/slack/{datetime.now().strftime('%Y-%m-%d')}/",
            "state_updated": True,
            "next_cursor": new_cursor
        }
        
    elif source == "calendar":
        # Get Google credentials
        google_creds = credential_vault.get_google_oauth_credentials()
        if not google_creds:
            raise Exception("Invalid or missing Google Calendar credentials")
            
        # Initialize Calendar collector
        config_path = Path(__file__).parent / "config"
        collector = CalendarCollector(config_path=config_path)
        
        # Get last cursor
        cursor = state_manager.get_cursor("calendar")
        
        # Run collection
        collection_results = collector.collect_all_calendar_data(max_calendars=50)
        
        # Update state  
        new_cursor = datetime.now().isoformat()
        state_manager.update_cursor("calendar", new_cursor)
        state_manager.update_last_run("calendar")
        state_manager.update_collection_stats("calendar", {
            "calendars_discovered": collection_results.get("discovered", {}).get("calendars", 0),
            "events_collected": collection_results.get("collected", {}).get("events", 0),
            "users_discovered": collection_results.get("discovered", {}).get("users", 0)
        })
        
        return {
            "discovered": collection_results.get("discovered", {}),
            "collected": collection_results.get("collected", {}),
            "data_path": f"data/raw/calendar/{datetime.now().strftime('%Y-%m-%d')}/",
            "state_updated": True,
            "next_cursor": new_cursor
        }
        
    elif source == "employees":
        # Initialize Employee collector (doesn't need auth)
        config_path = Path(__file__).parent / "config"
        collector = EmployeeCollector(config_path=config_path)
        
        # Run collection
        collection_results = collector.to_json()
        
        # Update state
        state_manager.update_last_run("employees") 
        state_manager.update_collection_stats("employees", {
            "employees_collected": collection_results.get("discovered", {}).get("unified_employees", 0),
            "slack_users": collection_results.get("discovered", {}).get("slack_users", 0),
            "calendar_users": collection_results.get("discovered", {}).get("calendar_users", 0),
            "drive_users": collection_results.get("discovered", {}).get("drive_users", 0)
        })
        
        return {
            "discovered": collection_results.get("discovered", {}),
            "collected": collection_results.get("roster_data", {}),
            "changes": collection_results.get("changes", {}),
            "data_path": collection_results.get("data_path", f"data/raw/employees/{datetime.now().strftime('%Y-%m-%d')}/"),
            "state_updated": True
        }
        
    else:
        raise ValueError(f"Unsupported source: {source}. Must be one of: slack, calendar, employees, all")

def show_status() -> Dict[str, Any]:
    """Show system status and collection statistics"""
    try:
        state_manager = SimpleStateManager()
        summary = state_manager.get_state_summary()
        
        # Get data directory info
        base_path = Path(__file__).parent
        data_path = base_path / "data"
        
        dir_info = {}
        for subdir in ["raw", "processed", "state", "logs"]:
            subdir_path = data_path / subdir
            if subdir_path.exists():
                dir_info[subdir] = {
                    "exists": True,
                    "file_count": len(list(subdir_path.rglob("*"))) if subdir_path.is_dir() else 0
                }
            else:
                dir_info[subdir] = {"exists": False, "file_count": 0}
        
        return {
            "status": "success",
            "command": "status",
            "system_state": summary,
            "data_directories": dir_info,
            "base_path": str(base_path),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        handle_error("status", e)

def health_check() -> Dict[str, Any]:
    """Basic health check of authentication and data directories"""
    try:
        health_status = {
            "status": "success",
            "command": "health", 
            "checks": {},
            "timestamp": datetime.now().isoformat()
        }
        
        # Check data directories
        base_path = Path(__file__).parent
        data_path = base_path / "data"
        
        required_dirs = ["raw", "processed", "state", "logs"]
        for dir_name in required_dirs:
            dir_path = data_path / dir_name
            health_status["checks"][f"data_dir_{dir_name}"] = {
                "status": "pass" if dir_path.exists() else "fail",
                "path": str(dir_path),
                "writable": dir_path.is_dir() and os.access(dir_path, os.W_OK) if dir_path.exists() else False
            }
        
        # Check authentication using specific credential vault methods
        try:
            slack_token = credential_vault.get_slack_bot_token()
            health_status["checks"]["auth_slack_bot"] = {
                "status": "pass" if slack_token else "fail",
                "error": "No Slack bot token found" if not slack_token else None
            }
        except Exception as e:
            health_status["checks"]["auth_slack_bot"] = {
                "status": "error",
                "error": str(e)
            }
        
        try:
            google_creds = credential_vault.get_google_oauth_credentials()
            health_status["checks"]["auth_google_oauth"] = {
                "status": "pass" if google_creds else "fail", 
                "error": "No Google OAuth credentials found" if not google_creds else None
            }
        except Exception as e:
            health_status["checks"]["auth_google_oauth"] = {
                "status": "error",
                "error": str(e)
            }
        
        # Check state manager
        try:
            state_manager = SimpleStateManager()
            health_status["checks"]["state_manager"] = {
                "status": "pass",
                "state_file": str(state_manager.state_file),
                "sources": list(state_manager.supported_sources)
            }
        except Exception as e:
            health_status["checks"]["state_manager"] = {
                "status": "error",
                "error": str(e)
            }
            
        return health_status
        
    except Exception as e:
        handle_error("health", e)

def process_data(process_type: str) -> Dict[str, Any]:
    """Placeholder for data processing (future implementation)"""
    return {
        "status": "success",
        "command": "process",
        "type": process_type,
        "message": f"Processing type '{process_type}' not yet implemented",
        "timestamp": datetime.now().isoformat()
    }

def main():
    """Main entry point with tool pattern structure"""
    parser = argparse.ArgumentParser(description='AI Chief of Staff - Tool Pattern CLI')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Collect command
    collect_parser = subparsers.add_parser('collect', help='Run data collection')
    collect_parser.add_argument('--source', required=True, 
                               choices=['slack', 'calendar', 'employees', 'all'],
                               help='Data source to collect from')
    
    # Status command  
    status_parser = subparsers.add_parser('status', help='Show system status')
    
    # Health command
    health_parser = subparsers.add_parser('health', help='Run health check')
    
    # Process command (future)
    process_parser = subparsers.add_parser('process', help='Process collected data')
    process_parser.add_argument('--type', required=True,
                               choices=['goals', 'commitments', 'insights'],
                               help='Type of processing to run')
    
    args = parser.parse_args()
    
    if not args.command:
        output_json({
            "status": "error", 
            "error": "No command specified",
            "available_commands": ["collect", "status", "health", "process"]
        }, exit_code=1)
    
    # Execute commands
    try:
        if args.command == 'collect':
            result = collect_data(args.source)
            output_json(result)
            
        elif args.command == 'status':
            result = show_status()
            output_json(result)
            
        elif args.command == 'health':
            result = health_check()
            output_json(result)
            
        elif args.command == 'process':
            result = process_data(args.type)
            output_json(result)
            
    except Exception as e:
        handle_error(args.command, e)

if __name__ == "__main__":
    main()
