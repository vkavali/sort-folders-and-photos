"""Application-wide tunables.

Centralized so engine + workers + UI read from a single source of truth.
"""

from __future__ import annotations

import re

HASH_CHUNK_SIZE: int = 8 * 1024 * 1024  # 8 MiB

DUPLICATES_DIR: str = "Duplicates"
UNSORTED_DIR: str = "Unsorted"

MEDIA_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".jpg", ".jpeg", ".png", ".mp4",
        ".raw", ".cr2", ".nef", ".arw",
        ".tif", ".tiff", ".heic", ".mov", ".avi",
    }
)

PROCESSING_MODE_FLATTEN: str = "flatten"
PROCESSING_MODE_GROUP: str = "group"

ACTION_COPY: str = "copy"
ACTION_MOVE: str = "move"

# Folder names that are almost always pass-through containers rather than
# meaningful event categories. Matched case-insensitively against the
# normalized (alphanumeric-only) folder name.
GENERIC_FOLDER_NAMES: frozenset[str] = frozenset(
    {
        "pics", "pic", "pictures", "picture",
        "photos", "photo",
        "images", "image", "img", "imgs",
        "raw", "rawfiles", "raws",
        "jpg", "jpgs", "jpeg", "jpegs",
        "files", "media", "export", "exports",
        "selected", "final", "finals", "edited",
        "new folder", "newfolder",
    }
)

# Matches names containing a 6+ digit run, or Google-Drive-style export
# names like "Marriage-20260111T075732Z-3-001".
_TIMESTAMP_RE = re.compile(r"\d{6,}")


def looks_like_timestamp_name(name: str) -> bool:
    return bool(_TIMESTAMP_RE.search(name))


def is_generic_folder_name(name: str) -> bool:
    normalized = re.sub(r"[^a-z0-9 ]+", " ", name.lower()).strip()
    return normalized in GENERIC_FOLDER_NAMES
