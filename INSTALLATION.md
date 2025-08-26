# AI Chief of Staff - Installation Guide

This guide provides step-by-step instructions for setting up the AI Chief of Staff system on your local machine.

## Prerequisites

### System Requirements
- **Operating System**: macOS, Linux, or Windows with WSL2
- **Python**: Version 3.9 or higher
- **SQLite**: Version 3.35+ with FTS5 support (usually included with Python)
- **Memory**: Minimum 4GB RAM, 8GB recommended for large datasets
- **Disk Space**: 2GB for installation, additional space for data storage

### Required Accounts and APIs
- **Slack Workspace**: Admin access to create a Slack app
- **Google Cloud Console**: Access to create OAuth credentials
- **API Access**: Ability to enable Google Calendar and Drive APIs

## Step 1: Clone and Setup

```bash
# Clone the repository
git clone https://github.com/your-org/ai-cos-lab.git
cd ai-cos-lab

# Create and activate virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Step 2: Environment Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env file with your configuration
# See detailed configuration guide below
```

### Environment Variables Configuration

Open `.env` in your text editor and configure the following:

#### System Configuration
```bash
# Set your data directory (optional)
AICOS_BASE_DIR=/path/to/your/data/directory

# For development/testing
AICOS_TEST_MODE=true
```

## 🔐 Authentication & Token Storage

**IMPORTANT**: All API tokens are stored encrypted in `src/core/encrypted_keys.db`  
**Never put production tokens in .env files!**

#### Slack Authentication Setup
1. Go to [Slack API Console](https://api.slack.com/apps)
2. Create a new app for your workspace
3. Get your bot token (starts with `xoxb-`) from "OAuth & Permissions"
4. Get your app token (starts with `xapp-`) from "Basic Information" 
5. Store tokens securely using the key manager:
   ```bash
   python -c "
   from src.core.key_manager import key_manager
   
   # Store Slack credentials
   slack_config = {
       'bot_token': 'xoxb-your-actual-bot-token',
       'user_token': 'xoxp-your-user-token-if-needed'
   }
   key_manager.store_key('slack_credentials', slack_config, 'slack_auth')
   print('✅ Slack tokens stored encrypted')
   "
   ```

#### Google APIs Authentication Setup
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing project
3. Enable Calendar and Drive APIs
4. Create OAuth 2.0 credentials (download the JSON file)
5. Use the OAuth setup tool to store credentials:
   ```bash
   python tools/setup_google_oauth.py
   # This opens a browser for OAuth flow and stores tokens encrypted
   ```

**Token Storage Location:**
- **Database**: `src/core/encrypted_keys.db` (AES-256 encrypted)
- **Master Key**: `src/core/.master_key` (auto-generated if missing)
- **Google OAuth**: Additional files in `data/auth/` for OAuth tokens

## Step 3: Google OAuth Setup

```bash
# Run the OAuth setup tool
python tools/setup_google_oauth.py

# Follow the browser prompts to authorize the application
# This will create necessary credential files
```

## Step 4: Verify Installation

```bash
# Test basic functionality
python -c "import src.core.config; print('Configuration loaded successfully')"

# Test database creation
python -c "from src.search.database import SearchDatabase; db = SearchDatabase(); print('Database connection successful')"

# Run a simple collection test
export AICOS_TEST_MODE=true
python tools/collect_data.py --source=employee --output=console
```

## Step 5: Initial Data Collection

```bash
# Set test mode for initial setup
export AICOS_TEST_MODE=false

# Run your first data collection
python tools/collect_data.py --source=slack --output=json
python tools/collect_data.py --source=calendar --output=json

# Index the collected data
python tools/search_cli.py index data/archive/

# Test search functionality
python tools/search_cli.py search "test query"
```

## Configuration Guide

### Slack App Configuration

#### Required Scopes
Add these OAuth scopes to your Slack app:
- `channels:read` - Read public channel information
- `channels:history` - Read messages from public channels
- `groups:read` - Read private channel information  
- `groups:history` - Read messages from private channels
- `im:read` - Read direct message information
- `im:history` - Read direct message content
- `users:read` - Read user information
- `team:read` - Read workspace information

#### Socket Mode (if using bot features)
1. Enable Socket Mode in your Slack app settings
2. Generate an App Token with `connections:write` scope
3. Add the App Token to your `.env` file

### Google APIs Configuration

#### Required APIs
Enable these APIs in Google Cloud Console:
- Google Calendar API
- Google Drive API

#### OAuth Consent Screen
1. Configure OAuth consent screen
2. Add your email to test users (during development)
3. Set authorized redirect URIs: `http://localhost:8080`

### Directory Structure

After installation, your data directory will look like:
```
data/
├── archive/
│   ├── slack/YYYY-MM-DD/
│   ├── calendar/YYYY-MM-DD/
│   └── employees/
├── auth/
│   ├── credentials.json
│   └── token.pickle
└── search.db
```

## Testing Your Installation

### Run Test Suite
```bash
# Run unit tests
python -m pytest tests/unit/ -v

# Run integration tests (requires configuration)
python -m pytest tests/integration/ -v
```

### Manual Testing
```bash
# Test each collector individually
python tools/collect_data.py --source=slack --output=console
python tools/collect_data.py --source=calendar --output=console
python tools/collect_data.py --source=employee --output=console

# Test search functionality
python tools/search_cli.py stats
python tools/search_cli.py search "meeting"
```

## Troubleshooting

### Common Issues

#### Python Virtual Environment
```bash
# If venv activation fails
python -m venv --clear venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install --upgrade pip
pip install -r requirements.txt
```

#### SQLite FTS5 Support
```bash
# Test FTS5 support
python -c "import sqlite3; conn = sqlite3.connect(':memory:'); conn.execute('CREATE VIRTUAL TABLE test USING fts5(content)'); print('FTS5 supported')"
```

#### Google OAuth Issues
- Ensure redirect URI matches exactly: `http://localhost:8080`
- Check that Calendar and Drive APIs are enabled
- Verify OAuth consent screen is configured
- For development, add your email to test users

#### Slack API Issues
- Verify bot token starts with `xoxb-`
- Verify app token starts with `xapp-`
- Ensure required scopes are added to your Slack app
- Check that the bot is added to channels you want to collect from

### Getting Help
1. Check the logs in the terminal output
2. Verify all environment variables are set correctly
3. Ensure all required APIs are enabled and configured
4. Test each component individually using the CLI tools

## Next Steps

After successful installation:
1. Review [CAPABILITIES.md](./CAPABILITIES.md) for available features
2. Check [tools/README.md](./tools/README.md) for detailed CLI documentation
3. Set up regular data collection using the overnight collection tool
4. Configure archive management and compression settings

## Security Notes

- Keep your `.env` file secure and never commit it to version control
- Regularly rotate API keys and tokens
- Use test mode for development to avoid collecting real data
- Review the security documentation for production deployments