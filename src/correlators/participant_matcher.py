#!/usr/bin/env python3
"""
Participant Matcher - Name/Email-based Meeting-Email Correlation  
Implements participant-based correlation algorithms for matching meeting attendees

This module provides sophisticated participant matching to correlate Google Meet email
notifications with their corresponding Google Docs meeting notes based on attendee overlap.

Key Challenge: Email has formal email addresses, Google Docs have informal first names.
Need fuzzy matching across different name formats and representations.

Architecture:
- NameNormalizer: Standardizes names across different formats
- ParticipantMatcher: Main correlation engine with overlap scoring
- EmailNameExtractor: Extracts names from email addresses
- NameSimilarity: Fuzzy name matching with confidence scoring

Usage:
    from src.correlators.participant_matcher import ParticipantMatcher
    matcher = ParticipantMatcher()
    match = matcher.find_participant_match(email_record, doc_candidates)
"""

import re
import logging
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass
from enum import Enum
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


class ParticipantConfidence(Enum):
    """Confidence levels for participant matching"""
    PERFECT_MATCH = 0.95       # 100% participant overlap
    HIGH_CONFIDENCE = 0.85     # 80-99% overlap
    MEDIUM_CONFIDENCE = 0.70   # 60-79% overlap  
    LOW_CONFIDENCE = 0.50      # 40-59% overlap
    NO_MATCH = 0.0             # <40% overlap


@dataclass
class ParticipantMatch:
    """Result of participant matching with detailed scoring"""
    email_id: str
    doc_id: str
    confidence: float
    overlap_percentage: float
    matched_participants: List[Dict[str, str]]
    email_only_participants: List[str]
    doc_only_participants: List[str]
    match_signals: Dict[str, Any]
    
    def is_valid_match(self, min_confidence: float = 0.5) -> bool:
        """Check if this is a valid match above confidence threshold"""
        return self.confidence >= min_confidence


class NameNormalizer:
    """Standardizes names across different formats for comparison"""
    
    def __init__(self):
        self.common_name_variations = {
            'dave': 'david',
            'mike': 'michael', 
            'mike': 'michael',
            'jim': 'james',
            'bob': 'robert',
            'bill': 'william',
            'tom': 'thomas',
            'chris': 'christopher',
            'steve': 'stephen',
            'rob': 'robert',
            'dan': 'daniel',
            'matt': 'matthew',
            'joe': 'joseph',
            'ben': 'benjamin'
        }
        
        # Common email domain patterns
        self.company_domains = [
            'company.com', 'corp.com', 'org', 'startup.com',
            'gmail.com', 'outlook.com', 'yahoo.com'
        ]
    
    def extract_name_from_email(self, email: str) -> Optional[str]:
        """Extract name from email address"""
        if '@' not in email:
            return None
        
        local_part = email.split('@')[0]
        
        # Handle common email formats
        if '.' in local_part:
            # firstname.lastname@domain.com
            parts = local_part.split('.')
            if len(parts) == 2:
                first, last = parts
                return f"{first.title()} {last.title()}"
            else:
                # Take first two parts
                return f"{parts[0].title()} {parts[1].title()}"
        
        elif '_' in local_part:
            # firstname_lastname@domain.com
            parts = local_part.split('_')
            if len(parts) >= 2:
                return f"{parts[0].title()} {parts[1].title()}"
        
        elif any(char.isdigit() for char in local_part):
            # firstname.lastname123@domain.com
            clean_name = re.sub(r'\d+', '', local_part)
            if '.' in clean_name:
                parts = clean_name.split('.')
                if len(parts) >= 2:
                    return f"{parts[0].title()} {parts[1].title()}"
        
        # Fallback: capitalize the local part
        return local_part.replace('.', ' ').replace('_', ' ').title()
    
    def normalize_name(self, name: str) -> str:
        """Normalize name for consistent comparison"""
        if not name:
            return ""
        
        # Clean and normalize
        name = name.strip().lower()
        name = re.sub(r'[^\w\s]', '', name)  # Remove punctuation
        name = re.sub(r'\s+', ' ', name)     # Normalize whitespace
        
        # Handle common variations
        words = name.split()
        normalized_words = []
        
        for word in words:
            if word in self.common_name_variations:
                normalized_words.append(self.common_name_variations[word])
            else:
                normalized_words.append(word)
        
        return ' '.join(normalized_words)
    
    def extract_first_name(self, full_name: str) -> str:
        """Extract just the first name for comparison"""
        normalized = self.normalize_name(full_name)
        if not normalized:
            return ""
        
        return normalized.split()[0]
    
    def extract_last_name(self, full_name: str) -> str:
        """Extract just the last name for comparison"""
        normalized = self.normalize_name(full_name)
        if not normalized:
            return ""
        
        parts = normalized.split()
        return parts[-1] if len(parts) > 1 else ""


class NameSimilarity:
    """Fuzzy name matching with confidence scoring"""
    
    def __init__(self):
        self.normalizer = NameNormalizer()
    
    def calculate_similarity(self, name1: str, name2: str) -> float:
        """Calculate similarity score between two names (0.0-1.0)"""
        if not name1 or not name2:
            return 0.0
        
        # Normalize both names
        norm1 = self.normalizer.normalize_name(name1)
        norm2 = self.normalizer.normalize_name(name2)
        
        if norm1 == norm2:
            return 1.0
        
        # Try different matching strategies
        scores = []
        
        # 1. Direct string similarity
        scores.append(SequenceMatcher(None, norm1, norm2).ratio())
        
        # 2. First name matching
        first1 = self.normalizer.extract_first_name(name1)
        first2 = self.normalizer.extract_first_name(name2)
        if first1 and first2:
            scores.append(SequenceMatcher(None, first1, first2).ratio())
        
        # 3. Last name matching (if available)
        last1 = self.normalizer.extract_last_name(name1)
        last2 = self.normalizer.extract_last_name(name2)
        if last1 and last2:
            scores.append(SequenceMatcher(None, last1, last2).ratio())
        
        # 4. Partial matching (any word in name1 matches any word in name2)
        words1 = set(norm1.split())
        words2 = set(norm2.split())
        if words1 and words2:
            intersection = words1.intersection(words2)
            union = words1.union(words2)
            scores.append(len(intersection) / len(union))
        
        # Return the maximum score across strategies
        return max(scores) if scores else 0.0
    
    def find_best_name_match(self, target_name: str, candidate_names: List[str], 
                           min_similarity: float = 0.6) -> Optional[Tuple[str, float]]:
        """Find best matching name from candidates"""
        best_match = None
        best_score = 0.0
        
        for candidate in candidate_names:
            score = self.calculate_similarity(target_name, candidate)
            if score >= min_similarity and score > best_score:
                best_match = candidate
                best_score = score
        
        return (best_match, best_score) if best_match else None


class ParticipantMatcher:
    """Main participant correlation engine"""
    
    def __init__(self, min_overlap_threshold: float = 0.4):
        """
        Initialize participant matcher
        
        Args:
            min_overlap_threshold: Minimum participant overlap to consider valid match
        """
        self.min_overlap_threshold = min_overlap_threshold
        self.name_normalizer = NameNormalizer()
        self.name_similarity = NameSimilarity()
        self.logger = logging.getLogger(f"{__name__}.ParticipantMatcher")
    
    def extract_email_participants(self, email_record: Dict[str, Any]) -> List[str]:
        """Extract participant names from email record"""
        participants = []
        
        # Try different fields for participants
        participant_fields = ['participants', 'attendees', 'invitees', 'recipients']
        
        for field in participant_fields:
            if field in email_record and email_record[field]:
                field_participants = email_record[field]
                if isinstance(field_participants, list):
                    participants.extend(field_participants)
                elif isinstance(field_participants, str):
                    # Split comma-separated participants
                    participants.extend([p.strip() for p in field_participants.split(',')])
        
        # Extract names from email addresses
        extracted_names = []
        for participant in participants:
            if '@' in participant:
                # It's an email address
                name = self.name_normalizer.extract_name_from_email(participant)
                if name:
                    extracted_names.append(name)
                else:
                    extracted_names.append(participant)  # Keep original if can't extract
            else:
                # Already a name
                extracted_names.append(participant)
        
        # Normalize and deduplicate
        normalized_names = []
        seen = set()
        for name in extracted_names:
            normalized = self.name_normalizer.normalize_name(name)
            if normalized and normalized not in seen:
                normalized_names.append(name)  # Keep original format
                seen.add(normalized)
        
        return normalized_names
    
    def extract_doc_participants(self, doc_record: Dict[str, Any]) -> List[str]:
        """Extract participant names from Google Doc record"""
        participants = []
        
        # Check meeting metadata
        if 'meeting_metadata' in doc_record:
            metadata = doc_record['meeting_metadata']
            if 'participants' in metadata and metadata['participants']:
                participants.extend(metadata['participants'])
        
        # Check filename for participant patterns (Name1 _ Name2)
        if 'filename' in doc_record:
            filename = doc_record['filename']
            # Look for "Name1 _ Name2" pattern at start of filename
            match = re.match(r'^([A-Za-z]+)\s*_\s*([A-Za-z]+)', filename)
            if match:
                name1, name2 = match.groups()
                participants.extend([name1.strip(), name2.strip()])
        
        # Deduplicate and normalize
        normalized_names = []
        seen = set()
        for name in participants:
            normalized = self.name_normalizer.normalize_name(name)
            if normalized and normalized not in seen:
                normalized_names.append(name)  # Keep original format
                seen.add(normalized)
        
        return normalized_names
    
    def calculate_participant_overlap(self, email_participants: List[str], 
                                    doc_participants: List[str]) -> Tuple[float, List[Dict[str, str]], List[str], List[str]]:
        """
        Calculate overlap percentage between participant lists
        
        Returns:
            Tuple of (overlap_percentage, matched_pairs, email_only, doc_only)
        """
        if not email_participants and not doc_participants:
            return 0.0, [], [], []
        
        if not email_participants or not doc_participants:
            return 0.0, [], email_participants, doc_participants
        
        matched_pairs = []
        email_matched = set()
        doc_matched = set()
        
        # Find matches using fuzzy name matching
        for i, email_participant in enumerate(email_participants):
            best_match = self.name_similarity.find_best_name_match(
                email_participant, doc_participants, min_similarity=0.6
            )
            
            if best_match:
                doc_participant, similarity = best_match
                doc_index = doc_participants.index(doc_participant)
                
                # Avoid duplicate matches
                if i not in email_matched and doc_index not in doc_matched:
                    matched_pairs.append({
                        'email_participant': email_participant,
                        'doc_participant': doc_participant, 
                        'similarity': similarity
                    })
                    email_matched.add(i)
                    doc_matched.add(doc_index)
        
        # Calculate overlap percentage
        total_unique_participants = len(set(email_participants + doc_participants))
        if total_unique_participants == 0:
            overlap_percentage = 0.0
        else:
            overlap_percentage = (len(matched_pairs) * 2) / total_unique_participants
        
        # Get unmatched participants
        email_only = [p for i, p in enumerate(email_participants) if i not in email_matched]
        doc_only = [p for i, p in enumerate(doc_participants) if i not in doc_matched]
        
        return overlap_percentage, matched_pairs, email_only, doc_only
    
    def calculate_participant_confidence(self, overlap_percentage: float) -> float:
        """Calculate confidence score based on participant overlap"""
        if overlap_percentage >= 1.0:
            return ParticipantConfidence.PERFECT_MATCH.value
        elif overlap_percentage >= 0.8:
            return ParticipantConfidence.HIGH_CONFIDENCE.value
        elif overlap_percentage >= 0.6:
            return ParticipantConfidence.MEDIUM_CONFIDENCE.value
        elif overlap_percentage >= 0.4:
            return ParticipantConfidence.LOW_CONFIDENCE.value
        else:
            return ParticipantConfidence.NO_MATCH.value
    
    def find_participant_match(self, email_record: Dict[str, Any], 
                             doc_candidates: List[Dict[str, Any]]) -> Optional[ParticipantMatch]:
        """
        Find best participant match between email and document candidates
        
        Args:
            email_record: Email record with participant information
            doc_candidates: List of Google Doc records to match against
            
        Returns:
            Best participant match or None if no suitable match found
        """
        email_participants = self.extract_email_participants(email_record)
        if not email_participants:
            self.logger.debug(f"No email participants found for: {email_record.get('title', 'unknown')}")
            return None
        
        best_match = None
        best_confidence = 0.0
        
        for doc_record in doc_candidates:
            doc_participants = self.extract_doc_participants(doc_record)
            if not doc_participants:
                continue
            
            overlap_percentage, matched_pairs, email_only, doc_only = self.calculate_participant_overlap(
                email_participants, doc_participants
            )
            
            confidence = self.calculate_participant_confidence(overlap_percentage)
            
            if confidence > best_confidence:
                match_signals = {
                    'email_participants': email_participants,
                    'doc_participants': doc_participants,
                    'overlap_percentage': overlap_percentage,
                    'matched_count': len(matched_pairs),
                    'email_participant_count': len(email_participants),
                    'doc_participant_count': len(doc_participants)
                }
                
                best_match = ParticipantMatch(
                    email_id=email_record.get('id', 'unknown'),
                    doc_id=doc_record.get('id', 'unknown'), 
                    confidence=confidence,
                    overlap_percentage=overlap_percentage,
                    matched_participants=matched_pairs,
                    email_only_participants=email_only,
                    doc_only_participants=doc_only,
                    match_signals=match_signals
                )
                best_confidence = confidence
        
        return best_match if best_match and best_match.is_valid_match() else None
    
    def find_all_participant_matches(self, email_records: List[Dict[str, Any]], 
                                   doc_records: List[Dict[str, Any]]) -> List[ParticipantMatch]:
        """
        Find all valid participant matches between email and document records
        
        Args:
            email_records: List of email records
            doc_records: List of Google Doc records
            
        Returns:
            List of all valid participant matches sorted by confidence
        """
        matches = []
        
        for email_record in email_records:
            match = self.find_participant_match(email_record, doc_records)
            if match:
                matches.append(match)
        
        # Sort by confidence (highest first)
        matches.sort(key=lambda x: x.confidence, reverse=True)
        return matches


# Example usage and testing
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.DEBUG)
    
    # Example email and doc records
    email_record = {
        'id': 'email_001',
        'title': 'Weekly Team Meeting',
        'participants': ['david.campos@company.com', 'charlie.gunn@company.com', 'sarah.johnson@company.com']
    }
    
    doc_candidates = [
        {
            'id': 'doc_001',
            'title': 'Team Meeting Notes',
            'filename': 'David _ Charlie - weekly sync - Notes by Gemini.docx',
            'meeting_metadata': {
                'participants': ['David', 'Charlie']
            }
        },
        {
            'id': 'doc_002',
            'title': 'Other Meeting',
            'filename': 'Other Meeting - Notes by Gemini.docx',
            'meeting_metadata': {
                'participants': ['Alice', 'Bob']
            }
        }
    ]
    
    # Test participant matching
    matcher = ParticipantMatcher()
    match = matcher.find_participant_match(email_record, doc_candidates)
    
    if match:
        print(f"Found participant match!")
        print(f"  Confidence: {match.confidence:.2f}")
        print(f"  Overlap: {match.overlap_percentage:.1%}")
        print(f"  Matched participants: {match.matched_participants}")
        print(f"  Email only: {match.email_only_participants}")
        print(f"  Doc only: {match.doc_only_participants}")
    else:
        print("No participant match found")