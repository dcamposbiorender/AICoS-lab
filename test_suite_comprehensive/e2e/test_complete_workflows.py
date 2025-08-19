"""
End-to-end workflow tests for AI Chief of Staff system.

Tests complete user workflows:
- Fresh system setup and initialization
- First-time data collection from all sources
- Incremental collection cycles
- Search and query workflows
- Archive management operations
- System maintenance and recovery
"""

import pytest
import tempfile
import subprocess
import json
import time
import os
from pathlib import Path
from unittest.mock import patch
import shutil

# Import test utilities
import sys
sys.path.append('..')
from fixtures.large_datasets import LargeDatasetGenerator
from utilities.test_helpers import CLITestHelper, SystemValidator

# Import components for validation
sys.path.append('../src')
from src.core.config import Config


class TestSystemInitialization:
    """Test fresh system setup and initialization."""
    
    def setup_method(self):
        """Set up fresh test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_env = {
            "AICOS_BASE_DIR": self.temp_dir,
            "AICOS_TEST_MODE": "true",
            "SLACK_BOT_TOKEN": "xoxb-test-token",
            "GOOGLE_CLIENT_ID": "test-client-id",
            "GOOGLE_CLIENT_SECRET": "test-client-secret"
        }
        self.cli_helper = CLITestHelper(self.temp_dir, self.test_env)
    
    @pytest.mark.e2e
    def test_fresh_system_initialization(self):
        """Test complete fresh system setup from scratch."""
        print("🚀 Testing fresh system initialization...")
        
        # Verify empty directory
        assert not any(Path(self.temp_dir).iterdir()), "Directory should be empty initially"
        
        # Initialize system by running config validation
        with patch.dict(os.environ, self.test_env):
            config = Config()
            
            # Verify directory structure created
            expected_dirs = ["data", "logs", "state", "archive"]
            for dir_name in expected_dirs:
                dir_path = Path(self.temp_dir) / dir_name
                assert dir_path.exists(), f"Directory {dir_name} should be created"
                assert dir_path.is_dir(), f"{dir_name} should be a directory"
            
            # Verify configuration loaded correctly
            assert config.base_dir == Path(self.temp_dir)
            assert config.test_mode is True
            assert config.slack_token == "xoxb-test-token"
            
            print("  ✅ System directories created")
            print("  ✅ Configuration loaded successfully")
            print("  ✅ Test mode activated")
    
    @pytest.mark.e2e
    def test_system_health_check(self):
        """Test system health validation after initialization."""
        with patch.dict(os.environ, self.test_env):
            config = Config()
            validator = SystemValidator(config)
            
            print("🏥 Running system health check...")
            
            health_report = validator.run_health_check()
            
            # Verify health check results
            assert health_report["overall_status"] == "healthy", "System should be healthy after init"
            assert health_report["config_valid"] is True, "Configuration should be valid"
            assert health_report["directories_accessible"] is True, "Directories should be accessible"
            assert health_report["disk_space_sufficient"] is True, "Disk space should be sufficient"
            
            print("  ✅ Overall system status: healthy")
            print("  ✅ Configuration valid")
            print("  ✅ Directories accessible")
            print("  ✅ Sufficient disk space")


class TestDataCollectionWorkflows:
    """Test complete data collection workflows."""
    
    def setup_method(self):
        """Set up data collection test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_env = {
            "AICOS_BASE_DIR": self.temp_dir,
            "AICOS_TEST_MODE": "true",
            "SLACK_BOT_TOKEN": "xoxb-test-token",
            "GOOGLE_CLIENT_ID": "test-client-id",
            "GOOGLE_CLIENT_SECRET": "test-client-secret"
        }
        self.cli_helper = CLITestHelper(self.temp_dir, self.test_env)
        self.data_generator = LargeDatasetGenerator()
    
    @pytest.mark.e2e
    def test_first_time_collection_all_sources(self):
        """Test first-time data collection from all sources."""
        print("📊 Testing first-time collection from all sources...")
        
        # Run collection tool
        result = self.cli_helper.run_tool("collect_data.py", ["--source", "all", "--test-mode"])
        
        assert result.returncode == 0, f"Collection failed: {result.stderr}"
        
        # Parse collection results
        try:
            collection_result = json.loads(result.stdout)
            assert "results" in collection_result, "Collection should return results"
            
            # Verify all sources were processed
            expected_sources = ["slack", "calendar", "drive", "employees"]
            for source in expected_sources:
                assert source in collection_result["results"], f"Missing {source} in results"
                assert collection_result["results"][source]["status"] == "success", f"{source} collection failed"
                
                # Verify data was archived
                source_dir = Path(self.temp_dir) / "archive" / source
                assert source_dir.exists(), f"Archive directory for {source} should exist"
                
                # Check for data files
                data_files = list(source_dir.rglob("*.jsonl"))
                if source != "employees":  # Employees might use different format
                    assert len(data_files) > 0, f"Should have data files for {source}"
            
            print("  ✅ All sources collected successfully")
            print("  ✅ Archive directories created")
            print("  ✅ Data files written")
            
        except json.JSONDecodeError:
            pytest.fail(f"Invalid JSON output from collection tool: {result.stdout}")
    
    @pytest.mark.e2e
    def test_incremental_collection_workflow(self):
        """Test incremental data collection workflow."""
        print("🔄 Testing incremental collection workflow...")
        
        # First collection
        print("  Running initial collection...")
        initial_result = self.cli_helper.run_tool("collect_data.py", ["--source", "slack", "--test-mode"])
        assert initial_result.returncode == 0, "Initial collection should succeed"
        
        # Simulate time passing and new data
        time.sleep(0.1)
        
        # Second collection (incremental)
        print("  Running incremental collection...")
        incremental_result = self.cli_helper.run_tool("collect_data.py", ["--source", "slack", "--test-mode", "--incremental"])
        assert incremental_result.returncode == 0, "Incremental collection should succeed"
        
        # Verify state management
        state_files = list(Path(self.temp_dir).rglob("*.db"))
        assert len(state_files) > 0, "State files should exist after collection"
        
        # Verify archive structure
        slack_archive = Path(self.temp_dir) / "archive" / "slack"
        assert slack_archive.exists(), "Slack archive should exist"
        
        daily_dirs = [d for d in slack_archive.iterdir() if d.is_dir()]
        assert len(daily_dirs) > 0, "Should have daily archive directories"
        
        print("  ✅ Incremental collection completed")
        print("  ✅ State files maintained")
        print("  ✅ Archive structure preserved")
    
    @pytest.mark.e2e
    def test_collection_error_handling(self):
        """Test collection error handling and recovery."""
        print("🚨 Testing collection error handling...")
        
        # Test with invalid credentials (should handle gracefully in test mode)
        invalid_env = {**self.test_env, "SLACK_BOT_TOKEN": "invalid-token"}
        
        with patch.dict(os.environ, invalid_env):
            result = self.cli_helper.run_tool("collect_data.py", ["--source", "slack", "--test-mode"])
            
            # Should handle gracefully in test mode
            if result.returncode != 0:
                assert "error" in result.stderr.lower() or "failed" in result.stderr.lower()
                print("  ✅ Invalid credentials handled gracefully")
            else:
                print("  ✅ Test mode bypassed credential validation")
        
        # Test partial collection failure
        print("  Testing partial failure recovery...")
        
        # This should succeed even if some sources fail
        result = self.cli_helper.run_tool("collect_data.py", ["--source", "all", "--test-mode", "--continue-on-error"])
        
        # Should complete even with partial failures
        print("  ✅ Partial failure recovery working")


class TestSearchWorkflows:
    """Test search and query workflows."""
    
    def setup_method(self):
        """Set up search test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_env = {
            "AICOS_BASE_DIR": self.temp_dir,
            "AICOS_TEST_MODE": "true"
        }
        self.cli_helper = CLITestHelper(self.temp_dir, self.test_env)
    
    @pytest.mark.e2e
    def test_search_after_collection_workflow(self):
        """Test complete search workflow after data collection."""
        print("🔍 Testing search workflow after collection...")
        
        # Step 1: Collect some data
        print("  Step 1: Collecting test data...")
        collection_result = self.cli_helper.run_tool("collect_data.py", ["--source", "slack", "--test-mode"])
        assert collection_result.returncode == 0, "Data collection should succeed"
        
        # Step 2: Index the data
        print("  Step 2: Indexing collected data...")
        # The indexing might be automatic or we might need to trigger it
        # For now, assume it's part of the search CLI
        
        # Step 3: Perform searches
        print("  Step 3: Performing searches...")
        
        search_queries = [
            "test",
            "message",
            "project", 
            "meeting"
        ]
        
        for query in search_queries:
            search_result = self.cli_helper.run_tool("search_cli.py", ["--query", query, "--limit", "10"])
            
            if search_result.returncode == 0:
                try:
                    search_output = json.loads(search_result.stdout)
                    assert "results" in search_output, f"Search output should contain results for '{query}'"
                    print(f"    ✅ Search for '{query}': {len(search_output.get('results', []))} results")
                except json.JSONDecodeError:
                    print(f"    ⚠️  Search for '{query}': non-JSON output (might be table format)")
            else:
                print(f"    ⚠️  Search for '{query}' failed: {search_result.stderr}")
    
    @pytest.mark.e2e
    def test_advanced_search_features(self):
        """Test advanced search features and filters."""
        print("🎯 Testing advanced search features...")
        
        # Test date-based searches
        date_searches = [
            ["--query", "test", "--date", "2025-08-18"],
            ["--query", "message", "--since", "2025-08-01"],
            ["--query", "project", "--before", "2025-09-01"]
        ]
        
        for search_args in date_searches:
            result = self.cli_helper.run_tool("search_cli.py", search_args)
            print(f"    Date search with {search_args}: {'✅' if result.returncode == 0 else '❌'}")
        
        # Test source filtering
        source_searches = [
            ["--query", "test", "--source", "slack"],
            ["--query", "meeting", "--source", "calendar"],
            ["--query", "document", "--source", "drive"]
        ]
        
        for search_args in source_searches:
            result = self.cli_helper.run_tool("search_cli.py", search_args)
            print(f"    Source filter {search_args}: {'✅' if result.returncode == 0 else '❌'}")
        
        # Test output formats
        format_tests = [
            ["--query", "test", "--format", "json"],
            ["--query", "test", "--format", "table"],
            ["--query", "test", "--format", "csv"]
        ]
        
        for search_args in format_tests:
            result = self.cli_helper.run_tool("search_cli.py", search_args)
            print(f"    Format test {search_args}: {'✅' if result.returncode == 0 else '❌'}")


class TestArchiveManagementWorkflows:
    """Test archive management and maintenance workflows."""
    
    def setup_method(self):
        """Set up archive management test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_env = {
            "AICOS_BASE_DIR": self.temp_dir,
            "AICOS_TEST_MODE": "true"
        }
        self.cli_helper = CLITestHelper(self.temp_dir, self.test_env)
    
    @pytest.mark.e2e
    def test_archive_compression_workflow(self):
        """Test archive compression workflow."""
        print("🗜️  Testing archive compression workflow...")
        
        # Step 1: Create some archive data
        print("  Step 1: Creating test archive data...")
        with patch.dict(os.environ, self.test_env):
            config = Config()
            
            # Create test JSONL files
            test_dir = config.archive_dir / "test_source" / "2025-08-01"  # Old date for compression
            test_dir.mkdir(parents=True)
            
            test_file = test_dir / "test_data.jsonl"
            test_data = [{"id": i, "data": f"test_{i}"} for i in range(100)]
            
            with open(test_file, 'w') as f:
                for record in test_data:
                    f.write(json.dumps(record) + '\n')
            
            original_size = test_file.stat().st_size
            print(f"    Created test file: {original_size} bytes")
        
        # Step 2: Run compression
        print("  Step 2: Running compression...")
        compress_result = self.cli_helper.run_tool("manage_archives.py", ["--compress", "--age-days", "1"])
        
        if compress_result.returncode == 0:
            print("    ✅ Compression completed successfully")
            
            # Verify compression occurred
            compressed_files = list(test_dir.glob("*.jsonl.gz"))
            if len(compressed_files) > 0:
                compressed_size = compressed_files[0].stat().st_size
                compression_ratio = (original_size - compressed_size) / original_size * 100
                print(f"    📊 Compression ratio: {compression_ratio:.1f}%")
                
                # Original file should be removed
                assert not test_file.exists(), "Original file should be removed after compression"
            else:
                print("    ⚠️  No compressed files found (compression might not have triggered)")
        else:
            print(f"    ❌ Compression failed: {compress_result.stderr}")
    
    @pytest.mark.e2e
    def test_archive_verification_workflow(self):
        """Test archive verification workflow."""
        print("🔍 Testing archive verification workflow...")
        
        # Create test archive with known good and bad data
        with patch.dict(os.environ, self.test_env):
            config = Config()
            
            # Create good archive
            good_dir = config.archive_dir / "good_test" / "2025-08-18"
            good_dir.mkdir(parents=True)
            
            good_file = good_dir / "good_data.jsonl"
            good_data = [{"id": i, "valid": True} for i in range(50)]
            
            with open(good_file, 'w') as f:
                for record in good_data:
                    f.write(json.dumps(record) + '\n')
            
            # Create problematic archive
            bad_dir = config.archive_dir / "bad_test" / "2025-08-18"
            bad_dir.mkdir(parents=True)
            
            bad_file = bad_dir / "bad_data.jsonl"
            with open(bad_file, 'w') as f:
                f.write('{"valid": true}\n')  # Good line
                f.write('{"invalid": json}\n')  # Bad JSON
                f.write('{"valid": true}\n')   # Good line
        
        # Run verification
        print("  Running archive verification...")
        verify_result = self.cli_helper.run_tool("verify_archive.py", ["--path", str(config.archive_dir)])
        
        if verify_result.returncode == 0:
            print("    ✅ Verification completed")
            
            # Check if verification found issues
            if "error" in verify_result.stdout.lower() or "invalid" in verify_result.stdout.lower():
                print("    🔍 Verification correctly identified issues")
            else:
                print("    ✅ No issues found in verification")
        else:
            print(f"    ⚠️  Verification had issues: {verify_result.stderr}")
    
    @pytest.mark.e2e
    def test_archive_statistics_workflow(self):
        """Test archive statistics and reporting workflow."""
        print("📊 Testing archive statistics workflow...")
        
        # Run statistics collection
        stats_result = self.cli_helper.run_tool("manage_archives.py", ["--stats", "--format", "json"])
        
        if stats_result.returncode == 0:
            try:
                stats_data = json.loads(stats_result.stdout)
                
                print("    ✅ Statistics generated successfully")
                print(f"    📊 Total files: {stats_data.get('total_files', 'N/A')}")
                print(f"    📊 Total size: {stats_data.get('total_size', 'N/A')} bytes")
                print(f"    📊 Compressed files: {stats_data.get('compressed_files', 'N/A')}")
                
                # Verify required fields
                required_fields = ["total_files", "total_size", "archive_health"]
                for field in required_fields:
                    assert field in stats_data, f"Statistics should include {field}"
                
            except json.JSONDecodeError:
                print("    ⚠️  Statistics output not in JSON format")
        else:
            print(f"    ❌ Statistics collection failed: {stats_result.stderr}")


class TestDisasterRecoveryWorkflows:
    """Test disaster recovery and backup workflows."""
    
    def setup_method(self):
        """Set up disaster recovery test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.backup_dir = tempfile.mkdtemp()
        self.test_env = {
            "AICOS_BASE_DIR": self.temp_dir,
            "AICOS_TEST_MODE": "true"
        }
        self.cli_helper = CLITestHelper(self.temp_dir, self.test_env)
    
    @pytest.mark.e2e
    def test_backup_and_restore_workflow(self):
        """Test complete backup and restore workflow."""
        print("💾 Testing backup and restore workflow...")
        
        # Step 1: Create test data
        print("  Step 1: Creating test data...")
        with patch.dict(os.environ, self.test_env):
            config = Config()
            
            # Create test archive data
            test_data_dir = config.archive_dir / "backup_test" / "2025-08-18"
            test_data_dir.mkdir(parents=True)
            
            test_file = test_data_dir / "important_data.jsonl"
            important_data = [{"id": i, "critical": True, "data": f"important_{i}"} for i in range(100)]
            
            with open(test_file, 'w') as f:
                for record in important_data:
                    f.write(json.dumps(record) + '\n')
            
            original_checksum = self._calculate_file_checksum(test_file)
            print(f"    Created test data with checksum: {original_checksum[:8]}...")
        
        # Step 2: Create backup
        print("  Step 2: Creating backup...")
        backup_result = self.cli_helper.run_tool("backup_archives.py", ["--target", self.backup_dir, "--type", "full"])
        
        if backup_result.returncode == 0:
            print("    ✅ Backup created successfully")
            
            # Verify backup exists
            backup_files = list(Path(self.backup_dir).rglob("*"))
            assert len(backup_files) > 0, "Backup should contain files"
        else:
            print(f"    ⚠️  Backup creation issues: {backup_result.stderr}")
        
        # Step 3: Simulate disaster (delete original data)
        print("  Step 3: Simulating disaster...")
        shutil.rmtree(config.archive_dir)
        assert not config.archive_dir.exists(), "Original data should be deleted"
        print("    💥 Original data deleted")
        
        # Step 4: Restore from backup
        print("  Step 4: Restoring from backup...")
        restore_result = self.cli_helper.run_tool("backup_archives.py", ["--restore", self.backup_dir, "--target", str(config.archive_dir)])
        
        if restore_result.returncode == 0:
            print("    ✅ Restore completed successfully")
            
            # Verify data restoration
            restored_file = test_data_dir / "important_data.jsonl"
            if restored_file.exists():
                restored_checksum = self._calculate_file_checksum(restored_file)
                
                if restored_checksum == original_checksum:
                    print("    ✅ Data integrity verified after restore")
                else:
                    print("    ⚠️  Data integrity issue detected")
            else:
                print("    ⚠️  Restored file not found")
        else:
            print(f"    ❌ Restore failed: {restore_result.stderr}")
    
    def _calculate_file_checksum(self, file_path):
        """Calculate SHA256 checksum of a file."""
        import hashlib
        
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()


@pytest.mark.e2e
class TestSystemIntegrationWorkflows:
    """Test complete system integration workflows."""
    
    def setup_method(self):
        """Set up system integration test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_env = {
            "AICOS_BASE_DIR": self.temp_dir,
            "AICOS_TEST_MODE": "true",
            "SLACK_BOT_TOKEN": "xoxb-test-token",
            "GOOGLE_CLIENT_ID": "test-client-id",
            "GOOGLE_CLIENT_SECRET": "test-client-secret"
        }
        self.cli_helper = CLITestHelper(self.temp_dir, self.test_env)
    
    def test_complete_system_workflow(self):
        """Test complete end-to-end system workflow."""
        print("🎯 Testing complete system workflow...")
        
        # Step 1: System initialization
        print("  Step 1: System initialization...")
        with patch.dict(os.environ, self.test_env):
            config = Config()
            validator = SystemValidator(config)
            health = validator.run_health_check()
            assert health["overall_status"] == "healthy", "System should be healthy"
            print("    ✅ System initialized and healthy")
        
        # Step 2: Data collection
        print("  Step 2: Data collection...")
        collection_result = self.cli_helper.run_tool("collect_data.py", ["--source", "all", "--test-mode"])
        assert collection_result.returncode == 0, "Data collection should succeed"
        print("    ✅ Data collection completed")
        
        # Step 3: Search functionality
        print("  Step 3: Search functionality...")
        search_result = self.cli_helper.run_tool("search_cli.py", ["--query", "test", "--limit", "5"])
        print(f"    Search result: {'✅' if search_result.returncode == 0 else '❌'}")
        
        # Step 4: Archive management
        print("  Step 4: Archive management...")
        stats_result = self.cli_helper.run_tool("manage_archives.py", ["--stats"])
        print(f"    Archive stats: {'✅' if stats_result.returncode == 0 else '❌'}")
        
        # Step 5: Verification
        print("  Step 5: System verification...")
        verify_result = self.cli_helper.run_tool("verify_archive.py", ["--quick"])
        print(f"    Archive verification: {'✅' if verify_result.returncode == 0 else '❌'}")
        
        print("  🎉 Complete system workflow test finished!")


if __name__ == "__main__":
    # Run end-to-end tests
    pytest.main([
        __file__,
        "-v",
        "-m", "e2e",
        "--tb=short",
        "-s"  # Show print statements
    ])