"""
Sample archive data for testing purposes.

Provides pre-built archive samples for performance and integration testing.
"""

import json
import tempfile
from pathlib import Path
from typing import Dict, List, Any

def create_sample_archive(record_count: int = 1000) -> Path:
    """Create a sample archive directory with test data."""
    temp_dir = Path(tempfile.mkdtemp())
    archive_dir = temp_dir / "sample_archive"
    archive_dir.mkdir(exist_ok=True)
    
    # Create slack directory with sample data
    slack_dir = archive_dir / "slack" / "2025-08-19"
    slack_dir.mkdir(parents=True, exist_ok=True)
    
    sample_records = []
    for i in range(record_count):
        sample_records.append({
            "id": f"sample_msg_{i}",
            "text": f"Sample message {i} for testing search and indexing performance",
            "user": f"U{1000000 + i % 100:07d}",
            "channel": f"C{1000000 + i % 20:07d}",
            "ts": f"172400000{i:06d}.000000",
            "type": "message"
        })
    
    # Write to JSONL file
    data_file = slack_dir / "data.jsonl"
    with open(data_file, 'w') as f:
        for record in sample_records:
            f.write(json.dumps(record) + '\n')
    
    # Create manifest
    manifest = {
        "source": "slack",
        "date": "2025-08-19",
        "record_count": record_count,
        "files": ["data.jsonl"]
    }
    
    with open(slack_dir / "manifest.json", 'w') as f:
        json.dump(manifest, f, indent=2)
    
    return archive_dir

def get_sample_messages(count: int = 100) -> List[Dict[str, Any]]:
    """Get sample Slack messages for testing."""
    messages = []
    for i in range(count):
        messages.append({
            "id": f"test_msg_{i}",
            "text": f"Test message {i} with various keywords like project, meeting, discussion",
            "user": f"U{1000000 + i % 10:07d}",
            "channel": f"C{1000000 + i % 5:07d}",
            "ts": f"172400000{i:06d}.000000",
            "type": "message"
        })
    return messages