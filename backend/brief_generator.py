"""
Brief Generation System for Agent H Frontend Integration

References:
- Task specification: /Users/david.campos/VibeCode/AICoS-Lab/tasks/frontend_agent_h_integration.md
- SearchDatabase: src/search/database.py
- State management patterns: backend/state_manager.py

Features:
- Generate formatted briefs for meetings with related content search
- Create daily intelligence briefs with executive summaries
- Multiple output formats (HTML, text, JSON)
- Performance optimized for real-time use (<500ms for brief generation)
- Integration with existing SearchDatabase for content correlation
"""

import logging
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

# Add project root for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

logger = logging.getLogger(__name__)

class BriefGenerator:
    """
    Generate formatted briefs for meetings and daily intelligence
    
    Responsibilities:
    - Generate meeting briefs with related content from SearchDatabase
    - Create daily intelligence briefs with actionable insights
    - Support multiple output formats for different interfaces
    - Maintain performance suitable for real-time dashboard use
    - Integrate with existing search infrastructure without modification
    """
    
    def __init__(self, search_db=None):
        """
        Initialize brief generator
        
        Args:
            search_db: Optional SearchDatabase instance for content search
        """
        self.search_db = search_db
        
        # Try to initialize SearchDatabase if not provided
        if not self.search_db:
            try:
                from src.search.database import SearchDatabase
                self.search_db = SearchDatabase('data/search.db')
                logger.info("Initialized SearchDatabase for brief content search")
            except Exception as e:
                logger.warning(f"SearchDatabase not available: {e}")
                self.search_db = None
        
        # Performance tracking
        self._briefs_generated = 0
        self._total_generation_time = 0
        
        logger.info("BriefGenerator initialized")
    
    async def generate_meeting_brief(self, meeting_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate comprehensive brief for a specific meeting
        
        Args:
            meeting_data: Calendar item with meeting details
            
        Returns:
            Dict with brief content in multiple formats
        """
        start_time = datetime.now()
        self._briefs_generated += 1
        
        try:
            meeting_title = meeting_data.get('title', 'Meeting')
            meeting_code = meeting_data.get('code', 'Unknown')
            meeting_time = meeting_data.get('time', '')
            attendees = meeting_data.get('attendees', [])
            
            logger.info(f"Generating brief for meeting {meeting_code}: {meeting_title}")
            
            # Search for related content using SearchDatabase
            related_content = await self.search_related_content(meeting_title, attendees)
            
            # Generate meeting summary
            summary = self.generate_meeting_summary(meeting_title, related_content, attendees)
            
            # Build comprehensive brief
            brief = {
                'meeting_code': meeting_code,
                'meeting_title': meeting_title,
                'meeting_time': meeting_time,
                'meeting_date': meeting_data.get('date', ''),
                'attendees': attendees,
                'attendee_count': len(attendees),
                'related_content': related_content,
                'related_content_count': len(related_content),
                'summary': summary,
                'generated_at': datetime.now().isoformat(),
                'keywords': self.extract_meeting_keywords(meeting_title)
            }
            
            # Add formatted versions for different interfaces
            brief['formatted_html'] = self.format_meeting_brief_html(brief)
            brief['formatted_text'] = self.format_meeting_brief_text(brief)
            brief['formatted_slack'] = self.format_meeting_brief_slack(brief)
            
            # Track performance
            generation_time = (datetime.now() - start_time).total_seconds() * 1000
            self._total_generation_time += generation_time
            brief['generation_time_ms'] = round(generation_time, 2)
            
            logger.info(f"Generated brief for {meeting_code} in {generation_time:.1f}ms with {len(related_content)} related items")
            return brief
            
        except Exception as e:
            logger.error(f"Failed to generate meeting brief: {e}")
            return {
                'meeting_code': meeting_data.get('code', 'Unknown'),
                'meeting_title': meeting_data.get('title', 'Meeting'),
                'error': str(e),
                'generated_at': datetime.now().isoformat(),
                'formatted_text': f"Brief generation failed: {str(e)}"
            }
    
    async def generate_daily_brief(self, state_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate daily intelligence brief with executive summary
        
        Args:
            state_data: Current system state with calendar, priorities, commitments
            
        Returns:
            Dict with daily brief content and insights
        """
        start_time = datetime.now()
        
        try:
            calendar = state_data.get('calendar', [])
            priorities = state_data.get('priorities', [])
            commitments = state_data.get('commitments', {'owe': [], 'owed': []})
            
            logger.info("Generating daily intelligence brief")
            
            # Calculate key metrics
            metrics = self.calculate_daily_metrics(calendar, priorities, commitments)
            
            # Generate executive summary
            executive_summary = self.generate_executive_summary(state_data, metrics)
            
            # Identify critical and time-sensitive items
            critical_items = self.identify_critical_items(state_data)
            time_sensitive_items = self.identify_time_sensitive_items(state_data)
            
            # Build comprehensive daily brief
            brief = {
                'date': datetime.now().strftime('%A, %B %d, %Y'),
                'generated_at': datetime.now().isoformat(),
                'metrics': metrics,
                'executive_summary': executive_summary,
                'critical_items': critical_items,
                'time_sensitive': time_sensitive_items,
                'recommendations': self.generate_daily_recommendations(state_data, critical_items),
                'upcoming_meetings': [m for m in calendar if not m.get('past', False)][:5]
            }
            
            # Add formatted versions
            brief['formatted_html'] = self.format_daily_brief_html(brief)
            brief['formatted_text'] = self.format_daily_brief_text(brief)
            
            # Track performance
            generation_time = (datetime.now() - start_time).total_seconds() * 1000
            brief['generation_time_ms'] = round(generation_time, 2)
            
            logger.info(f"Generated daily brief in {generation_time:.1f}ms")
            return brief
            
        except Exception as e:
            logger.error(f"Failed to generate daily brief: {e}")
            return {
                'date': datetime.now().strftime('%A, %B %d, %Y'),
                'error': str(e),
                'generated_at': datetime.now().isoformat(),
                'formatted_text': f"Daily brief generation failed: {str(e)}"
            }
    
    async def search_related_content(self, title: str, attendees: List[str]) -> List[Dict[str, Any]]:
        """
        Search for content related to meeting using SearchDatabase
        
        Args:
            title: Meeting title for keyword search
            attendees: List of attendee emails for people-based search
            
        Returns:
            List of related content items with relevance scoring
        """
        if not self.search_db:
            # Return mock data for testing when SearchDatabase not available
            return [
                {'source': 'slack', 'text': f'Recent discussion about {title}', 'relevance': 0.8},
                {'source': 'drive', 'title': f'{title} - Meeting Notes.doc', 'relevance': 0.9}
            ]
        
        related = []
        
        try:
            # Search by meeting title keywords
            title_keywords = self.extract_meeting_keywords(title)
            for keyword in title_keywords[:3]:  # Limit to avoid too many queries
                if len(keyword) > 3:  # Skip very short keywords
                    results = self.search_db.search(keyword, limit=2)
                    for result in results:
                        result['relevance'] = 0.8  # Title keyword match
                        result['match_reason'] = f'title keyword: {keyword}'
                    related.extend(results)
            
            # Search by attendee activity
            for attendee in attendees[:3]:  # Limit to avoid too many queries
                if '@' in attendee:  # Valid email format
                    attendee_results = self.search_db.search(f'from:{attendee}', limit=2)
                    for result in attendee_results:
                        result['relevance'] = 0.6  # Attendee match
                        result['match_reason'] = f'attendee: {attendee}'
                    related.extend(attendee_results)
            
            # Search for recent mentions of meeting topic
            recent_results = self.search_db.search(f'meeting {title}', limit=2)
            for result in recent_results:
                result['relevance'] = 0.7  # Recent mention
                result['match_reason'] = 'recent meeting mention'
            related.extend(recent_results)
            
        except Exception as e:
            logger.warning(f"Error searching related content: {e}")
            # Return empty list on search error
            related = []
        
        # Remove duplicates and sort by relevance
        unique_related = self.deduplicate_search_results(related)
        unique_related.sort(key=lambda x: x.get('relevance', 0), reverse=True)
        
        return unique_related[:8]  # Limit to top 8 most relevant items
    
    def calculate_daily_metrics(self, calendar: List[Dict], priorities: List[Dict], 
                               commitments: Dict[str, List[Dict]]) -> Dict[str, Any]:
        """Calculate key metrics for daily brief"""
        return {
            'total_meetings': len(calendar),
            'important_meetings': len([m for m in calendar if m.get('alert', False)]),
            'total_priorities': len(priorities),
            'pending_priorities': len([p for p in priorities if p.get('status') != 'done']),
            'completed_priorities': len([p for p in priorities if p.get('status') == 'done']),
            'commitments_owed': len(commitments.get('owe', [])),
            'commitments_owed_to_me': len(commitments.get('owed', [])),
            'due_today': len([c for c in commitments.get('owe', []) 
                            if self.is_due_today(c.get('due_date'))]),
        }
    
    def generate_executive_summary(self, state_data: Dict[str, Any], metrics: Dict[str, Any]) -> str:
        """Generate executive summary for daily brief"""
        priorities = state_data.get('priorities', [])
        commitments = state_data.get('commitments', {'owe': [], 'owed': []})
        
        total_priorities = metrics['total_priorities']
        pending_priorities = metrics['pending_priorities']
        total_meetings = metrics['total_meetings']
        important_meetings = metrics['important_meetings']
        due_today = metrics['due_today']
        
        summary_parts = []
        
        # Priorities summary
        if total_priorities > 0:
            completion_rate = ((total_priorities - pending_priorities) / total_priorities) * 100
            summary_parts.append(f"You have {pending_priorities} of {total_priorities} priorities pending ({completion_rate:.0f}% complete)")
        else:
            summary_parts.append("No priorities currently tracked")
        
        # Meetings summary
        if total_meetings > 0:
            if important_meetings > 0:
                summary_parts.append(f"{total_meetings} meetings scheduled with {important_meetings} flagged as important")
            else:
                summary_parts.append(f"{total_meetings} meetings scheduled")
        else:
            summary_parts.append("No meetings scheduled")
        
        # Urgent items summary
        if due_today > 0:
            summary_parts.append(f"⚠️ {due_today} commitments due today requiring immediate attention")
        
        return ". ".join(summary_parts) + "."
    
    def identify_critical_items(self, state_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify critical items requiring immediate attention"""
        critical = []
        
        # High priority items or items with alerts
        priorities = state_data.get('priorities', [])
        for priority in priorities:
            if (priority.get('alert') or 
                priority.get('status') == 'partial' or
                priority.get('urgency') == 'high'):
                critical.append({
                    'type': 'priority',
                    'code': priority.get('code'),
                    'text': priority.get('text', priority.get('title', 'Unknown')),
                    'reason': 'High priority or requires completion',
                    'urgency': priority.get('urgency', 'medium')
                })
        
        # Urgent commitments due today
        commitments = state_data.get('commitments', {'owe': [], 'owed': []})
        for commitment in commitments.get('owe', []):
            if self.is_due_today(commitment.get('due_date')):
                critical.append({
                    'type': 'commitment',
                    'code': commitment.get('code'),
                    'text': commitment.get('text', commitment.get('description', 'Unknown')),
                    'reason': 'Due today',
                    'due_date': commitment.get('due_date')
                })
        
        # Important meetings today
        calendar = state_data.get('calendar', [])
        for meeting in calendar:
            if meeting.get('alert') and not meeting.get('past', False):
                critical.append({
                    'type': 'meeting',
                    'code': meeting.get('code'),
                    'title': meeting.get('title'),
                    'time': meeting.get('time'),
                    'reason': 'Important meeting requiring preparation'
                })
        
        return critical[:10]  # Limit to top 10 critical items
    
    def identify_time_sensitive_items(self, state_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify time-sensitive items for today"""
        time_sensitive = []
        
        # Today's meetings (especially upcoming ones)
        calendar = state_data.get('calendar', [])
        for meeting in calendar:
            if not meeting.get('past', False):  # Upcoming meetings
                time_sensitive.append({
                    'type': 'meeting',
                    'code': meeting.get('code'),
                    'time': meeting.get('time'),
                    'title': meeting.get('title'),
                    'urgency': 'high' if meeting.get('alert') else 'medium'
                })
        
        # Commitments due soon
        commitments = state_data.get('commitments', {'owe': [], 'owed': []})
        for commitment in commitments.get('owe', []):
            if self.is_due_soon(commitment.get('due_date')):
                time_sensitive.append({
                    'type': 'commitment',
                    'code': commitment.get('code'),
                    'text': commitment.get('text', 'Unknown'),
                    'due_date': commitment.get('due_date'),
                    'urgency': 'high' if self.is_due_today(commitment.get('due_date')) else 'medium'
                })
        
        return time_sensitive[:8]  # Limit results
    
    def generate_daily_recommendations(self, state_data: Dict[str, Any], critical_items: List[Dict]) -> List[str]:
        """Generate actionable recommendations for the day"""
        recommendations = []
        
        if critical_items:
            recommendations.append(f"Focus on {len(critical_items)} critical items requiring immediate attention")
        
        priorities = state_data.get('priorities', [])
        pending_priorities = [p for p in priorities if p.get('status') != 'done']
        if len(pending_priorities) > 5:
            recommendations.append("Consider breaking down large priorities into smaller, actionable tasks")
        
        meetings = state_data.get('calendar', [])
        if len(meetings) > 4:
            recommendations.append("Heavy meeting day - block time for follow-up actions and documentation")
        
        important_meetings = [m for m in meetings if m.get('alert')]
        if important_meetings:
            recommendations.append("Prepare for important meetings - review related content and set clear objectives")
        
        return recommendations[:5]  # Limit to top 5 recommendations
    
    def extract_meeting_keywords(self, title: str) -> List[str]:
        """Extract meaningful keywords from meeting title"""
        # Simple keyword extraction - could be enhanced with NLP
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'meeting', 'call', 'sync'}
        words = title.lower().split()
        keywords = [word.strip('()[]{}.,!?;:') for word in words if len(word) > 2 and word not in stop_words]
        return keywords[:5]  # Return top 5 keywords
    
    def deduplicate_search_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate search results based on text content"""
        seen_texts = set()
        unique_results = []
        
        for result in results:
            text_key = result.get('text', result.get('title', ''))[:100]  # First 100 chars as key
            if text_key not in seen_texts:
                seen_texts.add(text_key)
                unique_results.append(result)
        
        return unique_results
    
    def is_due_today(self, due_date_str: Optional[str]) -> bool:
        """Check if a due date is today"""
        if not due_date_str:
            return False
        
        try:
            due_date = datetime.fromisoformat(due_date_str.replace('Z', '+00:00')).date()
            return due_date == datetime.now().date()
        except:
            return False
    
    def is_due_soon(self, due_date_str: Optional[str], days_ahead: int = 2) -> bool:
        """Check if a due date is within the next few days"""
        if not due_date_str:
            return False
        
        try:
            due_date = datetime.fromisoformat(due_date_str.replace('Z', '+00:00')).date()
            today = datetime.now().date()
            return today <= due_date <= today + timedelta(days=days_ahead)
        except:
            return False
    
    def format_meeting_brief_html(self, brief: Dict[str, Any]) -> str:
        """Format meeting brief as HTML for dashboard display"""
        html = f"""
        <div class="brief-section">
            <div class="brief-header">
                <h3>Meeting Brief: {brief['meeting_title']}</h3>
                <div class="brief-meta">
                    <span class="brief-code">{brief['meeting_code']}</span>
                    <span class="brief-time">{brief['meeting_time']}</span>
                    <span class="brief-attendees">{brief['attendee_count']} attendees</span>
                </div>
            </div>
            
            <div class="brief-summary">
                <h4>Summary</h4>
                <p>{brief['summary']}</p>
            </div>
        """
        
        if brief['related_content']:
            html += """
            <div class="brief-related">
                <h4>Related Content</h4>
                <ul>
            """
            for item in brief['related_content'][:5]:  # Limit to 5 items
                text = item.get('text', item.get('title', 'Unknown'))[:100] + ('...' if len(str(text)) > 100 else '')
                relevance = item.get('relevance', 0)
                html += f'<li><span class="relevance">{relevance:.1f}</span> {text}</li>'
            
            html += "</ul></div>"
        
        html += f"""
            <div class="brief-footer">
                <small>Generated at {brief['generated_at'][:16]} in {brief.get('generation_time_ms', 0):.1f}ms</small>
            </div>
        </div>
        """
        
        return html
    
    def format_meeting_brief_text(self, brief: Dict[str, Any]) -> str:
        """Format meeting brief as plain text for Slack/CLI"""
        text = f"📋 Meeting Brief: {brief['meeting_title']} ({brief['meeting_code']})\n"
        text += f"⏰ Time: {brief['meeting_time']}\n"
        text += f"👥 Attendees: {brief['attendee_count']}\n\n"
        
        text += f"Summary: {brief['summary']}\n\n"
        
        if brief['related_content']:
            text += "Related Content:\n"
            for item in brief['related_content'][:5]:
                item_text = item.get('text', item.get('title', 'Unknown'))[:80]
                relevance = item.get('relevance', 0)
                text += f"• [{relevance:.1f}] {item_text}\n"
        
        return text
    
    def format_meeting_brief_slack(self, brief: Dict[str, Any]) -> List[Dict]:
        """Format meeting brief as Slack blocks"""
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*📋 {brief['meeting_title']}* ({brief['meeting_code']})"
                }
            },
            {
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": f"⏰ {brief['meeting_time']}"},
                    {"type": "mrkdwn", "text": f"👥 {brief['attendee_count']} attendees"}
                ]
            }
        ]
        
        if brief['summary']:
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": brief['summary']}
            })
        
        if brief['related_content']:
            content_text = "\n".join([
                f"• {item.get('text', item.get('title', 'Unknown'))[:60]}"
                for item in brief['related_content'][:3]
            ])
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Related Content:*\n{content_text}"}
            })
        
        return blocks
    
    def format_daily_brief_html(self, brief: Dict[str, Any]) -> str:
        """Format daily brief as HTML"""
        metrics = brief['metrics']
        
        html = f"""
        <div class="daily-brief">
            <div class="brief-title">Daily Intelligence Brief</div>
            <div class="brief-date">{brief['date']}</div>
            
            <div class="brief-metrics">
                <div class="metric">
                    <span class="metric-value">{metrics['total_meetings']}</span>
                    <span class="metric-label">Meetings</span>
                </div>
                <div class="metric">
                    <span class="metric-value">{metrics['pending_priorities']}</span>
                    <span class="metric-label">Priorities</span>
                </div>
                <div class="metric">
                    <span class="metric-value">{metrics['due_today']}</span>
                    <span class="metric-label">Due Today</span>
                </div>
            </div>
            
            <div class="brief-section">
                <h3>Executive Summary</h3>
                <p>{brief['executive_summary']}</p>
            </div>
        """
        
        if brief['critical_items']:
            html += """
            <div class="brief-section">
                <h3>Critical Items</h3>
                <ul class="critical-list">
            """
            for item in brief['critical_items'][:5]:
                html += f"""
                <li class="critical-item {item['type']}">
                    <strong>{item.get('code', 'Unknown')}:</strong> 
                    {item.get('text', item.get('title', 'Unknown'))} 
                    <em>({item['reason']})</em>
                </li>
                """
            html += "</ul></div>"
        
        if brief['recommendations']:
            html += """
            <div class="brief-section">
                <h3>Recommendations</h3>
                <ul class="recommendations">
            """
            for rec in brief['recommendations']:
                html += f"<li>{rec}</li>"
            html += "</ul></div>"
        
        html += f"""
            <div class="brief-footer">
                <small>Generated in {brief.get('generation_time_ms', 0):.1f}ms</small>
            </div>
        </div>
        """
        
        return html
    
    def format_daily_brief_text(self, brief: Dict[str, Any]) -> str:
        """Format daily brief as plain text"""
        text = f"📊 Daily Intelligence Brief - {brief['date']}\n"
        text += "=" * 50 + "\n\n"
        
        text += f"Executive Summary:\n{brief['executive_summary']}\n\n"
        
        metrics = brief['metrics']
        text += f"Key Metrics:\n"
        text += f"• {metrics['total_meetings']} meetings scheduled\n"
        text += f"• {metrics['pending_priorities']} priorities pending\n"
        text += f"• {metrics['due_today']} items due today\n\n"
        
        if brief['critical_items']:
            text += "Critical Items:\n"
            for item in brief['critical_items'][:5]:
                text += f"• {item.get('code', '??')}: {item.get('text', item.get('title', 'Unknown'))} ({item['reason']})\n"
            text += "\n"
        
        if brief['recommendations']:
            text += "Recommendations:\n"
            for i, rec in enumerate(brief['recommendations'], 1):
                text += f"{i}. {rec}\n"
        
        return text
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get brief generator performance statistics"""
        return {
            'briefs_generated': self._briefs_generated,
            'total_generation_time_ms': self._total_generation_time,
            'average_generation_time_ms': self._total_generation_time / max(self._briefs_generated, 1),
            'search_db_available': self.search_db is not None
        }