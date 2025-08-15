"""
Comprehensive mock Slack data for testing collector wrappers.
Covers all edge cases: threads, reactions, bots, deleted messages, etc.
Data is deterministic - same function calls return identical results.
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Any

# Base timestamp for deterministic data
BASE_TS = datetime(2025, 8, 15, 9, 0, 0)

def get_mock_channels() -> List[Dict[str, Any]]:
    """Mock Slack channels with varied attributes covering edge cases."""
    return [
        {
            "id": "C1234567890",
            "name": "general",
            "is_channel": True,
            "is_group": False,
            "is_im": False,
            "is_mpim": False,
            "is_private": False,
            "created": int((BASE_TS - timedelta(days=365)).timestamp()),
            "is_archived": False,
            "is_general": True,
            "unlinked": 0,
            "name_normalized": "general",
            "is_shared": False,
            "is_org_shared": False,
            "is_member": True,
            "is_private": False,
            "is_mpim": False,
            "members": ["U1111111111", "U2222222222", "U3333333333", "USLACKBOT"],
            "topic": {
                "value": "Company-wide announcements and general discussion",
                "creator": "U1111111111",
                "last_set": int((BASE_TS - timedelta(days=30)).timestamp())
            },
            "purpose": {
                "value": "This channel is for workspace-wide communication and announcements.",
                "creator": "U1111111111", 
                "last_set": int((BASE_TS - timedelta(days=365)).timestamp())
            },
            "num_members": 4
        },
        {
            "id": "C2345678901",
            "name": "engineering",
            "is_channel": True,
            "is_group": False,
            "is_im": False,
            "is_mpim": False,
            "is_private": True,
            "created": int((BASE_TS - timedelta(days=200)).timestamp()),
            "is_archived": False,
            "is_general": False,
            "unlinked": 0,
            "name_normalized": "engineering",
            "is_shared": False,
            "is_org_shared": False,
            "is_member": True,
            "is_private": True,
            "is_mpim": False,
            "members": ["U1111111111", "U2222222222", "U4444444444"],
            "topic": {
                "value": "Engineering discussions and technical updates",
                "creator": "U2222222222",
                "last_set": int((BASE_TS - timedelta(days=7)).timestamp())
            },
            "purpose": {
                "value": "Private channel for engineering team coordination",
                "creator": "U1111111111",
                "last_set": int((BASE_TS - timedelta(days=200)).timestamp())
            },
            "num_members": 3
        },
        {
            "id": "C3456789012", 
            "name": "archived-old-project",
            "is_channel": True,
            "is_group": False,
            "is_im": False,
            "is_mpim": False,
            "is_private": False,
            "created": int((BASE_TS - timedelta(days=500)).timestamp()),
            "is_archived": True,
            "is_general": False,
            "unlinked": 0,
            "name_normalized": "archived-old-project",
            "is_shared": False,
            "is_org_shared": False,
            "is_member": False,
            "is_private": False,
            "is_mpim": False,
            "members": [],
            "topic": {
                "value": "",
                "creator": "",
                "last_set": 0
            },
            "purpose": {
                "value": "Old project channel - now archived",
                "creator": "U1111111111",
                "last_set": int((BASE_TS - timedelta(days=500)).timestamp())
            },
            "num_members": 0
        },
        {
            "id": "D1111111111",
            "name": "",
            "is_channel": False,
            "is_group": False,
            "is_im": True,
            "is_mpim": False,
            "is_private": True,
            "created": int((BASE_TS - timedelta(days=100)).timestamp()),
            "is_archived": False,
            "is_general": False,
            "unlinked": 0,
            "name_normalized": "",
            "is_shared": False,
            "is_org_shared": False,
            "is_member": True,
            "is_private": True,
            "is_mpim": False,
            "user": "U2222222222",
            "num_members": 2
        },
        {
            "id": "G4567890123",
            "name": "leadership-private", 
            "is_channel": False,
            "is_group": True,
            "is_im": False,
            "is_mpim": False,
            "is_private": True,
            "created": int((BASE_TS - timedelta(days=90)).timestamp()),
            "is_archived": False,
            "is_general": False,
            "unlinked": 0,
            "name_normalized": "leadership-private",
            "is_shared": False,
            "is_org_shared": False,
            "is_member": True,
            "is_private": True,
            "is_mpim": False,
            "members": ["U1111111111", "U3333333333"],
            "topic": {
                "value": "Leadership team private discussions",
                "creator": "U1111111111",
                "last_set": int((BASE_TS - timedelta(days=30)).timestamp())
            },
            "purpose": {
                "value": "Private group for leadership coordination",
                "creator": "U1111111111",
                "last_set": int((BASE_TS - timedelta(days=90)).timestamp())
            },
            "num_members": 2
        }
    ]

def get_mock_users() -> List[Dict[str, Any]]:
    """Mock Slack users including regular users, bots, and edge cases."""
    return [
        {
            "id": "U1111111111",
            "team_id": "T1234567890",
            "name": "alice.ceo",
            "deleted": False,
            "color": "9f69e7",
            "real_name": "Alice Johnson",
            "tz": "America/New_York",
            "tz_label": "Eastern Standard Time",
            "tz_offset": -18000,
            "profile": {
                "title": "Chief Executive Officer",
                "phone": "+1-555-0101",
                "skype": "",
                "real_name": "Alice Johnson",
                "real_name_normalized": "Alice Johnson",
                "display_name": "Alice (CEO)",
                "display_name_normalized": "Alice (CEO)",
                "fields": {
                    "Xf1234567890": {
                        "value": "Engineering",
                        "alt": "Department"
                    }
                },
                "status_text": "In meetings",
                "status_emoji": ":calendar:",
                "status_emoji_display_info": [],
                "status_expiration": int((BASE_TS + timedelta(hours=4)).timestamp()),
                "avatar_hash": "g1234567890",
                "email": "alice@company.com",
                "first_name": "Alice",
                "last_name": "Johnson",
                "image_24": "https://secure.gravatar.com/avatar/1234.jpg?s=24&d=https%3A%2F%2Fa.slack-edge.com%2Fdf10d%2Fimg%2Favatars%2Fava_0001-24.png",
                "image_32": "https://secure.gravatar.com/avatar/1234.jpg?s=32&d=https%3A%2F%2Fa.slack-edge.com%2Fdf10d%2Fimg%2Favatars%2Fava_0001-32.png",
                "image_48": "https://secure.gravatar.com/avatar/1234.jpg?s=48&d=https%3A%2F%2Fa.slack-edge.com%2Fdf10d%2Fimg%2Favatars%2Fava_0001-48.png",
                "image_72": "https://secure.gravatar.com/avatar/1234.jpg?s=72&d=https%3A%2F%2Fa.slack-edge.com%2Fdf10d%2Fimg%2Favatars%2Fava_0001-72.png",
                "image_192": "https://secure.gravatar.com/avatar/1234.jpg?s=192&d=https%3A%2F%2Fa.slack-edge.com%2Fdf10d%2Fimg%2Favatars%2Fava_0001-192.png",
                "image_512": "https://secure.gravatar.com/avatar/1234.jpg?s=512&d=https%3A%2F%2Fa.slack-edge.com%2Fdf10d%2Fimg%2Favatars%2Fava_0001-512.png"
            },
            "is_admin": True,
            "is_owner": True,
            "is_primary_owner": True,
            "is_restricted": False,
            "is_ultra_restricted": False,
            "is_bot": False,
            "is_app_user": False,
            "updated": int((BASE_TS - timedelta(days=1)).timestamp()),
            "is_email_confirmed": True,
            "who_can_share_contact_card": "EVERYONE"
        },
        {
            "id": "U2222222222", 
            "team_id": "T1234567890",
            "name": "bob.engineer",
            "deleted": False,
            "color": "e7392d",
            "real_name": "Bob Smith",
            "tz": "America/Los_Angeles",
            "tz_label": "Pacific Standard Time", 
            "tz_offset": -28800,
            "profile": {
                "title": "Senior Software Engineer",
                "phone": "+1-555-0102",
                "skype": "",
                "real_name": "Bob Smith",
                "real_name_normalized": "Bob Smith",
                "display_name": "Bob",
                "display_name_normalized": "Bob",
                "fields": {
                    "Xf1234567890": {
                        "value": "Engineering",
                        "alt": "Department"
                    }
                },
                "status_text": "Coding",
                "status_emoji": ":computer:",
                "status_emoji_display_info": [],
                "status_expiration": 0,
                "avatar_hash": "g2345678901",
                "email": "bob@company.com",
                "first_name": "Bob",
                "last_name": "Smith",
                "image_24": "https://secure.gravatar.com/avatar/2345.jpg?s=24&d=https%3A%2F%2Fa.slack-edge.com%2Fdf10d%2Fimg%2Favatars%2Fava_0002-24.png",
                "image_32": "https://secure.gravatar.com/avatar/2345.jpg?s=32&d=https%3A%2F%2Fa.slack-edge.com%2Fdf10d%2Fimg%2Favatars%2Fava_0002-32.png",
                "image_48": "https://secure.gravatar.com/avatar/2345.jpg?s=48&d=https%3A%2F%2Fa.slack-edge.com%2Fdf10d%2Fimg%2Favatars%2Fava_0002-48.png",
                "image_72": "https://secure.gravatar.com/avatar/2345.jpg?s=72&d=https%3A%2F%2Fa.slack-edge.com%2Fdf10d%2Fimg%2Favatars%2Fava_0002-72.png",
                "image_192": "https://secure.gravatar.com/avatar/2345.jpg?s=192&d=https%3A%2F%2Fa.slack-edge.com%2Fdf10d%2Fimg%2Favatars%2Fava_0002-192.png",
                "image_512": "https://secure.gravatar.com/avatar/2345.jpg?s=512&d=https%3A%2F%2Fa.slack-edge.com%2Fdf10d%2Fimg%2Favatars%2Fava_0002-512.png"
            },
            "is_admin": False,
            "is_owner": False,
            "is_primary_owner": False,
            "is_restricted": False,
            "is_ultra_restricted": False,
            "is_bot": False,
            "is_app_user": False,
            "updated": int((BASE_TS - timedelta(hours=2)).timestamp()),
            "is_email_confirmed": True,
            "who_can_share_contact_card": "EVERYONE"
        },
        {
            "id": "U3333333333",
            "team_id": "T1234567890", 
            "name": "charlie.product",
            "deleted": False,
            "color": "674b1b",
            "real_name": "Charlie Brown",
            "tz": "Europe/London",
            "tz_label": "Greenwich Mean Time",
            "tz_offset": 0,
            "profile": {
                "title": "Product Manager",
                "phone": "+44-20-7946-0958",
                "skype": "",
                "real_name": "Charlie Brown",
                "real_name_normalized": "Charlie Brown",
                "display_name": "Charlie",
                "display_name_normalized": "Charlie",
                "fields": {
                    "Xf1234567890": {
                        "value": "Product",
                        "alt": "Department"
                    }
                },
                "status_text": "",
                "status_emoji": "",
                "status_emoji_display_info": [],
                "status_expiration": 0,
                "avatar_hash": "g3456789012",
                "email": "charlie@company.com",
                "first_name": "Charlie",
                "last_name": "Brown",
                "image_24": "https://secure.gravatar.com/avatar/3456.jpg?s=24&d=https%3A%2F%2Fa.slack-edge.com%2Fdf10d%2Fimg%2Favatars%2Fava_0003-24.png",
                "image_32": "https://secure.gravatar.com/avatar/3456.jpg?s=32&d=https%3A%2F%2Fa.slack-edge.com%2Fdf10d%2Fimg%2Favatars%2Fava_0003-32.png",
                "image_48": "https://secure.gravatar.com/avatar/3456.jpg?s=48&d=https%3A%2F%2Fa.slack-edge.com%2Fdf10d%2Fimg%2Favatars%2Fava_0003-48.png",
                "image_72": "https://secure.gravatar.com/avatar/3456.jpg?s=72&d=https%3A%2F%2Fa.slack-edge.com%2Fdf10d%2Fimg%2Favatars%2Fava_0003-72.png",
                "image_192": "https://secure.gravatar.com/avatar/3456.jpg?s=192&d=https%3A%2F%2Fa.slack-edge.com%2Fdf10d%2Fimg%2Favatars%2Fava_0003-192.png",
                "image_512": "https://secure.gravatar.com/avatar/3456.jpg?s=512&d=https%3A%2F%2Fa.slack-edge.com%2Fdf10d%2Fimg%2Favatars%2Fava_0003-512.png"
            },
            "is_admin": False,
            "is_owner": False,
            "is_primary_owner": False,
            "is_restricted": False,
            "is_ultra_restricted": False,
            "is_bot": False,
            "is_app_user": False,
            "updated": int((BASE_TS - timedelta(hours=8)).timestamp()),
            "is_email_confirmed": True,
            "who_can_share_contact_card": "EVERYONE"
        },
        {
            "id": "U4444444444",
            "team_id": "T1234567890",
            "name": "diana.contractor", 
            "deleted": False,
            "color": "4bbe2e",
            "real_name": "Diana Wilson",
            "tz": "America/Chicago",
            "tz_label": "Central Standard Time",
            "tz_offset": -21600,
            "profile": {
                "title": "Contractor - DevOps",
                "phone": "",
                "skype": "",
                "real_name": "Diana Wilson",
                "real_name_normalized": "Diana Wilson",
                "display_name": "Diana (Contractor)",
                "display_name_normalized": "Diana (Contractor)",
                "fields": {
                    "Xf1234567890": {
                        "value": "Engineering",
                        "alt": "Department"
                    }
                },
                "status_text": "Working remotely",
                "status_emoji": ":house_with_garden:",
                "status_emoji_display_info": [],
                "status_expiration": 0,
                "avatar_hash": "g4567890123",
                "email": "diana.contractor@company.com",
                "first_name": "Diana",
                "last_name": "Wilson",
                "image_24": "https://secure.gravatar.com/avatar/4567.jpg?s=24&d=https%3A%2F%2Fa.slack-edge.com%2Fdf10d%2Fimg%2Favatars%2Fava_0004-24.png",
                "image_32": "https://secure.gravatar.com/avatar/4567.jpg?s=32&d=https%3A%2F%2Fa.slack-edge.com%2Fdf10d%2Fimg%2Favatars%2Fava_0004-32.png",
                "image_48": "https://secure.gravatar.com/avatar/4567.jpg?s=48&d=https%3A%2F%2Fa.slack-edge.com%2Fdf10d%2Fimg%2Favatars%2Fava_0004-48.png",
                "image_72": "https://secure.gravatar.com/avatar/4567.jpg?s=72&d=https%3A%2F%2Fa.slack-edge.com%2Fdf10d%2Fimg%2Favatars%2Fava_0004-72.png",
                "image_192": "https://secure.gravatar.com/avatar/4567.jpg?s=192&d=https%3A%2F%2Fa.slack-edge.com%2Fdf10d%2Fimg%2Favatars%2Fava_0004-192.png",
                "image_512": "https://secure.gravatar.com/avatar/4567.jpg?s=512&d=https%3A%2F%2Fa.slack-edge.com%2Fdf10d%2Fimg%2Favatars%2Fava_0004-512.png"
            },
            "is_admin": False,
            "is_owner": False,
            "is_primary_owner": False,
            "is_restricted": True,
            "is_ultra_restricted": False,
            "is_bot": False,
            "is_app_user": False,
            "updated": int((BASE_TS - timedelta(days=3)).timestamp()),
            "is_email_confirmed": True,
            "who_can_share_contact_card": "EVERYONE"
        },
        {
            "id": "USLACKBOT",
            "team_id": "T1234567890",
            "name": "slackbot",
            "deleted": False,
            "color": "757575",
            "real_name": "Slackbot",
            "tz": "",
            "tz_label": "",
            "tz_offset": 0,
            "profile": {
                "title": "",
                "phone": "",
                "skype": "",
                "real_name": "Slackbot",
                "real_name_normalized": "Slackbot",
                "display_name": "Slackbot",
                "display_name_normalized": "Slackbot",
                "fields": {},
                "status_text": "",
                "status_emoji": "",
                "status_emoji_display_info": [],
                "status_expiration": 0,
                "avatar_hash": "sv41d8cd98f0",
                "always_active": True,
                "first_name": "slackbot",
                "last_name": "",
                "image_24": "https://a.slack-edge.com/80588/img/slackbot_24.png",
                "image_32": "https://a.slack-edge.com/80588/img/slackbot_32.png",
                "image_48": "https://a.slack-edge.com/80588/img/slackbot_48.png",
                "image_72": "https://a.slack-edge.com/80588/img/slackbot_72.png",
                "image_192": "https://a.slack-edge.com/80588/img/slackbot_192.png",
                "image_512": "https://a.slack-edge.com/80588/img/slackbot_512.png"
            },
            "is_admin": False,
            "is_owner": False,
            "is_primary_owner": False,
            "is_restricted": False,
            "is_ultra_restricted": False,
            "is_bot": True,
            "is_app_user": False,
            "updated": 0,
            "is_email_confirmed": False
        },
        {
            "id": "B5555555555",
            "team_id": "T1234567890",
            "name": "github-bot",
            "deleted": False,
            "color": "36c5f0",
            "real_name": "GitHub",
            "tz": "",
            "tz_label": "",
            "tz_offset": 0,
            "profile": {
                "title": "",
                "phone": "",
                "skype": "",
                "real_name": "GitHub",
                "real_name_normalized": "GitHub",
                "display_name": "GitHub",
                "display_name_normalized": "GitHub",
                "bot_id": "B5555555555",
                "api_app_id": "A0F7YS25R",
                "fields": {},
                "status_text": "",
                "status_emoji": "",
                "status_emoji_display_info": [],
                "status_expiration": 0,
                "avatar_hash": "gf0d6fb7b35e", 
                "image_24": "https://avatars.slack-edge.com/2019-05-28/github_24.png",
                "image_32": "https://avatars.slack-edge.com/2019-05-28/github_32.png",
                "image_48": "https://avatars.slack-edge.com/2019-05-28/github_48.png",
                "image_72": "https://avatars.slack-edge.com/2019-05-28/github_72.png",
                "image_192": "https://avatars.slack-edge.com/2019-05-28/github_192.png",
                "image_512": "https://avatars.slack-edge.com/2019-05-28/github_512.png"
            },
            "is_admin": False,
            "is_owner": False,
            "is_primary_owner": False,
            "is_restricted": False,
            "is_ultra_restricted": False,
            "is_bot": True,
            "is_app_user": True,
            "updated": int((BASE_TS - timedelta(days=10)).timestamp()),
            "is_email_confirmed": False
        },
        {
            "id": "U9999999999",
            "team_id": "T1234567890",
            "name": "deleted.user",
            "deleted": True,
            "color": "666666",
            "real_name": "Deleted User",
            "tz": "",
            "tz_label": "",
            "tz_offset": 0,
            "profile": {
                "title": "",
                "phone": "",
                "skype": "",
                "real_name": "Deleted User", 
                "real_name_normalized": "Deleted User",
                "display_name": "Deleted User",
                "display_name_normalized": "Deleted User",
                "fields": {},
                "status_text": "",
                "status_emoji": "",
                "status_emoji_display_info": [],
                "status_expiration": 0,
                "avatar_hash": "g0000000000",
                "first_name": "Deleted",
                "last_name": "User",
                "image_24": "https://a.slack-edge.com/80588/img/avatars/ava_0000-24.png",
                "image_32": "https://a.slack-edge.com/80588/img/avatars/ava_0000-32.png",
                "image_48": "https://a.slack-edge.com/80588/img/avatars/ava_0000-48.png",
                "image_72": "https://a.slack-edge.com/80588/img/avatars/ava_0000-72.png",
                "image_192": "https://a.slack-edge.com/80588/img/avatars/ava_0000-192.png",
                "image_512": "https://a.slack-edge.com/80588/img/avatars/ava_0000-512.png"
            },
            "is_admin": False,
            "is_owner": False,
            "is_primary_owner": False,
            "is_restricted": False,
            "is_ultra_restricted": False,
            "is_bot": False,
            "is_app_user": False,
            "updated": int((BASE_TS - timedelta(days=30)).timestamp()),
            "is_email_confirmed": False
        }
    ]

def get_mock_messages() -> List[Dict[str, Any]]:
    """
    Mock Slack messages with comprehensive edge case coverage:
    - Regular messages, threaded replies, reactions
    - Bot messages, system messages, deleted messages
    - Messages with files, links, mentions
    - Different message subtypes and formatting
    """
    base_timestamp = BASE_TS.timestamp()
    
    return [
        # Regular message in general channel
        {
            "type": "message",
            "subtype": None,
            "ts": f"{base_timestamp:.6f}",
            "user": "U1111111111",
            "team": "T1234567890",
            "user_team": "T1234567890",
            "source_team": "T1234567890",
            "channel": "C1234567890",
            "text": "Good morning team! Hope everyone is having a great day.",
            "permalink": "https://company.slack.com/archives/C1234567890/p1692096000000000",
            "blocks": [
                {
                    "type": "rich_text",
                    "block_id": "abc123",
                    "elements": [
                        {
                            "type": "rich_text_section",
                            "elements": [
                                {
                                    "type": "text",
                                    "text": "Good morning team! Hope everyone is having a great day."
                                }
                            ]
                        }
                    ]
                }
            ],
            "reactions": [
                {
                    "name": "wave",
                    "users": ["U2222222222", "U3333333333"],
                    "count": 2
                },
                {
                    "name": "coffee",
                    "users": ["U2222222222"],
                    "count": 1
                }
            ]
        },
        
        # Thread parent message with replies
        {
            "type": "message",
            "subtype": None,
            "ts": f"{base_timestamp + 300:.6f}",  # 5 minutes later
            "user": "U2222222222",
            "team": "T1234567890",
            "user_team": "T1234567890", 
            "source_team": "T1234567890",
            "channel": "C2345678901",
            "text": "I've been working on the new feature. Here's the current progress:",
            "permalink": "https://company.slack.com/archives/C2345678901/p1692096300000000",
            "thread_ts": f"{base_timestamp + 300:.6f}",
            "reply_count": 3,
            "reply_users_count": 2,
            "latest_reply": f"{base_timestamp + 900:.6f}",
            "reply_users": ["U1111111111", "U4444444444"],
            "blocks": [
                {
                    "type": "rich_text",
                    "block_id": "def456",
                    "elements": [
                        {
                            "type": "rich_text_section",
                            "elements": [
                                {
                                    "type": "text",
                                    "text": "I've been working on the new feature. Here's the current progress:"
                                }
                            ]
                        }
                    ]
                }
            ],
            "files": [
                {
                    "id": "F1234567890ABCDEF",
                    "created": int(base_timestamp + 300),
                    "timestamp": int(base_timestamp + 300),
                    "name": "feature_progress.png",
                    "title": "Feature Progress Screenshot", 
                    "mimetype": "image/png",
                    "filetype": "png",
                    "pretty_type": "PNG",
                    "user": "U2222222222",
                    "editable": False,
                    "size": 245679,
                    "mode": "hosted",
                    "is_external": False,
                    "external_type": "",
                    "is_public": False,
                    "public_url_shared": False,
                    "display_as_bot": False,
                    "username": "",
                    "url_private": "https://files.slack.com/files-pri/T1234567890-F1234567890ABCDEF/feature_progress.png",
                    "url_private_download": "https://files.slack.com/files-pri/T1234567890-F1234567890ABCDEF/download/feature_progress.png",
                    "thumb_64": "https://files.slack.com/files-tmb/T1234567890-F1234567890ABCDEF-123456/feature_progress_64.png",
                    "thumb_80": "https://files.slack.com/files-tmb/T1234567890-F1234567890ABCDEF-123456/feature_progress_80.png",
                    "thumb_360": "https://files.slack.com/files-tmb/T1234567890-F1234567890ABCDEF-123456/feature_progress_360.png",
                    "thumb_360_w": 360,
                    "thumb_360_h": 240,
                    "thumb_480": "https://files.slack.com/files-tmb/T1234567890-F1234567890ABCDEF-123456/feature_progress_480.png",
                    "thumb_480_w": 480,
                    "thumb_480_h": 320,
                    "thumb_160": "https://files.slack.com/files-tmb/T1234567890-F1234567890ABCDEF-123456/feature_progress_160.png",
                    "image_exif_rotation": 1,
                    "original_w": 1200,
                    "original_h": 800,
                    "permalink": "https://company.slack.com/files/U2222222222/F1234567890ABCDEF/feature_progress.png",
                    "permalink_public": "https://slack-files.com/T1234567890-F1234567890ABCDEF-123456",
                    "channels": ["C2345678901"],
                    "groups": [],
                    "ims": [],
                    "comments_count": 0
                }
            ]
        },
        
        # Thread reply
        {
            "type": "message",
            "subtype": None,
            "ts": f"{base_timestamp + 600:.6f}",  # 10 minutes later
            "user": "U1111111111",
            "team": "T1234567890",
            "user_team": "T1234567890",
            "source_team": "T1234567890",
            "channel": "C2345678901",
            "text": "Excellent work! The UI looks much cleaner now. <@U2222222222> when do you think this will be ready for review?",
            "thread_ts": f"{base_timestamp + 300:.6f}",  # References parent thread
            "parent_user_id": "U2222222222",
            "permalink": "https://company.slack.com/archives/C2345678901/p1692096600000000?thread_ts=1692096300.000000",
            "blocks": [
                {
                    "type": "rich_text",
                    "block_id": "ghi789",
                    "elements": [
                        {
                            "type": "rich_text_section",
                            "elements": [
                                {
                                    "type": "text",
                                    "text": "Excellent work! The UI looks much cleaner now. "
                                },
                                {
                                    "type": "user",
                                    "user_id": "U2222222222"
                                },
                                {
                                    "type": "text",
                                    "text": " when do you think this will be ready for review?"
                                }
                            ]
                        }
                    ]
                }
            ],
            "reactions": [
                {
                    "name": "eyes",
                    "users": ["U2222222222"],
                    "count": 1
                }
            ]
        },
        
        # Bot message from GitHub integration
        {
            "type": "message",
            "subtype": "bot_message",
            "ts": f"{base_timestamp + 1200:.6f}",  # 20 minutes later
            "bot_id": "B5555555555",
            "username": "GitHub",
            "icons": {
                "image_36": "https://avatars.slack-edge.com/2019-05-28/github_36.png",
                "image_48": "https://avatars.slack-edge.com/2019-05-28/github_48.png",
                "image_72": "https://avatars.slack-edge.com/2019-05-28/github_72.png"
            },
            "team": "T1234567890",
            "channel": "C2345678901",
            "text": "",
            "permalink": "https://company.slack.com/archives/C2345678901/p1692097200000000",
            "attachments": [
                {
                    "service_name": "GitHub",
                    "service_url": "https://github.com/",
                    "title": "[company/webapp] Pull request opened by bob.smith",
                    "title_link": "https://github.com/company/webapp/pull/123",
                    "text": "Add new feature dashboard\n\nThis PR includes:\n- New dashboard component\n- Updated routing\n- Tests for all new functionality",
                    "fallback": "[company/webapp] Pull request opened by bob.smith: Add new feature dashboard",
                    "color": "36a64f",
                    "fields": [
                        {
                            "title": "Repository",
                            "value": "company/webapp",
                            "short": True
                        },
                        {
                            "title": "Branch",
                            "value": "feature/dashboard",
                            "short": True
                        }
                    ],
                    "footer": "GitHub",
                    "footer_icon": "https://github.com/favicon.ico",
                    "ts": int(base_timestamp + 1200),
                    "mrkdwn_in": ["text", "pretext"]
                }
            ]
        },
        
        # Message with link and unfurling
        {
            "type": "message",
            "subtype": None,
            "ts": f"{base_timestamp + 1800:.6f}",  # 30 minutes later
            "user": "U3333333333",
            "team": "T1234567890",
            "user_team": "T1234567890",
            "source_team": "T1234567890", 
            "channel": "C1234567890",
            "text": "Great article about our industry trends: https://techcrunch.com/2025/08/15/ai-startup-trends/",
            "permalink": "https://company.slack.com/archives/C1234567890/p1692097800000000",
            "blocks": [
                {
                    "type": "rich_text",
                    "block_id": "jkl012",
                    "elements": [
                        {
                            "type": "rich_text_section",
                            "elements": [
                                {
                                    "type": "text",
                                    "text": "Great article about our industry trends: "
                                },
                                {
                                    "type": "link",
                                    "url": "https://techcrunch.com/2025/08/15/ai-startup-trends/"
                                }
                            ]
                        }
                    ]
                }
            ],
            "attachments": [
                {
                    "service_name": "TechCrunch",
                    "title": "AI Startup Trends for 2025",
                    "title_link": "https://techcrunch.com/2025/08/15/ai-startup-trends/",
                    "text": "Analysis of the latest trends in AI startup funding and technology adoption...",
                    "fallback": "TechCrunch: AI Startup Trends for 2025",
                    "from_url": "https://techcrunch.com/2025/08/15/ai-startup-trends/",
                    "service_icon": "https://techcrunch.com/favicon.ico",
                    "id": 1,
                    "original_url": "https://techcrunch.com/2025/08/15/ai-startup-trends/"
                }
            ]
        },
        
        # Channel join system message
        {
            "type": "message",
            "subtype": "channel_join",
            "ts": f"{base_timestamp + 2400:.6f}",  # 40 minutes later
            "user": "U4444444444",
            "team": "T1234567890",
            "channel": "C2345678901",
            "text": "<@U4444444444|diana.contractor> has joined the channel",
            "permalink": "https://company.slack.com/archives/C2345678901/p1692098400000000",
            "inviter": "U1111111111"
        },
        
        # Channel leave system message
        {
            "type": "message", 
            "subtype": "channel_leave",
            "ts": f"{base_timestamp + 2450:.6f}",  # A bit later
            "user": "U9999999999",  # Former employee
            "team": "T1234567890",
            "channel": "C2345678901",
            "text": "<@U9999999999|deleted.user> has left the channel"
        },
        
        # Minimal message for edge case testing (only 4 fields)
        {
            "type": "message",
            "ts": f"{base_timestamp + 2500:.6f}",
            "channel": "C1234567890", 
            "text": "quick message"
        },
        
        # Message with emoji and formatting
        {
            "type": "message",
            "subtype": None,
            "ts": f"{base_timestamp + 3000:.6f}",  # 50 minutes later
            "user": "U4444444444",
            "team": "T1234567890",
            "user_team": "T1234567890",
            "source_team": "T1234567890",
            "channel": "C2345678901",
            "text": "Thanks for adding me! :wave: I'm excited to contribute to the *engineering* team. Looking forward to working with everyone! :rocket:",
            "permalink": "https://company.slack.com/archives/C2345678901/p1692099000000000",
            "blocks": [
                {
                    "type": "rich_text",
                    "block_id": "mno345",
                    "elements": [
                        {
                            "type": "rich_text_section",
                            "elements": [
                                {
                                    "type": "text",
                                    "text": "Thanks for adding me! "
                                },
                                {
                                    "type": "emoji",
                                    "name": "wave"
                                },
                                {
                                    "type": "text",
                                    "text": " I'm excited to contribute to the "
                                },
                                {
                                    "type": "text",
                                    "text": "engineering",
                                    "style": {
                                        "bold": True
                                    }
                                },
                                {
                                    "type": "text",
                                    "text": " team. Looking forward to working with everyone! "
                                },
                                {
                                    "type": "emoji",
                                    "name": "rocket"
                                }
                            ]
                        }
                    ]
                }
            ],
            "reactions": [
                {
                    "name": "heart",
                    "users": ["U1111111111", "U2222222222"],
                    "count": 2
                }
            ]
        },
        
        # Deleted message (tombstone)
        {
            "type": "message",
            "subtype": "message_deleted",
            "ts": f"{base_timestamp + 3600:.6f}",  # 60 minutes later
            "channel": "C1234567890",
            "deleted_ts": f"{base_timestamp + 3300:.6f}",
            "event_ts": f"{base_timestamp + 3600:.6f}",
            "hidden": True,
            "previous_message": {
                "type": "message",
                "user": "U2222222222",
                "text": "Never mind, found the solution",
                "ts": f"{base_timestamp + 3300:.6f}"
            }
        },
        
        # Message edited
        {
            "type": "message",
            "subtype": "message_changed",
            "ts": f"{base_timestamp + 4200:.6f}",  # 70 minutes later
            "channel": "C1234567890",
            "event_ts": f"{base_timestamp + 4200:.6f}",
            "message": {
                "type": "message",
                "user": "U3333333333",
                "text": "The meeting is scheduled for 3 PM EST (updated time)",
                "ts": f"{base_timestamp + 4000:.6f}",
                "edited": {
                    "user": "U3333333333",
                    "ts": f"{base_timestamp + 4200:.6f}"
                },
                "blocks": [
                    {
                        "type": "rich_text",
                        "block_id": "pqr678",
                        "elements": [
                            {
                                "type": "rich_text_section",
                                "elements": [
                                    {
                                        "type": "text",
                                        "text": "The meeting is scheduled for 3 PM EST (updated time)"
                                    }
                                ]
                            }
                        ]
                    }
                ]
            },
            "previous_message": {
                "type": "message",
                "user": "U3333333333",
                "text": "The meeting is scheduled for 2 PM EST",
                "ts": f"{base_timestamp + 4000:.6f}",
                "blocks": [
                    {
                        "type": "rich_text",
                        "block_id": "pqr678",
                        "elements": [
                            {
                                "type": "rich_text_section",
                                "elements": [
                                    {
                                        "type": "text",
                                        "text": "The meeting is scheduled for 2 PM EST"
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        },
        
        # Slackbot automated message
        {
            "type": "message",
            "subtype": "bot_message",
            "ts": f"{base_timestamp + 4800:.6f}",  # 80 minutes later
            "bot_id": "BSLACKBOT",
            "username": "Slackbot",
            "team": "T1234567890",
            "channel": "D1111111111",  # DM channel
            "text": "I can help you with that! Here are some resources about Slack integrations: https://api.slack.com/docs",
            "permalink": "https://company.slack.com/archives/D1111111111/p1692100800000000"
        },
        
        # Message in archived channel (edge case)
        {
            "type": "message",
            "subtype": None,
            "ts": f"{base_timestamp - 86400:.6f}",  # Yesterday (before archival)
            "user": "U1111111111",
            "team": "T1234567890",
            "user_team": "T1234567890",
            "source_team": "T1234567890",
            "channel": "C3456789012",  # archived-old-project
            "text": "This project is complete. Archiving this channel.",
            "permalink": "https://company.slack.com/archives/C3456789012/p1692009600000000"
        }
    ]

def get_mock_rate_limit_responses() -> Dict[str, Any]:
    """Mock rate limit responses for testing rate limiting behavior."""
    return {
        "rate_limited_response": {
            "ok": False,
            "error": "rate_limited",
            "headers": {
                "retry-after": "30",
                "x-rate-limit-remaining": "0",
                "x-rate-limit-limit": "100",
                "x-rate-limit-reset": str(int((BASE_TS + timedelta(minutes=1)).timestamp()))
            }
        },
        "success_response": {
            "ok": True,
            "channels": get_mock_channels()[:3],  # Partial response
            "response_metadata": {
                "next_cursor": "dGVhbTpDMDYxRkE1UEI="
            },
            "headers": {
                "x-rate-limit-remaining": "99",
                "x-rate-limit-limit": "100",
                "x-rate-limit-reset": str(int((BASE_TS + timedelta(minutes=1)).timestamp()))
            }
        }
    }

def get_mock_api_error_responses() -> Dict[str, Any]:
    """Mock API error responses for testing error handling."""
    return {
        "invalid_auth": {
            "ok": False,
            "error": "invalid_auth"
        },
        "missing_scope": {
            "ok": False,
            "error": "missing_scope",
            "needed": "channels:read",
            "provided": "channels:history"
        },
        "channel_not_found": {
            "ok": False,
            "error": "channel_not_found"
        },
        "account_inactive": {
            "ok": False,
            "error": "account_inactive"
        },
        "internal_error": {
            "ok": False,
            "error": "internal_error"
        }
    }

# Helper functions for test consistency
def validate_mock_data():
    """Validate that all mock data is well-formed JSON and consistent."""
    try:
        channels = get_mock_channels()
        users = get_mock_users() 
        messages = get_mock_messages()
        
        # Validate JSON serializability
        json.dumps(channels)
        json.dumps(users)
        json.dumps(messages)
        
        # Basic consistency checks
        channel_ids = {c["id"] for c in channels}
        user_ids = {u["id"] for u in users}
        
        for msg in messages:
            if "channel" in msg:
                assert msg["channel"] in channel_ids, f"Message references unknown channel: {msg['channel']}"
            if "user" in msg:
                assert msg["user"] in user_ids, f"Message references unknown user: {msg['user']}"
                
        return True
    except Exception as e:
        print(f"Mock data validation failed: {e}")
        return False

def get_mock_collection_result() -> Dict[str, Any]:
    """Mock result from slack collector matching scavenge/ format."""
    return {
        "discovered": {
            "channels": len(get_mock_channels()),
            "users": len(get_mock_users()),
            "conversations": 5  # Number of channels with messages
        },
        "collected": {
            "messages": len(get_mock_messages()),
            "conversations": 5,
            "files": 1,  # One message has a file
            "threads": 1,  # One thread in the messages
            "reactions": 4  # Total reactions across messages
        },
        "channels": get_mock_channels(),
        "users": get_mock_users(),
        "messages": get_mock_messages()
    }

# Alias functions for test compatibility
def get_mock_slack_channels():
    """Alias for get_mock_channels() for test compatibility"""
    return get_mock_channels()

def get_mock_slack_messages():
    """Alias for get_mock_messages() for test compatibility"""
    return get_mock_messages()

# Ensure data is valid on import
if __name__ == "__main__":
    assert validate_mock_data(), "Mock data validation failed"
    print("All Slack mock data validated successfully!")