# Semantic File Aggregator — Specification (Revision 2)

> **Plan-mode document — revised per reviewer feedback.**
> The first revision assumed a fixed list of wedding-event categories; that
> assumption is dropped. This revision introduces two user-selectable
> processing modes and a dynamic clustering engine that learns categories
> on the fly from whatever folder names are actually present.
>
> No new application code has been written against this revision yet —
> scaffold files from the earlier revision will be refactored only after
> you approve the revised plan below.

---

## 1. Purpose

A modern desktop utility that walks a deeply nested folder tree and either

1. **Flattens** every discovered media file into a single master destination, or
2. **Dynamically groups** files into categories that are *discovered from the
   folder names themselves* — no hard-coded taxonomy.

In both modes the app renames by EXIF timestamp, deduplicates by cryptographic
hash, and preserves every unique byte (duplicates are isolated, never dropped).

---

## 2. Two Core Processing Modes

The first UI page (Source Page) now asks the user to pick one of:

### Mode A — **Flatten All**

- Every media file ends up in `<destination>/` directly.
- Destination filename: `YYYYMMDD_HHMMSS_<original_basename><ext>`.
- Collision / duplicate logic identical to Mode B but inside a single folder.
- No mapping step; the Mapping Page is skipped and we go straight to Progress.

### Mode B — **Dynamic Grouping** (default)

- The app infers categories by clustering the *leaf parent folder names* that
  contain media.
- The UI shows a table of clusters → representative labels → member folders,
  and lets the user rename a cluster or merge two clusters before the move.
- Files land in `<destination>/<cluster_label>/<timestamped_name>`.

There is **no predefined list of canonical categories.**
`app/categories.py` from revision 1 is removed entirely.

---

## 3. Target Platform & Stack

| Area | Choice | Rationale |
| --- | --- | --- |
| Language | Python 3.10+ | `match`, modern typing, dataclasses |
| UI | PyQt6 | Responsive, `QThread`/`pyqtSignal` for safe async UI |
| Similarity | `rapidfuzz` | C++-accelerated `token_sort_ratio` for pairwise distances |
| Clustering | `rapidfuzz` + union-find (single-linkage) | See §6 for why we pick this over PolyFuzz |
| EXIF | `Pillow` + `exifread` (RAW fallback) | Broad format coverage |
| Hashing | `hashlib` MD5, opportunistic `xxhash` xxh64 upgrade | MD5 for dedup; xxhash for speed if installed |
| Concurrency | `QThread` host + `ThreadPoolExecutor` inside | GUI stays responsive, I/O-bound parallelism |

**Note on PolyFuzz:** PolyFuzz is a lovely high-level wrapper but its default
install pulls in `sentence-transformers` + PyTorch (~2 GB) and its
non-embedding backends reduce to exactly the rapidfuzz + linkage approach we
implement here. We therefore re-use PolyFuzz's algorithm (group-by-similarity
with single linkage) without the heavy dependency footprint. If you still want
a `polyfuzz` dependency I can add it.

---

## 4. File / Module Layout (revised)

```
sort-folders-and-photos/
├── SPEC.md                        # this document
├── README.md                      # quickstart (post-impl)
├── requirements.txt               # PyQt6, rapidfuzz, Pillow, exifread, xxhash
├── app/
│   ├── __init__.py
│   ├── main.py                    # QApplication entry point
│   ├── config.py                  # tunables: similarity threshold, chunk sizes
│   ├── engine/
│   │   ├── __init__.py
│   │   ├── scanner.py             # os.scandir walk → MediaItem stream
│   │   ├── clusterer.py           # NEW: folder-name clustering (replaces matcher.py)
│   │   ├── exif.py                # DateTimeOriginal extraction + fallbacks
│   │   ├── hasher.py              # chunked MD5 with xxhash upgrade
│   │   ├── planner.py             # builds PlannedMove list (supports both modes)
│   │   └── executor.py            # copy-then-verify-then-delete; thread-safe
│   ├── workers/
│   │   ├── __init__.py
│   │   ├── scan_worker.py         # QThread: scan + cluster
│   │   └── process_worker.py      # QThread: execute plan
│   └── ui/
│       ├── __init__.py
│       ├── main_window.py         # QStackedWidget host
│       ├── source_page.py         # MODE RADIO + src/dest pickers
│       ├── mapping_page.py        # cluster table: rename + merge + member peek
│       ├── progress_page.py       # determinate progress + live log + cancel
│       └── summary_page.py        # per-status counts + open-destination
├── generate_test_data.py          # builds messy nested tree with no fixed taxonomy
└── tests/
    ├── __init__.py
    ├── test_clusterer.py          # NEW: single-linkage + rename + merge
    ├── test_hasher.py             # digest determinism & algorithm tagging
    └── test_planner.py            # flatten mode + grouped mode + collisions
```

*No `categories.py` anywhere.* The category label for every planned move is
either the user-chosen cluster label (Mode B) or the empty string (Mode A,
meaning "write to destination root").

---

## 5. Data Model

```python
@dataclass(frozen=True)
class MediaItem:
    source_path: Path
    parent_folder: str     # leaf directory name; used for clustering
    size_bytes: int

@dataclass
class Cluster:
    id: int                         # stable within a scan
    label: str                      # editable representative label
    members: list[str]              # parent-folder names in this cluster
    file_count: int
    avg_internal_similarity: float  # quality metric, 0..100

@dataclass
class PlannedMove:
    item: MediaItem
    category: str                   # "" in Flatten mode, cluster.label in Group mode
    dest_filename: str = ""
    dest_path: Path | None = None
    hash_digest: str | None = None
    status: Literal["pending","moved","duplicate","collision_renamed",
                    "error","skipped"] = "pending"
    message: str = ""
```

---

## 6. Dynamic Clustering Engine (replaces old matcher)

Input: the set of unique leaf parent-folder names that actually contain media.
Output: a `list[Cluster]`.

### Algorithm (single-linkage agglomerative)

1. **Normalize** each folder name: lowercase, collapse non-alphanumerics to
   spaces, strip, then re-join.
2. **Pairwise similarity** matrix using
   `rapidfuzz.fuzz.token_sort_ratio` (0..100). This is the same distance
   PolyFuzz uses in its "RapidFuzz" mode.
3. **Build a graph**: add an edge between two folder names whenever their
   similarity ≥ `SIMILARITY_THRESHOLD` (default **80**).
4. **Find connected components** via union-find (equivalent to
   single-linkage clustering, same as PolyFuzz's default grouping).
5. For each component, pick a representative label = the member whose mean
   similarity to all other members is highest (medoid). Ties break on the
   shorter, alphabetically-first string.
6. Record `avg_internal_similarity` per cluster for UI transparency.

### User operations on the UI side

- **Rename** a cluster — changes `label` only; members unaffected.
- **Merge** two clusters — unions their members, keeps the label of whichever
  row the user dragged onto (or the left one by default).
- **Split** is *not* in scope for v1 (user can simply pick a stricter
  threshold and re-scan). Called out in §12.

### Why single linkage + rapidfuzz (and not K-means / DBSCAN)?

- Folder names are short strings; edit-distance is the natural metric.
- Single-linkage with a threshold is transparent: a user can predict which
  folders will merge.
- No hyperparameters beyond the threshold.
- Pure-Python + rapidfuzz = milliseconds for thousands of folder names.

---

## 7. Flatten Mode Specifics

- `clusterer` is not invoked.
- All `PlannedMove.category = ""`; `dest_path = <destination_root>`.
- Mapping Page is skipped in the UI flow.
- Collision / duplicate rules are otherwise identical.

---

## 8. EXIF & Timestamp Rules (unchanged from revision 1)

1. Pillow `_getexif()` → DateTimeOriginal (tag 36867).
2. Fallback: `exifread` for RAW (`.raw`, `.cr2`, `.nef`, `.arw`).
3. Fallback: filesystem `mtime`.
4. Reformat to `YYYYMMDD_HHMMSS`, prepend to the original basename.
5. Collision (different content, same name) → append `_1`, `_2`, …
6. Exact duplicate (same hash) → isolated to
   `<destination_root>/Duplicates/…` (never silently dropped).

---

## 9. Hashing (unchanged)

- 8 MiB chunked reads.
- `hashlib.md5` by default; `xxhash.xxh64` used when the `xxhash` package
  imports cleanly.
- Digest strings are tagged (`md5:…` / `xxh64:…`) so the two algorithms
  can never accidentally compare equal.

---

## 10. Concurrency Model (unchanged)

```
MainWindow (GUI thread)
 ├── ScanWorker(QThread)
 │    └── scanner.scan()  → list[MediaItem]
 │    └── clusterer.cluster() → list[Cluster]    (skipped in Flatten mode)
 │    └── emits: scan_progress(int),
 │               scan_done(list[MediaItem], list[Cluster])
 └── ProcessWorker(QThread)
      └── ThreadPoolExecutor(max_workers=min(8, os.cpu_count()*2))
           └── per file: hash → reserve → copy → verify-hash → delete-src
      └── emits: file_done(PlannedMove), progress(done, total), log(str)
```

Safety guarantees unchanged: only signals cross thread boundaries, a shared
thread-safe `_ReservationLedger` guarantees unique destination filenames, and
cancel = finish-in-flight-then-stop.

---

## 11. UI Flow (revised pages)

1. **Source Page**
   - **Mode** radio group: *Flatten All* / *Dynamic Grouping* (default).
   - Source Root picker (required).
   - Destination Root picker (required, auto-created, must not be inside src).
   - Similarity threshold slider (visible only when Dynamic Grouping is
     selected; default 80, range 50–99).
   - Button: **Scan**.
2. **Mapping Page** *(only shown in Dynamic Grouping mode)*
   - `QTableView` with columns: `Cluster Label (editable) | Members |
     File Count | Avg Similarity`.
   - Toolbar buttons: **Merge Selected**, **Re-cluster at…** (slider),
     **Reset Labels**.
   - Double-click the Members cell to peek at the folder list in a popover.
   - Button: **Start Processing**.
3. **Progress Page** — determinate `QProgressBar`, live append-only log,
   **Cancel**.
4. **Summary Page** — moved / duplicates isolated / collisions renamed /
   errors / skipped counts; **Open Destination** / **Done** buttons.

---

## 12. Error Handling & Cancel (unchanged)

- Per-file exceptions are isolated, logged, and the pipeline continues.
- Cancel = finish in-flight copies, skip the rest, land on Summary with
  partial counts.
- Failed verification removes the partial destination and leaves the source
  intact (copy-then-verify-then-delete).

---

## 13. Self-Verification Plan (revised)

`generate_test_data.py` creates a `_test_tree/source/` that is **deliberately
taxonomy-agnostic** — the old wedding-specific labels are gone. Example:

```
ProjectAlpha/
  alpha_raw/
    IMG_0001.JPG           # unique content
  Alpha Raw/               # near-duplicate name → should cluster with alpha_raw
    IMG_0002.JPG
  Alpha-final/             # moderate similarity → clusters at 70, not at 90
    IMG_0001.JPG           # SAME NAME as above, DIFFERENT content
ClientBravo/
  bravo_shoot_day1/
    DSC_9000.JPG           # unique
    DSC_9001.JPG
  Bravo Shoot Day 2/
    DSC_9000.JPG           # EXACT duplicate of the one above
unrelated_notes/            # singleton cluster — no siblings
  notes.png
videos/
  clip1.mp4                 # no EXIF → mtime fallback
```

Expected outcome, threshold=80, Dynamic Grouping:
- 3 or 4 clusters: `{alpha_raw, Alpha Raw, Alpha-final}`,
  `{bravo_shoot_day1, Bravo Shoot Day 2}`, `{unrelated_notes}`, `{videos}`.
- All files end up under `<dest>/<cluster_label>/` with timestamp prefix.
- Same-name-different-content `IMG_0001.JPG` collision is auto-suffixed.
- Same-hash `DSC_9000.JPG` appears once in the Bravo cluster; second copy
  lands in `Duplicates/`.

Expected outcome, **Flatten All**:
- All files under `<dest>/` directly, timestamped.
- Duplicates isolated into `<dest>/Duplicates/`.
- Collisions resolved with `_N` suffixes.

---

## 14. Out of Scope (explicit non-goals)

- Cluster splitting in the UI (user re-runs with stricter threshold instead).
- Cloud / network storage.
- Thumbnail preview.
- Semantic (embedding-based) clustering — only string similarity for v1.
  If you want sentence-transformers-grade clustering, that's a different
  dependency conversation.

---

## Consolidated Answers to Previous Open Questions

| # | Question | Decision |
| - | -------- | -------- |
| 1 | Canonical category list | **Dropped entirely.** Categories are discovered dynamically. |
| 2 | Match threshold | Renamed to **`SIMILARITY_THRESHOLD`**, default **80**, user-adjustable slider. |
| 3 | Hash algorithm | **MD5 default, xxhash opportunistic upgrade.** |
| 4 | Cancel semantics | **Finish in-flight, then stop.** |
| 5 | Destination layout | **Flat** `<dest>/<Category>/<file>` in Group mode, **flat** `<dest>/<file>` in Flatten mode. No year buckets. |

---

## New Open Questions

1. **PolyFuzz dependency** — happy with the pure `rapidfuzz + union-find`
   implementation (algorithmically identical to PolyFuzz's RapidFuzz mode),
   or do you want me to add `polyfuzz` as an explicit dependency?
2. **Merge UX** — merge via (a) multi-select + "Merge" button,
   (b) drag-and-drop rows, or (c) both? I'll default to (a) for simplicity
   unless you want (c).
3. **Default mode** — launch in *Dynamic Grouping* as planned, or
   *Flatten All*?

**Reply "approved" (optionally with answers) and I'll refactor the scaffold
modules I've already written, write the clustering engine, finish the UI,
and run the self-verification suite.**
