#!/usr/bin/env python3
"""
Slack Collector - Dynamic discovery-based Slack conversation and channel collection
Handles dynamic channel/user discovery, rule-based filtering, and rate limiting
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
import time
import requests

# Add auth system to path
sys.path.insert(0, str(Path(__file__).parent.parent / "core"))
from auth_manager import credential_vault

class SlackRateLimiter:
    """Slack-specific rate limiting with method-aware limits"""
    
    def __init__(self, requests_per_second: float = 1, channels_per_minute: int = 20):
        self.requests_per_second = requests_per_second
        self.channels_per_minute = channels_per_minute
        self.last_request_time = 0
        self.last_channel_time = 0
        self.request_count = 0
        self.channel_count = 0
        
    def wait_for_api_limit(self):
        """Wait for general API rate limit"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        min_interval = 1.0 / self.requests_per_second
        
        if time_since_last < min_interval:
            wait_time = min_interval - time_since_last
            time.sleep(wait_time)
        
        self.last_request_time = time.time()
        self.request_count += 1
    
    def wait_for_channel_limit(self):
        """Wait for channel-specific rate limit"""
        current_time = time.time()
        time_since_last_channel = current_time - self.last_channel_time
        min_channel_interval = 60.0 / self.channels_per_minute
        
        if time_since_last_channel < min_channel_interval:
            wait_time = min_channel_interval - time_since_last_channel
            time.sleep(wait_time)
        
        self.last_channel_time = time.time()
        self.channel_count += 1

class SlackCollector:
    """
    Dynamic discovery-based Slack collector with rule-based filtering
    Discovers all channels and users, then applies collection rules
    """
    
    def __init__(self, config_path: Optional[Path] = None):
        self.project_root = Path(__file__).parent.parent.parent
        
        # Load configuration
        self.config = self._load_config(config_path)
        
        # Initialize storage paths
        today = datetime.now().strftime("%Y-%m-%d")
        self.data_path = self.project_root / "data" / "raw" / "slack" / today
        self.data_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize rate limiter
        self.rate_limiter = SlackRateLimiter(
            requests_per_second=self.config.get('requests_per_second', 1.0),
            channels_per_minute=self.config.get('channels_per_minute', 20)
        )
        
        # Initialize Slack authentication
        self.bot_token = None
        self.user_token = None
        self.headers = {}
        
        # Discovery caches
        self.channel_cache = {}
        self.user_cache = {}
        
        # Collection results
        self.collection_results = {
            "status": "initialized",
            "discovered": {"channels": 0, "users": 0},
            "collected": {"channels": 0, "messages": 0},
            "data_path": str(self.data_path),
            "next_cursor": None
        }
        
        print(f"💬 SLACK COLLECTOR INITIALIZED")
        print(f"💾 Storage: {self.data_path}")
        print(f"⚡ Rate limit: {self.config.get('requests_per_second', 1.0)} req/sec")
    
    def _load_config(self, config_path: Optional[Path] = None) -> Dict:
        """Load collection configuration with rule-based filtering"""
        default_config = {
            "requests_per_second": 1.0,
            "channels_per_minute": 20,
            "rolling_window_hours": 72,
            "collection_rules": {
                "include_all_channels": True,
                "exclude_patterns": ["test-*", "archive-*"],
                "must_include": ["leadership", "product"],
                "member_only": True,
                "include_private": False
            },
            "cursor_delay_seconds": 1.0
        }
        
        if config_path and config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    user_config = json.load(f)
                default_config.update(user_config)
                print(f"✅ Config loaded from {config_path}")
            except Exception as e:
                print(f"⚠️ Failed to load config from {config_path}: {e}")
        
        return default_config
    
    def apply_collection_rules(self, channels: Dict[str, Dict]) -> Dict[str, Dict]:
        """Apply collection rules to filter channels"""
        rules = self.config.get('collection_rules', {})
        filtered_channels = {}
        
        for channel_id, channel in channels.items():
            channel_name = channel.get('name', '')
            
            # Skip if not a member and member_only is True
            if rules.get('member_only', True) and not channel.get('is_member', False):
                continue
            
            # Skip private channels if not included
            if not rules.get('include_private', False) and channel.get('is_private', False):
                continue
            
            # Check must_include patterns first
            must_include = rules.get('must_include', [])
            if must_include and any(pattern in channel_name for pattern in must_include):
                filtered_channels[channel_id] = channel
                continue
            
            # Check exclude patterns
            exclude_patterns = rules.get('exclude_patterns', [])
            if any(self._matches_pattern(channel_name, pattern) for pattern in exclude_patterns):
                continue
            
            # Include if include_all_channels is True
            if rules.get('include_all_channels', True):
                filtered_channels[channel_id] = channel
        
        print(f"📋 Filtered channels: {len(filtered_channels)}/{len(channels)} channels selected")
        return filtered_channels
    
    def _matches_pattern(self, name: str, pattern: str) -> bool:
        """Simple pattern matching for channel names"""
        if pattern.endswith('*'):
            return name.startswith(pattern[:-1])
        elif pattern.startswith('*'):
            return name.endswith(pattern[1:])
        else:
            return pattern in name
    
    def setup_slack_authentication(self) -> bool:
        """Setup Slack authentication"""
        try:
            auth_status = credential_vault.validate_authentication()
            
            if not auth_status.get('slack_bot_token'):
                print("❌ Slack bot token not available")
                return False
            
            self.bot_token = credential_vault.get_slack_bot_token()
            self.user_token = credential_vault.get_slack_user_token()  # Optional for user endpoints
            
            # Test bot token
            test_headers = {"Authorization": f"Bearer {self.bot_token}"}
            test_response = requests.get("https://slack.com/api/auth.test", headers=test_headers)
            
            if test_response.status_code == 200 and test_response.json().get('ok'):
                print("✅ Slack authentication ready")
                return True
            else:
                print("❌ Slack authentication test failed")
                return False
                
        except Exception as e:
            print(f"❌ Slack authentication setup failed: {e}")
            return False
    
    def discover_all_channels(self) -> Dict[str, Dict]:
        """Discover all available channels in workspace"""
        print("🔍 Discovering Slack channels...")
        
        self.rate_limiter.wait_for_api_limit()
        
        try:
            headers = {"Authorization": f"Bearer {self.bot_token}"}
            all_channels = {}
            cursor = None
            
            while True:
                params = {
                    "types": "public_channel,private_channel",
                    "limit": 1000,
                    "exclude_archived": True
                }
                
                if cursor:
                    params["cursor"] = cursor
                
                response = requests.get(
                    "https://slack.com/api/conversations.list",
                    headers=headers,
                    params=params
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get('ok'):
                        channels = result.get('channels', [])
                        
                        for channel in channels:
                            all_channels[channel['id']] = {
                                'id': channel['id'],
                                'name': channel.get('name', 'unknown'),
                                'is_private': channel.get('is_private', False),
                                'is_member': channel.get('is_member', False),
                                'is_archived': channel.get('is_archived', False),
                                'num_members': channel.get('num_members', 0),
                                'purpose': channel.get('purpose', {}).get('value', ''),
                                'topic': channel.get('topic', {}).get('value', ''),
                                'created': channel.get('created', 0)
                            }
                        
                        # Check for more pages
                        cursor = result.get('response_metadata', {}).get('next_cursor')
                        if not cursor:
                            break
                        
                        time.sleep(self.config.get('cursor_delay_seconds', 1.0))
                    else:
                        print(f"❌ API error: {result.get('error', 'Unknown')}")
                        break
                else:
                    print(f"❌ HTTP error: {response.status_code}")
                    break
            
            self.channel_cache = all_channels
            self.collection_results["discovered"]["channels"] = len(all_channels)
            print(f"✅ Discovered {len(all_channels)} channels")
            return all_channels
            
        except Exception as e:
            print(f"❌ Channel discovery failed: {e}")
            return {}
    
    def discover_all_users(self) -> Dict[str, Dict]:
        """Discover all users in workspace"""
        print("🔍 Discovering Slack users...")
        
        self.rate_limiter.wait_for_api_limit()
        
        try:
            headers = {"Authorization": f"Bearer {self.bot_token}"}
            all_users = {}
            cursor = None
            
            while True:
                params = {
                    "limit": 1000
                }
                
                if cursor:
                    params["cursor"] = cursor
                
                response = requests.get(
                    "https://slack.com/api/users.list",
                    headers=headers,
                    params=params
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get('ok'):
                        users = result.get('members', [])
                        
                        for user in users:
                            if not user.get('deleted', False) and not user.get('is_bot', False):
                                all_users[user['id']] = {
                                    'id': user['id'],
                                    'name': user.get('name', 'unknown'),
                                    'real_name': user.get('real_name', ''),
                                    'display_name': user.get('profile', {}).get('display_name', ''),
                                    'email': user.get('profile', {}).get('email', ''),
                                    'is_admin': user.get('is_admin', False),
                                    'is_owner': user.get('is_owner', False),
                                    'is_primary_owner': user.get('is_primary_owner', False),
                                    'timezone': user.get('tz', '')
                                }
                        
                        # Check for more pages
                        cursor = result.get('response_metadata', {}).get('next_cursor')
                        if not cursor:
                            break
                        
                        time.sleep(self.config.get('cursor_delay_seconds', 1.0))
                    else:
                        print(f"❌ API error: {result.get('error', 'Unknown')}")
                        break
                else:
                    print(f"❌ HTTP error: {response.status_code}")
                    break
            
            self.user_cache = all_users
            self.collection_results["discovered"]["users"] = len(all_users)
            print(f"✅ Discovered {len(all_users)} users")
            return all_users
            
        except Exception as e:
            print(f"❌ User discovery failed: {e}")
            return {}
    
    def collect_conversation_history(self, channel_id: str, channel_name: str, hours_back: int = 72) -> Dict:
        """Collect conversation history with rolling window"""
        
        # Calculate rolling window
        oldest_timestamp = (datetime.now() - timedelta(hours=hours_back)).timestamp()
        
        self.rate_limiter.wait_for_channel_limit()
        
        try:
            headers = {"Authorization": f"Bearer {self.bot_token}"}
            messages = []
            cursor = None
            
            while True:
                params = {
                    "channel": channel_id,
                    "oldest": str(oldest_timestamp),
                    "limit": 1000
                }
                
                if cursor:
                    params["cursor"] = cursor
                
                response = requests.get(
                    "https://slack.com/api/conversations.history",
                    headers=headers,
                    params=params
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get('ok'):
                        batch_messages = result.get('messages', [])
                        messages.extend(batch_messages)
                        
                        # Check for more pages
                        cursor = result.get('response_metadata', {}).get('next_cursor')
                        if not cursor or len(batch_messages) == 0:
                            break
                        
                        # Rate limit between pages
                        time.sleep(self.config.get('cursor_delay_seconds', 1.0))
                    else:
                        print(f"    ❌ API error: {result.get('error', 'Unknown')}")
                        break
                else:
                    print(f"    ❌ HTTP error: {response.status_code}")
                    break
            
            # Process messages and extract threads
            processed_data = self._process_conversation_data(messages, channel_id, channel_name)
            
            return processed_data
            
        except Exception as e:
            print(f"    ❌ Failed to collect conversation history: {e}")
            return {'messages': [], 'threads': [], 'error': str(e)}
    
    def _process_conversation_data(self, messages: List[Dict], channel_id: str, channel_name: str) -> Dict:
        """Process conversation data and extract insights"""
        
        # Categorize messages
        regular_messages = []
        thread_messages = []
        bot_messages = []
        
        for message in messages:
            if message.get('subtype') == 'bot_message':
                bot_messages.append(message)
            elif message.get('thread_ts'):
                thread_messages.append(message)
            else:
                regular_messages.append(message)
        
        # Extract threads
        threads = self._extract_conversation_threads(thread_messages)
        
        # Calculate conversation analytics
        analytics = self._calculate_conversation_analytics(messages, channel_name)
        
        processed_data = {
            'channel_info': {
                'id': channel_id,
                'name': channel_name,
                'collection_timestamp': datetime.now().isoformat(),
                'rolling_window_hours': self.config.get('rolling_window_hours', 72)
            },
            'message_summary': {
                'total_messages': len(messages),
                'regular_messages': len(regular_messages),
                'thread_messages': len(thread_messages),
                'bot_messages': len(bot_messages),
                'unique_authors': len(set(msg.get('user', '') for msg in messages if msg.get('user')))
            },
            'messages': regular_messages,
            'threads': threads,
            'analytics': analytics
        }
        
        return processed_data
    
    def _extract_conversation_threads(self, thread_messages: List[Dict]) -> List[Dict]:
        """Extract and organize conversation threads"""
        threads_by_ts = {}
        
        # Group messages by thread timestamp
        for message in thread_messages:
            thread_ts = message.get('thread_ts')
            if thread_ts not in threads_by_ts:
                threads_by_ts[thread_ts] = []
            threads_by_ts[thread_ts].append(message)
        
        # Process each thread
        processed_threads = []
        for thread_ts, thread_msgs in threads_by_ts.items():
            # Sort messages chronologically
            thread_msgs.sort(key=lambda x: float(x.get('ts', 0)))
            
            thread_data = {
                'thread_ts': thread_ts,
                'message_count': len(thread_msgs),
                'participants': list(set(msg.get('user', '') for msg in thread_msgs if msg.get('user'))),
                'start_time': datetime.fromtimestamp(float(thread_msgs[0].get('ts', 0))).isoformat() if thread_msgs else None,
                'last_reply': datetime.fromtimestamp(float(thread_msgs[-1].get('ts', 0))).isoformat() if thread_msgs else None,
                'messages': thread_msgs,
                'priority_score': self._calculate_thread_priority(thread_msgs)
            }
            
            processed_threads.append(thread_data)
        
        # Sort threads by priority score
        processed_threads.sort(key=lambda x: x['priority_score'], reverse=True)
        
        return processed_threads
    
    def _calculate_thread_priority(self, messages: List[Dict]) -> float:
        """Calculate priority score for conversation thread"""
        priority_score = 0.0
        
        # More messages = higher priority
        priority_score += len(messages) * 0.5
        
        # More participants = higher priority
        unique_participants = set(msg.get('user', '') for msg in messages if msg.get('user'))
        priority_score += len(unique_participants) * 1.0
        
        # Recent activity = higher priority
        if messages:
            last_ts = float(messages[-1].get('ts', 0))
            hours_ago = (time.time() - last_ts) / 3600
            if hours_ago < 24:
                priority_score += 5.0 - (hours_ago / 5)  # Boost recent threads
        
        # Executive participation = much higher priority
        for message in messages:
            user_id = message.get('user', '')
            if user_id and self._is_executive_user(user_id):
                priority_score += 10.0
                break
        
        return priority_score
    
    def _is_executive_user(self, user_id: str) -> bool:
        """Check if user is an executive (requires user info lookup)"""
        # This would require user info caching - simplified for now
        return False
    
    def _calculate_conversation_analytics(self, messages: List[Dict], channel_name: str) -> Dict:
        """Calculate conversation analytics"""
        if not messages:
            return {}
        
        # Time-based analysis
        message_times = []
        hourly_distribution = {}
        daily_distribution = {}
        
        for message in messages:
            if message.get('ts'):
                try:
                    dt = datetime.fromtimestamp(float(message['ts']))
                    message_times.append(dt)
                    
                    hour = dt.hour
                    day = dt.strftime('%A')
                    
                    hourly_distribution[hour] = hourly_distribution.get(hour, 0) + 1
                    daily_distribution[day] = daily_distribution.get(day, 0) + 1
                except:
                    continue
        
        # User activity analysis
        user_activity = {}
        for message in messages:
            user_id = message.get('user')
            if user_id:
                if user_id not in user_activity:
                    user_activity[user_id] = {'message_count': 0, 'thread_starts': 0, 'reactions_given': 0}
                user_activity[user_id]['message_count'] += 1
                
                if not message.get('thread_ts'):  # Original message, not thread reply
                    user_activity[user_id]['thread_starts'] += 1
        
        # Most active users
        most_active_users = sorted(
            user_activity.items(), 
            key=lambda x: x[1]['message_count'], 
            reverse=True
        )[:10]
        
        analytics = {
            'activity_summary': {
                'total_messages': len(messages),
                'unique_users': len(user_activity),
                'messages_per_day': len(messages) / 3 if messages else 0,  # 72-hour window / 3 days
                'peak_hour': max(hourly_distribution, key=hourly_distribution.get) if hourly_distribution else None,
                'busiest_day': max(daily_distribution, key=daily_distribution.get) if daily_distribution else None
            },
            'engagement_metrics': {
                'most_active_users': [{'user_id': user, 'stats': stats} for user, stats in most_active_users],
                'hourly_distribution': hourly_distribution,
                'daily_distribution': daily_distribution
            },
            'conversation_health': {
                'response_rate': self._calculate_response_rate(messages),
                'thread_depth': self._calculate_average_thread_depth(messages),
                'participation_diversity': len(user_activity) / max(len(messages), 1) if messages else 0
            }
        }
        
        return analytics
    
    def _calculate_response_rate(self, messages: List[Dict]) -> float:
        """Calculate conversation response rate"""
        # Simplified - count messages with thread replies
        messages_with_replies = len([msg for msg in messages if msg.get('reply_count', 0) > 0])
        total_messages = len([msg for msg in messages if not msg.get('thread_ts')])  # Non-thread messages
        
        return (messages_with_replies / total_messages) * 100 if total_messages > 0 else 0
    
    def _calculate_average_thread_depth(self, messages: List[Dict]) -> float:
        """Calculate average thread depth"""
        thread_counts = {}
        for message in messages:
            thread_ts = message.get('thread_ts')
            if thread_ts:
                thread_counts[thread_ts] = thread_counts.get(thread_ts, 0) + 1
        
        return sum(thread_counts.values()) / len(thread_counts) if thread_counts else 0
    
    def collect_from_filtered_channels(self, filtered_channels: Dict[str, Dict], max_channels: int = 50) -> Dict:
        """Collect conversation history from filtered channels"""
        
        # Prioritize channels based on member count and membership
        prioritized_channels = sorted(
            filtered_channels.values(),
            key=lambda ch: (
                ch.get('num_members', 0),
                1 if ch.get('is_member', False) else 0
            ),
            reverse=True
        )[:max_channels]
        
        print(f"\n💬 COLLECTING FROM FILTERED SLACK CHANNELS")
        print(f"🎯 Processing {len(prioritized_channels)} channels")
        
        successful_collections = 0
        total_messages = 0
        collected_channels = {}
        
        for i, channel in enumerate(prioritized_channels, 1):
            channel_id = channel['id']
            channel_name = channel['name']
            
            print(f"  [{i}/{len(prioritized_channels)}] #{channel_name} ({channel.get('num_members', 0)} members)")
            
            try:
                conversation_data = self.collect_conversation_history(
                    channel_id, 
                    channel_name, 
                    self.config.get('rolling_window_hours', 72)
                )
                
                if 'error' not in conversation_data:
                    collected_channels[channel_id] = conversation_data
                    successful_collections += 1
                    total_messages += conversation_data.get('message_summary', {}).get('total_messages', 0)
                
            except Exception as e:
                print(f"    ❌ Failed to collect #{channel_name}: {e}")
        
        return {
            'channels_processed': len(prioritized_channels),
            'successful_collections': successful_collections,
            'total_messages_collected': total_messages,
            'collected_data': collected_channels
        }
    
    def save_collection_data(self, channels_data: Dict, users_data: Dict) -> None:
        """Save collected data to JSON files"""
        timestamp = datetime.now().isoformat()
        
        # Save channels data
        channels_file = self.data_path / "channels.json"
        with open(channels_file, 'w') as f:
            json.dump(channels_data, f, indent=2)
        
        # Save users data  
        users_file = self.data_path / "users.json"
        with open(users_file, 'w') as f:
            json.dump(users_data, f, indent=2)
        
        print(f"💾 Data saved to {self.data_path}")
    
    def to_json(self) -> str:
        """Output collection results as JSON string"""
        return json.dumps(self.collection_results, indent=2)
    
    def collect_all_slack_data(self, force_refresh: bool = False, max_channels: int = 50) -> Dict:
        """Collect comprehensive Slack data using dynamic discovery"""
        
        if not self.setup_slack_authentication():
            self.collection_results["status"] = "error"
            return {'error': 'Failed to setup Slack authentication'}
        
        print(f"\n🚀 STARTING DYNAMIC SLACK COLLECTION")
        collection_start = datetime.now()
        
        try:
            # 1. Discover all channels
            all_channels = self.discover_all_channels()
            
            # 2. Discover all users
            all_users = self.discover_all_users()
            
            # 3. Apply collection rules to filter channels
            filtered_channels = self.apply_collection_rules(all_channels)
            
            # 4. Collect from filtered channels
            channel_results = self.collect_from_filtered_channels(filtered_channels, max_channels)
            
            collection_end = datetime.now()
            duration = (collection_end - collection_start).total_seconds() / 60
            
            # Update collection results
            self.collection_results.update({
                "status": "success",
                "collected": {
                    "channels": channel_results["successful_collections"],
                    "messages": channel_results["total_messages_collected"]
                },
                "next_cursor": collection_end.timestamp()
            })
            
            # Save collected data
            self.save_collection_data(channel_results["collected_data"], all_users)
            
            final_results = {
                'collection_summary': {
                    'start_time': collection_start.isoformat(),
                    'end_time': collection_end.isoformat(),
                    'duration_minutes': round(duration, 1),
                    'total_api_requests': self.rate_limiter.request_count
                },
                'discovery_results': {
                    'total_channels_discovered': len(all_channels),
                    'filtered_channels': len(filtered_channels),
                    'users_discovered': len(all_users)
                },
                'channel_results': channel_results,
                'collection_results': self.collection_results
            }
            
            print(f"\n🎉 SLACK COLLECTION COMPLETE!")
            print(f"⏱️  Duration: {duration:.1f} minutes")
            print(f"📊 API requests: {self.rate_limiter.request_count}")
            print(f"💾 Stored: {self.data_path}")
            
            return final_results
            
        except Exception as e:
            print(f"❌ Collection failed: {e}")
            self.collection_results["status"] = "error"
            return {"error": str(e), "collection_results": self.collection_results}

def main():
    """Test Slack collector with dynamic discovery"""
    config_path = None  # Use default config
    
    # Initialize Slack collector
    collector = SlackCollector(config_path)
    
    # Run collection
    results = collector.collect_all_slack_data(force_refresh=True, max_channels=10)
    
    print(f"\n📊 Final Results:")
    print(json.dumps(results, indent=2))
    
    # Output JSON for tool pattern
    print("\n📋 Collection Results JSON:")
    print(collector.to_json())
    
    return results

if __name__ == "__main__":
    main()