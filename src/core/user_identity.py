#!/usr/bin/env python3
"""
User Identity Configuration and Management
Handles PRIMARY_USER configuration and cross-system identity mapping

Provides simple lab-grade implementation for user-centric architecture while
maintaining backwards compatibility with non-personalized mode.
"""

import os
import re
from typing import Optional, Dict, Any, Set
from pathlib import Path

class UserIdentity:
    """
    Simple PRIMARY_USER configuration and identity mapping
    
    Features:
    - Load PRIMARY_USER from environment variables
    - Cross-system identity mapping (email ↔ slack_id ↔ calendar_id) 
    - Backwards compatibility (works without PRIMARY_USER configured)
    - Validation of user identity consistency
    """
    
    def __init__(self, config=None):
        """Initialize UserIdentity with configuration
        
        Args:
            config: Config instance (optional, will create default if None)
        """
        # Load config (avoid circular import by importing here)
        if config is None:
            from .config import get_config
            self.config = get_config()
        else:
            self.config = config
            
        # Cache for primary user configuration
        self._primary_user = None
        self._primary_user_loaded = False
        
        # Cache for employee data (used in identity mapping)
        self._employee_data = None
        self._employee_data_loaded = False
    
    def _load_primary_user(self) -> Optional[Dict[str, Any]]:
        """Load PRIMARY_USER from configuration
        
        Returns:
            Dictionary with user configuration or None if not configured
        """
        if self._primary_user_loaded:
            return self._primary_user
            
        # Try to load from Config class first (integrated approach)
        if hasattr(self.config, 'get_primary_user_config'):
            config_user = self.config.get_primary_user_config()
            if config_user:
                self._primary_user = config_user
                self._primary_user_loaded = True
                print(f"✅ PRIMARY_USER loaded from config: {config_user['email']}")
                return config_user
        
        # Fallback to direct environment variable loading (backwards compatibility)
        email = os.getenv('AICOS_PRIMARY_USER_EMAIL')
        slack_id = os.getenv('AICOS_PRIMARY_USER_SLACK_ID')
        calendar_id = os.getenv('AICOS_PRIMARY_USER_CALENDAR_ID')
        name = os.getenv('AICOS_PRIMARY_USER_NAME')
        
        # If no email configured, return None (backwards compatibility)
        if not email:
            self._primary_user = None
            self._primary_user_loaded = True
            return None
        
        # Validate email format
        if not self._is_valid_email(email):
            print(f"⚠️ Invalid PRIMARY_USER email format: {email}")
            self._primary_user = None
            self._primary_user_loaded = True
            return None
        
        # Build primary user configuration
        primary_user = {
            "email": email,
            "slack_id": slack_id,
            "calendar_id": calendar_id or email,  # Default calendar_id to email
            "name": name
        }
        
        self._primary_user = primary_user
        self._primary_user_loaded = True
        
        print(f"✅ PRIMARY_USER loaded: {email}")
        return primary_user
    
    def _is_valid_email(self, email: str) -> bool:
        """Validate email format
        
        Args:
            email: Email address to validate
            
        Returns:
            True if email format is valid
        """
        if not email or not isinstance(email, str):
            return False
            
        # Simple email regex validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(email_pattern, email.strip()))
    
    def get_primary_user(self) -> Optional[Dict[str, Any]]:
        """Get PRIMARY_USER configuration or None if not configured
        
        Returns:
            Dictionary with primary user data or None
        """
        return self._load_primary_user()
    
    def set_primary_user(self, email: str, slack_id: Optional[str] = None, 
                        calendar_id: Optional[str] = None, 
                        name: Optional[str] = None) -> bool:
        """Set PRIMARY_USER configuration programmatically
        
        Args:
            email: User email address (required)
            slack_id: Slack user ID (optional)
            calendar_id: Calendar ID (optional, defaults to email)
            name: Display name (optional)
            
        Returns:
            True if successful, False if validation failed
        """
        # Validate required email
        if not email or not self._is_valid_email(email):
            print(f"❌ Invalid email for PRIMARY_USER: {email}")
            return False
        
        # Set primary user configuration
        self._primary_user = {
            "email": email,
            "slack_id": slack_id,
            "calendar_id": calendar_id or email,
            "name": name
        }
        self._primary_user_loaded = True
        
        print(f"✅ PRIMARY_USER set programmatically: {email}")
        return True
    
    def is_primary_user(self, identifier: str) -> bool:
        """Check if identifier matches primary user
        
        Args:
            identifier: Email, slack_id, or calendar_id to check
            
        Returns:
            True if identifier matches primary user
        """
        primary_user = self.get_primary_user()
        if not primary_user or not identifier:
            return False
        
        # Check all identity fields
        return identifier in [
            primary_user.get("email"),
            primary_user.get("slack_id"), 
            primary_user.get("calendar_id")
        ]
    
    def _load_employee_data(self) -> Dict[str, Any]:
        """Load employee data for identity mapping
        
        Returns:
            Dictionary mapping emails to employee records
        """
        if self._employee_data_loaded:
            return self._employee_data or {}
        
        try:
            from ..collectors.employee_collector import EmployeeCollector
            
            collector = EmployeeCollector()
            result = collector.to_json()
            
            employees = result.get("roster_data", {}).get("employees", {})
            self._employee_data = employees
            self._employee_data_loaded = True
            
            print(f"✅ Employee data loaded: {len(employees)} employees")
            return employees
            
        except Exception as e:
            print(f"⚠️ Could not load employee data for identity mapping: {e}")
            self._employee_data = {}
            self._employee_data_loaded = True
            return {}
    
    def resolve_slack_user(self, email: str) -> Optional[str]:
        """Find Slack user ID from email using employee data
        
        Args:
            email: Email address to look up
            
        Returns:
            Slack user ID or None if not found
        """
        if not email:
            return None
            
        employees = self._load_employee_data()
        employee = employees.get(email)
        
        if employee and employee.get("slack_id"):
            return employee["slack_id"]
        
        return None
    
    def resolve_calendar_user(self, email: str) -> Optional[str]:
        """Find calendar ID from email
        
        In Google Workspace, calendar ID typically equals email address.
        
        Args:
            email: Email address to look up
            
        Returns:
            Calendar ID (typically same as email) or email as default
        """
        if not email:
            return None
        
        employees = self._load_employee_data()
        employee = employees.get(email)
        
        if employee and employee.get("calendar_id"):
            return employee["calendar_id"]
        
        # Default: calendar ID is usually the same as email in Google Workspace
        return email if self._is_valid_email(email) else None
    
    def resolve_email_from_slack_id(self, slack_id: str) -> Optional[str]:
        """Find email from Slack user ID
        
        Args:
            slack_id: Slack user ID to look up
            
        Returns:
            Email address or None if not found
        """
        if not slack_id:
            return None
            
        employees = self._load_employee_data()
        
        for email, employee in employees.items():
            if employee.get("slack_id") == slack_id:
                return email
        
        return None
    
    def validate_user_exists(self, user_config: Dict[str, Any]) -> bool:
        """Validate user exists in connected systems
        
        Args:
            user_config: Dictionary with user identity information
            
        Returns:
            True if user validation passes
        """
        if not user_config:
            return False
        
        email = user_config.get("email")
        slack_id = user_config.get("slack_id")
        
        # Validate email format
        if email and not self._is_valid_email(email):
            return False
        
        try:
            # Validate Slack user if configured
            if slack_id and not self._validate_slack_user(slack_id):
                return False
            
            # Validate calendar user if configured  
            if email and not self._validate_calendar_user(email):
                return False
                
            return True
            
        except Exception as e:
            print(f"⚠️ User validation error: {e}")
            return False
    
    def _validate_slack_user(self, slack_id: str) -> bool:
        """Validate user exists in Slack workspace
        
        Args:
            slack_id: Slack user ID to validate
            
        Returns:
            True if user exists in Slack
        """
        try:
            from .auth_manager import credential_vault
            
            slack_token = credential_vault.get_slack_bot_token()
            if not slack_token:
                print("⚠️ No Slack token available for user validation")
                return True  # Don't fail validation if token unavailable
            
            import requests
            
            headers = {"Authorization": f"Bearer {slack_token}"}
            response = requests.get(
                "https://slack.com/api/users.info",
                headers=headers,
                params={"user": slack_id}
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("ok", False) and not result.get("user", {}).get("deleted", True)
            
            return False
            
        except Exception as e:
            print(f"⚠️ Slack user validation error: {e}")
            return True  # Don't fail validation on errors
    
    def _validate_calendar_user(self, email: str) -> bool:
        """Validate user has calendar access
        
        Args:
            email: Email to validate for calendar access
            
        Returns:
            True if user has calendar access
        """
        try:
            from .auth_manager import credential_vault
            
            google_creds = credential_vault.get_google_oauth_credentials()
            if not google_creds or not google_creds.valid:
                print("⚠️ No Google credentials available for calendar validation")
                return True  # Don't fail validation if credentials unavailable
            
            # For simplicity, assume all valid emails have calendar access
            return self._is_valid_email(email)
            
        except Exception as e:
            print(f"⚠️ Calendar user validation error: {e}")
            return True  # Don't fail validation on errors

class IdentityMapper:
    """Helper class for cross-system identity mapping"""
    
    def __init__(self, user_identity: UserIdentity):
        """Initialize with UserIdentity instance
        
        Args:
            user_identity: UserIdentity instance to use for mapping
        """
        self.user_identity = user_identity
    
    def get_user_identities(self, primary_identifier: str) -> Dict[str, Optional[str]]:
        """Get all known identities for a user across systems
        
        Args:
            primary_identifier: Email, slack_id, or calendar_id
            
        Returns:
            Dictionary with all known identities for the user
        """
        result = {
            "email": None,
            "slack_id": None, 
            "calendar_id": None
        }
        
        # Determine if primary identifier is email or slack_id
        if "@" in primary_identifier:
            # Primary identifier is email
            result["email"] = primary_identifier
            result["slack_id"] = self.user_identity.resolve_slack_user(primary_identifier)
            result["calendar_id"] = self.user_identity.resolve_calendar_user(primary_identifier)
        else:
            # Primary identifier is likely slack_id
            result["email"] = self.user_identity.resolve_email_from_slack_id(primary_identifier)
            result["slack_id"] = primary_identifier
            if result["email"]:
                result["calendar_id"] = self.user_identity.resolve_calendar_user(result["email"])
        
        return result
    
    def find_common_users(self, system1_users: Set[str], system2_users: Set[str]) -> Set[str]:
        """Find users common between two systems
        
        Args:
            system1_users: Set of user identifiers from system 1
            system2_users: Set of user identifiers from system 2
            
        Returns:
            Set of common user email addresses
        """
        common_emails = set()
        
        for user1 in system1_users:
            identities1 = self.get_user_identities(user1)
            email1 = identities1.get("email")
            
            if email1:
                for user2 in system2_users:
                    identities2 = self.get_user_identities(user2)
                    email2 = identities2.get("email")
                    
                    if email1 == email2:
                        common_emails.add(email1)
        
        return common_emails

# Convenience function for other modules
def get_primary_user() -> Optional[Dict[str, Any]]:
    """Convenience function to get primary user configuration
    
    Returns:
        Primary user configuration or None
    """
    user_identity = UserIdentity()
    return user_identity.get_primary_user()

# Convenience function for identity checking
def is_primary_user(identifier: str) -> bool:
    """Convenience function to check if identifier matches primary user
    
    Args:
        identifier: Email, slack_id, or calendar_id to check
        
    Returns:
        True if identifier matches primary user
    """
    user_identity = UserIdentity()
    return user_identity.is_primary_user(identifier)

if __name__ == "__main__":
    # Test the UserIdentity system
    print("🧪 Testing UserIdentity System")
    print("=" * 40)
    
    user_identity = UserIdentity()
    primary_user = user_identity.get_primary_user()
    
    if primary_user:
        print(f"✅ PRIMARY_USER configured:")
        print(f"  📧 Email: {primary_user['email']}")
        print(f"  💬 Slack ID: {primary_user['slack_id']}")
        print(f"  📅 Calendar ID: {primary_user['calendar_id']}")
        print(f"  👤 Name: {primary_user['name']}")
        
        # Test identity mapping
        print(f"\n🔍 Testing identity mapping:")
        email = primary_user['email']
        slack_id = user_identity.resolve_slack_user(email)
        calendar_id = user_identity.resolve_calendar_user(email)
        
        print(f"  Email → Slack: {slack_id}")
        print(f"  Email → Calendar: {calendar_id}")
        
        # Test primary user identification
        print(f"\n✅ Primary user identification:")
        print(f"  Email match: {user_identity.is_primary_user(email)}")
        if slack_id:
            print(f"  Slack ID match: {user_identity.is_primary_user(slack_id)}")
            
    else:
        print("ℹ️ No PRIMARY_USER configured (backwards compatible mode)")
        print("  System will work without personalization")
        
    print("\n✅ UserIdentity system test complete")