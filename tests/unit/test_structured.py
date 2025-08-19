"""
Comprehensive test suite for structured pattern extraction functionality
Tests @mentions, TODOs, hashtags, URLs, and action item detection

References:
- src/queries/structured.py - Pattern extraction utilities to be implemented
- tests/fixtures/mock_slack_data.py - Mock data structure patterns
- src/search/database.py - Database integration patterns
"""

import pytest
import re
from datetime import datetime
from typing import List, Dict, Any
from unittest.mock import Mock, patch

# Import module to be implemented
from src.queries.structured import StructuredExtractor, PatternType


class TestMentionExtraction:
    """Test @mention parsing from Slack messages and other text"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.extractor = StructuredExtractor()
    
    def test_basic_user_mentions(self):
        """Extract basic @mentions from message text"""
        text = "Hey @john and @jane, can you review this?"
        mentions = self.extractor.extract_mentions(text)
        
        assert len(mentions) == 2
        assert "john" in mentions
        assert "jane" in mentions
    
    def test_user_mentions_with_dots_underscores(self):
        """Extract @mentions with dots and underscores in usernames"""
        text = "CC @john.doe and @jane_smith on this"
        mentions = self.extractor.extract_mentions(text)
        
        assert len(mentions) == 2
        assert "john.doe" in mentions
        assert "jane_smith" in mentions
    
    def test_channel_mentions(self):
        """Extract #channel mentions from messages"""
        text = "Discussed in #general and #product-team channels"
        channels = self.extractor.extract_channel_mentions(text)
        
        assert len(channels) == 2
        assert "general" in channels
        assert "product-team" in channels
    
    def test_special_mentions(self):
        """Handle special mentions (@here, @everyone, @channel)"""
        text = "@here urgent update, cc @everyone and @channel"
        mentions = self.extractor.extract_mentions(text)
        
        assert "here" in mentions
        assert "everyone" in mentions
        assert "channel" in mentions
        assert len(mentions) == 3
    
    def test_slack_format_mentions(self):
        """Extract mentions in Slack's <@USER123> format"""
        text = "Hey <@U12345ABC> and <@U67890DEF>, please check this"
        mentions = self.extractor.extract_slack_mentions(text)
        
        assert len(mentions) == 2
        assert "U12345ABC" in mentions
        assert "U67890DEF" in mentions
    
    def test_mixed_mention_formats(self):
        """Handle mixed mention formats in same text"""
        text = "Hey @john, please ping <@U12345ABC> and discuss in #general"
        
        user_mentions = self.extractor.extract_mentions(text)
        slack_mentions = self.extractor.extract_slack_mentions(text)
        channel_mentions = self.extractor.extract_channel_mentions(text)
        
        assert "john" in user_mentions
        assert "U12345ABC" in slack_mentions
        assert "general" in channel_mentions
    
    def test_mentions_at_boundaries(self):
        """Test mentions at word boundaries and in punctuation"""
        text = "(@john) [check with @jane], and @bob!"
        mentions = self.extractor.extract_mentions(text)
        
        assert len(mentions) == 3
        assert "john" in mentions
        assert "jane" in mentions
        assert "bob" in mentions
    
    def test_false_positive_prevention(self):
        """Prevent false positives for @ symbols in emails and other contexts"""
        text = "Send to john@company.com and @actualuser but not user@email.com"
        mentions = self.extractor.extract_mentions(text)
        
        # Should only extract @actualuser, not email addresses
        assert len(mentions) == 1
        assert "actualuser" in mentions
        assert "john" not in mentions  # From john@company.com
        assert "company.com" not in mentions
    
    def test_empty_and_edge_cases(self):
        """Handle empty strings and edge cases"""
        assert self.extractor.extract_mentions("") == []
        assert self.extractor.extract_mentions(None) == []
        assert self.extractor.extract_mentions("No mentions here") == []
        assert self.extractor.extract_mentions("@") == []  # Just @ symbol
        assert self.extractor.extract_mentions("@@@@") == []  # Multiple @ symbols


class TestPatternExtraction:
    """Test TODO, DEADLINE, and action item extraction"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.extractor = StructuredExtractor()
    
    def test_todo_patterns_basic(self):
        """Find basic TODO items in messages"""
        text = "TODO: Review PR #123. Also TODO: Update documentation"
        todos = self.extractor.extract_todos(text)
        
        assert len(todos) == 2
        assert todos[0]['text'] == "Review PR #123"
        assert todos[1]['text'] == "Update documentation"
        assert all(todo['type'] == PatternType.TODO for todo in todos)
    
    def test_todo_patterns_variations(self):
        """Handle different TODO format variations"""
        text = """
        TODO: First item
        todo: Second item (lowercase)
        - TODO Third item (with dash)
        [] TODO: Fourth item (with checkbox)
        """
        todos = self.extractor.extract_todos(text)
        
        assert len(todos) >= 4
        todo_texts = [todo['text'] for todo in todos]
        assert "First item" in todo_texts
        assert "Second item (lowercase)" in todo_texts
        assert "Third item (with dash)" in todo_texts
        assert "Fourth item (with checkbox)" in todo_texts
    
    def test_deadline_patterns(self):
        """Find DEADLINE and due date patterns"""
        text = "Report due DEADLINE: Friday EOD. Submit by DEADLINE: 2025-08-20 5pm"
        deadlines = self.extractor.extract_deadlines(text)
        
        assert len(deadlines) == 2
        assert deadlines[0]['deadline'] == "Friday EOD"
        assert deadlines[1]['deadline'] == "2025-08-20 5pm"
        assert all(d['type'] == PatternType.DEADLINE for d in deadlines)
    
    def test_due_date_variations(self):
        """Handle various due date formats"""
        text = """
        Due: Monday
        Due by: Next Friday
        Due date: 2025-08-25
        Deadline Monday EOD
        """
        deadlines = self.extractor.extract_deadlines(text)
        
        assert len(deadlines) >= 4
        deadline_texts = [d['deadline'] for d in deadlines]
        assert "Monday" in deadline_texts
        assert "Next Friday" in deadline_texts
        assert "2025-08-25" in deadline_texts
        assert "Monday EOD" in deadline_texts
    
    def test_action_item_extraction(self):
        """Find action items with assignments"""
        text = "ACTION: @john to follow up with client by Tuesday"
        actions = self.extractor.extract_action_items(text)
        
        assert len(actions) == 1
        assert actions[0]['assignee'] == "john"
        assert actions[0]['action'] == "follow up with client"
        assert actions[0]['due'] == "Tuesday"
        assert actions[0]['type'] == PatternType.ACTION
    
    def test_action_item_variations(self):
        """Handle different action item formats"""
        text = """
        ACTION ITEM: @jane to review proposal
        @bob will handle deployment by Friday
        TASK: @alice to update slides
        AI: @mike to send invites
        """
        actions = self.extractor.extract_action_items(text)
        
        assert len(actions) >= 4
        assignees = [action['assignee'] for action in actions]
        assert "jane" in assignees
        assert "bob" in assignees  
        assert "alice" in assignees
        assert "mike" in assignees
    
    def test_action_items_without_due_dates(self):
        """Handle action items without explicit due dates"""
        text = "ACTION: @john to review the code and @jane to write tests"
        actions = self.extractor.extract_action_items(text)
        
        assert len(actions) >= 2
        # Should handle actions without due dates gracefully
        for action in actions:
            assert 'assignee' in action
            assert 'action' in action
            # due field might be None or empty string
    
    def test_mixed_pattern_extraction(self):
        """Extract multiple pattern types from same text"""
        text = """
        TODO: Review proposal by DEADLINE: Friday
        ACTION: @john to implement changes
        Also need to update #general channel
        """
        
        todos = self.extractor.extract_todos(text)
        deadlines = self.extractor.extract_deadlines(text)
        actions = self.extractor.extract_action_items(text)
        channels = self.extractor.extract_channel_mentions(text)
        
        assert len(todos) >= 1
        assert len(deadlines) >= 1
        assert len(actions) >= 1
        assert len(channels) >= 1
    
    def test_multiline_patterns(self):
        """Handle patterns spanning multiple lines"""
        text = """TODO: 
        Review the quarterly report
        and submit feedback by EOD"""
        
        todos = self.extractor.extract_todos(text)
        assert len(todos) >= 1
        # Should capture multiline TODO content
        assert "Review the quarterly report" in todos[0]['text']
    
    def test_pattern_with_metadata(self):
        """Extract patterns with additional metadata"""
        text = "TODO: Fix bug #456 @john DEADLINE: 2025-08-20"
        
        todos = self.extractor.extract_todos(text)
        assert len(todos) == 1
        
        todo = todos[0]
        assert 'text' in todo
        assert 'type' in todo
        assert 'position' in todo  # Character position in text
        # May include extracted metadata like mentions, IDs, etc.


class TestContentExtraction:
    """Test URL, hashtag, and document reference extraction"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.extractor = StructuredExtractor()
    
    def test_url_extraction(self):
        """Extract URLs and links from messages"""
        text = "Check https://github.com/repo and https://docs.google.com/doc123"
        urls = self.extractor.extract_urls(text)
        
        assert len(urls) == 2
        assert urls[0]['url'] == "https://github.com/repo"
        assert urls[1]['url'] == "https://docs.google.com/doc123"
        assert all(url['type'] == PatternType.URL for url in urls)
    
    def test_url_variations(self):
        """Handle various URL formats"""
        text = """
        http://example.com
        https://secure.example.com/path?param=value
        ftp://files.example.com
        www.example.com (without protocol)
        example.com/path (minimal URL)
        """
        urls = self.extractor.extract_urls(text)
        
        assert len(urls) >= 3  # At least the clear HTTP/HTTPS URLs
        url_strings = [url['url'] for url in urls]
        assert "http://example.com" in url_strings
        assert "https://secure.example.com/path?param=value" in url_strings
        assert "ftp://files.example.com" in url_strings
    
    def test_hashtag_extraction(self):
        """Extract hashtags and project tags"""
        text = "Working on #project-alpha #urgent #Q3-goals this week"
        hashtags = self.extractor.extract_hashtags(text)
        
        assert len(hashtags) == 3
        assert "project-alpha" in hashtags
        assert "urgent" in hashtags
        assert "Q3-goals" in hashtags
    
    def test_hashtag_vs_channel_distinction(self):
        """Distinguish between hashtags and channel mentions"""
        text = "Update #general channel about #project-status"
        
        channels = self.extractor.extract_channel_mentions(text)
        hashtags = self.extractor.extract_hashtags(text)
        
        # Implementation should distinguish based on context
        # Both might extract both, or use different detection logic
        assert len(channels) >= 1 or len(hashtags) >= 1
    
    def test_document_reference_extraction(self):
        """Find document and file references"""
        text = "See spreadsheet Q3-Budget.xlsx and proposal.pdf in shared folder"
        docs = self.extractor.extract_document_refs(text)
        
        assert len(docs) == 2
        doc_names = [doc['name'] for doc in docs]
        assert "Q3-Budget.xlsx" in doc_names
        assert "proposal.pdf" in doc_names
    
    def test_document_with_paths(self):
        """Handle document references with paths"""
        text = "Check /shared/reports/annual-report.docx and ../assets/logo.png"
        docs = self.extractor.extract_document_refs(text)
        
        assert len(docs) == 2
        doc_names = [doc['name'] for doc in docs]
        assert "annual-report.docx" in doc_names
        assert "logo.png" in doc_names
        
        # Should also capture paths
        assert any(doc.get('path') == "/shared/reports/" for doc in docs)
    
    def test_email_extraction(self):
        """Extract email addresses from text"""
        text = "Contact john.doe@company.com or support@example.org for help"
        emails = self.extractor.extract_emails(text)
        
        assert len(emails) == 2
        email_addresses = [email['address'] for email in emails]
        assert "john.doe@company.com" in email_addresses
        assert "support@example.org" in email_addresses
    
    def test_phone_number_extraction(self):
        """Extract phone numbers from text"""
        text = "Call me at 555-123-4567 or (555) 987-6543"
        phones = self.extractor.extract_phone_numbers(text)
        
        assert len(phones) >= 2
        phone_numbers = [phone['number'] for phone in phones]
        assert any("555-123-4567" in num for num in phone_numbers)
        assert any("555-987-6543" in num for num in phone_numbers)
    
    def test_mixed_content_extraction(self):
        """Extract all content types from complex text"""
        text = """
        TODO: Review https://docs.google.com/doc123 
        Contact @john at john@company.com or call 555-1234
        Update #project-status and share report.pdf
        DEADLINE: Friday EOD
        """
        
        results = self.extractor.extract_all_patterns(text)
        
        # Should find multiple pattern types
        assert PatternType.TODO in results
        assert PatternType.URL in results
        assert PatternType.EMAIL in results
        assert PatternType.HASHTAG in results or PatternType.CHANNEL in results
        assert PatternType.DEADLINE in results
        assert PatternType.DOCUMENT in results
    
    def test_pattern_positioning(self):
        """Verify pattern positions are captured accurately"""
        text = "TODO: First task and TODO: Second task"
        todos = self.extractor.extract_todos(text)
        
        assert len(todos) == 2
        assert todos[0]['position'] < todos[1]['position']
        assert todos[0]['text'] == "First task"
        assert todos[1]['text'] == "Second task"
    
    def test_overlapping_patterns(self):
        """Handle overlapping or nested patterns"""
        text = "TODO: Check email@example.com and update #status"
        
        results = self.extractor.extract_all_patterns(text)
        
        # Should detect TODO containing email and hashtag
        assert PatternType.TODO in results
        assert PatternType.EMAIL in results
        # Nested patterns should be preserved


class TestStructuredExtractorConfiguration:
    """Test configuration and customization of pattern extraction"""
    
    def test_custom_patterns(self):
        """Test adding custom extraction patterns"""
        extractor = StructuredExtractor()
        
        # Add custom pattern for ticket IDs
        ticket_pattern = r'TICKET-\d+'
        extractor.add_custom_pattern(PatternType.CUSTOM, ticket_pattern)
        
        text = "Fixed issue TICKET-123 and created TICKET-456"
        custom_patterns = extractor.extract_custom_patterns(text, PatternType.CUSTOM)
        
        assert len(custom_patterns) == 2
        assert "TICKET-123" in [p['text'] for p in custom_patterns]
        assert "TICKET-456" in [p['text'] for p in custom_patterns]
    
    def test_pattern_filtering(self):
        """Test filtering patterns by type or criteria"""
        extractor = StructuredExtractor()
        text = "TODO: Task one ACTION: Task two DEADLINE: Friday"
        
        # Extract only specific pattern types
        todos_only = extractor.extract_patterns(text, [PatternType.TODO])
        actions_only = extractor.extract_patterns(text, [PatternType.ACTION])
        
        assert all(p['type'] == PatternType.TODO for p in todos_only)
        assert all(p['type'] == PatternType.ACTION for p in actions_only)
    
    def test_case_sensitivity_options(self):
        """Test case-sensitive vs case-insensitive extraction"""
        extractor_sensitive = StructuredExtractor(case_sensitive=True)
        extractor_insensitive = StructuredExtractor(case_sensitive=False)
        
        text = "TODO: First task and todo: second task"
        
        sensitive_todos = extractor_sensitive.extract_todos(text)
        insensitive_todos = extractor_insensitive.extract_todos(text)
        
        # Case-insensitive should find more matches
        assert len(insensitive_todos) >= len(sensitive_todos)
    
    def test_performance_with_large_text(self):
        """Test performance with large text inputs"""
        import time
        
        # Create large text with many patterns
        large_text = "TODO: Task item. " * 1000 + "@user mention. " * 1000
        extractor = StructuredExtractor()
        
        start = time.time()
        results = extractor.extract_all_patterns(large_text)
        end = time.time()
        
        # Should complete within reasonable time
        assert (end - start) < 2.0  # Less than 2 seconds
        assert len(results) > 0
    
    def test_unicode_and_international_content(self):
        """Test handling of Unicode and international content"""
        text = "TODO: Review résumé and café meeting notes 中文字符"
        
        extractor = StructuredExtractor()
        todos = extractor.extract_todos(text)
        
        assert len(todos) >= 1
        # Should handle Unicode characters in extracted content
        assert "résumé" in todos[0]['text'] or "café" in todos[0]['text']