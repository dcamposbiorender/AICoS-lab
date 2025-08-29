"""
CRM Directory - Central management for people data extending PersonResolver

References:
- src/queries/person_queries.py - PersonResolver for cross-system ID mapping
- src/core/state.py - SQLite patterns and atomic operations
- src/search/database.py - Database connection patterns

Core Philosophy: Extend existing PersonResolver with persistent CRM storage
Never replace existing functionality, only enhance it.
"""

import sqlite3
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, date, timedelta
from contextlib import contextmanager

from ..queries.person_queries import PersonResolver
from ..core.config import get_config
from .models import (
    CRMPerson, Note, ActionItem, Interaction, Relationship,
    ActionDirection, ActionStatus, InteractionType
)

logger = logging.getLogger(__name__)


def safe_json_dumps(obj: Any) -> Optional[str]:
    """Safely serialize object to JSON, handling serialization errors"""
    if obj is None:
        return None
    try:
        return json.dumps(obj)
    except (TypeError, ValueError) as e:
        logger.warning(f"JSON serialization failed for {type(obj)}: {e}")
        # Return a safe fallback
        return json.dumps(str(obj)) if obj else None


def safe_json_loads(json_str: Optional[str], default: Any = None) -> Any:
    """Safely deserialize JSON string, handling parsing errors"""
    if not json_str:
        return default
    try:
        return json.loads(json_str)
    except (TypeError, ValueError, json.JSONDecodeError) as e:
        logger.warning(f"JSON deserialization failed for '{json_str[:50]}...': {e}")
        return default


class CRMDirectory:
    """
    Central directory for CRM data, extending PersonResolver capabilities
    
    Features:
    - Imports and enhances existing 209-person roster
    - Persistent SQLite storage with audit trails
    - Cross-system ID mapping via PersonResolver
    - Rich person profiles with notes and relationships
    - Bidirectional action item tracking
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize CRM directory with database connection"""
        config = get_config()
        if db_path:
            self.db_path = db_path
        else:
            self.db_path = str(config.base_dir / "data" / "crm.db")
        
        # Initialize PersonResolver for cross-system ID mapping
        self.person_resolver = PersonResolver()
        
        # Ensure directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database schema
        self._init_database()
        
        logger.info(f"CRM Directory initialized: {self.db_path}")
        logger.info(f"PersonResolver loaded with {len(self.person_resolver.employees)} employees")
    
    def _init_database(self):
        """Initialize SQLite database schema"""
        with self._get_connection() as conn:
            # People table - rich profiles
            conn.execute("""
                CREATE TABLE IF NOT EXISTS people (
                    email TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    slack_id TEXT,
                    company TEXT,
                    role TEXT,
                    department TEXT,
                    phone TEXT,
                    location TEXT,
                    timezone TEXT,
                    linkedin TEXT,
                    twitter TEXT,
                    github TEXT,
                    website TEXT,
                    background TEXT,
                    interests TEXT, -- JSON array
                    expertise TEXT, -- JSON array
                    reports_to TEXT,
                    team_members TEXT, -- JSON array
                    key_relationships TEXT, -- JSON object
                    preferred_channel TEXT,
                    response_time TEXT,
                    meeting_preference TEXT,
                    important_dates TEXT, -- JSON array
                    tags TEXT, -- JSON array
                    first_seen TEXT,
                    last_interaction TEXT,
                    interaction_count INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (reports_to) REFERENCES people(email)
                )
            """)
            
            # Notes table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS notes (
                    id TEXT PRIMARY KEY,
                    person_email TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    author TEXT NOT NULL,
                    content TEXT NOT NULL,
                    source TEXT NOT NULL,
                    tags TEXT, -- JSON array
                    metadata TEXT, -- JSON object
                    FOREIGN KEY (person_email) REFERENCES people(email)
                )
            """)
            
            # Action items table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS action_items (
                    id TEXT PRIMARY KEY,
                    direction TEXT NOT NULL, -- i_owe, they_owe
                    counterparty TEXT NOT NULL,
                    description TEXT NOT NULL,
                    due_date TEXT,
                    status TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    source TEXT NOT NULL,
                    context TEXT,
                    created_at TEXT NOT NULL,
                    completed_at TEXT,
                    last_reminded TEXT,
                    confidence REAL NOT NULL,
                    extraction_method TEXT NOT NULL,
                    reminder_dates TEXT, -- JSON array
                    follow_up_required BOOLEAN,
                    tags TEXT, -- JSON array
                    metadata TEXT, -- JSON object
                    FOREIGN KEY (counterparty) REFERENCES people(email)
                )
            """)
            
            # Interactions table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS interactions (
                    id TEXT PRIMARY KEY,
                    person_email TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    interaction_type TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    content TEXT,
                    source TEXT NOT NULL,
                    source_id TEXT,
                    reference TEXT,
                    channel TEXT,
                    participants TEXT, -- JSON array
                    duration_minutes INTEGER,
                    key_topics TEXT, -- JSON array
                    sentiment_score REAL,
                    follow_up_required BOOLEAN,
                    parent_interaction_id TEXT,
                    thread_id TEXT,
                    metadata TEXT, -- JSON object
                    FOREIGN KEY (person_email) REFERENCES people(email),
                    FOREIGN KEY (parent_interaction_id) REFERENCES interactions(id)
                )
            """)
            
            # Relationships table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS relationships (
                    id TEXT PRIMARY KEY,
                    from_person TEXT NOT NULL,
                    to_person TEXT NOT NULL,
                    relationship_type TEXT NOT NULL,
                    strength REAL NOT NULL,
                    context TEXT,
                    created_at TEXT NOT NULL,
                    last_interaction TEXT,
                    mutual BOOLEAN,
                    metadata TEXT, -- JSON object
                    FOREIGN KEY (from_person) REFERENCES people(email),
                    FOREIGN KEY (to_person) REFERENCES people(email),
                    UNIQUE(from_person, to_person, relationship_type)
                )
            """)
            
            # Audit trail table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_trail (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    table_name TEXT NOT NULL,
                    record_id TEXT NOT NULL,
                    action TEXT NOT NULL, -- create, update, delete
                    field_name TEXT,
                    old_value TEXT,
                    new_value TEXT,
                    author TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    metadata TEXT -- JSON object
                )
            """)
            
            # Create indexes for performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_notes_person_email ON notes(person_email)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_notes_timestamp ON notes(timestamp DESC)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_actions_counterparty ON action_items(counterparty)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_actions_direction ON action_items(direction)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_actions_status ON action_items(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_actions_due_date ON action_items(due_date)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_interactions_person_email ON interactions(person_email)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_interactions_timestamp ON interactions(timestamp DESC)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_relationships_from_person ON relationships(from_person)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_relationships_to_person ON relationships(to_person)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_record ON audit_trail(table_name, record_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_people_name ON people(name)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_people_slack_id ON people(slack_id)")
            
            conn.commit()
    
    @contextmanager
    def _get_connection(self, auto_commit: bool = False):
        """Get database connection with proper cleanup and transaction handling"""
        conn = sqlite3.connect(
            self.db_path,
            timeout=30.0,  # 30 second timeout to prevent indefinite blocking
            check_same_thread=False  # Allow connection sharing across threads
        )
        conn.row_factory = sqlite3.Row  # Enable dict-like access
        
        # Configure SQLite for optimal concurrent performance
        conn.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging for better concurrency
        conn.execute("PRAGMA synchronous=NORMAL")  # Balance between performance and durability
        conn.execute("PRAGMA cache_size=10000")  # Increase cache for better performance
        conn.execute("PRAGMA temp_store=memory")  # Store temporary tables in memory
        conn.execute("PRAGMA mmap_size=268435456")  # 256MB memory-mapped I/O
        conn.execute("PRAGMA busy_timeout=30000")  # 30 second busy timeout
        
        # Begin transaction for write operations
        if auto_commit:
            conn.execute("BEGIN IMMEDIATE")  # Acquire write lock immediately
        
        try:
            yield conn
            # Commit transaction if auto_commit enabled
            if auto_commit:
                conn.commit()
        except sqlite3.OperationalError as e:
            # Handle database lock errors specifically
            if auto_commit:
                conn.rollback()
                logger.error(f"Database locked, transaction rolled back: {e}")
            raise
        except Exception as e:
            # Rollback transaction on error
            if auto_commit:
                conn.rollback()
                logger.error(f"Transaction rolled back due to error: {e}")
            raise
        finally:
            conn.close()
    
    def _log_audit(self, conn: sqlite3.Connection, table_name: str, record_id: str, 
                   action: str, author: str = "system", field_name: str = None,
                   old_value: Any = None, new_value: Any = None, metadata: Dict = None):
        """Log action to audit trail"""
        conn.execute("""
            INSERT INTO audit_trail 
            (table_name, record_id, action, field_name, old_value, new_value, author, timestamp, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            table_name, record_id, action, field_name,
            safe_json_dumps(old_value),
            safe_json_dumps(new_value),
            author, datetime.now().isoformat(),
            safe_json_dumps(metadata)
        ))
    
    def enrich_from_resolver(self) -> int:
        """
        Import existing 209 employees from PersonResolver into CRM
        
        Returns:
            Number of people imported
        """
        imported = 0
        
        with self._get_connection(auto_commit=True) as conn:
            for employee in self.person_resolver.employees:
                # Extract employee data
                email = employee.get('email', '')
                if not email:
                    continue
                
                # Create CRMPerson from existing data
                crm_person = CRMPerson(
                    email=email,
                    name=employee.get('slack_name', '') or employee.get('email', '').split('@')[0],
                    slack_id=employee.get('slack_id', ''),
                    role=employee.get('slack_title', ''),
                    first_seen=datetime.fromisoformat(employee['last_seen']) if employee.get('last_seen') else None,
                    tags=['imported_from_resolver']
                )
                
                # Save to database
                if self._save_person(conn, crm_person, author="enrich_from_resolver"):
                    imported += 1
                    
        logger.info(f"Enriched CRM with {imported} people from PersonResolver")
        return imported
    
    def _save_person(self, conn: sqlite3.Connection, person: CRMPerson, author: str = "system") -> bool:
        """Save person to database with audit trail"""
        try:
            # Check if person exists
            existing = conn.execute(
                "SELECT email, updated_at FROM people WHERE email = ?", 
                (person.email,)
            ).fetchone()
            
            # Prepare data for insertion (28 values for 28 columns after email)
            data = (
                person.email, person.name, person.slack_id, person.company, person.role,
                person.department, person.phone, person.location, person.timezone,
                person.linkedin, person.twitter, person.github, person.website, person.background,
                safe_json_dumps(person.interests), safe_json_dumps(person.expertise),
                person.reports_to, safe_json_dumps(person.team_members), 
                safe_json_dumps(person.key_relationships),
                person.preferred_channel, person.response_time, person.meeting_preference,
                safe_json_dumps(person.important_dates), safe_json_dumps(person.tags),
                person.first_seen.isoformat() if person.first_seen else None,
                person.last_interaction.isoformat() if person.last_interaction else None,
                person.interaction_count,
                person.created_at.isoformat(), person.updated_at.isoformat()
            )
            
            if existing:
                # Update existing person (exclude email and created_at from update)
                update_data = (
                    person.name, person.slack_id, person.company, person.role,
                    person.department, person.phone, person.location, person.timezone,
                    person.linkedin, person.twitter, person.github, person.website, person.background,
                    safe_json_dumps(person.interests), safe_json_dumps(person.expertise),
                    person.reports_to, safe_json_dumps(person.team_members), 
                    safe_json_dumps(person.key_relationships),
                    person.preferred_channel, person.response_time, person.meeting_preference,
                    safe_json_dumps(person.important_dates), safe_json_dumps(person.tags),
                    person.first_seen.isoformat() if person.first_seen else None,
                    person.last_interaction.isoformat() if person.last_interaction else None,
                    person.interaction_count,
                    person.updated_at.isoformat(),
                    person.email  # WHERE clause
                )
                
                conn.execute("""
                    UPDATE people SET 
                    name=?, slack_id=?, company=?, role=?, department=?, phone=?, location=?, timezone=?,
                    linkedin=?, twitter=?, github=?, website=?, background=?, interests=?, expertise=?,
                    reports_to=?, team_members=?, key_relationships=?, preferred_channel=?, 
                    response_time=?, meeting_preference=?, important_dates=?, tags=?,
                    first_seen=?, last_interaction=?, interaction_count=?, updated_at=?
                    WHERE email=?
                """, update_data)
                
                self._log_audit(conn, "people", person.email, "update", author)
            else:
                # Insert new person (29 values total)
                conn.execute("""
                    INSERT INTO people (
                        email, name, slack_id, company, role, department, phone, location, timezone,
                        linkedin, twitter, github, website, background, interests, expertise,
                        reports_to, team_members, key_relationships, preferred_channel, 
                        response_time, meeting_preference, important_dates, tags,
                        first_seen, last_interaction, interaction_count, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, data)
                
                self._log_audit(conn, "people", person.email, "create", author)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to save person {person.email}: {e}")
            return False
    
    def add_or_update_person(self, person: CRMPerson, author: str = "system") -> str:
        """Add or update person in CRM directory"""
        with self._get_connection(auto_commit=True) as conn:
            if self._save_person(conn, person, author):
                return person.email
            else:
                raise ValueError(f"Failed to save person: {person.email}")
    
    def get_person_by_email(self, email: str, include_archived: bool = True) -> Optional[CRMPerson]:
        """Retrieve person by email"""
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM people WHERE email = ?", (email,)).fetchone()
            
            if not row:
                return None
            
            # Convert row to CRMPerson
            data = dict(row)
            
            # Parse JSON fields
            for field in ['interests', 'expertise', 'team_members', 'key_relationships', 
                         'important_dates', 'tags']:
                default_value = {} if field == 'key_relationships' else []
                data[field] = safe_json_loads(data[field], default_value)
            
            # Parse datetime fields
            for field in ['first_seen', 'last_interaction', 'created_at', 'updated_at']:
                if data[field]:
                    data[field] = datetime.fromisoformat(data[field])
            
            return CRMPerson.from_dict(data)
    
    def search_people(self, query: str) -> List[CRMPerson]:
        """Search people by name, email, role, or company"""
        with self._get_connection() as conn:
            # Full-text search across relevant fields - use parameterized query to prevent SQL injection
            search_pattern = f"%{query.lower()}%"
            
            rows = conn.execute("""
                SELECT * FROM people 
                WHERE LOWER(name) LIKE ? 
                   OR LOWER(email) LIKE ? 
                   OR LOWER(role) LIKE ? 
                   OR LOWER(company) LIKE ?
                   OR LOWER(department) LIKE ?
                ORDER BY name
            """, (search_pattern, search_pattern, search_pattern, search_pattern, search_pattern)).fetchall()
            
            people = []
            for row in rows:
                data = dict(row)
                
                # Parse JSON and datetime fields (same as get_person_by_email)
                for field in ['interests', 'expertise', 'team_members', 'key_relationships', 
                             'important_dates', 'tags']:
                    if data[field]:
                        data[field] = json.loads(data[field])
                    else:
                        data[field] = [] if field != 'key_relationships' else {}
                
                for field in ['first_seen', 'last_interaction', 'created_at', 'updated_at']:
                    if data[field]:
                        data[field] = datetime.fromisoformat(data[field])
                
                people.append(CRMPerson.from_dict(data))
            
            return people
    
    def count_people(self) -> int:
        """Get total count of people in CRM"""
        with self._get_connection() as conn:
            result = conn.execute("SELECT COUNT(*) FROM people").fetchone()
            return result[0]
    
    def add_note(self, email: str, note: Note) -> bool:
        """Add note to person's profile"""
        note.person_email = email
        
        with self._get_connection(auto_commit=True) as conn:
            # Verify person exists
            if not conn.execute("SELECT email FROM people WHERE email = ?", (email,)).fetchone():
                return False
            
            # Insert note
            conn.execute("""
                INSERT INTO notes (id, person_email, timestamp, author, content, source, tags, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                note.id, note.person_email, note.timestamp.isoformat(), 
                note.author, note.content, note.source,
                json.dumps(note.tags), json.dumps(note.metadata)
            ))
            
            self._log_audit(conn, "notes", note.id, "create", note.author)
            return True
    
    def get_person_notes(self, email: str, limit: int = 50) -> List[Note]:
        """Get notes for a person"""
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM notes 
                WHERE person_email = ? 
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (email, limit)).fetchall()
            
            notes = []
            for row in rows:
                data = dict(row)
                data['timestamp'] = datetime.fromisoformat(data['timestamp'])
                data['tags'] = json.loads(data['tags']) if data['tags'] else []
                data['metadata'] = json.loads(data['metadata']) if data['metadata'] else {}
                notes.append(Note.from_dict(data))
            
            return notes
    
    def add_action_item(self, action: ActionItem) -> bool:
        """Add action item"""
        with self._get_connection(auto_commit=True) as conn:
            data = action.to_dict()
            
            conn.execute("""
                INSERT INTO action_items (
                    id, direction, counterparty, description, due_date, status, priority,
                    source, context, created_at, completed_at, last_reminded, confidence,
                    extraction_method, reminder_dates, follow_up_required, tags, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data['id'], data['direction'], data['counterparty'], data['description'],
                data['due_date'], data['status'], data['priority'], data['source'],
                data['context'], data['created_at'], data['completed_at'], data['last_reminded'],
                data['confidence'], data['extraction_method'], 
                json.dumps(data['reminder_dates']), data['follow_up_required'],
                json.dumps(data['tags']), json.dumps(data['metadata'])
            ))
            
            self._log_audit(conn, "action_items", action.id, "create", "system")
            return True
    
    def store_interaction(self, interaction: 'Interaction') -> bool:
        """Store interaction in CRM database"""
        try:
            with self._get_connection(auto_commit=True) as conn:
                # Convert interaction to database format
                conn.execute("""
                    INSERT INTO interactions (
                        id, person_email, timestamp, interaction_type, summary, content,
                        source, source_id, reference, channel, participants, duration_minutes,
                        key_topics, sentiment_score, follow_up_required, parent_interaction_id,
                        thread_id, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    interaction.id, interaction.person_email, interaction.timestamp.isoformat(),
                    interaction.interaction_type.value, interaction.summary, interaction.content,
                    interaction.source, interaction.source_id, interaction.reference,
                    interaction.channel, json.dumps(interaction.participants),
                    interaction.duration_minutes, json.dumps(interaction.key_topics),
                    interaction.sentiment_score, interaction.follow_up_required,
                    interaction.parent_interaction_id, interaction.thread_id,
                    json.dumps(interaction.metadata) if interaction.metadata else None
                ))
                
                self._log_audit(conn, "interactions", interaction.id, "create", "interaction_manager")
                return True
                
        except Exception as e:
            logger.error(f"Failed to store interaction {interaction.id}: {e}")
            return False
    
    def get_person_interactions(self, email: str, limit: int = 50) -> List['Interaction']:
        """Get interactions for a person from CRM database"""
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM interactions 
                WHERE person_email = ? 
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (email, limit)).fetchall()
            
            interactions = []
            for row in rows:
                data = dict(row)
                
                # Parse JSON fields
                data['participants'] = json.loads(data['participants']) if data['participants'] else []
                data['key_topics'] = json.loads(data['key_topics']) if data['key_topics'] else []
                data['metadata'] = json.loads(data['metadata']) if data['metadata'] else {}
                
                # Parse datetime
                data['timestamp'] = datetime.fromisoformat(data['timestamp'])
                
                # Convert to Interaction object
                from .models import Interaction, InteractionType
                interaction = Interaction(
                    id=data['id'],
                    person_email=data['person_email'],
                    timestamp=data['timestamp'],
                    interaction_type=InteractionType(data['interaction_type']),
                    summary=data['summary'],
                    content=data['content'] or '',
                    source=data['source'],
                    source_id=data['source_id'] or '',
                    reference=data['reference'] or '',
                    channel=data['channel'] or '',
                    participants=data['participants'],
                    duration_minutes=data['duration_minutes'],
                    key_topics=data['key_topics'],
                    sentiment_score=data['sentiment_score'],
                    follow_up_required=bool(data['follow_up_required']) if data['follow_up_required'] is not None else False,
                    parent_interaction_id=data['parent_interaction_id'],
                    thread_id=data['thread_id'],
                    metadata=data['metadata']
                )
                interactions.append(interaction)
            
            return interactions
    
    def get_actions_i_owe(self, status: Optional[ActionStatus] = None) -> List[ActionItem]:
        """Get all actions I owe to others"""
        return self._get_actions(ActionDirection.I_OWE, status=status)
    
    def get_actions_they_owe_me(self, counterparty: Optional[str] = None, status: Optional[ActionStatus] = None) -> List[ActionItem]:
        """Get all actions others owe to me"""
        return self._get_actions(ActionDirection.THEY_OWE, counterparty=counterparty, status=status)
    
    def get_actions_i_owe_person(self, counterparty: str, status: Optional[ActionStatus] = None) -> List[ActionItem]:
        """Get all actions I owe to a specific person"""
        return self._get_actions(ActionDirection.I_OWE, counterparty=counterparty, status=status)
    
    def _get_actions(self, direction: ActionDirection, counterparty: Optional[str] = None, 
                    status: Optional[ActionStatus] = None) -> List[ActionItem]:
        """Internal method to get actions with filters"""
        with self._get_connection() as conn:
            query = "SELECT * FROM action_items WHERE direction = ?"
            params = [direction.value]
            
            if counterparty:
                query += " AND counterparty = ?"
                params.append(counterparty)
            
            if status:
                query += " AND status = ?"
                params.append(status.value)
            
            query += " ORDER BY created_at DESC"
            
            rows = conn.execute(query, params).fetchall()
            
            actions = []
            for row in rows:
                data = dict(row)
                
                # Parse JSON fields
                data['reminder_dates'] = json.loads(data['reminder_dates']) if data['reminder_dates'] else []
                data['tags'] = json.loads(data['tags']) if data['tags'] else []
                data['metadata'] = json.loads(data['metadata']) if data['metadata'] else {}
                
                actions.append(ActionItem.from_dict(data))
            
            return actions
    
    def get_audit_trail(self, record_id: str, table_name: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """Get audit trail for a record"""
        with self._get_connection() as conn:
            if table_name:
                query = "SELECT * FROM audit_trail WHERE table_name = ? AND record_id = ? ORDER BY timestamp DESC LIMIT ?"
                params = (table_name, record_id, limit)
            else:
                query = "SELECT * FROM audit_trail WHERE record_id = ? ORDER BY timestamp DESC LIMIT ?"
                params = (record_id, limit)
            
            rows = conn.execute(query, params).fetchall()
            
            return [dict(row) for row in rows]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get CRM statistics"""
        with self._get_connection() as conn:
            stats = {}
            
            # People stats
            stats['total_people'] = conn.execute("SELECT COUNT(*) FROM people").fetchone()[0]
            stats['people_with_notes'] = conn.execute("SELECT COUNT(DISTINCT person_email) FROM notes").fetchone()[0]
            stats['people_with_actions'] = conn.execute("SELECT COUNT(DISTINCT counterparty) FROM action_items").fetchone()[0]
            
            # Action stats
            stats['total_actions'] = conn.execute("SELECT COUNT(*) FROM action_items").fetchone()[0]
            stats['actions_i_owe'] = conn.execute("SELECT COUNT(*) FROM action_items WHERE direction = 'i_owe'").fetchone()[0]
            stats['actions_they_owe'] = conn.execute("SELECT COUNT(*) FROM action_items WHERE direction = 'they_owe'").fetchone()[0]
            stats['overdue_actions'] = conn.execute(
                "SELECT COUNT(*) FROM action_items WHERE due_date < ? AND status NOT IN ('completed', 'cancelled')", 
                (datetime.now().isoformat(),)
            ).fetchone()[0]
            
            # Note stats
            stats['total_notes'] = conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
            
            # Interaction stats
            stats['total_interactions'] = conn.execute("SELECT COUNT(*) FROM interactions").fetchone()[0]
            
            # Relationship stats
            stats['total_relationships'] = conn.execute("SELECT COUNT(*) FROM relationships").fetchone()[0]
            
            return stats