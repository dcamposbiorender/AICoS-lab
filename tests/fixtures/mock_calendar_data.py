"""
Comprehensive mock Google Calendar data for testing collector wrappers.
Covers timezones, recurring events, attendees, modifications, and edge cases.
Data is deterministic - same function calls return identical results.
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Any
import pytz

# Base timestamp for deterministic data (Aug 15, 2025, 9 AM UTC)
BASE_DT = datetime(2025, 8, 15, 9, 0, 0, tzinfo=pytz.UTC)

def get_mock_calendars() -> List[Dict[str, Any]]:
    """Mock Google Calendar list with different access levels."""
    return [
        {
            "kind": "calendar#calendarListEntry",
            "etag": "\"1692096000000\"",
            "id": "alice@company.com",
            "summary": "alice@company.com",
            "description": "Alice Johnson's primary calendar",
            "location": "New York, NY, USA",
            "timeZone": "America/New_York",
            "summaryOverride": "Alice (CEO)",
            "colorId": "1",
            "backgroundColor": "#ac725e",
            "foregroundColor": "#1d1d1d",
            "hidden": False,
            "selected": True,
            "accessRole": "owner",
            "defaultReminders": [
                {
                    "method": "email",
                    "minutes": 10
                },
                {
                    "method": "popup",
                    "minutes": 10
                }
            ],
            "notificationSettings": {
                "notifications": [
                    {
                        "type": "eventCreation",
                        "method": "email"
                    },
                    {
                        "type": "eventChange",
                        "method": "email"
                    },
                    {
                        "type": "eventCancellation",
                        "method": "email"
                    },
                    {
                        "type": "eventResponse",
                        "method": "email"
                    }
                ]
            },
            "primary": True,
            "conferenceProperties": {
                "allowedConferenceSolutionTypes": ["hangoutsMeet"]
            }
        },
        {
            "kind": "calendar#calendarListEntry",
            "etag": "\"1692096000001\"",
            "id": "bob@company.com",
            "summary": "bob@company.com",
            "description": "Bob Smith's engineering calendar",
            "location": "San Francisco, CA, USA",
            "timeZone": "America/Los_Angeles",
            "summaryOverride": "Bob (Engineering)",
            "colorId": "2",
            "backgroundColor": "#d06b64",
            "foregroundColor": "#1d1d1d",
            "hidden": False,
            "selected": True,
            "accessRole": "reader",
            "defaultReminders": [
                {
                    "method": "popup",
                    "minutes": 15
                }
            ],
            "primary": False
        },
        {
            "kind": "calendar#calendarListEntry",
            "etag": "\"1692096000002\"",
            "id": "charlie@company.com",
            "summary": "charlie@company.com",
            "description": "Charlie Brown's product calendar",
            "location": "London, UK",
            "timeZone": "Europe/London",
            "summaryOverride": "Charlie (Product)",
            "colorId": "3",
            "backgroundColor": "#fa573c",
            "foregroundColor": "#ffffff",
            "hidden": False,
            "selected": True,
            "accessRole": "reader",
            "defaultReminders": [
                {
                    "method": "email",
                    "minutes": 30
                }
            ],
            "primary": False
        },
        {
            "kind": "calendar#calendarListEntry",
            "etag": "\"1692096000003\"",
            "id": "company-events@company.com",
            "summary": "Company Events",
            "description": "Company-wide events and announcements",
            "timeZone": "America/New_York",
            "colorId": "4",
            "backgroundColor": "#ff7537",
            "foregroundColor": "#1d1d1d",
            "hidden": False,
            "selected": True,
            "accessRole": "reader",
            "defaultReminders": [
                {
                    "method": "popup",
                    "minutes": 60
                }
            ],
            "primary": False
        },
        {
            "kind": "calendar#calendarListEntry",
            "etag": "\"1692096000004\"",
            "id": "diana.contractor@company.com",
            "summary": "diana.contractor@company.com",
            "description": "Diana Wilson's contractor calendar",
            "location": "Chicago, IL, USA",
            "timeZone": "America/Chicago",
            "summaryOverride": "Diana (Contractor)",
            "colorId": "5",
            "backgroundColor": "#42d692",
            "foregroundColor": "#1d1d1d",
            "hidden": False,
            "selected": True,
            "accessRole": "freeBusyReader",
            "defaultReminders": [],
            "primary": False
        }
    ]

def get_mock_events() -> List[Dict[str, Any]]:
    """
    Mock Google Calendar events with comprehensive coverage:
    - Different timezones and all-day events
    - Recurring events with exceptions
    - Multiple attendees with RSVP status
    - Modified and cancelled events
    - Various event types and states
    """
    
    # Helper to create datetime strings in different timezones
    def dt_to_str(dt, tz_str=None):
        if tz_str:
            tz = pytz.timezone(tz_str)
            dt = dt.astimezone(tz)
        return dt.isoformat()
    
    def date_to_str(dt):
        return dt.strftime("%Y-%m-%d")
    
    base_dt_ny = BASE_DT.astimezone(pytz.timezone('America/New_York'))
    base_dt_sf = BASE_DT.astimezone(pytz.timezone('America/Los_Angeles'))
    base_dt_london = BASE_DT.astimezone(pytz.timezone('Europe/London'))
    
    return [
        # Regular meeting with multiple attendees across timezones
        {
            "kind": "calendar#event",
            "etag": "\"3392096000000\"",
            "id": "event_001_weekly_standup",
            "status": "confirmed",
            "htmlLink": "https://calendar.google.com/event?eid=event_001_weekly_standup",
            "created": dt_to_str(BASE_DT - timedelta(days=7)),
            "updated": dt_to_str(BASE_DT - timedelta(hours=1)),
            "summary": "Weekly Engineering Standup",
            "description": "Weekly standup meeting for the engineering team.\n\nAgenda:\n- Sprint progress\n- Blockers and issues\n- Planning for next week\n\nZoom: https://company.zoom.us/j/123456789",
            "location": "Zoom Meeting",
            "creator": {
                "email": "alice@company.com",
                "displayName": "Alice Johnson",
                "self": True
            },
            "organizer": {
                "email": "alice@company.com",
                "displayName": "Alice Johnson",
                "self": True
            },
            "start": {
                "dateTime": dt_to_str(base_dt_ny, "America/New_York"),
                "timeZone": "America/New_York"
            },
            "end": {
                "dateTime": dt_to_str(base_dt_ny + timedelta(minutes=30), "America/New_York"),
                "timeZone": "America/New_York"
            },
            "endTimeUnspecified": False,
            "recurrence": [
                "RRULE:FREQ=WEEKLY;BYDAY=TU"
            ],
            "recurringEventId": "event_001_weekly_standup",
            "originalStartTime": {
                "dateTime": dt_to_str(base_dt_ny, "America/New_York"),
                "timeZone": "America/New_York"
            },
            "transparency": "opaque",
            "visibility": "default",
            "iCalUID": "event_001_weekly_standup@google.com",
            "sequence": 2,
            "attendees": [
                {
                    "email": "alice@company.com",
                    "displayName": "Alice Johnson",
                    "organizer": True,
                    "self": True,
                    "responseStatus": "accepted"
                },
                {
                    "email": "bob@company.com",
                    "displayName": "Bob Smith",
                    "responseStatus": "accepted",
                    "comment": "Looking forward to it!"
                },
                {
                    "email": "charlie@company.com",
                    "displayName": "Charlie Brown",
                    "responseStatus": "tentative",
                    "comment": "May be 5 mins late"
                },
                {
                    "email": "diana.contractor@company.com",
                    "displayName": "Diana Wilson",
                    "responseStatus": "accepted",
                    "optional": True
                }
            ],
            "guestsCanInviteOthers": False,
            "guestsCanModify": False,
            "guestsCanSeeOtherGuests": True,
            "privateCopy": False,
            "locked": False,
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {
                        "method": "email",
                        "minutes": 15
                    },
                    {
                        "method": "popup",
                        "minutes": 10
                    }
                ]
            },
            "eventType": "default",
            "conferenceData": {
                "entryPoints": [
                    {
                        "entryPointType": "video",
                        "uri": "https://company.zoom.us/j/123456789",
                        "label": "company.zoom.us/j/123456789",
                        "pin": "654321"
                    },
                    {
                        "entryPointType": "phone",
                        "uri": "tel:+1-669-900-6833,,123456789#,,654321#",
                        "label": "+1 669 900 6833",
                        "pin": "654321"
                    }
                ],
                "conferenceSolution": {
                    "key": {
                        "type": "addOn"
                    },
                    "name": "Zoom Meeting",
                    "iconUri": "https://fonts.gstatic.com/s/i/productlogos/meet_2020q4/v6/web-512dp/logo_meet_2020q4_color_2x_web_512dp.png"
                },
                "conferenceId": "123456789",
                "signature": "ADiJVJP9Df8Sn2Kq"
            }
        },
        
        # All-day event across multiple timezones
        {
            "kind": "calendar#event",
            "etag": "\"3392096000001\"",
            "id": "event_002_company_retreat",
            "status": "confirmed",
            "htmlLink": "https://calendar.google.com/event?eid=event_002_company_retreat",
            "created": dt_to_str(BASE_DT - timedelta(days=30)),
            "updated": dt_to_str(BASE_DT - timedelta(days=5)),
            "summary": "Annual Company Retreat",
            "description": "Annual company retreat in Napa Valley.\n\nSchedule:\n- Team building activities\n- Strategic planning sessions\n- Networking dinner\n\nLocation: Auberge du Soleil\nAddress: 180 Rutherford Hill Rd, Rutherford, CA 94573",
            "location": "Auberge du Soleil, Rutherford, CA",
            "creator": {
                "email": "alice@company.com",
                "displayName": "Alice Johnson"
            },
            "organizer": {
                "email": "company-events@company.com",
                "displayName": "Company Events"
            },
            "start": {
                "date": date_to_str(BASE_DT.date() + timedelta(days=30))
            },
            "end": {
                "date": date_to_str(BASE_DT.date() + timedelta(days=32))
            },
            "endTimeUnspecified": False,
            "transparency": "opaque",
            "visibility": "default",
            "iCalUID": "event_002_company_retreat@google.com",
            "sequence": 1,
            "attendees": [
                {
                    "email": "alice@company.com",
                    "displayName": "Alice Johnson",
                    "responseStatus": "accepted"
                },
                {
                    "email": "bob@company.com",
                    "displayName": "Bob Smith",
                    "responseStatus": "accepted"
                },
                {
                    "email": "charlie@company.com",
                    "displayName": "Charlie Brown",
                    "responseStatus": "accepted"
                },
                {
                    "email": "diana.contractor@company.com",
                    "displayName": "Diana Wilson",
                    "responseStatus": "declined",
                    "comment": "Contractor - not included in company events"
                }
            ],
            "guestsCanInviteOthers": False,
            "guestsCanModify": False,
            "guestsCanSeeOtherGuests": True,
            "privateCopy": False,
            "locked": False,
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {
                        "method": "email",
                        "minutes": 1440  # 24 hours
                    }
                ]
            },
            "eventType": "default"
        },
        
        # Recurring event with exception (modified instance)
        {
            "kind": "calendar#event",
            "etag": "\"3392096000002\"",
            "id": "event_003_daily_standup_exception",
            "status": "confirmed",
            "htmlLink": "https://calendar.google.com/event?eid=event_003_daily_standup_exception",
            "created": dt_to_str(BASE_DT - timedelta(days=14)),
            "updated": dt_to_str(BASE_DT - timedelta(hours=3)),
            "summary": "Daily Standup - EXTENDED SESSION",
            "description": "Extended daily standup with sprint planning.\n\nExtra agenda items:\n- Sprint retrospective\n- Next sprint planning\n- Technical debt discussion",
            "location": "Conference Room A (instead of usual Zoom)",
            "creator": {
                "email": "bob@company.com",
                "displayName": "Bob Smith"
            },
            "organizer": {
                "email": "bob@company.com",
                "displayName": "Bob Smith"
            },
            "start": {
                "dateTime": dt_to_str(base_dt_sf + timedelta(hours=1), "America/Los_Angeles"),
                "timeZone": "America/Los_Angeles"
            },
            "end": {
                "dateTime": dt_to_str(base_dt_sf + timedelta(hours=1, minutes=60), "America/Los_Angeles"),
                "timeZone": "America/Los_Angeles"
            },
            "endTimeUnspecified": False,
            "recurringEventId": "event_003_daily_standup_recurring",
            "originalStartTime": {
                "dateTime": dt_to_str(base_dt_sf + timedelta(hours=1), "America/Los_Angeles"),
                "timeZone": "America/Los_Angeles"
            },
            "transparency": "opaque",
            "visibility": "default",
            "iCalUID": "event_003_daily_standup_recurring@google.com",
            "sequence": 3,
            "attendees": [
                {
                    "email": "bob@company.com",
                    "displayName": "Bob Smith",
                    "organizer": True,
                    "responseStatus": "accepted"
                },
                {
                    "email": "alice@company.com",
                    "displayName": "Alice Johnson",
                    "responseStatus": "accepted"
                },
                {
                    "email": "diana.contractor@company.com",
                    "displayName": "Diana Wilson",
                    "responseStatus": "tentative",
                    "comment": "Will join if available"
                }
            ],
            "guestsCanInviteOthers": True,
            "guestsCanModify": True,
            "guestsCanSeeOtherGuests": True,
            "privateCopy": False,
            "locked": False,
            "reminders": {
                "useDefault": True
            },
            "eventType": "default"
        },
        
        # Cancelled event
        {
            "kind": "calendar#event",
            "etag": "\"3392096000003\"",
            "id": "event_004_cancelled_meeting",
            "status": "cancelled",
            "htmlLink": "https://calendar.google.com/event?eid=event_004_cancelled_meeting",
            "created": dt_to_str(BASE_DT - timedelta(days=3)),
            "updated": dt_to_str(BASE_DT - timedelta(hours=2)),
            "summary": "Product Strategy Review - CANCELLED",
            "description": "CANCELLED: Product strategy review meeting.\n\nReason: Key stakeholder unavailable.\nRescheduling for next week.",
            "location": "Conference Room B",
            "creator": {
                "email": "charlie@company.com",
                "displayName": "Charlie Brown"
            },
            "organizer": {
                "email": "charlie@company.com",
                "displayName": "Charlie Brown"
            },
            "start": {
                "dateTime": dt_to_str(base_dt_london - timedelta(hours=2), "Europe/London"),
                "timeZone": "Europe/London"
            },
            "end": {
                "dateTime": dt_to_str(base_dt_london - timedelta(hours=1), "Europe/London"),
                "timeZone": "Europe/London"
            },
            "endTimeUnspecified": False,
            "transparency": "transparent",
            "visibility": "default",
            "iCalUID": "event_004_cancelled_meeting@google.com",
            "sequence": 2,
            "attendees": [
                {
                    "email": "charlie@company.com",
                    "displayName": "Charlie Brown",
                    "organizer": True,
                    "responseStatus": "accepted"
                },
                {
                    "email": "alice@company.com",
                    "displayName": "Alice Johnson",
                    "responseStatus": "accepted"
                },
                {
                    "email": "bob@company.com",
                    "displayName": "Bob Smith",
                    "responseStatus": "declined",
                    "comment": "Conflicts with engineering standup"
                }
            ],
            "guestsCanInviteOthers": False,
            "guestsCanModify": False,
            "guestsCanSeeOtherGuests": True,
            "privateCopy": False,
            "locked": False,
            "reminders": {
                "useDefault": True
            },
            "eventType": "default"
        },
        
        # Private event (limited visibility)
        {
            "kind": "calendar#event",
            "etag": "\"3392096000004\"",
            "id": "event_005_private_meeting",
            "status": "confirmed",
            "htmlLink": "https://calendar.google.com/event?eid=event_005_private_meeting",
            "created": dt_to_str(BASE_DT - timedelta(days=1)),
            "updated": dt_to_str(BASE_DT - timedelta(hours=1)),
            "summary": "Executive Strategy Session",
            "description": "Private executive meeting - confidential agenda",
            "location": "Executive Conference Room",
            "creator": {
                "email": "alice@company.com",
                "displayName": "Alice Johnson"
            },
            "organizer": {
                "email": "alice@company.com",
                "displayName": "Alice Johnson"
            },
            "start": {
                "dateTime": dt_to_str(base_dt_ny + timedelta(hours=4), "America/New_York"),
                "timeZone": "America/New_York"
            },
            "end": {
                "dateTime": dt_to_str(base_dt_ny + timedelta(hours=5), "America/New_York"),
                "timeZone": "America/New_York"
            },
            "endTimeUnspecified": False,
            "transparency": "opaque",
            "visibility": "private",
            "iCalUID": "event_005_private_meeting@google.com",
            "sequence": 0,
            "attendees": [
                {
                    "email": "alice@company.com",
                    "displayName": "Alice Johnson",
                    "organizer": True,
                    "self": True,
                    "responseStatus": "accepted"
                }
            ],
            "guestsCanInviteOthers": False,
            "guestsCanModify": False,
            "guestsCanSeeOtherGuests": False,
            "privateCopy": False,
            "locked": True,
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {
                        "method": "popup",
                        "minutes": 5
                    }
                ]
            },
            "eventType": "default"
        },
        
        # Working location event (special event type)
        {
            "kind": "calendar#event",
            "etag": "\"3392096000005\"",
            "id": "event_006_working_location",
            "status": "confirmed",
            "htmlLink": "https://calendar.google.com/event?eid=event_006_working_location",
            "created": dt_to_str(BASE_DT - timedelta(days=1)),
            "updated": dt_to_str(BASE_DT - timedelta(hours=1)),
            "summary": "Working from home",
            "description": "Working from home today due to maintenance in the office building.",
            "creator": {
                "email": "bob@company.com",
                "displayName": "Bob Smith"
            },
            "organizer": {
                "email": "bob@company.com",
                "displayName": "Bob Smith"
            },
            "start": {
                "date": date_to_str(BASE_DT.date())
            },
            "end": {
                "date": date_to_str(BASE_DT.date() + timedelta(days=1))
            },
            "endTimeUnspecified": False,
            "transparency": "transparent",
            "visibility": "public",
            "iCalUID": "event_006_working_location@google.com",
            "sequence": 0,
            "attendees": [
                {
                    "email": "bob@company.com",
                    "displayName": "Bob Smith",
                    "organizer": True,
                    "self": True,
                    "responseStatus": "accepted"
                }
            ],
            "guestsCanInviteOthers": False,
            "guestsCanModify": False,
            "guestsCanSeeOtherGuests": False,
            "privateCopy": False,
            "locked": False,
            "reminders": {
                "useDefault": False,
                "overrides": []
            },
            "eventType": "workingLocation",
            "workingLocationProperties": {
                "type": "homeOffice"
            }
        },
        
        # Out of office event
        {
            "kind": "calendar#event",
            "etag": "\"3392096000006\"",
            "id": "event_007_out_of_office",
            "status": "confirmed",
            "htmlLink": "https://calendar.google.com/event?eid=event_007_out_of_office",
            "created": dt_to_str(BASE_DT - timedelta(days=10)),
            "updated": dt_to_str(BASE_DT - timedelta(days=5)),
            "summary": "Charlie - Vacation",
            "description": "Charlie is on vacation in Portugal.\n\nEmergency contact: alice@company.com\nReturn date: Aug 25, 2025",
            "creator": {
                "email": "charlie@company.com",
                "displayName": "Charlie Brown"
            },
            "organizer": {
                "email": "charlie@company.com",
                "displayName": "Charlie Brown"
            },
            "start": {
                "date": date_to_str(BASE_DT.date() + timedelta(days=5))
            },
            "end": {
                "date": date_to_str(BASE_DT.date() + timedelta(days=10))
            },
            "endTimeUnspecified": False,
            "transparency": "transparent",
            "visibility": "public",
            "iCalUID": "event_007_out_of_office@google.com",
            "sequence": 1,
            "attendees": [
                {
                    "email": "charlie@company.com",
                    "displayName": "Charlie Brown",
                    "organizer": True,
                    "self": True,
                    "responseStatus": "accepted"
                }
            ],
            "guestsCanInviteOthers": False,
            "guestsCanModify": False,
            "guestsCanSeeOtherGuests": False,
            "privateCopy": False,
            "locked": False,
            "reminders": {
                "useDefault": False,
                "overrides": []
            },
            "eventType": "outOfOffice"
        },
        
        # Focus time block (no attendees)
        {
            "kind": "calendar#event",
            "etag": "\"3392096000007\"",
            "id": "event_008_focus_time",
            "status": "confirmed",
            "htmlLink": "https://calendar.google.com/event?eid=event_008_focus_time",
            "created": dt_to_str(BASE_DT - timedelta(days=1)),
            "updated": dt_to_str(BASE_DT - timedelta(hours=1)),
            "summary": "Focus Time - Deep Work",
            "description": "Blocked time for focused development work.\n\n- No interruptions\n- Phone on silent\n- Slack status: Do not disturb\n\nProject: New dashboard feature",
            "creator": {
                "email": "bob@company.com",
                "displayName": "Bob Smith"
            },
            "organizer": {
                "email": "bob@company.com",
                "displayName": "Bob Smith"
            },
            "start": {
                "dateTime": dt_to_str(base_dt_sf + timedelta(hours=2), "America/Los_Angeles"),
                "timeZone": "America/Los_Angeles"
            },
            "end": {
                "dateTime": dt_to_str(base_dt_sf + timedelta(hours=5), "America/Los_Angeles"),
                "timeZone": "America/Los_Angeles"
            },
            "endTimeUnspecified": False,
            "transparency": "opaque",
            "visibility": "private",
            "iCalUID": "event_008_focus_time@google.com",
            "sequence": 0,
            "attendees": [
                {
                    "email": "bob@company.com",
                    "displayName": "Bob Smith",
                    "organizer": True,
                    "self": True,
                    "responseStatus": "accepted"
                }
            ],
            "guestsCanInviteOthers": False,
            "guestsCanModify": False,
            "guestsCanSeeOtherGuests": False,
            "privateCopy": False,
            "locked": False,
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {
                        "method": "popup",
                        "minutes": 0
                    }
                ]
            },
            "eventType": "focusTime"
        },
        
        # External meeting with non-company attendees
        {
            "kind": "calendar#event",
            "etag": "\"3392096000008\"",
            "id": "event_009_external_meeting",
            "status": "confirmed",
            "htmlLink": "https://calendar.google.com/event?eid=event_009_external_meeting",
            "created": dt_to_str(BASE_DT - timedelta(days=5)),
            "updated": dt_to_str(BASE_DT - timedelta(hours=6)),
            "summary": "Partnership Discussion - TechCorp",
            "description": "Partnership discussion with TechCorp representatives.\n\nAgenda:\n- Technology integration opportunities\n- Revenue sharing models\n- Timeline and milestones\n\nNDA: Required for all attendees",
            "location": "Google Meet",
            "creator": {
                "email": "alice@company.com",
                "displayName": "Alice Johnson"
            },
            "organizer": {
                "email": "alice@company.com",
                "displayName": "Alice Johnson"
            },
            "start": {
                "dateTime": dt_to_str(base_dt_ny + timedelta(hours=6), "America/New_York"),
                "timeZone": "America/New_York"
            },
            "end": {
                "dateTime": dt_to_str(base_dt_ny + timedelta(hours=7), "America/New_York"),
                "timeZone": "America/New_York"
            },
            "endTimeUnspecified": False,
            "transparency": "opaque",
            "visibility": "default",
            "iCalUID": "event_009_external_meeting@google.com",
            "sequence": 1,
            "attendees": [
                {
                    "email": "alice@company.com",
                    "displayName": "Alice Johnson",
                    "organizer": True,
                    "self": True,
                    "responseStatus": "accepted"
                },
                {
                    "email": "charlie@company.com",
                    "displayName": "Charlie Brown",
                    "responseStatus": "accepted"
                },
                {
                    "email": "john.doe@techcorp.com",
                    "displayName": "John Doe",
                    "responseStatus": "accepted",
                    "comment": "Looking forward to the discussion"
                },
                {
                    "email": "jane.smith@techcorp.com",
                    "displayName": "Jane Smith",
                    "responseStatus": "tentative"
                }
            ],
            "guestsCanInviteOthers": False,
            "guestsCanModify": False,
            "guestsCanSeeOtherGuests": True,
            "privateCopy": False,
            "locked": False,
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {
                        "method": "email",
                        "minutes": 60
                    },
                    {
                        "method": "popup",
                        "minutes": 15
                    }
                ]
            },
            "eventType": "default",
            "conferenceData": {
                "entryPoints": [
                    {
                        "entryPointType": "video",
                        "uri": "https://meet.google.com/abc-defg-hij",
                        "label": "meet.google.com/abc-defg-hij"
                    }
                ],
                "conferenceSolution": {
                    "key": {
                        "type": "hangoutsMeet"
                    },
                    "name": "Google Meet",
                    "iconUri": "https://fonts.gstatic.com/s/i/productlogos/meet_2020q4/v6/web-512dp/logo_meet_2020q4_color_2x_web_512dp.png"
                },
                "conferenceId": "abc-defg-hij",
                "signature": "ADiJVJP9Df8Sn2Kq"
            }
        },
        
        # Tentative event that became confirmed
        {
            "kind": "calendar#event",
            "etag": "\"3392096000009\"",
            "id": "event_010_confirmed_later",
            "status": "confirmed",
            "htmlLink": "https://calendar.google.com/event?eid=event_010_confirmed_later",
            "created": dt_to_str(BASE_DT - timedelta(days=7)),
            "updated": dt_to_str(BASE_DT - timedelta(hours=12)),
            "summary": "Q3 Planning Session",
            "description": "Q3 planning session - confirmed as of this morning.\n\nUpdated agenda:\n- Revenue goals review\n- Resource allocation\n- Key initiatives prioritization\n- Risk assessment",
            "location": "Boardroom",
            "creator": {
                "email": "alice@company.com",
                "displayName": "Alice Johnson"
            },
            "organizer": {
                "email": "alice@company.com",
                "displayName": "Alice Johnson"
            },
            "start": {
                "dateTime": dt_to_str(base_dt_ny + timedelta(days=1, hours=2), "America/New_York"),
                "timeZone": "America/New_York"
            },
            "end": {
                "dateTime": dt_to_str(base_dt_ny + timedelta(days=1, hours=4), "America/New_York"),
                "timeZone": "America/New_York"
            },
            "endTimeUnspecified": False,
            "transparency": "opaque",
            "visibility": "default",
            "iCalUID": "event_010_confirmed_later@google.com",
            "sequence": 3,
            "attendees": [
                {
                    "email": "alice@company.com",
                    "displayName": "Alice Johnson",
                    "organizer": True,
                    "self": True,
                    "responseStatus": "accepted"
                },
                {
                    "email": "charlie@company.com",
                    "displayName": "Charlie Brown",
                    "responseStatus": "accepted",
                    "comment": "Great that we got this confirmed"
                },
                {
                    "email": "bob@company.com",
                    "displayName": "Bob Smith",
                    "responseStatus": "needsAction",
                    "optional": True
                }
            ],
            "guestsCanInviteOthers": False,
            "guestsCanModify": False,
            "guestsCanSeeOtherGuests": True,
            "privateCopy": False,
            "locked": False,
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {
                        "method": "email",
                        "minutes": 30
                    }
                ]
            },
            "eventType": "default"
        }
    ]

def get_mock_event_changes() -> List[Dict[str, Any]]:
    """Mock event changes for testing change detection."""
    return [
        {
            "kind": "calendar#event",
            "eventId": "event_001_weekly_standup",
            "eventType": "modified",
            "changeType": "time_changed",
            "oldValue": {
                "start": {
                    "dateTime": dt_to_str(BASE_DT - timedelta(minutes=30), "America/New_York"),
                    "timeZone": "America/New_York"
                }
            },
            "newValue": {
                "start": {
                    "dateTime": dt_to_str(BASE_DT, "America/New_York"),
                    "timeZone": "America/New_York"
                }
            },
            "changedBy": "alice@company.com",
            "changeTime": dt_to_str(BASE_DT - timedelta(hours=1))
        },
        {
            "kind": "calendar#event",
            "eventId": "event_004_cancelled_meeting",
            "eventType": "cancelled",
            "changeType": "status_changed",
            "oldValue": {
                "status": "confirmed"
            },
            "newValue": {
                "status": "cancelled"
            },
            "changedBy": "charlie@company.com",
            "changeTime": dt_to_str(BASE_DT - timedelta(hours=2))
        },
        {
            "kind": "calendar#event",
            "eventId": "event_009_external_meeting",
            "eventType": "modified",
            "changeType": "attendee_added",
            "oldValue": {
                "attendees_count": 3
            },
            "newValue": {
                "attendees_count": 4,
                "added_attendee": {
                    "email": "jane.smith@techcorp.com",
                    "displayName": "Jane Smith"
                }
            },
            "changedBy": "alice@company.com",
            "changeTime": dt_to_str(BASE_DT - timedelta(hours=6))
        }
    ]

def get_mock_api_errors() -> Dict[str, Any]:
    """Mock Calendar API errors for testing error handling."""
    return {
        "unauthorized": {
            "error": {
                "code": 401,
                "message": "Request had invalid authentication credentials.",
                "status": "UNAUTHENTICATED"
            }
        },
        "forbidden": {
            "error": {
                "code": 403,
                "message": "The request is missing a valid API key.",
                "status": "PERMISSION_DENIED"
            }
        },
        "not_found": {
            "error": {
                "code": 404,
                "message": "Calendar not found",
                "status": "NOT_FOUND"
            }
        },
        "rate_limited": {
            "error": {
                "code": 429,
                "message": "Rate limit exceeded",
                "status": "RESOURCE_EXHAUSTED"
            }
        },
        "internal_error": {
            "error": {
                "code": 500,
                "message": "Internal server error",
                "status": "INTERNAL"
            }
        }
    }

def get_mock_timezone_data() -> Dict[str, Any]:
    """Mock timezone information for testing timezone handling."""
    return {
        "timezones": [
            {
                "id": "America/New_York",
                "displayName": "Eastern Standard Time",
                "rawOffset": -18000000,  # -5 hours in milliseconds
                "dstOffset": 3600000,    # +1 hour in milliseconds
                "timeZoneName": "EST"
            },
            {
                "id": "America/Los_Angeles",
                "displayName": "Pacific Standard Time",
                "rawOffset": -28800000,  # -8 hours in milliseconds
                "dstOffset": 3600000,    # +1 hour in milliseconds
                "timeZoneName": "PST"
            },
            {
                "id": "Europe/London",
                "displayName": "Greenwich Mean Time",
                "rawOffset": 0,          # +0 hours in milliseconds
                "dstOffset": 3600000,    # +1 hour in milliseconds
                "timeZoneName": "GMT"
            },
            {
                "id": "America/Chicago",
                "displayName": "Central Standard Time",
                "rawOffset": -21600000,  # -6 hours in milliseconds
                "dstOffset": 3600000,    # +1 hour in milliseconds
                "timeZoneName": "CST"
            }
        ]
    }

# Helper functions
def validate_mock_calendar_data():
    """Validate that all mock calendar data is well-formed."""
    try:
        calendars = get_mock_calendars()
        events = get_mock_events()
        changes = get_mock_event_changes()
        
        # Validate JSON serializability
        json.dumps(calendars)
        json.dumps(events)
        json.dumps(changes)
        
        # Basic consistency checks
        calendar_ids = {c["id"] for c in calendars}
        
        for event in events:
            # Ensure required fields exist
            assert "id" in event
            assert "summary" in event
            assert "start" in event
            assert "end" in event
            assert "status" in event
            
            # Check attendees reference valid calendars where possible
            if "attendees" in event:
                for attendee in event["attendees"]:
                    assert "email" in attendee
                    assert "responseStatus" in attendee
        
        return True
    except Exception as e:
        print(f"Calendar mock data validation failed: {e}")
        return False

def get_mock_collection_result() -> Dict[str, Any]:
    """Mock result from calendar collector matching expected format."""
    events = get_mock_events()
    calendars = get_mock_calendars()
    
    return {
        "discovered": {
            "calendars": len(calendars),
            "events": len(events),
            "timezones": 4
        },
        "collected": {
            "events": len([e for e in events if e["status"] != "cancelled"]),
            "cancelled_events": len([e for e in events if e["status"] == "cancelled"]),
            "recurring_events": len([e for e in events if "recurrence" in e]),
            "all_day_events": len([e for e in events if "date" in e.get("start", {})]),
            "attendees": sum(len(e.get("attendees", [])) for e in events)
        },
        "calendars": calendars,
        "events": events,
        "changes": get_mock_event_changes(),
        "metadata": {
            "collection_time": dt_to_str(BASE_DT),
            "timezone_info": get_mock_timezone_data()
        }
    }

def dt_to_str(dt, tz_str=None):
    """Helper function to convert datetime to string with optional timezone."""
    if tz_str:
        tz = pytz.timezone(tz_str)
        dt = dt.astimezone(tz)
    return dt.isoformat()

# Alias functions for test compatibility  
def get_mock_calendar_events():
    """Alias for get_mock_events() for test compatibility"""
    return get_mock_events()

# Ensure data is valid on import
if __name__ == "__main__":
    assert validate_mock_calendar_data(), "Calendar mock data validation failed"
    print("All Calendar mock data validated successfully!")