# Phase 1 Enhancement: Query Caching & User Preferences

**Date Created**: 2025-08-21  
**Owner**: Enhancement Team  
**Status**: PENDING  
**Estimated Time**: 3 days (24 hours)  
**Dependencies**: Search infrastructure ✅, Query Engine ✅, Database (340K+ records) ✅

## Executive Summary

Implement high-value, low-complexity enhancements that provide immediate performance improvements and personalization without architectural complexity. These enhancements were recommended after evaluating and rejecting complex memory systems (Memori, M3, Knowledge Graphs) in favor of simple, effective solutions.

**Core Philosophy**: Maximum benefit with minimal complexity. These improvements should make the system faster and smarter without adding debugging burden or maintenance overhead.

## Architectural Context

### Why These Enhancements Now

After comprehensive analysis ([docs/architecture_decisions/memory_systems_analysis.md](../docs/architecture_decisions/memory_systems_analysis.md)), we determined:
- Complex memory systems would add 50-100% latency and 3x maintenance burden
- Current system already achieves <1 second queries with 340K+ records
- Simple improvements can provide 80% of the benefit with 5% of the complexity

### Integration Benefits
- **Immediate Impact**: CLI tools get instant speed boost
- **Slack Bot Ready**: Bot inherits all improvements automatically
- **Zero Breaking Changes**: Purely additive enhancements
- **Future Proof**: Clean integration points for further optimization

## Module Architecture

### Relevant Files for Context

**Read for Understanding:**
- `src/search/database.py` - SearchDatabase class for query execution (target for caching)
- `src/intelligence/query_engine.py` - QueryEngine with existing query history
- `src/queries/time_queries.py` - TimeQueryEngine for deterministic queries
- `src/queries/person_queries.py` - PersonQueryEngine for person lookups
- `tools/search_cli.py` - CLI interface that will benefit from caching

**Files to Create:**
- `src/search/query_cache.py` - Query result caching system
- `src/intelligence/user_preferences.py` - User preference learning and tracking
- `src/search/cache_manager.py` - Cache lifecycle and invalidation management
- `tests/unit/test_query_cache.py` - Comprehensive cache testing
- `tests/unit/test_user_preferences.py` - Preference learning tests
- `tests/integration/test_caching_performance.py` - Performance validation

**Files to Modify:**
- `src/search/database.py` - Add cache integration hooks
- `src/intelligence/query_engine.py` - Add preference tracking
- `tools/search_cli.py` - Display cache hit indicators
- `src/core/config.py` - Add cache configuration options

**Reference Patterns:**
- `src/core/state.py` - SQLite state management patterns
- `src/collectors/base.py:71-82` - Circuit breaker state management
- `src/search/database.py:165-170` - Database optimization patterns

## Test-Driven Development Plan

### Phase 1: Query Result Caching (Day 1 - 8 hours)

#### Test Acceptance Criteria (Write FIRST)

**File**: `tests/unit/test_query_cache.py`
```python
import pytest
import time
import hashlib
from datetime import datetime, timedelta
from src.search.query_cache import QueryCache, CacheEntry, CacheStats
from src.search.cache_manager import CacheManager, InvalidationStrategy

class TestQueryCache:
    """Test query result caching with TTL and invalidation"""
    
    def test_basic_cache_hit(self):
        """Cache returns stored results for identical queries"""
        cache = QueryCache(ttl_seconds=3600)
        
        query = "find messages from john about project deadline"
        results = [
            {'id': 1, 'content': 'Project deadline is Friday', 'source': 'slack'},
            {'id': 2, 'content': 'John said deadline moved', 'source': 'slack'}
        ]
        
        # Store in cache
        cache.set(query, results)
        
        # Retrieve from cache
        cached = cache.get(query)
        
        assert cached is not None
        assert cached == results
        assert cache.stats.hits == 1
        assert cache.stats.misses == 0
    
    def test_cache_miss_on_different_query(self):
        """Cache correctly misses for different queries"""
        cache = QueryCache(ttl_seconds=3600)
        
        cache.set("query one", [{'id': 1}])
        result = cache.get("query two")
        
        assert result is None
        assert cache.stats.hits == 0
        assert cache.stats.misses == 1
    
    def test_ttl_expiration(self):
        """Cache entries expire after TTL"""
        cache = QueryCache(ttl_seconds=1)  # 1 second TTL
        
        cache.set("test query", [{'id': 1}])
        
        # Should hit immediately
        assert cache.get("test query") is not None
        
        # Should miss after TTL
        time.sleep(1.1)
        assert cache.get("test query") is None
    
    def test_query_normalization(self):
        """Similar queries normalize to same cache key"""
        cache = QueryCache(ttl_seconds=3600)
        
        # These queries should normalize to same key
        queries = [
            "find messages from John",
            "Find Messages From John",  # Different case
            "find  messages  from  John",  # Extra spaces
            "find messages from John "  # Trailing space
        ]
        
        results = [{'id': 1, 'content': 'test'}]
        cache.set(queries[0], results)
        
        # All variations should hit cache
        for query in queries[1:]:
            cached = cache.get(query)
            assert cached == results, f"Failed for query: {query}"
    
    def test_cache_size_limits(self):
        """Cache respects maximum size limits"""
        cache = QueryCache(ttl_seconds=3600, max_size_mb=1)  # 1MB limit
        
        # Add entries until size limit
        for i in range(1000):
            query = f"query_{i}"
            # Large result set
            results = [{'id': j, 'data': 'x' * 1000} for j in range(10)]
            cache.set(query, results)
            
            if cache.get_size_mb() > 1:
                break
        
        assert cache.get_size_mb() <= 1.1  # Allow 10% tolerance
        assert cache.stats.evictions > 0
    
    def test_lru_eviction(self):
        """Least recently used entries evicted first"""
        cache = QueryCache(ttl_seconds=3600, max_entries=3)
        
        cache.set("query1", [{'id': 1}])
        cache.set("query2", [{'id': 2}])
        cache.set("query3", [{'id': 3}])
        
        # Access query1 to make it recently used
        cache.get("query1")
        
        # Add new entry, should evict query2 (least recently used)
        cache.set("query4", [{'id': 4}])
        
        assert cache.get("query1") is not None  # Still cached
        assert cache.get("query2") is None  # Evicted
        assert cache.get("query3") is not None  # Still cached
        assert cache.get("query4") is not None  # Newly added

class TestCacheInvalidation:
    """Test cache invalidation strategies"""
    
    def test_time_based_invalidation(self):
        """Invalidate cache entries by time window"""
        manager = CacheManager()
        cache = manager.get_cache("search")
        
        # Add entries with different timestamps
        cache.set("old_query", [{'id': 1}], 
                 timestamp=datetime.now() - timedelta(hours=2))
        cache.set("new_query", [{'id': 2}], 
                 timestamp=datetime.now())
        
        # Invalidate entries older than 1 hour
        manager.invalidate_by_time(older_than_hours=1)
        
        assert cache.get("old_query") is None
        assert cache.get("new_query") is not None
    
    def test_source_based_invalidation(self):
        """Invalidate cache entries by data source"""
        manager = CacheManager()
        cache = manager.get_cache("search")
        
        # Cache queries from different sources
        cache.set("slack query", [{'id': 1, 'source': 'slack'}])
        cache.set("calendar query", [{'id': 2, 'source': 'calendar'}])
        cache.set("mixed query", [
            {'id': 3, 'source': 'slack'},
            {'id': 4, 'source': 'calendar'}
        ])
        
        # Invalidate slack-related entries
        manager.invalidate_by_source("slack")
        
        assert cache.get("slack query") is None
        assert cache.get("calendar query") is not None
        assert cache.get("mixed query") is None  # Has slack content
    
    def test_pattern_based_invalidation(self):
        """Invalidate cache entries matching pattern"""
        manager = CacheManager()
        cache = manager.get_cache("search")
        
        cache.set("messages from john", [{'id': 1}])
        cache.set("messages from jane", [{'id': 2}])
        cache.set("calendar events", [{'id': 3}])
        
        # Invalidate all message queries
        manager.invalidate_by_pattern("messages from")
        
        assert cache.get("messages from john") is None
        assert cache.get("messages from jane") is None
        assert cache.get("calendar events") is not None

class TestCacheStatistics:
    """Test cache performance statistics and monitoring"""
    
    def test_hit_rate_calculation(self):
        """Calculate cache hit rate accurately"""
        cache = QueryCache(ttl_seconds=3600)
        
        # Create hit/miss pattern
        cache.set("cached", [{'id': 1}])
        
        cache.get("cached")  # Hit
        cache.get("cached")  # Hit
        cache.get("uncached")  # Miss
        cache.get("cached")  # Hit
        cache.get("another")  # Miss
        
        stats = cache.get_stats()
        
        assert stats.hits == 3
        assert stats.misses == 2
        assert stats.hit_rate == 0.6  # 3/5
    
    def test_cache_performance_tracking(self):
        """Track cache performance metrics"""
        cache = QueryCache(ttl_seconds=3600)
        
        # Simulate cache operations
        start = time.time()
        cache.set("query", [{'id': i} for i in range(100)])
        set_time = time.time() - start
        
        start = time.time()
        result = cache.get("query")
        get_time = time.time() - start
        
        stats = cache.get_stats()
        
        # Cache should be much faster than original query
        assert get_time < set_time * 0.1  # At least 10x faster
        assert stats.avg_save_time_ms > 0
        assert stats.total_queries == 1
```

#### Implementation Tasks

**Task 1.1: Core Cache Implementation (3 hours)**
```python
# src/search/query_cache.py
import hashlib
import json
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

@dataclass
class CacheEntry:
    """Single cache entry with metadata"""
    query: str
    query_hash: str
    results: List[Dict[str, Any]]
    timestamp: datetime
    access_count: int = 0
    last_accessed: datetime = None
    size_bytes: int = 0
    sources: List[str] = None
    
    def is_expired(self, ttl_seconds: int) -> bool:
        """Check if entry has expired"""
        age = (datetime.now() - self.timestamp).total_seconds()
        return age > ttl_seconds

@dataclass
class CacheStats:
    """Cache performance statistics"""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    total_queries: int = 0
    avg_save_time_ms: float = 0
    cache_size_mb: float = 0
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate"""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0

class QueryCache:
    """
    High-performance query result cache with TTL and LRU eviction
    
    Features:
    - TTL-based expiration
    - LRU eviction when size limits reached
    - Query normalization for better hit rates
    - Source-based invalidation support
    - Performance statistics tracking
    """
    
    def __init__(self, ttl_seconds: int = 3600, max_size_mb: float = 100, 
                 max_entries: int = 10000):
        self.ttl_seconds = ttl_seconds
        self.max_size_mb = max_size_mb
        self.max_entries = max_entries
        self.cache = OrderedDict()  # Maintains insertion order for LRU
        self.stats = CacheStats()
        
    def _normalize_query(self, query: str) -> str:
        """Normalize query for consistent cache keys"""
        # Lowercase, remove extra spaces, strip
        normalized = ' '.join(query.lower().split())
        return normalized.strip()
    
    def _hash_query(self, query: str) -> str:
        """Generate cache key from normalized query"""
        normalized = self._normalize_query(query)
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def get(self, query: str) -> Optional[List[Dict[str, Any]]]:
        """Retrieve cached results if available"""
        query_hash = self._hash_query(query)
        
        if query_hash in self.cache:
            entry = self.cache[query_hash]
            
            # Check expiration
            if entry.is_expired(self.ttl_seconds):
                del self.cache[query_hash]
                self.stats.misses += 1
                return None
            
            # Update access tracking
            entry.access_count += 1
            entry.last_accessed = datetime.now()
            
            # Move to end (most recently used)
            self.cache.move_to_end(query_hash)
            
            self.stats.hits += 1
            return entry.results
        
        self.stats.misses += 1
        return None
    
    def set(self, query: str, results: List[Dict[str, Any]], 
            timestamp: datetime = None):
        """Store query results in cache"""
        query_hash = self._hash_query(query)
        
        # Extract sources from results
        sources = list(set(r.get('source', 'unknown') for r in results))
        
        entry = CacheEntry(
            query=self._normalize_query(query),
            query_hash=query_hash,
            results=results,
            timestamp=timestamp or datetime.now(),
            sources=sources,
            size_bytes=len(json.dumps(results).encode())
        )
        
        # Evict if necessary
        self._evict_if_needed(entry.size_bytes)
        
        self.cache[query_hash] = entry
        self.stats.total_queries += 1
    
    def _evict_if_needed(self, new_entry_size: int):
        """Evict entries if size or count limits exceeded"""
        # Check entry count limit
        while len(self.cache) >= self.max_entries:
            self._evict_lru()
        
        # Check size limit
        while self.get_size_mb() + (new_entry_size / 1024 / 1024) > self.max_size_mb:
            if not self._evict_lru():
                break  # Nothing left to evict
    
    def _evict_lru(self) -> bool:
        """Evict least recently used entry"""
        if self.cache:
            self.cache.popitem(last=False)  # Remove first item (LRU)
            self.stats.evictions += 1
            return True
        return False
    
    def get_size_mb(self) -> float:
        """Calculate total cache size in MB"""
        total_bytes = sum(entry.size_bytes for entry in self.cache.values())
        return total_bytes / 1024 / 1024
    
    def get_stats(self) -> CacheStats:
        """Get cache performance statistics"""
        self.stats.cache_size_mb = self.get_size_mb()
        return self.stats
    
    def clear(self):
        """Clear all cache entries"""
        self.cache.clear()
        self.stats = CacheStats()
    
    def invalidate_by_source(self, source: str):
        """Invalidate entries containing specific source"""
        to_remove = []
        for query_hash, entry in self.cache.items():
            if source in entry.sources:
                to_remove.append(query_hash)
        
        for query_hash in to_remove:
            del self.cache[query_hash]
```

**Task 1.2: Cache Manager Implementation (2 hours)**
```python
# src/search/cache_manager.py
class CacheManager:
    """Manage multiple caches and invalidation strategies"""
    
    def __init__(self):
        self.caches = {}
        self.invalidation_hooks = []
    
    def get_cache(self, name: str) -> QueryCache:
        """Get or create named cache"""
        if name not in self.caches:
            self.caches[name] = QueryCache()
        return self.caches[name]
    
    def invalidate_by_time(self, older_than_hours: int):
        """Invalidate entries older than specified hours"""
        cutoff = datetime.now() - timedelta(hours=older_than_hours)
        for cache in self.caches.values():
            to_remove = []
            for query_hash, entry in cache.cache.items():
                if entry.timestamp < cutoff:
                    to_remove.append(query_hash)
            for query_hash in to_remove:
                del cache.cache[query_hash]
    
    def invalidate_by_source(self, source: str):
        """Invalidate entries from specific source"""
        for cache in self.caches.values():
            cache.invalidate_by_source(source)
    
    def invalidate_by_pattern(self, pattern: str):
        """Invalidate entries matching query pattern"""
        for cache in self.caches.values():
            to_remove = []
            for query_hash, entry in cache.cache.items():
                if pattern.lower() in entry.query:
                    to_remove.append(query_hash)
            for query_hash in to_remove:
                del cache.cache[query_hash]
```

**Task 1.3: Database Integration (2 hours)**
- Modify SearchDatabase to use QueryCache
- Add cache configuration to Config class
- Implement cache warming strategies
- Add cache invalidation hooks for data updates

**Task 1.4: CLI Integration (1 hour)**
- Add cache hit indicators to search results
- Implement cache statistics command
- Add cache management commands (clear, stats, warm)
- Create visual indicators for cached vs fresh results

### Phase 2: User Preference Learning (Day 2-3 - 16 hours)

#### Test Acceptance Criteria (Write FIRST)

**File**: `tests/unit/test_user_preferences.py`
```python
import pytest
from datetime import datetime, timedelta
from src.intelligence.user_preferences import (
    UserPreferences, PreferenceTracker, QueryPattern, PreferenceProfile
)

class TestPreferenceTracking:
    """Test user preference learning from query patterns"""
    
    def test_source_preference_learning(self):
        """Learn which data sources user prefers"""
        tracker = PreferenceTracker(user_id="test_user")
        
        # Simulate user queries
        tracker.track_query("find slack messages", sources_used=["slack"])
        tracker.track_query("search slack for updates", sources_used=["slack"])
        tracker.track_query("calendar events today", sources_used=["calendar"])
        tracker.track_query("messages from john", sources_used=["slack"])
        
        preferences = tracker.get_source_preferences()
        
        assert preferences["slack"] > preferences["calendar"]
        assert preferences["slack"] > preferences.get("drive", 0)
        assert sum(preferences.values()) == 1.0  # Normalized to 1
    
    def test_time_range_preference(self):
        """Learn typical time ranges user queries"""
        tracker = PreferenceTracker(user_id="test_user")
        
        # User typically queries last week
        tracker.track_query("messages last week", time_range="last_week")
        tracker.track_query("what happened last week", time_range="last_week")
        tracker.track_query("last week's meetings", time_range="last_week")
        tracker.track_query("yesterday's updates", time_range="yesterday")
        
        preferences = tracker.get_time_preferences()
        
        assert preferences["preferred_range"] == "last_week"
        assert preferences["range_frequency"]["last_week"] > 0.5
    
    def test_keyword_extraction(self):
        """Extract common keywords from user queries"""
        tracker = PreferenceTracker(user_id="test_user")
        
        queries = [
            "project alpha status",
            "updates on project alpha",
            "project alpha meeting notes",
            "budget review meeting",
            "quarterly budget analysis"
        ]
        
        for query in queries:
            tracker.track_query(query)
        
        keywords = tracker.get_common_keywords(min_frequency=2)
        
        assert "project" in keywords
        assert "alpha" in keywords
        assert "budget" in keywords
        assert len(keywords) <= 10  # Top 10 keywords
    
    def test_query_time_patterns(self):
        """Learn when user typically makes queries"""
        tracker = PreferenceTracker(user_id="test_user")
        
        # Morning queries
        for hour in [9, 10, 11]:
            tracker.track_query(
                f"query at {hour}", 
                timestamp=datetime.now().replace(hour=hour)
            )
        
        # Afternoon query
        tracker.track_query(
            "afternoon query",
            timestamp=datetime.now().replace(hour=14)
        )
        
        patterns = tracker.get_temporal_patterns()
        
        assert patterns["peak_hours"][0] in [9, 10, 11]
        assert patterns["morning_user"] == True
        assert patterns["queries_by_hour"][9] > 0
    
    def test_result_interaction_tracking(self):
        """Track which results user interacts with"""
        tracker = PreferenceTracker(user_id="test_user")
        
        # User clicks on certain types of results
        tracker.track_result_interaction(
            query="project updates",
            result_id="1",
            result_metadata={"source": "slack", "author": "john"}
        )
        tracker.track_result_interaction(
            query="team updates",
            result_id="2", 
            result_metadata={"source": "slack", "author": "john"}
        )
        tracker.track_result_interaction(
            query="calendar",
            result_id="3",
            result_metadata={"source": "calendar", "author": "system"}
        )
        
        preferences = tracker.get_interaction_preferences()
        
        assert preferences["preferred_authors"]["john"] > 0.5
        assert preferences["clicked_sources"]["slack"] > preferences["clicked_sources"]["calendar"]

class TestPreferenceApplication:
    """Test applying learned preferences to improve results"""
    
    def test_result_reranking(self):
        """Rerank results based on user preferences"""
        preferences = UserPreferences(user_id="test_user")
        
        # Set learned preferences
        preferences.set_source_preference("slack", 0.7)
        preferences.set_source_preference("calendar", 0.3)
        preferences.set_author_preference("john", 0.8)
        
        # Original results
        results = [
            {"id": 1, "source": "calendar", "author": "jane", "score": 0.9},
            {"id": 2, "source": "slack", "author": "john", "score": 0.8},
            {"id": 3, "source": "slack", "author": "bob", "score": 0.85},
            {"id": 4, "source": "drive", "author": "john", "score": 0.7}
        ]
        
        reranked = preferences.apply_preferences(results)
        
        # John's slack message should rank highest despite lower original score
        assert reranked[0]["id"] == 2
        assert reranked[0]["personalized_score"] > reranked[0]["score"]
    
    def test_query_expansion(self):
        """Expand queries with learned common terms"""
        preferences = UserPreferences(user_id="test_user")
        
        # User frequently searches for "project alpha"
        preferences.add_common_term("project alpha", frequency=10)
        preferences.add_common_term("budget", frequency=5)
        
        # Expand query
        original = "status update"
        expanded = preferences.expand_query(original)
        
        # Should suggest related common terms
        assert "project alpha" in expanded["suggestions"]
        assert expanded["expanded_query"] != original
    
    def test_default_filter_application(self):
        """Apply default filters based on preferences"""
        preferences = UserPreferences(user_id="test_user")
        
        # User typically queries last week
        preferences.set_time_preference("last_week", frequency=0.7)
        # User typically looks at slack
        preferences.set_source_preference("slack", 0.8)
        
        # Apply defaults to empty query
        query_params = {}
        enhanced = preferences.apply_defaults(query_params)
        
        assert enhanced["time_range"] == "last_week"
        assert enhanced["preferred_sources"] == ["slack"]
        assert enhanced["boost_factors"]["slack"] > 1.0

class TestPreferencePersonalization:
    """Test personalization features"""
    
    def test_multi_user_isolation(self):
        """Preferences are isolated per user"""
        tracker1 = PreferenceTracker(user_id="user1")
        tracker2 = PreferenceTracker(user_id="user2")
        
        tracker1.track_query("slack messages", sources_used=["slack"])
        tracker2.track_query("calendar events", sources_used=["calendar"])
        
        prefs1 = tracker1.get_source_preferences()
        prefs2 = tracker2.get_source_preferences()
        
        assert prefs1["slack"] > prefs1.get("calendar", 0)
        assert prefs2["calendar"] > prefs2.get("slack", 0)
    
    def test_preference_decay(self):
        """Old preferences decay over time"""
        tracker = PreferenceTracker(user_id="test_user", decay_days=7)
        
        # Old preference
        old_time = datetime.now() - timedelta(days=14)
        tracker.track_query("old query", sources_used=["drive"], timestamp=old_time)
        
        # Recent preference
        tracker.track_query("new query", sources_used=["slack"])
        tracker.track_query("another new", sources_used=["slack"])
        
        preferences = tracker.get_source_preferences()
        
        # Recent preferences should dominate
        assert preferences["slack"] > preferences.get("drive", 0) * 2
    
    def test_preference_export_import(self):
        """Export and import preference profiles"""
        tracker = PreferenceTracker(user_id="test_user")
        
        # Build preferences
        tracker.track_query("test query", sources_used=["slack"])
        tracker.add_keyword("important")
        
        # Export
        profile = tracker.export_profile()
        
        assert profile["user_id"] == "test_user"
        assert "source_preferences" in profile
        assert "keywords" in profile
        
        # Import to new tracker
        new_tracker = PreferenceTracker(user_id="test_user")
        new_tracker.import_profile(profile)
        
        assert new_tracker.get_source_preferences() == tracker.get_source_preferences()
```

#### Implementation Tasks

**Task 2.1: Preference Tracking Core (4 hours)**
```python
# src/intelligence/user_preferences.py
from collections import defaultdict, Counter
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import json
import sqlite3

class PreferenceTracker:
    """
    Track and learn user preferences from query patterns
    
    Features:
    - Source preference learning
    - Time range pattern detection
    - Keyword extraction
    - Temporal usage patterns
    - Result interaction tracking
    """
    
    def __init__(self, user_id: str, db_path: str = "preferences.db", 
                 decay_days: int = 30):
        self.user_id = user_id
        self.db_path = db_path
        self.decay_days = decay_days
        
        # In-memory tracking
        self.query_history = []
        self.interactions = []
        self.keywords = Counter()
        
        # Initialize database
        self._init_db()
    
    def _init_db(self):
        """Initialize preference database"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS query_history (
                user_id TEXT,
                query TEXT,
                sources TEXT,
                time_range TEXT,
                timestamp DATETIME,
                results_count INTEGER
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS interactions (
                user_id TEXT,
                query TEXT,
                result_id TEXT,
                result_metadata TEXT,
                timestamp DATETIME
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS preferences (
                user_id TEXT PRIMARY KEY,
                profile TEXT,
                updated_at DATETIME
            )
        """)
        conn.commit()
        conn.close()
    
    def track_query(self, query: str, sources_used: List[str] = None,
                   time_range: str = None, timestamp: datetime = None):
        """Track a user query for preference learning"""
        timestamp = timestamp or datetime.now()
        
        # Store in memory
        self.query_history.append({
            'query': query,
            'sources': sources_used or [],
            'time_range': time_range,
            'timestamp': timestamp
        })
        
        # Extract keywords
        words = query.lower().split()
        for word in words:
            if len(word) > 3:  # Skip short words
                self.keywords[word] += 1
        
        # Persist to database
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT INTO query_history VALUES (?, ?, ?, ?, ?, ?)",
            (self.user_id, query, json.dumps(sources_used), 
             time_range, timestamp, 0)
        )
        conn.commit()
        conn.close()
    
    def track_result_interaction(self, query: str, result_id: str,
                                result_metadata: Dict[str, Any]):
        """Track which results user interacts with"""
        self.interactions.append({
            'query': query,
            'result_id': result_id,
            'metadata': result_metadata,
            'timestamp': datetime.now()
        })
        
        # Persist to database
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT INTO interactions VALUES (?, ?, ?, ?, ?)",
            (self.user_id, query, result_id, 
             json.dumps(result_metadata), datetime.now())
        )
        conn.commit()
        conn.close()
    
    def get_source_preferences(self) -> Dict[str, float]:
        """Calculate source preferences from query history"""
        source_counts = defaultdict(int)
        total = 0
        
        # Apply time decay
        cutoff = datetime.now() - timedelta(days=self.decay_days)
        
        for entry in self.query_history:
            if entry['timestamp'] > cutoff:
                for source in entry['sources']:
                    source_counts[source] += 1
                    total += 1
        
        # Normalize to probabilities
        if total > 0:
            return {k: v/total for k, v in source_counts.items()}
        return {}
    
    def get_time_preferences(self) -> Dict[str, Any]:
        """Analyze time range preferences"""
        time_counts = defaultdict(int)
        
        for entry in self.query_history:
            if entry['time_range']:
                time_counts[entry['time_range']] += 1
        
        if time_counts:
            preferred = max(time_counts, key=time_counts.get)
            total = sum(time_counts.values())
            
            return {
                'preferred_range': preferred,
                'range_frequency': {k: v/total for k, v in time_counts.items()}
            }
        return {'preferred_range': None, 'range_frequency': {}}
    
    def get_common_keywords(self, min_frequency: int = 2) -> List[str]:
        """Get frequently used keywords"""
        return [word for word, count in self.keywords.most_common(10)
                if count >= min_frequency]
    
    def get_temporal_patterns(self) -> Dict[str, Any]:
        """Analyze when user typically queries"""
        hours = defaultdict(int)
        
        for entry in self.query_history:
            hour = entry['timestamp'].hour
            hours[hour] += 1
        
        if hours:
            peak_hour = max(hours, key=hours.get)
            morning = sum(hours[h] for h in range(6, 12))
            total = sum(hours.values())
            
            return {
                'peak_hours': [peak_hour],
                'morning_user': morning > total * 0.5,
                'queries_by_hour': dict(hours)
            }
        return {}
    
    def get_interaction_preferences(self) -> Dict[str, Any]:
        """Analyze result interaction patterns"""
        author_clicks = defaultdict(int)
        source_clicks = defaultdict(int)
        
        for interaction in self.interactions:
            metadata = interaction['metadata']
            if 'author' in metadata:
                author_clicks[metadata['author']] += 1
            if 'source' in metadata:
                source_clicks[metadata['source']] += 1
        
        # Normalize
        total_authors = sum(author_clicks.values()) or 1
        total_sources = sum(source_clicks.values()) or 1
        
        return {
            'preferred_authors': {k: v/total_authors 
                                for k, v in author_clicks.items()},
            'clicked_sources': {k: v/total_sources 
                              for k, v in source_clicks.items()}
        }
    
    def export_profile(self) -> Dict[str, Any]:
        """Export user preference profile"""
        return {
            'user_id': self.user_id,
            'source_preferences': self.get_source_preferences(),
            'time_preferences': self.get_time_preferences(),
            'keywords': self.get_common_keywords(),
            'temporal_patterns': self.get_temporal_patterns(),
            'interaction_preferences': self.get_interaction_preferences(),
            'exported_at': datetime.now().isoformat()
        }
    
    def import_profile(self, profile: Dict[str, Any]):
        """Import user preference profile"""
        # This would restore preferences from exported profile
        pass
```

**Task 2.2: Preference Application Engine (4 hours)**
```python
class UserPreferences:
    """Apply learned preferences to enhance queries and results"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.tracker = PreferenceTracker(user_id)
        self.source_weights = {}
        self.author_weights = {}
        self.common_terms = []
    
    def set_source_preference(self, source: str, weight: float):
        """Set source preference weight"""
        self.source_weights[source] = weight
    
    def set_author_preference(self, author: str, weight: float):
        """Set author preference weight"""
        self.author_weights[author] = weight
    
    def add_common_term(self, term: str, frequency: int):
        """Add common search term"""
        self.common_terms.append((term, frequency))
    
    def apply_preferences(self, results: List[Dict]) -> List[Dict]:
        """Apply preferences to rerank results"""
        for result in results:
            original_score = result.get('score', 1.0)
            
            # Apply source boost
            source = result.get('source', 'unknown')
            source_boost = self.source_weights.get(source, 1.0)
            
            # Apply author boost
            author = result.get('author', 'unknown')
            author_boost = self.author_weights.get(author, 1.0)
            
            # Calculate personalized score
            result['personalized_score'] = (
                original_score * source_boost * author_boost
            )
        
        # Sort by personalized score
        return sorted(results, key=lambda x: x['personalized_score'], 
                     reverse=True)
    
    def expand_query(self, query: str) -> Dict[str, Any]:
        """Expand query with learned terms"""
        suggestions = []
        
        # Find related common terms
        query_words = set(query.lower().split())
        for term, freq in sorted(self.common_terms, 
                                key=lambda x: x[1], reverse=True):
            if term not in query_words:
                suggestions.append(term)
                if len(suggestions) >= 3:
                    break
        
        expanded = query
        if suggestions:
            expanded = f"{query} {' '.join(suggestions[:2])}"
        
        return {
            'original_query': query,
            'expanded_query': expanded,
            'suggestions': suggestions
        }
    
    def apply_defaults(self, query_params: Dict) -> Dict:
        """Apply default preferences to query"""
        enhanced = query_params.copy()
        
        # Apply time range default
        if 'time_range' not in enhanced:
            time_prefs = self.tracker.get_time_preferences()
            if time_prefs['preferred_range']:
                enhanced['time_range'] = time_prefs['preferred_range']
        
        # Apply source preferences
        source_prefs = self.tracker.get_source_preferences()
        if source_prefs:
            preferred = sorted(source_prefs.items(), 
                             key=lambda x: x[1], reverse=True)
            enhanced['preferred_sources'] = [s for s, _ in preferred[:2]]
            enhanced['boost_factors'] = {
                s: 1 + (w * 0.5) for s, w in source_prefs.items()
            }
        
        return enhanced
```

**Task 2.3: Integration with Query Engine (4 hours)**
- Modify QueryEngine to use PreferenceTracker
- Add preference learning hooks to search operations
- Implement result reranking based on preferences
- Add preference-based query expansion

**Task 2.4: Privacy and Persistence (4 hours)**
- Implement secure preference storage
- Add preference export/import functionality
- Create preference reset and privacy controls
- Add preference analytics dashboard

## Integration Requirements

### Cache Integration Points
- SearchDatabase: Add cache layer before query execution
- QueryEngine: Check cache before processing
- CLI tools: Display cache status in results
- Slack bot: Inherit cache benefits automatically

### Preference Integration Points
- QueryEngine: Track all queries for learning
- SearchDatabase: Apply preference-based result ranking
- CLI tools: Show personalized suggestions
- User settings: Preference management interface

### Performance Requirements
- Cache hit response time: <10ms
- Cache miss overhead: <5ms
- Preference calculation: <50ms
- Memory usage: <200MB for typical cache
- Preference database: <10MB per user

## Success Criteria

### Cache Validation ✅
- [ ] 80% hit rate for repeated queries
- [ ] 10x speed improvement for cached queries
- [ ] Proper TTL expiration working
- [ ] LRU eviction functioning correctly
- [ ] Cache invalidation strategies working

### Preference Validation ✅
- [ ] Source preferences correctly learned
- [ ] Time patterns accurately detected
- [ ] Result reranking improves relevance
- [ ] Query expansion provides useful suggestions
- [ ] Multi-user isolation working

### Integration Validation ✅
- [ ] CLI tools show cache indicators
- [ ] Preferences apply to all query types
- [ ] No performance degradation for cache misses
- [ ] Preference learning doesn't slow queries
- [ ] Both systems work together seamlessly

## Monitoring and Metrics

### Cache Metrics to Track
```python
cache_metrics = {
    'hit_rate': 'percentage',          # Target: >80%
    'avg_response_time_ms': 'number',  # Target: <10ms for hits
    'cache_size_mb': 'number',         # Monitor growth
    'eviction_rate': 'percentage',     # Should be low
    'invalidation_count': 'number'     # Track manual invalidations
}
```

### Preference Metrics to Track
```python
preference_metrics = {
    'queries_tracked': 'number',       # Total queries learned from
    'users_with_preferences': 'number', # Active users
    'avg_rerank_delta': 'percentage',  # How much ranking changes
    'expansion_usage': 'percentage',   # How often expansion helps
    'preference_accuracy': 'percentage' # Based on user feedback
}
```

## Implementation Schedule

### Day 1: Query Caching (8 hours)
- **Morning (4 hours)**: Write tests, implement QueryCache class
- **Afternoon (4 hours)**: Integrate with SearchDatabase, add CLI support

### Day 2: User Preferences Core (8 hours)
- **Morning (4 hours)**: Write tests, implement PreferenceTracker
- **Afternoon (4 hours)**: Build preference application engine

### Day 3: Integration & Testing (8 hours)
- **Morning (4 hours)**: Complete integrations, add monitoring
- **Afternoon (4 hours)**: Performance testing, documentation

## Risk Mitigation

### Cache Risks
- **Risk**: Cache inconsistency after data updates
- **Mitigation**: Implement source-based invalidation hooks

- **Risk**: Memory overflow from large cache
- **Mitigation**: Strict size limits with LRU eviction

### Preference Risks
- **Risk**: Incorrect preference learning
- **Mitigation**: Decay old preferences, allow manual reset

- **Risk**: Privacy concerns with tracking
- **Mitigation**: Local storage only, easy preference deletion

## Documentation Requirements

### User Documentation
- How caching improves performance
- Understanding preference learning
- Managing cache and preferences
- Privacy controls and data deletion

### Developer Documentation
- Cache integration guide
- Preference API reference
- Invalidation strategies
- Monitoring and debugging

## Delivery Checklist

Before marking complete:
- [ ] All test suites written and passing (>90% coverage)
- [ ] Cache integration working with SearchDatabase
- [ ] Preference learning functioning correctly
- [ ] Performance benchmarks documented
- [ ] CLI tools updated with new features
- [ ] Integration with existing systems validated
- [ ] Documentation complete
- [ ] Monitoring metrics implemented

---

**Note**: These enhancements were chosen after comprehensive analysis showed that complex memory systems (Memori, M3, Knowledge Graphs) would add unnecessary complexity. These simple improvements provide 80% of the benefit with 5% of the complexity.

**Reference**: [docs/architecture_decisions/memory_systems_analysis.md](../docs/architecture_decisions/memory_systems_analysis.md)