"""Canonical event categories and matching configuration.

Any folder whose best fuzzy score against these categories is below
MATCH_THRESHOLD is automatically routed to UNSORTED.
"""

from __future__ import annotations

CANONICAL_CATEGORIES: list[str] = [
    "Engagement",
    "Haldi",
    "Mehendi",
    "Sangeet",
    "Baraat",
    "Wedding",
    "Reception",
    "Decor",
    "Pre-Wedding",
    "Post-Wedding",
    "Portraits",
    "Candid",
    "Drone",
]

UNSORTED: str = "Unsorted"
DUPLICATES_DIR: str = "Duplicates"

MATCH_THRESHOLD: float = 80.0

MEDIA_EXTENSIONS: frozenset[str] = frozenset(
    {".jpg", ".jpeg", ".png", ".mp4", ".raw", ".cr2", ".nef", ".arw", ".tif", ".tiff"}
)


def all_choices() -> list[str]:
    """All category options the user can pick in the mapping dropdown."""
    return [*CANONICAL_CATEGORIES, UNSORTED]
