#!/usr/bin/env python3
"""
AI Chief of Staff Setup - Simple Entry Point

This script provides a simple entry point to run the AI Chief of Staff
setup wizard. It handles the environment setup and provides clear guidance
for getting started with the system.

Usage:
    python tools/setup.py                    # Interactive setup
    python tools/setup.py --non-interactive  # Automated setup
    python tools/setup.py --help            # Show help

The setup wizard will guide you through:
1. Environment configuration (directories, database)
2. Slack API setup and validation
3. Google services (Calendar + Drive) configuration
4. User identity setup (PRIMARY_USER)
5. System validation and testing
6. Initial data collection and indexing
"""

import sys
import os
import argparse
from pathlib import Path

# Add src directory to Python path
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

def main():
    """Main entry point for setup wizard"""
    parser = argparse.ArgumentParser(
        description="AI Chief of Staff Setup Wizard",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tools/setup.py                    # Interactive setup with prompts
  python tools/setup.py --non-interactive  # Automated setup using environment variables
  python tools/setup.py --version          # Show version information

Environment Variables (for non-interactive mode):
  AICOS_BASE_DIR                    # Base directory for data storage
  SLACK_BOT_TOKEN                   # Slack bot token (xoxb-...)
  GOOGLE_CLIENT_ID                  # Google OAuth client ID
  GOOGLE_CLIENT_SECRET              # Google OAuth client secret
  AICOS_PRIMARY_USER_EMAIL          # Primary user email address
  AICOS_PRIMARY_USER_SLACK_ID       # Primary user Slack ID (optional)
  AICOS_PRIMARY_USER_NAME           # Primary user display name (optional)

For more information, see README.md
        """
    )
    
    parser.add_argument(
        "--non-interactive", 
        action="store_true",
        help="Run setup in non-interactive mode using environment variables"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="AI Chief of Staff Setup Wizard v1.0.0"
    )
    
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run setup in test mode (for development/testing)"
    )
    
    args = parser.parse_args()
    
    # Show welcome message
    print_welcome()
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Set test mode if requested
    if args.test:
        os.environ['AICOS_TEST_MODE'] = 'true'
        print("🧪 Running in TEST MODE")
    
    try:
        # Import and run the setup wizard
        from cli.setup_wizard import run_setup_wizard
        
        interactive = not args.non_interactive
        
        print(f"🚀 Starting setup wizard (interactive={interactive})...")
        
        result = run_setup_wizard(interactive=interactive)
        
        if result.success:
            print_success_message(result)
            sys.exit(0)
        else:
            print_error_message(result)
            sys.exit(1)
            
    except ImportError as e:
        print(f"❌ Setup wizard import failed: {e}")
        print("Make sure you're running from the project root directory.")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Setup interrupted by user")
        print("You can resume setup by running this script again.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        print("Please check the error message and try again.")
        sys.exit(1)

def print_welcome():
    """Print welcome message"""
    print("=" * 60)
    print("🤖 AI Chief of Staff - Setup Wizard")
    print("=" * 60)
    print("Welcome! This wizard will help you set up your AI Chief of Staff.")
    print("The setup process takes about 5 minutes and will configure:")
    print("  • Environment and data directories")
    print("  • Slack API integration")
    print("  • Google Calendar and Drive APIs")
    print("  • Your user identity and preferences")
    print("  • Initial data collection and search indexing")
    print()

def check_python_version():
    """Check if Python version meets requirements"""
    import sys
    
    required_version = (3, 10)
    current_version = sys.version_info[:2]
    
    if current_version < required_version:
        print(f"❌ Python {required_version[0]}.{required_version[1]}+ required")
        print(f"   Current version: {current_version[0]}.{current_version[1]}")
        print("   Please upgrade Python and try again.")
        return False
    
    print(f"✅ Python {current_version[0]}.{current_version[1]} detected")
    return True

def print_success_message(result):
    """Print success message with next steps"""
    print("\n" + "=" * 60)
    print("🎉 Setup Complete!")
    print("=" * 60)
    print("Your AI Chief of Staff is now ready to use!")
    print()
    
    # Show setup summary
    setup_data = result.setup_data or {}
    
    if setup_data.get('base_dir'):
        print(f"📂 Data directory: {setup_data['base_dir']}")
    
    if setup_data.get('primary_user', {}).get('email'):
        print(f"👤 Primary user: {setup_data['primary_user']['email']}")
    
    collection_data = setup_data.get('collection_results', {})
    if collection_data:
        messages = collection_data.get('messages', 0)
        events = collection_data.get('events', 0)
        files = collection_data.get('files', 0)
        print(f"📊 Data collected: {messages} messages, {events} events, {files} files")
    
    index_data = setup_data.get('search_index', {})
    if index_data.get('records'):
        print(f"🔍 Search index: {index_data['records']:,} records ready")
    
    print("\n🚀 Quick Start Commands:")
    print("  python tools/daily_summary.py      # Generate daily brief")
    print("  python tools/search_cli.py \"query\" # Search your data")
    print("  python app.py                      # Launch dashboard")
    print()
    print("📖 For more information, see README.md")
    print("✅ Setup completed successfully!")

def print_error_message(result):
    """Print error message with recovery guidance"""
    print("\n" + "=" * 60)
    print("❌ Setup Failed")
    print("=" * 60)
    print(f"Error: {result.error}")
    print()
    
    if result.steps_completed:
        print(f"✅ Completed steps: {', '.join(result.steps_completed)}")
        print("The wizard can resume from where it left off.")
        print()
    
    print("🔧 Troubleshooting:")
    print("  • Check that you have internet connectivity")
    print("  • Verify that your API tokens are valid")
    print("  • Ensure you have write permissions in the chosen directory")
    print("  • Make sure all required environment variables are set")
    print()
    print("📖 For detailed setup instructions, see README.md")
    print("🔄 Run the setup wizard again to retry or resume")

if __name__ == "__main__":
    main()