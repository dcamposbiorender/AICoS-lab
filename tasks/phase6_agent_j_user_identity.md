# Agent J: User Identity Configuration - Phase 6 Implementation

**Date Created**: 2025-08-28  
**Owner**: Agent J (User Identity Team)  
**Status**: PENDING  
**Estimated Time**: 4 hours (0.5 day)  
**Dependencies**: None (foundation module)

## Executive Summary

Implement simple PRIMARY_USER configuration to identify who the system serves, enabling personalization across all components. This establishes the foundation for user-centric architecture without over-engineering.

**Core Philosophy**: Simple, practical lab-grade implementation. Store PRIMARY_USER configuration and provide identity mapping across Slack, Calendar, and Drive systems.

## CRITICAL REQUIREMENTS (Lab-Grade Simplicity)

### Requirement 1: PRIMARY_USER Configuration - ESSENTIAL
- **Purpose**: System awareness of who the primary user is
- **Implementation**: Simple configuration class with email, slack_id, calendar_id, name
- **Storage**: Environment variables or .env file
- **Validation**: Verify user exists in connected systems

### Requirement 2: Cross-System Identity Mapping - ESSENTIAL  
- **Purpose**: Map user identity across Slack, Calendar, and Drive
- **Implementation**: Bidirectional lookup functions (email ↔ slack_id ↔ calendar_id)
- **Validation**: Handle missing mappings gracefully
- **Fallback**: Work without complete mapping (warnings only)

### Requirement 3: Backwards Compatibility - ESSENTIAL
- **Purpose**: System works without PRIMARY_USER configured
- **Implementation**: Default to non-personalized mode
- **Validation**: All existing functionality continues working
- **Migration**: No breaking changes to current codebase

## Module Architecture

### Relevant Files for User Identity

**Read for Context:**
- `src/core/config.py` - Configuration management patterns
- `src/core/auth_manager.py` - Credential management approach  
- `src/collectors/employee_collector.py` - Employee data structure
- `src/collectors/slack_collector.py` - Slack user ID patterns

**Files to Create:**
- `src/core/user_identity.py` - User identity configuration and mapping
- `tests/unit/test_user_identity.py` - Comprehensive user identity tests
- `tests/fixtures/mock_user_data.py` - Test user data

**Files to Modify:**
- `src/core/config.py` - Add PRIMARY_USER configuration section
- `.env.example` - Add PRIMARY_USER environment variables

**Reference Patterns:**
- `src/core/config.py:46-100` - Configuration class pattern with validation
- `src/core/auth_manager.py:15-45` - Credential validation approach

## Implementation Tasks

### Task J.1: Core User Identity Module (1 hour)

**File**: `src/core/user_identity.py`

**Implementation**:
```python
class UserIdentity:
    """Simple PRIMARY_USER configuration and identity mapping"""
    
    def __init__(self, config=None):
        self.config = config or Config()
        self.primary_user = None
        self._load_primary_user()
    
    def _load_primary_user(self):
        """Load PRIMARY_USER from configuration"""
        # Load from environment or config file
        
    def set_primary_user(self, email, slack_id=None, calendar_id=None, name=None):
        """Set PRIMARY_USER configuration"""
        # Validate and store user identity
        
    def get_primary_user(self):
        """Get PRIMARY_USER configuration or None"""
        # Return user dict or None if not configured
        
    def is_primary_user(self, identifier):
        """Check if identifier matches primary user"""
        # Handle email, slack_id, or calendar_id
```

**Acceptance Tests**:
1. Load PRIMARY_USER from environment variables
2. Set and retrieve PRIMARY_USER configuration  
3. Validate PRIMARY_USER has required fields (email)
4. Handle missing PRIMARY_USER gracefully (return None)
5. Map email to slack_id and calendar_id
6. Validate user identity consistency
7. Work without configuration (backwards compatible)

### Task J.2: Configuration Integration (1 hour)

**File**: `src/core/config.py`

**Implementation**:
- Add PRIMARY_USER section to Config class
- Environment variable loading (AICOS_PRIMARY_USER_EMAIL, etc.)
- Validation that PRIMARY_USER fields are valid
- Integration with existing configuration patterns

**Environment Variables**:
```bash
AICOS_PRIMARY_USER_EMAIL=david.campos@biorender.com
AICOS_PRIMARY_USER_SLACK_ID=U123456  
AICOS_PRIMARY_USER_CALENDAR_ID=david.campos@biorender.com
AICOS_PRIMARY_USER_NAME="David Campos"
```

**Acceptance Tests**:
1. Load PRIMARY_USER from environment variables
2. Validate email format  
3. Handle missing environment variables gracefully
4. Integrate with existing Config class
5. Preserve backwards compatibility
6. Export configuration to other modules

### Task J.3: Cross-System Identity Mapping (1 hour)

**File**: `src/core/user_identity.py` (extension)

**Implementation**:
```python
class IdentityMapper:
    """Map user identity across systems"""
    
    def resolve_slack_user(self, email):
        """Find Slack user ID from email"""
        # Use employee collector data or Slack API
        
    def resolve_calendar_user(self, email):  
        """Find calendar ID from email (usually same as email)"""
        
    def validate_user_exists(self, user_config):
        """Validate user exists in all connected systems"""
        # Check Slack, Calendar, Drive access
```

**Acceptance Tests**:
1. Map email to Slack user ID using employee data
2. Map email to Calendar ID (validate exists)
3. Handle missing user mappings gracefully
4. Validate user exists in Slack workspace
5. Validate user has Calendar access
6. Provide helpful error messages for missing users
7. Work with partial identity mapping

### Task J.4: Comprehensive Testing (1 hour)

**File**: `tests/unit/test_user_identity.py`

**Test Categories**:
1. **Configuration Tests**:
   - Load PRIMARY_USER from environment
   - Handle missing configuration
   - Validate configuration format
   - Integration with Config class

2. **Identity Mapping Tests**:
   - Map email to Slack ID
   - Map email to Calendar ID
   - Handle missing mappings
   - Validate cross-system consistency

3. **Validation Tests**:
   - Validate user exists in systems
   - Handle API failures gracefully
   - Provide clear error messages
   - Work with offline/test mode

4. **Backwards Compatibility Tests**:
   - Work without PRIMARY_USER configured
   - Don't break existing functionality
   - Graceful fallbacks
   - No exceptions when unconfigured

**Mock Data** (`tests/fixtures/mock_user_data.py`):
```python
MOCK_PRIMARY_USER = {
    "email": "david.campos@biorender.com",
    "slack_id": "U123456789",
    "calendar_id": "david.campos@biorender.com", 
    "name": "David Campos"
}

MOCK_EMPLOYEE_DATA = [
    {"email": "david.campos@biorender.com", "slack_id": "U123456789"},
    # ... other employees
]
```

## Test-Driven Development Workflow

### Pre-Implementation Tests (Write First)
1. Create test file with failing tests
2. Define expected behavior for PRIMARY_USER configuration
3. Test identity mapping functionality
4. Test backwards compatibility scenarios

### Implementation (Make Tests Pass)
1. Create UserIdentity class with minimal functionality
2. Implement configuration loading
3. Add identity mapping methods
4. Integrate with Config class

### Validation (Confirm Success)
1. All tests pass
2. Integration with existing config system works
3. User identity can be retrieved from any module
4. System works without PRIMARY_USER configured

## Integration Points

### With Existing Components
- **Config System**: PRIMARY_USER stored in Config class
- **Collectors**: Use UserIdentity for context awareness
- **Dashboard**: Query PRIMARY_USER for personalization
- **Briefs**: Use user identity for filtering
- **Search**: Apply user context for relevance

### API for Other Modules
```python
from src.core.user_identity import UserIdentity

# Get user identity
user_identity = UserIdentity()
primary_user = user_identity.get_primary_user()

if primary_user:
    # Personalize for primary user
    user_email = primary_user['email']
    user_slack_id = primary_user['slack_id']
else:
    # Non-personalized mode
    pass
```

## Success Metrics

### Technical Success Criteria
- All tests pass (15+ test cases)
- PRIMARY_USER configuration loads correctly
- Identity mapping works across systems
- Backwards compatible with existing code
- Integration with Config class seamless

### Functional Success Criteria  
- System knows who the primary user is
- User identity accessible from any module
- Cross-system mapping functional (email ↔ slack_id ↔ calendar_id)
- Graceful handling of missing configuration
- No breaking changes to existing functionality

### Quality Gates
- Code review approved
- Test coverage ≥95% for new code
- Documentation complete
- Integration tests pass
- Performance impact minimal

## Risk Mitigation

### Configuration Risks
- **Missing PRIMARY_USER**: Graceful fallback to non-personalized mode
- **Invalid user identity**: Clear validation and error messages
- **Environment variable issues**: Default values and helpful warnings

### Integration Risks  
- **Breaking existing code**: Extensive backwards compatibility testing
- **Performance impact**: Minimal configuration loading overhead
- **Dependency issues**: Keep module dependencies simple

### Data Risks
- **User not found**: Helpful error messages, don't crash
- **Partial identity mapping**: Work with available data
- **API failures**: Fallback to cached/default behavior

## Completion Criteria

### Code Complete When
- UserIdentity class implemented and tested
- Config integration complete
- Identity mapping functional
- All tests passing
- Backwards compatibility verified

### Agent J Complete When  
- Other agents can use `UserIdentity().get_primary_user()`
- PRIMARY_USER configuration documented
- Integration patterns established
- Foundation ready for Agent K setup wizard
- Agent L can implement personalization

This provides the foundation for Phase 6 user-centric architecture while maintaining lab-grade simplicity and backwards compatibility.