# Semantic File Aggregator

A modern Windows desktop utility that walks a deeply nested media archive and
either **flattens** every file into a single destination or **dynamically
groups** them by clustering similar folder names — no predefined categories.
Files are renamed by EXIF timestamp, deduplicated by cryptographic hash, and
every unique byte is preserved.

See [`SPEC.md`](SPEC.md) for the full design.

## Features

- **Two modes:** *Flatten All* or *Dynamic Grouping* (default).
- **Dynamic clustering** via `rapidfuzz` + union-find single-linkage — handles
  typographical variants like `engagegem et` ↔ `Engagement` with no
  predefined taxonomy.
- **Cryptographic dedup** with MD5 (opportunistically upgraded to xxhash) and
  a byte-size pre-filter so unique-size files never pay the hashing cost.
- **Chronological rename** using EXIF `DateTimeOriginal` (fallback to RAW
  tags, then filesystem mtime) — destination files sort chronologically in
  any file manager.
- **Copy-then-verify-then-delete** transactional safety; source directories
  are never deleted.
- **Responsive GUI:** PyQt6 with a `QThread` host driving a
  `ThreadPoolExecutor` for I/O-bound parallelism. Cancel is graceful —
  in-flight copies finish, remaining files are skipped.
- **Drag-and-drop** folder inputs plus a **merge-clusters** UI (multi-select
  button AND drag-and-drop rows).

## Install

```
pip install -r requirements.txt
```

## Run

```
python -m app.main
```

## Self-verification

```
python generate_test_data.py        # builds _test_tree/source + destination
python -m pytest tests/ -v          # 15 engine tests
```
