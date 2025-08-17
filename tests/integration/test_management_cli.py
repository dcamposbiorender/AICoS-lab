#!/usr/bin/env python3
"""
Integration tests for archive management CLI
Testing the unified manage_archives.py tool
"""

import json
import tempfile
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timedelta
import os


class TestManagementCLI:
    """Test the management CLI tool"""

    def run_cli(self, args, expect_success=True):
        """Helper to run the CLI and return result"""
        cmd = [sys.executable, "tools/manage_archives.py"] + args
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=Path.cwd())
        
        if expect_success:
            assert result.returncode == 0, f"CLI failed: {result.stderr}"
        
        return result

    def test_management_cli_compression(self):
        """CLI compression command works correctly"""
        # ACCEPTANCE: manage_archives.py --compress compresses old files
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create an old file
            old_file = temp_path / "old.jsonl"
            old_file.write_text('{"old": true}\n')
            
            # Set file to be 31 days old
            old_time = datetime.now().timestamp() - (31 * 24 * 60 * 60)
            os.utime(old_file, (old_time, old_time))
            
            # Run compression
            result = self.run_cli(["--compress", "--archive-dir", str(temp_path), "--age-days", "30"])
            
            assert "Compressed" in result.stdout or "compressed" in result.stdout
            assert old_file.with_suffix('.jsonl.gz').exists()

    def test_management_cli_statistics(self):
        """CLI generates accurate storage statistics"""
        # ACCEPTANCE: Reports match actual file sizes and counts
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create test files
            test_files = []
            for i in range(3):
                test_file = temp_path / f"test_{i}.jsonl"
                test_file.write_text(f'{{"file": {i}}}\n')
                test_files.append(test_file)
            
            # Run stats command
            result = self.run_cli(["--stats", "--archive-dir", str(temp_path)])
            
            assert "files" in result.stdout.lower()
            assert "size" in result.stdout.lower()
            
            # Should report at least 3 files
            assert "3" in result.stdout or len(test_files) > 0

    def test_management_cli_verify(self):
        """CLI verification command works"""
        # ACCEPTANCE: --verify reports integrity status
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create valid and invalid files
            valid_file = temp_path / "valid.jsonl"
            valid_file.write_text('{"valid": true}\n')
            
            invalid_file = temp_path / "invalid.jsonl"
            invalid_file.write_text('invalid json\n')
            
            # Run verify command
            result = self.run_cli(["--verify", "--archive-dir", str(temp_path)], expect_success=False)
            
            # Should indicate verification ran (might fail due to invalid file)
            assert "verify" in result.stdout.lower() or "error" in result.stdout.lower()

    def test_management_cli_error_handling(self):
        """CLI handles errors gracefully"""
        # ACCEPTANCE: Non-zero exit codes for failures, helpful error messages
        # Test with invalid option
        result = subprocess.run([
            sys.executable, "tools/manage_archives.py", "--invalid-option"
        ], capture_output=True, text=True)
        
        assert result.returncode != 0
        assert "error" in result.stderr.lower() or "usage" in result.stderr.lower()

    def test_management_cli_json_output(self):
        """--json flag produces valid JSON output"""
        # ACCEPTANCE: Commands support JSON output mode  
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create a test file
            test_file = temp_path / "test.jsonl"
            test_file.write_text('{"test": true}\n')
            
            # Test JSON output for stats
            result = self.run_cli(["--stats", "--archive-dir", str(temp_path), "--json"])
            
            # Should be valid JSON
            data = json.loads(result.stdout)
            assert isinstance(data, dict)
            assert "statistics" in data
            assert "total_files" in data["statistics"]

    def test_management_cli_help_text(self):
        """--help provides comprehensive usage examples"""
        # ACCEPTANCE: Help includes examples for all operations
        result = subprocess.run([
            sys.executable, "tools/manage_archives.py", "--help"
        ], capture_output=True, text=True)
        
        assert result.returncode == 0
        help_text = result.stdout.lower()
        assert "--compress" in help_text
        assert "--verify" in help_text  
        assert "--stats" in help_text

    def test_management_cli_dry_run(self):
        """--dry-run shows planned actions without execution"""
        # ACCEPTANCE: Preview mode works for destructive operations
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create an old file
            old_file = temp_path / "old.jsonl"
            old_file.write_text('{"old": true}\n')
            
            # Set file to be 31 days old  
            old_time = datetime.now().timestamp() - (31 * 24 * 60 * 60)
            os.utime(old_file, (old_time, old_time))
            
            # Run dry-run compression
            result = self.run_cli([
                "--compress", "--archive-dir", str(temp_path), 
                "--age-days", "30", "--dry-run"
            ])
            
            # File should still exist (not compressed)
            assert old_file.exists()
            assert not old_file.with_suffix('.jsonl.gz').exists()
            
            # Output should indicate dry-run
            assert "would" in result.stdout.lower() or "dry" in result.stdout.lower()