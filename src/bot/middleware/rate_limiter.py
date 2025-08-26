#!/usr/bin/env python3
"""
Dual-Mode Rate Limiter for Slack Bot

Implements dual-mode rate limiting:
- Interactive mode: ≤1s response time for user commands  
- Bulk mode: ≥2s intervals for data collection operations

Integrates with existing rate limiting patterns from slack_collector.py
"""

import time
import logging
import threading
from typing import Dict, Optional, Callable, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
from collections import defaultdict, deque

from slack_bolt import BoltRequest, BoltResponse
from slack_bolt.middleware import Middleware

logger = logging.getLogger(__name__)

class RateLimitMode(Enum):
    """Rate limiting modes"""
    INTERACTIVE = "interactive"    # Fast response for user commands (≤1s)
    BULK = "bulk"                 # Conservative for bulk operations (≥2s)
    DISABLED = "disabled"         # No rate limiting

@dataclass
class RateLimitConfig:
    """Rate limiting configuration"""
    mode: RateLimitMode
    requests_per_minute: int
    burst_allowance: int
    cooldown_seconds: float
    backoff_multiplier: float = 2.0
    max_backoff_seconds: float = 600.0  # 10 minutes

class RateLimitBucket:
    """Token bucket for rate limiting"""
    
    def __init__(self, capacity: int, refill_rate: float):
        """
        Initialize rate limit bucket
        
        Args:
            capacity: Maximum tokens in bucket
            refill_rate: Tokens per second refill rate
        """
        self.capacity = capacity
        self.tokens = float(capacity)
        self.refill_rate = refill_rate
        self.last_refill = time.time()
        self.lock = threading.Lock()
    
    def consume(self, tokens: int = 1) -> bool:
        """
        Try to consume tokens from bucket
        
        Args:
            tokens: Number of tokens to consume
            
        Returns:
            True if tokens consumed, False if not available
        """
        with self.lock:
            now = time.time()
            
            # Refill tokens based on elapsed time
            elapsed = now - self.last_refill
            self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
            self.last_refill = now
            
            # Try to consume tokens
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            
            return False
    
    def wait_time(self, tokens: int = 1) -> float:
        """
        Calculate wait time until tokens available
        
        Args:
            tokens: Number of tokens needed
            
        Returns:
            Wait time in seconds
        """
        with self.lock:
            if self.tokens >= tokens:
                return 0.0
            
            needed_tokens = tokens - self.tokens
            return needed_tokens / self.refill_rate

class RateLimiter(Middleware):
    """
    Dual-mode rate limiter for Slack bot operations
    
    Features:
    - Interactive mode: Fast responses for user commands
    - Bulk mode: Conservative rate limiting for data operations  
    - Per-user and per-team rate limiting
    - Exponential backoff on repeated limit hits
    - Integration with Slack's rate limiting headers
    """
    
    def __init__(self, default_mode: RateLimitMode = RateLimitMode.INTERACTIVE):
        """
        Initialize rate limiter
        
        Args:
            default_mode: Default rate limiting mode
        """
        super().__init__()
        self.default_mode = default_mode
        
        # Rate limiting configurations
        self.configs = {
            RateLimitMode.INTERACTIVE: RateLimitConfig(
                mode=RateLimitMode.INTERACTIVE,
                requests_per_minute=60,      # 1 request per second
                burst_allowance=10,          # Allow bursts up to 10
                cooldown_seconds=0.5,        # Quick cooldown
                backoff_multiplier=1.5       # Gentle backoff
            ),
            RateLimitMode.BULK: RateLimitConfig(
                mode=RateLimitMode.BULK,
                requests_per_minute=30,      # 1 request per 2 seconds
                burst_allowance=5,           # Small burst allowance
                cooldown_seconds=2.0,        # 2 second minimum
                backoff_multiplier=2.0       # Standard backoff
            )
        }
        
        # Per-user/team rate limiting buckets
        self.user_buckets: Dict[str, RateLimitBucket] = {}
        self.team_buckets: Dict[str, RateLimitBucket] = {}
        
        # Backoff tracking
        self.backoff_state: Dict[str, Dict] = defaultdict(dict)
        
        # Request history for analytics
        self.request_history: deque = deque(maxlen=1000)
        
        # Thread lock for bucket management
        self.bucket_lock = threading.Lock()
        
        logger.info(f"⏱️ Rate limiter initialized with default mode: {default_mode.value}")
    
    def process(self, *, req: BoltRequest, resp: BoltResponse, next: Callable[[], BoltResponse]) -> BoltResponse:
        """
        Process request with rate limiting
        
        Args:
            req: Bolt request object
            resp: Bolt response object
            next: Next middleware/handler in chain
            
        Returns:
            Bolt response (possibly rate limited)
        """
        try:
            # Extract request metadata
            user_id = self._extract_user_id(req)
            team_id = self._extract_team_id(req)
            request_type = self._classify_request(req)
            
            # Determine rate limiting mode
            rate_mode = self._determine_rate_mode(req, request_type)
            
            if rate_mode == RateLimitMode.DISABLED:
                return next()
            
            # Check rate limits
            rate_limit_result = self._check_rate_limits(user_id, team_id, rate_mode)
            
            if not rate_limit_result['allowed']:
                return self._handle_rate_limit_exceeded(req, resp, rate_limit_result, rate_mode)
            
            # Record request start time
            start_time = time.time()
            
            # Process request
            response = next()
            
            # Record request completion
            end_time = time.time()
            self._record_request(user_id, team_id, request_type, rate_mode, start_time, end_time)
            
            # Check Slack's rate limit headers and adjust if needed
            self._handle_slack_rate_limit_headers(response, user_id, team_id)
            
            return response
            
        except Exception as e:
            logger.error(f"Rate limiter error: {e}")
            # On error, allow through to avoid blocking bot
            return next()
    
    def _extract_user_id(self, req: BoltRequest) -> Optional[str]:
        """Extract user ID from request"""
        # Try different locations where user ID might be
        if req.body.get("user_id"):
            return req.body["user_id"]
        elif req.body.get("user", {}).get("id"):
            return req.body["user"]["id"]
        elif req.body.get("event", {}).get("user"):
            return req.body["event"]["user"]
        
        return None
    
    def _extract_team_id(self, req: BoltRequest) -> Optional[str]:
        """Extract team ID from request"""
        if req.body.get("team_id"):
            return req.body["team_id"]
        elif req.body.get("team", {}).get("id"):
            return req.body["team"]["id"]
        
        return None
    
    def _classify_request(self, req: BoltRequest) -> str:
        """Classify request type for rate limiting purposes"""
        # Slash commands
        if req.body.get("command"):
            return "slash_command"
        
        # Interactive components
        if req.body.get("type") == "interactive_component":
            return "interactive_component"
        
        # Events
        if req.body.get("type") == "event_callback":
            return "event"
        
        # OAuth flow
        if "oauth" in req.path.lower():
            return "oauth"
        
        # Default
        return "unknown"
    
    def _determine_rate_mode(self, req: BoltRequest, request_type: str) -> RateLimitMode:
        """Determine appropriate rate limiting mode for request"""
        # OAuth and health checks - no rate limiting
        if request_type in ["oauth", "url_verification"]:
            return RateLimitMode.DISABLED
        
        # Interactive user commands - fast mode
        if request_type in ["slash_command", "interactive_component"]:
            return RateLimitMode.INTERACTIVE
        
        # Bulk operations - conservative mode  
        if request_type == "event":
            return RateLimitMode.BULK
        
        # Check for bulk operation indicators
        command_text = req.body.get("text", "").lower()
        if any(keyword in command_text for keyword in ["collect", "sync", "bulk", "all"]):
            return RateLimitMode.BULK
        
        return self.default_mode
    
    def _get_bucket(self, key: str, config: RateLimitConfig) -> RateLimitBucket:
        """Get or create rate limiting bucket for key"""
        bucket_dict = self.user_buckets if key.startswith("user:") else self.team_buckets
        
        with self.bucket_lock:
            if key not in bucket_dict:
                bucket_dict[key] = RateLimitBucket(
                    capacity=config.burst_allowance,
                    refill_rate=config.requests_per_minute / 60.0  # per second
                )
            
            return bucket_dict[key]
    
    def _check_rate_limits(self, user_id: Optional[str], team_id: Optional[str], 
                          rate_mode: RateLimitMode) -> Dict[str, Any]:
        """Check if request is within rate limits"""
        config = self.configs[rate_mode]
        
        # Check user-level rate limit
        user_allowed = True
        user_wait_time = 0.0
        
        if user_id:
            user_key = f"user:{user_id}"
            user_bucket = self._get_bucket(user_key, config)
            user_allowed = user_bucket.consume()
            
            if not user_allowed:
                user_wait_time = user_bucket.wait_time()
        
        # Check team-level rate limit (more generous)
        team_allowed = True
        team_wait_time = 0.0
        
        if team_id:
            team_key = f"team:{team_id}"
            # Team bucket gets 3x the capacity
            team_config = RateLimitConfig(
                mode=rate_mode,
                requests_per_minute=config.requests_per_minute * 3,
                burst_allowance=config.burst_allowance * 3,
                cooldown_seconds=config.cooldown_seconds
            )
            
            team_bucket = self._get_bucket(team_key, team_config)
            team_allowed = team_bucket.consume()
            
            if not team_allowed:
                team_wait_time = team_bucket.wait_time()
        
        # Apply backoff if user has been rate limited recently
        backoff_key = user_id or team_id or "unknown"
        backoff_wait = self._get_backoff_wait_time(backoff_key)
        
        allowed = user_allowed and team_allowed and (backoff_wait == 0)
        total_wait_time = max(user_wait_time, team_wait_time, backoff_wait)
        
        return {
            'allowed': allowed,
            'wait_time': total_wait_time,
            'user_allowed': user_allowed,
            'team_allowed': team_allowed,
            'backoff_wait': backoff_wait,
            'rate_mode': rate_mode
        }
    
    def _get_backoff_wait_time(self, key: str) -> float:
        """Get exponential backoff wait time"""
        if key not in self.backoff_state:
            return 0.0
        
        backoff_info = self.backoff_state[key]
        last_backoff = backoff_info.get('last_backoff', 0)
        consecutive_limits = backoff_info.get('consecutive_limits', 0)
        
        if consecutive_limits == 0:
            return 0.0
        
        # Calculate backoff time
        base_backoff = 2.0  # Start with 2 seconds
        backoff_time = min(
            base_backoff * (2 ** (consecutive_limits - 1)),
            600.0  # Max 10 minutes
        )
        
        elapsed = time.time() - last_backoff
        remaining_backoff = max(0, backoff_time - elapsed)
        
        return remaining_backoff
    
    def _handle_rate_limit_exceeded(self, req: BoltRequest, resp: BoltResponse,
                                  rate_limit_result: Dict[str, Any], 
                                  rate_mode: RateLimitMode) -> BoltResponse:
        """Handle rate limit exceeded"""
        wait_time = rate_limit_result['wait_time']
        user_id = self._extract_user_id(req)
        
        # Update backoff state
        backoff_key = user_id or self._extract_team_id(req) or "unknown"
        self._update_backoff_state(backoff_key)
        
        # Log rate limit
        logger.warning(f"Rate limit exceeded for user {user_id}, mode: {rate_mode.value}, wait: {wait_time:.1f}s")
        
        # Return rate limit response
        resp.status = 429
        resp.headers["Retry-After"] = str(int(wait_time) + 1)
        
        # For interactive commands, return user-friendly message
        if rate_mode == RateLimitMode.INTERACTIVE:
            resp.body = {
                "response_type": "ephemeral",
                "text": "⏳ Slow down!",
                "attachments": [
                    {
                        "color": "warning",
                        "fields": [
                            {
                                "title": "Rate Limit Reached",
                                "value": f"Please wait {wait_time:.0f} seconds before trying again.\n\n"
                                        f"This helps keep the bot responsive for everyone! 🤖",
                                "short": False
                            }
                        ]
                    }
                ]
            }
        else:
            resp.body = {
                "error": "rate_limited",
                "message": f"Rate limit exceeded. Try again in {wait_time:.0f} seconds."
            }
        
        return resp
    
    def _update_backoff_state(self, key: str):
        """Update exponential backoff state"""
        now = time.time()
        
        if key not in self.backoff_state:
            self.backoff_state[key] = {
                'consecutive_limits': 1,
                'last_backoff': now,
                'first_limit': now
            }
        else:
            backoff_info = self.backoff_state[key]
            
            # Reset if it's been a while since last rate limit
            if now - backoff_info['last_backoff'] > 300:  # 5 minutes
                backoff_info['consecutive_limits'] = 1
                backoff_info['first_limit'] = now
            else:
                backoff_info['consecutive_limits'] += 1
            
            backoff_info['last_backoff'] = now
    
    def _record_request(self, user_id: Optional[str], team_id: Optional[str],
                       request_type: str, rate_mode: RateLimitMode,
                       start_time: float, end_time: float):
        """Record request for analytics"""
        request_record = {
            'timestamp': datetime.fromtimestamp(start_time).isoformat(),
            'user_id': user_id,
            'team_id': team_id,
            'request_type': request_type,
            'rate_mode': rate_mode.value,
            'duration': end_time - start_time,
            'success': True
        }
        
        self.request_history.append(request_record)
    
    def _handle_slack_rate_limit_headers(self, response: BoltResponse, 
                                       user_id: Optional[str], 
                                       team_id: Optional[str]):
        """Handle Slack's rate limit headers and adjust internal limits"""
        if not hasattr(response, 'headers'):
            return
        
        # Check for Slack rate limit headers
        retry_after = response.headers.get('Retry-After')
        rate_limit_remaining = response.headers.get('X-RateLimit-Remaining')
        
        if retry_after:
            # Slack is telling us to back off
            backoff_seconds = int(retry_after)
            backoff_key = user_id or team_id or "global"
            
            logger.warning(f"Slack rate limit hit, backing off for {backoff_seconds}s")
            
            # Force backoff state
            self.backoff_state[backoff_key] = {
                'consecutive_limits': 3,  # Treat as multiple consecutive limits
                'last_backoff': time.time(),
                'first_limit': time.time()
            }
        
        if rate_limit_remaining and int(rate_limit_remaining) < 10:
            # We're close to Slack's rate limit, be more conservative
            logger.info(f"Slack rate limit low: {rate_limit_remaining} remaining")
            
            # Temporarily reduce our rate limits
            backoff_key = user_id or team_id or "global"
            if backoff_key not in self.backoff_state:
                self.backoff_state[backoff_key] = {
                    'consecutive_limits': 1,
                    'last_backoff': time.time(),
                    'first_limit': time.time()
                }
    
    def get_rate_limit_stats(self) -> Dict[str, Any]:
        """Get rate limiting statistics"""
        recent_requests = [r for r in self.request_history 
                          if time.time() - time.mktime(datetime.fromisoformat(r['timestamp']).timetuple()) < 300]
        
        interactive_count = len([r for r in recent_requests if r['rate_mode'] == 'interactive'])
        bulk_count = len([r for r in recent_requests if r['rate_mode'] == 'bulk'])
        
        return {
            'total_requests_5min': len(recent_requests),
            'interactive_requests_5min': interactive_count,
            'bulk_requests_5min': bulk_count,
            'active_users': len(self.user_buckets),
            'active_teams': len(self.team_buckets),
            'backoff_users': len([k for k, v in self.backoff_state.items() 
                                 if v.get('consecutive_limits', 0) > 0]),
            'avg_response_time': sum(r['duration'] for r in recent_requests) / len(recent_requests) 
                               if recent_requests else 0,
            'default_mode': self.default_mode.value
        }
    
    def clear_rate_limits(self, user_id: Optional[str] = None, team_id: Optional[str] = None):
        """Clear rate limits for user/team (admin function)"""
        if user_id:
            user_key = f"user:{user_id}"
            self.user_buckets.pop(user_key, None)
            self.backoff_state.pop(user_id, None)
            logger.info(f"Cleared rate limits for user {user_id}")
        
        if team_id:
            team_key = f"team:{team_id}"
            self.team_buckets.pop(team_key, None)
            self.backoff_state.pop(team_id, None)
            logger.info(f"Cleared rate limits for team {team_id}")
        
        if not user_id and not team_id:
            # Clear all
            self.user_buckets.clear()
            self.team_buckets.clear()
            self.backoff_state.clear()
            logger.info("Cleared all rate limits")

# Global rate limiter instance
_global_rate_limiter = None

def get_rate_limiter(default_mode: RateLimitMode = RateLimitMode.INTERACTIVE) -> RateLimiter:
    """Get global rate limiter instance"""
    global _global_rate_limiter
    if _global_rate_limiter is None:
        _global_rate_limiter = RateLimiter(default_mode)
    return _global_rate_limiter

# Convenience function for bulk operations  
def with_bulk_rate_limiting(func: Callable) -> Callable:
    """Decorator to temporarily use bulk rate limiting"""
    def wrapper(*args, **kwargs):
        rate_limiter = get_rate_limiter()
        original_mode = rate_limiter.default_mode
        
        try:
            rate_limiter.default_mode = RateLimitMode.BULK
            return func(*args, **kwargs)
        finally:
            rate_limiter.default_mode = original_mode
    
    return wrapper