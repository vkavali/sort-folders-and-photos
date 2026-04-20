"""Chunked cryptographic digest with opportunistic xxhash upgrade."""

from __future__ import annotations

import hashlib
from pathlib import Path

from app.config import HASH_CHUNK_SIZE

try:
    import xxhash  # type: ignore

    _XXHASH_AVAILABLE = True
except Exception:  # pragma: no cover
    _XXHASH_AVAILABLE = False


def _new_hasher(prefer_xxhash: bool):
    if prefer_xxhash and _XXHASH_AVAILABLE:
        return xxhash.xxh64(), "xxh64"
    return hashlib.md5(), "md5"


def file_digest(path: Path, *, prefer_xxhash: bool = True) -> str:
    """Return a tagged hex digest ("xxh64:…" / "md5:…") for the file's bytes."""
    hasher, tag = _new_hasher(prefer_xxhash)
    with open(path, "rb") as f:
        while True:
            chunk = f.read(HASH_CHUNK_SIZE)
            if not chunk:
                break
            hasher.update(chunk)
    return f"{tag}:{hasher.hexdigest()}"
