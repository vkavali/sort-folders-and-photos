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

## Install (end users — recommended)

Go to the **[Releases](../../releases)** page on GitHub, download the latest
`SemanticFileAggregator-Setup.exe`, double-click it, click Next, click Install.
The app appears in the Start menu and can be uninstalled from Add/Remove
Programs just like any other Windows program. No Python required.

## Publish a new release (maintainer)

Every time you push a git tag starting with `v`, GitHub Actions automatically
builds and publishes a fresh `Setup.exe` to the Releases page.

```
git tag v1.0.0
git push origin v1.0.0
```

Wait ~5 minutes, then refresh the Releases page.

You can also trigger a test build manually: go to the **Actions** tab → *Build
installer* → *Run workflow*. That produces a downloadable installer as a
workflow artifact (no public release created).

## Run from source

```
pip install -r requirements.txt
python -m app.main
```

Requires Python 3.10+.

## Build the installer locally (alternative to GitHub Actions)

On a Windows machine with Python 3.10+ and [Inno Setup 6](https://jrsoftware.org/isdl.php)
installed:

```
build.bat
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
```

Output: `Output\SemanticFileAggregator-Setup.exe`.

## Self-verification

```
python generate_test_data.py        # builds _test_tree/source + destination
python -m pytest tests/ -v          # 15 engine tests
```
