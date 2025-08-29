#!/usr/bin/env python3
"""
Interactive Setup Wizard for AI Chief of Staff System

This wizard guides users through complete system setup from scratch, including:
- Environment configuration (directories, database, AICOS_BASE_DIR)
- API credentials setup (Slack bot tokens, Google OAuth)
- User identity configuration (PRIMARY_USER setup)
- System validation and initial data collection

References:
- src/core/config.py - Configuration management patterns
- src/core/auth_manager.py - Credential storage approaches
- src/core/user_identity.py - User identity configuration
- tools/collect_data.py - Data collection orchestration
"""

import os
import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

@dataclass
class SetupResult:
    """Result of setup wizard execution"""
    success: bool
    error: Optional[str] = None
    steps_completed: List[str] = None
    setup_data: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.steps_completed is None:
            self.steps_completed = []

class SetupError(Exception):
    """Custom exception for setup wizard failures"""
    pass

class SetupWizard:
    """
    Interactive setup wizard for complete system configuration
    
    Provides step-by-step guidance through:
    1. Environment setup (directories, database)
    2. Slack API configuration and validation
    3. Google services setup (Calendar + Drive)
    4. User identity configuration
    5. System validation
    6. Initial data collection and indexing
    
    Features:
    - Clear progress indication
    - Resume capability if interrupted
    - Comprehensive validation
    - Helpful error messages with recovery guidance
    """
    
    def __init__(self, interactive: bool = True):
        """Initialize setup wizard
        
        Args:
            interactive: If True, prompts user for input. If False, uses defaults/environment
        """
        self.interactive = interactive
        self.setup_data = {}
        self.steps_completed = []
        self.total_steps = 6
        
        # Import wizard steps (delayed to avoid circular imports)
        self._step_modules = {}
        
    def _load_step_module(self, step_name: str):
        """Dynamically load a wizard step module"""
        if step_name in self._step_modules:
            return self._step_modules[step_name]
            
        try:
            if step_name == 'environment':
                from .wizard_steps.environment_setup import EnvironmentSetup
                module = EnvironmentSetup()
            elif step_name == 'slack':
                from .wizard_steps.slack_setup import SlackSetup
                module = SlackSetup()
            elif step_name == 'google':
                from .wizard_steps.google_setup import GoogleSetup
                module = GoogleSetup()
            elif step_name == 'user':
                from .wizard_steps.user_setup import UserSetup
                module = UserSetup()
            elif step_name == 'validation':
                from .wizard_steps.validation_setup import ValidationSetup
                module = ValidationSetup()
            else:
                raise ImportError(f"Unknown step: {step_name}")
                
            self._step_modules[step_name] = module
            return module
            
        except ImportError as e:
            raise SetupError(f"Failed to load setup step '{step_name}': {e}")
    
    def run(self) -> SetupResult:
        """
        Main wizard flow with progress tracking and error handling
        
        Returns:
            SetupResult with success status and details
        """
        try:
            self._show_welcome()
            
            # Step 1: Environment Setup
            self._show_step_header(1, "Environment Setup")
            env_step = self._load_step_module('environment')
            env_result = env_step.run(self.setup_data, interactive=self.interactive)
            self.setup_data.update(env_result)
            self.steps_completed.append("environment")
            
            # Step 2: Slack Configuration
            self._show_step_header(2, "Slack Configuration")
            slack_step = self._load_step_module('slack')
            slack_result = slack_step.run(self.setup_data, interactive=self.interactive)
            self.setup_data.update(slack_result)
            self.steps_completed.append("slack")
            
            # Step 3: Google Services
            self._show_step_header(3, "Google Services")
            google_step = self._load_step_module('google')
            google_result = google_step.run(self.setup_data, interactive=self.interactive)
            self.setup_data.update(google_result)
            self.steps_completed.append("google")
            
            # Step 4: User Identity
            self._show_step_header(4, "User Identity")
            user_step = self._load_step_module('user')
            user_result = user_step.run(self.setup_data, interactive=self.interactive)
            self.setup_data.update(user_result)
            self.steps_completed.append("user")
            
            # Step 5-6: System Validation & Initial Collection
            self._show_step_header(5, "System Validation & Initial Collection")
            validation_step = self._load_step_module('validation')
            validation_result = validation_step.run(self.setup_data, interactive=self.interactive)
            self.setup_data.update(validation_result)
            self.steps_completed.extend(["validation", "initial_collection"])
            
            # Show success summary
            self._show_success_summary()
            
            return SetupResult(
                success=True,
                steps_completed=self.steps_completed,
                setup_data=self.setup_data
            )
            
        except SetupError as e:
            self._show_error_help(e)
            return SetupResult(
                success=False,
                error=str(e),
                steps_completed=self.steps_completed,
                setup_data=self.setup_data
            )
        except KeyboardInterrupt:
            print("\n\n⚠️  Setup interrupted by user")
            print("You can resume setup later by running the wizard again.")
            return SetupResult(
                success=False,
                error="Interrupted by user",
                steps_completed=self.steps_completed,
                setup_data=self.setup_data
            )
        except Exception as e:
            print(f"\n❌ Unexpected error during setup: {e}")
            return SetupResult(
                success=False,
                error=f"Unexpected error: {e}",
                steps_completed=self.steps_completed,
                setup_data=self.setup_data
            )
    
    def _show_welcome(self):
        """Display welcome message and setup overview"""
        print("\n🚀 AI Chief of Staff Setup Wizard")
        print("=" * 50)
        print("This wizard will guide you through complete system setup:")
        print("  1. Environment & Directory Structure")
        print("  2. Slack API Configuration")
        print("  3. Google Services (Calendar + Drive)")
        print("  4. User Identity Configuration")
        print("  5. System Validation")
        print("  6. Initial Data Collection")
        print("\n⏱️  Estimated time: 5 minutes")
        print("💾 All credentials stored encrypted locally")
        print("🛡️  No data ever leaves your infrastructure")
        
        if self.interactive:
            print("\nPress Enter to begin...")
            input()
    
    def _show_step_header(self, step_num: int, step_name: str):
        """Display step header with progress indication"""
        progress_bar = self._create_progress_bar(step_num - 1)
        print(f"\n{progress_bar} Step {step_num}/{self.total_steps}: {step_name}")
        print("-" * 50)
    
    def _create_progress_bar(self, completed_steps: int) -> str:
        """Create visual progress bar"""
        filled = "●" * completed_steps
        empty = "○" * (self.total_steps - completed_steps)
        return f"[{filled}{empty}]"
    
    def _show_success_summary(self):
        """Display successful completion summary"""
        print("\n" + "=" * 50)
        print("🎉 Setup Complete!")
        print("=" * 50)
        
        print("\n📊 System Status:")
        
        # API Status
        apis_configured = []
        if self.setup_data.get('slack_token'):
            apis_configured.append("Slack ✅")
        if self.setup_data.get('google_oauth'):
            apis_configured.append("Calendar ✅")
            apis_configured.append("Drive ✅")
        
        print(f"• APIs configured: {' '.join(apis_configured)}")
        
        # Data Collection Status
        collection_data = self.setup_data.get('collection_results', {})
        if collection_data:
            messages = collection_data.get('messages', 0)
            events = collection_data.get('events', 0)
            files = collection_data.get('files', 0)
            print(f"• Data collected: {messages:,} messages, {events} events, {files} files")
        
        # Search Index Status
        index_data = self.setup_data.get('search_index', {})
        if index_data:
            records = index_data.get('records', 0)
            print(f"• Search index: {records:,} records ready")
        
        # Primary User Status
        primary_user = self.setup_data.get('primary_user')
        if primary_user:
            print(f"• PRIMARY_USER: {primary_user.get('email', 'configured')}")
        
        print("\n🚀 Quick Start:")
        print("• Daily brief: python tools/daily_summary.py")
        print("• Search: python tools/search_cli.py \"meeting notes\"")
        print("• Dashboard: python app.py")
        
        print("\n📖 Documentation: README.md")
        print("\n✅ Your AI Chief of Staff is ready to use!")
    
    def _show_error_help(self, error: SetupError):
        """Display error message with helpful recovery guidance"""
        print(f"\n❌ Setup Error: {error}")
        print("\n📋 Recovery Options:")
        print("1. Fix the issue and run the wizard again")
        print("2. Check README.md for manual configuration")
        print("3. Ensure all requirements are met:")
        print("   - Python 3.10+ installed")
        print("   - Internet connection available")
        print("   - Write permissions in chosen directory")
        print("   - Valid API tokens/credentials")
        
        if self.steps_completed:
            print(f"\n✅ Completed steps: {', '.join(self.steps_completed)}")
            print("The wizard will resume from the failed step.")
    
    def can_resume(self) -> bool:
        """Check if setup can be resumed from previous state"""
        return len(self.steps_completed) > 0
    
    def get_setup_summary(self) -> Dict[str, Any]:
        """Get summary of current setup state"""
        return {
            "steps_completed": self.steps_completed,
            "total_steps": self.total_steps,
            "progress_percentage": (len(self.steps_completed) / self.total_steps) * 100,
            "setup_data": self.setup_data
        }

def run_setup_wizard(interactive: bool = True) -> SetupResult:
    """
    Convenience function to run the setup wizard
    
    Args:
        interactive: If True, prompts user for input
        
    Returns:
        SetupResult with success status and details
    """
    wizard = SetupWizard(interactive=interactive)
    return wizard.run()

if __name__ == "__main__":
    # Command line interface
    import argparse
    
    parser = argparse.ArgumentParser(description="AI Chief of Staff Setup Wizard")
    parser.add_argument("--non-interactive", action="store_true", 
                       help="Run in non-interactive mode using environment variables")
    parser.add_argument("--version", action="version", version="1.0.0")
    
    args = parser.parse_args()
    
    interactive = not args.non_interactive
    
    print("🤖 Starting AI Chief of Staff Setup Wizard...")
    result = run_setup_wizard(interactive=interactive)
    
    if result.success:
        print("✅ Setup completed successfully!")
        sys.exit(0)
    else:
        print(f"❌ Setup failed: {result.error}")
        sys.exit(1)