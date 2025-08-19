"""
Mock API responses for testing collectors and integrations.

Provides realistic mock data for:
- Slack API responses
- Google Calendar API responses  
- Google Drive API responses
- Authentication flows
"""

from typing import Dict, List, Any
from datetime import datetime, timedelta

# Mock Slack API responses
def mock_slack_conversations_list():
    """Mock response for Slack conversations.list API"""
    return {
        "ok": True,
        "channels": [
            {
                "id": "C1234567890",
                "name": "general",
                "is_channel": True,
                "is_group": False,
                "is_im": False,
                "created": 1609459200,
                "creator": "U0987654321",
                "is_archived": False,
                "is_general": True,
                "unlinked": 0,
                "name_normalized": "general",
                "is_shared": False,
                "is_ext_shared": False,
                "is_org_shared": False,
                "pending_shared": [],
                "is_pending_ext_shared": False,
                "is_member": True,
                "is_private": False,
                "is_mpim": False,
                "topic": {
                    "value": "Company-wide announcements and general discussion",
                    "creator": "U0987654321",
                    "last_set": 1609459200
                },
                "purpose": {
                    "value": "This channel is for team-wide communication and updates",
                    "creator": "U0987654321", 
                    "last_set": 1609459200
                },
                "num_members": 25
            }
        ],
        "response_metadata": {
            "next_cursor": ""
        }
    }

def mock_slack_conversations_history():
    """Mock response for Slack conversations.history API"""
    return {
        "ok": True,
        "messages": [
            {
                "type": "message",
                "text": "I'll have the quarterly report done by Friday",
                "user": "U0987654321",
                "ts": "1692364245.123456",
                "thread_ts": "1692364245.123456",
                "reply_count": 2,
                "reply_users_count": 2,
                "latest_reply": "1692364845.789012",
                "reply_users": ["U1111111111", "U2222222222"],
                "subscribed": False,
                "reactions": [
                    {
                        "name": "thumbsup",
                        "users": ["U1111111111"],
                        "count": 1
                    }
                ]
            },
            {
                "type": "message", 
                "text": "Great! Looking forward to reviewing it",
                "user": "U1111111111",
                "ts": "1692364845.789012",
                "thread_ts": "1692364245.123456"
            }
        ],
        "has_more": False,
        "pin_count": 0,
        "response_metadata": {
            "next_cursor": ""
        }
    }

def mock_slack_users_list():
    """Mock response for Slack users.list API"""
    return {
        "ok": True,
        "members": [
            {
                "id": "U0987654321",
                "team_id": "T1234567890",
                "name": "alice.smith",
                "deleted": False,
                "color": "9f69e7",
                "real_name": "Alice Smith",
                "tz": "America/New_York",
                "tz_label": "Eastern Daylight Time",
                "tz_offset": -14400,
                "profile": {
                    "title": "Engineering Manager",
                    "phone": "",
                    "skype": "",
                    "real_name": "Alice Smith",
                    "real_name_normalized": "Alice Smith",
                    "display_name": "alice",
                    "display_name_normalized": "alice",
                    "fields": {},
                    "status_text": "",
                    "status_emoji": "",
                    "status_expiration": 0,
                    "avatar_hash": "ge3b51ca72de",
                    "email": "alice.smith@company.com",
                    "first_name": "Alice",
                    "last_name": "Smith",
                    "image_24": "https://...",
                    "image_32": "https://...",
                    "image_48": "https://...",
                    "image_72": "https://...",
                    "image_192": "https://...",
                    "image_512": "https://..."
                },
                "is_admin": False,
                "is_owner": False,
                "is_primary_owner": False,
                "is_restricted": False,
                "is_ultra_restricted": False,
                "is_bot": False,
                "updated": 1692364245,
                "is_app_user": False,
                "has_2fa": False
            }
        ],
        "cache_ts": 1692364245,
        "response_metadata": {
            "next_cursor": ""
        }
    }

# Mock Google Calendar API responses
def mock_calendar_events_list():
    """Mock response for Google Calendar events.list API"""
    return {
        "kind": "calendar#events",
        "etag": "\"p33g3cd0edk67o0g\"",
        "summary": "alice@company.com",
        "updated": "2025-08-18T12:00:00.000Z",
        "timeZone": "America/New_York",
        "accessRole": "owner",
        "defaultReminders": [
            {
                "method": "popup",
                "minutes": 30
            }
        ],
        "nextSyncToken": "CAIShjdlKLt1CL_8wQ==",
        "items": [
            {
                "kind": "calendar#event",
                "etag": "\"3181161784712000\"",
                "id": "abc123def456ghi789",
                "status": "confirmed",
                "htmlLink": "https://www.google.com/calendar/event?eid=...",
                "created": "2025-08-15T10:00:00.000Z",
                "updated": "2025-08-15T10:00:00.000Z",
                "summary": "Project Alpha Review Meeting",
                "description": "Review Q3 progress and plan Q4 deliverables",
                "location": "Conference Room A",
                "creator": {
                    "email": "alice.smith@company.com",
                    "displayName": "Alice Smith"
                },
                "organizer": {
                    "email": "alice.smith@company.com",
                    "displayName": "Alice Smith"
                },
                "start": {
                    "dateTime": "2025-08-20T14:00:00-04:00",
                    "timeZone": "America/New_York"
                },
                "end": {
                    "dateTime": "2025-08-20T15:00:00-04:00",
                    "timeZone": "America/New_York"
                },
                "iCalUID": "abc123def456ghi789@google.com",
                "sequence": 0,
                "attendees": [
                    {
                        "email": "alice.smith@company.com",
                        "displayName": "Alice Smith",
                        "organizer": True,
                        "responseStatus": "accepted"
                    },
                    {
                        "email": "bob.jones@company.com",
                        "displayName": "Bob Jones",
                        "responseStatus": "accepted"
                    }
                ],
                "reminders": {
                    "useDefault": False,
                    "overrides": [
                        {
                            "method": "popup",
                            "minutes": 30
                        }
                    ]
                }
            }
        ]
    }

# Mock Google Drive API responses  
def mock_drive_files_list():
    """Mock response for Google Drive files.list API"""
    return {
        "kind": "drive#fileList",
        "nextPageToken": "next_page_token_123",
        "incompleteSearch": False,
        "files": [
            {
                "kind": "drive#file",
                "id": "1abc2def3ghi4jkl5mno",
                "name": "Q3_Project_Alpha_Report.pdf",
                "mimeType": "application/pdf",
                "parents": ["0B9jT5xK8V3DdOGVhNjlmbW9HYVU"],
                "createdTime": "2025-08-15T14:30:00.000Z",
                "modifiedTime": "2025-08-18T16:45:00.000Z",
                "version": "3",
                "size": "2048576",
                "md5Checksum": "d41d8cd98f00b204e9800998ecf8427e",
                "webViewLink": "https://drive.google.com/file/d/1abc2def3ghi4jkl5mno/view?usp=drivesdk",
                "webContentLink": "https://drive.google.com/uc?id=1abc2def3ghi4jkl5mno&export=download",
                "iconLink": "https://drive-thirdparty.googleusercontent.com/16/type/application/pdf",
                "hasThumbnail": True,
                "thumbnailLink": "https://docs.google.com/a/company.com/file/d/1abc2def3ghi4jkl5mno/thumbnail?sz=s220",
                "thumbnailVersion": "2",
                "viewedByMe": True,
                "viewedByMeTime": "2025-08-18T10:00:00.000Z",
                "owners": [
                    {
                        "kind": "drive#user",
                        "displayName": "Alice Smith",
                        "photoLink": "https://lh3.googleusercontent.com/a/default-user=s64",
                        "me": True,
                        "permissionId": "12345678901234567890",
                        "emailAddress": "alice.smith@company.com"
                    }
                ],
                "lastModifyingUser": {
                    "kind": "drive#user",
                    "displayName": "Alice Smith",
                    "photoLink": "https://lh3.googleusercontent.com/a/default-user=s64",
                    "me": True,
                    "permissionId": "12345678901234567890",
                    "emailAddress": "alice.smith@company.com"
                },
                "shared": True,
                "ownedByMe": True,
                "capabilities": {
                    "canAddChildren": False,
                    "canChangeCopyRequiresWriterPermission": True,
                    "canChangeViewersCanCopyContent": True,
                    "canComment": True,
                    "canCopy": True,
                    "canDelete": True,
                    "canDownload": True,
                    "canEdit": True,
                    "canListChildren": False,
                    "canMoveItemIntoTeamDrive": True,
                    "canMoveTeamDriveItem": False,
                    "canReadRevisions": True,
                    "canRemoveChildren": False,
                    "canRename": True,
                    "canShare": True,
                    "canTrash": True,
                    "canUntrash": True
                },
                "permissions": [
                    {
                        "kind": "drive#permission",
                        "id": "12345678901234567890",
                        "type": "user",
                        "emailAddress": "alice.smith@company.com",
                        "role": "owner",
                        "displayName": "Alice Smith",
                        "photoLink": "https://lh3.googleusercontent.com/a/default-user=s64",
                        "deleted": False
                    }
                ],
                "quotaBytesUsed": "2048576",
                "isAppAuthorized": True
            }
        ]
    }

# Authentication mock responses
def mock_oauth_token_response():
    """Mock OAuth token response"""
    return {
        "access_token": "ya29.mock_access_token_here",
        "refresh_token": "1//mock_refresh_token_here", 
        "token_type": "Bearer",
        "expires_in": 3599,
        "scope": "https://www.googleapis.com/auth/calendar https://www.googleapis.com/auth/drive.metadata.readonly"
    }

def mock_slack_oauth_access():
    """Mock Slack OAuth access response"""
    return {
        "ok": True,
        "access_token": "xoxb-mock-slack-bot-token",
        "token_type": "bot", 
        "scope": "channels:read,chat:write,groups:read,im:read,mpim:read,users:read",
        "bot_user_id": "U01ABC123DEF",
        "app_id": "A01ABC123DEF",
        "team": {
            "id": "T1234567890",
            "name": "Test Company"
        },
        "enterprise": None,
        "authed_user": {
            "id": "U0987654321",
            "scope": "search:read",
            "access_token": "xoxp-mock-user-token",
            "token_type": "user"
        }
    }