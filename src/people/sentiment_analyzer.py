"""
Sentiment Analyzer - Enhanced sentiment analysis for relationship health tracking

References:
- src/people/interaction_manager.py - Interaction processing patterns
- src/people/models.py - Interaction and relationship models
- src/core/config.py - Configuration management

Core Philosophy: Use both rule-based and AI-assisted sentiment analysis to track 
relationship health over time, identifying patterns that indicate strengthening 
or deteriorating professional relationships.
"""

import re
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class SentimentScore(Enum):
    """Sentiment scoring scale"""
    VERY_NEGATIVE = -2
    NEGATIVE = -1
    NEUTRAL = 0
    POSITIVE = 1
    VERY_POSITIVE = 2


@dataclass
class SentimentAnalysis:
    """Result of sentiment analysis"""
    score: float  # -1.0 to 1.0
    confidence: float  # 0.0 to 1.0
    category: SentimentScore
    indicators: List[str]  # What triggered this sentiment
    relationship_signals: Dict[str, Any]  # Professional relationship indicators
    metadata: Dict[str, Any]


class SentimentAnalyzer:
    """
    Enhanced sentiment analyzer for professional relationship health tracking
    
    Features:
    - Rule-based sentiment analysis optimized for business communication
    - Relationship health indicators (engagement, collaboration, conflict)
    - Trend analysis over time for relationship deterioration/improvement
    - Context-aware analysis (meetings vs casual chat vs formal emails)
    """
    
    def __init__(self):
        """Initialize sentiment analyzer with business-focused patterns"""
        
        # Positive sentiment patterns
        self.positive_patterns = {
            'appreciation': [
                r'thank you', r'thanks', r'appreciate', r'grateful', r'great job',
                r'well done', r'excellent', r'fantastic', r'amazing', r'brilliant'
            ],
            'agreement': [
                r'exactly', r'agreed', r'absolutely', r'perfect', r'sounds good',
                r'makes sense', r'good point', r'i agree', r"that's right"
            ],
            'enthusiasm': [
                r'excited', r'looking forward', r'can\'t wait', r'awesome',
                r'love this', r'this is great', r'fantastic idea'
            ],
            'collaboration': [
                r'let\'s work together', r'team effort', r'collaborate', r'partnership',
                r'work with you', r'join forces', r'coordinate'
            ]
        }
        
        # Negative sentiment patterns
        self.negative_patterns = {
            'frustration': [
                r'frustrated', r'annoyed', r'irritated', r'this is ridiculous',
                r'waste of time', r'pointless', r'unnecessary'
            ],
            'disagreement': [
                r'disagree', r'wrong', r'incorrect', r'not right', r'i don\'t think',
                r'that doesn\'t work', r'problematic', r'issues with'
            ],
            'urgency_stress': [
                r'urgent', r'asap', r'immediately', r'overdue', r'behind schedule',
                r'late', r'deadline missed', r'critical issue'
            ],
            'conflict': [
                r'unacceptable', r'disappointed', r'concerns about', r'not satisfied',
                r'this won\'t work', r'serious problem', r'major issue'
            ]
        }
        
        # Neutral/professional patterns
        self.neutral_patterns = [
            r'noted', r'understood', r'received', r'will review', r'will check',
            r'let me know', r'please advise', r'for your reference'
        ]
        
        # Relationship health indicators
        self.engagement_indicators = {
            'high': [
                r'what do you think', r'your thoughts', r'your opinion',
                r'let\'s discuss', r'can we talk', r'input needed'
            ],
            'low': [
                r'fyi', r'for your information', r'just letting you know',
                r'no response needed', r'no action required'
            ]
        }
        
        # Professional formality indicators
        self.formality_patterns = {
            'formal': [
                r'dear', r'regards', r'sincerely', r'please find attached',
                r'i would like to', r'i am writing to'
            ],
            'casual': [
                r'hey', r'hi there', r'thanks!', r'sounds good!', r'cool',
                r'awesome', r'lol', r'btw'
            ]
        }
        
        logger.info("SentimentAnalyzer initialized with business communication patterns")
    
    def analyze_text(self, text: str, context: Optional[Dict] = None) -> SentimentAnalysis:
        """
        Analyze sentiment of text content
        
        Args:
            text: Text content to analyze
            context: Optional context (interaction type, source, etc.)
            
        Returns:
            SentimentAnalysis result
        """
        if not text or not text.strip():
            return SentimentAnalysis(
                score=0.0,
                confidence=0.0,
                category=SentimentScore.NEUTRAL,
                indicators=[],
                relationship_signals={},
                metadata={}
            )
        
        text_lower = text.lower()
        indicators = []
        positive_score = 0.0
        negative_score = 0.0
        total_matches = 0
        
        # Analyze positive patterns
        for category, patterns in self.positive_patterns.items():
            matches = sum(1 for pattern in patterns if re.search(pattern, text_lower))
            if matches > 0:
                positive_score += matches * self._get_category_weight(category, 'positive')
                total_matches += matches
                indicators.append(f"positive_{category}")
        
        # Analyze negative patterns
        for category, patterns in self.negative_patterns.items():
            matches = sum(1 for pattern in patterns if re.search(pattern, text_lower))
            if matches > 0:
                negative_score += matches * self._get_category_weight(category, 'negative')
                total_matches += matches
                indicators.append(f"negative_{category}")
        
        # Calculate base sentiment score
        if total_matches == 0:
            score = 0.0
            confidence = 0.1
        else:
            score = (positive_score - negative_score) / total_matches
            score = max(-1.0, min(1.0, score))  # Clamp to [-1, 1]
            confidence = min(1.0, total_matches / 10.0)  # Higher confidence with more matches
        
        # Determine category
        category = self._score_to_category(score)
        
        # Analyze relationship signals
        relationship_signals = self._analyze_relationship_signals(text_lower, context)
        
        # Context-based adjustments
        if context:
            score, confidence = self._adjust_for_context(score, confidence, context)
        
        return SentimentAnalysis(
            score=score,
            confidence=confidence,
            category=category,
            indicators=indicators,
            relationship_signals=relationship_signals,
            metadata={
                'text_length': len(text),
                'total_matches': total_matches,
                'positive_score': positive_score,
                'negative_score': negative_score,
                'analysis_timestamp': datetime.now().isoformat()
            }
        )
    
    def _get_category_weight(self, category: str, sentiment_type: str) -> float:
        """Get weight for different sentiment categories"""
        weights = {
            'positive': {
                'appreciation': 0.8,
                'agreement': 0.6,
                'enthusiasm': 1.0,
                'collaboration': 0.9
            },
            'negative': {
                'frustration': 0.9,
                'disagreement': 0.7,
                'urgency_stress': 0.6,
                'conflict': 1.0
            }
        }
        return weights.get(sentiment_type, {}).get(category, 0.5)
    
    def _score_to_category(self, score: float) -> SentimentScore:
        """Convert numeric score to sentiment category"""
        if score <= -0.6:
            return SentimentScore.VERY_NEGATIVE
        elif score <= -0.2:
            return SentimentScore.NEGATIVE
        elif score >= 0.6:
            return SentimentScore.VERY_POSITIVE
        elif score >= 0.2:
            return SentimentScore.POSITIVE
        else:
            return SentimentScore.NEUTRAL
    
    def _analyze_relationship_signals(self, text_lower: str, context: Optional[Dict]) -> Dict[str, Any]:
        """Analyze professional relationship health indicators"""
        signals = {
            'engagement_level': 'medium',
            'formality_level': 'professional',
            'collaboration_indicators': [],
            'response_expectation': 'normal',
            'relationship_direction': 'stable'
        }
        
        # Analyze engagement level
        high_engagement_matches = sum(1 for pattern in self.engagement_indicators['high'] 
                                    if re.search(pattern, text_lower))
        low_engagement_matches = sum(1 for pattern in self.engagement_indicators['low'] 
                                   if re.search(pattern, text_lower))
        
        if high_engagement_matches > low_engagement_matches:
            signals['engagement_level'] = 'high'
        elif low_engagement_matches > high_engagement_matches:
            signals['engagement_level'] = 'low'
        
        # Analyze formality level
        formal_matches = sum(1 for pattern in self.formality_patterns['formal'] 
                           if re.search(pattern, text_lower))
        casual_matches = sum(1 for pattern in self.formality_patterns['casual'] 
                           if re.search(pattern, text_lower))
        
        if formal_matches > casual_matches:
            signals['formality_level'] = 'formal'
        elif casual_matches > formal_matches:
            signals['formality_level'] = 'casual'
        
        # Look for collaboration indicators
        collaboration_words = ['collaborate', 'team', 'together', 'partnership', 'joint']
        for word in collaboration_words:
            if word in text_lower:
                signals['collaboration_indicators'].append(word)
        
        # Determine response expectation
        if any(pattern in text_lower for pattern in ['asap', 'urgent', 'immediately']):
            signals['response_expectation'] = 'urgent'
        elif any(pattern in text_lower for pattern in ['when you can', 'no rush', 'fyi']):
            signals['response_expectation'] = 'low'
        
        return signals
    
    def _adjust_for_context(self, score: float, confidence: float, context: Dict) -> Tuple[float, float]:
        """Adjust sentiment based on context (interaction type, source, etc.)"""
        interaction_type = context.get('interaction_type', '')
        source = context.get('source', '')
        
        # Email tends to be more formal/neutral
        if source == 'email':
            score *= 0.8  # Slightly dampen sentiment
            confidence *= 0.9
        
        # Slack messages can be more expressive
        elif source == 'slack':
            score *= 1.1  # Amplify sentiment slightly
            confidence *= 1.1
        
        # Meeting notes are usually neutral/informational
        elif interaction_type == 'meeting':
            if abs(score) < 0.3:  # If already neutral, make it more neutral
                score *= 0.5
            confidence *= 0.8
        
        # Clamp values
        score = max(-1.0, min(1.0, score))
        confidence = max(0.0, min(1.0, confidence))
        
        return score, confidence
    
    def analyze_relationship_trend(self, sentiment_history: List[SentimentAnalysis], 
                                 time_window_days: int = 30) -> Dict[str, Any]:
        """
        Analyze relationship trend over time
        
        Args:
            sentiment_history: List of sentiment analyses over time
            time_window_days: Time window for trend analysis
            
        Returns:
            Dict with trend analysis results
        """
        if len(sentiment_history) < 2:
            return {
                'trend': 'insufficient_data',
                'direction': 'unknown',
                'confidence': 0.0,
                'recent_average': 0.0,
                'change_rate': 0.0,
                'relationship_health': 'unknown'
            }
        
        # Filter to time window
        cutoff_time = datetime.now() - timedelta(days=time_window_days)
        recent_analyses = [
            analysis for analysis in sentiment_history 
            if datetime.fromisoformat(analysis.metadata['analysis_timestamp']) > cutoff_time
        ]
        
        if len(recent_analyses) < 2:
            recent_analyses = sentiment_history[-10:]  # Use last 10 if insufficient recent data
        
        # Calculate metrics
        scores = [analysis.score for analysis in recent_analyses]
        recent_average = sum(scores) / len(scores)
        
        # Calculate trend using linear regression (simple)
        n = len(scores)
        x_values = list(range(n))
        x_mean = sum(x_values) / n
        y_mean = recent_average
        
        numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, scores))
        denominator = sum((x - x_mean) ** 2 for x in x_values)
        
        change_rate = numerator / denominator if denominator != 0 else 0
        
        # Determine trend direction
        if change_rate > 0.05:
            trend = 'improving'
            direction = 'positive'
        elif change_rate < -0.05:
            trend = 'declining' 
            direction = 'negative'
        else:
            trend = 'stable'
            direction = 'neutral'
        
        # Calculate trend confidence
        trend_confidence = min(1.0, len(recent_analyses) / 10.0)
        
        # Determine relationship health
        if recent_average > 0.4:
            health = 'excellent'
        elif recent_average > 0.1:
            health = 'good'
        elif recent_average > -0.1:
            health = 'neutral'
        elif recent_average > -0.4:
            health = 'concerning'
        else:
            health = 'poor'
        
        return {
            'trend': trend,
            'direction': direction,
            'confidence': trend_confidence,
            'recent_average': recent_average,
            'change_rate': change_rate,
            'relationship_health': health,
            'data_points': len(recent_analyses),
            'time_window_days': time_window_days,
            'analysis_timestamp': datetime.now().isoformat()
        }
    
    def get_relationship_insights(self, sentiment_history: List[SentimentAnalysis]) -> List[str]:
        """Generate actionable insights about relationship health"""
        if not sentiment_history:
            return ["Insufficient interaction data for relationship insights"]
        
        insights = []
        
        # Recent sentiment patterns
        recent_scores = [a.score for a in sentiment_history[-5:]]
        recent_avg = sum(recent_scores) / len(recent_scores)
        
        if recent_avg > 0.3:
            insights.append("✅ Recent interactions show positive sentiment - relationship appears healthy")
        elif recent_avg < -0.3:
            insights.append("⚠️ Recent interactions show negative sentiment - may need attention")
        
        # Engagement patterns
        recent_engagement = [
            a.relationship_signals.get('engagement_level', 'medium') 
            for a in sentiment_history[-5:]
        ]
        
        low_engagement_count = recent_engagement.count('low')
        if low_engagement_count >= 3:
            insights.append("📉 Low engagement detected - consider more interactive communication")
        
        high_engagement_count = recent_engagement.count('high')
        if high_engagement_count >= 3:
            insights.append("📈 High engagement detected - active collaboration opportunity")
        
        # Formality trends
        recent_formality = [
            a.relationship_signals.get('formality_level', 'professional') 
            for a in sentiment_history[-5:]
        ]
        
        if recent_formality.count('formal') >= 4:
            insights.append("🎯 Communication has become more formal - relationship may be distancing")
        elif recent_formality.count('casual') >= 4:
            insights.append("🤝 Communication has become more casual - relationship appears comfortable")
        
        # Collaboration indicators
        collaboration_mentions = sum(
            len(a.relationship_signals.get('collaboration_indicators', [])) 
            for a in sentiment_history[-10:]
        )
        
        if collaboration_mentions >= 3:
            insights.append("🤝 Strong collaboration signals - good partnership potential")
        elif collaboration_mentions == 0:
            insights.append("💡 Limited collaboration signals - consider joint projects or initiatives")
        
        return insights