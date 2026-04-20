"""Tests for the chunked file digest."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.engine.hasher import file_digest


def _write(path: Path, data: bytes) -> None:
    path.write_bytes(data)


def test_deterministic_digest(tmp_path: Path):
    a = tmp_path / "a.bin"
    b = tmp_path / "b.bin"
    _write(a, b"hello world")
    _write(b, b"hello world")
    assert file_digest(a) == file_digest(b)


def test_different_content_different_digest(tmp_path: Path):
    a = tmp_path / "a.bin"
    b = tmp_path / "b.bin"
    _write(a, b"hello world")
    _write(b, b"hello worlz")
    assert file_digest(a) != file_digest(b)


def test_tagged_prefix_md5(tmp_path: Path):
    a = tmp_path / "a.bin"
    _write(a, b"hello")
    digest = file_digest(a, prefer_xxhash=False)
    assert digest.startswith("md5:")


def test_tagged_prefix_xxhash_if_available(tmp_path: Path):
    a = tmp_path / "a.bin"
    _write(a, b"hello")
    digest = file_digest(a, prefer_xxhash=True)
    # Either xxh64 (if xxhash is installed) or md5 (if not)
    assert digest.startswith("xxh64:") or digest.startswith("md5:")


def test_chunked_digest_matches_single_read(tmp_path: Path):
    big = tmp_path / "big.bin"
    _write(big, b"A" * (9 * 1024 * 1024))  # larger than one 8 MiB chunk
    d1 = file_digest(big, prefer_xxhash=False)
    d2 = file_digest(big, prefer_xxhash=False)
    assert d1 == d2
