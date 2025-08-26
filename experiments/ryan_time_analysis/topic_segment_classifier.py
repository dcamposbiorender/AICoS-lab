#!/usr/bin/env python3
"""
Sub-Agent 2: Topic & Segment Classification System
Classifies 2,358 authenticated calendar events by topic and company segment
Creates data for topic×segment×week heatmap visualization
"""

import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import re
from collections import defaultdict, Counter
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional, Set
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class MeetingEvent:
    """Structure for calendar event data"""
    event_id: str
    summary: str
    start_datetime: datetime
    end_datetime: datetime
    duration_minutes: int
    attendees: List[dict]
    organizer: dict
    has_external_attendees: bool
    calendar_week: str
    iso_week: int
    iso_year: int

@dataclass
class TopicClassification:
    """Structure for topic classification results"""
    topic: str
    subtopic: str
    confidence: float
    keywords_matched: List[str]

@dataclass
class SegmentClassification:
    """Structure for segment classification results"""
    segment: str
    subsegment: str
    confidence: float
    attendee_analysis: dict

class TopicClassifier:
    """Classifies meetings by topic based on title analysis"""
    
    def __init__(self):
        self.topic_keywords = {
            'Engineering': {
                'keywords': [
                    'standup', 'sprint', 'technical', 'arch', 'architecture', 'code', 'dev', 
                    'engineering', 'build', 'deploy', 'infrastructure', 'tech', 'api',
                    'backend', 'frontend', 'database', 'system', 'platform', 'scrum',
                    'retrospective', 'retro', 'review', 'bug', 'feature', 'release'
                ],
                'subtopics': {
                    'Development': ['code', 'dev', 'programming', 'build', 'deploy'],
                    'Architecture': ['arch', 'architecture', 'technical', 'system', 'platform'],
                    'Process': ['standup', 'sprint', 'scrum', 'retrospective', 'retro']
                }
            },
            'Product': {
                'keywords': [
                    'roadmap', 'feature', 'spec', 'design', 'product', 'ux', 'ui', 'user',
                    'customer', 'requirement', 'wireframe', 'prototype', 'usability',
                    'research', 'analytics', 'metrics', 'feedback', 'testing'
                ],
                'subtopics': {
                    'Strategy': ['roadmap', 'strategy', 'planning', 'vision'],
                    'Design': ['design', 'ux', 'ui', 'wireframe', 'prototype'],
                    'Research': ['research', 'analytics', 'metrics', 'feedback', 'user']
                }
            },
            'Go_to_Market': {
                'keywords': [
                    'sales', 'marketing', 'customer', 'gtm', 'go-to-market', 'launch', 
                    'campaign', 'revenue', 'growth', 'market', 'lead', 'prospect',
                    'demo', 'pitch', 'proposal', 'contract', 'deal', 'pipeline',
                    'acquisition', 'retention', 'churn', 'expansion'
                ],
                'subtopics': {
                    'Sales': ['sales', 'deal', 'pipeline', 'prospect', 'contract', 'revenue'],
                    'Marketing': ['marketing', 'campaign', 'launch', 'acquisition', 'lead'],
                    'Customer Success': ['customer', 'retention', 'expansion', 'success']
                }
            },
            'Operations': {
                'keywords': [
                    'ops', 'finance', 'legal', 'hr', 'admin', 'operations', 'budget',
                    'compliance', 'policy', 'payroll', 'benefits', 'hiring', 'onboarding',
                    'accounting', 'audit', 'risk', 'security', 'procurement'
                ],
                'subtopics': {
                    'Finance': ['finance', 'budget', 'accounting', 'audit', 'revenue'],
                    'HR': ['hr', 'hiring', 'onboarding', 'benefits', 'payroll'],
                    'Legal': ['legal', 'compliance', 'policy', 'risk', 'contract']
                }
            },
            'Leadership_Strategy': {
                'keywords': [
                    'strategy', 'board', 'exec', 'executive', 'planning', 'vision', 
                    'okrs', 'goals', 'leadership', 'decision', 'quarterly', 'annual',
                    'review', 'performance', 'culture', 'transformation', 'roadmap'
                ],
                'subtopics': {
                    'Strategic Planning': ['strategy', 'planning', 'vision', 'roadmap'],
                    'Executive': ['exec', 'executive', 'board', 'leadership'],
                    'Performance': ['okrs', 'goals', 'review', 'performance']
                }
            },
            'People_1on1': {
                'keywords': [
                    '1:1', '1-1', 'one-on-one', 'catch up', 'check-in', 'feedback', 
                    'review', 'career', 'coaching', 'mentoring', 'development',
                    'performance', 'growth', 'personal'
                ],
                'subtopics': {
                    'Regular 1:1s': ['1:1', '1-1', 'one-on-one'],
                    'Coaching': ['coaching', 'mentoring', 'development', 'growth'],
                    'Feedback': ['feedback', 'review', 'performance']
                }
            },
            'External_Business': {
                'keywords': [
                    'partnership', 'vendor', 'client', 'external', 'business development',
                    'bd', 'integration', 'collaboration', 'alliance', 'supplier',
                    'contractor', 'consultant', 'advisory', 'investor'
                ],
                'subtopics': {
                    'Partnerships': ['partnership', 'alliance', 'collaboration'],
                    'Vendors': ['vendor', 'supplier', 'contractor'],
                    'Business Development': ['bd', 'business development', 'client']
                }
            },
            'Recruiting_Hiring': {
                'keywords': [
                    'interview', 'practical', 'candidate', 'hiring', 'recruit',
                    'feedback', 'debrief', 'career walkthrough', 'screening',
                    'panel', 'reference', 'offer'
                ],
                'subtopics': {
                    'Interviews': ['interview', 'practical', 'screening', 'panel'],
                    'Process': ['debrief', 'feedback', 'reference', 'offer'],
                    'Strategy': ['hiring', 'recruit', 'strategy']
                }
            },
            'Personal_Life': {
                'keywords': [
                    'lunch', 'dinner', 'workout', 'personal', 'family', 'nomi',
                    'bath', 'bed time', 'break', 'buffer', 'travel', 'vacation',
                    'ooo', 'out of office', 'heads down', 'plan for tomorrow'
                ],
                'subtopics': {
                    'Meals': ['lunch', 'dinner'],
                    'Family': ['nomi', 'family', 'personal'],
                    'Fitness': ['workout', 'exercise'],
                    'Admin': ['break', 'buffer', 'travel', 'plan for tomorrow']
                }
            }
        }
    
    def classify_topic(self, meeting_title: str) -> TopicClassification:
        """Classify meeting topic based on title keywords"""
        title_lower = meeting_title.lower()
        
        # Remove common noise words and brackets
        title_clean = re.sub(r'[\[\](){}]', ' ', title_lower)
        title_clean = re.sub(r'\s+', ' ', title_clean).strip()
        
        best_topic = 'Uncategorized'
        best_subtopic = 'General'
        max_score = 0
        matched_keywords = []
        
        for topic, config in self.topic_keywords.items():
            score = 0
            current_matches = []
            
            # Check for keyword matches
            for keyword in config['keywords']:
                if keyword in title_clean:
                    score += 1
                    current_matches.append(keyword)
            
            # Bonus for exact matches and important keywords
            if any(kw in title_clean for kw in ['1:1', 'standup', 'interview', 'practical']):
                score += 2
            
            if score > max_score:
                max_score = score
                best_topic = topic
                matched_keywords = current_matches
                
                # Determine subtopic
                best_subtopic = 'General'
                for subtopic, sub_keywords in config.get('subtopics', {}).items():
                    if any(kw in title_clean for kw in sub_keywords):
                        best_subtopic = subtopic
                        break
        
        # Special handling for common patterns
        if '1:1' in title_clean or 'one-on-one' in title_clean:
            best_topic = 'People_1on1'
            best_subtopic = 'Regular 1:1s'
            max_score = max(max_score, 3)
        
        if any(word in title_clean for word in ['interview', 'practical', 'debrief']):
            best_topic = 'Recruiting_Hiring'
            max_score = max(max_score, 3)
        
        if any(word in title_clean for word in ['lunch', 'dinner', 'workout', 'nomi']):
            best_topic = 'Personal_Life'
            max_score = max(max_score, 2)
        
        confidence = min(max_score / 3.0, 1.0)  # Normalize to 0-1
        
        return TopicClassification(
            topic=best_topic,
            subtopic=best_subtopic,
            confidence=confidence,
            keywords_matched=matched_keywords
        )

class SegmentClassifier:
    """Classifies meetings by company segment based on attendee analysis"""
    
    def __init__(self):
        self.role_segments = {
            'Engineering': [
                'engineering', 'engineer', 'dev', 'developer', 'tech', 'technical',
                'architect', 'backend', 'frontend', 'fullstack', 'devops', 'sre',
                'platform', 'infrastructure', 'software', 'qa', 'test'
            ],
            'Product': [
                'product', 'design', 'designer', 'ux', 'ui', 'research', 'researcher',
                'pm', 'product manager', 'user experience', 'user interface',
                'analytics', 'data'
            ],
            'Go_to_Market': [
                'sales', 'marketing', 'gtm', 'go-to-market', 'growth', 'customer success',
                'account', 'revenue', 'business development', 'bd', 'partnerships',
                'demand generation', 'content', 'brand'
            ],
            'Operations': [
                'ops', 'operations', 'finance', 'hr', 'human resources', 'legal',
                'admin', 'accounting', 'payroll', 'benefits', 'recruiting',
                'talent', 'people', 'office manager'
            ],
            'Leadership': [
                'ceo', 'cto', 'cfo', 'cmo', 'coo', 'vp', 'vice president',
                'director', 'head of', 'chief', 'executive', 'senior leadership',
                'founder', 'co-founder'
            ]
        }
        
        self.biorender_domains = ['biorender.com', 'biorender.ca']
        
    def classify_segment(self, attendees: List[dict], has_external: bool) -> SegmentClassification:
        """Classify meeting segment based on attendee analysis"""
        
        if not attendees:
            return SegmentClassification(
                segment='Internal',
                subsegment='Individual',
                confidence=1.0,
                attendee_analysis={'total': 0, 'internal': 0, 'external': 0}
            )
        
        internal_count = 0
        external_count = 0
        segment_counts = defaultdict(int)
        
        # Analyze each attendee
        for attendee in attendees:
            email = attendee.get('email', '')
            display_name = attendee.get('displayName', '')
            
            # Determine if internal or external
            is_internal = any(domain in email for domain in self.biorender_domains)
            
            if is_internal:
                internal_count += 1
                
                # Try to classify role segment based on email/name
                role_segment = self._classify_role_segment(email, display_name)
                segment_counts[role_segment] += 1
            else:
                external_count += 1
        
        total_attendees = len(attendees)
        
        # Determine primary segment
        if external_count > internal_count:
            primary_segment = 'External'
            subsegment = 'Client_Partner'
            confidence = 0.9
        elif external_count > 0:
            primary_segment = 'Mixed'
            subsegment = 'Internal_External'
            confidence = 0.8
        else:
            primary_segment = 'Internal'
            if segment_counts:
                # Find most common internal segment
                most_common_segment = max(segment_counts, key=segment_counts.get)
                subsegment = most_common_segment
                confidence = 0.7 + (segment_counts[most_common_segment] / internal_count) * 0.3
            else:
                subsegment = 'General'
                confidence = 0.5
        
        attendee_analysis = {
            'total': total_attendees,
            'internal': internal_count,
            'external': external_count,
            'segment_distribution': dict(segment_counts)
        }
        
        return SegmentClassification(
            segment=primary_segment,
            subsegment=subsegment,
            confidence=confidence,
            attendee_analysis=attendee_analysis
        )
    
    def _classify_role_segment(self, email: str, display_name: str) -> str:
        """Classify role segment based on email and display name"""
        text_to_analyze = f"{email} {display_name}".lower()
        
        for segment, keywords in self.role_segments.items():
            if any(keyword in text_to_analyze for keyword in keywords):
                return segment
        
        return 'General'

class TimeAnalyzer:
    """Analyzes meeting timing patterns"""
    
    @staticmethod
    def get_iso_week(date_obj: datetime) -> Tuple[int, int]:
        """Get ISO year and week number"""
        return date_obj.isocalendar()[:2]  # year, week
    
    @staticmethod
    def get_week_string(date_obj: datetime) -> str:
        """Get human-readable week string"""
        year, week = TimeAnalyzer.get_iso_week(date_obj)
        return f"{year}-W{week:02d}"

class CalendarAnalyzer:
    """Main analyzer for calendar events"""
    
    def __init__(self, calendar_file: str):
        self.calendar_file = calendar_file
        self.topic_classifier = TopicClassifier()
        self.segment_classifier = SegmentClassifier()
        self.events = []
        self.classified_events = []
    
    def load_calendar_data(self) -> List[MeetingEvent]:
        """Load and parse calendar events from JSONL file"""
        logger.info(f"Loading calendar data from: {self.calendar_file}")
        
        events = []
        with open(self.calendar_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    event_data = json.loads(line.strip())
                    
                    # Parse datetime
                    start_dt = datetime.fromisoformat(
                        event_data['start']['dateTime'].replace('Z', '+00:00')
                    )
                    end_dt = datetime.fromisoformat(
                        event_data['end']['dateTime'].replace('Z', '+00:00')
                    )
                    
                    # Create meeting event
                    meeting = MeetingEvent(
                        event_id=event_data['id'],
                        summary=event_data.get('summary', 'No Title'),
                        start_datetime=start_dt,
                        end_datetime=end_dt,
                        duration_minutes=event_data.get('meeting_duration_minutes', 0),
                        attendees=event_data.get('attendees', []),
                        organizer=event_data.get('organizer', {}),
                        has_external_attendees=event_data.get('has_external_attendees', False),
                        calendar_week=TimeAnalyzer.get_week_string(start_dt),
                        iso_week=TimeAnalyzer.get_iso_week(start_dt)[1],
                        iso_year=TimeAnalyzer.get_iso_week(start_dt)[0]
                    )
                    
                    events.append(meeting)
                    
                except Exception as e:
                    logger.warning(f"Error parsing line {line_num}: {e}")
                    continue
        
        logger.info(f"Loaded {len(events)} calendar events")
        self.events = events
        return events
    
    def classify_all_events(self) -> List[dict]:
        """Classify all events by topic and segment"""
        logger.info("Classifying all events by topic and segment")
        
        classified_events = []
        
        for i, event in enumerate(self.events):
            # Classify topic
            topic_class = self.topic_classifier.classify_topic(event.summary)
            
            # Classify segment
            segment_class = self.segment_classifier.classify_segment(
                event.attendees, 
                event.has_external_attendees
            )
            
            # Create classified event record
            classified_event = {
                'event_id': event.event_id,
                'summary': event.summary,
                'start_datetime': event.start_datetime.isoformat(),
                'end_datetime': event.end_datetime.isoformat(),
                'duration_minutes': event.duration_minutes,
                'calendar_week': event.calendar_week,
                'iso_week': event.iso_week,
                'iso_year': event.iso_year,
                
                # Topic classification
                'topic': topic_class.topic,
                'subtopic': topic_class.subtopic,
                'topic_confidence': topic_class.confidence,
                'keywords_matched': topic_class.keywords_matched,
                
                # Segment classification
                'segment': segment_class.segment,
                'subsegment': segment_class.subsegment,
                'segment_confidence': segment_class.confidence,
                'attendee_analysis': segment_class.attendee_analysis,
                
                # Additional metadata
                'has_external_attendees': event.has_external_attendees,
                'attendee_count': len(event.attendees),
                'organizer_email': event.organizer.get('email', ''),
                'is_self_organized': event.organizer.get('self', False)
            }
            
            classified_events.append(classified_event)
            
            if (i + 1) % 500 == 0:
                logger.info(f"Classified {i + 1}/{len(self.events)} events")
        
        logger.info(f"Classification complete: {len(classified_events)} events classified")
        self.classified_events = classified_events
        return classified_events
    
    def create_weekly_matrix(self) -> pd.DataFrame:
        """Create topic × segment × week engagement matrix"""
        logger.info("Creating weekly topic×segment engagement matrix")
        
        # Create base dataframe
        matrix_data = []
        
        for event in self.classified_events:
            matrix_data.append({
                'calendar_week': event['calendar_week'],
                'iso_year': event['iso_year'],
                'iso_week': event['iso_week'],
                'topic': event['topic'],
                'segment': event['segment'],
                'subsegment': event['subsegment'],
                'duration_minutes': event['duration_minutes'],
                'duration_hours': event['duration_minutes'] / 60.0,
                'event_count': 1,
                'topic_confidence': event['topic_confidence'],
                'segment_confidence': event['segment_confidence']
            })
        
        df = pd.DataFrame(matrix_data)
        
        # Create weekly aggregation
        weekly_agg = df.groupby(['calendar_week', 'iso_year', 'iso_week', 'topic', 'segment']).agg({
            'duration_hours': 'sum',
            'duration_minutes': 'sum',
            'event_count': 'sum',
            'topic_confidence': 'mean',
            'segment_confidence': 'mean'
        }).reset_index()
        
        logger.info(f"Created weekly matrix with {len(weekly_agg)} topic×segment×week combinations")
        return weekly_agg
    
    def generate_summary_statistics(self) -> dict:
        """Generate summary statistics for the analysis"""
        logger.info("Generating summary statistics")
        
        total_events = len(self.classified_events)
        total_hours = sum(event['duration_minutes'] for event in self.classified_events) / 60.0
        
        # Topic distribution
        topic_counts = Counter(event['topic'] for event in self.classified_events)
        topic_hours = defaultdict(float)
        for event in self.classified_events:
            topic_hours[event['topic']] += event['duration_minutes'] / 60.0
        
        # Segment distribution
        segment_counts = Counter(event['segment'] for event in self.classified_events)
        segment_hours = defaultdict(float)
        for event in self.classified_events:
            segment_hours[event['segment']] += event['duration_minutes'] / 60.0
        
        # Weekly analysis
        weekly_events = defaultdict(int)
        weekly_hours = defaultdict(float)
        for event in self.classified_events:
            week = event['calendar_week']
            weekly_events[week] += 1
            weekly_hours[week] += event['duration_minutes'] / 60.0
        
        # Confidence analysis
        topic_confidences = [event['topic_confidence'] for event in self.classified_events]
        segment_confidences = [event['segment_confidence'] for event in self.classified_events]
        
        # Date range
        dates = [datetime.fromisoformat(event['start_datetime']) for event in self.classified_events]
        date_range = {
            'earliest': min(dates).date().isoformat(),
            'latest': max(dates).date().isoformat(),
            'total_weeks': len(set(event['calendar_week'] for event in self.classified_events))
        }
        
        summary = {
            'total_events': total_events,
            'total_hours': round(total_hours, 2),
            'date_range': date_range,
            
            'topic_distribution': {
                'by_count': dict(topic_counts),
                'by_hours': {k: round(v, 2) for k, v in topic_hours.items()}
            },
            
            'segment_distribution': {
                'by_count': dict(segment_counts),
                'by_hours': {k: round(v, 2) for k, v in segment_hours.items()}
            },
            
            'weekly_patterns': {
                'events_per_week': {k: v for k, v in sorted(weekly_events.items())},
                'hours_per_week': {k: round(v, 2) for k, v in sorted(weekly_hours.items())}
            },
            
            'classification_quality': {
                'avg_topic_confidence': round(np.mean(topic_confidences), 3),
                'avg_segment_confidence': round(np.mean(segment_confidences), 3),
                'topic_confidence_distribution': {
                    'high (>0.8)': sum(1 for c in topic_confidences if c > 0.8),
                    'medium (0.5-0.8)': sum(1 for c in topic_confidences if 0.5 <= c <= 0.8),
                    'low (<0.5)': sum(1 for c in topic_confidences if c < 0.5)
                }
            }
        }
        
        return summary

def main():
    """Main execution function"""
    logger.info("Starting Sub-Agent 2: Topic & Segment Classification")
    
    # Initialize analyzer
    calendar_file = "/Users/david.campos/VibeCode/AICoS-Lab/experiments/ryan_time_analysis/data/raw/calendar_full_6months/ryan_calendar_6months.jsonl"
    analyzer = CalendarAnalyzer(calendar_file)
    
    # Load and classify data
    events = analyzer.load_calendar_data()
    classified_events = analyzer.classify_all_events()
    weekly_matrix = analyzer.create_weekly_matrix()
    summary_stats = analyzer.generate_summary_statistics()
    
    # Export results
    output_base = "/Users/david.campos/VibeCode/AICoS-Lab/experiments/ryan_time_analysis/"
    
    # 1. Complete classification results
    with open(f"{output_base}topic_classification_results.json", 'w') as f:
        json.dump(classified_events, f, indent=2, default=str)
    
    # 2. Weekly topic×segment matrix for heatmap
    weekly_matrix.to_csv(f"{output_base}weekly_topic_segment_matrix.csv", index=False)
    weekly_matrix.to_json(f"{output_base}weekly_topic_segment_matrix.json", 
                         orient='records', indent=2)
    
    # 3. Summary statistics and metrics
    with open(f"{output_base}topic_segment_analysis_summary.json", 'w') as f:
        json.dump(summary_stats, f, indent=2)
    
    # 4. Create heatmap data structure
    heatmap_data = create_heatmap_data_structure(weekly_matrix)
    with open(f"{output_base}topic_segment_heatmap_data.json", 'w') as f:
        json.dump(heatmap_data, f, indent=2)
    
    # 5. Pivot table for visualization
    pivot_table = create_pivot_table(classified_events)
    pivot_table.to_csv(f"{output_base}topic_segment_pivot_table.csv")
    
    logger.info("Analysis complete! Generated files:")
    logger.info("- topic_classification_results.json (all classified events)")
    logger.info("- weekly_topic_segment_matrix.csv (week-by-week data)")
    logger.info("- topic_segment_analysis_summary.json (summary metrics)")
    logger.info("- topic_segment_heatmap_data.json (heatmap structure)")
    logger.info("- topic_segment_pivot_table.csv (pivot table)")
    
    # Display key insights
    display_key_insights(summary_stats, weekly_matrix)

def create_heatmap_data_structure(weekly_matrix: pd.DataFrame) -> dict:
    """Create structured data for heatmap visualization"""
    
    # Get all unique weeks in chronological order
    weeks = sorted(weekly_matrix['calendar_week'].unique())
    topics = sorted(weekly_matrix['topic'].unique())
    segments = sorted(weekly_matrix['segment'].unique())
    
    # Create nested structure for heatmap
    heatmap_structure = {
        'metadata': {
            'total_weeks': len(weeks),
            'total_topics': len(topics),
            'total_segments': len(segments),
            'date_range': {
                'start_week': weeks[0],
                'end_week': weeks[-1]
            }
        },
        'dimensions': {
            'weeks': weeks,
            'topics': topics,
            'segments': segments
        },
        'data': []
    }
    
    # Create data points for each combination
    for _, row in weekly_matrix.iterrows():
        data_point = {
            'week': row['calendar_week'],
            'topic': row['topic'],
            'segment': row['segment'],
            'hours': float(row['duration_hours']),
            'events': int(row['event_count']),
            'topic_confidence': float(row['topic_confidence']),
            'segment_confidence': float(row['segment_confidence'])
        }
        heatmap_structure['data'].append(data_point)
    
    return heatmap_structure

def create_pivot_table(classified_events: List[dict]) -> pd.DataFrame:
    """Create pivot table for easier analysis"""
    
    # Convert to DataFrame
    df = pd.DataFrame(classified_events)
    
    # Create pivot table: Topics (rows) x Weeks (columns) with Hours as values
    pivot = pd.pivot_table(
        df,
        values='duration_minutes',
        index='topic',
        columns='calendar_week',
        aggfunc='sum',
        fill_value=0
    )
    
    # Convert minutes to hours
    pivot = pivot / 60.0
    
    # Add total columns
    pivot['Total_Hours'] = pivot.sum(axis=1)
    
    return pivot

def display_key_insights(summary_stats: dict, weekly_matrix: pd.DataFrame):
    """Display key insights from the analysis"""
    
    print("\n" + "="*80)
    print("SUB-AGENT 2: TOPIC & SEGMENT CLASSIFICATION - KEY INSIGHTS")
    print("="*80)
    
    print(f"📊 OVERALL STATISTICS:")
    print(f"   • Total Events Classified: {summary_stats['total_events']:,}")
    print(f"   • Total Meeting Hours: {summary_stats['total_hours']:,.1f}")
    print(f"   • Date Range: {summary_stats['date_range']['earliest']} to {summary_stats['date_range']['latest']}")
    print(f"   • Weeks Covered: {summary_stats['date_range']['total_weeks']}")
    
    print(f"\n📈 TOP MEETING TOPICS (by hours):")
    topic_hours = summary_stats['topic_distribution']['by_hours']
    for i, (topic, hours) in enumerate(sorted(topic_hours.items(), key=lambda x: x[1], reverse=True)[:7]):
        print(f"   {i+1:2d}. {topic.replace('_', ' '):20} {hours:6.1f} hours ({hours/summary_stats['total_hours']*100:4.1f}%)")
    
    print(f"\n🏢 COMPANY SEGMENTS (by hours):")
    segment_hours = summary_stats['segment_distribution']['by_hours']
    for i, (segment, hours) in enumerate(sorted(segment_hours.items(), key=lambda x: x[1], reverse=True)):
        print(f"   {i+1}. {segment:15} {hours:6.1f} hours ({hours/summary_stats['total_hours']*100:4.1f}%)")
    
    print(f"\n🎯 CLASSIFICATION QUALITY:")
    quality = summary_stats['classification_quality']
    print(f"   • Average Topic Confidence: {quality['avg_topic_confidence']:.3f}")
    print(f"   • Average Segment Confidence: {quality['avg_segment_confidence']:.3f}")
    print(f"   • High Confidence Classifications: {quality['topic_confidence_distribution']['high (>0.8)']} events")
    
    print(f"\n📅 WEEKLY PATTERNS:")
    weekly_hours = list(summary_stats['weekly_patterns']['hours_per_week'].values())
    if weekly_hours:
        print(f"   • Average Hours per Week: {np.mean(weekly_hours):5.1f}")
        print(f"   • Peak Week Hours: {max(weekly_hours):5.1f}")
        print(f"   • Lowest Week Hours: {min(weekly_hours):5.1f}")
    
    # Top topic-segment combinations
    print(f"\n🎯 TOP TOPIC×SEGMENT COMBINATIONS:")
    combo_hours = weekly_matrix.groupby(['topic', 'segment'])['duration_hours'].sum().sort_values(ascending=False)
    for i, ((topic, segment), hours) in enumerate(combo_hours.head(8).items()):
        print(f"   {i+1:2d}. {topic.replace('_', ' ')[:15]:15} × {segment:10} {hours:6.1f} hours")
    
    print("\n" + "="*80)
    print("✅ DELIVERABLE: Heatmap data ready for 'topic engagement week by week by segment'")
    print("   Files generated: topic_segment_heatmap_data.json, weekly_topic_segment_matrix.csv")
    print("="*80)

if __name__ == "__main__":
    main()