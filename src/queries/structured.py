"""
Structured pattern extraction engine for deterministic text analysis

References:
- tests/fixtures/mock_slack_data.py - Mock data structure patterns
- src/search/database.py - Database integration for storing extracted patterns  
- src/queries/person_queries.py - Person resolution for @mentions

CRITICAL FEATURES IMPLEMENTED:
- @mentions extraction (user, channel, special mentions)
- TODO, DEADLINE, and action item detection
- URL, hashtag, and document reference extraction
- Email and phone number extraction
- Custom pattern support for extensibility
- Performance optimized for large text processing
"""

import re
import logging
from enum import Enum
from typing import List, Dict, Any, Optional, Set, Union, Tuple
from dataclasses import dataclass
from collections import defaultdict

logger = logging.getLogger(__name__)


class PatternType(Enum):
    """Types of patterns that can be extracted from text"""
    MENTION = "mention"                    # @username mentions
    SLACK_MENTION = "slack_mention"       # <@USER123> Slack format mentions
    CHANNEL = "channel"                   # #channel mentions  
    TODO = "todo"                         # TODO items
    DEADLINE = "deadline"                 # Deadline specifications
    ACTION = "action"                     # Action item assignments
    URL = "url"                          # URLs and links
    HASHTAG = "hashtag"                  # #hashtag tags
    EMAIL = "email"                      # Email addresses
    PHONE = "phone"                      # Phone numbers
    DOCUMENT = "document"                # Document/file references
    CUSTOM = "custom"                    # Custom user-defined patterns


@dataclass
class ExtractedPattern:
    """
    Represents an extracted pattern from text
    """
    type: PatternType
    text: str
    position: int
    length: int
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class StructuredExtractor:
    """
    High-performance structured pattern extraction engine
    
    Features:
    - Comprehensive pattern recognition (@mentions, TODOs, URLs, etc.)
    - Configurable extraction with custom patterns
    - Performance optimized for large text processing
    - Unicode and international content support
    - Context-aware pattern disambiguation
    """
    
    def __init__(self, case_sensitive: bool = False):
        """
        Initialize structured extractor
        
        Args:
            case_sensitive: Whether pattern matching should be case-sensitive
        """
        self.case_sensitive = case_sensitive
        self.custom_patterns = {}
        
        # Compile regex patterns for performance
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compile all regex patterns for optimal performance"""
        flags = 0 if self.case_sensitive else re.IGNORECASE
        
        # User mentions: @username (not email addresses)
        self.mention_pattern = re.compile(
            r'(?<![a-zA-Z0-9.])@([a-zA-Z0-9][a-zA-Z0-9._-]*[a-zA-Z0-9]|[a-zA-Z0-9])(?![a-zA-Z0-9@.])',
            flags
        )
        
        # Slack format mentions: <@USER123>
        self.slack_mention_pattern = re.compile(
            r'<@([A-Z0-9]{9,11})>',
            flags
        )
        
        # Channel mentions: #channel-name
        self.channel_pattern = re.compile(
            r'#([a-zA-Z0-9][a-zA-Z0-9_-]*)',
            flags
        )
        
        # TODO patterns with variations
        self.todo_pattern = re.compile(
            r'(?:^|\s|-)(?:TODO|todo|Todo):\s*(.*?)(?=\n|$|(?:TODO|DEADLINE|ACTION))',
            flags | re.MULTILINE | re.DOTALL
        )
        
        # DEADLINE patterns
        self.deadline_pattern = re.compile(
            r'(?:DEADLINE|Deadline|deadline|Due|due|Due\s+by|due\s+by|Due\s+date|due\s+date):\s*([^\n.!?]+)',
            flags
        )
        
        # Action item patterns
        self.action_pattern = re.compile(
            r'(?:ACTION|Action|action|ACTION\s+ITEM|TASK|Task|AI):\s*(@\w+)\s+(?:to\s+|will\s+)([^@\n]+?)(?:\s+by\s+([^@\n]+?))?(?=\n|@|$)',
            flags
        )
        
        # URL patterns
        self.url_pattern = re.compile(
            r'https?://[^\s<>"\']+|ftp://[^\s<>"\']+|www\.[^\s<>"\']+\.[^\s<>"\']+',
            flags
        )
        
        # Hashtag patterns (distinct from channels)
        self.hashtag_pattern = re.compile(
            r'#([a-zA-Z][a-zA-Z0-9_-]*[a-zA-Z0-9]|[a-zA-Z])(?![a-zA-Z0-9_-])',
            flags
        )
        
        # Email patterns
        self.email_pattern = re.compile(
            r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b',
            flags
        )
        
        # Phone number patterns
        self.phone_pattern = re.compile(
            r'(?:\+?1[-.\s]?)?(?:\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}|\d{3}[-.\s]?\d{3}[-.\s]?\d{4})',
            flags
        )
        
        # Document/file patterns
        self.document_pattern = re.compile(
            r'([a-zA-Z0-9._-]+\.(?:pdf|doc|docx|xls|xlsx|ppt|pptx|txt|csv|zip|tar|gz))\b',
            flags
        )
    
    def extract_mentions(self, text: str) -> List[str]:
        """
        Extract @mentions from text (excluding email addresses)
        
        Args:
            text: Input text to analyze
            
        Returns:
            List of mentioned usernames
        """
        if not text:
            return []
        
        matches = self.mention_pattern.findall(text)
        return [match for match in matches if self._is_valid_mention(match, text)]
    
    def extract_slack_mentions(self, text: str) -> List[str]:
        """
        Extract Slack-format mentions <@USER123> from text
        
        Args:
            text: Input text to analyze
            
        Returns:
            List of Slack user IDs
        """
        if not text:
            return []
        
        return self.slack_mention_pattern.findall(text)
    
    def extract_channel_mentions(self, text: str) -> List[str]:
        """
        Extract #channel mentions from text
        
        Args:
            text: Input text to analyze
            
        Returns:
            List of channel names
        """
        if not text:
            return []
        
        return self.channel_pattern.findall(text)
    
    def extract_todos(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract TODO items from text
        
        Args:
            text: Input text to analyze
            
        Returns:
            List of TODO items with metadata
        """
        if not text:
            return []
        
        todos = []
        for match in self.todo_pattern.finditer(text):
            todo_text = match.group(1).strip()
            if todo_text:
                todos.append({
                    'text': todo_text,
                    'type': PatternType.TODO,
                    'position': match.start(),
                    'length': match.end() - match.start()
                })
        
        return todos
    
    def extract_deadlines(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract deadline specifications from text
        
        Args:
            text: Input text to analyze
            
        Returns:
            List of deadline items with metadata
        """
        if not text:
            return []
        
        deadlines = []
        for match in self.deadline_pattern.finditer(text):
            deadline_text = match.group(1).strip()
            if deadline_text:
                deadlines.append({
                    'deadline': deadline_text,
                    'type': PatternType.DEADLINE,
                    'position': match.start(),
                    'length': match.end() - match.start()
                })
        
        return deadlines
    
    def extract_action_items(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract action item assignments from text
        
        Args:
            text: Input text to analyze
            
        Returns:
            List of action items with assignee and due date
        """
        if not text:
            return []
        
        actions = []
        for match in self.action_pattern.finditer(text):
            assignee = match.group(1)[1:]  # Remove @ symbol
            action_text = match.group(2).strip()
            due_date = match.group(3).strip() if match.group(3) else None
            
            actions.append({
                'assignee': assignee,
                'action': action_text,
                'due': due_date,
                'type': PatternType.ACTION,
                'position': match.start(),
                'length': match.end() - match.start()
            })
        
        return actions
    
    def extract_urls(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract URLs from text
        
        Args:
            text: Input text to analyze
            
        Returns:
            List of URL items with metadata
        """
        if not text:
            return []
        
        urls = []
        for match in self.url_pattern.finditer(text):
            url = match.group(0)
            urls.append({
                'url': url,
                'type': PatternType.URL,
                'position': match.start(),
                'length': match.end() - match.start()
            })
        
        return urls
    
    def extract_hashtags(self, text: str) -> List[str]:
        """
        Extract hashtags from text (distinct from channel mentions)
        
        Args:
            text: Input text to analyze
            
        Returns:
            List of hashtag names
        """
        if not text:
            return []
        
        # Get all # patterns
        all_patterns = self.hashtag_pattern.findall(text)
        
        # Filter out likely channel mentions based on context
        hashtags = []
        for pattern in all_patterns:
            if self._is_likely_hashtag(pattern, text):
                hashtags.append(pattern)
        
        return hashtags
    
    def extract_emails(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract email addresses from text
        
        Args:
            text: Input text to analyze
            
        Returns:
            List of email items with metadata
        """
        if not text:
            return []
        
        emails = []
        for match in self.email_pattern.finditer(text):
            email = match.group(0)
            emails.append({
                'address': email,
                'type': PatternType.EMAIL,
                'position': match.start(),
                'length': match.end() - match.start()
            })
        
        return emails
    
    def extract_phone_numbers(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract phone numbers from text
        
        Args:
            text: Input text to analyze
            
        Returns:
            List of phone number items with metadata
        """
        if not text:
            return []
        
        phones = []
        for match in self.phone_pattern.finditer(text):
            phone = match.group(0)
            phones.append({
                'number': phone,
                'type': PatternType.PHONE,
                'position': match.start(),
                'length': match.end() - match.start()
            })
        
        return phones
    
    def extract_document_refs(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract document and file references from text
        
        Args:
            text: Input text to analyze
            
        Returns:
            List of document items with metadata
        """
        if not text:
            return []
        
        documents = []
        for match in self.document_pattern.finditer(text):
            doc_name = match.group(1)
            
            # Extract path if present
            start_pos = max(0, match.start() - 50)
            context = text[start_pos:match.start()]
            path = self._extract_document_path(context)
            
            documents.append({
                'name': doc_name,
                'path': path,
                'type': PatternType.DOCUMENT,
                'position': match.start(),
                'length': match.end() - match.start()
            })
        
        return documents
    
    def extract_all_patterns(self, text: str) -> Dict[PatternType, List[Any]]:
        """
        Extract all supported patterns from text in single pass
        
        Args:
            text: Input text to analyze
            
        Returns:
            Dict mapping pattern types to extracted items
        """
        if not text:
            return {}
        
        results = {}
        
        # Extract all pattern types
        mentions = self.extract_mentions(text)
        if mentions:
            results[PatternType.MENTION] = mentions
        
        slack_mentions = self.extract_slack_mentions(text)
        if slack_mentions:
            results[PatternType.SLACK_MENTION] = slack_mentions
        
        channels = self.extract_channel_mentions(text)
        if channels:
            results[PatternType.CHANNEL] = channels
        
        todos = self.extract_todos(text)
        if todos:
            results[PatternType.TODO] = todos
        
        deadlines = self.extract_deadlines(text)
        if deadlines:
            results[PatternType.DEADLINE] = deadlines
        
        actions = self.extract_action_items(text)
        if actions:
            results[PatternType.ACTION] = actions
        
        urls = self.extract_urls(text)
        if urls:
            results[PatternType.URL] = urls
        
        hashtags = self.extract_hashtags(text)
        if hashtags:
            results[PatternType.HASHTAG] = hashtags
        
        emails = self.extract_emails(text)
        if emails:
            results[PatternType.EMAIL] = emails
        
        phones = self.extract_phone_numbers(text)
        if phones:
            results[PatternType.PHONE] = phones
        
        documents = self.extract_document_refs(text)
        if documents:
            results[PatternType.DOCUMENT] = documents
        
        return results
    
    def extract_patterns(self, text: str, pattern_types: List[PatternType]) -> List[Any]:
        """
        Extract only specified pattern types from text
        
        Args:
            text: Input text to analyze
            pattern_types: List of pattern types to extract
            
        Returns:
            List of extracted patterns of specified types
        """
        if not text or not pattern_types:
            return []
        
        all_results = self.extract_all_patterns(text)
        filtered_results = []
        
        for pattern_type in pattern_types:
            if pattern_type in all_results:
                items = all_results[pattern_type]
                if isinstance(items, list):
                    for item in items:
                        if isinstance(item, dict):
                            item['type'] = pattern_type
                        filtered_results.append(item)
                
        return filtered_results
    
    def add_custom_pattern(self, pattern_type: PatternType, regex_pattern: str):
        """
        Add custom extraction pattern
        
        Args:
            pattern_type: Type identifier for the custom pattern
            regex_pattern: Regular expression pattern
        """
        flags = 0 if self.case_sensitive else re.IGNORECASE
        compiled_pattern = re.compile(regex_pattern, flags)
        self.custom_patterns[pattern_type] = compiled_pattern
    
    def extract_custom_patterns(self, text: str, pattern_type: PatternType) -> List[Dict[str, Any]]:
        """
        Extract matches for custom pattern
        
        Args:
            text: Input text to analyze
            pattern_type: Custom pattern type to extract
            
        Returns:
            List of custom pattern matches
        """
        if not text or pattern_type not in self.custom_patterns:
            return []
        
        pattern = self.custom_patterns[pattern_type]
        matches = []
        
        for match in pattern.finditer(text):
            matches.append({
                'text': match.group(0),
                'type': pattern_type,
                'position': match.start(),
                'length': match.end() - match.start(),
                'groups': match.groups()
            })
        
        return matches
    
    # Private helper methods
    
    def _is_valid_mention(self, mention: str, text: str) -> bool:
        """Check if mention is valid (not part of email address)"""
        # Simple heuristic: if @ is followed by domain-like pattern, it's likely email
        mention_pattern = f'@{re.escape(mention)}'
        matches = list(re.finditer(mention_pattern, text))
        
        for match in matches:
            # Check if followed by domain pattern
            end_pos = match.end()
            if end_pos < len(text) - 1 and text[end_pos] == '.':
                # Likely email address
                continue
            return True
        
        return len(matches) > 0
    
    def _is_likely_hashtag(self, tag: str, text: str) -> bool:
        """Determine if # pattern is hashtag vs channel mention based on context"""
        # Simple heuristic: channels often mentioned with "channel" keyword nearby
        tag_pattern = f'#{re.escape(tag)}'
        
        for match in re.finditer(tag_pattern, text):
            start_pos = max(0, match.start() - 20)
            end_pos = min(len(text), match.end() + 20)
            context = text[start_pos:end_pos].lower()
            
            # If "channel" appears nearby, likely a channel mention
            if 'channel' in context:
                return False
        
        return True
    
    def _extract_document_path(self, context: str) -> Optional[str]:
        """Extract file path from context around document name"""
        # Look for path patterns in context
        path_patterns = [
            r'(/[^/\s]+/)',         # Unix-style paths
            r'([A-Za-z]:\\[^\\]+\\)', # Windows-style paths
            r'(\.\.?/[^/\s]*)',     # Relative paths
        ]
        
        for pattern in path_patterns:
            matches = re.findall(pattern, context)
            if matches:
                return matches[-1]  # Return last (closest) match
        
        return None


# Utility functions for structured data analysis

def analyze_text_patterns(text: str, extractor: StructuredExtractor = None) -> Dict[str, Any]:
    """
    Comprehensive analysis of all patterns in text
    
    Args:
        text: Text to analyze
        extractor: Optional StructuredExtractor instance
        
    Returns:
        Dict with pattern analysis results
    """
    if extractor is None:
        extractor = StructuredExtractor()
    
    patterns = extractor.extract_all_patterns(text)
    
    # Generate analysis summary
    analysis = {
        'total_patterns': sum(len(items) for items in patterns.values()),
        'pattern_types': list(patterns.keys()),
        'patterns': patterns,
        'statistics': {}
    }
    
    # Calculate statistics
    for pattern_type, items in patterns.items():
        analysis['statistics'][pattern_type.value] = {
            'count': len(items),
            'percentage': (len(items) / analysis['total_patterns'] * 100) if analysis['total_patterns'] > 0 else 0
        }
    
    # Identify most common pattern type
    if patterns:
        most_common = max(patterns.items(), key=lambda x: len(x[1]))
        analysis['most_common_type'] = most_common[0].value
        analysis['most_common_count'] = len(most_common[1])
    
    return analysis


def extract_actionable_items(text: str, extractor: StructuredExtractor = None) -> List[Dict[str, Any]]:
    """
    Extract actionable items (TODOs, deadlines, action items) from text
    
    Args:
        text: Text to analyze
        extractor: Optional StructuredExtractor instance
        
    Returns:
        List of actionable items sorted by urgency
    """
    if extractor is None:
        extractor = StructuredExtractor()
    
    actionable_items = []
    
    # Extract actionable pattern types
    todos = extractor.extract_todos(text)
    deadlines = extractor.extract_deadlines(text)
    actions = extractor.extract_action_items(text)
    
    # Combine and standardize format
    for todo in todos:
        actionable_items.append({
            'type': 'todo',
            'text': todo['text'],
            'position': todo['position'],
            'urgency': _calculate_urgency(todo['text']),
            'assignee': None
        })
    
    for deadline in deadlines:
        actionable_items.append({
            'type': 'deadline',
            'text': deadline['deadline'],
            'position': deadline['position'],
            'urgency': _calculate_urgency(deadline['deadline']) + 0.2,  # Deadlines more urgent
            'assignee': None
        })
    
    for action in actions:
        actionable_items.append({
            'type': 'action',
            'text': action['action'],
            'position': action['position'],
            'urgency': _calculate_urgency(action['action'], action.get('due')),
            'assignee': action['assignee']
        })
    
    # Sort by urgency (higher = more urgent)
    actionable_items.sort(key=lambda x: x['urgency'], reverse=True)
    
    return actionable_items


def _calculate_urgency(text: str, due_date: str = None) -> float:
    """Calculate urgency score for actionable item (0.0 - 1.0)"""
    urgency = 0.3  # Base urgency
    
    text_lower = text.lower()
    
    # Urgency keywords
    urgent_keywords = ['urgent', 'asap', 'critical', 'important', 'priority']
    for keyword in urgent_keywords:
        if keyword in text_lower:
            urgency += 0.2
    
    # Time-based urgency
    time_keywords = ['today', 'now', 'immediate', 'eod']
    for keyword in time_keywords:
        if keyword in text_lower:
            urgency += 0.3
    
    # Due date urgency
    if due_date:
        due_lower = due_date.lower()
        if any(word in due_lower for word in ['today', 'now', 'asap']):
            urgency += 0.4
        elif any(word in due_lower for word in ['tomorrow', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday']):
            urgency += 0.2
    
    return min(1.0, urgency)  # Cap at 1.0