# Agent K: Comprehensive Setup Wizard - Phase 6 Implementation

**Date Created**: 2025-08-28  
**Owner**: Agent K (Setup & Onboarding Team)  
**Status**: PENDING  
**Estimated Time**: 8-12 hours (1-1.5 days)  
**Dependencies**: Agent J (UserIdentity class structure)

## Executive Summary

Create an interactive CLI wizard that guides users through complete AI Chief of Staff system setup from scratch. This includes environment configuration, API credentials, user identity, and validation that everything works correctly.

**Core Philosophy**: Complete, foolproof setup experience that takes a user from zero to fully working system in <5 minutes with clear progress indication and helpful error messages.

## CRITICAL REQUIREMENTS (Complete System Setup)

### Requirement 1: Environment Setup - ESSENTIAL
- **Purpose**: Create all required directories, database, and configuration
- **Implementation**: Interactive prompts with validation
- **Coverage**: AICOS_BASE_DIR, data directories, SQLite database initialization
- **Validation**: Check disk space, permissions, and dependencies

### Requirement 2: API Credential Configuration - ESSENTIAL
- **Purpose**: Set up and validate all external service connections
- **Coverage**: Slack bot tokens, Google Calendar OAuth, Google Drive API
- **Implementation**: Interactive prompts with real-time validation
- **Security**: Encrypted storage of sensitive credentials

### Requirement 3: User Identity Configuration - ESSENTIAL
- **Purpose**: Configure PRIMARY_USER and verify cross-system mapping
- **Implementation**: Use Agent J's UserIdentity class
- **Validation**: Verify user exists in Slack, Calendar, and Drive
- **Mapping**: Establish email ↔ Slack ID ↔ Calendar ID relationships

### Requirement 4: Initial Data Collection & Validation - ESSENTIAL
- **Purpose**: Verify entire system works end-to-end
- **Implementation**: Run collectors, build search index, generate test brief
- **Validation**: Ensure data collection, search, and personalization work
- **Feedback**: Show progress and success confirmation

## Module Architecture

### Relevant Files for Setup Wizard

**Read for Context:**
- `src/core/config.py` - Configuration management and validation patterns
- `src/core/auth_manager.py` - Credential storage and validation approach
- `src/core/user_identity.py` - User identity configuration (Agent J dependency)
- `tools/collect_data.py` - Data collection orchestration patterns
- `src/collectors/base.py` - Collector initialization and validation

**Files to Create:**
- `src/cli/setup_wizard.py` - Main interactive setup wizard
- `src/cli/wizard_steps/` - Individual setup step modules
  - `__init__.py` - Setup steps package
  - `environment_setup.py` - Directory and database setup
  - `slack_setup.py` - Slack configuration and validation
  - `google_setup.py` - Google services (Calendar + Drive) setup
  - `user_setup.py` - PRIMARY_USER configuration
  - `validation_setup.py` - End-to-end system validation
- `tools/setup.py` - Simple entry point for wizard
- `tests/unit/test_setup_wizard.py` - Comprehensive wizard testing
- `tests/integration/test_complete_setup.py` - End-to-end setup testing

**Files to Modify:**
- `src/core/config.py` - Add setup wizard integration methods
- `.env.example` - Update with all required environment variables
- `README.md` - Add setup wizard instructions

**Reference Patterns:**
- `src/core/config.py:46-100` - Configuration validation patterns
- `src/core/auth_manager.py:50-120` - Credential validation approach
- `tools/collect_data.py:30-80` - Progress indication patterns

## Implementation Tasks

### Task K.1: Setup Wizard Framework (2 hours)

**File**: `src/cli/setup_wizard.py`

**Implementation**:
```python
class SetupWizard:
    """Interactive setup wizard for complete system configuration"""
    
    def __init__(self):
        self.config = None
        self.steps_completed = []
        self.setup_data = {}
        
    def run(self):
        """Main wizard flow with progress tracking"""
        print("🚀 AI Chief of Staff Setup Wizard")
        print("=" * 50)
        
        try:
            self.setup_environment()      # Step 1/6
            self.setup_slack()            # Step 2/6  
            self.setup_google()           # Step 3/6
            self.setup_user_identity()    # Step 4/6
            self.validate_setup()         # Step 5/6
            self.run_initial_collection() # Step 6/6
            self.show_success_summary()
        except SetupError as e:
            self.show_error_help(e)
            
    def setup_environment(self):
        """Step 1: Environment and directory setup"""
        
    def setup_slack(self):
        """Step 2: Slack API configuration"""
        
    def setup_google(self):
        """Step 3: Google Calendar and Drive setup"""
        
    def setup_user_identity(self):
        """Step 4: PRIMARY_USER configuration"""
        
    def validate_setup(self):
        """Step 5: Validate all components work"""
        
    def run_initial_collection(self):
        """Step 6: Initial data collection and indexing"""
```

**Acceptance Tests**:
1. Wizard runs from start to finish without errors
2. Each step shows clear progress indication
3. Graceful error handling with helpful messages
4. Resume capability if interrupted
5. Step validation before proceeding
6. Clear success/failure indication
7. Help text available for each step

### Task K.2: Environment Setup Step (1 hour)

**File**: `src/cli/wizard_steps/environment_setup.py`

**Implementation**:
```python
class EnvironmentSetup:
    """Step 1: Environment configuration and directory setup"""
    
    def run(self, wizard_data):
        print("\n[Step 1/6] Environment Setup")
        print("-" * 30)
        
        # Set AICOS_BASE_DIR
        base_dir = self.get_base_directory()
        
        # Create directory structure
        self.create_directories(base_dir)
        
        # Initialize SQLite database
        self.initialize_database(base_dir)
        
        # Check dependencies and disk space
        self.validate_environment(base_dir)
        
        print("✅ Environment setup complete")
        return {"base_dir": base_dir}
```

**Features**:
- Interactive base directory selection (with sensible default)
- Directory creation with permission validation
- SQLite database initialization
- Dependency checking (Python packages)
- Disk space validation (minimum 1GB free)
- .env file creation

**Acceptance Tests**:
1. Prompt for AICOS_BASE_DIR with default
2. Create all required directories (data/, logs/, etc.)
3. Initialize SQLite database with proper schema
4. Validate write permissions on all directories
5. Check minimum disk space requirements
6. Verify Python dependencies are installed
7. Create .env file with base configuration
8. Handle permission errors gracefully
9. Resume if partially completed

### Task K.3: Slack Configuration Step (2 hours)

**File**: `src/cli/wizard_steps/slack_setup.py`

**Implementation**:
```python
class SlackSetup:
    """Step 2: Slack API token configuration and validation"""
    
    def run(self, wizard_data):
        print("\n[Step 2/6] Slack Configuration")  
        print("-" * 30)
        
        # Get workspace information
        workspace = self.get_workspace_info()
        
        # Configure bot token
        bot_token = self.configure_bot_token()
        
        # Validate token and get workspace data
        workspace_data = self.validate_slack_connection(bot_token)
        
        # Store encrypted credentials
        self.store_slack_credentials(bot_token, workspace_data)
        
        print("✅ Slack configuration complete")
        return {"slack_token": bot_token, "workspace": workspace_data}
```

**Features**:
- Workspace name input with validation
- Bot token input with format validation (xoxb-)
- Explain test vs production token differences
- Real-time API connection testing
- User list retrieval for identity mapping
- Scope validation and permission checking
- Encrypted credential storage using auth_manager

**Token Setup Guidance**:
```
Enter your Slack workspace name: biorender
Enter your bot token (starts with xoxb-): 

ℹ️  Bot Token Setup:
   1. Go to https://api.slack.com/apps
   2. Create new app or select existing
   3. Go to OAuth & Permissions
   4. Install app to workspace
   5. Copy Bot User OAuth Token (xoxb-...)

⚠️  Test vs Production:
   - Test: Limited permissions, safe for development
   - Production: Full access, use carefully
```

**Acceptance Tests**:
1. Prompt for workspace name with validation
2. Bot token input with format checking (xoxb- prefix)
3. Real-time token validation with Slack API
4. Retrieve workspace info (name, user count)
5. Get user list for PRIMARY_USER mapping
6. Validate required OAuth scopes
7. Store credentials securely with encryption
8. Handle network errors gracefully
9. Provide clear setup instructions
10. Re-test connection after storage

### Task K.4: Google Services Setup (2 hours)

**File**: `src/cli/wizard_steps/google_setup.py`

**Implementation**:
```python
class GoogleSetup:
    """Step 3: Google Calendar and Drive API setup"""
    
    def run(self, wizard_data):
        print("\n[Step 3/6] Google Services")
        print("-" * 30)
        
        # Configure OAuth credentials
        oauth_creds = self.setup_oauth_credentials()
        
        # Calendar API setup
        calendar_info = self.setup_calendar_api(oauth_creds)
        
        # Drive API setup  
        drive_info = self.setup_drive_api(oauth_creds)
        
        # Store credentials securely
        self.store_google_credentials(oauth_creds, calendar_info, drive_info)
        
        print("✅ Google services configuration complete")
        return {"calendar": calendar_info, "drive": drive_info}
```

**Features**:
- OAuth 2.0 flow guidance and automation
- Browser-based authentication with local callback
- Calendar API authentication and testing
- Drive API authentication and testing
- Calendar list retrieval for user selection
- Service account vs OAuth explanation
- Credential validation and storage

**OAuth Flow Guidance**:
```
Google OAuth Setup:
1. Opening browser for authentication...
2. Sign in to your Google account
3. Grant permissions to AI Chief of Staff
4. Copy authorization code if needed

Testing Calendar API...
✅ Found 3 calendars:
   - david.campos@biorender.com (primary)
   - Meetings@biorender.com
   - Team Events@biorender.com

Testing Drive API...
✅ Drive access confirmed
```

**Acceptance Tests**:
1. Guide user through OAuth 2.0 flow
2. Open browser for authentication
3. Handle authorization code exchange
4. Test Calendar API connection
5. List available calendars
6. Test Drive API connection
7. Validate API permissions and scopes
8. Store credentials securely
9. Handle authentication failures gracefully
10. Re-test APIs after credential storage

### Task K.5: User Identity Setup Step (1 hour)

**File**: `src/cli/wizard_steps/user_setup.py`

**Implementation**:
```python
class UserSetup:
    """Step 4: PRIMARY_USER configuration and validation"""
    
    def run(self, wizard_data):
        print("\n[Step 4/6] User Identity")
        print("-" * 30)
        
        # Get user email
        user_email = self.get_user_email()
        
        # Find user in Slack
        slack_user = self.find_slack_user(user_email, wizard_data['slack'])
        
        # Find user in Calendar  
        calendar_user = self.find_calendar_user(user_email, wizard_data['calendar'])
        
        # Configure PRIMARY_USER
        user_identity = self.configure_primary_user(
            user_email, slack_user, calendar_user
        )
        
        print("✅ User identity configured")
        return {"primary_user": user_identity}
```

**Features**:
- Email input with validation
- Cross-reference with Slack user list
- Verify calendar access for user
- Configure PRIMARY_USER using Agent J's UserIdentity class
- Identity mapping validation
- Optional team member configuration

**User Identity Flow**:
```
Enter your email: david.campos@biorender.com

Finding in Slack workspace...
✅ Found: @david.campos (User ID: U123456789)

Checking Calendar access...  
✅ Found: david.campos@biorender.com

Configuring PRIMARY_USER...
✅ Identity mapping complete:
   Email: david.campos@biorender.com
   Slack: @david.campos (U123456789)
   Calendar: david.campos@biorender.com
```

**Acceptance Tests**:
1. Prompt for user email with validation
2. Search Slack users by email
3. Confirm calendar access for user
4. Configure PRIMARY_USER using UserIdentity class
5. Validate cross-system identity mapping
6. Handle user not found in Slack gracefully
7. Handle calendar access issues
8. Store PRIMARY_USER configuration
9. Confirm identity mapping works
10. Optional: Add team members

### Task K.6: System Validation & Initial Collection (2 hours)

**File**: `src/cli/wizard_steps/validation_setup.py`

**Implementation**:
```python
class ValidationSetup:
    """Steps 5-6: System validation and initial data collection"""
    
    def run(self, wizard_data):
        print("\n[Step 5/6] System Validation")
        print("-" * 30)
        
        # Test all API connections
        self.validate_all_connections(wizard_data)
        
        # Test write permissions and database
        self.validate_storage_systems(wizard_data)
        
        print("\n[Step 6/6] Initial Data Collection")
        print("-" * 30)
        
        # Run collectors for last 7 days
        collection_results = self.run_initial_collection(wizard_data)
        
        # Build search index
        self.build_search_index(collection_results)
        
        # Generate test brief
        test_brief = self.generate_test_brief(wizard_data['primary_user'])
        
        print("✅ System validation and setup complete")
        return {"collection": collection_results, "test_brief": test_brief}
```

**Features**:
- Comprehensive API connection testing
- Database and file system validation
- Initial data collection (7 days)
- Search index building
- Test brief generation
- Performance validation
- Error recovery and retry logic

**Validation Flow**:
```
[Step 5/6] System Validation
Testing Slack connection... ✅
Testing Google Calendar... ✅  
Testing Google Drive... ✅
Validating database... ✅
Checking write permissions... ✅

[Step 6/6] Initial Data Collection
Collecting Slack data (7 days)... 1,543 messages ✅
Collecting Calendar events... 47 events ✅
Collecting Drive changes... 231 files ✅
Building search index... 340,071 records ✅
Generating test brief... ✅

🎉 Setup Complete!
```

**Acceptance Tests**:
1. Test all API connections work
2. Validate database operations
3. Check file system permissions
4. Run collectors for limited time period
5. Verify data collection succeeded
6. Build and test search index
7. Generate personalized test brief
8. Measure setup performance
9. Provide clear success/failure status
10. Show next steps for using system

### Task K.7: Comprehensive Testing (2 hours)

**File**: `tests/unit/test_setup_wizard.py`

**Test Categories**:
1. **Wizard Framework Tests**:
   - Complete wizard flow succeeds
   - Step-by-step progression tracking
   - Error handling and recovery
   - Resume capability after interruption
   - Progress indication accuracy

2. **Environment Setup Tests**:
   - Directory creation with permissions
   - Database initialization
   - Dependency validation
   - Disk space checking
   - .env file creation

3. **API Configuration Tests**:
   - Slack token validation
   - Google OAuth flow simulation
   - API connection testing  
   - Credential storage security
   - Permission validation

4. **User Identity Tests**:
   - Email validation and mapping
   - Slack user lookup
   - Calendar user verification
   - PRIMARY_USER configuration
   - Cross-system identity validation

5. **Validation Tests**:
   - End-to-end system testing
   - Data collection validation
   - Search index building
   - Brief generation testing
   - Performance measurement

**Integration Testing** (`tests/integration/test_complete_setup.py`):
- Full wizard run from start to finish
- Real API connections (with test credentials)
- Complete data flow validation
- Performance benchmarking
- Error scenario testing

## User Experience Design

### Progress Indication
```
🚀 AI Chief of Staff Setup Wizard
==================================

[●●●●●○] Step 5/6: System Validation
⏱️  Estimated time remaining: 2 minutes

Testing API connections...
✅ Slack connection successful
✅ Google Calendar authorized
✅ Google Drive accessible
```

### Error Handling
```
❌ Setup Error: Slack Token Invalid

The bot token you entered doesn't work:
• Token format: Must start with 'xoxb-'  
• Token status: Invalid or expired
• Workspace: Not found or no permissions

📋 How to fix:
1. Go to https://api.slack.com/apps
2. Select your app
3. Go to OAuth & Permissions
4. Copy Bot User OAuth Token

Would you like to try again? [y/N]:
```

### Success Summary
```
🎉 Setup Complete!

Your AI Chief of Staff is ready to use:

📊 System Status:
• APIs configured: Slack ✅ Calendar ✅ Drive ✅  
• Data collected: 1,590 messages, 47 events, 231 files
• Search index: 340,071 records ready
• PRIMARY_USER: david.campos@biorender.com

🚀 Quick Start:
• Daily brief: python tools/daily_summary.py
• Search: python tools/search_cli.py "meeting notes"
• Dashboard: python app.py

📖 Documentation: README.md
```

## Integration Points

### With Existing Components
- **Config System**: Uses and extends existing Config class
- **Auth Manager**: Leverages credential storage and validation
- **Collectors**: Runs initial collection to validate setup
- **Search System**: Builds initial search index
- **User Identity**: Uses Agent J's UserIdentity class
- **CLI Tools**: Validates all tools work after setup

### Setup Wizard API
```python
from src.cli.setup_wizard import SetupWizard

# Run complete setup
wizard = SetupWizard()
result = wizard.run()

# Check setup status
if result.success:
    print("Setup completed successfully")
else:
    print(f"Setup failed: {result.error}")

# Re-run specific steps
wizard.setup_slack()  # Re-configure Slack only
```

## Success Metrics

### Technical Success Criteria
- Setup completes in <5 minutes with clear progress
- All API credentials validated and stored securely
- PRIMARY_USER configured and identity mapped
- Initial data collection and indexing successful
- All system components working after setup

### User Experience Success Criteria
- Clear, helpful progress indication throughout
- Error messages provide actionable guidance
- Setup can be resumed if interrupted
- Success confirmation with next steps
- No manual configuration file editing required

### Quality Gates
- 95% test coverage for wizard components
- All error scenarios handled gracefully
- Performance meets time targets (<5 minutes)
- Security review for credential handling
- User testing with fresh installations

## Risk Mitigation

### Setup Failure Risks
- **Network issues**: Retry logic and offline graceful degradation
- **Permission problems**: Clear error messages and fix guidance
- **Invalid credentials**: Real-time validation and retry prompts
- **Disk space**: Pre-flight checks and requirements display

### Security Risks
- **Credential exposure**: Encrypted storage only, no plaintext
- **Token validation**: Real API calls to verify permissions
- **File permissions**: Validate secure storage locations
- **OAuth flow**: Secure browser-based authentication

### User Experience Risks
- **Complex setup**: Step-by-step guidance with progress indication
- **Setup interruption**: Resume capability from any step
- **Unclear errors**: Helpful error messages with fix instructions
- **Time pressure**: Clear time expectations and progress updates

## Completion Criteria

### Code Complete When
- All setup wizard components implemented
- Comprehensive test coverage (95%+)
- Integration with Agent J's UserIdentity class
- Secure credential storage and validation
- Clear error handling and recovery

### Agent K Complete When
- Setup wizard runs fresh installations successfully
- All API credentials configured and validated
- PRIMARY_USER identity established and mapped
- Initial data collection and indexing works
- Clear success confirmation and next steps
- Agent L can implement personalization using configured identity

This creates a comprehensive, foolproof setup experience that takes users from zero to fully functional AI Chief of Staff system in minutes.