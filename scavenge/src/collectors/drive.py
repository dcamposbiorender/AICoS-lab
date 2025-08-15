#!/usr/bin/env python3
"""
Google Drive Raw Data Ingestor
90-day comprehensive document extraction and content processing
"""

import json
import sys
import io
from datetime import datetime, timedelta
from pathlib import Path

# Add paths for existing Google integration
sys.path.insert(0, '../../chief_of_staff/api_tools')
sys.path.insert(0, '../credentials')

from secure_config import secure_config  
from real_google_apis import RealGoogleAPIs

class DriveIngestor:
    """Raw Google Drive data extraction with content processing"""
    
    def __init__(self):
        self.data_root = Path(__file__).parent
        self.drive_dir = self.data_root / "drive_raw"
        self.drive_dir.mkdir(exist_ok=True)
        
        # Date range (90 days)
        self.end_date = datetime.now()
        self.start_date = self.end_date - timedelta(days=90)
        
        # Target mimeTypes for content extraction
        self.target_mimetypes = {
            'application/vnd.google-apps.document': 'gdoc',
            'application/vnd.google-apps.presentation': 'gslides', 
            'application/vnd.google-apps.spreadsheet': 'gsheets',
            'text/plain': 'txt',
            'application/pdf': 'pdf',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx'
        }
        
        print(f"💾 Drive Ingestor initialized")
        print(f"📅 Date Range: {self.start_date.strftime('%Y-%m-%d')} → {self.end_date.strftime('%Y-%m-%d')}")
        print(f"🎯 Target Types: {list(self.target_mimetypes.values())}")
    
    def log_event(self, message: str):
        """Simple logging"""
        timestamp = datetime.now().isoformat()
        print(f"💾 {timestamp}: {message}")
        
        # Also log to main ingestion log
        log_file = self.data_root / "logs" / "ingestion_log.jsonl"
        log_entry = {
            "timestamp": timestamp,
            "event_type": "DRIVE",
            "message": message,
            "data": {}
        }
        
        with open(log_file, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
    
    def extract_text_content(self, service, file_metadata):
        """Extract text content from various file types"""
        file_id = file_metadata['id']
        mime_type = file_metadata['mimeType']
        
        try:
            if mime_type == 'application/vnd.google-apps.document':
                # Google Docs - export as plain text
                content = service.files().export(
                    fileId=file_id, 
                    mimeType='text/plain'
                ).execute()
                return content.decode('utf-8')
                
            elif mime_type == 'application/vnd.google-apps.presentation':
                # Google Slides - export as plain text
                content = service.files().export(
                    fileId=file_id,
                    mimeType='text/plain'
                ).execute()
                return content.decode('utf-8')
                
            elif mime_type == 'application/vnd.google-apps.spreadsheet':
                # Google Sheets - export as CSV then convert to readable text
                content = service.files().export(
                    fileId=file_id,
                    mimeType='text/csv'
                ).execute()
                return content.decode('utf-8')
                
            elif mime_type == 'text/plain':
                # Plain text files
                content = service.files().get_media(fileId=file_id).execute()
                return content.decode('utf-8')
                
            elif mime_type == 'application/pdf':
                # PDF files - just save metadata, content extraction would need additional libs
                return f"[PDF FILE: {file_metadata.get('name', 'unknown')} - Content extraction requires additional processing]"
                
            else:
                return f"[UNSUPPORTED MIME TYPE: {mime_type}]"
                
        except Exception as e:
            self.log_event(f"Content extraction failed for {file_id}: {str(e)}")
            return f"[EXTRACTION FAILED: {str(e)}]"
    
    async def ingest_drive_files(self):
        """Extract Drive files and content from 90-day period"""
        self.log_event("Starting Google Drive ingestion")
        
        try:
            # Get authenticated Drive service
            google_apis = RealGoogleAPIs()
            service = google_apis.get_service('drive', 'v3')
            self.log_event("Drive service authenticated")
            
            # Build query for files modified in last 90 days
            query_parts = [
                f"modifiedTime >= '{self.start_date.isoformat()}'",
                f"modifiedTime <= '{self.end_date.isoformat()}'",
                "trashed = false"
            ]
            
            # Add mimeType filter
            mime_filter = " or ".join([f"mimeType = '{mt}'" for mt in self.target_mimetypes.keys()])
            query_parts.append(f"({mime_filter})")
            
            query = " and ".join(query_parts)
            self.log_event(f"Drive query: {query}")
            
            # Get files matching criteria
            files_result = service.files().list(
                q=query,
                fields="nextPageToken, files(id, name, mimeType, size, createdTime, modifiedTime, owners, lastModifyingUser, parents, webViewLink, shared)",
                pageSize=1000
            ).execute()
            
            files = files_result.get('files', [])
            self.log_event(f"Found {len(files)} files matching criteria")
            
            processed_files = []
            content_extracted = 0
            
            for i, file_metadata in enumerate(files):
                file_id = file_metadata['id']
                file_name = file_metadata.get('name', 'unknown')
                mime_type = file_metadata['mimeType']
                
                self.log_event(f"Processing {i+1}/{len(files)}: {file_name}")
                
                # Extract content if it's a supported type
                content = ""
                if mime_type in self.target_mimetypes:
                    content = self.extract_text_content(service, file_metadata)
                    if content and not content.startswith('['):
                        content_extracted += 1
                
                # Save content to individual file
                if content:
                    content_file = self.drive_dir / f"file_{file_id}.txt"
                    with open(content_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                
                # Prepare metadata
                file_data = {
                    'file_id': file_id,
                    'name': file_name,
                    'mimeType': mime_type,
                    'size': file_metadata.get('size'),
                    'createdTime': file_metadata.get('createdTime'),
                    'modifiedTime': file_metadata.get('modifiedTime'),
                    'owners': file_metadata.get('owners', []),
                    'lastModifyingUser': file_metadata.get('lastModifyingUser', {}),
                    'parents': file_metadata.get('parents', []),
                    'webViewLink': file_metadata.get('webViewLink'),
                    'shared': file_metadata.get('shared', False),
                    'content_extracted': bool(content and not content.startswith('[')),
                    'content_file': f"file_{file_id}.txt" if content else None
                }
                
                processed_files.append(file_data)
            
            # Save file metadata index
            metadata_file = self.drive_dir / "drive_files_metadata.jsonl"
            with open(metadata_file, 'w') as f:
                for file_data in processed_files:
                    f.write(json.dumps(file_data) + '\n')
            
            # Generate summary
            summary = {
                "ingestion_timestamp": datetime.now().isoformat(),
                "date_range": {
                    "start": self.start_date.isoformat(),
                    "end": self.end_date.isoformat()
                },
                "total_files_found": len(files),
                "total_files_processed": len(processed_files),
                "content_extracted_count": content_extracted,
                "supported_mimetypes": self.target_mimetypes,
                "metadata_file": str(metadata_file)
            }
            
            summary_file = self.drive_dir / "drive_summary.json"
            with open(summary_file, 'w') as f:
                json.dump(summary, f, indent=2)
            
            self.log_event(f"Drive ingestion complete: {len(processed_files)} files processed, {content_extracted} with content extracted")
            return True
            
        except Exception as e:
            self.log_event(f"Drive ingestion failed: {str(e)}")
            return False

if __name__ == "__main__":
    import asyncio
    
    async def main():
        ingestor = DriveIngestor()
        success = await ingestor.ingest_drive_files()
        
        if success:
            print("✅ Drive ingestion completed successfully")
        else:
            print("❌ Drive ingestion failed")
    
    asyncio.run(main())