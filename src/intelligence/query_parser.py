"""
Natural Language Query Parser for AI Chief of Staff
Transforms natural language queries into structured search parameters
References: Team A search infrastructure for query execution
"""

import re
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class NLQueryParser:
    """
    Natural language query parser with intent recognition
    Supports 9 query intent types for comprehensive query understanding
    """
    
    def __init__(self):
        """Initialize parser with patterns and mappings"""
        
        # Intent recognition patterns for 9 intent types
        self.intent_patterns = {
            'SEARCH_MESSAGES': [
                r'\b(messages?|chat|discussion|conversation|slack)\b',
                r'\b(said|mentioned|talked about|discussed)\b',
                r'\bwhat did.*\b(say|mention|talk|discuss)\b',
                r'\b(dm|direct message|channel)\b'
            ],
            'FIND_COMMITMENTS': [
                r'\b(promise|commit|deliver)\b',  # Removed "deadline" and "due" from general match
                r'\b(action item|action items|todo|task|responsibility)\b',
                r'\b(will|going to|agreed to)\b.*\b(by|before)\b',
                r'\bwho.*\b(committed|promised|agreed)\b',
                r'\bwhat.*\b(deadlines?|commitments?)\b',
                r'\b[A-Z][a-z]+\'?s?\s+(commitments?|deadlines?|tasks?)\b',  # "Alice's commitments"
                r'\b(deadline|due)\b.*\b(by|before|this|next)\b',  # Only deadline with time context
                r'\bwhat.*\b(deadline|due)\b'  # "What deadline" patterns
            ],
            'BUILD_CONTEXT': [
                r'\b(context|background|summary|overview)\b',
                r'\b(what.*about|tell me about|explain|give me)\b.*\b(context|background|overview)\b',
                r'\b(history|timeline|development)\b'
            ],
            'MULTI_SOURCE_SEARCH': [
                r'\b(calendar|meetings?|events?)\b.*\b(and|both)\b.*\b(slack|messages?|discussions?)\b',
                r'\b(slack|messages?|discussions?)\b.*\b(and|both)\b.*\b(calendar|meetings?|events?)\b',
                r'\b(files?|documents?)\b.*\b(and|both)\b.*\b(messages?|slack)\b',
                r'\b(messages?|slack)\b.*\b(and|both)\b.*\b(files?|documents?)\b',
                r'\b(meetings?|events?)\b.*\b(and|both)\b.*\b(documents?|files?)\b'
            ],
            'CLARIFICATION_NEEDED': [
                r'^(what\'s going on\??|help me|what\'s happening\??)$',
                r'^.{1,5}$',  # Very short queries
                r'^\s*(help)\s*\??$'  # Single word queries only for help
            ],
            'SHOW_STATISTICS': [
                r'\b(how many|count|total|statistics|stats|numbers?)\b',
                r'\b(activity level|frequency|volume)\b',
                r'\b(report|metrics|analytics)\b'
            ],
            'TIME_RANGE_QUERY': [
                r'\b(everything|all)\b.*\b(from|since|during|between)\b.*\b(month|year|quarter)\b',
                r'\b(show|find|get)\b.*\b(everything)\b.*\b(last|this|past)\b.*\b(month|year|quarter)\b',
                r'\b(timeline|chronological|over time)\b'
            ],
            'PERSON_ACTIVITY': [
                r'\bwhat.*\b(alice|bob|charlie|david|eve|john|jane)\b.*\b(doing|up to|working|been)\b',
                r'\b(alice|bob|charlie|david|eve|john|jane)\b.*\b(been|working|activity|updates)\b',
                r'\b(activity|updates|progress)\b.*\b(from|by)\b.*\b[A-Z][a-z]+\b'
            ],
            'TRENDING_TOPICS': [
                r'\b(trending|hot topics?|popular|buzz)\b',
                r'\bwhat.*\b(talking about|trending|popular)\b',
                r'\b(themes?|topics?|subjects?)\b.*\b(trending|popular|common)\b'
            ]
        }
        
        # Source mapping patterns
        self.source_patterns = {
            'slack': [r'\b(message|chat|slack|dm|channel)\b'],
            'calendar': [r'\b(meeting|event|calendar|scheduled)\b'],
            'drive': [r'\b(file|document|drive|folder)\b'],
            'employees': [r'\b(person|people|team|staff|employee)\b']
        }
        
        # Time period patterns
        self.time_patterns = {
            'today': r'\b(today|this morning|this afternoon)\b',
            'yesterday': r'\b(yesterday)\b',
            'last_week': r'\b(last week|past week)\b',
            'last_month': r'\b(last month|past month)\b',
            'this_week': r'\b(this week|current week)\b',
            'this_month': r'\b(this month|current month)\b',
            'by_friday': r'\b(by friday|before friday|friday deadline)\b',
            'by_end_of_week': r'\b(by.*end.*week|before weekend)\b'
        }
        
        # Common query expansions
        self.expansions = {
            'bug': ['bug', 'issue', 'defect', 'problem', 'error', 'crash'],
            'meeting': ['meeting', 'call', 'discussion', 'standup', 'sync'],
            'project': ['project', 'initiative', 'effort', 'work'],
            'deadline': ['deadline', 'due date', 'delivery', 'milestone'],
            'update': ['update', 'status', 'progress', 'report']
        }
        
        # Person name normalization patterns
        self.name_patterns = {
            'common_variations': {
                'john': ['john', 'johnny', 'jon'],
                'michael': ['michael', 'mike', 'mick'],
                'william': ['william', 'will', 'bill', 'billy'],
                'robert': ['robert', 'rob', 'bob', 'bobby'],
                'james': ['james', 'jim', 'jimmy'],
                'richard': ['richard', 'rick', 'rich', 'dick'],
                'alice': ['alice', 'ali', 'allie'],
                'bob': ['bob', 'robert', 'bobby'],
                'charlie': ['charlie', 'charles', 'chuck'],
                'dave': ['dave', 'david', 'davy'],
                'eve': ['eve', 'evelyn', 'eva']
            }
        }
    
    def parse(self, query: str) -> Dict[str, Any]:
        """
        Parse natural language query into structured format
        
        Args:
            query: Natural language query string
            
        Returns:
            Dictionary with extracted information including:
            - original_query: Original query string
            - intent: Detected query intent type
            - keywords: Extracted meaningful keywords
            - sources: Data sources to search
            - time_filter: Time-based filter if detected
            - person_filter: Person name if detected
            - person_variants: Name variations for better matching
            - response_type: Type of response expected
            - confidence: Confidence score (0-1)
            - clarification_options: Options if clarification needed
            - metadata: Additional metadata
        """
        if not query or not query.strip():
            return self._create_clarification_result(query or "")
        
        query_lower = query.lower().strip()
        
        parsed = {
            'original_query': query,
            'intent': self._detect_intent(query_lower),
            'keywords': self._extract_keywords(query_lower),
            'sources': self._detect_sources(query_lower),
            'time_filter': self._extract_time_filter(query_lower),
            'person_filter': self._extract_person_filter(query),
            'person_variants': [],
            'response_type': "search_results",
            'confidence': 0.0,
            'clarification_options': [],
            'metadata': {}
        }
        
        # Set person variants if person detected
        if parsed['person_filter']:
            parsed['person_variants'] = self._get_name_variants(parsed['person_filter'])
        
        # Expand keywords for better matching
        parsed['keywords'] = self._expand_keywords(parsed['keywords'])
        
        # Set response type based on intent
        parsed['response_type'] = self._determine_response_type(parsed['intent'])
        
        # Calculate confidence score
        parsed['confidence'] = self._calculate_confidence(parsed, query_lower)
        
        # Add clarification options if needed
        if parsed['intent'] == 'CLARIFICATION_NEEDED':
            parsed['clarification_options'] = self._generate_clarifications(query_lower)
        
        return parsed
    
    def _detect_intent(self, query: str) -> str:
        """Detect the primary intent of the query"""
        scores = {}
        
        for intent, patterns in self.intent_patterns.items():
            score = 0
            for pattern in patterns:
                if re.search(pattern, query, re.IGNORECASE):
                    score += 1
            
            # Give bonus scores for high-priority intents
            if intent == 'MULTI_SOURCE_SEARCH' and score > 0:
                score += 0.5  # Boost multi-source when it matches
            if intent == 'SHOW_STATISTICS' and score > 0:
                score += 0.5  # Boost statistics when it matches
            
            scores[intent] = score
        
        # Special handling for clarification needed
        if not any(scores.values()) or len(query.strip()) <= 3:
            return 'CLARIFICATION_NEEDED'
        
        # Return intent with highest score
        max_intent = max(scores, key=scores.get)
        
        # If score is very low, request clarification
        if scores[max_intent] == 0:
            return 'CLARIFICATION_NEEDED'
            
        return max_intent
    
    def _extract_keywords(self, query: str) -> List[str]:
        """Extract meaningful keywords from query"""
        # Remove common stop words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 
            'by', 'about', 'what', 'when', 'where', 'who', 'why', 'how', 'find', 'show', 'get', 
            'give', 'me', 'all', 'any', 'some', 'from', 'is', 'was', 'are', 'were', 'be', 'been',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'can'
        }
        
        # Basic keyword extraction
        words = re.findall(r'\b[a-zA-Z]{2,}\b', query.lower())
        keywords = [word for word in words if word not in stop_words]
        
        # Extract quoted phrases
        quoted_phrases = re.findall(r'"([^"]*)"', query)
        keywords.extend(quoted_phrases)
        
        # Extract multi-word concepts
        concepts = self._extract_concepts(query)
        keywords.extend(concepts)
        
        return list(set(keywords))  # Remove duplicates
    
    def _extract_concepts(self, query: str) -> List[str]:
        """Extract multi-word concepts and phrases"""
        concepts = []
        
        # Common multi-word patterns
        patterns = [
            r'\b([A-Z][a-z]+ [A-Z][a-z]+)\b',  # Proper nouns like "John Smith"
            r'\b(\w+ project)\b',
            r'\b(\w+ system)\b',
            r'\b(\w+ meeting)\b',
            r'\b(\w+ deadline)\b',
            r'\b(\w+ update)\b',
            r'\b(Q[1-4] \w+)\b'  # Quarter references
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            concepts.extend([match.lower() for match in matches])
        
        return concepts
    
    def _detect_sources(self, query: str) -> List[str]:
        """Detect which data sources to search"""
        sources = []
        
        for source, patterns in self.source_patterns.items():
            for pattern in patterns:
                if re.search(pattern, query, re.IGNORECASE):
                    sources.append(source)
                    break
        
        # Default to all sources if none specified, unless intent is specific
        if not sources:
            sources = ['slack', 'calendar', 'drive']
        
        return list(set(sources))
    
    def _extract_time_filter(self, query: str) -> Optional[str]:
        """Extract time-based filters from query"""
        for time_key, pattern in self.time_patterns.items():
            if re.search(pattern, query, re.IGNORECASE):
                return time_key
        
        return None
    
    def _extract_person_filter(self, query: str) -> Optional[str]:
        """Extract person names from query"""
        # Look for common person reference patterns
        patterns = [
            r'\bwhat did\s+([A-Z][a-z]+)\s+',
            r'\b([A-Z][a-z]+)\s+(promise|commit|deliver|said|mentioned|wrote|sent)\b',
            r'\b(from|by|with|to)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b',
            r'\b(Alice|Bob|Charlie|Dave|Eve|Frank|Grace|Harry|John|Jane|Mike|Sarah)\b'  # Common names
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query)
            if match:
                if len(match.groups()) > 1:
                    # Check which group contains the name
                    name = match.group(1) if match.group(1)[0].isupper() else match.group(2)
                    return name.strip()
                else:
                    return match.group(1).strip()
        
        return None
    
    def _get_name_variants(self, name: str) -> List[str]:
        """Get common variants of a person's name"""
        name_lower = name.lower()
        variants = [name, name_lower, name.title()]
        
        # Add common nickname variants
        first_name = name.split()[0].lower()
        if first_name in self.name_patterns['common_variations']:
            common_variants = self.name_patterns['common_variations'][first_name]
            variants.extend(common_variants)
            # Also add title case versions
            variants.extend([v.title() for v in common_variants])
        
        return list(set(variants))
    
    def _expand_keywords(self, keywords: List[str]) -> List[str]:
        """Expand keywords with synonyms and related terms"""
        expanded = keywords.copy()
        
        for keyword in keywords:
            if keyword in self.expansions:
                expanded.extend(self.expansions[keyword])
        
        return list(set(expanded))
    
    def _determine_response_type(self, intent: str) -> str:
        """Determine the type of response to provide"""
        response_mapping = {
            'SEARCH_MESSAGES': "search_results",
            'FIND_COMMITMENTS': "commitment_summary",
            'BUILD_CONTEXT': "context_summary",
            'MULTI_SOURCE_SEARCH': "search_results",
            'CLARIFICATION_NEEDED': "clarification",
            'SHOW_STATISTICS': "statistics_summary",
            'TIME_RANGE_QUERY': "timeline_summary",
            'PERSON_ACTIVITY': "person_summary",
            'TRENDING_TOPICS': "trending_summary"
        }
        
        return response_mapping.get(intent, "search_results")
    
    def _calculate_confidence(self, parsed: Dict[str, Any], query: str) -> float:
        """Calculate confidence score for the parsing"""
        confidence = 0.0
        
        # Base confidence on intent detection
        if parsed['intent'] != 'CLARIFICATION_NEEDED':
            confidence += 0.4
        
        # Boost for specific keywords
        if parsed['keywords']:
            confidence += min(0.3, len(parsed['keywords']) * 0.1)
        
        # Boost for time filters
        if parsed['time_filter']:
            confidence += 0.1
        
        # Boost for person detection
        if parsed['person_filter']:
            confidence += 0.1
        
        # Boost for source detection (but not if all sources selected)
        if len(parsed['sources']) < 4:  # Not all sources = more specific
            confidence += 0.1
        
        # Penalty for very short queries
        if len(query.strip()) < 5:
            confidence -= 0.2
        
        return max(0.0, min(1.0, confidence))
    
    def _generate_clarifications(self, query: str) -> List[str]:
        """Generate clarification options for ambiguous queries"""
        options = [
            "Search for recent messages",
            "Find upcoming calendar events", 
            "Look for shared documents",
            "Show project updates",
            "Find action items and commitments"
        ]
        
        # Customize based on query content
        if any(word in query for word in ['project', 'work', 'task']):
            options.insert(0, "Show project-related information")
        
        if any(word in query for word in ['meeting', 'call', 'event']):
            options.insert(0, "Search calendar events")
            
        if any(word in query for word in ['file', 'document', 'doc']):
            options.insert(0, "Find documents and files")
        
        return options[:3]  # Return top 3 options
    
    def _create_clarification_result(self, query: str) -> Dict[str, Any]:
        """Create a clarification-needed result for empty or invalid queries"""
        return {
            'original_query': query,
            'intent': 'CLARIFICATION_NEEDED',
            'keywords': [],
            'sources': ['slack', 'calendar', 'drive'],
            'time_filter': None,
            'person_filter': None,
            'person_variants': [],
            'response_type': 'clarification',
            'confidence': 0.0,
            'clarification_options': [
                "Search for recent messages",
                "Find upcoming calendar events",
                "Look for shared documents"
            ],
            'metadata': {'reason': 'empty_or_invalid_query'}
        }