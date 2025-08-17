#!/usr/bin/env python3
"""
Tests for basic verification utilities
Following TDD approach - tests written first before implementation
"""

import json
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch

from tools.verify_archive import ArchiveVerifier, VerificationError


class TestSimpleVerification:
    """Test basic archive verification functionality"""

    def test_jsonl_format_validation(self):
        """Detects invalid JSONL format"""
        # ACCEPTANCE: Identifies malformed JSON lines
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            test_file = temp_path / "test.jsonl"
            
            # Create file with both valid and invalid JSON lines
            with open(test_file, 'w') as f:
                f.write('{"valid": true}\n')  # Line 1: valid
                f.write('{"another": "valid"}\n')  # Line 2: valid
                f.write('{"invalid": missing_quotes}\n')  # Line 3: invalid
                f.write('{"valid": "again"}\n')  # Line 4: valid
                f.write('incomplete json\n')  # Line 5: invalid
            
            verifier = ArchiveVerifier()
            errors = verifier.validate_jsonl_format(test_file)
            
            assert len(errors) == 2
            assert any(error['line_number'] == 3 for error in errors)
            assert any(error['line_number'] == 5 for error in errors)

    def test_file_existence_check(self):
        """Verifies expected files exist"""
        # ACCEPTANCE: Reports missing archive files
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create some files
            existing_file = temp_path / "existing.jsonl"
            existing_file.write_text('{"exists": true}\n')
            
            verifier = ArchiveVerifier()
            
            # Test existing file
            assert verifier.check_file_exists(existing_file) == True
            
            # Test non-existent file
            missing_file = temp_path / "missing.jsonl"
            assert verifier.check_file_exists(missing_file) == False

    def test_compression_integrity(self):
        """Validates compressed files can be read"""
        # ACCEPTANCE: Detects corrupted .gz files
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create and compress a valid file
            from src.core.compression import Compressor
            
            original_file = temp_path / "test.jsonl"
            original_file.write_text('{"test": "data"}\n')
            
            compressor = Compressor()
            compressed_file = compressor.compress(original_file)
            
            verifier = ArchiveVerifier()
            
            # Test valid compressed file
            assert verifier.validate_compressed_file(compressed_file) == True
            
            # Create an invalid compressed file (not actually gzipped)
            fake_compressed = temp_path / "fake.jsonl.gz"
            fake_compressed.write_text('not gzipped content')
            
            # Test invalid compressed file
            assert verifier.validate_compressed_file(fake_compressed) == False

    def test_directory_structure_validation(self):
        """Validates expected directory structure exists"""
        # ACCEPTANCE: Checks archive directory organization
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create expected structure
            archive_dir = temp_path / "archive"
            
            # Create all expected subdirectories
            subdirs = ['slack', 'calendar', 'drive', 'employees']
            for subdir in subdirs:
                subdir_path = archive_dir / subdir / "2025-08-15"
                subdir_path.mkdir(parents=True)
                (subdir_path / f"{subdir}.jsonl").write_text(f'{{"{subdir}": "test"}}\n')
            
            verifier = ArchiveVerifier()
            issues = verifier.validate_directory_structure(archive_dir)
            
            # Should find no issues with valid structure
            assert len(issues) == 0

    def test_verification_report_generation(self):
        """Generates comprehensive verification report"""
        # ACCEPTANCE: JSON report with detailed findings
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create test files with various issues
            good_file = temp_path / "good.jsonl"
            good_file.write_text('{"good": true}\n')
            
            bad_file = temp_path / "bad.jsonl"
            bad_file.write_text('invalid json\n')
            
            verifier = ArchiveVerifier()
            report = verifier.generate_report(temp_path)
            
            assert 'timestamp' in report
            assert 'files_checked' in report
            assert 'errors_found' in report
            assert 'summary' in report
            
            # Should have found at least one error
            assert report['errors_found'] > 0

    def test_verification_error_handling(self):
        """Handles verification errors gracefully"""
        # ACCEPTANCE: Raises VerificationError for invalid inputs
        verifier = ArchiveVerifier()
        
        # Test with non-existent directory
        with pytest.raises(VerificationError):
            verifier.validate_directory_structure(Path("nonexistent_directory"))
        
        # Test with non-existent file
        with pytest.raises(VerificationError):
            verifier.validate_jsonl_format(Path("nonexistent_file.jsonl"))

    def test_batch_verification(self):
        """Can verify multiple files efficiently"""
        # ACCEPTANCE: Processes multiple files in batch
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create multiple test files
            files = []
            for i in range(5):
                test_file = temp_path / f"test_{i}.jsonl"
                if i == 2:  # Make one file invalid
                    test_file.write_text('invalid json\n')
                else:
                    test_file.write_text(f'{{"file": {i}}}\n')
                files.append(test_file)
            
            verifier = ArchiveVerifier()
            results = verifier.verify_files_batch(files)
            
            assert len(results) == 5
            assert sum(1 for r in results if r['valid']) == 4  # 4 valid files
            assert sum(1 for r in results if not r['valid']) == 1  # 1 invalid file