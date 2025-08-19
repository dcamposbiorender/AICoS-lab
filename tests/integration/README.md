# AI Chief of Staff - Deterministic Test Harness

This test harness validates the data collection architecture by testing actual API discovery and collection capabilities **without making up any data**.

## Quick Start

1. **Activate virtual environment:**
   ```bash
   source venv/bin/activate
   ```

2. **Install dependencies (if needed):**
   ```bash
   pip install colorama  # For colored output (optional)
   ```

3. **Run the test harness:**
   ```bash
   python tests/integration/test_collector_harness.py --verbose
   ```

## Usage Examples

### Basic Testing
```bash
# Run all tests with default settings (7, 30, 90 days)
python tests/integration/test_collector_harness.py

# Run with detailed output
python tests/integration/test_collector_harness.py --verbose

# Quick test with just 7 days
python tests/integration/test_collector_harness.py --days 7

# Test specific time windows
python tests/integration/test_collector_harness.py --days 7 30 --verbose
```

### Collector-Specific Testing
```bash
# Test only Slack collector
python tests/integration/test_collector_harness.py --collector slack --verbose

# Test only Calendar collector  
python tests/integration/test_collector_harness.py --collector calendar

# Test only Drive collector
python tests/integration/test_collector_harness.py --collector drive
```

### 🌙 Overnight Bulk Collection Testing

For downloading **all organizational data** overnight with conservative rate limiting:

```bash
# Test full year in 90-day increments (overnight safe)
python tests/integration/test_collector_harness.py --yearly-increments --bulk-overnight --verbose

# This tests: 90 days, 180 days, 270 days, 365 days
# With rate limiting: 2s base → 1min → 5min → 10min backoff
```

### ⚡ Rate Limiting Strategy

**Conservative Bulk Collection Settings:**
- **Slack**: 2 seconds between requests, exponential backoff to 10 minutes
- **Calendar**: 3 seconds between requests + jitter, backoff to 10 minutes  
- **Drive**: Similar conservative approach for metadata-only collection

**Why Conservative?**
- Prevents API exhaustion during overnight runs
- Handles large organizational datasets (hundreds of channels, many calendars)
- Automatic recovery from rate limiting with exponential backoff
- Designed to run unattended overnight and complete successfully

## What the Test Does

### ✅ DETERMINISTIC TESTING - NO FAKE DATA
- **Discovery Tests**: Counts actual channels, calendars, and files from your workspace
- **Rate Limiting Tests**: Validates API rate limiting is working to prevent 429 errors
- **Collection Tests**: Collects real data for 7, 30, and 90 day windows
- **Validation Tests**: Checks data structure completeness

### 📊 Test Phases for Each Collector

#### Phase 1: Discovery Test
- **Slack**: Discovers channels (public, private, DMs, groups) and users
- **Calendar**: Discovers calendars and builds user roster  
- **Drive**: Discovers files and categorizes by MIME type

#### Phase 2: Rate Limiting Test
- Tests that rate limiters prevent API abuse
- Measures actual request timing
- Validates spacing between requests

#### Phase 3: Collection Test (Progressive)
- **7 days**: Quick collection test
- **30 days**: Medium-scale collection  
- **90 days**: Full-scale collection test
- Measures performance and completeness

#### Phase 4: Validation Test
- Checks required fields are present
- Validates data structure integrity
- Ensures no corruption or missing data

## Expected Output

```
================================================================================
AI CHIEF OF STAFF - DETERMINISTIC COLLECTOR TEST HARNESS
================================================================================
Testing data collection WITHOUT making up any data
All counts and metrics come from actual API discovery
================================================================================

▶ Testing SLACK Collector
────────────────────────────────────────────────────────

  ► Running Discovery Test...
    ✓ Discovered 47 channels and 23 users
      - total_channels: 47
      - public_channels: 25
      - private_channels: 5
      - direct_messages: 12
      - group_messages: 5
      - total_users: 23
      - active_users: 21

  ► Testing Rate Limiting...
    ✓ Rate limiting working: 1.02s avg delay (expected ~0.50s)

  ► Testing 7-Day Collection...
    ✓ Collected 1,234 messages from 3/5 channels
      - days: 7
      - channels_available: 47
      - channels_tested: 5
      - channels_collected: 3
      - total_messages: 1234
      - avg_messages_per_channel: 411.33
      - api_requests: 15

[Similar output for other collectors and time windows]

================================================================================
TEST RESULTS SUMMARY
================================================================================
Total Tests: 12
Duration: 127.45 seconds
Success Rate: 91.7%

✓ Passed: 11
✗ Failed: 1
⚠ Errors: 0

Failed Tests:
  • drive_collection_90d: Drive collection not yet implemented for 90 days

📊 Report saved to: /path/to/test_results.json
```

## Exit Codes

- **0**: All tests passed
- **1**: Some tests failed or encountered errors  
- **130**: Interrupted by user (Ctrl+C)

## Output Files

- **`test_results.json`**: Detailed JSON report of all test results
- Contains metrics, timing, and detailed failure information
- Can be processed programmatically for CI/CD integration

## Troubleshooting

### Authentication Issues
```
❌ Slack authentication failed
```
- Check that Slack credentials are configured in the credential vault
- Verify bot token has necessary permissions

### Import Errors
```
⚠️ Import error: No module named 'src.core.config'
```
- Make sure you're running from the project root directory
- Activate virtual environment: `source venv/bin/activate`

### No Data Found
```
❌ No channels discovered (check workspace access)
```
- Verify the bot is added to channels you want to test
- Check API credentials have correct scopes

### Rate Limiting Too Fast
```
❌ Rate limiting too fast: 0.02s < 0.50s
```
- Rate limiter may need tuning
- Check if test environment has different rate limits

## Integration with CI/CD

The test harness returns proper exit codes and generates JSON reports, making it suitable for automated testing:

```bash
# In CI/CD pipeline
python tests/integration/test_collector_harness.py --days 7
if [ $? -eq 0 ]; then
    echo "✅ All collector tests passed"
else
    echo "❌ Collector tests failed - check test_results.json"
    exit 1
fi
```

## Key Features

- 🎯 **No Fake Data**: All counts come from actual API discovery
- 🌈 **Colored Output**: Easy-to-read terminal output with ✓/✗ indicators
- ⏱️ **Performance Metrics**: Measures timing for all operations
- 📊 **Detailed Reporting**: JSON output for programmatic processing
- 🔄 **Progressive Testing**: 7 → 30 → 90 day windows
- 🛡️ **Rate Limit Validation**: Ensures API abuse prevention
- 🧪 **Real Integration Testing**: Tests actual API endpoints and data