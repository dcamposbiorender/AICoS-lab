# Plan Implementation Details (Archived)

*This file contains detailed implementation specifications that were moved from plan.md to reduce context window usage.*

## Implementation Approach

### Technical Decisions
1. **SQLite FTS5**: Chosen for portability and zero-dependency deployment
2. **Connection Pooling**: Prevent database lock issues under concurrent load
3. **Incremental Indexing**: Only process changed data to minimize overhead
4. **Batch Processing**: Index in transactions for optimal performance

### Key Components
```python
# src/search/database.py
class SearchDatabase:
    def __init__(self, db_path: Path):
        self.pool = self._create_connection_pool()
    
    def initialize_schema(self):
        """Create tables and FTS5 virtual tables"""
        
    def search(self, query: str, filters: Dict) -> List[SearchResult]:
        """Execute FTS5 search with filters"""

# src/search/indexer.py  
class IndexerPipeline:
    def index_archive(self, archive_path: Path):
        """Index JSONL archive into search database"""
    
    def incremental_update(self, since: datetime):
        """Index only new/changed records"""

# src/search/query_engine.py
class QueryEngine:
    def parse_query(self, natural_query: str) -> SQLQuery:
        """Convert natural language to SQL"""
    
    def execute(self, query: str) -> SearchResults:
        """Execute search and return formatted results"""
```

### Data Flow
1. JSONL archives → Indexer → SQLite FTS5 database
2. User query → Query parser → SQL → FTS5 search → Formatted results
3. Incremental updates → Change detection → Selective re-indexing

### Success Metrics
- Search response time: <2 seconds for any query
- Indexing speed: >1000 records/second
- Search accuracy: >95% relevant results in top 10
- Incremental update time: <30 seconds for daily data
- Database size: <2x raw data size with indexes

### Risk Mitigation
- **Database Corruption**: Implement backup before indexing
- **Memory Issues**: Use streaming/batch processing
- **Lock Contention**: Connection pooling with timeouts
- **Query Complexity**: Set maximum query complexity limits
- **Performance Degradation**: Regular VACUUM and ANALYZE

### Dependencies
- Stage 1a: Archive structure for data source
- Stage 1b: Collectors providing JSONL data
- Stage 1c: Compression for handling large archives

### Testing Strategy
1. **Unit Tests**: Each component in isolation
2. **Integration Tests**: Full pipeline with sample data
3. **Performance Tests**: Measure against success metrics
4. **Stress Tests**: Handle large datasets and concurrent queries
5. **User Acceptance**: Real queries return expected results

### Estimated Timeline
- Stage 3a: 3 hours (Database foundation)
- Stage 3b: 3 hours (Indexing engine)
- Stage 3c: 2 hours (Query interface)
- **Total**: 8 hours of focused development

### Definition of Done
- [ ] All tests passing (>90% coverage)
- [ ] Search returns results in <2 seconds
- [ ] Incremental indexing working
- [ ] CLI tool functional with all features
- [ ] Documentation complete
- [ ] Performance metrics met
- [ ] Code reviewed and approved

## OAuth Token Management Simplification (Future Enhancement)

### Current Pain Points
The current OAuth setup requires users to:
1. Create OAuth apps in Google Cloud Console and Slack workspace
2. Navigate complex developer consoles to find credentials
3. Copy multiple tokens and secrets into JSON files
4. Run setup scripts that involve browser redirects
5. Manage pickle files and token refresh manually
6. Understand file paths and directory structures

**Reality Check**: This is completely unacceptable for non-technical users who just want their AI assistant to work.

### Proposed Solutions for Future Implementation

#### Solution 1: Web-Based Setup Wizard (Best for Non-Technical Users)
**Implementation**: 
- Local web server that launches automatically
- Step-by-step visual guide with screenshots
- Direct OAuth flow in the browser (no copy-paste)
- Automatic credential storage in system keychain
- One-click "Connect to Slack" and "Connect to Google" buttons

**Tradeoffs**:
- ✅ **Pros**: Dead simple for users, familiar web interface, no terminal required
- ❌ **Cons**: Requires building web UI, hosting OAuth redirect endpoints, more complex to maintain

**Non-Technical User Experience**: ⭐⭐⭐⭐⭐ (Just click buttons in browser)

#### Solution 2: Hosted OAuth Application (Recommended Long-Term)
**Implementation**:
- Provide a centrally-hosted OAuth app that users authorize
- Users click "Install AI Chief of Staff" link
- System handles all token management automatically
- Refresh tokens stored encrypted locally
- Zero configuration required by end user

**Tradeoffs**:
- ✅ **Pros**: Literally zero setup for users, professional experience, automatic updates
- ❌ **Cons**: Requires hosting infrastructure, privacy concerns with centralized auth, ongoing maintenance costs

**Non-Technical User Experience**: ⭐⭐⭐⭐⭐ (One click install like any app)

#### Solution 3: Docker Container with Pre-configured Auth
**Implementation**:
- Package entire system in Docker container
- Mount credentials as encrypted volumes
- Provide docker-compose with clear instructions
- Include web UI for initial setup
- Auto-refresh tokens in background

**Tradeoffs**:
- ✅ **Pros**: Consistent environment, easier deployment, includes all dependencies
- ❌ **Cons**: Users need Docker installed, still need initial token setup, resource overhead

**Non-Technical User Experience**: ⭐⭐ (Docker is intimidating for non-technical users)

#### Solution 4: Interactive CLI Wizard (Quick Win)
**Implementation**:
- Interactive prompts guide through setup
- Validates tokens immediately after entry
- Auto-detects missing credentials
- Creates all necessary files automatically
- Shows direct links to credential pages

**Tradeoffs**:
- ✅ **Pros**: Quick to implement, improves current experience, good error messages
- ❌ **Cons**: Still requires terminal use, manual credential copying, intimidating for non-technical users

**Non-Technical User Experience**: ⭐⭐ (Terminal is scary for many users)

#### Solution 5: Environment Variable Simplification (Minimum Viable)
**Implementation**:
- Single .env file with all credentials
- Clear template with step-by-step comments
- Validation script that checks everything
- Support for system environment variables
- Automatic token refresh

**Tradeoffs**:
- ✅ **Pros**: Simple to implement, standard approach, easy to document
- ❌ **Cons**: Still requires manual setup, editing text files, understanding environment variables

**Non-Technical User Experience**: ⭐ (Editing .env files is not user-friendly)

### Implementation Priority & Recommendations

#### For Non-Technical Users (The Only Real Option)
**Must Have**: Either Solution 1 (Web Wizard) or Solution 2 (Hosted OAuth)
- These are the ONLY viable options for true non-technical users
- Everything else requires technical knowledge that defeats the purpose
- A web interface is table stakes for consumer software in 2025

#### Phased Approach
1. **Phase 1 (Immediate)**: Implement Solution 5 (Environment Variables) as foundation
   - Gets us off hardcoded paths
   - Provides base for other solutions
   - 1-2 days of work

2. **Phase 2 (Short-term)**: Build Solution 1 (Web Wizard)
   - Local web server with OAuth flow
   - Could reuse code from existing dashboard plans
   - 1-2 weeks of work

3. **Phase 3 (Long-term)**: Deploy Solution 2 (Hosted OAuth)
   - Professional hosted solution
   - Requires infrastructure and legal review
   - 1-2 months including compliance

### Key Insights

**The Hard Truth**: Current OAuth setup is a complete blocker for non-technical adoption. No executive or general user will:
- Create developer accounts
- Navigate Google Cloud Console
- Understand OAuth scopes
- Edit JSON files
- Run Python scripts

**The Solution**: Must provide either:
1. A web interface (minimum viable for consumers)
2. A hosted service (ideal for scaling)

**Everything else is just making the current bad experience slightly less bad**, which is not sufficient for real-world deployment to non-technical users.

### Success Criteria for OAuth Simplification
- Time from download to working: <5 minutes
- Number of manual steps: <3
- Technical knowledge required: None
- Success rate for non-technical users: >95%
- Support tickets about auth: <5%