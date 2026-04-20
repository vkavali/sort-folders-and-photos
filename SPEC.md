# Semantic File Aggregator — Specification

> Plan-mode document. No application code has been written yet. Please review
> and approve (or request changes) before I proceed to implementation.

## 1. Purpose

A modern Windows desktop utility that walks a deeply nested folder tree
(typical of wedding photographers: `Shoot/Day1/RAW/sangeeet/photographer_A/...`),
maps user-created folder names onto a curated list of canonical event
categories via fuzzy string matching, then flattens every discovered media file
into a single top-level category folder — renaming by EXIF timestamp,
deduplicating by cryptographic hash, and preserving every unique byte.

## 2. Target Platform & Stack

| Area | Choice | Rationale |
| --- | --- | --- |
| Language | Python 3.10+ | Modern typing, `match`, generous library support |
| UI | PyQt6 | First-class Windows look & feel; `QThread`/`pyqtSignal` for safe async UI |
| Fuzzy matching | `rapidfuzz` | C++ accelerated Levenshtein; `token_sort_ratio` |
| EXIF | `Pillow` (primary) + `exifread` (fallback) | Pillow covers JPEG/PNG/TIFF; exifread handles many RAW variants |
| Hashing | `hashlib` (MD5 with optional `xxhash` if installed) | MD5 is fast & collision-safe for dedupe; xxhash optional perf win |
| Concurrency | `QThread` worker + `ThreadPoolExecutor` inside it | Keeps GUI thread free; I/O-bound parallelism |
| Packaging | Plain `python app/main.py`; optional `pyinstaller` note | Run anywhere with requirements installed |

## 3. File / Module Layout

```
sort-folders-and-photos/
├── SPEC.md                      # this document
├── README.md                    # quickstart + screenshots (post-impl)
├── requirements.txt             # PyQt6, rapidfuzz, Pillow, exifread
├── app/
│   ├── __init__.py
│   ├── main.py                  # entry point: builds QApplication, shows MainWindow
│   ├── categories.py            # CANONICAL_CATEGORIES list + synonym hints
│   ├── engine/
│   │   ├── __init__.py
│   │   ├── scanner.py           # os.scandir recursive walker → yields MediaItem
│   │   ├── matcher.py           # rapidfuzz wrapper: folder_name → (category, score)
│   │   ├── exif.py              # DateTimeOriginal extraction + fallback to mtime
│   │   ├── hasher.py            # chunked MD5 (8 MiB) + optional xxhash
│   │   ├── planner.py           # builds the move plan (src → dst, collisions, dupes)
│   │   └── executor.py          # copy-then-verify-then-delete worker
│   ├── workers/
│   │   ├── __init__.py
│   │   ├── scan_worker.py       # QThread: scan + hint mappings; emits progress
│   │   └── process_worker.py    # QThread: hash + execute plan; emits progress/log
│   └── ui/
│       ├── __init__.py
│       ├── main_window.py       # root window; wires workers + pages
│       ├── source_page.py       # pick root dir + destination dir
│       ├── mapping_page.py      # QTableView of folder → category dropdowns
│       ├── progress_page.py     # determinate QProgressBar + live log + cancel
│       └── summary_page.py      # final report: moved / duplicates / collisions
├── generate_test_data.py        # builds dummy nested tree for self-test
└── tests/
    ├── __init__.py
    ├── test_matcher.py          # fuzzy mapping unit tests
    ├── test_hasher.py           # hash determinism / collision behavior
    └── test_planner.py          # collision + duplicate logic
```

Rationale: strict separation so the `engine/` package is GUI-agnostic (unit
testable in isolation); `workers/` is the bridge from engine to Qt signals;
`ui/` contains only presentation.

## 4. Data Model

```python
@dataclass(frozen=True)
class MediaItem:
    source_path: Path
    parent_folder: str      # leaf directory name used for matching
    size_bytes: int

@dataclass
class Mapping:
    parent_folder: str
    suggested_category: str       # rapidfuzz best match
    confidence: float             # 0..100
    chosen_category: str          # editable by user; may == suggested or "Unsorted"

@dataclass
class PlannedMove:
    item: MediaItem
    category: str
    dest_filename: str            # timestamped + collision-suffixed
    dest_path: Path
    hash_digest: Optional[str]    # filled in during execution
    status: Literal["pending","moved","duplicate","collision_renamed","error"]
    message: str
```

## 5. Canonical Categories (configurable)

Defaults live in `app/categories.py`:

```
Engagement, Haldi, Mehendi, Sangeet, Wedding, Reception,
Pre-Wedding, Post-Wedding, Portraits, Candid, Drone, Unsorted
```

Any folder whose best fuzzy score is **below 70** is auto-assigned `Unsorted`
(user can override in the mapping table).

## 6. Fuzzy Matching Rules

- Normalize: lowercase, strip non-alphanumerics, collapse whitespace.
- Score each parent folder against each canonical category using
  `rapidfuzz.fuzz.token_sort_ratio`.
- Pick the max; if max < `MATCH_THRESHOLD` (default 70) → `Unsorted`.
- Cache `{parent_folder: (category, score)}` so repeated folders resolve once.

## 7. EXIF & Timestamp Rules

1. Try Pillow `_getexif()` → tag `36867` (`DateTimeOriginal`).
2. Fallback to `exifread` for RAW (`.raw`, `.cr2`, `.nef`, `.arw`).
3. Fallback to filesystem `mtime` if no EXIF present.
4. Reformat `YYYY:MM:DD HH:MM:SS` → `YYYYMMDD_HHMMSS`.
5. Final destination filename: `YYYYMMDD_HHMMSS_<original_basename><ext>`.
6. If two distinct files (different hashes) collide on that name, append
   `_1`, `_2`, … until unique.
7. If identical hashes collide, the later file is routed to
   `<destination_root>/Duplicates/<original_relative_path>` instead of the
   category folder — never silently dropped.

## 8. Hashing

- Chunk size: 8 MiB.
- Algorithm: MD5 via `hashlib.md5()` (adequate for dedupe; not a security use).
- Optional: if `xxhash` is importable, use `xxhash.xxh64()` for ~4× speed on
  large RAW files (detected at runtime, no hard dependency).
- Hashes are computed lazily — only when a destination-name collision occurs
  OR as part of the per-file processing step — and cached per `source_path`
  to avoid double reads.

## 9. Concurrency Model

```
MainWindow (GUI thread)
 ├── ScanWorker(QThread)
 │    └── engine.scanner.walk() → list[MediaItem]
 │    └── engine.matcher.suggest() → list[Mapping]
 │    └── emits: progress(int), scan_done(list[MediaItem], list[Mapping])
 └── ProcessWorker(QThread)
      └── ThreadPoolExecutor(max_workers=min(8, os.cpu_count()*2))
           └── per-file: hash → plan → copy → verify-hash → delete-source
      └── emits: file_done(PlannedMove), progress(done, total), log(str)
```

Safety guarantees:
- Only the worker thread touches the filesystem and the plan list.
- Only `pyqtSignal` emissions cross thread boundaries (no shared mutable state).
- `QThread.requestInterruption()` is polled between files for graceful cancel.
- **Copy-then-move**: `shutil.copy2` to destination, re-hash destination,
  compare, then `os.remove(source)`. If verify fails the destination is
  removed and the source is left intact.

## 10. UI Flow (4 stacked pages in a `QStackedWidget`)

1. **Source Page** — pick *Source Root* and *Destination Root* (required
   distinct; destination auto-creates). Button: **Scan**.
2. **Mapping Page** — `QTableView` with columns:
   `Folder Name | File Count | Suggested | Confidence | Chosen (dropdown)`.
   Button: **Start Processing**.
3. **Progress Page** — determinate `QProgressBar`, live scrolling log
   (`QPlainTextEdit`, append-only), **Cancel** button.
4. **Summary Page** — counts: moved, duplicates isolated, collisions renamed,
   errors. Button: **Open Destination** / **Done**.

## 11. Error Handling

- Any per-file exception is caught, logged, and marked `status="error"` —
  the pipeline continues for remaining files.
- Destination write failures (permission, disk full) bubble up to the UI
  as a single modal; partial work is preserved (copy-then-move means
  source files remain on failure).
- Cancel mid-run: in-flight copies finish, pending files are skipped, user
  lands on Summary with partial counts.

## 12. Self-Verification Plan (step 3 of the workflow)

`generate_test_data.py` will create under `./_test_tree/source/`:

```
Day1/
  engagegem et/            # misspelled → Engagement
    IMG_0001.JPG           # unique content, unique EXIF
    IMG_0002.JPG
  sangeeet/                # misspelled → Sangeet
    IMG_0001.JPG           # SAME NAME as above, DIFFERENT content
    DSC_9000.JPG           # EXACT DUPLICATE of Day2/.../DSC_9000.JPG
Day2/
  haldi_shots/             # → Haldi
    DSC_9000.JPG           # exact duplicate (same bytes)
    raw/
      clip1.mp4            # no EXIF → falls back to mtime
  weddng/                  # → Wedding
    IMG_0001.JPG           # another same-name, different-content
randomjunk/                 # low score → Unsorted
  note.png
```

Expected outcome after run:
- `destination/Engagement/`, `destination/Sangeet/`, `destination/Haldi/`,
  `destination/Wedding/`, `destination/Unsorted/` all populated.
- All files prefixed `YYYYMMDD_HHMMSS_`.
- Three `IMG_0001.JPG`-derived files land in three different categories —
  no collision because different categories. But where same-name different-
  content *do* collide inside one category, the second gets `_1` appended.
- `DSC_9000.JPG` appears exactly once under `Haldi/`; the second copy is
  isolated into `destination/Duplicates/...`.
- Source tree still contains only files that failed or were skipped.

## 13. Out of Scope (explicit non-goals)

- No cloud upload, no network I/O.
- No image preview thumbnails (would balloon memory for large shoots).
- No undo log beyond the Duplicates folder + source-preserved-on-error.
- No macOS/Linux-specific theming (app runs but visuals tuned for Windows).

---

## Open Questions for Approval

1. **Canonical category list** — is the list in §5 acceptable, or would you
   like me to add/remove categories (e.g., Baraat, Cocktail, Reception-Night)?
2. **Match threshold** — happy with 70, or prefer stricter (e.g., 80)?
3. **Hash algorithm** — MD5 default is fine? (xxhash auto-used if installed.)
4. **Cancel semantics** — finish-in-flight-then-stop, as specced? Or hard-abort?
5. **Destination layout** — flat `<dest>/<Category>/<file>` as specced, or
   `<dest>/<Category>/<YYYY>/<file>` with year sub-buckets?

**If this plan looks good, reply "approved" (optionally with answers to the
open questions) and I'll proceed to implementation + test harness + self-run.**
