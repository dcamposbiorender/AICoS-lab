#!/usr/bin/env python3
"""
Extract Ryan's Slack Data from Existing Collections
Parse existing Slack data to find all messages by/about Ryan for 6-month analysis

This script processes existing Slack data files to extract Ryan's activity
without requiring new API calls or authentication.
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

class RyanDataExtractor:
    """Extract Ryan's data from existing Slack collections"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.ryan_user_id = "UBL74SKU0"
        self.ryan_email = "ryan@biorender.com"
        
        # Target date range (August 2024 - February 2025)
        self.start_date = datetime(2024, 8, 20)
        self.end_date = datetime(2025, 2, 7, 23, 59, 59)  # End of day
        
        # Output paths
        self.output_path = self.project_root / "experiments" / "ryan_time_analysis" / "data" / "raw" / "slack"
        self.output_path.mkdir(parents=True, exist_ok=True)
        
        # Existing data paths
        self.existing_data_path = self.project_root / "data" / "raw" / "slack"
        
        print(f"🎯 RYAN DATA EXTRACTOR")
        print(f"📧 Target: {self.ryan_email} ({self.ryan_user_id})")
        print(f"📅 Period: {self.start_date.date()} to {self.end_date.date()}")
        print(f"📂 Source: {self.existing_data_path}")
        print(f"💾 Output: {self.output_path}")
    
    def extract_ryan_data(self) -> Dict:
        """Extract Ryan's data from all existing Slack collections"""
        
        print(f"\n🔍 SCANNING EXISTING SLACK DATA")
        start_time = datetime.now()
        
        # Find all existing data directories
        data_dirs = [d for d in self.existing_data_path.iterdir() if d.is_dir()]
        print(f"📂 Found {len(data_dirs)} data directories: {[d.name for d in data_dirs]}")
        
        all_ryan_messages = []
        all_channels = {}
        all_users = {}
        processing_summary = {}
        
        for data_dir in data_dirs:
            print(f"\n📁 Processing {data_dir.name}...")
            
            # Process this directory's data
            dir_results = self._process_data_directory(data_dir)
            
            if dir_results:
                # Merge results
                all_ryan_messages.extend(dir_results["messages"])
                all_channels.update(dir_results["channels"])
                all_users.update(dir_results["users"])
                
                processing_summary[data_dir.name] = {
                    "messages_found": len(dir_results["messages"]),
                    "channels_with_ryan": len(dir_results["channels"]),
                    "users_total": len(dir_results["users"])
                }
                
                print(f"  ✅ Found {len(dir_results['messages'])} Ryan messages in {len(dir_results['channels'])} channels")
            else:
                processing_summary[data_dir.name] = {"error": "No data found or processing failed"}
                print(f"  ⚠️ No data found")
        
        # Filter messages to target date range
        filtered_messages = self._filter_messages_by_date(all_ryan_messages)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Create comprehensive results
        results = {
            "extraction_timestamp": start_time.isoformat(),
            "extraction_duration_seconds": duration,
            "target_user": {
                "email": self.ryan_email,
                "slack_id": self.ryan_user_id,
                "real_name": all_users.get(self.ryan_user_id, {}).get("real_name", "Ryan Marien")
            },
            "date_range": {
                "start": self.start_date.isoformat(),
                "end": self.end_date.isoformat()
            },
            "processing_summary": processing_summary,
            "extraction_results": {
                "total_messages_found": len(all_ryan_messages),
                "messages_in_date_range": len(filtered_messages),
                "channels_analyzed": len(all_channels),
                "total_users": len(all_users)
            }
        }
        
        # Save extracted data
        self._save_extracted_data(filtered_messages, all_channels, all_users, results)
        
        print(f"\n🎉 EXTRACTION COMPLETE!")
        print(f"⏱️  Duration: {duration:.1f} seconds")
        print(f"📊 Found {len(filtered_messages)} messages in date range")
        print(f"💾 Data saved to: {self.output_path}")
        
        return results
    
    def _process_data_directory(self, data_dir: Path) -> Optional[Dict]:
        """Process a single data directory to extract Ryan's messages"""
        
        try:
            # Load channels.json if it exists
            channels_file = data_dir / "channels.json"
            users_file = data_dir / "users.json"
            
            if not channels_file.exists():
                print(f"    ⚠️ No channels.json found")
                return None
            
            # Load channel data
            with open(channels_file, 'r') as f:
                channels_data = json.load(f)
            
            # Load users data
            users_data = {}
            if users_file.exists():
                with open(users_file, 'r') as f:
                    users_data = json.load(f)
            
            # Extract Ryan's messages from channel data
            ryan_messages = []
            channels_with_ryan = {}
            
            for channel_id, channel_info in channels_data.items():
                channel_name = channel_info.get("channel_info", {}).get("name", "unknown")
                
                # Check regular messages
                messages = channel_info.get("messages", [])
                ryan_channel_messages = []
                
                for message in messages:
                    if self._is_ryan_message_or_mention(message):
                        # Enrich message with channel context
                        enriched_message = dict(message)
                        enriched_message["channel_id"] = channel_id
                        enriched_message["channel_name"] = channel_name
                        enriched_message["data_source"] = data_dir.name
                        ryan_channel_messages.append(enriched_message)
                
                # Check thread messages
                threads = channel_info.get("threads", [])
                for thread in threads:
                    thread_messages = thread.get("messages", [])
                    for message in thread_messages:
                        if self._is_ryan_message_or_mention(message):
                            enriched_message = dict(message)
                            enriched_message["channel_id"] = channel_id
                            enriched_message["channel_name"] = channel_name
                            enriched_message["thread_ts"] = thread.get("thread_ts", "")
                            enriched_message["data_source"] = data_dir.name
                            enriched_message["message_context"] = "thread"
                            ryan_channel_messages.append(enriched_message)
                
                # If we found Ryan messages in this channel, include it
                if ryan_channel_messages:
                    ryan_messages.extend(ryan_channel_messages)
                    channels_with_ryan[channel_id] = {
                        "name": channel_name,
                        "ryan_messages": len(ryan_channel_messages),
                        "channel_info": channel_info.get("channel_info", {})
                    }
            
            return {
                "messages": ryan_messages,
                "channels": channels_with_ryan,
                "users": users_data
            }
            
        except Exception as e:
            print(f"    ❌ Error processing {data_dir.name}: {e}")
            return None
    
    def _is_ryan_message_or_mention(self, message: Dict) -> bool:
        """Check if message is by Ryan or mentions Ryan"""
        
        # Message sent by Ryan
        if message.get("user") == self.ryan_user_id:
            return True
        
        # Message mentions Ryan
        text = message.get("text", "").lower()
        if (f"<@{self.ryan_user_id}>" in message.get("text", "") or
            "ryan" in text or
            self.ryan_email in text):
            return True
        
        return False
    
    def _filter_messages_by_date(self, messages: List[Dict]) -> List[Dict]:
        """Filter messages to the target 6-month date range"""
        
        filtered = []
        for message in messages:
            try:
                # Parse message timestamp
                ts = float(message.get("ts", "0"))
                message_dt = datetime.fromtimestamp(ts)
                
                # Check if in target range
                if self.start_date <= message_dt <= self.end_date:
                    # Add parsed datetime for analysis
                    message["datetime"] = message_dt.isoformat()
                    message["date"] = message_dt.date().isoformat()
                    message["hour"] = message_dt.hour
                    message["day_of_week"] = message_dt.strftime("%A")
                    message["month"] = message_dt.strftime("%Y-%m")
                    filtered.append(message)
                    
            except (ValueError, TypeError):
                # Skip messages with invalid timestamps
                continue
        
        print(f"🗓️ Date filtering: {len(messages)} → {len(filtered)} messages in target range")
        return filtered
    
    def _save_extracted_data(self, messages: List[Dict], channels: Dict, 
                           users: Dict, results: Dict):
        """Save extracted data in organized format"""
        
        # Save extraction summary
        summary_file = self.output_path / "extraction_summary.json"
        with open(summary_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        # Save users data
        users_file = self.output_path / "users.json"
        with open(users_file, 'w') as f:
            json.dump(users, f, indent=2)
        
        # Save channels data
        channels_file = self.output_path / "ryan_channels.json"
        with open(channels_file, 'w') as f:
            json.dump(channels, f, indent=2)
        
        # Save messages in JSON format
        messages_file = self.output_path / "ryan_messages.json"
        with open(messages_file, 'w') as f:
            json.dump(messages, f, indent=2)
        
        # Save messages in JSONL format for easier processing
        messages_jsonl = self.output_path / "ryan_messages.jsonl"
        with open(messages_jsonl, 'w') as f:
            for message in messages:
                f.write(json.dumps(message) + "\n")
        
        # Create message type breakdown
        message_types = {}
        ryan_own_messages = []
        ryan_mentions = []
        
        for msg in messages:
            msg_user = msg.get("user", "")
            if msg_user == self.ryan_user_id:
                ryan_own_messages.append(msg)
                msg_type = "ryan_message"
            else:
                ryan_mentions.append(msg)
                msg_type = "ryan_mention"
            
            message_types[msg_type] = message_types.get(msg_type, 0) + 1
        
        # Save categorized messages
        categorized_file = self.output_path / "ryan_messages_categorized.json"
        categorized_data = {
            "summary": {
                "total_messages": len(messages),
                "ryan_own_messages": len(ryan_own_messages),
                "ryan_mentions": len(ryan_mentions),
                "message_types": message_types,
                "date_range": {
                    "start": min(msg["date"] for msg in messages) if messages else None,
                    "end": max(msg["date"] for msg in messages) if messages else None
                }
            },
            "ryan_own_messages": ryan_own_messages,
            "ryan_mentions": ryan_mentions
        }
        
        with open(categorized_file, 'w') as f:
            json.dump(categorized_data, f, indent=2)
        
        print(f"💾 Saved extraction files:")
        print(f"  - Summary: {summary_file}")
        print(f"  - Users: {users_file} ({len(users)} users)")
        print(f"  - Channels: {channels_file} ({len(channels)} channels)")
        print(f"  - Messages JSON: {messages_file} ({len(messages)} messages)")
        print(f"  - Messages JSONL: {messages_jsonl}")
        print(f"  - Categorized: {categorized_file}")
        
        # Print breakdown
        print(f"\n📊 Message Breakdown:")
        print(f"  Ryan's own messages: {len(ryan_own_messages)}")
        print(f"  Messages mentioning Ryan: {len(ryan_mentions)}")
        print(f"  Total: {len(messages)}")


def main():
    """Run Ryan's data extraction from existing Slack data"""
    extractor = RyanDataExtractor()
    results = extractor.extract_ryan_data()
    
    print(f"\n📋 Extraction Results:")
    print(json.dumps(results, indent=2))
    
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)