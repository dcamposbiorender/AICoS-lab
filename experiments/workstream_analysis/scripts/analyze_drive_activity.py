#!/usr/bin/env python3
"""
Google Drive Activity Analysis for Workstream Mapping

Analyzes your Google Drive document activity to understand what documents
you're working on and how they relate to your workstreams.

Key Features:
- Maps documents to workstreams based on title and content patterns
- Identifies recently active documents you're collaborating on
- Analyzes document sharing patterns and collaboration
- Prioritizes documents by recent activity and relevance

Usage:
    python analyze_drive_activity.py
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any
from collections import defaultdict, Counter
import re

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Target email for analysis
TARGET_EMAIL = "david.campos@biorender.com"

# Document patterns that indicate workstreams
WORKSTREAM_DOCUMENT_PATTERNS = {
    "gtm_efficiency": {
        "title_keywords": ["pipeline", "sales", "gtm", "revenue", "funnel", "conversion", "quota", "forecast", "council"],
        "content_keywords": ["pipeline", "sales", "revenue", "forecast", "quota", "conversion", "funnel", "gtm"],
        "doc_types": ["presentation", "spreadsheet", "document"]
    },
    "data_platform": {
        "title_keywords": ["data", "analytics", "dashboard", "metrics", "looker", "signal", "insights", "reporting"],
        "content_keywords": ["data", "analytics", "dashboard", "metrics", "insights", "reporting", "looker"],
        "doc_types": ["spreadsheet", "document", "presentation"]
    },
    "ai_transformation": {
        "title_keywords": ["ai", "artificial intelligence", "automation", "agent", "governance", "ml", "machine learning", "chainlit"],
        "content_keywords": ["ai", "automation", "agent", "governance", "machine learning", "ml", "chainlit"],
        "doc_types": ["document", "presentation", "spreadsheet"]
    },
    "icp_expansion": {
        "title_keywords": ["icp", "persona", "segment", "tam", "market", "pricing", "expansion", "customer"],
        "content_keywords": ["icp", "persona", "segment", "market", "pricing", "expansion", "tam"],
        "doc_types": ["document", "presentation", "spreadsheet"]
    },
    "ai_bizops_team": {
        "title_keywords": ["hiring", "team", "interview", "headcount", "bizops", "org", "organizational"],
        "content_keywords": ["hiring", "interview", "team", "headcount", "bizops", "organizational"],
        "doc_types": ["document", "spreadsheet"]
    },
    "cost_optimization": {
        "title_keywords": ["cost", "budget", "efficiency", "optimization", "spend", "savings", "financial"],
        "content_keywords": ["cost", "budget", "efficiency", "spend", "savings", "optimization"],
        "doc_types": ["spreadsheet", "document"]
    },
    "executive": {
        "title_keywords": ["exec", "leadership", "strategy", "board", "offsites", "ofc", "management"],
        "content_keywords": ["exec", "leadership", "strategy", "board", "management", "offsites"],
        "doc_types": ["document", "presentation"]
    }
}

def find_drive_files(base_path: Path) -> List[Path]:
    """Find Drive data files"""
    drive_files = []
    
    drive_paths = [
        base_path / "data" / "raw" / "drive",
        base_path / "data" / "archive" / "drive"
    ]
    
    for drive_path in drive_paths:
        if not drive_path.exists():
            continue
            
        # Look for JSONL files in date subdirectories
        for date_dir in drive_path.glob("2025-*"):
            if date_dir.is_dir():
                for file_path in date_dir.glob("*.jsonl"):
                    drive_files.append(file_path)
                for file_path in date_dir.glob("*.json"):
                    drive_files.append(file_path)
    
    return drive_files

def classify_document_workstream(doc: Dict[str, Any]) -> Dict[str, float]:
    """Classify document into workstreams based on title and metadata"""
    scores = defaultdict(float)
    
    title = doc.get('name', '').lower()
    mime_type = doc.get('mimeType', '')
    
    # Map mime types to doc types
    doc_type = 'unknown'
    if 'document' in mime_type:
        doc_type = 'document'
    elif 'spreadsheet' in mime_type:
        doc_type = 'spreadsheet'  
    elif 'presentation' in mime_type:
        doc_type = 'presentation'
    
    for workstream, patterns in WORKSTREAM_DOCUMENT_PATTERNS.items():
        # Score based on title keywords
        for keyword in patterns['title_keywords']:
            if keyword in title:
                scores[workstream] += 3.0
        
        # Bonus for matching document types
        if doc_type in patterns['doc_types']:
            scores[workstream] += 1.0
    
    return dict(scores)

def analyze_document_activity(doc: Dict[str, Any], target_email: str) -> Dict[str, Any]:
    """Analyze activity metrics for a document"""
    
    # Parse modification time
    modified_time = doc.get('modifiedTime')
    if modified_time:
        try:
            modified_dt = datetime.fromisoformat(modified_time.replace('Z', '+00:00'))
            days_since_modified = (datetime.now(modified_dt.tzinfo) - modified_dt).days
        except:
            days_since_modified = 999
    else:
        days_since_modified = 999
    
    # Check if user is owner or collaborator
    owners = doc.get('owners', [])
    is_owner = any(owner.get('emailAddress') == target_email for owner in owners)
    
    # Get sharing info
    shared = doc.get('shared', False)
    
    # Calculate activity score
    activity_score = 0.0
    
    # Recent activity bonus
    if days_since_modified <= 7:
        activity_score += 5.0
    elif days_since_modified <= 30:
        activity_score += 3.0
    elif days_since_modified <= 90:
        activity_score += 1.0
    
    # Ownership bonus
    if is_owner:
        activity_score += 2.0
    
    # Sharing bonus (indicates collaboration)
    if shared:
        activity_score += 1.0
    
    return {
        'days_since_modified': days_since_modified,
        'is_owner': is_owner,
        'is_shared': shared,
        'activity_score': activity_score,
        'size_bytes': doc.get('size', 0)
    }

def analyze_drive_data(drive_files: List[Path], target_email: str) -> Dict[str, Any]:
    """Analyze Drive data for workstream insights"""
    
    all_documents = []
    workstream_docs = defaultdict(list)
    recent_activity = []
    collaboration_patterns = Counter()
    
    for drive_file in drive_files:
        print(f"Processing {drive_file}...")
        
        try:
            with open(drive_file, 'r', encoding='utf-8') as f:
                if drive_file.suffix == '.json':
                    # Single JSON file
                    data = json.load(f)
                    if 'files' in data:
                        docs = data['files']
                    else:
                        docs = [data] if isinstance(data, dict) else []
                else:
                    # JSONL file
                    docs = []
                    for line in f:
                        line = line.strip()
                        if line:
                            docs.append(json.loads(line))
                
                for doc in docs:
                    if not doc.get('name'):
                        continue
                        
                    # Skip folders
                    if doc.get('mimeType') == 'application/vnd.google-apps.folder':
                        continue
                    
                    # Classify workstream relevance
                    workstream_scores = classify_document_workstream(doc)
                    
                    # Analyze activity
                    activity = analyze_document_activity(doc, target_email)
                    
                    # Create document record
                    doc_record = {
                        'id': doc.get('id'),
                        'name': doc.get('name'),
                        'mime_type': doc.get('mimeType'),
                        'size': doc.get('size', 0),
                        'created_time': doc.get('createdTime'),
                        'modified_time': doc.get('modifiedTime'),
                        'web_view_link': doc.get('webViewLink'),
                        'workstream_scores': workstream_scores,
                        'primary_workstream': max(workstream_scores, key=workstream_scores.get) if workstream_scores else 'unclassified',
                        'activity': activity,
                        'owners': [owner.get('emailAddress') for owner in doc.get('owners', [])],
                        'shared': doc.get('shared', False)
                    }
                    
                    all_documents.append(doc_record)
                    
                    # Group by workstream
                    if workstream_scores:
                        primary_workstream = max(workstream_scores, key=workstream_scores.get)
                        workstream_docs[primary_workstream].append(doc_record)
                    
                    # Track recent activity
                    if activity['days_since_modified'] <= 30:
                        recent_activity.append(doc_record)
                    
                    # Track collaboration
                    if doc_record['shared']:
                        collaboration_patterns['shared_docs'] += 1
                    if activity['is_owner']:
                        collaboration_patterns['owned_docs'] += 1
                        
        except Exception as e:
            print(f"Error processing {drive_file}: {e}")
            continue
    
    return {
        'documents': all_documents,
        'workstream_documents': dict(workstream_docs),
        'recent_activity': sorted(recent_activity, key=lambda x: x['activity']['activity_score'], reverse=True),
        'collaboration_stats': dict(collaboration_patterns),
        'analysis_stats': {
            'total_documents': len(all_documents),
            'classified_documents': len([d for d in all_documents if d['primary_workstream'] != 'unclassified']),
            'recently_active': len(recent_activity),
            'owned_documents': collaboration_patterns.get('owned_docs', 0),
            'shared_documents': collaboration_patterns.get('shared_docs', 0)
        }
    }

def generate_drive_insights(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Generate insights from Drive analysis"""
    
    workstream_doc_counts = {
        workstream: len(docs) 
        for workstream, docs in analysis['workstream_documents'].items()
    }
    
    # Get top documents by activity score
    top_active_docs = sorted(
        analysis['documents'],
        key=lambda x: x['activity']['activity_score'],
        reverse=True
    )[:20]
    
    # Group recent activity by workstream
    recent_by_workstream = defaultdict(list)
    for doc in analysis['recent_activity']:
        recent_by_workstream[doc['primary_workstream']].append(doc)
    
    insights = {
        'workstream_document_distribution': workstream_doc_counts,
        'top_active_documents': top_active_docs,
        'recent_activity_by_workstream': dict(recent_by_workstream),
        'document_type_breakdown': Counter(
            doc['mime_type'] for doc in analysis['documents']
        ),
        'ownership_vs_collaboration': {
            'owned': analysis['collaboration_stats'].get('owned_docs', 0),
            'shared': analysis['collaboration_stats'].get('shared_docs', 0),
            'total': len(analysis['documents'])
        }
    }
    
    return insights

def main():
    """Main execution function"""
    print("Starting Google Drive activity analysis...")
    
    # Setup paths
    base_path = Path(__file__).parent.parent.parent.parent
    output_path = Path(__file__).parent.parent / "data_extraction"
    
    # Find Drive files
    print("Finding Drive data files...")
    drive_files = find_drive_files(base_path)
    
    if not drive_files:
        print("ERROR: No Drive files found")
        return
    
    print(f"Found {len(drive_files)} Drive data files")
    
    # Analyze Drive data
    print("Analyzing Drive documents...")
    analysis = analyze_drive_data(drive_files, TARGET_EMAIL)
    
    # Generate insights
    print("Generating insights...")
    insights = generate_drive_insights(analysis)
    
    # Save results
    output_file = output_path / "drive_activity_analysis.json"
    output_data = {
        'analysis_metadata': {
            'target_user': TARGET_EMAIL,
            'drive_files_processed': [str(f) for f in drive_files],
            'analysis_timestamp': datetime.now().isoformat()
        },
        'analysis': analysis,
        'insights': insights
    }
    
    output_path.mkdir(exist_ok=True)
    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)
    
    # Print summary
    print(f"\n=== DRIVE ANALYSIS SUMMARY ===")
    print(f"Total documents: {analysis['analysis_stats']['total_documents']}")
    print(f"Classified documents: {analysis['analysis_stats']['classified_documents']}")
    print(f"Recently active (30 days): {analysis['analysis_stats']['recently_active']}")
    print(f"Documents you own: {analysis['analysis_stats']['owned_documents']}")
    print(f"Shared documents: {analysis['analysis_stats']['shared_documents']}")
    
    print(f"\n=== TOP WORKSTREAMS BY DOCUMENT COUNT ===")
    for workstream, count in sorted(insights['workstream_document_distribution'].items(), 
                                   key=lambda x: x[1], reverse=True)[:5]:
        print(f"{workstream}: {count} documents")
    
    print(f"\n=== MOST ACTIVE RECENT DOCUMENTS ===")
    for doc in insights['top_active_documents'][:5]:
        score = doc['activity']['activity_score']
        days = doc['activity']['days_since_modified']
        print(f"{doc['name'][:50]}... (Score: {score:.1f}, {days} days ago)")
    
    print(f"\nResults saved to: {output_file}")

if __name__ == "__main__":
    main()