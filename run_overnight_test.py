#!/usr/bin/env python3
"""
Overnight Bulk Collection Test Runner

This script sets up OAuth credentials and runs the full overnight test
to validate that ALL of BioRender's data can be downloaded successfully.

Usage:
    python run_overnight_test.py
"""

import sys
import subprocess
from pathlib import Path

def main():
    """Run the complete overnight test setup and execution"""
    print("🌙 BioRender Overnight Bulk Collection Test")
    print("=" * 50)
    
    project_root = Path(__file__).parent
    token_file = project_root / "data" / "auth" / "token.pickle"
    
    # Step 1: Check/Setup OAuth credentials
    if not token_file.exists():
        print("🔐 Setting up Google OAuth credentials...")
        try:
            result = subprocess.run([
                sys.executable, "tools/setup_google_oauth.py"
            ], cwd=project_root, check=True)
        except subprocess.CalledProcessError:
            print("❌ OAuth setup failed. Please run manually:")
            print("   python tools/setup_google_oauth.py")
            return False
    else:
        print("✅ OAuth credentials found")
        
        # Test existing credentials
        print("🧪 Testing existing credentials...")
        try:
            result = subprocess.run([
                sys.executable, "tools/setup_google_oauth.py", "--test-only"
            ], cwd=project_root, check=True, capture_output=True, text=True)
            print("✅ Existing credentials work")
        except subprocess.CalledProcessError:
            print("⚠️ Existing credentials may be expired. Re-running setup...")
            try:
                result = subprocess.run([
                    sys.executable, "tools/setup_google_oauth.py"
                ], cwd=project_root, check=True)
            except subprocess.CalledProcessError:
                print("❌ OAuth refresh failed")
                return False
    
    print("\n" + "=" * 50)
    print("🚀 Starting Overnight Bulk Collection Test")
    print("This will test downloading ALL BioRender data:")
    print("- All 368+ Slack channels")
    print("- All Google Calendars")
    print("- Drive metadata")
    print("- Progressive windows: 90d, 180d, 270d, 365d")
    print("- Conservative rate limiting with backoff")
    print("=" * 50)
    
    # Step 2: Run the overnight test
    try:
        result = subprocess.run([
            sys.executable, "tests/integration/test_collector_harness.py",
            "--yearly-increments",
            "--bulk-overnight", 
            "--verbose"
        ], cwd=project_root, check=False)  # Don't fail on test failures
        
        print("\n" + "=" * 50)
        if result.returncode == 0:
            print("🎉 ALL TESTS PASSED!")
            print("✅ BioRender overnight bulk collection validated")
            print("✅ Ready for production overnight data download")
        else:
            print("⚠️ Some tests failed, but collection may still be working")
            print("📊 Check test_results.json for detailed results")
            
        print(f"\n📄 Detailed results saved to: {project_root}/test_results.json")
        return result.returncode == 0
        
    except KeyboardInterrupt:
        print("\n⚠️ Test interrupted by user")
        return False
    except Exception as e:
        print(f"\n❌ Test execution failed: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)