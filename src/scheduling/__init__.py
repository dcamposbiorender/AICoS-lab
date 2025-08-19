"""
Calendar Module - Deterministic Calendar Coordination
CRITICAL: All datetime operations are timezone-aware using pytz
"""

from .availability import AvailabilityEngine, FreeSlot
from .conflicts import ConflictDetector

__all__ = ['AvailabilityEngine', 'FreeSlot', 'ConflictDetector']