# Agent H: Integration & Command Processing - Phase 4.5 Frontend

**Date Created**: 2025-08-28  
**Owner**: Agent H (Systems Integration Team)  
**Status**: PENDING  
**Estimated Time**: 8 hours (1 day)  
**Dependencies**: Agents E, F, G must be complete (backend API, dashboard, coding system)

## Executive Summary

Connect all existing infrastructure (collectors, SearchDatabase, Slack bot) to the new frontend system. Implement unified command processing and ensure real-time synchronization between dashboard and Slack interfaces.

**Core Philosophy**: No rewriting of existing components - just create clean integration points. Leverage the working infrastructure and enhance it with real-time capabilities and unified command processing.

## Relevant Files for Context

**Read for Context:**
- `src/collectors/slack_collector.py` - Existing Slack data collection
- `src/collectors/calendar_collector.py` - Calendar collection patterns
- `src/search/database.py` - SearchDatabase integration (340K+ records)
- `src/bot/slack_bot.py` - Existing Slack bot implementation
- `backend/server.py` - API endpoints (from Agent E)
- `backend/coding_system.py` - Coding system (from Agent G)

**Files to Create:**
- `backend/collector_integration.py` - Connect collectors to real-time API
- `backend/command_processor.py` - Unified command execution
- `backend/brief_generator.py` - Brief formatting and generation
- `tools/run_frontend.py` - Startup script for integrated system

**Files to Modify:**
- `src/bot/slack_bot.py` - Update to use new backend API

## Test Acceptance Criteria (Write FIRST)

### File: `tests/test_integration.py`
```python
import pytest
import asyncio
import json
from unittest.mock import Mock, patch, AsyncMock
from backend.collector_integration import CollectorIntegrator
from backend.command_processor import UnifiedCommandProcessor
from backend.brief_generator import BriefGenerator

class TestCollectorIntegration:
    """Test integration between existing collectors and new API"""
    
    @pytest.fixture
    def mock_state_manager(self):
        """Mock state manager for testing"""
        mock = Mock()
        mock.update_state = AsyncMock()
        mock.broadcast_update = AsyncMock()
        return mock
    
    @pytest.fixture
    def integrator(self, mock_state_manager):
        return CollectorIntegrator(mock_state_manager)
    
    @patch('backend.collector_integration.SlackCollector')
    async def test_slack_collection_integration(self, mock_slack_collector, integrator):
        """Test Slack collection triggers state updates"""
        # Mock collector response
        mock_collector = mock_slack_collector.return_value
        mock_collector.collect_with_progress = AsyncMock(return_value=[
            {'type': 'slack_message', 'channel': 'general', 'text': 'Test message'}
        ])
        
        # Run collection
        await integrator.trigger_slack_collection()
        
        # Verify state update called
        integrator.state_manager.update_state.assert_called()
        integrator.state_manager.broadcast_update.assert_called()
    
    @patch('backend.collector_integration.CalendarCollector') 
    async def test_calendar_collection_integration(self, mock_calendar_collector, integrator):
        """Test Calendar collection creates coded items"""
        # Mock collector response
        mock_collector = mock_calendar_collector.return_value
        mock_collector.collect_with_progress = AsyncMock(return_value=[
            {'start_time': '09:00', 'title': 'Product Sync', 'date': '2025-08-28'},
            {'start_time': '11:00', 'title': '1:1 w/ Sarah', 'date': '2025-08-28'}
        ])
        
        # Run collection
        await integrator.trigger_calendar_collection()
        
        # Verify coding system applied
        # Should have called state update with coded calendar items
        call_args = integrator.state_manager.update_state.call_args_list
        assert any('calendar' in str(call) for call in call_args)
    
    async def test_progress_updates(self, integrator, mock_state_manager):
        """Test collection progress updates broadcast in real-time"""
        
        # Mock progress callback
        progress_values = []
        async def capture_progress(progress):
            progress_values.append(progress)
        
        integrator.progress_callback = capture_progress
        
        # Simulate collection with progress
        await integrator.simulate_collection_progress(duration_seconds=0.1)
        
        # Should have received multiple progress updates
        assert len(progress_values) > 1
        assert progress_values[0] < progress_values[-1]
        assert progress_values[-1] == 100

class TestCommandProcessor:
    """Test unified command processing across interfaces"""
    
    @pytest.fixture
    def processor(self):
        from backend.state_manager import StateManager
        from backend.coding_system import CodingManager
        from backend.code_parser import CodeParser
        
        state_mgr = StateManager()
        coding_mgr = CodingManager()
        parser = CodeParser()
        
        return UnifiedCommandProcessor(state_mgr, coding_mgr, parser)
    
    async def test_approve_command_execution(self, processor):
        """Test approve command updates item status"""
        # Set up test data with coded items
        test_priorities = [
            {'code': 'P1', 'text': 'Test Priority', 'status': 'pending'}
        ]
        
        processor.coding_manager.assign_codes = Mock(return_value=test_priorities)
        processor.coding_manager.get_by_code = Mock(return_value=test_priorities[0])
        
        # Execute approve command
        result = await processor.execute_command('approve P1')
        
        assert result['success'] == True
        assert result['action'] == 'approve'
        assert result['code'] == 'P1'
    
    async def test_brief_command_execution(self, processor):
        """Test brief command generates meeting context"""
        # Set up test calendar item
        test_calendar_item = {
            'code': 'C3', 
            'title': 'Budget Review',
            'time': '2:00 PM',
            'attendees': ['john@example.com', 'cfo@example.com']
        }
        
        processor.coding_manager.get_by_code = Mock(return_value=test_calendar_item)
        
        # Execute brief command
        result = await processor.execute_command('brief C3')
        
        assert result['success'] == True
        assert result['action'] == 'brief'
        assert result['code'] == 'C3'
        assert 'brief_content' in result
    
    async def test_multi_command_execution(self, processor):
        """Test pipe-separated commands execute in sequence"""
        # Mock individual command responses
        processor.execute_single_command = AsyncMock(side_effect=[
            {'success': True, 'action': 'approve', 'code': 'P7'},
            {'success': True, 'action': 'refresh'},
            {'success': True, 'action': 'brief', 'code': 'C3'}
        ])
        
        # Execute multi-command
        result = await processor.execute_command('approve P7 | refresh | brief C3')
        
        assert result['success'] == True
        assert len(result['results']) == 3
        assert processor.execute_single_command.call_count == 3

class TestSlackBotIntegration:
    """Test updated Slack bot using new backend API"""
    
    @pytest.fixture
    def mock_api_client(self):
        """Mock API client for testing"""
        mock = Mock()
        mock.post = AsyncMock(return_value=Mock(json=AsyncMock(return_value={'success': True})))
        mock.get = AsyncMock(return_value=Mock(json=AsyncMock(return_value={'status': 'IDLE'})))
        return mock
    
    @patch('src.bot.slack_bot.aiohttp.ClientSession')
    async def test_slack_command_forwards_to_api(self, mock_session, mock_api_client):
        """Test Slack commands forward to backend API"""
        mock_session.return_value.__aenter__.return_value = mock_api_client
        
        # Import and test updated Slack bot
        from src.bot.slack_bot import SimpleSlackBot
        bot = SimpleSlackBot(api_base_url='http://localhost:8000')
        
        # Simulate Slack command
        await bot.handle_cos_command('approve P7')
        
        # Verify API call made
        mock_api_client.post.assert_called_once()
        call_args = mock_api_client.post.call_args
        assert '/api/command' in call_args[0][0]  # URL
        assert 'approve P7' in str(call_args[1]['json'])  # Command data
    
    async def test_slack_websocket_integration(self):
        """Test Slack bot can receive WebSocket updates"""
        # This would test WebSocket client in Slack bot
        # For now, verify the integration point exists
        from src.bot.slack_bot import SimpleSlackBot
        
        bot = SimpleSlackBot()
        assert hasattr(bot, 'connect_to_dashboard') or hasattr(bot, 'api_base_url')

class TestBriefGeneration:
    """Test meeting brief generation system"""
    
    @pytest.fixture
    def brief_generator(self):
        return BriefGenerator()
    
    async def test_meeting_brief_generation(self, brief_generator):
        """Test generating brief for calendar meeting"""
        meeting_data = {
            'code': 'C3',
            'title': 'Budget Review',
            'time': '2:00 PM',
            'date': '2025-08-28',
            'attendees': ['john@example.com', 'cfo@example.com']
        }
        
        # Mock search for related content
        with patch.object(brief_generator, 'search_related_content') as mock_search:
            mock_search.return_value = [
                {'source': 'slack', 'text': 'Q3 budget numbers look good'},
                {'source': 'drive', 'title': 'Budget Spreadsheet v2.xlsx'}
            ]
            
            brief = await brief_generator.generate_meeting_brief(meeting_data)
            
            assert brief['meeting_code'] == 'C3'
            assert brief['meeting_title'] == 'Budget Review'
            assert 'related_content' in brief
            assert len(brief['related_content']) > 0
            assert 'formatted_html' in brief
    
    async def test_daily_brief_generation(self, brief_generator):
        """Test generating daily intelligence brief"""
        # Mock system state
        mock_state = {
            'calendar': [
                {'code': 'C1', 'title': 'Team Standup', 'time': '9:00 AM'},
                {'code': 'C2', 'title': 'Product Review', 'time': '2:00 PM'}
            ],
            'priorities': [
                {'code': 'P1', 'text': 'Q1 Planning', 'status': 'done'},
                {'code': 'P2', 'text': 'Budget Review', 'status': 'pending'}
            ],
            'commitments': {
                'owe': [{'code': 'M1', 'text': 'Report to CFO', 'due_date': '2025-08-28'}],
                'owed': [{'code': 'M2', 'text': 'Feedback from team', 'due_date': '2025-08-28'}]
            }
        }
        
        brief = await brief_generator.generate_daily_brief(mock_state)
        
        assert 'executive_summary' in brief
        assert 'critical_items' in brief
        assert 'time_sensitive' in brief
        assert brief['total_meetings'] == 2
        assert brief['pending_priorities'] == 1

class TestErrorHandling:
    """Test error handling across integration points"""
    
    async def test_collector_failure_handling(self):
        """Test graceful handling of collector failures"""
        from backend.collector_integration import CollectorIntegrator
        
        mock_state = Mock()
        mock_state.update_state = AsyncMock(side_effect=Exception("Test error"))
        
        integrator = CollectorIntegrator(mock_state)
        
        # Should not crash on collector error
        result = await integrator.safe_collect_with_fallback('slack')
        
        assert 'error' in result
        assert result['success'] == False
    
    async def test_command_error_recovery(self):
        """Test command processor handles errors gracefully"""
        from backend.command_processor import UnifiedCommandProcessor
        
        processor = UnifiedCommandProcessor(None, None, None)
        
        # Invalid command should return structured error
        result = await processor.execute_command('invalid command xyz')
        
        assert result['success'] == False
        assert 'error' in result
        assert 'suggestions' in result or 'help' in result
```

## Implementation Tasks

### Task H1: Collector Integration (3 hours)

**Objective**: Connect existing collectors to real-time API with progress updates

**File**: `backend/collector_integration.py`
```python
import asyncio
import logging
from typing import Dict, List, Any, Callable, Optional
from datetime import datetime

# Import existing collectors
from src.collectors.slack_collector import SlackCollector
from src.collectors.calendar_collector import CalendarCollector 
from src.collectors.drive_collector import DriveCollector
from src.collectors.employee_collector import EmployeeCollector

# Import new components
from backend.state_manager import StateManager
from backend.coding_system import CodingManager, CodeType

logger = logging.getLogger(__name__)

class CollectorIntegrator:
    """
    Integrates existing collectors with new real-time frontend system
    
    Responsibilities:
    - Trigger collection from existing collectors
    - Apply coding system to collected data
    - Update state with real-time progress
    - Handle errors gracefully
    """
    
    def __init__(self, state_manager: StateManager, coding_manager: CodingManager):
        self.state_manager = state_manager
        self.coding_manager = coding_manager
        
        # Initialize collectors using existing patterns
        self.collectors = {
            'slack': SlackCollector(),
            'calendar': CalendarCollector(),
            'drive': DriveCollector(),
            'employee': EmployeeCollector()
        }
        
        self.progress_callbacks: List[Callable] = []
    
    async def trigger_full_collection(self) -> Dict[str, Any]:
        """Run full collection across all sources"""
        await self.state_manager.update_state('system/status', 'COLLECTING')
        await self.state_manager.update_state('system/progress', 0)
        
        results = {}
        total_collectors = len(self.collectors)
        completed = 0
        
        try:
            for collector_name, collector in self.collectors.items():
                logger.info(f"Starting {collector_name} collection")
                
                # Update progress
                progress = int((completed / total_collectors) * 100)
                await self.state_manager.update_state('system/progress', progress)
                
                # Run collection
                result = await self.run_single_collector(collector_name, collector)
                results[collector_name] = result
                
                completed += 1
            
            # Final progress update
            await self.state_manager.update_state('system/progress', 100)
            await self.state_manager.update_state('system/status', 'IDLE')
            await self.state_manager.update_state('system/last_sync', datetime.now().isoformat())
            
            return {
                'success': True,
                'results': results,
                'message': f"Collected data from {completed} sources"
            }
            
        except Exception as e:
            logger.error(f"Collection failed: {e}")
            await self.state_manager.update_state('system/status', 'ERROR')
            return {
                'success': False,
                'error': str(e),
                'partial_results': results
            }
    
    async def trigger_quick_collection(self) -> Dict[str, Any]:
        """Run quick collection (Slack only for recent data)"""
        await self.state_manager.update_state('system/status', 'COLLECTING')
        await self.state_manager.update_state('system/progress', 0)
        
        try:
            # Just collect recent Slack data
            result = await self.run_single_collector('slack', self.collectors['slack'])
            
            await self.state_manager.update_state('system/progress', 100)
            await self.state_manager.update_state('system/status', 'IDLE')
            
            return {
                'success': True,
                'results': {'slack': result},
                'message': "Quick collection completed"
            }
            
        except Exception as e:
            logger.error(f"Quick collection failed: {e}")
            await self.state_manager.update_state('system/status', 'ERROR')
            return {
                'success': False,
                'error': str(e)
            }
    
    async def run_single_collector(self, name: str, collector) -> Dict[str, Any]:
        """Run a single collector and process results"""
        try:
            # Use existing collector interface
            collected_data = collector.collect()  # or collector.collect_recent() 
            
            if name == 'slack':
                await self.process_slack_data(collected_data)
            elif name == 'calendar':
                await self.process_calendar_data(collected_data)
            elif name == 'drive':
                await self.process_drive_data(collected_data)
            elif name == 'employee':
                await self.process_employee_data(collected_data)
            
            return {
                'success': True,
                'count': len(collected_data) if isinstance(collected_data, list) else 1,
                'message': f"{name} collection completed"
            }
            
        except Exception as e:
            logger.error(f"Error collecting {name}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def process_slack_data(self, data: List[Dict[str, Any]]):
        """Process Slack data for dashboard display"""
        # For now, just update a simple count
        # In real implementation, this might extract priorities/commitments
        slack_stats = {
            'message_count': len([d for d in data if d.get('type') == 'message']),
            'last_updated': datetime.now().isoformat()
        }
        
        await self.state_manager.update_state('slack_stats', slack_stats)
    
    async def process_calendar_data(self, data: List[Dict[str, Any]]):
        """Process calendar data and apply coding"""
        # Transform to dashboard format
        calendar_items = []
        
        for event in data:
            item = {
                'time': event.get('start_time', ''),
                'title': event.get('title', event.get('summary', 'Untitled')),
                'date': event.get('date', ''),
                'attendees': event.get('attendees', [])
            }
            
            # Check for alerts (conflicts, important meetings)
            if self.is_important_meeting(event):
                item['alert'] = True
            
            calendar_items.append(item)
        
        # Apply coding system
        coded_calendar = self.coding_manager.assign_codes(CodeType.CALENDAR, calendar_items)
        
        # Update state
        await self.state_manager.update_state('calendar', coded_calendar)
    
    async def process_drive_data(self, data: List[Dict[str, Any]]):
        """Process drive data for activity tracking"""
        # Simple processing for now
        drive_stats = {
            'file_changes': len(data),
            'last_updated': datetime.now().isoformat()
        }
        
        await self.state_manager.update_state('drive_stats', drive_stats)
    
    async def process_employee_data(self, data: List[Dict[str, Any]]):
        """Process employee roster data"""
        # Store employee mapping for attendee resolution
        await self.state_manager.update_state('employee_roster', data)
    
    def is_important_meeting(self, event: Dict[str, Any]) -> bool:
        """Determine if meeting should be flagged as important"""
        title = event.get('title', '').lower()
        
        # Flag meetings with important keywords
        important_keywords = ['budget', 'board', 'review', 'decision', 'urgent']
        return any(keyword in title for keyword in important_keywords)
    
    async def add_progress_callback(self, callback: Callable[[int], None]):
        """Add callback for collection progress updates"""
        self.progress_callbacks.append(callback)
    
    async def notify_progress(self, progress: int):
        """Notify all progress callbacks"""
        for callback in self.progress_callbacks:
            try:
                await callback(progress)
            except Exception as e:
                logger.warning(f"Progress callback failed: {e}")
```

**Acceptance Criteria**:
- Existing collectors integrate without modification
- Real-time progress updates work
- Data gets coded and stored in state
- Error handling doesn't crash system

### Task H2: Unified Command Processor (2 hours)

**Objective**: Process commands from both dashboard and Slack using same logic

**File**: `backend/command_processor.py`
```python
import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from backend.state_manager import StateManager
from backend.coding_system import CodingManager
from backend.code_parser import CodeParser
from backend.brief_generator import BriefGenerator

logger = logging.getLogger(__name__)

class UnifiedCommandProcessor:
    """
    Unified command processing for dashboard and Slack interfaces
    
    Handles all commands consistently regardless of source:
    - approve P7
    - brief C3  
    - refresh / quick / full
    - Multi-commands with pipes
    """
    
    def __init__(self, state_manager: StateManager, coding_manager: CodingManager, 
                 parser: CodeParser, brief_generator: BriefGenerator = None):
        self.state_manager = state_manager
        self.coding_manager = coding_manager
        self.parser = parser
        self.brief_generator = brief_generator or BriefGenerator()
        
        # Command handlers
        self.handlers = {
            'approve': self.handle_approve,
            'complete': self.handle_complete,
            'brief': self.handle_brief,
            'refresh': self.handle_refresh,
            'quick_collection': self.handle_quick_collection,
            'full_collection': self.handle_full_collection,
            'update': self.handle_update
        }
    
    async def execute_command(self, command: str) -> Dict[str, Any]:
        """
        Execute a command and return structured result
        
        Args:
            command: Natural language command string
            
        Returns:
            Dict with success status and result data
        """
        try:
            # Parse command
            parsed = self.parser.parse(command)
            
            if 'error' in parsed:
                return {
                    'success': False,
                    'error': parsed['error'],
                    'suggestions': parsed.get('suggestions', [])
                }
            
            # Handle multiple commands
            if parsed.get('type') == 'multiple':
                return await self.execute_multiple_commands(parsed)
            
            # Single command
            return await self.execute_single_command(parsed)
            
        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            return {
                'success': False,
                'error': f"Command execution failed: {str(e)}",
                'command': command
            }
    
    async def execute_multiple_commands(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        """Execute multiple pipe-separated commands"""
        commands = parsed.get('commands', [])
        results = []
        
        for cmd in commands:
            result = await self.execute_single_command(cmd)
            results.append(result)
            
            # Stop on first failure
            if not result.get('success', False):
                break
        
        overall_success = all(r.get('success', False) for r in results)
        
        return {
            'success': overall_success,
            'type': 'multiple',
            'results': results,
            'message': f"Executed {len(results)} commands"
        }
    
    async def execute_single_command(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single parsed command"""
        action = parsed.get('action')
        
        if action in self.handlers:
            return await self.handlers[action](parsed)
        else:
            return {
                'success': False,
                'error': f"Unknown action: {action}",
                'available_actions': list(self.handlers.keys())
            }
    
    async def handle_approve(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        """Handle approve command"""
        code = parsed.get('code')
        if not code:
            return {'success': False, 'error': 'No code specified for approve'}
        
        # Find the item
        item = self.coding_manager.get_by_code(code)
        if not item:
            return {'success': False, 'error': f'Item {code} not found'}
        
        # Update item status
        code_type = parsed.get('type', 'priority')
        
        if code_type == 'priority':
            item['status'] = 'done'
            # Update in state
            await self.update_item_in_state('priorities', code, item)
            
            return {
                'success': True,
                'action': 'approve',
                'code': code,
                'item_text': item.get('text', 'Unknown'),
                'message': f"Approved {code}: {item.get('text', 'Unknown')}"
            }
        else:
            return {
                'success': False,
                'error': f"Cannot approve {code_type} item {code}"
            }
    
    async def handle_complete(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        """Handle complete/done command"""
        code = parsed.get('code')
        if not code:
            return {'success': False, 'error': 'No code specified for complete'}
        
        item = self.coding_manager.get_by_code(code)
        if not item:
            return {'success': False, 'error': f'Item {code} not found'}
        
        # Mark as complete
        item['status'] = 'done'
        
        # Update in appropriate state section
        code_type = parsed.get('type', 'priority')
        if code_type == 'priority':
            await self.update_item_in_state('priorities', code, item)
        elif code_type == 'commitment':
            await self.update_commitment_in_state(code, item)
        
        return {
            'success': True,
            'action': 'complete',
            'code': code,
            'message': f"Completed {code}"
        }
    
    async def handle_brief(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        """Handle brief command"""
        code = parsed.get('code')
        if not code:
            return {'success': False, 'error': 'No code specified for brief'}
        
        item = self.coding_manager.get_by_code(code)
        if not item:
            return {'success': False, 'error': f'Item {code} not found'}
        
        code_type = parsed.get('type', 'calendar')
        
        if code_type == 'calendar':
            # Generate meeting brief
            brief = await self.brief_generator.generate_meeting_brief(item)
            
            # Update state to show brief
            await self.state_manager.update_state('active_brief', brief)
            
            return {
                'success': True,
                'action': 'brief',
                'code': code,
                'brief_content': brief,
                'message': f"Generated brief for {code}: {item.get('title', 'Meeting')}"
            }
        else:
            return {
                'success': False,
                'error': f"Cannot generate brief for {code_type} item {code}"
            }
    
    async def handle_refresh(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        """Handle refresh command"""
        # Trigger quick collection
        from backend.collector_integration import CollectorIntegrator
        
        integrator = CollectorIntegrator(self.state_manager, self.coding_manager)
        result = await integrator.trigger_quick_collection()
        
        return {
            'success': result['success'],
            'action': 'refresh',
            'message': result.get('message', 'Refresh completed'),
            'details': result
        }
    
    async def handle_quick_collection(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        """Handle quick collection command"""
        return await self.handle_refresh(parsed)
    
    async def handle_full_collection(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        """Handle full collection command"""
        from backend.collector_integration import CollectorIntegrator
        
        integrator = CollectorIntegrator(self.state_manager, self.coding_manager)
        result = await integrator.trigger_full_collection()
        
        return {
            'success': result['success'],
            'action': 'full_collection',
            'message': result.get('message', 'Full collection completed'),
            'details': result
        }
    
    async def handle_update(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        """Handle update command"""
        code = parsed.get('code')
        new_value = parsed.get('new_value')
        
        if not code or not new_value:
            return {'success': False, 'error': 'Update requires code and new value'}
        
        item = self.coding_manager.get_by_code(code)
        if not item:
            return {'success': False, 'error': f'Item {code} not found'}
        
        # Update appropriate field
        if 'text' in item:
            item['text'] = new_value
        elif 'title' in item:
            item['title'] = new_value
        else:
            return {'success': False, 'error': f'Cannot update {code}'}
        
        # Update in state
        code_type = parsed.get('type', 'priority')
        if code_type == 'priority':
            await self.update_item_in_state('priorities', code, item)
        elif code_type == 'calendar':
            await self.update_item_in_state('calendar', code, item)
        
        return {
            'success': True,
            'action': 'update',
            'code': code,
            'new_value': new_value,
            'message': f"Updated {code} to: {new_value}"
        }
    
    async def update_item_in_state(self, section: str, code: str, updated_item: Dict[str, Any]):
        """Update a specific item in state by code"""
        current_state = self.state_manager.state.get(section, [])
        
        for i, item in enumerate(current_state):
            if item.get('code') == code:
                current_state[i] = updated_item
                break
        
        await self.state_manager.update_state(section, current_state)
    
    async def update_commitment_in_state(self, code: str, updated_item: Dict[str, Any]):
        """Update commitment item (special handling for nested structure)"""
        commitments = self.state_manager.state.get('commitments', {'owe': [], 'owed': []})
        
        # Check both owe and owed sections
        for section in ['owe', 'owed']:
            for i, item in enumerate(commitments[section]):
                if item.get('code') == code:
                    commitments[section][i] = updated_item
                    await self.state_manager.update_state('commitments', commitments)
                    return
```

**Acceptance Criteria**:
- Commands execute consistently from any interface
- State updates broadcast to all clients
- Error handling provides useful feedback
- Multi-command support works reliably

### Task H3: Slack Bot Updates (2 hours)

**Objective**: Update existing Slack bot to use new backend API

**File**: `src/bot/slack_bot.py` (Modify existing)
```python
# Add to existing SimpleSlackBot class

import aiohttp
import json

class SimpleSlackBot:
    # ... existing code ...
    
    def __init__(self, api_base_url: str = 'http://localhost:8000'):
        # ... existing initialization ...
        self.api_base_url = api_base_url
        self.session = None
    
    async def connect_to_api(self):
        """Initialize HTTP session for API calls"""
        if not self.session:
            self.session = aiohttp.ClientSession()
    
    async def disconnect_from_api(self):
        """Clean up HTTP session"""
        if self.session:
            await self.session.close()
            self.session = None
    
    def _register_handlers(self):
        """Register slash command handlers with API integration"""
        
        @self.app.command("/cos")
        async def handle_cos_command(ack, respond, command):
            await ack()
            
            try:
                await self.connect_to_api()
                
                # Send command to backend API
                result = await self.execute_api_command(command['text'])
                
                if result['success']:
                    message = self.format_success_response(result)
                else:
                    message = self.format_error_response(result)
                
                await respond(message)
                
            except Exception as e:
                logger.error(f"Error handling /cos command: {e}")
                await respond({
                    "text": f"❌ Error executing command: {str(e)}",
                    "response_type": "ephemeral"
                })
    
    async def execute_api_command(self, command_text: str) -> Dict[str, Any]:
        """Execute command via backend API"""
        url = f"{self.api_base_url}/api/command"
        
        async with self.session.post(url, json={'command': command_text}) as response:
            if response.status == 200:
                return await response.json()
            else:
                error_text = await response.text()
                return {
                    'success': False,
                    'error': f"API error ({response.status}): {error_text}"
                }
    
    def format_success_response(self, result: Dict[str, Any]) -> Dict[str, str]:
        """Format successful command result for Slack"""
        action = result.get('action', 'unknown')
        message = result.get('message', 'Command executed successfully')
        
        if action == 'approve':
            return {
                "text": f"✅ {message}",
                "response_type": "ephemeral"
            }
        elif action == 'brief':
            # Show brief content
            brief_content = result.get('brief_content', {})
            return {
                "text": f"📋 Brief for {result.get('code', 'Unknown')}",
                "blocks": self.format_brief_blocks(brief_content),
                "response_type": "ephemeral"
            }
        elif action in ['refresh', 'quick_collection', 'full_collection']:
            return {
                "text": f"🔄 {message}",
                "response_type": "ephemeral"
            }
        else:
            return {
                "text": f"✅ {message}",
                "response_type": "ephemeral"
            }
    
    def format_error_response(self, result: Dict[str, Any]) -> Dict[str, str]:
        """Format error result for Slack"""
        error = result.get('error', 'Unknown error')
        suggestions = result.get('suggestions', [])
        
        message = f"❌ {error}"
        
        if suggestions:
            message += f"\n\nSuggestions: {', '.join(suggestions)}"
        
        return {
            "text": message,
            "response_type": "ephemeral"
        }
    
    def format_brief_blocks(self, brief_content: Dict[str, Any]) -> List[Dict]:
        """Format brief content as Slack blocks"""
        blocks = []
        
        if brief_content.get('meeting_title'):
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{brief_content['meeting_title']}*"
                }
            })
        
        if brief_content.get('related_content'):
            content_text = "\n".join([
                f"• {item.get('text', item.get('title', 'Unknown'))}"
                for item in brief_content['related_content'][:5]  # Limit to 5 items
            ])
            
            blocks.append({
                "type": "section", 
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Related Content:*\n{content_text}"
                }
            })
        
        return blocks

# Add cleanup on app shutdown
import atexit
atexit.register(lambda: asyncio.run(bot.disconnect_from_api()) if 'bot' in globals() else None)
```

**Acceptance Criteria**:
- Existing Slack commands work through new API
- Responses formatted consistently
- Brief content displays properly in Slack
- Error handling preserves user experience

### Task H4: Brief Generation System (1 hour)

**Objective**: Generate formatted briefs for meetings and daily summaries

**File**: `backend/brief_generator.py`
```python
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class BriefGenerator:
    """
    Generate formatted briefs for meetings and daily intelligence
    """
    
    def __init__(self, search_db=None):
        self.search_db = search_db
    
    async def generate_meeting_brief(self, meeting_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate brief for a specific meeting
        
        Args:
            meeting_data: Calendar item with meeting details
            
        Returns:
            Dict with brief content in multiple formats
        """
        meeting_title = meeting_data.get('title', 'Meeting')
        meeting_code = meeting_data.get('code', 'Unknown')
        attendees = meeting_data.get('attendees', [])
        
        # Search for related content
        related_content = await self.search_related_content(meeting_title, attendees)
        
        # Generate brief
        brief = {
            'meeting_code': meeting_code,
            'meeting_title': meeting_title,
            'meeting_time': meeting_data.get('time', ''),
            'attendees': attendees,
            'related_content': related_content,
            'generated_at': datetime.now().isoformat(),
            'summary': self.generate_meeting_summary(meeting_title, related_content)
        }
        
        # Add formatted versions
        brief['formatted_html'] = self.format_meeting_brief_html(brief)
        brief['formatted_text'] = self.format_meeting_brief_text(brief)
        
        return brief
    
    async def generate_daily_brief(self, state_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate daily intelligence brief"""
        calendar = state_data.get('calendar', [])
        priorities = state_data.get('priorities', [])
        commitments = state_data.get('commitments', {'owe': [], 'owed': []})
        
        # Calculate metrics
        total_meetings = len(calendar)
        pending_priorities = len([p for p in priorities if p.get('status') != 'done'])
        due_today = len([c for c in commitments.get('owe', []) 
                        if self.is_due_today(c.get('due_date'))])
        
        # Generate brief
        brief = {
            'date': datetime.now().strftime('%A, %B %d, %Y'),
            'total_meetings': total_meetings,
            'pending_priorities': pending_priorities,
            'due_today': due_today,
            'executive_summary': self.generate_executive_summary(state_data),
            'critical_items': self.identify_critical_items(state_data),
            'time_sensitive': self.identify_time_sensitive_items(state_data)
        }
        
        brief['formatted_html'] = self.format_daily_brief_html(brief)
        
        return brief
    
    async def search_related_content(self, title: str, attendees: List[str]) -> List[Dict[str, Any]]:
        """Search for content related to meeting"""
        related = []
        
        try:
            if self.search_db:
                # Search by title keywords
                title_results = self.search_db.search(title, limit=3)
                related.extend(title_results)
                
                # Search by attendee activity
                for attendee in attendees[:2]:  # Limit to avoid too many queries
                    attendee_results = self.search_db.search(f"from:{attendee}", limit=2)
                    related.extend(attendee_results)
            else:
                # Mock related content for testing
                related = [
                    {'source': 'slack', 'text': f'Recent discussion about {title}'},
                    {'source': 'drive', 'title': f'{title} - Meeting Notes.doc'}
                ]
        
        except Exception as e:
            logger.warning(f"Error searching related content: {e}")
            related = []
        
        return related[:5]  # Limit results
    
    def generate_meeting_summary(self, title: str, related_content: List[Dict]) -> str:
        """Generate summary for meeting brief"""
        if not related_content:
            return f"Meeting: {title}. No recent related activity found."
        
        return (f"Meeting: {title}. Found {len(related_content)} related items "
                f"including recent discussions and documents.")
    
    def generate_executive_summary(self, state_data: Dict[str, Any]) -> str:
        """Generate executive summary for daily brief"""
        priorities = state_data.get('priorities', [])
        commitments = state_data.get('commitments', {'owe': [], 'owed': []})
        
        total_priorities = len(priorities)
        pending_priorities = len([p for p in priorities if p.get('status') != 'done'])
        total_commitments = len(commitments.get('owe', [])) + len(commitments.get('owed', []))
        
        return (f"You have {pending_priorities} of {total_priorities} priorities pending "
                f"and {total_commitments} active commitments requiring attention.")
    
    def identify_critical_items(self, state_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify critical items requiring immediate attention"""
        critical = []
        
        # High priority items
        priorities = state_data.get('priorities', [])
        for priority in priorities:
            if priority.get('alert') or priority.get('status') == 'partial':
                critical.append({
                    'type': 'priority',
                    'code': priority.get('code'),
                    'text': priority.get('text'),
                    'reason': 'High priority or partially complete'
                })
        
        # Urgent commitments
        commitments = state_data.get('commitments', {'owe': [], 'owed': []})
        for commitment in commitments.get('owe', []):
            if self.is_due_today(commitment.get('due_date')):
                critical.append({
                    'type': 'commitment',
                    'code': commitment.get('code'),
                    'text': commitment.get('text'),
                    'reason': 'Due today'
                })
        
        return critical[:5]  # Limit to top 5
    
    def identify_time_sensitive_items(self, state_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify time-sensitive items for today"""
        time_sensitive = []
        
        # Today's meetings
        calendar = state_data.get('calendar', [])
        for meeting in calendar:
            if meeting.get('alert'):
                time_sensitive.append({
                    'type': 'meeting',
                    'code': meeting.get('code'),
                    'time': meeting.get('time'),
                    'title': meeting.get('title'),
                    'reason': 'Important meeting'
                })
        
        return time_sensitive
    
    def is_due_today(self, due_date_str: Optional[str]) -> bool:
        """Check if a due date is today"""
        if not due_date_str:
            return False
        
        try:
            due_date = datetime.fromisoformat(due_date_str).date()
            return due_date == datetime.now().date()
        except:
            return False
    
    def format_meeting_brief_html(self, brief: Dict[str, Any]) -> str:
        """Format meeting brief as HTML"""
        html = f"""
        <div class="brief-section">
            <h3>Meeting Brief: {brief['meeting_title']}</h3>
            <p><strong>Code:</strong> {brief['meeting_code']}</p>
            <p><strong>Time:</strong> {brief['meeting_time']}</p>
            
            <h4>Related Content</h4>
            <ul>
        """
        
        for item in brief['related_content']:
            text = item.get('text', item.get('title', 'Unknown'))
            html += f"<li>{text}</li>"
        
        html += """
            </ul>
        </div>
        """
        
        return html
    
    def format_meeting_brief_text(self, brief: Dict[str, Any]) -> str:
        """Format meeting brief as plain text"""
        text = f"Meeting Brief: {brief['meeting_title']} ({brief['meeting_code']})\n"
        text += f"Time: {brief['meeting_time']}\n\n"
        
        if brief['related_content']:
            text += "Related Content:\n"
            for item in brief['related_content']:
                item_text = item.get('text', item.get('title', 'Unknown'))
                text += f"• {item_text}\n"
        
        return text
    
    def format_daily_brief_html(self, brief: Dict[str, Any]) -> str:
        """Format daily brief as HTML"""
        html = f"""
        <div class="brief-title">Daily Intelligence Brief</div>
        <div class="brief-date">{brief['date']}</div>
        
        <div class="brief-section">
            <h3>Executive Summary</h3>
            <p>{brief['executive_summary']}</p>
        </div>
        """
        
        if brief['critical_items']:
            html += """
            <div class="brief-section">
                <h3>Critical Items</h3>
                <ul>
            """
            for item in brief['critical_items']:
                html += f"<li><strong>{item['code']}:</strong> {item['text']} - {item['reason']}</li>"
            html += "</ul></div>"
        
        return html
```

**Acceptance Criteria**:
- Meeting briefs generate with related content
- Daily briefs provide useful executive summary
- Multiple output formats supported
- Performance acceptable for real-time use

## Integration Requirements

### Database Integration
- Use existing SearchDatabase for content search
- Query performance <500ms for brief generation
- No modifications to search infrastructure

### Collector Compatibility
- Work with existing collector interfaces
- Preserve all existing functionality
- Add progress callbacks without breaking changes

### State Management
- Integrate seamlessly with Agent E state manager
- Maintain real-time update performance
- Handle concurrent access properly

## Files to Create/Modify

### New Integration Files
```
backend/
├── collector_integration.py    # Connect collectors to API
├── command_processor.py       # Unified command handling  
└── brief_generator.py         # Brief generation system
```

### Modified Files
```
src/bot/slack_bot.py           # Add API integration
tools/run_frontend.py          # Startup script
```

### Configuration Files
```
config/
└── integration_config.yaml   # Integration settings
```

## Success Criteria

### Collector Integration ✅
- [ ] Existing collectors work without modification
- [ ] Real-time progress updates during collection
- [ ] Data properly coded and stored in state
- [ ] Error handling doesn't crash system

### Command Processing ✅
- [ ] Commands work identically from dashboard and Slack
- [ ] Multi-command pipes execute in sequence  
- [ ] State updates broadcast to all clients
- [ ] Error messages provide helpful feedback

### Slack Bot Integration ✅
- [ ] Existing Slack functionality preserved
- [ ] Commands forward to backend API correctly
- [ ] Brief content displays well in Slack
- [ ] Response times acceptable (<3 seconds)

### Brief Generation ✅
- [ ] Meeting briefs include relevant context
- [ ] Daily briefs provide actionable insights
- [ ] Performance suitable for real-time use
- [ ] Multiple output formats work correctly

## Delivery Checklist

Before marking Agent H complete:
- [ ] All test suites written and passing
- [ ] Collector integration functional
- [ ] Command processor handles all common commands
- [ ] Slack bot updated and working
- [ ] Brief generation produces useful output
- [ ] Performance targets met across all operations
- [ ] No regression in existing functionality

---

**Contact Agent H Team Lead for questions or Agent I testing coordination**  
**Integration Point**: Agent I depends on all Agent H systems working