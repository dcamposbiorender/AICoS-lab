# Agent L: Personalization Integration - Phase 6 Implementation

**Date Created**: 2025-08-28  
**Owner**: Agent L (Personalization Team)  
**Status**: PENDING  
**Estimated Time**: 8 hours (1 day)  
**Dependencies**: Agent J (UserIdentity) and Agent K (Setup Wizard) must be complete

## Executive Summary

Integrate PRIMARY_USER configuration throughout existing system components to deliver personalized dashboards, briefs, and search results. Transform the system from generic data display to user-centric presentation focusing on what matters most to the primary user.

**Core Philosophy**: Simple, effective personalization that makes the user the center of all data and interactions. No complex algorithms - just practical filtering and boosting that delivers immediate value.

## CRITICAL REQUIREMENTS (User-Centric Data)

### Requirement 1: Dashboard Personalization - ESSENTIAL
- **Purpose**: Show user's actual calendar data, not sample/demo data
- **Implementation**: Use PRIMARY_USER to filter calendar events
- **Impact**: Dashboard becomes personally relevant and useful
- **Validation**: User sees their meetings, not other employees'

### Requirement 2: Brief Personalization - ESSENTIAL
- **Purpose**: Prioritize user's activities, meetings, and mentions in daily briefs
- **Implementation**: Filter and boost user-related content
- **Impact**: Briefs focus on what the user cares about most
- **Validation**: User's commitments and mentions appear prominently

### Requirement 3: Search Relevance Boosting - ESSENTIAL
- **Purpose**: Prioritize search results related to the primary user
- **Implementation**: Boost relevance scores for user-related content
- **Impact**: Search finds user's information first
- **Validation**: User-related results appear at top of search

### Requirement 4: Backwards Compatibility - ESSENTIAL
- **Purpose**: System works without PRIMARY_USER configured
- **Implementation**: Graceful fallback to non-personalized mode
- **Impact**: No breaking changes to existing functionality
- **Validation**: All features work as before when unconfigured

## Module Architecture

### Relevant Files for Personalization

**Read for Context:**
- `src/core/user_identity.py` - PRIMARY_USER configuration (Agent J)
- `tools/load_dashboard_data.py` - Current dashboard data loading
- `src/bot/commands/brief.py` - Brief generation logic
- `src/bot/commands/filtered_brief.py` - Brief filtering patterns
- `src/search/database.py` - Search result processing
- `src/intelligence/activity_analyzer.py` - Activity analysis for briefs

**Files to Create:**
- `src/personalization/simple_filter.py` - Core personalization filtering
- `src/personalization/relevance_boost.py` - Search relevance boosting
- `src/personalization/calendar_filter.py` - Calendar personalization
- `src/personalization/brief_personalizer.py` - Brief personalization
- `tests/unit/test_personalization.py` - Personalization testing
- `tests/integration/test_user_centric_flow.py` - End-to-end personalization

**Files to Modify:**
- `tools/load_dashboard_data.py` - Use user's calendar data
- `src/bot/commands/brief.py` - Apply personalization filter
- `src/bot/commands/filtered_brief.py` - Integrate user filtering
- `src/cli/interfaces.py` - Add personalization to interfaces
- `src/intelligence/activity_analyzer.py` - User-centric analysis

**Reference Patterns:**
- `src/bot/commands/brief.py:24-86` - Brief generation and formatting
- `tools/load_dashboard_data.py:15-45` - Data loading patterns
- `src/intelligence/activity_analyzer.py:30-80` - Activity filtering logic

## Implementation Tasks

### Task L.1: Core Personalization Framework (2 hours)

**File**: `src/personalization/simple_filter.py`

**Implementation**:
```python
class SimpleFilter:
    """Core personalization filtering for user-centric data presentation"""
    
    def __init__(self):
        from src.core.user_identity import UserIdentity
        self.user_identity = UserIdentity()
        self.primary_user = self.user_identity.get_primary_user()
        
    def is_user_relevant(self, data_item):
        """Check if data item is relevant to primary user"""
        if not self.primary_user:
            return True  # No filtering if no PRIMARY_USER
            
        # Check various user identifiers
        return (
            self.involves_user_email(data_item) or
            self.involves_user_slack(data_item) or
            self.involves_user_calendar(data_item)
        )
    
    def boost_user_content(self, items, boost_factor=1.5):
        """Boost relevance of user-related items"""
        for item in items:
            if self.is_user_relevant(item):
                if hasattr(item, 'score'):
                    item.score *= boost_factor
                elif hasattr(item, 'relevance'):
                    item.relevance *= boost_factor
        return sorted(items, key=lambda x: getattr(x, 'score', 0), reverse=True)
    
    def filter_for_user(self, items, include_others=True, user_first=True):
        """Filter and organize items with user content prioritized"""
        if not self.primary_user:
            return items  # No filtering
            
        user_items = [item for item in items if self.is_user_relevant(item)]
        other_items = [item for item in items if not self.is_user_relevant(item)]
        
        if not include_others:
            return user_items
        elif user_first:
            return user_items + other_items[:10]  # User items + limited others
        else:
            return items
```

**Acceptance Tests**:
1. Identify user-relevant data items correctly
2. Boost relevance scores for user content
3. Filter items with user content first
4. Handle missing PRIMARY_USER gracefully
5. Work with different data types (calendar, slack, drive)
6. Maintain backwards compatibility
7. Preserve original data when not filtering

### Task L.2: Dashboard Personalization (2 hours)

**File**: `tools/load_dashboard_data.py` (modifications)

**Current Issue**: Dashboard shows demo data instead of user's calendar

**Implementation**:
```python
from src.personalization.simple_filter import SimpleFilter
from src.core.user_identity import UserIdentity

def load_calendar_data():
    """Load calendar data prioritizing PRIMARY_USER"""
    user_identity = UserIdentity()
    primary_user = user_identity.get_primary_user()
    
    if primary_user:
        # Load user's specific calendar file
        user_email = primary_user['email']
        calendar_file = f"employee_{user_email.replace('@', '_at_').replace('.', '_')}.jsonl"
        
        try:
            user_calendar = load_user_calendar_file(calendar_file)
            if user_calendar:
                return format_user_calendar(user_calendar, primary_user)
        except FileNotFoundError:
            print(f"⚠️ User calendar not found: {calendar_file}")
    
    # Fallback to existing behavior
    return load_all_calendars()

def format_user_calendar(calendar_data, user):
    """Format calendar data with user-centric presentation"""
    # Prioritize user's meetings
    # Show user as organizer/attendee
    # Highlight user's availability
```

**New File**: `src/personalization/calendar_filter.py`
```python
class CalendarPersonalizer:
    """Personalize calendar display for PRIMARY_USER"""
    
    def filter_user_events(self, events, user):
        """Filter events involving the user"""
        user_events = []
        for event in events:
            if self.is_user_event(event, user):
                user_events.append(self.enhance_user_event(event, user))
        return user_events
    
    def is_user_event(self, event, user):
        """Check if event involves the user"""
        # Check organizer, attendees, calendar
        
    def enhance_user_event(self, event, user):
        """Add user context to event display"""
        # Mark user role (organizer/attendee)
        # Highlight user's calendar
```

**Acceptance Tests**:
1. Load user's specific calendar file when PRIMARY_USER configured
2. Display user's meetings prominently in dashboard
3. Show user as organizer/attendee where applicable
4. Fallback to all calendars when user calendar missing
5. Handle calendar file format correctly
6. Maintain existing dashboard format and style
7. Work without PRIMARY_USER (backwards compatible)
8. Show user's availability and conflicts
9. Performance remains acceptable (<3s load time)
10. Error handling for missing calendar data

### Task L.3: Brief Personalization (2 hours)

**Files**: `src/bot/commands/brief.py`, `src/personalization/brief_personalizer.py`

**Current Issue**: Briefs treat all activities equally

**Implementation**:
```python
# src/personalization/brief_personalizer.py
class BriefPersonalizer:
    """Personalize brief content for PRIMARY_USER"""
    
    def __init__(self):
        self.filter = SimpleFilter()
        
    def personalize_brief_data(self, brief_data):
        """Apply personalization to brief data"""
        if not self.filter.primary_user:
            return brief_data  # No personalization
            
        # Prioritize user's activities
        if 'slack_activity' in brief_data:
            brief_data['slack_activity'] = self.personalize_slack_activity(
                brief_data['slack_activity']
            )
            
        if 'calendar_activity' in brief_data:
            brief_data['calendar_activity'] = self.personalize_calendar_activity(
                brief_data['calendar_activity']
            )
            
        # Add user-specific highlights
        brief_data['user_highlights'] = self.extract_user_highlights(brief_data)
        
        return brief_data
    
    def personalize_slack_activity(self, slack_data):
        """Focus on user's Slack activity"""
        user = self.filter.primary_user
        
        # Count user's messages vs total
        # Highlight channels where user is active
        # Show mentions of the user
        
    def extract_user_highlights(self, brief_data):
        """Extract highlights relevant to the user"""
        highlights = []
        
        # User's meetings today
        # Messages mentioning the user
        # User's commitments and deadlines
        # Files user created/modified
        
        return highlights[:5]  # Top 5 user highlights
```

**Brief Format Enhancement**:
```python
def format_brief_response(brief_result: Dict[str, Any]) -> str:
    """Format brief with user-centric focus"""
    
    # Add user-specific section at top
    if 'user_highlights' in data:
        response += "🎯 **Your Key Activities:**\n"
        for highlight in data['user_highlights']:
            response += f"• {highlight}\n"
        response += "\n"
    
    # Standard sections with user context
    # Slack activity (user's messages highlighted)
    # Calendar (user's meetings first)
    # Drive (user's files emphasized)
```

**Acceptance Tests**:
1. Brief highlights user's activities prominently
2. User's meetings appear first in calendar section
3. Slack mentions of user highlighted
4. User's message counts emphasized
5. User-specific highlights section added
6. Files user created/modified shown first
7. Backwards compatible without PRIMARY_USER
8. Brief remains concise and readable
9. Performance impact minimal (<2s generation)
10. User context clearly indicated

### Task L.4: Search Relevance Boosting (2 hours)

**File**: `src/personalization/relevance_boost.py`

**Current Issue**: Search treats all results equally

**Implementation**:
```python
class RelevanceBooster:
    """Boost search results relevant to PRIMARY_USER"""
    
    def __init__(self):
        self.filter = SimpleFilter()
        
    def boost_search_results(self, results, boost_factor=1.5):
        """Apply relevance boosting to search results"""
        if not self.filter.primary_user:
            return results  # No boosting
            
        for result in results:
            if self.is_user_relevant_result(result):
                result.score *= boost_factor
                result.boosted = True  # Mark as boosted
                
        return sorted(results, key=lambda x: x.score, reverse=True)
    
    def is_user_relevant_result(self, result):
        """Check if search result involves the user"""
        user = self.filter.primary_user
        
        # Check result content for user identifiers
        content = getattr(result, 'content', '') or ''
        
        return (
            user['email'] in content or
            user['slack_id'] in content or
            f"@{user['name'].split()[0].lower()}" in content.lower() or
            self.check_user_in_metadata(result, user)
        )
    
    def check_user_in_metadata(self, result, user):
        """Check result metadata for user involvement"""
        metadata = getattr(result, 'metadata', {})
        
        # Check attendees, authors, mentions
        attendees = metadata.get('attendees', [])
        author = metadata.get('author', '')
        
        return (
            user['email'] in attendees or
            user['email'] == author or
            user['slack_id'] == metadata.get('user_id')
        )
```

**Integration with Search**:
```python
# Modify existing search to use relevance boosting
def search_with_personalization(query, limit=20):
    """Search with user relevance boosting"""
    # Perform normal search
    results = normal_search(query, limit * 2)  # Get extra results
    
    # Apply personalization boost
    booster = RelevanceBooster()
    boosted_results = booster.boost_search_results(results)
    
    return boosted_results[:limit]  # Return top results after boosting
```

**Acceptance Tests**:
1. User-related search results boosted by 50%
2. Results involving user's email boosted
3. Results with user's Slack mentions boosted
4. Results from user's calendar events boosted
5. Results authored by user boosted
6. Boost indication preserved in results
7. Search remains fast (<2s response time)
8. Backwards compatible without PRIMARY_USER
9. Relevance scores calculated correctly
10. Top results clearly user-relevant

### Task L.5: Integration Testing & Validation (2 hours)

**File**: `tests/integration/test_user_centric_flow.py`

**End-to-End Testing**:
```python
class TestUserCentricFlow:
    """Test complete personalization flow"""
    
    def test_complete_personalization_flow(self):
        """Test personalization across all components"""
        # Setup PRIMARY_USER
        user_identity = UserIdentity()
        user_identity.set_primary_user(
            email="test@example.com",
            slack_id="U123456",
            name="Test User"
        )
        
        # Test dashboard personalization
        dashboard_data = load_calendar_data()
        assert user_calendar_data_present(dashboard_data)
        
        # Test brief personalization
        brief = generate_brief()
        assert user_highlights_present(brief)
        
        # Test search personalization
        results = search_with_personalization("meeting")
        assert user_results_boosted(results)
        
    def test_backwards_compatibility(self):
        """Test system works without PRIMARY_USER"""
        # Clear PRIMARY_USER configuration
        # Test all components work normally
        # Verify no exceptions or errors
```

**Performance Testing**:
```python
def test_personalization_performance():
    """Ensure personalization doesn't slow down system"""
    # Test dashboard load time <3s
    # Test brief generation <5s
    # Test search response <2s
    # Compare with/without personalization
```

**User Experience Validation**:
```python
def test_user_centric_experience():
    """Validate user-centric experience"""
    # User's calendar shows in dashboard
    # User's activities prominent in brief
    # User's search results appear first
    # Clear indication of personalization
```

## User Experience Examples

### Dashboard Before/After

**Before (Generic)**:
```
📅 Today's Calendar (All Employees)
• 9:00 AM - Team Standup (alice@company.com)
• 10:00 AM - Project Review (bob@company.com)  
• 2:00 PM - David's 1:1 (david.campos@biorender.com)
```

**After (Personalized)**:
```
📅 Your Calendar Today
• 10:00 AM - Leadership Sync (You're organizing)
• 2:00 PM - 1:1 with Sarah (You're attending)
• 4:00 PM - Product Demo (You're presenting)

📊 Team Activity (Context)
• 3 other meetings scheduled
```

### Brief Before/After

**Before (Generic)**:
```
📋 Daily Brief

💬 Slack: 1,543 messages across 12 channels
📅 Calendar: 47 meetings scheduled
📁 Drive: 231 files modified
```

**After (Personalized)**:
```
📋 Your Daily Brief

🎯 Your Key Activities:
• 3 meetings you're organizing today
• 12 Slack mentions in #leadership  
• Product demo slides updated by you

💬 Your Slack Activity: 47 messages sent
📅 Your Calendar: 3 meetings, 2 conflicts resolved
📁 Your Files: 5 documents updated
```

### Search Before/After

**Before (Generic)**:
```
Search: "quarterly goals"

1. Q3 Goals Discussion - #general-chat (Score: 0.85)
2. Quarterly Planning - alice@company.com (Score: 0.82)
3. Goal Setting Workshop - team-calendar (Score: 0.78)
```

**After (Personalized)**:
```
Search: "quarterly goals" 

1. Your Q3 Goals Discussion - #leadership (Score: 1.28) 🎯
2. Quarterly Planning with You - david.campos@biorender.com (Score: 1.23) 🎯
3. Goal Setting Workshop - team-calendar (Score: 0.78)
```

## Integration Points

### With Existing Components
- **Dashboard**: Load user's calendar data prominently
- **Brief Generation**: Apply personalization filter to all data
- **Search System**: Boost user-relevant results automatically  
- **Activity Analysis**: Focus analysis on user's activities
- **CLI Tools**: Add user context to all command outputs

### Personalization API
```python
from src.personalization.simple_filter import SimpleFilter

# Initialize personalization
filter = SimpleFilter()

# Check if data is user-relevant
if filter.is_user_relevant(data_item):
    # Highlight or prioritize
    
# Boost content for user
boosted_items = filter.boost_user_content(items)

# Filter with user content first
filtered_items = filter.filter_for_user(items, user_first=True)
```

## Success Metrics

### Technical Success Criteria
- Dashboard shows user's actual calendar data
- Briefs prioritize user activities in top 3 highlights
- Search results boost user content by 50%
- All personalization backwards compatible
- Performance impact <10% on all operations

### User Experience Success Criteria
- User immediately sees their information prominently
- Brief focuses on user's activities and commitments
- Search finds user's information first
- Clear indication of personalized vs contextual content
- System feels personally relevant to the user

### Quality Gates
- 90% test coverage for personalization components
- All integration tests pass
- Performance benchmarks met
- User experience validation complete
- Backwards compatibility verified

## Risk Mitigation

### Personalization Risks
- **Over-filtering**: Include contextual information, not just user data
- **Performance impact**: Optimize filtering and boosting algorithms
- **Configuration errors**: Graceful fallback to non-personalized mode
- **User not found**: Handle missing user identity gracefully

### Integration Risks
- **Breaking changes**: Extensive backwards compatibility testing
- **Data consistency**: Validate personalization doesn't corrupt data
- **API changes**: Maintain existing interfaces while adding personalization
- **Performance regression**: Benchmark before and after personalization

### User Experience Risks
- **Information isolation**: Show user data prominently but include context
- **Unexpected behavior**: Clear indication of personalized content
- **Missing personalization**: Fallback messaging when PRIMARY_USER not set
- **Overwhelming changes**: Gradual personalization introduction

## Completion Criteria

### Code Complete When
- All personalization components implemented
- Dashboard loads user's actual calendar data
- Briefs highlight user activities prominently  
- Search boosts user-relevant results
- Comprehensive test coverage achieved

### Agent L Complete When
- User sees their calendar in dashboard (not demo data)
- Briefs focus on user's meetings, commitments, mentions
- Search prioritizes user-relevant results consistently
- All personalization backwards compatible
- System transforms from generic to user-centric
- Phase 6 user-centric architecture complete

This completes the transformation from a generic system to a truly user-centric AI Chief of Staff that revolves around the primary user's needs, activities, and priorities.