"""
FastAPI service for AI Chief of Staff search and intelligence
Provides REST API endpoints for natural language queries and context building

References:
- src/intelligence/query_engine.py - Natural language query parsing and intent recognition
- src/intelligence/result_aggregator.py - Multi-source result aggregation with intelligence
- src/search/database.py - SQLite FTS5 search database interface
- tasks_C.md lines 1264-1643 - Detailed API service specification
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel, Field
import asyncio
from contextlib import asynccontextmanager

from src.intelligence.query_engine import QueryEngine
from src.intelligence.result_aggregator import ResultAggregator
from src.search.database import SearchDatabase

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global instances
query_engine: Optional[QueryEngine] = None
aggregator: Optional[ResultAggregator] = None
search_db: Optional[SearchDatabase] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan with proper initialization and cleanup"""
    # Startup
    global query_engine, aggregator, search_db
    
    logger.info("Initializing AI Chief of Staff API...")
    
    try:
        # Initialize components in proper order
        search_db = SearchDatabase()
        query_engine = QueryEngine()
        aggregator = ResultAggregator()
        
        logger.info("API initialized successfully")
        yield
        
    except Exception as e:
        logger.error(f"Failed to initialize API: {e}")
        raise
    
    # Shutdown
    logger.info("Shutting down API...")
    if search_db:
        search_db.close()


# Create FastAPI app with comprehensive configuration
app = FastAPI(
    title="AI Chief of Staff API",
    description="Natural language search and intelligence for organizational data",
    version="1.0.0",
    lifespan=lifespan
)

# Add middleware in correct order
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models for comprehensive API validation
class SearchRequest(BaseModel):
    """Search request model with comprehensive validation"""
    query: str = Field(..., min_length=1, max_length=500, description="Natural language search query")
    sources: Optional[List[str]] = Field(None, example=["slack", "calendar", "drive"])
    time_filter: Optional[str] = Field(None, example="last_week")
    person_filter: Optional[str] = Field(None, example="alice")
    max_results: int = Field(10, ge=1, le=100, description="Maximum number of results")
    user_id: Optional[str] = Field(None, example="user123", description="User identifier for personalization")


class ContextRequest(BaseModel):
    """Context building request with intelligent options"""
    topic: str = Field(..., min_length=1, max_length=200, description="Topic to build context for")
    sources: Optional[List[str]] = Field(None, description="Sources to search across")
    time_range: Optional[str] = Field(None, example="last_month")
    include_timeline: bool = Field(True, description="Include chronological timeline")
    include_commitments: bool = Field(True, description="Include extracted commitments")


class CommitmentsRequest(BaseModel):
    """Commitments search request for action item extraction"""
    query: Optional[str] = Field("commitments", max_length=200, description="Query for commitment search")
    person: Optional[str] = Field(None, description="Filter commitments by person")
    time_filter: Optional[str] = Field("last_week", description="Time range filter")
    sources: Optional[List[str]] = Field(None, description="Sources to search")


class SearchResponse(BaseModel):
    """Comprehensive search response with metadata and intelligence"""
    results: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    query_info: Dict[str, Any]
    timestamp: str


# Dependency injection with proper error handling
async def get_query_engine() -> QueryEngine:
    """Get query engine instance with availability check"""
    if query_engine is None:
        raise HTTPException(status_code=503, detail="Query engine not initialized")
    return query_engine


async def get_aggregator() -> ResultAggregator:
    """Get result aggregator instance with availability check"""
    if aggregator is None:
        raise HTTPException(status_code=503, detail="Aggregator not initialized")
    return aggregator


async def get_search_db() -> SearchDatabase:
    """Get search database instance with availability check"""
    if search_db is None:
        raise HTTPException(status_code=503, detail="Search database not initialized")
    return search_db


# API Endpoints with comprehensive functionality
@app.get("/health")
async def health_check():
    """Health check endpoint with service status"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }


@app.post("/api/v1/search", response_model=SearchResponse)
async def search(
    request: SearchRequest,
    background_tasks: BackgroundTasks,
    engine: QueryEngine = Depends(get_query_engine),
    agg: ResultAggregator = Depends(get_aggregator),
    db: SearchDatabase = Depends(get_search_db)
):
    """
    Natural language search endpoint with intelligence
    
    Processes natural language queries and returns intelligent search results
    with context, relevance ranking, and metadata extraction.
    """
    try:
        # Parse the query with natural language understanding
        parsed_query = engine.parse_query(request.query, request.user_id)
        
        # Apply request filters to parsed query
        if request.sources:
            parsed_query.sources = request.sources
        if request.time_filter:
            parsed_query.time_filter = request.time_filter
        if request.person_filter:
            parsed_query.person_filter = request.person_filter
        
        # Convert parsed query to search parameters
        search_params = {
            'query': ' '.join(parsed_query.keywords),
            'source': parsed_query.sources[0] if len(parsed_query.sources) == 1 else None,
            'date_range': _convert_time_filter(parsed_query.time_filter),
            'limit': request.max_results
        }
        
        # Execute search with intelligent parameters
        raw_results = db.search(**search_params)
        
        # Aggregate results with multi-source intelligence
        source_results = {'mixed': raw_results}  # Simplified for single search
        aggregated = agg.aggregate(source_results, request.query, request.max_results)
        
        # Log search for analytics (background task)
        background_tasks.add_task(
            _log_search_analytics, 
            request.query, 
            len(aggregated.results),
            request.user_id
        )
        
        return SearchResponse(
            results=aggregated.results,
            metadata={
                "total_sources": aggregated.total_sources,
                "duplicates_removed": aggregated.duplicates_removed,
                "confidence_score": aggregated.confidence_score,
                "key_people": aggregated.key_people,
                "key_topics": aggregated.key_topics
            },
            query_info={
                "original_query": request.query,
                "parsed_intent": parsed_query.intent.value,
                "keywords": parsed_query.keywords,
                "sources_searched": parsed_query.sources,
                "time_filter": parsed_query.time_filter,
                "confidence": parsed_query.confidence
            },
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@app.post("/api/v1/context")
async def build_context(
    request: ContextRequest,
    engine: QueryEngine = Depends(get_query_engine),
    agg: ResultAggregator = Depends(get_aggregator),
    db: SearchDatabase = Depends(get_search_db)
):
    """
    Context building endpoint for intelligent topic summaries
    
    Builds comprehensive context summaries from multi-source data
    including timelines, key people, and commitment extraction.
    """
    try:
        # Search for topic across multiple sources
        sources = request.sources or ["slack", "calendar", "drive"]
        all_results = {}
        
        for source in sources:
            search_params = {
                'query': request.topic,
                'source': source,
                'date_range': _convert_time_filter(request.time_range),
                'limit': 20  # Get more results for better context building
            }
            results = db.search(**search_params)
            if results:
                all_results[source] = results
        
        # Aggregate with full intelligence processing
        aggregated = agg.aggregate(all_results, request.topic, 50)
        
        response = {
            "topic": request.topic,
            "summary": aggregated.context_summary,
            "key_people": aggregated.key_people,
            "key_topics": aggregated.key_topics,
            "confidence_score": aggregated.confidence_score,
            "timestamp": datetime.now().isoformat()
        }
        
        # Include optional fields based on request
        if request.include_timeline:
            response["timeline"] = aggregated.timeline
        
        if request.include_commitments:
            response["commitments"] = aggregated.commitments
        
        return response
        
    except Exception as e:
        logger.error(f"Context building error: {e}")
        raise HTTPException(status_code=500, detail=f"Context building failed: {str(e)}")


@app.post("/api/v1/commitments")
async def find_commitments(
    request: CommitmentsRequest,
    engine: QueryEngine = Depends(get_query_engine),
    agg: ResultAggregator = Depends(get_aggregator),
    db: SearchDatabase = Depends(get_search_db)
):
    """
    Commitments extraction endpoint for action item detection
    
    Finds commitments and action items from conversations using
    intelligent pattern recognition and natural language processing.
    """
    try:
        # Build search query optimized for commitment detection
        search_query = request.query or "will deliver promise commit deadline"
        
        # Search parameters optimized for commitment finding
        search_params = {
            'query': search_query,
            'source': request.sources[0] if request.sources and len(request.sources) == 1 else None,
            'date_range': _convert_time_filter(request.time_filter),
            'limit': 50  # Get more results to find commitments in context
        }
        
        # Execute search
        raw_results = db.search(**search_params)
        
        # Filter for commitment-related content using intelligent patterns
        commitment_results = []
        commitment_keywords = ['will', 'promise', 'commit', 'deliver', 'deadline', 'by', 'responsible']
        
        for result in raw_results:
            content = result.get('content', '').lower()
            if any(word in content for word in commitment_keywords):
                commitment_results.append(result)
        
        # Aggregate to extract commitments with intelligence
        source_results = {'mixed': commitment_results}
        aggregated = agg.aggregate(source_results, search_query, 30)
        
        # Filter commitments by person if specified
        filtered_commitments = aggregated.commitments
        if request.person:
            filtered_commitments = [
                c for c in aggregated.commitments 
                if request.person.lower() in c.get('person', '').lower()
            ]
        
        return {
            "commitments": filtered_commitments,
            "total_found": len(aggregated.commitments),
            "filtered_count": len(filtered_commitments),
            "search_metadata": {
                "results_searched": len(commitment_results),
                "confidence_score": aggregated.confidence_score
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Commitments search error: {e}")
        raise HTTPException(status_code=500, detail=f"Commitments search failed: {str(e)}")


@app.get("/api/v1/stats")
async def get_statistics(db: SearchDatabase = Depends(get_search_db)):
    """Get comprehensive database and API statistics"""
    try:
        db_stats = db.get_stats()
        
        return {
            "database": db_stats,
            "api_version": "1.0.0",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Stats error: {e}")
        raise HTTPException(status_code=500, detail=f"Stats unavailable: {str(e)}")


# Utility functions for request processing
def _convert_time_filter(time_filter: Optional[str]) -> Optional[tuple]:
    """
    Convert time filter string to date range tuple for database queries
    
    Supports natural language time expressions like 'last_week', 'today', etc.
    """
    if not time_filter:
        return None
    
    now = datetime.now()
    
    time_mappings = {
        'today': (now.date().isoformat(), now.date().isoformat()),
        'yesterday': ((now - timedelta(days=1)).date().isoformat(), 
                     (now - timedelta(days=1)).date().isoformat()),
        'last_week': ((now - timedelta(days=7)).date().isoformat(), 
                      now.date().isoformat()),
        'last_month': ((now - timedelta(days=30)).date().isoformat(), 
                       now.date().isoformat()),
        'this_week': ((now - timedelta(days=now.weekday())).date().isoformat(),
                      now.date().isoformat())
    }
    
    return time_mappings.get(time_filter)


async def _log_search_analytics(query: str, result_count: int, user_id: Optional[str]):
    """
    Log search analytics for monitoring and improvement (background task)
    
    In production, this would log to analytics system like Elasticsearch,
    DataDog, or custom analytics database.
    """
    # For lab deployment, just log to application logs
    logger.info(f"Search Analytics: query='{query[:50]}...', results={result_count}, user={user_id}")


# Production deployment configuration
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.intelligence.api_service:app",
        host="0.0.0.0", 
        port=8000,
        reload=True,  # For development
        log_level="info"
    )