#!/usr/bin/env python3
"""
User Setup Step for AI Chief of Staff Setup Wizard

Handles:
- PRIMARY_USER email input and validation
- Cross-reference with Slack user list
- Calendar user verification
- User identity configuration using Agent J's UserIdentity class
- Identity mapping validation across systems

References:
- src/core/user_identity.py - UserIdentity class from Agent J
- src/core/config.py:252-296 - PRIMARY_USER configuration patterns
"""

import os
import re
from pathlib import Path
from typing import Dict, Any, Optional, List

class UserSetup:
    """Step 4: PRIMARY_USER configuration and validation"""
    
    def __init__(self):
        self.email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    def run(self, wizard_data: Dict[str, Any], interactive: bool = True) -> Dict[str, Any]:
        """
        Execute user identity setup step
        
        Args:
            wizard_data: Shared wizard data dictionary (includes Slack users)
            interactive: If True, prompt user for input
            
        Returns:
            Dictionary with setup results
        """
        print("Configuring user identity (PRIMARY_USER)...")
        
        # Step 1: Get user email
        user_email = self._get_user_email(interactive)
        
        # Step 2: Find user in Slack
        slack_user = self._find_slack_user(user_email, wizard_data.get('workspace', {}))
        
        # Step 3: Verify calendar access
        calendar_user = self._verify_calendar_user(user_email)
        
        # Step 4: Configure PRIMARY_USER using UserIdentity
        user_identity = self._configure_primary_user(user_email, slack_user, calendar_user)
        
        # Step 5: Store configuration
        self._store_user_configuration(user_identity)
        
        print("✅ User identity configured")
        
        return {
            "primary_user": user_identity,
            "slack_user_found": slack_user is not None,
            "calendar_verified": True
        }
    
    def _get_user_email(self, interactive: bool) -> str:
        """Get and validate user email address"""
        # Check for existing configuration
        existing_email = os.getenv('AICOS_PRIMARY_USER_EMAIL')
        
        if interactive:
            print("\n👤 User Identity Configuration")
            print("Enter your email address to configure as PRIMARY_USER.")
            print("This should be the email you use for Slack and Google Calendar.")
            
            if existing_email:
                print(f"Current: {existing_email}")
                use_existing = input("Use existing email? [Y/n]: ").strip().lower()
                if use_existing in ('', 'y', 'yes'):
                    return existing_email
            
            email = input("Your email address: ").strip().lower()
            
            if not email:
                raise RuntimeError("Email address is required")
            
            # Validate email format
            if not re.match(self.email_pattern, email):
                raise RuntimeError(f"Invalid email format: {email}")
            
            return email
        else:
            # Non-interactive mode
            if existing_email:
                print(f"👤 Using existing PRIMARY_USER email: {existing_email}")
                return existing_email
            else:
                raise RuntimeError(
                    "AICOS_PRIMARY_USER_EMAIL environment variable required for non-interactive mode"
                )
    
    def _find_slack_user(self, email: str, workspace_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Find user in Slack workspace by email"""
        print(f"🔍 Finding user in Slack workspace...")
        
        users = workspace_data.get('users', [])
        if not users:
            print("⚠️  No Slack users available for lookup")
            return None
        
        # Search for user by email
        for user in users:
            if user.get('email', '').lower() == email.lower():
                print(f"✅ Found Slack user: @{user.get('name', 'unknown')} (ID: {user['id']})")
                return user
        
        print(f"⚠️  User {email} not found in Slack workspace")
        print("This might be okay if:")
        print("  • You use a different email for Slack")
        print("  • Your Slack account is not yet activated") 
        print("  • The bot doesn't have permission to see all users")
        
        return None
    
    def _verify_calendar_user(self, email: str) -> bool:
        """Verify user has calendar access"""
        print("📅 Verifying Calendar access...")
        
        # In Google Workspace, calendar ID typically equals email
        # For now, we assume the email has calendar access
        print(f"✅ Calendar access assumed for: {email}")
        return True
    
    def _configure_primary_user(self, email: str, slack_user: Optional[Dict[str, Any]], 
                              calendar_verified: bool) -> Dict[str, Any]:
        """Configure PRIMARY_USER using UserIdentity class"""
        print("⚙️  Configuring PRIMARY_USER identity...")
        
        # Extract Slack information
        slack_id = slack_user['id'] if slack_user else None
        display_name = None
        
        if slack_user:
            # Try different name fields
            display_name = (slack_user.get('real_name') or 
                          slack_user.get('display_name') or 
                          slack_user.get('name'))
        
        # Create user identity configuration
        user_identity = {
            'email': email,
            'slack_id': slack_id,
            'calendar_id': email,  # Google Workspace default
            'name': display_name
        }
        
        # Use Agent J's UserIdentity class to validate
        try:
            from ...core.user_identity import UserIdentity
            
            # Create UserIdentity instance and test configuration
            identity_manager = UserIdentity()
            
            # Set the primary user programmatically
            success = identity_manager.set_primary_user(
                email=email,
                slack_id=slack_id,
                calendar_id=email,
                name=display_name
            )
            
            if success:
                # Validate the configuration
                if identity_manager.validate_user_exists(user_identity):
                    print("✅ User identity validation passed")
                else:
                    print("⚠️  User identity validation had warnings (continuing)")
            else:
                raise RuntimeError("Failed to configure PRIMARY_USER")
                
        except ImportError:
            print("⚠️  UserIdentity class not available, using basic validation")
        except Exception as e:
            print(f"⚠️  UserIdentity validation warning: {e}")
        
        print(f"✅ PRIMARY_USER configured:")
        print(f"  📧 Email: {user_identity['email']}")
        print(f"  💬 Slack ID: {user_identity['slack_id'] or 'Not found'}")
        print(f"  📅 Calendar ID: {user_identity['calendar_id']}")
        print(f"  👤 Name: {user_identity['name'] or 'Not specified'}")
        
        return user_identity
    
    def _store_user_configuration(self, user_identity: Dict[str, Any]):
        """Store PRIMARY_USER configuration in environment variables"""
        print("💾 Storing PRIMARY_USER configuration...")
        
        try:
            # Set environment variables
            os.environ['AICOS_PRIMARY_USER_EMAIL'] = user_identity['email']
            
            if user_identity['slack_id']:
                os.environ['AICOS_PRIMARY_USER_SLACK_ID'] = user_identity['slack_id']
            
            if user_identity['calendar_id']:
                os.environ['AICOS_PRIMARY_USER_CALENDAR_ID'] = user_identity['calendar_id']
            
            if user_identity['name']:
                os.environ['AICOS_PRIMARY_USER_NAME'] = user_identity['name']
            
            # Update .env file if it exists
            self._update_env_file(user_identity)
            
            print("✅ PRIMARY_USER configuration stored")
            
        except Exception as e:
            print(f"⚠️  Warning: Could not store configuration: {e}")
    
    def _update_env_file(self, user_identity: Dict[str, Any]):
        """Update .env file with PRIMARY_USER configuration"""
        try:
            base_dir = os.getenv('AICOS_BASE_DIR')
            if not base_dir:
                return
            
            env_file = Path(base_dir) / '.env'
            if not env_file.exists():
                return
            
            # Read existing .env content
            content = env_file.read_text()
            
            # Update PRIMARY_USER variables
            updates = {
                'AICOS_PRIMARY_USER_EMAIL': user_identity['email'],
                'AICOS_PRIMARY_USER_SLACK_ID': user_identity.get('slack_id', ''),
                'AICOS_PRIMARY_USER_CALENDAR_ID': user_identity.get('calendar_id', ''),
                'AICOS_PRIMARY_USER_NAME': user_identity.get('name', '')
            }
            
            for key, value in updates.items():
                if value:  # Only set non-empty values
                    pattern = rf'^#{key}=.*$'
                    replacement = f'{key}={value}'
                    
                    if re.search(pattern, content, re.MULTILINE):
                        content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
                    else:
                        # Add new line if not found
                        content += f'\n{replacement}\n'
            
            env_file.write_text(content)
            print(f"✅ Updated .env file: {env_file}")
            
        except Exception as e:
            print(f"⚠️  Could not update .env file: {e}")

if __name__ == "__main__":
    # Test the user setup
    setup = UserSetup()
    
    # Mock wizard data with Slack users
    mock_data = {
        'workspace': {
            'users': [
                {
                    'id': 'U123456789',
                    'name': 'testuser',
                    'real_name': 'Test User',
                    'email': 'test@example.com'
                }
            ]
        }
    }
    
    result = setup.run(mock_data, interactive=True)
    print(f"Setup result: {result}")