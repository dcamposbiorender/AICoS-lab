#!/usr/bin/env python3
"""
Commitment Extractor - Phase 2 Lite Implementation
Basic AI-powered commitment and goal extraction from collected data

This module provides minimal commitment extraction using pattern matching
and basic NLP to identify commitments, TODOs, and goals from Slack messages,
meeting notes, and documents. Designed as a bridge to full Phase 2 intelligence.

Architecture:
- Uses deterministic patterns for high-confidence extraction
- Integrates with search database for querying content
- Provides structured output compatible with Phase 6 orchestration
- Lab-grade implementation focused on essential patterns

Implementation Status: FUNCTIONAL MINIMAL VERSION
Ready for Phase 6 integration and user value delivery
"""

import re
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

from ..search.database import SearchDatabase
from ..core.config import get_config
from .bot_filter import BotFilter

logger = logging.getLogger(__name__)


class CommitmentType(Enum):
    """Types of commitments that can be extracted"""
    TODO = "todo"
    DEADLINE = "deadline"
    MEETING_SCHEDULED = "meeting_scheduled"
    ACTION_ITEM = "action_item"
    GOAL = "goal"
    FOLLOW_UP = "follow_up"


@dataclass
class ExtractedCommitment:
    """A commitment or action item extracted from content"""
    commitment_id: str
    content: str
    commitment_type: CommitmentType
    confidence_score: float
    source: str
    source_date: str
    context: str
    person_mentioned: Optional[str]
    due_date: Optional[str]
    priority: str  # low, medium, high
    metadata: Dict[str, Any]


@dataclass
class CommitmentExtractionResult:
    """Results from commitment extraction process"""
    commitments_found: int
    high_confidence_commitments: int
    extraction_duration: float
    sources_processed: List[str]
    extracted_commitments: List[ExtractedCommitment]
    extraction_stats: Dict[str, int]


class CommitmentExtractor:
    """
    Phase 2 Lite commitment extraction using pattern matching
    
    Focuses on high-confidence patterns to minimize false positives
    while capturing the most important commitments and action items.
    """
    
    def __init__(self, base_path: Path = None):
        self.base_path = Path(base_path or get_config().base_dir)
        self.search_db = SearchDatabase(str(self.base_path / "data" / "search.db"))
        
        # Initialize bot filter for clean extraction
        users_file = self.base_path / "data" / "raw" / "slack" / "2025-08-25" / "users.json"
        self.bot_filter = BotFilter(str(users_file) if users_file.exists() else None)
        
        # Compile extraction patterns for performance
        self._compile_patterns()
        
        logger.info(f"Commitment Extractor initialized - Phase 2 Lite with bot filtering")
        logger.info(f"Base path: {self.base_path}")
    
    def _compile_patterns(self):
        """Compile regex patterns for commitment extraction"""
        
        # TODO and action item patterns
        self.todo_patterns = [
            re.compile(r'\btodo:?\s+(.+?)(?:\n|$)', re.IGNORECASE),
            re.compile(r'\b(?:need to|should|must|have to)\s+(.{10,100}?)(?:\.|;|\n|$)', re.IGNORECASE),
            re.compile(r'action item:?\s+(.+?)(?:\n|$)', re.IGNORECASE),
            re.compile(r'\[\s*\]\s*(.+?)(?:\n|$)'),  # Checkbox items
            re.compile(r'(?:^|\n)\s*[-*•]\s*(.+?)\s*(?:\n|$)')  # Bullet points
        ]
        
        # Deadline patterns
        self.deadline_patterns = [
            re.compile(r'(?:due|deadline|by)\s+(.{5,50}?)(?:\.|;|\n|$)', re.IGNORECASE),
            re.compile(r'(?:before|until)\s+(.{5,30}?)(?:\.|;|\n|$)', re.IGNORECASE),
            re.compile(r'(?:friday|monday|tuesday|wednesday|thursday|saturday|sunday)', re.IGNORECASE),
            re.compile(r'\b(?:today|tomorrow|next week|this week|end of week)\b', re.IGNORECASE)
        ]
        
        # Meeting scheduling patterns
        self.meeting_patterns = [
            re.compile(r'(?:schedule|book|set up)\s+(?:a\s+)?(?:meeting|call|sync)', re.IGNORECASE),
            re.compile(r'let\'s\s+(?:meet|sync|catch up)', re.IGNORECASE),
            re.compile(r'(?:available|free)\s+(?:for|to)\s+(?:meet|chat|sync)', re.IGNORECASE)
        ]
        
        # Person mention patterns
        self.person_patterns = [
            re.compile(r'<@([A-Z0-9]+)>'),  # Slack user mentions
            re.compile(r'@(\w+)'),  # @mentions
            re.compile(r'\b([A-Z][a-z]+\s+[A-Z][a-z]+)\b'),  # Names like "John Smith"
            re.compile(r'\b([a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,})\b')  # Email addresses (improved)
        ]
        
        # Priority indicators
        self.priority_patterns = {
            'high': re.compile(r'\b(?:urgent|asap|critical|important|high priority)\b', re.IGNORECASE),
            'medium': re.compile(r'\b(?:soon|this week|priority|needed)\b', re.IGNORECASE),
            'low': re.compile(r'\b(?:when possible|low priority|eventually|someday)\b', re.IGNORECASE)
        }
        
        logger.info("Compiled extraction patterns for commitment detection")
    
    def extract_commitments_from_search(self, 
                                       query: str = None, 
                                       days_back: int = 7,
                                       sources: List[str] = None) -> CommitmentExtractionResult:
        """
        Extract commitments from search results
        
        Args:
            query: Optional search query to filter content
            days_back: Number of days back to search
            sources: List of sources to include (slack, drive, calendar)
        """
        start_time = datetime.now()
        extracted_commitments = []
        sources_processed = []
        extraction_stats = {
            'records_processed': 0,
            'todos_found': 0,
            'deadlines_found': 0,
            'meetings_found': 0,
            'action_items_found': 0
        }
        
        logger.info(f"Starting commitment extraction...")
        logger.info(f"Query: {query or 'all content'}")
        logger.info(f"Days back: {days_back}")
        logger.info(f"Sources: {sources or 'all'}")
        
        # Define date range for search
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        date_range = (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
        
        # Get content from each source
        target_sources = sources or ['slack', 'drive', 'calendar']
        
        for source in target_sources:
            try:
                # Search for content in this source
                if query:
                    search_results = self.search_db.search(
                        query=query,
                        source=source,
                        date_range=date_range,
                        limit=1000
                    )
                else:
                    # Get all recent content from this source using a broad query
                    search_results = self.search_db.search(
                        query="the OR and OR to OR of",  # Broad terms likely to match most content
                        source=source,
                        date_range=date_range,
                        limit=1000
                    )
                
                logger.info(f"Processing {len(search_results)} records from {source}")
                sources_processed.append(source)
                
                # Extract commitments from each result
                for result in search_results:
                    # Check if this is from a bot user
                    metadata = result.get('metadata', {})
                    user_id = None
                    
                    # Try to extract user ID from metadata
                    if isinstance(metadata, dict):
                        user_id = metadata.get('user') or metadata.get('user_id')
                    elif isinstance(metadata, str):
                        try:
                            meta_dict = json.loads(metadata)
                            user_id = meta_dict.get('user') or meta_dict.get('user_id')
                        except:
                            pass
                    
                    # Skip bot messages
                    if user_id and self.bot_filter.is_bot(user_id, result.get('content')):
                        logger.debug(f"Skipping bot message from {user_id}")
                        continue
                    
                    commitments = self._extract_from_content(
                        content=result['content'],
                        source=source,
                        source_date=result['date'],
                        metadata=metadata
                    )
                    
                    extracted_commitments.extend(commitments)
                    extraction_stats['records_processed'] += 1
                    
                    # Update extraction stats
                    for commitment in commitments:
                        extraction_stats[f"{commitment.commitment_type.value}s_found"] += 1
                
            except Exception as e:
                logger.error(f"Error processing source {source}: {e}")
                continue
        
        # Calculate high confidence commitments
        high_confidence_commitments = len([
            c for c in extracted_commitments if c.confidence_score >= 0.8
        ])
        
        # Calculate processing duration
        processing_duration = (datetime.now() - start_time).total_seconds()
        
        # Create result
        result = CommitmentExtractionResult(
            commitments_found=len(extracted_commitments),
            high_confidence_commitments=high_confidence_commitments,
            extraction_duration=processing_duration,
            sources_processed=sources_processed,
            extracted_commitments=extracted_commitments,
            extraction_stats=extraction_stats
        )
        
        logger.info(f"Commitment extraction completed:")
        logger.info(f"  Total commitments: {len(extracted_commitments)}")
        logger.info(f"  High confidence: {high_confidence_commitments}")
        logger.info(f"  Duration: {processing_duration:.2f}s")
        
        return result
    
    def _extract_from_content(self, 
                            content: str, 
                            source: str, 
                            source_date: str,
                            metadata: Any) -> List[ExtractedCommitment]:
        """Extract commitments from a single piece of content"""
        commitments = []
        
        # Parse metadata if it's a JSON string
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except:
                metadata = {}
        
        # Extract different types of commitments
        commitments.extend(self._extract_todos(content, source, source_date, metadata))
        commitments.extend(self._extract_deadlines(content, source, source_date, metadata))
        commitments.extend(self._extract_meetings(content, source, source_date, metadata))
        
        return commitments
    
    def _extract_todos(self, content: str, source: str, source_date: str, metadata: dict) -> List[ExtractedCommitment]:
        """Extract TODO items and action items"""
        commitments = []
        
        for pattern in self.todo_patterns:
            for match in pattern.finditer(content):
                # Get the captured group or the full match
                match_text = match.group(1) if match.groups() else match.group(0)
                
                if len(match_text.strip()) < 10:  # Skip very short items
                    continue
                
                # Extract person mentions
                person = self._extract_person_mentions(match_text)
                
                # Determine priority
                priority = self._determine_priority(match_text)
                
                # Calculate confidence score
                confidence = self._calculate_confidence(match_text, CommitmentType.TODO)
                
                commitment = ExtractedCommitment(
                    commitment_id=f"todo_{source}_{len(commitments)}_{abs(hash(match_text)) % 10000}",
                    content=match_text.strip(),
                    commitment_type=CommitmentType.TODO,
                    confidence_score=confidence,
                    source=source,
                    source_date=source_date,
                    context=content[:200] + "..." if len(content) > 200 else content,
                    person_mentioned=person,
                    due_date=self._extract_due_date(match_text),
                    priority=priority,
                    metadata=metadata
                )
                
                commitments.append(commitment)
        
        return commitments
    
    def _extract_deadlines(self, content: str, source: str, source_date: str, metadata: dict) -> List[ExtractedCommitment]:
        """Extract deadline-related commitments"""
        commitments = []
        
        for pattern in self.deadline_patterns:
            for match in pattern.finditer(content):
                # Get the captured group or the full match
                match_text = match.group(1) if match.groups() else match.group(0)
                
                if len(match_text.strip()) < 5:
                    continue
                
                person = self._extract_person_mentions(match_text)
                priority = self._determine_priority(match_text)
                confidence = self._calculate_confidence(match_text, CommitmentType.DEADLINE)
                
                commitment = ExtractedCommitment(
                    commitment_id=f"deadline_{source}_{len(commitments)}_{abs(hash(match_text)) % 10000}",
                    content=match_text.strip(),
                    commitment_type=CommitmentType.DEADLINE,
                    confidence_score=confidence,
                    source=source,
                    source_date=source_date,
                    context=content[:200] + "..." if len(content) > 200 else content,
                    person_mentioned=person,
                    due_date=self._extract_due_date(match_text),
                    priority=priority,
                    metadata=metadata
                )
                
                commitments.append(commitment)
        
        return commitments
    
    def _extract_meetings(self, content: str, source: str, source_date: str, metadata: dict) -> List[ExtractedCommitment]:
        """Extract meeting scheduling commitments"""
        commitments = []
        
        for pattern in self.meeting_patterns:
            for match in pattern.finditer(content):
                # Get the matched text
                match_text = match.group(0)
                
                # Get surrounding context for better understanding
                context_text = self._get_surrounding_context(content, match_text, 50)
                
                person = self._extract_person_mentions(context_text)
                priority = self._determine_priority(context_text)
                confidence = self._calculate_confidence(context_text, CommitmentType.MEETING_SCHEDULED)
                
                commitment = ExtractedCommitment(
                    commitment_id=f"meeting_{source}_{len(commitments)}_{abs(hash(context_text)) % 10000}",
                    content=context_text.strip(),
                    commitment_type=CommitmentType.MEETING_SCHEDULED,
                    confidence_score=confidence,
                    source=source,
                    source_date=source_date,
                    context=content[:200] + "..." if len(content) > 200 else content,
                    person_mentioned=person,
                    due_date=None,  # Meetings don't have due dates
                    priority=priority,
                    metadata=metadata
                )
                
                commitments.append(commitment)
        
        return commitments
    
    def _extract_person_mentions(self, text: str) -> Optional[str]:
        """Extract person mentions from text"""
        for pattern in self.person_patterns:
            match = pattern.search(text)
            if match:
                return match.group(1) if match.groups() else match.group(0)
        return None
    
    def _determine_priority(self, text: str) -> str:
        """Determine priority level from text"""
        for priority, pattern in self.priority_patterns.items():
            if pattern.search(text):
                return priority
        return 'medium'  # Default priority
    
    def _extract_due_date(self, text: str) -> Optional[str]:
        """Extract due date from text (simplified)"""
        for pattern in self.deadline_patterns:
            match = pattern.search(text)
            if match:
                # Get the first group if it exists, otherwise the whole match
                return match.group(1).strip() if match.groups() else match.group(0).strip()
        return None
    
    def _calculate_confidence(self, text: str, commitment_type: CommitmentType) -> float:
        """Calculate confidence score for extracted commitment"""
        confidence = 0.5  # Base confidence
        
        # Boost confidence for specific patterns
        if commitment_type == CommitmentType.TODO:
            if 'todo' in text.lower() or 'action item' in text.lower():
                confidence += 0.3
            if any(word in text.lower() for word in ['need to', 'should', 'must']):
                confidence += 0.2
        
        elif commitment_type == CommitmentType.DEADLINE:
            if any(word in text.lower() for word in ['due', 'deadline', 'by']):
                confidence += 0.3
            if any(word in text.lower() for word in ['friday', 'monday', 'tuesday', 'wednesday', 'thursday']):
                confidence += 0.2
        
        elif commitment_type == CommitmentType.MEETING_SCHEDULED:
            if 'schedule' in text.lower() or 'meeting' in text.lower():
                confidence += 0.3
        
        # Cap confidence at 1.0
        return min(confidence, 1.0)
    
    def _get_surrounding_context(self, text: str, match: str, context_chars: int) -> str:
        """Get surrounding context for a match"""
        match_pos = text.find(match)
        if match_pos == -1:
            return match
        
        start = max(0, match_pos - context_chars)
        end = min(len(text), match_pos + len(match) + context_chars)
        
        return text[start:end]
    
    def get_commitment_summary(self, result: CommitmentExtractionResult) -> Dict[str, Any]:
        """Generate summary of extracted commitments"""
        summary = {
            'total_commitments': result.commitments_found,
            'high_confidence_commitments': result.high_confidence_commitments,
            'commitments_by_type': {},
            'commitments_by_source': {},
            'commitments_by_priority': {'high': 0, 'medium': 0, 'low': 0},
            'recent_commitments': []
        }
        
        # Analyze commitments by type and source
        for commitment in result.extracted_commitments:
            # By type
            type_key = commitment.commitment_type.value
            summary['commitments_by_type'][type_key] = summary['commitments_by_type'].get(type_key, 0) + 1
            
            # By source
            summary['commitments_by_source'][commitment.source] = summary['commitments_by_source'].get(commitment.source, 0) + 1
            
            # By priority
            summary['commitments_by_priority'][commitment.priority] += 1
        
        # Get recent high-confidence commitments
        recent_high_conf = [
            c for c in result.extracted_commitments 
            if c.confidence_score >= 0.8
        ][:10]
        
        summary['recent_commitments'] = [
            {
                'content': c.content[:100] + "..." if len(c.content) > 100 else c.content,
                'type': c.commitment_type.value,
                'source': c.source,
                'confidence': c.confidence_score,
                'priority': c.priority
            }
            for c in recent_high_conf
        ]
        
        return summary
    
    def extract_commitments(self, content: str) -> List[Dict[str, Any]]:
        """
        Extract commitments from a single piece of content
        
        This method is used by the CRM system for direct content processing.
        Returns a simplified list of commitment dictionaries.
        
        Args:
            content: Text content to analyze
            
        Returns:
            List of commitment dictionaries
        """
        if not content or not content.strip():
            return []
        
        # Use existing internal method to extract commitments
        extracted_commitments = self._extract_from_content(
            content=content,
            source="direct",
            source_date=datetime.now().isoformat(),
            metadata={}
        )
        
        # Convert to simplified dictionary format expected by CRM
        simplified_commitments = []
        for commitment in extracted_commitments:
            simplified_commitments.append({
                'id': commitment.commitment_id,
                'text': commitment.content,
                'description': commitment.content,
                'confidence_score': commitment.confidence_score,
                'type': commitment.commitment_type.value,
                'priority': commitment.priority,
                'person_mentioned': commitment.person_mentioned,
                'due_date': commitment.due_date,
                'metadata': {
                    'source': commitment.source,
                    'extraction_method': 'pattern_match',
                    'context': commitment.context
                }
            })
        
        return simplified_commitments


def create_commitment_extractor(base_path: Path = None) -> CommitmentExtractor:
    """Factory function to create commitment extractor"""
    return CommitmentExtractor(base_path)


# CLI interface for testing
if __name__ == "__main__":
    print("🧠 Commitment Extractor - Phase 2 Lite")
    print("=" * 50)
    
    try:
        extractor = CommitmentExtractor()
        
        # Extract commitments from recent content
        result = extractor.extract_commitments_from_search(
            query=None,  # Search all content
            days_back=7,
            sources=['slack', 'drive']
        )
        
        print(f"✅ Commitment extraction completed:")
        print(f"   🎯 Total commitments: {result.commitments_found}")
        print(f"   ⭐ High confidence: {result.high_confidence_commitments}")
        print(f"   ⏱️  Duration: {result.extraction_duration:.2f}s")
        print(f"   📊 Sources processed: {', '.join(result.sources_processed)}")
        
        # Show summary
        summary = extractor.get_commitment_summary(result)
        print(f"\n📋 Commitment Summary:")
        print(f"   By type: {summary['commitments_by_type']}")
        print(f"   By priority: {summary['commitments_by_priority']}")
        
        if summary['recent_commitments']:
            print(f"\n🔝 Recent High-Confidence Commitments:")
            for i, commitment in enumerate(summary['recent_commitments'][:5], 1):
                print(f"   {i}. [{commitment['type']}] {commitment['content']} (confidence: {commitment['confidence']:.2f})")
        
        print("\n🎯 Phase 2 Lite commitment extraction ready for Phase 6 integration!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()