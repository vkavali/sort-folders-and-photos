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

## Run from source

```
pip install -r requirements.txt
python -m app.main
```

Requires Python 3.10+.

## Install as a desktop app

Bundle into a standalone, double-clickable app with PyInstaller. No Python
install required on the target machine afterwards.

**Windows:**

```
build.bat
```

Output: `dist\SemanticFileAggregator\SemanticFileAggregator.exe`. Pin it to
Start / Taskbar, or drop a shortcut into `shell:programs` to make it appear
in the Start menu.

**macOS / Linux:**

```
./build.sh
```

macOS output: `dist/SemanticFileAggregator.app` — drag to `/Applications`.
Linux output: `dist/SemanticFileAggregator/SemanticFileAggregator` — install
under `~/.local/opt/` and drop a `.desktop` file in
`~/.local/share/applications/` for menu integration.

Under the hood both scripts run `pyinstaller --noconfirm
SemanticFileAggregator.spec`. The spec file bundles all `app` submodules and
produces a windowed (no-console) desktop app.

## Self-verification

```
python generate_test_data.py        # builds _test_tree/source + destination
python -m pytest tests/ -v          # 15 engine tests
```
