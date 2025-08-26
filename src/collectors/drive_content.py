#!/usr/bin/env python3
"""
Drive Content Extraction - Phase 1.5 Implementation
Minimal Drive content extraction to bridge Phase 1 and Phase 2

This module provides basic Drive content extraction using existing 
infrastructure, focusing on meeting notes and documents that can
provide immediate value to the AI Chief of Staff system.

Architecture:
- Uses existing DocxContentExtractor for document parsing
- Integrates with search database for indexing
- Provides structured output compatible with Phase 1 components
- Lab-grade implementation focused on essential functionality

Implementation Status: FUNCTIONAL MINIMAL VERSION
Ready for Phase 2 intelligence integration
"""

import logging
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

from ..extractors.docx_extractor import DocxContentExtractor, ExtractedDocument
from ..search.database import SearchDatabase
from ..core.config import get_config

logger = logging.getLogger(__name__)


@dataclass
class DriveContentResult:
    """Results from Drive content extraction"""
    documents_processed: int
    documents_indexed: int
    content_extracted: bool
    processing_duration: float
    extracted_documents: List[Dict[str, Any]]
    errors: List[str]


class DriveContentExtractor:
    """
    Minimal Drive content extraction for Phase 1.5
    
    Focuses on local document processing and indexing to provide
    immediate value while preparing for Phase 2 intelligence integration.
    """
    
    def __init__(self, base_path: Path = None):
        self.base_path = Path(base_path or get_config().base_dir)
        self.docx_extractor = DocxContentExtractor(preserve_structure=True)
        self.search_db = SearchDatabase(str(self.base_path / "data" / "search.db"))
        
        # Common Drive document locations for lab-grade detection
        self.search_paths = [
            self.base_path / "data" / "drive",
            self.base_path / "documents",
            Path.home() / "Downloads",  # Common location for downloaded meeting notes
            Path.home() / "Documents" / "Meeting Notes"
        ]
        
        logger.info(f"Drive Content Extractor initialized")
        logger.info(f"Base path: {self.base_path}")
        logger.info(f"Search paths: {[str(p) for p in self.search_paths if p.exists()]}")
    
    def extract_drive_content(self) -> DriveContentResult:
        """
        Extract and index Drive content from local paths
        
        This is a Phase 1.5 implementation that focuses on local document
        processing without requiring Drive API integration.
        """
        start_time = datetime.now()
        extracted_documents = []
        errors = []
        documents_processed = 0
        documents_indexed = 0
        
        logger.info("Starting Drive content extraction...")
        
        # Find and process DOCX files in search paths
        for search_path in self.search_paths:
            if not search_path.exists():
                continue
                
            logger.info(f"Scanning path: {search_path}")
            
            try:
                # Find DOCX files (meeting notes, documents)
                docx_files = list(search_path.rglob("*.docx"))
                logger.info(f"Found {len(docx_files)} DOCX files in {search_path}")
                
                for docx_file in docx_files:
                    try:
                        # Extract content using existing extractor
                        extracted_doc = self.docx_extractor.extract_content(str(docx_file))
                        
                        if extracted_doc and extracted_doc.content.strip():
                            # Convert to searchable record format
                            search_record = self._convert_to_search_record(extracted_doc, docx_file)
                            
                            # Index in search database
                            result = self.search_db.index_records_batch([search_record], 'drive')
                            
                            if result['indexed'] > 0:
                                extracted_documents.append(search_record)
                                documents_indexed += 1
                                logger.info(f"Indexed document: {docx_file.name}")
                            else:
                                errors.append(f"Failed to index: {docx_file.name}")
                        
                        documents_processed += 1
                        
                    except Exception as e:
                        error_msg = f"Error processing {docx_file.name}: {str(e)}"
                        errors.append(error_msg)
                        logger.error(error_msg)
                        continue
                        
            except Exception as e:
                error_msg = f"Error scanning path {search_path}: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)
                continue
        
        # Calculate processing duration
        processing_duration = (datetime.now() - start_time).total_seconds()
        
        # Create result
        result = DriveContentResult(
            documents_processed=documents_processed,
            documents_indexed=documents_indexed,
            content_extracted=documents_indexed > 0,
            processing_duration=processing_duration,
            extracted_documents=extracted_documents,
            errors=errors
        )
        
        logger.info(f"Drive content extraction completed:")
        logger.info(f"  Processed: {documents_processed} documents")
        logger.info(f"  Indexed: {documents_indexed} documents")
        logger.info(f"  Duration: {processing_duration:.2f}s")
        logger.info(f"  Errors: {len(errors)}")
        
        return result
    
    def _convert_to_search_record(self, extracted_doc: ExtractedDocument, 
                                 file_path: Path) -> Dict[str, Any]:
        """
        Convert extracted document to search database record format
        
        Compatible with existing search database schema and Phase 1 components.
        """
        # Extract date from filename or file stats
        try:
            file_date = datetime.fromtimestamp(file_path.stat().st_mtime).strftime('%Y-%m-%d')
        except:
            file_date = datetime.now().strftime('%Y-%m-%d')
        
        # Serialize datetime objects in meeting_metadata safely
        safe_meeting_metadata = {}
        for key, value in extracted_doc.meeting_metadata.items():
            if isinstance(value, datetime):
                safe_meeting_metadata[key] = value.isoformat()
            elif hasattr(value, 'isoformat'):  # Handle date objects
                safe_meeting_metadata[key] = value.isoformat()
            else:
                safe_meeting_metadata[key] = value
        
        # Create search record
        search_record = {
            'id': f"drive_{file_path.stem}_{file_path.stat().st_mtime}",
            'content': extracted_doc.content,
            'source': 'drive',
            'created_at': datetime.fromtimestamp(file_path.stat().st_mtime).isoformat() + 'Z',
            'date': file_date,
            'metadata': json.dumps({
                'filename': extracted_doc.filename,
                'title': extracted_doc.title,
                'file_path': str(file_path),
                'file_size_bytes': file_path.stat().st_size,
                'meeting_metadata': safe_meeting_metadata,
                'confidence_score': extracted_doc.confidence_score,
                'extraction_stats': extracted_doc.extraction_stats
            }),
            'person_id': None,  # Phase 1.5 doesn't extract person from documents
            'channel_id': str(file_path.parent.name)  # Use directory name as channel
        }
        
        return search_record
    
    def get_extraction_stats(self) -> Dict[str, Any]:
        """Get statistics about Drive content extraction"""
        stats = self.search_db.get_stats()
        
        drive_stats = {
            'total_drive_records': stats.get('records_by_source', {}).get('drive', 0),
            'search_paths_available': len([p for p in self.search_paths if p.exists()]),
            'extractor_stats': self.docx_extractor.stats if hasattr(self.docx_extractor, 'stats') else {}
        }
        
        return drive_stats


def create_drive_content_extractor(base_path: Path = None) -> DriveContentExtractor:
    """Factory function to create Drive content extractor"""
    return DriveContentExtractor(base_path)


# CLI interface for testing
if __name__ == "__main__":
    import sys
    
    print("🚀 Drive Content Extractor - Phase 1.5")
    print("=" * 50)
    
    try:
        extractor = DriveContentExtractor()
        result = extractor.extract_drive_content()
        
        print(f"✅ Processing completed:")
        print(f"   📄 Documents processed: {result.documents_processed}")
        print(f"   📇 Documents indexed: {result.documents_indexed}")
        print(f"   ⏱️  Duration: {result.processing_duration:.2f}s")
        print(f"   ❌ Errors: {len(result.errors)}")
        
        if result.errors:
            print("\n⚠️  Errors encountered:")
            for error in result.errors[:5]:  # Show first 5 errors
                print(f"   • {error}")
        
        if result.extracted_documents:
            print(f"\n📋 Sample extracted documents:")
            for doc in result.extracted_documents[:3]:  # Show first 3
                metadata = json.loads(doc['metadata'])
                print(f"   • {metadata['filename']} ({doc['date']})")
        
        # Show extraction stats
        stats = extractor.get_extraction_stats()
        print(f"\n📊 Extraction Statistics:")
        print(f"   Total Drive records: {stats['total_drive_records']}")
        print(f"   Available search paths: {stats['search_paths_available']}")
        
        print("\n🎯 Phase 1.5 Drive content extraction ready for Phase 2!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)