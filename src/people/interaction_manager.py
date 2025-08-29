"""
Interaction Manager - Leverage existing SearchDatabase for CRM interactions

References:
- src/search/database.py - SearchDatabase with 340K+ indexed records
- src/intelligence/commitment_extractor.py - Basic commitment extraction patterns
- src/queries/person_queries.py - PersonResolver for cross-system ID mapping
- src/correlators/meeting_correlator.py - Meeting/message correlation patterns

Core Philosophy: Reuse existing search infrastructure, don't rebuild it.
This manager wraps the existing SearchDatabase to extract person interactions
and feed them into the CRM system.
"""

import json
import logging
import re
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

from ..search.database import SearchDatabase
from ..intelligence.commitment_extractor import CommitmentExtractor
from ..core.config import get_config
from .models import Interaction, ActionItem, ActionDirection, ActionStatus, InteractionType
from .crm_directory import CRMDirectory
from .sentiment_analyzer import SentimentAnalyzer

logger = logging.getLogger(__name__)


class InteractionManager:
    """
    Manages person interactions by leveraging existing SearchDatabase
    
    Features:
    - Queries 340K+ indexed messages for person interactions
    - Uses existing CommitmentExtractor for action items
    - Cross-system correlation via PersonResolver
    - Feeds CRM with structured interaction data
    """
    
    def __init__(self, search_db_path: Optional[str] = None, crm_db_path: Optional[str] = None, crm_instance: Optional['CRMDirectory'] = None):
        """Initialize interaction manager with existing infrastructure"""
        config = get_config()
        
        # Reuse existing SearchDatabase with 340K+ records
        if search_db_path:
            self.search_db = SearchDatabase(search_db_path)
        else:
            self.search_db = SearchDatabase(str(config.base_dir / "data" / "search.db"))
        
        # Reuse existing CommitmentExtractor
        self.commitment_extractor = CommitmentExtractor()
        
        # Initialize CRM directory (reuse if provided)
        self.crm = crm_instance if crm_instance else CRMDirectory(crm_db_path)
        
        # Initialize enhanced sentiment analyzer
        self.sentiment_analyzer = SentimentAnalyzer()
        
        # Stats tracking
        self.stats = {
            "interactions_processed": 0,
            "commitments_extracted": 0,
            "sources_queried": 0,
            "processing_time": 0.0
        }
        
        logger.info("InteractionManager initialized - leveraging existing SearchDatabase")
        logger.info(f"SearchDB path: {self.search_db.db_path}")
        logger.info(f"CRM DB path: {self.crm.db_path}")
    
    def get_person_interactions(self, email: str, days: int = 30, limit: int = 100) -> List[Interaction]:
        """
        Get all interactions for a person from existing search database
        
        Args:
            email: Person's email address
            days: Number of days back to search
            limit: Maximum number of interactions to return
            
        Returns:
            List of Interaction objects
        """
        start_time = datetime.now()
        
        # Get all identifiers for this person via existing PersonResolver
        person_ids = self._get_person_identifiers(email)
        if not person_ids:
            logger.warning(f"No identifiers found for person: {email}")
            return []
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        all_interactions = []
        sources_queried = []
        
        # Search across all sources using existing SearchDatabase
        for source in ['slack', 'calendar', 'drive', 'email']:
            try:
                # Search by various identifiers
                for identifier_type, identifier in person_ids.items():
                    if not identifier:
                        continue
                    
                    # Use existing SearchDatabase.search method - escape special FTS5 characters
                    escaped_identifier = identifier.replace('@', ' ').replace('.', ' ')
                    results = self.search_db.search(
                        query=escaped_identifier,
                        source=source,
                        date_range=(start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')),
                        limit=limit
                    )
                    
                    # Convert search results to Interaction objects
                    interactions = self._convert_search_results_to_interactions(
                        results, email, source, identifier_type
                    )
                    all_interactions.extend(interactions)
                    
                    if results:
                        sources_queried.append(f"{source}:{identifier_type}")
                        
            except Exception as e:
                logger.error(f"Failed to search {source} for {email}: {e}")
                continue
        
        # Remove duplicates based on source_id
        unique_interactions = self._deduplicate_interactions(all_interactions)
        
        # Sort by timestamp (most recent first)
        unique_interactions.sort(key=lambda x: x.timestamp, reverse=True)
        
        # Update stats
        processing_time = (datetime.now() - start_time).total_seconds()
        self.stats["interactions_processed"] += len(unique_interactions)
        self.stats["sources_queried"] += len(sources_queried)
        self.stats["processing_time"] += processing_time
        
        logger.info(f"Found {len(unique_interactions)} interactions for {email} "
                   f"across {len(sources_queried)} sources in {processing_time:.2f}s")
        
        # Apply conversation threading
        threaded_interactions = self._apply_conversation_threading(unique_interactions)
        
        return threaded_interactions[:limit]
    
    def _get_person_identifiers(self, email: str) -> Dict[str, str]:
        """Get all identifiers for a person via existing PersonResolver"""
        try:
            # Use CRM's PersonResolver (already initialized)
            resolver = self.crm.person_resolver
            
            # Try to find person in existing roster
            person = None
            for employee in resolver.employees:
                # Safety check: ensure employee is a dict, not a string
                if isinstance(employee, dict) and employee.get('email', '').lower() == email.lower():
                    person = employee
                    break
            
            if not person:
                # Fallback: try to resolve by email directly
                try:
                    resolved = resolver.find_person(email)
                    if resolved:
                        person = resolved
                except Exception:
                    pass
            
            if person:
                return {
                    'email': person.get('email', ''),
                    'slack_id': person.get('slack_id', ''),
                    'slack_name': person.get('slack_name', ''),
                    'name': person.get('name', '') or person.get('slack_name', ''),
                    'display_name': person.get('slack_display_name', '')
                }
            else:
                # Return basic identifiers
                return {
                    'email': email,
                    'slack_id': '',
                    'slack_name': '',
                    'name': email.split('@')[0],
                    'display_name': ''
                }
                
        except Exception as e:
            logger.error(f"Failed to get identifiers for {email}: {e}")
            return {'email': email, 'slack_id': '', 'slack_name': '', 'name': '', 'display_name': ''}
    
    def _convert_search_results_to_interactions(self, results: List[Dict], 
                                              person_email: str, source: str, 
                                              identifier_type: str) -> List[Interaction]:
        """Convert SearchDatabase results to Interaction objects"""
        interactions = []
        
        for result in results:
            try:
                # Determine interaction type based on source
                interaction_type = self._determine_interaction_type(source, result)
                
                # Extract timestamp
                timestamp = self._extract_timestamp(result)
                
                # Analyze sentiment
                content = result.get('content', '')
                sentiment_analysis = self.sentiment_analyzer.analyze_text(
                    content, 
                    context={
                        'interaction_type': interaction_type.value,
                        'source': source,
                        'channel': result.get('channel', '')
                    }
                ) if content else None
                
                # Create interaction object
                interaction = Interaction(
                    person_email=person_email,
                    timestamp=timestamp,
                    interaction_type=interaction_type,
                    summary=self._generate_summary(result),
                    content=content,
                    source=source,
                    source_id=result.get('id', ''),
                    reference=self._build_reference(source, result),
                    channel=result.get('channel', ''),
                    participants=self._extract_participants(result),
                    key_topics=self._extract_key_topics(content),
                    sentiment_score=sentiment_analysis.score if sentiment_analysis else 0.0,
                    metadata={
                        'identifier_type': identifier_type,
                        'search_score': result.get('score', 0),
                        'sentiment_analysis': sentiment_analysis.__dict__ if sentiment_analysis else None,
                        'raw_result': result
                    }
                )
                
                interactions.append(interaction)
                
            except Exception as e:
                logger.error(f"Failed to convert search result to interaction: {e}")
                continue
        
        return interactions
    
    def _determine_interaction_type(self, source: str, result: Dict) -> InteractionType:
        """Determine interaction type from source and content"""
        if source == 'slack':
            if result.get('thread_ts'):
                return InteractionType.SLACK_THREAD
            else:
                return InteractionType.SLACK_MESSAGE
        elif source == 'calendar':
            return InteractionType.MEETING
        elif source == 'drive':
            return InteractionType.DOCUMENT
        elif source == 'email':
            return InteractionType.EMAIL
        else:
            return InteractionType.NOTE
    
    def _extract_timestamp(self, result: Dict) -> datetime:
        """Extract timestamp from search result"""
        # Try various timestamp fields
        for field in ['timestamp', 'date', 'created_at', 'updated_at']:
            if field in result and result[field]:
                try:
                    if isinstance(result[field], str):
                        # Try parsing ISO format
                        return datetime.fromisoformat(result[field].replace('Z', '+00:00'))
                    elif isinstance(result[field], (int, float)):
                        # Unix timestamp
                        return datetime.fromtimestamp(result[field])
                except Exception:
                    continue
        
        # Fallback to current time
        logger.warning(f"Could not extract timestamp from result: {result.keys()}")
        return datetime.now()
    
    def _generate_summary(self, result: Dict) -> str:
        """Generate a brief summary of the interaction"""
        content = result.get('content', '')
        
        if not content:
            return f"{result.get('source', 'Unknown')} interaction"
        
        # Extract first sentence or first 100 characters
        sentences = content.split('. ')
        if sentences and len(sentences[0]) <= 100:
            return sentences[0]
        else:
            return content[:100] + "..." if len(content) > 100 else content
    
    def _build_reference(self, source: str, result: Dict) -> str:
        """Build reference URL/identifier for the interaction"""
        if source == 'slack':
            channel = result.get('channel', '')
            ts = result.get('timestamp', '') or result.get('ts', '')
            if channel and ts:
                # Format: slack://C1234567890/p1234567890123456
                return f"slack://{channel}/{ts.replace('.', 'p')}"
        elif source == 'calendar':
            event_id = result.get('id', '')
            if event_id:
                return f"calendar://event/{event_id}"
        elif source == 'drive':
            file_id = result.get('id', '')
            if file_id:
                return f"drive://file/{file_id}"
        
        return f"{source}://{result.get('id', 'unknown')}"
    
    def _extract_participants(self, result: Dict) -> List[str]:
        """Extract participants from search result"""
        participants = []
        
        # Try various participant fields
        for field in ['participants', 'attendees', 'mentions', 'recipients']:
            if field in result and result[field]:
                if isinstance(result[field], list):
                    participants.extend(result[field])
                elif isinstance(result[field], str):
                    participants.append(result[field])
        
        # Add author if present
        if 'author' in result and result['author']:
            participants.append(result['author'])
        
        # Deduplicate and filter
        return list(set(p for p in participants if p and '@' in p))
    
    def _extract_key_topics(self, content: str) -> List[str]:
        """Extract key topics from content using simple heuristics"""
        if not content:
            return []
        
        # Simple keyword extraction (could be enhanced with NLP)
        keywords = []
        
        # Look for common business topics
        business_terms = [
            'meeting', 'project', 'deadline', 'budget', 'roadmap', 'milestone',
            'review', 'approval', 'launch', 'release', 'feature', 'bug', 'issue',
            'client', 'customer', 'user', 'feedback', 'requirements', 'spec',
            'design', 'development', 'testing', 'deployment', 'marketing',
            'sales', 'revenue', 'growth', 'strategy', 'team', 'hire', 'onboard'
        ]
        
        content_lower = content.lower()
        for term in business_terms:
            if term in content_lower:
                keywords.append(term)
        
        # Extract @mentions and #hashtags
        mentions = re.findall(r'@(\w+)', content)
        hashtags = re.findall(r'#(\w+)', content)
        
        keywords.extend([f"@{m}" for m in mentions])
        keywords.extend([f"#{h}" for h in hashtags])
        
        return list(set(keywords))[:10]  # Limit to 10 topics
    
    def _deduplicate_interactions(self, interactions: List[Interaction]) -> List[Interaction]:
        """Remove duplicate interactions based on source_id and timestamp"""
        seen = set()
        unique = []
        
        for interaction in interactions:
            key = f"{interaction.source}:{interaction.source_id}:{interaction.timestamp}"
            if key not in seen:
                seen.add(key)
                unique.append(interaction)
        
        return unique
    
    def _apply_conversation_threading(self, interactions: List[Interaction]) -> List[Interaction]:
        """
        Apply conversation threading to group related interactions
        
        Threads interactions based on:
        1. Explicit thread IDs (Slack thread_ts, email In-Reply-To)
        2. Temporal clustering (same participants within time window)
        3. Topic similarity (shared keywords/topics)
        """
        if len(interactions) <= 1:
            return interactions
        
        # Sort by timestamp for chronological processing
        sorted_interactions = sorted(interactions, key=lambda x: x.timestamp)
        
        # Thread detection strategies
        threads = {}
        thread_counter = 0
        
        for interaction in sorted_interactions:
            thread_id = None
            
            # Strategy 1: Explicit threading (Slack, Email)
            explicit_thread_id = self._extract_explicit_thread_id(interaction)
            if explicit_thread_id:
                thread_id = f"explicit_{explicit_thread_id}"
            
            # Strategy 2: Find related interactions by temporal + participant clustering
            if not thread_id:
                related_thread = self._find_related_thread(interaction, threads)
                if related_thread:
                    thread_id = related_thread
            
            # Strategy 3: Create new thread
            if not thread_id:
                thread_id = f"thread_{thread_counter}"
                thread_counter += 1
            
            # Add to thread
            if thread_id not in threads:
                threads[thread_id] = []
            threads[thread_id].append(interaction)
            
            # Update interaction with thread information
            interaction.thread_id = thread_id
            if len(threads[thread_id]) > 1:
                interaction.parent_interaction_id = threads[thread_id][0].id
        
        # Log threading statistics
        thread_stats = {
            'total_interactions': len(interactions),
            'threads_created': len(threads),
            'avg_thread_size': sum(len(t) for t in threads.values()) / len(threads) if threads else 0
        }
        
        logger.info(f"Applied threading: {thread_stats['threads_created']} threads, "
                   f"avg size: {thread_stats['avg_thread_size']:.1f}")
        
        return sorted_interactions
    
    def _extract_explicit_thread_id(self, interaction: Interaction) -> Optional[str]:
        """Extract explicit thread ID from interaction metadata"""
        if not interaction.metadata or 'raw_result' not in interaction.metadata:
            return None
        
        raw_result = interaction.metadata['raw_result']
        
        # Slack thread detection
        if interaction.source == 'slack':
            thread_ts = raw_result.get('thread_ts') or raw_result.get('thread_timestamp')
            if thread_ts:
                return f"slack_{thread_ts}"
        
        # Email thread detection
        elif interaction.source == 'email':
            # Look for In-Reply-To or References headers
            headers = raw_result.get('headers', {})
            in_reply_to = headers.get('In-Reply-To') or headers.get('in-reply-to')
            if in_reply_to:
                return f"email_{in_reply_to}"
            
            # Look for subject line threading (Re: patterns)
            subject = headers.get('Subject') or headers.get('subject') or raw_result.get('subject', '')
            if subject.startswith(('Re:', 'RE:', 'Fw:', 'FW:')):
                # Extract base subject for threading
                base_subject = re.sub(r'^(Re:|RE:|Fw:|FW:)\s*', '', subject).strip()
                return f"email_subject_{base_subject[:50]}"
        
        return None
    
    def _find_related_thread(self, interaction: Interaction, existing_threads: Dict[str, List[Interaction]]) -> Optional[str]:
        """Find existing thread this interaction might belong to"""
        time_window = timedelta(hours=24)  # 24 hour window for related interactions
        
        for thread_id, thread_interactions in existing_threads.items():
            if not thread_interactions:
                continue
                
            latest_in_thread = max(thread_interactions, key=lambda x: x.timestamp)
            
            # Check temporal proximity
            if interaction.timestamp - latest_in_thread.timestamp > time_window:
                continue
            
            # Check if it's a good candidate
            if self._interactions_are_related(interaction, thread_interactions):
                return thread_id
        
        return None
    
    def _interactions_are_related(self, interaction: Interaction, thread_interactions: List[Interaction]) -> bool:
        """Determine if an interaction belongs to an existing thread"""
        if not thread_interactions:
            return False
        
        # Compare against the most recent interaction in thread
        recent_interaction = thread_interactions[-1]
        
        # Same source and channel
        if (interaction.source == recent_interaction.source and 
            interaction.channel == recent_interaction.channel and
            interaction.channel):  # Must have a channel
            return True
        
        # Shared participants (2+ common participants)
        interaction_participants = set(interaction.participants)
        recent_participants = set(recent_interaction.participants)
        common_participants = interaction_participants & recent_participants
        
        if len(common_participants) >= 2:
            return True
        
        # Similar topics (3+ shared keywords)
        interaction_topics = set(interaction.key_topics)
        recent_topics = set(recent_interaction.key_topics)
        common_topics = interaction_topics & recent_topics
        
        if len(common_topics) >= 3:
            return True
        
        # Subject/content similarity for emails
        if interaction.source == 'email' and recent_interaction.source == 'email':
            # Extract potential subject lines from summaries
            interaction_words = set(interaction.summary.lower().split()[:10])
            recent_words = set(recent_interaction.summary.lower().split()[:10])
            common_words = interaction_words & recent_words
            
            if len(common_words) >= 3:
                return True
        
        return False
    
    def get_conversation_threads(self, person_email: str, days: int = 30) -> Dict[str, List[Interaction]]:
        """
        Get conversation threads for a person
        
        Args:
            person_email: Person's email address
            days: Number of days back to analyze
            
        Returns:
            Dict mapping thread_id to list of interactions
        """
        interactions = self.get_person_interactions(person_email, days=days, limit=200)
        
        # Group by thread_id
        threads = {}
        for interaction in interactions:
            thread_id = interaction.thread_id or 'unthreaded'
            if thread_id not in threads:
                threads[thread_id] = []
            threads[thread_id].append(interaction)
        
        # Sort each thread chronologically
        for thread_id in threads:
            threads[thread_id].sort(key=lambda x: x.timestamp)
        
        # Sort threads by most recent interaction
        sorted_threads = {}
        for thread_id in sorted(threads.keys(), 
                              key=lambda t: max(i.timestamp for i in threads[t]), 
                              reverse=True):
            sorted_threads[thread_id] = threads[thread_id]
        
        logger.info(f"Retrieved {len(sorted_threads)} conversation threads for {person_email}")
        
        return sorted_threads
    
    def extract_action_items_from_interactions(self, interactions: List[Interaction], 
                                             person_email: str) -> List[ActionItem]:
        """
        Extract action items from interactions using existing CommitmentExtractor
        
        Args:
            interactions: List of interactions to analyze
            person_email: Email of the person these interactions relate to
            
        Returns:
            List of ActionItem objects
        """
        start_time = datetime.now()
        action_items = []
        
        for interaction in interactions:
            if not interaction.content:
                continue
            
            try:
                # Use existing CommitmentExtractor
                extracted_commitments = self.commitment_extractor.extract_commitments(
                    interaction.content
                )
                
                for commitment in extracted_commitments:
                    # Determine direction based on context
                    direction = self._determine_commitment_direction(
                        commitment, interaction, person_email
                    )
                    
                    # Extract due date if available
                    due_date = self._extract_due_date(commitment.get('text', ''))
                    
                    # Create ActionItem
                    action_item = ActionItem(
                        direction=direction,
                        counterparty=person_email,
                        description=commitment.get('description', commitment.get('text', '')),
                        due_date=due_date,
                        status=ActionStatus.PENDING,
                        priority=self._determine_priority(commitment.get('text', '')),
                        source=interaction.reference,
                        context=interaction.summary,
                        confidence=commitment.get('confidence_score', 0.5),
                        extraction_method="pattern_match",
                        tags=self._generate_commitment_tags(commitment, interaction),
                        metadata={
                            'interaction_id': interaction.id,
                            'extraction_timestamp': datetime.now().isoformat(),
                            'raw_commitment': commitment
                        }
                    )
                    
                    # Only add high-confidence commitments
                    if action_item.confidence > 0.7:
                        action_items.append(action_item)
                        
            except Exception as e:
                logger.error(f"Failed to extract commitments from interaction {interaction.id}: {e}")
                continue
        
        # Update stats
        processing_time = (datetime.now() - start_time).total_seconds()
        self.stats["commitments_extracted"] += len(action_items)
        self.stats["processing_time"] += processing_time
        
        logger.info(f"Extracted {len(action_items)} action items from "
                   f"{len(interactions)} interactions in {processing_time:.2f}s")
        
        return action_items
    
    def _determine_commitment_direction(self, commitment: Dict, 
                                      interaction: Interaction, 
                                      person_email: str) -> ActionDirection:
        """Determine if commitment is I_OWE or THEY_OWE based on context"""
        text = commitment.get('text', '').lower()
        
        # Simple heuristics for direction detection
        i_owe_patterns = [
            "i will", "i'll", "i can", "i should", "i need to", "let me",
            "i'll send", "i'll create", "i'll update", "i'll review"
        ]
        
        they_owe_patterns = [
            "you will", "you'll", "you can", "you should", "you need to",
            "could you", "can you", "please send", "please create", "please update"
        ]
        
        # Check for I_OWE patterns
        if any(pattern in text for pattern in i_owe_patterns):
            return ActionDirection.I_OWE
        
        # Check for THEY_OWE patterns
        if any(pattern in text for pattern in they_owe_patterns):
            return ActionDirection.THEY_OWE
        
        # Default based on interaction author
        # If the person is the author, assume they're committing (I_OWE)
        # If someone else is the author, assume they're asking person to do something (THEY_OWE)
        if interaction.metadata and interaction.metadata.get('raw_result'):
            author = interaction.metadata['raw_result'].get('author', '')
            if author and author.lower() == person_email.lower():
                return ActionDirection.I_OWE
            else:
                return ActionDirection.THEY_OWE
        
        # Default fallback
        return ActionDirection.I_OWE
    
    def _extract_due_date(self, text: str) -> Optional[datetime]:
        """Extract due date from text using simple patterns"""
        
        # Look for date patterns
        date_patterns = [
            r'by\s+(\w+day)',  # by Friday
            r'due\s+(\w+day)',  # due Monday
            r'before\s+(\w+day)',  # before Tuesday
            r'by\s+(\d{1,2}/\d{1,2})',  # by 12/25
            r'due\s+(\d{1,2}/\d{1,2})',  # due 12/25
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text.lower())
            if match:
                try:
                    # Simple date parsing (could be enhanced)
                    date_str = match.group(1)
                    
                    # Handle weekdays
                    weekdays = {
                        'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
                        'friday': 4, 'saturday': 5, 'sunday': 6
                    }
                    
                    if date_str in weekdays:
                        # Find next occurrence of this weekday
                        today = date.today()
                        target_weekday = weekdays[date_str]
                        days_ahead = target_weekday - today.weekday()
                        if days_ahead <= 0:  # Target day already happened this week
                            days_ahead += 7
                        target_date = today + timedelta(days=days_ahead)
                        return datetime.combine(target_date, datetime.min.time())
                    
                    # Handle MM/DD format (assumes current year)
                    if '/' in date_str:
                        month, day = map(int, date_str.split('/'))
                        year = datetime.now().year
                        return datetime(year, month, day)
                        
                except Exception:
                    continue
        
        return None
    
    def _determine_priority(self, text: str) -> str:
        """Determine priority based on text content"""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ['urgent', 'asap', 'immediately', 'critical']):
            return "urgent"
        elif any(word in text_lower for word in ['important', 'priority', 'soon']):
            return "high"
        elif any(word in text_lower for word in ['when you can', 'no rush', 'eventually']):
            return "low"
        else:
            return "medium"
    
    def _generate_commitment_tags(self, commitment: Dict, interaction: Interaction) -> List[str]:
        """Generate tags for a commitment based on context"""
        tags = []
        
        # Add source tag
        tags.append(f"source:{interaction.source}")
        
        # Add interaction type tag
        tags.append(f"type:{interaction.interaction_type.value}")
        
        # Add confidence tag
        confidence = commitment.get('confidence_score', 0)
        if confidence > 0.9:
            tags.append("high_confidence")
        elif confidence > 0.7:
            tags.append("medium_confidence")
        else:
            tags.append("low_confidence")
        
        # Add topic tags from interaction
        if interaction.key_topics:
            tags.extend([f"topic:{topic}" for topic in interaction.key_topics[:3]])
        
        return tags
    
    def sync_interactions_to_crm(self, person_email: str, days: int = 30) -> Dict[str, int]:
        """
        Sync person's interactions and action items to CRM
        
        Args:
            person_email: Person's email address  
            days: Number of days back to sync
            
        Returns:
            Dict with sync statistics
        """
        start_time = datetime.now()
        
        # Get interactions
        interactions = self.get_person_interactions(person_email, days=days)
        
        # Extract action items
        action_items = self.extract_action_items_from_interactions(interactions, person_email)
        
        # Store in CRM database
        interactions_stored = 0
        actions_stored = 0
        
        for interaction in interactions:
            try:
                # Store interaction using new CRMDirectory method
                if self.crm.store_interaction(interaction):
                    interactions_stored += 1
            except Exception as e:
                logger.error(f"Failed to store interaction: {e}")
        
        for action_item in action_items:
            try:
                if self.crm.add_action_item(action_item):
                    actions_stored += 1
            except Exception as e:
                logger.error(f"Failed to store action item: {e}")
        
        # Update person's last interaction timestamp
        if interactions:
            try:
                person = self.crm.get_person_by_email(person_email)
                if person:
                    person.last_interaction = interactions[0].timestamp  # Most recent
                    person.interaction_count += interactions_stored
                    self.crm.add_or_update_person(person, author="sync_interactions")
            except Exception as e:
                logger.error(f"Failed to update person interaction metadata: {e}")
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        sync_stats = {
            "person_email": person_email,
            "days_synced": days,
            "interactions_found": len(interactions),
            "interactions_stored": interactions_stored,
            "action_items_extracted": len(action_items),
            "action_items_stored": actions_stored,
            "processing_time": processing_time,
            "sources_queried": len(set(i.source for i in interactions))
        }
        
        logger.info(f"Synced {interactions_stored} interactions and {actions_stored} "
                   f"action items for {person_email} in {processing_time:.2f}s")
        
        return sync_stats
    
    def analyze_relationship_health(self, person_email: str, days: int = 90) -> Dict[str, Any]:
        """
        Analyze relationship health over time using sentiment analysis
        
        Args:
            person_email: Person's email address
            days: Number of days back to analyze
            
        Returns:
            Dict with comprehensive relationship health analysis
        """
        # Get interactions with sentiment data
        interactions = self.get_person_interactions(person_email, days=days, limit=200)
        
        if not interactions:
            return {
                'person_email': person_email,
                'health_status': 'no_data',
                'insights': ['No interaction data available for analysis'],
                'metrics': {}
            }
        
        # Extract sentiment analyses
        sentiment_history = []
        for interaction in interactions:
            if (interaction.metadata and 
                interaction.metadata.get('sentiment_analysis')):
                # Reconstruct SentimentAnalysis from dict
                sentiment_data = interaction.metadata['sentiment_analysis']
                from .sentiment_analyzer import SentimentAnalysis, SentimentScore
                
                sentiment_analysis = SentimentAnalysis(
                    score=sentiment_data['score'],
                    confidence=sentiment_data['confidence'],
                    category=SentimentScore(sentiment_data['category']),
                    indicators=sentiment_data['indicators'],
                    relationship_signals=sentiment_data['relationship_signals'],
                    metadata=sentiment_data['metadata']
                )
                sentiment_history.append(sentiment_analysis)
        
        if not sentiment_history:
            return {
                'person_email': person_email,
                'health_status': 'insufficient_sentiment_data',
                'insights': ['Interactions found but lack sentiment analysis'],
                'metrics': {}
            }
        
        # Analyze trends
        trend_analysis = self.sentiment_analyzer.analyze_relationship_trend(
            sentiment_history, time_window_days=days
        )
        
        # Get relationship insights
        insights = self.sentiment_analyzer.get_relationship_insights(sentiment_history)
        
        # Calculate additional metrics
        total_interactions = len(interactions)
        avg_sentiment = sum(s.score for s in sentiment_history) / len(sentiment_history)
        sentiment_volatility = self._calculate_sentiment_volatility(sentiment_history)
        
        # Categorize interactions by source
        source_breakdown = {}
        for interaction in interactions:
            source = interaction.source
            if source not in source_breakdown:
                source_breakdown[source] = {'count': 0, 'avg_sentiment': 0.0}
            source_breakdown[source]['count'] += 1
        
        # Calculate average sentiment by source
        for source in source_breakdown:
            source_interactions = [i for i in interactions if i.source == source]
            source_sentiments = [
                i.sentiment_score for i in source_interactions 
                if i.sentiment_score is not None
            ]
            if source_sentiments:
                source_breakdown[source]['avg_sentiment'] = sum(source_sentiments) / len(source_sentiments)
        
        return {
            'person_email': person_email,
            'analysis_period_days': days,
            'health_status': trend_analysis['relationship_health'],
            'trend': trend_analysis,
            'insights': insights,
            'metrics': {
                'total_interactions': total_interactions,
                'sentiment_data_points': len(sentiment_history),
                'avg_sentiment': avg_sentiment,
                'sentiment_volatility': sentiment_volatility,
                'source_breakdown': source_breakdown,
                'analysis_timestamp': datetime.now().isoformat()
            }
        }
    
    def _calculate_sentiment_volatility(self, sentiment_history: List) -> float:
        """Calculate sentiment volatility (standard deviation)"""
        if len(sentiment_history) < 2:
            return 0.0
        
        scores = [s.score for s in sentiment_history]
        mean = sum(scores) / len(scores)
        variance = sum((score - mean) ** 2 for score in scores) / len(scores)
        return variance ** 0.5
    
    def get_stats(self) -> Dict[str, Any]:
        """Get interaction manager statistics"""
        return {
            **self.stats,
            "search_db_path": self.search_db.db_path,
            "crm_db_path": self.crm.db_path,
            "crm_people_count": self.crm.count_people()
        }