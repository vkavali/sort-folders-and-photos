"""Application-wide tunables.

Centralized so engine + workers + UI read from a single source of truth.
No predefined list of categories lives anywhere in the codebase.
"""

from __future__ import annotations

SIMILARITY_THRESHOLD: float = 80.0
SIMILARITY_MIN: float = 50.0
SIMILARITY_MAX: float = 99.0

HASH_CHUNK_SIZE: int = 8 * 1024 * 1024  # 8 MiB

DUPLICATES_DIR: str = "Duplicates"

MEDIA_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".jpg", ".jpeg", ".png", ".mp4",
        ".raw", ".cr2", ".nef", ".arw",
        ".tif", ".tiff", ".heic", ".mov", ".avi",
    }
)

PROCESSING_MODE_FLATTEN: str = "flatten"
PROCESSING_MODE_GROUP: str = "group"
