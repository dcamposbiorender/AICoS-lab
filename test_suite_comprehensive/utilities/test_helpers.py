"""
Test helper utilities for AI Chief of Staff comprehensive testing.

Provides common testing utilities:
- CLI test execution helpers
- System validation utilities
- Test data management
- Result validation helpers
"""

import subprocess
import json
import time
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
import tempfile
from dataclasses import dataclass


@dataclass
class CommandResult:
    """Result of a command execution."""
    returncode: int
    stdout: str
    stderr: str
    duration: float


class CLITestHelper:
    """Helper for testing CLI tools."""
    
    def __init__(self, base_dir: str, env_vars: Dict[str, str]):
        """Initialize CLI test helper."""
        self.base_dir = Path(base_dir)
        self.env_vars = env_vars
        self.tools_dir = Path("../tools")  # Relative to test suite
    
    def run_tool(self, tool_name: str, args: List[str] = None, timeout: int = 60) -> CommandResult:
        """Run a CLI tool with arguments."""
        if args is None:
            args = []
        
        tool_path = self.tools_dir / tool_name
        cmd = ["python", str(tool_path)] + args
        
        # Set up environment
        test_env = os.environ.copy()
        test_env.update(self.env_vars)
        
        start_time = time.time()
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=test_env,
                cwd=self.base_dir
            )
            
            duration = time.time() - start_time
            
            return CommandResult(
                returncode=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                duration=duration
            )
            
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            return CommandResult(
                returncode=-1,
                stdout="",
                stderr=f"Command timed out after {timeout} seconds",
                duration=duration
            )
        except Exception as e:
            duration = time.time() - start_time
            return CommandResult(
                returncode=-2,
                stdout="",
                stderr=f"Command execution failed: {e}",
                duration=duration
            )
    
    def run_collection(self, source: str = "all", additional_args: List[str] = None) -> CommandResult:
        """Run data collection with standard arguments."""
        args = ["--source", source, "--test-mode"]
        if additional_args:
            args.extend(additional_args)
        
        return self.run_tool("collect_data.py", args)
    
    def run_search(self, query: str, additional_args: List[str] = None) -> CommandResult:
        """Run search with standard arguments."""
        args = ["--query", query]
        if additional_args:
            args.extend(additional_args)
        
        return self.run_tool("search_cli.py", args)
    
    def run_archive_management(self, operation: str, additional_args: List[str] = None) -> CommandResult:
        """Run archive management operations."""
        args = [f"--{operation}"]
        if additional_args:
            args.extend(additional_args)
        
        return self.run_tool("manage_archives.py", args)


class SystemValidator:
    """Validates system health and configuration."""
    
    def __init__(self, config):
        """Initialize system validator."""
        self.config = config
    
    def run_health_check(self) -> Dict[str, Any]:
        """Run comprehensive system health check."""
        health_report = {
            "timestamp": time.time(),
            "overall_status": "unknown",
            "checks": {}
        }
        
        # Configuration validation
        health_report["checks"]["config_valid"] = self._check_config_validity()
        
        # Directory accessibility
        health_report["checks"]["directories_accessible"] = self._check_directory_access()
        
        # Disk space
        health_report["checks"]["disk_space_sufficient"] = self._check_disk_space()
        
        # Database connectivity
        health_report["checks"]["database_accessible"] = self._check_database_access()
        
        # File permissions
        health_report["checks"]["permissions_correct"] = self._check_file_permissions()
        
        # Determine overall status
        all_checks_passed = all(health_report["checks"].values())
        health_report["overall_status"] = "healthy" if all_checks_passed else "unhealthy"
        
        # Add convenience boolean fields
        for check_name, result in health_report["checks"].items():
            health_report[check_name] = result
        
        return health_report
    
    def _check_config_validity(self) -> bool:
        """Check if configuration is valid."""
        try:
            # Basic configuration checks
            assert self.config.base_dir.exists(), "Base directory should exist"
            assert self.config.base_dir.is_dir(), "Base directory should be a directory"
            
            # Test mode checks
            if hasattr(self.config, 'test_mode'):
                assert self.config.test_mode is not None, "Test mode should be set"
            
            return True
        except Exception:
            return False
    
    def _check_directory_access(self) -> bool:
        """Check if all required directories are accessible."""
        try:
            required_dirs = [
                self.config.data_dir,
                self.config.archive_dir,
                self.config.logs_dir,
                self.config.state_dir
            ]
            
            for directory in required_dirs:
                assert directory.exists(), f"Directory {directory} should exist"
                assert directory.is_dir(), f"{directory} should be a directory"
                
                # Test write access
                test_file = directory / ".write_test"
                test_file.write_text("test")
                test_file.unlink()
            
            return True
        except Exception:
            return False
    
    def _check_disk_space(self) -> bool:
        """Check if sufficient disk space is available."""
        try:
            import shutil
            
            total, used, free = shutil.disk_usage(self.config.base_dir)
            free_gb = free / (1024 ** 3)
            
            # Require at least 1GB free space
            return free_gb >= 1.0
        except Exception:
            return False
    
    def _check_database_access(self) -> bool:
        """Check if database can be accessed."""
        try:
            # Try to create a temporary database
            import sqlite3
            
            db_path = self.config.state_dir / "health_check.db"
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("CREATE TABLE IF NOT EXISTS test (id INTEGER)")
            cursor.execute("INSERT INTO test VALUES (1)")
            cursor.execute("SELECT * FROM test")
            result = cursor.fetchone()
            conn.close()
            
            # Clean up
            if db_path.exists():
                db_path.unlink()
            
            return result is not None
        except Exception:
            return False
    
    def _check_file_permissions(self) -> bool:
        """Check if file permissions are correct."""
        try:
            # Check if we can create and modify files
            test_file = self.config.data_dir / "permission_test.txt"
            test_file.write_text("permission test")
            
            # Check read access
            content = test_file.read_text()
            assert content == "permission test"
            
            # Check modification
            test_file.write_text("modified")
            modified_content = test_file.read_text()
            assert modified_content == "modified"
            
            # Clean up
            test_file.unlink()
            
            return True
        except Exception:
            return False


class DataValidator:
    """Validates data integrity and format."""
    
    @staticmethod
    def validate_jsonl_file(file_path: Path) -> Dict[str, Any]:
        """Validate JSONL file format and content."""
        validation_result = {
            "valid": True,
            "total_lines": 0,
            "valid_lines": 0,
            "invalid_lines": 0,
            "errors": []
        }
        
        try:
            with open(file_path, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    validation_result["total_lines"] += 1
                    
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        json.loads(line)
                        validation_result["valid_lines"] += 1
                    except json.JSONDecodeError as e:
                        validation_result["invalid_lines"] += 1
                        validation_result["errors"].append({
                            "line": line_num,
                            "error": str(e),
                            "content": line[:100] + "..." if len(line) > 100 else line
                        })
                        validation_result["valid"] = False
        
        except Exception as e:
            validation_result["valid"] = False
            validation_result["errors"].append({
                "type": "file_error",
                "error": str(e)
            })
        
        return validation_result
    
    @staticmethod
    def validate_archive_structure(archive_dir: Path) -> Dict[str, Any]:
        """Validate archive directory structure."""
        validation_result = {
            "valid": True,
            "sources": {},
            "total_files": 0,
            "errors": []
        }
        
        try:
            for source_dir in archive_dir.iterdir():
                if not source_dir.is_dir():
                    continue
                
                source_name = source_dir.name
                source_info = {
                    "daily_dirs": 0,
                    "jsonl_files": 0,
                    "compressed_files": 0,
                    "manifest_files": 0
                }
                
                for daily_dir in source_dir.iterdir():
                    if not daily_dir.is_dir():
                        continue
                    
                    source_info["daily_dirs"] += 1
                    
                    for file_path in daily_dir.iterdir():
                        if file_path.suffix == ".jsonl":
                            source_info["jsonl_files"] += 1
                            validation_result["total_files"] += 1
                        elif file_path.suffix == ".gz":
                            source_info["compressed_files"] += 1
                            validation_result["total_files"] += 1
                        elif file_path.name == "manifest.json":
                            source_info["manifest_files"] += 1
                
                validation_result["sources"][source_name] = source_info
        
        except Exception as e:
            validation_result["valid"] = False
            validation_result["errors"].append({
                "type": "structure_error",
                "error": str(e)
            })
        
        return validation_result


class TestDataManager:
    """Manages test data for comprehensive testing."""
    
    def __init__(self, base_dir: Path):
        """Initialize test data manager."""
        self.base_dir = base_dir
        self.test_data_dir = base_dir / "test_data"
        self.test_data_dir.mkdir(exist_ok=True)
    
    def create_test_archive(self, source: str, records: List[Dict[str, Any]], date: str = "2025-08-18") -> Path:
        """Create test archive with specified records."""
        archive_dir = self.test_data_dir / "archive" / source / date
        archive_dir.mkdir(parents=True, exist_ok=True)
        
        jsonl_file = archive_dir / f"{source}_data.jsonl"
        
        with open(jsonl_file, 'w') as f:
            for record in records:
                f.write(json.dumps(record) + '\n')
        
        # Create manifest
        manifest = {
            "source": source,
            "date": date,
            "record_count": len(records),
            "file_size": jsonl_file.stat().st_size,
            "created_at": time.time()
        }
        
        manifest_file = archive_dir / "manifest.json"
        with open(manifest_file, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        return jsonl_file
    
    def create_test_database(self, name: str) -> Path:
        """Create test SQLite database."""
        db_path = self.test_data_dir / f"{name}.db"
        
        import sqlite3
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create test table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS test_records (
                id INTEGER PRIMARY KEY,
                content TEXT,
                timestamp TEXT,
                source TEXT
            )
        """)
        
        conn.commit()
        conn.close()
        
        return db_path
    
    def cleanup_test_data(self) -> None:
        """Clean up all test data."""
        import shutil
        
        if self.test_data_dir.exists():
            shutil.rmtree(self.test_data_dir)


class PerformanceAssertions:
    """Custom assertions for performance testing."""
    
    @staticmethod
    def assert_response_time(actual_time: float, max_time: float, operation: str):
        """Assert operation completed within time limit."""
        assert actual_time <= max_time, (
            f"{operation} took {actual_time:.3f}s, "
            f"expected <={max_time:.3f}s"
        )
    
    @staticmethod
    def assert_throughput(items_processed: int, duration: float, min_rate: float, operation: str):
        """Assert operation achieved minimum throughput."""
        actual_rate = items_processed / duration if duration > 0 else float('inf')
        assert actual_rate >= min_rate, (
            f"{operation} achieved {actual_rate:.1f} items/sec, "
            f"expected >={min_rate:.1f} items/sec"
        )
    
    @staticmethod
    def assert_memory_usage(actual_mb: float, max_mb: float, operation: str):
        """Assert operation used acceptable amount of memory."""
        assert actual_mb <= max_mb, (
            f"{operation} used {actual_mb:.1f}MB memory, "
            f"expected <={max_mb:.1f}MB"
        )
    
    @staticmethod
    def assert_compression_ratio(original_size: int, compressed_size: int, min_ratio: float):
        """Assert compression achieved minimum ratio."""
        actual_ratio = (original_size - compressed_size) / original_size * 100
        assert actual_ratio >= min_ratio, (
            f"Compression ratio {actual_ratio:.1f}%, "
            f"expected >={min_ratio:.1f}%"
        )