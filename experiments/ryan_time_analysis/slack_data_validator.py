#!/usr/bin/env python3
"""
SLACK DATA AUTHENTICITY VALIDATOR
=================================

CRITICAL MISSION: Identify if Slack data is SYNTHETIC/FABRICATED

This script specifically targets Slack data patterns that reveal fabrication.
"""

import json
import csv
from collections import Counter, defaultdict
from datetime import datetime
import statistics

class SlackDataValidator:
    """Identifies synthetic Slack data patterns"""
    
    def __init__(self):
        self.messages = []
        self.channels = []
        self.users = []
        self.synthetic_red_flags = []
        
    def load_slack_data(self, base_path):
        """Load all Slack data files"""
        try:
            # Load messages CSV
            messages_file = f"{base_path}/data/processed/slack_messages.csv"
            with open(messages_file, 'r') as f:
                reader = csv.DictReader(f)
                self.messages = list(reader)
            
            # Load channels CSV
            channels_file = f"{base_path}/data/processed/slack_channels.csv"
            with open(channels_file, 'r') as f:
                reader = csv.DictReader(f)
                self.channels = list(reader)
            
            # Load users CSV
            users_file = f"{base_path}/data/processed/slack_users.csv"
            with open(users_file, 'r') as f:
                reader = csv.DictReader(f)
                self.users = list(reader)
                
            print(f"✅ Loaded {len(self.messages)} messages, {len(self.channels)} channels, {len(self.users)} users")
            return True
            
        except Exception as e:
            print(f"❌ Failed to load Slack data: {e}")
            return False
    
    def detect_synthetic_message_patterns(self):
        """Detect synthetic patterns in message content"""
        synthetic_flags = []
        
        # Check for templated message IDs
        message_ids = [msg['message_id'] for msg in self.messages]
        sequential_ids = sum(1 for mid in message_ids if mid.startswith('msg_'))
        
        if sequential_ids > len(message_ids) * 0.8:
            synthetic_flags.append(f"Sequential message IDs detected: {sequential_ids}/{len(message_ids)}")
        
        # Check for repeated content
        message_texts = [msg['text'] for msg in self.messages]
        text_counts = Counter(message_texts)
        duplicates = sum(1 for count in text_counts.values() if count > 1)
        
        if duplicates > 10:
            synthetic_flags.append(f"Suspicious duplicate messages: {duplicates}")
        
        # Check for templated channel IDs
        channel_ids = [msg['channel_id'] for msg in self.messages]
        templated_channels = sum(1 for cid in channel_ids if cid.startswith('C123'))
        
        if templated_channels > 0:
            synthetic_flags.append(f"Template channel IDs found: {templated_channels}")
        
        # Check for artificial user IDs
        user_ids = [msg['user_id'] for msg in self.messages]
        artificial_users = sum(1 for uid in user_ids if uid.startswith('U00000'))
        
        if artificial_users > 0:
            synthetic_flags.append(f"Artificial user IDs found: {artificial_users}")
        
        return synthetic_flags
    
    def check_message_authenticity(self):
        """Check if messages look realistic vs generated"""
        authentic_indicators = 0
        synthetic_indicators = 0
        
        # Check message content
        for msg in self.messages[:100]:  # Sample first 100
            text = msg['text'].lower()
            
            # Authentic patterns
            if any(pattern in text for pattern in ['sync', 'meeting', 'agenda', 'review', 'update']):
                authentic_indicators += 1
            
            # Synthetic patterns
            if any(pattern in text for pattern in ['as ryan suggested', 'ryan mentioned', 'team performance reviews']):
                synthetic_indicators += 1
        
        return {
            'authentic_indicators': authentic_indicators,
            'synthetic_indicators': synthetic_indicators,
            'synthetic_ratio': synthetic_indicators / len(self.messages[:100]) if self.messages else 0
        }
    
    def analyze_timing_patterns(self):
        """Look for unnatural timing patterns"""
        timestamps = []
        
        for msg in self.messages:
            try:
                timestamp = float(msg['timestamp'])
                timestamps.append(timestamp)
            except:
                continue
        
        if not timestamps:
            return {'error': 'No valid timestamps'}
        
        # Check for round number bias in timestamps
        timestamp_endings = [str(int(ts))[-2:] for ts in timestamps]
        ending_counts = Counter(timestamp_endings)
        
        # Real timestamps should be fairly random
        # Synthetic ones might show bias toward certain endings
        most_common_ending = ending_counts.most_common(1)[0] if ending_counts else ('00', 0)
        
        return {
            'total_messages': len(timestamps),
            'timestamp_range_days': (max(timestamps) - min(timestamps)) / 86400,
            'most_common_ending': most_common_ending,
            'ending_bias': most_common_ending[1] / len(timestamps) if timestamps else 0
        }
    
    def validate_slack_structure(self):
        """Check if Slack data structure is realistic"""
        validation_results = {}
        
        # Check channel structure
        if self.channels:
            channel_names = [ch.get('name', '') for ch in self.channels]
            validation_results['channel_analysis'] = {
                'total_channels': len(self.channels),
                'has_dm_channels': any('Direct Message' in name for name in channel_names),
                'has_team_channels': any('team-' in name for name in channel_names),
                'template_channels': sum(1 for name in channel_names if any(temp in name for temp in ['leadership', 'executive', 'engineering']))
            }
        
        # Check user structure  
        if self.users:
            user_ids = [u.get('id', '') for u in self.users]
            validation_results['user_analysis'] = {
                'total_users': len(self.users),
                'template_user_ids': sum(1 for uid in user_ids if uid.startswith('U00000')),
                'real_user_id_pattern': sum(1 for uid in user_ids if uid.startswith('UBL74SKU'))
            }
        
        return validation_results
    
    def generate_slack_authenticity_report(self):
        """Generate comprehensive Slack authenticity report"""
        
        # Run all validations
        synthetic_flags = self.detect_synthetic_message_patterns()
        message_auth = self.check_message_authenticity()
        timing_analysis = self.analyze_timing_patterns()
        structure_validation = self.validate_slack_structure()
        
        # Calculate authenticity score
        authenticity_score = 100
        
        # Deduct for synthetic patterns
        authenticity_score -= len(synthetic_flags) * 20
        authenticity_score -= message_auth['synthetic_ratio'] * 50
        
        # Check for critical synthetic indicators
        critical_synthetic = any([
            any('Template channel IDs' in flag for flag in synthetic_flags),
            any('Artificial user IDs' in flag for flag in synthetic_flags),
            message_auth['synthetic_ratio'] > 0.3
        ])
        
        if critical_synthetic:
            authenticity_score = min(authenticity_score, 30)
        
        authenticity_score = max(0, authenticity_score)
        
        report = {
            'slack_validation_metadata': {
                'validation_timestamp': datetime.now().isoformat(),
                'data_files_analyzed': ['slack_messages.csv', 'slack_channels.csv', 'slack_users.csv'],
                'total_messages_analyzed': len(self.messages)
            },
            'synthetic_detection': {
                'synthetic_flags': synthetic_flags,
                'message_authenticity': message_auth,
                'timing_analysis': timing_analysis,
                'structure_validation': structure_validation
            },
            'overall_assessment': {
                'authenticity_score': authenticity_score,
                'is_synthetic': authenticity_score < 50,
                'critical_synthetic_indicators': critical_synthetic,
                'recommendation': 'DATA IS SYNTHETIC - DO NOT USE' if critical_synthetic else 'Requires further investigation'
            },
            'evidence_of_fabrication': self.get_fabrication_evidence(synthetic_flags, message_auth)
        }
        
        return report
    
    def get_fabrication_evidence(self, synthetic_flags, message_auth):
        """Get specific evidence of data fabrication"""
        evidence = []
        
        if synthetic_flags:
            evidence.extend(synthetic_flags)
        
        if message_auth['synthetic_ratio'] > 0.2:
            evidence.append(f"High synthetic content ratio: {message_auth['synthetic_ratio']:.2%}")
        
        # Check for specific fabricated patterns
        sample_messages = [msg['text'] for msg in self.messages[:20]]
        
        templated_phrases = [
            'As Ryan suggested',
            'Ryan mentioned this',
            'Team performance reviews are due',
            'Strategy review complete',
            'Updated roadmap priorities'
        ]
        
        for phrase in templated_phrases:
            occurrences = sum(1 for msg in sample_messages if phrase in msg)
            if occurrences > 0:
                evidence.append(f"Templated phrase '{phrase}' found {occurrences} times in sample")
        
        return evidence

def main():
    """Run Slack data validation"""
    print("🚨 SLACK DATA AUTHENTICITY VALIDATION")
    print("=" * 50)
    
    base_path = "/Users/david.campos/VibeCode/AICoS-Lab/experiments/ryan_time_analysis"
    
    validator = SlackDataValidator()
    
    if validator.load_slack_data(base_path):
        report = validator.generate_slack_authenticity_report()
        
        # Save report
        report_file = f"{base_path}/slack_authenticity_report.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print("\n🎯 SLACK VALIDATION RESULTS")
        print("=" * 50)
        print(f"📊 Authenticity Score: {report['overall_assessment']['authenticity_score']}/100")
        print(f"🚨 Is Synthetic: {report['overall_assessment']['is_synthetic']}")
        print(f"⚠️  Critical Indicators: {report['overall_assessment']['critical_synthetic_indicators']}")
        print(f"💡 Recommendation: {report['overall_assessment']['recommendation']}")
        
        if report['evidence_of_fabrication']:
            print(f"\n🔍 EVIDENCE OF FABRICATION:")
            for evidence in report['evidence_of_fabrication']:
                print(f"   • {evidence}")
        
        print(f"\n📄 Report saved: {report_file}")
        
        return not report['overall_assessment']['is_synthetic']
    
    return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)