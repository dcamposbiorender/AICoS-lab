#!/usr/bin/env python3
"""
Test script for the enhanced Drive collector with DriveToRag patterns.
"""

import sys
from pathlib import Path

# Add src to path so we can import
sys.path.insert(0, str(Path(__file__).parent / "src"))

from collectors.drive import DriveArchiveWrapper
import json

def test_enhanced_drive_collector():
    """Test the enhanced Drive collector functionality."""
    print("Testing Enhanced Drive Collector with DriveToRag Patterns")
    print("=" * 60)
    
    # Create collector instance
    collector = DriveArchiveWrapper()
    
    # Test data collection
    print("\n1. Testing data collection...")
    try:
        result = collector.collect()
        print("✅ Data collection successful")
        
        # Check data structure
        assert 'data' in result, "Missing 'data' key in result"
        assert 'metadata' in result, "Missing 'metadata' key in result"
        
        data = result['data']
        files = data.get('files', [])
        changes = data.get('changes', [])
        
        print(f"   - Files collected: {len(files)}")
        print(f"   - Changes tracked: {len(changes)}")
        
        # Test file categorization
        print("\n2. Testing file categorization...")
        categories_found = set()
        for file_data in files:
            category = file_data.get('category')
            categories_found.add(category)
            print(f"   - {file_data['name']}: {category} ({file_data['mimeType']})")
            
            # Verify required fields
            required_fields = ['id', 'name', 'mimeType', 'category', 'content_hash', 'extractable', 'processing_priority']
            for field in required_fields:
                assert field in file_data, f"Missing required field '{field}' in file data"
        
        print(f"   ✅ Found {len(categories_found)} categories: {', '.join(categories_found)}")
        
        # Test content hashing
        print("\n3. Testing content hashing...")
        hashes_found = []
        for file_data in files:
            content_hash = file_data.get('content_hash')
            assert content_hash, "Missing content hash"
            assert len(content_hash) > 10, "Content hash too short"
            hashes_found.append(content_hash)
            print(f"   - {file_data['name']}: {content_hash}")
        
        # Verify hashes are unique
        assert len(set(hashes_found)) == len(hashes_found), "Content hashes should be unique"
        print("   ✅ All content hashes are unique")
        
        # Test change tracking
        print("\n4. Testing change tracking...")
        for change in changes:
            assert 'content_hash_changed' in change, "Missing content_hash_changed in change record"
            assert 'new_hash' in change, "Missing new_hash in change record"
            print(f"   - Change {change['changeId']}: {change['operation']} on {change['fileId']}")
        
        print("   ✅ Change tracking includes content hashes")
        
        # Test collection metadata
        print("\n5. Testing collection metadata...")
        metadata = data.get('collection_metadata', {})
        required_metadata = ['file_type_breakdown', 'extractable_files', 'total_estimated_extraction_time']
        for field in required_metadata:
            assert field in metadata, f"Missing metadata field '{field}'"
            
        print(f"   - File type breakdown: {metadata['file_type_breakdown']}")
        print(f"   - Extractable files: {metadata['extractable_files']}")
        print(f"   - Estimated extraction time: {metadata['total_estimated_extraction_time']:.1f}s")
        print("   ✅ Enhanced metadata collection working")
        
        # Test state management
        print("\n6. Testing state management...")
        state = collector.get_state()
        
        enhanced_state_fields = ['content_hashes_tracked', 'file_categories_supported', 'extraction_ready_files']
        for field in enhanced_state_fields:
            assert field in state, f"Missing enhanced state field '{field}'"
            
        print(f"   - Categories supported: {len(state['file_categories_supported'])}")
        print(f"   - Extraction ready files: {state['extraction_ready_files']}")
        print("   ✅ Enhanced state management working")
        
        print("\n" + "=" * 60)
        print("🎉 ALL TESTS PASSED!")
        print("Enhanced Drive collector with DriveToRag patterns is working correctly.")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_enhanced_drive_collector()
    sys.exit(0 if success else 1)