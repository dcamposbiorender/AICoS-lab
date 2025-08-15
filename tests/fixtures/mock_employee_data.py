"""
Comprehensive mock Employee/Roster data for testing collector wrappers.
Covers ID mappings, organizational structure, status variations, and edge cases.
Data is deterministic - same function calls return identical results.
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

# Base timestamp for deterministic data
BASE_DT = datetime(2025, 8, 15, 9, 0, 0)

def get_mock_employee_roster() -> List[Dict[str, Any]]:
    """
    Mock employee roster with comprehensive ID mappings and organizational data.
    Covers active/inactive employees, contractors, various departments, and edge cases.
    """
    return [
        # Active employees with complete ID mapping
        {
            "employee_id": "EMP001",
            "slack_id": "U1111111111",
            "email": "alice@company.com",
            "calendar_id": "alice@company.com",
            "google_workspace_id": "alice@company.com",
            "first_name": "Alice",
            "last_name": "Johnson",
            "display_name": "Alice Johnson",
            "preferred_name": "Alice",
            "title": "Chief Executive Officer",
            "department": "Executive",
            "division": "Leadership",
            "location": "New York, NY",
            "office": "NYC Headquarters", 
            "floor": "15",
            "desk_number": "15-001",
            "phone": "+1-555-0101",
            "mobile": "+1-555-0201",
            "manager_id": None,
            "manager_email": None,
            "direct_reports": ["bob@company.com", "charlie@company.com", "eve@company.com"],
            "skip_level_reports": ["diana.contractor@company.com", "frank@company.com"],
            "employment_type": "full_time",
            "employee_status": "active",
            "hire_date": (BASE_DT - timedelta(days=1095)).strftime("%Y-%m-%d"),  # ~3 years ago
            "termination_date": None,
            "last_working_day": None,
            "timezone": "America/New_York",
            "work_schedule": {
                "monday": {"start": "09:00", "end": "17:00"},
                "tuesday": {"start": "09:00", "end": "17:00"},
                "wednesday": {"start": "09:00", "end": "17:00"},
                "thursday": {"start": "09:00", "end": "17:00"},
                "friday": {"start": "09:00", "end": "17:00"},
                "saturday": None,
                "sunday": None
            },
            "cost_center": "100-EXEC",
            "budget_owner": True,
            "security_clearance": "executive",
            "access_level": "full",
            "slack_admin": True,
            "calendar_admin": True,
            "drive_admin": True,
            "two_factor_enabled": True,
            "vpn_access": True,
            "remote_work_eligible": True,
            "equipment": {
                "laptop": "MacBook Pro 16-inch 2024",
                "monitor": "Dell UltraSharp 32-inch",
                "phone": "iPhone 15 Pro",
                "accessories": ["Magic Keyboard", "Magic Mouse", "AirPods Pro"]
            },
            "emergency_contact": {
                "name": "John Johnson",
                "relationship": "Spouse",
                "phone": "+1-555-0301"
            },
            "notes": "Executive team member - highest access level",
            "tags": ["executive", "decision_maker", "budget_owner", "admin"],
            "last_updated": BASE_DT.isoformat(),
            "data_source": "hr_system",
            "sync_status": "synchronized"
        },
        
        {
            "employee_id": "EMP002",
            "slack_id": "U2222222222",
            "email": "bob@company.com",
            "calendar_id": "bob@company.com",
            "google_workspace_id": "bob@company.com",
            "first_name": "Robert",
            "last_name": "Smith",
            "display_name": "Bob Smith",
            "preferred_name": "Bob",
            "title": "Senior Software Engineer",
            "department": "Engineering",
            "division": "Technology",
            "location": "San Francisco, CA",
            "office": "SF Tech Hub",
            "floor": "3",
            "desk_number": "03-042",
            "phone": "+1-555-0102",
            "mobile": "+1-555-0202",
            "manager_id": "EMP001",
            "manager_email": "alice@company.com",
            "direct_reports": ["diana.contractor@company.com"],
            "skip_level_reports": [],
            "employment_type": "full_time",
            "employee_status": "active",
            "hire_date": (BASE_DT - timedelta(days=730)).strftime("%Y-%m-%d"),  # ~2 years ago
            "termination_date": None,
            "last_working_day": None,
            "timezone": "America/Los_Angeles",
            "work_schedule": {
                "monday": {"start": "10:00", "end": "18:00"},
                "tuesday": {"start": "10:00", "end": "18:00"},
                "wednesday": {"start": "10:00", "end": "18:00"},
                "thursday": {"start": "10:00", "end": "18:00"},
                "friday": {"start": "10:00", "end": "16:00"},  # Early Fridays
                "saturday": None,
                "sunday": None
            },
            "cost_center": "200-ENG",
            "budget_owner": False,
            "security_clearance": "standard",
            "access_level": "developer",
            "slack_admin": False,
            "calendar_admin": False,
            "drive_admin": False,
            "two_factor_enabled": True,
            "vpn_access": True,
            "remote_work_eligible": True,
            "equipment": {
                "laptop": "MacBook Pro 14-inch 2023",
                "monitor": "LG UltraFine 27-inch",
                "phone": "iPhone 14",
                "accessories": ["Mechanical Keyboard", "Ergonomic Mouse", "Standing Desk"]
            },
            "emergency_contact": {
                "name": "Sarah Smith",
                "relationship": "Partner",
                "phone": "+1-555-0302"
            },
            "notes": "Senior engineer - technical lead for new features",
            "tags": ["engineering", "senior", "technical_lead", "fullstack"],
            "last_updated": (BASE_DT - timedelta(hours=2)).isoformat(),
            "data_source": "hr_system",
            "sync_status": "synchronized"
        },
        
        {
            "employee_id": "EMP003",
            "slack_id": "U3333333333",
            "email": "charlie@company.com",
            "calendar_id": "charlie@company.com",
            "google_workspace_id": "charlie@company.com",
            "first_name": "Charles",
            "last_name": "Brown",
            "display_name": "Charlie Brown",
            "preferred_name": "Charlie",
            "title": "Product Manager",
            "department": "Product",
            "division": "Product & Design",
            "location": "London, UK",
            "office": "London Office",
            "floor": "2", 
            "desk_number": "02-015",
            "phone": "+44-20-7946-0958",
            "mobile": "+44-7911-123456",
            "manager_id": "EMP001",
            "manager_email": "alice@company.com",
            "direct_reports": ["frank@company.com"],
            "skip_level_reports": [],
            "employment_type": "full_time",
            "employee_status": "active",
            "hire_date": (BASE_DT - timedelta(days=545)).strftime("%Y-%m-%d"),  # ~1.5 years ago
            "termination_date": None,
            "last_working_day": None,
            "timezone": "Europe/London",
            "work_schedule": {
                "monday": {"start": "09:00", "end": "17:30"},
                "tuesday": {"start": "09:00", "end": "17:30"},
                "wednesday": {"start": "09:00", "end": "17:30"},
                "thursday": {"start": "09:00", "end": "17:30"},
                "friday": {"start": "09:00", "end": "17:30"},
                "saturday": None,
                "sunday": None
            },
            "cost_center": "300-PROD",
            "budget_owner": False,
            "security_clearance": "standard",
            "access_level": "manager",
            "slack_admin": False,
            "calendar_admin": False,
            "drive_admin": False,
            "two_factor_enabled": True,
            "vpn_access": True,
            "remote_work_eligible": True,
            "equipment": {
                "laptop": "MacBook Air M2 2023",
                "monitor": "Dell UltraSharp 24-inch",
                "phone": "iPhone 13",
                "accessories": ["Apple Magic Keyboard", "Apple Magic Mouse"]
            },
            "emergency_contact": {
                "name": "Lucy Brown",
                "relationship": "Sister",
                "phone": "+44-7911-654321"
            },
            "notes": "Product manager - owns roadmap and feature prioritization",
            "tags": ["product", "manager", "roadmap_owner", "stakeholder_management"],
            "last_updated": (BASE_DT - timedelta(hours=8)).isoformat(),
            "data_source": "hr_system",
            "sync_status": "synchronized"
        },
        
        # Contractor with limited access
        {
            "employee_id": "CNT001",
            "slack_id": "U4444444444",
            "email": "diana.contractor@company.com",
            "calendar_id": "diana.contractor@company.com",
            "google_workspace_id": "diana.contractor@company.com",
            "first_name": "Diana",
            "last_name": "Wilson",
            "display_name": "Diana Wilson",
            "preferred_name": "Diana",
            "title": "DevOps Contractor",
            "department": "Engineering",
            "division": "Technology",
            "location": "Chicago, IL",
            "office": "Remote",
            "floor": None,
            "desk_number": None,
            "phone": "+1-555-0104",
            "mobile": "+1-555-0204",
            "manager_id": "EMP002",
            "manager_email": "bob@company.com",
            "direct_reports": [],
            "skip_level_reports": [],
            "employment_type": "contractor",
            "employee_status": "active",
            "hire_date": (BASE_DT - timedelta(days=180)).strftime("%Y-%m-%d"),  # 6 months ago
            "termination_date": None,
            "contract_end_date": (BASE_DT + timedelta(days=185)).strftime("%Y-%m-%d"),  # 6 months from now
            "last_working_day": None,
            "timezone": "America/Chicago",
            "work_schedule": {
                "monday": {"start": "08:00", "end": "16:00"},
                "tuesday": {"start": "08:00", "end": "16:00"},
                "wednesday": {"start": "08:00", "end": "16:00"},
                "thursday": {"start": "08:00", "end": "16:00"},
                "friday": {"start": "08:00", "end": "16:00"},
                "saturday": None,
                "sunday": None
            },
            "cost_center": "200-ENG-CNT",
            "budget_owner": False,
            "security_clearance": "restricted",
            "access_level": "contractor",
            "slack_admin": False,
            "calendar_admin": False,
            "drive_admin": False,
            "two_factor_enabled": True,
            "vpn_access": True,
            "remote_work_eligible": True,
            "equipment": {
                "laptop": "Own Device - MacBook Pro",
                "monitor": "Own Device",
                "phone": "Personal Device",
                "accessories": []
            },
            "emergency_contact": {
                "name": "Michael Wilson",
                "relationship": "Spouse",
                "phone": "+1-555-0304"
            },
            "notes": "Contractor - DevOps infrastructure and deployment automation",
            "tags": ["contractor", "devops", "infrastructure", "temporary"],
            "last_updated": (BASE_DT - timedelta(days=3)).isoformat(),
            "data_source": "contractor_system",
            "sync_status": "synchronized"
        },
        
        # New employee (onboarding)
        {
            "employee_id": "EMP005",
            "slack_id": "U5555555555",
            "email": "eve@company.com",
            "calendar_id": "eve@company.com",
            "google_workspace_id": "eve@company.com",
            "first_name": "Evelyn",
            "last_name": "Davis",
            "display_name": "Eve Davis",
            "preferred_name": "Eve",
            "title": "Marketing Manager",
            "department": "Marketing",
            "division": "Growth",
            "location": "Austin, TX",
            "office": "Austin Office",
            "floor": "1",
            "desk_number": "01-023",
            "phone": "+1-555-0105",
            "mobile": "+1-555-0205",
            "manager_id": "EMP001",
            "manager_email": "alice@company.com",
            "direct_reports": [],
            "skip_level_reports": [],
            "employment_type": "full_time",
            "employee_status": "onboarding",
            "hire_date": (BASE_DT - timedelta(days=5)).strftime("%Y-%m-%d"),  # 5 days ago
            "termination_date": None,
            "last_working_day": None,
            "timezone": "America/Chicago",
            "work_schedule": {
                "monday": {"start": "09:00", "end": "17:00"},
                "tuesday": {"start": "09:00", "end": "17:00"},
                "wednesday": {"start": "09:00", "end": "17:00"},
                "thursday": {"start": "09:00", "end": "17:00"},
                "friday": {"start": "09:00", "end": "17:00"},
                "saturday": None,
                "sunday": None
            },
            "cost_center": "400-MKT",
            "budget_owner": False,
            "security_clearance": "standard",
            "access_level": "standard",
            "slack_admin": False,
            "calendar_admin": False,
            "drive_admin": False,
            "two_factor_enabled": True,
            "vpn_access": False,  # Not set up yet
            "remote_work_eligible": True,
            "equipment": {
                "laptop": "Pending IT Setup",
                "monitor": "Pending IT Setup",
                "phone": "Pending IT Setup",
                "accessories": []
            },
            "emergency_contact": {
                "name": "Robert Davis",
                "relationship": "Father",
                "phone": "+1-555-0305"
            },
            "notes": "New hire - currently in onboarding process",
            "tags": ["new_hire", "onboarding", "marketing", "pending_setup"],
            "last_updated": (BASE_DT - timedelta(days=1)).isoformat(),
            "data_source": "hr_system",
            "sync_status": "pending_setup"
        },
        
        # Junior employee
        {
            "employee_id": "EMP006",
            "slack_id": "U6666666666",
            "email": "frank@company.com",
            "calendar_id": "frank@company.com",
            "google_workspace_id": "frank@company.com",
            "first_name": "Frank",
            "last_name": "Miller",
            "display_name": "Frank Miller",
            "preferred_name": "Frank",
            "title": "Junior Product Designer",
            "department": "Product",
            "division": "Product & Design",
            "location": "Remote",
            "office": "Remote",
            "floor": None,
            "desk_number": None,
            "phone": "+1-555-0106",
            "mobile": "+1-555-0206",
            "manager_id": "EMP003",
            "manager_email": "charlie@company.com",
            "direct_reports": [],
            "skip_level_reports": [],
            "employment_type": "full_time",
            "employee_status": "active",
            "hire_date": (BASE_DT - timedelta(days=120)).strftime("%Y-%m-%d"),  # 4 months ago
            "termination_date": None,
            "last_working_day": None,
            "timezone": "America/Denver",
            "work_schedule": {
                "monday": {"start": "09:00", "end": "17:00"},
                "tuesday": {"start": "09:00", "end": "17:00"},
                "wednesday": {"start": "09:00", "end": "17:00"},
                "thursday": {"start": "09:00", "end": "17:00"},
                "friday": {"start": "09:00", "end": "17:00"},
                "saturday": None,
                "sunday": None
            },
            "cost_center": "300-PROD",
            "budget_owner": False,
            "security_clearance": "standard",
            "access_level": "standard",
            "slack_admin": False,
            "calendar_admin": False,
            "drive_admin": False,
            "two_factor_enabled": True,
            "vpn_access": True,
            "remote_work_eligible": True,
            "equipment": {
                "laptop": "MacBook Air M1 2022",
                "monitor": "Dell 24-inch",
                "phone": "iPhone 12",
                "accessories": ["Wacom Tablet", "Design Mouse"]
            },
            "emergency_contact": {
                "name": "Janet Miller",
                "relationship": "Mother",
                "phone": "+1-555-0306"
            },
            "notes": "Junior designer - learning product design fundamentals",
            "tags": ["junior", "designer", "product", "remote", "learning"],
            "last_updated": (BASE_DT - timedelta(days=7)).isoformat(),
            "data_source": "hr_system",
            "sync_status": "synchronized"
        },
        
        # Former employee (terminated)
        {
            "employee_id": "EMP999",
            "slack_id": "U9999999999",  # Matches deleted user in Slack mock data
            "email": "deleted.user@company.com",
            "calendar_id": "deleted.user@company.com",
            "google_workspace_id": None,  # Account deleted
            "first_name": "Deleted",
            "last_name": "User",
            "display_name": "Deleted User",
            "preferred_name": "Deleted",
            "title": "Former Sales Manager",
            "department": "Sales",
            "division": "Revenue",
            "location": "New York, NY",
            "office": "NYC Headquarters",
            "floor": None,
            "desk_number": None,
            "phone": None,
            "mobile": None,
            "manager_id": "EMP001",
            "manager_email": "alice@company.com",
            "direct_reports": [],
            "skip_level_reports": [],
            "employment_type": "full_time",
            "employee_status": "terminated",
            "hire_date": (BASE_DT - timedelta(days=800)).strftime("%Y-%m-%d"),
            "termination_date": (BASE_DT - timedelta(days=30)).strftime("%Y-%m-%d"),  # Terminated 30 days ago
            "last_working_day": (BASE_DT - timedelta(days=30)).strftime("%Y-%m-%d"),
            "timezone": "America/New_York",
            "work_schedule": None,
            "cost_center": "500-SALES",
            "budget_owner": False,
            "security_clearance": None,
            "access_level": "revoked",
            "slack_admin": False,
            "calendar_admin": False,
            "drive_admin": False,
            "two_factor_enabled": False,
            "vpn_access": False,
            "remote_work_eligible": False,
            "equipment": {
                "laptop": "Returned",
                "monitor": "Returned",
                "phone": "Returned",
                "accessories": []
            },
            "emergency_contact": None,
            "notes": "Former employee - all access revoked, accounts deleted",
            "tags": ["terminated", "former_employee", "access_revoked"],
            "last_updated": (BASE_DT - timedelta(days=30)).isoformat(),
            "data_source": "hr_system",
            "sync_status": "deleted"
        },
        
        # Employee with incomplete data (edge case)
        {
            "employee_id": "EMP007",
            "slack_id": None,  # No Slack account yet
            "email": "grace@company.com",
            "calendar_id": "grace@company.com",
            "google_workspace_id": "grace@company.com",
            "first_name": "Grace",
            "last_name": "Lee",
            "display_name": "Grace Lee",
            "preferred_name": "Grace",
            "title": "Data Analyst",
            "department": "Analytics",
            "division": "Technology",
            "location": "Seattle, WA",
            "office": "Seattle Office",
            "floor": "4",
            "desk_number": "04-008",
            "phone": "+1-555-0107",
            "mobile": "+1-555-0207",
            "manager_id": "EMP002",
            "manager_email": "bob@company.com",
            "direct_reports": [],
            "skip_level_reports": [],
            "employment_type": "full_time",
            "employee_status": "pre_start",
            "hire_date": (BASE_DT + timedelta(days=14)).strftime("%Y-%m-%d"),  # Starts in 2 weeks
            "termination_date": None,
            "last_working_day": None,
            "timezone": "America/Los_Angeles",
            "work_schedule": {
                "monday": {"start": "09:00", "end": "17:00"},
                "tuesday": {"start": "09:00", "end": "17:00"},
                "wednesday": {"start": "09:00", "end": "17:00"},
                "thursday": {"start": "09:00", "end": "17:00"},
                "friday": {"start": "09:00", "end": "17:00"},
                "saturday": None,
                "sunday": None
            },
            "cost_center": "200-ENG-DATA",
            "budget_owner": False,
            "security_clearance": "pending",
            "access_level": "pending",
            "slack_admin": False,
            "calendar_admin": False,
            "drive_admin": False,
            "two_factor_enabled": False,
            "vpn_access": False,
            "remote_work_eligible": True,
            "equipment": {
                "laptop": "On Order",
                "monitor": "On Order",
                "phone": "On Order",
                "accessories": []
            },
            "emergency_contact": {
                "name": "David Lee",
                "relationship": "Brother",
                "phone": "+1-555-0307"
            },
            "notes": "Future employee - starting in 2 weeks, accounts pending setup",
            "tags": ["future_employee", "pre_start", "accounts_pending", "analytics"],
            "last_updated": (BASE_DT - timedelta(days=5)).isoformat(),
            "data_source": "hr_system",
            "sync_status": "pending_start"
        },
        
        # Intern (temporary employee)
        {
            "employee_id": "INT001",
            "slack_id": "U8888888888",
            "email": "henry.intern@company.com",
            "calendar_id": "henry.intern@company.com",
            "google_workspace_id": "henry.intern@company.com",
            "first_name": "Henry",
            "last_name": "Chen",
            "display_name": "Henry Chen",
            "preferred_name": "Henry",
            "title": "Software Engineering Intern",
            "department": "Engineering",
            "division": "Technology",
            "location": "San Francisco, CA",
            "office": "SF Tech Hub",
            "floor": "3",
            "desk_number": "03-101",
            "phone": "+1-555-0108",
            "mobile": "+1-555-0208",
            "manager_id": "EMP002",
            "manager_email": "bob@company.com",
            "direct_reports": [],
            "skip_level_reports": [],
            "employment_type": "intern",
            "employee_status": "active",
            "hire_date": (BASE_DT - timedelta(days=30)).strftime("%Y-%m-%d"),  # Started a month ago
            "termination_date": (BASE_DT + timedelta(days=60)).strftime("%Y-%m-%d"),  # 3-month internship
            "last_working_day": (BASE_DT + timedelta(days=60)).strftime("%Y-%m-%d"),
            "timezone": "America/Los_Angeles",
            "work_schedule": {
                "monday": {"start": "10:00", "end": "18:00"},
                "tuesday": {"start": "10:00", "end": "18:00"},
                "wednesday": {"start": "10:00", "end": "18:00"},
                "thursday": {"start": "10:00", "end": "18:00"},
                "friday": {"start": "10:00", "end": "16:00"},
                "saturday": None,
                "sunday": None
            },
            "cost_center": "200-ENG-INT",
            "budget_owner": False,
            "security_clearance": "intern",
            "access_level": "intern",
            "slack_admin": False,
            "calendar_admin": False,
            "drive_admin": False,
            "two_factor_enabled": True,
            "vpn_access": False,  # Limited access
            "remote_work_eligible": False,
            "equipment": {
                "laptop": "MacBook Air M1",
                "monitor": "Dell 22-inch",
                "phone": "None",
                "accessories": ["Basic keyboard and mouse"]
            },
            "emergency_contact": {
                "name": "Lisa Chen",
                "relationship": "Mother",
                "phone": "+1-555-0308"
            },
            "notes": "Summer intern - CS student from UC Berkeley",
            "tags": ["intern", "temporary", "student", "engineering", "limited_access"],
            "last_updated": (BASE_DT - timedelta(days=2)).isoformat(),
            "data_source": "hr_system",
            "sync_status": "synchronized"
        },
        
        # Part-time employee (additional employee to reach 10+ count)
        {
            "employee_id": "EMP008",
            "slack_id": "U7777777777",
            "email": "iris@company.com",
            "calendar_id": "iris@company.com",
            "google_workspace_id": "iris@company.com",
            "first_name": "Iris",
            "last_name": "Chen",
            "display_name": "Iris Chen",
            "preferred_name": "Iris",
            "title": "Part-time Customer Success Manager",
            "department": "Support",
            "division": "Customer Success",
            "location": "Portland, OR",
            "office": "Remote",
            "floor": None,
            "desk_number": None,
            "phone": "+1-555-0109",
            "mobile": "+1-555-0209",
            "manager_id": "EMP001",
            "manager_email": "alice@company.com",
            "direct_reports": [],
            "skip_level_reports": [],
            "employment_type": "part_time",
            "employee_status": "active",
            "hire_date": (BASE_DT - timedelta(days=90)).strftime("%Y-%m-%d"),
            "termination_date": None,
            "last_working_day": None,
            "timezone": "America/Los_Angeles",
            "work_schedule": {
                "monday": {"start": "09:00", "end": "13:00"},  # 4 hour days
                "tuesday": {"start": "09:00", "end": "13:00"},
                "wednesday": {"start": "09:00", "end": "13:00"},
                "thursday": None,  # Off Thursday
                "friday": {"start": "09:00", "end": "13:00"},
                "saturday": None,
                "sunday": None
            },
            "cost_center": "600-SUPPORT",
            "budget_owner": False,
            "security_clearance": "standard",
            "access_level": "standard",
            "slack_admin": False,
            "calendar_admin": False,
            "drive_admin": False,
            "two_factor_enabled": True,
            "vpn_access": False,
            "remote_work_eligible": True,
            "equipment": {
                "laptop": "MacBook Air M1 2021",
                "monitor": "Personal Device",
                "phone": "Personal Device", 
                "accessories": []
            },
            "emergency_contact": {
                "name": "Paul Chen",
                "relationship": "Spouse",
                "phone": "+1-555-0309"
            },
            "notes": "Part-time customer success - handles onboarding",
            "tags": ["part_time", "customer_success", "onboarding", "remote"],
            "last_updated": (BASE_DT - timedelta(days=1)).isoformat(),
            "data_source": "hr_system",
            "sync_status": "synchronized"
        }
    ]

def get_mock_organizational_chart() -> Dict[str, Any]:
    """Mock organizational chart showing reporting structure."""
    return {
        "alice@company.com": {
            "employee_id": "EMP001",
            "name": "Alice Johnson",
            "title": "Chief Executive Officer",
            "department": "Executive",
            "manager": None,
            "direct_reports": [
                "bob@company.com",
                "charlie@company.com", 
                "eve@company.com"
            ],
            "skip_level_reports": [
                "diana.contractor@company.com",
                "frank@company.com",
                "grace@company.com",
                "henry.intern@company.com"
            ],
            "level": 1
        },
        "bob@company.com": {
            "employee_id": "EMP002",
            "name": "Bob Smith",
            "title": "Senior Software Engineer",
            "department": "Engineering",
            "manager": "alice@company.com",
            "direct_reports": [
                "diana.contractor@company.com",
                "grace@company.com",
                "henry.intern@company.com"
            ],
            "skip_level_reports": [],
            "level": 2
        },
        "charlie@company.com": {
            "employee_id": "EMP003",
            "name": "Charlie Brown",
            "title": "Product Manager",
            "department": "Product",
            "manager": "alice@company.com",
            "direct_reports": [
                "frank@company.com"
            ],
            "skip_level_reports": [],
            "level": 2
        },
        "eve@company.com": {
            "employee_id": "EMP005",
            "name": "Eve Davis",
            "title": "Marketing Manager",
            "department": "Marketing",
            "manager": "alice@company.com",
            "direct_reports": [],
            "skip_level_reports": [],
            "level": 2
        },
        "diana.contractor@company.com": {
            "employee_id": "CNT001", 
            "name": "Diana Wilson",
            "title": "DevOps Contractor",
            "department": "Engineering",
            "manager": "bob@company.com",
            "direct_reports": [],
            "skip_level_reports": [],
            "level": 3
        },
        "frank@company.com": {
            "employee_id": "EMP006",
            "name": "Frank Miller",
            "title": "Junior Product Designer",
            "department": "Product",
            "manager": "charlie@company.com",
            "direct_reports": [],
            "skip_level_reports": [],
            "level": 3
        },
        "grace@company.com": {
            "employee_id": "EMP007",
            "name": "Grace Lee",
            "title": "Data Analyst",
            "department": "Analytics",
            "manager": "bob@company.com",
            "direct_reports": [],
            "skip_level_reports": [],
            "level": 3
        },
        "henry.intern@company.com": {
            "employee_id": "INT001",
            "name": "Henry Chen",
            "title": "Software Engineering Intern",
            "department": "Engineering",
            "manager": "bob@company.com",
            "direct_reports": [],
            "skip_level_reports": [],
            "level": 3
        }
    }

def get_mock_department_structure() -> Dict[str, Any]:
    """Mock department structure with headcounts and budgets."""
    return {
        "Executive": {
            "head": "alice@company.com",
            "employees": 1,
            "budget": 50000,
            "cost_center": "100-EXEC",
            "locations": ["New York, NY"]
        },
        "Engineering": {
            "head": "bob@company.com",
            "employees": 3,  # Bob + Diana + Henry
            "budget": 450000,
            "cost_center": "200-ENG",
            "locations": ["San Francisco, CA", "Chicago, IL", "Seattle, WA"]
        },
        "Product": {
            "head": "charlie@company.com",
            "employees": 2,  # Charlie + Frank
            "budget": 200000,
            "cost_center": "300-PROD",
            "locations": ["London, UK", "Remote"]
        },
        "Marketing": {
            "head": "eve@company.com", 
            "employees": 1,
            "budget": 150000,
            "cost_center": "400-MKT",
            "locations": ["Austin, TX"]
        },
        "Analytics": {
            "head": "bob@company.com",  # Reports to engineering
            "employees": 1,
            "budget": 75000,
            "cost_center": "200-ENG-DATA",
            "locations": ["Seattle, WA"]
        }
    }

def get_mock_employee_changes() -> List[Dict[str, Any]]:
    """Mock employee changes for testing change detection."""
    return [
        {
            "change_type": "new_employee",
            "employee_id": "EMP005",
            "email": "eve@company.com",
            "change_date": (BASE_DT - timedelta(days=5)).strftime("%Y-%m-%d"),
            "change_details": {
                "action": "hired",
                "title": "Marketing Manager",
                "department": "Marketing",
                "start_date": (BASE_DT - timedelta(days=5)).strftime("%Y-%m-%d")
            },
            "changed_by": "hr_system",
            "notes": "New hire in marketing department"
        },
        {
            "change_type": "termination",
            "employee_id": "EMP999",
            "email": "deleted.user@company.com",
            "change_date": (BASE_DT - timedelta(days=30)).strftime("%Y-%m-%d"),
            "change_details": {
                "action": "terminated",
                "reason": "voluntary_resignation",
                "last_working_day": (BASE_DT - timedelta(days=30)).strftime("%Y-%m-%d"),
                "access_revoked": True
            },
            "changed_by": "hr_system",
            "notes": "Employee resigned - all access revoked"
        },
        {
            "change_type": "role_change",
            "employee_id": "EMP002",
            "email": "bob@company.com",
            "change_date": (BASE_DT - timedelta(days=60)).strftime("%Y-%m-%d"),
            "change_details": {
                "action": "promotion",
                "old_title": "Software Engineer",
                "new_title": "Senior Software Engineer",
                "salary_change": True
            },
            "changed_by": "alice@company.com",
            "notes": "Promoted to senior level"
        },
        {
            "change_type": "department_transfer",
            "employee_id": "EMP007",
            "email": "grace@company.com",
            "change_date": (BASE_DT - timedelta(days=10)).strftime("%Y-%m-%d"),
            "change_details": {
                "action": "department_change",
                "old_department": "Engineering",
                "new_department": "Analytics",
                "old_manager": "bob@company.com",
                "new_manager": "bob@company.com"  # Same manager, different cost center
            },
            "changed_by": "hr_system",
            "notes": "Moved to analytics team within engineering"
        },
        {
            "change_type": "access_change",
            "employee_id": "CNT001",
            "email": "diana.contractor@company.com",
            "change_date": (BASE_DT - timedelta(days=7)).strftime("%Y-%m-%d"),
            "change_details": {
                "action": "access_updated",
                "vpn_access": True,
                "security_clearance": "restricted",
                "two_factor_enabled": True
            },
            "changed_by": "it_security",
            "notes": "Updated contractor access permissions"
        }
    ]

def get_mock_id_mappings() -> Dict[str, Any]:
    """Mock ID mappings between different systems."""
    employees = get_mock_employee_roster()
    mappings = {}
    
    for emp in employees:
        email = emp["email"]
        mappings[email] = {
            "email": email,
            "employee_id": emp["employee_id"],
            "slack_id": emp.get("slack_id"),
            "calendar_id": emp.get("calendar_id"),
            "google_workspace_id": emp.get("google_workspace_id"),
            "display_name": emp["display_name"],
            "status": emp["employee_status"],
            "last_updated": emp["last_updated"]
        }
    
    return mappings

def get_mock_sync_errors() -> List[Dict[str, Any]]:
    """Mock synchronization errors for testing error handling."""
    return [
        {
            "error_type": "slack_id_missing",
            "employee_id": "EMP007",
            "email": "grace@company.com",
            "error_message": "Employee exists in HR system but has no Slack account",
            "severity": "warning",
            "resolution": "Create Slack account or mark as Slack-exempt",
            "last_seen": (BASE_DT - timedelta(days=5)).isoformat()
        },
        {
            "error_type": "terminated_user_active",
            "employee_id": "EMP999",
            "email": "deleted.user@company.com",
            "error_message": "Employee marked as terminated but Slack account still active",
            "severity": "high",
            "resolution": "Deactivate Slack account immediately",
            "last_seen": (BASE_DT - timedelta(days=30)).isoformat()
        },
        {
            "error_type": "calendar_access_missing",
            "employee_id": "INT001",
            "email": "henry.intern@company.com", 
            "error_message": "Unable to access calendar - insufficient permissions",
            "severity": "medium",
            "resolution": "Grant calendar read access for intern account",
            "last_seen": (BASE_DT - timedelta(hours=6)).isoformat()
        },
        {
            "error_type": "data_mismatch",
            "employee_id": "EMP003",
            "email": "charlie@company.com",
            "error_message": "Display name differs between HR system and Slack profile",
            "severity": "low",
            "resolution": "Update Slack profile or HR system to match",
            "last_seen": (BASE_DT - timedelta(hours=2)).isoformat()
        }
    ]

# Helper functions
def validate_mock_employee_data():
    """Validate that all mock employee data is well-formed and consistent."""
    try:
        roster = get_mock_employee_roster()
        org_chart = get_mock_organizational_chart()
        departments = get_mock_department_structure()
        
        # Validate JSON serializability
        json.dumps(roster)
        json.dumps(org_chart)
        json.dumps(departments)
        
        # Basic consistency checks
        emails = {emp["email"] for emp in roster if emp["employee_status"] in ["active", "onboarding"]}
        
        for emp in roster:
            # Required fields
            assert "employee_id" in emp
            assert "email" in emp
            assert "employee_status" in emp
            
            # Manager relationship consistency
            if emp.get("manager_email") and emp["employee_status"] == "active":
                assert emp["manager_email"] in emails or emp["manager_email"] == "alice@company.com"
        
        # Org chart consistency
        for email, info in org_chart.items():
            if email in emails:
                emp = next(e for e in roster if e["email"] == email)
                assert emp["employee_id"] == info["employee_id"]
        
        return True
    except Exception as e:
        print(f"Employee mock data validation failed: {e}")
        return False

def get_mock_collection_result() -> Dict[str, Any]:
    """Mock result from employee collector matching expected format."""
    roster = get_mock_employee_roster()
    active_employees = [e for e in roster if e["employee_status"] in ["active", "onboarding"]]
    
    return {
        "discovered": {
            "total_employees": len(roster),
            "active_employees": len(active_employees),
            "departments": len(get_mock_department_structure()),
            "contractors": len([e for e in roster if e["employment_type"] == "contractor"]),
            "interns": len([e for e in roster if e["employment_type"] == "intern"])
        },
        "collected": {
            "employees": len(active_employees),
            "complete_mappings": len([e for e in active_employees if e.get("slack_id") and e.get("calendar_id")]),
            "missing_slack": len([e for e in active_employees if not e.get("slack_id")]),
            "missing_calendar": len([e for e in active_employees if not e.get("calendar_id")]),
            "org_chart_relationships": len(get_mock_organizational_chart())
        },
        "roster": roster,
        "organizational_chart": get_mock_organizational_chart(),
        "department_structure": get_mock_department_structure(),
        "id_mappings": get_mock_id_mappings(),
        "changes": get_mock_employee_changes(),
        "sync_errors": get_mock_sync_errors(),
        "metadata": {
            "collection_time": BASE_DT.isoformat(),
            "data_sources": ["hr_system", "contractor_system"],
            "sync_status": "synchronized"
        }
    }

# Ensure data is valid on import
if __name__ == "__main__":
    assert validate_mock_employee_data(), "Employee mock data validation failed"
    print("All Employee mock data validated successfully!")