#!/usr/bin/env python3
"""
Collect Ryan's Slack Data - 6 Month Analysis
Target: Ryan Marien (ryan@biorender.com / UBL74SKU0)
Period: August 2024 - February 2025 (same as calendar data)

This script focuses specifically on collecting Slack messages involving Ryan
from the 6-month period to complement the calendar analysis.
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.collectors.slack_collector import SlackCollector
from src.core.auth_manager import credential_vault

class RyanSlackCollector:
    """Specialized collector for Ryan's Slack data over 6 months"""
    
    def __init__(self):
        self.project_root = project_root
        self.ryan_user_id = "UBL74SKU0"
        self.ryan_email = "ryan@biorender.com"
        
        # Target date range matching calendar data
        self.start_date = "2024-08-20"
        self.end_date = "2025-02-07"
        
        # Calculate timestamps for Slack API
        self.start_timestamp = datetime.strptime(self.start_date, "%Y-%m-%d").timestamp()
        self.end_timestamp = datetime.strptime(self.end_date, "%Y-%m-%d").timestamp()
        
        # Setup output paths
        self.output_path = self.project_root / "experiments" / "ryan_time_analysis" / "data" / "raw" / "slack"
        self.output_path.mkdir(parents=True, exist_ok=True)
        
        print(f"🎯 RYAN SLACK DATA COLLECTOR")
        print(f"📧 Target: {self.ryan_email} ({self.ryan_user_id})")
        print(f"📅 Period: {self.start_date} to {self.end_date}")
        print(f"💾 Output: {self.output_path}")
    
    def collect_ryan_slack_data(self):
        """Collect all Slack data involving Ryan for the 6-month period"""
        
        print(f"\n🚀 STARTING RYAN SLACK COLLECTION")
        start_time = datetime.now()
        
        try:
            # Initialize standard Slack collector
            collector = SlackCollector()
            
            # Setup authentication
            if not collector.setup_slack_authentication():
                print("❌ Failed to setup Slack authentication")
                return {"error": "Authentication failed"}
            
            # Discover all channels
            print("🔍 Discovering all Slack channels...")
            all_channels = collector.discover_all_channels()
            
            # Discover all users  
            print("🔍 Discovering all Slack users...")
            all_users = collector.discover_all_users()
            
            # Verify Ryan is in user list
            if self.ryan_user_id not in all_users:
                print(f"❌ Ryan's user ID {self.ryan_user_id} not found in workspace")
                return {"error": f"User {self.ryan_user_id} not found"}
            
            print(f"✅ Found Ryan in user list: {all_users[self.ryan_user_id]['real_name']}")
            
            # Filter channels to focus on those Ryan is likely in
            relevant_channels = self._filter_channels_for_ryan(all_channels)
            
            # Collect message data from relevant channels
            ryan_data = self._collect_ryan_messages(collector, relevant_channels)
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds() / 60
            
            # Create summary and save data
            summary = {
                "collection_timestamp": start_time.isoformat(),
                "target_user": {
                    "email": self.ryan_email,
                    "slack_id": self.ryan_user_id,
                    "real_name": all_users[self.ryan_user_id]["real_name"]
                },
                "date_range": {
                    "start": self.start_date,
                    "end": self.end_date,
                    "start_timestamp": self.start_timestamp,
                    "end_timestamp": self.end_timestamp
                },
                "discovery_results": {
                    "total_channels": len(all_channels),
                    "relevant_channels": len(relevant_channels),
                    "total_users": len(all_users)
                },
                "collection_results": ryan_data["summary"],
                "duration_minutes": round(duration, 2)
            }
            
            # Save all data
            self._save_collection_data(ryan_data, all_users, summary)
            
            print(f"\n🎉 RYAN SLACK COLLECTION COMPLETE!")
            print(f"⏱️  Duration: {duration:.1f} minutes")
            print(f"💾 Data saved to: {self.output_path}")
            
            return summary
            
        except Exception as e:
            print(f"❌ Collection failed: {e}")
            return {"error": str(e)}
    
    def _filter_channels_for_ryan(self, all_channels: Dict) -> Dict:
        """Filter channels to focus on those relevant to Ryan"""
        
        print(f"🔍 Filtering {len(all_channels)} channels for Ryan relevance...")
        
        relevant_channels = {}
        
        # Criteria for Ryan-relevant channels:
        # 1. Direct messages (DMs)
        # 2. Group messages (MPIMs) 
        # 3. Channels Ryan is a member of
        # 4. Executive/leadership channels
        # 5. Channels with keywords related to Ryan's role
        
        executive_keywords = [
            'executive', 'exec', 'leadership', 'management', 'ceo', 'cto', 
            'directors', 'leads', 'managers', 'strategy', 'planning',
            'board', 'founders', 'senior', 'heads'
        ]
        
        for channel_id, channel in all_channels.items():
            include_channel = False
            reason = ""
            
            # Always include DMs and MPIMs (high signal for executive analysis)
            if channel.get('is_im', False):
                include_channel = True
                reason = "Direct message"
            elif channel.get('is_mpim', False):
                include_channel = True
                reason = "Group direct message"
            
            # Include channels Ryan is a member of
            elif channel.get('is_member', False):
                include_channel = True
                reason = "Ryan is member"
            
            # Include executive/leadership channels regardless of membership
            else:
                channel_name = channel.get('name', '').lower()
                channel_purpose = channel.get('purpose', '').lower()
                channel_topic = channel.get('topic', '').lower()
                
                text_to_check = f"{channel_name} {channel_purpose} {channel_topic}"
                
                if any(keyword in text_to_check for keyword in executive_keywords):
                    include_channel = True
                    reason = "Executive/leadership channel"
            
            if include_channel:
                relevant_channels[channel_id] = channel
                print(f"  ✅ #{channel.get('name', 'unknown')}: {reason}")
        
        print(f"📋 Selected {len(relevant_channels)}/{len(all_channels)} channels for Ryan analysis")
        return relevant_channels
    
    def _collect_ryan_messages(self, collector, relevant_channels: Dict) -> Dict:
        """Collect messages from relevant channels focusing on Ryan's activity"""
        
        print(f"\n💬 COLLECTING MESSAGES FROM {len(relevant_channels)} CHANNELS")
        
        total_messages = 0
        ryan_messages = 0
        ryan_mentions = 0
        channels_processed = 0
        channels_with_ryan = 0
        
        all_ryan_data = {}
        
        for channel_id, channel in relevant_channels.items():
            channel_name = channel.get('name', 'unknown')
            print(f"  Processing #{channel_name}...")
            
            try:
                # Collect conversation history for the full 6-month period
                # Convert 6 months to hours (approximately 26 weeks * 7 days * 24 hours)
                hours_back = 26 * 7 * 24  # ~6 months
                
                conversation_data = collector.collect_conversation_history(
                    channel_id, 
                    channel_name,
                    hours_back=hours_back
                )
                
                if 'error' in conversation_data:
                    print(f"    ⚠️ Error collecting #{channel_name}: {conversation_data['error']}")
                    continue
                
                # Filter messages to focus on Ryan's activity and mentions
                ryan_activity = self._extract_ryan_activity(conversation_data, channel_name)
                
                if ryan_activity['ryan_messages'] > 0 or ryan_activity['ryan_mentions'] > 0:
                    all_ryan_data[channel_id] = ryan_activity
                    channels_with_ryan += 1
                    
                    print(f"    ✅ #{channel_name}: {ryan_activity['ryan_messages']} messages, {ryan_activity['ryan_mentions']} mentions")
                
                # Update counters
                total_messages += conversation_data.get('message_summary', {}).get('total_messages', 0)
                ryan_messages += ryan_activity['ryan_messages']
                ryan_mentions += ryan_activity['ryan_mentions']
                channels_processed += 1
                
            except Exception as e:
                print(f"    ❌ Failed to collect #{channel_name}: {e}")
        
        summary = {
            "channels_processed": channels_processed,
            "channels_with_ryan": channels_with_ryan,
            "total_messages_scanned": total_messages,
            "ryan_messages_found": ryan_messages,
            "ryan_mentions_found": ryan_mentions
        }
        
        return {
            "summary": summary,
            "ryan_data": all_ryan_data
        }
    
    def _extract_ryan_activity(self, conversation_data: Dict, channel_name: str) -> Dict:
        """Extract Ryan's messages and mentions from conversation data"""
        
        ryan_messages = []
        ryan_mentions = []
        ryan_threads = []
        
        # Process regular messages
        messages = conversation_data.get('messages', [])
        for message in messages:
            # Ryan's own messages
            if message.get('user') == self.ryan_user_id:
                ryan_messages.append(message)
            
            # Messages mentioning Ryan
            text = message.get('text', '')
            if (f"<@{self.ryan_user_id}>" in text or 
                "ryan" in text.lower() or
                self.ryan_email in text):
                ryan_mentions.append(message)
        
        # Process thread messages
        threads = conversation_data.get('threads', [])
        for thread in threads:
            thread_messages = thread.get('messages', [])
            ryan_in_thread = False
            thread_ryan_messages = []
            thread_mentions = []
            
            for msg in thread_messages:
                if msg.get('user') == self.ryan_user_id:
                    ryan_in_thread = True
                    thread_ryan_messages.append(msg)
                
                text = msg.get('text', '')
                if (f"<@{self.ryan_user_id}>" in text or 
                    "ryan" in text.lower() or
                    self.ryan_email in text):
                    thread_mentions.append(msg)
            
            if ryan_in_thread or thread_mentions:
                ryan_threads.append({
                    "thread_ts": thread.get('thread_ts'),
                    "ryan_messages": thread_ryan_messages,
                    "mentions": thread_mentions,
                    "total_messages": len(thread_messages),
                    "participants": thread.get('participants', [])
                })
        
        return {
            "channel_name": channel_name,
            "ryan_messages": len(ryan_messages),
            "ryan_mentions": len(ryan_mentions),
            "ryan_threads": len(ryan_threads),
            "messages": ryan_messages,
            "mentions": ryan_mentions,
            "threads": ryan_threads,
            "channel_info": conversation_data.get('channel_info', {}),
            "analytics": conversation_data.get('analytics', {})
        }
    
    def _save_collection_data(self, ryan_data: Dict, all_users: Dict, summary: Dict):
        """Save collected data in organized format"""
        
        # Save summary
        summary_file = self.output_path / "collection_summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        # Save user data
        users_file = self.output_path / "users.json" 
        with open(users_file, 'w') as f:
            json.dump(all_users, f, indent=2)
        
        # Save Ryan's activity data
        ryan_file = self.output_path / "ryan_activity.json"
        with open(ryan_file, 'w') as f:
            json.dump(ryan_data, f, indent=2)
        
        # Create JSONL format for easier processing
        ryan_messages_jsonl = self.output_path / "ryan_messages.jsonl"
        with open(ryan_messages_jsonl, 'w') as f:
            for channel_id, channel_data in ryan_data["ryan_data"].items():
                # Write Ryan's own messages
                for message in channel_data["messages"]:
                    enriched = dict(message)
                    enriched["channel_id"] = channel_id
                    enriched["channel_name"] = channel_data["channel_name"]
                    enriched["message_type"] = "ryan_message"
                    f.write(json.dumps(enriched) + "\n")
                
                # Write messages mentioning Ryan
                for message in channel_data["mentions"]:
                    enriched = dict(message)
                    enriched["channel_id"] = channel_id 
                    enriched["channel_name"] = channel_data["channel_name"]
                    enriched["message_type"] = "ryan_mention"
                    f.write(json.dumps(enriched) + "\n")
                
                # Write thread messages
                for thread in channel_data["threads"]:
                    for message in thread["ryan_messages"]:
                        enriched = dict(message)
                        enriched["channel_id"] = channel_id
                        enriched["channel_name"] = channel_data["channel_name"] 
                        enriched["message_type"] = "ryan_thread_message"
                        enriched["thread_ts"] = thread["thread_ts"]
                        f.write(json.dumps(enriched) + "\n")
        
        print(f"💾 Saved data files:")
        print(f"  - {summary_file}")
        print(f"  - {users_file}")
        print(f"  - {ryan_file}")
        print(f"  - {ryan_messages_jsonl}")


def main():
    """Run Ryan's Slack data collection"""
    collector = RyanSlackCollector()
    results = collector.collect_ryan_slack_data()
    
    if "error" in results:
        print(f"❌ Collection failed: {results['error']}")
        return 1
    
    print(f"\n📊 Collection Summary:")
    print(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)