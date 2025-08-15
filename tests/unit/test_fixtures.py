"""
Validation tests for all mock fixture data.
Ensures fixtures are deterministic, comprehensive, and cover all edge cases.
These tests validate the test data itself before using it in collector tests.
"""

import json
import pytest
from datetime import datetime, timedelta
from typing import Dict, List, Any

# Import all mock data modules
from tests.fixtures.mock_slack_data import (
    get_mock_channels, get_mock_users, get_mock_messages,
    get_mock_rate_limit_responses, get_mock_api_error_responses,
    get_mock_collection_result as get_slack_collection_result,
    validate_mock_data as validate_slack_data
)

from tests.fixtures.mock_calendar_data import (
    get_mock_calendars, get_mock_events, get_mock_event_changes,
    get_mock_api_errors as get_calendar_api_errors,
    get_mock_timezone_data, get_mock_collection_result as get_calendar_collection_result,
    validate_mock_calendar_data
)

from tests.fixtures.mock_employee_data import (
    get_mock_employee_roster, get_mock_organizational_chart,
    get_mock_department_structure, get_mock_employee_changes,
    get_mock_id_mappings, get_mock_sync_errors,
    get_mock_collection_result as get_employee_collection_result,
    validate_mock_employee_data
)

from tests.fixtures.mock_drive_data import (
    get_mock_drive_files, get_mock_drive_changes, get_mock_permission_changes,
    get_mock_api_errors as get_drive_api_errors, get_mock_privacy_filters,
    get_mock_collection_result as get_drive_collection_result,
    validate_mock_drive_data
)


class TestMockDataDeterminism:
    """Test that mock data is deterministic - same inputs produce identical outputs."""
    
    def test_slack_data_is_deterministic(self):
        """Slack mock data returns consistent results across multiple calls."""
        # Test channels
        channels1 = get_mock_channels()
        channels2 = get_mock_channels()
        assert channels1 == channels2, "Slack channels data should be deterministic"
        
        # Test users
        users1 = get_mock_users()
        users2 = get_mock_users()
        assert users1 == users2, "Slack users data should be deterministic"
        
        # Test messages
        messages1 = get_mock_messages()
        messages2 = get_mock_messages()
        assert messages1 == messages2, "Slack messages data should be deterministic"
        
        # Test collection result
        result1 = get_slack_collection_result()
        result2 = get_slack_collection_result()
        assert result1 == result2, "Slack collection result should be deterministic"
    
    def test_calendar_data_is_deterministic(self):
        """Calendar mock data returns consistent results across multiple calls."""
        # Test calendars
        calendars1 = get_mock_calendars()
        calendars2 = get_mock_calendars()
        assert calendars1 == calendars2, "Calendar data should be deterministic"
        
        # Test events
        events1 = get_mock_events()
        events2 = get_mock_events()
        assert events1 == events2, "Calendar events data should be deterministic"
        
        # Test changes
        changes1 = get_mock_event_changes()
        changes2 = get_mock_event_changes()
        assert changes1 == changes2, "Calendar changes data should be deterministic"
    
    def test_employee_data_is_deterministic(self):
        """Employee mock data returns consistent results across multiple calls."""
        # Test roster
        roster1 = get_mock_employee_roster()
        roster2 = get_mock_employee_roster()
        assert roster1 == roster2, "Employee roster data should be deterministic"
        
        # Test org chart
        org1 = get_mock_organizational_chart()
        org2 = get_mock_organizational_chart()
        assert org1 == org2, "Organizational chart should be deterministic"
        
        # Test ID mappings
        mappings1 = get_mock_id_mappings()
        mappings2 = get_mock_id_mappings()
        assert mappings1 == mappings2, "ID mappings should be deterministic"
    
    def test_drive_data_is_deterministic(self):
        """Drive mock data returns consistent results across multiple calls."""
        # Test files
        files1 = get_mock_drive_files()
        files2 = get_mock_drive_files()
        assert files1 == files2, "Drive files data should be deterministic"
        
        # Test changes
        changes1 = get_mock_drive_changes()
        changes2 = get_mock_drive_changes()
        assert changes1 == changes2, "Drive changes should be deterministic"
        
        # Test permission changes
        perms1 = get_mock_permission_changes()
        perms2 = get_mock_permission_changes()
        assert perms1 == perms2, "Permission changes should be deterministic"


class TestMockDataValidJson:
    """Test that all mock data is valid JSON and properly serializable."""
    
    def test_slack_data_is_valid_json(self):
        """All Slack mock data can be serialized to valid JSON."""
        # Test all Slack data structures
        json.dumps(get_mock_channels())
        json.dumps(get_mock_users()) 
        json.dumps(get_mock_messages())
        json.dumps(get_mock_rate_limit_responses())
        json.dumps(get_mock_api_error_responses())
        json.dumps(get_slack_collection_result())
        # If we get here without exception, JSON is valid
    
    def test_calendar_data_is_valid_json(self):
        """All Calendar mock data can be serialized to valid JSON."""
        json.dumps(get_mock_calendars())
        json.dumps(get_mock_events())
        json.dumps(get_mock_event_changes())
        json.dumps(get_calendar_api_errors())
        json.dumps(get_mock_timezone_data())
        json.dumps(get_calendar_collection_result())
    
    def test_employee_data_is_valid_json(self):
        """All Employee mock data can be serialized to valid JSON."""
        json.dumps(get_mock_employee_roster())
        json.dumps(get_mock_organizational_chart())
        json.dumps(get_mock_department_structure())
        json.dumps(get_mock_employee_changes())
        json.dumps(get_mock_id_mappings())
        json.dumps(get_mock_sync_errors())
        json.dumps(get_employee_collection_result())
    
    def test_drive_data_is_valid_json(self):
        """All Drive mock data can be serialized to valid JSON."""
        json.dumps(get_mock_drive_files())
        json.dumps(get_mock_drive_changes())
        json.dumps(get_mock_permission_changes())
        json.dumps(get_drive_api_errors())
        json.dumps(get_mock_privacy_filters())
        json.dumps(get_drive_collection_result())


class TestSlackMockDataEdgeCases:
    """Test that Slack mock data covers all required edge cases."""
    
    def test_slack_channels_cover_all_types(self):
        """Slack channels include all channel types and states."""
        channels = get_mock_channels()
        
        # Check we have all channel types
        channel_types = {
            'public': any(c['is_channel'] and not c['is_private'] for c in channels),
            'private': any(c['is_channel'] and c['is_private'] for c in channels), 
            'dm': any(c['is_im'] for c in channels),
            'group': any(c['is_group'] for c in channels),
            'archived': any(c['is_archived'] for c in channels)
        }
        
        assert all(channel_types.values()), f"Missing channel types: {[k for k, v in channel_types.items() if not v]}"
        
        # Check we have channels with different member counts
        member_counts = [c.get('num_members', 0) for c in channels]
        assert 0 in member_counts, "Should have empty channels"
        assert any(count > 3 for count in member_counts), "Should have channels with multiple members"
    
    def test_slack_users_cover_all_types(self):
        """Slack users include all user types and states."""
        users = get_mock_users()
        
        user_types = {
            'regular': any(not u['is_bot'] and not u['deleted'] for u in users),
            'admin': any(u.get('is_admin', False) for u in users),
            'owner': any(u.get('is_owner', False) for u in users),
            'bot': any(u['is_bot'] for u in users),
            'deleted': any(u['deleted'] for u in users),
            'restricted': any(u.get('is_restricted', False) for u in users),
            'app_user': any(u.get('is_app_user', False) for u in users)
        }
        
        assert all(user_types.values()), f"Missing user types: {[k for k, v in user_types.items() if not v]}"
    
    def test_slack_messages_cover_all_types(self):
        """Slack messages include all message types and edge cases."""
        messages = get_mock_messages()
        
        message_types = {
            'regular': any(m.get('subtype') is None for m in messages),
            'bot': any(m.get('subtype') == 'bot_message' for m in messages),
            'system': any(m.get('subtype') == 'channel_join' for m in messages),
            'deleted': any(m.get('subtype') == 'message_deleted' for m in messages),
            'edited': any(m.get('subtype') == 'message_changed' for m in messages),
            'threaded': any(m.get('thread_ts') and m.get('thread_ts') != m.get('ts') for m in messages),
            'with_reactions': any(m.get('reactions') for m in messages),
            'with_files': any(m.get('files') for m in messages)
        }
        
        assert all(message_types.values()), f"Missing message types: {[k for k, v in message_types.items() if not v]}"
    
    def test_slack_data_relationships_valid(self):
        """Slack data has valid cross-references between channels, users, and messages."""
        channels = get_mock_channels()
        users = get_mock_users()
        messages = get_mock_messages()
        
        channel_ids = {c['id'] for c in channels}
        user_ids = {u['id'] for u in users}
        
        # Check message references
        for msg in messages:
            if 'channel' in msg:
                assert msg['channel'] in channel_ids, f"Message references unknown channel: {msg['channel']}"
            if 'user' in msg:
                assert msg['user'] in user_ids, f"Message references unknown user: {msg['user']}"


class TestCalendarMockDataEdgeCases:
    """Test that Calendar mock data covers all required edge cases."""
    
    def test_calendar_events_cover_all_types(self):
        """Calendar events include all event types and states."""
        events = get_mock_events()
        
        event_types = {
            'regular': any(e.get('eventType') == 'default' for e in events),
            'all_day': any('date' in e.get('start', {}) for e in events),
            'recurring': any(e.get('recurrence') for e in events),
            'cancelled': any(e.get('status') == 'cancelled' for e in events),
            'private': any(e.get('visibility') == 'private' for e in events),
            'out_of_office': any(e.get('eventType') == 'outOfOffice' for e in events),
            'working_location': any(e.get('eventType') == 'workingLocation' for e in events),
            'focus_time': any(e.get('eventType') == 'focusTime' for e in events)
        }
        
        assert all(event_types.values()), f"Missing event types: {[k for k, v in event_types.items() if not v]}"
    
    def test_calendar_timezones_handled(self):
        """Calendar events span multiple timezones."""
        events = get_mock_events()
        
        timezones = set()
        for event in events:
            if 'timeZone' in event.get('start', {}):
                timezones.add(event['start']['timeZone'])
            if 'timeZone' in event.get('end', {}):
                timezones.add(event['end']['timeZone'])
        
        # Should have at least 3 different timezones
        assert len(timezones) >= 3, f"Should have multiple timezones, found: {timezones}"
        
        expected_zones = {'America/New_York', 'America/Los_Angeles', 'Europe/London'}
        assert expected_zones.intersection(timezones), f"Should include major timezones, found: {timezones}"
    
    def test_calendar_attendees_comprehensive(self):
        """Calendar attendees have all response states."""
        events = get_mock_events()
        
        response_statuses = set()
        for event in events:
            for attendee in event.get('attendees', []):
                response_statuses.add(attendee.get('responseStatus'))
        
        expected_statuses = {'accepted', 'declined', 'tentative', 'needsAction'}
        missing = expected_statuses - response_statuses
        assert not missing, f"Missing response statuses: {missing}"


class TestEmployeeMockDataEdgeCases:
    """Test that Employee mock data covers all required edge cases."""
    
    def test_employee_statuses_comprehensive(self):
        """Employee roster includes all employment statuses."""
        roster = get_mock_employee_roster()
        
        statuses = {emp['employee_status'] for emp in roster}
        expected_statuses = {'active', 'onboarding', 'terminated', 'pre_start'}
        missing = expected_statuses - statuses
        assert not missing, f"Missing employee statuses: {missing}"
    
    def test_employment_types_comprehensive(self):
        """Employee roster includes all employment types."""
        roster = get_mock_employee_roster()
        
        types = {emp['employment_type'] for emp in roster}
        expected_types = {'full_time', 'contractor', 'intern'}
        missing = expected_types - types
        assert not missing, f"Missing employment types: {missing}"
    
    def test_id_mapping_completeness(self):
        """ID mappings cover all active employees."""
        roster = get_mock_employee_roster()
        mappings = get_mock_id_mappings()
        
        active_employees = [e for e in roster if e['employee_status'] in ['active', 'onboarding']]
        
        for emp in active_employees:
            email = emp['email']
            assert email in mappings, f"Missing ID mapping for {email}"
            
            mapping = mappings[email]
            assert mapping['employee_id'] == emp['employee_id']
            assert mapping['display_name'] == emp['display_name']
    
    def test_organizational_chart_consistency(self):
        """Organizational chart matches employee roster."""
        roster = get_mock_employee_roster()
        org_chart = get_mock_organizational_chart()
        
        # Active employees should be in org chart
        active_emails = {e['email'] for e in roster if e['employee_status'] == 'active'}
        org_emails = set(org_chart.keys())
        
        # Most active employees should be in org chart (some exceptions for very new employees)
        overlap = len(active_emails & org_emails)
        assert overlap >= len(active_emails) * 0.8, "Org chart should include most active employees"


class TestDriveMockDataEdgeCases:
    """Test that Drive mock data covers all required edge cases."""
    
    def test_drive_privacy_compliance(self):
        """Drive mock data contains no file content - only metadata."""
        files = get_mock_drive_files()
        
        # Ensure no content fields exist
        for file_item in files:
            forbidden_fields = ['content', 'body', 'text_content', 'file_content', 'data']
            for field in forbidden_fields:
                assert field not in file_item, f"File {file_item['id']} contains forbidden field: {field}"
    
    def test_drive_file_types_comprehensive(self):
        """Drive files include all major file types."""
        files = get_mock_drive_files()
        
        mime_types = {f['mimeType'] for f in files}
        expected_types = {
            'application/vnd.google-apps.folder',
            'application/vnd.google-apps.document', 
            'application/vnd.google-apps.spreadsheet',
            'application/vnd.google-apps.presentation',
            'application/pdf',
            'image/png'
        }
        
        missing = expected_types - mime_types
        assert not missing, f"Missing file types: {missing}"
    
    def test_drive_sharing_states_covered(self):
        """Drive files cover different sharing states."""
        files = get_mock_drive_files()
        
        sharing_states = {
            'private': any(not f.get('shared', True) for f in files),
            'internal': any(f.get('shared') and all(
                '@company.com' in p.get('emailAddress', '') or p.get('domain') == 'company.com'
                for p in f.get('permissions', []) if p.get('emailAddress') or p.get('domain')
            ) for f in files),
            'external': any(f.get('shared') and any(
                '@company.com' not in p.get('emailAddress', '') and p.get('domain') != 'company.com'
                for p in f.get('permissions', []) if p.get('emailAddress')
            ) for f in files),
            'trashed': any(f.get('trashed', False) for f in files)
        }
        
        assert all(sharing_states.values()), f"Missing sharing states: {[k for k, v in sharing_states.items() if not v]}"
    
    def test_drive_permission_roles_complete(self):
        """Drive permissions include all role types."""
        files = get_mock_drive_files()
        
        roles = set()
        for file_item in files:
            for permission in file_item.get('permissions', []):
                roles.add(permission.get('role'))
        
        expected_roles = {'owner', 'writer', 'reader', 'commenter'}
        missing = expected_roles - roles
        assert not missing, f"Missing permission roles: {missing}"


class TestMockDataInternalValidation:
    """Test internal validation functions for all mock data."""
    
    def test_slack_validation_passes(self):
        """Slack mock data passes its internal validation."""
        assert validate_slack_data(), "Slack mock data should pass validation"
    
    def test_calendar_validation_passes(self):
        """Calendar mock data passes its internal validation."""
        assert validate_mock_calendar_data(), "Calendar mock data should pass validation"
    
    def test_employee_validation_passes(self):
        """Employee mock data passes its internal validation."""
        assert validate_mock_employee_data(), "Employee mock data should pass validation"
    
    def test_drive_validation_passes(self):
        """Drive mock data passes its internal validation."""
        assert validate_mock_drive_data(), "Drive mock data should pass validation"


class TestMockDataScaleAndPerformance:
    """Test that mock data provides sufficient scale for testing."""
    
    def test_slack_data_scale(self):
        """Slack mock data provides sufficient scale for testing."""
        channels = get_mock_channels()
        users = get_mock_users() 
        messages = get_mock_messages()
        
        assert len(channels) >= 5, f"Should have >=5 channels, got {len(channels)}"
        assert len(users) >= 7, f"Should have >=7 users, got {len(users)}"
        assert len(messages) >= 10, f"Should have >=10 messages, got {len(messages)}"
    
    def test_calendar_data_scale(self):
        """Calendar mock data provides sufficient scale for testing."""
        calendars = get_mock_calendars()
        events = get_mock_events()
        
        assert len(calendars) >= 4, f"Should have >=4 calendars, got {len(calendars)}"
        assert len(events) >= 10, f"Should have >=10 events, got {len(events)}"
    
    def test_employee_data_scale(self):
        """Employee mock data provides sufficient scale for testing."""
        roster = get_mock_employee_roster()
        
        assert len(roster) >= 8, f"Should have >=8 employees, got {len(roster)}"
        
        # Should have employees in different states
        active = [e for e in roster if e['employee_status'] == 'active']
        assert len(active) >= 5, f"Should have >=5 active employees, got {len(active)}"
    
    def test_drive_data_scale(self):
        """Drive mock data provides sufficient scale for testing."""
        files = get_mock_drive_files()
        changes = get_mock_drive_changes()
        
        assert len(files) >= 7, f"Should have >=7 files, got {len(files)}"
        assert len(changes) >= 5, f"Should have >=5 changes, got {len(changes)}"


class TestCrossSystemConsistency:
    """Test consistency across different mock data systems."""
    
    def test_user_id_consistency(self):
        """User IDs are consistent across Slack and Employee systems."""
        slack_users = get_mock_users()
        employees = get_mock_employee_roster()
        
        # Build mapping from email to slack ID
        email_to_slack = {}
        for user in slack_users:
            if user.get('profile', {}).get('email'):
                email_to_slack[user['profile']['email']] = user['id']
        
        # Check employee slack IDs match
        for emp in employees:
            if emp.get('slack_id') and emp['email'] in email_to_slack:
                expected_slack_id = email_to_slack[emp['email']]
                assert emp['slack_id'] == expected_slack_id, \
                    f"Slack ID mismatch for {emp['email']}: employee={emp['slack_id']}, slack={expected_slack_id}"
    
    def test_calendar_user_consistency(self):
        """Calendar users are consistent with Employee system."""
        calendars = get_mock_calendars()
        employees = get_mock_employee_roster()
        
        # Build set of employee emails
        employee_emails = {emp['email'] for emp in employees if emp['employee_status'] == 'active'}
        
        # Check calendar owners are employees
        calendar_emails = {cal['id'] for cal in calendars if '@company.com' in cal['id']}
        
        # Most calendar emails should correspond to employees
        overlap = len(calendar_emails & employee_emails)
        assert overlap >= len(calendar_emails) * 0.6, \
            f"Calendar users should mostly be employees. Overlap: {overlap}/{len(calendar_emails)}"


if __name__ == "__main__":
    # Run basic validation
    print("Running mock data validation...")
    
    # Test determinism
    print("✓ Testing determinism...")
    test_determinism = TestMockDataDeterminism()
    test_determinism.test_slack_data_is_deterministic()
    test_determinism.test_calendar_data_is_deterministic()
    test_determinism.test_employee_data_is_deterministic()
    test_determinism.test_drive_data_is_deterministic()
    
    # Test JSON validity
    print("✓ Testing JSON validity...")
    test_json = TestMockDataValidJson()
    test_json.test_slack_data_is_valid_json()
    test_json.test_calendar_data_is_valid_json()
    test_json.test_employee_data_is_valid_json()
    test_json.test_drive_data_is_valid_json()
    
    # Test internal validation
    print("✓ Testing internal validation...")
    test_validation = TestMockDataInternalValidation()
    test_validation.test_slack_validation_passes()
    test_validation.test_calendar_validation_passes()
    test_validation.test_employee_validation_passes()
    test_validation.test_drive_validation_passes()
    
    print("All mock data validation passed! ✅")