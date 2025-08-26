# AI Chief of Staff - Data Collectors Guide

This guide provides comprehensive instructions for running the AI Chief of Staff data collectors to gather information from Slack, Google Calendar, Google Drive, and employee data sources.

## Quick Start

```bash
# Activate the virtual environment
source venv/bin/activate

# Run all collectors
python tools/collect_data.py --source=all

# Generate daily summary from collected data
python tools/daily_summary.py
```

## Available Collectors

### 1. Slack Collector (`slack`)
Collects messages, channels, and user information from Slack workspaces.

**Requirements:**
- Slack bot token (starts with `xoxb-`)
- Optional: Slack user token (starts with `xoxp-`) for enhanced features

**Usage:**
```bash
# Basic Slack collection
python tools/collect_data.py --source=slack

# With console output
python tools/collect_data.py --source=slack --output=console
```

**What it collects:**
- Public and private channel messages
- Direct messages (if user token provided)
- Channel metadata and user information
- Thread conversations and reactions

**Output location:** `data/raw/slack/YYYY-MM-DD/`

### 2. Google Drive Collector (`drive`)
Collects file metadata from Google Drive (not file contents).

**Requirements:**
- Google OAuth credentials (set up via `python tools/setup_google_oauth.py`)
- Drive API access enabled

**Usage:**
```bash
# Basic Drive collection
python tools/collect_data.py --source=drive

# View collection stats
python tools/collect_data.py --source=drive --output=console
```

**What it collects:**
- File metadata (names, types, modification dates)
- Sharing permissions and collaboration info
- File activity and version history
- Folder structure and organization

**Output location:** `data/raw/drive/YYYY-MM-DD/`

### 3. Google Calendar Collector (`calendar`)
Collects calendar events and meeting information.

**Requirements:**
- Google OAuth credentials
- Calendar API access enabled

**Usage:**
```bash
# Basic Calendar collection
python tools/collect_data.py --source=calendar

# Collect specific employees' calendars
python tools/collect_data.py --source=calendar --employees="alice@example.com,bob@example.com"

# Adjust time range (weeks)
python tools/collect_data.py --source=calendar --lookback-weeks=52 --lookahead-weeks=8
```

**What it collects:**
- Meeting events with attendees
- Event titles, descriptions, and locations
- Meeting durations and recurrence patterns
- Organizer and participant information

**Output location:** `data/raw/calendar/YYYY-MM-DD/`

### 4. Employee Collector (`employee`)
Builds a unified employee roster from other data sources.

**Requirements:**
- Data from other collectors (Slack, Calendar, Drive)

**Usage:**
```bash
# Build employee roster
python tools/collect_data.py --source=employee
```

**What it collects:**
- Employee email addresses and names
- Slack user IDs and calendar IDs
- Cross-platform identity mapping
- Active status and last seen information

**Output location:** `data/raw/employees/roster.json`

## Authentication Setup

### Google Services (Drive & Calendar)

1. **Initial OAuth Setup:**
   ```bash
   python tools/setup_google_oauth.py
   ```
   This opens a browser for OAuth consent and stores tokens securely.

2. **Verify Google Authentication:**
   ```bash
   python -c "from src.core.auth_manager import credential_vault; print('Google Auth:', credential_vault.get_google_oauth_creds() is not None)"
   ```

### Slack Authentication

1. **Check Current Tokens:**
   ```bash
   python -c "from src.core.auth_manager import credential_vault; credential_vault.validate_authentication()"
   ```

2. **View Authentication Status:**
   ```bash
   python -c "from src.core.key_manager import key_manager; print('Available keys:', key_manager.list_keys())"
   ```

**Note:** Slack tokens are stored encrypted in `src/core/encrypted_keys.db`. Production tokens use the `slack_tokens_production` key.

## Collection Commands Reference

### Run All Collectors
```bash
# Collect from all sources
python tools/collect_data.py --source=all

# Collect all with console output
python tools/collect_data.py --source=all --output=console
```

### Individual Collectors
```bash
# Drive only
python tools/collect_data.py --source=drive

# Slack only
python tools/collect_data.py --source=slack

# Calendar only
python tools/collect_data.py --source=calendar

# Employee roster only
python tools/collect_data.py --source=employee
```

### Output Formats
```bash
# Archive to JSONL files (default)
python tools/collect_data.py --source=drive --output=archive

# Display stats to console
python tools/collect_data.py --source=slack --output=console

# Save to JSON file
python tools/collect_data.py --source=calendar --output=json
```

## Automated Collection

### Overnight Collection
For automated daily collection:

```bash
# Run overnight collection tool
python tools/overnight_collection.py
```

### Cron Job Setup
Add to your crontab for daily 2 AM collection:
```bash
0 2 * * * cd /path/to/ai-cos-lab && source venv/bin/activate && python tools/overnight_collection.py
```

## Data Verification and Management

### Verify Collection Results
```bash
# Check archive integrity
python tools/verify_archive.py

# View collection statistics
python tools/manage_archives.py --stats
```

### Generate Summaries
```bash
# Daily summary from collected data
python tools/daily_summary.py

# Weekly summary
python tools/daily_summary.py --period=week

# Save summary to file
python tools/daily_summary.py --output-file=reports/daily-summary.json
```

## Understanding Output

### Successful Collection
```
✅ drive: 4.52s - {'files': 279, 'api_requests': 3, 'duration_mins': 0.1}
```
- **drive**: Collector name
- **4.52s**: Collection duration
- **279 files**: Number of items collected
- **3 API requests**: Efficiency metric

### Collection Errors
```
❌ Slack bot token not available
```
- Authentication issue - check token setup

```
⚠️ Rate limit hits: 2
```
- API rate limiting - collection will continue with delays

## Troubleshooting

### Common Issues

**1. "Slack bot token not found"**
- Solution: Set up Slack tokens in encrypted database
- Check: `python -c "from src.core.key_manager import key_manager; print(key_manager.list_keys())"`

**2. "Google OAuth failed"**
- Solution: Re-run `python tools/setup_google_oauth.py`
- Check: Ensure Calendar and Drive APIs are enabled in Google Cloud Console

**3. "No data collected"**
- Solution: Verify date ranges and permissions
- Check: Employee has access to channels/calendars being collected

**4. "Permission denied"**
- Solution: Check file permissions on `data/` directory
- Fix: `chmod -R 755 data/`

### Debug Mode
For detailed debugging output:
```bash
# Set debug environment
export LOG_LEVEL=DEBUG
python tools/collect_data.py --source=slack --output=console
```

### Test Mode
For testing without affecting production data:
```bash
# Use test mode
export AICOS_TEST_MODE=true
python tools/collect_data.py --source=all
```

## Data Storage Structure

After collection, data is organized as:

```
data/raw/
├── slack/
│   └── 2025-08-25/
│       ├── channels.json       # Channel metadata
│       ├── messages_*.jsonl    # Message data (JSONL format)
│       └── users.json          # User information
├── calendar/
│   └── 2025-08-25/
│       └── events_*.json       # Calendar events
├── drive/
│   └── 2025-08-25/
│       ├── drive_files_*.jsonl # File metadata (JSONL)
│       └── drive_summary.json  # Collection summary
└── employees/
    └── roster.json             # Employee roster mapping
```

## Performance Considerations

### Collection Speed
- **Drive**: ~279 files in 4-5 seconds
- **Slack**: Varies by message volume and channels
- **Calendar**: Fast for individual calendars, slower for organization-wide

### API Limits
- **Google Drive**: 1000 requests per 100 seconds
- **Google Calendar**: 1000 requests per 100 seconds  
- **Slack**: 1 request per second (configurable)

### Storage Usage
- **JSONL files**: Compressed and efficient
- **Metadata only**: No file contents stored
- **Incremental**: Only new/changed data collected

## Best Practices

### Daily Operations
1. Run collectors during off-peak hours (2-4 AM)
2. Monitor collection logs for errors
3. Verify data completeness regularly
4. Generate daily summaries to validate data flow

### Maintenance
1. Rotate old archives quarterly
2. Monitor disk usage in `data/` directory
3. Update OAuth tokens before expiration
4. Test backup and recovery procedures

### Security
1. Never commit credential files to version control
2. Use encrypted token storage only
3. Limit API scopes to minimum required
4. Regular security audits of stored data

## Getting Help

### Log Files
Check logs for detailed error information:
```bash
# View recent collector logs
tail -f logs/collector_runs.jsonl

# Search for errors
grep "ERROR" logs/collector_runs.jsonl
```

### Support Commands
```bash
# Test authentication
python -c "from src.core.auth_manager import credential_vault; credential_vault.validate_authentication()"

# List available data
find data/raw/ -name "*.json" -o -name "*.jsonl" | head -10

# Check system health
python tools/verify_archive.py --quick-check
```

For additional support, refer to:
- [Installation Guide](../INSTALLATION.md)
- [System Architecture](./architecture.md)
- [Troubleshooting Guide](./TROUBLESHOOTING.md)