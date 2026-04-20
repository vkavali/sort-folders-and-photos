"""GUI-agnostic core engine for Semantic File Aggregator."""

from .scanner import MediaItem, scan
from .matcher import Mapping, suggest_mappings
from .exif import extract_timestamp
from .hasher import file_digest
from .planner import PlannedMove, build_plan
from .executor import execute_plan, ExecutionStats

__all__ = [
    "MediaItem",
    "scan",
    "Mapping",
    "suggest_mappings",
    "extract_timestamp",
    "file_digest",
    "PlannedMove",
    "build_plan",
    "execute_plan",
    "ExecutionStats",
]
