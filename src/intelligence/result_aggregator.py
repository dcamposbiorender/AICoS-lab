"""
Result aggregation and intelligence processing
Combines multi-source search results into coherent, intelligent responses
References: Team A search results format, NLP techniques for text processing
"""

import re
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from collections import defaultdict, Counter
import difflib

logger = logging.getLogger(__name__)

@dataclass 
class AggregatedResult:
    """Intelligent aggregated result from multiple sources"""
    results: List[Dict[str, Any]] = field(default_factory=list)
    total_sources: int = 0
    source_breakdown: Dict[str, int] = field(default_factory=dict)
    timeline: List[Dict[str, Any]] = field(default_factory=list)
    commitments: List[Dict[str, Any]] = field(default_factory=list)
    context_summary: str = ""
    key_people: List[str] = field(default_factory=list)
    key_topics: List[str] = field(default_factory=list)
    confidence_score: float = 0.0
    duplicates_removed: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class ResultAggregator:
    """
    Intelligent result aggregation with context building
    
    Features:
    - Multi-source result merging
    - Relevance-based ranking  
    - Timeline extraction
    - Commitment and action item detection
    - Context summarization
    - Duplicate detection and removal
    - Key entity extraction
    """
    
    def __init__(self):
        """Initialize aggregator with intelligence patterns"""
        
        # Commitment detection patterns
        self.commitment_patterns = [
            r'\b(I will|I\'ll|I am going to|I plan to)\s+([^.!?]+)',
            r'\b(\w+)\s+(agreed to|promised to|committed to)\s+([^.!?]+)',
            r'\b(will|shall)\s+([^.!?]+?)\s+by\s+(\w+day|\d+)',
            r'\b(responsible for|assigned to|taking care of)\s+([^.!?]+)',
            r'\b(deadline|due date|delivery)\s+([^.!?]+)'
        ]
        
        # Action item patterns
        self.action_patterns = [
            r'\b(TODO|FIXME|ACTION|TASK):\s*([^.!?\n]+)',
            r'\b(need to|have to|must|should)\s+([^.!?]+)',
            r'\b(follow up|check on|review)\s+([^.!?]+)'
        ]
        
        # Person mention patterns
        self.person_patterns = [
            r'@(\w+)',  # @mentions
            r'\b([A-Z][a-z]+)\s+(said|mentioned|wrote|sent)',
            r'\b(from|by|with|to)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)'
        ]
        
        # Time expressions
        self.time_expressions = [
            r'\b(today|tomorrow|yesterday)\b',
            r'\b(this|next|last)\s+(week|month|year|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',
            r'\b(by|before|after)\s+(friday|monday|tuesday|wednesday|thursday|saturday|sunday)\b',
            r'\b(\d{1,2}/\d{1,2}|\d{4}-\d{2}-\d{2})\b'
        ]
    
    def aggregate(self, source_results: Dict[str, List[Dict]], 
                  query: str, max_results: int = 50, 
                  strategy: str = "relevance") -> AggregatedResult:
        """
        Aggregate results from multiple sources with intelligence
        
        Args:
            source_results: Dict mapping source names to result lists
            query: Original query for context
            max_results: Maximum results to include
            strategy: Aggregation strategy ('relevance', 'chronological', 'source_grouped')
            
        Returns:
            AggregatedResult with intelligence processing
        """
        if not source_results:
            return AggregatedResult(
                context_summary=f"No results found for '{query}'",
                confidence_score=0.0
            )
        
        # Flatten and deduplicate results
        all_results = []
        source_counts = {}
        
        for source, results in source_results.items():
            source_counts[source] = len(results)
            for result in results:
                result['_source'] = source  # Tag with source
                all_results.append(result)
        
        # Remove duplicates
        unique_results, duplicates_removed = self._remove_duplicates(all_results)
        
        # Apply aggregation strategy
        if strategy == "chronological":
            ranked_results = self._rank_chronologically(unique_results)
        elif strategy == "source_grouped":
            ranked_results = self._rank_by_source_groups(unique_results, query)
        else:  # Default: relevance
            ranked_results = self._rank_by_relevance(unique_results, query)
        
        # Limit results
        limited_results = ranked_results[:max_results]
        
        # Build aggregated result
        aggregated = AggregatedResult(
            results=limited_results,
            total_sources=len(source_results),
            source_breakdown=source_counts,
            duplicates_removed=duplicates_removed
        )
        
        # Add intelligence processing
        aggregated.timeline = self._extract_timeline(limited_results)
        aggregated.commitments = self._extract_commitments(limited_results)
        aggregated.key_people = self._extract_key_people(limited_results)
        aggregated.key_topics = self._extract_key_topics(limited_results, query)
        aggregated.context_summary = self._generate_context_summary(limited_results, query)
        aggregated.confidence_score = self._calculate_confidence(aggregated)
        
        return aggregated
    
    def _remove_duplicates(self, results: List[Dict]) -> Tuple[List[Dict], int]:
        """Remove duplicate or highly similar results, but only within same source"""
        if not results:
            return [], 0
            
        unique_results = []
        duplicates_removed = 0
        
        for result in results:
            content = result.get('content', '')
            source = result.get('source', '')
            is_duplicate = False
            
            # Check against existing results for similarity (within same source only)
            for i, existing in enumerate(unique_results):
                # Only compare within same source to avoid removing legitimate cross-source results
                if existing.get('source', '') != source:
                    continue
                    
                existing_content = existing.get('content', '')
                similarity = self._calculate_similarity(content, existing_content)
                
                if similarity >= 0.95:  # Very restrictive similarity threshold - only exact duplicates
                    is_duplicate = True
                    # Keep the one with higher relevance score
                    if result.get('relevance_score', 0) > existing.get('relevance_score', 0):
                        # Replace existing with current
                        unique_results[i] = result
                    duplicates_removed += 1
                    break
            
            if not is_duplicate:
                unique_results.append(result)
        
        return unique_results, duplicates_removed
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two text strings"""
        if not text1 or not text2:
            return 0.0
        
        # Use difflib for simple similarity
        similarity = difflib.SequenceMatcher(None, text1.lower(), text2.lower()).ratio()
        return similarity
    
    def _rank_by_relevance(self, results: List[Dict], query: str) -> List[Dict]:
        """Rank results by relevance score and query match"""
        
        def relevance_key(result):
            base_score = result.get('relevance_score', 0)
            
            # Boost for exact query matches
            content = result.get('content', '').lower()
            query_boost = 0
            for word in query.lower().split():
                if word in content:
                    query_boost += 0.25  # Significant boost for query matches
            
            # Boost for recency
            date_str = result.get('date', '')
            recency_boost = self._calculate_recency_boost(date_str)
            
            return base_score + query_boost + recency_boost
        
        # Sort and update relevance_score to reflect actual ranking
        sorted_results = sorted(results, key=relevance_key, reverse=True)
        
        # Update relevance_score field to reflect actual calculated relevance
        for result in sorted_results:
            result['relevance_score'] = relevance_key(result)
            
        return sorted_results
    
    def _rank_chronologically(self, results: List[Dict]) -> List[Dict]:
        """Rank results chronologically (oldest first for timeline view)"""
        def date_key(result):
            date_str = result.get('date', '')
            if not date_str:
                return datetime.min
            try:
                return datetime.fromisoformat(date_str.split('T')[0])
            except (ValueError, AttributeError):
                return datetime.min
        
        return sorted(results, key=date_key)  # Oldest first for timeline
    
    def _rank_by_source_groups(self, results: List[Dict], query: str) -> List[Dict]:
        """Group results by source, then rank within groups"""
        grouped = defaultdict(list)
        
        # Group by source
        for result in results:
            source = result.get('source', 'unknown')
            grouped[source].append(result)
        
        # Rank within each group and combine
        final_results = []
        for source in sorted(grouped.keys()):  # Alphabetical source order
            group_results = self._rank_by_relevance(grouped[source], query)
            final_results.extend(group_results)
        
        return final_results
    
    def _calculate_recency_boost(self, date_str: str) -> float:
        """Calculate boost based on result recency"""
        if not date_str:
            return 0.0
        
        try:
            result_date = datetime.fromisoformat(date_str.split('T')[0])
            days_old = (datetime.now() - result_date).days
            
            # Boost recent results
            if days_old <= 1:
                return 0.3  # Strong boost for very recent
            elif days_old <= 7:
                return 0.15
            elif days_old <= 30:
                return 0.05
            else:
                return 0.0
                
        except (ValueError, AttributeError):
            return 0.0
    
    def _extract_timeline(self, results: List[Dict]) -> List[Dict]:
        """Extract chronological timeline from results"""
        timeline_events = []
        
        for result in results:
            date_str = result.get('date', '')
            if date_str:
                try:
                    parsed_date = datetime.fromisoformat(date_str.split('T')[0])
                    timeline_events.append({
                        'date': date_str,
                        'parsed_date': parsed_date,
                        'content': result.get('content', ''),
                        'source': result.get('source', ''),
                        'metadata': result.get('metadata', {})
                    })
                except ValueError:
                    continue
        
        # Sort chronologically
        timeline_events.sort(key=lambda x: x['parsed_date'])
        
        # Remove parsed_date for clean output
        for event in timeline_events:
            del event['parsed_date']
        
        return timeline_events
    
    def _extract_commitments(self, results: List[Dict]) -> List[Dict]:
        """Extract commitments and action items from results"""
        commitments = []
        
        for result in results:
            content = result.get('content', '')
            
            # Check commitment patterns
            for pattern in self.commitment_patterns:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    # Safely extract commitment text
                    groups = match.groups()
                    commitment_text = groups[-1] if groups else match.group(0)
                    
                    commitment = {
                        'text': match.group(0),
                        'person': self._extract_person_from_match(match, result),
                        'commitment': commitment_text,
                        'source': result.get('source', ''),
                        'date': result.get('date', ''),
                        'confidence': 0.8
                    }
                    commitments.append(commitment)
            
            # Check action patterns
            for pattern in self.action_patterns:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    # Safely extract commitment text
                    groups = match.groups()
                    commitment_text = groups[-1] if groups else match.group(0)
                    
                    commitment = {
                        'text': match.group(0),
                        'person': result.get('metadata', {}).get('user', 'Unknown'),
                        'commitment': commitment_text,
                        'source': result.get('source', ''),
                        'date': result.get('date', ''),
                        'confidence': 0.6  # Lower confidence for general actions
                    }
                    commitments.append(commitment)
        
        return commitments
    
    def _extract_person_from_match(self, match, result) -> str:
        """Extract person name from regex match or result metadata"""
        # Try to get from match groups
        groups = match.groups()
        for group in groups:
            if group and re.match(r'^[A-Z][a-z]+$', group):
                return group
        
        # Fall back to result metadata
        return result.get('metadata', {}).get('user', 'Unknown')
    
    def _extract_key_people(self, results: List[Dict]) -> List[str]:
        """Extract key people mentioned across results"""
        people = set()
        
        for result in results:
            content = result.get('content', '')
            metadata = result.get('metadata', {})
            
            # From metadata
            if 'user' in metadata:
                people.add(metadata['user'])
            if 'attendees' in metadata:
                people.update(metadata['attendees'])
            
            # From content using patterns
            for pattern in self.person_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches:
                    if isinstance(match, tuple):
                        for name in match:
                            if name and self._is_person_name(name):
                                people.add(name)
                    elif self._is_person_name(match):
                        people.add(match)
        
        # Return most mentioned people (limit to top 10)
        return list(people)[:10]
    
    def _extract_key_topics(self, results: List[Dict], query: str) -> List[str]:
        """Extract key topics and concepts from results"""
        word_counts = Counter()
        
        # Collect all content
        all_content = []
        for result in results:
            content = result.get('content', '')
            all_content.append(content.lower())
        
        combined_content = ' '.join(all_content)
        
        # Extract meaningful terms (simple approach)
        # Filter out common stop words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 
                     'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were',
                     'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did',
                     'will', 'would', 'could', 'should', 'may', 'might', 'must'}
        
        words = re.findall(r'\b[a-zA-Z]{3,}\b', combined_content)
        meaningful_words = [word for word in words if word.lower() not in stop_words]
        
        word_counts.update(meaningful_words)
        
        # Get top terms, excluding query terms
        query_words = set(query.lower().split())
        top_topics = []
        
        for word, count in word_counts.most_common(20):
            if word.lower() not in query_words and len(word) > 3:
                top_topics.append(word)
        
        return top_topics[:10]
    
    def _generate_context_summary(self, results: List[Dict], query: str) -> str:
        """Generate intelligent context summary from results"""
        if not results:
            return f"No results found for '{query}'"
        
        # Extract key information
        total_results = len(results)
        sources = set(r.get('source', '') for r in results)
        date_range = self._get_date_range(results)
        
        # Start building summary
        summary_parts = []
        
        # Opening statement
        summary_parts.append(f"Found {total_results} results about '{query}'")
        
        if len(sources) > 1:
            source_list = ', '.join(sorted(sources))
            summary_parts.append(f"across {source_list}")
        
        if date_range:
            summary_parts.append(f"from {date_range}")
        
        # Add key insights
        insights = self._extract_key_insights(results, query)
        if insights:
            summary_parts.append("Key insights:")
            summary_parts.extend(insights)
        
        return '. '.join(summary_parts) + '.'
    
    def _get_date_range(self, results: List[Dict]) -> Optional[str]:
        """Get human-readable date range from results"""
        dates = []
        
        for result in results:
            date_str = result.get('date', '')
            if date_str:
                try:
                    parsed_date = datetime.fromisoformat(date_str.split('T')[0])
                    dates.append(parsed_date)
                except ValueError:
                    continue
        
        if not dates:
            return None
        
        dates.sort()
        earliest = dates[0]
        latest = dates[-1]
        
        # Format based on range
        if earliest == latest:
            return earliest.strftime('%B %d')
        elif (latest - earliest).days <= 7:
            return f"{earliest.strftime('%B %d')} to {latest.strftime('%B %d')}"
        else:
            return f"{earliest.strftime('%B %d')} to {latest.strftime('%B %d, %Y')}"
    
    def _extract_key_insights(self, results: List[Dict], query: str) -> List[str]:
        """Extract key insights and patterns from results"""
        insights = []
        
        # Look for specific keywords in content
        all_content = ' '.join(r.get('content', '') for r in results).lower()
        
        # Extract important keywords that might be missing from summary
        important_keywords = ['deadline', 'friday', 'monday', 'tuesday', 'wednesday', 'thursday', 
                             'saturday', 'sunday', 'due', 'complete', 'finish', 'delivery']
        found_keywords = [kw for kw in important_keywords if kw in all_content]
        
        # Most recent result
        if results:
            recent = results[0]  # Already sorted by relevance/recency
            insights.append(f"Most recent: {recent.get('content', '')[:100]}...")
        
        # Important keywords found
        if found_keywords:
            insights.append(f"Key terms mentioned: {', '.join(found_keywords[:3]).title()}")
        
        # Commitment count
        commitments = self._extract_commitments(results)
        if commitments:
            insights.append(f"Found {len(commitments)} commitments or action items")
        
        # Source distribution
        source_counts = Counter(r.get('source', '') for r in results)
        if len(source_counts) > 1:
            dominant_source = source_counts.most_common(1)[0]
            insights.append(f"Most results from {dominant_source[0]} ({dominant_source[1]} items)")
        
        return insights[:4]  # Limit to top 4 insights
    
    def _calculate_confidence(self, aggregated: AggregatedResult) -> float:
        """Calculate overall confidence in the aggregated result"""
        confidence = 0.0
        
        # Base confidence on number of results
        if aggregated.results:
            confidence += min(0.4, len(aggregated.results) * 0.1)
        
        # Boost for multiple sources
        if aggregated.total_sources > 1:
            confidence += 0.2
        
        # Boost for commitments found
        if aggregated.commitments:
            confidence += 0.1
        
        # Boost for timeline coherence
        if len(aggregated.timeline) > 1:
            confidence += 0.1
        
        # Boost for key people identified
        if aggregated.key_people:
            confidence += 0.1
        
        # Penalty for many duplicates removed
        if aggregated.duplicates_removed > len(aggregated.results) * 0.5:
            confidence -= 0.2
        
        return min(1.0, max(0.0, confidence))
    
    def _is_person_name(self, name: str) -> bool:
        """Check if a string is likely a person name"""
        if not name or len(name) < 2:
            return False
        
        # Basic pattern: starts with capital, contains only letters
        if not re.match(r'^[A-Z][a-z]+$', name):
            return False
        
        # Filter out common false positives
        false_positives = {
            'Friday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Saturday', 'Sunday',
            'January', 'February', 'March', 'April', 'May', 'June', 'July', 'August',
            'September', 'October', 'November', 'December', 'Today', 'Tomorrow', 'Yesterday'
        }
        
        return name not in false_positives