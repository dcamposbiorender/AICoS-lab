#!/usr/bin/env python3
"""
Simple CLI Wrapper for Slack Bot - Phase 4a Foundation

Basic wrapper around existing CLI tools for simple integration.
Keeps it simple and functional - this is for demonstration, not enterprise production.
"""

import subprocess
import json
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)

class CLIWrapper:
    """Simple wrapper around existing CLI tools for bot integration"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.tools_dir = self.project_root / "tools"
        
    def search_data(self, query: str, limit: int = 5) -> Dict[str, Any]:
        """Simple search using existing search CLI"""
        try:
            # Use the existing search_cli.py tool
            search_script = self.tools_dir / "search_cli.py"
            if not search_script.exists():
                return {"error": "Search tool not available", "results": []}
            
            # Run search command
            cmd = [
                "python3", str(search_script),
                "search", query,
                "--limit", str(limit),
                "--format", "json"
            ]
            
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=30,
                cwd=self.project_root
            )
            
            if result.returncode != 0:
                logger.error(f"Search command failed: {result.stderr}")
                return {"error": f"Search failed: {result.stderr}", "results": []}
            
            try:
                output = json.loads(result.stdout)
                return {
                    "query": query,
                    "results": output.get("results", [])[:limit],
                    "total": output.get("total", 0),
                    "duration": output.get("duration", 0)
                }
            except json.JSONDecodeError:
                # Fallback to plain text output
                return {
                    "query": query,
                    "results": [{"content": result.stdout, "source": "search"}],
                    "total": 1,
                    "duration": 0
                }
                
        except subprocess.TimeoutExpired:
            return {"error": "Search timeout", "results": []}
        except Exception as e:
            logger.error(f"Search error: {e}")
            return {"error": str(e), "results": []}
    
    def get_brief(self, period: str = "daily") -> Dict[str, Any]:
        """Simple daily brief using existing CLI tools"""
        try:
            # Try to use existing daily_summary.py tool
            summary_script = self.tools_dir / "daily_summary.py"
            if not summary_script.exists():
                return {"error": "Daily summary tool not available"}
            
            cmd = [
                "python3", str(summary_script),
                "--format", "json",
                "--period", period
            ]
            
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=60,
                cwd=self.project_root
            )
            
            if result.returncode != 0:
                logger.error(f"Brief command failed: {result.stderr}")
                return {"error": f"Brief generation failed: {result.stderr}"}
            
            try:
                return json.loads(result.stdout)
            except json.JSONDecodeError:
                return {
                    "period": period,
                    "summary": result.stdout,
                    "generated_at": "now"
                }
                
        except subprocess.TimeoutExpired:
            return {"error": "Brief generation timeout"}
        except Exception as e:
            logger.error(f"Brief error: {e}")
            return {"error": str(e)}
    
    def find_slots(self, person: str, duration: int = 30) -> Dict[str, Any]:
        """Simple calendar slot finding using existing tools"""
        try:
            # Use existing find_slots.py tool
            slots_script = self.tools_dir / "find_slots.py"
            if not slots_script.exists():
                return {"error": "Calendar tool not available"}
            
            cmd = [
                "python3", str(slots_script),
                "--person", person,
                "--duration", str(duration),
                "--format", "json"
            ]
            
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=30,
                cwd=self.project_root
            )
            
            if result.returncode != 0:
                logger.error(f"Slots command failed: {result.stderr}")
                return {"error": f"Calendar lookup failed: {result.stderr}"}
            
            try:
                return json.loads(result.stdout)
            except json.JSONDecodeError:
                return {
                    "person": person,
                    "duration": duration,
                    "slots": [],
                    "message": result.stdout
                }
                
        except subprocess.TimeoutExpired:
            return {"error": "Calendar lookup timeout"}
        except Exception as e:
            logger.error(f"Calendar error: {e}")
            return {"error": str(e)}
    
    def get_health_status(self) -> Dict[str, Any]:
        """Simple health check using existing infrastructure"""
        try:
            # Check if key components are available
            search_available = (self.tools_dir / "search_cli.py").exists()
            summary_available = (self.tools_dir / "daily_summary.py").exists()
            calendar_available = (self.tools_dir / "find_slots.py").exists()
            
            # Try a quick search test
            search_test = False
            if search_available:
                try:
                    test_result = self.search_data("test", limit=1)
                    search_test = "error" not in test_result
                except:
                    pass
            
            return {
                "status": "ok" if search_available else "degraded",
                "components": {
                    "search": search_available and search_test,
                    "summary": summary_available,
                    "calendar": calendar_available
                },
                "message": "Bot foundation operational"
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "message": "Health check failed"
            }

# Global instance for easy import
cli_wrapper = CLIWrapper()

# Convenience functions
def search(query: str, limit: int = 5) -> Dict[str, Any]:
    """Search using existing CLI tools"""
    return cli_wrapper.search_data(query, limit)

def get_brief(period: str = "daily") -> Dict[str, Any]:
    """Get brief using existing CLI tools"""
    return cli_wrapper.get_brief(period)

def find_slots(person: str, duration: int = 30) -> Dict[str, Any]:
    """Find calendar slots using existing CLI tools"""
    return cli_wrapper.find_slots(person, duration)

def health_check() -> Dict[str, Any]:
    """Get system health status"""
    return cli_wrapper.get_health_status()

if __name__ == "__main__":
    # Simple test
    print("🧪 Testing CLI Wrapper")
    print("=" * 40)
    
    # Test health
    health = health_check()
    print(f"Health: {health}")
    
    # Test search
    search_result = search("test query", limit=2)
    print(f"Search: {search_result.get('total', 0)} results")
    
    # Test brief
    brief_result = get_brief()
    print(f"Brief: {'OK' if 'error' not in brief_result else 'Error'}")
    
    print("\n✅ CLI wrapper test complete")