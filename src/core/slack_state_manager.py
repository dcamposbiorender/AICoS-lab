#!/usr/bin/env python3
"""
Slack State Manager - Phase 5C Incremental State Management
Manages incremental processing state for Slack timeline correlation and intelligence.
Handles cursor management, processing checkpoints, and performance optimization.
"""

import json
import sqlite3
import hashlib
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class SlackProcessingCursor:
    """Tracks processing progress for Slack channels"""
    channel_id: str
    channel_name: str
    last_message_timestamp: float
    last_processed_at: datetime
    messages_processed: int
    correlation_attempts: int
    successful_correlations: int
    processing_state: str  # 'active', 'paused', 'complete', 'error'
    error_count: int
    last_error: Optional[str]
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['last_processed_at'] = self.last_processed_at.isoformat()
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SlackProcessingCursor':
        data = data.copy()
        data['last_processed_at'] = datetime.fromisoformat(data['last_processed_at'])
        return cls(**data)


@dataclass
class CorrelationCheckpoint:
    """Checkpoint for meeting correlation processing"""
    checkpoint_id: str
    meeting_id: str
    correlation_stage: str  # 'slack_analysis', 'timeline_extraction', 'participant_mapping', 'complete'
    channels_analyzed: Set[str]
    slack_contexts_found: int
    scheduling_messages_found: int
    participant_mappings: int
    processing_time_ms: float
    created_at: datetime
    completed_at: Optional[datetime]
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['channels_analyzed'] = list(self.channels_analyzed)
        result['created_at'] = self.created_at.isoformat()
        result['completed_at'] = self.completed_at.isoformat() if self.completed_at else None
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CorrelationCheckpoint':
        data = data.copy()
        data['channels_analyzed'] = set(data['channels_analyzed'])
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        if data['completed_at']:
            data['completed_at'] = datetime.fromisoformat(data['completed_at'])
        return cls(**data)


class SlackStateManager:
    """
    Manages incremental processing state for Slack intelligence operations
    Optimizes performance for large Slack datasets and timeline correlation
    """
    
    def __init__(self, base_path: Path):
        self.base_path = Path(base_path)
        self.db_path = self.base_path / "data" / "state" / "slack_processing.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        
        # Performance settings
        self.batch_size = 1000  # Process messages in batches
        self.checkpoint_interval_seconds = 300  # Checkpoint every 5 minutes
        self.max_processing_time_hours = 12  # Maximum processing time before timeout
        self.correlation_cache_size = 10000  # Cache recent correlations
        
        # Initialize database
        self._init_database()
        
        # In-memory caches for performance
        self.channel_cursors_cache = {}
        self.correlation_cache = {}
        self.participant_mapping_cache = {}
        
        print(f"📊 Slack State Manager initialized")
        print(f"💾 Database: {self.db_path}")
    
    def _init_database(self):
        """Initialize SQLite database for state management"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS slack_processing_cursors (
                    channel_id TEXT PRIMARY KEY,
                    channel_name TEXT,
                    last_message_timestamp REAL,
                    last_processed_at TEXT,
                    messages_processed INTEGER,
                    correlation_attempts INTEGER,
                    successful_correlations INTEGER,
                    processing_state TEXT,
                    error_count INTEGER,
                    last_error TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS correlation_checkpoints (
                    checkpoint_id TEXT PRIMARY KEY,
                    meeting_id TEXT,
                    correlation_stage TEXT,
                    channels_analyzed TEXT,  -- JSON array
                    slack_contexts_found INTEGER,
                    scheduling_messages_found INTEGER,
                    participant_mappings INTEGER,
                    processing_time_ms REAL,
                    created_at TEXT,
                    completed_at TEXT,
                    checkpoint_data TEXT  -- JSON blob for additional data
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS processing_metrics (
                    metric_date TEXT PRIMARY KEY,
                    channels_processed INTEGER,
                    messages_analyzed INTEGER,
                    correlations_created INTEGER,
                    average_processing_time_ms REAL,
                    peak_memory_mb REAL,
                    error_rate REAL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes for performance
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_cursors_state 
                ON slack_processing_cursors(processing_state)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_checkpoints_meeting 
                ON correlation_checkpoints(meeting_id)
            """)
            
            conn.commit()
    
    def get_channel_cursor(self, channel_id: str) -> Optional[SlackProcessingCursor]:
        """Get processing cursor for a channel"""
        # Check cache first
        if channel_id in self.channel_cursors_cache:
            return self.channel_cursors_cache[channel_id]
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM slack_processing_cursors WHERE channel_id = ?
            """, (channel_id,))
            
            row = cursor.fetchone()
            if row:
                # Convert row to cursor object
                cursor_data = {
                    'channel_id': row[0],
                    'channel_name': row[1],
                    'last_message_timestamp': row[2],
                    'last_processed_at': row[3],
                    'messages_processed': row[4],
                    'correlation_attempts': row[5],
                    'successful_correlations': row[6],
                    'processing_state': row[7],
                    'error_count': row[8],
                    'last_error': row[9]
                }
                
                cursor_obj = SlackProcessingCursor.from_dict(cursor_data)
                self.channel_cursors_cache[channel_id] = cursor_obj
                return cursor_obj
        
        return None
    
    def update_channel_cursor(self, cursor: SlackProcessingCursor):
        """Update processing cursor for a channel"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO slack_processing_cursors 
                (channel_id, channel_name, last_message_timestamp, last_processed_at,
                 messages_processed, correlation_attempts, successful_correlations,
                 processing_state, error_count, last_error, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                cursor.channel_id,
                cursor.channel_name,
                cursor.last_message_timestamp,
                cursor.last_processed_at.isoformat(),
                cursor.messages_processed,
                cursor.correlation_attempts,
                cursor.successful_correlations,
                cursor.processing_state,
                cursor.error_count,
                cursor.last_error,
                datetime.now(timezone.utc).isoformat()
            ))
            conn.commit()
        
        # Update cache
        self.channel_cursors_cache[cursor.channel_id] = cursor
    
    def create_correlation_checkpoint(self, 
                                    meeting_id: str,
                                    stage: str,
                                    channels_analyzed: Set[str],
                                    processing_stats: Dict[str, Any]) -> str:
        """Create a checkpoint during correlation processing"""
        checkpoint_id = f"{meeting_id}_{stage}_{int(datetime.now(timezone.utc).timestamp())}"
        
        checkpoint = CorrelationCheckpoint(
            checkpoint_id=checkpoint_id,
            meeting_id=meeting_id,
            correlation_stage=stage,
            channels_analyzed=channels_analyzed,
            slack_contexts_found=processing_stats.get('slack_contexts', 0),
            scheduling_messages_found=processing_stats.get('scheduling_messages', 0),
            participant_mappings=processing_stats.get('participant_mappings', 0),
            processing_time_ms=processing_stats.get('processing_time_ms', 0.0),
            created_at=datetime.now(timezone.utc),
            completed_at=None
        )
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO correlation_checkpoints
                (checkpoint_id, meeting_id, correlation_stage, channels_analyzed,
                 slack_contexts_found, scheduling_messages_found, participant_mappings,
                 processing_time_ms, created_at, completed_at, checkpoint_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                checkpoint.checkpoint_id,
                checkpoint.meeting_id,
                checkpoint.correlation_stage,
                json.dumps(list(checkpoint.channels_analyzed)),
                checkpoint.slack_contexts_found,
                checkpoint.scheduling_messages_found,
                checkpoint.participant_mappings,
                checkpoint.processing_time_ms,
                checkpoint.created_at.isoformat(),
                None,
                json.dumps(processing_stats)
            ))
            conn.commit()
        
        return checkpoint_id
    
    def complete_correlation_checkpoint(self, checkpoint_id: str):
        """Mark a correlation checkpoint as complete"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE correlation_checkpoints 
                SET completed_at = ?, updated_at = ?
                WHERE checkpoint_id = ?
            """, (
                datetime.now(timezone.utc).isoformat(),
                datetime.now(timezone.utc).isoformat(),
                checkpoint_id
            ))
            conn.commit()
    
    def get_processing_candidates(self, 
                                max_channels: int = 100,
                                prioritize_errors: bool = True) -> List[SlackProcessingCursor]:
        """Get channels that need processing, ordered by priority"""
        with sqlite3.connect(self.db_path) as conn:
            # Build query based on prioritization
            if prioritize_errors:
                query = """
                    SELECT * FROM slack_processing_cursors
                    WHERE processing_state IN ('error', 'paused', 'active')
                    ORDER BY 
                        CASE processing_state 
                            WHEN 'error' THEN 1 
                            WHEN 'paused' THEN 2 
                            WHEN 'active' THEN 3 
                        END,
                        last_processed_at ASC
                    LIMIT ?
                """
            else:
                query = """
                    SELECT * FROM slack_processing_cursors
                    WHERE processing_state != 'complete'
                    ORDER BY messages_processed DESC, last_processed_at ASC
                    LIMIT ?
                """
            
            cursor = conn.execute(query, (max_channels,))
            rows = cursor.fetchall()
            
            candidates = []
            for row in rows:
                cursor_data = {
                    'channel_id': row[0],
                    'channel_name': row[1],
                    'last_message_timestamp': row[2],
                    'last_processed_at': row[3],
                    'messages_processed': row[4],
                    'correlation_attempts': row[5],
                    'successful_correlations': row[6],
                    'processing_state': row[7],
                    'error_count': row[8],
                    'last_error': row[9]
                }
                candidates.append(SlackProcessingCursor.from_dict(cursor_data))
        
        return candidates
    
    def get_incremental_messages(self, 
                               channel_id: str, 
                               messages: List[Dict[str, Any]],
                               force_full_processing: bool = False) -> List[Dict[str, Any]]:
        """Get messages that need processing for a channel"""
        if force_full_processing:
            return messages
        
        cursor = self.get_channel_cursor(channel_id)
        if not cursor:
            # No cursor exists, process all messages
            return messages
        
        # Filter to messages newer than last processed timestamp
        incremental_messages = []
        for msg in messages:
            msg_timestamp = float(msg.get('ts', 0))
            if msg_timestamp > cursor.last_message_timestamp:
                incremental_messages.append(msg)
        
        return incremental_messages
    
    def calculate_processing_priority(self, cursor: SlackProcessingCursor) -> float:
        """Calculate processing priority score for a channel"""
        score = 0.0
        
        # Higher score for channels with errors (need attention)
        if cursor.processing_state == 'error':
            score += 100.0
        elif cursor.processing_state == 'paused':
            score += 50.0
        
        # Higher score for channels with more messages to process
        score += min(cursor.messages_processed / 1000, 10.0)
        
        # Higher score for channels with successful correlations
        if cursor.correlation_attempts > 0:
            success_rate = cursor.successful_correlations / cursor.correlation_attempts
            score += success_rate * 20.0
        
        # Lower score for recently processed channels
        hours_since_processed = (datetime.now(timezone.utc) - cursor.last_processed_at).total_seconds() / 3600
        if hours_since_processed < 1:
            score *= 0.1  # Heavily penalize recently processed
        elif hours_since_processed < 24:
            score *= 0.5  # Moderately penalize recent processing
        
        return score
    
    def batch_process_messages(self,
                             channel_id: str,
                             messages: List[Dict[str, Any]],
                             processor_func,
                             checkpoint_callback=None) -> Dict[str, Any]:
        """Process messages in batches with checkpointing"""
        cursor = self.get_channel_cursor(channel_id)
        if not cursor:
            # Create initial cursor
            cursor = SlackProcessingCursor(
                channel_id=channel_id,
                channel_name=f"channel_{channel_id}",
                last_message_timestamp=0.0,
                last_processed_at=datetime.now(timezone.utc) - timedelta(days=1),
                messages_processed=0,
                correlation_attempts=0,
                successful_correlations=0,
                processing_state='active',
                error_count=0,
                last_error=None
            )
        
        # Get incremental messages
        incremental_messages = self.get_incremental_messages(channel_id, messages)
        
        if not incremental_messages:
            print(f"📊 Channel {channel_id}: No new messages to process")
            return {'processed': 0, 'correlations': 0}
        
        print(f"📊 Processing {len(incremental_messages)} messages for {channel_id}")
        
        # Process in batches
        total_processed = 0
        total_correlations = 0
        last_checkpoint_time = datetime.now(timezone.utc)
        
        cursor.processing_state = 'active'
        
        for i in range(0, len(incremental_messages), self.batch_size):
            batch = incremental_messages[i:i + self.batch_size]
            
            try:
                # Process batch
                batch_results = processor_func(batch)
                
                # Update cursor
                cursor.messages_processed += len(batch)
                cursor.correlation_attempts += batch_results.get('correlation_attempts', 0)
                cursor.successful_correlations += batch_results.get('successful_correlations', 0)
                
                if batch:
                    cursor.last_message_timestamp = max(
                        cursor.last_message_timestamp,
                        max(float(msg.get('ts', 0)) for msg in batch)
                    )
                
                total_processed += len(batch)
                total_correlations += batch_results.get('successful_correlations', 0)
                
                # Checkpoint if needed
                now = datetime.now(timezone.utc)
                if (now - last_checkpoint_time).total_seconds() > self.checkpoint_interval_seconds:
                    cursor.last_processed_at = now
                    cursor.processing_state = 'active'
                    self.update_channel_cursor(cursor)
                    
                    if checkpoint_callback:
                        checkpoint_callback(cursor, batch_results)
                    
                    last_checkpoint_time = now
                    print(f"    ✓ Checkpoint: {total_processed}/{len(incremental_messages)} messages")
                
            except Exception as e:
                cursor.error_count += 1
                cursor.last_error = str(e)
                cursor.processing_state = 'error'
                print(f"    ❌ Error processing batch: {e}")
                logger.error(f"Batch processing error for {channel_id}: {e}")
                break
        
        # Final cursor update
        cursor.last_processed_at = datetime.now(timezone.utc)
        if cursor.processing_state != 'error':
            cursor.processing_state = 'complete' if total_processed == len(incremental_messages) else 'paused'
        
        self.update_channel_cursor(cursor)
        
        return {
            'processed': total_processed,
            'correlations': total_correlations,
            'cursor_state': cursor.processing_state
        }
    
    def get_processing_statistics(self) -> Dict[str, Any]:
        """Get overall processing statistics"""
        with sqlite3.connect(self.db_path) as conn:
            # Channel statistics
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total_channels,
                    SUM(CASE WHEN processing_state = 'complete' THEN 1 ELSE 0 END) as completed_channels,
                    SUM(CASE WHEN processing_state = 'error' THEN 1 ELSE 0 END) as error_channels,
                    SUM(CASE WHEN processing_state = 'active' THEN 1 ELSE 0 END) as active_channels,
                    SUM(messages_processed) as total_messages,
                    SUM(correlation_attempts) as total_correlation_attempts,
                    SUM(successful_correlations) as total_successful_correlations,
                    AVG(CAST(successful_correlations AS FLOAT) / NULLIF(correlation_attempts, 0)) as avg_success_rate
                FROM slack_processing_cursors
            """)
            
            channel_stats = cursor.fetchone()
            
            # Checkpoint statistics  
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total_checkpoints,
                    COUNT(CASE WHEN completed_at IS NOT NULL THEN 1 END) as completed_checkpoints,
                    AVG(processing_time_ms) as avg_processing_time_ms,
                    MAX(processing_time_ms) as max_processing_time_ms
                FROM correlation_checkpoints
            """)
            
            checkpoint_stats = cursor.fetchone()
        
        return {
            'channel_statistics': {
                'total_channels': channel_stats[0] or 0,
                'completed_channels': channel_stats[1] or 0,
                'error_channels': channel_stats[2] or 0,
                'active_channels': channel_stats[3] or 0,
                'completion_rate': (channel_stats[1] or 0) / max(channel_stats[0] or 1, 1) * 100,
                'total_messages_processed': channel_stats[4] or 0,
                'total_correlation_attempts': channel_stats[5] or 0,
                'successful_correlations': channel_stats[6] or 0,
                'average_success_rate': channel_stats[7] or 0.0
            },
            'checkpoint_statistics': {
                'total_checkpoints': checkpoint_stats[0] or 0,
                'completed_checkpoints': checkpoint_stats[1] or 0,
                'completion_rate': (checkpoint_stats[1] or 0) / max(checkpoint_stats[0] or 1, 1) * 100,
                'average_processing_time_ms': checkpoint_stats[2] or 0.0,
                'max_processing_time_ms': checkpoint_stats[3] or 0.0
            },
            'cache_statistics': {
                'channel_cursors_cached': len(self.channel_cursors_cache),
                'correlation_cache_size': len(self.correlation_cache),
                'participant_mapping_cache_size': len(self.participant_mapping_cache)
            }
        }
    
    def clear_processing_state(self, channel_id: Optional[str] = None):
        """Clear processing state for debugging or reset"""
        if channel_id:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM slack_processing_cursors WHERE channel_id = ?", (channel_id,))
                conn.execute("DELETE FROM correlation_checkpoints WHERE meeting_id LIKE ?", (f"%{channel_id}%",))
                conn.commit()
            
            # Clear from cache
            if channel_id in self.channel_cursors_cache:
                del self.channel_cursors_cache[channel_id]
        else:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM slack_processing_cursors")
                conn.execute("DELETE FROM correlation_checkpoints")
                conn.commit()
            
            # Clear all caches
            self.channel_cursors_cache.clear()
            self.correlation_cache.clear()
            self.participant_mapping_cache.clear()
        
        print(f"🧹 Cleared processing state" + (f" for {channel_id}" if channel_id else " for all channels"))
    
    def optimize_performance(self):
        """Optimize database and cache performance"""
        with sqlite3.connect(self.db_path) as conn:
            # Vacuum database
            conn.execute("VACUUM")
            
            # Update statistics
            conn.execute("ANALYZE")
            
            # Clean up old checkpoints (keep last 1000)
            conn.execute("""
                DELETE FROM correlation_checkpoints 
                WHERE checkpoint_id NOT IN (
                    SELECT checkpoint_id FROM correlation_checkpoints 
                    ORDER BY created_at DESC LIMIT 1000
                )
            """)
            
            conn.commit()
        
        # Clear old cache entries
        if len(self.correlation_cache) > self.correlation_cache_size:
            # Keep most recent entries
            items = list(self.correlation_cache.items())
            items.sort(key=lambda x: x[1].get('timestamp', 0), reverse=True)
            self.correlation_cache = dict(items[:self.correlation_cache_size])
        
        print("⚡ Performance optimization complete")