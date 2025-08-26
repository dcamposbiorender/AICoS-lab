#!/usr/bin/env python3
"""
Meeting Correlator - Main Correlation Engine for Phase 3
Orchestrates temporal, participant, and content matching for comprehensive correlation

This is the main correlation engine that combines all three matching strategies
(temporal, participant, content) to create unified meeting records from email
notifications and Google Docs meeting notes.

Architecture:
- MeetingCorrelator: Main orchestration engine
- CompositeMatching: Multi-criteria correlation with weighted scoring
- CorrelationStrategy: Configurable correlation approaches
- ResultsManager: Manages correlated and orphaned records

Usage:
    from src.correlators.meeting_correlator import MeetingCorrelator
    correlator = MeetingCorrelator()
    results = correlator.correlate_meetings(email_records, doc_records)
"""

import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

from .correlation_models import (
    CorrelatedMeeting, CorrelationMatch, OrphanedRecord, CorrelationMetrics,
    MatchType, CorrelationStatus
)
from .temporal_matcher import TemporalMatcher, TemporalMatch
from .participant_matcher import ParticipantMatcher, ParticipantMatch  
from .content_matcher import ContentMatcher, ContentMatch

logger = logging.getLogger(__name__)


class CorrelationStrategy(Enum):
    """Different correlation strategies"""
    TEMPORAL_FIRST = "temporal_first"         # Prioritize time matching
    PARTICIPANT_FIRST = "participant_first"   # Prioritize participant matching
    CONTENT_FIRST = "content_first"           # Prioritize content matching
    COMPOSITE = "composite"                   # Weighted combination of all methods
    ADAPTIVE = "adaptive"                     # Choose best method per record


@dataclass
class CompositeMatchResult:
    """Combined result from all matching strategies"""
    email_id: str
    doc_id: str
    overall_confidence: float
    match_type: MatchType
    
    # Individual match results
    temporal_match: Optional[TemporalMatch]
    participant_match: Optional[ParticipantMatch]
    content_match: Optional[ContentMatch]
    
    # Combined scoring
    temporal_score: float
    participant_score: float
    content_score: float
    composite_score: float
    
    # Match details
    match_signals: Dict[str, Any]
    
    def get_best_individual_match(self) -> Tuple[str, float]:
        """Get the best individual matching strategy and its score"""
        scores = {
            'temporal': self.temporal_score,
            'participant': self.participant_score,
            'content': self.content_score
        }
        
        best_strategy = max(scores.items(), key=lambda x: x[1])
        return best_strategy


@dataclass
class CorrelationResults:
    """Complete correlation results with metrics"""
    correlated_meetings: List[CorrelatedMeeting]
    orphaned_emails: List[OrphanedRecord]
    orphaned_docs: List[OrphanedRecord]
    correlation_metrics: CorrelationMetrics
    processing_time: float
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics"""
        return {
            'total_correlations': len(self.correlated_meetings),
            'orphaned_emails': len(self.orphaned_emails),
            'orphaned_docs': len(self.orphaned_docs),
            'correlation_accuracy': self.correlation_metrics.correlation_accuracy,
            'processing_time': self.processing_time,
            'average_confidence': self.correlation_metrics.average_confidence
        }


class MeetingCorrelator:
    """Main correlation engine orchestrating all matching strategies"""
    
    def __init__(self, 
                 strategy: CorrelationStrategy = CorrelationStrategy.COMPOSITE,
                 min_confidence_threshold: float = 0.6,
                 orphan_timeout_days: int = 7):
        """
        Initialize meeting correlator
        
        Args:
            strategy: Correlation strategy to use
            min_confidence_threshold: Minimum confidence for valid correlation
            orphan_timeout_days: Days to wait before marking records as orphaned
        """
        self.strategy = strategy
        self.min_confidence_threshold = min_confidence_threshold
        self.orphan_timeout_days = orphan_timeout_days
        
        # Initialize individual matchers
        self.temporal_matcher = TemporalMatcher()
        self.participant_matcher = ParticipantMatcher()
        self.content_matcher = ContentMatcher()
        
        self.logger = logging.getLogger(f"{__name__}.MeetingCorrelator")
        
        # Strategy weights for composite matching
        self.strategy_weights = {
            CorrelationStrategy.TEMPORAL_FIRST: {'temporal': 0.6, 'participant': 0.25, 'content': 0.15},
            CorrelationStrategy.PARTICIPANT_FIRST: {'temporal': 0.2, 'participant': 0.6, 'content': 0.2},
            CorrelationStrategy.CONTENT_FIRST: {'temporal': 0.15, 'participant': 0.25, 'content': 0.6},
            CorrelationStrategy.COMPOSITE: {'temporal': 0.4, 'participant': 0.35, 'content': 0.25},
            CorrelationStrategy.ADAPTIVE: {'temporal': 0.33, 'participant': 0.33, 'content': 0.33}
        }
    
    def find_composite_match(self, email_record: Dict[str, Any], 
                           doc_candidates: List[Dict[str, Any]]) -> Optional[CompositeMatchResult]:
        """
        Find best composite match using all matching strategies
        
        Args:
            email_record: Email record to match
            doc_candidates: List of Google Doc candidates
            
        Returns:
            Best composite match or None
        """
        # Run all individual matchers
        temporal_match = self.temporal_matcher.find_temporal_match(email_record, doc_candidates)
        participant_match = self.participant_matcher.find_participant_match(email_record, doc_candidates)
        content_match = self.content_matcher.find_content_match(email_record, doc_candidates)
        
        # Create candidate matches map
        doc_matches = {}
        
        if temporal_match:
            if temporal_match.doc_id not in doc_matches:
                doc_matches[temporal_match.doc_id] = {}
            doc_matches[temporal_match.doc_id]['temporal'] = temporal_match
        
        if participant_match:
            if participant_match.doc_id not in doc_matches:
                doc_matches[participant_match.doc_id] = {}
            doc_matches[participant_match.doc_id]['participant'] = participant_match
        
        if content_match:
            if content_match.doc_id not in doc_matches:
                doc_matches[content_match.doc_id] = {}
            doc_matches[content_match.doc_id]['content'] = content_match
        
        if not doc_matches:
            return None
        
        # Calculate composite scores for each candidate doc
        best_composite_match = None
        best_composite_score = 0.0
        
        weights = self.strategy_weights[self.strategy]
        
        for doc_id, matches in doc_matches.items():
            temporal_score = matches.get('temporal', type('', (), {'confidence': 0.0})()).confidence
            participant_score = matches.get('participant', type('', (), {'confidence': 0.0})()).confidence  
            content_score = matches.get('content', type('', (), {'confidence': 0.0})()).confidence
            
            # Calculate weighted composite score
            if self.strategy == CorrelationStrategy.ADAPTIVE:
                # Use the maximum individual score as the composite (adaptive)
                composite_score = max(temporal_score, participant_score, content_score)
                match_type = MatchType.COMPOSITE
                
                # Determine primary match type
                if temporal_score == composite_score:
                    match_type = MatchType.TEMPORAL
                elif participant_score == composite_score:
                    match_type = MatchType.PARTICIPANT
                elif content_score == composite_score:
                    match_type = MatchType.CONTENT
            else:
                # Weighted combination
                composite_score = (
                    weights['temporal'] * temporal_score +
                    weights['participant'] * participant_score +
                    weights['content'] * content_score
                )
                match_type = MatchType.COMPOSITE
            
            if composite_score > best_composite_score and composite_score >= self.min_confidence_threshold:
                match_signals = {
                    'temporal_signals': matches.get('temporal').match_signals if 'temporal' in matches else None,
                    'participant_signals': matches.get('participant').match_signals if 'participant' in matches else None,
                    'content_signals': matches.get('content').match_signals if 'content' in matches else None,
                    'strategy_weights': weights,
                    'composite_calculation': {
                        'temporal_weighted': weights['temporal'] * temporal_score,
                        'participant_weighted': weights['participant'] * participant_score,
                        'content_weighted': weights['content'] * content_score
                    }
                }
                
                best_composite_match = CompositeMatchResult(
                    email_id=email_record.get('id', 'unknown'),
                    doc_id=doc_id,
                    overall_confidence=composite_score,
                    match_type=match_type,
                    temporal_match=matches.get('temporal'),
                    participant_match=matches.get('participant'),
                    content_match=matches.get('content'),
                    temporal_score=temporal_score,
                    participant_score=participant_score,
                    content_score=content_score,
                    composite_score=composite_score,
                    match_signals=match_signals
                )
                best_composite_score = composite_score
        
        return best_composite_match
    
    def create_correlation_match(self, composite_match: CompositeMatchResult) -> CorrelationMatch:
        """Create CorrelationMatch from CompositeMatchResult"""
        return CorrelationMatch(
            email_id=composite_match.email_id,
            doc_id=composite_match.doc_id,
            match_type=composite_match.match_type,
            confidence_score=composite_match.overall_confidence,
            match_details=composite_match.match_signals,
            created_at=datetime.now(timezone.utc)
        )
    
    def correlate_meetings(self, email_records: List[Dict[str, Any]], 
                         doc_records: List[Dict[str, Any]]) -> CorrelationResults:
        """
        Main correlation method - correlate all emails with documents
        
        Args:
            email_records: List of email records from Phase 1
            doc_records: List of Google Doc records from Phase 2
            
        Returns:
            Complete correlation results with metrics
        """
        start_time = time.time()
        
        self.logger.info(f"Starting correlation: {len(email_records)} emails, {len(doc_records)} docs")
        self.logger.info(f"Using strategy: {self.strategy.value}")
        
        # Track results
        correlated_meetings = []
        matched_email_ids = set()
        matched_doc_ids = set()
        correlation_attempts = []
        
        # Find correlations
        for email_record in email_records:
            email_id = email_record.get('id', f"email_{hash(str(email_record)) % 10000}")
            email_record['id'] = email_id  # Ensure ID is set
            
            composite_match = self.find_composite_match(email_record, doc_records)
            
            if composite_match:
                # Find corresponding doc record
                doc_record = next(
                    (doc for doc in doc_records if doc.get('id') == composite_match.doc_id),
                    None
                )
                
                if doc_record and composite_match.doc_id not in matched_doc_ids:
                    # Create correlation
                    correlation_match = self.create_correlation_match(composite_match)
                    
                    # Create correlated meeting
                    correlated_meeting = CorrelatedMeeting.from_email_and_doc(
                        email_record, doc_record, correlation_match
                    )
                    
                    correlated_meetings.append(correlated_meeting)
                    matched_email_ids.add(email_id)
                    matched_doc_ids.add(composite_match.doc_id)
                    
                    self.logger.debug(f"Correlated email '{email_record.get('title', 'unknown')}' "
                                    f"with doc '{doc_record.get('title', 'unknown')}' "
                                    f"(confidence: {composite_match.overall_confidence:.2f})")
            
            correlation_attempts.append({
                'email_id': email_id,
                'match_found': composite_match is not None,
                'confidence': composite_match.overall_confidence if composite_match else 0.0
            })
        
        # Create orphaned records
        orphaned_emails = []
        orphaned_docs = []
        
        for email_record in email_records:
            email_id = email_record.get('id')
            if email_id not in matched_email_ids:
                orphaned_email = OrphanedRecord(
                    record_id=email_id,
                    record_type='email',
                    original_record=email_record,
                    correlation_attempts=[
                        attempt for attempt in correlation_attempts 
                        if attempt['email_id'] == email_id
                    ],
                    orphaned_at=datetime.now(timezone.utc),
                    created_at=datetime.now(timezone.utc)
                )
                orphaned_emails.append(orphaned_email)
        
        for doc_record in doc_records:
            doc_id = doc_record.get('id', f"doc_{hash(str(doc_record)) % 10000}")
            doc_record['id'] = doc_id  # Ensure ID is set
            
            if doc_id not in matched_doc_ids:
                orphaned_doc = OrphanedRecord(
                    record_id=doc_id,
                    record_type='google_doc',
                    original_record=doc_record,
                    correlation_attempts=[],
                    orphaned_at=datetime.now(timezone.utc),
                    created_at=datetime.now(timezone.utc)
                )
                orphaned_docs.append(orphaned_doc)
        
        # Calculate metrics
        processing_time = time.time() - start_time
        
        # Count matches by type
        temporal_matches = sum(1 for m in correlated_meetings 
                             if m.correlation_match.match_type == MatchType.TEMPORAL)
        participant_matches = sum(1 for m in correlated_meetings
                                if m.correlation_match.match_type == MatchType.PARTICIPANT)
        content_matches = sum(1 for m in correlated_meetings
                            if m.correlation_match.match_type == MatchType.CONTENT)
        composite_matches = sum(1 for m in correlated_meetings
                              if m.correlation_match.match_type == MatchType.COMPOSITE)
        
        metrics = CorrelationMetrics(
            total_emails=len(email_records),
            total_docs=len(doc_records),
            successful_correlations=len(correlated_meetings),
            orphaned_emails=len(orphaned_emails),
            orphaned_docs=len(orphaned_docs),
            correlation_accuracy=0.0,  # Will be calculated
            processing_time=processing_time,
            average_confidence=sum(m.correlation_match.confidence_score for m in correlated_meetings) / 
                             len(correlated_meetings) if correlated_meetings else 0.0,
            temporal_matches=temporal_matches,
            participant_matches=participant_matches,
            content_matches=content_matches,
            composite_matches=composite_matches,
            created_at=datetime.now(timezone.utc)
        )
        
        metrics.calculate_accuracy()
        
        # Log results
        self.logger.info(f"Correlation complete: {len(correlated_meetings)} matches found")
        self.logger.info(f"Orphaned: {len(orphaned_emails)} emails, {len(orphaned_docs)} docs")
        self.logger.info(f"Accuracy: {metrics.correlation_accuracy:.1f}%")
        self.logger.info(f"Processing time: {processing_time:.2f}s")
        
        return CorrelationResults(
            correlated_meetings=correlated_meetings,
            orphaned_emails=orphaned_emails,
            orphaned_docs=orphaned_docs,
            correlation_metrics=metrics,
            processing_time=processing_time
        )
    
    def extract_structured_content(self, correlated_meetings: List[CorrelatedMeeting]) -> None:
        """Extract action items, todos, and deadlines from correlated meetings"""
        try:
            from ..queries.structured import StructuredExtractor
            extractor = StructuredExtractor()
            
            for meeting in correlated_meetings:
                if meeting.meeting_content:
                    # Extract structured content
                    meeting.action_items = extractor.extract_action_items(meeting.meeting_content)
                    meeting.todos = extractor.extract_todos(meeting.meeting_content)
                    meeting.deadlines = extractor.extract_deadlines(meeting.meeting_content)
                    
                    # Update timestamp
                    meeting.updated_at = datetime.now(timezone.utc)
                    
        except ImportError:
            self.logger.warning("StructuredExtractor not available, skipping content extraction")


# Example usage and testing
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Example data
    email_records = [
        {
            'id': 'email_001',
            'title': 'Weekly Team Sync Meeting',
            'participants': ['david@company.com', 'charlie@company.com'],
            'meeting_datetime': datetime(2025, 6, 24, 8, 46, tzinfo=timezone.utc)
        }
    ]
    
    doc_records = [
        {
            'id': 'doc_001',
            'title': 'Team Sync Notes',
            'filename': 'David _ Charlie - weekly sync - 2025_06_24 08_48 PDT - Notes by Gemini.docx',
            'meeting_metadata': {
                'participants': ['David', 'Charlie'],
                'date': datetime(2025, 6, 24).date()
            },
            'content': 'Meeting notes with action items...'
        }
    ]
    
    # Test correlation
    correlator = MeetingCorrelator(strategy=CorrelationStrategy.COMPOSITE)
    results = correlator.correlate_meetings(email_records, doc_records)
    
    print("Correlation Results:")
    print(f"  Correlated meetings: {len(results.correlated_meetings)}")
    print(f"  Orphaned emails: {len(results.orphaned_emails)}")
    print(f"  Orphaned docs: {len(results.orphaned_docs)}")
    print(f"  Accuracy: {results.correlation_metrics.correlation_accuracy:.1f}%")
    
    if results.correlated_meetings:
        meeting = results.correlated_meetings[0]
        print(f"\nExample correlation:")
        print(f"  Title: {meeting.meeting_title}")
        print(f"  Confidence: {meeting.correlation_match.confidence_score:.2f}")
        print(f"  Match type: {meeting.correlation_match.match_type.value}")
        print(f"  Participants: {meeting.participants}")