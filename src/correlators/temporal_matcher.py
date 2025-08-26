#!/usr/bin/env python3
"""
Temporal Matcher - Time-based Meeting-Email Correlation
Implements temporal correlation algorithms for matching email notifications with Google Docs

This module provides sophisticated time-based matching to correlate Google Meet email
notifications with their corresponding Google Docs meeting notes based on timestamps.

Key Challenge: Email notifications arrive first, Google Docs are generated later.
Time windows need to account for meeting duration and processing delays.

Architecture:
- TimeWindow: Flexible time range matching with tolerance
- TemporalMatcher: Main correlation engine with confidence scoring
- TimezoneHandler: Robust timezone conversion and normalization
- TemporalSignals: Multiple time-based correlation signals

Usage:
    from src.correlators.temporal_matcher import TemporalMatcher
    matcher = TemporalMatcher()
    match = matcher.find_temporal_match(email_record, doc_candidates)
"""

import re
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

try:
    import pytz
    PYTZ_AVAILABLE = True
except ImportError:
    PYTZ_AVAILABLE = False
    logging.warning("pytz not available, using basic timezone handling")

logger = logging.getLogger(__name__)


class TemporalConfidence(Enum):
    """Confidence levels for temporal matching"""
    EXACT_MATCH = 0.95      # Within 2 minutes
    HIGH_CONFIDENCE = 0.85  # Within 5 minutes  
    MEDIUM_CONFIDENCE = 0.70 # Within 15 minutes
    LOW_CONFIDENCE = 0.50   # Within 30 minutes
    NO_MATCH = 0.0          # Beyond tolerance


@dataclass
class TimeWindow:
    """Flexible time window for matching with tolerance"""
    start_time: datetime
    end_time: datetime
    tolerance_minutes: int = 15
    
    def contains(self, target_time: datetime) -> bool:
        """Check if target time falls within this window (with tolerance)"""
        adjusted_start = self.start_time - timedelta(minutes=self.tolerance_minutes)
        adjusted_end = self.end_time + timedelta(minutes=self.tolerance_minutes)
        return adjusted_start <= target_time <= adjusted_end
    
    def time_difference(self, target_time: datetime) -> timedelta:
        """Calculate minimum time difference to this window"""
        if self.contains(target_time):
            return timedelta(0)
        
        diff_to_start = abs(target_time - self.start_time)
        diff_to_end = abs(target_time - self.end_time)
        return min(diff_to_start, diff_to_end)


@dataclass 
class TemporalMatch:
    """Result of temporal matching with detailed scoring"""
    email_id: str
    doc_id: str
    confidence: float
    time_difference_minutes: float
    match_signals: Dict[str, Any]
    
    def is_valid_match(self, min_confidence: float = 0.5) -> bool:
        """Check if this is a valid match above confidence threshold"""
        return self.confidence >= min_confidence


class TimezoneHandler:
    """Robust timezone handling for temporal correlation"""
    
    def __init__(self):
        self.common_timezones = {
            'PDT': 'US/Pacific',
            'PST': 'US/Pacific', 
            'EDT': 'US/Eastern',
            'EST': 'US/Eastern',
            'CDT': 'US/Central',
            'CST': 'US/Central',
            'MDT': 'US/Mountain',
            'MST': 'US/Mountain'
        }
    
    def normalize_to_utc(self, dt: datetime, timezone_str: Optional[str] = None) -> datetime:
        """Normalize datetime to UTC for comparison"""
        if dt.tzinfo is not None:
            # Already has timezone info
            return dt.astimezone(timezone.utc)
        
        if timezone_str and PYTZ_AVAILABLE:
            # Apply timezone from string
            try:
                tz_name = self.common_timezones.get(timezone_str, timezone_str)
                tz = pytz.timezone(tz_name)
                localized_dt = tz.localize(dt)
                return localized_dt.astimezone(timezone.utc)
            except Exception:
                logger.warning(f"Could not parse timezone: {timezone_str}")
        
        # Assume local timezone or UTC if no info
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        
        return dt
    
    def parse_timestamp_from_filename(self, filename: str) -> Optional[datetime]:
        """Extract timestamp from Google Docs filename format"""
        # Pattern: YYYY_MM_DD HH_MM TZ
        pattern = r'(\d{4}_\d{2}_\d{2})\s+(\d{2}_\d{2})\s+([A-Z]{3})'
        match = re.search(pattern, filename)
        
        if match:
            date_str = match.group(1).replace('_', '-')  # 2025-06-24
            time_str = match.group(2).replace('_', ':')  # 08:46
            tz_str = match.group(3)                      # PDT
            
            try:
                dt_str = f"{date_str} {time_str}"
                dt = datetime.strptime(dt_str, '%Y-%m-%d %H:%M')
                return self.normalize_to_utc(dt, tz_str)
            except ValueError as e:
                logger.warning(f"Could not parse timestamp from filename: {e}")
        
        return None


class TemporalMatcher:
    """Main temporal correlation engine"""
    
    def __init__(self, max_time_diff_hours: int = 24):
        """
        Initialize temporal matcher
        
        Args:
            max_time_diff_hours: Maximum time difference to consider for matching
        """
        self.max_time_diff = timedelta(hours=max_time_diff_hours)
        self.timezone_handler = TimezoneHandler()
        self.logger = logging.getLogger(f"{__name__}.TemporalMatcher")
    
    def extract_email_time(self, email_record: Dict[str, Any]) -> Optional[datetime]:
        """Extract meeting time from email record"""
        # Try multiple fields for meeting time
        time_fields = ['meeting_datetime', 'meeting_time', 'scheduled_time', 'start_time']
        
        for field in time_fields:
            if field in email_record and email_record[field]:
                time_value = email_record[field]
                if isinstance(time_value, datetime):
                    return self.timezone_handler.normalize_to_utc(time_value)
                elif isinstance(time_value, str):
                    try:
                        dt = datetime.fromisoformat(time_value.replace('Z', '+00:00'))
                        return self.timezone_handler.normalize_to_utc(dt)
                    except ValueError:
                        continue
        
        # Fallback to email metadata
        if 'email_metadata' in email_record:
            metadata = email_record['email_metadata']
            if 'date' in metadata:
                try:
                    dt = datetime.fromisoformat(metadata['date'].replace('Z', '+00:00'))
                    return self.timezone_handler.normalize_to_utc(dt)
                except (ValueError, AttributeError):
                    pass
        
        return None
    
    def extract_doc_time(self, doc_record: Dict[str, Any]) -> Optional[datetime]:
        """Extract meeting time from Google Doc record"""
        # Try filename timestamp first (most reliable)
        if 'filename' in doc_record:
            filename_time = self.timezone_handler.parse_timestamp_from_filename(doc_record['filename'])
            if filename_time:
                return filename_time
        
        # Try meeting metadata
        if 'meeting_metadata' in doc_record:
            metadata = doc_record['meeting_metadata']
            
            # Combine date and time if available
            if 'date' in metadata and 'time' in metadata:
                try:
                    date_obj = metadata['date']
                    time_str = metadata['time']
                    timezone_str = metadata.get('timezone')
                    
                    if hasattr(date_obj, 'strftime'):
                        date_str = date_obj.strftime('%Y-%m-%d')
                    else:
                        date_str = str(date_obj)
                    
                    dt_str = f"{date_str} {time_str}"
                    dt = datetime.strptime(dt_str, '%Y-%m-%d %H:%M')
                    return self.timezone_handler.normalize_to_utc(dt, timezone_str)
                    
                except (ValueError, AttributeError) as e:
                    self.logger.debug(f"Could not parse doc metadata time: {e}")
            
            # Just date available
            elif 'date' in metadata:
                try:
                    date_obj = metadata['date']
                    if hasattr(date_obj, 'strftime'):
                        # Use start of day for date-only matches
                        dt = datetime.combine(date_obj, datetime.min.time())
                        return self.timezone_handler.normalize_to_utc(dt)
                except (ValueError, AttributeError):
                    pass
        
        return None
    
    def calculate_temporal_confidence(self, time_diff: timedelta) -> float:
        """Calculate confidence score based on time difference"""
        diff_minutes = abs(time_diff.total_seconds()) / 60
        
        if diff_minutes <= 2:
            return TemporalConfidence.EXACT_MATCH.value
        elif diff_minutes <= 5:
            return TemporalConfidence.HIGH_CONFIDENCE.value
        elif diff_minutes <= 15:
            return TemporalConfidence.MEDIUM_CONFIDENCE.value
        elif diff_minutes <= 30:
            return TemporalConfidence.LOW_CONFIDENCE.value
        else:
            return TemporalConfidence.NO_MATCH.value
    
    def find_temporal_match(self, email_record: Dict[str, Any], 
                           doc_candidates: List[Dict[str, Any]]) -> Optional[TemporalMatch]:
        """
        Find best temporal match between email and document candidates
        
        Args:
            email_record: Email record with timing information
            doc_candidates: List of Google Doc records to match against
            
        Returns:
            Best temporal match or None if no suitable match found
        """
        email_time = self.extract_email_time(email_record)
        if not email_time:
            self.logger.debug(f"No email time found for: {email_record.get('title', 'unknown')}")
            return None
        
        best_match = None
        best_confidence = 0.0
        
        for doc_record in doc_candidates:
            doc_time = self.extract_doc_time(doc_record)
            if not doc_time:
                continue
            
            time_diff = doc_time - email_time
            
            # Skip if time difference is too large
            if abs(time_diff) > self.max_time_diff:
                continue
            
            confidence = self.calculate_temporal_confidence(time_diff)
            
            if confidence > best_confidence:
                match_signals = {
                    'email_time': email_time.isoformat(),
                    'doc_time': doc_time.isoformat(), 
                    'time_difference': time_diff.total_seconds(),
                    'time_diff_minutes': time_diff.total_seconds() / 60,
                    'email_time_source': self._get_email_time_source(email_record),
                    'doc_time_source': self._get_doc_time_source(doc_record)
                }
                
                best_match = TemporalMatch(
                    email_id=email_record.get('id', 'unknown'),
                    doc_id=doc_record.get('id', 'unknown'),
                    confidence=confidence,
                    time_difference_minutes=abs(time_diff.total_seconds()) / 60,
                    match_signals=match_signals
                )
                best_confidence = confidence
        
        return best_match if best_match and best_match.is_valid_match() else None
    
    def find_all_temporal_matches(self, email_records: List[Dict[str, Any]], 
                                doc_records: List[Dict[str, Any]]) -> List[TemporalMatch]:
        """
        Find all valid temporal matches between email and document records
        
        Args:
            email_records: List of email records
            doc_records: List of Google Doc records
            
        Returns:
            List of all valid temporal matches sorted by confidence
        """
        matches = []
        
        for email_record in email_records:
            match = self.find_temporal_match(email_record, doc_records)
            if match:
                matches.append(match)
        
        # Sort by confidence (highest first)
        matches.sort(key=lambda x: x.confidence, reverse=True)
        return matches
    
    def _get_email_time_source(self, email_record: Dict[str, Any]) -> str:
        """Get description of where email time was extracted from"""
        time_fields = ['meeting_datetime', 'meeting_time', 'scheduled_time', 'start_time']
        for field in time_fields:
            if field in email_record and email_record[field]:
                return field
        
        if 'email_metadata' in email_record and 'date' in email_record['email_metadata']:
            return 'email_metadata.date'
        
        return 'unknown'
    
    def _get_doc_time_source(self, doc_record: Dict[str, Any]) -> str:
        """Get description of where doc time was extracted from"""
        if 'filename' in doc_record:
            filename = doc_record['filename']
            if re.search(r'\d{4}_\d{2}_\d{2}\s+\d{2}_\d{2}\s+[A-Z]{3}', filename):
                return 'filename_timestamp'
        
        if 'meeting_metadata' in doc_record:
            metadata = doc_record['meeting_metadata']
            if 'date' in metadata and 'time' in metadata:
                return 'meeting_metadata.date_time'
            elif 'date' in metadata:
                return 'meeting_metadata.date'
        
        return 'unknown'


# Example usage and testing
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.DEBUG)
    
    # Example email and doc records
    email_record = {
        'id': 'email_001',
        'title': 'Weekly Team Meeting',
        'meeting_datetime': datetime(2025, 6, 24, 8, 46, tzinfo=timezone.utc)
    }
    
    doc_candidates = [
        {
            'id': 'doc_001',
            'title': 'Team Meeting Notes',
            'filename': 'Weekly Team Meeting - 2025_06_24 08_48 PDT - Notes by Gemini.docx',
            'meeting_metadata': {
                'date': datetime(2025, 6, 24).date(),
                'time': '08:48',
                'timezone': 'PDT'
            }
        },
        {
            'id': 'doc_002', 
            'title': 'Other Meeting',
            'filename': 'Other Meeting - 2025_06_24 10_00 PDT - Notes by Gemini.docx'
        }
    ]
    
    # Test temporal matching
    matcher = TemporalMatcher()
    match = matcher.find_temporal_match(email_record, doc_candidates)
    
    if match:
        print(f"Found temporal match!")
        print(f"  Confidence: {match.confidence:.2f}")
        print(f"  Time difference: {match.time_difference_minutes:.1f} minutes") 
        print(f"  Match signals: {match.match_signals}")
    else:
        print("No temporal match found")