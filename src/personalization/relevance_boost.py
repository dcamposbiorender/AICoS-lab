#!/usr/bin/env python3
"""
Relevance Booster - Search Result Personalization for AI Chief of Staff

Boosts search results relevant to PRIMARY_USER to improve search experience.
Prioritizes user-related content while maintaining backwards compatibility.

References:
- src/personalization/simple_filter.py - Core filtering patterns
- src/search/database.py - Search result structure
- tasks/phase6_agent_l_personalization.md - Complete specification
"""

import logging
from typing import Any, Dict, List, Optional
from .simple_filter import SimpleFilter

logger = logging.getLogger(__name__)

class RelevanceBooster:
    """
    Boost search results relevant to PRIMARY_USER
    
    Features:
    - Identifies user-relevant search results across different sources
    - Applies configurable boost factor to user-related content
    - Maintains result ranking and metadata
    - Backwards compatible without PRIMARY_USER configuration
    
    Usage:
        booster = RelevanceBooster()
        boosted_results = booster.boost_search_results(results, boost_factor=1.5)
        
    Integration with Search:
        def search_with_personalization(query, limit=20):
            results = normal_search(query, limit * 2)
            booster = RelevanceBooster()
            return booster.boost_search_results(results)[:limit]
    """
    
    def __init__(self, simple_filter: Optional[SimpleFilter] = None):
        """
        Initialize RelevanceBooster
        
        Args:
            simple_filter: Optional SimpleFilter instance for user detection
        """
        self.filter = simple_filter or SimpleFilter()
        
        if self.filter.primary_user:
            logger.info(f"✅ RelevanceBooster initialized with PRIMARY_USER: {self.filter.primary_user['email']}")
        else:
            logger.info("ℹ️ RelevanceBooster initialized without PRIMARY_USER (no boosting)")
    
    def boost_search_results(self, results: List[Any], boost_factor: float = 1.5) -> List[Any]:
        """
        Apply relevance boosting to search results
        
        Args:
            results: List of search result objects
            boost_factor: Multiplication factor for boosting (default 1.5)
            
        Returns:
            List of search results with boosted scores, sorted by relevance
        """
        if not results:
            return []
            
        if not self.filter.primary_user:
            return results  # No boosting without PRIMARY_USER
            
        logger.debug(f"🔄 Applying relevance boosting (factor: {boost_factor}) to {len(results)} results")
        
        boosted_count = 0
        
        for result in results:
            if self.is_user_relevant_result(result):
                # Apply boost factor to score
                original_score = getattr(result, 'score', 0)
                if hasattr(result, 'score') and result.score is not None:
                    result.score *= boost_factor
                    result.boosted = True
                    boosted_count += 1
                    logger.debug(f"  Boosted result: {original_score:.3f} → {result.score:.3f}")
                elif isinstance(result, dict) and 'score' in result:
                    result['score'] *= boost_factor
                    result['boosted'] = True
                    boosted_count += 1
                    logger.debug(f"  Boosted result: {original_score:.3f} → {result['score']:.3f}")
        
        # Sort by score descending
        def get_score(result):
            if hasattr(result, 'score'):
                return result.score or 0
            elif isinstance(result, dict):
                return result.get('score', 0)
            return 0
            
        sorted_results = sorted(results, key=get_score, reverse=True)
        
        if boosted_count > 0:
            logger.info(f"✅ Boosted {boosted_count} user-relevant results out of {len(results)}")
        else:
            logger.debug(f"ℹ️ No user-relevant results found to boost")
            
        return sorted_results
    
    def is_user_relevant_result(self, result: Any) -> bool:
        """
        Check if search result involves the primary user
        
        Args:
            result: Search result object or dictionary
            
        Returns:
            True if result is relevant to PRIMARY_USER
        """
        if not self.filter.primary_user:
            return False
            
        user = self.filter.primary_user
        
        # Get result content and metadata
        content = self._extract_content(result)
        metadata = self._extract_metadata(result)
        
        # Check content for user identifiers
        if self._check_content_relevance(content, user):
            return True
            
        # Check metadata for user involvement
        if self._check_metadata_relevance(metadata, user):
            return True
            
        return False
    
    def _extract_content(self, result: Any) -> str:
        """Extract textual content from search result"""
        content = ""
        
        # Handle object attributes
        if hasattr(result, 'content'):
            content += str(result.content or "")
        if hasattr(result, 'text'):
            content += " " + str(result.text or "")
        if hasattr(result, 'title'):
            content += " " + str(result.title or "")
        if hasattr(result, 'summary'):
            content += " " + str(result.summary or "")
            
        # Handle dictionary
        if isinstance(result, dict):
            content_fields = ['content', 'text', 'title', 'summary', 'description', 'body']
            for field in content_fields:
                if field in result and result[field]:
                    content += " " + str(result[field])
                    
        return content.strip()
    
    def _extract_metadata(self, result: Any) -> Dict[str, Any]:
        """Extract metadata from search result"""
        metadata = {}
        
        # Handle object attributes
        if hasattr(result, 'metadata') and isinstance(result.metadata, dict):
            metadata.update(result.metadata)
            
        # Handle dictionary
        if isinstance(result, dict):
            # Direct metadata field
            if 'metadata' in result and isinstance(result['metadata'], dict):
                metadata.update(result['metadata'])
                
            # Common metadata fields at root level
            metadata_fields = ['attendees', 'author', 'user_id', 'organizer', 'participants']
            for field in metadata_fields:
                if field in result:
                    metadata[field] = result[field]
                    
        return metadata
    
    def _check_content_relevance(self, content: str, user: Dict[str, Any]) -> bool:
        """Check if content contains user identifiers"""
        if not content:
            return False
            
        content_lower = content.lower()
        
        # Check user email
        user_email = user.get("email", "").lower()
        if user_email and user_email in content_lower:
            return True
            
        # Check user Slack ID
        user_slack_id = user.get("slack_id", "")
        if user_slack_id and user_slack_id in content:
            return True
            
        # Check user name patterns
        user_name = user.get("name", "")
        if user_name:
            # Check @username mention pattern
            first_name = user_name.split()[0].lower() if user_name else ""
            if first_name and f"@{first_name}" in content_lower:
                return True
                
            # Check full name
            if user_name.lower() in content_lower:
                return True
                
        return False
    
    def _check_metadata_relevance(self, metadata: Dict[str, Any], user: Dict[str, Any]) -> bool:
        """Check if metadata indicates user involvement"""
        if not metadata:
            return False
            
        user_email = user.get("email", "").lower()
        user_slack_id = user.get("slack_id", "")
        
        # Check attendees list
        attendees = metadata.get('attendees', [])
        if isinstance(attendees, list) and user_email:
            attendees_lower = [str(a).lower() for a in attendees]
            if user_email in attendees_lower:
                return True
                
        # Check author/organizer
        author_fields = ['author', 'organizer', 'creator', 'sender']
        for field in author_fields:
            value = metadata.get(field)
            if value:
                if isinstance(value, str) and user_email and value.lower() == user_email:
                    return True
                elif isinstance(value, dict) and value.get('email', '').lower() == user_email:
                    return True
                    
        # Check user_id (Slack)
        if user_slack_id and metadata.get('user_id') == user_slack_id:
            return True
            
        return False
    
    def get_boosted_results_info(self, results: List[Any]) -> Dict[str, Any]:
        """
        Get information about boosted results
        
        Args:
            results: List of search results (after boosting)
            
        Returns:
            Dictionary with boosting statistics
        """
        if not results:
            return {'total_results': 0, 'boosted_results': 0, 'boost_percentage': 0}
            
        total_results = len(results)
        boosted_results = 0
        
        for result in results:
            # Check for boost marker
            is_boosted = False
            if hasattr(result, 'boosted'):
                is_boosted = result.boosted
            elif isinstance(result, dict):
                is_boosted = result.get('boosted', False)
                
            if is_boosted:
                boosted_results += 1
                
        boost_percentage = (boosted_results / total_results) * 100 if total_results > 0 else 0
        
        return {
            'total_results': total_results,
            'boosted_results': boosted_results,
            'boost_percentage': boost_percentage,
            'primary_user': self.filter.primary_user['email'] if self.filter.primary_user else None
        }

# Convenience function for search integration
def search_with_personalization(search_func, query: str, limit: int = 20, boost_factor: float = 1.5):
    """
    Wrapper function to add personalization to any search function
    
    Args:
        search_func: Function that performs search and returns results
        query: Search query string
        limit: Number of results to return
        boost_factor: Boost factor for user-relevant results
        
    Returns:
        Personalized search results
        
    Usage:
        def my_search(query, limit):
            # Your search logic here
            return results
            
        personalized_results = search_with_personalization(my_search, "query", 20)
    """
    # Get extra results to account for boosting
    extra_results = search_func(query, limit * 2)
    
    # Apply personalization boost
    booster = RelevanceBooster()
    boosted_results = booster.boost_search_results(extra_results, boost_factor)
    
    # Return top results after boosting
    return boosted_results[:limit]

if __name__ == "__main__":
    # Test the RelevanceBooster system
    print("🧪 Testing RelevanceBooster System")
    print("=" * 40)
    
    # Create mock search results for testing
    class MockResult:
        def __init__(self, title, score, content="", metadata=None):
            self.title = title
            self.score = score
            self.content = content
            self.metadata = metadata or {}
            self.boosted = False
    
    # Initialize booster
    booster = RelevanceBooster()
    
    if booster.filter.primary_user:
        user_email = booster.filter.primary_user['email']
        print(f"✅ PRIMARY_USER configured: {user_email}")
        
        # Create test results
        test_results = [
            MockResult("Meeting notes", 0.8, content=f"Meeting with {user_email}"),
            MockResult("Project update", 0.7, content="General project update"),
            MockResult("User mention", 0.6, content=f"Message mentioning {user_email.split('@')[0]}"),
            MockResult("Other document", 0.5, content="Unrelated content"),
        ]
        
        print(f"\n🔍 Original scores:")
        for result in test_results:
            print(f"  {result.title}: {result.score:.3f}")
        
        # Apply boosting
        boosted_results = booster.boost_search_results(test_results)
        
        print(f"\n📈 After boosting:")
        for result in boosted_results:
            boost_indicator = " (boosted)" if getattr(result, 'boosted', False) else ""
            print(f"  {result.title}: {result.score:.3f}{boost_indicator}")
        
        # Get boosting info
        info = booster.get_boosted_results_info(boosted_results)
        print(f"\n📊 Boosting statistics:")
        print(f"  Boosted: {info['boosted_results']}/{info['total_results']} ({info['boost_percentage']:.1f}%)")
        
    else:
        print("ℹ️ No PRIMARY_USER configured (no boosting)")
        print("  Search results will be returned unchanged")
        
    print("\n✅ RelevanceBooster system test complete")