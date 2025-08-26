# Security Guide - AI Chief of Staff

This document outlines the security measures, best practices, and considerations for the AI Chief of Staff system.

## Security Philosophy

The AI Chief of Staff system is designed with a **local-first, privacy-focused** approach:
- **No Cloud Dependencies**: All data processing occurs locally
- **Encrypted Storage**: Sensitive credentials are encrypted at rest
- **Audit Trails**: Complete transparency with source attribution
- **Minimal Surface Area**: Limited external API access points

## Data Security

### Local-First Architecture
- **All data remains on your infrastructure**
- No external data processing or cloud storage
- Sensitive organizational data never leaves your control
- API calls are limited to data collection only

### Data Storage Security
```bash
# Data directory structure with security considerations
data/
├── auth/                    # Encrypted credential storage
│   ├── credentials.json     # Google OAuth credentials
│   └── token.pickle         # Session tokens (consider replacing)
├── archive/                 # Raw data archives
│   └── [YYYY-MM-DD]/       # Daily directories for isolation
└── search.db               # Indexed data (local SQLite)
```

### Data Retention and Cleanup
```bash
# Configure data retention
DATA_RETENTION_DAYS=365

# Enable automatic cleanup
python tools/manage_archives.py --cleanup --age-days 365

# Secure deletion of old data
python tools/manage_archives.py --secure-delete --age-days 730
```

## Credential Management

### Environment Variables Security
```bash
# Secure .env file permissions
chmod 600 .env

# Ensure .env is in .gitignore
echo ".env" >> .gitignore
```

### Credential Storage
The system uses multiple layers of credential protection:

#### Google OAuth Credentials
- **Storage**: Encrypted JSON files in `data/auth/`
- **Encryption**: AES-256 with per-key random salts
- **Access**: Limited to authenticated processes only

#### Slack API Tokens
- **Storage**: Environment variables only (not persisted)
- **Scope**: Minimal required permissions
- **Rotation**: Regular token rotation recommended

### Best Practices for API Keys
1. **Generate dedicated API keys** for the Chief of Staff system
2. **Use minimum required permissions** for each API
3. **Rotate tokens regularly** (recommended: every 90 days)
4. **Monitor API usage** through respective consoles
5. **Revoke unused or old tokens** immediately

## API Security

### Slack API Security
```bash
# Required Slack scopes (minimal set)
channels:read        # Read channel information
channels:history     # Read public messages
groups:read         # Read private channel info
groups:history      # Read private messages
users:read          # Read user profiles
im:read            # Read DM information
im:history         # Read DM content
```

#### Slack Security Considerations
- Bot tokens are more secure than user tokens
- Enable audit logging in Slack workspace
- Regular review of bot permissions and channel access
- Monitor bot activity through Slack admin tools

### Google APIs Security
```bash
# Required Google API scopes (minimal set)
https://www.googleapis.com/auth/calendar.readonly
https://www.googleapis.com/auth/drive.metadata.readonly
```

#### Google Security Considerations
- Use OAuth 2.0 with PKCE when possible
- Enable 2FA on Google accounts with API access
- Regular review of OAuth consent and permissions
- Monitor API usage through Google Cloud Console

### Rate Limiting and Circuit Breakers
```python
# Built-in security through rate limiting
RATE_LIMIT_DELAY = 2  # seconds between requests
CIRCUIT_BREAKER_THRESHOLD = 5  # failed requests before circuit opens
CIRCUIT_BREAKER_TIMEOUT = 300  # seconds before retry
```

## Network Security

### Outbound Connections
The system makes connections to:
- `slack.com` - Slack API endpoints
- `googleapis.com` - Google Calendar/Drive APIs
- No other external connections required

### Firewall Configuration
```bash
# Allow outbound HTTPS to required domains only
# Block all other outbound connections
# No inbound connections required (local-only operation)
```

### TLS/SSL Verification
- All API connections use TLS 1.2+
- Certificate pinning implemented for critical endpoints
- SSL verification cannot be disabled in production

## Access Control

### File System Permissions
```bash
# Secure file permissions
chmod 700 data/                    # Data directory: owner only
chmod 600 data/auth/*             # Credential files: owner read/write only
chmod 644 data/archive/*.jsonl    # Archive data: owner write, others read
chmod 600 .env                    # Environment: owner read/write only
```

### Database Security
```bash
# SQLite security settings
PRAGMA journal_mode = WAL;        # Write-ahead logging for consistency
PRAGMA synchronous = FULL;        # Full durability
PRAGMA temp_store = memory;       # Temporary data in memory only
PRAGMA secure_delete = ON;        # Secure deletion of data
```

### Process Security
- Run with minimal required privileges
- No root/administrator privileges required
- Isolated Python virtual environment
- No network listener processes

## Monitoring and Auditing

### Security Event Logging
```python
# Security events are logged with full context
- Failed authentication attempts
- API rate limit violations
- Unusual data access patterns
- Credential refresh events
- System configuration changes
```

### Audit Trail
Every piece of processed information includes:
- **Source attribution** (exact file and line)
- **Collection timestamp**
- **Processing metadata**
- **API call traces**

### Log Management
```bash
# Log rotation and retention
LOG_RETENTION_DAYS=90
LOG_MAX_SIZE=100MB

# Secure log permissions
chmod 640 logs/*.log
```

## Production Security Hardening

### Environment Hardening
```bash
# Disable test mode in production
AICOS_TEST_MODE=false

# Enable production security features
SECURITY_ENHANCED=true

# Set restrictive logging
LOG_LEVEL=WARNING
```

### System Hardening
1. **Disable unnecessary services** on the host system
2. **Enable automatic security updates**
3. **Configure host-based firewall rules**
4. **Enable file integrity monitoring**
5. **Regular security patching schedule**

### Backup Security
```bash
# Encrypted backups
python tools/manage_archives.py --backup --encrypt

# Secure backup storage with limited retention
BACKUP_RETENTION_DAYS=30
BACKUP_ENCRYPTION_KEY_ROTATION_DAYS=90
```

## Incident Response

### Security Incident Procedures
1. **Immediate containment**
   - Stop all data collection processes
   - Rotate all API keys and tokens
   - Preserve system state for analysis

2. **Assessment**
   - Review audit logs for unauthorized access
   - Check API usage logs for anomalies
   - Verify data integrity

3. **Recovery**
   - Address identified vulnerabilities
   - Restore from clean backups if necessary
   - Update security configurations

### Emergency Procedures
```bash
# Emergency shutdown
python tools/emergency_shutdown.py

# Credential rotation
python tools/rotate_all_credentials.py

# Clean restart
python tools/secure_restart.py
```

## Compliance Considerations

### Data Privacy
- **GDPR**: Personal data processing under legitimate interest
- **CCPA**: Employee data with proper notice
- **PIPEDA**: Reasonable organizational purposes

### Data Minimization
- Collect only necessary organizational data
- Regular purging of old data
- Anonymization where possible

### Organizational Policies
- Employee privacy notification recommended
- Data retention policy alignment
- Information security policy compliance

## Security Testing

### Regular Security Validation
```bash
# Run security tests
python -m pytest tests/security/ -v

# Credential validation
python tools/validate_security.py

# Permission auditing
python tools/audit_permissions.py
```

### Penetration Testing
- External security assessment recommended annually
- Focus on credential handling and data access
- API security and rate limiting validation

## Contact and Reporting

For security issues or concerns:
1. **Do not** file public issues for security problems
2. Contact system administrators directly
3. Document all security-related incidents
4. Follow organizational incident response procedures

This security model provides defense-in-depth while maintaining the system's core functionality and ease of use.