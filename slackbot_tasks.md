# Slack Bot Integration - Phase 4 Complete Implementation Plan (ENHANCED SECURITY)

**Date Created**: 2025-08-21  
**Date Updated**: 2025-08-21 (OAuth Integration)  
**Owner**: Phase 4 Slack Bot Team  
**Status**: PENDING  
**Estimated Time**: 5 days (40 hours)  
**Dependencies**: Phase 1 complete ✅, Search infrastructure ✅, Query engines ✅, Calendar coordination ✅, **NEW**: OAuth scope management ✅, Permission checker ✅, Encrypted credentials ✅

## Executive Summary

Implement comprehensive Slack bot interface that exposes all Phase 1 deterministic functionality through natural slash commands with enterprise-grade security and permission management. The bot acts as a thin orchestration layer over existing CLI tools, providing native Slack experience without duplicating business logic.

**Core Philosophy**: Zero new business logic - only secure user interface and workflow coordination. All operations delegate to existing deterministic tools with proven reliability, enhanced with comprehensive OAuth scope validation, proactive permission checking, and encrypted credential management.

## CRITICAL DEPENDENCIES ANALYSIS

### Existing Infrastructure ✅ (All Available)
- **slack-sdk==3.33.2** and **slack-bolt==1.21.2** - Already in requirements/base.txt
- **Search Infrastructure** - 340,071 records indexed, <1s response time
- **Query Engines** - Time, person, structured extraction all operational
- **Calendar Coordination** - AvailabilityEngine and ConflictDetector implemented
- **Authentication System** - credential_vault with Google/Slack API access
- **CLI Tools** - All 7 tools (search_cli.py, find_slots.py, etc.) functional

### New Dependencies Required
- None - all required infrastructure already implemented
- **ENHANCED**: OAuth scope management system (84 permissions) integrated ✅
- **ENHANCED**: Runtime permission checker with 40+ API endpoint validation ✅
- **ENHANCED**: Encrypted credential storage with AES-256 security ✅

## Slack Bot Architecture

### Relevant Files for Slack Bot Integration

**Read for Context:**
- `requirements/base.txt:14-16` - Slack SDK dependencies already available
- `src/core/auth_manager.py` - Enhanced authentication with OAuth scope management
- `src/core/slack_scopes.py` - Comprehensive 84-scope OAuth definitions ⭐
- `src/core/permission_checker.py` - Runtime API permission validation ⭐
- `data/auth/slack_scopes.json` - Persistent scope storage configuration ⭐
- `src/collectors/slack_collector.py:19-50` - SlackRateLimiter patterns for bot API calls
- `src/search/database.py` - Direct database access for fast search responses
- `tools/search_cli.py` - CLI patterns to wrap for bot commands
- `tools/find_slots.py` - Calendar coordination patterns for /cos schedule
- `tools/query_facts.py` - Pattern extraction for goals/commitments
- `tools/daily_summary.py` - Briefing generation for /cos brief

**Files to Create:**
- `src/bot/__init__.py` - Bot module initialization
- `src/bot/slack_bot.py` - Main Slack Bolt application with OAuth integration
- `src/bot/auth/oauth_handler.py` - OAuth 2.0 flow implementation ⭐
- `src/bot/auth/scope_validator.py` - Runtime scope validation ⭐
- `src/bot/commands/base_command.py` - Base command with @require_permissions ⭐
- `src/bot/commands/search.py` - /cos search command handler
- `src/bot/commands/schedule.py` - /cos schedule command handler
- `src/bot/commands/goals.py` - /cos goals command handler
- `src/bot/commands/brief.py` - /cos brief command handler
- `src/bot/commands/commitments.py` - /cos commitments command handler
- `src/bot/commands/admin.py` - /cos admin command handler ⭐
- `src/bot/commands/help.py` - /cos help command handler
- `src/bot/middleware/permission_check.py` - Permission validation middleware ⭐
- `src/bot/middleware/rate_limiter.py` - Dual-mode rate limiting ⭐
- `src/bot/middleware/audit_logger.py` - Security audit trail ⭐
- `src/bot/utils/formatters.py` - Slack Block Kit formatting utilities
- `src/bot/utils/async_bridge.py` - Async/sync bridge for CLI tools
- `src/bot/utils/scope_helpers.py` - OAuth scope utilities ⭐
- `src/bot/integrations/cli_wrapper.py` - Secure CLI tool integration wrapper
- `tools/run_slack_bot.py` - Bot deployment script with security validation
- `tests/bot/test_slack_commands.py` - Enhanced bot command test suite
- `tests/bot/test_oauth_security.py` - OAuth and security test suite ⭐

**Reference Patterns:**
- `src/collectors/slack_collector.py:36-50` - Slack API rate limiting patterns
- `src/cli/formatters.py` - Output formatting patterns for consistent display
- `src/core/config.py:59-85` - Configuration validation patterns
- `tests/unit/test_query_engine.py` - Test patterns for async operations

## Test-Driven Development Plan

### Phase 4a: Bot Foundation with OAuth Integration (Day 1 - 8 hours)

#### Test Acceptance Criteria (Write FIRST)

**File**: `tests/bot/test_slack_bot_foundation.py`
```python
import pytest
from unittest.mock import Mock, patch, AsyncMock
from slack_bolt.async_app import AsyncApp
from slack_bolt.request.async_request import AsyncBoltRequest

from src.bot.slack_bot import AICOSSlackBot
from src.bot.utils.async_bridge import AsyncCLIBridge

class TestSlackBotFoundation:
    """Test core Slack bot initialization and routing"""
    
    @pytest.fixture
    def mock_slack_app(self):
        """Mock Slack Bolt app for testing"""
        app = Mock(spec=AsyncApp)
        app.command = Mock()
        app.event = Mock()
        app.action = Mock()
        return app
    
    @pytest.fixture  
    def bot_instance(self, mock_slack_app):
        """Initialize bot with mocked Slack app"""
        with patch('src.bot.slack_bot.AsyncApp', return_value=mock_slack_app):
            return AICOSSlackBot()
    
    def test_bot_initialization_with_credentials(self, bot_instance):
        """Bot initializes with proper Slack credentials and OAuth validation"""
        # Should initialize without errors
        assert bot_instance is not None
        assert hasattr(bot_instance, 'app')
        assert hasattr(bot_instance, 'cli_bridge')
        assert hasattr(bot_instance, 'permission_checker')
        assert hasattr(bot_instance, 'oauth_handler')
        
        # Should validate Slack token exists
        assert bot_instance.slack_token is not None
        assert bot_instance.slack_token.startswith('xoxb-')
        
        # Should validate comprehensive OAuth scopes
        scopes = bot_instance.get_available_scopes()
        assert 'chat:write' in scopes
        assert 'channels:read' in scopes
        assert len(scopes) >= 40  # Should have comprehensive permissions
    
    def test_slash_command_registration(self, bot_instance, mock_slack_app):
        """All slash commands properly registered"""
        expected_commands = [
            '/cos-search', '/cos-schedule', '/cos-goals', 
            '/cos-brief', '/cos-commitments', '/cos-admin', '/cos-help'
        ]
        
        # Verify all commands were registered
        assert mock_slack_app.command.call_count == len(expected_commands)
        
        # Check specific command patterns
        registered_commands = [call[0][0] for call in mock_slack_app.command.call_args_list]
        for cmd in expected_commands:
            assert cmd in registered_commands
    
    def test_event_handlers_registration(self, bot_instance, mock_slack_app):
        """Event handlers properly registered for bot mentions"""
        # Should register app_mention event
        mock_slack_app.event.assert_any_call("app_mention")
        
        # Should register message events in bot DMs
        mock_slack_app.event.assert_any_call("message")
    
    def test_error_handling_middleware(self, bot_instance):
        """Error handling middleware properly configured"""
        # Should have global error handler
        assert hasattr(bot_instance, 'handle_global_error')
        
        # Should capture and log all errors
        with patch('src.bot.slack_bot.logger') as mock_logger:
            error = Exception("Test error")
            bot_instance.handle_global_error(error, None, None)
            mock_logger.error.assert_called_once()
    
    def test_rate_limiting_configuration(self, bot_instance):
        """Dual-mode rate limiting properly configured for Slack API"""
        # Should have dual-mode rate limiter
        assert hasattr(bot_instance, 'rate_limiter')
        assert hasattr(bot_instance.rate_limiter, 'interactive_mode')
        assert hasattr(bot_instance.rate_limiter, 'bulk_mode')
        
        # Interactive mode should be faster for bot responses
        assert bot_instance.rate_limiter.interactive_delay <= 1.0
        # Bulk mode should be conservative
        assert bot_instance.rate_limiter.bulk_delay >= 2.0
    
    def test_oauth_scope_validation(self, bot_instance):
        """OAuth scope validation integrated and functional"""
        # Should validate required scopes for API operations
        validation = bot_instance.validate_api_permissions('chat.postMessage')
        assert validation['valid'] == True
        assert 'chat:write' in validation.get('satisfied_scopes', [])
        
        # Should handle missing scopes gracefully
        fake_validation = bot_instance.validate_api_permissions('fake.api', ['fake:scope'])
        assert 'missing_scopes' in fake_validation
    
    def test_permission_checker_integration(self, bot_instance):
        """Permission checker properly integrated with all commands"""
        # Should have permission checker available
        assert hasattr(bot_instance, 'permission_checker')
        assert bot_instance.permission_checker is not None
        
        # Should validate common API endpoints
        search_check = bot_instance.permission_checker.check_api_permissions('search.messages')
        assert 'required_scopes' in search_check
        assert 'search:read' in search_check['required_scopes']

class TestAsyncCLIBridge:
    """Test async/sync bridge for CLI tool integration"""
    
    @pytest.fixture
    def cli_bridge(self):
        """Initialize CLI bridge"""
        return AsyncCLIBridge()
    
    @pytest.mark.asyncio
    async def test_search_cli_integration(self, cli_bridge):
        """Bridge properly calls search_cli.py and returns results"""
        with patch('subprocess.run') as mock_subprocess:
            # Mock successful search CLI response
            mock_subprocess.return_value.returncode = 0
            mock_subprocess.return_value.stdout = '''
            {
                "results": [
                    {"text": "Test message", "source": "slack", "timestamp": "2025-08-21T10:00:00Z"}
                ],
                "total_count": 1,
                "query_time_ms": 234
            }
            '''
            
            result = await cli_bridge.execute_search("test query")
            
            assert result['total_count'] == 1
            assert result['query_time_ms'] < 1000  # <1s requirement
            assert len(result['results']) == 1
    
    @pytest.mark.asyncio
    async def test_calendar_cli_integration(self, cli_bridge):
        """Bridge properly calls find_slots.py and returns slots"""
        with patch('subprocess.run') as mock_subprocess:
            mock_subprocess.return_value.returncode = 0
            mock_subprocess.return_value.stdout = '''
            {
                "available_slots": [
                    {"start": "2025-08-21T14:00:00Z", "end": "2025-08-21T15:00:00Z", "duration_minutes": 60}
                ],
                "conflicts": [],
                "search_time_ms": 1234
            }
            '''
            
            result = await cli_bridge.execute_calendar_search("@john.doe", "60")
            
            assert len(result['available_slots']) == 1
            assert result['search_time_ms'] < 5000  # <5s requirement
    
    @pytest.mark.asyncio
    async def test_cli_error_handling(self, cli_bridge):
        """Bridge properly handles CLI tool errors"""
        with patch('subprocess.run') as mock_subprocess:
            # Mock CLI tool failure
            mock_subprocess.return_value.returncode = 1
            mock_subprocess.return_value.stderr = "Database connection failed"
            
            with pytest.raises(Exception) as excinfo:
                await cli_bridge.execute_search("test query")
            
            assert "Database connection failed" in str(excinfo.value)
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self, cli_bridge):
        """Bridge handles CLI tool timeouts gracefully"""
        with patch('asyncio.wait_for') as mock_wait:
            mock_wait.side_effect = asyncio.TimeoutError()
            
            with pytest.raises(Exception) as excinfo:
                await cli_bridge.execute_search("test query", timeout=30)
            
            assert "timeout" in str(excinfo.value).lower()

class TestSlackAuthentication:
    """Test Slack app authentication and permissions"""
    
    def test_oauth_token_validation(self):
        """Bot validates OAuth token format and permissions"""
        from src.bot.slack_bot import validate_slack_credentials
        
        # Should accept valid bot token
        valid_token = "xoxb-EXAMPLE-TOKEN-FORMAT"
        assert validate_slack_credentials(valid_token) == True
        
        # Should reject invalid token formats
        invalid_tokens = [
            "invalid-token",
            "xoxp-1234567890-1234567890123-abcdefghijklmnopqrstuvwx",  # User token
            None,
            ""
        ]
        
        for token in invalid_tokens:
            assert validate_slack_credentials(token) == False
    
    def test_required_scopes_validation(self):
        """Bot validates required Slack scopes are granted"""
        from src.bot.slack_bot import validate_bot_scopes
        
        required_scopes = [
            'app_mentions:read', 'chat:write', 'commands', 
            'channels:read', 'users:read', 'im:history'
        ]
        
        # Should pass with all required scopes
        assert validate_bot_scopes(required_scopes) == True
        
        # Should fail with missing scopes
        incomplete_scopes = ['chat:write', 'commands']
        assert validate_bot_scopes(incomplete_scopes) == False

class TestBotConfiguration:
    """Test bot configuration and environment setup"""
    
    def test_environment_variable_loading(self):
        """Bot loads configuration from environment variables"""
        with patch.dict('os.environ', {
            'SLACK_BOT_TOKEN': 'xoxb-test-token',
            'SLACK_SIGNING_SECRET': 'test-signing-secret',
            'AICOS_BASE_DIR': '/tmp/test-aicos'
        }):
            from src.bot.slack_bot import BotConfig
            config = BotConfig()
            
            assert config.slack_bot_token == 'xoxb-test-token'
            assert config.signing_secret == 'test-signing-secret'
            assert config.base_dir == '/tmp/test-aicos'
    
    def test_configuration_validation(self):
        """Bot validates all required configuration before starting"""
        from src.bot.slack_bot import BotConfig
        
        # Should fail with missing required vars
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(Exception) as excinfo:
                BotConfig()
            assert "SLACK_BOT_TOKEN" in str(excinfo.value)
    
    def test_database_connection_validation(self):
        """Bot validates database connection on startup"""
        from src.bot.slack_bot import validate_database_connection
        
        # Should succeed with valid database
        with patch('src.search.database.SearchDatabase') as mock_db:
            mock_db.return_value.test_connection.return_value = True
            assert validate_database_connection() == True
        
        # Should fail with invalid database
        with patch('src.search.database.SearchDatabase') as mock_db:
            mock_db.return_value.test_connection.side_effect = Exception("Connection failed")
            assert validate_database_connection() == False
```

#### Implementation Tasks

**Task 4a.1: Slack Bolt Application Setup (2 hours)**
- Create AICOSSlackBot class with AsyncApp initialization
- Configure OAuth 2.0 with proper scopes (app_mentions:read, chat:write, commands)
- Set up signing secret validation and token verification
- Add environment variable loading with validation

**Task 4a.2: Slash Command Router Framework (2 hours)**
- Implement command registration system for all /cos commands
- Create base SlackCommand class with common patterns
- Add command parameter parsing and validation
- Implement command help system with usage examples

**Task 4a.3: CLI Tool Integration Bridge (2 hours)**
- Create AsyncCLIBridge for sync→async CLI tool calls
- Implement subprocess execution with timeout handling
- Add JSON response parsing and validation
- Create error handling for CLI tool failures

**Task 4a.4: Rate Limiting and Error Handling (2 hours)**
- Integrate SlackRateLimiter patterns for bot API calls
- Implement global error handler with user-friendly messages
- Add retry logic for transient failures
- Create comprehensive logging for all operations

### Phase 4b: Search & Brief Commands (Day 2 - 8 hours)

#### Test Acceptance Criteria (Write FIRST)

**File**: `tests/bot/test_search_brief_commands.py`
```python
import pytest
from unittest.mock import Mock, patch, AsyncMock
from slack_bolt.context.async_context import AsyncBoltContext

from src.bot.commands.search import SearchCommand
from src.bot.commands.brief import BriefCommand
from src.bot.utils.formatters import SlackBlockFormatter

class TestSearchCommand:
    """Test /cos search command implementation"""
    
    @pytest.fixture
    def search_command(self):
        """Initialize search command handler"""
        return SearchCommand()
    
    @pytest.fixture
    def mock_ack(self):
        """Mock Slack ack function"""
        return AsyncMock()
    
    @pytest.fixture
    def mock_respond(self):
        """Mock Slack respond function"""
        return AsyncMock()
    
    @pytest.fixture
    def mock_command_request(self):
        """Mock Slack command request"""
        return {
            'text': 'meeting notes from last week',
            'user_id': 'U123456',
            'channel_id': 'C123456',
            'team_id': 'T123456'
        }
    
    @pytest.mark.asyncio
    async def test_search_basic_query(self, search_command, mock_ack, mock_respond, mock_command_request):
        """Basic search query returns formatted results"""
        with patch('src.bot.integrations.cli_wrapper.execute_search') as mock_search:
            # Mock search results
            mock_search.return_value = {
                'results': [
                    {
                        'text': 'Important meeting notes about Q3 planning',
                        'source': 'slack',
                        'channel': 'general',
                        'timestamp': '2025-08-15T14:30:00Z',
                        'author': 'john.doe@company.com'
                    },
                    {
                        'text': 'Follow-up on Q3 planning discussion',
                        'source': 'slack', 
                        'channel': 'product',
                        'timestamp': '2025-08-16T10:15:00Z',
                        'author': 'jane.smith@company.com'
                    }
                ],
                'total_count': 2,
                'query_time_ms': 450
            }
            
            await search_command.handle(
                command=mock_command_request,
                ack=mock_ack,
                respond=mock_respond
            )
            
            # Should acknowledge immediately
            mock_ack.assert_called_once()
            
            # Should respond with formatted results
            mock_respond.assert_called_once()
            response_blocks = mock_respond.call_args[1]['blocks']
            
            # Verify response structure
            assert len(response_blocks) >= 3  # Header + results + footer
            assert 'Found 2 results' in str(response_blocks)
            assert 'Q3 planning' in str(response_blocks)
            assert '450ms' in str(response_blocks)  # Query time
    
    @pytest.mark.asyncio
    async def test_search_no_results(self, search_command, mock_ack, mock_respond, mock_command_request):
        """Search with no results returns helpful message"""
        mock_command_request['text'] = 'nonexistent query xyz123'
        
        with patch('src.bot.integrations.cli_wrapper.execute_search') as mock_search:
            mock_search.return_value = {
                'results': [],
                'total_count': 0,
                'query_time_ms': 123
            }
            
            await search_command.handle(
                command=mock_command_request,
                ack=mock_ack, 
                respond=mock_respond
            )
            
            mock_respond.assert_called_once()
            response_text = str(mock_respond.call_args)
            
            assert 'No results found' in response_text
            assert 'nonexistent query xyz123' in response_text
            assert 'Try different keywords' in response_text
    
    @pytest.mark.asyncio
    async def test_search_pagination(self, search_command, mock_ack, mock_respond, mock_command_request):
        """Search with many results includes pagination"""
        with patch('src.bot.integrations.cli_wrapper.execute_search') as mock_search:
            # Mock large result set
            mock_results = []
            for i in range(25):  # More than default page size
                mock_results.append({
                    'text': f'Result {i+1} content',
                    'source': 'slack',
                    'channel': 'general',
                    'timestamp': f'2025-08-{15+i%7:02d}T10:00:00Z'
                })
            
            mock_search.return_value = {
                'results': mock_results,
                'total_count': 25,
                'query_time_ms': 890
            }
            
            await search_command.handle(
                command=mock_command_request,
                ack=mock_ack,
                respond=mock_respond
            )
            
            response_blocks = mock_respond.call_args[1]['blocks']
            
            # Should show first page (10 results)
            assert 'Showing 1-10 of 25 results' in str(response_blocks)
            
            # Should include "Load More" button
            assert any('Load More' in str(block) for block in response_blocks)
    
    @pytest.mark.asyncio
    async def test_search_error_handling(self, search_command, mock_ack, mock_respond, mock_command_request):
        """Search handles database errors gracefully"""
        with patch('src.bot.integrations.cli_wrapper.execute_search') as mock_search:
            mock_search.side_effect = Exception("Database connection failed")
            
            await search_command.handle(
                command=mock_command_request,
                ack=mock_ack,
                respond=mock_respond
            )
            
            mock_respond.assert_called_once()
            response_text = str(mock_respond.call_args)
            
            assert 'Search temporarily unavailable' in response_text
            assert 'try again' in response_text.lower()
            # Should not expose internal error details to user
            assert 'Database connection failed' not in response_text
    
    @pytest.mark.asyncio
    async def test_search_performance_tracking(self, search_command, mock_ack, mock_respond, mock_command_request):
        """Search tracks and reports performance metrics"""
        with patch('src.bot.integrations.cli_wrapper.execute_search') as mock_search:
            mock_search.return_value = {
                'results': [],
                'total_count': 0,
                'query_time_ms': 1500  # Slower than target
            }
            
            with patch('src.bot.utils.metrics.record_search_performance') as mock_metrics:
                await search_command.handle(
                    command=mock_command_request,
                    ack=mock_ack,
                    respond=mock_respond
                )
                
                # Should record performance metrics
                mock_metrics.assert_called_once_with(
                    query='meeting notes from last week',
                    result_count=0,
                    response_time_ms=1500,
                    user_id='U123456'
                )

class TestBriefCommand:
    """Test /cos brief command implementation"""
    
    @pytest.fixture
    def brief_command(self):
        """Initialize brief command handler"""
        return BriefCommand()
    
    @pytest.mark.asyncio
    async def test_daily_brief_generation(self, brief_command, mock_ack, mock_respond, mock_command_request):
        """Daily brief generates comprehensive summary"""
        with patch('src.bot.integrations.cli_wrapper.execute_daily_summary') as mock_summary:
            mock_summary.return_value = {
                'date': '2025-08-21',
                'summary_sections': {
                    'key_updates': [
                        'Q3 planning meeting scheduled for Friday',
                        '3 new team members joining next week'
                    ],
                    'active_goals': [
                        {'title': 'Complete hiring for engineering team', 'progress': 75, 'due': '2025-08-30'},
                        {'title': 'Finalize Q4 roadmap', 'progress': 45, 'due': '2025-09-15'}
                    ],
                    'commitments_due': [
                        {'description': 'Send budget forecast to board', 'due': '2025-08-22', 'assignee': 'david@company.com'}
                    ],
                    'meeting_highlights': [
                        {'title': 'Weekly team sync', 'key_decisions': ['Approved new feature timeline']}
                    ]
                },
                'stats': {
                    'total_messages': 142,
                    'meetings_attended': 6,
                    'documents_modified': 8
                },
                'generation_time_ms': 2340
            }
            
            await brief_command.handle(
                command=mock_command_request,
                ack=mock_ack,
                respond=mock_respond
            )
            
            mock_respond.assert_called_once()
            response_blocks = mock_respond.call_args[1]['blocks']
            
            # Verify brief structure
            assert 'Daily Brief - August 21, 2025' in str(response_blocks)
            assert 'Q3 planning meeting' in str(response_blocks)
            assert '75% complete' in str(response_blocks)  # Goal progress
            assert 'Send budget forecast' in str(response_blocks)  # Commitment
            assert '142 messages' in str(response_blocks)  # Stats
    
    @pytest.mark.asyncio
    async def test_brief_with_no_activity(self, brief_command, mock_ack, mock_respond, mock_command_request):
        """Brief handles days with minimal activity"""
        with patch('src.bot.integrations.cli_wrapper.execute_daily_summary') as mock_summary:
            mock_summary.return_value = {
                'date': '2025-08-21',
                'summary_sections': {
                    'key_updates': [],
                    'active_goals': [],
                    'commitments_due': [],
                    'meeting_highlights': []
                },
                'stats': {
                    'total_messages': 3,
                    'meetings_attended': 0,
                    'documents_modified': 0
                },
                'generation_time_ms': 456
            }
            
            await brief_command.handle(
                command=mock_command_request,
                ack=mock_ack,
                respond=mock_respond
            )
            
            response_blocks = mock_respond.call_args[1]['blocks']
            
            assert 'Quiet day' in str(response_blocks)
            assert 'No major updates' in str(response_blocks)
    
    @pytest.mark.asyncio
    async def test_brief_custom_date_range(self, brief_command, mock_ack, mock_respond):
        """Brief supports custom date ranges"""
        custom_command = {
            'text': 'last_week',  # Custom range
            'user_id': 'U123456',
            'channel_id': 'C123456'
        }
        
        with patch('src.bot.integrations.cli_wrapper.execute_daily_summary') as mock_summary:
            mock_summary.return_value = {
                'date_range': '2025-08-14 to 2025-08-20',
                'summary_sections': {'key_updates': ['Weekly summary data']},
                'stats': {'total_messages': 450},
                'generation_time_ms': 3400
            }
            
            await brief_command.handle(
                command=custom_command,
                ack=mock_ack,
                respond=mock_respond
            )
            
            response_blocks = mock_respond.call_args[1]['blocks']
            
            assert 'August 14-20, 2025' in str(response_blocks)
            assert 'Weekly summary data' in str(response_blocks)

class TestSlackBlockFormatter:
    """Test Slack Block Kit formatting utilities"""
    
    @pytest.fixture
    def formatter(self):
        """Initialize block formatter"""
        return SlackBlockFormatter()
    
    def test_search_results_formatting(self, formatter):
        """Search results format properly with Block Kit"""
        results = [
            {
                'text': 'Important meeting about Q3 planning',
                'source': 'slack',
                'channel': 'general',
                'author': 'john.doe@company.com',
                'timestamp': '2025-08-15T14:30:00Z'
            }
        ]
        
        blocks = formatter.format_search_results(results, total_count=1, query_time=450)
        
        # Should return valid Block Kit structure
        assert isinstance(blocks, list)
        assert len(blocks) >= 2  # Header + result
        
        # Check header block
        header_block = blocks[0]
        assert header_block['type'] == 'header'
        assert 'Found 1 result' in header_block['text']['text']
        
        # Check result block
        result_block = blocks[1]
        assert result_block['type'] == 'section'
        assert 'Q3 planning' in result_block['text']['text']
        assert '#general' in result_block['text']['text']
        assert 'john.doe' in result_block['text']['text']
    
    def test_brief_formatting(self, formatter):
        """Brief formats properly with rich blocks"""
        brief_data = {
            'date': '2025-08-21',
            'summary_sections': {
                'key_updates': ['Important update 1', 'Important update 2'],
                'active_goals': [
                    {'title': 'Complete project X', 'progress': 80, 'due': '2025-08-30'}
                ]
            },
            'stats': {'total_messages': 142}
        }
        
        blocks = formatter.format_daily_brief(brief_data)
        
        assert isinstance(blocks, list)
        assert len(blocks) >= 3  # Header + sections + stats
        
        # Check structure
        assert any('Daily Brief' in str(block) for block in blocks)
        assert any('Important update 1' in str(block) for block in blocks)
        assert any('80%' in str(block) for block in blocks)  # Progress
        assert any('142 messages' in str(block) for block in blocks)
    
    def test_error_message_formatting(self, formatter):
        """Error messages format with helpful guidance"""
        error_blocks = formatter.format_error_message(
            title="Search Unavailable",
            message="The search system is temporarily unavailable. Please try again in a few minutes.",
            include_help=True
        )
        
        assert isinstance(error_blocks, list)
        assert len(error_blocks) >= 1
        
        # Should include error emoji and helpful message
        assert ':warning:' in str(error_blocks) or '⚠️' in str(error_blocks)
        assert 'try again' in str(error_blocks)
        
        # Should include help option when requested
        assert 'help' in str(error_blocks).lower()
```

#### Implementation Tasks

**Task 4b.1: Search Command Implementation (3 hours)**
- Create SearchCommand class with direct SearchDatabase integration
- Implement natural language query parsing and filtering
- Add Slack Block Kit formatting for rich search results
- Create pagination for large result sets

**Task 4b.2: Brief Command Implementation (2 hours)**  
- Create BriefCommand wrapper for daily_summary.py
- Implement custom date range support (today, yesterday, last_week)
- Add rich formatting for brief sections (updates, goals, commitments)
- Create summary statistics display

**Task 4b.3: Slack Block Kit Formatters (2 hours)**
- Create SlackBlockFormatter utility class
- Implement search result formatting with source attribution
- Add brief formatting with sections and progress indicators
- Create error message formatting with actionable guidance

**Task 4b.4: Async Operations & Performance (1 hour)**
- Implement progress indicators for long-running operations
- Add performance tracking and metrics collection
- Create timeout handling for CLI tool calls
- Add result caching for common queries

### Phase 4c: Calendar & Goals Commands (Day 3 - 8 hours)

#### Test Acceptance Criteria (Write FIRST)

**File**: `tests/bot/test_calendar_goals_commands.py`
```python
import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta

from src.bot.commands.schedule import ScheduleCommand
from src.bot.commands.goals import GoalsCommand

class TestScheduleCommand:
    """Test /cos schedule command implementation"""
    
    @pytest.fixture
    def schedule_command(self):
        """Initialize schedule command handler"""
        return ScheduleCommand()
    
    @pytest.mark.asyncio
    async def test_schedule_single_person(self, schedule_command, mock_ack, mock_respond):
        """Schedule meeting with single person"""
        command_request = {
            'text': '@john.doe 60min',
            'user_id': 'U123456',
            'channel_id': 'C123456'
        }
        
        with patch('src.bot.integrations.cli_wrapper.execute_calendar_search') as mock_calendar:
            mock_calendar.return_value = {
                'available_slots': [
                    {
                        'start': '2025-08-22T14:00:00Z',
                        'end': '2025-08-22T15:00:00Z', 
                        'duration_minutes': 60,
                        'attendees': ['requester@company.com', 'john.doe@company.com']
                    },
                    {
                        'start': '2025-08-22T15:30:00Z',
                        'end': '2025-08-22T16:30:00Z',
                        'duration_minutes': 60,
                        'attendees': ['requester@company.com', 'john.doe@company.com']
                    }
                ],
                'conflicts': [],
                'search_time_ms': 1200
            }
            
            await schedule_command.handle(
                command=command_request,
                ack=mock_ack,
                respond=mock_respond
            )
            
            mock_respond.assert_called_once()
            response_blocks = mock_respond.call_args[1]['blocks']
            
            # Should show available slots
            assert 'Found 2 available slots' in str(response_blocks)
            assert '2:00 PM - 3:00 PM' in str(response_blocks)
            assert '3:30 PM - 4:30 PM' in str(response_blocks)
            
            # Should include booking buttons
            assert any('Book This Slot' in str(block) for block in response_blocks)
    
    @pytest.mark.asyncio 
    async def test_schedule_multiple_people(self, schedule_command, mock_ack, mock_respond):
        """Schedule meeting with multiple people"""
        command_request = {
            'text': '@john.doe @jane.smith @bob.wilson 45min',
            'user_id': 'U123456',
            'channel_id': 'C123456'
        }
        
        with patch('src.bot.integrations.cli_wrapper.execute_calendar_search') as mock_calendar:
            mock_calendar.return_value = {
                'available_slots': [
                    {
                        'start': '2025-08-23T10:00:00Z',
                        'end': '2025-08-23T10:45:00Z',
                        'duration_minutes': 45,
                        'attendees': [
                            'requester@company.com',
                            'john.doe@company.com', 
                            'jane.smith@company.com',
                            'bob.wilson@company.com'
                        ]
                    }
                ],
                'conflicts': [
                    {
                        'person': 'bob.wilson@company.com',
                        'conflicting_meeting': 'Daily standup',
                        'time': '2025-08-23T11:00:00Z'
                    }
                ],
                'search_time_ms': 2300
            }
            
            await schedule_command.handle(
                command=command_request,
                ack=mock_ack,
                respond=mock_respond
            )
            
            response_blocks = mock_respond.call_args[1]['blocks']
            
            # Should show available slots for all attendees
            assert '4 attendees' in str(response_blocks)
            assert '10:00 AM - 10:45 AM' in str(response_blocks)
            
            # Should show conflicts
            assert 'bob.wilson has conflict' in str(response_blocks)
            assert 'Daily standup' in str(response_blocks)
    
    @pytest.mark.asyncio
    async def test_schedule_no_slots_available(self, schedule_command, mock_ack, mock_respond):
        """Handle case when no slots are available"""
        command_request = {
            'text': '@busy.person 30min',
            'user_id': 'U123456'
        }
        
        with patch('src.bot.integrations.cli_wrapper.execute_calendar_search') as mock_calendar:
            mock_calendar.return_value = {
                'available_slots': [],
                'conflicts': [],
                'search_time_ms': 890,
                'reasons': ['No common availability in next 7 days']
            }
            
            await schedule_command.handle(
                command=command_request,
                ack=mock_ack,
                respond=mock_respond
            )
            
            response_blocks = mock_respond.call_args[1]['blocks']
            
            assert 'No available slots found' in str(response_blocks)
            assert 'next 7 days' in str(response_blocks)
            assert 'Try a different time range' in str(response_blocks)
    
    @pytest.mark.asyncio
    async def test_schedule_interactive_booking(self, schedule_command):
        """Handle interactive slot booking"""
        # Mock button interaction
        booking_payload = {
            'actions': [{
                'action_id': 'book_slot',
                'value': json.dumps({
                    'slot_start': '2025-08-22T14:00:00Z',
                    'slot_end': '2025-08-22T15:00:00Z',
                    'attendees': ['john.doe@company.com'],
                    'duration_minutes': 60
                })
            }],
            'user': {'id': 'U123456'},
            'channel': {'id': 'C123456'}
        }
        
        mock_ack = AsyncMock()
        mock_respond = AsyncMock()
        
        with patch('src.bot.integrations.cli_wrapper.create_calendar_event') as mock_create:
            mock_create.return_value = {
                'event_id': 'evt_123456',
                'status': 'confirmed',
                'calendar_link': 'https://calendar.google.com/event/123456'
            }
            
            await schedule_command.handle_booking(
                body=booking_payload,
                ack=mock_ack,
                respond=mock_respond
            )
            
            mock_respond.assert_called_once()
            response_text = str(mock_respond.call_args)
            
            assert 'Meeting booked successfully' in response_text
            assert 'August 22, 2:00 PM - 3:00 PM' in response_text
            assert 'calendar.google.com' in response_text
    
    @pytest.mark.asyncio
    async def test_schedule_timezone_handling(self, schedule_command, mock_ack, mock_respond):
        """Handle timezone-aware scheduling"""
        command_request = {
            'text': '@colleague 30min timezone:PST',
            'user_id': 'U123456'
        }
        
        with patch('src.bot.integrations.cli_wrapper.execute_calendar_search') as mock_calendar:
            mock_calendar.return_value = {
                'available_slots': [
                    {
                        'start': '2025-08-22T22:00:00Z',  # 2:00 PM PST
                        'end': '2025-08-22T22:30:00Z',    # 2:30 PM PST
                        'timezone': 'America/Los_Angeles',
                        'duration_minutes': 30
                    }
                ],
                'timezone_info': {
                    'requested_timezone': 'America/Los_Angeles',
                    'display_format': 'PST'
                }
            }
            
            await schedule_command.handle(
                command=command_request,
                ack=mock_ack,
                respond=mock_respond
            )
            
            response_blocks = mock_respond.call_args[1]['blocks']
            
            # Should display times in requested timezone
            assert '2:00 PM PST' in str(response_blocks)
            assert '2:30 PM PST' in str(response_blocks)

class TestGoalsCommand:
    """Test /cos goals command implementation"""
    
    @pytest.fixture
    def goals_command(self):
        """Initialize goals command handler"""
        return GoalsCommand()
    
    @pytest.mark.asyncio
    async def test_list_active_goals(self, goals_command, mock_ack, mock_respond):
        """List all active goals with progress"""
        command_request = {'text': '', 'user_id': 'U123456'}
        
        with patch('src.bot.integrations.cli_wrapper.execute_pattern_extraction') as mock_patterns:
            mock_patterns.return_value = {
                'goals': [
                    {
                        'id': 'goal_001',
                        'title': 'Complete Q3 hiring goals',
                        'description': 'Hire 5 engineers and 2 product managers',
                        'progress': 70,
                        'due_date': '2025-09-30',
                        'assignee': 'david@company.com',
                        'status': 'in_progress',
                        'last_update': '2025-08-20T16:00:00Z',
                        'source_references': [
                            {'file': 'slack/2025-08-15/messages_general.jsonl', 'line': 234},
                            {'file': 'calendar/2025-08-20/events_hiring.json', 'event': 'hiring_review_weekly'}
                        ]
                    },
                    {
                        'id': 'goal_002', 
                        'title': 'Launch new product feature',
                        'progress': 45,
                        'due_date': '2025-08-31',
                        'assignee': 'jane.smith@company.com',
                        'status': 'at_risk',
                        'last_update': '2025-08-19T10:30:00Z'
                    }
                ],
                'stats': {
                    'total_goals': 2,
                    'completed': 0,
                    'in_progress': 1,
                    'at_risk': 1
                }
            }
            
            await goals_command.handle(
                command=command_request,
                ack=mock_ack,
                respond=mock_respond
            )
            
            response_blocks = mock_respond.call_args[1]['blocks']
            
            # Should show goal summary
            assert 'Active Goals (2)' in str(response_blocks)
            assert 'Q3 hiring goals' in str(response_blocks)
            assert '70%' in str(response_blocks)  # Progress
            assert 'Launch new product feature' in str(response_blocks)
            assert '45%' in str(response_blocks)
            
            # Should show status indicators
            assert 'In Progress' in str(response_blocks)
            assert 'At Risk' in str(response_blocks)
    
    @pytest.mark.asyncio
    async def test_goal_details_view(self, goals_command, mock_ack, mock_respond):
        """View detailed information for specific goal"""
        command_request = {
            'text': 'goal_001',  # Specific goal ID
            'user_id': 'U123456'
        }
        
        with patch('src.bot.integrations.cli_wrapper.execute_pattern_extraction') as mock_patterns:
            mock_patterns.return_value = {
                'goal': {
                    'id': 'goal_001',
                    'title': 'Complete Q3 hiring goals',
                    'description': 'Hire 5 engineers and 2 product managers',
                    'progress': 70,
                    'due_date': '2025-09-30',
                    'assignee': 'david@company.com',
                    'status': 'in_progress',
                    'milestones': [
                        {'description': 'Engineering interviews completed', 'status': 'done'},
                        {'description': 'Product manager interviews', 'status': 'in_progress'},
                        {'description': 'Onboarding process setup', 'status': 'pending'}
                    ],
                    'recent_updates': [
                        {
                            'date': '2025-08-20',
                            'update': 'Completed final round with 3 engineering candidates',
                            'source': 'slack #hiring channel'
                        }
                    ],
                    'blockers': [
                        'Waiting for budget approval for senior PM role'
                    ]
                }
            }
            
            await goals_command.handle(
                command=command_request,
                ack=mock_ack,
                respond=mock_respond
            )
            
            response_blocks = mock_respond.call_args[1]['blocks']
            
            # Should show detailed goal information
            assert 'Complete Q3 hiring goals' in str(response_blocks)
            assert 'Hire 5 engineers and 2 product managers' in str(response_blocks)
            assert 'Engineering interviews completed ✅' in str(response_blocks)
            assert 'Waiting for budget approval' in str(response_blocks)  # Blocker
    
    @pytest.mark.asyncio
    async def test_goals_by_person(self, goals_command, mock_ack, mock_respond):
        """Filter goals by assignee"""
        command_request = {
            'text': 'assignee:jane.smith',
            'user_id': 'U123456'
        }
        
        with patch('src.bot.integrations.cli_wrapper.execute_pattern_extraction') as mock_patterns:
            mock_patterns.return_value = {
                'goals': [
                    {
                        'id': 'goal_002',
                        'title': 'Launch new product feature',
                        'assignee': 'jane.smith@company.com',
                        'progress': 45,
                        'status': 'at_risk'
                    },
                    {
                        'id': 'goal_005',
                        'title': 'Q4 product planning',
                        'assignee': 'jane.smith@company.com',
                        'progress': 20,
                        'status': 'in_progress'
                    }
                ],
                'filter_applied': 'assignee:jane.smith@company.com'
            }
            
            await goals_command.handle(
                command=command_request,
                ack=mock_ack,
                respond=mock_respond
            )
            
            response_blocks = mock_respond.call_args[1]['blocks']
            
            assert "Jane's Goals (2)" in str(response_blocks)
            assert 'Launch new product feature' in str(response_blocks)
            assert 'Q4 product planning' in str(response_blocks)
    
    @pytest.mark.asyncio
    async def test_goals_no_results(self, goals_command, mock_ack, mock_respond):
        """Handle case when no goals found"""
        command_request = {'text': '', 'user_id': 'U123456'}
        
        with patch('src.bot.integrations.cli_wrapper.execute_pattern_extraction') as mock_patterns:
            mock_patterns.return_value = {
                'goals': [],
                'stats': {'total_goals': 0}
            }
            
            await goals_command.handle(
                command=command_request,
                ack=mock_ack,
                respond=mock_respond
            )
            
            response_blocks = mock_respond.call_args[1]['blocks']
            
            assert 'No active goals found' in str(response_blocks)
            assert 'create some goals' in str(response_blocks).lower()

class TestInteractiveElements:
    """Test interactive buttons and modals"""
    
    @pytest.mark.asyncio
    async def test_slot_booking_button(self):
        """Test interactive slot booking button"""
        from src.bot.handlers.interaction_handler import handle_slot_booking
        
        mock_ack = AsyncMock()
        mock_respond = AsyncMock()
        
        button_payload = {
            'actions': [{
                'action_id': 'book_slot_123',
                'value': json.dumps({
                    'start': '2025-08-22T14:00:00Z',
                    'end': '2025-08-22T15:00:00Z',
                    'attendees': ['john.doe@company.com']
                })
            }],
            'user': {'id': 'U123456'},
            'response_url': 'https://hooks.slack.com/actions/...'
        }
        
        with patch('src.bot.integrations.cli_wrapper.create_calendar_event') as mock_create:
            mock_create.return_value = {'event_id': 'evt_123', 'status': 'confirmed'}
            
            await handle_slot_booking(
                body=button_payload,
                ack=mock_ack,
                respond=mock_respond
            )
            
            # Should create calendar event
            mock_create.assert_called_once()
            
            # Should respond with confirmation
            mock_respond.assert_called_once()
            response_text = str(mock_respond.call_args)
            assert 'Meeting booked' in response_text
    
    @pytest.mark.asyncio
    async def test_goal_update_modal(self):
        """Test goal update modal interaction"""
        from src.bot.handlers.interaction_handler import handle_goal_update
        
        modal_payload = {
            'view': {
                'state': {
                    'values': {
                        'progress_block': {
                            'progress_input': {'value': '85'}
                        },
                        'status_block': {
                            'status_select': {'selected_option': {'value': 'in_progress'}}
                        },
                        'notes_block': {
                            'notes_input': {'value': 'Made significant progress on feature development'}
                        }
                    }
                },
                'private_metadata': json.dumps({'goal_id': 'goal_001'})
            },
            'user': {'id': 'U123456'}
        }
        
        mock_ack = AsyncMock()
        
        with patch('src.bot.integrations.cli_wrapper.update_goal') as mock_update:
            mock_update.return_value = {'status': 'updated', 'goal_id': 'goal_001'}
            
            await handle_goal_update(
                body=modal_payload,
                ack=mock_ack
            )
            
            # Should update goal with new information
            mock_update.assert_called_once()
            update_args = mock_update.call_args[1]
            assert update_args['progress'] == 85
            assert update_args['status'] == 'in_progress'
            assert 'significant progress' in update_args['notes']
```

#### Implementation Tasks

**Task 4c.1: Schedule Command Core (3 hours)**
- Create ScheduleCommand class with AvailabilityEngine integration
- Parse attendee mentions and duration specifications
- Implement multi-person availability intersection
- Add timezone-aware slot finding and display

**Task 4c.2: Interactive Scheduling Interface (2 hours)**
- Create slot selection UI with booking buttons
- Implement calendar event creation workflow
- Add booking confirmation and calendar links
- Handle scheduling conflicts and alternatives

**Task 4c.3: Goals Command Implementation (2 hours)**
- Create GoalsCommand with StructuredExtractor integration
- Implement goal listing with progress indicators
- Add goal detail views with milestones and blockers
- Create goal filtering (by person, status, due date)

**Task 4c.4: Interactive Goal Management (1 hour)**
- Add goal update modal with progress/status fields
- Implement goal creation workflow
- Create goal sharing and collaboration features
- Add goal completion tracking

### Phase 4d: Advanced Commands & Polish (Day 4 - 8 hours)

#### Test Acceptance Criteria (Write FIRST)

**File**: `tests/bot/test_advanced_commands.py`
```python
import pytest
from unittest.mock import Mock, patch, AsyncMock

from src.bot.commands.commitments import CommitmentsCommand
from src.bot.commands.help import HelpCommand

class TestCommitmentsCommand:
    """Test /cos commitments command implementation"""
    
    @pytest.fixture
    def commitments_command(self):
        return CommitmentsCommand()
    
    @pytest.mark.asyncio
    async def test_list_active_commitments(self, commitments_command, mock_ack, mock_respond):
        """List all active commitments with due dates"""
        command_request = {'text': '', 'user_id': 'U123456'}
        
        with patch('src.bot.integrations.cli_wrapper.execute_pattern_extraction') as mock_patterns:
            mock_patterns.return_value = {
                'commitments': [
                    {
                        'id': 'commit_001',
                        'description': 'Send budget forecast to board',
                        'assignee': 'david@company.com',
                        'due_date': '2025-08-22T17:00:00Z',
                        'status': 'pending',
                        'priority': 'high',
                        'source': 'slack #exec-team',
                        'created': '2025-08-20T10:30:00Z'
                    },
                    {
                        'id': 'commit_002',
                        'description': 'Review hiring pipeline with Jane',
                        'assignee': 'john.doe@company.com',
                        'due_date': '2025-08-23T15:00:00Z',
                        'status': 'in_progress',
                        'priority': 'medium'
                    }
                ],
                'stats': {
                    'total_commitments': 2,
                    'overdue': 0,
                    'due_today': 1,
                    'due_this_week': 2
                }
            }
            
            await commitments_command.handle(
                command=command_request,
                ack=mock_ack,
                respond=mock_respond
            )
            
            response_blocks = mock_respond.call_args[1]['blocks']
            
            # Should show commitment summary
            assert 'Active Commitments (2)' in str(response_blocks)
            assert 'Send budget forecast' in str(response_blocks)
            assert 'Due tomorrow' in str(response_blocks)  # Due date formatting
            assert 'Review hiring pipeline' in str(response_blocks)
            
            # Should show priority indicators
            assert '🔴' in str(response_blocks)  # High priority
            assert '🟡' in str(response_blocks)  # Medium priority
    
    @pytest.mark.asyncio
    async def test_overdue_commitments_warning(self, commitments_command, mock_ack, mock_respond):
        """Highlight overdue commitments"""
        command_request = {'text': '', 'user_id': 'U123456'}
        
        with patch('src.bot.integrations.cli_wrapper.execute_pattern_extraction') as mock_patterns:
            mock_patterns.return_value = {
                'commitments': [
                    {
                        'id': 'commit_003',
                        'description': 'Complete quarterly review',
                        'due_date': '2025-08-20T17:00:00Z',  # Past due
                        'status': 'overdue',
                        'priority': 'high',
                        'days_overdue': 1
                    }
                ],
                'stats': {
                    'overdue': 1,
                    'total_commitments': 1
                }
            }
            
            await commitments_command.handle(
                command=command_request,
                ack=mock_ack,
                respond=mock_respond
            )
            
            response_blocks = mock_respond.call_args[1]['blocks']
            
            # Should prominently show overdue items
            assert '⚠️ OVERDUE' in str(response_blocks)
            assert 'quarterly review' in str(response_blocks)
            assert '1 day overdue' in str(response_blocks)
    
    @pytest.mark.asyncio
    async def test_commitments_by_person(self, commitments_command, mock_ack, mock_respond):
        """Filter commitments by assignee"""
        command_request = {
            'text': 'for:john.doe',
            'user_id': 'U123456'
        }
        
        with patch('src.bot.integrations.cli_wrapper.execute_pattern_extraction') as mock_patterns:
            mock_patterns.return_value = {
                'commitments': [
                    {
                        'description': 'Prepare product demo',
                        'assignee': 'john.doe@company.com',
                        'due_date': '2025-08-25T12:00:00Z',
                        'status': 'pending'
                    }
                ],
                'filter_applied': 'assignee:john.doe@company.com'
            }
            
            await commitments_command.handle(
                command=command_request,
                ack=mock_ack,
                respond=mock_respond
            )
            
            response_blocks = mock_respond.call_args[1]['blocks']
            
            assert "John's Commitments" in str(response_blocks)
            assert 'Prepare product demo' in str(response_blocks)
    
    @pytest.mark.asyncio
    async def test_commitment_status_update(self, commitments_command):
        """Handle commitment status updates"""
        update_payload = {
            'actions': [{
                'action_id': 'mark_complete',
                'value': 'commit_001'
            }],
            'user': {'id': 'U123456'}
        }
        
        mock_ack = AsyncMock()
        mock_respond = AsyncMock()
        
        with patch('src.bot.integrations.cli_wrapper.update_commitment_status') as mock_update:
            mock_update.return_value = {
                'commitment_id': 'commit_001',
                'new_status': 'completed',
                'completed_at': '2025-08-21T14:30:00Z'
            }
            
            await commitments_command.handle_status_update(
                body=update_payload,
                ack=mock_ack,
                respond=mock_respond
            )
            
            # Should update commitment status
            mock_update.assert_called_once_with('commit_001', 'completed')
            
            # Should respond with confirmation
            response_text = str(mock_respond.call_args)
            assert 'Commitment marked complete' in response_text

class TestHelpCommand:
    """Test /cos help command implementation"""
    
    @pytest.fixture
    def help_command(self):
        return HelpCommand()
    
    @pytest.mark.asyncio
    async def test_general_help(self, help_command, mock_ack, mock_respond):
        """Show general help with all commands"""
        command_request = {'text': '', 'user_id': 'U123456'}
        
        await help_command.handle(
            command=command_request,
            ack=mock_ack,
            respond=mock_respond
        )
        
        response_blocks = mock_respond.call_args[1]['blocks']
        
        # Should show all available commands
        assert 'AI Chief of Staff Commands' in str(response_blocks)
        assert '/cos search' in str(response_blocks)
        assert '/cos schedule' in str(response_blocks)
        assert '/cos goals' in str(response_blocks)
        assert '/cos brief' in str(response_blocks)
        assert '/cos commitments' in str(response_blocks)
        
        # Should include interactive examples
        assert 'Try an example' in str(response_blocks)
        assert any('button' in str(block) for block in response_blocks)
    
    @pytest.mark.asyncio
    async def test_specific_command_help(self, help_command, mock_ack, mock_respond):
        """Show detailed help for specific command"""
        command_request = {
            'text': 'search',
            'user_id': 'U123456'
        }
        
        await help_command.handle(
            command=command_request,
            ack=mock_ack,
            respond=mock_respond
        )
        
        response_blocks = mock_respond.call_args[1]['blocks']
        
        # Should show detailed search help
        assert 'Search Command Help' in str(response_blocks)
        assert 'meeting notes from last week' in str(response_blocks)  # Example
        assert 'from:john.doe' in str(response_blocks)  # Filter example
        assert 'channel:general' in str(response_blocks)  # Channel filter
    
    @pytest.mark.asyncio
    async def test_interactive_help_examples(self, help_command):
        """Handle interactive help example buttons"""
        example_payload = {
            'actions': [{
                'action_id': 'try_search_example',
                'value': 'meeting notes from last week'
            }],
            'user': {'id': 'U123456'},
            'channel': {'id': 'C123456'}
        }
        
        mock_ack = AsyncMock()
        mock_client = AsyncMock()
        
        await help_command.handle_example(
            body=example_payload,
            ack=mock_ack,
            client=mock_client
        )
        
        # Should execute the example command
        mock_client.views_open.assert_called_once()
        
        # Modal should show example command execution
        modal_view = mock_client.views_open.call_args[1]['view']
        assert 'Search Example' in modal_view['title']['text']
        assert 'meeting notes from last week' in str(modal_view)

class TestErrorHandling:
    """Test comprehensive error handling"""
    
    @pytest.mark.asyncio
    async def test_cli_tool_timeout(self, mock_ack, mock_respond):
        """Handle CLI tool timeout gracefully"""
        from src.bot.commands.search import SearchCommand
        
        search_command = SearchCommand()
        command_request = {'text': 'test query', 'user_id': 'U123456'}
        
        with patch('src.bot.integrations.cli_wrapper.execute_search') as mock_search:
            mock_search.side_effect = asyncio.TimeoutError("Command timed out")
            
            await search_command.handle(
                command=command_request,
                ack=mock_ack,
                respond=mock_respond
            )
            
            response_text = str(mock_respond.call_args)
            
            assert 'Search is taking longer than expected' in response_text
            assert 'try a simpler query' in response_text.lower()
            # Should not expose internal timeout details
            assert 'TimeoutError' not in response_text
    
    @pytest.mark.asyncio
    async def test_database_error_handling(self, mock_ack, mock_respond):
        """Handle database connection errors"""
        from src.bot.commands.goals import GoalsCommand
        
        goals_command = GoalsCommand()
        command_request = {'text': '', 'user_id': 'U123456'}
        
        with patch('src.bot.integrations.cli_wrapper.execute_pattern_extraction') as mock_extract:
            mock_extract.side_effect = Exception("Database connection failed")
            
            await goals_command.handle(
                command=command_request,
                ack=mock_ack,
                respond=mock_respond
            )
            
            response_blocks = mock_respond.call_args[1]['blocks']
            
            assert 'Goals temporarily unavailable' in str(response_blocks)
            assert 'technical issue' in str(response_blocks)
            assert 'Database connection failed' not in str(response_blocks)
    
    @pytest.mark.asyncio
    async def test_rate_limit_handling(self):
        """Handle Slack API rate limits"""
        from src.bot.utils.rate_limiter import SlackAPILimiter
        
        limiter = SlackAPILimiter()
        
        # Simulate rate limit hit
        with patch('time.sleep') as mock_sleep:
            limiter.handle_rate_limit(retry_after=60)
            
            # Should implement exponential backoff
            mock_sleep.assert_called()
            sleep_duration = mock_sleep.call_args[0][0]
            assert sleep_duration >= 60  # At least the retry_after value
    
    @pytest.mark.asyncio
    async def test_invalid_user_input(self, mock_ack, mock_respond):
        """Handle invalid user input gracefully"""
        from src.bot.commands.schedule import ScheduleCommand
        
        schedule_command = ScheduleCommand()
        
        # Invalid command format
        command_request = {
            'text': 'invalid format no duration',
            'user_id': 'U123456'
        }
        
        await schedule_command.handle(
            command=command_request,
            ack=mock_ack,
            respond=mock_respond
        )
        
        response_blocks = mock_respond.call_args[1]['blocks']
        
        assert 'Invalid format' in str(response_blocks)
        assert 'Example:' in str(response_blocks)  # Should show correct format
        assert '@person 60min' in str(response_blocks)  # Example usage

class TestPerformanceOptimization:
    """Test performance optimizations"""
    
    @pytest.mark.asyncio
    async def test_response_caching(self):
        """Test caching of frequent responses"""
        from src.bot.utils.cache import ResponseCache
        
        cache = ResponseCache()
        
        # Cache search results
        results = {'results': ['test'], 'total_count': 1}
        cache.set('search:meeting notes', results, ttl=300)  # 5 minutes
        
        # Should retrieve from cache
        cached_results = cache.get('search:meeting notes')
        assert cached_results == results
        
        # Should expire after TTL
        with patch('time.time') as mock_time:
            mock_time.return_value = 1000000  # Future time
            expired_results = cache.get('search:meeting notes')
            assert expired_results is None
    
    @pytest.mark.asyncio
    async def test_background_processing(self):
        """Test background processing for long operations"""
        from src.bot.utils.background import BackgroundTaskManager
        
        task_manager = BackgroundTaskManager()
        
        # Submit long-running task
        task_id = await task_manager.submit_task(
            'generate_comprehensive_brief',
            {'date_range': 'last_month', 'user_id': 'U123456'}
        )
        
        assert task_id is not None
        
        # Should track task progress
        status = await task_manager.get_task_status(task_id)
        assert status in ['pending', 'in_progress', 'completed', 'failed']
    
    def test_memory_usage_monitoring(self):
        """Monitor bot memory usage"""
        from src.bot.utils.monitoring import MemoryMonitor
        
        monitor = MemoryMonitor()
        usage = monitor.get_current_usage()
        
        assert 'memory_mb' in usage
        assert 'cpu_percent' in usage
        assert usage['memory_mb'] > 0
        
        # Should alert if usage too high
        with patch.object(monitor, 'get_current_usage', return_value={'memory_mb': 1000}):
            alert = monitor.check_thresholds(max_memory_mb=500)
            assert alert['memory_exceeded'] == True
```

#### Implementation Tasks

**Task 4d.1: Commitments Command Implementation (2 hours)**
- Create CommitmentsCommand with pattern extraction integration
- Implement commitment listing with priority and due date sorting
- Add overdue commitment warnings and status tracking
- Create commitment update and completion workflows

**Task 4d.2: Help Command with Interactive Examples (2 hours)**
- Create comprehensive HelpCommand with all command documentation
- Implement interactive example buttons for each command
- Add context-sensitive help based on user's recent activity
- Create command usage analytics and optimization suggestions

**Task 4d.3: Advanced Error Handling (2 hours)**
- Implement comprehensive error handling for all failure modes
- Add graceful degradation when CLI tools are unavailable
- Create user-friendly error messages with actionable guidance
- Add error reporting and monitoring integration

**Task 4d.4: Performance Optimization (2 hours)**
- Implement response caching for frequent queries
- Add background processing for long-running operations
- Create performance monitoring and alerting
- Optimize Slack API usage with batching and rate limiting

### Phase 4e: Integration Testing & Documentation (Day 5 - 8 hours)

#### Test Acceptance Criteria (Write FIRST)

**File**: `tests/bot/test_end_to_end.py`
```python
import pytest
from unittest.mock import Mock, patch, AsyncMock
import json

class TestEndToEndWorkflows:
    """Test complete user workflows end-to-end"""
    
    @pytest.mark.asyncio
    async def test_complete_search_workflow(self):
        """Complete search workflow from command to result interaction"""
        # User sends /cos search command
        # Bot responds with results
        # User clicks "Load More" button
        # Bot responds with additional results
        pass  # Implementation details...
    
    @pytest.mark.asyncio
    async def test_complete_scheduling_workflow(self):
        """Complete scheduling workflow from request to calendar booking"""
        # User sends /cos schedule @person 60min
        # Bot finds available slots
        # User clicks "Book This Slot" 
        # Bot creates calendar event and confirms
        pass  # Implementation details...
    
    @pytest.mark.asyncio
    async def test_error_recovery_workflow(self):
        """Test error recovery and fallback mechanisms"""
        # Simulate database failure during search
        # Bot should provide fallback response
        # System should recover automatically
        pass  # Implementation details...

class TestSlackWorkspaceIntegration:
    """Test integration with real Slack workspace (manual tests)"""
    
    def test_bot_installation_procedure(self):
        """Document bot installation and setup procedure"""
        installation_steps = [
            "1. Create new Slack app at api.slack.com",
            "2. Configure OAuth scopes: app_mentions:read, chat:write, commands, channels:read, users:read",
            "3. Add slash commands: /cos-search, /cos-schedule, /cos-goals, /cos-brief, /cos-commitments, /cos-help",
            "4. Install app to workspace and obtain bot token",
            "5. Configure environment variables: SLACK_BOT_TOKEN, SLACK_SIGNING_SECRET",
            "6. Deploy bot application and verify connectivity"
        ]
        
        # These steps should be documented in deployment guide
        assert len(installation_steps) == 6
    
    def test_permission_validation(self):
        """Validate bot has required permissions"""
        required_scopes = [
            'app_mentions:read',   # Respond to @mentions
            'chat:write',          # Send messages and responses
            'commands',            # Handle slash commands
            'channels:read',       # Read channel information
            'users:read',          # Look up user information
            'im:history'           # Read direct message history
        ]
        
        # Bot should validate all scopes on startup
        assert len(required_scopes) == 6

class TestPerformanceBenchmarks:
    """Validate performance requirements are met"""
    
    @pytest.mark.asyncio
    async def test_search_response_time(self):
        """Search responses must be under 3 seconds"""
        from src.bot.commands.search import SearchCommand
        
        start_time = time.time()
        
        search_command = SearchCommand()
        with patch('src.bot.integrations.cli_wrapper.execute_search') as mock_search:
            mock_search.return_value = {'results': [], 'total_count': 0, 'query_time_ms': 500}
            
            await search_command.handle(
                command={'text': 'test query', 'user_id': 'U123456'},
                ack=AsyncMock(),
                respond=AsyncMock()
            )
        
        response_time = time.time() - start_time
        assert response_time < 3.0  # Must respond within 3 seconds
    
    @pytest.mark.asyncio
    async def test_calendar_response_time(self):
        """Calendar operations must be under 5 seconds"""
        from src.bot.commands.schedule import ScheduleCommand
        
        start_time = time.time()
        
        schedule_command = ScheduleCommand()
        with patch('src.bot.integrations.cli_wrapper.execute_calendar_search') as mock_calendar:
            mock_calendar.return_value = {'available_slots': [], 'search_time_ms': 2000}
            
            await schedule_command.handle(
                command={'text': '@person 60min', 'user_id': 'U123456'},
                ack=AsyncMock(),
                respond=AsyncMock()
            )
        
        response_time = time.time() - start_time
        assert response_time < 5.0  # Must respond within 5 seconds
    
    def test_memory_usage_limits(self):
        """Bot memory usage must stay under 500MB"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        memory_mb = process.memory_info().rss / 1024 / 1024
        
        # Should stay under 500MB for normal operations
        assert memory_mb < 500
    
    @pytest.mark.asyncio
    async def test_concurrent_request_handling(self):
        """Bot should handle multiple concurrent requests"""
        from src.bot.slack_bot import AICOSSlackBot
        
        bot = AICOSSlackBot()
        
        # Simulate 10 concurrent search requests
        tasks = []
        for i in range(10):
            task = bot.handle_search_command(
                command={'text': f'query {i}', 'user_id': f'U{i:06d}'},
                ack=AsyncMock(),
                respond=AsyncMock()
            )
            tasks.append(task)
        
        # All should complete successfully
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # No tasks should have failed
        assert all(not isinstance(result, Exception) for result in results)

class TestDeploymentValidation:
    """Validate deployment readiness"""
    
    def test_configuration_completeness(self):
        """All required configuration is present"""
        from src.bot.slack_bot import BotConfig
        
        required_env_vars = [
            'SLACK_BOT_TOKEN',
            'SLACK_SIGNING_SECRET', 
            'AICOS_BASE_DIR'
        ]
        
        # Should validate all required vars on startup
        with patch.dict('os.environ', {var: 'test_value' for var in required_env_vars}):
            config = BotConfig()
            
            for var in required_env_vars:
                assert hasattr(config, var.lower())
    
    def test_dependency_availability(self):
        """All CLI tool dependencies are available"""
        cli_tools = [
            'tools/search_cli.py',
            'tools/find_slots.py', 
            'tools/query_facts.py',
            'tools/daily_summary.py'
        ]
        
        for tool in cli_tools:
            tool_path = Path(tool)
            assert tool_path.exists(), f"Required CLI tool missing: {tool}"
    
    def test_database_connectivity(self):
        """Database is accessible and functional"""
        from src.search.database import SearchDatabase
        
        db = SearchDatabase()
        
        # Should be able to connect and query
        try:
            result = db.search('test query', limit=1)
            assert isinstance(result, dict)
            assert 'results' in result
        except Exception as e:
            pytest.fail(f"Database connectivity failed: {e}")
    
    def test_slack_api_connectivity(self):
        """Can connect to Slack API"""
        from slack_sdk import WebClient
        import os
        
        if 'SLACK_BOT_TOKEN' not in os.environ:
            pytest.skip("SLACK_BOT_TOKEN not configured")
        
        client = WebClient(token=os.environ['SLACK_BOT_TOKEN'])
        
        try:
            response = client.auth_test()
            assert response['ok'] == True
        except Exception as e:
            pytest.fail(f"Slack API connectivity failed: {e}")
```

#### Implementation Tasks

**Task 4e.1: End-to-End Integration Testing (3 hours)**
- Create comprehensive workflow tests for all major user journeys
- Test complete command flows from input to response
- Validate interactive element workflows (buttons, modals)
- Test error recovery and fallback mechanisms

**Task 4e.2: Performance Validation (2 hours)**
- Implement performance benchmarking for all commands
- Validate 3-second response time requirement
- Test concurrent request handling and resource usage
- Create performance monitoring and alerting

**Task 4e.3: Documentation Creation (2 hours)**
- Create Slack app installation and configuration guide
- Document all slash commands with examples and usage
- Create troubleshooting guide for common issues
- Write architecture documentation for future development

**Task 4e.4: Deployment Preparation (1 hour)**
- Create deployment scripts and procedures
- Validate all dependencies and configuration
- Test bot in staging environment
- Create rollback procedures and monitoring

## Integration Requirements

### Slack App Configuration

**Required OAuth Scopes**:
- `app_mentions:read` - Respond to @mentions in channels
- `chat:write` - Send messages and command responses
- `commands` - Handle slash commands
- `channels:read` - Read channel information for context
- `users:read` - Look up user information for @mentions
- `im:history` - Access direct message history (optional)

**Slash Commands Setup**:
```
Command: /cos-search
Request URL: https://your-bot.com/slack/commands/search
Description: Search across all your data sources
Usage Hint: search [query] [filters]

Command: /cos-schedule  
Request URL: https://your-bot.com/slack/commands/schedule
Description: Find meeting times with colleagues
Usage Hint: schedule @person [duration] [date]

Command: /cos-goals
Request URL: https://your-bot.com/slack/commands/goals
Description: View and manage active goals
Usage Hint: goals [filters] or goals [goal-id]

Command: /cos-brief
Request URL: https://your-bot.com/slack/commands/brief
Description: Generate daily or weekly briefings
Usage Hint: brief [today|yesterday|last_week]

Command: /cos-commitments
Request URL: https://your-bot.com/slack/commands/commitments
Description: Track commitments and deadlines
Usage Hint: commitments [for:person] [status:pending]

Command: /cos-help
Request URL: https://your-bot.com/slack/commands/help
Description: Get help with AI Chief of Staff commands
Usage Hint: help [command-name]
```

### CLI Tool Integration Patterns

**Async Bridge Pattern**:
```python
class AsyncCLIBridge:
    """Bridge sync CLI tools to async Slack bot operations"""
    
    async def execute_search(self, query: str, filters: Dict = None) -> Dict:
        """Execute search_cli.py asynchronously"""
        cmd = ['python', 'tools/search_cli.py', 'search', query]
        if filters:
            cmd.extend(['--filters', json.dumps(filters)])
        
        process = await asyncio.create_subprocess_exec(
            *cmd, 
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await asyncio.wait_for(
            process.communicate(), 
            timeout=30  # 30-second timeout
        )
        
        if process.returncode != 0:
            raise Exception(f"CLI tool failed: {stderr.decode()}")
            
        return json.loads(stdout.decode())
```

### Performance Requirements

**Response Time Targets**:
- Search commands: <1 second (direct database access)
- Calendar commands: <5 seconds (calendar API calls)
- Brief generation: <10 seconds (complex aggregation)
- All other commands: <3 seconds (general requirement)

**Resource Limits**:
- Memory usage: <500MB steady state
- CPU usage: <50% average during normal operations
- Concurrent requests: Handle 20+ simultaneous commands
- API rate limits: Respect Slack's 1 req/sec posting limit

### Error Handling Strategy

**Error Categories & Responses**:

1. **User Input Errors**
   - Invalid command syntax → Show usage examples
   - Missing required parameters → Prompt for missing info
   - Unknown @mentions → Suggest correct usernames

2. **System Errors**
   - Database unavailable → "Search temporarily down, try again in a few minutes"
   - CLI tool timeout → "Operation taking longer than expected, check back soon"
   - Rate limit exceeded → "Slow down a bit, try again in a moment"

3. **API Errors**
   - Slack API failure → Log error, show generic "temporary issue" message
   - Calendar API failure → Fall back to cached data if available
   - Authentication failure → "Please contact admin to refresh credentials"

### Success Criteria

**Functional Requirements**:
- [ ] All 6 slash commands operational (/cos-search, /cos-schedule, /cos-goals, /cos-brief, /cos-commitments, /cos-help)
- [ ] Interactive elements work (buttons, modals, pagination)
- [ ] Error handling covers all failure modes gracefully
- [ ] All existing CLI functionality accessible via bot

**Performance Requirements**:
- [ ] 95% of commands respond within target times
- [ ] Bot handles 20+ concurrent requests without degradation
- [ ] Memory usage stays under 500MB during normal operations
- [ ] Zero data corruption or loss during bot operations

**User Experience Requirements**:
- [ ] Commands feel natural and intuitive to executives
- [ ] Error messages provide actionable guidance
- [ ] Interactive elements work on mobile and desktop
- [ ] Help system provides immediate assistance

**Integration Requirements**:
- [ ] No performance impact on existing CLI tools
- [ ] Complete audit trail maintained for all operations
- [ ] Authentication system properly integrated
- [ ] Graceful fallback to CLI when bot unavailable

## Delivery Checklist

**Before marking Phase 4 complete**:
- [ ] All slash commands implemented and tested
- [ ] Interactive workflows (booking, updates) functional
- [ ] Comprehensive error handling implemented
- [ ] Performance benchmarks meet all targets
- [ ] End-to-end testing completed
- [ ] Documentation complete (installation, usage, troubleshooting)
- [ ] Deployment procedures validated
- [ ] Integration with existing systems confirmed
- [ ] User acceptance testing completed
- [ ] Production deployment successful

---

**Contact Phase 4 Team Lead for questions or clarification**  
**Integration Dependencies**: Phase 1 complete ✅, All CLI tools operational ✅  
**Next Phase**: Phase 5 Scale & Optimization