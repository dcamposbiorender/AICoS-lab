#!/usr/bin/env python3
"""
Content Matcher - Fuzzy Content-based Meeting-Email Correlation
Implements content-based correlation algorithms for matching meeting titles and subjects

This module provides sophisticated content matching to correlate Google Meet email
notifications with their corresponding Google Docs meeting notes based on title/content similarity.

Key Challenge: Email subjects are formal ("Meeting: Weekly Team Sync"), 
Google Doc titles are informal ("Team Sync Notes"). Need semantic understanding.

Architecture:
- TextNormalizer: Standardizes text across different formats
- ContentMatcher: Main correlation engine with semantic similarity
- KeywordExtractor: Extracts meaningful terms for comparison
- SimilarityScorer: Multiple similarity algorithms with confidence scoring

Usage:
    from src.correlators.content_matcher import ContentMatcher
    matcher = ContentMatcher()
    match = matcher.find_content_match(email_record, doc_candidates)
"""

import re
import logging
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass
from enum import Enum
from difflib import SequenceMatcher
from collections import Counter

logger = logging.getLogger(__name__)


class ContentConfidence(Enum):
    """Confidence levels for content matching"""
    PERFECT_MATCH = 0.95       # >95% similarity
    HIGH_CONFIDENCE = 0.85     # 80-95% similarity
    MEDIUM_CONFIDENCE = 0.70   # 60-79% similarity
    LOW_CONFIDENCE = 0.50      # 40-59% similarity
    NO_MATCH = 0.0             # <40% similarity


@dataclass
class ContentMatch:
    """Result of content matching with detailed scoring"""
    email_id: str
    doc_id: str
    confidence: float
    title_similarity: float
    keyword_overlap: float
    semantic_similarity: float
    matched_keywords: List[str]
    email_title: str
    doc_title: str
    match_signals: Dict[str, Any]
    
    def is_valid_match(self, min_confidence: float = 0.5) -> bool:
        """Check if this is a valid match above confidence threshold"""
        return self.confidence >= min_confidence


class TextNormalizer:
    """Standardizes text across different formats for comparison"""
    
    def __init__(self):
        # Common stopwords to remove from comparison
        self.stopwords = {
            'meeting', 'call', 'session', 'sync', 'standup', 'review', 
            'notes', 'by', 'gemini', 'with', 'and', 'or', 'the', 'a', 'an',
            'for', 'of', 'in', 'on', 'at', 'to', 'from', 'up', 'out', 'about'
        }
        
        # Email-specific prefixes to remove
        self.email_prefixes = {
            'meeting:', 'call:', 'session:', 'sync:', 'standup:', 
            're:', 'fwd:', 'fw:', 'subject:', 'notes:'
        }
        
        # Meeting type keywords that indicate meeting purpose
        self.meeting_keywords = {
            'standup', 'daily', 'weekly', 'monthly', 'quarterly',
            'planning', 'retrospective', 'retro', 'review', 'sync',
            'kickoff', 'demo', 'presentation', 'training', 'onboarding',
            'interview', 'intro', 'introduction', 'check-in', 'checkin',
            'all-hands', 'townhall', 'team', 'group', 'staff', 'leadership'
        }
        
        # Common abbreviations and their expansions
        self.abbreviations = {
            'w/': 'with',
            'w': 'with',
            '&': 'and',
            '+': 'and', 
            'q1': 'quarterly',
            'q2': 'quarterly',
            'q3': 'quarterly', 
            'q4': 'quarterly',
            'prep': 'preparation',
            'onsite': 'onsite',
            'offsite': 'offsite'
        }
    
    def normalize_text(self, text: str) -> str:
        """Normalize text for consistent comparison"""
        if not text:
            return ""
        
        # Convert to lowercase
        normalized = text.lower().strip()
        
        # Remove email prefixes
        for prefix in self.email_prefixes:
            if normalized.startswith(prefix):
                normalized = normalized[len(prefix):].strip()
        
        # Expand abbreviations
        for abbrev, expansion in self.abbreviations.items():
            normalized = normalized.replace(abbrev, expansion)
        
        # Remove punctuation except underscores and hyphens
        normalized = re.sub(r'[^\w\s\-_]', ' ', normalized)
        
        # Replace underscores and hyphens with spaces
        normalized = normalized.replace('_', ' ').replace('-', ' ')
        
        # Normalize whitespace
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        return normalized
    
    def extract_keywords(self, text: str, min_length: int = 2) -> List[str]:
        """Extract meaningful keywords from text"""
        normalized = self.normalize_text(text)
        words = normalized.split()
        
        # Filter out stopwords and short words
        keywords = []
        for word in words:
            if (len(word) >= min_length and 
                word not in self.stopwords and 
                not word.isdigit()):
                keywords.append(word)
        
        return keywords
    
    def extract_meeting_type(self, text: str) -> Optional[str]:
        """Extract meeting type/purpose from text"""
        normalized = self.normalize_text(text)
        words = set(normalized.split())
        
        # Find intersection with meeting keywords
        meeting_types = words.intersection(self.meeting_keywords)
        
        # Return the most specific meeting type found
        priority_order = ['standup', 'daily', 'weekly', 'monthly', 'quarterly',
                         'retrospective', 'retro', 'planning', 'review']
        
        for meeting_type in priority_order:
            if meeting_type in meeting_types:
                return meeting_type
        
        # Return any meeting type found
        return list(meeting_types)[0] if meeting_types else None


class KeywordExtractor:
    """Extracts meaningful terms for comparison"""
    
    def __init__(self):
        self.text_normalizer = TextNormalizer()
    
    def extract_weighted_keywords(self, text: str) -> Dict[str, float]:
        """Extract keywords with weights based on importance"""
        keywords = self.text_normalizer.extract_keywords(text)
        
        # Calculate weights
        keyword_weights = {}
        keyword_counts = Counter(keywords)
        total_keywords = len(keywords)
        
        for keyword, count in keyword_counts.items():
            # Base weight: term frequency
            base_weight = count / total_keywords
            
            # Bonus for meeting-specific terms
            if keyword in self.text_normalizer.meeting_keywords:
                base_weight *= 2.0
            
            # Bonus for longer, more specific terms
            if len(keyword) > 6:
                base_weight *= 1.5
            
            keyword_weights[keyword] = base_weight
        
        return keyword_weights
    
    def calculate_keyword_overlap(self, text1: str, text2: str) -> Tuple[float, List[str]]:
        """Calculate keyword overlap between two texts"""
        keywords1 = set(self.text_normalizer.extract_keywords(text1))
        keywords2 = set(self.text_normalizer.extract_keywords(text2))
        
        if not keywords1 and not keywords2:
            return 0.0, []
        
        if not keywords1 or not keywords2:
            return 0.0, []
        
        # Calculate Jaccard similarity
        intersection = keywords1.intersection(keywords2)
        union = keywords1.union(keywords2)
        
        overlap_score = len(intersection) / len(union) if union else 0.0
        matched_keywords = list(intersection)
        
        return overlap_score, matched_keywords


class SimilarityScorer:
    """Multiple similarity algorithms with confidence scoring"""
    
    def __init__(self):
        self.text_normalizer = TextNormalizer()
        self.keyword_extractor = KeywordExtractor()
    
    def string_similarity(self, text1: str, text2: str) -> float:
        """Basic string similarity using sequence matching"""
        if not text1 or not text2:
            return 0.0
        
        norm1 = self.text_normalizer.normalize_text(text1)
        norm2 = self.text_normalizer.normalize_text(text2)
        
        return SequenceMatcher(None, norm1, norm2).ratio()
    
    def keyword_similarity(self, text1: str, text2: str) -> Tuple[float, List[str]]:
        """Keyword-based similarity with matched terms"""
        return self.keyword_extractor.calculate_keyword_overlap(text1, text2)
    
    def weighted_keyword_similarity(self, text1: str, text2: str) -> float:
        """Weighted keyword similarity considering term importance"""
        weights1 = self.keyword_extractor.extract_weighted_keywords(text1)
        weights2 = self.keyword_extractor.extract_weighted_keywords(text2)
        
        if not weights1 or not weights2:
            return 0.0
        
        # Calculate weighted overlap
        common_keywords = set(weights1.keys()).intersection(set(weights2.keys()))
        
        if not common_keywords:
            return 0.0
        
        # Sum weights of common keywords
        common_weight = sum(min(weights1[k], weights2[k]) for k in common_keywords)
        
        # Normalize by total weights
        total_weight = sum(weights1.values()) + sum(weights2.values())
        
        return (common_weight * 2) / total_weight if total_weight > 0 else 0.0
    
    def semantic_similarity(self, text1: str, text2: str) -> float:
        """Semantic similarity considering meeting context"""
        # Extract meeting types
        meeting_type1 = self.text_normalizer.extract_meeting_type(text1)
        meeting_type2 = self.text_normalizer.extract_meeting_type(text2)
        
        meeting_type_bonus = 0.2 if meeting_type1 and meeting_type1 == meeting_type2 else 0.0
        
        # Base similarity scores
        string_sim = self.string_similarity(text1, text2)
        keyword_sim, _ = self.keyword_similarity(text1, text2)
        weighted_sim = self.weighted_keyword_similarity(text1, text2)
        
        # Combine scores with weights
        semantic_score = (
            0.3 * string_sim +
            0.4 * keyword_sim +
            0.3 * weighted_sim +
            meeting_type_bonus
        )
        
        return min(semantic_score, 1.0)  # Cap at 1.0


class ContentMatcher:
    """Main content correlation engine"""
    
    def __init__(self, min_similarity_threshold: float = 0.4):
        """
        Initialize content matcher
        
        Args:
            min_similarity_threshold: Minimum content similarity to consider valid match
        """
        self.min_similarity_threshold = min_similarity_threshold
        self.text_normalizer = TextNormalizer()
        self.similarity_scorer = SimilarityScorer()
        self.logger = logging.getLogger(f"{__name__}.ContentMatcher")
    
    def extract_email_title(self, email_record: Dict[str, Any]) -> str:
        """Extract title/subject from email record"""
        # Try different fields for email subject/title
        title_fields = ['title', 'subject', 'meeting_title', 'meeting_subject']
        
        for field in title_fields:
            if field in email_record and email_record[field]:
                return str(email_record[field]).strip()
        
        # Fallback to email metadata
        if 'email_metadata' in email_record:
            metadata = email_record['email_metadata']
            if 'subject' in metadata:
                return str(metadata['subject']).strip()
        
        return ""
    
    def extract_doc_title(self, doc_record: Dict[str, Any]) -> str:
        """Extract title from Google Doc record"""
        # Primary: document title
        if 'title' in doc_record and doc_record['title']:
            return str(doc_record['title']).strip()
        
        # Secondary: filename (cleaned)
        if 'filename' in doc_record and doc_record['filename']:
            filename = doc_record['filename']
            # Remove common filename suffixes
            title = re.sub(r'\s*-\s*\d{4}_\d{2}_\d{2}.*$', '', filename)
            title = re.sub(r'\.docx$', '', title, flags=re.IGNORECASE)
            title = re.sub(r'\s*-\s*Notes by Gemini.*$', '', title, flags=re.IGNORECASE)
            return title.strip()
        
        return ""
    
    def calculate_content_confidence(self, title_similarity: float, keyword_overlap: float, 
                                   semantic_similarity: float) -> float:
        """Calculate overall confidence score from component similarities"""
        # Weighted combination of similarity scores
        combined_score = (
            0.4 * title_similarity +
            0.3 * keyword_overlap +
            0.3 * semantic_similarity
        )
        
        if combined_score >= 0.95:
            return ContentConfidence.PERFECT_MATCH.value
        elif combined_score >= 0.8:
            return ContentConfidence.HIGH_CONFIDENCE.value
        elif combined_score >= 0.6:
            return ContentConfidence.MEDIUM_CONFIDENCE.value
        elif combined_score >= 0.4:
            return ContentConfidence.LOW_CONFIDENCE.value
        else:
            return ContentConfidence.NO_MATCH.value
    
    def find_content_match(self, email_record: Dict[str, Any], 
                          doc_candidates: List[Dict[str, Any]]) -> Optional[ContentMatch]:
        """
        Find best content match between email and document candidates
        
        Args:
            email_record: Email record with title/subject information
            doc_candidates: List of Google Doc records to match against
            
        Returns:
            Best content match or None if no suitable match found
        """
        email_title = self.extract_email_title(email_record)
        if not email_title:
            self.logger.debug(f"No email title found for: {email_record.get('id', 'unknown')}")
            return None
        
        best_match = None
        best_confidence = 0.0
        
        for doc_record in doc_candidates:
            doc_title = self.extract_doc_title(doc_record)
            if not doc_title:
                continue
            
            # Calculate various similarity scores
            title_similarity = self.similarity_scorer.string_similarity(email_title, doc_title)
            keyword_overlap, matched_keywords = self.similarity_scorer.keyword_similarity(email_title, doc_title)
            semantic_similarity = self.similarity_scorer.semantic_similarity(email_title, doc_title)
            
            confidence = self.calculate_content_confidence(
                title_similarity, keyword_overlap, semantic_similarity
            )
            
            if confidence > best_confidence and confidence >= self.min_similarity_threshold:
                match_signals = {
                    'email_title': email_title,
                    'doc_title': doc_title,
                    'email_title_normalized': self.text_normalizer.normalize_text(email_title),
                    'doc_title_normalized': self.text_normalizer.normalize_text(doc_title),
                    'title_similarity': title_similarity,
                    'keyword_overlap': keyword_overlap,
                    'semantic_similarity': semantic_similarity,
                    'matched_keywords': matched_keywords,
                    'email_meeting_type': self.text_normalizer.extract_meeting_type(email_title),
                    'doc_meeting_type': self.text_normalizer.extract_meeting_type(doc_title)
                }
                
                best_match = ContentMatch(
                    email_id=email_record.get('id', 'unknown'),
                    doc_id=doc_record.get('id', 'unknown'),
                    confidence=confidence,
                    title_similarity=title_similarity,
                    keyword_overlap=keyword_overlap,
                    semantic_similarity=semantic_similarity,
                    matched_keywords=matched_keywords,
                    email_title=email_title,
                    doc_title=doc_title,
                    match_signals=match_signals
                )
                best_confidence = confidence
        
        return best_match if best_match and best_match.is_valid_match() else None
    
    def find_all_content_matches(self, email_records: List[Dict[str, Any]], 
                               doc_records: List[Dict[str, Any]]) -> List[ContentMatch]:
        """
        Find all valid content matches between email and document records
        
        Args:
            email_records: List of email records
            doc_records: List of Google Doc records
            
        Returns:
            List of all valid content matches sorted by confidence
        """
        matches = []
        
        for email_record in email_records:
            match = self.find_content_match(email_record, doc_records)
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
        'title': 'Meeting: Weekly Team Sync & Sprint Planning',
        'subject': 'Weekly Team Sync & Sprint Planning Session'
    }
    
    doc_candidates = [
        {
            'id': 'doc_001',
            'title': 'Team Sync Weekly Planning Notes',
            'filename': 'Weekly Team Sprint Planning - 2025_06_24 - Notes by Gemini.docx'
        },
        {
            'id': 'doc_002',
            'title': 'Quarterly Review Meeting',
            'filename': 'Q2 Review - 2025_06_24 - Notes by Gemini.docx'
        }
    ]
    
    # Test content matching
    matcher = ContentMatcher()
    match = matcher.find_content_match(email_record, doc_candidates)
    
    if match:
        print(f"Found content match!")
        print(f"  Confidence: {match.confidence:.2f}")
        print(f"  Title similarity: {match.title_similarity:.2f}")
        print(f"  Keyword overlap: {match.keyword_overlap:.2f}")
        print(f"  Semantic similarity: {match.semantic_similarity:.2f}")
        print(f"  Email title: '{match.email_title}'")
        print(f"  Doc title: '{match.doc_title}'")
        print(f"  Matched keywords: {match.matched_keywords}")
    else:
        print("No content match found")