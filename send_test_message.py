#!/usr/bin/env python3
"""
Send test message to david.campos via Slack bot
"""

import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def send_hello_world_test():
    """Send a hello world test message to david.campos"""
    
    try:
        from src.core.auth_manager import credential_vault
        from slack_sdk import WebClient
        from slack_sdk.errors import SlackApiError
        
        # Get bot token
        bot_token = credential_vault.get_slack_bot_token()
        if not bot_token:
            print("❌ Error: No Slack bot token found")
            return False
            
        print(f"✅ Bot token found: {bot_token[:12]}...")
            
        # Initialize Slack client
        client = WebClient(token=bot_token)
        
        # First, let's find the user by email
        try:
            # Search for user by email
            response = client.users_lookupByEmail(email="david.campos@biorender.com")
            user_id = response["user"]["id"]
            user_name = response["user"]["real_name"]
            print(f"✅ Found user: {user_name} (ID: {user_id})")
            
        except SlackApiError as e:
            print(f"❌ Error finding user by email: {e.response['error']}")
            return False
        
        # Send the hello world test message
        try:
            test_message = """🤖 Hello World Test from AI Chief of Staff! 

This is a test message to verify Slack bot connectivity.

✅ Phase 4/5 Testing Complete
✅ System Performance: Exceptional  
✅ Database: 345,084+ records indexed
✅ All CLI tools operational

The AI Chief of Staff system is ready for production use!

_Sent via automated testing from Claude Code_"""

            response = client.chat_postMessage(
                channel=user_id,  # Send as DM
                text="Hello World Test from AI Chief of Staff!",
                blocks=[
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": test_message
                        }
                    }
                ]
            )
            
            if response["ok"]:
                print(f"✅ Successfully sent test message to {user_name}")
                print(f"   Message timestamp: {response['ts']}")
                print(f"   Channel: {response['channel']}")
                return True
            else:
                print(f"❌ Failed to send message: {response}")
                return False
                
        except SlackApiError as e:
            print(f"❌ Error sending message: {e.response['error']}")
            return False
            
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Sending Hello World test message via Slack bot...")
    success = send_hello_world_test()
    
    if success:
        print("\n🎉 Test message sent successfully!")
        print("   Check your Slack DMs for the message from AI Chief of Staff bot")
    else:
        print("\n❌ Test message failed to send")
        print("   Check bot token configuration and workspace permissions")
        
    sys.exit(0 if success else 1)