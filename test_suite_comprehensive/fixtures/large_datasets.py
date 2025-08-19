"""
Large-scale test dataset generators for comprehensive testing.

Generates realistic test data at scale:
- 10,000+ Slack messages with threading
- 1,000+ calendar events across timezones
- 5,000+ drive file metadata entries
- 200+ employee records with full mappings
"""

import json
import random
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Generator
from faker import Faker
import uuid

fake = Faker()

class LargeDatasetGenerator:
    """Generates large-scale realistic test datasets."""
    
    def __init__(self, seed: int = 42):
        """Initialize with deterministic seed for reproducible tests."""
        Faker.seed(seed)
        random.seed(seed)
        self.channels = self._generate_channels()
        self.users = self._generate_users()
        self.employees = self._generate_employees()
    
    def _generate_channels(self, count: int = 50) -> List[Dict[str, Any]]:
        """Generate realistic Slack channels."""
        channels = []
        
        # Common channel types in organizations
        channel_types = [
            ("general", "Company-wide announcements and general discussion"),
            ("random", "Random chatter and non-work discussions"),
            ("engineering", "Engineering team discussions"),
            ("product", "Product development and planning"),
            ("design", "Design team collaboration"),
            ("marketing", "Marketing campaigns and strategies"),
            ("sales", "Sales team coordination"),
            ("support", "Customer support discussions"),
            ("hr", "Human resources announcements"),
            ("it-help", "IT support and technical issues")
        ]
        
        # Add common channels
        for i, (name, purpose) in enumerate(channel_types):
            channels.append({
                "id": f"C{1000000 + i:07d}",
                "name": name,
                "is_channel": True,
                "is_group": False,
                "is_im": False,
                "created": int((datetime.now() - timedelta(days=365)).timestamp()),
                "creator": f"U{1000000 + i % 10:07d}",
                "is_archived": False,
                "is_general": name == "general",
                "members": [f"U{1000000 + j:07d}" for j in range(min(50, count))],
                "topic": {
                    "value": purpose,
                    "creator": f"U{1000000 + i % 10:07d}",
                    "last_set": int((datetime.now() - timedelta(days=30)).timestamp())
                },
                "purpose": {
                    "value": purpose,
                    "creator": f"U{1000000 + i % 10:07d}",
                    "last_set": int((datetime.now() - timedelta(days=30)).timestamp())
                },
                "num_members": min(50, count)
            })
        
        # Add project-specific channels
        projects = ["project-alpha", "project-beta", "project-gamma", "q4-planning", "bug-triage"]
        for i, project in enumerate(projects):
            channels.append({
                "id": f"C{2000000 + i:07d}",
                "name": project,
                "is_channel": True,
                "is_group": False,
                "is_im": False,
                "created": int((datetime.now() - timedelta(days=random.randint(30, 180))).timestamp()),
                "creator": f"U{1000000 + random.randint(0, 9):07d}",
                "is_archived": False,
                "is_general": False,
                "members": [f"U{1000000 + j:07d}" for j in range(random.randint(5, 20))],
                "topic": {
                    "value": f"Discussion for {project}",
                    "creator": f"U{1000000 + i % 10:07d}",
                    "last_set": int((datetime.now() - timedelta(days=10)).timestamp())
                },
                "purpose": {
                    "value": f"Coordination and updates for {project}",
                    "creator": f"U{1000000 + i % 10:07d}",
                    "last_set": int((datetime.now() - timedelta(days=10)).timestamp())
                },
                "num_members": random.randint(5, 20)
            })
        
        return channels
    
    def _generate_users(self, count: int = 200) -> List[Dict[str, Any]]:
        """Generate realistic Slack users."""
        users = []
        
        # Common roles in organizations
        roles = [
            "Software Engineer", "Senior Software Engineer", "Engineering Manager",
            "Product Manager", "Senior Product Manager", "Designer", "UX Designer",
            "Marketing Manager", "Sales Representative", "Customer Success Manager",
            "Data Scientist", "DevOps Engineer", "QA Engineer", "CEO", "CTO",
            "VP of Engineering", "VP of Product", "VP of Sales", "HR Manager"
        ]
        
        for i in range(count):
            first_name = fake.first_name()
            last_name = fake.last_name()
            email = f"{first_name.lower()}.{last_name.lower()}@{fake.domain_name()}"
            
            users.append({
                "id": f"U{1000000 + i:07d}",
                "team_id": "T1000000",
                "name": f"{first_name.lower()}.{last_name.lower()}",
                "deleted": False,
                "color": fake.hex_color()[1:],  # Remove # prefix
                "real_name": f"{first_name} {last_name}",
                "tz": random.choice(["America/New_York", "America/Los_Angeles", "Europe/London", "UTC"]),
                "tz_label": random.choice(["Eastern Standard Time", "Pacific Standard Time", "Greenwich Mean Time", "Coordinated Universal Time"]),
                "tz_offset": random.choice([-18000, -28800, 0, 0]),
                "profile": {
                    "title": random.choice(roles),
                    "phone": fake.phone_number(),
                    "skype": f"{first_name.lower()}.{last_name.lower()}",
                    "real_name": f"{first_name} {last_name}",
                    "real_name_normalized": f"{first_name} {last_name}",
                    "display_name": f"{first_name} {last_name}",
                    "display_name_normalized": f"{first_name} {last_name}",
                    "email": email,
                    "image_24": f"https://avatars.slack-edge.com/{fake.uuid4()}_24.jpg",
                    "image_32": f"https://avatars.slack-edge.com/{fake.uuid4()}_32.jpg",
                    "image_48": f"https://avatars.slack-edge.com/{fake.uuid4()}_48.jpg",
                    "image_72": f"https://avatars.slack-edge.com/{fake.uuid4()}_72.jpg",
                    "image_192": f"https://avatars.slack-edge.com/{fake.uuid4()}_192.jpg",
                    "image_512": f"https://avatars.slack-edge.com/{fake.uuid4()}_512.jpg",
                    "team": "T1000000"
                },
                "is_admin": i < 5,  # First 5 users are admins
                "is_owner": i == 0,  # First user is owner
                "is_primary_owner": i == 0,
                "is_restricted": False,
                "is_ultra_restricted": False,
                "is_bot": False,
                "updated": int(datetime.now().timestamp()),
                "is_app_user": False,
                "has_2fa": random.choice([True, False])
            })
        
        return users
    
    def _generate_employees(self, count: int = 200) -> List[Dict[str, Any]]:
        """Generate employee records with ID mappings."""
        employees = []
        
        departments = [
            "Engineering", "Product", "Design", "Marketing", "Sales",
            "Customer Success", "HR", "Finance", "Legal", "Operations"
        ]
        
        for i, user in enumerate(self.users[:count]):
            employees.append({
                "id": f"EMP{1000 + i:04d}",
                "email": user["profile"]["email"],
                "first_name": user["real_name"].split()[0],
                "last_name": user["real_name"].split()[-1],
                "slack_id": user["id"],
                "calendar_id": user["profile"]["email"],
                "department": random.choice(departments),
                "title": user["profile"]["title"],
                "manager_id": f"EMP{1000 + random.randint(0, min(20, count-1)):04d}" if i > 0 else None,
                "start_date": fake.date_between(start_date="-2y", end_date="today").isoformat(),
                "status": "active" if random.random() > 0.05 else "inactive",  # 95% active
                "location": random.choice(["New York", "San Francisco", "London", "Toronto", "Remote"]),
                "timezone": user["tz"],
                "phone": user["profile"]["phone"],
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            })
        
        return employees
    
    def generate_slack_messages(self, count: int = 10000) -> Generator[Dict[str, Any], None, None]:
        """Generate realistic Slack messages with threading."""
        message_types = [
            "regular", "thread_reply", "file_share", "link_share", 
            "code_snippet", "meeting_update", "announcement"
        ]
        
        # Track threads for realistic threading
        active_threads = {}
        
        for i in range(count):
            channel = random.choice(self.channels)
            user = random.choice(self.users)
            msg_type = random.choice(message_types)
            
            # Base timestamp
            base_time = datetime.now() - timedelta(days=random.randint(0, 90))
            ts = str(base_time.timestamp()).replace(".", "")[:16] + ".000000"
            
            message = {
                "type": "message",
                "ts": ts,
                "user": user["id"],
                "channel": channel["id"],
                "text": self._generate_message_text(msg_type, user["real_name"]),
                "source_team": "T1000000",
                "user_team": "T1000000"
            }
            
            # Add threading (30% chance for replies)
            if random.random() < 0.3 and active_threads:
                # This is a thread reply
                thread_ts = random.choice(list(active_threads.keys()))
                message["thread_ts"] = thread_ts
                message["parent_user_id"] = active_threads[thread_ts]["user"]
                active_threads[thread_ts]["reply_count"] += 1
            elif random.random() < 0.2:
                # Start a new thread
                active_threads[ts] = {
                    "user": user["id"],
                    "reply_count": 0
                }
            
            # Add reactions (20% chance)
            if random.random() < 0.2:
                message["reactions"] = self._generate_reactions()
            
            # Add files (5% chance)
            if random.random() < 0.05:
                message["files"] = self._generate_file_attachments()
            
            # Add edited timestamp (10% chance)
            if random.random() < 0.1:
                edit_time = base_time + timedelta(minutes=random.randint(1, 60))
                message["edited"] = {
                    "user": user["id"],
                    "ts": str(edit_time.timestamp()).replace(".", "")[:16] + ".000000"
                }
            
            yield message
    
    def _generate_message_text(self, msg_type: str, user_name: str) -> str:
        """Generate realistic message text based on type."""
        templates = {
            "regular": [
                "Hey team, just wanted to check in on the progress.",
                "Does anyone know if the deployment went through?",
                "Thanks for the update, looks good to me!",
                "Can we schedule a quick sync to discuss this?",
                "I'll take a look at this and get back to you.",
                "Great work on the feature, the users love it!",
                "We should consider this for the next sprint.",
                "The metrics are looking much better this week."
            ],
            "thread_reply": [
                "Thanks for clarifying that!",
                "I agree with this approach.",
                "Let me know if you need any help with implementation.",
                "That makes sense, good point.",
                "I can work on this part.",
                "Should we document this decision?",
                "Sounds good to me!"
            ],
            "file_share": [
                "Here's the latest version of the design mockups.",
                "Sharing the performance report from last week.",
                "Updated documentation attached.",
                "Here are the test results we discussed."
            ],
            "link_share": [
                "Found this interesting article: https://example.com/article",
                "Relevant documentation: https://docs.example.com",
                "Bug report: https://github.com/company/repo/issues/123"
            ],
            "code_snippet": [
                "```python\ndef example_function():\n    return 'Hello World'\n```",
                "```javascript\nconst data = await fetch('/api/data');\n```",
                "```sql\nSELECT * FROM users WHERE active = true;\n```"
            ],
            "meeting_update": [
                "Stand-up cancelled today, async updates in thread.",
                "Meeting moved to 2pm EST.",
                "Adding agenda item for tomorrow's planning meeting.",
                "Post-mortem scheduled for Friday 3pm."
            ],
            "announcement": [
                "🎉 Congratulations to the team on shipping v2.0!",
                "📢 All hands meeting scheduled for next Tuesday at 2pm.",
                "🚀 New feature rollout starts Monday.",
                "⚠️ Scheduled maintenance this weekend, expect brief downtime."
            ]
        }
        
        return random.choice(templates.get(msg_type, templates["regular"]))
    
    def _generate_reactions(self) -> List[Dict[str, Any]]:
        """Generate realistic message reactions."""
        reactions = []
        common_emojis = ["👍", "❤️", "😄", "🎉", "✅", "👀", "🔥", "💯"]
        
        for emoji in random.sample(common_emojis, random.randint(1, 3)):
            user_count = random.randint(1, 5)
            reactions.append({
                "name": emoji,
                "users": [f"U{1000000 + j:07d}" for j in range(user_count)],
                "count": user_count
            })
        
        return reactions
    
    def _generate_file_attachments(self) -> List[Dict[str, Any]]:
        """Generate realistic file attachments."""
        file_types = [
            {"name": "design_mockup.png", "mimetype": "image/png", "size": 1024*512},
            {"name": "report.pdf", "mimetype": "application/pdf", "size": 1024*1024*2},
            {"name": "data.xlsx", "mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "size": 1024*256},
            {"name": "code.py", "mimetype": "text/x-python", "size": 1024*4}
        ]
        
        file_info = random.choice(file_types)
        
        return [{
            "id": f"F{random.randint(10000000, 99999999)}",
            "name": file_info["name"],
            "title": file_info["name"],
            "mimetype": file_info["mimetype"],
            "size": file_info["size"],
            "url_private": f"https://files.slack.com/files-pri/T1000000-F{random.randint(10000000, 99999999)}/{file_info['name']}",
            "permalink": f"https://company.slack.com/files/U{random.randint(1000000, 1000199):07d}/F{random.randint(10000000, 99999999)}/{file_info['name']}",
            "created": int(datetime.now().timestamp()),
            "is_external": False,
            "is_public": False,
            "public_url_shared": False
        }]
    
    def generate_calendar_events(self, count: int = 1000) -> Generator[Dict[str, Any], None, None]:
        """Generate realistic calendar events across timezones."""
        meeting_types = [
            "1:1", "Team Standup", "Sprint Planning", "Sprint Review", 
            "All Hands", "Product Demo", "Design Review", "Architecture Review",
            "Customer Call", "Interview", "Training", "Social Event"
        ]
        
        for i in range(count):
            attendee_count = random.randint(2, min(20, len(self.employees)))
            attendees = random.sample(self.employees, attendee_count)
            organizer = attendees[0]
            
            # Random date within last 6 months
            event_date = fake.date_time_between(start_date="-6M", end_date="now")
            
            # Duration between 30 minutes and 2 hours
            duration = timedelta(minutes=random.choice([30, 60, 90, 120]))
            end_time = event_date + duration
            
            meeting_type = random.choice(meeting_types)
            
            yield {
                "id": f"event_{uuid.uuid4()}",
                "summary": f"{meeting_type} - {fake.catch_phrase()}",
                "description": fake.text(max_nb_chars=200) if random.random() < 0.7 else "",
                "start": {
                    "dateTime": event_date.isoformat(),
                    "timeZone": organizer["timezone"]
                },
                "end": {
                    "dateTime": end_time.isoformat(),
                    "timeZone": organizer["timezone"]
                },
                "attendees": [
                    {
                        "email": attendee["email"],
                        "displayName": f"{attendee['first_name']} {attendee['last_name']}",
                        "responseStatus": random.choice(["accepted", "tentative", "declined", "needsAction"]),
                        "organizer": attendee == organizer
                    }
                    for attendee in attendees
                ],
                "organizer": {
                    "email": organizer["email"],
                    "displayName": f"{organizer['first_name']} {organizer['last_name']}"
                },
                "location": random.choice([
                    "Conference Room A", "Conference Room B", "Zoom", 
                    "Google Meet", "Teams", "Phone", "Office"
                ]) if random.random() < 0.8 else "",
                "status": "confirmed",
                "created": fake.date_time_between(start_date="-6M", end_date=event_date).isoformat(),
                "updated": fake.date_time_between(start_date=event_date, end_date="now").isoformat(),
                "recurringEventId": f"recurring_{uuid.uuid4()}" if random.random() < 0.3 else None,
                "transparency": "opaque",
                "visibility": "default",
                "guestsCanModify": False,
                "guestsCanInviteOthers": random.choice([True, False]),
                "guestsCanSeeOtherGuests": True,
                "hangoutLink": f"https://meet.google.com/{fake.uuid4()}" if "Google Meet" in meeting_type else None
            }
    
    def generate_drive_metadata(self, count: int = 5000) -> Generator[Dict[str, Any], None, None]:
        """Generate realistic Drive file metadata."""
        file_types = [
            {"name": "Document", "extension": "docx", "mimeType": "application/vnd.google-apps.document"},
            {"name": "Spreadsheet", "extension": "xlsx", "mimeType": "application/vnd.google-apps.spreadsheet"},
            {"name": "Presentation", "extension": "pptx", "mimeType": "application/vnd.google-apps.presentation"},
            {"name": "PDF", "extension": "pdf", "mimeType": "application/pdf"},
            {"name": "Image", "extension": "png", "mimeType": "image/png"},
            {"name": "Code", "extension": "py", "mimeType": "text/x-python"}
        ]
        
        folders = [
            "Engineering", "Product", "Design", "Marketing", "Sales",
            "HR", "Finance", "Legal", "Shared", "Archive"
        ]
        
        for i in range(count):
            file_type = random.choice(file_types)
            owner = random.choice(self.employees)
            
            # File size (realistic distribution)
            if file_type["extension"] in ["png", "jpg"]:
                size = random.randint(100*1024, 10*1024*1024)  # 100KB - 10MB
            elif file_type["extension"] in ["pdf", "docx", "pptx"]:
                size = random.randint(50*1024, 50*1024*1024)   # 50KB - 50MB
            else:
                size = random.randint(1*1024, 5*1024*1024)     # 1KB - 5MB
            
            created_time = fake.date_time_between(start_date="-2y", end_date="now")
            modified_time = fake.date_time_between(start_date=created_time, end_date="now")
            
            yield {
                "id": f"drive_file_{uuid.uuid4()}",
                "name": f"{fake.catch_phrase().replace(' ', '_')}.{file_type['extension']}",
                "mimeType": file_type["mimeType"],
                "size": str(size),
                "parents": [f"folder_{random.choice(folders).lower()}"],
                "owners": [{
                    "displayName": f"{owner['first_name']} {owner['last_name']}",
                    "emailAddress": owner["email"],
                    "kind": "drive#user"
                }],
                "lastModifyingUser": {
                    "displayName": f"{owner['first_name']} {owner['last_name']}",
                    "emailAddress": owner["email"],
                    "kind": "drive#user"
                },
                "createdTime": created_time.isoformat() + "Z",
                "modifiedTime": modified_time.isoformat() + "Z",
                "viewedByMeTime": modified_time.isoformat() + "Z" if random.random() < 0.8 else None,
                "shared": random.choice([True, False]),
                "permissions": self._generate_drive_permissions(owner),
                "webViewLink": f"https://drive.google.com/file/d/{uuid.uuid4()}/view",
                "webContentLink": f"https://drive.google.com/uc?id={uuid.uuid4()}" if file_type["extension"] != "folder" else None,
                "thumbnailLink": f"https://drive.google.com/thumbnail?id={uuid.uuid4()}" if file_type["extension"] in ["png", "jpg", "pdf"] else None,
                "version": str(random.randint(1, 20)),
                "trashed": False,
                "explicitlyTrashed": False
            }
    
    def _generate_drive_permissions(self, owner: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate Drive file permissions."""
        permissions = [{
            "id": f"permission_{uuid.uuid4()}",
            "type": "user",
            "emailAddress": owner["email"],
            "role": "owner",
            "displayName": f"{owner['first_name']} {owner['last_name']}"
        }]
        
        # Add random viewers/editors (50% chance)
        if random.random() < 0.5:
            share_count = random.randint(1, 5)
            shared_with = random.sample(self.employees, min(share_count, len(self.employees)-1))
            
            for user in shared_with:
                if user != owner:
                    permissions.append({
                        "id": f"permission_{uuid.uuid4()}",
                        "type": "user",
                        "emailAddress": user["email"],
                        "role": random.choice(["reader", "writer", "commenter"]),
                        "displayName": f"{user['first_name']} {user['last_name']}"
                    })
        
        return permissions

def get_large_slack_dataset(count: int = 10000) -> List[Dict[str, Any]]:
    """Get large Slack dataset for testing."""
    generator = LargeDatasetGenerator()
    return list(generator.generate_slack_messages(count))

def get_large_calendar_dataset(count: int = 1000) -> List[Dict[str, Any]]:
    """Get large calendar dataset for testing."""
    generator = LargeDatasetGenerator()
    return list(generator.generate_calendar_events(count))

def get_large_drive_dataset(count: int = 5000) -> List[Dict[str, Any]]:
    """Get large Drive dataset for testing."""
    generator = LargeDatasetGenerator()
    return list(generator.generate_drive_metadata(count))

def get_employee_dataset(count: int = 200) -> List[Dict[str, Any]]:
    """Get employee dataset for testing."""
    generator = LargeDatasetGenerator()
    return generator.employees[:count]