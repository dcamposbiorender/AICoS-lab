#!/usr/bin/env python3
"""
Email Collector - Meeting Notes Processing Module
Processes .eml files from Google Meet/Gemini for action item extraction

This collector specifically handles meeting notes emails that arrive as .eml files
from Google Meet with Gemini-generated content, typically base64 encoded.

Architecture:
- Follows BaseArchiveCollector interface for consistency
- Integrates with existing auth_manager.py and archive_writer.py
- Uses JSONL format for persistent storage
- Implements robust error handling for email parsing edge cases

Usage:
    from src.collectors.email_collector import EmailCollector
    collector = EmailCollector()
    result = collector.collect()
"""

import base64
import email
import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import decode_header
from email.utils import parsedate_to_datetime

# Import existing system components
try:
    from ..core.config import get_config
    from ..core.state import StateManager
    from ..core.archive_writer import ArchiveWriter
    from .base import BaseArchiveCollector, CollectorError
    from .circuit_breaker import CircuitBreaker
except ImportError:
    # Fallback for direct execution
    print("Warning: Could not import core components. Running in standalone mode.")
    
    class BaseArchiveCollector:
        def __init__(self, collector_type, config_path=None):
            self.collector_type = collector_type
            
    class CollectorError(Exception):
        pass

logger = logging.getLogger(__name__)


@dataclass
class ParsedEmail:
    """Structured representation of parsed meeting notes email"""
    subject: str
    from_address: str
    to_addresses: List[str]
    date: datetime
    meeting_title: str
    meeting_date: Optional[datetime]
    participants: List[str]
    content: str
    source_file: str
    confidence_score: float
    raw_headers: Dict[str, str]
    

class EmailParsingError(CollectorError):
    """Raised when email parsing fails"""
    pass


class EmailCollector(BaseArchiveCollector):
    """
    Collector for processing meeting notes emails (.eml files)
    
    Features:
    - Google Meet/Gemini email detection and parsing
    - Base64 content decoding with error recovery
    - Meeting metadata extraction (title, participants, date)
    - Integration with existing archive system
    - Robust error handling for malformed emails
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize EmailCollector
        
        Args:
            config_path: Optional path to config file
        """
        super().__init__(collector_type="email", config_path=config_path)
        self.logger = logging.getLogger(f"{__name__}.EmailCollector")
        
        # Email parsing patterns
        self._compile_patterns()
        
        # Processing statistics
        self.stats = {
            'files_processed': 0,
            'successful_parses': 0,
            'failed_parses': 0,
            'emails_extracted': 0,
            'start_time': None,
            'end_time': None
        }
    
    def _compile_patterns(self):
        """Compile regex patterns for email content extraction"""
        
        # Meeting notes file pattern
        self.meeting_notes_pattern = re.compile(
            r'Notes_.*\.eml$', 
            re.IGNORECASE
        )
        
        # Google Meet/Gemini signature patterns
        self.gemini_patterns = [
            re.compile(r'Notes from ["\u201c](.+?)["\u201d]', re.IGNORECASE),
            re.compile(r'Meeting started \d{4}_\d{2}_\d{2}', re.IGNORECASE),
            re.compile(r'Notes by Gemini', re.IGNORECASE),
            re.compile(r'Google Meet', re.IGNORECASE)
        ]
        
        # Meeting title extraction patterns
        self.title_patterns = [
            re.compile(r'Notes from ["\u201c](.+?)["\u201d]'),
            re.compile(r'Subject:.*Notes.*["\u201c](.+?)["\u201d]', re.IGNORECASE),
            re.compile(r'^(.+?) - \d{4}_\d{2}_\d{2}.*Notes by Gemini', re.IGNORECASE)
        ]
        
        # Participant extraction patterns
        self.participant_patterns = [
            re.compile(r'participants?[:\s]+(.+?)(?:\n\n|\n[A-Z])', re.IGNORECASE | re.DOTALL),
            re.compile(r'attendees?[:\s]+(.+?)(?:\n\n|\n[A-Z])', re.IGNORECASE | re.DOTALL),
            re.compile(r'including\s+([A-Za-z\s,]+?)(?:\s+discussed|\s+,)', re.IGNORECASE)
        ]
    
    def collect(self, source_dirs: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Main collection method - scan directories for meeting notes emails
        
        Args:
            source_dirs: Optional list of directories to scan. Defaults to Downloads.
            
        Returns:
            Dict with collection results and statistics
        """
        self.stats['start_time'] = datetime.now()
        self.logger.info(f"Starting email collection for meeting notes")
        
        try:
            # Default to user's Downloads directory if not specified
            if source_dirs is None:
                source_dirs = [
                    os.path.expanduser("~/Downloads"),
                    "/Users/david.campos/Downloads"  # Explicit path for user's setup
                ]
            
            all_emails = []
            
            for source_dir in source_dirs:
                if os.path.exists(source_dir):
                    self.logger.info(f"Scanning directory: {source_dir}")
                    dir_emails = self._scan_directory(source_dir)
                    all_emails.extend(dir_emails)
                else:
                    self.logger.warning(f"Directory not found: {source_dir}")
            
            # Process discovered emails
            processed_emails = []
            for email_file in all_emails:
                try:
                    parsed_email = self.parse_eml_file(email_file)
                    if parsed_email:
                        processed_emails.append(parsed_email)
                        self.stats['successful_parses'] += 1
                        self.stats['emails_extracted'] += 1
                except Exception as e:
                    self.logger.error(f"Failed to parse {email_file}: {e}")
                    self.stats['failed_parses'] += 1
                
                self.stats['files_processed'] += 1
            
            # Archive processed emails using existing system
            if processed_emails and hasattr(self, 'archive_writer'):
                for email_data in processed_emails:
                    self.archive_writer.write_record(email_data.__dict__)
            
            self.stats['end_time'] = datetime.now()
            processing_time = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
            
            results = {
                'success': True,
                'emails_processed': len(processed_emails),
                'files_scanned': self.stats['files_processed'],
                'processing_time_seconds': processing_time,
                'emails': [email.__dict__ for email in processed_emails],
                'statistics': self.stats
            }
            
            self.logger.info(f"Email collection completed: {len(processed_emails)} emails processed")
            return results
            
        except Exception as e:
            self.logger.error(f"Email collection failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'statistics': self.stats
            }
    
    def _scan_directory(self, directory: str) -> List[str]:
        """
        Scan directory for meeting notes .eml files
        
        Args:
            directory: Directory path to scan
            
        Returns:
            List of .eml file paths that match meeting notes patterns
        """
        email_files = []
        
        try:
            for filename in os.listdir(directory):
                if self.meeting_notes_pattern.match(filename):
                    file_path = os.path.join(directory, filename)
                    if os.path.isfile(file_path):
                        email_files.append(file_path)
                        self.logger.debug(f"Found meeting notes email: {filename}")
        
        except PermissionError:
            self.logger.warning(f"Permission denied scanning directory: {directory}")
        except Exception as e:
            self.logger.error(f"Error scanning directory {directory}: {e}")
        
        return sorted(email_files)  # Process in alphabetical order
    
    def parse_eml_file(self, file_path: str) -> Optional[ParsedEmail]:
        """
        Parse a single .eml file and extract meeting notes data
        
        Args:
            file_path: Path to .eml file
            
        Returns:
            ParsedEmail object with extracted data, or None if parsing fails
        """
        self.logger.debug(f"Parsing email file: {file_path}")
        
        try:
            # Read email file
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                email_content = f.read()
            
            # Parse email using Python's email library
            msg = email.message_from_string(email_content)
            
            # Extract basic email headers
            headers = self._extract_headers(msg)
            
            # Extract and decode email content
            content = self._extract_content(msg)
            
            if not content:
                self.logger.warning(f"No content extracted from {file_path}")
                return None
            
            # Extract meeting-specific metadata
            meeting_metadata = self._extract_meeting_metadata(content, headers)
            
            # Calculate confidence score
            confidence = self._calculate_confidence(content, headers, meeting_metadata)
            
            # Create structured email object
            parsed_email = ParsedEmail(
                subject=headers.get('subject', ''),
                from_address=headers.get('from', ''),
                to_addresses=self._parse_addresses(headers.get('to', '')),
                date=self._parse_date(headers.get('date')),
                meeting_title=meeting_metadata.get('title', ''),
                meeting_date=meeting_metadata.get('date'),
                participants=meeting_metadata.get('participants', []),
                content=content,
                source_file=file_path,
                confidence_score=confidence,
                raw_headers=headers
            )
            
            self.logger.info(f"Successfully parsed email: {parsed_email.meeting_title}")
            return parsed_email
            
        except Exception as e:
            self.logger.error(f"Failed to parse email {file_path}: {e}")
            raise EmailParsingError(f"Email parsing failed: {e}")
    
    def _extract_headers(self, msg: email.message.Message) -> Dict[str, str]:
        """Extract and decode email headers"""
        headers = {}
        
        for header_name in ['subject', 'from', 'to', 'cc', 'date', 'message-id']:
            header_value = msg.get(header_name, '')
            if header_value:
                # Decode header if it's encoded
                try:
                    decoded_parts = decode_header(header_value)
                    decoded_value = ''
                    for part, encoding in decoded_parts:
                        if isinstance(part, bytes):
                            decoded_value += part.decode(encoding or 'utf-8', errors='ignore')
                        else:
                            decoded_value += part
                    headers[header_name] = decoded_value
                except Exception as e:
                    self.logger.warning(f"Failed to decode header {header_name}: {e}")
                    headers[header_name] = str(header_value)
            else:
                headers[header_name] = ''
        
        return headers
    
    def _extract_content(self, msg: email.message.Message) -> str:
        """
        Extract and decode email content, handling base64 and multipart messages
        
        Args:
            msg: Email message object
            
        Returns:
            Decoded email content as string
        """
        content = ""
        
        try:
            if msg.is_multipart():
                # Handle multipart messages
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        payload = part.get_payload(decode=True)
                        if payload:
                            try:
                                # Try UTF-8 first
                                content += payload.decode('utf-8', errors='ignore')
                            except:
                                # Fallback to latin-1
                                content += payload.decode('latin-1', errors='ignore')
            else:
                # Handle single part messages
                content_type = msg.get_content_type()
                if content_type == "text/plain" or not content_type:
                    payload = msg.get_payload(decode=True)
                    if payload:
                        if isinstance(payload, bytes):
                            content = payload.decode('utf-8', errors='ignore')
                        else:
                            content = str(payload)
            
            # Clean up content
            content = self._clean_content(content)
            
        except Exception as e:
            self.logger.error(f"Failed to extract email content: {e}")
            # Try alternative extraction method
            try:
                raw_payload = msg.get_payload()
                if isinstance(raw_payload, str):
                    content = raw_payload
            except:
                pass
        
        return content
    
    def _clean_content(self, content: str) -> str:
        """Clean and normalize email content"""
        if not content:
            return ""
        
        # Remove CRLF line endings
        content = content.replace('\r\n', '\n').replace('\r', '\n')
        
        # Remove excessive whitespace
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        # Remove common email artifacts
        content = re.sub(r'--[a-f0-9]{20,}.*?Content-Type:', 'Content-Type:', content, flags=re.DOTALL)
        
        return content.strip()
    
    def _extract_meeting_metadata(self, content: str, headers: Dict[str, str]) -> Dict[str, Any]:
        """
        Extract meeting-specific metadata from email content and headers
        
        Args:
            content: Email content
            headers: Email headers
            
        Returns:
            Dictionary with meeting metadata
        """
        metadata = {
            'title': '',
            'date': None,
            'participants': []
        }
        
        # Extract meeting title
        title = self._extract_meeting_title(content, headers)
        if title:
            metadata['title'] = title
        
        # Extract meeting date/time
        meeting_date = self._extract_meeting_date(content, headers)
        if meeting_date:
            metadata['date'] = meeting_date
        
        # Extract participants
        participants = self._extract_participants(content)
        if participants:
            metadata['participants'] = participants
        
        return metadata
    
    def _extract_meeting_title(self, content: str, headers: Dict[str, str]) -> str:
        """Extract meeting title from content or headers"""
        
        # Try content patterns first
        for pattern in self.title_patterns:
            match = pattern.search(content)
            if match:
                return match.group(1).strip()
        
        # Try subject line
        subject = headers.get('subject', '')
        if 'Notes_' in subject:
            # Clean up subject line
            title = re.sub(r'Notes_\s*["\u201c]?(.+?)["\u201d]?', r'\1', subject)
            return title.strip()
        
        return ""
    
    def _extract_meeting_date(self, content: str, headers: Dict[str, str]) -> Optional[datetime]:
        """Extract meeting date from content or headers"""
        
        # Try email date first
        email_date = headers.get('date')
        if email_date:
            parsed_date = self._parse_date(email_date)
            if parsed_date:
                return parsed_date
        
        # Look for date patterns in content
        date_patterns = [
            r'(\d{4}_\d{2}_\d{2})',
            r'(August \d{1,2}, \d{4})',
            r'(\d{1,2}/\d{1,2}/\d{4})',
            r'(\d{4}-\d{2}-\d{2})'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, content)
            if match:
                date_str = match.group(1)
                try:
                    # Parse various date formats
                    if '_' in date_str:
                        return datetime.strptime(date_str, '%Y_%m_%d').replace(tzinfo=timezone.utc)
                    elif '/' in date_str:
                        return datetime.strptime(date_str, '%m/%d/%Y').replace(tzinfo=timezone.utc)
                    elif '-' in date_str:
                        return datetime.strptime(date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
                except ValueError:
                    continue
        
        return None
    
    def _extract_participants(self, content: str) -> List[str]:
        """Extract participant names/emails from content"""
        participants = []
        
        # Look for participant patterns
        for pattern in self.participant_patterns:
            match = pattern.search(content)
            if match:
                participant_text = match.group(1)
                # Split by commas and clean up
                names = [name.strip() for name in participant_text.split(',')]
                participants.extend([name for name in names if name and len(name) > 2])
        
        # Also look for names mentioned in content (people doing actions)
        action_patterns = [
            r'([A-Z][a-z]+\s+[A-Z][a-z]+)\s+(?:will|expressed|suggested|explained)',
            r'including\s+([A-Z][a-z]+\s+[A-Z][a-z]+)',
        ]
        
        for pattern in action_patterns:
            matches = re.findall(pattern, content)
            participants.extend(matches)
        
        # Remove duplicates and return
        return list(set(participants))
    
    def _parse_addresses(self, address_string: str) -> List[str]:
        """Parse email addresses from address string"""
        if not address_string:
            return []
        
        # Simple email extraction
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        emails = re.findall(email_pattern, address_string)
        return emails
    
    def _parse_date(self, date_string: Optional[str]) -> Optional[datetime]:
        """Parse email date string to datetime object"""
        if not date_string:
            return None
        
        try:
            return parsedate_to_datetime(date_string)
        except Exception as e:
            self.logger.warning(f"Failed to parse date '{date_string}': {e}")
            return None
    
    def _calculate_confidence(self, content: str, headers: Dict[str, str], 
                            metadata: Dict[str, Any]) -> float:
        """
        Calculate confidence score for parsed email data
        
        Returns:
            Float between 0.0 and 1.0 indicating parsing confidence
        """
        confidence = 0.0
        
        # Base confidence for successful content extraction
        if content:
            confidence += 0.3
        
        # Bonus for Google Meet/Gemini signatures
        for pattern in self.gemini_patterns:
            if pattern.search(content) or pattern.search(headers.get('subject', '')):
                confidence += 0.2
                break
        
        # Bonus for meeting title extraction
        if metadata.get('title'):
            confidence += 0.2
        
        # Bonus for participant extraction
        if metadata.get('participants'):
            confidence += 0.2
        
        # Bonus for date extraction
        if metadata.get('date'):
            confidence += 0.1
        
        return min(1.0, confidence)
    
    def detect_meeting_notes_emails(self, directory: str) -> List[str]:
        """
        Public method to detect meeting notes emails in a directory
        
        Args:
            directory: Directory to scan
            
        Returns:
            List of file paths that appear to be meeting notes emails
        """
        return self._scan_directory(directory)
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        return self.stats.copy()


# Standalone execution for testing
if __name__ == "__main__":
    import sys
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    collector = EmailCollector()
    
    if len(sys.argv) > 1:
        # Process specific file
        file_path = sys.argv[1]
        if os.path.exists(file_path):
            try:
                parsed_email = collector.parse_eml_file(file_path)
                if parsed_email:
                    print(f"Successfully parsed email:")
                    print(f"  Title: {parsed_email.meeting_title}")
                    print(f"  Date: {parsed_email.meeting_date}")
                    print(f"  Participants: {parsed_email.participants}")
                    print(f"  Confidence: {parsed_email.confidence_score:.2f}")
                    print(f"  Content preview: {parsed_email.content[:200]}...")
                else:
                    print("Failed to parse email")
            except Exception as e:
                print(f"Error parsing email: {e}")
        else:
            print(f"File not found: {file_path}")
    else:
        # Run full collection
        results = collector.collect()
        print(f"Collection results: {results}")