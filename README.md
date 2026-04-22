# Semantic File Aggregator

A local-only Windows desktop utility that takes a deeply nested media
archive (wedding shoots, phone backups, old SD cards) and flattens it into
a tidy destination — or sorts it into categories you pick from the folder
names themselves. Files are renamed by EXIF timestamp, duplicates are
isolated with cryptographic hashing, and every unique byte is preserved.

Licensed under the [MIT License](LICENSE). See [`SPEC.md`](SPEC.md) for the
full design and [`SECURITY.md`](SECURITY.md) for the trust model.

## Install (end users)

1. Open the repo's **[Releases](../../releases)** page.
2. Download **`SemanticFileAggregator-Setup.exe`**.
3. Double-click it, click Next, click Install.
4. The app appears in your Start menu. Uninstall any time via Add/Remove
   Programs, just like any other Windows program.

No Python required. No admin rights required.

> **First-run SmartScreen notice:** the installer is currently unsigned, so
> Windows may say *"Windows protected your PC"*. Click **More info → Run
> anyway** after verifying the checksum (below). A signed installer is
> planned.

## Why you can trust it

- **No network calls**, no telemetry, no analytics, no auto-updater, no
  background services — the app only runs while its window is open and
  never contacts any server. Audit the `app/` directory yourself; there
  are no HTTP clients imported anywhere.
- **Open source under MIT** — every line is public. Anyone can read, audit,
  fork, or rebuild it.
- **Reproducible builds on GitHub** — the Windows installer is built by
  our public GitHub Actions workflow from a specific commit. No installer
  is ever uploaded by hand.
- **Copy by default** — the app never deletes your source files unless you
  explicitly pick *Move*, and then only after each destination copy is
  hash-verified byte-for-byte.
- **Duplicates are isolated, never dropped** — any exact-duplicate files
  land under `Duplicates/` so you can review them before deleting.

See [`SECURITY.md`](SECURITY.md) for the full trust model.

## Features

- **Two modes:** *Folder picker* (review each folder name, tick which to
  keep, optionally split one by EXIF time) or *Flatten all* (single
  destination folder, no subfolders).
- **Dynamic categorization** with no predefined list — categories come
  from your folder names, not some hard-coded taxonomy.
- **Copy or Move**, defaulting to Copy for safety. Source directories
  are preserved in both modes.
- **Chronological rename** using EXIF `DateTimeOriginal` (falls back to
  RAW tags, then filesystem mtime) so destination files sort in capture
  order in any file manager.
- **Cryptographic deduplication** via chunked MD5 (auto-upgraded to
  xxHash if available) with a byte-size pre-filter so files with unique
  sizes skip hashing.
- **Collision handling:** two distinct files with the same name get an
  auto-incrementing `_1`, `_2`, … suffix.
- **Responsive GUI** built on PyQt6 with a `QThread` + `ThreadPoolExecutor`
  pipeline. Cancel is graceful — in-flight copies finish, the rest are
  skipped.

## Publish a new release (maintainer)

Every time you push a git tag starting with `v`, GitHub Actions builds the
installer, computes the SHA-256, generates a sigstore attestation, and
attaches all three to a new GitHub Release.

```
git tag v1.0.0
git push origin v1.0.0
```

Or click **Actions → Build installer → Run workflow** to test without
publishing (produces a downloadable workflow artifact instead).

## Run from source (developers)

```
pip install -r requirements.txt
python -m app.main
```

Requires Python 3.10+.

## Build the installer locally

On Windows with Python 3.10+ and
[Inno Setup 6](https://jrsoftware.org/isdl.php) installed:

```
build.bat
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
```

Output: `Output\SemanticFileAggregator-Setup.exe`.

## Development verification

```
python generate_test_data.py        # builds _test_tree/source + destination
python -m pytest tests/ -v          # 16 engine tests
```

## Reporting issues

Use the repo's [Issues](../../issues) tab. For anything sensitive, email the
maintainer listed in the repo's profile.

## Contributing

Pull requests welcome. Keep the engine GUI-agnostic (see `app/engine/`);
the UI lives under `app/ui/`. All engine additions should come with a test
in `tests/`.
