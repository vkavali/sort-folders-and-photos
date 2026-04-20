"""Fuzzy folder-name → canonical-category matcher."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable

from rapidfuzz import fuzz, process

from app.categories import (
    CANONICAL_CATEGORIES,
    MATCH_THRESHOLD,
    UNSORTED,
)

_NORMALIZE_RE = re.compile(r"[^a-z0-9]+")


@dataclass
class Mapping:
    parent_folder: str
    suggested_category: str
    confidence: float
    chosen_category: str = ""
    file_count: int = 0

    def __post_init__(self) -> None:
        if not self.chosen_category:
            self.chosen_category = self.suggested_category


def _normalize(name: str) -> str:
    return _NORMALIZE_RE.sub(" ", name.lower()).strip()


def score_folder(folder: str) -> tuple[str, float]:
    """Return (best_category, confidence_0_100) for a folder name."""
    candidate = _normalize(folder)
    if not candidate:
        return UNSORTED, 0.0

    normalized_categories = {_normalize(c): c for c in CANONICAL_CATEGORIES}
    match = process.extractOne(
        candidate,
        list(normalized_categories.keys()),
        scorer=fuzz.token_sort_ratio,
    )
    if match is None:
        return UNSORTED, 0.0
    key, score, _ = match
    if score < MATCH_THRESHOLD:
        return UNSORTED, float(score)
    return normalized_categories[key], float(score)


def suggest_mappings(folder_counts: Iterable[tuple[str, int]]) -> list[Mapping]:
    """Produce one Mapping per unique folder name."""
    seen: dict[str, Mapping] = {}
    for folder, count in folder_counts:
        if folder in seen:
            seen[folder].file_count += count
            continue
        category, confidence = score_folder(folder)
        seen[folder] = Mapping(
            parent_folder=folder,
            suggested_category=category,
            confidence=confidence,
            chosen_category=category,
            file_count=count,
        )
    return sorted(seen.values(), key=lambda m: m.parent_folder.lower())
