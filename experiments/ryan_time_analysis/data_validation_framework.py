#!/usr/bin/env python3
"""
RYAN MARIEN TIME ANALYSIS - DATA AUTHENTICITY VALIDATION FRAMEWORK
==================================================================

CRITICAL MISSION: Validate that calendar data is REAL, not synthetic/fabricated

This script performs comprehensive validation checks on calendar data to determine
authenticity with high confidence.
"""

import json
import hashlib
import re
from datetime import datetime, timedelta
from collections import Counter, defaultdict
from pathlib import Path
import statistics

class CalendarDataValidator:
    """Comprehensive calendar data authenticity validator"""
    
    def __init__(self, calendar_file_path):
        self.calendar_file_path = Path(calendar_file_path)
        self.events = []
        self.validation_results = {}
        self.authenticity_score = 0
        
        # RED FLAGS for synthetic data
        self.synthetic_red_flags = [
            'Meeting 1', 'Meeting 2', 'Test Meeting', 'Sample Event',
            'Lorem ipsum', 'placeholder', 'template', 'fake', 'example',
            'Generic Meeting', 'Test Event', 'Sample Title'
        ]
        
        # REALISTIC PATTERNS indicators
        self.realistic_patterns = [
            '@biorender.com', 'zoom.us', 'lattice', '1:1', 'team-', 
            'Nomi', 'lunch', 'workout', 'synergy', 'summer', 'hard work'
        ]
    
    def load_calendar_data(self):
        """Load and parse calendar JSONL file"""
        try:
            self.events = []
            with open(self.calendar_file_path, 'r') as f:
                for line in f:
                    if line.strip():
                        self.events.append(json.loads(line))
            print(f"✅ Loaded {len(self.events)} calendar events")
            return True
        except Exception as e:
            print(f"❌ Failed to load calendar data: {e}")
            return False
    
    def validate_event_count(self):
        """Validate claimed event count of 2,358"""
        actual_count = len(self.events)
        claimed_count = 2358
        
        count_match = actual_count == claimed_count
        
        result = {
            'claimed_count': claimed_count,
            'actual_count': actual_count,
            'count_matches': count_match,
            'confidence': 100 if count_match else 0
        }
        
        self.validation_results['event_count'] = result
        return result
    
    def validate_date_range(self):
        """Validate claimed date range: Aug 20, 2024 - Feb 7, 2025"""
        if not self.events:
            return {'error': 'No events loaded'}
        
        # Extract all dates
        dates = []
        for event in self.events:
            try:
                date_str = event['start']['dateTime']
                date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                dates.append(date_obj)
            except:
                continue
        
        if not dates:
            return {'error': 'No valid dates found'}
        
        dates.sort()
        actual_start = dates[0].date()
        actual_end = dates[-1].date()
        
        # Expected range
        expected_start = datetime(2024, 8, 20).date()
        expected_end = datetime(2025, 2, 7).date()
        
        date_range_valid = (
            abs((actual_start - expected_start).days) <= 1 and
            abs((actual_end - expected_end).days) <= 1
        )
        
        result = {
            'expected_start': str(expected_start),
            'expected_end': str(expected_end),
            'actual_start': str(actual_start),
            'actual_end': str(actual_end),
            'date_range_valid': date_range_valid,
            'total_span_days': (actual_end - actual_start).days,
            'confidence': 90 if date_range_valid else 20
        }
        
        self.validation_results['date_range'] = result
        return result
    
    def check_meeting_titles_authenticity(self):
        """Analyze meeting titles for realistic vs synthetic patterns"""
        if not self.events:
            return {'error': 'No events loaded'}
        
        titles = [event.get('summary', '') for event in self.events]
        
        # Check for synthetic red flags
        synthetic_flags = 0
        realistic_indicators = 0
        
        for title in titles:
            title_lower = title.lower()
            
            # Count synthetic red flags
            for flag in self.synthetic_red_flags:
                if flag.lower() in title_lower:
                    synthetic_flags += 1
                    break
            
            # Count realistic indicators
            for pattern in self.realistic_patterns:
                if pattern.lower() in title_lower:
                    realistic_indicators += 1
                    break
        
        # Analyze title patterns
        title_counter = Counter(titles)
        most_common_titles = title_counter.most_common(10)
        
        # Check for template-like repetition
        repeated_titles = sum(1 for count in title_counter.values() if count > 50)
        
        authenticity_indicators = {
            'biorender_references': sum(1 for t in titles if 'biorender' in t.lower()),
            'personal_references': sum(1 for t in titles if any(name in t.lower() for name in ['nomi', 'ryan', 'natalie'])),
            'meeting_types': sum(1 for t in titles if any(mt in t.lower() for mt in ['1:1', 'lunch', 'workout', 'sync'])),
            'company_events': sum(1 for t in titles if any(ce in t.lower() for ce in ['synergy', 'summer', 'team']))
        }
        
        result = {
            'total_titles': len(titles),
            'unique_titles': len(set(titles)),
            'synthetic_flags': synthetic_flags,
            'realistic_indicators': realistic_indicators,
            'repeated_titles_over_50': repeated_titles,
            'most_common_titles': most_common_titles,
            'authenticity_indicators': authenticity_indicators,
            'authenticity_score': max(0, min(100, 
                (realistic_indicators / len(titles)) * 100 - 
                (synthetic_flags / len(titles)) * 50
            ))
        }
        
        self.validation_results['meeting_titles'] = result
        return result
    
    def validate_attendee_emails(self):
        """Check for realistic email patterns vs synthetic domains"""
        if not self.events:
            return {'error': 'No events loaded'}
        
        all_emails = []
        
        for event in self.events:
            # Organizer email
            if 'organizer' in event and 'email' in event['organizer']:
                all_emails.append(event['organizer']['email'])
            
            # Attendee emails
            if 'attendees' in event:
                for attendee in event['attendees']:
                    if 'email' in attendee:
                        all_emails.append(attendee['email'])
        
        # Analyze email domains
        email_domains = Counter()
        valid_email_pattern = re.compile(r'^[^@]+@[^@]+\.[^@]+$')
        
        valid_emails = 0
        synthetic_domains = 0
        
        synthetic_domain_patterns = ['example.com', 'test.com', 'fake.com', 'sample.com']
        
        for email in all_emails:
            if valid_email_pattern.match(email):
                valid_emails += 1
                domain = email.split('@')[1]
                email_domains[domain] += 1
                
                if any(sd in domain.lower() for sd in synthetic_domain_patterns):
                    synthetic_domains += 1
        
        # Check for realistic domain patterns
        biorender_emails = sum(1 for e in all_emails if 'biorender.com' in e)
        google_calendar_emails = sum(1 for e in all_emails if 'group.calendar.google.com' in e)
        
        result = {
            'total_emails': len(all_emails),
            'valid_email_format': valid_emails,
            'synthetic_domains': synthetic_domains,
            'biorender_emails': biorender_emails,
            'google_calendar_emails': google_calendar_emails,
            'top_domains': dict(email_domains.most_common(10)),
            'email_validity_score': (valid_emails / len(all_emails) * 100) if all_emails else 0
        }
        
        self.validation_results['attendee_emails'] = result
        return result
    
    def check_meeting_durations(self):
        """Analyze meeting duration patterns for realism"""
        if not self.events:
            return {'error': 'No events loaded'}
        
        durations = []
        
        for event in self.events:
            try:
                start_str = event['start']['dateTime']
                end_str = event['end']['dateTime']
                
                start = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
                end = datetime.fromisoformat(end_str.replace('Z', '+00:00'))
                
                duration_minutes = (end - start).total_seconds() / 60
                durations.append(duration_minutes)
            except:
                continue
        
        if not durations:
            return {'error': 'No valid durations found'}
        
        # Analyze duration patterns
        duration_counter = Counter(durations)
        common_durations = duration_counter.most_common(10)
        
        # Check for realistic patterns (15, 30, 60 minute meetings are common)
        standard_durations = [15, 30, 45, 60, 90, 120]
        standard_duration_events = sum(duration_counter[d] for d in standard_durations if d in duration_counter)
        
        result = {
            'total_events_with_duration': len(durations),
            'average_duration_minutes': statistics.mean(durations),
            'median_duration_minutes': statistics.median(durations),
            'min_duration_minutes': min(durations),
            'max_duration_minutes': max(durations),
            'common_durations': common_durations,
            'standard_duration_events': standard_duration_events,
            'standard_duration_percentage': (standard_duration_events / len(durations) * 100) if durations else 0
        }
        
        self.validation_results['meeting_durations'] = result
        return result
    
    def detect_synthetic_patterns(self):
        """Look for patterns that suggest synthetic/generated data"""
        if not self.events:
            return {'error': 'No events loaded'}
        
        synthetic_markers = {
            'perfect_distributions': 0,
            'round_number_bias': 0,
            'template_patterns': 0,
            'unrealistic_regularity': 0
        }
        
        # Check for perfect hour alignment (suspicious if too many)
        hour_aligned = sum(1 for event in self.events 
                          if event.get('start', {}).get('dateTime', '').endswith(':00:00-04:00'))
        
        # Check for suspiciously regular patterns
        daily_counts = defaultdict(int)
        for event in self.events:
            try:
                date_str = event['start']['dateTime'][:10]  # Get YYYY-MM-DD
                daily_counts[date_str] += 1
            except:
                continue
        
        # Look for days with suspiciously similar event counts
        count_values = list(daily_counts.values())
        if count_values:
            count_mode = statistics.mode(count_values)
            mode_frequency = count_values.count(count_mode)
            total_days = len(count_values)
            regularity_score = (mode_frequency / total_days) * 100
            
            if regularity_score > 80:  # More than 80% of days have same count
                synthetic_markers['unrealistic_regularity'] = regularity_score
        
        result = {
            'hour_aligned_events': hour_aligned,
            'hour_aligned_percentage': (hour_aligned / len(self.events) * 100) if self.events else 0,
            'daily_event_counts': dict(daily_counts),
            'synthetic_markers': synthetic_markers,
            'regularity_suspicion': synthetic_markers['unrealistic_regularity'] > 70
        }
        
        self.validation_results['synthetic_patterns'] = result
        return result
    
    def calculate_file_integrity(self):
        """Calculate file checksums and integrity measures"""
        if not self.calendar_file_path.exists():
            return {'error': 'File not found'}
        
        # Calculate file hash
        sha256_hash = hashlib.sha256()
        with open(self.calendar_file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        
        file_stats = self.calendar_file_path.stat()
        
        result = {
            'file_path': str(self.calendar_file_path),
            'file_size_bytes': file_stats.st_size,
            'file_size_mb': round(file_stats.st_size / (1024 * 1024), 2),
            'sha256_checksum': sha256_hash.hexdigest(),
            'last_modified': datetime.fromtimestamp(file_stats.st_mtime).isoformat(),
            'line_count': len(self.events) if self.events else 0
        }
        
        self.validation_results['file_integrity'] = result
        return result
    
    def extract_sample_events(self, sample_size=10):
        """Extract sample events as evidence of authenticity"""
        if not self.events or len(self.events) < sample_size:
            return {'error': 'Insufficient events for sampling'}
        
        # Select diverse sample events
        sample_indices = [
            0,  # First event
            len(self.events) - 1,  # Last event
            *[i for i in range(100, len(self.events), len(self.events) // (sample_size - 2))]
        ][:sample_size]
        
        sample_events = []
        for i in sample_indices:
            if i < len(self.events):
                event = self.events[i].copy()
                # Keep only key fields for sample
                sample_event = {
                    'id': event.get('id', 'N/A'),
                    'summary': event.get('summary', 'N/A'),
                    'start': event.get('start', {}).get('dateTime', 'N/A'),
                    'attendee_count': event.get('attendee_count', 0),
                    'organizer_email': event.get('organizer', {}).get('email', 'N/A'),
                    'description_length': len(event.get('description', '')),
                    'has_external_attendees': event.get('has_external_attendees', False)
                }
                sample_events.append(sample_event)
        
        self.validation_results['sample_events'] = sample_events
        return sample_events
    
    def run_comprehensive_validation(self):
        """Run all validation checks and calculate overall authenticity score"""
        print("🔍 RYAN MARIEN CALENDAR DATA AUTHENTICITY VALIDATION")
        print("=" * 60)
        
        if not self.load_calendar_data():
            return False
        
        # Run all validation checks
        validation_checks = [
            ('Event Count', self.validate_event_count),
            ('Date Range', self.validate_date_range),
            ('Meeting Titles', self.check_meeting_titles_authenticity),
            ('Attendee Emails', self.validate_attendee_emails),
            ('Meeting Durations', self.check_meeting_durations),
            ('Synthetic Patterns', self.detect_synthetic_patterns),
            ('File Integrity', self.calculate_file_integrity),
            ('Sample Events', self.extract_sample_events)
        ]
        
        for check_name, check_function in validation_checks:
            print(f"\n⚡ Running: {check_name}")
            result = check_function()
            if 'error' not in result:
                print(f"✅ {check_name} validation completed")
            else:
                print(f"❌ {check_name} validation failed: {result['error']}")
        
        # Calculate overall authenticity score
        self.calculate_authenticity_score()
        
        return True
    
    def calculate_authenticity_score(self):
        """Calculate overall authenticity score based on all validation results"""
        score_components = []
        
        # Event count accuracy (20% weight)
        if 'event_count' in self.validation_results:
            score_components.append((self.validation_results['event_count'].get('confidence', 0), 20))
        
        # Date range accuracy (15% weight)
        if 'date_range' in self.validation_results:
            score_components.append((self.validation_results['date_range'].get('confidence', 0), 15))
        
        # Meeting titles authenticity (25% weight)
        if 'meeting_titles' in self.validation_results:
            score_components.append((self.validation_results['meeting_titles'].get('authenticity_score', 0), 25))
        
        # Email validity (15% weight)
        if 'attendee_emails' in self.validation_results:
            score_components.append((self.validation_results['attendee_emails'].get('email_validity_score', 0), 15))
        
        # Duration realism (10% weight)
        if 'meeting_durations' in self.validation_results:
            standard_pct = self.validation_results['meeting_durations'].get('standard_duration_percentage', 0)
            duration_score = min(100, standard_pct * 2)  # Scale to 100
            score_components.append((duration_score, 10))
        
        # Synthetic pattern detection (15% weight) - inverse scoring
        if 'synthetic_patterns' in self.validation_results:
            regularity = self.validation_results['synthetic_patterns']['synthetic_markers'].get('unrealistic_regularity', 0)
            synthetic_score = max(0, 100 - regularity)  # Lower regularity = higher authenticity
            score_components.append((synthetic_score, 15))
        
        # Calculate weighted average
        if score_components:
            total_weighted_score = sum(score * weight for score, weight in score_components)
            total_weight = sum(weight for _, weight in score_components)
            self.authenticity_score = total_weighted_score / total_weight
        else:
            self.authenticity_score = 0
        
        self.validation_results['overall_authenticity_score'] = round(self.authenticity_score, 2)
    
    def generate_validation_report(self):
        """Generate comprehensive validation report"""
        report = {
            'validation_metadata': {
                'validation_timestamp': datetime.now().isoformat(),
                'calendar_file_path': str(self.calendar_file_path),
                'validator_version': '1.0',
                'validation_purpose': 'Ryan Marien time analysis data authenticity verification'
            },
            'validation_results': self.validation_results,
            'overall_assessment': {
                'authenticity_score': self.authenticity_score,
                'data_classification': self.classify_data_authenticity(),
                'confidence_level': self.get_confidence_level(),
                'recommendation': self.get_recommendation()
            },
            'key_evidence': self.get_key_evidence(),
            'red_flags': self.get_red_flags()
        }
        
        return report
    
    def classify_data_authenticity(self):
        """Classify data as AUTHENTIC, SYNTHETIC, or QUESTIONABLE"""
        if self.authenticity_score >= 85:
            return 'AUTHENTIC'
        elif self.authenticity_score >= 60:
            return 'QUESTIONABLE'
        else:
            return 'SYNTHETIC'
    
    def get_confidence_level(self):
        """Get confidence level in the assessment"""
        if self.authenticity_score >= 90 or self.authenticity_score <= 30:
            return 'HIGH'
        elif self.authenticity_score >= 70 or self.authenticity_score <= 50:
            return 'MEDIUM'
        else:
            return 'LOW'
    
    def get_recommendation(self):
        """Get recommendation based on validation results"""
        classification = self.classify_data_authenticity()
        
        if classification == 'AUTHENTIC':
            return 'Data appears to be genuine calendar export. Safe to use for analysis.'
        elif classification == 'QUESTIONABLE':
            return 'Data shows mixed indicators. Recommend manual review of sample events before proceeding.'
        else:
            return 'Data shows strong indicators of being synthetic/fabricated. DO NOT USE for analysis.'
    
    def get_key_evidence(self):
        """Extract key pieces of evidence supporting the assessment"""
        evidence = []
        
        if 'event_count' in self.validation_results:
            count_data = self.validation_results['event_count']
            evidence.append(f"Event count matches claim: {count_data['count_matches']} ({count_data['actual_count']} events)")
        
        if 'meeting_titles' in self.validation_results:
            titles_data = self.validation_results['meeting_titles']
            evidence.append(f"Realistic meeting titles: {titles_data['realistic_indicators']}/{titles_data['total_titles']}")
            evidence.append(f"BioRender references: {titles_data['authenticity_indicators']['biorender_references']}")
        
        if 'attendee_emails' in self.validation_results:
            email_data = self.validation_results['attendee_emails']
            evidence.append(f"Valid email formats: {email_data['email_validity_score']:.1f}%")
            evidence.append(f"BioRender emails: {email_data['biorender_emails']}")
        
        return evidence
    
    def get_red_flags(self):
        """Extract any red flags found during validation"""
        red_flags = []
        
        if 'meeting_titles' in self.validation_results:
            synthetic_flags = self.validation_results['meeting_titles']['synthetic_flags']
            if synthetic_flags > 0:
                red_flags.append(f"Found {synthetic_flags} synthetic title patterns")
        
        if 'synthetic_patterns' in self.validation_results:
            if self.validation_results['synthetic_patterns']['regularity_suspicion']:
                red_flags.append("Suspiciously regular daily event patterns detected")
        
        if 'attendee_emails' in self.validation_results:
            synthetic_domains = self.validation_results['attendee_emails']['synthetic_domains']
            if synthetic_domains > 0:
                red_flags.append(f"Found {synthetic_domains} synthetic email domains")
        
        return red_flags

def main():
    """Main validation execution"""
    calendar_file = "/Users/david.campos/VibeCode/AICoS-Lab/experiments/ryan_time_analysis/data/raw/calendar_full_6months/ryan_calendar_6months.jsonl"
    
    validator = CalendarDataValidator(calendar_file)
    
    if validator.run_comprehensive_validation():
        # Generate and save validation report
        report = validator.generate_validation_report()
        
        # Save validation report
        report_file = "/Users/david.campos/VibeCode/AICoS-Lab/experiments/ryan_time_analysis/data_validation_report.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print("\n" + "=" * 60)
        print("🎯 VALIDATION SUMMARY")
        print("=" * 60)
        print(f"📊 Overall Authenticity Score: {validator.authenticity_score:.1f}/100")
        print(f"📝 Data Classification: {validator.classify_data_authenticity()}")
        print(f"🎯 Confidence Level: {validator.get_confidence_level()}")
        print(f"💡 Recommendation: {validator.get_recommendation()}")
        
        print(f"\n📄 Full validation report saved to: {report_file}")
        
        return validator.authenticity_score >= 70  # Return True if likely authentic
    
    return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)