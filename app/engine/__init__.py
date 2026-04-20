"""GUI-agnostic core engine for Semantic File Aggregator."""

from .scanner import MediaItem, scan
from .clusterer import Cluster, cluster_folders, recluster
from .exif import extract_timestamp, format_timestamp
from .hasher import file_digest
from .planner import PlannedMove, build_plan
from .executor import execute_plan, ExecutionStats

__all__ = [
    "MediaItem",
    "scan",
    "Cluster",
    "cluster_folders",
    "recluster",
    "extract_timestamp",
    "format_timestamp",
    "file_digest",
    "PlannedMove",
    "build_plan",
    "execute_plan",
    "ExecutionStats",
]
