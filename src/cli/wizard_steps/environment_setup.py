#!/usr/bin/env python3
"""
Environment Setup Step for AI Chief of Staff Setup Wizard

Handles:
- AICOS_BASE_DIR configuration
- Directory structure creation  
- SQLite database initialization
- Dependency checking and validation
- Disk space requirements
- .env file creation

References:
- src/core/config.py:87-131 - Directory validation patterns
- src/core/state.py - Database initialization patterns
"""

import os
import shutil
import sqlite3
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional

class EnvironmentSetup:
    """Step 1: Environment configuration and directory setup"""
    
    def __init__(self):
        self.required_dirs = [
            "data",
            "data/archive", 
            "data/archive/slack",
            "data/archive/calendar",
            "data/archive/drive",
            "data/archive/employees",
            "data/state",
            "data/logs"
        ]
        self.min_disk_space_gb = 1  # Minimum 1GB free space required
    
    def run(self, wizard_data: Dict[str, Any], interactive: bool = True) -> Dict[str, Any]:
        """
        Execute environment setup step
        
        Args:
            wizard_data: Shared wizard data dictionary
            interactive: If True, prompt user for input
            
        Returns:
            Dictionary with setup results
        """
        print("Setting up environment and directory structure...")
        
        # Step 1: Configure base directory
        base_dir = self._setup_base_directory(interactive)
        
        # Step 2: Create directory structure
        self._create_directories(base_dir)
        
        # Step 3: Initialize SQLite database
        self._initialize_database(base_dir)
        
        # Step 4: Validate environment
        self._validate_environment(base_dir)
        
        # Step 5: Create .env file
        env_file = self._create_env_file(base_dir)
        
        print("✅ Environment setup complete")
        
        return {
            "base_dir": str(base_dir),
            "env_file": str(env_file),
            "directories_created": len(self.required_dirs)
        }
    
    def _setup_base_directory(self, interactive: bool) -> Path:
        """Set up and validate AICOS_BASE_DIR"""
        # Check if already configured
        existing_base_dir = os.getenv('AICOS_BASE_DIR')
        
        if interactive and not existing_base_dir:
            # Prompt user for base directory
            default_dir = str(Path.home() / "aicos_data")
            
            print(f"\n📂 Choose data directory for AI Chief of Staff")
            print(f"This directory will store all your data, logs, and configuration.")
            print(f"Default: {default_dir}")
            
            response = input(f"Directory path [{default_dir}]: ").strip()
            base_dir_str = response if response else default_dir
        elif existing_base_dir:
            base_dir_str = existing_base_dir
            print(f"📂 Using existing AICOS_BASE_DIR: {base_dir_str}")
        else:
            # Non-interactive mode: use default or environment
            base_dir_str = existing_base_dir or str(Path.home() / "aicos_data")
            print(f"📂 Using base directory: {base_dir_str}")
        
        base_dir = Path(base_dir_str).resolve()
        
        # Create base directory if it doesn't exist
        if not base_dir.exists():
            try:
                base_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
                print(f"✅ Created base directory: {base_dir}")
            except PermissionError as e:
                raise RuntimeError(f"Cannot create base directory {base_dir}: {e}")
        
        # Validate it's a directory and writable
        if not base_dir.is_dir():
            raise RuntimeError(f"Base directory path is not a directory: {base_dir}")
        
        if not os.access(base_dir, os.W_OK):
            raise RuntimeError(f"Base directory is not writable: {base_dir}")
        
        # Set environment variable for this session
        os.environ['AICOS_BASE_DIR'] = str(base_dir)
        
        return base_dir
    
    def _create_directories(self, base_dir: Path):
        """Create all required directories"""
        print("📁 Creating directory structure...")
        
        for dir_name in self.required_dirs:
            dir_path = base_dir / dir_name
            try:
                dir_path.mkdir(parents=True, exist_ok=True, mode=0o700)
            except PermissionError as e:
                raise RuntimeError(f"Cannot create directory {dir_path}: {e}")
            
            # Validate write permissions
            if not os.access(dir_path, os.W_OK):
                raise RuntimeError(f"Directory not writable: {dir_path}")
        
        print(f"✅ Created {len(self.required_dirs)} directories")
    
    def _initialize_database(self, base_dir: Path):
        """Initialize SQLite database with proper schema"""
        print("🗄️  Initializing SQLite database...")
        
        db_path = base_dir / "data" / "aicos.db"
        
        try:
            # Create database and basic tables
            with sqlite3.connect(str(db_path)) as conn:
                cursor = conn.cursor()
                
                # Enable FTS5 if available (for search functionality)
                cursor.execute("SELECT sqlite_version()")
                version = cursor.fetchone()[0]
                print(f"📊 SQLite version: {version}")
                
                # Create basic state table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS system_state (
                        key TEXT PRIMARY KEY,
                        value TEXT,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Insert initial setup state
                cursor.execute("""
                    INSERT OR REPLACE INTO system_state (key, value) 
                    VALUES ('setup_completed', 'false')
                """)
                cursor.execute("""
                    INSERT OR REPLACE INTO system_state (key, value) 
                    VALUES ('setup_version', '1.0.0')
                """)
                
                conn.commit()
                print("✅ Database initialized successfully")
                
        except sqlite3.Error as e:
            raise RuntimeError(f"Failed to initialize database: {e}")
    
    def _validate_environment(self, base_dir: Path):
        """Validate environment meets requirements"""
        print("🔍 Validating environment...")
        
        # Check disk space
        self._check_disk_space(base_dir)
        
        # Check Python dependencies
        self._check_dependencies()
        
        # Check file permissions
        self._check_permissions(base_dir)
        
        print("✅ Environment validation passed")
    
    def _check_disk_space(self, base_dir: Path):
        """Check minimum disk space requirements"""
        try:
            total, used, free = shutil.disk_usage(base_dir)
            free_gb = free / (1024**3)
            
            if free_gb < self.min_disk_space_gb:
                raise RuntimeError(
                    f"Insufficient disk space. Required: {self.min_disk_space_gb}GB, "
                    f"Available: {free_gb:.1f}GB"
                )
            
            print(f"💾 Available disk space: {free_gb:.1f}GB")
            
        except OSError as e:
            raise RuntimeError(f"Cannot check disk usage: {e}")
    
    def _check_dependencies(self):
        """Check critical Python dependencies are available"""
        critical_deps = [
            'sqlite3',  # Built-in
            'pathlib',  # Built-in
            'json',     # Built-in
        ]
        
        # Optional dependencies (warn if missing)
        optional_deps = [
            ('requests', 'HTTP requests'),
            ('cryptography', 'credential encryption'),
        ]
        
        # Check critical dependencies
        for dep in critical_deps:
            try:
                __import__(dep)
            except ImportError:
                raise RuntimeError(f"Critical dependency missing: {dep}")
        
        # Check optional dependencies
        missing_optional = []
        for dep, description in optional_deps:
            try:
                __import__(dep)
            except ImportError:
                missing_optional.append(f"{dep} ({description})")
        
        if missing_optional:
            print(f"⚠️  Optional dependencies missing: {', '.join(missing_optional)}")
            print("Some features may be limited. Run 'pip install -r requirements.txt'")
        
        print("✅ Dependency check completed")
    
    def _check_permissions(self, base_dir: Path):
        """Check that all directories are writable"""
        for dir_name in self.required_dirs:
            dir_path = base_dir / dir_name
            if not os.access(dir_path, os.W_OK):
                raise RuntimeError(f"Directory not writable: {dir_path}")
        
        # Test write by creating and removing a temporary file
        test_file = base_dir / "data" / ".write_test"
        try:
            test_file.write_text("test")
            test_file.unlink()
        except Exception as e:
            raise RuntimeError(f"Cannot write to data directory: {e}")
    
    def _create_env_file(self, base_dir: Path) -> Path:
        """Create .env file with base configuration"""
        env_file = base_dir / ".env"
        
        # Don't overwrite existing .env file
        if env_file.exists():
            print(f"📄 .env file already exists: {env_file}")
            return env_file
        
        env_content = f"""# AI Chief of Staff Environment Configuration
# Generated by setup wizard

# Base directory for all data storage
AICOS_BASE_DIR={base_dir}

# Environment settings
ENVIRONMENT=production
LOG_LEVEL=INFO
AICOS_TEST_MODE=false

# Data retention (days)
DATA_RETENTION_DAYS=365

# Time and timezone settings
TIMEZONE=UTC
BRIEFING_TIME=06:00

# API tokens (will be set by setup wizard)
# SLACK_BOT_TOKEN=
# SLACK_USER_TOKEN=
# GOOGLE_CLIENT_ID=
# GOOGLE_CLIENT_SECRET=
# ANTHROPIC_API_KEY=

# Primary user configuration (will be set by setup wizard)
# AICOS_PRIMARY_USER_EMAIL=
# AICOS_PRIMARY_USER_SLACK_ID=
# AICOS_PRIMARY_USER_CALENDAR_ID=
# AICOS_PRIMARY_USER_NAME=
"""
        
        try:
            env_file.write_text(env_content)
            print(f"✅ Created .env file: {env_file}")
        except Exception as e:
            print(f"⚠️  Could not create .env file: {e}")
        
        return env_file

if __name__ == "__main__":
    # Test the environment setup
    setup = EnvironmentSetup()
    result = setup.run({}, interactive=True)
    print(f"Setup result: {result}")