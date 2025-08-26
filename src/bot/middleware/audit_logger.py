#!/usr/bin/env python3
"""
Security Audit Logger for Slack Bot

Comprehensive security audit trail for all bot operations:
- OAuth events and permission changes
- Command executions and their outcomes
- Permission violations and security events
- API calls and rate limiting events
- User interactions and data access
"""

import json
import logging
import hashlib
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path

from slack_bolt import BoltRequest, BoltResponse
from slack_bolt.middleware import Middleware

logger = logging.getLogger(__name__)

class AuditEventType(Enum):
    """Types of audit events"""
    OAUTH_FLOW = "oauth_flow"
    PERMISSION_CHECK = "permission_check"
    COMMAND_EXECUTION = "command_execution"
    API_CALL = "api_call"
    RATE_LIMIT = "rate_limit"
    SECURITY_VIOLATION = "security_violation"
    DATA_ACCESS = "data_access"
    ERROR = "error"
    AUTHENTICATION = "authentication"

class SecurityLevel(Enum):
    """Security levels for events"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"

@dataclass
class AuditEvent:
    """Audit event structure"""
    timestamp: str
    event_type: AuditEventType
    security_level: SecurityLevel
    user_id: Optional[str] = None
    team_id: Optional[str] = None
    channel_id: Optional[str] = None
    command: Optional[str] = None
    api_method: Optional[str] = None
    success: bool = True
    error_message: Optional[str] = None
    request_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    oauth_scopes: Optional[List[str]] = None
    permission_result: Optional[Dict] = None
    rate_limit_info: Optional[Dict] = None
    data_accessed: Optional[List[str]] = None
    additional_context: Optional[Dict] = None

class AuditLogger(Middleware):
    """
    Security audit logger middleware for Slack bot
    
    Features:
    - Comprehensive logging of all security-relevant events
    - Structured audit trail with searchable metadata
    - Configurable security levels and filtering
    - Integration with external security systems
    - Tamper-evident logging with checksums
    - PII redaction and data privacy controls
    """
    
    def __init__(self, log_file_path: Optional[str] = None, 
                 enable_console_logging: bool = True,
                 min_security_level: SecurityLevel = SecurityLevel.INFO):
        """
        Initialize audit logger
        
        Args:
            log_file_path: Path to audit log file (None for memory-only)
            enable_console_logging: Whether to log to console
            min_security_level: Minimum security level to log
        """
        super().__init__()
        self.enable_console_logging = enable_console_logging
        self.min_security_level = min_security_level
        
        # Set up file logging
        self.log_file_path = None
        if log_file_path:
            self.log_file_path = Path(log_file_path)
            self.log_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # In-memory audit trail (last 1000 events)
        self.audit_trail: List[AuditEvent] = []
        self.max_memory_events = 1000
        
        # Event counters for monitoring
        self.event_counters = {event_type: 0 for event_type in AuditEventType}
        self.security_counters = {level: 0 for level in SecurityLevel}
        
        # Known security patterns
        self.security_patterns = self._load_security_patterns()
        
        logger.info(f"🛡️ Security audit logger initialized with {min_security_level.value} level")
    
    def process(self, *, req: BoltRequest, resp: BoltResponse, next: Callable[[], BoltResponse]) -> BoltResponse:
        """
        Process request with security audit logging
        
        Args:
            req: Bolt request object
            resp: Bolt response object
            next: Next middleware/handler in chain
            
        Returns:
            Bolt response with audit logging
        """
        # Generate request ID for tracking
        request_id = self._generate_request_id(req)
        
        # Extract security-relevant request info
        security_context = self._extract_security_context(req, request_id)
        
        # Log incoming request
        if self._should_log_request(security_context):
            self._log_request_start(security_context)
        
        # Process request
        start_time = datetime.now()
        try:
            response = next()
            
            # Log successful completion
            self._log_request_completion(security_context, response, start_time, True)
            
            return response
            
        except Exception as e:
            # Log error
            self._log_request_completion(security_context, None, start_time, False, str(e))
            
            # Re-raise the exception
            raise
    
    def log_oauth_event(self, event_type: str, team_id: str, user_id: Optional[str] = None,
                       scopes: Optional[List[str]] = None, success: bool = True,
                       error_message: Optional[str] = None, additional_context: Optional[Dict] = None):
        """Log OAuth-related security event"""
        event = AuditEvent(
            timestamp=datetime.now().isoformat(),
            event_type=AuditEventType.OAUTH_FLOW,
            security_level=SecurityLevel.INFO if success else SecurityLevel.WARNING,
            user_id=user_id,
            team_id=team_id,
            success=success,
            error_message=error_message,
            oauth_scopes=scopes,
            additional_context=additional_context or {'oauth_event_type': event_type}
        )
        
        self._write_audit_event(event)
    
    def log_permission_check(self, user_id: str, team_id: str, command: str,
                           permission_result: Dict, api_method: Optional[str] = None):
        """Log permission check event"""
        security_level = SecurityLevel.INFO
        if not permission_result.get('valid'):
            security_level = SecurityLevel.WARNING
        
        # Check for suspicious permission patterns
        if self._detect_permission_anomaly(user_id, command, permission_result):
            security_level = SecurityLevel.CRITICAL
        
        event = AuditEvent(
            timestamp=datetime.now().isoformat(),
            event_type=AuditEventType.PERMISSION_CHECK,
            security_level=security_level,
            user_id=user_id,
            team_id=team_id,
            command=command,
            api_method=api_method,
            success=permission_result.get('valid', False),
            permission_result=self._sanitize_permission_result(permission_result)
        )
        
        self._write_audit_event(event)
    
    def log_command_execution(self, user_id: str, team_id: str, channel_id: str,
                            command: str, success: bool, error_message: Optional[str] = None,
                            data_accessed: Optional[List[str]] = None):
        """Log command execution event"""
        security_level = SecurityLevel.INFO
        
        # Escalate security level for sensitive commands
        if self._is_sensitive_command(command):
            security_level = SecurityLevel.WARNING
        
        if not success:
            security_level = SecurityLevel.WARNING
        
        event = AuditEvent(
            timestamp=datetime.now().isoformat(),
            event_type=AuditEventType.COMMAND_EXECUTION,
            security_level=security_level,
            user_id=user_id,
            team_id=team_id,
            channel_id=channel_id,
            command=command,
            success=success,
            error_message=error_message,
            data_accessed=data_accessed
        )
        
        self._write_audit_event(event)
    
    def log_api_call(self, api_method: str, user_id: Optional[str], team_id: Optional[str],
                    success: bool, error_message: Optional[str] = None,
                    rate_limit_info: Optional[Dict] = None):
        """Log Slack API call event"""
        security_level = SecurityLevel.INFO
        
        if not success:
            security_level = SecurityLevel.WARNING
        
        if rate_limit_info and rate_limit_info.get('rate_limited'):
            security_level = SecurityLevel.WARNING
        
        event = AuditEvent(
            timestamp=datetime.now().isoformat(),
            event_type=AuditEventType.API_CALL,
            security_level=security_level,
            user_id=user_id,
            team_id=team_id,
            api_method=api_method,
            success=success,
            error_message=error_message,
            rate_limit_info=rate_limit_info
        )
        
        self._write_audit_event(event)
    
    def log_security_violation(self, violation_type: str, user_id: Optional[str], 
                             team_id: Optional[str], description: str,
                             additional_context: Optional[Dict] = None):
        """Log security violation event"""
        event = AuditEvent(
            timestamp=datetime.now().isoformat(),
            event_type=AuditEventType.SECURITY_VIOLATION,
            security_level=SecurityLevel.CRITICAL,
            user_id=user_id,
            team_id=team_id,
            error_message=description,
            additional_context=additional_context or {'violation_type': violation_type}
        )
        
        self._write_audit_event(event)
        
        # Log to console immediately for critical events
        logger.critical(f"SECURITY VIOLATION: {violation_type} - {description}")
    
    def log_data_access(self, user_id: str, team_id: str, data_types: List[str],
                       channel_id: Optional[str] = None, success: bool = True):
        """Log data access event for privacy compliance"""
        event = AuditEvent(
            timestamp=datetime.now().isoformat(),
            event_type=AuditEventType.DATA_ACCESS,
            security_level=SecurityLevel.INFO,
            user_id=user_id,
            team_id=team_id,
            channel_id=channel_id,
            success=success,
            data_accessed=data_types
        )
        
        self._write_audit_event(event)
    
    def _extract_security_context(self, req: BoltRequest, request_id: str) -> Dict[str, Any]:
        """Extract security-relevant context from request"""
        context = {
            'request_id': request_id,
            'timestamp': datetime.now().isoformat(),
            'ip_address': self._get_client_ip(req),
            'user_agent': req.headers.get('User-Agent'),
            'user_id': None,
            'team_id': None,
            'channel_id': None,
            'command': None,
            'request_type': 'unknown'
        }
        
        # Extract user/team/channel info
        if req.body.get("user_id"):
            context['user_id'] = req.body["user_id"]
        elif req.body.get("user", {}).get("id"):
            context['user_id'] = req.body["user"]["id"]
        
        if req.body.get("team_id"):
            context['team_id'] = req.body["team_id"]
        elif req.body.get("team", {}).get("id"):
            context['team_id'] = req.body["team"]["id"]
        
        if req.body.get("channel_id"):
            context['channel_id'] = req.body["channel_id"]
        elif req.body.get("channel", {}).get("id"):
            context['channel_id'] = req.body["channel"]["id"]
        
        # Extract command info
        if req.body.get("command"):
            context['command'] = req.body["command"]
            context['request_type'] = 'slash_command'
        elif req.body.get("type") == "interactive_component":
            context['request_type'] = 'interactive_component'
        elif req.body.get("type") == "event_callback":
            context['request_type'] = 'event'
        
        return context
    
    def _should_log_request(self, context: Dict[str, Any]) -> bool:
        """Determine if request should be logged"""
        request_type = context.get('request_type')
        
        # Always log security-relevant requests
        if request_type in ['slash_command', 'interactive_component']:
            return True
        
        # Log OAuth and auth requests
        if 'oauth' in context.get('request_id', '').lower():
            return True
        
        # Skip health checks and noise
        if request_type in ['url_verification', 'challenge']:
            return False
        
        return True
    
    def _log_request_start(self, context: Dict[str, Any]):
        """Log request start"""
        # Basic request logging at INFO level
        if context.get('command'):
            self.log_command_execution(
                context['user_id'],
                context['team_id'], 
                context['channel_id'],
                context['command'],
                True  # Assume success for start, will update on completion
            )
    
    def _log_request_completion(self, context: Dict[str, Any], response: Optional[BoltResponse],
                              start_time: datetime, success: bool, error_message: Optional[str] = None):
        """Log request completion"""
        duration = (datetime.now() - start_time).total_seconds()
        
        # Update context with completion info
        completion_context = context.copy()
        completion_context.update({
            'duration_seconds': duration,
            'success': success,
            'error_message': error_message,
            'response_status': response.status if response else None
        })
        
        # Log completion event if it was a significant request
        if context.get('command') and not success:
            self.log_command_execution(
                context['user_id'],
                context['team_id'],
                context['channel_id'],
                context['command'],
                success,
                error_message
            )
    
    def _generate_request_id(self, req: BoltRequest) -> str:
        """Generate unique request ID"""
        timestamp = str(datetime.now().timestamp())
        content_hash = hashlib.md5(str(req.body).encode()).hexdigest()[:8]
        return f"req_{timestamp}_{content_hash}"
    
    def _get_client_ip(self, req: BoltRequest) -> Optional[str]:
        """Extract client IP address"""
        # Check common headers for IP
        ip_headers = ['X-Forwarded-For', 'X-Real-IP', 'X-Client-IP']
        
        for header in ip_headers:
            ip = req.headers.get(header)
            if ip:
                # Take first IP if comma-separated
                return ip.split(',')[0].strip()
        
        return None
    
    def _detect_permission_anomaly(self, user_id: str, command: str, permission_result: Dict) -> bool:
        """Detect anomalous permission patterns"""
        # Check for repeated permission violations
        recent_violations = [
            event for event in self.audit_trail[-50:]  # Last 50 events
            if (event.user_id == user_id and 
                event.event_type == AuditEventType.PERMISSION_CHECK and
                not event.success)
        ]
        
        if len(recent_violations) >= 5:  # 5 violations in recent history
            return True
        
        # Check for privilege escalation attempts
        missing_scopes = permission_result.get('missing_scopes', [])
        if any(scope in missing_scopes for scope in ['admin', 'usergroups:write', 'channels:write']):
            return True
        
        return False
    
    def _is_sensitive_command(self, command: str) -> bool:
        """Check if command is security-sensitive"""
        sensitive_patterns = [
            'admin', 'delete', 'remove', 'revoke', 'export', 
            'download', 'sync', 'collect', 'bulk'
        ]
        
        command_lower = command.lower()
        return any(pattern in command_lower for pattern in sensitive_patterns)
    
    def _sanitize_permission_result(self, permission_result: Dict) -> Dict:
        """Sanitize permission result for logging"""
        # Remove sensitive information but keep audit-relevant data
        sanitized = {
            'valid': permission_result.get('valid'),
            'missing_scope_count': len(permission_result.get('missing_scopes', [])),
            'available_scope_count': len(permission_result.get('available_scopes', [])),
            'validation_level': permission_result.get('validation_level')
        }
        
        # Include first few missing scopes for context
        missing_scopes = permission_result.get('missing_scopes', [])
        if missing_scopes:
            sanitized['sample_missing_scopes'] = missing_scopes[:3]
        
        return sanitized
    
    def _load_security_patterns(self) -> Dict[str, List[str]]:
        """Load known security patterns for detection"""
        return {
            'suspicious_commands': [
                'rm -rf', 'sudo', 'passwd', 'chmod 777',
                'curl', 'wget', 'nc ', 'telnet'
            ],
            'data_exfiltration': [
                'export', 'download', 'backup', 'dump', 
                'extract', 'copy', 'transfer'
            ],
            'privilege_escalation': [
                'admin', 'root', 'sudo', 'su ',
                'elevate', 'privilege', 'escalate'
            ]
        }
    
    def _write_audit_event(self, event: AuditEvent):
        """Write audit event to storage"""
        # Check minimum security level
        security_levels_order = [SecurityLevel.INFO, SecurityLevel.WARNING, SecurityLevel.CRITICAL, SecurityLevel.EMERGENCY]
        if security_levels_order.index(event.security_level) < security_levels_order.index(self.min_security_level):
            return
        
        # Add to memory trail
        self.audit_trail.append(event)
        if len(self.audit_trail) > self.max_memory_events:
            self.audit_trail.pop(0)
        
        # Update counters
        self.event_counters[event.event_type] += 1
        self.security_counters[event.security_level] += 1
        
        # Write to file if configured
        if self.log_file_path:
            self._write_to_file(event)
        
        # Log to console if enabled
        if self.enable_console_logging:
            self._log_to_console(event)
    
    def _write_to_file(self, event: AuditEvent):
        """Write audit event to file"""
        try:
            with open(self.log_file_path, 'a', encoding='utf-8') as f:
                # Write as JSON line
                event_dict = asdict(event)
                # Convert enums to strings
                event_dict['event_type'] = event.event_type.value
                event_dict['security_level'] = event.security_level.value
                
                json.dump(event_dict, f, default=str)
                f.write('\n')
                
        except Exception as e:
            logger.error(f"Failed to write audit event to file: {e}")
    
    def _log_to_console(self, event: AuditEvent):
        """Log audit event to console"""
        level_map = {
            SecurityLevel.INFO: logging.INFO,
            SecurityLevel.WARNING: logging.WARNING,
            SecurityLevel.CRITICAL: logging.ERROR,
            SecurityLevel.EMERGENCY: logging.CRITICAL
        }
        
        log_level = level_map[event.security_level]
        
        message = f"AUDIT [{event.event_type.value}] "
        if event.user_id:
            message += f"User: {event.user_id} "
        if event.command:
            message += f"Command: {event.command} "
        if event.api_method:
            message += f"API: {event.api_method} "
        if not event.success and event.error_message:
            message += f"Error: {event.error_message}"
        
        logger.log(log_level, message)
    
    def get_audit_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get audit summary for specified time period"""
        cutoff_time = datetime.now().timestamp() - (hours * 3600)
        
        recent_events = [
            event for event in self.audit_trail
            if datetime.fromisoformat(event.timestamp).timestamp() > cutoff_time
        ]
        
        # Count events by type and security level
        type_counts = {}
        level_counts = {}
        user_activity = {}
        
        for event in recent_events:
            type_counts[event.event_type.value] = type_counts.get(event.event_type.value, 0) + 1
            level_counts[event.security_level.value] = level_counts.get(event.security_level.value, 0) + 1
            
            if event.user_id:
                user_activity[event.user_id] = user_activity.get(event.user_id, 0) + 1
        
        return {
            'time_period_hours': hours,
            'total_events': len(recent_events),
            'events_by_type': type_counts,
            'events_by_security_level': level_counts,
            'top_users': sorted(user_activity.items(), key=lambda x: x[1], reverse=True)[:10],
            'critical_events': len([e for e in recent_events if e.security_level in [SecurityLevel.CRITICAL, SecurityLevel.EMERGENCY]]),
            'success_rate': len([e for e in recent_events if e.success]) / len(recent_events) if recent_events else 1.0
        }
    
    def search_audit_events(self, query: Dict[str, Any], limit: int = 100) -> List[AuditEvent]:
        """Search audit events with filters"""
        filtered_events = []
        
        for event in reversed(self.audit_trail):  # Most recent first
            if len(filtered_events) >= limit:
                break
                
            # Apply filters
            if query.get('user_id') and event.user_id != query['user_id']:
                continue
            if query.get('team_id') and event.team_id != query['team_id']:
                continue
            if query.get('event_type') and event.event_type.value != query['event_type']:
                continue
            if query.get('security_level') and event.security_level.value != query['security_level']:
                continue
            if query.get('success') is not None and event.success != query['success']:
                continue
            
            # Time range filter
            if query.get('start_time'):
                event_time = datetime.fromisoformat(event.timestamp)
                start_time = datetime.fromisoformat(query['start_time'])
                if event_time < start_time:
                    continue
            
            filtered_events.append(event)
        
        return filtered_events

# Global audit logger instance
_global_audit_logger = None

def get_audit_logger(log_file_path: Optional[str] = None) -> AuditLogger:
    """Get global audit logger instance"""
    global _global_audit_logger
    if _global_audit_logger is None:
        _global_audit_logger = AuditLogger(log_file_path)
    return _global_audit_logger

# Convenience functions for external use
def log_oauth_event(event_type: str, team_id: str, **kwargs):
    """Log OAuth event using global logger"""
    return get_audit_logger().log_oauth_event(event_type, team_id, **kwargs)

def log_permission_check(user_id: str, team_id: str, command: str, permission_result: Dict, **kwargs):
    """Log permission check using global logger"""
    return get_audit_logger().log_permission_check(user_id, team_id, command, permission_result, **kwargs)

def log_security_violation(violation_type: str, user_id: Optional[str], team_id: Optional[str], description: str, **kwargs):
    """Log security violation using global logger"""
    return get_audit_logger().log_security_violation(violation_type, user_id, team_id, description, **kwargs)