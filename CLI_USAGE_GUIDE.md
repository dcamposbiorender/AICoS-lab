# AI Chief of Staff - CLI Tools Usage Guide

This guide provides comprehensive documentation for the AI Chief of Staff CLI tools, including usage examples, common workflows, and troubleshooting information.

## Overview

The AI Chief of Staff system provides two main CLI tools:

1. **`query_facts.py`** - Unified query interface for searching and analyzing organizational data
2. **`daily_summary.py`** - Automated report generation for daily, weekly, and monthly summaries

Both tools support multiple output formats, test mode for development, and comprehensive error handling.

## Quick Start

```bash
# Activate virtual environment
source venv/bin/activate

# Set test mode (optional, for development)
export AICOS_TEST_MODE=true

# Basic queries
python tools/query_facts.py time "yesterday"
python tools/query_facts.py person "alice@example.com"
python tools/daily_summary.py --date 2025-08-19
```

## Query Facts CLI (`query_facts.py`)

The unified query interface provides access to all organizational data through natural language queries and structured searches.

### Time-Based Queries

Query data by time expressions using natural language:

```bash
# Recent activity
python tools/query_facts.py time "today"
python tools/query_facts.py time "yesterday"
python tools/query_facts.py time "last week"

# Specific dates
python tools/query_facts.py time "2025-08-19"
python tools/query_facts.py time "August 2025"

# With filters and options
python tools/query_facts.py time "yesterday" --source slack --format json
python tools/query_facts.py time "last week" --limit 20 --verbose
```

**Supported Time Expressions:**
- `today`, `yesterday`
- `last week`, `this week`, `past 7 days`
- `last month`, `this month`
- Specific dates: `2025-08-19`
- Month/year: `August 2025`, `2025`

### Person-Based Queries

Search for activity and interactions with specific people:

```bash
# Basic person query
python tools/query_facts.py person "alice@example.com"
python tools/query_facts.py person "U123456789"  # Slack user ID

# With time range and activity summary
python tools/query_facts.py person "bob@company.com" --time-range "last week"
python tools/query_facts.py person "alice@example.com" --activity-summary
python tools/query_facts.py person "charlie@team.com" --include-interactions
```

**Person ID Formats:**
- Email addresses: `alice@example.com`
- Slack user IDs: `U123456789`
- Display names: `Alice Johnson` (if supported)

### Pattern Extraction

Extract structured information from conversations and documents:

```bash
# Extract TODOs and action items
python tools/query_facts.py patterns --pattern-type todos --time-range "today"
python tools/query_facts.py patterns --pattern-type action_items --time-range "this week"

# Find mentions and references
python tools/query_facts.py patterns --pattern-type mentions --person "alice@example.com"

# Identify deadlines and decisions
python tools/query_facts.py patterns --pattern-type deadlines --format json
python tools/query_facts.py patterns --pattern-type decisions --time-range "last month"
```

**Pattern Types:**
- `todos` - TODO items and task mentions
- `mentions` - @mentions and references to people
- `deadlines` - Deadline and due date mentions
- `decisions` - Decision points and outcomes
- `action_items` - Action items and assignments

### Calendar Coordination

Find meeting slots, check conflicts, and analyze availability:

```bash
# Find free time slots
python tools/query_facts.py calendar find-slots \
    --attendees "alice@example.com,bob@example.com" \
    --duration 60

# Check for conflicts
python tools/query_facts.py calendar check-conflicts \
    --attendees "team@company.com" \
    --start-time "2025-08-20T14:00:00" \
    --duration 30

# Check availability
python tools/query_facts.py calendar availability \
    --person "alice@example.com" --date "2025-08-20"
```

### Statistics and Analytics

Generate activity statistics and insights:

```bash
# Basic statistics
python tools/query_facts.py stats --time-range "last week"

# With breakdown by channel or person
python tools/query_facts.py stats --time-range "last week" --breakdown channel
python tools/query_facts.py stats --time-range "this month" --breakdown person

# Include rankings and trends
python tools/query_facts.py stats --time-range "past 30 days" --person-ranking
python tools/query_facts.py stats --time-range "this quarter" --include-trends
```

### Interactive Mode

Start an interactive query session for exploratory analysis:

```bash
# Start interactive mode
python tools/query_facts.py --interactive

# In interactive mode, use commands like:
Query> yesterday
Query> person alice@example.com
Query> patterns todos
Query> /help
Query> q
```

**Interactive Commands:**
- Time expressions: `yesterday`, `last week`
- Person queries: `person alice@example.com`
- Pattern extraction: `patterns todos`
- Special commands: `/help`, `/stats`
- Exit: `q`, `quit`, `exit`

### Output Formats

All query commands support multiple output formats:

```bash
# JSON (structured data)
python tools/query_facts.py time "today" --format json

# CSV (spreadsheet-friendly)
python tools/query_facts.py person "alice@example.com" --format csv

# Table (human-readable, default)
python tools/query_facts.py patterns --pattern-type todos --format table

# Markdown (documentation-friendly)
python tools/query_facts.py stats --time-range "last week" --format markdown
```

## Daily Summary CLI (`daily_summary.py`)

Generate comprehensive activity summaries and reports across all data sources.

### Basic Summary Generation

```bash
# Daily summary (default: yesterday)
python tools/daily_summary.py

# Specific date
python tools/daily_summary.py --date 2025-08-19

# Different periods
python tools/daily_summary.py --period week
python tools/daily_summary.py --period month --date 2025-08-01
```

### Person-Focused Summaries

```bash
# Summary for specific person
python tools/daily_summary.py --person "alice@example.com"
python tools/daily_summary.py --person "bob@company.com" --period week

# Detailed personal summary
python tools/daily_summary.py --person "alice@example.com" --detailed
```

### Output Formats and Files

```bash
# Different output formats
python tools/daily_summary.py --format json
python tools/daily_summary.py --format markdown
python tools/daily_summary.py --format table
python tools/daily_summary.py --format csv

# Save to file
python tools/daily_summary.py --output-file reports/daily_summary.json
python tools/daily_summary.py --output-file reports/weekly_report.md --period week
```

### Comparative Analysis

```bash
# Compare to previous periods
python tools/daily_summary.py --compare-to "last week"
python tools/daily_summary.py --compare-to "last month" --period month
python tools/daily_summary.py --compare-to "yesterday" --verbose
```

### Scheduled Execution

For automation and cron jobs:

```bash
# Scheduled mode (minimal output)
python tools/daily_summary.py --scheduled --output-file reports/daily.json

# Example cron job (daily at 8 AM)
# 0 8 * * * cd /path/to/aicos && python tools/daily_summary.py --scheduled --output-file reports/daily_$(date +\%Y\%m\%d).json
```

### Advanced Options

```bash
# Detailed analysis with trends
python tools/daily_summary.py --detailed --include-trends --period week

# Exclude weekend activity
python tools/daily_summary.py --exclude-weekends --period week

# Verbose output with performance info
python tools/daily_summary.py --verbose --compare-to "last week"
```

### Batch Processing

Generate summaries for date ranges:

```bash
# Generate summaries for a week
python tools/daily_summary.py batch 2025-08-01 2025-08-07

# With person focus and custom output
python tools/daily_summary.py batch 2025-08-15 2025-08-21 \
    --person "alice@example.com" \
    --output-dir reports/alice \
    --format json
```

## Common Workflows

### Daily Executive Briefing

```bash
#!/bin/bash
# Morning briefing workflow

echo "=== Daily Executive Briefing ==="

# Yesterday's activity overview
echo "📊 Yesterday's Activity:"
python tools/query_facts.py time "yesterday" --limit 5

# Key highlights summary
echo -e "\n📝 Daily Summary:"
python tools/daily_summary.py --date yesterday --format table

# Pending TODOs
echo -e "\n✅ Pending TODOs:"
python tools/query_facts.py patterns --pattern-type todos --time-range "today"

# Available meeting slots
echo -e "\n📅 Available Slots Today:"
python tools/query_facts.py calendar find-slots \
    --attendees "exec@company.com" --duration 30
```

### Weekly Team Coordination

```bash
#!/bin/bash
# Weekly team coordination workflow

TEAM_MEMBERS="alice@example.com,bob@example.com,charlie@example.com"

# Team activity summary
echo "📈 Weekly Team Summary:"
python tools/daily_summary.py --period week --detailed --include-trends

# Find team meeting slots
echo -e "\n📅 Team Meeting Slots:"
python tools/query_facts.py calendar find-slots \
    --attendees "$TEAM_MEMBERS" --duration 60

# Team mentions and decisions
echo -e "\n🗣️ Key Decisions:"
python tools/query_facts.py patterns --pattern-type decisions --time-range "this week"
```

### Monthly Reporting

```bash
#!/bin/bash
# Monthly reporting workflow

MONTH="2025-08"
OUTPUT_DIR="reports/${MONTH}"
mkdir -p "$OUTPUT_DIR"

# Generate comprehensive monthly report
python tools/daily_summary.py \
    --period month \
    --detailed \
    --include-trends \
    --compare-to "last month" \
    --format markdown \
    --output-file "${OUTPUT_DIR}/monthly_report.md"

# Activity statistics
python tools/query_facts.py stats \
    --time-range "this month" \
    --breakdown channel \
    --format json > "${OUTPUT_DIR}/channel_stats.json"

python tools/query_facts.py stats \
    --time-range "this month" \
    --breakdown person \
    --format json > "${OUTPUT_DIR}/person_stats.json"

# Pattern analysis
for pattern in todos mentions deadlines decisions; do
    python tools/query_facts.py patterns \
        --pattern-type "$pattern" \
        --time-range "this month" \
        --format json > "${OUTPUT_DIR}/${pattern}_patterns.json"
done

echo "Monthly reports generated in $OUTPUT_DIR"
```

## Environment Configuration

### Test Mode

Enable test mode for development and testing:

```bash
# Enable test mode
export AICOS_TEST_MODE=true

# Test mode features:
# - Uses mock data instead of real APIs
# - Bypasses credential validation
# - Shows "TEST MODE ACTIVE" indicator
# - Returns consistent test data

# Disable test mode
unset AICOS_TEST_MODE
```

### Configuration Options

```bash
# Custom configuration directory
export AICOS_CONFIG_DIR=/path/to/config

# Reports output directory
export AICOS_REPORTS_DIR=/path/to/reports

# Verbose logging
export AICOS_VERBOSE=true
```

### Performance Tuning

```bash
# For large datasets
python tools/query_facts.py time "last month" --limit 100

# For faster queries
python tools/query_facts.py person "alice@example.com" --time-range "today"

# Memory-efficient processing
python tools/daily_summary.py --exclude-weekends --period week
```

## Output Format Examples

### JSON Output

```json
{
  "results": [
    {
      "content": "Project milestone completed",
      "source": "slack",
      "date": "2025-08-19",
      "relevance_score": 0.95,
      "metadata": {
        "channel": "general",
        "author": "alice@example.com"
      }
    }
  ],
  "metadata": {
    "query_type": "time",
    "test_mode": true
  },
  "performance": {
    "execution_time_ms": 150,
    "result_count": 1
  },
  "count": 1
}
```

### CSV Output

```csv
content,source,date,relevance_score
"Project milestone completed",slack,2025-08-19,0.950
"Team meeting scheduled",calendar,2025-08-19,0.850
"Code review completed",slack,2025-08-19,0.800
```

### Table Output

```
1. SLACK | 2025-08-19 | Score: 0.950
   Project milestone completed

2. CALENDAR | 2025-08-19 | Score: 0.850
   Team meeting scheduled

3. SLACK | 2025-08-19 | Score: 0.800
   Code review completed
```

### Markdown Output

```markdown
# Query Results

## 1. SLACK | 2025-08-19 | Score: 0.950

Project milestone completed

## 2. CALENDAR | 2025-08-19 | Score: 0.850

Team meeting scheduled

## 3. SLACK | 2025-08-19 | Score: 0.800

Code review completed
```

## Error Handling and Troubleshooting

### Common Error Messages

**Invalid Time Expression:**
```bash
❌ Validation Error: Invalid time expression: invalid-time
💡 Suggestion: Use expressions like 'today', 'yesterday', 'last week', or specific dates like '2025-08-19'
```

**Missing Required Arguments:**
```bash
❌ Validation Error: Missing required argument: attendees
💡 Suggestion: Use --attendees with comma-separated email addresses
```

**Configuration Issues:**
```bash
❌ Configuration Error: AICOS_CONFIG_DIR not found
💡 Suggestion: Check configuration directory path or set AICOS_TEST_MODE=true for testing
```

### Debug Mode

Enable verbose output for debugging:

```bash
# Verbose mode shows:
# - Performance timing
# - Debug information
# - Technical details
python tools/query_facts.py time "today" --verbose
python tools/daily_summary.py --verbose
```

### Test Data Validation

```bash
# Verify test mode is working
export AICOS_TEST_MODE=true
python tools/query_facts.py time "today" --format json | grep "mock_mode"

# Should show: "mock_mode": true
```

### Performance Troubleshooting

**Slow Queries:**
- Use `--limit` to reduce result count
- Specify shorter time ranges
- Use `--source` to filter by data type

**Memory Issues:**
- Reduce query scope with time ranges
- Use streaming output formats
- Process data in smaller batches

**Database Lock Issues:**
- Ensure no concurrent operations
- Check for long-running processes
- Restart if persistent

## Integration Examples

### Slack Integration

```bash
# Find all mentions of a project
python tools/query_facts.py patterns --pattern-type mentions | grep "project-alpha"

# Get team channel activity
python tools/query_facts.py time "this week" --source slack --format csv
```

### Calendar Integration

```bash
# Check availability for this afternoon
python tools/query_facts.py calendar availability --person "alice@example.com" --date today

# Find slots avoiding conflicts
python tools/query_facts.py calendar check-conflicts \
    --attendees "alice@example.com,bob@example.com" \
    --start-time "2025-08-20T14:00:00" --duration 60
```

### Drive Integration

```bash
# Find document activity
python tools/query_facts.py time "last week" --source drive

# Pattern matching in documents
python tools/query_facts.py patterns --pattern-type todos --source drive
```

## Best Practices

### Query Optimization

1. **Use specific time ranges** for faster queries
2. **Filter by source** when possible (`--source slack`)
3. **Limit results** for large datasets (`--limit 20`)
4. **Use appropriate output formats** for your use case

### Automation

1. **Use scheduled mode** for cron jobs (`--scheduled`)
2. **Save to files** for persistent reports (`--output-file`)
3. **Handle errors gracefully** in scripts
4. **Use test mode** for development pipelines

### Data Analysis

1. **Start with broad queries**, then narrow down
2. **Use multiple formats** for different audiences
3. **Combine time and person filters** for targeted analysis
4. **Export CSV** for spreadsheet analysis

### Security

1. **Use test mode** for development
2. **Secure output files** with appropriate permissions
3. **Validate inputs** in automated scripts
4. **Monitor API usage** and rate limits

## Support and Resources

### Getting Help

```bash
# Command help
python tools/query_facts.py --help
python tools/query_facts.py time --help
python tools/daily_summary.py --help

# Interactive help
python tools/query_facts.py --interactive
# Then type: /help
```

### Version Information

```bash
python tools/query_facts.py --version
python tools/daily_summary.py --version
```

### System Information

```bash
# Check test mode status
python -c "import os; print('Test mode:', os.getenv('AICOS_TEST_MODE', 'false'))"

# Verify Python version
python --version  # Should be 3.10+
```

For additional support, refer to the project documentation or contact the development team.