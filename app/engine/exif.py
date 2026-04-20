"""EXIF DateTimeOriginal extraction with graceful fallbacks."""

from __future__ import annotations

import datetime as _dt
import os
from pathlib import Path
from typing import Optional

try:
    from PIL import Image, ExifTags  # type: ignore

    _DATETIME_ORIGINAL_TAG = next(
        (k for k, v in ExifTags.TAGS.items() if v == "DateTimeOriginal"),
        36867,
    )
    _PIL_AVAILABLE = True
except Exception:  # pragma: no cover
    _PIL_AVAILABLE = False
    _DATETIME_ORIGINAL_TAG = 36867

try:
    import exifread  # type: ignore

    _EXIFREAD_AVAILABLE = True
except Exception:  # pragma: no cover
    _EXIFREAD_AVAILABLE = False


_RAW_EXTENSIONS = {".raw", ".cr2", ".nef", ".arw"}


def _parse_exif_string(raw: str) -> Optional[_dt.datetime]:
    raw = raw.strip()
    for fmt in ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y:%m:%d %H:%M"):
        try:
            return _dt.datetime.strptime(raw, fmt)
        except ValueError:
            continue
    return None


def _from_pillow(path: Path) -> Optional[_dt.datetime]:
    if not _PIL_AVAILABLE:
        return None
    try:
        with Image.open(path) as img:
            exif = img.getexif()
            if not exif:
                return None
            value = exif.get(_DATETIME_ORIGINAL_TAG)
            if value is None:
                ifd = exif.get_ifd(0x8769) if hasattr(exif, "get_ifd") else None
                if ifd:
                    value = ifd.get(_DATETIME_ORIGINAL_TAG)
            if isinstance(value, bytes):
                value = value.decode("utf-8", "ignore")
            if isinstance(value, str):
                return _parse_exif_string(value)
    except Exception:
        return None
    return None


def _from_exifread(path: Path) -> Optional[_dt.datetime]:
    if not _EXIFREAD_AVAILABLE:
        return None
    try:
        with open(path, "rb") as f:
            tags = exifread.process_file(f, stop_tag="EXIF DateTimeOriginal", details=False)
        tag = tags.get("EXIF DateTimeOriginal") or tags.get("Image DateTime")
        if tag is None:
            return None
        return _parse_exif_string(str(tag))
    except Exception:
        return None


def _from_mtime(path: Path) -> _dt.datetime:
    return _dt.datetime.fromtimestamp(path.stat().st_mtime)


def extract_timestamp(path: Path) -> _dt.datetime:
    """Best-effort capture datetime extraction.

    Order: Pillow EXIF → exifread (for RAW) → filesystem mtime.
    Always returns a datetime (never None); callers format it.
    """
    ext = path.suffix.lower()
    stamp: Optional[_dt.datetime] = None

    if ext in _RAW_EXTENSIONS:
        stamp = _from_exifread(path) or _from_pillow(path)
    else:
        stamp = _from_pillow(path) or _from_exifread(path)

    if stamp is None:
        stamp = _from_mtime(path)
    return stamp


def format_timestamp(stamp: _dt.datetime) -> str:
    return stamp.strftime("%Y%m%d_%H%M%S")
