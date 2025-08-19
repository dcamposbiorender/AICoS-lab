#!/usr/bin/env python3
"""
Google OAuth Setup Script
Creates proper Google OAuth credentials for Calendar and Drive APIs

Usage:
    python tools/setup_google_oauth.py
    
This script will:
1. Use your Google OAuth client credentials
2. Open browser for authorization
3. Generate token.pickle file
4. Store credentials for auth_manager
"""

import json
import pickle
import sys
from pathlib import Path
from typing import Dict, Any

# Add project paths
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
except ImportError as e:
    print(f"❌ Missing Google API dependencies: {e}")
    print("Install with: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")
    sys.exit(1)


class GoogleOAuthSetup:
    """
    Google OAuth credential setup for AI Chief of Staff
    """
    
    def __init__(self):
        # Use current working directory instead of hardcoded path
        self.project_root = Path.cwd()
        self.auth_dir = self.project_root / "data" / "auth"
        self.auth_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"Project root: {self.project_root}")
        print(f"Auth directory: {self.auth_dir}")
        
        # Required scopes for Calendar and Drive
        self.SCOPES = [
            'https://www.googleapis.com/auth/calendar.readonly',
            'https://www.googleapis.com/auth/calendar.events.readonly',
            'https://www.googleapis.com/auth/drive.metadata.readonly',
            'https://www.googleapis.com/auth/drive.readonly',
        ]
        
        print("🔐 Google OAuth Setup for AI Chief of Staff")
        print("=" * 50)
        
    def create_credentials_json(self) -> bool:
        """Create credentials.json from your OAuth client info"""
        credentials_data = {
            "installed": {
                "client_id": "YOUR_CLIENT_ID_HERE.apps.googleusercontent.com",
                "project_id": "your-project-id",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_secret": "YOUR_CLIENT_SECRET_HERE",
                "redirect_uris": ["http://localhost"]
            }
        }
        
        credentials_file = self.auth_dir / "credentials.json"
        
        # Check if credentials already exist
        if credentials_file.exists():
            print(f"✅ Found existing credentials file: {credentials_file}")
            try:
                with open(credentials_file, 'r') as f:
                    existing_creds = json.load(f)
                    if existing_creds.get('installed', {}).get('client_id') != 'YOUR_CLIENT_ID_HERE.apps.googleusercontent.com':
                        return True  # Real credentials exist
            except Exception as e:
                print(f"⚠️ Error reading existing credentials: {e}")
        
        print(f"📝 Creating credentials template at: {credentials_file}")
        print()
        print("🚨 IMPORTANT: You need to replace the template values with your actual OAuth credentials!")
        print()
        print("To get your OAuth credentials:")
        print("1. Go to https://console.cloud.google.com/")
        print("2. Create a new project or select existing")
        print("3. Enable Calendar API and Drive API")
        print("4. Go to 'Credentials' → 'Create Credentials' → 'OAuth 2.0 Client IDs'")
        print("5. Choose 'Desktop application'")
        print("6. Download the JSON file")
        print("7. Replace the values in the template below")
        print()
        
        with open(credentials_file, 'w') as f:
            json.dump(credentials_data, f, indent=2)
            
        print(f"Template created. Edit this file with your real credentials: {credentials_file}")
        return False
    
    def setup_oauth_flow(self) -> bool:
        """Set up OAuth flow and generate token.pickle"""
        credentials_file = self.auth_dir / "credentials.json"
        token_file = self.auth_dir / "token.pickle"
        
        if not credentials_file.exists():
            print(f"❌ Credentials file not found: {credentials_file}")
            return False
            
        creds = None
        
        # Load existing token if available
        if token_file.exists():
            try:
                with open(token_file, 'rb') as token:
                    creds = pickle.load(token)
                print("✅ Found existing token.pickle")
            except Exception as e:
                print(f"⚠️ Error loading existing token: {e}")
                
        # If there are no (valid) credentials available, let the user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    print("🔄 Refreshing expired token...")
                    creds.refresh(Request())
                    print("✅ Token refreshed successfully")
                except Exception as e:
                    print(f"⚠️ Token refresh failed: {e}")
                    creds = None
                    
            if not creds:
                print("🌐 Starting OAuth flow...")
                print("Your browser will open for authorization")
                
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        credentials_file, self.SCOPES)
                    creds = flow.run_local_server(port=0)
                    print("✅ Authorization successful!")
                except Exception as e:
                    print(f"❌ OAuth flow failed: {e}")
                    return False
            
            # Save the credentials for the next run
            try:
                with open(token_file, 'wb') as token:
                    pickle.dump(creds, token)
                print(f"✅ Credentials saved to: {token_file}")
            except Exception as e:
                print(f"❌ Failed to save token: {e}")
                return False
                
        return True
    
    def test_credentials(self) -> bool:
        """Test that credentials work with Calendar and Drive APIs"""
        token_file = self.auth_dir / "token.pickle"
        
        if not token_file.exists():
            print(f"❌ No token.pickle file found at: {token_file}")
            # Check if it exists in the correct location from your ls output
            print(f"Checking auth directory: {self.auth_dir}")
            print(f"Files in auth dir: {list(self.auth_dir.glob('*'))}")
            return False
            
        try:
            with open(token_file, 'rb') as token:
                creds = pickle.load(token)
                
            # Test Calendar API
            print("🧪 Testing Calendar API access...")
            calendar_service = build('calendar', 'v3', credentials=creds)
            calendar_list = calendar_service.calendarList().list(maxResults=5).execute()
            calendars = calendar_list.get('items', [])
            print(f"✅ Calendar API working - found {len(calendars)} calendars")
            
            # Test Drive API
            print("🧪 Testing Drive API access...")
            drive_service = build('drive', 'v3', credentials=creds)
            results = drive_service.files().list(pageSize=5, fields="files(id, name)").execute()
            files = results.get('files', [])
            print(f"✅ Drive API working - found {len(files)} files")
            
            return True
            
        except Exception as e:
            print(f"❌ API test failed: {e}")
            return False
    
    def create_auth_config(self) -> bool:
        """Create sync_config.json for auth_manager compatibility"""
        token_file = self.auth_dir / "token.pickle"
        sync_config_file = self.auth_dir / "sync_config.json"
        
        if not token_file.exists():
            print("❌ token.pickle not found")
            return False
            
        # Create minimal sync config for auth_manager
        sync_config = {
            "google_oauth_setup": True,
            "credentials_file": str(token_file),
            "scopes": self.SCOPES,
            "created_by": "setup_google_oauth.py",
            "created_at": "2025-08-15"
        }
        
        with open(sync_config_file, 'w') as f:
            json.dump(sync_config, f, indent=2)
            
        print(f"✅ Created sync config: {sync_config_file}")
        return True
    
    def run_setup(self) -> bool:
        """Run complete OAuth setup process"""
        print("Starting Google OAuth setup...\n")
        
        # Step 1: Create credentials template
        if not self.create_credentials_json():
            print("\n❌ Setup incomplete - please update credentials.json with real values")
            return False
            
        # Step 2: Run OAuth flow
        if not self.setup_oauth_flow():
            print("\n❌ OAuth flow failed")
            return False
            
        # Step 3: Test credentials
        if not self.test_credentials():
            print("\n❌ Credential testing failed")
            return False
            
        # Step 4: Create auth config
        if not self.create_auth_config():
            print("\n❌ Auth config creation failed")
            return False
            
        print("\n🎉 Google OAuth setup complete!")
        print(f"📁 Credentials stored in: {self.auth_dir}")
        print("\nYou can now run the test harness:")
        print("python tests/integration/test_collector_harness.py --collector calendar --days 7")
        
        return True


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Set up Google OAuth for AI Chief of Staff",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tools/setup_google_oauth.py
  
This script will guide you through setting up Google OAuth credentials
for Calendar and Drive API access.
        """
    )
    
    parser.add_argument(
        "--test-only",
        action="store_true", 
        help="Only test existing credentials without running setup"
    )
    
    args = parser.parse_args()
    
    setup = GoogleOAuthSetup()
    
    if args.test_only:
        print("🧪 Testing existing credentials only...")
        success = setup.test_credentials()
    else:
        success = setup.run_setup()
    
    if success:
        print("✅ Setup completed successfully")
        sys.exit(0)
    else:
        print("❌ Setup failed")
        sys.exit(1)


if __name__ == "__main__":
    main()